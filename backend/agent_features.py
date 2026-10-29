"""Multi-step tasks and project knowledge routes, behind the same session auth."""
import asyncio
from pathlib import Path
from fastapi import APIRouter,Depends
from pydantic import BaseModel,ConfigDict,Field
from backend.tasks import TaskManager,TaskPlan
from backend.memory.knowledge import Knowledge
from backend.memory.library import MemoryBody

class Strict(BaseModel): model_config=ConfigDict(extra='forbid')
class TaskBody(Strict):
    goal:str=Field(min_length=1,max_length=1500)
    model:str=Field(min_length=1,max_length=200)
    scope_id:str=Field(default='',max_length=64)
    window_id:str=Field(default='',max_length=64)
    conversation_id:str=Field(default='',max_length=64)
class StartBody(Strict): allow_replan:bool=False
class ProjectBody(Strict): name:str=Field(min_length=1,max_length=100)
class LinkBody(Strict): project_id:str=Field(default='',max_length=64)
class DocumentBody(Strict): path:str=Field(min_length=1,max_length=1000)
class SearchBody(Strict):
    query:str=Field(min_length=1,max_length=1500)
    project_id:str=Field(default='',max_length=64)
class WindowGrantBody(Strict): candidate_id:str=Field(min_length=1,max_length=64)
class SummaryBody(Strict):
    conversation_id:str=Field(max_length=64)
    model:str=Field(min_length=1,max_length=200)

def install_agent_features(app,auth,store,library,continuity,tools,engine,ollama):
    router=APIRouter(dependencies=[Depends(auth)])
    tasks=TaskManager(store,engine,tools,ollama);knowledge=Knowledge(store,library,continuity,engine,ollama)
    app.state.tasks=tasks;app.state.knowledge=knowledge

    @router.get('/tasks')
    async def task_list():return tasks.list()
    @router.get('/tasks/{rid}')
    async def task_detail(rid:str):return tasks.get(rid)
    @router.post('/tasks')
    async def task_plan(body:TaskBody):
        if body.window_id and body.window_id not in {g['id'] for g in tools.gui.grants()}:raise ValueError('Janela não autorizada. Autorize em Ferramentas.')
        return tasks.plan(body.goal,body.model,body.scope_id,body.window_id,body.conversation_id)
    @router.put('/tasks/{rid}/plan')
    async def task_review(rid:str,body:TaskPlan):return tasks.review(rid,body)
    @router.post('/tasks/{rid}/start')
    async def task_start(rid:str,body:StartBody):return await tasks.start(rid,body.allow_replan)
    @router.post('/tasks/{rid}/pause')
    async def task_pause(rid:str):return tasks.pause(rid)

    # Windows UI Automation: the renderer lists windows; only the native
    # confirmation dialog may grant one (route omitted from the allowlist).
    @router.get('/windows/candidates')
    async def window_candidates():
        rows=await asyncio.to_thread(tools.gui.inventory)
        return [{'candidate_id':r['candidate_id'],'title':r['title'],'app':Path(r['exe']).stem} for r in rows]
    @router.get('/windows/grants')
    async def window_grants():return [{'id':g['id'],'title':g['title'],'app':Path(g['exe']).stem} for g in tools.gui.grants()]
    @router.post('/windows/grants')
    async def window_grant(body:WindowGrantBody):
        gid=await asyncio.to_thread(tools.gui.grant,body.candidate_id);return {'id':gid}
    @router.delete('/windows/grants/{gid}')
    async def window_revoke(gid:str):tools.gui.revoke(gid);return {'ok':True}

    @router.get('/projects')
    async def projects():return knowledge.projects()
    @router.post('/projects')
    async def create_project(body:ProjectBody):return knowledge.create_project(body.name)
    @router.delete('/projects/{pid}')
    async def delete_project(pid:str):return knowledge.delete_project(pid)
    @router.get('/projects/{pid}/documents')
    async def documents(pid:str):return knowledge.documents(pid)
    # Native file picker only; omitted from the renderer allowlist like /scopes.
    @router.post('/projects/{pid}/documents')
    async def import_document(pid:str,body:DocumentBody):return await asyncio.to_thread(knowledge.import_document,pid,body.path)
    @router.delete('/documents/{did}')
    async def delete_document(did:str):return knowledge.delete_document(did)
    @router.get('/conversations/{cid}/project')
    async def conversation_project(cid:str):return {'project_id':knowledge.project_for(cid)}
    @router.put('/conversations/{cid}/project')
    async def link_project(cid:str,body:LinkBody):return knowledge.link(cid,body.project_id)
    @router.get('/knowledge/status')
    async def knowledge_status():return knowledge.status()
    @router.post('/knowledge/index')
    async def index():return await knowledge.index()
    @router.post('/knowledge/index/cancel')
    async def cancel_index():
        event=engine.active.get('semantic-index')
        if event:event.set()
        return {'ok':True}
    @router.post('/knowledge/search')
    async def search(body:SearchBody):return await knowledge.search(body.query,body.project_id)
    @router.get('/projects/{pid}/summaries')
    async def summaries(pid:str):return knowledge.summary_drafts(pid)
    @router.post('/projects/summaries/draft')
    async def draft_summary(body:SummaryBody):return await knowledge.draft_summary(body.conversation_id,body.model)
    @router.post('/projects/summaries/{did}/approve')
    async def approve_summary(did:str,body:MemoryBody):return knowledge.approve_summary(did,body)
    @router.post('/projects/summaries/{did}/discard')
    async def discard_summary(did:str):
        store.write("UPDATE project_summary_drafts SET status='discarded' WHERE id=? AND status='draft'",(did,));return {'ok':True}
    app.include_router(router)
    return tasks,knowledge
