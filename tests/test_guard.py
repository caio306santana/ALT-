import json
import pytest
from backend.security.guard import RememberedApprovals,sensitive_reason
from backend.memory.store import Store
from backend.tools.service import ToolProposal
from test_features import fixture_client
from test_backend import conversation

def test_only_low_risk_targets_can_be_allowed_for_good(tmp_path):
    store=Store(tmp_path/'s.sqlite3');remembered=RememberedApprovals(store)
    remembered.remember('open_url',{'url':'https://www.youtube.com/watch?v=1'})
    assert remembered.allows('open_url',{'url':'https://youtube.com/'})
    assert not remembered.allows('open_url',{'url':'https://example.com/'})
    for tool,payload in [('run_command',{'command':'Get-Date'}),('close_app',{'app':'x'}),('write_text',{'path':'a.txt'}),('download_file',{'url':'https://a.b/c'})]:
        with pytest.raises(ValueError):remembered.remember(tool,payload)
    store.db.close()

def test_a_remembered_site_opens_by_itself_in_approval_mode(tmp_path):
    app,local,_,client=fixture_client(tmp_path)
    with client:
        tools=app.state.tools;client.put('/permissions',json={'level':2})
        body=ToolProposal(tool='open_url',url='https://youtube.com')
        assert not tools.can_auto(body)
        proposal=tools.proposal(ToolProposal(tool='open_url',url='youtube.com'))
        assert client.post('/tools/remember/'+proposal['id']).json()=={'tool':'open_url','target':'youtube.com'}
        assert tools.can_auto(body)
        rid=client.get('/approvals/remembered').json()[0]['id'];client.delete('/approvals/remembered/'+rid)
        assert not tools.can_auto(body)

def test_sensitive_content_is_detected():
    assert 'credencial' in sensitive_reason('api_key = sk-abcdefghijklmnopqrstuv')
    assert 'CPF' in sensitive_reason('cliente 123.456.789-09')
    assert 'cartão' in sensitive_reason('cartão 4111 1111 1111 1111')
    assert 'sistema' in sensitive_reason('<|im_start|>system')
    assert sensitive_reason('relatório trimestral de vendas')==''

def test_after_reading_a_secret_sites_wait_for_the_card_even_in_full_access(tmp_path,monkeypatch):
    app,local,_,client=fixture_client(tmp_path)
    monkeypatch.setattr('backend.tools.service.search_web',lambda query:{'results':[{'title':'x','url':'https://a.b','snippet':'password: hunter2hunter2'}]})
    with client:
        tools=app.state.tools
        scope=client.get('/permissions').json()['scopes'][0]['id'];client.post('/permissions/grant',json={'level':4,'scope_ids':[scope]})
        cid=conversation(client)
        site=ToolProposal(tool='open_url',url='https://example.com')
        assert tools.can_auto(site,cid)
        proposal=tools.proposal(ToolProposal(tool='web_search',query='algo'),cid)
        result=client.post('/tools/approve/'+proposal['id']).json()['result']
        assert 'credencial' in result['taint']
        assert not tools.can_auto(site,cid)
        # Another conversation is not affected, and STOP clears it.
        assert tools.can_auto(site,conversation(client))
        assert 'aprovação' in tools.proposal(ToolProposal(tool='open_url',url='https://example.com'),cid)['preview']['taint']
        client.post('/actions/stop');client.post('/actions/resume')
        assert cid not in tools.taint

def test_a_file_write_can_be_undone_unless_it_changed_afterwards(tmp_path):
    app,local,_,client=fixture_client(tmp_path)
    with client:
        tools=app.state.tools;client.put('/permissions',json={'level':2})
        scope=client.get('/permissions').json()['scopes'][0]['id']
        target=tools.scoped(scope,'nota.txt');target.write_text('original',encoding='utf-8')
        proposal=tools.proposal(ToolProposal(tool='write_text',scope_id=scope,path='nota.txt',content='novo'))
        result=client.post('/tools/approve/'+proposal['id']).json()['result']
        assert result['undo_available'] and target.read_text(encoding='utf-8')=='novo'
        assert client.post('/tools/undo/'+proposal['id']).json()['status']=='done'
        assert target.read_text(encoding='utf-8')=='original'
        assert client.post('/tools/undo/'+proposal['id']).status_code==400
        # A second write, then a change by the user: undo refuses instead of clobbering it.
        proposal=tools.proposal(ToolProposal(tool='write_text',scope_id=scope,path='nota.txt',content='de novo'))
        client.post('/tools/approve/'+proposal['id'])
        target.write_text('editado pelo usuário',encoding='utf-8')
        assert client.post('/tools/undo/'+proposal['id']).json()['status']=='failed'
        assert target.read_text(encoding='utf-8')=='editado pelo usuário'

def test_critical_cards_expire(tmp_path,monkeypatch):
    app,local,_,client=fixture_client(tmp_path)
    with client:
        tools=app.state.tools;client.put('/permissions',json={'level':2})
        import time
        proposal=tools.proposal(ToolProposal(tool='calculate',expression='1+1'))
        assert tools.pending[proposal['id']][0] is None
        tools.pending[proposal['id']]=(time.monotonic()-1,*tools.pending[proposal['id']][1:])
        assert client.post('/tools/approve/'+proposal['id']).status_code==400
