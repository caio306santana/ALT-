"""Real local smoke for stage 3: long conversation summary + search/read rounds within the Notebook context.

Temporary database; real Ollama (qwen3.5:4b) and public web search. Writes docs/continuity-0.5.3-smoke.json.
Every model call of the reply is recorded and checked against the context window."""
import json
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from backend.api import create_app
from backend.providers.ollama import Ollama
from backend.context import message_cost,tool_schema_cost

MODEL='qwen3.5:4b'
calls=[]
class Recorded(Ollama):
    async def stream(self,model,messages,cancel,profile=None):
        if profile and 'options' in profile:
            used=sum(message_cost(m.get('content') or '',model)+(message_cost(json.dumps(m['tool_calls'],ensure_ascii=False),model) if m.get('tool_calls') else 0) for m in messages)
            schema=tool_schema_cost(profile.get('tools'),model)
            calls.append({'messages':len(messages),'input_tokens_estimated':used,'schema':schema,'num_predict':profile['options']['num_predict'],
                'num_ctx':profile['options']['num_ctx'],'fits':used+schema+profile['options']['num_predict']<=profile['options']['num_ctx'],
                'summary_prompt':'resumo de continuidade' in messages[0]['content']})
        async for chunk in super().stream(model,messages,cancel,profile):yield chunk

history=[('user','Vamos planejar o Projeto Aurora, um app de estudos.'),('assistant','Ótimo. Qual é o primeiro ponto a decidir?'),
    ('user','Decidi que o backend vai ser em Python com FastAPI.'),('assistant','Anotado: backend em Python com FastAPI.'),
    ('user','O prazo de lançamento é 15 de dezembro.'),('assistant','Prazo registrado: 15 de dezembro.'),
    ('user','A interface vai usar React.'),('assistant','Certo, interface em React.')]
filler='Discutimos detalhes de organização das tarefas, telas e fluxo de estudo, sem novas decisões. '*14
token='synthetic-continuity-smoke-'+'x'*40
report={'model':MODEL,'profile':'notebook','environment':'temporary database; real Ollama on this notebook; public web search'}
with tempfile.TemporaryDirectory(prefix='alt-continuity-smoke-') as directory:
    app=create_app(Path(directory),token,Recorded())
    with TestClient(app,headers={'Authorization':'Bearer '+token}) as client:
        prefs=client.get('/settings').json();prefs['performance']='notebook';client.put('/settings',json=prefs)
        assert client.post('/permissions/grant',json={'level':4,'scope_ids':[]}).status_code==200
        cid=client.post('/conversations').json()['id']
        store=app.state.store
        for role,text in history:store.add(cid,role,text)
        for i in range(16):store.add(cid,'user' if i%2==0 else 'assistant',f'Rodada {i}. '+filler)
        ask='Pesquise na internet o que é WebGPU, leia uma fonte e me diga em duas frases se vale para o Projeto Aurora, lembrando a linguagem do backend que decidimos.'
        estimate=client.post('/chat/estimate',json={'conversation_id':cid,'model':MODEL,'content':ask}).json()
        report['before_summary']={k:estimate.get(k) for k in ('history_included','history_total','input_tokens','input_limit')}
        started=time.monotonic()
        summary=client.portal.call(app.state.summaries.update,cid,MODEL,estimate['history_included'])
        report['summary']={'seconds':round(time.monotonic()-started,1),'covered':summary and summary['covered'],'content':summary and summary['content'],
            'mentions_python':bool(summary and 'python' in summary['content'].casefold()),'mentions_deadline':bool(summary and '15' in summary['content'])}
        calls.clear();started=time.monotonic()
        response=client.post('/chat',json={'conversation_id':cid,'model':MODEL,'content':ask})
        events=[json.loads(line) for line in response.text.splitlines()]
        start=next(e for e in events if e['type']=='start')
        reply=''.join(e.get('text','') for e in events if e['type']=='delta')
        report['reply']={'seconds':round(time.monotonic()-started,1),'status':events[-1]['status'],'text':reply,
            'continuity_summary':start.get('continuity_summary'),'tools':[e['proposal']['preview'].get('tool') for e in events if e['type']=='tool_proposal'],
            'tool_results':len([e for e in events if e['type']=='tool_result']),'errors':[e.get('message') for e in events if e['type']=='error'],
            'context_rounds':(events[-1].get('metrics') or {}).get('context_rounds'),'prompt_tokens_last':(events[-1].get('metrics') or {}).get('prompt_tokens'),
            'mentions_python':'python' in reply.casefold()}
        report['calls']=calls
        report['every_call_fits']=all(c['fits'] for c in calls)
        report['originals_preserved']=len(client.get(f'/conversations/{cid}/messages').json())==len(history)+16+2
output=Path(__file__).resolve().parents[1]/'docs'/'continuity-0.5.3-smoke.json'
output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ('before_summary','every_call_fits','originals_preserved')},ensure_ascii=False))
print(json.dumps(report['summary'],ensure_ascii=False)[:600])
print(json.dumps({k:v for k,v in report['reply'].items()},ensure_ascii=False)[:1500])
