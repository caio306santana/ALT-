import json
from fastapi.testclient import TestClient
from backend.remote import Devices,gateway_app,Push,COOKIE
from backend.tools.service import ToolProposal
from test_features import fixture_client,TOKEN

class Clock:
    def __init__(self):self.t=1000.0
    def __call__(self):return self.t

def phone(app,tmp_path,host='pc.tail1234.ts.net'):
    app.state.store.set_settings({'remote_host':host,'remote_enabled':True})
    remote=app.state.remote
    gateway=gateway_app(app,TOKEN,remote.devices,remote.push,app.state.store.settings,static_dir=tmp_path)
    (tmp_path/'index.html').write_text('<!doctype html><title>ALT</title>',encoding='utf-8')
    client=TestClient(gateway,base_url=f'https://{host}')
    client.headers['Origin']=f'https://{host}'
    return client

def paired(app,client):
    code=app.state.remote.devices.pair_code()['code']
    response=client.post('/pair',json={'code':code,'name':'iPhone do Caio'})
    assert response.status_code==200 and COOKIE in response.cookies
    return response

def test_pairing_codes_are_single_use_expire_and_lock_after_failures(tmp_path):
    from backend.memory.store import Store
    clock=Clock();devices=Devices(Store(tmp_path/'s.sqlite3'),clock)
    code=devices.pair_code()['code']
    did,token=devices.claim(code,'iPhone');assert devices.device(token)['id']==did
    try:devices.claim(code,'iPhone');assert False
    except PermissionError:pass
    late=devices.pair_code()['code'];clock.t+=121
    try:devices.claim(late,'iPhone');assert False
    except PermissionError:pass
    for _ in range(3):
        try:devices.claim('ERRADO12','x')
        except PermissionError:pass
    fresh=devices.pair_code()['code']
    try:devices.claim(fresh,'x');assert False,'locked after 5 failures'
    except PermissionError as exc:assert 'tentativas' in str(exc)
    # Tokens are stored hashed, never in clear.
    assert token not in json.dumps(devices.store.rows('SELECT * FROM remote_devices'))

def test_the_gateway_checks_host_origin_and_the_device_cookie(tmp_path):
    app,local,_,client=fixture_client(tmp_path)
    with client:
        gateway=phone(app,tmp_path)
        assert gateway.get('/api/me').status_code==401
        assert gateway.get('/').status_code==200
        evil=TestClient(gateway.app,base_url='https://evil.example');assert evil.get('/').status_code==403
        assert gateway.post('/pair',json={'code':'x'},headers={'Origin':'https://evil.example'}).status_code==403
        # The desktop's bearer token is worthless here.
        assert gateway.get('/api/me',headers={'Authorization':'Bearer '+TOKEN}).status_code==401
        paired(app,gateway)
        assert gateway.get('/api/me').json()['device']=='iPhone do Caio'
        did=app.state.remote.devices.list()[0]['id'];app.state.remote.devices.revoke(did)
        assert gateway.get('/api/me').status_code==401

def test_nothing_runs_by_itself_from_the_phone_and_commands_are_pc_only(tmp_path):
    app,local,_,client=fixture_client(tmp_path)
    async def model_stream(model,messages,cancel,profile=None):
        yield {'message':{'tool_calls':[{'function':{'name':'alt_propose_action','arguments':{'tool':'calculate','expression':'2+2'}}}]}}
        yield {'done':True,'eval_count':3}
    local.stream=model_stream
    with client:
        settings=client.get('/settings').json();settings['model']='fixture:4b';client.put('/settings',json=settings)
        scope=client.get('/permissions').json()['scopes'][0]['id'];client.post('/permissions/grant',json={'level':4,'scope_ids':[scope]})
        gateway=phone(app,tmp_path);paired(app,gateway)
        cid=gateway.post('/api/conversations').json()['id']
        reply=gateway.post('/api/chat',json={'conversation_id':cid,'content':'quanto é 2+2'}).json()
        # In full access the desktop would run this alone; from the phone it is a card.
        assert reply['proposals'] and app.state.store.rows("SELECT status FROM actions")[0]['status']=='proposed'
        assert gateway.post(f"/api/actions/{reply['proposals'][0]['id']}/approve").json()['result']['value']==4
        command=app.state.tools.proposal(ToolProposal(tool='run_command',command='Get-Date'),cid)
        assert gateway.post(f"/api/actions/{command['id']}/approve").status_code==403

def test_push_subscriptions_are_validated_and_vapid_keys_stay_local(tmp_path):
    from backend.memory.store import Store
    store=Store(tmp_path/'s.sqlite3');Devices(store);push=Push(tmp_path/'remote',store)
    assert len(push.public_key())>80 and (tmp_path/'remote'/'vapid.pem').is_file()
    try:push.subscribe('d1',{'endpoint':'http://insecure.example','keys':{}});assert False
    except ValueError:pass
    import base64,os
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
    receiver=ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)
    subscription={'endpoint':'https://web.push.apple.com/abc','keys':{'p256dh':base64.urlsafe_b64encode(receiver).decode().rstrip('='),'auth':base64.urlsafe_b64encode(os.urandom(16)).decode().rstrip('=')}}
    push.subscribe('d1',subscription)
    body,headers=push.payload(subscription,'ALT','Resumo da manhã pronto')
    assert headers['Content-Encoding']=='aes128gcm' and headers['Authorization'].startswith('vapid t=') and b'Resumo' not in body
    store.db.close()

