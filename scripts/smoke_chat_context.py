"""Real local Notebook inference with a message previously rejected by the byte bound."""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from backend.api import create_app

token='synthetic-context-smoke-'+'x'*40
with tempfile.TemporaryDirectory(prefix='alt-context-smoke-') as directory:
    with TestClient(create_app(Path(directory),token),headers={'Authorization':'Bearer '+token}) as client:
        prefs=client.get('/settings').json();prefs['performance']='notebook'
        client.put('/settings',json=prefs)
        cid=client.post('/conversations').json()['id']
        memory=client.post('/memories',json={'title':'Projeto sintético Aurora','content':'O projeto Aurora organiza tarefas de estudo. O usuário prefere respostas curtas.'}).json()
        text=('Estou organizando meus projetos e quero discutir ideias com calma. '*70)+'\nConfirme que recebeu este contexto respondendo somente: Entendido.'
        body={'conversation_id':cid,'model':'qwen3.5:4b','content':text,'memory_ids':[memory['id']]}
        estimate=client.post('/chat/estimate',json=body).json()
        assert estimate['fits'],estimate
        print(json.dumps({'stage':'inference','old_byte_bound':len(text.encode('utf-8'))+32,'estimate':estimate},ensure_ascii=False),flush=True)
        response=client.post('/chat',json=body)
        assert response.status_code==200,response.text
        events=[json.loads(line) for line in response.text.splitlines()]
        assert events[-1]['status']=='complete',events
        messages=client.get(f'/conversations/{cid}/messages').json()
        assert messages[0]['content']==text and messages[-1]['content'].strip()
        actual=messages[-1]['metrics']['prompt_tokens']
        assert actual and actual<=estimate['input_tokens'],(actual,estimate)
        report={'test':'ordinary-long-message-notebook','model':body['model'],'estimate':estimate,
            'message_characters':len(text),'old_message_byte_bound':len(text.encode('utf-8'))+32,
            'reply':messages[-1]['content'],'metrics':messages[-1]['metrics'],'original_message_preserved':True}
        output=Path(__file__).resolve().parents[1]/'docs'/'chat-context-smoke.json'
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False),flush=True)
