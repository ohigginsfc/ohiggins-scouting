import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from tests.test_atomic_sofascore_import import db
from tests.test_sofascore_pipeline_post_download import _load_incremental

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def scraper(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT/'web_scraping_sofascore'))
    spec=importlib.util.spec_from_file_location('publication_test_scraper',ROOT/'web_scraping_sofascore/sofascore_scraper.py')
    mod=importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules,spec.name,mod)
    spec.loader.exec_module(mod)
    monkeypatch.setenv('SOFASCORE_FETCH_MODE','auto')
    monkeypatch.setattr(mod,'RETRY_DELAYS',[])
    return mod

@pytest.mark.parametrize('status',[401,403,429])
def test_access_denial_stops_before_other_hosts_or_browser(scraper,status):
    session=MagicMock()
    session.get.return_value=MagicMock(status_code=status,headers={},text='{}')
    with patch.object(scraper,'_make_http_session',return_value=(session,'requests')), \
         patch.object(scraper,'_http_warmup'), \
         patch.object(scraper,'_fetch_json_selenium_xhr') as xhr, \
         patch.object(scraper,'_fetch_json_selenium_get') as get:
        with pytest.raises(scraper.SofascoreFetchError,match=f'HTTP {status}'):
            scraper.fetch_json(scraper.BASE_URL+'/event/1/lineups',delay=0,driver=MagicMock())
    assert session.get.call_count==1
    xhr.assert_not_called();get.assert_not_called()


def test_exhausted_fetch_raises_instead_of_empty_lineup(scraper):
    with patch.object(scraper,'fetch_json_requests',return_value=(None,{'status_code':503})):
        with pytest.raises(scraper.SofascoreFetchError,match='after retries'):
            scraper.get_lineup_with_stats(None,1,delay_lineup=0,delay_fallback=0)


def test_browser_denial_does_not_try_direct_navigation(scraper):
    with patch.object(scraper,'fetch_json_requests',return_value=(None,{'status_code':503})), \
         patch.object(scraper,'_fetch_json_selenium_xhr',return_value=(None,403)), \
         patch.object(scraper,'_fetch_json_selenium_get') as get:
        with pytest.raises(scraper.SofascoreFetchError,match='HTTP 403'):
            scraper.fetch_json('https://example.invalid',delay=0,driver=MagicMock())
    get.assert_not_called()


def test_explicit_browser_mode_never_calls_http(scraper, monkeypatch):
    monkeypatch.setenv('SOFASCORE_FETCH_MODE', 'browser')
    with patch.object(scraper, 'fetch_json_requests') as http, \
         patch.object(scraper, '_fetch_json_selenium_xhr', return_value=('{"events":[{"id":123}]}', 200)):
        assert scraper.fetch_json('https://example.invalid', delay=0, driver=MagicMock()) == {'events':[{'id':123}]}
    http.assert_not_called()


@pytest.mark.parametrize('status', [401, 403, 429])
def test_explicit_browser_mode_reports_denial(scraper, monkeypatch, status):
    monkeypatch.setenv('SOFASCORE_FETCH_MODE', 'browser')
    with patch.object(scraper, 'fetch_json_requests') as http, \
         patch.object(scraper, '_fetch_json_selenium_xhr', return_value=(None, status)), \
         patch.object(scraper, '_fetch_json_selenium_get') as get:
        with pytest.raises(scraper.SofascoreFetchError, match=f'HTTP {status}'):
            scraper.fetch_json('https://example.invalid', delay=0, driver=MagicMock())
    http.assert_not_called()
    get.assert_not_called()


def test_explicit_browser_requires_driver(scraper, monkeypatch):
    monkeypatch.setenv('SOFASCORE_FETCH_MODE', 'browser')
    with pytest.raises(scraper.SofascoreFetchError, match='requires a Chrome driver'):
        scraper.fetch_json('https://example.invalid', delay=0, ctx=scraper.FetchContext())


def test_browser_warmup_failure_does_not_mark_session_ready(scraper):
    from selenium.common.exceptions import TimeoutException
    ctx = scraper.FetchContext()
    driver = MagicMock()
    with patch.object(scraper, 'WebDriverWait') as wait:
        wait.return_value.until.side_effect = TimeoutException('page not ready')
        with pytest.raises(TimeoutException):
            scraper._warmup_browser(driver, ctx)
    assert not ctx.browser_warmed


@pytest.mark.parametrize('ok',[True,False])
def test_event_publication_only_changes_downloaded_ids_in_checkpoint(db,ok):
    inc=_load_incremental();league=inc.LEAGUES[0]
    statuses={1:'downloaded',2:'downloaded',3:'failed',4:'pending',5:'processed'}
    with db() as conn:
        for eid,status in statuses.items():
            inc.ingestion_repo.upsert_event(conn,country=league.country,division=league.division,
                competition=league.competition,season=2025,event_id=eid,processing_status=status)
        inc.ingestion_repo.upsert_event(conn,country=league.country,division=league.division,
            competition='Other',season=2025,event_id=1,processing_status='downloaded')
    with patch.object(inc,'get_connection',side_effect=db):
        inc._mark_scope_import_outcome(league,2025,ok=ok,error_message=None if ok else 'test error',event_ids=[1,3,4,5])
    with db() as conn:
        actual=dict(conn.execute('SELECT event_id,processing_status FROM sofascore_event_ingestion WHERE competition=%s',(league.competition,)).fetchall())
        assert actual=={**statuses,1:'processed' if ok else 'downloaded'}
        assert conn.execute("SELECT processing_status FROM sofascore_event_ingestion WHERE competition='Other'").fetchone()[0]=='downloaded'


