import asyncio
import json
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.api import create_app
from backend.memory.store import Store
from backend.providers.codex import CodexProvider,clean_env
from backend.providers.anthropic import AnthropicProvider,AnthropicConfig
from backend.providers.ollama import ProviderError
from backend.security.vault import Vault
from test_backend import FixtureProvider,TOKEN,HEADERS,conversation,send,events

class FixtureCodex:
    def __init__(self):self.calls=[]
    def status(self):return {'id':'codex','available':True,'name':'Fixture cloud','location':'cloud','billing':'subscription','reason':'test only'}
    async def stream(self,messages,cancel):
        self.calls.append(messages)
        yield {'message':{'content':'Resposta de contrato de teste'}}
        yield {'done':True,'eval_count':5,'prompt_eval_count':20}

def fixture_client(tmp_path):
    local,cloud=FixtureProvider(),FixtureCodex()
    app=create_app(tmp_path,TOKEN,local,cloud)
    return app,local,cloud,TestClient(app,headers=HEADERS)

def test_personality_real_prompt_persists_across_models(tmp_path):
    app,local,cloud,client=fixture_client(tmp_path)
    with client:
        settings=client.get('/settings').json()
        assert 'provocadora' in settings['personality']['tone']
        assert 'Calma' in settings['personality']['tone']
        settings['personality']['name']='ALT pessoal'
        settings['personality']['irony']=80
        assert client.put('/settings',json=settings).status_code==200
        cid=conversation(client);send(client,cid);send(client,cid,'fixture:9b')
        assert all('ALT pessoal' in ctx[0]['content'] and 'Ironia: 80/100' in ctx[0]['content'] for _,ctx in local.contexts)
        assert client.get('/settings').json()['personality']['name']=='ALT pessoal'

def test_memory_is_selected_not_automatically_injected(tmp_path):
    app,local,cloud,client=fixture_client(tmp_path)
    with client:
        memory=client.post('/memories',json={'title':'Projeto reservado','content':'Preferência XZY exclusiva','category':'projeto'}).json()
        cid=conversation(client);send(client,cid)
        assert 'XZY' not in local.contexts[-1][1][0]['content']
        response=client.post('/chat',json={'conversation_id':cid,'model':'fixture:4b','content':'Continue','memory_ids':[memory['id']]})
        assert response.status_code==200
        assert 'XZY' in local.contexts[-1][1][0]['content']
        export=client.get('/memories/export').json()
        assert export['memories'][0]['title']=='Projeto reservado'
        assert client.put('/memories/'+memory['id'],json={'title':'Corrigida','content':'Novo contexto','enabled':False}).status_code==200
        assert client.post('/chat',json={'conversation_id':cid,'model':'fixture:4b','content':'Teste','memory_ids':[memory['id']]}).status_code==400
        assert client.delete('/memories/'+memory['id']).status_code==200
        assert client.get('/memories').json()==[]

@pytest.mark.parametrize('content',['senha: segredo','password=example123','sk-'+'A'*30,'-----BEGIN RSA PRIVATE KEY-----'])
def test_known_secrets_are_rejected_from_memory(tmp_path,content):
    app,_,_,client=fixture_client(tmp_path)
    with client:
        assert client.post('/memories',json={'title':'teste','content':content}).status_code==400

def test_cloud_context_requires_exact_one_use_consent(tmp_path):
    app,_,cloud,client=fixture_client(tmp_path)
    with client:
        cid=conversation(client);body={'conversation_id':cid,'model':'cloud:codex','content':'Olá de teste'}
        assert client.post('/chat',json=body).status_code==403
        assert cloud.calls==[]
        preview=client.post('/chat/preview',json=body).json()
        assert preview['messages'][-1]['content']=='Olá de teste'
        assert 'provocadora' in preview['messages'][0]['content']
        authorized={**body,'consent_receipt':preview['consent_receipt']}
        assert events(client.post('/chat',json=authorized))[-1]['status']=='complete'
        assert len(cloud.calls)==1
        assert client.post('/chat',json=authorized).status_code==403

def test_cloud_consent_rejects_changed_personality_memory_or_message(tmp_path):
    app,_,cloud,client=fixture_client(tmp_path)
    with client:
        cid=conversation(client);body={'conversation_id':cid,'model':'cloud:codex','content':'Teste'}
        receipt=client.post('/chat/preview',json=body).json()['consent_receipt']
        assert client.post('/chat',json={**body,'content':'Outro texto','consent_receipt':receipt}).status_code==403
        receipt=client.post('/chat/preview',json=body).json()['consent_receipt']
        settings=client.get('/settings').json();settings['personality']['irony']=0;client.put('/settings',json=settings)
        assert client.post('/chat',json={**body,'consent_receipt':receipt}).status_code==403
        receipt=client.post('/chat/preview',json=body).json()['consent_receipt']
        client.post('/actions/stop');client.post('/actions/resume')
        assert client.post('/chat',json={**body,'consent_receipt':receipt}).status_code==403
        assert cloud.calls==[]

