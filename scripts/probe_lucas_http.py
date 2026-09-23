"""Probe the original HTTP path, including its nonfatal homepage warmup."""
import importlib.metadata
import json
import sys
from pathlib import Path

sys.path.insert(0, '/app/web_scraping_sofascore')
import sofascore_scraper as scraper

report = {'source_commit':'cbe7121d9933e62b088ec608bd45700e1dcddcd7',
          'curl_cffi':importlib.metadata.version('curl_cffi'),
          'database_writes':False,'success':False,'requests':[]}
ctx = scraper.get_fetch_context()
session, backend = scraper._make_http_session(ctx)
original_get = session.get


def observed_get(url, **kwargs):
    try:
        response = original_get(url, **kwargs)
    except Exception as exc:
        report['requests'].append({'url':url,'error_type':type(exc).__name__})
        raise
    report['requests'].append({'url':url,'status':response.status_code})
    return response


session.get = observed_get
# Reuse one session just as the successful local historical collector did.
scraper._make_http_session = lambda context: (session, backend)
try:
    calendar, meta = scraper.fetch_json_requests(
        scraper.BASE_URL+'/unique-tournament/11653/season/57883/events/last/0', delay=5, ctx=ctx)
    events = calendar.get('events', []) if isinstance(calendar, dict) else []
    report['calendar_events'] = len(events)
    if not events or any(e.get('season',{}).get('id') != 57883 for e in events):
        raise ValueError('Calendar unavailable or wrong season')
    event = next(e for e in events if e.get('status',{}).get('type') == 'finished')
    report['event_id'] = event['id']
    lineup, meta = scraper.fetch_json_requests(
        scraper.BASE_URL+f"/event/{event['id']}/lineups", delay=5, ctx=ctx)
    if not isinstance(lineup,dict):
        raise ValueError('Lineup unavailable')
    counts = [sum(bool(p.get('statistics')) for p in lineup.get(side,{}).get('players',[]))
              for side in ('home','away')]
    report['players_with_statistics'] = counts
    report['success'] = all(count >= 11 for count in counts)
except Exception as exc:
    report['error_type'] = type(exc).__name__
finally:
    session.close()
    destination = Path('/report/report.json')
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report),flush=True)
sys.exit(0 if report['success'] else 2)
