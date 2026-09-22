"""Real PostgreSQL tests; use only a disposable local database named scouting_test.

SCOUTING_TEST_DATABASE_URL must be explicitly configured. No production DB_* used.
Each test applies the actual schema/migrations in its own temporary schema.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
import sys
import threading
import time
from uuid import uuid4

import pandas as pd
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from scouting.ingestion import import_sofascore_player_stats_csv as importer


@pytest.fixture
def db():
    dsn = os.getenv("SCOUTING_TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("Requires disposable local PostgreSQL via SCOUTING_TEST_DATABASE_URL")
    params = conninfo_to_dict(dsn)
    assert params.get("host") in {"localhost", "127.0.0.1", "::1"}
    assert params.get("dbname") == "scouting_test"
    schema = "atomic_test_" + uuid4().hex
    with psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    def connect(*, autocommit=False):
        return psycopg.connect(dsn, options=f"-c search_path={schema}", autocommit=autocommit, application_name=schema)
    try:
        with connect() as conn:
            conn.execute((ROOT / "db/init.sql").read_text(encoding="utf-8"))
            for path in sorted((ROOT / "db/migrations").glob("*.sql")):
                conn.execute(path.read_text(encoding="utf-8"))
        yield connect
    finally:
        with psycopg.connect(dsn, autocommit=True) as admin:
            admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def frame(player_id=1, **extra):
    return pd.DataFrame([dict(player_id=player_id, player_name=f"Synthetic Player {player_id}",
                              minutesPlayed=900, goals=5, **extra)])


def publish(db, data=None, **scope):
    args = dict(country="cl", division="primera", season="2026", competition="Synthetic League",
                source_file="synthetic.csv", replace=True)
    args.update(scope)
    with db() as conn:
        return importer.import_dataframe(conn, frame() if data is None else data, **args)


def snapshot(db):
    with db(autocommit=True) as conn:
        return {
            table: conn.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
            for table in ("players", "player_external_ids", "objective_metrics")
        }


def assert_failed(db, old_id, before):
    assert snapshot(db) == before
    with db(autocommit=True) as conn:
        assert conn.execute("SELECT status FROM data_import_batches WHERE id=%s", (old_id,)).fetchone()[0] == "completed"
        status, stats = conn.execute("SELECT status,stats FROM data_import_batches WHERE id<>%s", (old_id,)).fetchone()
        assert status == "failed"
        assert stats["metrics_inserted"] == 0
        assert stats["rolled_back"] is True


def test_row_error_rolls_back_players_profiles_links_and_flushed_metrics(db):
    old_id, _ = publish(db)
    before = snapshot(db)
    # Existing profile change, new players and >500 inserted metrics before failure.
    data = pd.concat([frame(1, country="Synthetic"), *[frame(i) for i in range(2, 520)],
                      pd.DataFrame([{"player_id": None, "player_name": "Invalid"}])], ignore_index=True)
    with pytest.raises(ValueError, match="Import aborted"):
        publish(db, data)
    assert_failed(db, old_id, before)
    with db(autocommit=True) as conn:
        stats = conn.execute("SELECT stats FROM data_import_batches WHERE status='failed'").fetchone()[0]
        assert stats["metrics_attempted"] >= 500


@pytest.mark.parametrize("after_completion", [False, True])
def test_failure_at_promotion_keeps_old_version_visible(db, monkeypatch, after_completion):
    old_id, _ = publish(db)
    before = snapshot(db)
    original = importer.import_batches_repository.complete_import_batch
    def fail(conn, batch_id, stats, **kwargs):
        # Old metrics have been deleted inside the writer, but an independent
        # reader must still see the original complete dataset.
        assert snapshot(db) == before
        if after_completion:
            original(conn, batch_id, stats, **kwargs)
        raise RuntimeError("injected before commit")
    monkeypatch.setattr(importer.import_batches_repository, "complete_import_batch", fail)
    with pytest.raises(RuntimeError, match="injected"):
        publish(db, frame(2))
    assert_failed(db, old_id, before)


def test_real_sql_error_rolls_back(db, monkeypatch):
    old_id, _ = publish(db)
    before = snapshot(db)
    original = importer.metrics_repository.create_metrics_batch
    def invalid(conn, rows, **kwargs):
        rows[0]["metric_value"] = "not-a-number"
        return original(conn, rows, **kwargs)
    monkeypatch.setattr(importer.metrics_repository, "create_metrics_batch", invalid)
    with pytest.raises(psycopg.Error):
        publish(db, frame(2))
    assert_failed(db, old_id, before)


def test_successful_retry_replaces_only_exact_scope_and_keeps_demo(db):
    old_id, _ = publish(db)
    other_id, _ = publish(db, frame(2), competition="Another League")
    country_id, _ = publish(db, frame(3), country="ar")
    with db() as conn:
        conn.execute("""INSERT INTO objective_metrics(player_id,source_name,season,competition,metric_name,metric_value,source_type)
                        SELECT id,'Sofascore','2026','Synthetic League','demo',1,'demo' FROM players LIMIT 1""")
    for _ in range(2):
        new_id, stats = publish(db, frame(4))
        with db(autocommit=True) as conn:
            assert conn.execute("SELECT status FROM data_import_batches WHERE id=%s", (old_id,)).fetchone()[0] == "replaced"
            assert conn.execute("SELECT count(*) FROM objective_metrics WHERE import_batch_id=%s", (old_id,)).fetchone()[0] == 0
            assert conn.execute("SELECT count(*) FROM objective_metrics WHERE import_batch_id=%s", (new_id,)).fetchone()[0] == stats["metrics_inserted"]
            assert conn.execute("SELECT count(*) FROM objective_metrics WHERE source_type='demo'").fetchone()[0] == 1
            for preserved in [other_id, country_id]:
                assert conn.execute("SELECT status FROM data_import_batches WHERE id=%s", (preserved,)).fetchone()[0] == "completed"
                assert conn.execute("SELECT count(*) FROM objective_metrics WHERE import_batch_id=%s", (preserved,)).fetchone()[0] > 0
            assert conn.execute("""SELECT count(*) FROM data_import_batches WHERE country='cl'
                                   AND competition='Synthetic League' AND status='completed'""").fetchone()[0] == 1


def test_empty_input_keeps_previous_version(db):
    old_id, _ = publish(db)
    before = snapshot(db)
    with pytest.raises(ValueError, match="Empty CSV"):
        publish(db, pd.DataFrame())
    assert snapshot(db) == before
    with db(autocommit=True) as conn:
        assert conn.execute("SELECT count(*) FROM data_import_batches").fetchone()[0] == 1


def test_metricless_row_rejects_whole_candidate(db):
    old_id, _ = publish(db)
    before = snapshot(db)
    with pytest.raises(ValueError, match="Import aborted"):
        publish(db, pd.DataFrame([{"player_id": 2, "player_name": "No Metrics"}]))
    assert_failed(db, old_id, before)


def test_concurrent_same_scope_imports_do_not_publish_two_versions(db, monkeypatch):
    publish(db)
    arrived = threading.Event()
    release = threading.Event()
    original = importer.import_batches_repository.complete_import_batch
    def hold(conn, batch_id, stats, **kwargs):
        if not arrived.is_set():
            arrived.set()
            assert release.wait(10)
        return original(conn, batch_id, stats, **kwargs)
    monkeypatch.setattr(importer.import_batches_repository, "complete_import_batch", hold)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(publish, db, frame(2))
        assert arrived.wait(10)
        second = pool.submit(publish, db, frame(3))
        deadline = time.monotonic() + 10
        waiting = False
        try:
            with db(autocommit=True) as observer:
                while time.monotonic() < deadline:
                    waiting = observer.execute(
                        """SELECT EXISTS (SELECT 1 FROM pg_locks l JOIN pg_stat_activity a ON a.pid=l.pid
                           WHERE l.locktype='advisory' AND NOT l.granted
                           AND a.application_name=current_setting('application_name'))"""
                    ).fetchone()[0]
                    if waiting:
                        break
                    time.sleep(0.02)
            assert waiting, "second publisher must wait for the first scope transaction"
        finally:
            release.set()
        first.result(timeout=15)
        second.result(timeout=15)
    with db(autocommit=True) as conn:
        assert conn.execute("SELECT count(*) FROM data_import_batches WHERE status='completed'").fetchone()[0] == 1
        assert conn.execute("SELECT count(DISTINCT import_batch_id) FROM objective_metrics").fetchone()[0] == 1


def test_unbatched_real_data_requires_reconciliation(db):
    publish(db)
    with db() as conn:
        conn.execute("UPDATE objective_metrics SET import_batch_id=NULL")
    before = snapshot(db)
    with pytest.raises(ValueError, match="reconciliation"):
        publish(db, frame(2))
    assert snapshot(db) == before


def test_rejects_callers_active_transaction_without_committing_it(db):
    with db() as conn:
        conn.execute("INSERT INTO players(full_name,normalized_name) VALUES ('Pending','pending')")
        with pytest.raises(ValueError, match="active transaction"):
            importer.import_dataframe(conn, frame(), country="cl", division="primera",
                                      season="2026", competition="Synthetic League", source_file="test.csv")
        with db(autocommit=True) as observer:
            assert observer.execute("SELECT count(*) FROM players").fetchone()[0] == 0
        conn.rollback()


def test_cli_invalid_csv_raises_instead_of_reporting_success(db, monkeypatch, tmp_path, capsys):
    old_id, _ = publish(db)
    before = snapshot(db)
    path = tmp_path / "candidate.csv"
    pd.DataFrame([{"player_id": None, "player_name": "Invalid"}]).to_csv(path, index=False)
    monkeypatch.setattr(importer, "get_connection", db)
    monkeypatch.setattr(sys, "argv", ["importer", str(path), "--country", "cl", "--division", "primera",
                                     "--season", "2026", "--competition", "Synthetic League", "--replace"])
    with pytest.raises(ValueError, match="Import aborted"):
        importer.main()
    assert "Metrics inserted:" not in capsys.readouterr().out
    assert_failed(db, old_id, before)
