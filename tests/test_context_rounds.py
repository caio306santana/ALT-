"""Stage 3 (Drael plan): every model call of one reply stays inside the context, not only the first."""
import json
import pytest
from backend.context import fit_round, RoundLimitError, message_cost, tool_schema_cost
from test_backend import conversation, events

size = lambda text: len(str(text).encode('utf-8'))


def shrink(message):
    if not message.get('alt_raw'): return None
    return {**message, 'content': 'resumo', 'alt_raw': None}


def test_older_tool_results_shrink_before_history_is_dropped():
    messages = [{'role': 'system', 'content': 's' * 10}, {'role': 'user', 'content': 'h' * 50},
                {'role': 'assistant', 'content': 'h' * 50}, {'role': 'user', 'content': 'pedido'},
                {'role': 'assistant', 'content': '', 'tool_calls': [{'function': {'name': 'x'}}]},
                {'role': 'tool', 'content': 'r' * 100, 'alt_raw': '{}'},
                {'role': 'assistant', 'content': '', 'tool_calls': [{'function': {'name': 'y'}}]},
                {'role': 'tool', 'content': 'n' * 100, 'alt_raw': '{}'}]
    total = sum(size(m['content']) for m in messages) + 2 * size(json.dumps([{'function': {'name': 'x'}}]))
    fitted, used, changes = fit_round(messages, total - 50, size, 3, shrink)
    assert changes == {'shrunk': 1, 'dropped': 0} and fitted[5]['content'] == 'resumo' and fitted[7]['content'] == 'n' * 100
    fitted, used, changes = fit_round(messages, total - 150, size, 3, shrink)
    assert changes['dropped'] >= 1 and fitted[0]['role'] == 'system' and any(m['content'] == 'pedido' for m in fitted)
    assert used <= total - 150
    with pytest.raises(RoundLimitError, match='cartões'):
        fit_round(messages, 20, size, 3, shrink)


def test_fitting_messages_are_untouched():
    messages = [{'role': 'system', 'content': 'a'}, {'role': 'user', 'content': 'b'}]
    assert fit_round(messages, 100, size, 1, shrink) == (messages, 2, {'shrunk': 0, 'dropped': 0})


class Searcher:
    """Real context assembly and tokenizer; asks for four different searches, then answers."""
    def __init__(self): self.calls = []
    async def models(self): return [{'name': 'qwen3.5:4b'}]
    async def stream(self, model, messages, cancel, profile):
        self.calls.append((messages, profile))
        if len(self.calls) <= 4:
            yield {'message': {'tool_calls': [{'function': {'name': 'alt_propose_action', 'arguments': {'tool': 'web_search', 'query': f'assunto {len(self.calls)}'}}}]}}
        else:
            yield {'message': {'content': 'Resumo das quatro pesquisas.'}}
        yield {'done': True, 'eval_count': 4, 'prompt_eval_count': 10}


def test_four_large_tool_results_never_exceed_the_notebook_context(tmp_path, monkeypatch):
    from backend.api import create_app
    from fastapi.testclient import TestClient
    from test_backend import TOKEN, HEADERS
    snippet = 'Trecho longo de uma fonte sintética sobre o assunto pesquisado, com bastante texto. ' * 18
    monkeypatch.setattr('backend.tools.service.search_web', lambda query: {'ok': True, 'found': True, 'query': query, 'results': [
        {'title': f'Fonte {i} sobre {query}', 'url': f'https://example.com/{query.replace(" ", "-")}/{i}', 'snippet': snippet} for i in range(6)]})
    provider = Searcher()
    app = create_app(tmp_path, TOKEN, provider)
    with TestClient(app, headers=HEADERS) as client:
        prefs = client.get('/settings').json(); prefs['performance'] = 'notebook'; client.put('/settings', json=prefs)
        scope = client.get('/permissions').json()['scopes'][0]['id']
        client.post('/permissions/grant', json={'level': 4, 'scope_ids': [scope]})
        cid = conversation(client)
        # A long earlier conversation: it has to make room for this reply's tool results.
        for i in range(12):
            app.state.store.add(cid, 'user' if i % 2 == 0 else 'assistant', f'Mensagem antiga {i}. ' + 'Contexto anterior da conversa. ' * 25)
        data = events(client.post('/chat', json={'conversation_id': cid, 'model': 'qwen3.5:4b', 'content': 'pesquise quatro assuntos e resuma'}))
        assert data[-1]['status'] == 'complete', data[-3:]
        assert len(provider.calls) == 5 and len([e for e in data if e['type'] == 'tool_result']) == 4
        for messages, profile in provider.calls:
            assert all(not key.startswith('alt_') for m in messages for key in m)
            used = sum(message_cost(m.get('content') or '', 'qwen3.5:4b') + (message_cost(json.dumps(m['tool_calls'], ensure_ascii=False), 'qwen3.5:4b') if m.get('tool_calls') else 0) for m in messages)
            schema = tool_schema_cost(profile.get('tools'), 'qwen3.5:4b')
            assert used + schema + profile['options']['num_predict'] <= profile['options']['num_ctx'], (used, schema, profile['options']['num_predict'])
        last = provider.calls[-1][0]
        # The owner's request and the system prompt survive; the newest result is the fuller one.
        assert last[0]['role'] == 'system' and any(m.get('content', '').startswith('pesquise quatro assuntos') for m in last)
        tools = [m for m in last if m['role'] == 'tool']
        assert len(tools) == 4 and 'assunto-4' in tools[-1]['content']
        assert 'resultado completo está no cartão' in tools[0]['content']
        metrics = data[-1]['metrics']
        assert metrics['context_rounds']['shrunk'] + metrics['context_rounds']['dropped'] > 0


def test_continuity_summary_outlives_the_raw_history():
    messages = [{'role': 'system', 'content': 's'}, {'role': 'user', 'content': 'resumo ' * 5, 'alt_keep': True},
                {'role': 'user', 'content': 'a' * 60}, {'role': 'assistant', 'content': 'b' * 60}, {'role': 'user', 'content': 'pedido'}]
    total = sum(size(m['content']) for m in messages)
    fitted, used, changes = fit_round(messages, total - 100, size, 4, shrink)
    assert changes['dropped'] == 2 and fitted[1].get('alt_keep') and fitted[-1]['content'] == 'pedido'
    fitted, used, changes = fit_round(messages, size('s') + size('pedido'), size, 4, shrink)
    assert [m['content'] for m in fitted] == ['s', 'pedido']
