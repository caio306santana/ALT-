"""Real local Qwen analysis of an approved synthetic result; no web/cloud calls."""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from backend.api import create_app
from backend.tools.service import ToolProposal

token = 'local-analysis-smoke-' + 'x' * 40
with tempfile.TemporaryDirectory(prefix='alt-analysis-smoke-') as directory:
    app = create_app(Path(directory), token)
    with TestClient(app, headers={'Authorization': 'Bearer ' + token}) as client:
        prefs = client.get('/settings').json(); prefs['performance'] = 'notebook'
        client.put('/settings', json=prefs)
        cid = client.post('/conversations').json()['id']
        scope = client.get('/permissions').json()['scopes'][0]
        text = 'Registro sintético: o projeto ALT organiza conversas e usa modelos locais. Informação çã 🧠.\n' * 120
        (Path(scope['path']) / 'analysis-fixture.txt').write_text(text, encoding='utf-8')
        client.put('/permissions', json={'level': 2})
        proposal = app.state.tools.proposal(ToolProposal(tool='read_text', scope_id=scope['id'], path='analysis-fixture.txt'), cid)
        assert client.post('/tools/approve/' + proposal['id']).status_code == 200
        response = client.post('/chat', json={'conversation_id': cid, 'model': 'qwen3.5:4b',
            'content': 'Resuma o registro sintético em uma única frase curta.', 'tool_result_id': proposal['id']})
        assert response.status_code == 200, response.text
        events = [json.loads(line) for line in response.text.splitlines()]
        assert events[0]['tool_result_truncated'], events
        assert events[-1]['status'] == 'complete', events
        reply = client.get(f'/conversations/{cid}/messages').json()[-1]
        assert reply['content'].strip()
        assert client.get(f'/conversations/{cid}/actions').json()[0]['result']['content'] == text
        print(json.dumps({'model': 'qwen3.5:4b', 'profile': 'notebook', 'analysis': 'ok',
            'reply': reply['content'], 'metrics': reply['metrics'], 'full_result_preserved': True}, ensure_ascii=False))
