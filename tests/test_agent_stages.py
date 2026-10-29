"""Stages 2, 3 and 5: multi-step tasks, project knowledge and reply verification."""
import hashlib
import json
import math
import re
import time
from fastapi.testclient import TestClient
from backend.api import create_app
from backend.evaluations import CASES,automatic_checks
from backend.tools.service import ToolProposal,SENSITIVE
from backend.verification import verify_reply
from test_backend import FixtureProvider,TOKEN,HEADERS,conversation,events

PLAN={'steps':[
    {'title':'Calcular','action':{'tool':'calculate','expression':'6*7'},'expected':'42'},
    {'title':'Gravar nota','action':{'tool':'write_text','path':'notas.txt','content':'Resultado 42','scope_id':'outro-escopo'}},
    {'title':'Conferir nota','action':{'tool':'read_text','path':'notas.txt','app':''},'expected':'Resultado 42'},
]}

# EmbeddingGemma task-prompt words carry no meaning in the fake vectors.
PROMPT_WORDS={'task','search','result','query','title','text','none'}

class AgentProvider(FixtureProvider):
    def __init__(self):
        super().__init__();self.plan=PLAN;self.reply=['Olá, ','mundo!'];self.embed_fail=False;self.embedded=0
    async def models(self):
        return [*await super().models(),{'name':'embeddinggemma:latest','digest':'gemma-digest','size':1}]
    async def stream(self,model,messages,cancel,profile=None):
        self.profiles.append(profile);self.contexts.append((model,messages))
        if profile and profile.get('format'):
            # A list holds successive answers, e.g. a flawed plan and its correction.
            plan=self.plan.pop(0) if isinstance(self.plan,list) and len(self.plan)>1 else self.plan[0] if isinstance(self.plan,list) else self.plan
            yield {'message':{'content':json.dumps(plan)}}
        else:
            for part in self.reply:yield {'message':{'content':part}}
        yield {'done':True,'eval_count':4,'eval_duration':2_000_000_000,'prompt_eval_count':10}
    async def embed(self,texts):
        if self.embed_fail:raise ValueError('Instale EmbeddingGemma para ativar a busca semântica local.')
        self.embedded+=len(texts);vectors=[]
        for text in texts:
            # Deterministic bag of words: shared words give similar vectors.
            vector=[0.0]*256
            for word in re.findall(r'\w+',text.casefold()):
                if len(word)>3 and word not in PROMPT_WORDS:vector[int(hashlib.sha256(word.encode()).hexdigest(),16)%256]+=1
            vectors.append(vector if any(vector) else [1.0]+[0.0]*255)
        return vectors

def agent_client(tmp_path):
    provider=AgentProvider();app=create_app(tmp_path,TOKEN,provider)
    return app,provider,TestClient(app,headers=HEADERS)

def wait(client,path,done,timeout=10):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        value=client.get(path).json()
        if done(value):return value
        time.sleep(.05)
    raise AssertionError(client.get(path).json())

def calculate_actions(app):return app.state.store.rows("SELECT id FROM actions WHERE tool='calculate'")

