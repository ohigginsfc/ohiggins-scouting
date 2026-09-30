"""Regresiones de la segunda auditoría: entregas inciertas, cobertura y operación Docker."""
import json
import shutil
import smtplib
import subprocess
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from scouting.comet import adelantados
from scouting.comet.ledger import MemoryLedger
from scouting.comet.pipeline import compute_all
from tests import comet_tiny
from tests.comet_tiny import sheet_row
from tests.test_comet_ops import FakeSMTP, SMTP_ENV
from tests.test_comet_pages import ADMIN, SCRIPT
from tests.test_comet_review_fixes import run_job, screen_env


@pytest.mark.parametrize('failure', [smtplib.SMTPServerDisconnected, TimeoutError, RuntimeError])
def test_lost_ack_after_acceptance_never_resends(failure):
    class AcceptedWithoutAck(FakeSMTP):
        def send_message(self, message):
            super().send_message(message)
            raise failure('synthetic lost acknowledgment')

    FakeSMTP.instances.clear()
    ledger = MemoryLedger()
    stored = {'digest_recipients': {'value': ['a@example.test', 'b@example.test'], 'confirmed': True}}
    code, _ = run_job(ledger=ledger, smtp=AcceptedWithoutAck, stored=stored)
    assert code == 1
    assert ledger.status(date(2026, 3, 16), 'a@example.test') == ('reservado', 1)
    assert ledger.status(date(2026, 3, 16), 'b@example.test') == ('fallido', 1), 'no se inició su envío'
    code, output = run_job(ledger=ledger, stored=stored)
    assert code == 1 and 'En duda' in output
    accepted = [m['To'] for instance in FakeSMTP.instances for m in instance.sent]
    assert accepted == ['a@example.test', 'b@example.test'], 'solo se reintenta el destinatario no procesado'


def test_failure_before_smtp_session_can_be_retried():
    def unavailable(*args, **kwargs):
        raise smtplib.SMTPServerDisconnected('synthetic unavailable before sending')

    FakeSMTP.instances.clear()
    ledger = MemoryLedger()
    stored = {'digest_recipients': {'value': ['a@example.test'], 'confirmed': True}}
    assert run_job(ledger=ledger, smtp=unavailable, stored=stored)[0] == 1
    assert ledger.status(date(2026, 3, 16), 'a@example.test') == ('fallido', 1)
    assert run_job(ledger=ledger, stored=stored)[0] == 0
    assert sum(len(s.sent) for s in FakeSMTP.instances) == 1


def test_conflict_in_another_category_excludes_all_advancement_rates(screen_env):
    raw = comet_tiny.build(extra_sheet=[sheet_row(4, 2, True, True, 60, goals=2, comp=200)])
    computed = compute_all(raw)
    ds = computed.ds
    assert set(ds.blocked_players(2026)['personid']) == {'2'}
    assert not adelantados.ahead_players(ds, 2026)['personid'].isin(['2']).any()
    assert not adelantados.ahead_permanence(ds, 2026)['personid'].isin(['2']).any()
    assert not adelantados.ahead_permanence_summary(ds, 2026)['personid'].isin(['2']).any()
    assert adelantados.ahead_share_by_category(ds, 2026)['adelantados'].sum() == 0
    assert 'Adelantados' not in set(adelantados.ahead_vs_peers(ds, computed.cat, 2026)['group'])
    assert len(ds.facts[(ds.facts['personid'] == '2') & ds.facts['participated']]) == 3, 'las actuaciones válidas se conservan'
    screen_env(raw)
    app = AppTest.from_string(SCRIPT.format(module='comet_insights', function='page_adelantados', admin=ADMIN), default_timeout=90).run()
    assert not app.exception and any('permanencia y comparación' in w.value for w in app.warning)


def test_seniority_caption_describes_selected_source(screen_env, monkeypatch):
    raw = comet_tiny.build()
    raw['players']['datefrom'] = pd.Timestamp('2019-01-01')
    screen_env(raw)
    import comet_context
    monkeypatch.setattr(comet_context, 'load_config', lambda: (
        {'seniority_rule': {'value': 'datefrom', 'confirmed': True}},
        comet_context.EMPTY_MARKS, comet_context.EMPTY_PERIODS, None))
    app = AppTest.from_string(SCRIPT.format(module='comet_insights', function='page_indicators', admin=ADMIN), default_timeout=90).run()
    assert not app.exception
    captions = ' '.join(c.value for c in app.caption)
    assert 'La antigüedad usa la fecha «datefrom»' in captions
    assert 'La antigüedad cuenta desde el primer partido' not in captions


def test_compose_passes_smtp_from_private_env_file(tmp_path):
    if not shutil.which('docker'):
        pytest.skip('Docker Compose no disponible')
    values = dict(PORTAL_SUPABASE_URL='https://example.test', PORTAL_SUPABASE_PUBLISHABLE_KEY='synthetic',
                  PORTAL_SUPABASE_SECRET_KEY='synthetic', PORTAL_AUTH_DATABASE_URL='synthetic',
                  SCOUTING_DATABASE_URL='synthetic', COMET_DATABASE_URL='synthetic', **SMTP_ENV,
                  COMET_DIGEST_SMTP_STARTTLS='1')
    envfile = tmp_path / 'synthetic.env'
    envfile.write_text('\n'.join(f'{k}={v}' for k, v in values.items()), encoding='utf8')
    proc = subprocess.run(['docker', 'compose', '--env-file', str(envfile), '-f',
                           str(Path('docker-compose.portal.yml').resolve()), 'config', '--format', 'json'],
                          check=True, capture_output=True, text=True, timeout=30)
    forwarded = json.loads(proc.stdout)['services']['portal']['environment']
    for key in SMTP_ENV:
        assert forwarded[key] == SMTP_ENV[key]
    assert forwarded['COMET_DIGEST_SMTP_STARTTLS'] == '1'