def test_personal_files_or_other_conversations_never_in_cloud_preview(tmp_path):
    (tmp_path/'personal.txt').write_text('NÃO ENVIAR',encoding='utf-8')
    app,_,cloud,client=fixture_client(tmp_path)
    with client:
        one,two=conversation(client),conversation(client)
        send(client,one,content='Outra conversa privada')
        preview=client.post('/chat/preview',json={'conversation_id':two,'model':'cloud:codex','content':'Teste'}).json()
        context=json.dumps(preview['messages'])
        assert 'NÃO ENVIAR' not in context and 'Outra conversa privada' not in context

def test_tool_write_needs_assisted_and_each_action_approval(tmp_path):
    app,_,_,client=fixture_client(tmp_path)
    with client:
        scope=client.get('/permissions').json()['scopes'][0]['id']
        body={'tool':'write_text','scope_id':scope,'path':'notas.md','content':'Texto aprovado'}
        proposal=client.post('/tools/propose',json=body).json()
        assert proposal['preview']['creates_file']
        assert not (tmp_path/'workspace'/'notas.md').exists()
        assert client.post('/tools/approve/'+proposal['id']).status_code==403
        assert client.put('/permissions',json={'level':2}).status_code==200
        response=client.post('/tools/approve/'+proposal['id'])
        assert response.status_code==200,response.text
        assert (tmp_path/'workspace'/'notas.md').read_text(encoding='utf-8')=='Texto aprovado'
        assert client.post('/tools/approve/'+proposal['id']).status_code==400
        assert client.get('/tools/history').json()[0]['status']=='complete'

@pytest.mark.parametrize('path',['../fora.txt','C:\\Windows\\win.ini','file.txt:secret','.env','.git/config','NUL.txt','a./notas.txt','private.key'])
def test_tool_scope_rejects_traversal_devices_and_sensitive_paths(tmp_path,path):
    app,_,_,client=fixture_client(tmp_path)
    with client:
        scope=client.get('/permissions').json()['scopes'][0]['id']
        response=client.post('/tools/propose',json={'tool':'read_text','scope_id':scope,'path':path})
        assert response.status_code==400,response.text

def test_tool_detects_file_changes_after_preview_and_revocation(tmp_path):
    app,_,_,client=fixture_client(tmp_path)
    target=tmp_path/'workspace'/'test.txt';target.write_text('Original',encoding='utf-8')
    with client:
        scope=client.get('/permissions').json()['scopes'][0]['id'];client.put('/permissions',json={'level':2})
        proposal=client.post('/tools/propose',json={'tool':'write_text','scope_id':scope,'path':'test.txt','content':'Novo'}).json()
        assert 'Original' in proposal['preview']['diff']
        target.write_text('Edição externa',encoding='utf-8')
        assert client.post('/tools/approve/'+proposal['id']).status_code==400
        assert target.read_text(encoding='utf-8')=='Edição externa'
        proposal=client.post('/tools/propose',json={'tool':'calculate','expression':'2+2'}).json()
        client.post('/permissions/revoke');client.put('/permissions',json={'level':2})
        assert client.post('/tools/approve/'+proposal['id']).status_code==400

def test_tool_calculator_is_not_a_python_executor(tmp_path):
    app,_,_,client=fixture_client(tmp_path)
    with client:
        for expression in ['__import__("os").getcwd()','2**99999','True','1/0','(1+']:
            assert client.post('/tools/propose',json={'tool':'calculate','expression':expression}).status_code==400
        proposal=client.post('/tools/propose',json={'tool':'calculate','expression':'(120+35)*2'}).json()
        client.put('/permissions',json={'level':2})
        assert client.post('/tools/approve/'+proposal['id']).json()['result']['value']==310

def test_game_mode_stops_and_unloads_only_selected_local_model(tmp_path):
    app,local,_,client=fixture_client(tmp_path)
    unloaded=[]
    async def unload(model):unloaded.append(model)
    local.unload=unload
    with client:
        settings=client.get('/settings').json();settings['model']='fixture:4b';client.put('/settings',json=settings)
        client.put('/permissions',json={'level':2})
        result=client.post('/game/enable').json()
        assert result['model_unloaded'] and unloaded==['fixture:4b']
        assert client.get('/health').json()['stopped']
        assert client.get('/health').json()['game_mode']
        assert client.get('/permissions').json()['level']==1
        client.post('/game/disable')
        assert not client.get('/health').json()['stopped']

def test_themes_and_extended_preferences_are_validated(tmp_path):
    app,_,_,client=fixture_client(tmp_path)
    with client:
        assert client.post('/themes',json={'name':'Pessoal','accent':'#123456'}).status_code==200
        assert client.get('/themes').json()[0]['name']=='Pessoal'
        settings=client.get('/settings').json();settings.update(appearance='light',scale=1.2,shortcut='Alt+F8')
        assert client.put('/settings',json=settings).status_code==200
        assert client.put('/settings',json={**settings,'shortcut':'Windows+R'}).status_code==422
        assert client.put('/settings',json={**settings,'secondary':'url(http://bad)'}).status_code==422
        assert client.put('/permissions',json={'level':4}).status_code==422

