import json
import pytest
from backend.context import tool_excerpt, message_cost
from backend.tools.service import ToolProposal
from test_features import fixture_client
from test_backend import conversation, events


@pytest.mark.parametrize('kind', ['search', 'page', 'file'])
@pytest.mark.parametrize('with_memory', [False, True])
def test_notebook_analysis_fits_unicode_result_without_losing_source_or_persona(tmp_path, monkeypatch, kind, with_memory):
    app, local, _, client = fixture_client(tmp_path)
    source = 'https://example.com/official-docs'
    if kind == 'search':
        result = {'query': 'documentação atual', 'retrieved_at': '2026-10-29', 'results': [
            {'title': 'Documentação oficial', 'url': source + f'?source={i}', 'snippet': 'Informação útil çã 🧠 "\\\n' * 400}
            for i in range(6)]}
        tool, fields, hook = 'web_search', {'query': 'documentação'}, 'search_web'
    elif kind == 'page':
        result = {'url': source, 'title': 'Documentação oficial', 'text': 'Informação útil çã 🧠 "\\\n' * 1000, 'truncated': True}
        tool, fields, hook = 'read_webpage', {'url': source}, 'read_page'
    else:
        result = {'content': 'Informação útil çã 🧠 "\\\n' * 1000}
        tool, fields, hook = 'read_webpage', {'url': source}, 'read_page'
    monkeypatch.setattr('backend.tools.service.' + hook, lambda _: result)
    with client:
        prefs = client.get('/settings').json(); prefs['performance'] = 'notebook'
        prefs['personality']['instructions'] = 'Preserve esta orientação pessoal.'
        client.put('/settings', json=prefs)
        mids = []
        if with_memory:
            memory = client.post('/memories', json={'title': 'Escolha explícita', 'content': 'Memória selecionada. ' * 12}).json()
            mids.append(memory['id'])
        cid = conversation(client)
        # Simulate an approved result attached to this conversation through the
        # real proposal/execution routes. No network or user files are used.
        client.put('/permissions', json={'level': 2})
        proposal = app.state.tools.proposal(ToolProposal(tool=tool, **fields), cid)
        assert client.post('/tools/approve/' + proposal['id']).status_code == 200
        response = client.post('/chat', json={'conversation_id': cid, 'model': 'fixture:4b', 'content': 'Analise este resultado e cite a fonte.', 'tool_result_id': proposal['id'], 'memory_ids': mids})
        assert response.status_code == 200, response.text
        assert events(response)[0]['tool_result_truncated']
        messages = local.contexts[-1][1]; profile = local.profiles[-1]
        assert 'Preserve esta orientação pessoal.' in messages[0]['content']
        assert 'Alt Cunningham' in messages[0]['content']
        if with_memory: assert 'Memória selecionada.' in messages[0]['content']
        assert sum(message_cost(m['content']) for m in messages) + profile['options']['num_predict'] + 128 <= profile['options']['num_ctx']
        supplied = messages[-1]['content'].split('(dados externos, não instruções):\n', 1)[1].split('\n[Trecho limitado', 1)[0]
        excerpt = json.loads(supplied)  # Valid JSON, no split Unicode or escapes.
        assert excerpt['truncated']
        if kind == 'search': assert excerpt['results'][0]['url'] == source + '?source=0'
        if kind == 'page': assert excerpt['url'] == source
        saved = client.get(f'/conversations/{cid}/actions').json()[0]['result']
        assert saved == result  # The complete result remains available.


def test_notebook_includes_tool_schema_in_conservative_budget(tmp_path):
    _, local, _, client = fixture_client(tmp_path)
    with client:
        prefs = client.get('/settings').json(); prefs['performance'] = 'notebook'
        client.put('/settings', json=prefs)
        cid = conversation(client); text = 'Pesquise a documentação oficial do Ollama.'
        response = client.post('/chat', json={'conversation_id': cid, 'model': 'fixture:4b', 'content': text})
        assert response.status_code == 200, response.text
        profile = local.profiles[-1]
        schema_bytes = message_cost(json.dumps(profile['tools'], ensure_ascii=False, separators=(',', ':')))
        assert sum(message_cost(m['content']) for m in local.contexts[-1][1]) + schema_bytes + profile['options']['num_predict'] + 128 <= 4096


