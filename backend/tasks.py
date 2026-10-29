"""Durable plan/review/execute/verify loop. Every action uses the tool policy."""
import asyncio
import hashlib
import json
import re
import time
from uuid import uuid4
from pydantic import BaseModel,ConfigDict,Field
from backend.tools.service import ToolProposal,calculate
from backend.memory.store import now
from backend.monitoring.performance import performance_profile
from backend.providers.ollama import cancellable
from backend.context import message_cost
from backend.evaluations import local_models

FILE_TOOLS=('list_files','find_files','read_text','write_text','open_folder')
ACTIVE=('planning','running','awaiting_approval')
# Arguments the planner may fill. Window/scope ids come from the task itself.
ARGUMENTS=('path','content','expression','app','target','snapshot_id','url','query')

class PlanStep(BaseModel):
    model_config=ConfigDict(extra='forbid')
    title:str=Field(min_length=1,max_length=180)
    action:ToolProposal
    expected:str=Field(default='',max_length=180)

class TaskPlan(BaseModel):
    model_config=ConfigDict(extra='forbid')
    steps:list[PlanStep]=Field(min_length=1,max_length=8)

def plan_schema(tools):
    action={'type':'object','properties':{'tool':{'type':'string','enum':tools},**{k:{'type':'string'} for k in ARGUMENTS}},'required':['tool']}
    step={'type':'object','properties':{'title':{'type':'string'},'action':action,'expected':{'type':'string'}},'required':['title','action']}
    return {'type':'object','properties':{'steps':{'type':'array','items':step,'minItems':1,'maxItems':8}},'required':['steps']}

def normalize_plan(text):
    """Drop empty optional arguments so field defaults (e.g. app) still apply."""
    data=json.loads(text)
    for step in data.get('steps',[]) if isinstance(data,dict) else []:
        if isinstance(step,dict) and isinstance(step.get('action'),dict):
            step['action']={k:v for k,v in step['action'].items() if k=='tool' or v not in ('',None)}
            if not step.get('expected'):step.pop('expected',None)
    return TaskPlan.model_validate(data)

def plan_problems(plan):
    """Arguments a step cannot run without, caught before the owner reviews it."""
    problems=[]
    for number,step in enumerate(plan.steps,1):
        action=step.action;path=action.path.strip().rstrip('/\\')
        if action.tool in ('read_text','write_text') and (not path or path=='.' or '.' not in path.replace('\\','/').split('/')[-1]):
            problems.append(f'etapa {number} ({action.tool}) precisa de path com nome de arquivo, ex.: "resultado.txt"')
        if action.tool in ('list_files','find_files','open_folder') and '.' in path.replace('\\','/').split('/')[-1].lstrip('.'):
            problems.append(f'etapa {number} ({action.tool}) recebe uma pasta, não um arquivo; use path "." para a pasta da tarefa')
        if action.tool=='calculate' and not action.expression.strip():problems.append(f'etapa {number} precisa de expression')
        if action.tool in ('web_search',) and not action.query.strip():problems.append(f'etapa {number} precisa de query')
        if action.tool in ('read_webpage','open_url','download_file','browser_open') and not action.url.strip():problems.append(f'etapa {number} precisa de url')
    return problems

