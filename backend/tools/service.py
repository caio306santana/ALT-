"""Small typed tools with per-action approval. No shell executor or arbitrary executable."""
import ast
import asyncio
import difflib
import hashlib
import json
import math
import os
import stat
import subprocess
import time
import urllib.parse
import webbrowser
from pathlib import Path, PureWindowsPath
from uuid import uuid4
from pydantic import BaseModel,Field,ConfigDict
from typing import Literal
from backend.memory.store import now

TEXT_EXTENSIONS={'.txt','.md','.json','.csv','.ts','.tsx','.js','.jsx','.py','.css','.html','.yaml','.yml','.sql','.toml'}
SENSITIVE={'.env','.ssh','.codex','.claude','.aws','.azure','.git','credentials','credentials.json','id_rsa','id_ed25519'}

class ToolProposal(BaseModel):
    model_config=ConfigDict(extra='forbid')
    tool:Literal['calculate','list_files','read_text','write_text','open_folder','open_app','open_url']
    scope_id:str=Field(default='',max_length=64)
    path:str=Field(default='',max_length=500)
    content:str=Field(default='',max_length=30000)
    expression:str=Field(default='',max_length=200)
    app:Literal['notepad','calculator']='notepad'
    url:str=Field(default='',max_length=2000)

def calculate(expression):
    try:tree=ast.parse(expression,mode='eval')
    except SyntaxError as exc:raise ValueError('Expressão inválida.') from exc
    def walk(node,depth=0):
        if depth>15:raise ValueError('Expressão muito complexa.')
        if isinstance(node,ast.Constant) and type(node.value) in (int,float):value=node.value
        elif isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.USub,ast.UAdd)):
            value=walk(node.operand,depth+1)*(-1 if isinstance(node.op,ast.USub) else 1)
        elif isinstance(node,ast.BinOp):
            a,b=walk(node.left,depth+1),walk(node.right,depth+1)
            if isinstance(node.op,ast.Add):value=a+b
            elif isinstance(node.op,ast.Sub):value=a-b
            elif isinstance(node.op,ast.Mult):value=a*b
            elif isinstance(node.op,ast.Div):value=a/b
            elif isinstance(node.op,ast.Mod):value=a%b
            elif isinstance(node.op,ast.Pow) and abs(b)<=10 and abs(a)<=1e6:value=a**b
            else:raise ValueError('Operação não permitida.')
        else:raise ValueError('Use apenas números e operações aritméticas.')
        if not isinstance(value,(int,float)) or not math.isfinite(value) or abs(value)>1e30:raise ValueError('Resultado fora do limite.')
        return value
    try:return walk(tree.body)
    except (SyntaxError,ZeroDivisionError,OverflowError) as exc:raise ValueError('Expressão inválida.') from exc

