"""Small, read-only physical storage snapshots; never export row payloads or credentials."""
from datetime import datetime, timezone

from psycopg.rows import dict_row


def measure(conn):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute('SET TRANSACTION READ ONLY')
        cur.execute('SELECT pg_database_size(current_database()) AS bytes')
        database_bytes = cur.fetchone()['bytes']
        cur.execute("""SELECT c.relname AS table_name, pg_total_relation_size(c.oid) AS total_bytes,
                              pg_table_size(c.oid) AS table_bytes, pg_indexes_size(c.oid) AS index_bytes
                       FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                       WHERE n.nspname=current_schema() AND c.relkind='r'
                       ORDER BY pg_total_relation_size(c.oid) DESC""")
        tables = cur.fetchall()
        cur.execute("""SELECT b.country,b.division,om.competition,om.season,count(*) AS metrics,
                              count(DISTINCT om.player_id) AS players
                       FROM objective_metrics om JOIN data_import_batches b ON b.id=om.import_batch_id
                       WHERE om.source_type='sofascore' AND b.status='completed'
                       GROUP BY b.country,b.division,om.competition,om.season
                       ORDER BY b.country,b.division,om.competition,om.season""")
        scopes = cur.fetchall()
    return dict(recorded_at=datetime.now(timezone.utc).isoformat(), database_bytes=database_bytes,
                schema_bytes=sum(t['total_bytes'] for t in tables), tables=tables, scopes=scopes)


def compare(before, after):
    old = int(before['database_bytes'])
    delta = int(after['database_bytes']) - old
    old_tables = {t['table_name']: t['total_bytes'] for t in before['tables']}
    new_tables = {t['table_name']: t['total_bytes'] for t in after['tables']}
    return dict(database_delta_bytes=delta,
                database_growth_percent=round(delta / old * 100, 4) if old else None,
                schema_delta_bytes=int(after['schema_bytes']) - int(before['schema_bytes']),
                table_delta_bytes={name: new_tables.get(name, 0) - old_tables.get(name, 0)
                                   for name in sorted(old_tables.keys() | new_tables.keys())})
