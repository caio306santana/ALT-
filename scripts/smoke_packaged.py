"""Validate the packaged backend runtime without relying on installed Python libraries."""
import json
import os
import secrets
import subprocess
import tempfile
import time
from pathlib import Path
import httpx

root=Path(__file__).resolve().parents[1]
executable=root/'release'/'win-unpacked'/'resources'/'backend'/'alt-backend.exe'
token=secrets.token_hex(32)
with tempfile.TemporaryDirectory(prefix='alt-packaged-') as directory:
    env={**os.environ,'ALT_SESSION_TOKEN':token,'ALT_DATA_DIR':directory,'ALT_PARENT_PID':str(os.getpid())}
    child=subprocess.Popen([str(executable)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',env=env,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        line=child.stdout.readline()
        assert line.startswith('ALT_READY:'),(line,child.stderr.read())
        port=json.loads(line.split(':',1)[1])['port']
        with httpx.Client(base_url=f'http://127.0.0.1:{port}',trust_env=False,timeout=20) as client:
            for _ in range(30):
                try:
                    response=client.get('/health',headers={'Authorization':'Bearer '+token})
                    break
                except httpx.ConnectError: time.sleep(.1)
            assert response.status_code==200,response.text
            assert client.get('/health').status_code==401
            headers={'Authorization':'Bearer '+token}
            cid=client.post('/conversations',headers=headers).json()['id']
            assert client.get(f'/conversations/{cid}/messages',headers=headers).json()==[]
            prefs=client.get('/settings',headers=headers).json()
            assert 'provocadora' in prefs['personality']['tone']
            memory=client.post('/memories',headers=headers,json={'title':'Synthetic package check','content':'Temporary fixture only'}).json()
            assert memory['id'] in [m['id'] for m in client.get('/memories',headers=headers).json()]
            proposal=client.post('/tools/propose',headers=headers,json={'tool':'calculate','expression':'(10+5)*2'}).json()
            assert client.post('/tools/approve/'+proposal['id'],headers=headers).status_code==403
            client.put('/permissions',headers=headers,json={'level':2})
            authorization=client.get('/permissions',headers=headers).json()
            assert authorization['persistent'] and authorization['expires_in'] is None
            assert client.post('/tools/approve/'+proposal['id'],headers=headers).json()['result']['value']==30
            client.post('/permissions/revoke',headers=headers)
            system=client.get('/system',headers=headers).json()
            assert system['ram']['total']>0
            print(json.dumps({'packaged_backend':'ok','health':response.json(),'cpu':system['cpu']['name'],'profile':system.get('performance',{}).get('effective'),'authentication':'401 without token','conversation_storage':'ok','personality_memory_permissions_tools':'ok'},ensure_ascii=False))
    finally:
        child.terminate();child.wait(timeout=10)