class ToolService:
    def __init__(self,store,engine,data_dir):
        self.store,self.engine=store,engine
        self.level=1;self.until=0;self.pending={}
        self.workspace=(data_dir/'workspace').resolve();self.workspace.mkdir(parents=True,exist_ok=True)
        store.db.executescript('''
          CREATE TABLE IF NOT EXISTS scopes(id TEXT PRIMARY KEY,path TEXT NOT NULL UNIQUE,created TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS actions(id TEXT PRIMARY KEY,tool TEXT NOT NULL,payload TEXT NOT NULL,status TEXT NOT NULL,result TEXT,created TEXT NOT NULL,updated TEXT NOT NULL);
        ''')
        store.db.commit()
        store.write("UPDATE actions SET status='interrupted' WHERE status IN ('proposed','running')")
        self.add_scope(self.workspace,internal=True)

    def status(self):
        if self.until<time.monotonic():self.level=1
        return {'level':self.level,'expires_in':max(0,int(self.until-time.monotonic())) if self.level==2 else 0,'scopes':self.store.rows('SELECT * FROM scopes ORDER BY created'),'tools':['calculate','list_files','read_text','write_text','open_folder','open_app','open_url']}

    def set_level(self,level):
        if level not in (1,2):raise ValueError('Níveis 3 e 4 ainda indisponíveis.')
        self.level=level;self.until=time.monotonic()+900 if level==2 else 0
        self.store.audit('permission_level',str(level))
        return self.status()

    def add_scope(self,path,internal=False):
        path=Path(path)
        if not path.is_absolute() or str(path).startswith(('\\\\','//')):raise ValueError('Escolha uma pasta local absoluta.')
        self.reject_links(path)
        root=path.resolve(strict=True)
        if not root.is_dir():raise ValueError('O escopo precisa ser uma pasta.')
        if not internal:
            if root==Path(root.anchor) or root==Path.home() or any(part.lower() in SENSITIVE or part.lower() in {'windows','program files','program files (x86)','appdata'} for part in root.parts):
                raise ValueError('Selecione uma pasta de projeto específica, fora de diretórios de sistema/credenciais.')
        sid=str(uuid4())
        self.store.write('INSERT OR IGNORE INTO scopes VALUES(?,?,?)',(sid,str(root),now()))
        return self.store.rows('SELECT * FROM scopes WHERE path=?',(str(root),))[0]

    def reject_links(self,path):
        for part in [path,*path.parents]:
            if part.exists() or part.is_symlink():
                info=part.lstat()
                if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:
                    raise ValueError('Links simbólicos e junctions não são permitidos no escopo de arquivos.')

    def scoped(self,sid,relative):
        roots=self.store.rows('SELECT path FROM scopes WHERE id=?',(sid,))
        if not roots:raise ValueError('Selecione uma pasta autorizada.')
        root=Path(roots[0]['path'])
        windows=PureWindowsPath(relative)
        if Path(relative).is_absolute() or windows.is_absolute() or windows.drive or ':' in relative or '\x00' in relative:
            raise ValueError('Informe um caminho relativo ao escopo.')
        parts=relative.replace('\\','/').split('/')
        devices={'con','prn','aux','nul',*[f'com{i}' for i in range(1,10)],*[f'lpt{i}' for i in range(1,10)]}
        if any(part=='..' or part.rstrip(' .')!=part or part.lower() in SENSITIVE or part.lower().startswith('.env') or part.lower().endswith(('.pem','.key','.pfx')) or part.split('.')[0].lower() in devices for part in parts):
            raise ValueError('Caminho sensível ou fora de escopo.')
        candidate=root.joinpath(*[p for p in parts if p and p!='.'])
        self.reject_links(candidate)
        resolved=candidate.resolve()
        if not resolved.is_relative_to(root.resolve()):raise ValueError('Caminho fora do escopo autorizado.')
        return resolved

    def file_state(self,path):
        if not path.exists():return None
        if not path.is_file() or path.stat().st_size>120000:raise ValueError('Escolha um arquivo de texto de até 120 KB.')
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def proposal(self,body):
        if self.engine.stopped:raise PermissionError('Ações suspensas.')
        payload=body.model_dump();preview={'tool':body.tool};fingerprint=None
        if body.tool in ('list_files','read_text','write_text','open_folder'):
            path=self.scoped(body.scope_id,body.path);preview['path']=str(path)
            if body.tool in ('read_text','write_text'):
                if path.suffix.lower() not in TEXT_EXTENSIONS:raise ValueError('Extensão não permitida para ferramentas de texto.')
                fingerprint=self.file_state(path)
                if body.tool=='read_text' and fingerprint is None:raise ValueError('Arquivo não encontrado.')
            if body.tool=='write_text':
                if not path.parent.is_dir():raise ValueError('A pasta de destino precisa existir.')
                before=path.read_text(encoding='utf-8') if fingerprint else ''
                preview['diff']=''.join(difflib.unified_diff(before.splitlines(True),body.content.splitlines(True),fromfile='antes',tofile='depois'))[:40000]
                preview['creates_file']=fingerprint is None
            if body.tool in ('list_files','open_folder') and not path.is_dir():raise ValueError('Pasta não encontrada.')
        elif body.tool=='calculate':preview['expression']=body.expression;calculate(body.expression)
        elif body.tool=='open_app':preview['app']=body.app
        elif body.tool=='open_url':
            url=urllib.parse.urlsplit(body.url)
            if url.scheme!='https' or not url.hostname or url.username or url.password or any(c.isspace() for c in body.url):raise ValueError('Use uma URL HTTPS válida, sem credenciais.')
            preview['url']=body.url
        aid=str(uuid4())
        self.pending[aid]=(time.monotonic()+300,payload,fingerprint)
        if len(self.pending)>100:self.pending.pop(next(iter(self.pending)))
        self.store.write('INSERT INTO actions VALUES(?,?,?,?,?,?,?)',(aid,body.tool,json.dumps(payload), 'proposed',None,now(),now()))
        return {'id':aid,'preview':preview,'expires_in':300,'requires_approval':True}

    async def approve(self,aid):
        if self.status()['level']!=2:raise PermissionError('Ative o modo assistido para aprovar esta ação.')
        entry=self.pending.pop(aid,None)
        if not entry or entry[0]<time.monotonic():raise ValueError('Proposta expirada ou já utilizada.')
        event=self.engine.begin('tool:'+aid)
        self.store.write("UPDATE actions SET status='running',updated=? WHERE id=?",(now(),aid))
        try:
            result=await asyncio.to_thread(self.execute,ToolProposal(**entry[1]),entry[2],event)
            self.store.write("UPDATE actions SET status='complete',result=?,updated=? WHERE id=?",(json.dumps(result,ensure_ascii=False),now(),aid))
            self.store.audit('tool_complete',aid)
            return {'id':aid,'status':'complete','result':result}
        except Exception:
            self.store.write("UPDATE actions SET status='error',updated=? WHERE id=?",(now(),aid));raise
        finally:self.engine.active.pop('tool:'+aid,None)

    def execute(self,body,fingerprint,event):
        if event.is_set() or self.engine.stopped:raise PermissionError('Ação interrompida.')
        if body.tool=='calculate':return {'value':calculate(body.expression)}
        if body.tool in ('list_files','read_text','write_text','open_folder'):
            path=self.scoped(body.scope_id,body.path)
            if body.tool=='list_files':
                entries=[]
                for p in sorted(path.iterdir(),key=lambda p:p.name.lower()):
                    if len(entries)>=200:break
                    try:
                        self.scoped(body.scope_id,str(p.relative_to(Path(self.store.rows('SELECT path FROM scopes WHERE id=?',(body.scope_id,))[0]['path']))))
                        entries.append({'name':p.name,'directory':p.is_dir(),'bytes':p.stat().st_size if p.is_file() else None})
                    except (OSError,ValueError):continue
                return {'entries':entries,'limit':200}
            if body.tool in ('read_text','write_text'):
                if self.file_state(path)!=fingerprint:raise ValueError('O arquivo mudou desde a prévia. Crie uma nova proposta.')
                if body.tool=='read_text':return {'content':path.read_text(encoding='utf-8')}
                # Exclusive staging, then atomic replacement. Revalidate before commit.
                temporary=path.with_name('.alt-write-'+str(uuid4())+'.tmp')
                try:
                    with temporary.open('x',encoding='utf-8',newline='') as handle:handle.write(body.content)
                    self.scoped(body.scope_id,body.path)
                    if event.is_set() or self.engine.stopped:raise PermissionError('Gravação cancelada antes da substituição.')
                    if self.file_state(path)!=fingerprint:raise ValueError('Arquivo alterado durante a gravação. Operação cancelada.')
                    os.replace(temporary,path)
                finally:
                    if temporary.exists():temporary.unlink()
                return {'path':str(path),'bytes':path.stat().st_size}
            if os.name!='nt':raise ValueError('Abertura de pastas disponível no Windows.')
            os.startfile(str(path));return {'opened':str(path)}
        if body.tool=='open_app':
            if os.name!='nt':raise ValueError('Aplicativos disponíveis no Windows.')
            executable=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32'/('notepad.exe' if body.app=='notepad' else 'calc.exe')
            subprocess.Popen([str(executable)],creationflags=subprocess.CREATE_NO_WINDOW)
            return {'opened':body.app}
        if body.tool=='open_url':
            opened=webbrowser.open(body.url)
            if not opened:raise ValueError('O sistema não confirmou a abertura do navegador.')
            return {'opened':body.url}
        raise ValueError('Ferramenta indisponível.')

    def revoke(self):
        self.level=1;self.until=0;self.pending.clear()
        self.store.write("UPDATE actions SET status='cancelled' WHERE status='proposed'")
        for key,event in self.engine.active.items():
            if key.startswith('tool:'):event.set()

    def history(self):
        return self.store.rows('SELECT id,tool,status,result,created,updated FROM actions ORDER BY created DESC LIMIT 100')
