import json
import pytest
from fastapi.testclient import TestClient
from backend.api import create_app
from backend.context import message_cost,fit_context_blocks
from test_context import QwenFixture
from test_backend import TOKEN,HEADERS,conversation,events


def setup_app(tmp_path,monkeypatch):
    provider=QwenFixture();app=create_app(tmp_path,TOKEN,provider)
    monkeypatch.setattr(app.state.tools.gui,'inventory',lambda:[])
    monkeypatch.setattr(app.state.tools.catalog,'cached_names',lambda:[])
    monkeypatch.setattr('backend.api.default_browser',lambda:'Navegador de teste')
    return app,provider,TestClient(app,headers=HEADERS)


@pytest.mark.parametrize('level',[2,4])
def test_automatic_estimate_uses_the_selected_model_not_byte_fallback(tmp_path,monkeypatch,level):
    app,provider,client=setup_app(tmp_path,monkeypatch)
    with client:
        prefs=client.get('/settings').json();prefs['performance']='notebook';client.put('/settings',json=prefs)
        if level==2:client.put('/permissions',json={'level':level})
        else:app.state.tools.grant(4,[])
        body={'model':'auto','content':'oi'}
        estimated=client.post('/chat/estimate',json=body).json()
        actual=client.post('/chat/estimate',json={**body,'model':estimated['model']}).json()
        assert estimated['requested_model']=='auto' and estimated['model']=='qwen3.5:4b'
        assert estimated['tokenizer']=='Qwen 3.5' and estimated['fits']
        assert estimated['input_tokens']==actual['input_tokens']<estimated['input_limit']==3200
        assert sum(estimated['components'].values())==estimated['input_tokens']
        assert provider.messages==[] and client.get('/conversations').json()==[]
        cid=conversation(client)
        reply=client.post('/chat',json={**body,'model':estimated['model'],'conversation_id':cid})
        assert reply.status_code==200 and events(reply)[-1]['status']=='complete'
        schema=message_cost(json.dumps(provider.profile['tools'],ensure_ascii=False,separators=(',',':')),'qwen3.5:4b')
        assert sum(message_cost(m['content'],'qwen3.5:4b') for m in provider.messages)+schema+provider.profile['options']['num_predict']+128<=4096


def test_large_window_observations_cannot_crowd_out_the_owners_message_or_memory(tmp_path,monkeypatch):
    app,provider,client=setup_app(tmp_path,monkeypatch)
    grants=[{'id':f'window-{i}','title':'Janela sintética '+str(i)} for i in range(5)]
    monkeypatch.setattr(app.state.tools.gui,'grants',lambda:grants)
    with client:
        prefs=client.get('/settings').json();prefs['performance']='notebook'
        prefs['personality']['instructions']='Preserve minhas prioridades pessoais.';client.put('/settings',json=prefs)
        app.state.tools.grant(4,[])
        # Granting intentionally discards stale observations; populate fixture readings afterwards.
        app.state.tools.gui.snapshots={g['id']:{'public':{'snapshot_id':'fixture-'+g['id'],'elements':[{'id':f'e{i}','label':'Botão sintético com descrição longa. '*10,'type':'Button'} for i in range(25)]}} for g in grants}
        memory=client.post('/memories',json={'title':'Prioridade','content':'O projeto Aurora é minha prioridade.'}).json()
        cid=conversation(client);text='clique no botão da janela'
        body={'model':'qwen3.5:4b','conversation_id':cid,'content':text,'memory_ids':[memory['id']]}
        estimate=client.post('/chat/estimate',json=body).json()
        assert estimate['fits'] and estimate['app_context_omitted']>0
        assert estimate['components']['app_context']<=768
        assert client.post('/chat',json=body).status_code==200
        assert provider.messages[-1]['content'].startswith(text)
        assert 'Preserve minhas prioridades pessoais.' in provider.messages[0]['content']
        assert 'O projeto Aurora é minha prioridade.' in provider.messages[0]['content']
        assert client.get('/tools/history').json()==[]  # Estimating never invokes a UI action.
        assert client.get(f'/conversations/{cid}/messages').json()[0]['content']==text


def test_automatic_estimation_reports_no_models_without_generating(tmp_path,monkeypatch):
    _,provider,client=setup_app(tmp_path,monkeypatch)
    async def no_models():return []
    provider.models=no_models
    with client:
        response=client.post('/chat/estimate',json={'model':'auto','content':'oi'})
        assert response.status_code==409 and 'modelo local' in response.json()['detail']
        assert provider.messages==[]


