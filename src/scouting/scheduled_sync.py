"""Bounded weekly use of the existing collector and atomic publisher."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from scouting import manual_sync as manual


def run(folder, fetch, *, apply=False, lookback_days=14):
    folder = Path(folder)
    summary_path = folder / 'weekly-summary.json'
    started = manual.r.now()
    if summary_path.exists():
        prior = manual.read(summary_path)
        retry_at = prior.get('retry_at')
        if retry_at and datetime.fromisoformat(retry_at) > datetime.fromisoformat(started):
            raise manual.r.ProviderBlocked(prior['http_status'], retry_at)
    summary = dict(started_at=started, season='2026', status='running', applied=False)
    manual.save(summary_path, summary)
    try:
        path = folder / 'candidate.json'
        resume = False
        if path.exists():
            previous = manual.read(path)
            if previous.get('version') != 1 or previous.get('season_id') != manual.SEASON_ID:
                raise ValueError('Wrong checkpoint scope/version')
            resume = (not previous.get('calendar_complete')
                      or set(previous.get('events', {})) != set(previous.get('matches', {})))
        state, frame = manual.collect(folder, fetch, resume=resume, lookback_days=lookback_days)
        if resume:
            # A resumed run has its old cutoff. Refresh it before claiming the weekly update is current.
            state, frame = manual.collect(folder, fetch, resume=False, lookback_days=lookback_days)
        result = manual.publish(folder, apply=apply)
        summary.update(status='published' if apply else 'validated', applied=apply,
                       cutoff=state['cutoff'], matches=len(state['events']), players=len(frame),
                       latest_event_at=datetime.fromtimestamp(
                           max(e['startTimestamp'] for e in state['events'].values()),
                           tz=datetime.fromisoformat(started).tzinfo).isoformat(),
                       publication=result)
    except manual.r.ProviderBlocked as exc:
        summary.update(status='blocked', http_status=exc.status, retry_at=exc.retry_at)
        raise
    except Exception as exc:
        summary.update(status='stopped', error_type=type(exc).__name__)
        raise
    finally:
        summary['finished_at'] = manual.r.now()
        manual.save(summary_path, summary)
    return summary
