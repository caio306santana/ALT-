import asyncio
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import pytest
from backend.tools.service import ToolProposal
from backend.security.permissions import PermissionEngine
from backend.desktop import DesktopBridge
from test_features import fixture_client
from test_backend import conversation,send,events

def test_policy_is_persistent_visible_and_enforced_again_at_execution(tmp_path):
    app,local,_,client=fixture_client(tmp_path)
    with client:
        body=client.get('/policy').json()['policy'];body['rules']='Debata com franqueza e explicite dúvidas.'
        body['capabilities']['calculate']='allow'
        assert client.put('/policy',json=body).status_code==200
        scope=client.get('/permissions').json()['scopes'][0]['id']
        client.post('/permissions/grant',json={'level':3,'scope_ids':[scope]})
        assert app.state.tools.can_auto(ToolProposal(tool='calculate',expression='2+2'))
        proposal=client.post('/tools/propose',json={'tool':'calculate','expression':'2+2'}).json()
        body['capabilities']['calculate']='deny';client.put('/policy',json=body)
        assert client.post('/tools/approve/'+proposal['id']).status_code in (400,403)
        assert client.post('/tools/propose',json={'tool':'calculate','expression':'2+2'}).status_code==403
        cid=conversation(client);assert send(client,cid).status_code==200
        assert 'Debata com franqueza' in local.contexts[-1][1][0]['content']
        assert 'Debata com franqueza' in client.get('/policy').json()['effective_prompt']
    _,_,_,client=fixture_client(tmp_path)
    with client:assert client.get('/policy').json()['policy']['capabilities']['calculate']=='deny'

def test_opt_in_recall_is_visible_budgeted_and_does_not_bypass_cloud_consent(tmp_path):
    _,local,cloud,client=fixture_client(tmp_path)
    with client:
        memory=client.post('/memories',json={'title':'Projeto Aurora','content':'Aurora usa arquivos Markdown para decisões.'}).json()
        cid=conversation(client);send(client,cid,content='Como retomo Aurora?')
        assert 'Markdown' not in local.contexts[-1][1][0]['content']
        body=client.get('/policy').json()['policy'];body['memory_recall']='automatic';client.put('/policy',json=body)
        data=events(send(client,cid,content='Como retomo Aurora?'))
        assert data[0]['recalled_memories'][0]['id']==memory['id']
        assert 'Markdown' in local.contexts[-1][1][0]['content']
        assert client.get('/memories/search',params={'q':'decisoes Aurora'}).json()[0]['id']==memory['id']
        payload={'conversation_id':cid,'model':'cloud:codex','content':'Retomar Aurora'}
        assert client.post('/chat',json=payload).status_code==403 and not cloud.calls
        preview=client.post('/chat/preview',json=payload).json()
        assert 'Markdown' in preview['messages'][0]['content']
        client.put('/memories/'+memory['id'],json={'title':'Projeto Aurora','content':'Aurora usa outro formato.'})
        assert client.post('/chat',json={**payload,'consent_receipt':preview['consent_receipt']}).status_code==403

def test_continuity_requires_review_rejects_stale_draft_and_import_is_atomic(tmp_path):
    _,_,_,client=fixture_client(tmp_path)
    with client:
        cid=conversation(client);send(client,cid,content='O projeto Aurora precisa de documentação.')
        draft=client.post('/continuity/draft',json={'conversation_id':cid,'model':'fixture:4b'}).json()
        assert draft['content'] and client.get('/memories').json()==[]
        send(client,cid,content='Agora mudamos a decisão.')
        body={'title':'Aurora','content':'Decisão revisada pelo usuário.','category':'contexto'}
        assert client.post('/continuity/approve/'+draft['id'],json=body).status_code==400
        draft=client.post('/continuity/draft',json={'conversation_id':cid,'model':'fixture:4b'}).json()
        assert client.post('/continuity/approve/'+draft['id'],json=body).status_code==200
        assert client.post('/continuity/approve/'+draft['id'],json=body).status_code==400
        assert client.post('/memories/import',json={'items':[body,{'title':'Segredo','content':'password=not-for-memory'}]}).status_code==400
        assert len(client.get('/memories').json())==1
        result=client.post('/memories/import',json={'items':[body,{'title':'Novo','content':'Texto revisado.'}]}).json()
        assert result=={'imported':1,'skipped':1}

