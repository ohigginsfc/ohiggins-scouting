"""Database-free, bounded Sofascore collection and authenticated checkpoints.

Only explicit browser requests are used. This module never imports DB settings.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import pandas as pd
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web_scraping_sofascore'))
import sofascore_scraper as scraper

MAGIC = b'OHIGGINS-SOFA-1\n'
SEASONS = {'2024': 57883, '2025': 71131}
COMPETITION = 'Primera División Chile'


class InvalidPackage(ValueError):
    pass


class BudgetReached(RuntimeError):
    pass


class ProviderBlocked(RuntimeError):
    def __init__(self, status, retry_at=None):
        self.status, self.retry_at = status, retry_at
        super().__init__(f'Provider blocked: {status}')


def now():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def read_key():
    try:
        key = base64.b64decode(os.environ['SOFASCORE_ARTIFACT_KEY'], validate=True)
        if len(key) != 32:
            raise ValueError()
        return key
    except (KeyError, ValueError) as exc:
        raise InvalidPackage('SOFASCORE_ARTIFACT_KEY must encode 32 random bytes') from exc


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('wb') as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def encrypt_document(document, path, key):
    nonce = os.urandom(12)
    atomic_write(path, MAGIC + nonce + AESGCM(key).encrypt(nonce, canonical(document), MAGIC))


def decrypt_document(path, key):
    raw = Path(path).read_bytes()
    if not raw.startswith(MAGIC):
        raise InvalidPackage('Unsupported encrypted package')
    offset = len(MAGIC)
    try:
        return json.loads(AESGCM(key).decrypt(raw[offset:offset+12], raw[offset+12:], MAGIC))
    except Exception as exc:
        raise InvalidPackage('Package authentication failed or invalid JSON') from exc


def new_state(season):
    if season not in SEASONS:
        raise InvalidPackage('Only Chile 2024 and 2025 are supported')
    return dict(version=1, season=season, tournament_id=11653, season_id=SEASONS[season],
                created_at=now(), updated_at=now(), calendar_complete=False, page=0,
                events={}, matches={}, errors={}, status='partial', retry_at=None)


def validate_event(event, state):
    if type(event.get('id')) is not int or event['id'] <= 0:
        raise InvalidPackage('Invalid event ID')
    if event.get('season', {}).get('id') != state['season_id']:
        raise InvalidPackage('Event belongs to a different season')
    if event.get('tournament', {}).get('uniqueTournament', {}).get('id') != 11653:
        raise InvalidPackage('Event belongs to a different tournament')


def validate_players(event, entries):
    if not isinstance(entries, list) or not entries:
        raise InvalidPackage('Empty lineup')
    seen = set()
    teams = {event['homeTeam']['id']: 0, event['awayTeam']['id']: 0}
    for entry in entries:
        pid = entry.get('player', {}).get('id')
        if type(pid) is not int or pid <= 0 or pid in seen:
            raise InvalidPackage('Invalid or duplicate player')
        seen.add(pid)
        if entry.get('event_id') != event['id']:
            raise InvalidPackage('Untraceable lineup entry')
        team = entry.get('team', {}).get('id')
        if team not in teams:
            raise InvalidPackage('Unexpected team in lineup')
        stats = entry.get('statistics')
        if not isinstance(stats, dict):
            raise InvalidPackage('Invalid statistics')
        # Unused substitutes may have no statistics. Starters may not.
        if not entry.get('substitute', False) and not stats:
            raise InvalidPackage('Starter statistics unavailable')
        if stats:
            teams[team] += 1
    if any(count < 11 for count in teams.values()):
        raise InvalidPackage('Incomplete team statistics')


def expected_ids(state):
    return {eid for eid, event in state['events'].items() if scraper.is_event_finished(event)}


def validate_state(state, season):
    if state.get('version') != 1 or state.get('season') != season or state.get('season_id') != SEASONS[season] or state.get('tournament_id') != 11653:
        raise InvalidPackage('Checkpoint scope/version mismatch')
    if state.get('status') not in {'partial', 'blocked', 'invalid', 'validated'}:
        raise InvalidPackage('Invalid checkpoint status')
    if type(state.get('page')) is not int or not 0 <= state['page'] <= 100:
        raise InvalidPackage('Invalid calendar cursor')
    if type(state.get('calendar_complete')) is not bool:
        raise InvalidPackage('Invalid calendar completion flag')
    for eid, event in state['events'].items():
        validate_event(event, state)
        if str(event['id']) != eid:
            raise InvalidPackage('Calendar identity mismatch')
    for eid, match in state['matches'].items():
        if eid not in expected_ids(state):
            raise InvalidPackage('Match outside finished calendar')
        if match['event_checksum'] != scraper.compute_event_checksum(state['events'][eid]):
            raise InvalidPackage('Match/calendar checksum mismatch')
        validate_players(state['events'][eid], match['players'])


def complete(state):
    return bool(state['calendar_complete'] and expected_ids(state)
                and expected_ids(state) == set(state['matches']) and not state['errors'])


def derived_files(state):
    raw = {}
    for eid in sorted(state['matches'], key=int):
        scraper.append_entries_to_checkpoint(raw, state['matches'][eid]['players'])
    rows = scraper.aggregate(raw, {}) if raw else []
    # Do not fetch player biography endpoints during historical recovery.
    # Embedded metadata is retained; unavailable biography remains missing.
    csv = pd.DataFrame(rows).to_csv(index=False, lineterminator='\n') if rows else ''
    teams = {}
    for event in state['events'].values():
        for side in ('homeTeam', 'awayTeam'):
            team = scraper.normalize_team_dict(event[side])
            teams[str(team['id'])] = team
    return {'events.json': [state['events'][eid] for eid in sorted(state['events'], key=int)], 'teams.json': teams,
            'checkpoint_raw.json': {str(pid):entries for pid,entries in raw.items()}, 'player_stats.csv': csv}


def pack(state):
    state['updated_at'] = now()
    validate_state(state, state['season'])
    files = derived_files(state)
    manifest = dict(version=1, country='cl', division='primera', competition=COMPETITION,
                    season=state['season'], tournament_id=11653, season_id=state['season_id'],
                    status=state['status'], expected=len(expected_ids(state)),
                    completed=len(state['matches']), failed=len(state['errors']),
                    created_at=state['created_at'], updated_at=state['updated_at'],
                    commit=os.getenv('GITHUB_SHA', 'local'), run_id=os.getenv('GITHUB_RUN_ID', 'local'),
                    state_sha256=digest(state), hashes={name:digest(data) for name,data in files.items()})
    return {'manifest':manifest, 'state':state, 'files':files}


def unpack(document, season, *, require_complete=False):
    try:
        state, manifest, files = document['state'], document['manifest'], document['files']
        validate_state(state, season)
        if manifest['version'] != 1 or manifest['season'] != season or manifest['state_sha256'] != digest(state):
            raise InvalidPackage('Manifest mismatch')
        if manifest['status'] != state['status']:
            raise InvalidPackage('Status mismatch')
        expected_manifest = {'country':'cl', 'division':'primera', 'competition':COMPETITION,
                             'tournament_id':11653, 'season_id':SEASONS[season],
                             'expected':len(expected_ids(state)), 'completed':len(state['matches']),
                             'failed':len(state['errors'])}
        if any(manifest.get(key) != value for key,value in expected_manifest.items()):
            raise InvalidPackage('Manifest scope/coverage mismatch')
        if manifest['hashes'] != {name:digest(data) for name,data in files.items()}:
            raise InvalidPackage('File checksum mismatch')
        if files != derived_files(state):
            raise InvalidPackage('Derived data mismatch')
        if require_complete and (state.get('probe_only') or state['status'] != 'validated' or not complete(state)):
            raise InvalidPackage('Incomplete package: publication forbidden')
        return state
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidPackage(str(exc)) from exc


class BrowserTransport:
    """One browser, fixed origin, request budget and a global request interval."""
    def __init__(self, driver, *, max_requests=300, seconds=2700, clock=time.monotonic, sleep=time.sleep):
        self.driver, self.clock, self.sleep = driver, clock, sleep
        self.deadline = clock() + seconds
        self.max_requests, self.requests, self.last = max_requests, 0, None

    def _budget(self):
        if self.requests >= self.max_requests or self.clock() >= self.deadline:
            raise BudgetReached('Request/time budget reached')

    def fetch(self, url, **_ignored):
        if not url.startswith(scraper.BASE_URL + '/'):
            raise InvalidPackage('Unexpected provider origin')
        for attempt, backoff in enumerate((0, 30, 120)):
            if backoff:
                if self.clock() + backoff >= self.deadline:
                    raise BudgetReached('Retry exceeds time budget')
                self.sleep(backoff)
            self._budget()
            if self.last is not None:
                self.sleep(max(0, 5 - (self.clock() - self.last)))
            self._budget()
            self.last = self.clock()
            self.requests += 1
            try:
                result = self.driver.execute_async_script('''
                    const done=arguments[arguments.length-1];
                    fetch(arguments[0], {signal:AbortSignal.timeout(25000)})
                      .then(async r=>done({status:r.status,body:await r.text(),retry:r.headers.get('retry-after')}))
                      .catch(()=>done({status:0,body:''}));
                ''', url)
                status = result['status']
            except Exception:
                status, result = 0, {}
            if status in (401, 403, 429):
                retry_at = None
                if status == 429:
                    retry = result.get('retry')
                    try:
                        retry_at = (datetime.now(timezone.utc) + timedelta(seconds=max(0,int(retry)))).isoformat()
                    except (TypeError, ValueError):
                        try:
                            retry_at = parsedate_to_datetime(retry).isoformat()
                        except (TypeError, ValueError, AttributeError):
                            retry_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
                raise ProviderBlocked(status, retry_at)
            if status == 404 and scraper.is_expected_missing_player_stats(url, status):
                return None
            if status == 200:
                try:
                    payload = json.loads(result['body'])
                except (ValueError, KeyError) as exc:
                    raise InvalidPackage('Provider returned non-JSON data') from exc
                if not isinstance(payload, (dict, list)) or (isinstance(payload, dict) and 'error' in payload):
                    raise InvalidPackage('Provider returned an error payload')
                if url.endswith('/incidents') and (not isinstance(payload,dict) or not isinstance(payload.get('incidents'),list)):
                    raise InvalidPackage('Missing incidents response')
                return payload
            if status and status < 500:
                raise InvalidPackage(f'Provider HTTP {status}')
            if attempt == 2:
                raise RuntimeError(f'Provider temporarily unavailable: {status}')


def collect(state, fetch, persist, *, max_events=25, probe=False):
    """Persist after every page and completed match; no database side effects."""
    state['status'] = 'partial'
    state['errors'] = {}
    try:
        while not state['calendar_complete']:
            page = state['page']
            if page >= 100:
                raise InvalidPackage('Calendar exceeds page limit')
            response = fetch(f"{scraper.BASE_URL}/unique-tournament/11653/season/{state['season_id']}/events/last/{page}")
            if not isinstance(response, dict) or not isinstance(response.get('events'), list) or type(response.get('hasNextPage')) is not bool:
                raise InvalidPackage('Incomplete calendar response')
            if not response['events'] and response['hasNextPage']:
                raise InvalidPackage('Empty non-terminal calendar page')
            for event in response['events']:
                validate_event(event, state)
                eid = str(event['id'])
                previous = state['events'].get(eid)
                if previous and previous != event:
                    raise InvalidPackage('Conflicting duplicate calendar event')
                state['events'][eid] = event
            state['page'] += 1
            state['calendar_complete'] = not response['hasNextPage']
            persist(state)
            if probe:
                break
        pending = sorted(expected_ids(state) - set(state['matches']), key=int)
        if not expected_ids(state):
            raise InvalidPackage('No finished events')
        for eid in pending[:1 if probe else max_events]:
            event = state['events'][eid]
            try:
                entries, _ = scraper.process_finished_event(None, event, delay_lineup=0, delay_fallback=0, delay_incidents=0, fetcher=fetch)
                validate_players(event, entries)
                state['matches'][eid] = {'event_checksum':scraper.compute_event_checksum(event), 'players':entries, 'downloaded_at':now()}
                persist(state)
            except (BudgetReached, ProviderBlocked):
                raise
            except Exception as exc:
                state['errors'][eid] = type(exc).__name__
                raise
        state['status'] = 'validated' if complete(state) and not probe else 'partial'
    except BudgetReached:
        state['status'] = 'partial'
    except ProviderBlocked as exc:
        state['status'], state['retry_at'] = 'blocked', exc.retry_at
        state['errors']['provider'] = str(exc.status)
    except Exception as exc:
        state['status'] = 'invalid'
        state['errors']['collection'] = type(exc).__name__
    persist(state)
    return state
