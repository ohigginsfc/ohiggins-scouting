import copy
import json
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from scouting import sofascore_recovery as r
from tests.test_atomic_sofascore_import import db, frame, publish, snapshot
from scouting.repositories.sofascore_event_ingestion_repository import upsert_event


def event(eid=1):
    return {'id':eid,'season':{'id':57883},'tournament':{'uniqueTournament':{'id':11653}},
            'status':{'type':'finished'},'homeTeam':{'id':1,'name':'Home'},'awayTeam':{'id':2,'name':'Away'}}


def players(eid=1):
    return [{'event_id':eid,'player':{'id':pid,'name':f'Player {pid}','position':'M'},
             'team':{'id':1 if pid<=11 else 2,'name':'Home' if pid<=11 else 'Away'},
             'statistics':{'minutesPlayed':90,'goals':1},'substitute':False} for pid in range(1,23)]


def complete_state():
    state=r.new_state('2024')
    state.update(calendar_complete=True,page=1,status='validated')
    state['events']['1']=event()
    state['matches']['1']={'event_checksum':r.scraper.compute_event_checksum(event()),'players':players(),'downloaded_at':r.now()}
    return state


def test_package_authenticated_and_scope_bound(tmp_path):
    package=r.pack(complete_state());key=b'x'*32;path=tmp_path/'recovery.sofa'
    r.encrypt_document(package,path,key)
    assert b'Player' not in path.read_bytes()
    assert r.unpack(r.decrypt_document(path,key),'2024',require_complete=True)['status']=='validated'
    with pytest.raises(r.InvalidPackage):
        r.decrypt_document(path,b'y'*32)
    damaged=bytearray(path.read_bytes());damaged[-1]^=1;path.write_bytes(damaged)
    with pytest.raises(r.InvalidPackage):
        r.decrypt_document(path,key)
    with pytest.raises(r.InvalidPackage):
        r.unpack(package,'2025')


@pytest.mark.parametrize('change',['partial','missing','wrong_event','wrong_season','duplicate','csv'])
def test_invalid_publications_rejected(change):
    document=r.pack(complete_state())
    if change=='csv':
        document['files']['player_stats.csv']='player_id\n999\n'
    else:
        state=document['state']
        if change=='partial': state['calendar_complete']=False
        if change=='missing': state['matches']={}
        if change=='wrong_event': state['matches']['1']['players'][0]['event_id']=2
        if change=='wrong_season': state['events']['1']['season']['id']=71131
        if change=='duplicate': state['matches']['1']['players'].append(copy.deepcopy(players()[0]))
        document['manifest']['state_sha256']=r.digest(state)
    with pytest.raises(r.InvalidPackage):
        r.unpack(document,'2024',require_complete=True)


def test_partial_pages_and_matches_resume_without_repeat():
    state=r.new_state('2024');saved=[]
    fetch=MagicMock(return_value={'events':[event(1),event(2)],'hasNextPage':False})
    with patch.object(r.scraper,'process_finished_event',side_effect=lambda _,ev,**kw:(players(ev['id']),None)) as scrape:
        r.collect(state,fetch,lambda s:saved.append(copy.deepcopy(s)),max_events=1)
        assert state['status']=='partial' and len(state['matches'])==1
        document=r.pack(state)
        state=r.unpack(document,'2024')
        fetch.reset_mock()
        r.collect(state,fetch,lambda s:saved.append(copy.deepcopy(s)),max_events=1)
        assert state['status']=='validated'
        assert [call.args[1]['id'] for call in scrape.call_args_list]==[1,2]
        fetch.assert_not_called()
        assert any(len(s['matches'])==1 for s in saved)


def test_page_budget_keeps_calendar_incomplete_and_resumable():
    state=r.new_state('2024')
    fetch=MagicMock(side_effect=[{'events':[event()],'hasNextPage':True},r.BudgetReached()])
    r.collect(state,fetch,lambda s:None)
    assert state['page']==1 and not state['calendar_complete'] and state['status']=='partial'
    with pytest.raises(r.InvalidPackage):
        r.unpack(r.pack(state),'2024',require_complete=True)


@pytest.mark.parametrize('status',[401,403,429])
def test_denial_stops_requests_and_preserves_completed_matches(status):
    state=complete_state();state['events']['2']=event(2)
    driver=MagicMock();driver.execute_async_script.return_value={'status':status,'body':'no','retry':'3600'}
    transport=r.BrowserTransport(driver)
    r.collect(state,transport.fetch,lambda s:None)
    assert state['status']=='blocked' and list(state['matches'])==['1']
    assert driver.execute_async_script.call_count==1
    if status==429: assert state['retry_at']


def test_request_budget_and_spacing():
    clock=[0.0];sleeps=[]
    def sleep(seconds): sleeps.append(seconds);clock[0]+=seconds
    driver=MagicMock();driver.execute_async_script.return_value={'status':200,'body':'{}'}
    transport=r.BrowserTransport(driver,max_requests=2,clock=lambda:clock[0],sleep=sleep)
    for _ in range(2): transport.fetch(r.scraper.BASE_URL+'/event/1/lineups')
    with pytest.raises(r.BudgetReached): transport.fetch(r.scraper.BASE_URL+'/event/1/lineups')
    assert sum(sleeps)>=5 and driver.execute_async_script.call_count==2


