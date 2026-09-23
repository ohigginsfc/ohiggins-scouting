"""Manual Chile 2026 collection; no database imports until explicit publication."""
from __future__ import annotations

import gzip
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from scouting import sofascore_recovery as r

SCOPE = dict(country='cl', division='primera', season='2026', competition=r.COMPETITION)
SEASON_ID = 88493


def save(path, value):
    r.atomic_write(path, r.canonical(value))


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def validate_event(event):
    r.validate_event(event, {'season_id': SEASON_ID})
    if event.get('status', {}).get('type') != 'finished':
        raise ValueError('Only finished events can be published')


def validate(state):
    if state.get('season_id') != SEASON_ID or state.get('version') != 1:
        raise ValueError('Wrong candidate scope/version')
    if not state.get('calendar_complete') or not state.get('events'):
        raise ValueError('Incomplete calendar')
    if set(state['events']) != set(state['matches']):
        raise ValueError('Incomplete season; publication refused')
    raw = {}
    for eid, event in state['events'].items():
        validate_event(event)
        if str(event['id']) != eid:
            raise ValueError('Event identity mismatch')
        match = state['matches'][eid]
        if match['checksum'] != r.scraper.compute_event_checksum(event):
            raise ValueError('Calendar/lineup mismatch')
        r.validate_players(event, match['players'])
        r.scraper.append_entries_to_checkpoint(raw, match['players'])
    return pd.DataFrame(r.scraper.aggregate(raw, {}))


class Http:
    def __init__(self, budget=1200):
        from curl_cffi import requests
        self.session = requests.Session(impersonate='chrome131')
        self.budget, self.count, self.last = budget, 0, 0.0

    def fetch(self, url, **kwargs):
        # Optional player biography/statistics fallback is deliberately omitted.
        if '/player/' in url:
            return None
        if self.count >= self.budget:
            raise RuntimeError('Request budget exhausted; resume the same checkpoint')
        time.sleep(max(0, 5 - (time.monotonic() - self.last)))
        self.last = time.monotonic()
        self.count += 1
        response = self.session.get(url, headers=r.scraper._http_headers(), timeout=30)
        if response.status_code != 200:
            raise RuntimeError(f'Provider HTTP {response.status_code}; stop and diagnose before resuming')
        value = response.json()
        if not isinstance(value, dict) or 'error' in value:
            raise ValueError('Invalid provider response')
        return value

    def close(self):
        self.session.close()


def collect(folder, fetch, *, resume=False, lookback_days=14):
    folder = Path(folder)
    path = folder / 'candidate.json'
    if resume:
        state = read(path)
        if state.get('version') != 1 or state.get('season_id') != SEASON_ID:
            raise ValueError('Wrong checkpoint scope/version')
    else:
        previous = read(path) if path.exists() else {'matches': {}}
        if path.exists():
            validate(previous)  # Never discard an unfinished run implicitly.
            save(folder / 'history' / (r.digest(previous) + '.json'), previous)
        state = dict(version=1, season_id=SEASON_ID, cutoff=r.now(),
                     lookback_days=lookback_days, calendar_complete=False,
                     events={}, matches={}, cache=previous['matches'], page=0)
        save(path, state)
    cutoff = datetime.fromisoformat(state['cutoff'])
    while not state['calendar_complete']:
        page = state['page']
        if page >= 30:
            raise ValueError('Calendar pagination budget exceeded')
        data = fetch(r.scraper.BASE_URL + f'/unique-tournament/11653/season/{SEASON_ID}/events/last/{page}')
        if not isinstance(data.get('events'), list) or type(data.get('hasNextPage')) is not bool:
            raise ValueError('Invalid calendar page')
        for event in data['events']:
            r.validate_event(event, state)
            if event.get('status', {}).get('type') == 'finished' and event['startTimestamp'] <= cutoff.timestamp():
                state['events'][str(event['id'])] = event
        state['page'] += 1
        state['calendar_complete'] = not data['hasNextPage']
        save(path, state)
    for eid, event in sorted(state['events'].items(), key=lambda item: int(item[0])):
        if eid in state['matches']:
            continue
        old = state.get('cache', {}).get(eid)
        checksum = r.scraper.compute_event_checksum(event)
        recent = event['startTimestamp'] >= (cutoff - timedelta(days=state['lookback_days'])).timestamp()
        if old and old['checksum'] == checksum and not recent:
            r.validate_players(event, old['players'])
            state['matches'][eid] = old
        else:
            entries, _ = r.scraper.process_finished_event(
                None, event, delay_lineup=0, delay_fallback=0, delay_incidents=0, fetcher=fetch)
            r.validate_players(event, entries)
            state['matches'][eid] = dict(checksum=checksum, players=entries)
        save(path, state)
        print(f"2026: {len(state['matches'])}/{len(state['events'])}", flush=True)
    frame = validate(state)
    state.pop('cache', None)
    save(path, state)
    return state, frame


