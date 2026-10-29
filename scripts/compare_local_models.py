"""Run the ALT lab against real installed local models, with synthetic prompts."""
import json
import sys
import tempfile
import time
import argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from backend.api import create_app

token='comparison-smoke-'+'x'*40
parser=argparse.ArgumentParser();parser.add_argument('--discussion',action='store_true');args=parser.parse_args()
with tempfile.TemporaryDirectory(prefix='alt-comparison-') as directory:
    with TestClient(create_app(Path(directory),token),headers={'Authorization':'Bearer '+token}) as client:
        installed=client.get('/models').json()['models']
        names=['qwen3.5:4b',next(m['name'] for m in installed if m['name'].lower().startswith('huihui_ai/qwen3.5-abliterated:4b'))]
        prefs=client.get('/settings').json();prefs['performance']='notebook';client.put('/settings',json=prefs)
        payload={'models':names}
        if args.discussion:payload['case_ids']=['discussion']
        response=client.post('/evaluations',json=payload);assert response.status_code==200,response.text
        rid=response.json()['id'];last=-1
        for _ in range(600):
            run=next(r for r in client.get('/evaluations').json()['runs'] if r['id']==rid)
            if len(run['results'])!=last:
                last=len(run['results']);print(json.dumps({'completed':last,'status':run['status']},ensure_ascii=False),flush=True)
            if run['status']!='running':break
            time.sleep(2)
        assert run['status']!='running','Evaluation did not finish.'
        destination=Path(__file__).resolve().parents[1]/'.local'/('model-comparison-0.3-discussion.json' if args.discussion else 'model-comparison-0.3.json')
        destination.write_text(json.dumps(run,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'saved':str(destination),'status':run['status'],'results':len(run['results'])},ensure_ascii=False),flush=True)