def test_mobile_stream_uses_the_same_validation_and_never_auto_executes(tmp_path):
    app,local,_,client=fixture_client(tmp_path)
    with client:
        client.put('/permissions',json={'level':2})
        gateway=phone(app,tmp_path);paired(app,gateway)
        cid=gateway.post('/api/conversations').json()['id']
        # A direct launch works without a model and remains a proposal on iPhone.
        response=gateway.post('/api/chat/stream',json={'conversation_id':cid,'content':'abre o bloco de notas','origin':'desktop','model':'cloud:anthropic'})
        assert response.status_code==200,response.text
        rows=[json.loads(line) for line in response.text.splitlines() if line]
        assert rows[0]['execution']=='direct' and rows[-1]['status']=='complete'
        assert any(row['type']=='tool_proposal' for row in rows)
        assert not any(row['type']=='tool_result' for row in rows)
        assert local.contexts==[]
        assert gateway.get('/api/models').json()['models'][0]['info']['capabilities']['vision'] is None
        assert gateway.post('/api/chat/cancel',json={'conversation_id':cid}).status_code==200
        assert gateway.post('/api/chat/cancel',json={'conversation_id':'../actions/resume'}).status_code==400
        # Native/local handler still validates body and conversations.
        assert gateway.post('/api/chat/stream',json={'conversation_id':'missing','content':'oi'}).status_code==404

def test_phone_with_cloud_selected_and_no_local_model_gets_clear_error(tmp_path):
    app,local,_,client=fixture_client(tmp_path)
    async def empty():return []
    local.models=empty
    with client:
        app.state.store.set_settings({'model':'cloud:anthropic'})
        gateway=phone(app,tmp_path);paired(app,gateway)
        response=gateway.post('/api/chat/stream',json={'conversation_id':'x','content':'oi'})
        assert response.status_code==409 and 'modelo local' in response.json()['detail']

def test_gateway_forwards_first_chunk_before_the_provider_finishes(tmp_path):
    import asyncio
    app,local,_,client=fixture_client(tmp_path)
    with client:
        app.state.store.set_settings({'model':'fixture:4b'})
        gateway=phone(app,tmp_path);paired(app,gateway)
        cid=gateway.post('/api/conversations').json()['id']
        async def run():
            release=asyncio.Event();seen=asyncio.Event();never_disconnect=asyncio.Event();chunks=[];sent=False
            async def source(*args,**kwargs):
                yield {'message':{'content':'primeiro'}}
                await release.wait()
                yield {'done':True,'eval_count':1}
            local.stream=source
            body=json.dumps({'conversation_id':cid,'content':'oi'}).encode()
            async def receive():
                nonlocal sent
                if not sent:sent=True;return {'type':'http.request','body':body,'more_body':False}
                await never_disconnect.wait();return {'type':'http.disconnect'}
            async def send(message):
                if message['type']=='http.response.body':
                    chunks.append(message.get('body',b''))
                    if b'primeiro' in b''.join(chunks):seen.set()
            scope={'type':'http','asgi':{'version':'3.0','spec_version':'2.4'},'http_version':'1.1','method':'POST','scheme':'https','path':'/api/chat/stream','raw_path':b'/api/chat/stream','query_string':b'',
                'headers':[(b'host',b'pc.tail1234.ts.net'),(b'origin',b'https://pc.tail1234.ts.net'),(b'content-type',b'application/json'),(b'cookie',(COOKIE+'='+gateway.cookies.get(COOKIE)).encode())],
                'client':('127.0.0.1',10000),'server':('pc.tail1234.ts.net',443),'root_path':''}
            task=asyncio.create_task(gateway.app(scope,receive,send))
            try:
                await asyncio.wait_for(seen.wait(),3)
                assert not task.done(),'Response must reach the phone while generation is in progress'
            finally:
                release.set();await asyncio.wait_for(task,3)
            assert b'"status": "complete"' in b''.join(chunks)
        asyncio.run(run())

def test_tailscale_does_not_replace_another_service_or_public_funnel():
    from backend.remote import Tailscale
    assert Tailscale.owns_or_empty({},47823)
    assert Tailscale.owns_or_empty({'TCP':{'443':{'HTTPS':True}},'Web':{'pc.tail.ts.net:443':{'Handlers':{'/':{'Proxy':'http://127.0.0.1:47823'}}}}},47823)
    assert not Tailscale.owns_or_empty({'Web':{'pc.tail.ts.net:443':{'Handlers':{'/':{'Proxy':'http://127.0.0.1:3000'}}}}},47823)
    assert not Tailscale.owns_or_empty({'AllowFunnel':{'pc.tail.ts.net:443':True}},47823)
    assert not Tailscale.owns_or_empty({'TCP':{'443':{'TCPForward':'localhost:2222'}}},47823)
