import pytest
from backend.personality import Personality,system_prompt,OLD_TONE,DEFAULT_TONE
from backend.tools.app_catalog import AppCatalog
from backend.tools.chat_tools import tool_spec
from backend.tools.service import ToolProposal,normalize_url
from test_features import fixture_client

def offered(text,level=4,**status):
    spec=tool_spec(text,{'level':level,**status})
    return spec[0]['function']['parameters']['properties']['tool']['enum'] if spec else []

@pytest.mark.parametrize('text',['abra uma nova aba no google','abre o google','entra no youtube.com','abriu?'])
def test_full_access_always_offers_sites_and_programs(text):
    tools=offered(text)
    assert 'open_url' in tools and 'open_app' in tools

def test_commands_are_offered_only_when_asked_and_never_in_observation():
    assert 'run_command' in offered('rode ipconfig no terminal')
    assert 'run_command' not in offered('abre o spotify')
    assert offered('rode ipconfig',level=1)==[]

def test_plain_navegador_means_the_default_browser_without_an_open_alt_page():
    assert not any(t.startswith('browser_') for t in offered('abre o google no navegador'))
    assert 'browser_read' in offered('clique em Entrar no navegador',browser_page=True)

def full_access(tmp_path,client):
    scope=client.get('/permissions').json()['scopes'][0]['id']
    assert client.post('/permissions/grant',json={'level':4,'scope_ids':[scope]}).json()['level']==4

def fake_menu(tmp_path):
    menu=tmp_path/'menu';(menu/'Spotify').mkdir(parents=True)
    for name in ('Spotify/Spotify.lnk','Google Chrome.lnk','Uninstall Chrome.lnk','Discord.lnk'):(menu/name).write_bytes(b'')
    return AppCatalog(roots=[menu],start_apps=False)

def test_catalog_resolves_spoken_names_and_skips_uninstallers(tmp_path):
    catalog=fake_menu(tmp_path)
    assert catalog.resolve('chrome')['name']=='Google Chrome'
    assert catalog.resolve('SPOTIFY')['name']=='Spotify'
    assert 'Uninstall Chrome' not in catalog.names()
    with pytest.raises(ValueError,match='Parecidos'):catalog.resolve('discordd app')

def test_full_access_opens_installed_programs_by_name_without_registration(tmp_path):
    app,local,_,client=fixture_client(tmp_path)
    with client:
        tools=app.state.tools;tools.catalog=fake_menu(tmp_path)
        # Outside full access only registered apps open.
        assert client.post('/tools/propose',json={'tool':'open_app','app':'spotify'}).status_code==400
        full_access(tmp_path,client)
        proposal=client.post('/tools/propose',json={'tool':'open_app','app':'spotify'}).json()
        assert proposal['preview']['app']=='Spotify'
        assert tools.can_auto(ToolProposal(tool='open_app',app='catalog:Spotify'))

def test_open_app_without_a_name_is_refused_instead_of_opening_notepad(tmp_path):
    app,local,_,client=fixture_client(tmp_path)
    with client:
        full_access(tmp_path,client)
        response=client.post('/tools/propose',json={'tool':'open_app'})
        assert response.status_code==400 and 'aplicativo' in response.text

def test_sites_open_from_a_bare_domain_or_a_search():
    assert normalize_url('google.com')=='https://google.com'
    assert normalize_url('http://example.com/a')=='https://example.com/a'
    assert normalize_url('','preço do RTX 5070')=='https://www.google.com/search?q=pre%C3%A7o+do+RTX+5070'

def test_commands_always_wait_for_the_approval_card_even_in_full_access(tmp_path):
    app,local,_,client=fixture_client(tmp_path)
    with client:
        full_access(tmp_path,client)
        proposal=client.post('/tools/propose',json={'tool':'run_command','command':'Get-Date'}).json()
        assert proposal['preview']['command']=='Get-Date'
        assert not app.state.tools.can_auto(ToolProposal(tool='run_command',command='Get-Date'))

def test_old_argumentative_default_migrates_but_a_custom_tone_is_kept():
    migrated=Personality(tone=OLD_TONE,irony=55,challenge=75,warmth=50,formality=35)
    assert migrated.tone==DEFAULT_TONE and migrated.challenge==15
    # A slider the user moved keeps its value.
    assert Personality(tone=OLD_TONE,challenge=0).challenge==0
    assert Personality(tone='Sarcástica',challenge=90).tone=='Sarcástica'

def test_debate_and_irony_rules_follow_the_sliders():
    calm=system_prompt({'personality':{'irony':0,'challenge':0}})
    assert 'premissas' not in calm and 'ironia leve' not in calm and 'use a ferramenta' in calm
    sharp=system_prompt({'personality':{'irony':80,'challenge':80}})
    assert 'premissas' in sharp and 'ironia leve' in sharp

