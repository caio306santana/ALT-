import json
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,ConfigDict,Field
from backend.security.policy import OwnerPolicy
from backend.memory.library import MemoryBody
from backend.memory.continuity import Continuity
from backend.evaluations import Evaluations,CASES
from backend.personality import system_prompt

class Strict(BaseModel): model_config=ConfigDict(extra='forbid')
class ProgramBody(Strict): path:str=Field(min_length=1,max_length=1000)
class DesktopReport(Strict):
    result:dict|None=None
    error:str|None=Field(default=None,max_length=500)
class DraftBody(Strict):
    conversation_id:str=Field(max_length=64)
    model:str=Field(min_length=1,max_length=120)
class ImportBody(Strict): items:list[MemoryBody]=Field(min_length=1,max_length=300)
class EvaluationBody(Strict):
    models:list[str]=Field(min_length=1,max_length=3)
    case_ids:list[Literal['debate','discussion','accuracy']]=Field(default_factory=lambda:['debate','discussion','accuracy'],min_length=1,max_length=3)
class RatingBody(Strict):
    model:str=Field(max_length=120)
    portuguese:int=Field(ge=1,le=5)
    personality:int=Field(ge=1,le=5)
    usefulness:int=Field(ge=1,le=5)
    freedom:int=Field(ge=1,le=5)
    notes:str=Field(default='',max_length=1000)

def install_workspace_features(app,auth,store,library,tools,engine,ollama,receipts,desktop):
    router=APIRouter(dependencies=[Depends(auth)])
    continuity=Continuity(store,library,engine,ollama);evaluations=Evaluations(store,engine,ollama)
    app.state.continuity=continuity;app.state.evaluations=evaluations;app.state.desktop=desktop

    @router.get('/policy')
    async def policy():return {**tools.policy.describe(),'effective_prompt':system_prompt({**store.settings(),'owner_policy':tools.policy.current().model_dump()})}
    # Native-only writes, intentionally omitted from the generic IPC allowlist.
    @router.put('/policy')
    async def save_policy(body:OwnerPolicy):
        result=tools.policy.save(body);tools.cancel_pending();receipts.revoke_all();return result
    @router.get('/programs')
    async def programs():return tools.programs()
    @router.post('/programs')
    async def add_program(body:ProgramBody):return tools.add_program(body.path)
    @router.delete('/programs/{pid}')
    async def remove_program(pid:str):
        tools.revoke();store.write('DELETE FROM programs WHERE id=?',(pid,));return tools.programs()
    @router.get('/desktop/jobs')
    async def claim():return {'job':desktop.claim()}
    @router.get('/desktop/jobs/{jid}')
    async def active(jid:str):return {'active':desktop.active(jid)}
    @router.post('/desktop/jobs/{jid}')
    async def finish(jid:str,body:DesktopReport):return {'accepted':desktop.finish(jid,body.result,body.error)}

    @router.get('/memories/search')
    async def search(q:str=''):return continuity.recall(q[:500])
    @router.post('/memories/import')
    async def import_items(body:ImportBody):return continuity.import_memories(body.items)
    @router.post('/continuity/draft')
    async def draft(body:DraftBody):return await continuity.draft(body.conversation_id,body.model)
    @router.post('/continuity/approve/{did}')
    async def approve(did:str,body:MemoryBody):return continuity.approve(did,body)
    @router.get('/evaluations')
    async def list_evaluations():return {'cases':CASES,'runs':evaluations.list()}
    @router.post('/evaluations')
    async def evaluate(body:EvaluationBody):return await evaluations.start(body.models,body.case_ids)
    @router.post('/evaluations/cancel')
    async def cancel():
        event=engine.active.get('evaluation')
        if event:event.set()
        return {'ok':True}
    @router.put('/evaluations/{rid}/rating')
    async def rate(rid:str,body:RatingBody):return evaluations.rate(rid,body.model,body.model_dump(exclude={'model'}))
    app.include_router(router)
    return continuity
