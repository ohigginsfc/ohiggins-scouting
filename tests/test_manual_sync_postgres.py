"""Publication uses only the disposable PostgreSQL fixture, never production."""
import gzip
import json
import pytest
from tests.test_atomic_sofascore_import import db, frame, snapshot
from tests.test_manual_sync import candidate, event
from scouting import manual_sync as m


def setup_candidate(tmp_path, monkeypatch, db):
    from scouting import db as database
    monkeypatch.setenv('DB_SCHEMA','scouting')
    monkeypatch.setenv('SCOUTING_DATABASE_URL','postgresql://unused/test')
    monkeypatch.setattr(database,'get_connection',db)
    monkeypatch.setattr(m,'validate',lambda state:frame())
    m.save(tmp_path/'candidate.json',candidate([event()]))


def test_manual_publication_metrics_and_events_commit_together(db,tmp_path,monkeypatch):
    setup_candidate(tmp_path,monkeypatch,db)
    before=snapshot(db)
    assert m.publish(tmp_path)['dry_run'] is True
    assert snapshot(db)==before
    result=m.publish(tmp_path,apply=True)
    with db() as conn:
        assert conn.execute('SELECT count(*) FROM objective_metrics').fetchone()[0]>0
        assert str(conn.execute("SELECT import_batch_id FROM sofascore_event_ingestion WHERE processing_status='processed'").fetchone()[0])==result['batch_id']
    backup=json.loads(gzip.decompress(__import__('pathlib').Path(result['backup']).read_bytes()))
    assert 'objective_metrics' in backup['tables']


def test_manual_event_failure_rolls_back_metrics(db,tmp_path,monkeypatch):
    from scouting.repositories import sofascore_event_ingestion_repository as repo
    setup_candidate(tmp_path,monkeypatch,db)
    m.publish(tmp_path,apply=True)
    before=snapshot(db)
    def fail(*args,**kwargs):raise RuntimeError('event write failed')
    monkeypatch.setattr(repo,'upsert_event',fail)
    with pytest.raises(RuntimeError,match='event write failed'):m.publish(tmp_path,apply=True)
    assert snapshot(db)==before
