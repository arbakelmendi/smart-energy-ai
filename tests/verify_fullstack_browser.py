"""Phase29 real routes, XSS text, cancellation/offline, multi-tab and accessible flows."""
import csv,io,json,secrets,sys,urllib.request
from pathlib import Path


def scenario(*,c,visit,submit,signed_in,signed_out,api,frontend,user_email,user_password,admin_email,admin_password,reload,pause,resume):
    def call(method,path,body=None):
        options={'method':method,'credentials':'include','headers':{'Content-Type':'application/json','X-SmartEnergy-CSRF':'1'}}
        if body is not None:options['body']=json.dumps(body)
        return c.evaluate('(async()=>{const r=await fetch('+json.dumps(api+path)+','+json.dumps(options)+');return {status:r.status,data:r.status===204?null:await r.json()};})()')
    def click(text):
        c.wait('Array.from(document.querySelectorAll("button")).some(b=>b.textContent.trim()==='+json.dumps(text)+'&&!b.disabled)')
        c.evaluate('Array.from(document.querySelectorAll("button")).find(b=>b.textContent.trim()==='+json.dumps(text)+').click()')
    def link(text):
        c.wait('Array.from(document.querySelectorAll("main a")).some(a=>a.textContent.trim()==='+json.dumps(text)+')')
        c.evaluate('Array.from(document.querySelectorAll("main a")).find(a=>a.textContent.trim()==='+json.dumps(text)+').click()')
    def login(email,password):
        call('POST','/auth/logout');visit('/login');signed_out();submit({'email':email,'password':password});signed_in()
    def dashboard(bid):c.wait('document.querySelector("[data-dashboard-building]")?.getAttribute("data-dashboard-building")==='+json.dumps(str(bid)))
    # All domain data in this additional complete journey is created by supported UI/APIs.
    call('POST','/auth/logout');email='hardening-'+secrets.token_hex(8)+'@example.com';password=secrets.token_urlsafe(24)
    marker='<img src=x onerror="window.__qaInjected=1">'
    visit('/signup');c.wait('!!document.querySelector("[name=confirm_password]")');submit({'full_name':marker,'email':email,'password':password,'confirm_password':password});signed_in()
    login(email,password)
    visit('/onboarding');c.wait('document.querySelector("h1")?.textContent==="Building setup"');c.evaluate('Array.from(document.links).find(a=>a.textContent.trim()==="Open Buildings").click()');c.wait('document.querySelector("h1")?.textContent==="Buildings"');click('Add building');submit({'name':marker,'building_type':'Office','city':marker,'description':marker})
    c.wait('document.querySelector("main")?.textContent.includes("Building overview")');bid=int(c.evaluate('location.pathname.split("/").pop()'))
    c.wait('document.querySelector("main")?.textContent.includes('+json.dumps(marker)+')')
    assert call('GET',f'/buildings/{bid}')['data']['description']==marker
    assert c.evaluate('window.__qaInjected===undefined&&!document.querySelector("main img[src=x]")')
    with (Path(__file__).resolve().parents[1]/'data/raw/energydata_complete.csv').open(newline='',encoding='utf-8') as stream:
        reader=csv.DictReader(stream);fields=reader.fieldnames;rows=[next(reader) for _ in range(1009)]
    # Manual first observation followed by non-overlapping CSV, no fixture DB writes.
    click('Add measurement');body={key:str(float(value)) for key,value in rows[0].items() if key not in ['date','rv1','rv2']};body['timestamp']=rows[0]['date'].replace(' ','T');submit(body)
    c.wait('!document.querySelector("input[name=Appliances]")')
    out=io.StringIO();writer=csv.DictWriter(out,fields);writer.writeheader();writer.writerows(rows[1:])
    c.evaluate('(()=>{const input=document.querySelector("input[name=file]");const dt=new DataTransfer();dt.items.add(new File(['+json.dumps(out.getvalue())+'],"history.csv",{type:"text/csv"}));input.files=dt.files;input.closest("form").requestSubmit();})()')
    c.wait('document.querySelector("main")?.textContent.includes("Imported 1008 of 1008 rows")');link('Open building dashboard');dashboard(bid)
    c.wait('document.querySelector("[data-dashboard-readiness]")?.getAttribute("data-dashboard-readiness")==="READY"');click('Predict next 10 minutes');c.wait('!!document.querySelector("[data-current-recommendation]")')
    prediction=call('GET',f'/buildings/{bid}/dashboard-summary')['data']['current_prediction'];assert prediction
    reload();dashboard(bid);c.wait('!!document.querySelector("[data-current-recommendation]")')
    for path in [f'/predictions?building={bid}',f'/recommendations?building={bid}']:
        visit(path);c.wait('!!document.querySelector("[data-history-total]")');reload();c.wait('!!document.querySelector("[data-history-total]")')
    # A second owned building is created by API; dashboard selection must isolate it.
    second_building=call('POST','/buildings',{'name':'Hardening second building'})['data']['id']
    visit(f'/dashboard?building={second_building}');dashboard(second_building);c.wait('document.querySelector("[data-dashboard-readiness]")?.getAttribute("data-dashboard-readiness")==="NO_MEASUREMENTS"')
    visit(f'/dashboard?building={bid}');dashboard(bid)
    # Genuine backend shutdown with the same browser open, then request-driven recovery.
    pause()
    try:
        click('Refresh stored state');c.wait('document.querySelector("main")?.textContent.includes("Dashboard unavailable")||document.querySelector("h1")?.textContent==="Unable to verify session"')
        assert not c.evaluate('!!document.querySelector("[data-current-recommendation]")')
        before=c.evaluate('performance.getEntriesByType("resource").filter(e=>e.name.startsWith('+json.dumps(api)+')).length')
        c.evaluate('new Promise(resolve=>setTimeout(resolve,1500))')
        after=c.evaluate('performance.getEntriesByType("resource").filter(e=>e.name.startsWith('+json.dumps(api)+')).length');assert after-before<10
    finally:resume()
    c.evaluate('Array.from(document.querySelectorAll("button")).find(b=>["Retry dashboard","Retry session"].includes(b.textContent.trim()))?.click()')
    dashboard(bid);c.wait('!!document.querySelector("[data-current-recommendation]")');assert call('GET',f'/buildings/{bid}/dashboard-summary')['data']['current_prediction']['id']==prediction['id']
    # Same cookie/session in a second real tab: logout then its next protected action fails.
    target=c.call('Target.createTarget',{'url':'about:blank'})['targetId'];other=None
    try:
        port=c.ws.sock.getpeername()[1]
        tabs=json.loads(urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list').read())
        other=type(c)(next(tab for tab in tabs if tab['id']==target)['webSocketDebuggerUrl']);other.hold=False
        for method in ['Page.enable','Runtime.enable','Network.enable']:other.call(method)
        other.call('Fetch.enable',{'patterns':[{'urlPattern':'*'}]});other.call('Page.navigate',{'url':frontend+f'/dashboard?building={bid}'})
        other.wait('!!document.querySelector("[data-current-recommendation]")')
        c.evaluate('Array.from(document.querySelectorAll("button")).find(b=>b.getAttribute("aria-label")==="Sign out").click()');signed_out()
        other.evaluate('Array.from(document.querySelectorAll("button")).find(b=>b.textContent.trim()==="Refresh stored state").click()')
        other.wait('location.pathname==="/login"&&!!document.querySelector("input[name=password]")')
        assert not other.errors and not other.cors
    finally:
        if other:other.ws.close()
        c.call('Target.closeTarget',{'targetId':target})
    # All existing route files across all three actor classes; no new routes.
    public=['/','/about','/contact','/login','/signup','/forgot-password','/reset-password','/verify-email','/onboarding']
    operational=['/dashboard','/buildings',f'/buildings/{bid}','/data',f'/predictions?building={bid}',f'/recommendations?building={bid}','/settings']
    administrative=['/admin','/admin/users','/admin/buildings']
    audited={}
    for actor in ['ANONYMOUS','USER','ADMIN']:
        if actor=='USER':login(email,password)
        if actor=='ADMIN':login(admin_email,admin_password)
        audited[actor]=[]
        for path in public+operational+administrative:
            print('Route QA: '+actor+' '+path,flush=True)
            visit(path)
            if actor=='ANONYMOUS' and path in operational+administrative:signed_out()
            elif actor=='USER' and path in administrative:c.wait('document.querySelector("h1")?.textContent==="Administrator access required"')
            else:
                try:c.wait('!!document.querySelector("h1")&&document.querySelector("h1").textContent!=="Checking session"')
                except Exception:
                    print(json.dumps({'actor':actor,'route':path,'location':c.evaluate('location.href'),'headings':c.evaluate('Array.from(document.querySelectorAll("h1")).map(e=>e.textContent)'),'body_preview':c.evaluate('document.body.textContent.slice(0,500)')}),flush=True)
                    c.screenshot('phase29_route_failure.png');raise
            assert c.evaluate('document.querySelector("h1")?.textContent.length>0')
            assert c.evaluate('!document.body.textContent.includes("Something went wrong")')
            audited[actor].append(path)
        if actor=='ADMIN':
            visit('/admin');c.wait('document.querySelectorAll("[data-admin-count]").length===8');reload();c.wait('document.querySelectorAll("[data-admin-count]").length===8')
    # Text injection check on the cross-owner detail as well as ordinary pages.
    visit('/admin/buildings?building='+str(bid));c.wait('!!document.querySelector("[data-admin-building-detail]")');assert marker in c.text();assert c.evaluate('window.__qaInjected===undefined&&!document.querySelector("main img[src=x]")')
    # USER B attacks every original domain view and all admin endpoints.
    login(user_email,user_password)
    for suffix in ['', '/measurements','/prediction-readiness','/predictions','/dashboard-summary']:
        assert call('GET',f'/buildings/{bid}'+suffix)['status']==404
    for path in ['/admin/overview','/admin/users','/admin/buildings','/admin/predictions']:assert call('GET',path)['status']==403
    # Keyboard and label sanity for representative real forms and mobile navigation.
    login(email,password)
    for width in [1440,390]:
        c.call('Emulation.setDeviceMetricsOverride',{'width':width,'height':1000,'deviceScaleFactor':1,'mobile':width==390})
        for path in [f'/dashboard?building={bid}','/buildings',f'/buildings/{bid}']:
            visit(path);c.wait('document.querySelector("h1")?.textContent!=="Checking session"&&!!document.querySelector("main")')
            if 'dashboard' in path:dashboard(bid)
            elif path==f'/buildings/{bid}':c.wait('document.querySelector("main")?.textContent.includes("Building overview")')
            assert c.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            if path==f'/buildings/{bid}':
                click('Add measurement');c.wait('!!document.querySelector("input[name=Appliances]")')
                assert c.evaluate('Array.from(document.querySelectorAll("main input,main select,main textarea")).every(e=>e.labels?.length||e.getAttribute("aria-label"))')
                assert c.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                c.screenshot(f'phase29_measurement_form_{width}.png');click('Cancel measurement')
        if width==390:
            c.evaluate('Array.from(document.querySelectorAll("button")).find(b=>b.getAttribute("aria-label")==="Open navigation").click()');c.wait('Array.from(document.querySelectorAll("button")).some(b=>b.getAttribute("aria-label")==="Close navigation")')
            c.evaluate('Array.from(document.querySelectorAll("button")).find(b=>b.getAttribute("aria-label")==="Close navigation").click()')
        visit('/buildings');click('Add building')
        assert c.evaluate('Array.from(document.querySelectorAll("main input,main select,main textarea")).every(e=>e.labels?.length||e.getAttribute("aria-label"))')
        c.evaluate('document.querySelector("input[name=name]").focus()');c.call('Input.dispatchKeyEvent',{'type':'keyDown','key':'Tab','code':'Tab','windowsVirtualKeyCode':9});c.call('Input.dispatchKeyEvent',{'type':'keyUp','key':'Tab','code':'Tab','windowsVirtualKeyCode':9});assert c.evaluate('document.activeElement?.name==="building_type"')
        c.screenshot(f'phase29_building_form_{width}.png')
    call('POST','/auth/logout')
    for width in [1440,390]:
        c.call('Emulation.setDeviceMetricsOverride',{'width':width,'height':1000,'deviceScaleFactor':1,'mobile':width==390})
        for path in ['/login','/signup']:
            visit(path);c.wait('!!document.querySelector("input[name=password]")&&!document.querySelector("fieldset").disabled')
            assert c.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            assert c.evaluate('document.querySelectorAll("form input").length>0&&Array.from(document.querySelectorAll("form input")).every(e=>e.labels?.length||e.getAttribute("aria-label"))')
            c.screenshot(f'phase29_{path[1:]}_{width}.png')
    c.call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False})
    login(admin_email,admin_password)
    def inspected_headers(url):
        with urllib.request.urlopen(url) as response:
            return {key:response.headers.get(key) for key in ['X-Content-Type-Options','Referrer-Policy','X-Frame-Options','Content-Security-Policy']}
    headers={'API':inspected_headers(api+'/health'),'frontend_SSR':inspected_headers(frontend+'/')}
    tokens=[item['value'] for item in c.call('Network.getCookies',{'urls':[api]})['cookies'] if item['name']=='smartenergy_session']
    logs=list((Path(__file__).resolve().parents[1]/'ml/results/generated').glob('phase29_*.log'))
    for path in logs:
        contents=path.read_text(encoding='utf-8',errors='replace')
        assert all(secret not in contents for secret in [password,user_password,admin_password,*tokens])
    print('Hardening QA: pure UI/API journey, backend offline/recovery, second-tab revocation, all routes by actor, XSS text, IDOR, refresh/restart and keyboard/label checks passed',flush=True)
    return {'passed':True,'pure_supported_UI_API_journey_no_manual_domain_DB_writes':True,'manual_plus_CSV_1009_history':True,'persisted_prediction_recommendation':True,'second_building_isolated':True,'backend_actually_stopped_and_restarted':True,'offline_no_current_forecast_and_no_immediate_request_loop':True,'Retry_restores_same_persisted_forecast':True,'two_real_tabs_logout_next_action_denied':True,'routes_by_actor':audited,'cross_user_and_admin_attack_denied':True,'XSS_full_name_building_city_description_render_as_text':True,'keyboard_Tab_form_labels_mobile_close_button':True,'responsive_widths':[1440,390],'admin_and_ledger_refresh_persistence':True,'security_headers_observed':headers,'runtime_password_and_sample_session_not_in_QA_logs':True}

