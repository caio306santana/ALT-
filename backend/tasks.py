"""Durable plan/review/execute/verify loop. Every action uses the tool policy."""
import asyncio
import hashlib
import json
import time
from uuid import uuid4
from pydantic import BaseModel,ConfigDict,Field
from backend.tools.service import ToolProposal
from backend.memory.store import now
from backend.monitoring.performance import performance_profile
from backend.providers.ollama import cancellable
from backend.context import message_cost
from backend.evaluations import local_models

class PlanStep(BaseModel):
    model_config=ConfigDict(extra='forbid')
    title:str=Field(min_length=1,max_length=180)
    action:ToolProposal
    expected:str=Field(default='',max_length=180)

class TaskPlan(BaseModel):
    model_config=ConfigDict(extra='forbid')
    steps:list[PlanStep]=Field(min_length=1,max_length=8)

class TaskManager:
    def __init__(self,store,engine,tools,ollama):
        self.store,self.engine,self.tools,self.ollama=store,engine,tools,ollama;self.workers={}
        store.db.execute('CREATE TABLE IF NOT EXISTS agent_runs(id TEXT PRIMARY KEY,conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE,payload TEXT NOT NULL,updated TEXT NOT NULL)');store.db.commit()
        for run in self.list():
            if run['state'] in ('running','awaiting_approval','planning'):
                run.update({'state':'paused','notice':'Execução interrompida pelo encerramento. Revise e retome; ações concluídas não serão repetidas.'});self.save(run)

    def list(self):return [json.loads(row['payload']) for row in self.store.rows('SELECT payload FROM agent_runs ORDER BY updated DESC LIMIT 50')]
    def get(self,rid):
        rows=self.store.rows('SELECT payload FROM agent_runs WHERE id=?',(rid,))
        if not rows:raise ValueError('Tarefa não encontrada.')
        return json.loads(rows[0]['payload'])
    def save(self,run):
        self.store.write('INSERT INTO agent_runs VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,updated=excluded.updated',(run['id'],run['conversation_id'],json.dumps(run,ensure_ascii=False),now()))

    async def generate_plan(self,goal,model,scope_id,window_id,cancel,feedback=''):
        if model not in [m['name'] for m in local_models(await self.ollama.models()) if not m['name'].startswith('embeddinggemma')]:raise ValueError('Planejamento requer modelo local instalado.')
        available=[t for t in ToolProposal.model_fields['tool'].annotation.__args__ if self.tools.policy.decision(t)!='deny']
        context={'goal':goal,'authorized_scope':scope_id,'authorized_window':window_id,'registered_apps':[{'id':p['id'],'name':p['name']} for p in self.tools.programs()[:8]],'feedback':feedback[:2500]}
        instruction='Planeje de 1 a 8 ações curtas para o objetivo. Não execute. Retorne JSON steps com title, action e expected. action contém tool e seus argumentos. Use apenas ferramentas listadas. Leia antes de interagir. Para elemento ainda não observado use snapshot_id="$latest" e target com rótulo exato. Use scope_id/window_id fornecidos. expected deve ficar vazio, salvo texto exato realmente verificável. Sem shell, privilégios ou novas permissões. Ferramentas: '+', '.join(available)
        messages=[{'role':'system','content':instruction},{'role':'user','content':json.dumps(context,ensure_ascii=False)}]
        profile=performance_profile(self.store.settings().get('performance','auto'))
        room=profile['options']['num_ctx']-sum(message_cost(m['content'],model) for m in messages)-128
        if room<256:raise ValueError('Objetivo grande demais para planejar neste perfil. Divida em tarefas menores.')
        profile['options']['num_predict']=min(1536,room);profile['format']=TaskPlan.model_json_schema();text='';done=False
        async with asyncio.timeout(300):
            async for chunk in cancellable(self.ollama.stream(model,messages,cancel,profile),cancel):
                text+=chunk.get('message',{}).get('content','');done=done or bool(chunk.get('done'))
        if cancel.is_set() or not done:raise ValueError('Planejamento interrompido; nenhuma ação executada.')
        try:return TaskPlan.model_validate_json(text)
        except Exception as exc:raise ValueError('O modelo não concluiu um plano válido. Simplifique o objetivo ou edite um plano revisado.') from exc

    async def plan(self,goal,model,scope_id='',window_id='',conversation_id=''):
        cid=conversation_id or self.store.create()['id']
        if not self.store.conversation(cid):raise ValueError('Conversa não encontrada.')
        cancel=self.engine.begin('task-planner')
        try:
            plan=await self.generate_plan(goal,model,scope_id,window_id,cancel)
            run={'id':str(uuid4()),'conversation_id':cid,'goal':goal,'model':model,'scope_id':scope_id,'window_id':window_id,
                'plan':plan.model_dump(),'state':'draft','cursor':0,'history':[],'repairs':0,'attempts':0,'allow_replan':False,'action_id':None,'created':now(),'notice':'Revise o plano antes de iniciar. Nenhuma ação foi executada.'}
            self.store.write('UPDATE conversations SET title=? WHERE id=?',(goal[:65],cid));self.save(run);return run
        finally:self.engine.active.pop('task-planner',None)

    def review(self,rid,plan):
        run=self.get(rid)
        if run['state'] not in ('draft','paused','error','needs_review'):raise ValueError('Pause a tarefa antes de editar.')
        if run['history']:raise ValueError('Crie uma nova tarefa para substituir um plano que já executou ações.')
        run['plan']=plan.model_dump();run['state']='draft';self.save(run);return run

    def bind(self,run,step):
        body=ToolProposal(**step['action'])
        if body.tool in ('list_files','find_files','read_text','write_text','open_folder'):
            body.scope_id=body.scope_id or run['scope_id']
            if body.scope_id!=run['scope_id']:raise PermissionError('O plano tentou sair da pasta escolhida para a tarefa.')
        if body.tool.startswith('windows_'):
            body.window_id=body.window_id or run['window_id']
            if not body.window_id or body.window_id!=run['window_id']:raise PermissionError('A tarefa não possui autorização para essa janela.')
        if body.tool in ('browser_click','browser_type','windows_invoke','windows_type'):
            snapshot=self.tools.desktop.snapshot if body.tool.startswith('browser_') else (self.tools.gui.snapshots.get(body.window_id) or {}).get('public')
            if not snapshot:raise ValueError('Leia a página/janela antes de interagir.')
            if body.snapshot_id in ('','$latest'):body.snapshot_id=snapshot['snapshot_id']
            if not any(e['id']==body.target for e in snapshot['elements']):
                matches=[e for e in snapshot['elements'] if e.get('label','').casefold().strip()==body.target.casefold().strip()]
                if len(matches)!=1:raise ValueError('O rótulo não identifica um único elemento observado; leia novamente ou revise o plano.')
                body.target=matches[0]['id']
        return body

    def verify(self,body,result,expected):
        if body.tool=='write_text':
            path=self.tools.scoped(body.scope_id,body.path)
            if hashlib.sha256(path.read_bytes()).digest()!=hashlib.sha256(body.content.encode('utf-8')).digest():return False,'O arquivo não corresponde ao conteúdo aprovado.'
        if body.tool=='calculate' and 'value' not in result:return False,'Calculadora não retornou valor.'
        if body.tool=='close_app' and not result.get('close_requested'):return False,'Nenhuma janela rastreada confirmou solicitação de fechamento.'
        if body.tool.startswith('browser_') and not result.get('snapshot_id'):return False,'Falta observação atual para verificar a página.'
        if body.tool.startswith('windows_') and not (result.get('snapshot_id') or result.get('observation',{}).get('snapshot_id')):return False,'Falta observação atual da janela.'
        if expected and expected.casefold() not in json.dumps(result,ensure_ascii=False).casefold():return False,'O texto esperado não foi observado: '+expected
        return True,'Resultado conferido com a ferramenta; isso não garante fatos além do resultado observado.'

    async def start(self,rid,allow_replan=False):
        if any(not task.done() for task in self.workers.values()):raise ValueError('Já existe uma tarefa em execução.')
        run=self.get(rid)
        if run['state'] not in ('draft','paused','error','needs_review'):raise ValueError('Tarefa não está pronta para iniciar/retomar.')
        if self.tools.status()['level']<2:raise PermissionError('Escolha um modo de execução no chat ou em Ferramentas.')
        cancel=self.engine.begin('task:'+rid);run.update({'state':'running','allow_replan':allow_replan,'action_id':None,'notice':'Executando o plano revisado.'});self.save(run)
        self.workers[rid]=asyncio.create_task(self.execute(run,cancel));return run

    def pause(self,rid):
        event=self.engine.active.get('task:'+rid)
        if event:event.set()
        run=self.get(rid)
        if run.get('action_id'):
            aid=run['action_id'];self.tools.pending.pop(aid,None);self.store.write("UPDATE actions SET status='cancelled' WHERE id=? AND status='proposed'",(aid,))
            tool_cancel=self.engine.active.get('tool:'+aid)
            if tool_cancel:tool_cancel.set()
        return {'pause_requested':True}

    async def execute(self,run,cancel):
        try:
            deadline=time.monotonic()+1800
            while run['cursor']<len(run['plan']['steps']):
                if cancel.is_set():break
                if run.get('attempts',0)>=12 or time.monotonic()>deadline:raise ValueError('Limite da rodada atingido. Crie uma nova tarefa a partir do progresso verificado.')
                step=run['plan']['steps'][run['cursor']];body=None
                try:
                    run['attempts']=run.get('attempts',0)+1;self.save(run)
                    body=self.bind(run,step);proposal=self.tools.proposal(body,run['conversation_id']);aid=proposal['id']
                    run.update({'action_id':aid,'current_proposal':proposal,'state':'running' if self.tools.can_auto(body) else 'awaiting_approval'});self.save(run)
                    if self.tools.can_auto(body):response=await self.tools.approve(aid);result=response['result']
                    else:
                        while not cancel.is_set():
                            rows=self.store.rows('SELECT status,result FROM actions WHERE id=?',(aid,))
                            if rows and rows[0]['status']=='complete':break
                            if not rows or rows[0]['status'] not in ('proposed','running'):raise ValueError('A ação foi recusada, cancelada ou falhou. Revise o plano.')
                            if rows[0]['status']=='proposed':self.tools.describe(aid)
                            await asyncio.sleep(.25)
                        if cancel.is_set():break
                        result=json.loads(rows[0]['result'])
                    ok,reason=self.verify(body,result,step.get('expected',''))
                    run['history'].append({'step':step['title'],'action_id':aid,'tool':body.tool,'verified':ok,'reason':reason,'result_excerpt':json.dumps(result,ensure_ascii=False)[:1800]})
                    if not ok:raise ValueError(reason)
                    run['cursor']+=1;run.update({'state':'running','action_id':None,'current_proposal':None});self.save(run)
                except PermissionError:
                    run.update({'state':'paused','notice':'Permissão recusada. Suas regras e a janela/pasta autorizada não foram alteradas.'});self.save(run);return
                except (ValueError,OSError) as exc:
                    if not run['allow_replan'] or run['repairs']>=2 or cancel.is_set():raise
                    run['repairs']+=1;run['notice']='Replanejando após observação: '+str(exc);self.save(run)
                    replacement=await self.generate_plan(run['goal'],run['model'],run['scope_id'],run['window_id'],cancel,json.dumps({'failure':str(exc),'completed':run['history']},ensure_ascii=False))
                    run['plan']=replacement.model_dump();run['cursor']=0;run['action_id']=None;run['current_proposal']=None;self.save(run)
            run.update({'state':'paused' if cancel.is_set() else 'completed','notice':'Interrompida; ações verificadas permanecem registradas.' if cancel.is_set() else 'Plano aprovado executado; resultados conferidos. Revise as evidências para confirmar o alcance do objetivo.','action_id':None,'current_proposal':None})
        except asyncio.CancelledError:
            run.update({'state':'paused','notice':'Execução encerrada; retome após revisar as evidências.'})
        except Exception as exc:run.update({'state':'needs_review','notice':str(exc)[:500]})
        finally:self.engine.active.pop('task:'+run['id'],None);self.save(run)
