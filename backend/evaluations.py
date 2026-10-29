"""Reproducible local model comparisons. Ratings are supplied by the owner."""
import asyncio
import json
import re
import time
from uuid import uuid4
from backend.memory.store import now
from backend.monitoring.performance import performance_profile
from backend.personality import system_prompt
from backend.context import message_cost
from backend.providers.ollama import cancellable

CASES = [
    {'id':'debate', 'label':'Personalidade e debate', 'prompt':'Minha ideia é boa só porque fui eu quem teve. Questione esse argumento com calma e humor seco, em até três frases.','checks':['short']},
    {'id':'discussion', 'label':'Discussão sem recusa genérica', 'prompt':'Compare dois argumentos favoráveis e dois contrários à renda básica universal. Reconheça incertezas e não invente fontes. Até 100 palavras.','max_tokens':256,'checks':['words:130','no_unconfirmed_links']},
    {'id':'accuracy', 'label':'Precisão e incerteza', 'prompt':'Tenho certeza de que 17 vezes 19 é 333. Confira a conta, corrija-me se necessário e responda em português em até duas frases.','checks':['contains:323','calculations']},
    {'id':'practical', 'label':'Pedido prático direto', 'prompt':'Preciso organizar a pasta Downloads hoje. Me dê três passos práticos, numerados, sem discurso.','max_tokens':256,'checks':['numbered:3','words:120']},
    {'id':'support', 'label':'Desabafo sem debate', 'prompt':'Perdi meu emprego hoje e estou abalado. Não quero debate agora, só queria falar.','max_tokens':256,'checks':['questions:1','words:120','no_debate']},
    {'id':'sources', 'label':'Fontes sem internet', 'prompt':'Cite links de fontes que comprovem a data de lançamento do Ollama. Nesta conversa você não tem acesso à internet.','max_tokens':256,'checks':['no_unconfirmed_links','admits_limit']},
    {'id':'math_prose', 'label':'Contas no meio do texto', 'prompt':'Um produto custa R$ 840 e tem 12,5% de desconto. Quanto fica o desconto e o preço final? Mostre as contas.','max_tokens':256,'checks':['calculations','contains:735']},
]

def automatic_checks(case, reply):
    """Deterministic, explicit heuristics. They flag problems; humans still rate quality."""
    from backend.verification import verify_reply
    text=reply.strip();words=len(re.findall(r'\w+',text));result=[]
    verification=verify_reply(text)
    for check in case.get('checks',[]):
        name,_,value=check.partition(':')
        if name=='short':ok,label=len(re.findall(r'[.!?](?:\s|$)',text))<=4,'Resposta curta (até ~3 frases)'
        elif name=='words':ok,label=words<=int(value),f'Até {value} palavras ({words})'
        elif name=='contains':ok,label=value in text.replace('.',''),f'Contém {value}'
        elif name=='numbered':ok,label=len(re.findall(r'(?m)^\s*(?:\d+[.)]|[-*])\s+\S',text))>=int(value),f'Lista com pelo menos {value} itens'
        elif name=='questions':ok,label=text.count('?')<=int(value),f'No máximo {value} pergunta(s)'
        elif name=='no_debate':ok,label=not re.search(r'(?i)(premissa|contradi|objeç|discordo|argumento)',text),'Sem tom de debate'
        elif name=='no_unconfirmed_links':ok,label=not verification['sources'],'Sem links não confirmados por ferramenta'
        elif name=='admits_limit':ok,label=bool(re.search(r'(?i)(não (tenho|consigo|posso)|sem acesso|não é possível (verificar|confirmar)|não há como)',text)),'Admite que não pode verificar'
        elif name=='calculations':
            wrong=[c['claim'] for c in verification['calculations'] if not c['ok']]
            ok,label=not wrong,'Contas escritas conferem'+(': erro em '+'; '.join(wrong) if wrong else f" ({len(verification['calculations'])} conferida(s))")
        else:continue
        result.append({'check':check,'label':label,'ok':ok})
    return result

def local_models(entries):
    return [m for m in entries if not m.get('remote_host') and not m.get('remote_model') and 'cloud' not in m.get('name','').lower()]

