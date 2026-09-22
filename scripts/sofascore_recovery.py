"""Remote collection and local-only application of encrypted recovery packages."""
from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from scouting import sofascore_recovery as recovery

REPO = 'ohigginsfc/ohiggins-scouting'
WORKFLOW = 'sofascore-recovery.yml'


def gh_api(path):
    return json.loads(subprocess.check_output(['gh', 'api', f'repos/{REPO}/{path}'], text=True, encoding='utf-8'))


def download_checkpoint(run_id, season, destination):
    """Only packages from manual main-branch runs of the trusted workflow."""
    name = f'sofascore-recovery-{season}-collect'
    if run_id == 'latest':
        runs = gh_api(f'actions/workflows/{WORKFLOW}/runs?branch=main&status=completed&event=workflow_dispatch&per_page=100')['workflow_runs']
    elif str(run_id).isdigit():
        runs = [gh_api(f'actions/runs/{run_id}')]
    else:
        raise recovery.InvalidPackage('Expected latest or a numeric run ID')
    for run in runs:
        if run['head_branch'] != 'main' or run['event'] != 'workflow_dispatch' or run['path'].split('@')[0] != f'.github/workflows/{WORKFLOW}':
            continue
        artifacts = gh_api(f"actions/runs/{run['id']}/artifacts?per_page=100")['artifacts']
        for artifact in artifacts:
            if artifact['name'] != name or artifact['expired']:
                continue
            with tempfile.TemporaryDirectory() as tmp:
                subprocess.run(['gh','run','download',str(run['id']),'--repo',REPO,'--name',name,'--dir',tmp],check=True,capture_output=True)
                source = Path(tmp) / 'recovery.sofa'
                if not source.is_file():
                    raise recovery.InvalidPackage('Checkpoint file absent')
                recovery.atomic_write(destination, source.read_bytes())
            return str(run['id'])
    raise recovery.InvalidPackage('No compatible checkpoint found; select new explicitly to start')


