"""Optional Windows Edge live Phase22 QA. Temporary DB/accounts, no developer data.

Run with project .venv. Reuses existing CDP helper definitions without running
its historical unauthenticated scenario. Ports are chosen dynamically; all own
processes and temporary DB/profile are cleaned. Evidence remains ignored.
"""
from pathlib import Path
import ast, base64, contextlib, hashlib, json, os, shutil, socket, subprocess, sys, tempfile, time
import urllib.request
import websocket

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
g = root / 'ml/results/generated'
g.mkdir(exist_ok=True)
flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
processes, logs = [], []


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def main():
    import secrets
    backend_port, frontend_port, debug_port = free_port(), free_port(), free_port()
    api = f'http://localhost:{backend_port}'
    frontend = f'http://localhost:{frontend_port}'
    original = (root / 'tests/verify_dashboard_browser.py').read_text(encoding='utf-8')
    original = original.replace('8000',str(backend_port)).replace('5173',str(frontend_port)).replace('phase17_', 'phase23_' if '--buildings' in sys.argv else 'phase22_')
    original = original.replace(f'127.0.0.1:{backend_port}', f'localhost:{backend_port}')
    tree = ast.parse(original)
    helpers = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in ('CDP','spawn','stop','ready')]
    assert len(helpers) == 4
    exec(compile(ast.Module(body=helpers,type_ignores=[]),'<existing-browser-helpers>','exec'),globals())
    import secrets
    from io import StringIO
    from unittest.mock import patch
    with tempfile.TemporaryDirectory(prefix='smartenergy-auth-qa-') as directory:
        url = 'sqlite:///' + (Path(directory) / 'auth.db').as_posix()
        environment = {'DATABASE_URL':url,'SMARTENERGY_CORS_ORIGINS':frontend,
                       'VITE_API_BASE_URL':api,'SMARTENERGY_COOKIE_SECURE':'false'}
        with patch.dict(os.environ, environment):
            from alembic import command
            from alembic.config import Config
            from sqlalchemy import select
            from sqlalchemy.orm import sessionmaker
            from backend.database import create_database_engine
            from backend.db_models import AuthSession, User, utc_now
            from backend.auth import COOKIE_NAME, token_digest
            from scripts.create_admin import create_admin
            command.upgrade(Config(str(root / 'alembic.ini')), 'head')
            engine = create_database_engine(url)
            factory = sessionmaker(engine, expire_on_commit=False)
            email = 'browser-' + secrets.token_hex(8) + '@example.com'
            admin_email = 'administrator-' + secrets.token_hex(8) + '@example.com'
            password, admin_password = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
            with factory() as db:
                create_admin(admin_email, 'Bootstrap verification admin', admin_password, db)
            with tempfile.TemporaryDirectory(prefix='phase22-profile-',dir=g) as profile:
                assert Path(profile).resolve().is_relative_to(g.resolve())
                try:
                    backend_cmd=[sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port',str(backend_port),'--log-level','warning']
                    backend=spawn(backend_cmd,'backend')
                    ready(api+'/health',backend)
                    front=spawn([shutil.which('npm.cmd'),'run','dev','--','--host','localhost','--port',str(frontend_port),'--strictPort'],'frontend')
                    html=ready(frontend+'/dashboard',front)
                    assert 'Checking session' in html and 'Held-out test MAE' not in html
                    browser=spawn([os.environ.get('SMARTENERGY_BROWSER','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'),
                        '--headless=new','--disable-gpu','--no-first-run','--disable-background-networking',
                        '--remote-debugging-address=127.0.0.1',f'--remote-debugging-port={debug_port}',
                        '--remote-allow-origins=http://localhost',f'--user-data-dir={profile}','about:blank'],'browser')
                    tabs=json.loads(ready(f'http://127.0.0.1:{debug_port}/json/list',browser))
                    c=CDP(next(t for t in tabs if t['type']=='page')['webSocketDebuggerUrl'])
                    c.hold=False
                    for method in ('Page.enable','Runtime.enable','Network.enable'):c.call(method)
                    c.call('Fetch.enable',{'patterns':[{'urlPattern':'*'}]})
                    c.call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False})
                    def wait_document(loader_id, changed=False):
                        deadline=time.monotonic()+55
                        while time.monotonic()<deadline:
                            current=c.call('Page.getFrameTree')['frameTree']['frame']['loaderId']
                            if (current != loader_id) if changed else (current == loader_id):
                                return
                            time.sleep(.05)
                        raise RuntimeError('Browser document commit timeout')
                    def visit(path):
                        result=c.call('Page.navigate',{'url':frontend+path})
                        if result.get('loaderId'):wait_document(result['loaderId'])
                    def reload():
                        old=c.call('Page.getFrameTree')['frameTree']['frame']['loaderId']
                        c.call('Page.reload');wait_document(old,changed=True)
                    def signed_in():
                        c.wait('document.querySelector("main")?.textContent.includes("Tuned XGBoost") && document.querySelectorAll(".recharts-bar-rectangle").length >= 16')
                    def signed_out():
                        c.wait('location.pathname === "/login" && !!document.querySelector("input[name=password]") && document.querySelector("fieldset")?.disabled === false')
                    def submit(values):
                        c.wait('document.querySelector("fieldset")?.disabled === false')
                        c.evaluate('(() => { const values='+json.dumps(values)+'; for (const [name,value] of Object.entries(values)) { const input=document.querySelector(`[name="${name}"]`); input.value=value; input.dispatchEvent(new Event("input",{bubbles:true})); } document.querySelector("form").requestSubmit(); return true; })()')
                    def me():
                        return c.evaluate('(async()=>{const r=await fetch('+json.dumps(api+'/auth/me')+', {credentials:"include"});return {status:r.status,body:await r.json()};})()')
                    protected=['/dashboard','/predictions','/recommendations','/data','/settings','/buildings/','/buildings/ubt-campus-a','/admin/','/admin/users','/admin/buildings']
                    for path in protected:
                        visit(path);signed_out()
                        destination = c.evaluate('new URLSearchParams(location.search).get("next")')
                        assert destination and destination.rstrip('/') == path.rstrip('/'), {'route':path,'destination':destination}
                    print('Auth QA: protected redirects preserve intended destination',flush=True)
                    visit('/dashboard');signed_out()
                    c.evaluate('localStorage.setItem("sea-session", JSON.stringify({name:"Forged",email:"forged@example.com",role:"Platform Admin",onboarded:true}))')
                    visit('/dashboard');signed_out()
                    assert c.evaluate('localStorage.getItem("sea-session")') is None
                    for path in ('/','/about','/contact','/forgot-password','/reset-password','/verify-email','/onboarding'):
                        visit(path);c.wait('!!document.querySelector("h1")')
                    visit('/signup');c.wait('!!document.querySelector("input[name=confirm_password]") && document.querySelector("fieldset")?.disabled === false')
                    submit({'full_name':'Browser verification user','email':email,'password':password,'confirm_password':password+'mismatch'})
                    c.wait('document.querySelector("[role=alert]")?.textContent.includes("Passwords do not match")')
                    submit({'full_name':'Browser verification user','email':email,'password':password,'confirm_password':password})
                    signed_in()
                    assert me()['status']==200
                    cookies=c.call('Network.getCookies',{'urls':[api]})['cookies']
                    cookie=next(item for item in cookies if item['name']==COOKIE_NAME)
                    assert cookie['httpOnly'] and cookie['sameSite']=='Lax' and not cookie['secure']
                    assert COOKIE_NAME not in c.evaluate('document.cookie')
                    with factory() as db:
                        user=db.scalar(select(User).where(User.email==email))
                        session=db.scalar(select(AuthSession).where(AuthSession.user_id==user.id))
                        assert session.token_hash==token_digest(cookie['value']) and session.token_hash!=cookie['value']
                    assert not c.evaluate('Array.from(document.links).some(a => a.getAttribute("href")?.startsWith("/admin"))')
                    reload();signed_in()
                    print('Auth QA: signup, HttpOnly cookie, database hash and refresh passed',flush=True)
                    # Persistence also survives backend restart, not just React memory.
                    stop(backend);backend=spawn(backend_cmd,'backend_restart');ready(api+'/health',backend)
                    reload();signed_in()
                    for width in (1440,390):
                        c.call('Emulation.setDeviceMetricsOverride',{'width':width,'height':1000,'deviceScaleFactor':1,'mobile':width==390})
                        assert c.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
                        c.screenshot(f'phase22_dashboard_{width}.png')
                    c.call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False})
                    for path in ('/admin','/admin/users','/admin/buildings'):
                        visit(path);c.wait('document.querySelector("h1")?.textContent === "Administrator access required"')
                        assert 'Cross-tenant inventory' not in c.text()
                    visit('/dashboard');signed_in()
                    c.evaluate('Array.from(document.querySelectorAll("button")).find(b => b.getAttribute("aria-label") === "Sign out").click()');signed_out()
                    reload();signed_out();assert me()['status']==401
                    visit('/login?next=%2Fsettings');signed_out()
                    submit({'email':email,'password':password+'wrong'})
                    c.wait('document.querySelector("[role=alert]")?.textContent.includes("Invalid email or password")')
                    submit({'email':email.upper(),'password':password})
                    c.wait('location.pathname === "/settings" && document.querySelector("main")?.textContent.includes("Browser verification user")')
                    with factory() as db:
                        user=db.scalar(select(User).where(User.email==email));user.is_active=False;db.commit()
                    reload();signed_out()
                    submit({'email':email,'password':password})
                    c.wait('document.querySelector("[role=alert]")?.textContent.includes("account inactive")')
                    with factory() as db:
                        user=db.scalar(select(User).where(User.email==email));user.is_active=True;db.commit()
                    submit({'email':email,'password':password})
                    c.wait('location.pathname === "/settings" && document.querySelector("main")?.textContent.includes("Browser verification user")')
                    print('Auth QA: logout, normalized re-login and inactive/reactivated session flow passed',flush=True)
                    with factory() as db:
                        from datetime import timedelta
                        user=db.scalar(select(User).where(User.email==email))
                        for session in db.scalars(select(AuthSession).where(AuthSession.user_id==user.id)):
                            session.created_at=utc_now()-timedelta(hours=2);session.expires_at=utc_now()-timedelta(hours=1)
                        db.commit()
                    reload();signed_out()
                    submit({'email':admin_email,'password':admin_password})
                    c.wait('location.pathname === "/settings" && document.body.textContent.includes("Bootstrap verification admin")')
                    for path in ('/admin/','/admin/users','/admin/buildings'):
                        visit(path);c.wait('document.querySelector("main")?.textContent.includes("No verified operational readings")')
                        assert c.evaluate('Array.from(document.links).some(a => a.getAttribute("href") === "/admin/users")')
                    visit('/dashboard');signed_in()
                    print('Auth QA: expiry and bootstrap ADMIN shell passed',flush=True)
                    building_verification = None
                    if '--buildings' in sys.argv:
                        from verify_buildings_browser import scenario
                        def restart_for_buildings():
                            nonlocal backend
                            stop(backend);backend=spawn(backend_cmd,'buildings_restart');ready(api+'/health',backend)
                        building_verification = scenario(c=c, visit=visit, submit=submit, signed_out=signed_out,
                            signed_in=signed_in, api=api, user_email=email, user_password=password,
                            admin_email=admin_email, admin_password=admin_password, restart=restart_for_buildings,reload=reload)
                    # Public research APIs still operate without cookies.
                    statuses={}
                    for path in ('/','/health','/model/info','/recommendations/thresholds','/analysis/model-comparison','/analysis/feature-importance','/docs','/openapi.json'):
                        with urllib.request.urlopen(api+path) as response:statuses[path]=response.status
                    import pandas as pd
                    from ml.src.model_inference import load_final_model,predict_next_appliances
                    from ml.src.recommendation_engine import predict_and_recommend
                    bundle=load_final_model()
                    frame=pd.read_csv(root/'data/processed/energy_train.csv',nrows=1,float_precision='round_trip')[bundle[1]['ordered_feature_names']]
                    body=json.dumps({'features':frame.iloc[0].to_dict()}).encode()
                    responses={}
                    for path in ('/forecast','/forecast/recommendation'):
                        request=urllib.request.Request(api+path,data=body,headers={'Content-Type':'application/json'})
                        with urllib.request.urlopen(request) as response:responses[path]=json.load(response)
                    assert responses['/forecast']['prediction_wh']==float(predict_next_appliances(frame,bundle).iloc[0])
                    assert responses['/forecast/recommendation']==predict_and_recommend(frame,model_bundle=bundle)[0]
                    assert not c.cors,c.cors
                    assert not c.errors,c.errors
                    evidence={'passed':True,'browser':'Installed Edge/CDP','frontend_origin':frontend,'backend_origin':api,
                        'database':'Disposable migrated SQLite; no developer DB used','credentials':'Generated only in runtime memory; never emitted or committed',
                        'SSR_does_not_render_authenticated_content':True,'unauthenticated_protected_routes':protected,
                        'forged_localstorage_ignored':True,'signup_form_password_confirmation':True,'signup_USER':True,
                        'cookie_flags':{'name':COOKIE_NAME,'httpOnly':True,'sameSite':'Lax','secure':False},'cookie_hidden_from_document_cookie':True,
                        'token_hash_only_in_database':True,'refresh_persists_session':True,'backend_restart_persists_session':True,
                        'logout_and_refresh_unauthenticated':True,'invalid_login_error':True,'normalized_login':True,'intended_destination_settings':True,
                        'inactive_login_and_session_blocked':True,'expired_session_blocked':True,'USER_admin_routes_forbidden':True,
                        'bootstrap_ADMIN_admin_shell_allowed':True,'no_admin_management_implemented':True,
                        'credentialed_CORS_passed':True,'cors_errors':c.cors,'runtime_errors':c.errors,
                        'responsive_widths':[1440,390],'public_research_GET_statuses':statuses,'public_forecast_helper_equivalence':True,
                        'public_recommendation_helper_equivalence':True,'dashboard_real_research_charts':True,'verification_processes_stopped':False}
                    if building_verification is not None:
                        evidence['building_management'] = building_verification
                    c.ws.close()
                finally:
                    for process in reversed(processes):stop(process)
                    for log in logs:log.close()
                    engine.dispose()
            evidence['verification_processes_stopped']=True
        evidence['temporary_database_and_profile_removed']=True
    (g/('phase23_browser_evidence.json' if '--buildings' in sys.argv else 'phase22_browser_evidence.json')).write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(evidence,indent=2))


if __name__ == '__main__':
    main()
