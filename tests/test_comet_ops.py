"""Resumen semanal por correo (nada se envía sin condiciones) y utilidades operativas de COMET."""
import ast
from pathlib import Path

import pytest

from scouting.comet import mailer
from scouting.comet.digest import Digest
from scouting.comet.ledger import MemoryLedger
from scripts import comet_demo_data, send_comet_weekly_digest as job
from tests import comet_tiny

DIGEST = Digest(subject='Resumen semanal COMET', text='texto', html='<p>html</p>', week_start=None, week_end=None,
                matches=1, alerts=0)
SMTP_ENV = {'COMET_DIGEST_SMTP_HOST': 'smtp.example.test', 'COMET_DIGEST_SMTP_FROM': 'comet@example.test',
            'COMET_DIGEST_SMTP_PORT': '2525', 'COMET_DIGEST_SMTP_USER': 'user', 'COMET_DIGEST_SMTP_PASSWORD': 'synthetic-secret'}


class FakeSMTP:
    instances = []

    def __init__(self, host, port, timeout=None):
        self.host, self.port, self.sent, self.calls = host, port, [], []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        self.calls.append('starttls')

    def login(self, user, password):
        self.calls.append(('login', user, password))

    def send_message(self, message):
        self.sent.append(message)


@pytest.fixture(autouse=True)
def reset_smtp():
    FakeSMTP.instances.clear()


def test_smtp_config_only_from_environment_and_incomplete_means_none():
    config = mailer.smtp_config_from_env(SMTP_ENV)
    assert (config.host, config.port, config.sender, config.starttls) == ('smtp.example.test', 2525, 'comet@example.test', True)
    assert mailer.smtp_config_from_env({'COMET_DIGEST_SMTP_HOST': 'x'}) is None
    assert mailer.smtp_config_from_env({**SMTP_ENV, 'COMET_DIGEST_SMTP_FROM': 'sin-arroba'}) is None
    assert mailer.smtp_config_from_env({**SMTP_ENV, 'COMET_DIGEST_SMTP_STARTTLS': '0'}).starttls is False


def test_each_recipient_gets_an_individual_multipart_message():
    config = mailer.smtp_config_from_env(SMTP_ENV)
    sent = mailer.send_digest(DIGEST, ['a@example.test', 'no valido', 'b@example.test'], config, smtp_factory=FakeSMTP)
    server = FakeSMTP.instances[0]
    assert sent == 2 and [m['To'] for m in server.sent] == ['a@example.test', 'b@example.test']
    assert server.calls == ['starttls', ('login', 'user', 'synthetic-secret')]
    message = server.sent[0]
    assert message['From'] == 'comet@example.test' and message['Subject'] == 'Resumen semanal COMET'
    assert message.is_multipart() and {p.get_content_type() for p in message.iter_parts()} == {'text/plain', 'text/html'}
    with pytest.raises(ValueError):
        mailer.send_digest(DIGEST, ['sin arroba', ' '], config, smtp_factory=FakeSMTP)


def run_job(argv, stored, env=None, printed=None, ledger=None, periods=None):
    raw = comet_tiny.build()
    lines = printed if printed is not None else []
    code = job.run(argv, env=env or {}, load_raw=lambda: raw,
                   stored=(stored, job.NO_PERIODS if periods is None else periods, None),
                   now=comet_tiny.TODAY, smtp_factory=FakeSMTP, ledger=ledger if ledger is not None else MemoryLedger(),
                   out=lines.append)
    return code, '\n'.join(lines)


def test_default_run_is_a_preview_and_sends_nothing(tmp_path):
    target = tmp_path / 'resumen.html'
    code, output = run_job(['--week-of', '2026-03-16', '--html-out', str(target)],
                           {'digest_recipients': {'value': ['a@example.test'], 'confirmed': True}}, SMTP_ENV)
    assert code == 0 and 'no se envió nada' in output and 'Campeonato U-15 2026' in output
    assert FakeSMTP.instances == [] and '<p' in target.read_text(encoding='utf8')


@pytest.mark.parametrize('stored, env, reason', [
    ({}, SMTP_ENV, 'destinatarios'),                                                           # sin destinatarios
    ({'digest_recipients': {'value': ['a@example.test'], 'confirmed': False}}, SMTP_ENV, 'destinatarios'),  # sin confirmar
    ({'digest_recipients': {'value': ['a@example.test'], 'confirmed': True}}, {}, 'COMET_DIGEST_SMTP_HOST'),  # sin correo
])
def test_send_is_refused_unless_recipients_are_confirmed_and_smtp_is_configured(stored, env, reason):
    code, output = run_job(['--week-of', '2026-03-16', '--send'], stored, env)
    assert code == 2 and reason in output and FakeSMTP.instances == []


def test_send_succeeds_only_with_confirmed_recipients_and_smtp():
    stored = {'digest_recipients': {'value': ['a@example.test', 'b@example.test'], 'confirmed': True}}
    code, output = run_job(['--week-of', '2026-03-16', '--send'], stored, SMTP_ENV)
    assert code == 0 and 'Enviados ahora: 2' in output
    assert [m['To'] for m in FakeSMTP.instances[0].sent] == ['a@example.test', 'b@example.test']


def test_job_uses_previous_full_week_by_default():
    lines = []
    job.run([], env={}, load_raw=lambda: comet_tiny.build(), stored=({}, job.NO_PERIODS, None), now=pd_ts('2026-03-25'),
            out=lines.append)
    assert 'semana del 16 al 22 de marzo de 2026' in '\n'.join(lines)


def pd_ts(text):
    import pandas as pd
    return pd.Timestamp(text)


def test_job_warns_when_stored_rules_are_unavailable():
    lines = []
    job.run(['--week-of', '2026-03-16'], env={}, load_raw=lambda: comet_tiny.build(),
            stored=({}, job.NO_PERIODS, 'Falta aplicar db/portal/003_comet_followup.sql en Supabase.'),
            now=comet_tiny.TODAY, out=lines.append)
    assert 'se usan las reglas por defecto' in lines[0]


def test_portal_screens_never_use_the_job_only_store_function():
    """`load_all_for_job` no comprueba sesión: solo puede usarla el script operativo."""
    for path in list(Path('app').rglob('*.py')):
        tree = ast.parse(path.read_text(encoding='utf8'))
        names = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)} | \
                {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        assert not {n for n in names if n.endswith('_for_job')}, f'{path} no debe usar funciones *_for_job'


def test_demo_data_is_deterministic_and_fictional():
    first, second = comet_demo_data.build_raw(), comet_demo_data.build_raw()
    for key in first:
        assert first[key].equals(second[key]), f'{key} debe ser reproducible con la misma semilla'
    assert set(first['matches']['home_team']) | set(first['matches']['away_team']) >= {comet_demo_data.OWN_CLUB}
    assert all(name for name in first['players']['displayname'])
    assert first['matches']['matchdate'].max() <= comet_demo_data.TODAY