def run_collection(args):
    key = recovery.read_key()  # Never open a browser without encrypted persistence.
    output = args.output / 'recovery.sofa'
    args.output.mkdir(parents=True, exist_ok=True)
    if args.mode == 'probe' and args.checkpoint != 'new':
        raise recovery.InvalidPackage('Probe requires checkpoint=new')
    if args.checkpoint == 'new':
        state = recovery.new_state(args.season)
    else:
        source = args.input_package
        if source is None:
            source = args.output / 'input.sofa'
            download_checkpoint(args.checkpoint, args.season, source)
        state = recovery.unpack(recovery.decrypt_document(source,key), args.season)
        if state.get('probe_only'):
            raise recovery.InvalidPackage('Probe is not a season checkpoint')
        retry_at = state.get('retry_at')
        if retry_at and datetime.fromisoformat(retry_at) > datetime.now(timezone.utc):
            raise recovery.InvalidPackage('Provider Retry-After has not elapsed')
    if args.refresh:
        if args.mode != 'collect':
            raise recovery.InvalidPackage('Refresh applies only to collect')
        state = recovery.new_state(args.season)
    if args.mode == 'validate':
        if not recovery.complete(state):
            raise recovery.InvalidPackage('Package is incomplete')
        state['status'] = 'validated'
    else:
        state['probe_only'] = args.mode == 'probe'
        persist = lambda current: recovery.encrypt_document(recovery.pack(current), output, key)
        persist(state)
        driver = None
        transport = None
        try:
            if args.transport == 'http':
                transport = recovery.HttpTransport()
                transport.warmup()
            else:
                driver = recovery.scraper.build_driver()
                driver.set_page_load_timeout(40)
                driver.set_script_timeout(35)
                driver.get(recovery.scraper.SOFASCORE_HOME)
                body = driver.find_element('tag name', 'body').text
                if '"code": 403' in body or '"code":403' in body or 'captcha' in driver.title.lower():
                    raise recovery.ProviderBlocked(403)
                recovery.scraper.WebDriverWait(driver,25).until(lambda d: 'Sofascore' in d.title and len(d.find_element('tag name','body').text.strip()) > 100)
                transport = recovery.BrowserTransport(driver)
            recovery.collect(state, transport.fetch, persist, probe=args.mode=='probe')
        except recovery.ProviderBlocked as exc:
            state['status'], state['errors'] = 'blocked', {'provider':str(exc.status)}
            state['retry_at'] = exc.retry_at
        except Exception as exc:
            state['status'], state['errors'] = 'invalid', {'runtime':type(exc).__name__}
        finally:
            if isinstance(transport, recovery.HttpTransport):
                transport.close()
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass
    document = recovery.pack(state)
    recovery.encrypt_document(document, output, key)
    summary = {key:document['manifest'][key] for key in ('season','status','expected','completed','failed')}
    summary['probe_ok'] = args.mode == 'probe' and len(state['matches']) == 1 and not state['errors']
    recovery.atomic_write(args.output/'summary.json',recovery.canonical(summary))
    print(json.dumps(summary))
    if os.getenv('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as report:
            report.write('## Sofascore recovery\n\n```json\n'+json.dumps(summary,indent=2)+'\n```\n')
            report.write('Only `validated` represents a complete season. `partial` is resumable and not importable.\n')
    return 2 if state['status'] in ('blocked','invalid') or (args.mode == 'probe' and not summary['probe_ok']) else 0


def apply_local(document, *, pg_dump=None):
    """Import only into the local demo database, after a successful backup."""
    from scouting.config.database import get_db_connection_params
    from scouting.db import get_connection
    from scouting.ingestion.import_sofascore_player_stats_csv import import_dataframe
    from scouting.repositories.sofascore_event_ingestion_repository import upsert_event
    state = recovery.unpack(document, document['manifest']['season'], require_complete=True)
    params = get_db_connection_params()
    if params['host'] not in ('localhost','127.0.0.1','::1') or params['dbname'] != 'scouting_local':
        raise recovery.InvalidPackage('This milestone only applies to local scouting_local')
    executable = pg_dump or shutil.which('pg_dump')
    if not executable:
        raise recovery.InvalidPackage('pg_dump required: supply --pg-dump')
    backup = ROOT/'data/recovery/backups'/f"scouting-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}.dump"
    backup.parent.mkdir(parents=True,exist_ok=True)
    env = os.environ.copy()
    env['PGPASSWORD'] = str(params['password'])
    subprocess.run([str(executable),'-h',str(params['host']),'-p',str(params['port']),'-U',str(params['user']),'-d',str(params['dbname']),'-Fc','-f',str(backup)],env=env,check=True,capture_output=True)
    if not backup.is_file() or not backup.stat().st_size:
        raise recovery.InvalidPackage('Database backup failed')
    def mark_events(conn, batch_id):
        for eid in sorted(state['matches'],key=int):
            event = state['events'][eid]
            upsert_event(conn,country='cl',division='primera',competition=recovery.COMPETITION,
                         season=int(state['season']),event_id=int(eid),home_team=event['homeTeam']['name'],
                         away_team=event['awayTeam']['name'],event_date=recovery.scraper.event_datetime_utc(event),
                         status='finished',checksum=recovery.scraper.compute_event_checksum(event),
                         processing_status='processed',import_batch_id=batch_id,commit=False)
    frame = recovery.pd.read_csv(io.StringIO(document['files']['player_stats.csv']))
    with get_connection() as conn:
        batch_id, stats = import_dataframe(conn,frame,country='cl',division='primera',season=state['season'],
                                          competition=recovery.COMPETITION,source_file='recovery:'+document['manifest']['state_sha256'],
                                          replace=True,publication_hook=mark_events)
    return {'batch_id':str(batch_id),'metrics_inserted':stats['metrics_inserted'],'backup':str(backup)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command',required=True)
    collect = commands.add_parser('run')
    collect.add_argument('--mode',choices=['probe','collect','validate'],required=True)
    collect.add_argument('--season',choices=list(recovery.SEASONS),required=True)
    collect.add_argument('--transport',choices=['http','browser'],default='http')
    collect.add_argument('--checkpoint',default='latest',help='new, latest, or trusted workflow run ID')
    collect.add_argument('--input-package',type=Path,help='Previously downloaded encrypted checkpoint')
    collect.add_argument('--output',type=Path,default=ROOT/'data/recovery/output')
    collect.add_argument('--refresh',action='store_true')
    local = commands.add_parser('local')
    local.add_argument('--season',choices=list(recovery.SEASONS),required=True)
    source = local.add_mutually_exclusive_group(required=True)
    source.add_argument('--package',type=Path)
    source.add_argument('--run-id')
    local.add_argument('--apply',action='store_true')
    local.add_argument('--pg-dump',type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'run':
            return run_collection(args)
        key = recovery.read_key()
        path = args.package
        if args.run_id:
            path = ROOT/'data/recovery/downloads'/f'{args.season}-{args.run_id}.sofa'
            download_checkpoint(args.run_id,args.season,path)
        document = recovery.decrypt_document(path,key)
        recovery.unpack(document,args.season,require_complete=True)
        print(json.dumps(apply_local(document,pg_dump=args.pg_dump) if args.apply else {'validated':True,'applied':False,'season':args.season}))
        return 0
    except Exception as exc:
        # Avoid provider payloads, environment values and connection credentials.
        print(f'Recovery failed: {type(exc).__name__}',file=sys.stderr)
        if isinstance(exc,recovery.InvalidPackage):
            print(str(exc),file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
