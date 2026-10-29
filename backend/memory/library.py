import json
import re
from uuid import uuid4
from pydantic import BaseModel,Field,ConfigDict
from typing import Literal
from backend.memory.store import now

class MemoryBody(BaseModel):
    model_config=ConfigDict(extra='forbid')
    title:str=Field(min_length=1,max_length=120)
    content:str=Field(min_length=1,max_length=6000)
    category:Literal['preferência','projeto','decisão','contexto']='preferência'
    enabled:bool=True

def reject_secrets(text):
    patterns=[r'\bsk-[\w-]{16,}',r'\bgh[pousr]_[\w]{20,}',r'-----BEGIN [A-Z ]*PRIVATE KEY-----',r'(?i)\b(senha|password|api[_ -]?key|token secreto)\s*[:=]\s*\S+']
    if any(re.search(p,text) for p in patterns):
        raise ValueError('Possível credencial detectada. Remova segredos antes de salvar como memória.')

class MemoryLibrary:
    def __init__(self,store):
        self.store=store
        store.db.executescript('''CREATE TABLE IF NOT EXISTS memories(id TEXT PRIMARY KEY,title TEXT NOT NULL,content TEXT NOT NULL,category TEXT NOT NULL,enabled INTEGER NOT NULL,created TEXT NOT NULL,updated TEXT NOT NULL);''')
        store.db.commit()

    def list(self,query=''):
        query=query.strip()[:200]
        rows=self.store.rows('SELECT * FROM memories WHERE title LIKE ? OR content LIKE ? ORDER BY updated DESC LIMIT 300',('%'+query+'%','%'+query+'%'))
        for row in rows:row['enabled']=bool(row['enabled'])
        return rows

    def save(self,body,mid=None):
        reject_secrets(body.title+'\n'+body.content)
        if not body.title.strip() or not body.content.strip():raise ValueError('Título e conteúdo precisam de texto.')
        if mid:
            if not self.store.rows('SELECT id FROM memories WHERE id=?',(mid,)):raise KeyError(mid)
            self.store.write('UPDATE memories SET title=?,content=?,category=?,enabled=?,updated=? WHERE id=?',(body.title,body.content,body.category,int(body.enabled),now(),mid))
        else:
            if self.store.rows('SELECT COUNT(*) AS count FROM memories')[0]['count']>=300:raise ValueError('Limite de 300 memórias. Exporte e revise as existentes antes de adicionar outras.')
            mid=str(uuid4());self.store.write('INSERT INTO memories VALUES(?,?,?,?,?,?,?)',(mid,body.title,body.content,body.category,int(body.enabled),now(),now()))
        self.store.audit('memory_saved',mid)
        return next(row for row in self.list() if row['id']==mid)

    def selected(self,ids):
        if len(ids)>10 or len(set(ids))!=len(ids):raise ValueError('Selecione até 10 memórias diferentes.')
        result=[];size=0
        for mid in ids:
            rows=self.store.rows('SELECT id,title,content,category FROM memories WHERE id=? AND enabled=1',(mid,))
            if not rows:raise ValueError('Uma memória selecionada não existe ou está desativada.')
            size+=len(rows[0]['content'])
            if size>8000:raise ValueError('As memórias selecionadas excedem 8.000 caracteres. Reduza a seleção.')
            result.append(rows[0])
        return result

    def export(self):return {'format':'alt-ai-memory','version':1,'exported_at':now(),'memories':self.list()}

    def delete(self,mid):
        self.store.write('DELETE FROM memories WHERE id=?',(mid,));self.store.audit('memory_deleted',mid)
