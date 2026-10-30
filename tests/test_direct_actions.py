import pytest
from backend.tools.direct import direct_action
from test_context_automatic import setup_app
from test_backend import conversation,events

@pytest.mark.parametrize('text,app',[
    ('abra o bloco de notas','notepad'),('abre o bloco de notas','notepad'),
    ('ALT, abra o Bloco de Notas, por favor!','notepad'),('abrir notepad','notepad'),
    ('Por favor, inicie a calculadora.','calculator'),('abre calculator','calculator'),
])
def test_exact_launch_intent(text,app):assert direct_action(text).app==app

@pytest.mark.parametrize('text',[
    'não abra o bloco de notas','como abrir o bloco de notas?',
    'explique "abra o bloco de notas"','abra o bloco de notas e me explique como usar',
    'abra o bloco de notas https://example.com','abra meu programa','reabra o bloco de notas',
    'quero falar sobre o bloco de notas',
])
def test_other_messages_stay_with_model(text):assert direct_action(text) is None

def test_attachments_and_tool_results_are_not_commands():
    assert direct_action('abra o bloco de notas',['file']) is None
    assert direct_action('abra o bloco de notas',tool_result_id='old-search') is None

@pytest.mark.parametrize('model',['auto','hermes3:3b','hermes3:8b','cloud:anthropic','cloud:codex','uninstalled'])
def test_direct_launch_needs_no_model_context_or_cloud_consent(tmp_path,monkeypatch,model):
    app,provider,client=setup_app(tmp_path,monkeypatch)
    async def forbidden(*args,**kwargs):raise AssertionError('Must not contact any model for a direct action')
    provider.models=forbidden;provider.stream=forbidden
    monkeypatch.setattr(app.state.codex,'status',lambda:pytest.fail('No cloud access'))
    monkeypatch.setattr(app.state.tools.catalog,'prewarm',lambda:None)
    monkeypatch.setattr(app.state.tools.catalog,'resolve',lambda name:(_ for _ in ()).throw(ValueError('fixture has no catalog')))
    executed=[]
    def execute(body,*_):
        executed.append(body.model_dump());return {'status':'done','window_seen':True,'launch_requested':body.app}
    monkeypatch.setattr(app.state.tools,'execute',execute)
    with client:
        prefs=client.get('/settings').json();prefs['personality']['instructions']='Longa instrução pessoal. '*100
        client.put('/settings',json=prefs)
        app.state.tools.grant(4,[]);cid=conversation(client)
        app.state.store.add(cid,'assistant','Pesquisa antiga: capacidades técnicas da ALT.','fixture','complete')
        body={'model':model,'content':'abra o bloco de notas','conversation_id':cid}
        estimate=client.post('/chat/estimate',json=body).json()
        assert estimate['fits'] and estimate['execution']=='direct' and estimate['input_tokens']==0
        response=client.post('/chat',json=body)
        assert response.status_code==200,response.text
        data=events(response);assert data[-1]['status']=='complete'
        assert [e['proposal']['preview']['tool'] for e in data if e['type']=='tool_proposal']==['open_app']
        assert len(executed)==1 and executed[0]['app']=='notepad'
        assert 'Bloco de Notas aberto.' in ''.join(e.get('text','') for e in data)
        assert data[0]['model']=='local:actions' and data[-1]['metrics']['execution']=='direct'
        assert client.get(f'/conversations/{cid}/messages').json()[-1]['model']=='local:actions'
        assert provider.messages==[]

@pytest.mark.parametrize('level,origin',[(1,'desktop'),(2,'desktop'),(4,'phone')])
def test_direct_launch_waits_when_permission_requires_review(tmp_path,monkeypatch,level,origin):
    app,_,client=setup_app(tmp_path,monkeypatch)
    monkeypatch.setattr(app.state.tools.catalog,'prewarm',lambda:None)
    monkeypatch.setattr(app.state.tools,'execute',lambda *_:pytest.fail('Must not execute'))
    with client:
        if level==4:app.state.tools.grant(4,[])
        elif level==2:client.put('/permissions',json={'level':2})
        data=events(client.post('/chat',json={'conversation_id':conversation(client),'model':'auto','content':'abre o bloco de notas','origin':origin}))
        assert data[-1]['status']=='complete'
        assert any(e['type']=='tool_proposal' for e in data)
        assert not any(e['type']=='tool_result' for e in data)
        assert 'ainda não foi executada' in ''.join(e.get('text','') for e in data)

@pytest.mark.parametrize('state',['failed','unverified'])
def test_direct_action_never_claims_unconfirmed_success(tmp_path,monkeypatch,state):
    app,_,client=setup_app(tmp_path,monkeypatch)
    monkeypatch.setattr(app.state.tools.catalog,'prewarm',lambda:None)
    monkeypatch.setattr(app.state.tools,'execute',lambda *_:{'status':state})
    with client:
        app.state.tools.grant(4,[])
        data=events(client.post('/chat',json={'conversation_id':conversation(client),'model':'auto','content':'abre o bloco de notas'}))
        assert 'Bloco de Notas aberto.' not in ''.join(e.get('text','') for e in data)

def test_stop_blocks_direct_action(tmp_path,monkeypatch):
    app,provider,client=setup_app(tmp_path,monkeypatch)
    with client:
        cid=conversation(client);client.post('/actions/stop')
        response=client.post('/chat',json={'conversation_id':cid,'model':'auto','content':'abre o bloco de notas'})
        assert response.status_code==403
        assert client.get('/tools/history').json()==[] and provider.messages==[]

def test_owner_denial_blocks_even_the_direct_path(tmp_path,monkeypatch):
    app,provider,client=setup_app(tmp_path,monkeypatch)
    monkeypatch.setattr(app.state.tools,'execute',lambda *_:pytest.fail('Denied action must not run'))
    with client:
        policy=client.get('/policy').json()['policy'];policy['capabilities']['apps']='deny'
        client.put('/policy',json=policy)
        data=events(client.post('/chat',json={'conversation_id':conversation(client),'model':'auto','content':'abra o bloco de notas'}))
        assert 'bloqueada nas suas regras' in ''.join(e.get('text','') for e in data)
        assert not any(e['type'] in ('tool_proposal','tool_result') for e in data)
        assert provider.messages==[]