class TaskManager:
    def __init__(self,store,engine,tools,ollama):
        self.store,self.engine,self.tools,self.ollama=store,engine,tools,ollama;self.workers={}
        store.db.execute('CREATE TABLE IF NOT EXISTS agent_runs(id TEXT PRIMARY KEY,conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE,payload TEXT NOT NULL,updated TEXT NOT NULL)');store.db.commit()
        for run in self.list():
            if run['state'] in ACTIVE:
                planned=run['state']!='planning'
                run.update({'state':'paused' if planned else 'error','notice':'Execução interrompida pelo encerramento. Revise e retome; ações concluídas não serão repetidas.' if planned else 'Planejamento interrompido pelo encerramento; nenhuma ação executada.'});self.save(run)

    def list(self):return [json.loads(row['payload']) for row in self.store.rows('SELECT payload FROM agent_runs ORDER BY updated DESC LIMIT 50')]
    def get(self,rid):
        rows=self.store.rows('SELECT payload FROM agent_runs WHERE id=?',(rid,))
        if not rows:raise ValueError('Tarefa não encontrada.')
        return json.loads(rows[0]['payload'])
    def save(self,run):
        self.store.write('INSERT INTO agent_runs VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,updated=excluded.updated',(run['id'],run['conversation_id'],json.dumps(run,ensure_ascii=False),now()))
    def busy(self):return any(not task.done() for task in self.workers.values())

    def available(self,run):
        names=[t for t in ToolProposal.model_fields['tool'].annotation.__args__ if self.tools.policy.decision(t)!='deny']
        if not run['window_id']:names=[t for t in names if not t.startswith('windows_')]
        if not run['scope_id']:names=[t for t in names if t not in FILE_TOOLS]
        if not self.tools.desktop:names=[t for t in names if not t.startswith('browser_')]
        # Small local models add unrelated steps when offered every tool; offer
        # browser/web/app tools only when the goal is about them.
        goal=run['goal'].casefold()
        if not re.search(r'naveg|browser|clique|clicar|digite|formul',goal):names=[t for t in names if not t.startswith('browser_')]
        if not re.search(r'pesquis|internet|site|p[áa]gina|http|link|baix|download|web|fonte',goal):names=[t for t in names if t not in ('web_search','read_webpage','open_url','download_file')]
        if not re.search(r'abr|apli|app|programa|feche|fechar|calculadora|bloco de notas|notepad|pasta',goal):names=[t for t in names if t not in ('open_app','close_app','open_folder')]
        return names

    async def generate_plan(self,run,cancel,feedback=''):
        model=run['model']
        if model not in [m['name'] for m in local_models(await self.ollama.models()) if not m['name'].startswith('embeddinggemma')]:raise ValueError('Planejamento requer modelo local instalado.')
        available=self.available(run)
        if not available:raise PermissionError('Todas as capacidades estão bloqueadas nas suas regras.')
        context={'goal':run['goal'],'registered_apps':[{'id':p['id'],'name':p['name']} for p in self.tools.programs()[:8]],'feedback':feedback[:2500]}
        if run['scope_id']:context['folder']='Pasta escolhida para a tarefa; use caminhos relativos a ela (\".\" é a raiz).'
        instruction=('Planeje de 1 a 8 ações curtas para o objetivo. Não execute. Retorne JSON com steps; cada step tem title, action e expected. '
            'action contém tool e somente os argumentos necessários. Use apenas as ferramentas listadas. Leia antes de interagir. '
            'Para elemento ainda não observado use snapshot_id="$latest" e target com rótulo exato. Cálculos usam expression com números e + - * / % **. '
            'expected fica vazio, salvo texto exato realmente verificável no resultado. Sem shell, privilégios ou novas permissões. Ferramentas: '+', '.join(available))
        messages=[{'role':'system','content':instruction},{'role':'user','content':json.dumps(context,ensure_ascii=False)}]
        profile=performance_profile(self.store.settings().get('performance','auto'))
        room=profile['options']['num_ctx']-sum(message_cost(m['content'],model) for m in messages)-128
        if room<256:raise ValueError('Objetivo grande demais para planejar neste perfil. Divida em tarefas menores.')
        profile['options']['num_predict']=min(1536,room);profile['format']=plan_schema(available);text='';done=False
        if feedback:messages[0]['content']+=' Planeje SOMENTE o que ainda falta: não repita etapas que aparecem como concluídas no feedback.'
        for attempt in range(2):
            text='';done=False
            async with asyncio.timeout(420):
                async for chunk in cancellable(self.ollama.stream(model,messages,cancel,profile),cancel):
                    text+=chunk.get('message',{}).get('content','');done=done or bool(chunk.get('done'))
            if cancel.is_set() or not done:raise ValueError('Planejamento interrompido; nenhuma ação executada.')
            try:plan=normalize_plan(text)
            except Exception as exc:raise ValueError('O modelo não concluiu um plano válido. Simplifique o objetivo ou edite o plano.') from exc
            if any(step.action.tool not in available for step in plan.steps):raise ValueError('O plano usou uma ferramenta indisponível para esta tarefa.')
            problems=plan_problems(plan)
            if not problems:return plan
            # One correction round with concrete feedback, before anything runs.
            messages+=[{'role':'assistant','content':text},{'role':'user','content':'Corrija o plano: '+'; '.join(problems)+'. Retorne o plano completo corrigido.'}]
        raise ValueError('O plano do modelo continua incompleto: '+'; '.join(problems)+'. Edite o plano antes de iniciar.')

    def plan(self,goal,model,scope_id='',window_id='',conversation_id=''):
        if self.busy():raise ValueError('Já existe uma tarefa em planejamento ou execução.')
        goal=goal.strip()
        if not goal:raise ValueError('Descreva o objetivo da tarefa.')
        if scope_id and scope_id not in {s['id'] for s in self.tools.status()['scopes']}:raise ValueError('Pasta não autorizada. Escolha uma pasta em Ferramentas.')
        cid=conversation_id or self.store.create()['id']
        if not self.store.conversation(cid):raise ValueError('Conversa não encontrada.')
        rid=str(uuid4());cancel=self.engine.begin('task:'+rid)
        run={'id':rid,'conversation_id':cid,'goal':goal,'model':model,'scope_id':scope_id,'window_id':window_id,
            'plan':None,'state':'planning','cursor':0,'history':[],'repairs':0,'attempts':0,'allow_replan':False,'action_id':None,'current_proposal':None,'created':now(),
            'notice':'Planejando com o modelo local. Nenhuma ação será executada antes da sua revisão.'}
        if not conversation_id:self.store.write('UPDATE conversations SET title=? WHERE id=?',('Tarefa: '+goal[:57],cid))
        self.save(run);self.workers[rid]=asyncio.create_task(self._plan(run,cancel));return run

    async def _plan(self,run,cancel):
        try:
            plan=await self.generate_plan(run,cancel)
            run.update({'plan':plan.model_dump(),'state':'draft','notice':'Revise o plano antes de iniciar. Nenhuma ação foi executada.'})
        except asyncio.CancelledError:run.update({'state':'error','notice':'Planejamento encerrado; nenhuma ação executada.'})
        except Exception as exc:run.update({'state':'error','notice':str(exc)[:500] or 'Falha no planejamento.'})
        finally:self.engine.active.pop('task:'+run['id'],None);self.save(run)

    def review(self,rid,plan):
        run=self.get(rid)
        if run['state'] not in ('draft','paused','error','needs_review'):raise ValueError('Pause a tarefa antes de editar.')
        if run['history']:raise ValueError('Crie uma nova tarefa para substituir um plano que já executou ações.')
        run.update({'plan':plan.model_dump(),'state':'draft','cursor':0,'action_id':None,'current_proposal':None,'notice':'Plano editado por você. Nenhuma ação foi executada.'});self.save(run);return run

    def bind(self,run,step):
        body=ToolProposal(**step['action'])
        if body.tool in FILE_TOOLS:
            # The task is confined to the folder chosen for it, whatever the model wrote.
            if not run['scope_id']:raise PermissionError('Esta tarefa não possui pasta autorizada.')
            body.scope_id=run['scope_id']
            if body.path in ('','/','\\'):body.path='.'
        if body.tool.startswith('windows_'):
            if not run['window_id']:raise PermissionError('A tarefa não possui autorização para essa janela.')
            body.window_id=run['window_id']
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
        if body.tool=='read_text' and 'content' not in result:return False,'A leitura não retornou conteúdo.'
        if body.tool=='calculate':
            if 'value' not in result:return False,'Calculadora não retornou valor.'
            if calculate(body.expression)!=result['value']:return False,'O valor não confere com um novo cálculo independente.'
        if body.tool=='close_app' and not result.get('close_requested'):return False,'Nenhuma janela rastreada confirmou solicitação de fechamento.'
        if body.tool.startswith('browser_') and not result.get('snapshot_id'):return False,'Falta observação atual para verificar a página.'
        if body.tool.startswith('windows_') and not (result.get('snapshot_id') or result.get('observation',{}).get('snapshot_id')):return False,'Falta observação atual da janela.'
        if expected and expected.casefold() not in json.dumps(result,ensure_ascii=False).casefold():return False,'O texto esperado não foi observado: '+expected
        return True,'Resultado conferido com a ferramenta; isso não garante fatos além do resultado observado.'

    async def start(self,rid,allow_replan=False):
        if self.busy():raise ValueError('Já existe uma tarefa em planejamento ou execução.')
        run=self.get(rid)
        if run['state'] not in ('draft','paused','error','needs_review') or not run.get('plan'):raise ValueError('Tarefa não está pronta para iniciar/retomar.')
        if self.tools.status()['level']<2:raise PermissionError('Escolha um modo de execução no chat ou em Ferramentas.')
        cancel=self.engine.begin('task:'+rid);run.update({'state':'running','allow_replan':allow_replan,'attempts':0,'repairs':0,'notice':'Executando o plano revisado.'});self.save(run)
        self.workers[rid]=asyncio.create_task(self.execute(run,cancel));return run

    def pause(self,rid):
        event=self.engine.active.get('task:'+rid)
        if event:event.set()
        run=self.get(rid)
        if run.get('action_id'):
            aid=run['action_id'];self.tools.pending.pop(aid,None);self.tools.previews.pop(aid,None)
            self.store.write("UPDATE actions SET status='cancelled' WHERE id=? AND status='proposed'",(aid,))
            tool_cancel=self.engine.active.get('tool:'+aid)
            if tool_cancel:tool_cancel.set()
        return {'pause_requested':True}

    def stop_all(self):
        for rid,task in list(self.workers.items()):
            if not task.done():self.pause(rid)

    async def outcome(self,run,body,cancel):
        """Result of the step's action, reusing an action that already ran.

        A resumed run never repeats a completed action: the id stays recorded
        until the step is verified, and a still-pending proposal is reused."""
        aid=run.get('action_id')
        rows=self.store.rows('SELECT status,result FROM actions WHERE id=?',(aid,)) if aid else []
        if rows and rows[0]['status']=='complete':return json.loads(rows[0]['result'])
        if not (rows and rows[0]['status']=='proposed' and aid in self.tools.pending):
            proposal=self.tools.proposal(body,run['conversation_id']);aid=proposal['id']
            run.update({'action_id':aid,'current_proposal':proposal})
        auto=self.tools.can_auto(body)
        run['state']='running' if auto else 'awaiting_approval';self.save(run)
        if auto:return (await self.tools.approve(aid))['result']
        while True:
            rows=self.store.rows('SELECT status,result FROM actions WHERE id=?',(aid,))
            if rows and rows[0]['status']=='complete':return json.loads(rows[0]['result'])
            if cancel.is_set():return None
            if not rows or rows[0]['status'] not in ('proposed','running'):raise ValueError('A ação foi recusada, cancelada ou falhou. Revise o plano.')
            await asyncio.sleep(.25)

    async def execute(self,run,cancel):
        try:
            deadline=time.monotonic()+1800
            while run['cursor']<len(run['plan']['steps']):
                if cancel.is_set():break
                if run['attempts']>=12 or time.monotonic()>deadline:raise ValueError('Limite da rodada atingido. Crie uma nova tarefa a partir do progresso verificado.')
                step=run['plan']['steps'][run['cursor']]
                try:
                    run['attempts']+=1;self.save(run)
                    body=self.bind(run,step);result=await self.outcome(run,body,cancel)
                    if result is None:break
                    ok,reason=self.verify(body,result,step.get('expected',''))
                    run['history'].append({'step':step['title'],'action_id':run['action_id'],'tool':body.tool,'verified':ok,'reason':reason,'result_excerpt':json.dumps(result,ensure_ascii=False)[:1800]})
                    if not ok:raise ValueError(reason)
                    run['cursor']+=1;run.update({'state':'running','action_id':None,'current_proposal':None});self.save(run)
                except PermissionError:
                    run.update({'state':'paused','notice':'Permissão recusada. Suas regras e a janela/pasta autorizada não foram alteradas.'});self.save(run);return
                except (ValueError,OSError) as exc:
                    if not run['allow_replan'] or run['repairs']>=2 or cancel.is_set():raise
                    run['repairs']+=1;run['notice']='Replanejando após observação: '+str(exc);self.save(run)
                    replacement=await self.generate_plan(run,cancel,json.dumps({'failure':str(exc),'completed':run['history']},ensure_ascii=False))
                    # Verified steps stay in history; the replacement covers what remains.
                    run['plan']={'steps':run['plan']['steps'][:run['cursor']]+replacement.model_dump()['steps']};run['action_id']=None;run['current_proposal']=None;self.save(run)
            interrupted=cancel.is_set() and run['cursor']<len(run['plan']['steps'])
            run.update({'state':'paused' if interrupted else 'completed','notice':'Interrompida; ações verificadas permanecem registradas e não serão repetidas.' if interrupted else 'Plano aprovado executado; resultados conferidos. Revise as evidências para confirmar o alcance do objetivo.'})
            if not interrupted:run.update({'action_id':None,'current_proposal':None})
        except asyncio.CancelledError:
            run.update({'state':'paused','notice':'Execução encerrada; retome após revisar as evidências.'})
        except Exception as exc:run.update({'state':'needs_review','notice':str(exc)[:500]})
        finally:self.engine.active.pop('task:'+run['id'],None);self.save(run)
