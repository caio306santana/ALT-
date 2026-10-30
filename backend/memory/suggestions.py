"""Facts the ALT noticed about the owner, waiting for review. Nothing becomes a memory by itself.

From OpenJarvis (memory/extractor.py, memory/service.py): a background, low-priority pass after a
finished reply asks the model for durable facts as a JSON array, tolerates messy output, caps the count
and length, and scans each fact; Mark LVI's lesson is the opposite of its own code — the model must not
write memory silently, so every fact lands here for the owner to approve or dismiss."""
import asyncio
import json
import re
from uuid import uuid4
from backend.memory.store import now
from backend.memory.library import MemoryBody
from backend.security.guard import sensitive_reason

PROMPT=('Extraia fatos duráveis sobre o usuário desta conversa: preferências, identidade, metas, projetos, restrições '
        'e pessoas próximas. Só o que continuará verdadeiro amanhã; nada sobre o assistente, nada do mundo em geral, '
        'nada que o usuário não disse. Cada fato em uma frase curta em português, na terceira pessoa ("Prefere ...", '
        '"Trabalha com ..."). Se não houver nenhum, devolva [].')
SCHEMA={'type':'array','items':{'type':'string'},'maxItems':5}
MAX_FACTS=10
MAX_CHARS=200
IDLE_SECONDS=60

def parse_facts(text):
    """JSON array, an object holding one, a JSON array buried in prose, or one fact per line."""
    data=None
    try:data=json.loads(text)
    except ValueError:
        match=re.search(r'\[.*\]',text,re.S)
        if match:
            try:data=json.loads(match.group())
            except ValueError:data=None
    if isinstance(data,dict):data=next((v for v in data.values() if isinstance(v,list)),[])
    if not isinstance(data,list):
        data=[re.sub(r'^\s*(?:[-*•]|\d+[.)])\s*','',line) for line in str(text).splitlines() if line.strip().startswith(('-','*','•')) or re.match(r'\s*\d+[.)]',line)]
    facts=[]
    for item in data:
        fact=re.sub(r'\s+',' ',str(item)).strip().strip('"')
        if 8<=len(fact)<=MAX_CHARS and fact.casefold() not in {f.casefold() for f in facts}:facts.append(fact)
    return facts[:MAX_FACTS]

class MemorySuggestions:
    def __init__(self,store,library,engine,ollama):
        self.store,self.library,self.engine,self.ollama=store,library,engine,ollama;self.tasks={}
        store.db.execute('CREATE TABLE IF NOT EXISTS memory_suggestions(id TEXT PRIMARY KEY,conversation_id TEXT NOT NULL,fact TEXT NOT NULL,flagged TEXT NOT NULL,status TEXT NOT NULL,created TEXT NOT NULL)');store.db.commit()

    def enabled(self):return bool(self.store.settings().get('memory_suggestions'))

    def schedule(self,cid,model):
        if not self.enabled() or model.startswith('cloud:') or self.engine.game_mode:return
        if cid in self.tasks and not self.tasks[cid].done():return
        async def run():
            # Low priority: only after 60 s without any reply being generated.
            quiet=0
            while quiet<IDLE_SECONDS:
                await asyncio.sleep(5)
                quiet=0 if any(not k.startswith(('tool:','model-download')) for k in self.engine.active) else quiet+5
            try:await self.extract(cid,model)
            except Exception:self.store.audit('memory_suggestions_failed',cid)
        self.tasks[cid]=asyncio.create_task(run())

    async def extract(self,cid,model):
        rows=[m for m in self.store.messages(cid) if m['status']=='complete'][-4:]
        if not rows:return []
        dialogue='\n'.join(('Usuário: ' if m['role']=='user' else 'Assistente: ')+m['content'][:800] for m in rows)
        from backend.monitoring.performance import performance_profile
        profile=performance_profile(self.store.settings().get('performance','auto'),self.engine.game_mode)
        profile['options']['num_predict']=200;profile['format']=SCHEMA
        text=''
        cancel=asyncio.Event()
        async for chunk in self.ollama.stream(model,[{'role':'system','content':PROMPT},{'role':'user','content':dialogue}],cancel,profile):
            text+=chunk.get('message',{}).get('content','')
        return self.add(cid,parse_facts(text))

    def add(self,cid,facts):
        known={r['content'].casefold() for r in self.store.rows('SELECT content FROM memories')}|{r['fact'].casefold() for r in self.store.rows('SELECT fact FROM memory_suggestions')}
        added=[]
        for fact in facts:
            reason=sensitive_reason(fact)
            if fact.casefold() in known or reason.startswith('uma credencial'):continue
            sid=str(uuid4());self.store.write('INSERT INTO memory_suggestions VALUES(?,?,?,?,?,?)',(sid,cid,fact,reason,'pending',now()))
            added.append(sid)
        return added

    def pending(self):return self.store.rows("SELECT id,conversation_id,fact,flagged,created FROM memory_suggestions WHERE status='pending' ORDER BY created DESC LIMIT 50")

    def approve(self,sid):
        rows=self.store.rows("SELECT fact FROM memory_suggestions WHERE id=? AND status='pending'",(sid,))
        if not rows:raise ValueError('Sugestão não encontrada.')
        fact=rows[0]['fact']
        memory=self.library.save(MemoryBody(title=fact[:60],content=fact,category='contexto',enabled=True))
        self.store.audit('memory_suggestion_approved',sid)
        self.store.write("UPDATE memory_suggestions SET status='approved' WHERE id=?",(sid,))
        return memory

    def dismiss(self,sid):self.store.write("UPDATE memory_suggestions SET status='dismissed' WHERE id=?",(sid,))
