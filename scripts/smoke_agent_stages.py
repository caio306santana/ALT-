"""Real local validation of stages 2, 3 and 5 with Ollama on this computer.

Uses a temporary data folder and synthetic content only. Writes
docs/agent-stages-smoke.json with what happened, including failures."""
import json
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from backend.api import create_app

MODEL=sys.argv[1] if len(sys.argv)>1 else 'qwen3.5:4b'
token='synthetic-agent-smoke-'+'x'*40
report={'model':MODEL,'profile':'notebook','started':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'stages':{}}
output=Path(__file__).resolve().parents[1]/'docs'/'agent-stages-smoke.json'

def save():output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def wait(client,path,done,timeout):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        value=client.get(path).json()
        if done(value):return value
        time.sleep(1)
    return client.get(path).json()
def log(stage,data):
    report['stages'][stage]=data;save();print(json.dumps({stage:data},ensure_ascii=False)[:1500],flush=True)

with tempfile.TemporaryDirectory(prefix='alt-agent-smoke-') as directory:
    data=Path(directory)
    with TestClient(create_app(data,token),headers={'Authorization':'Bearer '+token}) as client:
        prefs=client.get('/settings').json();prefs['performance']='notebook';client.put('/settings',json=prefs)

        # Stage 3: real EmbeddingGemma vectors over a document and memories.
        start=time.monotonic()
        doc=data/'receitas.md';doc.write_text('# Caderno de receitas\nBolo de cenoura: bata cenoura, ovos e óleo; misture farinha e açúcar; asse por 40 minutos. Cobertura de chocolate com manteiga.\n\n# Viagem\nO voo para Lisboa sai às 22h do terminal 2; levar adaptador de tomada tipo F.',encoding='utf-8')
        client.post('/memories',json={'title':'Preferência de estudo','content':'Prefiro estudar programação à noite, em blocos de 50 minutos.','category':'preferência'})
        client.post('/memories',json={'title':'Carro','content':'A revisão do carro vence em março; oficina do bairro.','category':'contexto'})
        project=client.post('/projects',json={'name':'Casa'}).json()
        imported=client.post(f"/projects/{project['id']}/documents",json={'path':str(doc)}).json()
        client.post('/knowledge/index')
        status=wait(client,'/knowledge/status',lambda s:s['status']!='running',600)
        queries={'que horas sai meu avião?':'Viagem','como faço o doce de cenoura?':'Bolo','quando estudo melhor?':'estudar','manutenção do veículo':'carro'}
        results={}
        for query,expected in queries.items():
            hits=client.post('/knowledge/search',json={'query':query}).json()
            results[query]={'top':(hits[0]['title']+' :: '+hits[0]['content'][:90]) if hits else None,'score':hits[0]['score'] if hits else None,'expected_in_top':bool(hits) and expected.casefold() in (hits[0]['title']+hits[0]['content']).casefold()}
        log('3_semantic_memory',{'document_chunks':imported.get('chunks'),'index':status,'searches':results,'seconds':round(time.monotonic()-start,1)})

        # Stage 3 in chat: semantic recall enters the prompt.
        policy=client.get('/policy').json()['policy'];policy['memory_recall']='semantic';client.put('/policy',json=policy)
        cid=client.post('/conversations').json()['id'];client.put(f'/conversations/{cid}/project',json={'project_id':project['id']})
        start=time.monotonic()
        events=[json.loads(l) for l in client.post('/chat',json={'conversation_id':cid,'model':MODEL,'content':'A que horas sai meu voo para Lisboa e o que preciso levar? Responda em uma frase.'}).text.splitlines()]
        reply=''.join(e.get('text','') for e in events if e['type']=='delta')
        log('3_chat_recall',{'recalled':events[0].get('recalled_memories'),'reply':reply,'status':events[-1]['status'],'mentions_22h':'22' in reply,'verification':(events[-1].get('metrics') or {}).get('verification'),'seconds':round(time.monotonic()-start,1)})

        # Stage 2: the local model plans; full access executes and verifies.
        workspace=client.get('/permissions').json()['scopes'][0]['id']
        client.post('/permissions/grant',json={'level':4,'scope_ids':[workspace]})
        start=time.monotonic()
        goal='Calcule 15% de 2400. Depois crie o arquivo resultado.txt com o texto "Resultado: 360". Por fim leia resultado.txt para conferir.'
        run=client.post('/tasks',json={'goal':goal,'model':MODEL,'scope_id':workspace}).json()
        run=wait(client,'/tasks/'+run['id'],lambda r:r['state']!='planning',900)
        planned={'state':run['state'],'notice':run['notice'],'plan':run['plan'],'planning_seconds':round(time.monotonic()-start,1)}
        if run['state']=='draft':
            client.post(f"/tasks/{run['id']}/start",json={'allow_replan':True})
            run=wait(client,'/tasks/'+run['id'],lambda r:r['state'] not in ('running','awaiting_approval','planning'),900)
        written=data/'workspace'/'resultado.txt'
        log('2_multi_step_task',{**planned,'final_state':run['state'],'final_notice':run['notice'],'history':[{k:h[k] for k in ('step','tool','verified','reason')} for h in run['history']],
            'file_written':written.read_text(encoding='utf-8') if written.exists() else None,'total_seconds':round(time.monotonic()-start,1)})

        # Stage 2: pause and resume against the real model, without repeating actions.
        client.post('/permissions/grant',json={'level':3,'scope_ids':[workspace]})
        run=client.post('/tasks',json={'goal':'Calcule 12*12 e depois grave o resultado em quadrado.txt.','model':MODEL,'scope_id':workspace}).json()
        run=wait(client,'/tasks/'+run['id'],lambda r:r['state']!='planning',900)
        pause={'planned_state':run['state'],'plan':run['plan']}
        if run['state']=='draft':
            client.post(f"/tasks/{run['id']}/start",json={})
            run=wait(client,'/tasks/'+run['id'],lambda r:r['state'] in ('awaiting_approval','completed','needs_review','paused'),300)
            pause['first_stop']=run['state'];pause['cursor_before_pause']=run['cursor'];pause['first_notice']=run['notice']
            if run['state']=='awaiting_approval':
                client.post(f"/tasks/{run['id']}/pause");wait(client,'/tasks/'+run['id'],lambda r:r['state']=='paused',60)
                before=len(client.get('/tools/history').json())
                client.post(f"/tasks/{run['id']}/start",json={})
                run=wait(client,'/tasks/'+run['id'],lambda r:r['state'] in ('awaiting_approval','completed','needs_review'),300)
                if run['state']=='awaiting_approval':client.post('/tools/approve/'+run['current_proposal']['id'])
                run=wait(client,'/tasks/'+run['id'],lambda r:r['state'] not in ('running','awaiting_approval'),300)
                completed=[a for a in client.get('/tools/history').json() if a['status']=='complete']
                pause.update({'final_state':run['state'],'completed_actions':[a['tool'] for a in completed],'history':[{k:h[k] for k in ('step','tool','verified')} for h in run['history']],'actions_proposed_after_resume':len(client.get('/tools/history').json())-before})
        log('2_pause_resume',pause)

        # Stage 5: personality in real situations, with automatic checks.
        start=time.monotonic()
        client.post('/evaluations',json={'models':[MODEL],'case_ids':['accuracy','practical','support','sources','math_prose']})
        runs=wait(client,'/evaluations',lambda d:d['runs'][0]['status']!='running',1800)['runs'][0]
        log('5_personality_and_checks',{'status':runs['status'],'seconds':round(time.monotonic()-start,1),'results':[{'case':r['case'],'status':r['status'],'reply':r['reply'],'checks':r.get('checks'),'seconds':r.get('seconds')} for r in runs['results']]})
report['finished']=time.strftime('%Y-%m-%dT%H:%M:%S%z');save()
