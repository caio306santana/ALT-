import pytest
from backend.tools import research


def test_valid_empty_search_is_distinct_from_provider_failure(monkeypatch):
    monkeypatch.setattr(research,'retrieve',lambda url:(url,'<rss><channel></channel></rss>','application/rss+xml'))
    result=research.search_web('  assunto sintético sem resultados  ')
    assert result['ok'] is True and result['found'] is False
    assert result['results']==[] and result['query']=='assunto sintético sem resultados'
    assert result['retrieved_at'] and 'não prova' in result['notice']

    def unavailable(_):raise ValueError('Página indisponível (HTTP 503).')
    monkeypatch.setattr(research,'retrieve',unavailable)
    with pytest.raises(ValueError,match='503'):research.search_web('consulta')


@pytest.mark.parametrize('body',['<rss>broken','<html><body>Service unavailable</body></html>','<rss/>'])
def test_unusable_response_does_not_masquerade_as_no_results(monkeypatch,body):
    monkeypatch.setattr(research,'retrieve',lambda url:(url,body,'application/rss+xml'))
    with pytest.raises(ValueError,match='indisponível'):research.search_web('consulta')


def test_search_keeps_complete_usable_sources_and_reports_found(monkeypatch):
    xml='<rss><channel><item><title>Fonte sintética</title><link>https://example.com/a?x=1&amp;y=2</link><description>Trecho.</description></item><item><title>Sem URL pública</title><link>javascript:alert(1)</link></item></channel></rss>'
    monkeypatch.setattr(research,'retrieve',lambda url:(url,xml,'application/rss+xml'))
    result=research.search_web('consulta')
    assert result['ok'] is True and result['found'] is True
    assert result['results']==[{'title':'Fonte sintética','url':'https://example.com/a?x=1&y=2','snippet':'Trecho.'}]


def test_provider_can_return_items_without_usable_https_sources(monkeypatch):
    xml='<rss><channel><item><title>Sem fonte utilizável</title><link>http://example.com/</link></item></channel></rss>'
    monkeypatch.setattr(research,'retrieve',lambda url:(url,xml,'application/rss+xml'))
    result=research.search_web('consulta')
    assert result['found'] is False and result['results']==[]


def test_empty_search_completes_and_is_preserved_in_action_history(tmp_path,monkeypatch):
    import json
    from test_features import fixture_client
    monkeypatch.setattr(research,'retrieve',lambda url:(url,'<rss><channel/></rss>','application/rss+xml'))
    _,_,_,client=fixture_client(tmp_path)
    with client:
        client.put('/permissions',json={'level':2})
        proposal=client.post('/tools/propose',json={'tool':'web_search','query':'consulta sintética'}).json()
        response=client.post('/tools/approve/'+proposal['id'])
        assert response.status_code==200,response.text
        data=response.json()
        assert data['status']=='complete' and data['result']['status']=='done'
        assert data['result']['found'] is False and data['result']['results']==[]
        saved=client.get('/tools/history').json()[0]
        assert saved['status']=='complete' and json.loads(saved['result'])['found'] is False
