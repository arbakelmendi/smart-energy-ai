"""Live Phase24 form/upload/history QA, plus full auth and building regression."""
import csv,io,json,secrets,sys
from pathlib import Path


def scenario(*,c,visit,submit,signed_out,signed_in,api,user_email,user_password,reload,restart):
    def click(text):c.evaluate('Array.from(document.querySelectorAll("button")).find(b=>b.textContent.trim()==='+json.dumps(text)+').click()')
    def call(method,path,body=None):
        options={'method':method,'credentials':'include','headers':{'Content-Type':'application/json','X-SmartEnergy-CSRF':'1'}}
        if body is not None:options['body']=json.dumps(body)
        return c.evaluate('(async()=>{const r=await fetch('+json.dumps(api+path)+','+json.dumps(options)+');return {status:r.status,data:r.status===204?null:await r.json()};})()')
    def login(email,password):
        assert call('POST','/auth/logout')['status']==200
        visit('/login');signed_out();submit({'email':email,'password':password});signed_in()
    def count(n):
        try:c.wait('document.querySelector("[data-measurement-count]")?.getAttribute("data-measurement-count")==='+json.dumps(str(n)),seconds=10)
        except Exception:
            print('Measurement QA diagnostics:',json.dumps(c.evaluate('({text:document.querySelector("main")?.textContent,invalid:Array.from(document.querySelectorAll("input:invalid")).map(e=>({name:e.name,value:e.value,message:e.validationMessage}))})')),flush=True)
            raise
    def upload(data):
        c.evaluate('(() => {const input=document.querySelector("input[name=file]");const dt=new DataTransfer();dt.items.add(new File(['+json.dumps(data)+'],"history.csv",{type:"text/csv"}));input.files=dt.files;input.dispatchEvent(new Event("change",{bubbles:true}));input.closest("form").requestSubmit();})()')
    with (Path(__file__).resolve().parents[1]/'data/raw/energydata_complete.csv').open(newline='',encoding='utf-8') as f:
        reader=csv.DictReader(f);fields=reader.fieldnames;rows=[next(reader) for _ in range(5)]
    def csv_text(records):
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fields);writer.writeheader();writer.writerows(records);return stream.getvalue()
    login(user_email,user_password)
    building=call('POST','/buildings',{'name':'Measurement browser verification'})
    assert building['status']==201;bid=building['data']['id'];path=f'/buildings/{bid}/measurements'
    visit(f'/buildings/{bid}');count(0);assert 'No measurements yet' in c.text()
    click('Add measurement');c.wait('document.querySelector("input[name=Appliances]") && document.querySelector("fieldset")?.disabled===false')
    body={k:str(float(v)) for k,v in rows[0].items() if k not in ('date','rv1','rv2')};body['timestamp']=rows[0]['date'].replace(' ','T')
    submit(body);count(1);c.wait('!document.querySelector("input[name=Appliances]")')
    reload();count(1);restart();visit(f'/buildings/{bid}');count(1)
    upload(csv_text(rows[1:3]));count(3);c.wait('document.querySelector("main")?.textContent.includes("Imported 2 of 2 rows")')
    assert call('GET',path)['data']['items'][0]['timestamp']==rows[2]['date'].replace(' ','T')
    bad={**rows[4],'T1':'not-numeric'}
    upload(csv_text([rows[3],bad]));c.wait('document.querySelector("[role=alert]")?.textContent.includes("CSV row 3 (T1)")');count(3)
    assert call('GET',path)['data']['total']==3
    upload(csv_text([rows[0]]));c.wait('document.querySelector("[role=alert]")?.textContent.includes("already exists")');count(3)
    click('Add measurement');c.wait('!!document.querySelector("input[name=Appliances]")');submit(body)
    c.wait('document.querySelector("input[name=Appliances]")?.closest("form").querySelector("[role=alert]")?.textContent.includes("already exists")');count(3);click('Cancel measurement')
    for width in (1440,390):
        c.call('Emulation.setDeviceMetricsOverride',{'width':width,'height':1000,'deviceScaleFactor':1,'mobile':width==390})
        assert c.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),'measurement page overflow'
        c.screenshot(f'phase24_measurements_{width}.png')
    c.call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False})
    row=call('GET',path)['data']['items'][0]
    c.evaluate('document.querySelector('+json.dumps('[data-measurement-id="'+str(row['id'])+'"] button')+').click()')
    click('Cancel measurement delete');count(3)
    c.evaluate('document.querySelector('+json.dumps('[data-measurement-id="'+str(row['id'])+'"] button')+').click()')
    click('Confirm measurement delete');count(2)
    assert call('GET',path)['data']['total']==2
    call('POST','/auth/logout');email='measurement-other-'+secrets.token_hex(8)+'@example.com';password=secrets.token_urlsafe(24)
    visit('/signup');c.wait('!!document.querySelector("[name=confirm_password]")');submit({'full_name':'Other measurement owner','email':email,'password':password,'confirm_password':password});signed_in()
    visit(f'/buildings/{bid}');c.wait('document.querySelector("main")?.textContent.includes("Building not found")')
    assert call('GET',path)['status']==404
    assert call('POST',path,{**{k:float(v) for k,v in body.items() if k!='timestamp'},'timestamp':body['timestamp']})['status']==404
    # Real multipart request under the second user's cookie; no Content-Type override.
    result=c.evaluate('(async()=>{const data=new FormData();data.append("file",new File(['+json.dumps(csv_text([rows[3]]))+'],"other.csv"));const r=await fetch('+json.dumps(api+path+'/import')+',{method:"POST",credentials:"include",headers:{"X-SmartEnergy-CSRF":"1"},body:data});return r.status;})()')
    assert result==404
    assert call('DELETE',path+f"/{row['id']}")['status']==404
    login(user_email,user_password);visit(f'/buildings/{bid}');count(2)
    assert 'Stored measurements: 2' in c.text()
    for fake in ('100% ready','Sensors online','occupants','kWh/day'):assert fake not in c.text()
    print('Measurement QA: manual/CSV persistence, atomic rejection, duplicates, delete, responsive UI and cross-owner isolation passed',flush=True)
    return {'passed':True,'manual_entry_all_raw_fields':True,'refresh_and_restart_persistence':True,'actual_FormData_upload':True,'confirmed_count_and_history':True,'invalid_csv_no_partial_insert':True,'structured_row_error_rendered':True,'csv_and_manual_duplicates_rejected':True,'delete_and_cancel':True,'cross_owner_read_create_import_delete_denied':True,'responsive_widths':[1440,390],'no_fake_readiness_or_metrics':True}

if __name__=='__main__':
    import verify_auth_browser
    sys.argv.extend(['--buildings','--measurements'])
    verify_auth_browser.main()