def test_comparison_uses_only_installed_local_models_and_preserves_results_and_ratings(tmp_path):
    app,local,_,client=fixture_client(tmp_path)
    with client:
        assert client.post('/evaluations',json={'models':['cloud:codex']}).status_code==400
        run=client.post('/evaluations',json={'models':['fixture:4b','fixture:9b']}).json()
        for _ in range(60):
            latest=client.get('/evaluations').json()['runs'][0]
            if latest['status']!='running':break
            time.sleep(.02)
        assert latest['status']=='complete' and len(latest['results'])==6
        assert {m for m,_ in local.contexts}=={'fixture:4b','fixture:9b'}
        rating={'model':'fixture:4b','portuguese':4,'personality':3,'usefulness':4,'freedom':4,'notes':'Revisão humana.'}
        assert client.put('/evaluations/'+run['id']+'/rating',json=rating).json()['ratings']['fixture:4b']['freedom']==4
        assert not app.state.engine.active

def test_desktop_jobs_are_one_use_cancelled_and_bound_to_observed_elements(tmp_path):
    app,_,_,client=fixture_client(tmp_path)
    with client,ThreadPoolExecutor() as pool:
        client.put('/permissions',json={'level':2})
        body=ToolProposal(tool='browser_read');proposal=app.state.tools.proposal(body)
        pending=pool.submit(lambda:client.post('/tools/approve/'+proposal['id']))
        job=None
        for _ in range(40):
            job=client.get('/desktop/jobs').json()['job']
            if job:break
            time.sleep(.02)
        assert job and client.get('/desktop/jobs').json()['job'] is None
        snapshot={'snapshot_id':'fixture-snapshot','url':'https://example.com/','elements':[{'id':'e1','label':'Documentação','href':'https://example.com/docs'}]}
        assert client.post('/desktop/jobs/'+job['id'],json={'result':snapshot}).json()['accepted']
        assert pending.result(timeout=3).status_code==200
        assert not client.post('/desktop/jobs/'+job['id'],json={'result':snapshot}).json()['accepted']
        click=client.post('/tools/propose',json={'tool':'browser_click','target':'e1','snapshot_id':'fixture-snapshot'}).json()
        assert click['preview']['element']['label']=='Documentação'
        assert client.post('/tools/propose',json={'tool':'browser_click','target':'e2','snapshot_id':'fixture-snapshot'}).status_code==400
        client.post('/actions/stop')
        assert app.state.desktop.snapshot is None
        assert client.post('/tools/approve/'+click['id']).status_code==403

def test_recursive_find_skips_private_names_and_program_registration_detects_changes(tmp_path):
    app,_,_,client=fixture_client(tmp_path)
    with client:
        root=app.state.tools.workspace;(root/'project').mkdir();(root/'project'/'report.md').write_text('ok')
        (root/'.env').write_text('private');(root/'.ssh').mkdir();(root/'.ssh'/'report.md').write_text('private')
        scope=client.get('/permissions').json()['scopes'][0]['id'];client.put('/permissions',json={'level':2})
        proposal=client.post('/tools/propose',json={'tool':'find_files','scope_id':scope,'query':'report'}).json()
        result=client.post('/tools/approve/'+proposal['id']).json()['result']
        assert len(result['entries'])==1 and result['entries'][0]['name'].endswith('report.md')
        executable=tmp_path/'example.exe';executable.write_bytes(b'synthetic, never executed')
        programs=client.post('/programs',json={'path':str(executable)}).json()
        pid=next(p['id'] for p in programs if p.get('path')==str(executable))
        assert client.post('/tools/propose',json={'tool':'open_app','app':'unknown'}).status_code==400
        proposal=client.post('/tools/propose',json={'tool':'open_app','app':pid}).json()
        executable.write_bytes(b'changed synthetic, never executed')
        assert client.post('/tools/approve/'+proposal['id']).status_code==400

def test_browser_schema_and_observation_fit_notebook_profile(tmp_path):
    app,local,_,client=fixture_client(tmp_path)
    with client:
        prefs=client.get('/settings').json();prefs['performance']='notebook';client.put('/settings',json=prefs)
        app.state.desktop.snapshot={'snapshot_id':'observed-fixture','url':'https://example.com/','elements':[{'id':'e1','label':'Documentação','tag':'a'}]}
        cid=conversation(client)
        response=send(client,cid,content='Clique em Documentação no navegador.')
        assert response.status_code==200,response.text
        assert 'observed-fixture' in local.contexts[-1][1][-1]['content']
        assert 'browser_click' in local.profiles[-1]['tools'][0]['function']['parameters']['properties']['tool']['enum']
