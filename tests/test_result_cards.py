"""Stage 2 (Drael plan): files and sources shown by result cards come from the stored action, never the renderer."""
from backend.tools import research
from test_features import fixture_client


def test_written_file_is_available_to_reveal_only_while_it_exists(tmp_path):
    _,_,_,client=fixture_client(tmp_path)
    with client:
        client.put('/permissions',json={'level':2})
        scope=client.get('/permissions').json()['scopes'][0]
        proposal=client.post('/tools/propose',json={'tool':'write_text','scope_id':scope['id'],'path':'nota.txt','content':'Olá'}).json()
        assert client.post('/tools/approve/'+proposal['id']).status_code==200
        artifact=client.get('/tools/artifact/'+proposal['id'])
        assert artifact.status_code==200,artifact.text
        data=artifact.json()
        assert data['name']=='nota.txt' and data['bytes']==len('Olá'.encode()) and data['path'].endswith('nota.txt')
        (tmp_path/'workspace'/'nota.txt').unlink()
        assert client.get('/tools/artifact/'+proposal['id']).status_code==400


def test_other_tools_and_pending_actions_expose_no_file(tmp_path):
    _,_,_,client=fixture_client(tmp_path)
    with client:
        client.put('/permissions',json={'level':2})
        calc=client.post('/tools/propose',json={'tool':'calculate','expression':'2+2'}).json()
        assert client.get('/tools/artifact/'+calc['id']).status_code==400
        client.post('/tools/approve/'+calc['id'])
        assert client.get('/tools/artifact/'+calc['id']).status_code==400
        assert client.get('/tools/artifact/inexistente').status_code==400


def test_sources_are_the_https_links_the_search_returned(tmp_path,monkeypatch):
    xml='<rss><channel><item><title>A</title><link>https://example.com/a</link><description>x</description></item></channel></rss>'
    monkeypatch.setattr(research,'retrieve',lambda url:(url,xml,'application/rss+xml'))
    _,_,_,client=fixture_client(tmp_path)
    with client:
        client.put('/permissions',json={'level':2})
        proposal=client.post('/tools/propose',json={'tool':'web_search','query':'consulta'}).json()
        assert client.get('/tools/sources/'+proposal['id']).status_code==400
        client.post('/tools/approve/'+proposal['id'])
        assert client.get('/tools/sources/'+proposal['id']).json()=={'urls':['https://example.com/a']}

