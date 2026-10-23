"""Windows/Edge final release journey. Fresh DB, real UI/API, no domain DB edits.

Run from an installed checkout with the verified model and raw UCI CSV. Reuses
existing CDP/Phase29 browser helpers; evidence is ignored. Never fits a model.
"""
from pathlib import Path
import ast
import base64
import csv
import io
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import websocket

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
g = root / 'ml/results/generated'
flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
processes, logs = [], []


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def main():
    g.mkdir(exist_ok=True)
    backend_port, frontend_port, debug_port = free_port(), free_port(), free_port()
    api, frontend = f'http://localhost:{backend_port}', f'http://localhost:{frontend_port}'
    source = (root/'tests/verify_dashboard_browser.py').read_text(encoding='utf-8')
    source = source.replace('8000', str(backend_port)).replace('5173', str(frontend_port)).replace('phase17_', 'phase30_')
    source = source.replace(f'127.0.0.1:{backend_port}', f'localhost:{backend_port}')
    nodes = [n for n in ast.parse(source).body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name in ('CDP','spawn','stop','ready')]
    assert len(nodes) == 4
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<existing-CDP-helpers>', 'exec'), globals())
    from unittest.mock import patch
    with tempfile.TemporaryDirectory(prefix='smartenergy-release-db-') as directory, tempfile.TemporaryDirectory(prefix='smartenergy-release-browser-') as profile:
        assert not Path(profile).resolve().is_relative_to(root)
        url = 'sqlite:///' + (Path(directory)/'release.db').as_posix()
        with patch.dict(os.environ, {'DATABASE_URL':url, 'SMARTENERGY_CORS_ORIGINS':frontend, 'VITE_API_BASE_URL':api, 'SMARTENERGY_COOKIE_SECURE':'false'}):
            from alembic import command
            from alembic.config import Config
            from sqlalchemy import inspect, text
            from sqlalchemy.orm import sessionmaker
            from backend.database import create_database_engine
            from scripts.create_admin import create_admin
            config = Config(str(root/'alembic.ini'))
            command.upgrade(config, 'head')
            engine = create_database_engine(url)
            with engine.connect() as db:
                tables = set(inspect(db).get_table_names())
                assert tables == {'alembic_version','users','auth_sessions','buildings','measurements','predictions'}
                assert all(db.execute(text('SELECT count(*) FROM '+table)).scalar_one()==0 for table in tables-{'alembic_version'})
                assert db.execute(text('PRAGMA foreign_keys')).scalar_one()==1
            factory = sessionmaker(engine, expire_on_commit=False)
            admin_email, admin_password = 'release-admin-'+secrets.token_hex(5)+'@example.com', secrets.token_urlsafe(24)
            with factory() as db:
                admin = create_admin(' '+admin_email.upper()+' ', 'Release verification admin', admin_password, db)
                assert admin.email == admin_email and admin.role == 'ADMIN'
                admin_id = admin.id
                try:
                    create_admin(admin_email, 'Must not overwrite', secrets.token_urlsafe(24), db)
                except ValueError:
                    pass
                else:
                    raise AssertionError('Duplicate bootstrap accepted')
            evidence = {'fresh_empty_schema_no_seeds':True, 'admin_bootstrap_normalized_hidden_prompt_helper':True, 'duplicate_bootstrap_rejected':True}
            c = None
            try:
                backend_cmd = [sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port',str(backend_port),'--log-level','warning']
                backend = spawn(backend_cmd, 'release_backend'); ready(api+'/health', backend)
                front = spawn([shutil.which('npm.cmd'),'run','dev','--','--host','localhost','--port',str(frontend_port),'--strictPort'], 'release_frontend')
                assert 'Checking session' in ready(frontend+'/dashboard', front)
                browser = spawn([os.environ.get('SMARTENERGY_BROWSER','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'), '--headless=new','--disable-gpu','--no-first-run','--disable-background-networking','--remote-debugging-address=127.0.0.1',f'--remote-debugging-port={debug_port}','--remote-allow-origins=http://localhost',f'--user-data-dir={profile}','about:blank'], 'release_browser')
                tabs = json.loads(ready(f'http://127.0.0.1:{debug_port}/json/list', browser))
                c = CDP(next(t for t in tabs if t['type']=='page')['webSocketDebuggerUrl']); c.hold=False
                for method in ['Page.enable','Runtime.enable','Network.enable']: c.call(method)
                c.call('Fetch.enable', {'patterns':[{'urlPattern':'*'}]})
                c.call('Emulation.setDeviceMetricsOverride', {'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False})
                def visit(path):
                    result=c.call('Page.navigate', {'url':frontend+path})
                    if result.get('loaderId'):
                        until=time.monotonic()+55
                        while c.call('Page.getFrameTree')['frameTree']['frame']['loaderId']!=result['loaderId']:
                            if time.monotonic()>until: raise RuntimeError('Document commit timeout')
                            time.sleep(.05)
                def reload():
                    old=c.call('Page.getFrameTree')['frameTree']['frame']['loaderId'];c.call('Page.reload')
                    until=time.monotonic()+55
                    while c.call('Page.getFrameTree')['frameTree']['frame']['loaderId']==old:
                        if time.monotonic()>until: raise RuntimeError('Reload commit timeout')
                        time.sleep(.05)
                def signed_in(): c.wait('!!document.querySelector("main [data-user-dashboard]")')
                def signed_out(): c.wait('location.pathname==="/login"&&!!document.querySelector("input[name=password]")&&document.querySelector("fieldset")?.disabled===false')
                def submit(values):
                    c.wait('document.querySelector("fieldset")?.disabled===false')
                    c.evaluate('(()=>{const values='+json.dumps(values)+';for(const [name,value] of Object.entries(values)){const e=document.querySelector(`form [name="${name}"]`);e.value=value;e.dispatchEvent(new Event("input",{bubbles:true}));}document.querySelector("form").requestSubmit();})()')
                def click(label):
                    expression='Array.from(document.querySelectorAll("button")).find(b=>b.textContent.trim()==='+json.dumps(label)+'&&!b.disabled)'
                    c.wait('!!('+expression+')');c.evaluate(expression+'.click()')
                def call(method,path,body=None):
                    options={'method':method,'credentials':'include','headers':{'Content-Type':'application/json','X-SmartEnergy-CSRF':'1'}}
                    if body is not None: options['body']=json.dumps(body)
                    return c.evaluate('(async()=>{const r=await fetch('+json.dumps(api+path)+','+json.dumps(options)+');return {status:r.status,data:r.status===204?null:await r.json()};})()')
                def login(email,password):
                    call('POST','/auth/logout');visit('/login');signed_out();submit({'email':email,'password':password});signed_in()
                def signup(email,password,name):
                    call('POST','/auth/logout');visit('/signup');c.wait('!!document.querySelector("[name=confirm_password]")');submit({'full_name':name,'email':email,'password':password,'confirm_password':password});signed_in()
                    return call('GET','/auth/me')['data']['id']
                email, password = 'release-user-'+secrets.token_hex(5)+'@example.com', secrets.token_urlsafe(24)
                visit('/login');signed_out()
                uid=signup(email,password,'Release USER A');login(email,password)
                visit('/buildings');c.wait('document.querySelector("h1")?.textContent==="Buildings"');click('Add building');submit({'name':'Release building A','city':'Observed history demo','building_type':'Office'})
                c.wait('document.querySelector("main")?.textContent.includes("Building overview")');bid=int(c.evaluate('location.pathname.split("/").pop()'))
                click('Edit building');submit({'name':'Release building A edited'});c.wait('!document.querySelector("input[name=name]")')
                assert call('GET',f'/buildings/{bid}')['data']['name']=='Release building A edited'
                reload();c.wait('document.querySelector("main")?.textContent.includes("Release building A edited")')
                with (root/'data/raw/energydata_complete.csv').open(newline='',encoding='utf-8') as stream:
                    reader=csv.DictReader(stream);fields=reader.fieldnames;rows=[next(reader) for _ in range(1010)]
                def raw(row): return {'timestamp':row['date'].replace(' ','T'), **{k:float(v) for k,v in row.items() if k not in ('date','rv1','rv2')}}
                click('Add measurement');submit({k:str(v) for k,v in raw(rows[0]).items()});c.wait('!document.querySelector("input[name=Appliances]")')
                assert call('GET',f'/buildings/{bid}/measurements')['data']['total']==1
                assert not call('GET',f'/buildings/{bid}/prediction-readiness')['data']['ready']
                out=io.StringIO();writer=csv.DictWriter(out,fields);writer.writeheader();writer.writerows(rows[1:1009])
                c.evaluate('(()=>{const e=document.querySelector("input[name=file]");const dt=new DataTransfer();dt.items.add(new File(['+json.dumps(out.getvalue())+'],"release-history.csv",{type:"text/csv"}));e.files=dt.files;e.closest("form").requestSubmit();})()')
                c.wait('document.querySelector("main")?.textContent.includes("Imported 1008 of 1008 rows")')
                assert call('GET',f'/buildings/{bid}/measurements')['data']['total']==1009
                # Duplicate API and invalid CSV leave the persisted count unchanged.
                assert call('POST',f'/buildings/{bid}/measurements',raw(rows[0]))['status']==409
                invalid='date,Appliances\n2016-01-01 00:00:00,invalid\n'
                result=c.evaluate('(async()=>{const f=new FormData();f.append("file",new Blob(['+json.dumps(invalid)+'],{type:"text/csv"}),"invalid.csv");const r=await fetch('+json.dumps(api+f'/buildings/{bid}/measurements/import')+',{method:"POST",credentials:"include",headers:{"X-SmartEnergy-CSRF":"1"},body:f});return r.status;})()')
                assert result==422 and call('GET',f'/buildings/{bid}/measurements')['data']['total']==1009
                def detail_state(code):
                    visit(f'/buildings/{bid}');c.wait('document.querySelector("[data-readiness-state]")?.getAttribute("data-readiness-state")==='+json.dumps(code))
                detail_state('READY')
                measurement=call('GET',f'/buildings/{bid}/measurements?limit=100')['data']['items'][50]
                assert call('DELETE',f'/buildings/{bid}/measurements/{measurement["id"]}')['status']==204
                assert not call('GET',f'/buildings/{bid}/prediction-readiness')['data']['ready']
                detail_state('LATEST_WINDOW_HAS_GAPS')
                restored={k:v for k,v in measurement.items() if k not in ('id','building_id')}
                assert call('POST',f'/buildings/{bid}/measurements',restored)['status']==201
                detail_state('READY');click('Predict next 10 minutes');c.wait('document.querySelector("[data-prediction-count]")?.getAttribute("data-prediction-count")==="1"')
                first=call('GET',f'/buildings/{bid}/predictions')['data']['items'][0]
                assert first['unit']=='Wh' and first['horizon_minutes']==10 and first['recommendation']
                assert call('POST',f'/buildings/{bid}/predictions')['data']['reused_existing_prediction']
                assert call('GET',f'/buildings/{bid}/predictions')['data']['total']==1
                assert call('POST',f'/buildings/{bid}/measurements',raw(rows[1009]))['status']==201
                assert call('GET',f'/buildings/{bid}/dashboard-summary')['data']['current_prediction'] is None
                detail_state('READY');click('Predict next 10 minutes');c.wait('document.querySelector("[data-prediction-count]")?.getAttribute("data-prediction-count")==="2"')
                newest=call('GET',f'/buildings/{bid}/dashboard-summary')['data']['current_prediction'];assert newest and newest['id']!=first['id']
                second=call('POST','/buildings',{'name':'Release building B'})['data']['id']
                for selected,code in [(second,'NO_MEASUREMENTS'),(bid,'READY')]:
                    visit(f'/dashboard?building={selected}');c.wait('document.querySelector("[data-dashboard-building]")?.getAttribute("data-dashboard-building")==='+json.dumps(str(selected)))
                    c.wait('document.querySelector("[data-dashboard-readiness]")?.getAttribute("data-dashboard-readiness")==='+json.dumps(code))
                    assert c.evaluate('document.querySelectorAll("#building-selector option").length')==3
                c.wait('!!document.querySelector("[data-current-recommendation]")')
                cookie=next(x['value'] for x in c.call('Network.getCookies',{'urls':[api]})['cookies'] if x['name']=='smartenergy_session')
                other_email,other_password='release-other-'+secrets.token_hex(5)+'@example.com',secrets.token_urlsafe(24)
                other_id=signup(other_email,other_password,'Release USER B')
                assert call('GET','/buildings')['data']['buildings']==[]
                for suffix in ['', '/measurements','/prediction-readiness','/dashboard-summary','/predictions']:
                    assert call('GET',f'/buildings/{bid}'+suffix)['status']==404
                visit(f'/buildings/{bid}');c.wait('document.querySelector("main")?.textContent.includes("Building not found")')
                login(admin_email,admin_password)
                for path,selector in [('/admin','[data-admin-overview]'),('/admin/users','[data-admin-user]'),(f'/admin/users?user={uid}','[data-admin-user-detail]'),(f'/admin/buildings?building={bid}','[data-admin-building-detail]')]:
                    visit(path);c.wait('!!document.querySelector('+json.dumps(selector)+')')
                overview=call('GET','/admin/overview')['data'];assert overview['total_measurements']==1010 and overview['total_predictions']==2 and overview['total_users']==3
                assert call('GET',f'/admin/users/{other_id}')['status']==200
                assert call('GET',f'/buildings/{bid}')['status']==404
                for width in [1440,390]:
                    c.call('Emulation.setDeviceMetricsOverride',{'width':width,'height':1000,'deviceScaleFactor':1,'mobile':width==390})
                    for path,selector in [('/admin','[data-admin-overview]'),('/admin/users','[data-admin-user]'),('/admin/buildings','[data-admin-building]')]:
                        visit(path);c.wait('!!document.querySelector('+json.dumps(selector)+')');assert c.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                        assert c.evaluate('!!document.querySelector("h1")&&Array.from(document.querySelectorAll("main input,main select")).every(e=>e.labels?.length||e.getAttribute("aria-label"))')
                    visit(f'/admin/users?user={uid}');c.wait('!!document.querySelector("[data-admin-user-detail]")');click('Deactivate account');c.wait('!!document.querySelector("[role=alertdialog]")')
                    assert c.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                    c.screenshot(f'phase30_admin_confirmation_{width}.png');click('Cancel deactivation')
                click('Deactivate account');click('Confirm deactivation');c.wait('Array.from(document.querySelectorAll("button")).some(b=>b.textContent.trim()==="Activate account"&&!b.disabled)')
                request=urllib.request.Request(api+'/auth/me',headers={'Cookie':'smartenergy_session='+cookie})
                try: urllib.request.urlopen(request)
                except urllib.error.HTTPError as error: assert error.code==401
                else: raise AssertionError('Revoked session accepted')
                assert call('POST','/auth/login',{'email':email,'password':password})['status']==401
                assert call('GET',f'/admin/users/{uid}')['data']['measurement_count']==1010
                click('Activate account');c.wait('Array.from(document.querySelectorAll("button")).some(b=>b.textContent.trim()==="Deactivate account"&&!b.disabled)')
                assert call('PATCH',f'/admin/users/{admin_id}/status',{'is_active':False})['status']==409
                login(email,password)
                def pause(): stop(backend)
                def resume():
                    nonlocal backend
                    backend=spawn(backend_cmd,'release_restart');ready(api+'/health',backend)
                pause();resume();visit(f'/dashboard?building={bid}');c.wait('!!document.querySelector("[data-current-recommendation]")')
                assert call('GET',f'/buildings/{bid}/dashboard-summary')['data']['current_prediction']['id']==newest['id']
                evidence.update(user_signup_logout_login_building_create_edit=True, manual_and_CSV_1009_persisted=True, invalid_import_atomic_duplicate_rejected=True, readiness_insufficient_ready_delete_restore=True, forecast_recommendation_Wh_10_minutes=True, identical_input_reused_and_new_origin_historical=True, second_owned_building_and_selector_isolated=True, USER_B_foreign_API_and_deep_link_denied=True, ADMIN_overview_users_buildings_predictions_and_status=True, deactivation_revokes_session_retains_data_reactivation_fresh_login=True, self_deactivation_denied=True, backend_restart_session_and_domain_persistence=True, admin_confirmation_desktop_mobile_accessibility_sanity=True)
                print('Release journey: fresh USER A/B, manual/CSV, readiness delete/restore, two forecasts, admin revocation/reactivation and restart passed',flush=True)
                # Existing supported-only journey adds all actor/routes, responsive forms,
                # keyboard, two real tabs, actual offline/Retry and XSS checks.
                from verify_fullstack_browser import scenario
                evidence['route_offline_responsive_accessibility_journey']=scenario(c=c,visit=visit,submit=submit,signed_in=signed_in,signed_out=signed_out,api=api,frontend=frontend,user_email=email,user_password=password,admin_email=admin_email,admin_password=admin_password,reload=reload,pause=pause,resume=resume)
                with urllib.request.urlopen(api+'/openapi.json') as response: document=json.load(response)
                operations=[{'method':method.upper(),'path':path} for path,item in document['paths'].items() for method in item if method in ('get','post','patch','delete','put')]
                forbidden={'password_hash','token_hash','feature_snapshot_json'}
                for name,schema in document['components']['schemas'].items(): assert not forbidden.intersection(schema.get('properties',{})),name
                with urllib.request.urlopen(api+'/docs') as response: assert response.status==200
                evidence.update(passed=True,OpenAPI_live_operation_inventory=operations,OpenAPI_sensitive_internal_fields_absent=True,Swagger_HTTP_200=True,runtime_errors=c.errors,cors_errors=c.cors)
                assert not c.errors and not c.cors
                for path in g.glob('phase30_*.log'):
                    contents=path.read_text(encoding='utf-8',errors='replace')
                    assert all(secret not in contents for secret in [password,other_password,admin_password,cookie])
                evidence['runtime_credentials_absent_from_QA_logs']=True
            finally:
                if c: c.ws.close()
                for process in reversed(processes): stop(process)
                for log in logs: log.close()
                engine.dispose()
    evidence.update(temporary_DB_profile_processes_cleaned=True,no_domain_DB_manipulation_after_bootstrap=True)
    (g/'phase30_release_browser_evidence.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(evidence,indent=2))


if __name__=='__main__':
    main()
