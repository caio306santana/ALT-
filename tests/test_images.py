"""Image generation: hardware choice, verified install, local ComfyUI and paid API, and the chat tool."""
import base64
import hashlib
import io
import json
import threading
import types
import httpx
import pytest
from backend import images as module
from backend.images import Images, detect_hardware, fetch
from backend.tools.service import ToolProposal
from test_features import fixture_client
from test_backend import conversation, events

PNG = b'\x89PNG\r\n\x1a\nfake'


def cards(*names):
    return lambda *a, **k: types.SimpleNamespace(stdout='\n'.join(names), returncode=0)


def test_the_graphics_card_decides_the_package():
    assert detect_hardware(cards('AMD Radeon(TM) Graphics', 'AMD Radeon RX 7600'))['variant'] == 'amd'
    assert detect_hardware(cards('AMD Radeon RX 7600'))['cpu_mode'] is False
    assert detect_hardware(cards('NVIDIA GeForce RTX 4060'))['variant'] == 'nvidia'
    notebook = detect_hardware(cards('Intel(R) Iris(R) Xe Graphics'))
    assert notebook['cpu_mode'] is True and notebook['variant'] == 'intel'


class Body(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): self.close()


def test_a_download_that_does_not_match_its_hash_is_discarded(tmp_path):
    target = tmp_path / 'model.safetensors'
    with pytest.raises(ValueError, match='hash'):
        fetch('https://x', target, 'a' * 64, lambda n: None, threading.Event(), lambda *a, **k: Body(b'conteudo'))
    assert not target.exists() and not list(tmp_path.iterdir())
    fetch('https://x', target, hashlib.sha256(b'conteudo').hexdigest(), lambda n: None, threading.Event(), lambda *a, **k: Body(b'conteudo'))
    assert target.read_bytes() == b'conteudo'


class Store:
    def __init__(self): self.values = {}
    def settings(self): return dict(self.values)
    def set_settings(self, update): self.values.update(update)
    def audit(self, *a): pass


class Vault:
    def __init__(self, data_dir): self.key = 'sk-test-' + 'x' * 40
    def configured(self): return True
    def get(self): return self.key


def test_install_uses_the_official_package_and_model_with_their_hashes(tmp_path, monkeypatch):
    archive, model = b'7z-bytes', b'model-bytes'
    release = {'tag_name': 'v0.43.0', 'assets': [{'name': 'ComfyUI_windows_portable_amd.7z', 'size': len(archive),
        'digest': 'sha256:' + hashlib.sha256(archive).hexdigest(),
        'browser_download_url': 'https://github.com/comfyanonymous/ComfyUI/releases/download/v0.43.0/ComfyUI_windows_portable_amd.7z'}]}
    monkeypatch.setitem(module.MODEL, 'sha256', hashlib.sha256(model).hexdigest())
    def opener(request, timeout=0):
        url = request.full_url
        return Body(json.dumps(release).encode() if 'api.github.com' in url else archive if url.endswith('.7z') else model)
    monkeypatch.setattr(module.urllib.request, 'urlopen', opener)
    monkeypatch.setattr(module, 'fetch', lambda url, target, sha, progress, cancel: fetch(url, target, sha, progress, cancel, opener))
    images = Images(tmp_path, Store(), Vault, runner=cards('AMD Radeon RX 7600'))
    def extract(args, **kwargs):
        if args[0].endswith('tar.exe'):
            python = images.portable() / 'python_embeded' / 'python.exe'
            python.parent.mkdir(parents=True); python.write_bytes(b'')
        return types.SimpleNamespace(returncode=0, stdout='AMD Radeon RX 7600')
    images.runner = extract
    images._install()
    assert images.state['error'] == '' and images.installed()
    assert images.model_path().read_bytes() == model and not (images.root / 'ComfyUI_windows_portable_amd.7z').exists()


def comfy_transport(seen):
    def handler(request):
        if request.url.path == '/prompt':
            seen.append(json.loads(request.content)); return httpx.Response(200, json={'prompt_id': 'p1'})
        if request.url.path == '/history/p1':
            return httpx.Response(200, json={'p1': {'outputs': {'9': {'images': [{'filename': 'ALT_0001.png', 'subfolder': '', 'type': 'output'}]}}}})
        if request.url.path == '/view': return httpx.Response(200, content=PNG)
        return httpx.Response(200, json={})
    return httpx.MockTransport(handler)


