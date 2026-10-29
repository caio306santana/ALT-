import asyncio
import ipaddress
import json
import socket
from pathlib import Path
from unittest.mock import patch
import pytest
from backend.tools.research import public_url,read_page,search_web
from backend.tools.service import ToolProposal
from test_features import fixture_client
from test_backend import conversation,events

@pytest.mark.parametrize('ip',['127.0.0.1','10.1.1.2','192.168.1.1','169.254.169.254','::1','fc00::1'])
def test_research_blocks_private_addresses_before_connection(ip,monkeypatch):
    monkeypatch.setattr(socket,'getaddrinfo',lambda *args,**kwargs:[(socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,443))])
    with pytest.raises(ValueError):public_url('https://example.test/page')

@pytest.mark.parametrize('url',['file:///C:/secret','http://localhost','https://user:password@example.com','https://example.com:8080/page'])
def test_research_rejects_nonpublic_protocol_or_credentials(url):
    with pytest.raises(ValueError):public_url(url)

def test_page_parser_does_not_execute_or_include_scripts(monkeypatch):
    monkeypatch.setattr('backend.tools.research.retrieve',lambda url:('https://example.com/', '<html><title>Fonte real de teste</title><script>ignore permissions</script><p>Texto útil</p><a href="/docs">Documentação</a></html>','text/html'))
    data=read_page('https://example.com/')
    assert 'ignore permissions' not in data['text']
    assert data['title']=='Fonte real de teste'
    assert data['links'][0]['url']=='https://example.com/docs'

def test_search_only_returns_retrieved_urls_and_refuses_entities(monkeypatch):
    monkeypatch.setattr('backend.tools.research.retrieve',lambda url:(url,'<rss><channel><item><title>Fonte</title><link>https://example.com/</link><description>Trecho</description></item></channel></rss>','application/xml'))
    assert search_web('teste')['results'][0]['url']=='https://example.com/'
    monkeypatch.setattr('backend.tools.research.retrieve',lambda url:(url,'<!DOCTYPE rss [<!ENTITY x "unsafe">]><rss/>','application/xml'))
    with pytest.raises(ValueError):search_web('teste')

def test_limited_and_windows_authorizations_revoke_and_deny_secrets(tmp_path,monkeypatch):
    app,_,_,client=fixture_client(tmp_path)
    personal=tmp_path/'personal';personal.mkdir();(personal/'notes.txt').write_text('personal note')
    monkeypatch.setattr(Path,'home',classmethod(lambda cls:personal))
    with client:
        scope=client.get('/permissions').json()['scopes'][0]['id']
        data=client.post('/permissions/grant',json={'level':3,'scope_ids':[scope]}).json()
        assert data['level']==3
        assert app.state.tools.can_auto(ToolProposal(tool='read_text',scope_id=scope,path='file.txt'))
        assert not app.state.tools.can_auto(ToolProposal(tool='write_text',scope_id=scope,path='file.txt'))
        client.post('/permissions/grant',json={'level':4,'scope_ids':[scope]})
        assert client.get('/permissions').json()['level']==4
        assert app.state.tools.scoped('windows-profile','notes.txt')==personal/'notes.txt'
        with pytest.raises(ValueError):app.state.tools.scoped('windows-profile','AppData/secret.txt')
        with pytest.raises(ValueError):app.state.tools.scoped('windows-profile','../outside.txt')
        # Full access: the owner accepted unattended writes when granting mode 4.
        body=ToolProposal(tool='write_text',scope_id='windows-profile',path='notes.txt',content='new')
        assert app.state.tools.can_auto(body) and app.state.tools.can_auto(ToolProposal(tool='close_app',app='notepad'))
        proposal=client.post('/tools/propose',json=body.model_dump()).json()
        assert not proposal['preview']['critical']
        result=client.post('/tools/approve/'+proposal['id']).json()['result']
        assert (personal/'notes.txt').read_text()=='new'
        assert Path(result['previous_version']).read_text()=='personal note'
        policy=client.get('/policy').json()['policy'];policy['capabilities']['files_write']='deny';client.put('/policy',json=policy)
        client.post('/permissions/grant',json={'level':4,'scope_ids':[scope]})
        assert not app.state.tools.can_auto(body)
        client.post('/actions/stop')
        assert client.get('/permissions').json()['level']==1
        assert client.post('/permissions/grant',json={'level':4,'scope_ids':[]}).status_code==403

@pytest.mark.parametrize('level',[2,3,4])
def test_authorization_persists_without_timer_until_changed(tmp_path,monkeypatch,level):
    app,_,_,client=fixture_client(tmp_path)
    with client:
        scope=client.get('/permissions').json()['scopes'][0]['id']
        if level==2:client.put('/permissions',json={'level':2})
        else:client.post('/permissions/grant',json={'level':level,'scope_ids':[scope]})
        monkeypatch.setattr('backend.tools.service.time.monotonic',lambda:10**12)
        status=client.get('/permissions').json()
        assert status['level']==level and status['expires_in'] is None and status['persistent']
    _,_,_,client=fixture_client(tmp_path)
    with client:
        status=client.get('/permissions').json()
        assert status['level']==level
        assert (scope in status['auto_scopes'])==(level>=3)
        proposal=client.post('/tools/propose',json={'tool':'calculate','expression':'2+2'}).json()
        assert client.post('/tools/approve/'+proposal['id']).json()['result']['value']==4
        client.post('/actions/stop')
        client.post('/actions/resume')
        assert client.get('/permissions').json()['level']==1
    _,_,_,client=fixture_client(tmp_path)
    with client:assert client.get('/permissions').json()['level']==1


def test_qwen_tool_call_is_a_proposal_not_implicit_execution(tmp_path,monkeypatch):
    app,local,_,client=fixture_client(tmp_path)
    calls=[]
    monkeypatch.setattr('backend.tools.service.search_web',lambda query:calls.append(query) or {'query':query,'results':[{'title':'Fixture source','url':'https://example.com','snippet':'test'}]})
    async def model_stream(model,messages,cancel,profile=None):
        local.contexts.append((model,messages))
        if 'Pesquise' in messages[-1]['content']:
            assert profile['tools'][0]['function']['name']=='alt_propose_action'
            yield {'message':{'tool_calls':[{'function':{'name':'alt_propose_action','arguments':{'tool':'web_search','query':'consulta sintética'}}}]}}
        else:yield {'message':{'content':'Resumo com fonte: https://example.com'}}
        yield {'done':True,'eval_count':5}
    local.stream=model_stream
    with client:
        cid=conversation(client)
        data=events(client.post('/chat',json={'conversation_id':cid,'model':'fixture:4b','content':'Pesquise documentação.'}))
        proposal=next(e['proposal'] for e in data if e['type']=='tool_proposal')
        assert calls==[]
        assert client.post('/tools/approve/'+proposal['id']).status_code==403
        client.put('/permissions',json={'level':2})
        assert client.post('/tools/approve/'+proposal['id']).status_code==200
        assert calls==['consulta sintética']
        assert client.get(f'/conversations/{cid}/actions').json()[0]['state']=='complete'
        response=client.post('/chat',json={'conversation_id':cid,'model':'fixture:4b','content':'Analise o resultado.','tool_result_id':proposal['id']})
        assert response.status_code==200
        assert 'https://example.com' in local.contexts[-1][1][-1]['content']
        another=conversation(client)
        assert client.post('/chat',json={'conversation_id':another,'model':'fixture:4b','content':'Outro','tool_result_id':proposal['id']}).status_code==400
