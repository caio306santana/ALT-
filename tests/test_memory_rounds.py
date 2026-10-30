import asyncio
from backend.memory.suggestions import parse_facts
from test_features import fixture_client
from test_backend import conversation,events

def test_facts_are_read_from_messy_model_output():
    assert parse_facts('["Prefere café sem açúcar","Trabalha com design"]')==['Prefere café sem açúcar','Trabalha com design']
    assert parse_facts('{"fatos":["Mora em Curitiba"]}')==['Mora em Curitiba']
    assert parse_facts('Claro! Aqui: ["Gosta de jogos de corrida"] espero ajudar')==['Gosta de jogos de corrida']
    assert parse_facts('- Usa Windows 11\n- Tem um gato chamado Bolt')==['Usa Windows 11','Tem um gato chamado Bolt']
    assert parse_facts('[]')==[] and len(parse_facts(str(['Fato número %d bem longo' % i for i in range(20)]).replace("'",'"')))==10

def test_suggestions_never_become_memories_without_approval(tmp_path):
    app,local,_,client=fixture_client(tmp_path)
    async def model_stream(model,messages,cancel,profile=None):
        yield {'message':{'content':'["Prefere respostas curtas","api_key = sk-abcdefghijklmnopqrstu","Prefere respostas curtas"]'}}
        yield {'done':True,'eval_count':5}
    with client:
        suggestions=app.state.suggestions;cid=conversation(client)
        client.post('/chat',json={'conversation_id':cid,'model':'fixture:4b','content':'gosto de respostas curtas'})
        local.stream=model_stream
        added=asyncio.run(suggestions.extract(cid,'fixture:4b'))
        assert len(added)==1 and client.get('/memories').json()==[]
        pending=client.get('/memories/suggestions').json()
        assert [p['fact'] for p in pending]==['Prefere respostas curtas']
        client.post(f"/memories/suggestions/{pending[0]['id']}/approve")
        assert client.get('/memories').json()[0]['content']=='Prefere respostas curtas'
        assert client.get('/memories/suggestions').json()==[]
        # Disabled by default: nothing is scheduled.
        suggestions.schedule(cid,'fixture:4b');assert cid not in suggestions.tasks

def test_a_search_is_answered_in_the_same_reply_and_a_repeated_call_stops(tmp_path,monkeypatch):
    app,local,_,client=fixture_client(tmp_path)
    monkeypatch.setattr('backend.tools.service.search_web',lambda query:{'results':[{'title':'Preço','url':'https://example.com/rtx','snippet':'R$ 4.000'}]})
    calls=[]
    async def model_stream(model,messages,cancel,profile=None):
        calls.append((messages,profile))
        if len(calls)<=2:yield {'message':{'tool_calls':[{'function':{'name':'alt_propose_action','arguments':{'tool':'web_search','query':'preço RTX 5070'}}}]}}
        else:yield {'message':{'content':'Custa cerca de R$ 4.000, segundo https://example.com/rtx.'}}
        yield {'done':True,'eval_count':5}
    local.stream=model_stream
    with client:
        scope=client.get('/permissions').json()['scopes'][0]['id'];client.post('/permissions/grant',json={'level':4,'scope_ids':[scope]})
        cid=conversation(client)
        data=events(client.post('/chat',json={'conversation_id':cid,'model':'fixture:4b','content':'pesquise o preço da RTX 5070'}))
        assert calls[1][0][-1]['role']=='tool' and 'R$ 4.000' in calls[1][0][-1]['content']
        # The second identical search was refused, the model got the error and answered.
        assert 'não vou repetir' in calls[2][0][-1]['content']
        reply=''.join(e.get('text','') for e in data if e['type']=='delta')
        assert 'R$ 4.000' in reply and len([e for e in data if e['type']=='tool_proposal'])==1

def test_memories_are_recalled_by_the_model_even_in_conversation_mode(tmp_path):
    app,local,_,client=fixture_client(tmp_path)
    calls=[]
    async def model_stream(model,messages,cancel,profile=None):
        calls.append(messages)
        if len(calls)==1:yield {'message':{'tool_calls':[{'function':{'name':'alt_propose_action','arguments':{'tool':'memory_recall','query':'aniversário'}}}]}}
        else:yield {'message':{'content':'Seu aniversário é em 12 de maio.'}}
        yield {'done':True,'eval_count':5}
    local.stream=model_stream
    with client:
        client.post('/memories',json={'title':'Aniversário','content':'O aniversário do usuário é em 12 de maio.'})
        cid=conversation(client)
        data=events(client.post('/chat',json={'conversation_id':cid,'model':'fixture:4b','content':'você lembra quando é meu aniversário?'}))
        assert '12 de maio' in calls[1][-1]['content']
        assert '12 de maio' in ''.join(e.get('text','') for e in data if e['type']=='delta')