def test_task_is_planned_reviewed_paused_and_resumed_without_repeating_actions(tmp_path):
    app,provider,client=agent_client(tmp_path)
    with client:
        scope=client.get('/permissions').json()['scopes'][0]['id']
        client.post('/permissions/grant',json={'level':3,'scope_ids':[scope]})
        run=client.post('/tasks',json={'goal':'Calcule 6*7 e salve em notas.txt','model':'fixture:4b','scope_id':scope}).json()
        assert run['state']=='planning' and not app.state.store.rows('SELECT id FROM actions')
        run=wait(client,'/tasks/'+run['id'],lambda r:r['state']!='planning')
        assert run['state']=='draft' and len(run['plan']['steps'])==3
        assert 'windows_read' not in provider.profiles[-1]['format']['properties']['steps']['items']['properties']['action']['properties']['tool']['enum']
        # Empty optional arguments from the model fall back to field defaults.
        assert run['plan']['steps'][2]['action']['app']=='notepad'
        assert client.post(f"/tasks/{run['id']}/start",json={}).status_code==200
        run=wait(client,'/tasks/'+run['id'],lambda r:r['state']=='awaiting_approval')
        assert run['cursor']==1 and run['history'][0]['verified'] and run['current_proposal']['preview']['tool']=='write_text'
        # The model asked for another scope; the task stays in its own folder.
        assert run['current_proposal']['preview']['path'].startswith(str((tmp_path/'workspace').resolve()))
        client.post(f"/tasks/{run['id']}/pause")
        run=wait(client,'/tasks/'+run['id'],lambda r:r['state']=='paused')
        assert app.state.store.rows('SELECT status FROM actions WHERE id=?',(run['action_id'],))[0]['status']=='cancelled'
        client.post(f"/tasks/{run['id']}/start",json={})
        run=wait(client,'/tasks/'+run['id'],lambda r:r['state']=='awaiting_approval')
        assert len(calculate_actions(app))==1
        assert client.post('/tools/approve/'+run['current_proposal']['id']).status_code==200
        run=wait(client,'/tasks/'+run['id'],lambda r:r['state'] not in ('running','awaiting_approval'))
        assert run['state']=='completed' and [h['verified'] for h in run['history']]==[True,True,True]
        assert (tmp_path/'workspace'/'notas.txt').read_text(encoding='utf-8')=='Resultado 42'
        assert len(calculate_actions(app))==1
        # Task actions appear in the task's conversation like chat proposals.
        assert len(client.get(f"/conversations/{run['conversation_id']}/actions").json())==4

def test_resume_reuses_an_action_that_completed_before_interruption(tmp_path):
    app,provider,client=agent_client(tmp_path)
    with client:
        scope=client.get('/permissions').json()['scopes'][0]['id']
        client.post('/permissions/grant',json={'level':3,'scope_ids':[scope]})
        provider.plan={'steps':[PLAN['steps'][0]]}
        run=client.post('/tasks',json={'goal':'Calcule','model':'fixture:4b','scope_id':scope}).json()
        run=wait(client,'/tasks/'+run['id'],lambda r:r['state']=='draft')
        tools=app.state.tools;proposal=tools.proposal(ToolProposal(tool='calculate',expression='6*7'),run['conversation_id'])
        client.post('/tools/approve/'+proposal['id'])
        stored=app.state.tasks.get(run['id']);stored.update({'state':'paused','action_id':proposal['id']});app.state.tasks.save(stored)
        client.post(f"/tasks/{run['id']}/start",json={})
        run=wait(client,'/tasks/'+run['id'],lambda r:r['state']=='completed')
        assert run['history'][0]['action_id']==proposal['id'] and len(calculate_actions(app))==1

def test_task_limits_follow_policy_scope_and_stop(tmp_path):
    app,provider,client=agent_client(tmp_path)
    with client:
        run=client.post('/tasks',json={'goal':'Sem pasta','model':'fixture:4b'}).json()
        run=wait(client,'/tasks/'+run['id'],lambda r:r['state']!='planning')
        # File tools are not offered without a chosen folder, so this plan is refused.
        assert run['state']=='error' and 'indisponível' in run['notice']
        assert client.post('/tasks',json={'goal':'x','model':'fixture:4b','scope_id':'nao-existe'}).status_code==400
        assert client.post('/tasks',json={'goal':'x','model':'inexistente:1b'}).status_code==200
        failed=wait(client,'/tasks',lambda rows:rows[0]['state']=='error')[0]
        assert 'modelo local' in failed['notice']
        provider.plan={'steps':[PLAN['steps'][0]]}
        run=client.post('/tasks',json={'goal':'Calcule','model':'fixture:4b'}).json()
        run=wait(client,'/tasks/'+run['id'],lambda r:r['state']=='draft')
        assert client.post(f"/tasks/{run['id']}/start",json={}).status_code==403
        client.put('/permissions',json={'level':2})
        client.post(f"/tasks/{run['id']}/start",json={})
        wait(client,'/tasks/'+run['id'],lambda r:r['state']=='awaiting_approval')
        client.post('/actions/stop')
        run=wait(client,'/tasks/'+run['id'],lambda r:r['state']=='paused')
        assert client.post(f"/tasks/{run['id']}/start",json={}).status_code==403
        edited={'steps':[{'title':'Outro','action':{'tool':'calculate','expression':'1+1'}}]}
        assert client.put(f"/tasks/{run['id']}/plan",json=edited).json()['plan']['steps'][0]['title']=='Outro'

