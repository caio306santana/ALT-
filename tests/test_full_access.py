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
    assert 'premissas' not in calm and 'ironia leve' not in calm and 'faça-a na hora' in calm
    sharp=system_prompt({'personality':{'irony':80,'challenge':80}})
    assert 'premissas' in sharp and 'ironia leve' in sharp
