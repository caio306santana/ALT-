"""Real local summary draft, reviewed memory and source provenance in a temp DB."""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from backend.api import create_app

token='continuity-smoke-'+'x'*40
with tempfile.TemporaryDirectory(prefix='alt-continuity-') as directory:
    app=create_app(Path(directory),token)
    with TestClient(app,headers={'Authorization':'Bearer '+token}) as client:
        prefs=client.get('/settings').json();prefs['performance']='notebook';client.put('/settings',json=prefs)
        cid=client.post('/conversations').json()['id']
        app.state.store.add(cid,'user','Projeto Aurora: organizar documentação em Markdown. Decisão: começar por README. Próximo passo: escrever instruções de instalação. Isto é um registro sintético de teste.')
        app.state.store.add(cid,'assistant','Registrado no diálogo. A decisão é começar pelo README em Markdown.')
        response=client.post('/continuity/draft',json={'conversation_id':cid,'model':'qwen3.5:4b'})
        assert response.status_code==200,response.text
        draft=response.json();assert draft['content'].strip()
        assert client.get('/memories').json()==[]
        reviewed={'title':'Aurora · revisão sintética','content':'Projeto Aurora: documentação em Markdown, começar pelo README. Próximo passo: instruções de instalação.','category':'projeto','enabled':True}
        saved=client.post('/continuity/approve/'+draft['id'],json=reviewed)
        assert saved.status_code==200,saved.text
        source=app.state.store.rows('SELECT * FROM memory_sources WHERE memory_id=?',(saved.json()['id'],))
        assert source[0]['conversation_id']==cid
        print(json.dumps({'continuity':'ok','model':'qwen3.5:4b','draft':draft['content'],'partial':draft['partial'],'memory_not_saved_before_review':True,'reviewed_memory_saved':True,'provenance':'conversation and message IDs saved'},ensure_ascii=False))