def test_local_generation_saves_the_png(tmp_path, monkeypatch):
    seen = []
    real = httpx.Client
    monkeypatch.setattr(module.httpx, 'Client', lambda **k: real(transport=comfy_transport(seen), base_url=''))
    store = Store(); store.values['image_provider'] = 'local'
    images = Images(tmp_path, store, Vault, runner=cards('AMD Radeon RX 7600'))
    images.running = lambda: True
    result = images.generate('an astronaut cat')
    assert result['provider'] == 'local' and (tmp_path / 'images' / 'generated' / f"{result['image_id']}.png").read_bytes() == PNG
    assert seen[0]['prompt']['6']['inputs']['text'] == 'an astronaut cat' and seen[0]['prompt']['3']['inputs']['steps'] == 1
    assert images.image(result['image_id'])['data'].startswith('data:image/png;base64,')
    with pytest.raises(ValueError): images.image('../../segredo')


def test_paid_api_generation_uses_the_vault_key(tmp_path, monkeypatch):
    sent = {}
    def post(url, headers, json, timeout, trust_env):
        sent.update(url=url, auth=headers['Authorization'], body=json)
        return httpx.Response(200, json={'data': [{'b64_json': base64.b64encode(PNG).decode()}]})
    monkeypatch.setattr(module.httpx, 'post', post)
    store = Store(); store.values['image_provider'] = 'openai'
    result = Images(tmp_path, store, Vault, runner=cards()).generate('a red bicycle')
    assert result['provider'] == 'openai' and sent['auth'] == 'Bearer sk-test-' + 'x' * 40 and sent['body']['prompt'] == 'a red bicycle'


def test_the_chat_tool_generates_and_paid_images_wait_for_a_card(tmp_path):
    app, local, _, client = fixture_client(tmp_path)
    async def model_stream(model, messages, cancel, profile=None):
        yield {'message': {'tool_calls': [{'function': {'name': 'alt_propose_action', 'arguments': {'tool': 'generate_image', 'content': 'a cat astronaut'}}}]}}
        yield {'done': True, 'eval_count': 3}
    local.stream = model_stream
    with client:
        images = app.state.images
        images.generate = lambda prompt, cancel=None: {'status': 'done', 'image_id': '0' * 8 + '-0000-0000-0000-' + '0' * 12, 'path': str(tmp_path / 'x.png'), 'prompt': prompt}
        app.state.store.set_settings({'image_provider': 'local'})
        scope = client.get('/permissions').json()['scopes'][0]['id']
        client.post('/permissions/grant', json={'level': 4, 'scope_ids': [scope]})
        data = events(client.post('/chat', json={'conversation_id': conversation(client), 'model': 'fixture:4b', 'content': 'gera uma imagem de um gato astronauta'}))
        result = next(e for e in data if e['type'] == 'tool_result')['result']
        assert result['status'] == 'done' and result['prompt'] == 'a cat astronaut'
        tools = app.state.tools
        app.state.store.set_settings({'image_provider': 'openai'})
        tools.level = 3
        assert not tools.can_auto(ToolProposal(tool='generate_image', content='x'))


def test_an_image_request_before_setup_says_how_to_turn_it_on(tmp_path):
    app, local, _, client = fixture_client(tmp_path)
    calls = []
    async def model_stream(model, messages, cancel, profile=None):
        calls.append(profile.get('tools'))
        yield {'message': {'tool_calls': [{'function': {'name': 'alt_propose_action', 'arguments': {'tool': 'generate_image', 'content': 'a cat'}}}]}}
        yield {'done': True, 'eval_count': 3}
    local.stream = model_stream
    with client:
        scope = client.get('/permissions').json()['scopes'][0]['id']
        client.post('/permissions/grant', json={'level': 4, 'scope_ids': [scope]})
        data = events(client.post('/chat', json={'conversation_id': conversation(client), 'model': 'fixture:4b', 'content': 'gere uma imagem de gato'}))
        assert 'generate_image' in json.dumps(calls[0]) and len(calls) == 1
        assert 'Configurações → Imagens' in ''.join(e.get('text', '') for e in data if e['type'] == 'delta')