def scenario_smoke(*,c,visit,submit,signed_in,signed_out,api,admin_email,admin_password):
    def call(method,path,body=None):
        options={'method':method,'credentials':'include','headers':{'Content-Type':'application/json','X-SmartEnergy-CSRF':'1'}}
        if body is not None:options['body']=json.dumps(body)
        return c.evaluate('(async()=>{const r=await fetch('+json.dumps(api+path)+','+json.dumps(options)+');return {status:r.status,data:await r.json()};})()')
    marker='<img src=x onerror="window.__qaInjected=1">'
    call('POST','/auth/logout');visit('/signup');c.wait('!!document.querySelector("[name=confirm_password]")')
    password=secrets.token_urlsafe(24)
    submit({'full_name':marker,'email':'text-smoke-'+secrets.token_hex(6)+'@example.com','password':password,'confirm_password':password});signed_in()
    assert call('GET','/auth/me')['data']['full_name']==marker
    visit('/onboarding');c.wait('document.querySelector("h1")?.textContent==="Building setup"')
    c.evaluate('Array.from(document.links).find(a=>a.textContent.trim()==="Open Buildings").click()')
    c.wait('document.querySelector("h1")?.textContent==="Buildings"')
    c.evaluate('Array.from(document.querySelectorAll("button")).find(b=>b.textContent.trim()==="Add building").click()')
    submit({'name':marker,'building_type':'Office','city':marker,'description':marker})
    c.wait('document.querySelector("main")?.textContent.includes("Building overview")')
    bid=int(c.evaluate('location.pathname.split("/").pop()'))
    row=call('GET',f'/buildings/{bid}')['data']
    for key in ['name','city','description']:assert row[key]==marker
    assert c.evaluate('document.querySelector("main dd.whitespace-pre-wrap")?.textContent==='+json.dumps(marker))
    assert c.evaluate('window.__qaInjected===undefined&&!document.querySelector("main img[src=x]")')
    c.screenshot('phase29_text_description_own.png')
    call('POST','/auth/logout');visit('/login');signed_out();submit({'email':admin_email,'password':admin_password});signed_in()
    visit('/admin/buildings?building='+str(bid));c.wait('!!document.querySelector("[data-admin-building-detail]")')
    assert c.evaluate('document.querySelector("[data-admin-building-detail] p.whitespace-pre-wrap")?.textContent==='+json.dumps(marker))
    assert c.evaluate('window.__qaInjected===undefined&&!document.querySelector("main img[src=x]")')
    c.screenshot('phase29_text_description_admin.png')
    print('QA smoke: out-of-repository browser profile and stored full_name/name/city/description text verified; metadata selector ambiguity corrected',flush=True)
    return {'passed':True,'supported_onboarding_navigation':True,'form_helper_scoped_to_controls':True,'API_confirms_full_name_name_city_description_marker':True,'description_specific_DOM_assertions_owner_and_admin':True,'no_injected_img_or_script_execution':True,'profile_outside_repo_asserted_by_harness':True}

if __name__=='__main__':
    import verify_auth_browser
    sys.argv.extend(['--buildings','--measurements','--readiness','--predictions','--dashboard','--admin','--hardening'])
    verify_auth_browser.main()
