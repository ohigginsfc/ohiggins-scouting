"""Regional jobs keep the same scope validation, checkpoints and provider mutex."""
from datetime import datetime, timezone

import pytest

from scouting import manual_sync as manual, sync_scheduler
from scouting.sofascore_leagues import DEFAULT_LEAGUE, LEAGUES
from tests.test_manual_sync import candidate, event, fake_players  # noqa: F401


REGIONAL = [
    ('ar_primera', 'ar', 'primera', 155, 87913, 8),
    ('ar_primera_nacional', 'ar', 'primera_nacional', 703, 87940, 9),
    ('uy_primera', 'uy', 'primera', 278, 89288, 10),
]


@pytest.mark.parametrize('key,country,division,tid,sid,hour', REGIONAL)
def test_regional_collector_validates_source_and_rejects_foreign_checkpoints(
        tmp_path, fake_players, key, country, division, tid, sid, hour):
    league = LEAGUES[key]
    assert (league.country, league.division, league.tournament_id, league.season_id) == (country, division, tid, sid)
    assert league.season == '2026' and not league.allow_name_match
    ev = event()
    ev['season']['id'] = sid
    ev['tournament']['uniqueTournament']['id'] = tid
    urls = []
    def fetch(url):
        urls.append(url)
        return {'events': [ev], 'hasNextPage': False}
    state, frame = manual.collect(tmp_path / key, fetch, league=league)
    assert not frame.empty and state['scope'] == league.scope and state['league_key'] == key
    assert urls == [manual.r.scraper.BASE_URL + f'/unique-tournament/{tid}/season/{sid}/events/last/0']
    with pytest.raises(ValueError):
        manual.validate(state)  # cannot enter Chile's publication scope
    with pytest.raises(ValueError):
        manual.validate(candidate([event()]), league=league)
    assert sync_scheduler.next_run(datetime(2026,11,23,12,tzinfo=timezone.utc), league=league).hour == hour
    command = sync_scheduler.worker_command(league.folder, league=league)
    assert command[4] == sync_scheduler.worker_command(DEFAULT_LEAGUE.folder)[4]


def test_regional_jobs_have_separate_folders_and_reject_foreign_scheduler_states(tmp_path):
    assert len({league.folder for league in LEAGUES.values()}) == len(LEAGUES)
    assert len({league.schedule_hour for league in LEAGUES.values()}) == len(LEAGUES)
    now = datetime(2026,11,23,12,tzinfo=timezone.utc)
    for key,*_ in REGIONAL:
        league = LEAGUES[key]
        state = sync_scheduler.tick(tmp_path / key, now, lambda: pytest.fail('early download'), league=league)
        assert state['league_key'] == key
        with pytest.raises(ValueError, match='scope'):
            sync_scheduler.tick(tmp_path / key, now, lambda: None)


def test_uruguay_without_player_statistics_is_not_published_as_zero():
    # This can occur even though the provider calendar and lineups return HTTP 200.
    league = LEAGUES['uy_primera']
    ev = event()
    ev['season']['id'] = league.season_id
    ev['tournament']['uniqueTournament']['id'] = league.tournament_id
    state = candidate([ev])
    state.update(league_key=league.key, tournament_id=league.tournament_id, season_id=league.season_id, scope=league.scope)
    state['matches']['1'] = dict(checksum=manual.r.scraper.compute_event_checksum(ev), players=[
        dict(player={'id':pid}, team={'id':1 if pid <= 11 else 2},
             event_id=1, substitute=False, statistics={}) for pid in range(1,23)])
    with pytest.raises(ValueError, match='statistics'):
        manual.validate(state, league=league)