def test_automatic_cloud_estimate_does_not_generate_or_grant_consent(tmp_path,monkeypatch):
    app,provider,client=setup_app(tmp_path,monkeypatch)
    async def choose(_):return {'model':'cloud:anthropic','band':'complexo','reason':'Fixture only'}
    monkeypatch.setattr(app.state.router,'choose',choose)
    def no_consent(*args,**kwargs):raise AssertionError('Estimating must not issue cloud consent')
    monkeypatch.setattr(app.state.receipts,'issue',no_consent)
    with client:
        estimate=client.post('/chat/estimate',json={'model':'auto','content':'teste'}).json()
        assert estimate['model']=='cloud:anthropic' and estimate['fits']
        assert provider.messages==[] and client.get('/conversations').json()==[]


def test_attached_document_is_counted_in_automatic_estimate(tmp_path,monkeypatch):
    app,_,client=setup_app(tmp_path,monkeypatch)
    with client:
        prefs=client.get('/settings').json();prefs['performance']='notebook';client.put('/settings',json=prefs)
        document=app.state.attachments.add('fixture.txt',('Registro sintético do projeto Aurora. '*100).encode())
        estimate=client.post('/chat/estimate',json={'model':'auto','content':'Resuma o anexo.','attachment_ids':[document['id']]}).json()
        assert estimate['fits'] and estimate['components']['documents']>0
        assert estimate['attachments']['documents']==['fixture.txt']


def test_auxiliary_blocks_keep_complete_boundaries_and_respect_budget():
    from backend.tools.outcome import untrusted
    cost=lambda text:message_cost(text,'qwen3.5:4b')
    small=untrusted('janela',json.dumps({'snapshot_id':'fixture','elements':[{'id':'e1','label':'Salvar'}]}))
    huge=untrusted('janela','Leitura muito longa. '*3000)
    selected,omitted=fit_context_blocks([small,huge],240,cost,'\nCONTEXTO:\n')
    assert omitted==1 and small in selected and huge not in selected
    assert cost(selected)<=240
    data=selected.split('<<<DADOS janela>>>\n')[1].split('\n<<<FIM DADOS>>>')[0]
    assert json.loads(data)['elements'][0]['label']=='Salvar'


def test_automatic_notebook_image_uses_real_model_budget(tmp_path,monkeypatch):
    from test_attachments import JPEG
    app,provider,client=setup_app(tmp_path,monkeypatch)
    with client:
        prefs=client.get('/settings').json();prefs['performance']='notebook';client.put('/settings',json=prefs)
        image=app.state.attachments.add('fixture.jpg',JPEG)
        cid=conversation(client)
        body={'conversation_id':cid,'model':'auto','content':'O que tem aqui?','attachment_ids':[image['id']]}
        estimated=client.post('/chat/estimate',json=body).json()
        assert estimated['fits'] and estimated['components']['images']==1600
        response=client.post('/chat',json={**body,'model':estimated['model']})
        assert response.status_code==200,response.text
        assert provider.messages[-1]['images']


def test_distress_word_is_not_mistaken_for_a_browser_tab_request():
    from backend.tools.chat_tools import route
    names,_,_=route('Perdi meu emprego hoje e estou abalado.',{'level':1})
    assert 'web_search' not in names
    names,_,_=route('Abra uma nova aba.',{'level':1})
    assert 'open_url' in names


def test_long_history_leaves_room_for_formatted_tool_definitions(tmp_path,monkeypatch):
    app,provider,client=setup_app(tmp_path,monkeypatch)
    with client:
        prefs=client.get('/settings').json();prefs['performance']='notebook';client.put('/settings',json=prefs)
        client.put('/permissions',json={'level':2})
        cid=conversation(client)
        for i in range(40):app.state.store.add(cid,'user' if i%2==0 else 'assistant',('Registro sintético antigo. '*15)+str(i))
        response=client.post('/chat',json={'conversation_id':cid,'model':'qwen3.5:4b','content':'Vamos continuar.'})
        assert response.status_code==200,response.text
        # The actual engine formats tool definitions inside its chat template;
        # history must not use the room consumed by that formatting.
        rendered_tools=message_cost(json.dumps(provider.profile['tools'],ensure_ascii=False,indent=2),'qwen3.5:4b')
        assert sum(message_cost(m['content'],'qwen3.5:4b') for m in provider.messages)+rendered_tools+provider.profile['options']['num_predict']+128<=4096
        assert len(client.get(f'/conversations/{cid}/messages').json())==42
