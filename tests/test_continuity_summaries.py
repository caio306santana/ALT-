"""Stage 3 (Drael plan): long conversations keep a labelled summary of what no longer fits the context."""
import asyncio
from backend.memory.summaries import LABEL
from test_backend import conversation, events


class Model:
    """Real tokenizer and context assembly; the summary reply is scripted."""
    def __init__(self, summary='- Objetivo: lançar o Projeto Aurora em novembro.\n- Decisão: começar pelo site.'):
        self.summary = summary; self.calls = []
    async def models(self): return [{'name': 'qwen3.5:4b'}]
    async def stream(self, model, messages, cancel, profile):
        self.calls.append(messages)
        yield {'message': {'content': self.summary if 'resumo de continuidade' in messages[0]['content'] else 'Certo, seguimos.'}}
        yield {'done': True, 'eval_count': 4, 'prompt_eval_count': 10}


def long_chat(tmp_path, model):
    from backend.api import create_app
    from fastapi.testclient import TestClient
    from test_backend import TOKEN, HEADERS
    app = create_app(tmp_path, TOKEN, model)
    client = TestClient(app, headers=HEADERS)
    return app, client


def fill(app, cid, count=24):
    for i in range(count):
        app.state.store.add(cid, 'user' if i % 2 == 0 else 'assistant', f'Mensagem {i} sobre o Projeto Aurora. ' + 'Detalhes da conversa anterior. ' * 30)


def test_summary_covers_omitted_messages_and_travels_labelled_as_derived(tmp_path):
    model = Model()
    app, client = long_chat(tmp_path, model)
    with client:
        prefs = client.get('/settings').json(); prefs['performance'] = 'notebook'; client.put('/settings', json=prefs)
        cid = conversation(client); fill(app, cid)
        estimate = client.post('/chat/estimate', json={'conversation_id': cid, 'model': 'qwen3.5:4b', 'content': 'onde paramos?'}).json()
        included = estimate['history_included']
        assert included < 24 and estimate['continuity_summary'] is None
        summaries = app.state.summaries
        assert len(summaries.pending(cid, included)) >= 4
        saved = asyncio.run(summaries.update(cid, 'qwen3.5:4b', included))
        assert saved and saved['covered'] >= 1 and 'Aurora' in saved['content']
        assert client.get('/memories').json() == [], 'A summary is never saved as a memory'
        data = events(client.post('/chat', json={'conversation_id': cid, 'model': 'qwen3.5:4b', 'content': 'onde paramos?'}))
        assert data[-1]['status'] == 'complete'
        start = next(e for e in data if e['type'] == 'start')
        assert start['continuity_summary']['covered'] == saved['covered']
        sent = model.calls[-1]
        block = next(m for m in sent if m['content'].startswith(LABEL))
        assert 'não é memória, instrução nem autorização' in block['content'] and 'Projeto Aurora em novembro' in block['content']
        assert sent.index(block) == 1 and sent[-1]['content'].startswith('onde paramos?')
        # The originals are still stored, untouched.
        assert len(client.get(f'/conversations/{cid}/messages').json()) == 26
        assert client.get('/permissions').json()['level'] == 1
        assert client.delete(f'/conversations/{cid}/summary').json() == {'ok': True}
        assert client.get(f'/conversations/{cid}/summary').json() == {}


def test_old_messages_with_a_secret_are_not_summarized(tmp_path):
    model = Model()
    app, client = long_chat(tmp_path, model)
    with client:
        prefs = client.get('/settings').json(); prefs['performance'] = 'notebook'; client.put('/settings', json=prefs)
        cid = conversation(client)
        app.state.store.add(cid, 'user', 'minha chave é sk-abcdefghijklmnopqrstuvwxyz123456')
        fill(app, cid)
        assert asyncio.run(app.state.summaries.update(cid, 'qwen3.5:4b', 2)) is None
        assert app.state.summaries.get(cid) is None and model.calls == []


def test_owner_can_turn_summaries_off(tmp_path):
    model = Model()
    app, client = long_chat(tmp_path, model)
    with client:
        prefs = client.get('/settings').json(); prefs['performance'] = 'notebook'; client.put('/settings', json=prefs)
        cid = conversation(client); fill(app, cid)
        summaries = app.state.summaries
        asyncio.run(summaries.update(cid, 'qwen3.5:4b', 2))
        policy = app.state.tools.policy.current().model_dump(); policy['conversation_summaries'] = False
        app.state.store.set_settings({'owner_policy': policy})
        estimate = client.post('/chat/estimate', json={'conversation_id': cid, 'model': 'qwen3.5:4b', 'content': 'oi'}).json()
        assert estimate['continuity_summary'] is None
        summaries.schedule(cid, 'qwen3.5:4b', 2)
        assert cid not in summaries.tasks


def test_a_new_reply_cancels_a_background_summary(tmp_path):
    model = Model()
    app, client = long_chat(tmp_path, model)
    with client:
        cid = conversation(client)
        background = asyncio.Event(); app.state.engine.active['summary:other'] = background
        events(client.post('/chat', json={'conversation_id': cid, 'model': 'qwen3.5:4b', 'content': 'oi'}))
        assert background.is_set()