def test_documents_are_indexed_searched_and_recalled_by_project(tmp_path):
    app,provider,client=agent_client(tmp_path)
    document=tmp_path/'receitas.md';document.write_text('# Receitas\nO bolo de cenoura leva cenoura, ovos, farinha e cobertura de chocolate.',encoding='utf-8')
    other=tmp_path/'outro.txt';other.write_text('Planilha de despesas mensais do escritório.',encoding='utf-8')
    with client:
        cozinha=client.post('/projects',json={'name':'Cozinha'}).json();escritorio=client.post('/projects',json={'name':'Escritório'}).json()
        imported=client.post(f"/projects/{cozinha['id']}/documents",json={'path':str(document)}).json()
        assert imported['chunks']==1 and not imported['duplicate']
        assert client.post(f"/projects/{cozinha['id']}/documents",json={'path':str(document)}).json()['duplicate']
        client.post(f"/projects/{escritorio['id']}/documents",json={'path':str(other)})
        assert client.post(f"/projects/{cozinha['id']}/documents",json={'path':'relativo.txt'}).status_code==400
        client.post('/knowledge/index')
        status=wait(client,'/knowledge/status',lambda s:s['status']=='complete')
        assert status['indexed']==status['items']==2
        found=client.post('/knowledge/search',json={'query':'ingredientes do bolo de cenoura'}).json()
        assert found[0]['kind']=='chunk' and 'cenoura' in found[0]['content'] and found[0]['score']>0
        assert client.post('/knowledge/search',json={'query':'bolo de cenoura','project_id':escritorio['id']}).json()==[]
        policy=client.get('/policy').json()['policy'];policy['memory_recall']='semantic';client.put('/policy',json=policy)
        cid=conversation(client);client.put(f'/conversations/{cid}/project',json={'project_id':cozinha['id']})
        data=events(client.post('/chat',json={'conversation_id':cid,'model':'fixture:4b','content':'Como faço o bolo de cenoura?'}))
        recalled=data[0]['recalled_memories']
        assert recalled and recalled[0]['kind']=='chunk' and recalled[0]['mode'].startswith('semântica')
        assert 'cobertura de chocolate' in provider.contexts[-1][1][0]['content']
        # Edited content is never ranked with a stale vector.
        app.state.store.write('UPDATE document_chunks SET content=? WHERE document_id=?',('Texto trocado sem cenoura.',imported['id']))
        assert client.post('/knowledge/search',json={'query':'bolo de cenoura'}).json()==[]
        provider.embed_fail=True
        estimate=client.post('/chat/estimate',json={'conversation_id':cid,'model':'fixture:4b','content':'receita de cenoura nova'}).json()
        assert estimate['recall_mode'].startswith('termos')
        client.delete('/documents/'+imported['id'])
        assert client.get(f"/projects/{cozinha['id']}/documents").json()==[]
        assert not app.state.store.rows("SELECT * FROM semantic_vectors WHERE kind='chunk' AND item_id NOT IN (SELECT id FROM document_chunks)")

def test_project_summary_is_a_reviewed_draft_linked_to_the_project(tmp_path):
    app,provider,client=agent_client(tmp_path)
    with client:
        project=client.post('/projects',json={'name':'Aurora'}).json();cid=conversation(client)
        body={'conversation_id':cid,'model':'fixture:4b'}
        assert client.post('/projects/summaries/draft',json=body).status_code==400
        client.put(f'/conversations/{cid}/project',json={'project_id':project['id']})
        client.post('/chat',json={'conversation_id':cid,'model':'fixture:4b','content':'Aurora usa Markdown.'})
        draft=client.post('/projects/summaries/draft',json=body).json()
        assert client.get('/memories').json()==[] and client.get(f"/projects/{project['id']}/summaries").json()[0]['id']==draft['id']
        memory=client.post(f"/projects/summaries/{draft['id']}/approve",json={'title':'Aurora','content':'Usa Markdown.','category':'projeto'}).json()
        assert app.state.store.rows('SELECT * FROM project_memories WHERE memory_id=?',(memory['id'],))
        assert client.get(f"/projects/{project['id']}/summaries").json()==[]

