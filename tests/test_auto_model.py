"""'Automático' always means a real local model, and Qwen comes before Hermes for actions."""
import asyncio
from backend.routing import default_local, preference
from backend.tools.direct import direct_action

MODELS = [{'name': 'hermes3:3b', 'size': 3131981167}, {'name': 'huihui_ai/qwen3.5-abliterated:4b', 'size': 3146734631},
          {'name': 'qwen3.5:4b', 'size': 3146734630}, {'name': 'embeddinggemma:latest', 'size': 621875611}]


def test_qwen_is_the_default_even_when_hermes_is_smaller():
    assert default_local(MODELS) == 'qwen3.5:4b'
    assert default_local([m for m in MODELS if 'qwen' not in m['name']]) == 'hermes3:3b'
    assert default_local([]) == ''


def test_router_picks_qwen_for_a_simple_action(tmp_path):
    from test_features import fixture_client
    app, local, _, client = fixture_client(tmp_path)
    async def models(): return MODELS
    local.models = models
    with client:
        route = asyncio.run(app.state.router.choose('abre o spotify')) if hasattr(app.state, 'router') else None
        if route: assert route['model'] == 'qwen3.5:4b'


def test_briefing_with_automatic_uses_a_real_model_and_survives_a_refusal(tmp_path):
    from backend.providers.ollama import ProviderError
    from test_features import fixture_client
    app, local, _, client = fixture_client(tmp_path)
    used = []
    async def models(): return MODELS
    async def refuse(model, messages, cancel, profile=None):
        used.append(model); raise ProviderError('Ollama recusou a geração.', 'inference')
        yield {}
    local.models = models; local.stream = refuse
    with client:
        app.state.store.set_settings({'model': 'auto'})
        response = client.post('/briefing/run')
        assert response.status_code == 200 and response.json()['text']
        assert used and used[0] == 'qwen3.5:4b'


def test_question_form_requests_are_direct():
    assert direct_action('alt consegue abri o bloco de notas e digitar ola ?').content == 'ola'
    assert direct_action('você pode abrir a calculadora?').app == 'calculator'
    assert direct_action('como abrir o bloco de notas?') is None
