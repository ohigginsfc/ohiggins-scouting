from tests.test_atomic_sofascore_import import db, publish
from scouting.repositories.sofascore_event_ingestion_repository import list_incomplete_coverage, upsert_event


def test_only_published_finished_scopes_with_gaps_are_reported(db):
    batch_id,_=publish(db)
    with db() as conn:
        for eid,status,processed in [(1,'finished',True),(2,'finished',False),(3,'notstarted',False)]:
            upsert_event(conn,country='cl',division='primera',competition='Synthetic League',
                         season=2026,event_id=eid,status=status,
                         processing_status='processed' if processed else 'failed',
                         import_batch_id=batch_id if processed else None)
        assert list_incomplete_coverage(conn)==[{'competition':'Synthetic League','season':2026,'expected':2,'processed':1}]
        upsert_event(conn,country='cl',division='primera',competition='Synthetic League',
                     season=2026,event_id=2,status='finished',processing_status='processed',import_batch_id=batch_id)
        assert list_incomplete_coverage(conn)==[]