def test_codex_args_disable_tools_and_personal_discovery(tmp_path,monkeypatch):
    provider=CodexProvider(tmp_path);monkeypatch.setattr(provider,'executable',lambda:'codex.exe')
    args=provider.arguments('Personality test')
    assert '--ignore-user-config' in args and '--ignore-rules' in args and '--ephemeral' in args
    assert 'features.shell_tool=false' in args and 'features.hooks=false' in args
    assert 'features.plugins=false' in args and 'features.memories=false' in args
    assert 'permissions.alt_chat.network.enabled=false' in args
    assert 'forced_login_method="chatgpt"' in args
    assert any('":root"="deny"' in value for value in args)
    monkeypatch.setenv('ALT_SESSION_TOKEN','PRIVATE');monkeypatch.setenv('ANTHROPIC_API_KEY','PRIVATE')
    assert 'ALT_SESSION_TOKEN' not in clean_env() and 'ANTHROPIC_API_KEY' not in clean_env()

@pytest.mark.skipif(os.name!='nt',reason='Windows DPAPI')
def test_vault_encrypts_fake_key_and_never_puts_it_in_history(tmp_path):
    vault=Vault(tmp_path);key='sk-ant-test-'+'x'*40
    vault.save(key)
    assert key.encode() not in vault.path.read_bytes()
    assert vault.get()==key and not vault.validated()
    vault.validate(['fixture-model']);assert vault.validated() and vault.model_available('fixture-model')
    vault.clear();assert not vault.configured()

def test_cloud_budget_blocks_before_network_and_survives_restart(tmp_path):
    class FakeVault:
        def configured(self):return True
        def validated(self):return True
        def model_available(self,model):return True
    store=Store(tmp_path/'test.sqlite3');provider=AnthropicProvider(store,FakeVault())
    cfg=AnthropicConfig(enabled=True,model='fixture',input_usd_per_million=1,output_usd_per_million=1,request_limit_usd=.01,session_limit_usd=.003,daily_limit_usd=.003,monthly_limit_usd=.003)
    provider.save(cfg);messages=[{'role':'user','content':'Teste'}]
    provider.reserve(messages)
    with pytest.raises(ProviderError) as error:provider.reserve(messages)
    assert error.value.code=='budget'
    provider=AnthropicProvider(store,FakeVault())
    with pytest.raises(ProviderError):provider.reserve(messages)
    store.db.close()

def test_api_config_does_not_break_general_settings(tmp_path):
    app,_,_,client=fixture_client(tmp_path)
    with client:
        assert client.put('/providers/anthropic',json={'enabled':False}).status_code==200
        assert client.get('/settings').status_code==200
        cid=conversation(client)
        assert client.post('/chat/preview',json={'conversation_id':cid,'model':'cloud:anthropic','content':'No network'}).status_code==409

def test_oversized_selected_memory_never_silently_truncates_personality(tmp_path):
    app,local,_,client=fixture_client(tmp_path)
    with client:
        settings=client.get('/settings').json();settings['performance']='notebook';client.put('/settings',json=settings)
        memory=client.post('/memories',json={'title':'Grande','content':'A'*6000}).json()
        cid=conversation(client)
        response=client.post('/chat',json={'conversation_id':cid,'model':'fixture:4b','content':'Continue','memory_ids':[memory['id']]})
        assert response.status_code==400 and 'contexto' in response.json()['detail']
        assert local.contexts==[]
        assert client.get(f'/conversations/{cid}/messages').json()==[]

def test_expired_permission_and_expired_proposal_cannot_execute(tmp_path):
    app,_,_,client=fixture_client(tmp_path)
    with client:
        client.put('/permissions',json={'level':2})
        proposal=client.post('/tools/propose',json={'tool':'calculate','expression':'2+2'}).json()
        app.state.tools.until=0
        assert client.post('/tools/approve/'+proposal['id']).status_code==403
        client.put('/permissions',json={'level':2})
        pending=app.state.tools.pending[proposal['id']]
        app.state.tools.pending[proposal['id']]=(0,pending[1],pending[2])
        assert client.post('/tools/approve/'+proposal['id']).status_code==400

def test_scope_rejects_existing_symbolic_link(tmp_path):
    app,_,_,client=fixture_client(tmp_path)
    outside=tmp_path/'outside';outside.mkdir();(outside/'secret.txt').write_text('private')
    link=tmp_path/'workspace'/'linked'
    try:link.symlink_to(outside,target_is_directory=True)
    except OSError:pytest.skip('This Windows user cannot create symbolic links')
    with client:
        scope=client.get('/permissions').json()['scopes'][0]['id']
        assert client.post('/tools/propose',json={'tool':'read_text','scope_id':scope,'path':'linked/secret.txt'}).status_code==400
