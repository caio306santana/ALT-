"""Optional subscription smoke. Sends only the synthetic text below through official CLI."""
import argparse
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from backend.api import create_app

parser=argparse.ArgumentParser()
parser.add_argument('--confirm-cloud',action='store_true',help='Authorize sending this synthetic prompt using your Codex subscription.')
args=parser.parse_args()
if not args.confirm_cloud:parser.error('Use --confirm-cloud only after authorizing subscription usage for the synthetic prompt.')
token='codex-smoke-'+'x'*40
with tempfile.TemporaryDirectory(prefix='alt-codex-smoke-') as directory:
    with TestClient(create_app(Path(directory),token),headers={'Authorization':'Bearer '+token}) as client:
        cid=client.post('/conversations').json()['id']
        body={'conversation_id':cid,'model':'cloud:codex','content':'Responda apenas: ALT-CODEX-OK.'}
        preview=client.post('/chat/preview',json=body)
        assert preview.status_code==200,preview.text
        body['consent_receipt']=preview.json()['consent_receipt']
        response=client.post('/chat',json=body)
        print(response.text)
        events=[json.loads(line) for line in response.text.splitlines()]
        assert events[-1]['status']=='complete',events
