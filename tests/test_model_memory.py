"""Notebook speed: only one chat model this ALT used stays in memory; low RAM is said, not hidden."""
import asyncio
from collections import namedtuple
import httpx
from backend.providers.ollama import Ollama
from test_backend import conversation, events


def test_only_models_this_alt_used_are_unloaded(monkeypatch):
    provider = Ollama(); unloaded = []
    async def running(): return [{'name': 'qwen3.5:4b'}, {'name': 'hermes3:3b'}, {'name': 'embeddinggemma:latest'}, {'name': 'outro-programa:7b'}]
    class Client:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, json): unloaded.append((json['model'], json['keep_alive']))
    monkeypatch.setattr(provider, 'running', running)
    monkeypatch.setattr(httpx, 'AsyncClient', Client)
    for name in ('qwen3.5:4b', 'hermes3:3b', 'embeddinggemma:latest'): provider.remember_use(name)
    assert asyncio.run(provider.release_others('qwen3.5:4b')) == ['hermes3:3b']
    assert unloaded == [('hermes3:3b', 0)]
    # A model from saved replies (an earlier session) counts too; other programs' models never.
    fresh = Ollama(); unloaded.clear(); monkeypatch.setattr(fresh, 'running', running)
    assert asyncio.run(fresh.release_others('qwen3.5:4b', {'hermes3:3b'})) == ['hermes3:3b']


def test_notebook_reply_warns_when_memory_is_almost_full(tmp_path, monkeypatch):
    from test_features import fixture_client
    app, local, _, client = fixture_client(tmp_path)
    Memory = namedtuple('Memory', 'total available')
    monkeypatch.setattr('backend.api.psutil.virtual_memory', lambda: Memory(20 * 1024**3, int(0.4 * 1024**3)))
    with client:
        prefs = client.get('/settings').json(); prefs['performance'] = 'notebook'; client.put('/settings', json=prefs)
        data = events(client.post('/chat', json={'conversation_id': conversation(client), 'model': 'fixture:4b', 'content': 'oi'}))
        assert any(e['type'] == 'notice' and 'Memória do computador quase cheia (0.4 GB' in e['message'] for e in data)
        assert data[-1]['status'] == 'complete'
