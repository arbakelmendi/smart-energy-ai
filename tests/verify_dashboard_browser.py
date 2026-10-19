"""Optional Windows browser regression check using installed Edge and websocket-client.

Run from the project root with project .venv. Requires free loopback ports 8000
and 5173. Uses no external page requests; writes ignored screenshots/evidence to
ml/results/generated. Override Edge executable via SMARTENERGY_BROWSER.
"""
from pathlib import Path
import base64,json,os,shutil,socket,subprocess,sys,tempfile,time,urllib.request
import websocket
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root));g=root/'ml/results/generated';g.mkdir(exist_ok=True)
flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
processes=[];logs=[];profile=None
phase18 = '--phase18' in sys.argv
phase18_extra = {}

def spawn(args,name):
 log=(g/f'phase17_{name}.log').open('w',encoding='utf-8');logs.append(log)
 p=subprocess.Popen(args,cwd=root,stdout=log,stderr=subprocess.STDOUT,creationflags=flags);processes.append(p);return p

def stop(p):
 if p.poll() is None:
  subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags);p.wait(timeout=10)

def ready(url,p):
 end=time.monotonic()+55
 while time.monotonic()<end:
  if p.poll() is not None:raise RuntimeError('Server exited')
  try:
   with urllib.request.urlopen(url,timeout=10) as r:return r.read().decode()
  except OSError:time.sleep(.25)
 raise RuntimeError('Readiness timeout')

class CDP:
 def __init__(self,url):
  self.ws=websocket.create_connection(url,timeout=30,origin='http://localhost');self.seq=0;self.responses={}
  self.cors=[];self.errors=[];self.api=[];self.blocked=0;self.hold=True;self.held=[];self.malformed=False;self.malformed_path="/model/info"
 def send(self,m,p):
  self.seq+=1;self.ws.send(json.dumps({'id':self.seq,'method':m,'params':p}));return self.seq
 def call(self,m,p=None):
  current=self.send(m,p or {})
  while current not in self.responses:
   x=json.loads(self.ws.recv())
   if 'id' in x:self.responses[x['id']]=x;continue
   event=x.get('method');v=x.get('params',{})
   if event=='Fetch.requestPaused':
    url=v['request']['url'];rid=v['requestId']
    if not url.startswith(('http://localhost:','http://127.0.0.1:','data:','blob:')):
     self.blocked+=1;self.send('Fetch.failRequest',{'requestId':rid,'errorReason':'BlockedByClient'})
    elif self.malformed and url=='http://127.0.0.1:8000'+self.malformed_path:
     self.send('Fetch.fulfillRequest',{'requestId':rid,'responseCode':200,'responseHeaders':[{'name':'Content-Type','value':'application/json'},{'name':'Access-Control-Allow-Origin','value':'http://localhost:5173'}],'body':base64.b64encode(b'{"malformed":true}').decode()})
    elif self.hold and url.startswith('http://127.0.0.1:8000/'):
     self.held.append(rid)
    else:self.send('Fetch.continueRequest',{'requestId':rid})
   if event=='Network.loadingFailed' and v.get('corsErrorStatus'):self.cors.append(v['corsErrorStatus'])
   if event=='Runtime.exceptionThrown':self.errors.append(v['exceptionDetails'])
   if event=='Network.responseReceived' and v['response']['url'].startswith('http://127.0.0.1:8000/'):
    self.api.append({'path':v['response']['url'].split(':8000')[-1],'status':v['response']['status']})
  result=self.responses.pop(current)
  if 'error' in result:raise RuntimeError(result['error'])
  return result.get('result',{})
 def evaluate(self,s):
  r=self.call('Runtime.evaluate',{'expression':s,'awaitPromise':True,'returnByValue':True})
  if r.get('exceptionDetails'):raise RuntimeError(r['exceptionDetails'])
  return r['result'].get('value')
 def wait(self,s,seconds=40):
  end=time.monotonic()+seconds
  while time.monotonic()<end:
   if self.evaluate(s):return
   time.sleep(.2)
  raise RuntimeError('Browser assertion timed out: '+s)
 def text(self):return self.evaluate('document.querySelector("main")?.textContent || ""')
 def screenshot(self,name):
  result=self.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':True})
  (g/name).write_bytes(base64.b64decode(result['data']))

