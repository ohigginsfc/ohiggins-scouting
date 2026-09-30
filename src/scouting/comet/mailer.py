"""Envío del resumen semanal por correo. Solo lo invoca el script operativo con `--send`."""
from __future__ import annotations

import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Mapping, Optional, Sequence

from .digest import Digest


@dataclass(frozen=True)
class SmtpConfig:
    host: str
    port: int
    sender: str
    username: str = ''
    password: str = ''
    starttls: bool = True


def smtp_config_from_env(env: Mapping[str, str]) -> Optional[SmtpConfig]:
    """Lee COMET_DIGEST_SMTP_*; None si falta el servidor o el remitente. La clave solo viene del entorno."""
    host = env.get('COMET_DIGEST_SMTP_HOST', '').strip()
    sender = env.get('COMET_DIGEST_SMTP_FROM', '').strip()
    if not host or '@' not in sender:
        return None
    return SmtpConfig(host=host, port=int(env.get('COMET_DIGEST_SMTP_PORT', '587') or 587), sender=sender,
                      username=env.get('COMET_DIGEST_SMTP_USER', '').strip(),
                      password=env.get('COMET_DIGEST_SMTP_PASSWORD', ''),
                      starttls=env.get('COMET_DIGEST_SMTP_STARTTLS', '1') != '0')


def build_message(digest: Digest, sender: str, recipient: str) -> EmailMessage:
    message = EmailMessage()
    message['Subject'] = digest.subject
    message['From'] = sender
    message['To'] = recipient
    message.set_content(digest.text)
    message.add_alternative(digest.html, subtype='html')
    return message


def valid_recipients(recipients: Sequence[str]) -> list:
    """Correos válidos, en minúsculas y sin repetir (dos formas del mismo correo no reciben dos mensajes)."""
    seen, out = set(), []
    for recipient in recipients:
        text = str(recipient).strip().lower()
        if '@' in text[1:] and ' ' not in text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def send_digest(digest: Digest, recipients: Sequence[str], smtp: SmtpConfig, *, smtp_factory=smtplib.SMTP) -> int:
    """Envía un correo individual por destinatario (nadie ve a los demás). Devuelve cuántos envió.

    Bajo nivel y SIN registro de entregas: el script operativo usa `send_digest_once`.
    """
    valid = valid_recipients(recipients)
    if not valid:
        raise ValueError('No hay destinatarios válidos.')
    with smtp_factory(smtp.host, smtp.port, timeout=30) as server:
        if smtp.starttls:
            server.starttls(context=ssl.create_default_context())
        if smtp.username:
            server.login(smtp.username, smtp.password)
        for recipient in valid:
            server.send_message(build_message(digest, smtp.sender, recipient))
    return len(valid)


@dataclass
class DeliveryReport:
    sent: list = field(default_factory=list)          # enviados en esta ejecución
    already_sent: list = field(default_factory=list)  # ya se habían enviado (no se repiten)
    in_doubt: list = field(default_factory=list)      # reserva sin cerrar: podría haberse enviado, revisar a mano
    exhausted: list = field(default_factory=list)     # fallaron todos los intentos
    failed: list = field(default_factory=list)        # fallaron ahora (se reintentarán en la próxima ejecución)
    unrecorded: list = field(default_factory=list)    # no se pudo cerrar el registro: la reserva queda «en duda»

    @property
    def clean(self) -> bool:
        return not (self.in_doubt or self.exhausted or self.failed or self.unrecorded)


def _reason(exc: Exception) -> str:
    """Motivo corto del fallo, sin el texto del servidor (podría incluir direcciones o credenciales)."""
    code = getattr(exc, 'smtp_code', None)
    return f'{type(exc).__name__}{f" {code}" if code else ""}'


def send_digest_once(digest: Digest, recipients: Sequence[str], smtp: SmtpConfig, ledger, *,
                     smtp_factory=smtplib.SMTP, max_attempts: int = 3) -> DeliveryReport:
    """Envía como mucho una vez por semana y destinatario, con registro y reintento limitado.

    Cada destinatario se reserva en el registro ANTES de enviar; dos ejecuciones de la misma semana no
    envían dos veces (la segunda ve `enviado` o pierde la reserva). Solo un rechazo definitivo deja
    `fallido` para reintentar. Si se pierde la confirmación durante el envío, la reserva queda en duda.
    """
    valid = valid_recipients(recipients)
    if not valid:
        raise ValueError('No hay destinatarios válidos.')
    report, week = DeliveryReport(), digest.week_start
    to_send = []
    for recipient in valid:
        state = ledger.status(week, recipient)
        status, attempts = state if state else (None, 0)
        if status == 'enviado':
            report.already_sent.append(recipient)
        elif status == 'reservado':
            report.in_doubt.append(recipient)
        elif status == 'fallido' and attempts >= max_attempts:
            report.exhausted.append(recipient)
        elif ledger.reserve(week, recipient, max_attempts):
            to_send.append(recipient)
        else:  # otra ejecución la reservó justo antes
            report.in_doubt.append(recipient)
    if not to_send:
        return report

    def close(recipient: str, **outcome) -> None:
        try:
            ledger.finish(week, recipient, **outcome)
        except Exception:  # si no se puede cerrar, la reserva queda «en duda»: nunca se reenvía sola
            report.unrecorded.append(recipient)

    handled = set()
    try:
        with smtp_factory(smtp.host, smtp.port, timeout=30) as server:
            if smtp.starttls:
                server.starttls(context=ssl.create_default_context())
            if smtp.username:
                server.login(smtp.username, smtp.password)
            for recipient in to_send:
                try:
                    message = build_message(digest, smtp.sender, recipient)
                except Exception as exc:  # todavía no se ha llamado al transporte
                    handled.add(recipient)
                    report.failed.append(recipient)
                    close(recipient, sent=False, error=_reason(exc))
                    continue
                try:
                    server.send_message(message)
                except (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused,
                        smtplib.SMTPDataError, smtplib.SMTPHeloError, smtplib.SMTPNotSupportedError) as exc:
                    handled.add(recipient)
                    report.failed.append(recipient)
                    close(recipient, sent=False, error=_reason(exc))
                except Exception:  # DATA pudo ser aceptado antes de perder la confirmación
                    handled.add(recipient)
                    report.in_doubt.append(recipient)
                    # No cerrar como fallido: se duplicaría al reintentar. Detener esta sesión;
                    # los destinatarios aún no procesados sí pueden reintentarse.
                    raise
                else:
                    handled.add(recipient)
                    report.sent.append(recipient)
                    close(recipient, sent=True)
    except Exception as exc:  # sin conexión o sin sesión: lo reservado y no procesado queda fallido
        for recipient in to_send:
            if recipient not in handled:
                report.failed.append(recipient)
                close(recipient, sent=False, error=_reason(exc))
    return report
