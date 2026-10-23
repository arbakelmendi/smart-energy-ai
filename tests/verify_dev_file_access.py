"""Probe only self-created harmless files for Vite private-file exposure; no real DB read."""
from pathlib import Path
import json,os,secrets,shutil,socket,subprocess,time,urllib.request,urllib.error
ROOT=Path(__file__).resolve().parents[1]
GENERATED=ROOT/'ml/results/generated'

def verify():
    nonce=secrets.token_hex(8);marker=('private-file-probe-'+nonce).encode()
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    paths=[ROOT/('phase29-probe-'+nonce+suffix) for suffix in ['.db','.db-wal','.db-shm','.sqlite3','.sqlite3-wal','.pem']]
    paths.append(GENERATED/('phase29-probe-'+nonce+'.log'))
    paths.append(ROOT/('.env.phase29-probe-'+nonce))
    for path in paths:
        resolved=path.resolve()
        assert resolved.parent in [ROOT.resolve(),GENERATED.resolve()] and resolved.name.startswith(('phase29-probe-','.env.phase29-probe-'))
        with path.open('xb') as stream:stream.write(marker)
    process=None;result={}
    def request(path):
        try:
            with urllib.request.urlopen(f'http://localhost:{port}'+path,timeout=15) as response:return response.status,response.read()
        except urllib.error.HTTPError as error:return error.code,error.read()
    try:
        with (GENERATED/'phase29_dev_file_access.log').open('w',encoding='utf-8') as log:
            process=subprocess.Popen([shutil.which('npm.cmd'),'run','dev','--','--host','localhost','--port',str(port),'--strictPort'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            end=time.monotonic()+55
            while time.monotonic()<end:
                if process.poll() is not None:raise RuntimeError('Probe frontend exited')
                try:
                    status,body=request('/')
                    if status==200:break
                except OSError:pass
                time.sleep(.2)
            else:raise RuntimeError('Probe frontend startup timeout')
            results=[]
            for path in paths:
                relative='/'+path.relative_to(ROOT).as_posix()
                for variant,url in [('direct',relative),('raw',relative+'?raw'),('url-import',relative+'?url'),('absolute-fs','/@fs/'+path.resolve().as_posix())]:
                    status,body=request(url)
                    results.append({'path_class':'generated QA log' if path.suffix=='.log' else 'env' if path.name.startswith('.env.') else path.suffix,'variant':variant,'status':status,'sentinel_disclosed':marker in body})
            normal={}
            for url in ['/','/login','/src/lib/api/client.ts','/@vite/client']:
                status,_=request(url);normal[url]=status
            result={'passed':all(not row['sentinel_disclosed'] and row['status'] in [403,404] for row in results) and all(status==200 for status in normal.values()),'private_probe_results':results,'normal_pages_and_modules':normal,'scope':'Only newly-created harmless sentinels, not developer DBs or credentials','default_developer_DB_touched':False}
    finally:
        if process is not None and process.poll() is None:
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW);process.wait(timeout=10)
        for path in paths:
            assert path.resolve().parent in [ROOT.resolve(),GENERATED.resolve()] and path.name.startswith(('phase29-probe-','.env.phase29-probe-'))
            path.unlink(missing_ok=True)
    result['own_process_and_sentinels_removed']=True
    return result

if __name__=='__main__':
    result=verify();(GENERATED/'phase29_dev_file_access.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)
