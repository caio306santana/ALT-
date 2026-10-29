"""Real Qwen tool proposal test. Does not execute the proposed external query."""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from backend.api import create_app
token='local-agent-smoke-'+'x'*40
with tempfile.TemporaryDirectory(prefix='alt-agent-smoke-') as directory:
    with TestClient(create_app(Path(directory),token),headers={'Authorization':'Bearer '+token}) as client:
        cid=client.post('/conversations').json()['id']
        response=client.post('/chat',json={'conversation_id':cid,'model':'qwen3.5:4b','content':'Pesquise na internet a documentação oficial do Ollama. Use a ferramenta de pesquisa para trazer fontes atuais.'})
        print(response.text)
        data=[json.loads(line) for line in response.text.splitlines()]
        proposed=[event for event in data if event['type']=='tool_proposal']
        assert proposed,'Model did not propose a real tool call.'
        assert proposed[0]['proposal']['preview']['tool']=='web_search'
        assert client.get('/tools/history').json()[0]['status']=='proposed','No action should execute without consent.'