def test_transient_failure_retries_only_twice():
    driver=MagicMock();driver.execute_async_script.return_value={'status':503,'body':''}
    with patch.object(r.time,'sleep') as sleep:
        transport=r.BrowserTransport(driver,sleep=sleep)
        with pytest.raises(RuntimeError): transport.fetch(r.scraper.BASE_URL+'/event/1/lineups')
    assert driver.execute_async_script.call_count==3
    assert 30 in [call.args[0] for call in sleep.call_args_list]
    assert 120 in [call.args[0] for call in sleep.call_args_list]


def test_expected_missing_substitute_statistics_is_nonfatal():
    driver=MagicMock();driver.execute_async_script.return_value={'status':404,'body':''}
    assert r.BrowserTransport(driver).fetch(r.scraper.BASE_URL+'/event/1/player/1/statistics') is None


def test_incomplete_calendar_schema_is_not_success():
    state=r.new_state('2024')
    r.collect(state,lambda url:{'events':[event()]},lambda s:None)
    assert state['status']=='invalid' and not state['calendar_complete']


def test_metric_and_event_publication_roll_back_together(db):
    publish(db)
    before=snapshot(db)
    def fail_after_event(conn,batch_id):
        upsert_event(conn,country='cl',division='primera',competition='Synthetic League',season=2026,
                     event_id=1,processing_status='processed',import_batch_id=batch_id,commit=False)
        raise RuntimeError('event confirmation failure')
    with pytest.raises(RuntimeError):
        publish(db,frame(2),publication_hook=fail_after_event)
    assert snapshot(db)==before
    with db() as conn:
        assert conn.execute('SELECT count(*) FROM sofascore_event_ingestion').fetchone()[0]==0


def test_real_aggregate_import_is_repeatable(db):
    rows=r.derived_files(complete_state())['player_stats.csv']
    import io
    df=pd.read_csv(io.StringIO(rows))
    for _ in range(2):
        batch,stats=publish(db,df)
        with db() as conn:
            assert conn.execute('SELECT count(*) FROM objective_metrics').fetchone()[0]==stats['metrics_inserted']


def test_existing_incremental_errors_never_publish():
    from tests.test_sofascore_pipeline_post_download import _load_incremental
    inc=_load_incremental();league=inc.LEAGUES[0]
    result=inc.LeagueIncrementalResult(league);result.errors=1
    with patch.object(inc,'import_league') as importer:
        assert inc.finalize_league_from_checkpoint(r.ROOT,league,'2025',result,skip_import=False,use_replace=True).errors==1
    importer.assert_not_called()


def test_local_apply_has_backup_and_commits_exact_events(db, monkeypatch, tmp_path):
    import sys
    monkeypatch.syspath_prepend(str(r.ROOT/'scripts'))
    import sofascore_recovery as cli
    monkeypatch.setattr(cli,'ROOT',tmp_path)
    def backup(args, **kwargs):
        assert kwargs['env']['PGPASSWORD']=='test-only'
        assert 'test-only' not in args
        from pathlib import Path
        Path(args[-1]).write_bytes(b'test backup')
    document=r.pack(complete_state())
    params={'host':'127.0.0.1','port':55439,'dbname':'scouting_local','user':'test','password':'test-only'}
    with patch('scouting.config.database.get_db_connection_params',return_value=params), \
         patch('scouting.db.get_connection',side_effect=db), \
         patch.object(cli.subprocess,'run',side_effect=backup):
        for _ in range(2):
            result=cli.apply_local(document,pg_dump='pg_dump')
            with db() as conn:
                assert conn.execute('SELECT count(*) FROM objective_metrics').fetchone()[0]==result['metrics_inserted']
                assert conn.execute("SELECT event_id,processing_status FROM sofascore_event_ingestion").fetchall()==[(1,'processed')]


def test_local_apply_rejects_remote_database(monkeypatch):
    monkeypatch.syspath_prepend(str(r.ROOT/'scripts'))
    import sofascore_recovery as cli
    with patch('scouting.config.database.get_db_connection_params',return_value={'host':'remote','dbname':'scouting_local'}), \
         patch.object(cli.subprocess,'run') as run:
        with pytest.raises(r.InvalidPackage,match='only applies'):
            cli.apply_local(r.pack(complete_state()),pg_dump='pg_dump')
    run.assert_not_called()


def test_backup_failure_prevents_import(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(r.ROOT/'scripts'))
    import sofascore_recovery as cli
    monkeypatch.setattr(cli,'ROOT',tmp_path)
    params={'host':'127.0.0.1','port':55439,'dbname':'scouting_local','user':'test','password':'test-only'}
    with patch('scouting.config.database.get_db_connection_params',return_value=params), \
         patch('scouting.db.get_connection') as connect, \
         patch.object(cli.subprocess,'run',side_effect=RuntimeError('backup failed')):
        with pytest.raises(RuntimeError): cli.apply_local(r.pack(complete_state()),pg_dump='pg_dump')
    connect.assert_not_called()