def test_reply_calculations_and_links_are_checked_and_stored(tmp_path):
    app,provider,client=agent_client(tmp_path)
    with client:
        cid=conversation(client)
        provider.reply=['Conferi: 17 × 19 = 333 e 12,5% de 840 = 105. ','Fonte: https://inventada.example/artigo']
        data=events(client.post('/chat',json={'conversation_id':cid,'model':'fixture:4b','content':'Veja https://docs.ollama.com e confira 17 × 19'}))
        verification=data[-1]['metrics']['verification']
        assert [c['ok'] for c in verification['calculations']]==[False,True] and verification['calculations'][0]['actual']==323
        assert verification['sources']==[{'url':'https://inventada.example/artigo','confirmed':False}] and verification['issues']==2
        assert app.state.store.messages(cid)[-1]['metrics']['verification']['issues']==2
        provider.reply=['Segundo https://docs.ollama.com, ok.']
        data=events(client.post('/chat',json={'conversation_id':cid,'model':'fixture:4b','content':'E então?'}))
        assert data[-1]['metrics']['verification']['sources'][0]['confirmed']

def test_verification_handles_brazilian_notation_rounding_and_non_claims():
    def results(text):return [(c['stated'],c['ok']) for c in verify_reply(text)['calculations']]
    assert results('1.234 × 3 = 3.702')==[('3.702',True)]
    assert results('2/3 ≈ 0,67')==[('0,67',True)]
    assert results('10 / 4 = 2')==[('2',False)]
    assert results('100 dividido por 8 dá 12,5')==[('12,5',True)]
    assert results('Entre 2024-2025 é diferente; item 5 de 7.')==[]

def test_real_situation_cases_have_explicit_automatic_checks():
    cases={c['id']:c for c in CASES}
    assert {'practical','support','sources','math_prose'}<=set(cases)
    wrong=automatic_checks(cases['accuracy'],'Sim, 17 vezes 19 é 333.')
    assert not all(c['ok'] for c in wrong)
    assert all(c['ok'] for c in automatic_checks(cases['sources'],'Não tenho acesso à internet, então não posso confirmar links.'))
    assert not all(c['ok'] for c in automatic_checks(cases['sources'],'Veja https://ollama.com/blog/lancamento'))
    assert not all(c['ok'] for c in automatic_checks(cases['support'],'Sua premissa é frágil? Por quê? Tem certeza?'))

