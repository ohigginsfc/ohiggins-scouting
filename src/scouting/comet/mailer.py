"""Envío del resumen semanal por correo. Solo lo invoca el script operativo con `--send`."""
from __future__ import annotations

import smtplib
import ssl
from dataclasses import dataclass
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


def send_digest(digest: Digest, recipients: Sequence[str], smtp: SmtpConfig, *, smtp_factory=smtplib.SMTP) -> int:
    """Envía un correo individual por destinatario (nadie ve a los demás). Devuelve cuántos envió."""
    valid = [r.strip() for r in recipients if '@' in r and ' ' not in r.strip()]
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
