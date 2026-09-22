"""Bounded A/B diagnostic of original vs current Selenium construction.

Both arms use the same navigation, requests, Chromium binary and runner.
No database access, HTTP fallback, cookies export or raw data publication.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import inspect
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'web_scraping_sofascore'))
import sofascore_scraper as scraper

ORIGINAL_COMMIT = 'cbe7121d9933e62b088ec608bd45700e1dcddcd7'
CALENDAR = scraper.BASE_URL+'/unique-tournament/11653/season/71131/events/last/0'
EVENT_ID = 13443447
LINEUPS = scraper.BASE_URL+f'/event/{EVENT_ID}/lineups'


def original_builder(path):
    """Execute only build_driver from the audited original; not its module."""
    source = path.read_text(encoding='utf-8')
    node = next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='build_driver')
    snippet = ast.get_source_segment(source,node)
    namespace = dict(vars(scraper))
    exec(compile(snippet,str(path),'exec'),namespace)
    return namespace['build_driver'],hashlib.sha256(snippet.encode()).hexdigest()


def summarize_response(response, kind):
    status = response.get('status',0)
    result = {'http_status':status,'valid':False}
    if status != 200:
        return result
    try:
        data=json.loads(response.get('body',''))
    except (ValueError,TypeError):
        return result
    if not isinstance(data,dict) or 'error' in data:
        return result
    if kind=='calendar':
        events=data.get('events')
        if isinstance(events,list) and events and all(isinstance(e,dict) and type(e.get('id')) is int for e in events):
            result.update(valid=True,events=len(events),target_present=any(e['id']==EVENT_ID for e in events))
    else:
        sides=[data.get(side,{}).get('players',[]) for side in ('home','away')]
        counts=[sum(bool(p.get('statistics')) for p in side if isinstance(p,dict)) for side in sides]
        result.update(players=sum(len(side) for side in sides),players_with_statistics=sum(counts))
        result['valid']=all(count>=11 for count in counts)
    return result


def browser_json(driver,url):
    # GET in the normal browser session, identical in both arms.
    return driver.execute_async_script('''
        const done=arguments[arguments.length-1];
        fetch(arguments[0],{credentials:'include',signal:AbortSignal.timeout(25000),
          headers:{'Accept':'application/json, text/plain, */*','Accept-Language':'es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7'}})
        .then(async r=>done({status:r.status,body:await r.text()}))
        .catch(()=>done({status:0,body:''}));
    ''',url)


def run_arm(name,build,source_hash):
    result={'configuration':name,'builder_sha256':source_hash,'success':False,'stage':'startup'}
    driver=None
    try:
        driver=build(headless=True)
        driver.set_page_load_timeout(40)
        driver.set_script_timeout(35)
        result['browser_version']=driver.capabilities.get('browserVersion')
        driver.get(scraper.SOFASCORE_HOME)
        result['stage']='homepage'
        body=driver.find_element('tag name','body').text
        try:
            payload=json.loads(body)
        except ValueError:
            payload={}
        if isinstance(payload,dict) and isinstance(payload.get('error'),dict):
            result['homepage_error_code']=payload['error'].get('code')
            return result
        scraper.WebDriverWait(driver,25).until(lambda d:'Sofascore' in d.title and len(d.find_element('tag name','body').text.strip())>100)
        result['homepage_loaded']=True
        time.sleep(5)
        result['stage']='calendar'
        result['calendar']=summarize_response(browser_json(driver,CALENDAR),'calendar')
        if not result['calendar']['valid']:
            return result
        time.sleep(5)
        result['stage']='lineups'
        result['lineups']=summarize_response(browser_json(driver,LINEUPS),'lineups')
        result['success']=result['lineups']['valid']
        return result
    except Exception as exc:
        result['error_type']=type(exc).__name__
        return result
    finally:
        if driver is not None:
            try: driver.quit()
            except Exception: pass


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original-source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    old,old_hash=original_builder(args.original_source)
    current_hash=hashlib.sha256(inspect.getsource(scraper.build_driver).encode()).hexdigest()
    results=[]
    for name,builder,sha in [('original',old,old_hash),('current',scraper.build_driver,current_hash)]:
        if results: time.sleep(15)
        result=run_arm(name,builder,sha)
        results.append(result)
        print(json.dumps(result))
    report={'original_commit':ORIGINAL_COMMIT,'season':2025,'event_id':EVENT_ID,
            'scope':'Selenium build_driver only; same GET flow; HTTP/curl fallback excluded',
            'order':['original','current'],'results':results}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    # Diagnostic execution success is NOT provider availability.
    return 0


if __name__=='__main__':
    raise SystemExit(main())