def bootstrap(source, folder):
    """Adopt the already downloaded raw season after checking every manifest hash."""
    source, folder = Path(source), Path(folder)
    if (folder / 'candidate.json').exists():
        raise ValueError('Destination already has a checkpoint')
    manifest = read(source / 'sha256.json')
    import hashlib
    for name, expected in manifest.items():
        path = (source / name).resolve()
        if not path.is_relative_to(source.resolve()):
            raise ValueError('Unsafe manifest path')
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Raw checkpoint checksum mismatch')
    events = read(source / 'events.json')
    required = {'events.json'} | {f'matches/{eid}/{name}.json' for eid in events for name in ('lineups', 'incidents')}
    if not required <= set(manifest):
        raise ValueError('Unverified raw files')
    state = dict(version=1, season_id=SEASON_ID, cutoff=r.now(), calendar_complete=True,
                 events=events, matches={})
    for eid, event in events.items():
        validate_event(event)
        def fetch(url, **kwargs):
            if '/player/' in url:
                return None
            suffix = url.split('/event/', 1)[1]
            if suffix not in (f'{eid}/lineups', f'{eid}/incidents'):
                raise ValueError('Unexpected endpoint')
            return read(source / 'matches' / (suffix + '.json'))
        entries, _ = r.scraper.process_finished_event(None, event, delay_lineup=0,
            delay_fallback=0, delay_incidents=0, fetcher=fetch)
        state['matches'][eid] = dict(checksum=r.scraper.compute_event_checksum(event), players=entries)
    validate(state)
    # Bootstrap is cache only: a fresh calendar must be collected before publishing.
    state['bootstrap_only'] = True
    save(folder / 'candidate.json', state)
    return len(events)


def guard_existing(conn, state):
    rows = conn.execute("""SELECT event_id FROM sofascore_event_ingestion
        WHERE country='cl' AND division='primera' AND competition=%s AND season=2026
        AND processing_status='processed'""", (r.COMPETITION,)).fetchall()
    if not {str(row[0]) for row in rows} <= set(state['events']):
        raise ValueError('Candidate omits already published events')
    latest = conn.execute("""SELECT max(scraped_at) FROM sofascore_event_ingestion
        WHERE country='cl' AND division='primera' AND competition=%s AND season=2026
        AND processing_status='processed'""", (r.COMPETITION,)).fetchone()[0]
    # The existing migration stores scraped_at as timestamp without time zone.
    if latest and latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)
    if latest and latest > datetime.fromisoformat(state['cutoff']):
        raise ValueError('A newer publication exists; collect again')


def publish(folder, *, apply=False):
    import os
    from psycopg import sql
    from scouting.db import get_connection
    from scouting.ingestion.import_sofascore_player_stats_csv import import_dataframe
    from scouting.repositories.sofascore_event_ingestion_repository import upsert_event
    if os.environ.get('DB_SCHEMA') != 'scouting' or not os.environ.get('SCOUTING_DATABASE_URL'):
        raise ValueError('Explicit SCOUTING_DATABASE_URL and DB_SCHEMA=scouting required')
    folder = Path(folder)
    state = read(folder / 'candidate.json')
    if state.get('bootstrap_only'):
        raise ValueError('Collect a fresh calendar after bootstrap')
    frame = validate(state)
    digest = r.digest(state)
    with get_connection() as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        guard_existing(conn, state)
        if not apply:
            return dict(dry_run=True, matches=len(state['events']), players=len(frame))
        # Portable data-only logical snapshot; no credentials, kept on private disk.
        schema = conn.execute('SELECT current_schema()').fetchone()[0]
        tables = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname=%s ORDER BY tablename", (schema,)).fetchall()
        backup = {'schema': schema, 'created_at': r.now(), 'tables': {}}
        for (table,) in tables:
            cur = conn.execute(sql.SQL('SELECT * FROM {}').format(sql.Identifier(schema, table)))
            backup['tables'][table] = dict(columns=[c.name for c in cur.description], rows=cur.fetchall())
        backup_path = folder / 'backups' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.json.gz')
        r.atomic_write(backup_path, gzip.compress(json.dumps(backup, default=str).encode()))
    def hook(conn, batch_id):
        # Recheck under importer's scope advisory lock, before transaction commit.
        guard_existing(conn, state)
        for eid, event in state['events'].items():
            upsert_event(conn, **{**SCOPE, 'season': 2026}, event_id=int(eid),
                home_team=event['homeTeam']['name'], away_team=event['awayTeam']['name'],
                event_date=r.scraper.event_datetime_utc(event), status='finished', has_lineups=True,
                checksum=state['matches'][eid]['checksum'], processing_status='processed',
                scraped_at=datetime.fromisoformat(state['cutoff']).astimezone(timezone.utc).replace(tzinfo=None),
                import_batch_id=batch_id, commit=False)
    with get_connection() as conn:
        batch, stats = import_dataframe(conn, frame, **SCOPE, source_file='manual-sync:'+digest,
                                       replace=True, publication_hook=hook)
    result = dict(batch_id=str(batch), metrics=stats['metrics_inserted'], matches=len(state['events']), backup=str(backup_path))
    save(folder / 'publication.json', result)
    return result
