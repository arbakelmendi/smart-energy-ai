"""Live readiness transitions/invalidation plus complete existing auth/building/CSV QA."""
import csv,io,json,secrets,sys
from pathlib import Path


def scenario(*,c,visit,submit,signed_out,signed_in,api,user_email,user_password,admin_email,admin_password,reference_id):
    start_api=len(c.api)
    def click(text):c.evaluate('Array.from(document.querySelectorAll("button")).find(b=>b.textContent.trim()==='+json.dumps(text)+').click()')
    def call(method,path,body=None):
        opts={'method':method,'credentials':'include','headers':{'Content-Type':'application/json','X-SmartEnergy-CSRF':'1'}}
        if body is not None:opts['body']=json.dumps(body)
        return c.evaluate('(async()=>{const r=await fetch('+json.dumps(api+path)+','+json.dumps(opts)+');return {status:r.status,data:r.status===204?null:await r.json()};})()')
    def login(email,password):
        assert call('POST','/auth/logout')['status']==200
        visit('/login');signed_out();submit({'email':email,'password':password});signed_in()
    def state(code):c.wait('document.querySelector("[data-readiness-state]")?.getAttribute("data-readiness-state")==='+json.dumps(code))
    with (Path(__file__).resolve().parents[1]/'data/raw/energydata_complete.csv').open(newline='',encoding='utf-8') as stream:
        reader=csv.DictReader(stream);fields=reader.fieldnames;rows=[next(reader) for _ in range(1011)]
    def csv_text(records):
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fields);writer.writeheader();writer.writerows(records);return stream.getvalue()
    def upload(records):
        c.evaluate('(() => {const e=document.querySelector("input[name=file]");const dt=new DataTransfer();dt.items.add(new File(['+json.dumps(csv_text(records))+'],"readiness.csv",{type:"text/csv"}));e.files=dt.files;e.closest("form").requestSubmit();})()')
    def manual(row):
        click('Add measurement');c.wait('!!document.querySelector("input[name=Appliances]") && document.querySelector("fieldset")?.disabled===false')
        body={k:str(float(v)) for k,v in row.items() if k not in ('date','rv1','rv2')};body['timestamp']=row['date'].replace(' ','T')
        submit(body)
        c.wait('!document.querySelector("input[name=Appliances]")')
    login(user_email,user_password)
    bid=call('POST','/buildings',{'name':'Readiness browser verification'})['data']['id']
    path=f'/buildings/{bid}/prediction-readiness';measurements=f'/buildings/{bid}/measurements'
    visit(f'/buildings/{bid}');state('NO_MEASUREMENTS')
    assert call('GET',path)['data']['measurement_count']==0
    manual(rows[0]);state('INSUFFICIENT_HISTORY')
    assert call('GET',path)['data']['continuous_intervals_available']==0
    upload(rows[1:1009]);state('READY')
    ready=call('GET',path)['data'];assert ready['measurement_count']==1009 and ready['required_observations']==1009
    assert ready['latest_measurement_timestamp']==rows[1008]['date'].replace(' ','T')
    # Navigate actual history pages and delete through UI, not an invisible direct mutation.
    for index in range(1,6):
        click('Next measurements');c.wait('document.querySelector("main")?.textContent.includes('+json.dumps('Offset '+str(index*100)+';')+')')
    selected=call('GET',measurements+'?limit=1&offset=500')['data']['items'][0]
    c.evaluate('document.querySelector('+json.dumps('[data-measurement-id="'+str(selected['id'])+'"] button')+').click()')
    click('Confirm measurement delete');state('LATEST_WINDOW_HAS_GAPS')
    gap=call('GET',path)['data'];assert not gap['ready'] and gap['measurement_count']==1008 and gap['first_gap']
    assert 'An incompatible interval was found between' in c.text()
    deleted=next(row for row in rows if row['date'].replace(' ','T')==selected['timestamp'])
    upload([deleted]);state('READY')
    # Manual create shifts the latest origin; a new gap must not fall back to an older ready row.
    manual(rows[1010]);state('LATEST_WINDOW_HAS_GAPS')
    latest=call('GET',path)['data'];assert latest['continuous_intervals_available']==0
    assert latest['latest_measurement_timestamp']==rows[1010]['date'].replace(' ','T')
    upload([rows[1009]]);state('READY')
    for width in (1440,390):
        c.call('Emulation.setDeviceMetricsOverride',{'width':width,'height':1000,'deviceScaleFactor':1,'mobile':width==390})
        assert c.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        c.screenshot(f'phase25_readiness_{width}.png')
    c.call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False})
    call('POST','/auth/logout');email='readiness-other-'+secrets.token_hex(8)+'@example.com';password=secrets.token_urlsafe(24)
    visit('/signup');c.wait('!!document.querySelector("[name=confirm_password]")');submit({'full_name':'Readiness other owner','email':email,'password':password,'confirm_password':password});signed_in()
    visit(f'/buildings/{bid}');c.wait('document.querySelector("main")?.textContent.includes("Building not found")')
    assert call('GET',path)['status']==404
    own=call('POST','/buildings',{'name':'Other owner empty readiness'})['data']['id']
    visit(f'/buildings/{own}');state('NO_MEASUREMENTS')
    assert call('GET',f'/buildings/{reference_id}/prediction-readiness')['status']==404
    login(admin_email,admin_password)
    assert call('GET',path)['status']==404
    visit(f'/buildings/{reference_id}');state('READY')
    reference=call('GET',f'/buildings/{reference_id}/prediction-readiness')['data']
    assert reference['measurement_count']==19735 and reference['ready']
    assert not any(r['path'].startswith('/forecast') for r in c.api[start_api:])
    print('Readiness QA: empty/insufficient/ready/gap/restored, create/import/delete invalidation, latest shift, ownership and full UCI reference passed',flush=True)
    return {'passed':True,'states':['NO_MEASUREMENTS','INSUFFICIENT_HISTORY','READY','LATEST_WINDOW_HAS_GAPS','READY'],
        'manual_create_updates_readiness_without_refresh':True,'CSV_import_updates_readiness_without_refresh':True,
        'delete_required_history_updates_readiness_without_refresh':True,'restore_returns_ready':True,
        'new_latest_gap_does_not_fall_back':True,'actual_measurement_history_pagination':True,
        'second_USER_and_ADMIN_owner_policy':True,'user_building_cache_isolation':True,
        'full_reference_building_ready':True,'reference_measurements':reference['measurement_count'],
        'no_forecast_requests_during_readiness_flow':True,'responsive_widths':[1440,390]}


if __name__=='__main__':
    import verify_auth_browser
    sys.argv.extend(['--buildings','--measurements','--readiness'])
    verify_auth_browser.main()
