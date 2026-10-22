"""Explicit real building forecasts, persisted history and complete earlier browser QA."""
import csv,io,json,secrets,sys
from pathlib import Path


def scenario(*,c,visit,submit,signed_out,signed_in,api,user_email,user_password,admin_email,admin_password,reference_id,reload,restart):
    def click(text):c.evaluate('Array.from(document.querySelectorAll("button")).find(b=>b.textContent.trim()==='+json.dumps(text)+').click()')
    def call(method,path,body=None):
        opts={'method':method,'credentials':'include','headers':{'Content-Type':'application/json','X-SmartEnergy-CSRF':'1'}}
        if body is not None:opts['body']=json.dumps(body)
        return c.evaluate('(async()=>{const r=await fetch('+json.dumps(api+path)+','+json.dumps(opts)+');return {status:r.status,data:r.status===204?null:await r.json()};})()')
    def login(email,password):
        assert call('POST','/auth/logout')['status']==200
        visit('/login');signed_out();submit({'email':email,'password':password});signed_in()
    def state(code):c.wait('document.querySelector("[data-readiness-state]")?.getAttribute("data-readiness-state")==='+json.dumps(code))
    def count(n):c.wait('document.querySelector("[data-prediction-count]")?.getAttribute("data-prediction-count")==='+json.dumps(str(n)))
    def button_disabled():return c.evaluate('Array.from(document.querySelectorAll("button")).find(b=>b.textContent.trim()==="Predict next 10 minutes")?.disabled')
    def enabled():c.wait('Array.from(document.querySelectorAll("button")).some(b=>b.textContent.trim()==="Predict next 10 minutes"&&!b.disabled)')
    with (Path(__file__).resolve().parents[1]/'data/raw/energydata_complete.csv').open(newline='',encoding='utf-8') as stream:
        reader=csv.DictReader(stream);fields=reader.fieldnames;rows=[next(reader) for _ in range(1010)]
    def upload(records):
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fields);writer.writeheader();writer.writerows(records)
        c.evaluate('(() => {const e=document.querySelector("input[name=file]");const d=new DataTransfer();d.items.add(new File(['+json.dumps(stream.getvalue())+'],"predictions.csv",{type:"text/csv"}));e.files=d.files;e.closest("form").requestSubmit();})()')
    login(user_email,user_password)
    bid=call('POST','/buildings',{'name':'Forecast browser verification'})['data']['id'];path=f'/buildings/{bid}/predictions'
    visit(f'/buildings/{bid}');state('NO_MEASUREMENTS');count(0);assert button_disabled()
    upload(rows[:10]);state('INSUFFICIENT_HISTORY');assert button_disabled()
    assert call('POST',path)['status']==409
    upload(rows[10:1009]);state('READY');enabled();click('Predict next 10 minutes');count(1)
    first=call('GET',path)['data']['items'][0]
    assert first['matches_current_history'] and first['recommendation']
    assert f"{first['prediction_wh']:.3f} Wh" in c.text()
    assert first['recommendation']['text'] in c.text()
    assert 'Measured Appliances at forecast source' in c.text()
    assert 'Predictions for other buildings are experimental' in c.text()
    reload();state('READY');count(1)
    restart();visit(f'/buildings/{bid}');state('READY');count(1)
    enabled();click('Predict next 10 minutes');c.wait('document.querySelector("main")?.textContent.includes("Reused the existing stored forecast")');count(1)
    assert call('GET',path)['data']['items'][0]['id']==first['id']
    click('Add measurement');c.wait('!!document.querySelector("input[name=Appliances]") && document.querySelector("fieldset")?.disabled===false')
    body={k:str(float(v)) for k,v in rows[1009].items() if k not in ('date','rv1','rv2')};body['timestamp']=rows[1009]['date'].replace(' ','T')
    submit(body);c.wait('!document.querySelector("input[name=Appliances]")');state('READY')
    c.wait('document.querySelector("[data-prediction-id]")?.textContent.includes("Historical snapshot")')
    assert not call('GET',path)['data']['items'][0]['matches_current_history']
    enabled();click('Predict next 10 minutes');count(2)
    history=call('GET',path)['data'];assert len(history['items'])==2
    second=history['items'][0];assert second['source_timestamp']==rows[1009]['date'].replace(' ','T')
    assert history['items'][1]['id']==first['id'] and second['id']!=first['id']
    ids=c.evaluate('Array.from(document.querySelectorAll("[data-prediction-history-id]")).map(e=>Number(e.dataset.predictionHistoryId))')
    assert ids==[second['id'],first['id']]
    for width in (1440,390):
        c.call('Emulation.setDeviceMetricsOverride',{'width':width,'height':1000,'deviceScaleFactor':1,'mobile':width==390})
        assert c.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        c.screenshot(f'phase26_prediction_{width}.png')
    c.call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False})
    for forbidden in ('95% confidence','Estimated savings','Apply recommendation','Turn HVAC off'):assert forbidden not in c.text()
    call('POST','/auth/logout');email='forecast-other-'+secrets.token_hex(8)+'@example.com';password=secrets.token_urlsafe(24)
    visit('/signup');c.wait('!!document.querySelector("[name=confirm_password]")');submit({'full_name':'Forecast other owner','email':email,'password':password,'confirm_password':password});signed_in()
    visit(f'/buildings/{bid}');c.wait('document.querySelector("main")?.textContent.includes("Building not found")')
    assert call('GET',path)['status']==404 and call('POST',path)['status']==404
    login(admin_email,admin_password);assert call('GET',path)['status']==404 and call('POST',path)['status']==404
    visit(f'/buildings/{reference_id}');state('READY');count(0);enabled();click('Predict next 10 minutes');count(1)
    reference=call('GET',f'/buildings/{reference_id}/predictions')['data']['items'][0]
    assert reference['matches_current_history'] and reference['recommendation']
    assert 'UCI Reference Building' in c.text()
    print('Forecast QA: explicit action, readiness gating, saved recommendation, refresh/restart, idempotency, new-input history, isolation and UCI reference passed',flush=True)
    return {'passed':True,'insufficient_history_button_disabled':True,'server_not_ready409':True,'explicit_forecast_and_recommendation':True,'current_vs_predicted_labels':True,'experimental_warning':True,'refresh_restart_persistence':True,'same_inputs_reused_one_row':True,'new_latest_old_snapshot_marked_historical':True,'new_latest_creates_second_forecast':True,'history_newest_first':True,'USER_B_and_ADMIN_owner_isolation':True,'full_reference_UI_forecast':True,'responsive_widths':[1440,390],'no_savings_confidence_actuation_UI':True}

if __name__=='__main__':
    import verify_auth_browser
    sys.argv.extend(['--buildings','--measurements','--readiness','--predictions'])
    verify_auth_browser.main()
