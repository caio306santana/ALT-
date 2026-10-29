"""Feature routes installed with the same authenticated session dependency."""
import json
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field,ConfigDict
from backend.memory.library import MemoryBody
from backend.tools.service import ToolProposal
from backend.providers.anthropic import AnthropicConfig

class PermissionBody(BaseModel):
    model_config=ConfigDict(extra='forbid')
    level:Literal[1,2]
class ScopeBody(BaseModel):
    model_config=ConfigDict(extra='forbid')
    path:str=Field(min_length=1,max_length=1000)
class GrantBody(BaseModel):
    model_config=ConfigDict(extra='forbid')
    level:Literal[3,4]
    scope_ids:list[str]=Field(default_factory=list,max_length=20)
class KeyBody(BaseModel):
    model_config=ConfigDict(extra='forbid')
    key:str=Field(min_length=1,max_length=500)
class ThemeBody(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=60)
    accent:str=Field(pattern=r'^#[0-9a-fA-F]{6}$')
    secondary:str=Field(default='#00c9f5',pattern=r'^#[0-9a-fA-F]{6}$')
    appearance:Literal['dark','light']='dark'
    opacity:int=Field(default=94,ge=65,le=100)
    glow:int=Field(default=35,ge=0,le=100)

def install_features(app,auth,store,library,tools,codex,anthropic,vault,engine,ollama,receipts):
    router=APIRouter(dependencies=[Depends(auth)])

    @router.get('/memories')
    async def memories():return library.list()
    @router.post('/memories')
    async def create_memory(body:MemoryBody):return library.save(body)
    @router.put('/memories/{mid}')
    async def edit_memory(mid:str,body:MemoryBody):
        try:return library.save(body,mid)
        except KeyError:raise HTTPException(404,'Memória não encontrada')
    @router.delete('/memories/{mid}')
    async def delete_memory(mid:str):library.delete(mid);return {'ok':True}
    @router.get('/memories/export')
    async def export_memories():return library.export()

    store.db.execute('CREATE TABLE IF NOT EXISTS themes(name TEXT PRIMARY KEY,payload TEXT NOT NULL)');store.db.commit()
    @router.get('/themes')
    async def themes():return [json.loads(r['payload']) for r in store.rows('SELECT payload FROM themes ORDER BY name')]
    @router.post('/themes')
    async def save_theme(body:ThemeBody):
        if len(store.rows('SELECT name FROM themes'))>=20 and not store.rows('SELECT name FROM themes WHERE name=?',(body.name,)):raise ValueError('Limite de 20 temas salvos.')
        store.write('INSERT INTO themes VALUES(?,?) ON CONFLICT(name) DO UPDATE SET payload=excluded.payload',(body.name,json.dumps(body.model_dump())))
        return body.model_dump()
    @router.delete('/themes/{name}')
    async def delete_theme(name:str):store.write('DELETE FROM themes WHERE name=?',(name,));return {'ok':True}

    @router.get('/permissions')
    async def permissions():return tools.status()
    @router.put('/permissions')
    async def permissions_set(body:PermissionBody):return tools.set_level(body.level)
    @router.post('/permissions/grant')
    async def grant(body:GrantBody):return tools.grant(body.level,body.scope_ids)
    @router.post('/permissions/revoke')
    async def revoke():tools.revoke();return tools.status()
    # Only the main-process folder picker may call this route; omitted from renderer API allowlist.
    @router.post('/scopes')
    async def scopes_add(body:ScopeBody):return tools.add_scope(body.path)
    @router.delete('/scopes/{sid}')
    async def scopes_remove(sid:str):
        tools.revoke();store.write('DELETE FROM scopes WHERE id=?',(sid,));return {'ok':True}
    @router.post('/tools/propose')
    async def propose(body:ToolProposal):return tools.proposal(body)
    @router.post('/tools/approve/{aid}')
    async def approve(aid:str):return await tools.approve(aid)
    @router.get('/tools/proposal/{aid}')
    async def proposal_detail(aid:str):return tools.describe(aid)
    @router.post('/tools/renew/{aid}')
    async def renew_proposal(aid:str):return tools.renew(aid)
    @router.post('/tools/confirm/{aid}')
    async def critical_confirm(aid:str):
        tools.describe(aid);tools.critical_confirmed.add(aid);return {'confirmed':True}
    @router.post('/tools/reject/{aid}')
    async def reject(aid:str):
        tools.pending.pop(aid,None);store.write("UPDATE actions SET status='rejected' WHERE id=? AND status='proposed'",(aid,));return {'ok':True}
    @router.get('/tools/history')
    async def tool_history():return tools.history()
    @router.get('/conversations/{cid}/actions')
    async def conversation_actions(cid:str):return tools.conversation_actions(cid)
    @router.get('/audit')
    async def audit():return store.rows('SELECT * FROM audit ORDER BY id DESC LIMIT 200')

    @router.get('/providers')
    async def providers():
        import asyncio
        return {'providers':[await asyncio.to_thread(codex.status),anthropic.status(),{'id':'claude-subscription','name':'Claude Code · assinatura','available':False,'location':'cloud','billing':'subscription','reason':'Integração de claude.ai em produtos terceiros exige aprovação da Anthropic; indisponível nesta versão.'}], 'anthropic':anthropic.config().model_dump(),'key_configured':vault.configured(),'api_models':vault.data().get('models',[]),'usage':anthropic.totals()}
    @router.put('/providers/anthropic')
    async def config(body:AnthropicConfig):return anthropic.save(body)
    # Main-process native confirmation only; never part of generic renderer allowlist.
    @router.put('/credentials/anthropic')
    async def key(body:KeyBody):vault.save(body.key);store.audit('credential_configured','anthropic');return await anthropic.verify_key()
    @router.delete('/credentials/anthropic')
    async def clear_key():vault.clear();return {'configured':False}

    @router.post('/game/enable')
    async def game_enable():
        import asyncio
        engine.stop();engine.game_mode=True;tools.revoke();receipts.revoke_all();store.audit('game_mode_enabled')
        model=store.settings().get('model','')
        unloaded=False;message='Gerações interrompidas. Nenhum modelo selecionado para descarregar.'
        if model and not model.startswith('cloud:'):
            for _ in range(30):
                if not engine.active:break
                await asyncio.sleep(.1)
            try:
                await ollama.unload(model)
                running=await ollama.running()
                unloaded=running is not None and not any(m.get('name')==model for m in running)
                message='Modelo selecionado descarregado.' if unloaded else 'Descarga solicitada; ainda não confirmada pelo Ollama.'
            except Exception:message='Ações suspensas, mas não foi possível descarregar o modelo.'
        return {'enabled':True,'model_unloaded':unloaded,'message':message}
    @router.post('/game/disable')
    async def game_disable():engine.stopped=False;engine.game_mode=False;store.audit('game_mode_disabled');return {'enabled':False,'message':'Modo normal retomado em observação.'}

    app.include_router(router)
