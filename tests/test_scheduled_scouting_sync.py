"""Weekly collection uses synthetic data and never an external provider or database."""
from datetime import datetime, timedelta, timezone

import pytest

from scouting import manual_sync as manual
from scouting import scheduled_sync as weekly
from tests.test_manual_sync import candidate, event, fake_players  # noqa: F401


def pipeline(monkeypatch):
    calls = []

    def collect(folder, fetch, **kwargs):
        calls.append(('collect', kwargs['resume']))
        state = candidate([event()])
        manual.save(folder / 'candidate.json', state)
        return state, [1]

    def publish(folder, *, apply=False):
        calls.append(('publish', apply))
        return {'dry_run': not apply, 'matches': 1, 'players': 1}

    monkeypatch.setattr(manual, 'collect', collect)
    monkeypatch.setattr(manual, 'publish', publish)
    return calls


def test_fresh_weekly_run_is_dry_by_default(tmp_path, monkeypatch):
    calls = pipeline(monkeypatch)
    result = weekly.run(tmp_path, lambda _: pytest.fail('synthetic pipeline'))
    assert calls == [('collect', False), ('publish', False)]
    assert result['status'] == 'validated' and result['applied'] is False
    assert manual.read(tmp_path / 'weekly-summary.json') == result


def test_weekly_apply_is_explicit(tmp_path, monkeypatch):
    calls = pipeline(monkeypatch)
    result = weekly.run(tmp_path, lambda _: None, apply=True)
    assert calls == [('collect', False), ('publish', True)]
    assert result['status'] == 'published' and result['applied'] is True


def test_partial_checkpoint_resumes_then_refreshes_to_current_cutoff(tmp_path, monkeypatch):
    state = candidate([event()])
    state['matches'] = {}
    manual.save(tmp_path / 'candidate.json', state)
    calls = pipeline(monkeypatch)
    weekly.run(tmp_path, lambda _: None, apply=True)
    assert calls == [('collect', True), ('collect', False), ('publish', True)]


def test_budget_exhaustion_preserves_checkpoint_and_never_publishes(tmp_path, monkeypatch):
    def exhausted(folder, fetch, **kwargs):
        state = candidate([event()])
        state['matches'] = {}
        manual.save(folder / 'candidate.json', state)
        raise manual.r.BudgetReached('budget')

    monkeypatch.setattr(manual, 'collect', exhausted)
    monkeypatch.setattr(manual, 'publish', lambda *a, **k: pytest.fail('partial publication'))
    with pytest.raises(manual.r.BudgetReached):
        weekly.run(tmp_path, lambda _: None, apply=True)
    assert manual.read(tmp_path / 'weekly-summary.json')['status'] == 'stopped'
    assert manual.read(tmp_path / 'candidate.json')['matches'] == {}


def test_rate_limit_is_remembered_and_blocks_further_provider_calls(tmp_path, monkeypatch):
    retry_at = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

    def blocked(*args, **kwargs):
        raise manual.r.ProviderBlocked(429, retry_at)

    monkeypatch.setattr(manual, 'collect', blocked)
    monkeypatch.setattr(manual, 'publish', lambda *a, **k: pytest.fail('blocked publication'))
    with pytest.raises(manual.r.ProviderBlocked):
        weekly.run(tmp_path, lambda _: None, apply=True)
    receipt = manual.read(tmp_path / 'weekly-summary.json')
    assert receipt['status'] == 'blocked' and receipt['retry_at'] == retry_at
    monkeypatch.setattr(manual, 'collect', lambda *a, **k: pytest.fail('cooldown ignored'))
    with pytest.raises(manual.r.ProviderBlocked) as failure:
        weekly.run(tmp_path, lambda _: pytest.fail('provider called'))
    assert failure.value.status == 429 and failure.value.retry_at == retry_at


def test_wrong_checkpoint_scope_stops_before_collection(tmp_path, monkeypatch):
    state = candidate([event()])
    state['season_id'] = 71131
    manual.save(tmp_path / 'candidate.json', state)
    monkeypatch.setattr(manual, 'collect', lambda *a, **k: pytest.fail('foreign checkpoint'))
    with pytest.raises(ValueError, match='scope'):
        weekly.run(tmp_path, lambda _: None)


def test_publication_failure_never_records_success(tmp_path, monkeypatch):
    pipeline(monkeypatch)
    monkeypatch.setattr(manual, 'publish', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('database')))
    with pytest.raises(RuntimeError):
        weekly.run(tmp_path, lambda _: None, apply=True)
    receipt = manual.read(tmp_path / 'weekly-summary.json')
    assert receipt['status'] == 'stopped' and receipt['applied'] is False


def test_complete_but_invalid_checkpoint_is_not_implicitly_replaced(tmp_path, monkeypatch, fake_players):
    state = candidate([event()])
    state['matches']['1']['checksum'] = 'incorrect'
    manual.save(tmp_path / 'candidate.json', state)
    with pytest.raises(ValueError, match='mismatch'):
        weekly.run(tmp_path, lambda _: pytest.fail('invalid checkpoint discarded'))
