import types
from datetime import datetime
import pytest
from backend.tools import system
from backend.tools.system import Reminders,parse_when,task_xml
from backend.tools.chat_tools import tool_spec
from backend.memory.store import Store
from test_features import fixture_client
from test_backend import conversation,events

NOW=lambda:datetime(2026,10,30,10,0)

def offered(text):
    spec=tool_spec(text,{'level':4})
    return spec[0]['function']['parameters']['properties']['tool']['enum'] if spec else []

def test_new_tools_are_routed_from_ordinary_portuguese():
    assert 'screen_look' in offered('olha minha tela e me diz o erro')
    assert 'system_volume' in offered('abaixa o volume pra 20')
    assert 'media_key' in offered('pausa a música')
    assert 'reminder_create' in offered('me lembra de ligar pro João às 15h')
    assert 'windows_keys' not in offered('pausa a música')

def test_reminder_times_accept_iso_or_relative_and_refuse_the_past():
    assert parse_when('em 10 minutos',NOW)==datetime(2026,10,30,10,10)
    assert parse_when('2026-10-30T15:00',NOW)==datetime(2026,10,30,15,0)
    for bad in ('2026-10-29T15:00','amanhã de manhã','2028-01-01T00:00'):
        with pytest.raises(ValueError):parse_when(bad,NOW)

def test_the_reminder_task_runs_with_least_privilege_and_never_carries_the_text(tmp_path):
    xml=task_xml(datetime(2026,10,30,15,0),tmp_path/'toast.ps1',tmp_path/'r.json')
    assert '<RunLevel>LeastPrivilege</RunLevel>' in xml and 'StartWhenAvailable>true' in xml and 'segredo' not in xml
    calls=[];tasks=set()
    def runner(*args):
        calls.append(args);name=args[args.index('/TN')+1]
        if args[0]=='/Create':tasks.add(name)
        if args[0]=='/Delete':tasks.discard(name)
        return types.SimpleNamespace(returncode=0 if args[0]!='/Query' or name in tasks else 1)
    store=Store(tmp_path/'s.sqlite3');reminders=Reminders(store,tmp_path,runner)
    created=reminders.create('ligar pro João; & del segredo','em 10 minutos')
    assert created['status']=='done' and not any('João' in ' '.join(map(str,c)) for c in calls)
    reminders.create('ligar pro dentista','em 20 minutos')
    assert reminders.cancel('ligar')['status']=='ask'
    assert reminders.cancel('dentista')['status']=='done'
    store.db.close()

def test_volume_without_change_is_unverified(monkeypatch):
    state={'level':50,'mute':False}
    monkeypatch.setattr(system,'volume_state',lambda:dict(state))
    monkeypatch.setattr(system,'set_volume_state',lambda new:state.update(new))
    monkeypatch.setattr(system.os,'name','nt')
    assert system.change_volume('30')['status']=='done' and state['level']==30
    assert system.change_volume('30')['status']=='unverified'
    assert system.change_volume('-10')['volume']['level']==20

def test_a_screenshot_is_answered_in_the_same_reply(tmp_path,monkeypatch):
    app,local,_,client=fixture_client(tmp_path)
    monkeypatch.setattr(system,'capture_screen',lambda:(b'\xff\xd8\xff\xe0fake',(1280,720)))
    calls=[]
    async def model_stream(model,messages,cancel,profile=None):
        calls.append((messages,profile))
        if len(calls)==1:yield {'message':{'tool_calls':[{'function':{'name':'alt_propose_action','arguments':{'tool':'screen_look'}}}]}}
        else:yield {'message':{'content':'Vejo um erro de conexão na tela.'}}
        yield {'done':True,'eval_count':5}
    local.stream=model_stream
    with client:
        scope=client.get('/permissions').json()['scopes'][0]['id'];client.post('/permissions/grant',json={'level':4,'scope_ids':[scope]})
        cid=conversation(client)
        data=events(client.post('/chat',json={'conversation_id':cid,'model':'fixture:4b','content':'olha minha tela'}))
        last=calls[1][0][-1]
        assert last['images'] and last['content'].startswith('CAPTURA DA TELA')
        assert not calls[1][1].get('tools')
        assert 'erro de conexão' in ''.join(e.get('text','') for e in data if e['type']=='delta')
        # The image is never written to the database.
        assert b'fake' not in (tmp_path/'alt-ai.sqlite3').read_bytes()
