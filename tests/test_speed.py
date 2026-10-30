import asyncio
from backend.monitoring.gpu import GpuWatch,SpeedReference
from backend.memory.store import Store
from backend.tools.chat_tools import stable_tool_spec
from test_features import fixture_client
from test_backend import conversation,events

class FakeCounters:
    query=object()
    def __init__(self):self.usage={}
    def sample(self):return dict(self.usage)

class Clock:
    def __init__(self):self.now=0
    def __call__(self):return self.now

def test_a_game_marks_the_card_busy_after_three_readings_and_clears_after_a_minute():
    counters,clock=FakeCounters(),Clock()
    names={1:'game.exe',2:'llama-server.exe',3:'dwm.exe'}
    watch=GpuWatch(counters,clock,lambda pid:names[pid])
    counters.usage={2:95,3:60}
    for _ in range(5):assert not watch.observe()['busy']
    counters.usage={1:80,2:95}
    watch.observe();watch.observe()
    assert watch.observe()=={'busy':True,'process':'game.exe','percent':80}
    counters.usage={2:95}
    clock.now=30;assert watch.observe()['busy']
    clock.now=61;assert not watch.observe()['busy']

def test_speed_reference_warns_when_this_pc_is_far_below_its_normal(tmp_path):
    store=Store(tmp_path/'s.sqlite3');speed=SpeedReference(store)
    assert speed.observe('qwen3.5:4b',{'tokens_per_second':57,'tokens':200})=={'reference':57,'ratio':1.0}
    assert speed.observe('qwen3.5:4b',{'tokens_per_second':55,'tokens':10}) is None
    assert speed.observe('qwen3.5:4b',{'tokens_per_second':4.5,'tokens':200},game=True) is None
    slow=speed.observe('qwen3.5:4b',{'tokens_per_second':4.5,'tokens':400})
    assert slow['ratio']<.1 and 'reiniciar o PC' in slow['warning']
    # A slow evening barely moves the reference.
    assert speed.all()['qwen3.5:4b']>56
    store.db.close()

def test_stable_tools_keep_the_same_definition_between_different_requests():
    status={'level':4}
    first,likely=stable_tool_spec('abre o spotify',status)
    second,_=stable_tool_spec('pesquise o preço do RTX 5070',status)
    assert first==second and 'open_app' in likely
    assert len(first[0]['function']['parameters']['properties']['tool']['enum'])==14
    extra,_=stable_tool_spec('calcule 17*19',status)
    assert extra[0]['function']['parameters']['properties']['tool']['enum'][-1]=='calculate'
    denied,_=stable_tool_spec('abre o spotify',status,lambda name:name!='run_command')
    assert 'run_command' not in denied[0]['function']['parameters']['properties']['tool']['enum']

def test_the_system_prompt_is_identical_between_turns_and_turn_context_goes_last(tmp_path):
    app,local,_,client=fixture_client(tmp_path)
    with client:
        settings=client.get('/settings').json();settings['tool_routing']='stable';client.put('/settings',json=settings)
        scope=client.get('/permissions').json()['scopes'][0]['id']
        client.post('/permissions/grant',json={'level':4,'scope_ids':[scope]})
        cid=conversation(client)
        for text in ('abre o spotify','qual a capital da França?'):client.post('/chat',json={'conversation_id':cid,'model':'fixture:4b','content':text})
        first,second=local.contexts[-2][1],local.contexts[-1][1]
        assert first[0]==second[0]
        assert local.profiles[-2]['tools']==local.profiles[-1]['tools']
        assert '[CONTEXTO DESTE TURNO' in first[-1]['content'] and first[-1]['content'].startswith('abre o spotify')
        assert 'Escopos locais' not in first[0]['content']

def test_a_busy_card_caps_the_answer_and_tells_the_user(tmp_path):
    app,local,_,client=fixture_client(tmp_path)
    with client:
        import time
        watch=app.state.gpu;watch.counters=FakeCounters()
        watch.busy_by,watch.last_busy=('game.exe',88),time.monotonic()
        cid=conversation(client)
        data=events(client.post('/chat',json={'conversation_id':cid,'model':'fixture:4b','content':'oi'}))
        assert any(e['type']=='notice' and 'game.exe' in e['message'] for e in data)
        assert local.profiles[-1]['options']['num_predict']<=256

def test_embeddings_run_on_the_processor(monkeypatch):
    import httpx
    from backend.providers.ollama import Ollama
    sent=[]
    def handler(request):
        if request.url.path=='/api/tags':return httpx.Response(200,json={'models':[{'name':'embeddinggemma:latest'}]})
        import json;sent.append(json.loads(request.content));return httpx.Response(200,json={'embeddings':[[0.1,0.2]]})
    real=httpx.AsyncClient
    monkeypatch.setattr('backend.providers.ollama.httpx.AsyncClient',lambda **kw:real(transport=httpx.MockTransport(handler)))
    asyncio.run(Ollama().embed(['texto']))
    assert sent[0]['options']['num_gpu']==0

def test_every_caller_uses_the_same_context_size_in_game_mode():
    from backend.monitoring.performance import performance_profile
    assert performance_profile('desktop',True)['options']['num_ctx']==performance_profile('notebook',True)['options']['num_ctx']==4096
    assert performance_profile('desktop')['keep_alive']=='30m' and performance_profile('desktop')['options']['num_predict']==1024
