"""Bounded weekly use of the existing collector and atomic publisher."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from scouting import manual_sync as manual
from scouting.sofascore_leagues import DEFAULT_LEAGUE

PROVIDER_COOLDOWN = manual.r.ROOT / 'data/recovery/sofascore-cooldown.json'


def run(folder, fetch, *, apply=False, lookback_days=14, league=DEFAULT_LEAGUE):
    folder = Path(folder)
    summary_path = folder / 'weekly-summary.json'
    started = manual.r.now()
    prior = manual.read(summary_path) if summary_path.exists() else {}
    summary = dict(started_at=started, season=league.season, league_key=league.key, status='running', applied=False)
    options = {} if league == DEFAULT_LEAGUE else {'league': league}
    manual.save(summary_path, summary)
    try:
        provider_wait = manual.read(PROVIDER_COOLDOWN) if PROVIDER_COOLDOWN.exists() else {}
        waits = [wait for wait in (prior, provider_wait)
                 if wait.get('retry_at') and datetime.fromisoformat(wait['retry_at']) > datetime.fromisoformat(started)]
        if waits:
            wait = max(waits, key=lambda item: datetime.fromisoformat(item['retry_at']))
            raise manual.r.ProviderBlocked(wait['http_status'], wait['retry_at'])
        path = folder / 'candidate.json'
        resume = False
        if path.exists():
            previous = manual.read(path)
            manual.validate_scope(previous, league)
            resume = (not previous.get('calendar_complete')
                      or set(previous.get('events', {})) != set(previous.get('matches', {})))
        state, frame = manual.collect(folder, fetch, resume=resume, lookback_days=lookback_days, **options)
        if resume:
            # A resumed run has its old cutoff. Refresh it before claiming the weekly update is current.
            state, frame = manual.collect(folder, fetch, resume=False, lookback_days=lookback_days, **options)
        result = manual.publish(folder, apply=apply, **options)
        summary.update(status='published' if apply else 'validated', applied=apply,
                       cutoff=state['cutoff'], matches=len(state['events']), players=len(frame),
                       latest_event_at=datetime.fromtimestamp(
                           max(e['startTimestamp'] for e in state['events'].values()),
                           tz=datetime.fromisoformat(started).tzinfo).isoformat(),
                       publication=result)
    except manual.r.ProviderBlocked as exc:
        retry_at = exc.retry_at or (datetime.fromisoformat(started) + timedelta(hours=24)).isoformat()
        summary.update(status='blocked', http_status=exc.status, retry_at=retry_at)
        manual.save(PROVIDER_COOLDOWN, dict(http_status=exc.status, retry_at=retry_at, blocked_at=started))
        raise
    except Exception as exc:
        summary.update(status='stopped', error_type=type(exc).__name__)
        raise
    finally:
        summary['finished_at'] = manual.r.now()
        manual.save(summary_path, summary)
    return summary
