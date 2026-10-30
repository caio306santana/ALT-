import asyncio
import json
import httpx
import pytest
from backend.model_info import normalize_info,effective_profile
from backend.providers.ollama import Ollama
from test_context_automatic import setup_app
from test_backend import conversation,events

def test_missing_metadata_remains_unknown_and_limits_are_not_guessed():
    for value in ({},None,{'model_info':{'llama.context_length':True}}, {'model_info':{'a.context_length':4096,'b.context_length':8192}}):
        info=normalize_info(value)
        assert info['max_context'] is None and all(v is None for v in info['capabilities'].values())
    info=normalize_info({'capabilities':['completion','tools'],'model_info':{'general.architecture':'llama','llama.context_length':131072},'thinking':{'values':[False],'default':False}})
    assert info['capabilities']=={'text':True,'vision':False,'tools':True,'thinking':False}
    assert info['max_context']==131072 and info['thinking_values']==[False]

def test_profile_never_grows_to_the_advertised_maximum():
    profile={'effective':'notebook','options':{'num_ctx':4096,'num_predict':768}}
    assert effective_profile(profile,{'max_context':131072})['options']['num_ctx']==4096
    limited=effective_profile(profile,{'max_context':2048})
    assert limited['context_limited_by_model'] and limited['options']['num_ctx']==2048
    assert profile['options']['num_ctx']==4096
    tiny=effective_profile(profile,{'max_context':512})
    assert tiny['options']['num_ctx']-min(tiny['options']['num_predict'],768)-128>=0

def test_metadata_cache_refresh_and_replaced_digest(monkeypatch):
    calls=[];original=httpx.AsyncClient
    def handler(request):
        calls.append(json.loads(request.content)['model'])
        return httpx.Response(200,json={'capabilities':['completion','vision','tools','thinking'],'model_info':{'general.architecture':'qwen35','qwen35.context_length':262144},'thinking':{'values':[True,False],'default':True}})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    async def run():
        provider=Ollama()
        first=await provider.describe('qwen3.5:4b',fingerprint='digest-1')
        assert first['capabilities']['thinking'] and first['thinking_default'] is True
        await provider.describe('qwen3.5:4b',fingerprint='digest-1');assert len(calls)==1
        await provider.describe('qwen3.5:4b',fingerprint='digest-2');assert len(calls)==2
        await provider.describe('qwen3.5:4b',refresh=True);assert len(calls)==3
        assert 'vision' in await provider.capabilities('qwen3.5:4b') and len(calls)==3
    asyncio.run(run())

def test_info_failure_does_not_hide_installed_models(monkeypatch,tmp_path):
    app,provider,client=setup_app(tmp_path,monkeypatch)
    async def unknown(*_,**__):return normalize_info(None)
    provider.describe=unknown
    with client:
        rows=client.get('/models?refresh=true').json()['models']
        assert len(rows)==2 and rows[0]['info']['capabilities']['vision'] is None
        assert rows[0]['info']['active_context'] in (4096,8192)

def test_reported_limits_and_tools_apply_to_the_actual_payload(tmp_path,monkeypatch):
    app,provider,client=setup_app(tmp_path,monkeypatch)
    async def details(*_,**__):return normalize_info({'capabilities':['completion'],'model_info':{'general.architecture':'qwen35','qwen35.context_length':2048}})
    provider.describe=details
    with client:
        prefs=client.get('/settings').json();prefs['performance']='desktop';client.put('/settings',json=prefs)
        client.put('/permissions',json={'level':2});cid=conversation(client)
        estimate=client.post('/chat/estimate',json={'model':'qwen3.5:4b','content':'Oi','conversation_id':cid}).json()
        assert estimate['total_context']==2048 and estimate['model_info']['max_context']==2048
        assert estimate['components']['tools']==0
        response=client.post('/chat',json={'model':'qwen3.5:4b','content':'Oi','conversation_id':cid})
        assert response.status_code==200,response.text
        assert events(response)[-1]['status']=='complete'
        assert provider.profile['options']['num_ctx']==2048 and not provider.profile.get('tools')