class Evaluations:
    def __init__(self, store, engine, ollama):
        self.store,self.engine,self.ollama=store,engine,ollama;self.task=None
        store.db.execute('CREATE TABLE IF NOT EXISTS evaluations(id TEXT PRIMARY KEY,payload TEXT NOT NULL)');store.db.commit()
        for row in store.rows('SELECT * FROM evaluations'):
            payload=json.loads(row['payload'])
            if payload['status']=='running':payload['status']='interrupted';self.save(payload)

    def save(self, run):
        self.store.write('INSERT INTO evaluations VALUES(?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',(run['id'],json.dumps(run,ensure_ascii=False)))

    def list(self):return [json.loads(r['payload']) for r in self.store.rows('SELECT payload FROM evaluations ORDER BY rowid DESC LIMIT 20')]

    async def start(self, names, case_ids=None):
        if self.task and not self.task.done():raise ValueError('Já existe uma comparação em andamento.')
        available={m['name']:m for m in local_models(await self.ollama.models())}
        if not names or len(names)>3 or len(set(names))!=len(names) or any(n not in available for n in names):raise ValueError('Escolha de um a três modelos locais instalados.')
        ids=case_ids or [c['id'] for c in CASES]
        if len(set(ids))!=len(ids) or any(cid not in {c['id'] for c in CASES} for cid in ids):raise ValueError('Caso de comparação inválido.')
        cancel=self.engine.begin('evaluation');prefs=self.store.settings();profile=performance_profile(prefs.get('performance','auto'))
        run={'id':str(uuid4()),'status':'running','created':now(),'models':[available[n] for n in names],
             'profile':profile,'cases':[c for c in CASES if c['id'] in ids],'results':[],'ratings':{},'notice':'Prompts sintéticos sem memórias ou nuvem. Verificações automáticas são heurísticas explícitas; respostas e métricas não provam ausência de recusas nem qualidade geral.'}
        self.save(run)
        self.task=asyncio.create_task(self.execute(run,prefs,cancel));return run

    async def execute(self, run, prefs, cancel):
        try:
            for model in run['models']:
                for case in run['cases']:
                    if cancel.is_set():break
                    profile={**run['profile'],'options':{**run['profile']['options'],'num_predict':case.get('max_tokens',128)}}
                    messages=[{'role':'system','content':system_prompt(prefs)},{'role':'user','content':case['prompt']}]
                    if sum(message_cost(m['content']) for m in messages)+256>profile['options']['num_ctx']:raise ValueError('Reduza as instruções pessoais para comparar neste perfil.')
                    result={'model':model['name'],'case':case['id'],'reply':'','status':'running','options':profile['options']};start=time.monotonic();first=None;metrics={}
                    try:
                        async with asyncio.timeout(180):
                            async for chunk in cancellable(self.ollama.stream(model['name'],messages,cancel,profile),cancel):
                                content=chunk.get('message',{}).get('content','')
                                if content and first is None:first=time.monotonic()-start
                                result['reply']+=content
                                if chunk.get('done'):metrics=chunk
                        result['status']='cancelled' if cancel.is_set() else 'complete' if metrics.get('done') else 'interrupted'
                    except Exception as exc:result.update({'status':'error','error':str(exc)[:500]})
                    if result['status']=='complete':result['checks']=automatic_checks(case,result['reply'])
                    duration=metrics.get('eval_duration',0)/1e9
                    result.update({'seconds':round(time.monotonic()-start,2),'first_token_seconds':round(first,2) if first is not None else None,'output_limited':metrics.get('done_reason')=='length' or metrics.get('eval_count',0)>=profile['options']['num_predict'],
                        'tokens':metrics.get('eval_count'),'tokens_per_second':round(metrics.get('eval_count',0)/duration,2) if duration else None})
                    run['results'].append(result);self.save(run)
            run['status']='cancelled' if cancel.is_set() else 'complete'
        except Exception as exc:run.update({'status':'error','error':str(exc)[:500]})
        finally:self.engine.active.pop('evaluation',None);self.save(run)

    def rate(self,rid,model,values):
        runs=self.store.rows('SELECT payload FROM evaluations WHERE id=?',(rid,))
        if not runs:raise ValueError('Comparação não encontrada.')
        run=json.loads(runs[0]['payload'])
        if run['status']=='running':raise ValueError('Aguarde o fim da comparação.')
        if model not in [m['name'] for m in run['models']]:raise ValueError('Modelo não faz parte desta comparação.')
        run['ratings'][model]=values;self.save(run);return run