def test_full_access_runs_tasks_unattended_reaches_other_folders_and_downloads(tmp_path,monkeypatch):
    app,provider,client=agent_client(tmp_path)
    home=tmp_path/'home';(home/'Downloads').mkdir(parents=True);outside=tmp_path/'dados';outside.mkdir();(outside/'lista.txt').write_text('itens',encoding='utf-8')
    monkeypatch.setattr('pathlib.Path.home',classmethod(lambda cls:home))
    # pytest's temporary folder lives under AppData, which stays blocked in real use.
    monkeypatch.setattr('backend.tools.service.SENSITIVE',SENSITIVE-{'appdata'})
    saved=[]
    def fake_download(url,destination,cancel):
        destination.write_bytes(b'conteudo');saved.append(destination);return {'path':str(destination),'bytes':8}
    monkeypatch.setattr('backend.tools.service.download',fake_download)
    with client:
        scope=client.get('/permissions').json()['scopes'][0]['id']
        client.post('/permissions/grant',json={'level':4,'scope_ids':[scope]})
        tools=app.state.tools
        assert tools.scoped('windows-profile',str(outside/'lista.txt'))==outside/'lista.txt'
        for blocked in (r'\\servidor\share\x.txt',str(home/'.ssh'/'id_rsa'),str(home/'senhas.txt')):
            try:tools.scoped('windows-profile',blocked);raise AssertionError(blocked)
            except ValueError:pass
        listing=client.post('/tools/approve/'+client.post('/tools/propose',json={'tool':'list_files','scope_id':'windows-profile','path':str(outside)}).json()['id']).json()
        assert listing['result']['entries'][0]['name']=='lista.txt'
        proposal=client.post('/tools/propose',json={'tool':'download_file','url':'https://example.com/arquivos/manual.pdf'}).json()
        assert proposal['preview']['path']==str(home/'Downloads'/'manual.pdf')
        assert tools.can_auto(ToolProposal(tool='download_file',url='https://example.com/a.zip'))
        client.post('/tools/approve/'+proposal['id'])
        assert saved==[home/'Downloads'/'manual.pdf']
        assert client.post('/tools/propose',json={'tool':'download_file','url':'http://example.com/a.zip'}).status_code==400
        # A multi-step task in full access needs no approval clicks.
        provider.plan={'steps':[PLAN['steps'][0],{'title':'Gravar','action':{'tool':'write_text','path':'r.txt','content':'42'}}]}
        run=client.post('/tasks',json={'goal':'Calcule e grave','model':'fixture:4b','scope_id':scope}).json()
        wait(client,'/tasks/'+run['id'],lambda r:r['state']=='draft')
        client.post(f"/tasks/{run['id']}/start",json={})
        run=wait(client,'/tasks/'+run['id'],lambda r:r['state'] not in ('running','awaiting_approval'))
        assert run['state']=='completed' and (tmp_path/'workspace'/'r.txt').read_text()=='42'
        client.post('/actions/stop')
        assert client.get('/permissions').json()['level']==1

def test_flawed_plan_gets_one_correction_round_before_review(tmp_path):
    app,provider,client=agent_client(tmp_path)
    flawed={'steps':[{'title':'Gravar','action':{'tool':'write_text','path':'.','content':'360'}}]}
    fixed={'steps':[{'title':'Gravar','action':{'tool':'write_text','path':'resultado.txt','content':'360'}}]}
    with client:
        scope=client.get('/permissions').json()['scopes'][0]['id']
        provider.plan=[flawed,fixed]
        run=client.post('/tasks',json={'goal':'Grave 360','model':'fixture:4b','scope_id':scope}).json()
        run=wait(client,'/tasks/'+run['id'],lambda r:r['state']!='planning')
        assert run['state']=='draft' and run['plan']['steps'][0]['action']['path']=='resultado.txt'
        assert 'nome de arquivo' in provider.contexts[-1][1][-1]['content']
        provider.plan=[flawed,flawed]
        run=client.post('/tasks',json={'goal':'Grave 360','model':'fixture:4b','scope_id':scope}).json()
        run=wait(client,'/tasks/'+run['id'],lambda r:r['state']!='planning')
        assert run['state']=='error' and 'nome de arquivo' in run['notice']

def test_documents_split_by_heading_and_use_embedding_prompts(tmp_path):
    from backend.memory.knowledge import extract_document,chunks
    doc=tmp_path/'notas.md';doc.write_text('# Receitas\nBolo de cenoura.\n\nCobertura de chocolate.\n\n# Viagem\nVoo às 22h.',encoding='utf-8')
    sections=extract_document(doc)
    assert [s[0] for s in sections]==['Receitas','Viagem'] and 'Voo' not in sections[0][1]
    assert list(chunks('a'*30+'\n\n'+'b'*30,size=40,overlap=5))==['a'*30,'b'*30]
    app,provider,client=agent_client(tmp_path)
    seen=[];original=provider.embed
    async def recording(texts):seen.extend(texts);return await original(texts)
    provider.embed=recording
    with client:
        project=client.post('/projects',json={'name':'Casa'}).json()
        client.post(f"/projects/{project['id']}/documents",json={'path':str(doc)})
        client.post('/knowledge/index');wait(client,'/knowledge/status',lambda s:s['status']=='complete')
        found=client.post('/knowledge/search',json={'query':'detalhes da viagem'}).json()
        assert found[0]['title'].endswith('Viagem')
    assert any(t.startswith('title: notas.md · Viagem | text: ') for t in seen) and 'task: search result | query: detalhes da viagem' in seen
