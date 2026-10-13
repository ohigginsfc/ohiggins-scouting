"""Aviso operativo por ejecución; sin datos deportivos, trazas ni credenciales."""
import os
import smtplib
from email.message import EmailMessage
from scouting.comet.mailer import SmtpConfig, smtp_session, valid_recipients


def smtp_config(env):
    user, password = env.get('COMET_REPORT_SMTP_USER', ''), env.get('COMET_REPORT_SMTP_PASSWORD', '')
    if not user or not password:
        raise ValueError('Falta SMTP de avisos COMET')
    port = int(env.get('COMET_REPORT_SMTP_PORT', '465') or 465)
    if port not in (465, 587):
        raise ValueError('Usar SMTP seguro en puerto 465 o 587')
    return SmtpConfig(host=env.get('COMET_REPORT_SMTP_HOST', 'smtp.gmail.com'), port=port,
                        sender=user, username=user, password=password, starttls=port == 587, implicit_tls=port == 465)


def login(server, config):
    if config.starttls:
        import ssl
        server.starttls(context=ssl.create_default_context())
    server.login(config.username, config.password)


def check_smtp(*, env=None, smtp_factory=smtplib.SMTP):
    """Comprueba TLS y autenticación; no manda correo."""
    config = smtp_config(os.environ if env is None else env)
    with smtp_session(config, smtp_factory) as server:
        login(server, config)


def send_status(status, *, env=None, smtp_factory=smtplib.SMTP):
    env = os.environ if env is None else env
    if status not in ('success', 'failure'):
        raise ValueError('Estado de ejecución inválido')
    recipients = valid_recipients(env.get('COMET_REPORT_NOTIFICATION_TO', '').split(','))
    if not recipients:
        raise ValueError('Falta destinatario de avisos COMET')
    config = smtp_config(env)
    verdict = 'OK' if status == 'success' else 'ERROR'
    # Do not paste provider exceptions or tracebacks into emails; operator can inspect the private run.
    body = f'COMET: {verdict}.\nSincronización y reportes del repositorio unificado.\n'
    repo, run = env.get('GITHUB_REPOSITORY', ''), env.get('GITHUB_RUN_ID', '')
    if repo == 'ohigginsfc/ohiggins-scouting' and run.isdigit():
        body += f'Ejecución: https://github.com/{repo}/actions/runs/{run}\n'
    with smtp_session(config, smtp_factory) as server:
        login(server, config)
        for recipient in recipients:
            message = EmailMessage()
            message['Subject'], message['From'], message['To'] = f'[{verdict}] COMET — portal O’Higgins', config.sender, recipient
            message.set_content(body)
            server.send_message(message)
    return len(recipients)