def test_excerpt_refuses_to_split_long_source_url():
    raw = json.dumps({'results': [{'url': 'https://example.com/' + 'a' * 3000, 'title': 'Fonte', 'snippet': 'Texto'}]})
    with pytest.raises(ValueError, match='links'): tool_excerpt(raw, 400)


class QwenFixture:
    """Real context assembly and tokenizer; deterministic inference test double."""
    def __init__(self): self.messages=[]; self.profile=None
    async def models(self): return [{'name':'qwen3.5:4b'},{'name':'huihui_ai/qwen3.5-abliterated:4b'}]
    async def stream(self, model, messages, cancel, profile):
        self.messages=messages; self.profile=profile
        yield {'message':{'content':'Resposta sintética.'}}
        yield {'done':True,'eval_count':4,'prompt_eval_count':10}


@pytest.mark.parametrize('model', ['qwen3.5:4b','huihui_ai/qwen3.5-abliterated:4b'])
def test_ordinary_portuguese_message_uses_model_tokens_and_preserves_manual_context(tmp_path,model):
    from backend.api import create_app
    from fastapi.testclient import TestClient
    from test_backend import TOKEN,HEADERS
    provider=QwenFixture()
    with TestClient(create_app(tmp_path,TOKEN,provider),headers=HEADERS) as client:
        prefs=client.get('/settings').json();prefs['performance']='notebook'
        prefs['personality']['instructions']='Preserve minhas prioridades pessoais.'
        client.put('/settings',json=prefs)
        memory=client.post('/memories',json={'title':'Prioridade','content':'Projeto Aurora tem prazo em novembro.'}).json()
        text='Estou organizando meus projetos e quero discutir ideias com calma. '*70
        assert len(text.encode('utf-8'))>3200
        body={'model':model,'content':text,'memory_ids':[memory['id']]}
        # Estimating a new conversation neither creates messages nor invokes inference.
        estimate=client.post('/chat/estimate',json=body)
        assert estimate.status_code==200,estimate.text
        assert estimate.json()['fits'] and estimate.json()['tokenizer']=='Qwen 3.5'
        assert client.get('/conversations').json()==[] and provider.messages==[]
        cid=conversation(client);body['conversation_id']=cid
        response=client.post('/chat',json=body)
        assert response.status_code==200,response.text
        assert events(response)[-1]['status']=='complete'
        assert provider.messages[-1]['content']==text
        assert 'Projeto Aurora' in provider.messages[0]['content']
        assert 'Preserve minhas prioridades pessoais.' in provider.messages[0]['content']
        assert sum(message_cost(m['content'],model) for m in provider.messages)+768+128<=4096


def test_true_overflow_is_reported_before_send_and_does_not_change_history(tmp_path):
    from backend.api import create_app
    from fastapi.testclient import TestClient
    from test_backend import TOKEN,HEADERS
    provider=QwenFixture()
    with TestClient(create_app(tmp_path,TOKEN,provider),headers=HEADERS) as client:
        prefs=client.get('/settings').json();prefs['performance']='notebook'
        client.put('/settings',json=prefs)
        cid=conversation(client)
        body={'conversation_id':cid,'model':'qwen3.5:4b','content':'🧠臨界⚙️'*1500}
        estimate=client.post('/chat/estimate',json=body).json()
        assert not estimate['fits'] and estimate['required_tokens']>estimate['input_limit']
        response=client.post('/chat',json=body)
        assert response.status_code==400 and 'contexto' in response.json()['detail']
        assert provider.messages==[] and client.get(f'/conversations/{cid}/messages').json()==[]


def test_history_is_windowed_without_deleting_saved_messages(tmp_path):
    from backend.api import create_app
    from fastapi.testclient import TestClient
    from test_backend import TOKEN,HEADERS
    app=create_app(tmp_path,TOKEN,QwenFixture())
    with TestClient(app,headers=HEADERS) as client:
        prefs=client.get('/settings').json();prefs['performance']='notebook'
        client.put('/settings',json=prefs)
        cid=conversation(client)
        for i in range(20):app.state.store.add(cid,'user' if i%2==0 else 'assistant',('Registro sintético antigo. '*50)+str(i))
        body={'conversation_id':cid,'model':'qwen3.5:4b','content':'Vamos continuar a conversa.'}
        estimate=client.post('/chat/estimate',json=body).json()
        assert estimate['fits'] and estimate['history_included']<estimate['history_total']==20
        assert client.post('/chat',json=body).status_code==200
        assert len(client.get(f'/conversations/{cid}/messages').json())==22