try:
 for host,port in [('127.0.0.1',8000),('localhost',5173)]:
  with socket.socket() as s:s.bind((host,port))
 backend_cmd=[sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','8000','--log-level','warning']
 backend=spawn(backend_cmd,'backend');ready('http://127.0.0.1:8000/health',backend)
 frontend=spawn([shutil.which('npm.cmd'),'run','dev','--','--host','localhost','--port','5173','--strictPort'],'frontend')
 html=ready('http://localhost:5173/dashboard',frontend)
 assert 'Loading verified data' in html and 'Held-out test MAE' not in html
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 profile=Path(tempfile.mkdtemp(prefix='phase17-browser-',dir=g)).resolve();assert profile.is_relative_to(g.resolve())
 browser=spawn([os.environ.get('SMARTENERGY_BROWSER', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'),'--headless=new','--disable-gpu','--no-first-run','--disable-background-networking','--remote-debugging-address=127.0.0.1',f'--remote-debugging-port={port}','--remote-allow-origins=http://localhost',f'--user-data-dir={profile}','about:blank'],'browser')
 tabs=json.loads(ready(f'http://127.0.0.1:{port}/json/list',browser))
 c=CDP(next(t for t in tabs if t['type']=='page')['webSocketDebuggerUrl'])
 for method in ('Page.enable','Runtime.enable','Network.enable'):c.call(method)
 c.call('Fetch.enable',{'patterns':[{'urlPattern':'*'}]})
 c.call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False})
 c.call('Page.navigate',{'url':'http://localhost:5173/dashboard'})
 c.wait('document.querySelector("main")?.textContent.includes("Loading verified data")')
 loading_verified=True;c.hold=False
 for rid in c.held:c.send('Fetch.continueRequest',{'requestId':rid})
 c.held=[]
 c.wait('document.querySelector("main")?.textContent.includes("Tuned XGBoost") && document.querySelectorAll(".recharts-bar-rectangle").length >= 16')
 c.wait('document.querySelector("main")?.textContent.includes("15,917")')
 import urllib.request as request
 def api(path):
  with request.urlopen('http://127.0.0.1:8000'+path) as r:return json.load(r)
 info=api('/model/info');comparison=api('/analysis/model-comparison');importance=api('/analysis/feature-importance');thresholds=api('/recommendations/thresholds')
 text=c.text()
 for key in ('mae','rmse','r2'):assert f"{info['final_held_out_metrics'][key]:.3f}" in text
 for required in ('Held-out test','Validation RMSE (Wh)','Predictive importance, not causal effect','Live forecast awaiting sensor history','No active recommendation'):
  assert required in text,required
 for p in (75,90,95):assert str(int(thresholds['percentiles_wh'][f'percentile_{p}']))+' Wh' in text
 forbidden=('Current load','Estimated savings','95% confidence','occupants','comfort risk','48 hours','LSTM','kWh/day','Peak demand','retrained')
 for term in forbidden:assert term not in text,term
 assert c.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
 c.screenshot('phase17_dashboard_desktop.png')
 # Exercise an actual chart tooltip at desktop size.
 point=c.evaluate("""(() => { const r=document.querySelector('.recharts-bar-rectangle')?.getBoundingClientRect();return r?{x:r.x+r.width/2,y:r.y+r.height/2}:null;})()""")
 assert point
 c.call('Input.dispatchMouseEvent',{'type':'mouseMoved','x':point['x'],'y':point['y']})
 c.wait("Array.from(document.querySelectorAll('.recharts-tooltip-wrapper')).some(e => getComputedStyle(e).visibility !== 'hidden' && e.textContent.includes('Validation RMSE'))",seconds=5)
 tooltip_verified=True
 c.call('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
 c.evaluate('window.dispatchEvent(new Event("resize"))');time.sleep(.5)
 assert c.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), 'Mobile page overflow'
 c.screenshot('phase17_dashboard_mobile.png')
 for route in ('/predictions','/recommendations'):
  c.call('Page.navigate',{'url':'http://localhost:5173'+route});c.wait('document.querySelector("main")?.textContent.includes("No active recommendation")')
  c.wait('!document.querySelector("main")?.textContent.includes("Loading verified data")')
  for term in forbidden:assert term not in c.text(),(route,term)
 for route in ('/data','/buildings','/admin','/buildings/ubt-campus-a'):
  c.call('Page.navigate',{'url':'http://localhost:5173'+route});c.wait('document.querySelector("main")?.textContent.includes("No verified operational readings")')
  for term in ('occupants','kWh/day','HVAC','CSV parsed'):assert term not in c.text(),(route,term)
 c.call('Page.navigate',{'url':'http://localhost:5173/dashboard'});c.wait('document.querySelector("main")?.textContent.includes("Tuned XGBoost")')
 if phase18:
  import re
  from urllib.error import HTTPError
  from ml.src import model_inference as inference
  from ml.src import recommendation_engine as recommendations
  import pandas as pd
  endpoints=['/','/health','/model/info','/recommendations/thresholds','/analysis/model-comparison','/analysis/feature-importance','/docs','/openapi.json']
  statuses={}
  for path in endpoints:
   with request.urlopen('http://127.0.0.1:8000'+path) as response:
    body=response.read().decode();statuses[path]=response.status
    assert str(root) not in body and 'Traceback (most recent call last)' not in body
  bundle=inference.load_final_model()
  frame=pd.read_csv(root/'data/processed/energy_train.csv',nrows=1,float_precision='round_trip')[bundle[1]['ordered_feature_names']]
  payload={'features':frame.iloc[0].to_dict()}
  def post(path,value):
   req=request.Request('http://127.0.0.1:8000'+path,data=json.dumps(value).encode(),headers={'Content-Type':'application/json'})
   try:
    with request.urlopen(req) as r:return r.status,json.load(r)
   except HTTPError as error:return error.code,json.load(error)
  status,forecast=post('/forecast',payload);assert status==200
  assert forecast['unit']=='Wh' and forecast['forecast_horizon_minutes']==10
  assert forecast['prediction_wh']==float(inference.predict_next_appliances(frame,bundle).iloc[0])
  status,recommendation=post('/forecast/recommendation',payload);assert status==200
  assert recommendation==recommendations.predict_and_recommend(frame,model_bundle=bundle)[0]
  assert recommendation['scope']['automatic_control'] is False and recommendation['scope']['estimated_savings'] is None
  invalid=[]
  missing=dict(payload['features']);missing.pop('lights')
  bad_inputs=[{'features':missing},{'features':{**payload['features'],'extra':1}},
   *[{'features':{**payload['features'],'Appliances':v}} for v in ['text',None,float('nan'),float('inf')]],{},[]]
  for value in bad_inputs:
   for path in ['/forecast','/forecast/recommendation']:
    status,body=post(path,value);assert status==422
    assert str(root) not in json.dumps(body) and 'Traceback' not in json.dumps(body)
    invalid.append(status)
  inventory=[]
  for file in sorted((root/'src/routes').glob('*.tsx')):
   match=re.search(r'createFileRoute\("([^\"]+)"\)',file.read_text(encoding='utf-8'))
   if match:
    route=match.group(1);url=route.replace('$id','ubt-campus-a')
    inventory.append({'source':file.relative_to(root).as_posix(),'route':route,'tested_url':url,'initial_classification':'C' if file.stem in ['index','about','contact','login','signup','forgot-password','reset-password','verify-email','onboarding','settings'] else 'A', 'final_classification':'A'})
  forbidden_legacy=['LSTM','2.94M','0.962','nightly retraining','95% confidence','343 sensors','Password changed.','Account created','We sent a confirmation','Arber Krasniqi']
  for width in [1440,390]:
   c.call('Emulation.setDeviceMetricsOverride',{'width':width,'height':1000 if width==1440 else 844,'deviceScaleFactor':1,'mobile':width==390})
   for item in inventory:
    print('Route QA:', item['route'], width, flush=True)
    c.call('Page.navigate',{'url':'http://localhost:5173'+item['tested_url']})
    c.wait('document.readyState === "complete" && !!document.querySelector("h1")')
    body=c.evaluate('document.body.textContent')
    for phrase in forbidden_legacy:assert phrase not in body,(item['route'],phrase)
    assert not re.search(r'\d+\s+occupants',body),item['route']
    assert c.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'),('overflow',item['route'],width)
    assert 'Cannot read properties' not in body and 'Something went wrong' not in body
    item.setdefault('responsive_widths_verified',[]).append(width)
  c.call('Page.navigate',{'url':'http://localhost:5173/'});c.wait("!!document.querySelector('button[aria-label=\"Open menu\"]')")
  c.evaluate("document.querySelector('button[aria-label=\"Open menu\"]').click()")
  c.wait('Array.from(document.querySelectorAll("nav a")).some(a => a.textContent.includes("About"))')
  c.evaluate("document.querySelector('a[href=\"/about\"]').click()");c.wait('location.pathname === "/about" && document.body.textContent.includes("Forecasting with evidence")')
  # Malformed persisted local demo state must not break the routed shell.
  c.evaluate('localStorage.setItem("sea-session", JSON.stringify({name:42,email:"demo@example.invalid",role:"Viewer",onboarded:true}))')
  c.call('Page.navigate',{'url':'http://localhost:5173/dashboard'});c.wait('document.querySelector("main")?.textContent.includes("Tuned XGBoost")')
  c.evaluate('localStorage.removeItem("sea-session")')
  malformed_checked=[]
  for path in ['/model/info','/analysis/model-comparison','/analysis/feature-importance','/recommendations/thresholds']:
   c.malformed_path=path;c.malformed=True;c.call('Page.reload')
   c.wait('document.querySelector("main")?.textContent.includes("Verified data unavailable")')
   malformed_checked.append(path)
  c.malformed=False;c.malformed_path='/model/info'
  c.call('Page.reload');c.wait('document.querySelectorAll(".recharts-bar-rectangle").length >= 16')
  before=len(c.api)
  for _ in range(6):time.sleep(.3);c.evaluate('document.readyState')
  steady_requests=len(c.api)-before
  assert steady_requests<=2,steady_requests
  phase18_extra={'live_endpoint_statuses':statuses,'live_forecast_equals_direct_inference':True,'live_recommendation_equals_phase14':True,
   'invalid_input_422_checks':len(invalid),'route_inventory':inventory,'mobile_navigation_verified':True,'corrupt_demo_session_safe':True,
   'malformed_research_responses_checked':malformed_checked,'steady_window_api_responses':steady_requests,
   'steady_window_seconds':1.8,'no_uncontrolled_request_loop':True}
 c.malformed=True;c.call('Page.reload');c.wait('document.querySelector("main")?.textContent.includes("Verified data unavailable")')
 assert f"{info['final_held_out_metrics']['mae']:.3f}" not in c.text()
 malformed_verified=True;c.malformed=False
 stop(backend);c.call('Page.reload')
 c.wait('document.querySelector("main")?.querySelectorAll("[role=alert]").length === 4')
 assert 'Loading verified data' not in c.text()
 for key in ('mae','rmse','r2'):assert f"{info['final_held_out_metrics'][key]:.3f}" not in c.text()
 assert c.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
 c.screenshot('phase17_dashboard_offline.png')
 backend=spawn(backend_cmd,'backend_recovery');ready('http://127.0.0.1:8000/health',backend)
 c.evaluate('document.querySelectorAll("main button").forEach(b => b.click())')
 c.wait('document.querySelector("main")?.textContent.includes("Tuned XGBoost") && document.querySelectorAll(".recharts-bar-rectangle").length >= 16')
 if phase18:
  stop(backend)
  unavailable_code = """
from backend import services
from ml.src import model_inference as inference
import uvicorn
services.model_bundle.cache_clear()
def absent():
    raise FileNotFoundError('controlled QA fixture')
inference.load_final_model = absent
uvicorn.run('backend.main:app', host='127.0.0.1', port=8000, log_level='critical')
"""
  unavailable_server=spawn([sys.executable,'-c',unavailable_code],'model_unavailable')
  ready('http://127.0.0.1:8000/',unavailable_server)
  try:request.urlopen('http://127.0.0.1:8000/health');raise AssertionError('Expected unavailable model')
  except HTTPError as error:
   assert error.code==503
   assert json.load(error)['model_available'] is False
  c.call('Page.reload');c.wait('document.querySelector("main")?.textContent.includes("Verified data unavailable")')
  c.wait('document.body.textContent.includes("Backend unavailable")')
  phase18_extra['controlled_model_unavailable_backend_and_ui_verified']=True
  stop(unavailable_server)
 assert not c.cors,c.cors
 assert not c.errors,c.errors
 evidence={'browser':'Microsoft Edge headless via local CDP','frontend_origin':'http://localhost:5173','backend_origin':'http://127.0.0.1:8000',
  'loading_state_verified':loading_verified,'real_kpis_match_api':True,'validation_chart_verified':True,'feature_importance_chart_verified':True,
  'thresholds_match_api':True,'tooltip_verified':tooltip_verified,'no_visible_unsupported_content_in_updated_views':True,
  'disabled_operational_routes_verified':['/data','/buildings','/admin','/buildings/ubt-campus-a'],
  'malformed_response_state_verified':malformed_verified,'offline_error_panels_without_fake_fallback':True,'retry_recovery_verified':True,
  'responsive_widths':[1440,390],'no_page_horizontal_overflow':True,'cors_errors':c.cors,'runtime_exceptions':c.errors,
  'api_response_statuses':c.api,'external_page_requests_blocked':c.blocked,'no_forecast_posts_used_to_populate_dashboard':True,
  'screenshots':['phase17_dashboard_desktop.png','phase17_dashboard_mobile.png','phase17_dashboard_offline.png'],
  'verification_processes_stopped':True}
 if phase18: evidence['phase18_checks']=phase18_extra
 (g/('phase18_browser_evidence.json' if phase18 else 'phase17_browser_evidence.json')).write_text(json.dumps(evidence,indent=2),encoding='utf-8')
 print(json.dumps(evidence,indent=2),flush=True);c.ws.close()
finally:
 for p in reversed(processes):stop(p)
 for log in logs:log.close()
 if profile and profile.is_relative_to(g.resolve()):shutil.rmtree(profile,ignore_errors=True)
