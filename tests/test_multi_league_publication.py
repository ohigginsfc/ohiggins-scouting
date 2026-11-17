"""Real PostgreSQL transactions in a disposable schema, never cloud data."""
import pytest

from scouting import manual_sync as manual
from scouting.sofascore_leagues import DEFAULT_LEAGUE, LEAGUES
from tests.test_atomic_sofascore_import import db, frame, snapshot  # noqa: F401
from tests.test_manual_sync import candidate, event
from tests.test_sofascore_league_scopes import b_candidate

B = LEAGUES['cl_primera_b']


def setup(db, monkeypatch, tmp_path):
    from scouting import db as database
    monkeypatch.setenv('DB_SCHEMA', 'scouting')
    monkeypatch.setenv('SCOUTING_DATABASE_URL', 'postgresql://unused/test')
    monkeypatch.setattr(database, 'get_connection', db)
    monkeypatch.setattr(manual, 'validate', lambda state, **kw: frame(
        1 if state['season_id'] == DEFAULT_LEAGUE.season_id else 2))
    first, second = tmp_path / 'primera', tmp_path / 'primera-b'
    manual.save(first / 'candidate.json', candidate([event()]))
    manual.save(second / 'candidate.json', b_candidate())
    manual.publish(first, apply=True)
    with db() as conn:
        pid = conn.execute('SELECT min(id) FROM players').fetchone()[0]
        conn.execute("INSERT INTO scouting_reports(player_id,source_type,summary) VALUES(%s,'manual','Synthetic private report')", (pid,))
    return second


def records(db):
    with db() as conn:
        return (conn.execute('SELECT * FROM objective_metrics WHERE competition=%s ORDER BY id',
                             (DEFAULT_LEAGUE.competition,)).fetchall(),
                conn.execute('SELECT * FROM scouting_reports ORDER BY id').fetchall())


def test_adding_and_replacing_primera_b_preserves_primera_and_reports(db, monkeypatch, tmp_path):
    folder = setup(db, monkeypatch, tmp_path)
    protected = records(db)
    before = snapshot(db)
    assert manual.publish(folder, league=B)['dry_run'] is True
    assert snapshot(db) == before
    manual.publish(folder, league=B, apply=True)
    assert records(db) == protected
    with db() as conn:
        assert conn.execute('SELECT count(*) FROM objective_metrics WHERE competition=%s', (B.competition,)).fetchone()[0] > 0
        assert conn.execute('SELECT count(*) FROM sofascore_event_ingestion WHERE division=%s', ('primera_b',)).fetchone()[0] == 1
    manual.publish(folder, league=B, apply=True)
    assert records(db) == protected
    with db() as conn:
        assert conn.execute("SELECT count(*) FROM data_import_batches WHERE division='primera_b' AND status='completed'").fetchone()[0] == 1


def test_failed_primera_b_publication_rolls_back_both_leagues_and_reports(db, monkeypatch, tmp_path):
    from scouting.repositories import sofascore_event_ingestion_repository as repo
    folder = setup(db, monkeypatch, tmp_path)
    manual.publish(folder, league=B, apply=True)
    protected, before = records(db), snapshot(db)

    def fail(*args, **kwargs):
        raise RuntimeError('synthetic event failure')

    monkeypatch.setattr(repo, 'upsert_event', fail)
    with pytest.raises(RuntimeError, match='synthetic event failure'):
        manual.publish(folder, league=B, apply=True)
    assert records(db) == protected and snapshot(db) == before


def test_new_provider_identity_with_the_same_name_does_not_take_over_existing_reports(db, monkeypatch, tmp_path):
    folder = setup(db, monkeypatch, tmp_path)
    protected = records(db)
    monkeypatch.setattr(manual, 'validate', lambda state, **kw: frame(2).assign(player_name='Synthetic Player 1'))
    manual.publish(folder, league=B, apply=True)
    with db() as conn:
        links = dict(conn.execute("SELECT external_id,player_id FROM player_external_ids WHERE provider='sofascore'").fetchall())
        assert links['1'] != links['2'], 'different provider IDs must not be merged by name'
        assert conn.execute('SELECT player_id FROM scouting_reports').fetchone()[0] == links['1']
        assert conn.execute('SELECT full_name FROM players WHERE id=%s', (links['2'],)).fetchone()[0] == 'Synthetic Player 1'
    manual.publish(folder, league=B, apply=True)
    assert records(db) == protected
    with db() as conn:
        assert conn.execute('SELECT count(*) FROM players').fetchone()[0] == 2


def test_legacy_name_matching_cannot_merge_two_distinct_provider_ids(db):
    from scouting.ingestion import import_sofascore_player_stats_csv as importer
    args = dict(country='cl', division='primera', season='2026', competition='Synthetic league', source_file='synthetic')
    with db() as conn:
        importer.import_dataframe(conn, frame(1), **args)
    with db() as conn:
        importer.import_dataframe(conn, frame(2).assign(player_name='Synthetic Player 1'), **args)
    with db() as conn:
        links = dict(conn.execute("SELECT external_id,player_id FROM player_external_ids WHERE provider='sofascore'").fetchall())
        assert links['1'] != links['2']
