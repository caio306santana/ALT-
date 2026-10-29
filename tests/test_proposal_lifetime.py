from backend.api import create_app
from fastapi.testclient import TestClient
from test_backend import TOKEN,HEADERS,FixtureProvider
from test_features import fixture_client


def test_owner_can_approve_after_long_model_or_review_wait(tmp_path,monkeypatch):
    app,_,_,client=fixture_client(tmp_path)
    with client:
        client.put('/permissions',json={'level':2})
        monkeypatch.setattr('backend.tools.service.time.monotonic',lambda:1000)
        proposal=client.post('/tools/propose',json={'tool':'calculate','expression':'17*19'}).json()
        assert proposal['expires_in'] is None
        monkeypatch.setattr('backend.tools.service.time.monotonic',lambda:1_000_000)
        response=client.post('/tools/approve/'+proposal['id'])
        assert response.status_code==200,response.text
        assert response.json()['result']['value']==323
        assert client.post('/tools/approve/'+proposal['id']).status_code==400


def test_pending_search_survives_restart_without_executing_until_approval(tmp_path,monkeypatch):
    calls=[]
    monkeypatch.setattr('backend.tools.service.search_web',lambda query:calls.append(query) or {'results':[]})
    app,_,_,client=fixture_client(tmp_path)
    with client:
        client.put('/permissions',json={'level':2})
        proposal=client.post('/tools/propose',json={'tool':'web_search','query':'Consulta sintética'}).json()
    assert calls==[]
    with TestClient(create_app(tmp_path,TOKEN,FixtureProvider()),headers=HEADERS) as reopened:
        assert calls==[]
        assert reopened.get('/tools/proposal/'+proposal['id']).status_code==200
        assert reopened.post('/tools/approve/'+proposal['id']).status_code==200
    assert calls==['Consulta sintética']


def test_delayed_write_still_rejects_changed_file_and_can_be_reviewed_again(tmp_path):
    app,_,_,client=fixture_client(tmp_path)
    with client:
        client.put('/permissions',json={'level':2})
        scope=client.get('/permissions').json()['scopes'][0]
        target=tmp_path/'workspace'/'example.txt';target.write_text('Antes',encoding='utf-8')
        proposal=client.post('/tools/propose',json={'tool':'write_text','scope_id':scope['id'],'path':'example.txt','content':'Depois'}).json()
        target.write_text('Alterado por outra pessoa',encoding='utf-8')
        assert client.post('/tools/approve/'+proposal['id']).status_code==400
        assert target.read_text(encoding='utf-8')=='Alterado por outra pessoa'
        renewed=client.post('/tools/renew/'+proposal['id']).json()
        assert renewed['id']!=proposal['id'] and 'Alterado por outra pessoa' in renewed['preview']['diff']
        assert target.read_text(encoding='utf-8')=='Alterado por outra pessoa'
        assert client.post('/tools/approve/'+renewed['id']).status_code==200
        assert target.read_text(encoding='utf-8')=='Depois'


def test_stop_revokes_even_persisted_proposals(tmp_path):
    app,_,_,client=fixture_client(tmp_path)
    with client:
        client.put('/permissions',json={'level':2})
        proposal=client.post('/tools/propose',json={'tool':'calculate','expression':'1+1'}).json()
        client.post('/actions/stop');client.post('/actions/resume')
        client.put('/permissions',json={'level':2})
        assert client.post('/tools/approve/'+proposal['id']).status_code==400
        assert client.post('/tools/renew/'+proposal['id']).status_code==400
