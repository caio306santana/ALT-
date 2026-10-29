"""Optional end-to-end check using a real installed Ollama model, isolated temp DB."""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from backend.api import create_app

def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--persona',action='store_true');args=parser.parse_args()
    token='local-smoke-test-'+'x'*40
    with tempfile.TemporaryDirectory(prefix='alt-smoke-') as directory:
        with TestClient(create_app(Path(directory),token),headers={'Authorization':'Bearer '+token}) as client:
            available=client.get('/models').json()
            assert available['connected'],available['error']
            names=[m['name'] for m in available['models']]
            assert 'qwen3.5:4b' in names,'Install qwen3.5:4b first (requires download consent).'
            cid=client.post('/conversations').json()['id']
            content='Minha ideia é boa só porque é minha. Você concorda? Responda em até três frases.' if args.persona else 'Responda apenas com a frase: ALT-AI local funcionando.'
            response=client.post('/chat',json={'conversation_id':cid,'model':'qwen3.5:4b','content':content})
            assert response.status_code==200,response.text
            data=[json.loads(line) for line in response.text.splitlines()]
            assert data[-1]['status']=='complete',data
            stored=client.get(f'/conversations/{cid}/messages').json()
            assert stored[-1]['content'].strip()
            print(json.dumps({'model':'qwen3.5:4b','reply':stored[-1]['content'],'status':stored[-1]['status'],'metrics':stored[-1]['metrics'],'history_messages':len(stored)},ensure_ascii=False))
if __name__=='__main__': main()
