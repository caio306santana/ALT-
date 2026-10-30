"""'Baixa X do site Y': the file link is found by code; programs always wait for the owner's card."""
from backend.tools import research
from backend.tools.research import find_download_candidates, clear_choice
from backend.tools.service import ToolProposal
from test_features import fixture_client
from test_backend import conversation, events

PAGE = 'https://example.org/downloads'


def fake_web(links, results=None):
    search = lambda query: {'results': results if results is not None else [{'title': 'Downloads', 'url': PAGE}], 'query': query}
    read = lambda url: {'url': url, 'links': links}
    return search, read


def test_the_requested_file_on_the_requested_site_wins():
    search, read = fake_web([
        {'title': 'Manual do produto (PDF)', 'url': 'https://example.org/files/manual-produto.pdf'},
        {'title': 'Catálogo 2026', 'url': 'https://example.org/files/catalogo.pdf'},
        {'title': 'Manual do produto', 'url': 'https://outro-site.com/manual-produto.pdf'},
        {'title': 'Contato', 'url': 'https://example.org/contato'}])
    found = find_download_candidates('manual do produto', 'example.org', search, read)
    top = clear_choice(found['candidates'], found['site'])
    assert top['url'] == 'https://example.org/files/manual-produto.pdf' and not top['executable']
    assert found['pages_read'] == [PAGE] and all('contato' not in c['url'] for c in found['candidates'])


def test_similar_files_ask_instead_of_guessing():
    search, read = fake_web([
        {'title': 'Manual 2025', 'url': 'https://example.org/manual-2025.pdf'},
        {'title': 'Manual 2026', 'url': 'https://example.org/manual-2026.pdf'}])
    found = find_download_candidates('manual', 'example.org', search, read)
    assert clear_choice(found['candidates'], found['site']) is None


def test_a_direct_file_link_is_used_as_is():
    found = find_download_candidates('', 'https://example.org/a/relatorio.pdf', lambda q: 1 / 0, lambda u: 1 / 0)
    assert found['candidates'][0]['url'] == 'https://example.org/a/relatorio.pdf'


def full_access(tmp_path, monkeypatch, links, saved):
    search, read = fake_web(links)
    monkeypatch.setattr(research, 'search_web', search)
    monkeypatch.setattr(research, 'read_page', read)
    def download(url, destination, cancel):
        saved.append((url, str(destination)))
        return {'path': str(destination), 'bytes': 10, 'sha256': 'a' * 64, 'url': url, 'content_type': 'application/pdf', 'notice': 'Arquivo salvo.'}
    monkeypatch.setattr('backend.tools.service.download', download)
    app, local, _, client = fixture_client(tmp_path)
    return app, local, client


def test_direct_request_downloads_without_the_model(tmp_path, monkeypatch):
    saved = []
    app, local, client = full_access(tmp_path, monkeypatch, [{'title': 'Manual do produto', 'url': 'https://example.org/files/manual-produto.pdf'}], saved)
    with client:
        scope = client.get('/permissions').json()['scopes'][0]['id']
        client.post('/permissions/grant', json={'level': 4, 'scope_ids': [scope]})
        data = events(client.post('/chat', json={'conversation_id': conversation(client), 'model': 'fixture:4b', 'content': 'baixa o manual do produto do site example.org'}))
        start = next(e for e in data if e['type'] == 'start')
        assert start['execution'] == 'direct'
        result = next(e for e in data if e['type'] == 'tool_result')['result']
        assert result['status'] == 'done' and result['chosen']['url'].endswith('manual-produto.pdf')
        assert saved and saved[0][1].endswith('manual-produto.pdf') and 'Downloads' in saved[0][1]
        reply = ''.join(e.get('text', '') for e in data if e['type'] == 'delta')
        assert 'Baixado: manual-produto.pdf' in reply and 'Não abri nem executei' in reply


def test_a_program_becomes_a_card_even_in_full_access(tmp_path, monkeypatch):
    saved = []
    app, local, client = full_access(tmp_path, monkeypatch, [{'title': 'Download 7-Zip para Windows', 'url': 'https://example.org/files/7z-setup.exe'}], saved)
    with client:
        scope = client.get('/permissions').json()['scopes'][0]['id']
        client.post('/permissions/grant', json={'level': 4, 'scope_ids': [scope]})
        data = events(client.post('/chat', json={'conversation_id': conversation(client), 'model': 'fixture:4b', 'content': 'baixa o 7-zip do site example.org'}))
        result = next(e for e in data if e['type'] == 'tool_result')['result']
        assert result['status'] == 'ask' and result['review_url'].endswith('7z-setup.exe') and not saved
        cards = [e['proposal'] for e in data if e['type'] == 'tool_proposal']
        follow = cards[-1]
        assert follow['preview']['tool'] == 'download_file' and follow['preview']['url'].endswith('7z-setup.exe')
        assert follow['id'] in app.state.tools.pending, 'the program waits for the owner'
        tools = app.state.tools
        assert not tools.can_auto(ToolProposal(tool='download_file', url='https://example.org/files/7z-setup.exe'))
        assert tools.can_auto(ToolProposal(tool='download_file', url='https://example.org/files/manual.pdf'))
