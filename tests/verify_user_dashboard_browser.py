"""Actual owned dashboard selection, stored analytics and current forecast lifecycle."""
import csv,io,json,secrets,sys
from pathlib import Path


def scenario(*,c,visit,submit,signed_out,signed_in,api,user_email,user_password,reload,restart):
    # The reused Phase17 interceptor originally mocked public responses only.
    # Private summary fixtures also need the credentialed CORS response header.
    send = c.send
    def credentialed_fixture(method, params):
        if method == 'Fetch.fulfillRequest':
            params = {**params, 'responseHeaders': [*params.get('responseHeaders', []),
                {'name': 'Access-Control-Allow-Credentials', 'value': 'true'}]}
        return send(method, params)
    c.send = credentialed_fixture
    def click(text):c.evaluate('Array.from(document.querySelectorAll("button")).find(b=>b.textContent.trim()==='+json.dumps(text)+').click()')
    def link(text):
        c.wait('Array.from(document.querySelectorAll("main a")).some(a=>a.textContent.trim()==='+json.dumps(text)+')')
        c.evaluate('Array.from(document.querySelectorAll("main a")).find(a=>a.textContent.trim()==='+json.dumps(text)+').click()')
    def call(method,path,body=None):
        opts={'method':method,'credentials':'include','headers':{'Content-Type':'application/json','X-SmartEnergy-CSRF':'1'}}
        if body is not None:opts['body']=json.dumps(body)
        return c.evaluate('(async()=>{const r=await fetch('+json.dumps(api+path)+','+json.dumps(opts)+');return {status:r.status,data:r.status===204?null:await r.json()};})()')
    def login(email,password):
        call('POST','/auth/logout');visit('/login');signed_out();submit({'email':email,'password':password});signed_in()
    def dashboard(bid):c.wait('document.querySelector("[data-dashboard-building]")?.getAttribute("data-dashboard-building")==='+json.dumps(str(bid)))
    def state(code):c.wait('document.querySelector("[data-dashboard-readiness]")?.getAttribute("data-dashboard-readiness")==='+json.dumps(code))
    def count(n):c.wait('Array.from(document.querySelectorAll("[data-summary-label]")).some(e=>e.dataset.summaryLabel==="Stored measurements"&&e.textContent==='+json.dumps(str(n))+')')
    def create(name):
        visit('/buildings');c.wait('document.querySelector("h1")?.textContent==="Buildings"');click('Add building')
        submit({'name':name,'building_type':'Office','city':'Dashboard fixture city'})
        c.wait(r'/^\/buildings\/[0-9]+$/.test(location.pathname)&&document.querySelector("main")?.textContent.includes('+json.dumps(name)+')')
        bid=int(c.evaluate('location.pathname.split("/").pop()'));link('Open building dashboard');dashboard(bid);return bid
    with (Path(__file__).resolve().parents[1]/'data/raw/energydata_complete.csv').open(newline='',encoding='utf-8') as stream:
        reader=csv.DictReader(stream);fields=reader.fieldnames;rows=[next(reader) for _ in range(1010)]
    def upload(records):
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fields);writer.writeheader();writer.writerows(records)
        c.evaluate('(() => {const input=document.querySelector("input[name=file]");const dt=new DataTransfer();dt.items.add(new File(['+json.dumps(stream.getvalue())+'],"dashboard.csv",{type:"text/csv"}));input.files=dt.files;input.closest("form").requestSubmit();})()')
    login(user_email,user_password)
    name='Dashboard A '+secrets.token_hex(4);bid=create(name);state('NO_MEASUREMENTS');count(0)
    assert 'No current forecast yet' in c.text()
    link('Manage measurements and building');c.wait('!!document.querySelector("input[name=file]")');upload(rows[:10])
    c.wait('document.querySelector("main")?.textContent.includes("Imported 10 of 10 rows")');link('Open building dashboard');dashboard(bid);count(10);state('INSUFFICIENT_HISTORY')
    assert c.evaluate('Array.from(document.querySelectorAll("button")).find(b=>b.textContent.trim()==="Predict next 10 minutes").disabled')
    c.wait('document.querySelector("[data-energy-points]")?.getAttribute("data-energy-points")==="10"')
    link('Manage measurements and building');c.wait('!!document.querySelector("input[name=file]")');upload(rows[10:1009])
    c.wait('document.querySelector("main")?.textContent.includes("Imported 999 of 999 rows")');link('Open building dashboard');dashboard(bid);count(1009);state('READY')
    c.wait('Array.from(document.querySelectorAll("button")).some(b=>b.textContent.trim()==="Predict next 10 minutes"&&!b.disabled)');click('Predict next 10 minutes')
    c.wait('document.querySelector("[data-current-forecast]")?.getAttribute("data-current-forecast")!=="none"&&!!document.querySelector("[data-current-recommendation]")')
    current=call('GET',f'/buildings/{bid}/dashboard-summary')['data']['current_prediction'];assert current
    assert current['recommendation']['text'] in c.text()
    reload();dashboard(bid);count(1009);state('READY');c.wait('!!document.querySelector("[data-current-recommendation]")')
    restart();visit(f'/dashboard?building={bid}');dashboard(bid);c.wait('!!document.querySelector("[data-current-recommendation]")')
    link('Manage measurements and building');c.wait('!!document.querySelector("input[name=file]")');click('Add measurement')
    body={k:str(float(v)) for k,v in rows[1009].items() if k not in ('date','rv1','rv2')};body['timestamp']=rows[1009]['date'].replace(' ','T');submit(body)
    c.wait('!document.querySelector("input[name=Appliances]")');link('Open building dashboard');dashboard(bid);count(1010);state('READY')
    c.wait('document.querySelector("main")?.textContent.includes("No current forecast yet")');assert not c.evaluate('!!document.querySelector("[data-current-recommendation]")')
    c.wait('Array.from(document.querySelectorAll("button")).some(b=>b.textContent.trim()==="Predict next 10 minutes"&&!b.disabled)');click('Predict next 10 minutes')
    c.wait('!!document.querySelector("[data-current-recommendation]")')
    summary=call('GET',f'/buildings/{bid}/dashboard-summary')['data'];assert summary['prediction_count']==2 and summary['current_prediction']['id']!=current['id']
    assert summary['recent_predictions'][0]['id']==summary['current_prediction']['id']
    link('Explore prediction history');c.wait('document.querySelector("[data-history-total]")?.textContent.includes("2")');assert name in c.text()
    link('Open building dashboard');dashboard(bid);link('View saved recommendations');c.wait('document.querySelector("main")?.textContent.includes("saved recommendation ledger")');assert summary['current_prediction']['recommendation']['text'] in c.text()
    link('Open building dashboard');dashboard(bid)
    for width in (1440,390):
        c.call('Emulation.setDeviceMetricsOverride',{'width':width,'height':1000,'deviceScaleFactor':1,'mobile':width==390})
        assert c.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        c.screenshot(f'phase27_dashboard_{width}.png')
    c.call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False})
    # Controlled malformed API result must replace operational cards, never supply defaults.
    c.malformed=True;c.malformed_path=f'/buildings/{bid}/dashboard-summary?limit=144';click('Refresh stored state')
    c.wait('document.querySelector("main")?.textContent.includes("Dashboard unavailable")');assert not c.evaluate('!!document.querySelector("[data-summary-label]")')
    c.malformed=False;click('Retry dashboard');dashboard(bid);count(1010)
    second_name='Dashboard B '+secrets.token_hex(4);other=create(second_name);count(0);state('NO_MEASUREMENTS');assert not c.evaluate('!!document.querySelector("[data-current-recommendation]")')
    c.evaluate('(()=>{const e=document.getElementById("building-selector");e.value='+json.dumps(str(bid))+';e.dispatchEvent(new Event("change",{bubbles:true}));})()');dashboard(bid);count(1010)
    assert c.evaluate('new URLSearchParams(location.search).has("building")')
    # SPA building edit -> back invalidates summary metadata; deletion removes the selected building.
    c.evaluate('(()=>{const e=document.getElementById("building-selector");e.value='+json.dumps(str(other))+';e.dispatchEvent(new Event("change",{bubbles:true}));})()');dashboard(other)
    link('Manage measurements and building');c.wait('document.querySelector("main")?.textContent.includes("Building overview")');click('Edit building');submit({'name':second_name+' edited'})
    c.wait('!document.querySelector("[name=name]")');link('Open building dashboard');dashboard(other);c.wait('document.querySelector("main")?.textContent.includes('+json.dumps(second_name+' edited')+')')
    link('Manage measurements and building');c.wait('document.querySelector("main")?.textContent.includes("Building overview")');click('Delete building');click('Confirm delete')
    c.wait(r'location.pathname.replace(/\/$/,"")==="/buildings"');visit(f'/dashboard?building={other}');c.wait('document.querySelector("main")?.textContent.includes("Building unavailable")')
    call('POST','/auth/logout');email='dashboard-other-'+secrets.token_hex(8)+'@example.com';password=secrets.token_urlsafe(24)
    visit('/signup');c.wait('!!document.querySelector("[name=confirm_password]")');submit({'full_name':'Other dashboard owner','email':email,'password':password,'confirm_password':password});signed_in()
    c.wait('document.querySelector("main")?.textContent.includes("No buildings yet")');assert name not in c.text()
    visit(f'/dashboard?building={bid}');c.wait('document.querySelector("main")?.textContent.includes("Building unavailable")');assert name not in c.text()
    assert call('GET',f'/buildings/{bid}/dashboard-summary')['status']==404
    login(user_email,user_password);visit(f'/dashboard?building={bid}');dashboard(bid);count(1010)
    for claim in ('Live consumption','Estimated savings','95% confidence','Occupants','Apply recommendation'):assert claim not in c.text()
    print('User dashboard QA: real counts/chart/readiness/current forecast, stale transition, SPA invalidation, selection, error isolation and multi-account ownership passed',flush=True)
    return {'passed':True,'initial_signup_no_buildings_verified_by_auth_harness':True,'UI_building_creation_and_dashboard_link':True,'insufficient_and_ready_history':True,'real_count_latest_and_chart':True,'explicit_persisted_forecast_recommendation':True,'refresh_and_restart':True,'new_measurement_old_forecast_not_current':True,'second_forecast_history':True,'prediction_and_recommendation_routes':True,'multiple_buildings_URL_selection':True,'building_edit_delete_invalidation':True,'malformed_backend_hides_values_retry':True,'second_account_and_foreign_URL_isolation':True,'responsive_widths':[1440,390],'no_fake_operational_claims':True}

if __name__=='__main__':
    import verify_auth_browser
    sys.argv.extend(['--buildings','--measurements','--readiness','--predictions','--dashboard'])
    verify_auth_browser.main()
