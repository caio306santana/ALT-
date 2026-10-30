import asyncio
import json
from pathlib import Path
import httpx
import pytest
from fastapi.testclient import TestClient
from backend.api import create_app
from backend.context import message_cost,tool_schema_cost,tokenizer_label,hermes_tokenizer_name
from backend.providers.ollama import Ollama
from test_backend import FixtureProvider,TOKEN,HEADERS,conversation,events

class HermesFixture(FixtureProvider):
    async def models(self):return [{'name':'hermes3:3b','size':2_000_000_000},{'name':'hermes3:8b','size':4_700_000_000}]

@pytest.mark.parametrize('model',['hermes3:3b','hermes3:8b'])
def test_hermes_chat_uses_its_own_tokenizer_and_preserves_persona(tmp_path,model):
    provider=HermesFixture();app=create_app(tmp_path,TOKEN,provider)
    with TestClient(app,headers=HEADERS) as client:
        prefs=client.get('/settings').json();prefs['performance']='notebook';prefs['personality']['instructions']='Preserve a prioridade Aurora.'
        client.put('/settings',json=prefs);client.put('/permissions',json={'level':2})
        body={'model':model,'content':'Quero discutir ideias e decisões do projeto com calma. '*40}
        estimate=client.post('/chat/estimate',json=body).json()
        assert estimate['fits'] and estimate['tokenizer']=='Hermes 3'
        assert len(body['content'].encode('utf-8'))>message_cost(body['content'],model)
        cid=conversation(client)
        response=client.post('/chat',json={**body,'conversation_id':cid})
        assert response.status_code==200,response.text
        assert events(response)[-1]['status']=='complete'
        name,messages=provider.contexts[-1];profile=provider.profiles[-1]
        assert name==model and 'Preserve a prioridade Aurora.' in messages[0]['content']
        assert sum(message_cost(m['content'],model) for m in messages)+tool_schema_cost(profile.get('tools'),model)+profile['options']['num_predict']+128<=4096
        # Catalog selection is explicit; no download occurs just for selecting.
        assert events(client.post('/setup/pull',json={'model':model}))[-1]['status']=='complete'

def test_hermes_aliases_and_unknown_models_do_not_use_qwen_tokenizer():
    text='Conversação em português: amanhã teremos uma decisão importante. '*30
    assert tokenizer_label('hermes3:latest')=='Hermes 3'
    assert message_cost(text,'hermes3:latest')==message_cost(text,'hermes3:8b')
    assert hermes_tokenizer_name('hermes3:70b') is None
    assert message_cost(text,'custom:hermes')==len(text.encode('utf-8'))+32

def test_hermes_native_tools_payload_omits_qwen_thinking_flag(monkeypatch):
    received=[]
    def handler(request):
        received.append(json.loads(request.content))
        return httpx.Response(200,content=json.dumps({'done':True,'message':{'tool_calls':[{'function':{'name':'alt_propose_action','arguments':{'tool':'open_app','app':'notepad'}}}]}})+'\n')
    original=httpx.AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    async def run():
        result=[row async for row in Ollama().stream('hermes3:3b',[{'role':'user','content':'fixture'}],asyncio.Event(),{'options':{'num_ctx':4096,'num_predict':768},'keep_alive':'1m','tools':[{'type':'function','function':{'name':'alt_propose_action'}}]})]
        assert result[0]['message']['tool_calls'][0]['function']['arguments']['app']=='notepad'
    asyncio.run(run())
    assert received[0]['model']=='hermes3:3b' and received[0]['tools']
    assert 'think' not in received[0]
