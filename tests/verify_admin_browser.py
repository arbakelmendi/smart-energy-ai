"""Live admin oversight and immediate revocation using the shared temporary-DB harness."""
import json,secrets,sys,urllib.request,urllib.error
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select,func
from backend.db_models import User,Building,Measurement,Prediction,AuthSession
from backend.auth import COOKIE_NAME


def scenario(*,c,visit,submit,signed_out,signed_in,api,user_email,user_password,admin_email,admin_password,factory):
    def click(text):
        c.wait('Array.from(document.querySelectorAll("button")).some(b=>b.textContent.trim()==='+json.dumps(text)+'&&!b.disabled)')
        c.evaluate('Array.from(document.querySelectorAll("button")).find(b=>b.textContent.trim()==='+json.dumps(text)+').click()')
    def call(method,path,body=None):
        options={'method':method,'credentials':'include','headers':{'Content-Type':'application/json','X-SmartEnergy-CSRF':'1'}}
        if body is not None:options['body']=json.dumps(body)
        return c.evaluate('(async()=>{const r=await fetch('+json.dumps(api+path)+','+json.dumps(options)+');return {status:r.status,data:await r.json()};})()')
    def filter_form(values):
        c.wait('!!document.querySelector("main form")')
        c.evaluate('(()=>{const values='+json.dumps(values)+';for(const [name,value] of Object.entries(values)){const input=document.querySelector(`[name="${name}"]`);input.value=value;input.dispatchEvent(new Event("input",{bubbles:true}));}document.querySelector("main form").requestSubmit();})()')
    def login(email,password):
        call('POST','/auth/logout');visit('/login');signed_out();submit({'email':email,'password':password});signed_in()
    def user_detail(uid):
        visit('/admin/users?user='+str(uid));c.wait('document.querySelector("[data-admin-user-detail]")?.getAttribute("data-admin-user-detail")==='+json.dumps(str(uid)))
    def overview_counts():
        visit('/admin');c.wait('document.querySelectorAll("[data-admin-count]").length===8')
        actual=call('GET','/admin/overview')['data']
        with factory() as db:
            expected={'total_users':db.scalar(select(func.count(User.id))),
                'active_users':db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))),
                'inactive_users':db.scalar(select(func.count(User.id)).where(User.is_active.is_(False))),
                'admin_users':db.scalar(select(func.count(User.id)).where(User.role=='ADMIN')),
                'regular_users':db.scalar(select(func.count(User.id)).where(User.role=='USER')),
                'total_buildings':db.scalar(select(func.count(Building.id))),
                'total_measurements':db.scalar(select(func.count(Measurement.id))),
                'total_predictions':db.scalar(select(func.count(Prediction.id)))}
        assert actual==expected
        for key,value in expected.items():assert c.evaluate('document.querySelector('+json.dumps('[data-admin-count="'+key+'"]')+').textContent')==str(value)
    login(user_email,user_password)
    a_cookie=next(item for item in c.call('Network.getCookies',{'urls':[api]})['cookies'] if item['name']==COOKIE_NAME)
    with factory() as db:
        a=db.scalar(select(User).where(User.email==user_email));aid=a.id
        saved=db.scalar(select(Prediction).join(Building).where(Building.owner_id==aid).order_by(Prediction.id.desc()).limit(1))
        assert saved is not None
        bid=saved.building_id;pid=saved.id
        before=[db.scalar(select(func.count()).select_from(model).where(model.building_id==bid)) for model in (Measurement,Prediction)]
    # USER B creates another real building through the normal UI.
    c.call('Network.deleteCookies',{'name':COOKIE_NAME,'url':api});email='admin-other-'+secrets.token_hex(6)+'@example.com';password=secrets.token_urlsafe(24)
    visit('/signup');c.wait('!!document.querySelector("[name=confirm_password]")');submit({'full_name':'Admin QA other owner','email':email,'password':password,'confirm_password':password});signed_in()
    b_id=call('GET','/auth/me')['data']['id']
    visit('/buildings');c.wait('document.querySelector("h1")?.textContent==="Buildings"');click('Add building');building_name='Admin QA B '+secrets.token_hex(4);submit({'name':building_name,'city':'Admin verification city','building_type':'Office'})
    c.wait('document.querySelector("main")?.textContent.includes("Building overview")&&document.querySelector("main")?.textContent.includes('+json.dumps(building_name)+')')
    b_bid=int(c.evaluate('location.pathname.split("/").pop()'))
    for path in ['/admin/overview','/admin/users','/admin/buildings','/admin/predictions']:
        assert call('GET',path)['status']==403
    visit('/admin');c.wait('document.querySelector("h1")?.textContent==="Administrator access required"')
    login(admin_email,admin_password);admin_id=call('GET','/auth/me')['data']['id'];overview_counts()
    c.wait('!!document.querySelector('+json.dumps('[data-admin-prediction="'+str(pid)+'"]')+')')
    # Lists and details show actual cross-owner data using dedicated admin APIs.
    visit('/admin/users');c.wait('document.querySelectorAll("[data-admin-user]").length>0');assert user_email in c.text() and email in c.text()
    filter_form({'search':email});c.wait('document.querySelectorAll("[data-admin-user]").length===1');assert email in c.text() and user_email not in c.text()
    filter_form({'search':'no-such-account-'+secrets.token_hex(4)});c.wait('document.querySelector("main")?.textContent.includes("No matching users")')
    user_detail(aid);assert 'Measurements:' in c.text();c.wait('document.querySelectorAll("[data-admin-building]").length>0')
    visit('/admin/buildings');c.wait('document.querySelectorAll("[data-admin-building]").length>=2');assert building_name in c.text()
    filter_form({'search':'Admin verification city'});c.wait('document.querySelectorAll("[data-admin-building]").length===1')
    visit('/admin/buildings?building='+str(bid));c.wait('!!document.querySelector("[data-admin-building-detail]")');assert user_email in c.text();assert 'Latest saved prediction, not necessarily current' in c.text()
    assert call('GET',f'/buildings/{bid}')['status']==404
    for width in (1440,390):
        c.call('Emulation.setDeviceMetricsOverride',{'width':width,'height':1000,'deviceScaleFactor':1,'mobile':width==390})
        for suffix,path in [('overview','/admin'),('users','/admin/users'),('buildings','/admin/buildings')]:
            visit(path);c.wait('document.querySelector("main")?.textContent.includes('+json.dumps({'overview':'Persisted prediction activity','users':'Accounts','buildings':'Cross-owner building inventory'}[suffix])+')')
            if suffix=='overview':c.wait('document.querySelectorAll("[data-admin-count]").length===8')
            else:c.wait('document.querySelectorAll("[data-admin-'+('user' if suffix=='users' else 'building')+']").length>0')
            assert c.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            c.screenshot(f'phase28_admin_{suffix}_{width}.png')
    c.call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False})
    # Deactivation requires confirmation, cancellation does not mutate.
    user_detail(aid);click('Deactivate account');c.wait('!!document.querySelector("[role=alertdialog]")');assert call('GET',f'/admin/users/{aid}')['data']['is_active']
    click('Cancel deactivation');assert call('GET',f'/admin/users/{aid}')['data']['is_active']
    with urllib.request.urlopen(urllib.request.Request(api+'/auth/me',headers={'Cookie':COOKIE_NAME+'='+a_cookie['value']})) as response:assert response.status==200
    click('Deactivate account');click('Confirm deactivation');c.wait('Array.from(document.querySelectorAll("button")).some(b=>b.textContent.trim()==="Activate account"&&!b.disabled)')
    with factory() as db:
        assert not db.get(User,aid).is_active
        assert db.scalar(select(func.count(AuthSession.id)).where(AuthSession.user_id==aid))==0
        assert before==[db.scalar(select(func.count()).select_from(model).where(model.building_id==bid)) for model in (Measurement,Prediction)]
        assert db.get(Building,bid) is not None
    # Verify the preserved USER A cookie fails immediately, before expiration.
    request=urllib.request.Request(api+'/auth/me',headers={'Cookie':COOKIE_NAME+'='+a_cookie['value']})
    try:urllib.request.urlopen(request);raise AssertionError('Revoked session authenticated')
    except urllib.error.HTTPError as error:assert error.code==401
    # Put that exact old session in a browser context and verify the frontend exits.
    c.call('Network.setCookie',{'name':COOKIE_NAME,'value':a_cookie['value'],'url':api,'path':'/','httpOnly':True,'sameSite':'Lax'})
    visit('/dashboard');signed_out();submit({'email':user_email,'password':user_password});c.wait('document.querySelector("[role=alert]")?.textContent.includes("account inactive")')
    submit({'email':admin_email,'password':admin_password});signed_in();user_detail(aid);click('Activate account');c.wait('Array.from(document.querySelectorAll("button")).some(b=>b.textContent.trim()==="Deactivate account")')
    login(user_email,user_password);assert call('GET',f'/buildings/{bid}/dashboard-summary')['data']['prediction_count']==before[1]
    assert not c.evaluate('Array.from(document.links).some(a=>a.getAttribute("href")?.startsWith("/admin"))')
    login(admin_email,admin_password);user_detail(admin_id)
    assert c.evaluate('Array.from(document.querySelectorAll("button")).find(b=>b.textContent.trim()==="Deactivate account").disabled')
    final=call('PATCH',f'/admin/users/{admin_id}/status',{'is_active':False});assert final['status']==409 and 'final active' in final['data']['detail']
    # With another active ADMIN, the independent self check remains authoritative.
    with factory() as db:db.get(User,b_id).role='ADMIN';db.commit()
    own=call('PATCH',f'/admin/users/{admin_id}/status',{'is_active':False});assert own['status']==409 and 'own' in own['data']['detail']
    with factory() as db:db.get(User,b_id).role='USER';db.commit()
    # Real pagination using clearly identified temporary account metadata fixtures.
    with factory() as db:
        encoded=db.get(User,aid).password_hash
        db.add_all([User(email=f'pagination-{i}-'+secrets.token_hex(4)+'@example.com',full_name=f'Pagination fixture {i}',password_hash=encoded,role='USER') for i in range(51)]);db.commit()
    visit('/admin/users');c.wait('document.querySelectorAll("[data-admin-user]").length===50');click('Next page');c.wait('document.querySelector("main")?.textContent.includes("Offset 50")');assert c.evaluate('document.querySelectorAll("[data-admin-user]").length')>0;click('Previous page');c.wait('document.querySelector("main")?.textContent.includes("Offset 0")')
    for path in ['/admin/buildings','/admin/predictions']:
        first=call('GET',path+'?limit=1')['data'];second=call('GET',path+'?limit=1&offset=1')['data'];assert first['total']>=2 and first['items'][0]['id']!=second['items'][0]['id']
    overview_counts()
    # Malformed private data is hidden with a controlled Retry state.
    c.malformed=True;c.malformed_path='/admin/overview';visit('/admin');c.wait('document.querySelector("main")?.textContent.includes("Administration unavailable")');assert not c.evaluate('!!document.querySelector("[data-admin-count]")')
    c.malformed=False;c.evaluate('Array.from(document.querySelectorAll("button")).find(b=>b.textContent.trim()==="Retry administration").click()');c.wait('document.querySelectorAll("[data-admin-count]").length===8')
    for forbidden in ['password_hash','token_hash','feature_snapshot_json','Last seen','Audit log','Mean accuracy','Energy monitored']:assert forbidden not in c.text()
    print('Admin QA: actual overview, cross-owner tables/details/activity, confirmation, immediate session revocation, retained domain data, reactivation, USER denial, self/final-admin protection, filtering, pagination and responsive layouts passed',flush=True)
    return {'passed':True,'overview_matches_SQL_counts':True,'cross_owner_users_buildings_predictions':True,'user_and_building_details':True,'normal_owner_API_remains_404':True,'USER_HTTP403_and_page_denial':True,'deactivation_confirmation_and_cancel':True,'all_sessions_revoked_immediately':True,'revoked_cookie_browser_redirect':True,'inactive_login_blocked':True,'domain_history_retained':True,'reactivation_new_login_succeeds':True,'self_and_final_admin_protected':True,'server_search_and_empty_results':True,'pagination_users_UI_buildings_predictions_API':True,'malformed_response_Retry':True,'responsive_widths':[1440,390],'runtime_fixtures_only_temporary_DB':True}

if __name__=='__main__':
    import verify_auth_browser
    sys.argv.extend(['--buildings','--measurements','--readiness','--predictions','--dashboard','--admin'])
    verify_auth_browser.main()
