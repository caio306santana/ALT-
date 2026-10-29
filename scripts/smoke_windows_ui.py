"""Real Windows UI Automation smoke on a window opened only for this test.

Opens the Windows Character Map (charmap.exe: a text field, buttons and a
checkbox), grants only that window, then reads, types and toggles through the
normal proposal/approval path, and finally lets the local model plan a task on
it. Terminals such as PowerShell are excluded by the driver, so they cannot host
the test window. The clipboard ("Copiar") is never used. Writes
docs/windows-ui-smoke.json. Real user windows are never granted."""
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from backend.api import create_app

MODEL=sys.argv[1] if len(sys.argv)>1 else 'qwen3.5:4b'
root=Path(__file__).resolve().parents[1];token='synthetic-windows-smoke-'+'x'*40
report={'model':MODEL,'window':'Mapa de Caracteres aberto pelo teste','steps':{}}
def log(name,data):report['steps'][name]=data;print(json.dumps({name:data},ensure_ascii=False)[:900],flush=True)
def act(client,body):
    proposal=client.post('/tools/propose',json=body);assert proposal.status_code==200,proposal.text
    response=client.post('/tools/approve/'+proposal.json()['id']);assert response.status_code==200,response.text
    return response.json()['result']
def wait(client,path,done,timeout):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        value=client.get(path).json()
        if done(value):return value
        time.sleep(1)
    return client.get(path).json()

# Open minimized and without focus so the owner's typing never lands in the test window.
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=7
window=subprocess.Popen(['charmap.exe'],startupinfo=startup)
try:
    with tempfile.TemporaryDirectory(prefix='alt-windows-smoke-',ignore_cleanup_errors=True) as directory:
        with TestClient(create_app(Path(directory),token),headers={'Authorization':'Bearer '+token}) as client:
            prefs=client.get('/settings').json();prefs['performance']='notebook';client.put('/settings',json=prefs)
            client.put('/permissions',json={'level':2})
            candidate=None
            for _ in range(20):
                candidate=next((c for c in client.get('/windows/candidates').json() if c['app'].lower()=='charmap'),None)
                if candidate:break
                time.sleep(1)
            assert candidate,'Janela de teste não apareceu'
            gid=client.post('/windows/grants',json={'candidate_id':candidate['candidate_id']}).json()['id']
            observed=act(client,{'tool':'windows_read','window_id':gid})
            log('read',{'title':observed['title'],'elements':[{k:e[k] for k in ('id','label','type','value')} for e in observed['elements']]})
            field=next(e for e in observed['elements'] if e['type']=='Edit')
            box=next(e for e in observed['elements'] if e['type']=='CheckBox')
            typed=act(client,{'tool':'windows_type','window_id':gid,'snapshot_id':observed['snapshot_id'],'target':field['id'],'content':'ALT'})['observation']
            log('type',{'field_value':next(e['value'] for e in typed['elements'] if e['type']=='Edit')})
            toggled=act(client,{'tool':'windows_invoke','window_id':gid,'snapshot_id':typed['snapshot_id'],'target':next(e['id'] for e in typed['elements'] if e['type']=='CheckBox')})['observation']
            log('invoke',{'elements_before':len(typed['elements']),'elements_after':len(toggled['elements']),'new_labels':sorted({e['label'] for e in toggled['elements']}-{e['label'] for e in typed['elements']})})
            stale=client.post('/tools/propose',json={'tool':'windows_invoke','window_id':gid,'snapshot_id':observed['snapshot_id'],'target':box['id']})
            log('stale_snapshot_refused',{'status':stale.status_code,'detail':stale.json().get('detail')})

            # Stage 2 + 4: the local model plans on the granted window; full access runs it.
            client.post('/permissions/grant',json={'level':4,'scope_ids':[]})
            start=time.monotonic()
            run=client.post('/tasks',json={'goal':'Na janela autorizada, leia a janela e digite Olá ALT no campo Caracteres a serem copiados.','model':MODEL,'window_id':gid}).json()
            run=wait(client,'/tasks/'+run['id'],lambda r:r['state']!='planning',900)
            planned={'state':run['state'],'notice':run['notice'],'plan':[(s['title'],s['action']['tool'],s['action'].get('target'),s['action'].get('content')) for s in (run['plan'] or {}).get('steps',[])],'planning_seconds':round(time.monotonic()-start,1)}
            if run['state']=='draft':
                client.post(f"/tasks/{run['id']}/start",json={'allow_replan':True})
                run=wait(client,'/tasks/'+run['id'],lambda r:r['state'] not in ('running','awaiting_approval','planning'),600)
            final=act(client,{'tool':'windows_read','window_id':gid})
            log('task_on_window',{**planned,'final_state':run['state'],'final_notice':run['notice'],'history':[{k:h[k] for k in ('step','tool','verified','reason')} for h in run['history']],
                'field_after':next((e['value'] for e in final['elements'] if e['type']=='Edit'),None),'seconds':round(time.monotonic()-start,1)})
finally:
    window.kill()
    (root/'docs'/'windows-ui-smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