def test_status_persistence_failure_is_not_reported_as_success():
    inc=_load_incremental()
    with patch.object(inc,'get_connection',side_effect=RuntimeError('unavailable')):
        with pytest.raises(RuntimeError,match='confirmar el estado'):
            inc._mark_scope_import_outcome(inc.LEAGUES[0],2025,ok=True,error_message=None,event_ids=[1])


@pytest.mark.parametrize('payload',['{}','{"1":[{}]}','{"1":[{"event_id":true}]}'])
def test_untraceable_checkpoint_never_imports(tmp_path,payload):
    inc=_load_incremental();league=inc.LEAGUES[0]
    folder=tmp_path/'web_scraping_sofascore/sofascore_output'/league.output_slug
    folder.mkdir(parents=True);(folder/'checkpoint_raw.json').write_text(payload)
    with patch.object(inc,'import_league') as importer, patch.object(inc,'_mark_scope_import_outcome') as mark:
        result=inc.finalize_league_from_checkpoint(tmp_path,league,'2025',inc.LeagueIncrementalResult(league),skip_import=False,use_replace=True)
    assert result.errors==1
    importer.assert_not_called();mark.assert_not_called()


def test_runtime_smoke_rejects_access_denied_page(scraper,monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT/'scripts'))
    import test_selenium_runtime as smoke
    monkeypatch.setitem(sys.modules,'sofascore_scraper',scraper)
    driver=MagicMock();driver.title='Access denied';driver.current_url='https://www.sofascore.com/'
    with patch.object(scraper,'build_driver',return_value=driver):
        assert smoke.main()==1
    driver.quit.assert_called_once()


def test_runtime_smoke_checks_async_runtime_only(scraper,monkeypatch,capsys):
    monkeypatch.syspath_prepend(str(ROOT/'scripts'))
    import test_selenium_runtime as smoke
    monkeypatch.setitem(sys.modules,'sofascore_scraper',scraper)
    driver=MagicMock();driver.title='Scouting Selenium runtime';driver.execute_async_script.return_value=driver.title
    with patch.object(scraper,'build_driver',return_value=driver):
        assert smoke.main()==0
    assert 'NO comprobados' in capsys.readouterr().out
    assert driver.get.call_args.args[0].startswith('data:')

@pytest.mark.parametrize('changed',[False,True])
def test_finalizer_uses_checkpoint_ids_and_rejects_mutation(tmp_path,changed):
    inc=_load_incremental();league=inc.LEAGUES[0]
    folder=tmp_path/'web_scraping_sofascore/sofascore_output'/league.output_slug
    folder.mkdir(parents=True)
    checkpoint=folder/'checkpoint_raw.json'
    checkpoint.write_text('{"1":[{"event_id":3},{"event_id":1},{"event_id":3}]}')
    (folder/'player_stats.csv').write_text('player_id,goals\n1,2\n')
    def stage(*args,**kwargs):
        if changed:
            checkpoint.write_text('{"1":[{"event_id":99}]}')
        return folder
    with patch('scouting.services.sofascore_teams_rebuild.ensure_teams_json',return_value=(True,'ok',2)), \
         patch.object(inc,'reaggregate_league_from_checkpoint',return_value=(True,'ok')), \
         patch.object(inc,'validate_sofascore_output',return_value=(True,'ok')), \
         patch.object(inc,'stage_league',side_effect=stage), \
         patch.object(inc,'import_league') as importer, \
         patch.object(inc,'_mark_scope_import_outcome') as mark:
        result=inc.finalize_league_from_checkpoint(tmp_path,league,'2025',inc.LeagueIncrementalResult(league),skip_import=False,use_replace=True)
    assert mark.call_args.kwargs['event_ids']==[1,3]
    assert mark.call_args.kwargs['ok'] is (not changed)
    assert result.errors==int(changed)
    assert importer.call_count==int(not changed)


def test_successful_json_response_remains_usable(scraper):
    payload={'home':{'players':[]},'away':{'players':[]}}
    with patch.object(scraper,'fetch_json_requests',return_value=(payload,{'status_code':200})):
        assert scraper.fetch_json('https://example.invalid',delay=0)==payload


def test_expected_missing_individual_stats_remains_nonfatal(scraper):
    with patch.object(scraper,'fetch_json_requests',return_value=(None,{'status_code':404,'expected_missing_player_stats':True})):
        assert scraper.fetch_json('https://example.invalid/event/1/player/1/statistics',delay=0) is None
