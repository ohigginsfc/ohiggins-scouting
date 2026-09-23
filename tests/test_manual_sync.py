from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from scouting import manual_sync as m


def event(eid=1, timestamp=1700000000):
    return dict(id=eid, season={'id': 88493}, tournament={'uniqueTournament': {'id': 11653}},
                status={'type': 'finished'}, startTimestamp=timestamp,
                homeTeam={'id': 1, 'name': 'Home'}, awayTeam={'id': 2, 'name': 'Away'})


@pytest.fixture
def fake_players(monkeypatch):
    monkeypatch.setattr(m.r, 'validate_players', lambda e, p: None)
    monkeypatch.setattr(m.r.scraper, 'compute_event_checksum', lambda e: str(e['id']))
    monkeypatch.setattr(m.r.scraper, 'append_entries_to_checkpoint', lambda raw, entries: raw.update({'x': entries}))
    monkeypatch.setattr(m.r.scraper, 'aggregate', lambda raw, teams: [{'player_id': 1}])
    monkeypatch.setattr(m.r.scraper, 'process_finished_event', lambda *a, **k: ([{'player': 1}], {}))


def candidate(events):
    return dict(version=1, season_id=88493, cutoff=m.r.now(), calendar_complete=True,
                events={str(e['id']): e for e in events},
                matches={str(e['id']): {'checksum': str(e['id']), 'players': []} for e in events})


def test_incomplete_and_foreign_candidate_rejected(fake_players):
    s=candidate([event()]);s['matches']={}
    with pytest.raises(ValueError,match='Incomplete season'):m.validate(s)
    s=candidate([event()]);s['events']['1']['season']['id']=71131
    with pytest.raises(ValueError,match='different season'):m.validate(s)


def test_cached_old_match_kept_recent_match_refetched(tmp_path,fake_players,monkeypatch):
    recent=event(2,int(datetime.now(timezone.utc).timestamp())-100)
    m.save(tmp_path/'candidate.json',candidate([event(),recent]))
    calls=[]
    monkeypatch.setattr(m.r.scraper,'process_finished_event',lambda driver,e,**kw:(calls.append(e['id']) or [],{}))
    state,_=m.collect(tmp_path,lambda url:{'events':[event(),recent],'hasNextPage':False})
    assert calls==[2]
    assert set(state['matches'])=={'1','2'}


def test_failed_download_checkpoint_resumes_without_losing_completed(tmp_path,fake_players,monkeypatch):
    def process(driver,e,**kw):
        if e['id']==2:raise RuntimeError('HTTP 403')
        return [],{}
    monkeypatch.setattr(m.r.scraper,'process_finished_event',process)
    fetch=lambda url:{'events':[event(),event(2)],'hasNextPage':False}
    with pytest.raises(RuntimeError):m.collect(tmp_path,fetch)
    assert set(m.read(tmp_path/'candidate.json')['matches'])=={'1'}
    with pytest.raises(ValueError):m.collect(tmp_path,fetch)
    calls=[]
    monkeypatch.setattr(m.r.scraper,'process_finished_event',lambda driver,e,**kw:(calls.append(e['id']) or [],{}))
    state,_=m.collect(tmp_path,lambda url:pytest.fail('Calendar should be cached'),resume=True)
    assert calls==[2] and len(state['matches'])==2


def test_guard_rejects_loss_of_published_matches():
    conn=MagicMock();conn.execute.return_value.fetchall.return_value=[(1,),(2,)]
    with pytest.raises(ValueError,match='omits'):m.guard_existing(conn,candidate([event()]))


def test_guard_rejects_older_candidate():
    conn=MagicMock();conn.execute.return_value.fetchall.return_value=[(1,)]
    conn.execute.return_value.fetchone.return_value=(datetime(2099,1,1,tzinfo=timezone.utc),)
    with pytest.raises(ValueError,match='newer'):m.guard_existing(conn,candidate([event()]))