def test_keyboard_shortcuts_are_parsed_and_the_windows_key_is_never_sent():
    from backend.tools.windows_ui import parse_keys
    assert parse_keys('Shift+Ctrl+T')==('ctrl+shift+t','^+t')
    assert parse_keys('pagedown*3')==('pagedown*3','{PGDN}'*3)
    for bad in ('win+r','ctrl+t*50','abc',''):
        with pytest.raises(ValueError):parse_keys(bad)
    assert 'windows_keys' in offered('aperta ctrl+t no chrome')
    assert 'windows_keys' not in offered('abra uma nova aba no google')

def test_closing_shortcuts_wait_for_the_card_even_in_full_access(tmp_path):
    app,local,_,client=fixture_client(tmp_path)
    with client:
        full_access(tmp_path,client);tools=app.state.tools
        assert tools.can_auto(ToolProposal(tool='windows_keys',window_id='w',keys='ctrl+t'))
        assert not tools.can_auto(ToolProposal(tool='windows_keys',window_id='w',keys='alt+f4'))

def test_a_failed_tool_call_gets_one_correction_round_then_a_plain_answer(tmp_path):
    from test_backend import conversation,events
    app,local,_,client=fixture_client(tmp_path)
    calls=[]
    async def model_stream(model,messages,cancel,profile=None):
        calls.append(messages)
        # Outside full access an unregistered program cannot be resolved, so every call fails.
        yield {'message':{'tool_calls':[{'function':{'name':'alt_propose_action','arguments':{'tool':'open_app','app':'Spotifyy'}}}]}}
        yield {'done':True,'eval_count':3}
    local.stream=model_stream
    with client:
        client.put('/permissions',json={'level':2})
        cid=conversation(client)
        data=events(client.post('/chat',json={'conversation_id':cid,'model':'fixture:4b','content':'abre o spotifyy'}))
        assert len(calls)==2 and calls[1][-1]['role']=='tool' and 'ERRO DA FERRAMENTA' in calls[1][-1]['content']
        assert not [e for e in data if e['type']=='error']
        reply=''.join(e.get('text','') for e in data if e['type']=='delta')
        assert reply.startswith('Não consegui executar:') and 'Acesso total' in reply
        assert data[-1]['status']=='complete'

def test_claude_tool_use_stream_becomes_the_same_action_call(tmp_path,monkeypatch):
    import asyncio,json,httpx
    from backend.memory.store import Store
    from backend.providers.anthropic import AnthropicProvider,AnthropicConfig
    class FakeVault:
        def configured(self):return True
        def validated(self):return True
        def model_available(self,model):return True
        def get(self):return 'sk-ant-test'
    sent=[]
    def sse(*events):return ''.join(f'event: {e["type"]}\ndata: {json.dumps(e)}\n\n' for e in events)
    def handler(request):
        sent.append(json.loads(request.content))
        body=sse({'type':'message_start','message':{'usage':{'input_tokens':50}}},
            {'type':'content_block_start','index':0,'content_block':{'type':'tool_use','id':'t1','name':'alt_propose_action','input':{}}},
            {'type':'content_block_delta','index':0,'delta':{'type':'input_json_delta','partial_json':'{"tool":"open_url",'}},
            {'type':'content_block_delta','index':0,'delta':{'type':'input_json_delta','partial_json':'"url":"youtube.com"}'}},
            {'type':'content_block_stop','index':0},
            {'type':'message_delta','delta':{'stop_reason':'tool_use'},'usage':{'output_tokens':20}},
            {'type':'message_stop'})
        return httpx.Response(200,text=body,headers={'content-type':'text/event-stream'})
    real=httpx.AsyncClient
    monkeypatch.setattr('backend.providers.anthropic.httpx.AsyncClient',lambda **kw:real(transport=httpx.MockTransport(handler)))
    store=Store(tmp_path/'s.sqlite3');provider=AnthropicProvider(store,FakeVault())
    provider.save(AnthropicConfig(enabled=True,model='claude-sonnet-5-5',input_usd_per_million=2,output_usd_per_million=10))
    spec=tool_spec('abre o youtube',{'level':4})
    async def collect():return [c async for c in provider.stream([{'role':'system','content':'s'},{'role':'user','content':'abre o youtube'}],asyncio.Event(),spec)]
    chunks=asyncio.run(collect())
    assert sent[0]['tools'][0]['name']=='alt_propose_action' and sent[0]['tools'][0]['input_schema']['properties']['tool']['enum']
    assert chunks[0]['message']['tool_calls'][0]['function']['arguments']=={'tool':'open_url','url':'youtube.com'}
    assert chunks[-1]['done']
    store.db.close()
