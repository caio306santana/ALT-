import asyncio
from backend.routing import complexity,band,ModelRouter
from test_features import fixture_client
from test_backend import conversation

def test_complexity_in_portuguese():
    assert band(complexity('oi, tudo bem?')[0])=='simples'
    assert band(complexity('Compare passo a passo as vantagens e desvantagens das duas placas')[0])=='médio'
    score,reasons=complexity('Analise passo a passo esse código python e explique detalhadamente o algoritmo')
    assert band(score)=='complexo' and 'código ou matemática' in reasons and 'raciocínio em etapas' in reasons

class Models:
    async def models(self):return [{'name':'qwen3.5:9b','size':6},{'name':'qwen3.5:4b','size':3},{'name':'embeddinggemma:latest','size':1}]

class Cloud:
    def __init__(self,available):self.available=available
    def status(self):return {'available':self.available}

class Engine:game_mode=False
class Gpu:
    busy=False
    def state(self):return {'busy':self.busy}

def router(tmp_path,cloud=False):
    from backend.memory.store import Store
    return ModelRouter(Store(tmp_path/'s.sqlite3'),Models(),Cloud(cloud),Engine(),Gpu())

def test_simple_goes_local_small_complex_goes_to_claude_only_when_configured(tmp_path):
    r=router(tmp_path,cloud=True)
    assert asyncio.run(r.choose('abre o spotify'))['model']=='qwen3.5:4b'
    assert asyncio.run(r.choose('compare as duas opções passo a passo'))['model']=='qwen3.5:9b'
    hard='Analise passo a passo esse código python e explique detalhadamente o algoritmo'
    choice=asyncio.run(r.choose(hard));assert choice['model']=='cloud:anthropic' and 'aprovação' in choice['reason']
    assert asyncio.run(router(tmp_path/'b',cloud=False).choose(hard))['model']=='qwen3.5:9b'

def test_game_mode_and_a_busy_card_force_the_small_model(tmp_path):
    r=router(tmp_path,cloud=True);r.engine.game_mode=True
    hard='Analise passo a passo esse código python e explique detalhadamente o algoritmo'
    assert asyncio.run(r.choose(hard))['model']=='qwen3.5:4b'
    r.engine.game_mode=False;r.gpu.busy=True
    assert asyncio.run(r.choose(hard))['model']=='qwen3.5:4b'

def test_history_overrides_a_band_after_five_samples(tmp_path):
    r=router(tmp_path)
    for _ in range(5):r.record('médio','qwen3.5:9b',False);r.record('médio','qwen3.5:4b',True)
    choice=asyncio.run(r.choose('compare as duas opções passo a passo'))
    assert choice['model']=='qwen3.5:4b' and 'histórico' in choice['reason']

def test_the_route_endpoint_and_learning_from_replies(tmp_path):
    app,local,_,client=fixture_client(tmp_path)
    with client:
        assert client.post('/chat/route',json={'content':'oi'}).json()['band']=='simples'
        cid=conversation(client)
        client.post('/chat',json={'conversation_id':cid,'model':'fixture:4b','content':'oi','route_band':'simples','route_reason':'conversa simples'})
        assert app.state.router.stats('simples')=={'fixture:4b':(1,1)}
