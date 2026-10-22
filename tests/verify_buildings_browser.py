"""Phase23 live two-owner building CRUD; reuses full isolated Phase22 auth QA.

Run with .venv. Accounts/database/ports/profile are temporary; no developer data.
"""
import json,secrets,sys,time


def scenario(*, c, visit, submit, signed_out, signed_in, api, user_email, user_password, admin_email, admin_password, restart, reload):
    def click(text):
        c.evaluate('Array.from(document.querySelectorAll("button")).find(b => b.textContent.trim() === '+json.dumps(text)+').click()')
    def login(email,password):
        # Use real logout, preserving its CSRF/server revocation checks.
        result=call('POST','/auth/logout')
        assert result['status']==200
        visit('/login');signed_out();submit({'email':email,'password':password});signed_in()
    def call(method,path,body=None):
        options={'method':method,'credentials':'include','headers':{'Content-Type':'application/json','X-SmartEnergy-CSRF':'1'}}
        if body is not None:options['body']=json.dumps(body)
        return c.evaluate('(async()=>{const r=await fetch('+json.dumps(api+path)+','+json.dumps(options)+');return {status:r.status,data:r.status===204?null:await r.json()};})()')
    def listed(name):
        c.wait('document.querySelector("main")?.textContent.includes('+json.dumps(name)+')')
    def create(name):
        visit('/buildings');c.wait('document.querySelector("h1")?.textContent === "Buildings" && !document.querySelector("main [role=status]")')
        click('Add building');c.wait('document.querySelector("fieldset")?.disabled === false')
        submit({'name':name,'building_type':'Office','floor_area_m2':'150.5','city':'Verification city','description':'Persisted browser metadata'})
        c.wait(r'/^\/buildings\/[0-9]+$/.test(location.pathname) && document.querySelector("main")?.textContent.includes('+json.dumps(name)+')')
        return int(c.evaluate('location.pathname.split("/").pop()'))

    login(user_email,user_password)
    visit('/buildings');listed('No buildings yet')
    a_name='Owner A building '+secrets.token_hex(3)
    a_id=create(a_name)
    assert call('GET',f'/buildings/{a_id}')['data']['name']==a_name
    visit('/buildings');listed(a_name)
    c.evaluate('Array.from(document.querySelectorAll("main a")).find(a => a.textContent.includes('+json.dumps(a_name)+')).click()')
    listed('Building overview');click('Edit building');c.wait('document.querySelector("fieldset")?.disabled === false')
    assert c.evaluate('document.querySelector("[name=name]").value')==a_name
    draft=a_name+' edited'
    before=len([x for x in c.api if x['path']=='/auth/me'])
    c.evaluate('window.__phase23field=document.querySelector("[name=name]");window.__phase23field.value='+json.dumps(draft)+';window.dispatchEvent(new Event("visibilitychange"))')
    deadline=time.monotonic()+15
    while len([x for x in c.api if x['path']=='/auth/me'])<=before and time.monotonic()<deadline:
        c.evaluate('document.readyState');time.sleep(.1)
    assert len([x for x in c.api if x['path']=='/auth/me'])>before
    assert c.evaluate('document.querySelector("[name=name]") === window.__phase23field && window.__phase23field.value === '+json.dumps(draft))
    submit({'name':draft,'building_type':'Educational','floor_area_m2':'175.25','city':'Updated city','description':'Updated persisted metadata'})
    listed(draft);c.wait('!document.querySelector("[name=name]")')
    assert call('GET',f'/buildings/{a_id}')['data']['floor_area_m2']==175.25
    reload();listed(draft)
    restart();visit(f'/buildings/{a_id}');listed(draft)
    for width in (1440,390):
        c.call('Emulation.setDeviceMetricsOverride',{'width':width,'height':1000,'deviceScaleFactor':1,'mobile':width==390})
        assert c.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        c.screenshot(f'phase23_building_{width}.png')
    c.call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False})
    for claim in ('kWh/day','Sensors online','vs baseline','occupants','95% confidence'):
        assert claim not in c.text()
    print('Building QA: create, edit, background session refresh and restart persistence passed',flush=True)

    assert call('POST','/auth/logout')['status']==200
    b_email='owner-b-'+secrets.token_hex(8)+'@example.com';b_password=secrets.token_urlsafe(24)
    visit('/signup');c.wait('document.querySelector("[name=confirm_password]") && document.querySelector("fieldset")?.disabled === false')
    submit({'full_name':'Owner B verification','email':b_email,'password':b_password,'confirm_password':b_password});signed_in()
    visit(f'/buildings/{a_id}');listed('Building not found');assert draft not in c.text()
    assert call('GET',f'/buildings/{a_id}')['status']==404
    assert call('PATCH',f'/buildings/{a_id}',{'name':'Cross owner'})['status']==404
    assert call('DELETE',f'/buildings/{a_id}')['status']==404
    assert call('POST','/buildings',{'name':'Injected','owner_id':1})['status']==422
    assert call('PATCH',f'/buildings/{a_id}',{'owner_id':1})['status']==422
    visit('/buildings');listed('No buildings yet')
    b_name='Owner B building '+secrets.token_hex(3);b_id=create(b_name)
    visit('/buildings');listed(b_name);assert draft not in c.text()
    assert [b['id'] for b in call('GET','/buildings')['data']['buildings']]==[b_id]
    print('Building QA: second USER is isolated in UI and GET/PATCH/DELETE APIs',flush=True)

    login(user_email,user_password);visit(f'/buildings/{a_id}');listed(draft)
    click('Delete building');listed('Delete this building?');click('Cancel delete')
    assert call('GET',f'/buildings/{a_id}')['status']==200
    click('Delete building');listed('Delete this building?');click('Confirm delete')
    c.wait(r'location.pathname.replace(/\/$/,"") === "/buildings" && document.querySelector("main")?.textContent.includes("No buildings yet")')
    assert call('GET',f'/buildings/{a_id}')['status']==404
    login(b_email,b_password);visit('/buildings');listed(b_name)
    assert call('GET',f'/buildings/{b_id}')['status']==200
    login(admin_email,admin_password);visit('/buildings');listed('No buildings yet')
    for method,body in [('GET',None),('PATCH',{'name':'Cross admin'}),('DELETE',None)]:
        assert call(method,f'/buildings/{b_id}',body)['status']==404
    own=call('POST','/buildings',{'name':'Admin owned verification'});assert own['status']==201
    own_id=own['data']['id']
    assert call('PATCH',f'/buildings/{own_id}',{'name':'Admin edit'})['status']==200
    assert call('DELETE',f'/buildings/{own_id}')['status']==204
    assert call('GET','/buildings')['data']['buildings']==[]
    visit('/admin/users');listed('No verified operational readings')
    print('Building QA: confirmed deletion, other-owner preservation and owner-only ADMIN policy passed',flush=True)
    return {'passed':True,'USER_A_create_list_view_edit':True,'refresh_and_backend_restart_persistence':True,
        'edit_form_survives_background_auth_revalidation':True,'USER_B_direct_url_and_API_isolation':True,
        'owner_injection_rejected':True,'USER_B_create_and_own_list_only':True,'USER_A_confirm_and_cancel_delete':True,
        'USER_B_building_preserved':True,'ADMIN_owner_only_policy':True,'actual_DELETE_204_handled':True,
        'no_fake_operational_metrics':True,'responsive_widths':[1440,390],'cache_updates_after_server_confirmation':True}


if __name__=='__main__':
    import verify_auth_browser
    sys.argv.append('--buildings')
    verify_auth_browser.main()
