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
from backend.tools.research import read_page,search_web
from backend.memory.library import reject_secrets
from backend.security.policy import Policy
import fnmatch
import threading

TEXT_EXTENSIONS={'.txt','.md','.json','.csv','.ts','.tsx','.js','.jsx','.py','.css','.html','.yaml','.yml','.sql','.toml'}
SENSITIVE={'.env','.ssh','.codex','.claude','.aws','.azure','.git','credentials','credentials.json','id_rsa','id_ed25519','appdata','ntuser.dat','ntuser.ini','secrets.txt','passwords.txt','senhas.txt'}

class ToolProposal(BaseModel):
    model_config=ConfigDict(extra='forbid')
    tool:Literal['calculate','list_files','find_files','read_text','write_text','open_folder','open_app','close_app','open_url','web_search','read_webpage','browser_open','browser_read','browser_back','browser_click','browser_type']
    scope_id:str=Field(default='',max_length=64)
    path:str=Field(default='',max_length=500)
    content:str=Field(default='',max_length=30000)
    expression:str=Field(default='',max_length=200)
    app:str=Field(default='notepad',pattern=r'^[a-zA-Z0-9-]{1,64}$')
    target:str=Field(default='',max_length=160)
    snapshot_id:str=Field(default='',max_length=64)
    url:str=Field(default='',max_length=2000)
    query:str=Field(default='',max_length=300)

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
    def __init__(self,store,engine,data_dir,desktop=None):
        self.store,self.engine=store,engine
        self.policy=Policy(store);self.desktop=desktop;self.launched={};self.launch_lock=threading.RLock()
        self.level=1;self.pending={};self.previews={};self.critical_confirmed=set();self.auto_scopes=set()
        self.workspace=(data_dir/'workspace').resolve();self.workspace.mkdir(parents=True,exist_ok=True)
        store.db.executescript('''
          CREATE TABLE IF NOT EXISTS scopes(id TEXT PRIMARY KEY,path TEXT NOT NULL UNIQUE,created TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS actions(id TEXT PRIMARY KEY,tool TEXT NOT NULL,payload TEXT NOT NULL,status TEXT NOT NULL,result TEXT,created TEXT NOT NULL,updated TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS action_context(id TEXT PRIMARY KEY,conversation_id TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS tool_authorization(id INTEGER PRIMARY KEY CHECK(id=1),level INTEGER NOT NULL,scopes TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS programs(id TEXT PRIMARY KEY,name TEXT NOT NULL,path TEXT NOT NULL UNIQUE,sha256 TEXT NOT NULL);
        ''')
        store.db.commit()
        store.write("UPDATE actions SET status='interrupted' WHERE status IN ('proposed','running')")
        self.add_scope(self.workspace,internal=True)
        saved=store.rows('SELECT level,scopes FROM tool_authorization WHERE id=1')
        if saved and saved[0]['level'] in (1,2,3,4):
            self.level=saved[0]['level']
            valid={s['id'] for s in store.rows('SELECT id FROM scopes')}
            self.auto_scopes=set(json.loads(saved[0]['scopes'])) & valid
            if self.level==4:self.auto_scopes.add('windows-profile')

    def save_authorization(self):
        self.store.write('INSERT INTO tool_authorization VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET level=excluded.level,scopes=excluded.scopes',(self.level,json.dumps(sorted(self.auto_scopes))))

    def status(self):
        scopes=self.store.rows('SELECT * FROM scopes ORDER BY created')
        if self.level==4:scopes.append({'id':'windows-profile','path':str(Path.home()),'label':'Perfil pessoal Windows · sessão supervisionada'})
        return {'level':self.level,'expires_in':None,'persistent':True,'scopes':scopes,'auto_scopes':list(self.auto_scopes),'tools':list(ToolProposal.model_fields['tool'].annotation.__args__),'windows_scope':'Perfil pessoal e pastas escolhidas; credenciais, AppData, sistema, shell e privilégios administrativos excluídos.'}

    def set_level(self,level):
        if level not in (1,2):raise ValueError('Níveis 3 e 4 ainda indisponíveis.')
        if level>1 and self.engine.stopped:raise PermissionError('Retome as ações antes de conceder permissões.')
        if level==1 or self.level>=3:self.revoke()
        self.level=level;self.auto_scopes.clear();self.save_authorization()
        self.store.audit('permission_level',str(level))
        return self.status()

    def grant(self,level,scope_ids):
        if level not in (3,4):raise ValueError('Modo inválido.')
        if self.engine.stopped:raise PermissionError('Retome as ações antes de conceder permissões.')
        valid={s['id'] for s in self.store.rows('SELECT id FROM scopes')}
        if any(sid not in valid for sid in scope_ids):raise ValueError('Escopo não encontrado.')
        self.revoke();self.level=level;self.auto_scopes=set(scope_ids)
        if level==4:self.auto_scopes.add('windows-profile')
        self.save_authorization()
        self.store.audit('supervised_session_granted',json.dumps({'level':level,'scopes':sorted(self.auto_scopes),'persistent':True}))
        return self.status()

    def can_auto(self,body):
        level=self.status()['level']
        decision=self.policy.decision(body.tool)
        if level not in (3,4) or decision=='deny':return False
        if body.tool in ('list_files','find_files','read_text','write_text','open_folder'):
            if body.scope_id not in self.auto_scopes:return False
            if body.tool=='write_text' and body.scope_id=='windows-profile':return False
        if body.tool=='close_app':return False
        if decision=='allow':return True
        return body.tool=='calculate' or body.tool in ('list_files','find_files','read_text') and body.scope_id in self.auto_scopes

    def programs(self):
        return [{'id':'notepad','name':'Bloco de Notas'},{'id':'calculator','name':'Calculadora'}]+self.store.rows('SELECT id,name,path FROM programs ORDER BY name')

    def add_program(self,path):
        candidate=Path(path)
        if not candidate.is_absolute() or str(candidate).startswith(('\\\\','//')) or candidate.suffix.lower()!='.exe':raise ValueError('Escolha um executável .exe local.')
        self.reject_links(candidate)
        if not candidate.is_file():raise ValueError('Executável não encontrado.')
        if len(self.store.rows('SELECT id FROM programs'))>=20 and not self.store.rows('SELECT id FROM programs WHERE path=?',(str(candidate.resolve()),)):raise ValueError('Limite de 20 aplicativos registrados.')
        digest=self.executable_hash(candidate)
        self.store.write('INSERT INTO programs VALUES(?,?,?,?) ON CONFLICT(path) DO UPDATE SET sha256=excluded.sha256',(str(uuid4()),candidate.stem,str(candidate.resolve()),digest))
        self.store.audit('program_registered',candidate.name)
        return self.programs()

    def executable_hash(self,path):
        digest=hashlib.sha256()
        with path.open('rb') as handle:
            for chunk in iter(lambda:handle.read(1024*1024),b''):digest.update(chunk)
        return digest.hexdigest()

    def describe(self,aid):
        entry=self.pending.get(aid)
        if not entry or entry[0]<time.monotonic():raise ValueError('Proposta expirada.')
        return self.previews[aid]

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
        if sid=='windows-profile':
            if self.status()['level']!=4:raise PermissionError('A autorização ampla do Windows foi revogada ou alterada.')
            roots=[{'path':str(Path.home())}]
            if Path(relative).is_absolute():
                try:relative=str(Path(relative).relative_to(Path.home()))
                except ValueError:raise ValueError('O controle amplo cobre o perfil pessoal. Escolha outra pasta explicitamente para acessar fora dele.')
        else:roots=self.store.rows('SELECT path FROM scopes WHERE id=?',(sid,))
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

    def proposal(self,body,conversation_id=''):
        if self.engine.stopped:raise PermissionError('Ações suspensas.')
        self.policy.check(body.tool)
        payload=body.model_dump();preview={'tool':body.tool};fingerprint=None
        if body.tool in ('list_files','find_files','read_text','write_text','open_folder'):
            path=self.scoped(body.scope_id,body.path);preview['path']=str(path)
            if body.tool in ('read_text','write_text'):
                if path.suffix.lower() not in TEXT_EXTENSIONS:raise ValueError('Extensão não permitida para ferramentas de texto.')
                fingerprint=self.file_state(path)
                if body.tool=='read_text' and fingerprint is None:raise ValueError('Arquivo não encontrado.')
            if body.tool=='write_text':
                reject_secrets(body.content)
                if not path.parent.is_dir():raise ValueError('A pasta de destino precisa existir.')
                before=path.read_text(encoding='utf-8') if fingerprint else ''
                preview['diff']=''.join(difflib.unified_diff(before.splitlines(True),body.content.splitlines(True),fromfile='antes',tofile='depois'))[:40000]
                preview['creates_file']=fingerprint is None
            if body.tool in ('list_files','find_files','open_folder') and not path.is_dir():raise ValueError('Pasta não encontrada.')
            if body.tool=='find_files':preview['query']=body.query
        elif body.tool=='calculate':preview['expression']=body.expression;calculate(body.expression)
        elif body.tool in ('open_app','close_app'):
            if body.app not in {p['id'] for p in self.programs()}:raise ValueError('Escolha um aplicativo registrado no painel Controle.')
            preview['app']=body.app
            if body.tool=='close_app':preview['notice']='Solicita fechamento normal somente de janelas abertas pela ALT; o programa pode pedir para salvar documentos.'
        elif body.tool.startswith('browser_'):
            if not self.desktop:raise ValueError('Navegador disponível somente no aplicativo desktop.')
            if body.tool=='browser_open':
                reject_secrets(body.url)
                parsed=urllib.parse.urlsplit(body.url)
                if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:raise ValueError('Use uma URL HTTPS pública.')
                preview['url']=body.url
            if body.tool in ('browser_click','browser_type'):
                if not body.target or not body.snapshot_id:raise ValueError('Leia a página primeiro e use o elemento e snapshot retornados.')
                snapshot=self.desktop.snapshot
                if not snapshot or snapshot.get('snapshot_id')!=body.snapshot_id:raise ValueError('Leia a página novamente; observação desatualizada.')
                element=next((e for e in snapshot['elements'] if e.get('id')==body.target),None)
                if not element:raise ValueError('Elemento não observado na página.')
                preview['element']=element
                reject_secrets(body.content)
                preview.update({'target':body.target,'snapshot_id':body.snapshot_id})
                if body.tool=='browser_type':preview['text']=body.content
                preview['external_notice']='Interação com site externo; clicar ou digitar pode enviar dados ao site.'
        elif body.tool=='open_url':
            reject_secrets(body.url)
            url=urllib.parse.urlsplit(body.url)
            if url.scheme!='https' or not url.hostname or url.username or url.password or any(c.isspace() for c in body.url):raise ValueError('Use uma URL HTTPS válida, sem credenciais.')
            preview['url']=body.url
        elif body.tool=='web_search':
            reject_secrets(body.query)
            if not body.query.strip():raise ValueError('Informe o assunto da pesquisa.')
            preview['query']=body.query;preview['external_notice']='Esta consulta será enviada a um mecanismo de pesquisa público.'
        elif body.tool=='read_webpage':
            reject_secrets(body.url)
            parsed=urllib.parse.urlsplit(body.url)
            if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:raise ValueError('Use uma URL HTTPS pública, sem credenciais.')
            preview['url']=body.url;preview['external_notice']='A página será consultada sem cookies ou sessões pessoais.'
        preview['critical']=body.tool=='write_text' and body.scope_id=='windows-profile'
        aid=str(uuid4())
        self.pending[aid]=(time.monotonic()+300,payload,fingerprint)
        self.previews[aid]=preview
        if len(self.pending)>100:self.pending.pop(next(iter(self.pending)))
        self.store.write('INSERT INTO actions VALUES(?,?,?,?,?,?,?)',(aid,body.tool,json.dumps(payload), 'proposed',None,now(),now()))
        self.store.write('INSERT INTO action_context VALUES(?,?)',(aid,conversation_id))
        return {'id':aid,'preview':preview,'expires_in':300,'requires_approval':True}

    async def approve(self,aid):
        if self.status()['level']<2:raise PermissionError('Ative uma sessão autorizada para aprovar esta ação.')
        preview=self.describe(aid)
        self.policy.check(self.pending[aid][1]['tool'])
        if preview.get('critical') and aid not in self.critical_confirmed:raise PermissionError('Gravação ampla exige confirmação adicional na janela nativa.')
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
        finally:self.engine.active.pop('tool:'+aid,None);self.previews.pop(aid,None);self.critical_confirmed.discard(aid)

    def execute(self,body,fingerprint,event):
        if event.is_set() or self.engine.stopped:raise PermissionError('Ação interrompida.')
        self.policy.check(body.tool)
        if body.tool.startswith('browser_'):
            if not self.desktop:raise ValueError('Abra o aplicativo desktop.')
            return self.desktop.request(body.model_dump(),event)
        if body.tool=='calculate':return {'value':calculate(body.expression)}
        if body.tool=='web_search':return search_web(body.query)
        if body.tool=='read_webpage':return read_page(body.url)
        if body.tool in ('list_files','find_files','read_text','write_text','open_folder'):
            path=self.scoped(body.scope_id,body.path)
            if body.tool=='find_files':
                entries=[];stack=[path];visited=0;deadline=time.monotonic()+5;cutoff=False
                while stack and visited<2000 and time.monotonic()<deadline and not event.is_set():
                    current=stack.pop();visited+=1
                    try:children=current.iterdir()
                    except OSError:continue
                    for child in children:
                        if event.is_set() or time.monotonic()>=deadline:cutoff=True;break
                        try:
                            root=Path.home() if body.scope_id=='windows-profile' else Path(self.store.rows('SELECT path FROM scopes WHERE id=?',(body.scope_id,))[0]['path'])
                            relative=str(child.relative_to(root));self.scoped(body.scope_id,relative)
                            if child.is_dir():stack.append(child)
                            if not body.query or body.query.casefold() in child.name.casefold() or fnmatch.fnmatch(child.name.casefold(),body.query.casefold()):
                                entries.append({'name':relative,'directory':child.is_dir()})
                                if len(entries)>=200:stack.clear();break
                        except (OSError,ValueError):continue
                return {'entries':entries,'directories_scanned':visited,'truncated':cutoff or bool(stack) or len(entries)>=200,'cancelled':event.is_set()}
            if body.tool=='list_files':
                entries=[]
                for p in sorted(path.iterdir(),key=lambda p:p.name.lower()):
                    if len(entries)>=200:break
                    try:
                        base=Path.home() if body.scope_id=='windows-profile' else Path(self.store.rows('SELECT path FROM scopes WHERE id=?',(body.scope_id,))[0]['path'])
                        self.scoped(body.scope_id,str(p.relative_to(base)))
                        entries.append({'name':p.name,'directory':p.is_dir(),'bytes':p.stat().st_size if p.is_file() else None})
                    except (OSError,ValueError):continue
                return {'entries':entries,'limit':200}
            if body.tool in ('read_text','write_text'):
                if self.file_state(path)!=fingerprint:raise ValueError('O arquivo mudou desde a prévia. Crie uma nova proposta.')
                if body.tool=='read_text':
                    content=path.read_text(encoding='utf-8');reject_secrets(content)
                    return {'content':content}
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
            os.startfile(str(path));return {'open_requested':str(path)}
        if body.tool=='open_app':
            if os.name!='nt':raise ValueError('Aplicativos disponíveis no Windows.')
            if body.app in ('notepad','calculator'):
                executable=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32'/('notepad.exe' if body.app=='notepad' else 'calc.exe')
            else:
                rows=self.store.rows('SELECT path,sha256 FROM programs WHERE id=?',(body.app,))
                if not rows:raise ValueError('Aplicativo não registrado.')
                executable=Path(rows[0]['path']);self.reject_links(executable)
                if self.executable_hash(executable)!=rows[0]['sha256']:raise ValueError('Executável alterado. Registre novamente pelo seletor nativo.')
            process=subprocess.Popen([str(executable)],creationflags=subprocess.CREATE_NO_WINDOW)
            import psutil
            try:
                with self.launch_lock:self.launched[body.app]=(process.pid,psutil.Process(process.pid).create_time())
            except psutil.NoSuchProcess:pass
            return {'launch_requested':body.app,'pid':process.pid}
        if body.tool=='close_app':
            return self.close_launched(body.app)
        if body.tool=='open_url':
            opened=webbrowser.open(body.url)
            if not opened:raise ValueError('O sistema não confirmou a abertura do navegador.')
            return {'opened':body.url}
        raise ValueError('Ferramenta indisponível.')

    def close_launched(self,app_id):
        if os.name!='nt':raise ValueError('Aplicativos disponíveis no Windows.')
        import ctypes
        from ctypes import wintypes
        import psutil
        with self.launch_lock:record=self.launched.get(app_id)
        if not record:raise ValueError('A ALT não possui uma janela rastreada deste aplicativo.')
        pid,created=record
        try:
            if psutil.Process(pid).create_time()!=created:raise ValueError('O processo original já foi encerrado.')
        except psutil.NoSuchProcess:raise ValueError('O processo original já foi encerrado.')
        user32=ctypes.WinDLL('user32',use_last_error=True);sent=[]
        callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
        user32.EnumWindows.argtypes=[callback_type,wintypes.LPARAM]
        user32.IsWindowVisible.argtypes=[wintypes.HWND]
        user32.IsWindowVisible.restype=wintypes.BOOL
        user32.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
        user32.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
        @callback_type
        def visit(hwnd,_):
            owner=wintypes.DWORD();user32.GetWindowThreadProcessId(hwnd,ctypes.byref(owner))
            if owner.value==pid and user32.IsWindowVisible(hwnd):
                if user32.PostMessageW(hwnd,0x0010,0,0):sent.append(int(hwnd))
            return True
        user32.EnumWindows(visit,0)
        return {'close_requested':bool(sent),'windows':len(sent),'notice':'Fechamento normal solicitado; o programa pode aguardar confirmação para salvar. Nenhum processo foi forçado.'}

    def revoke(self):
        self.level=1;self.auto_scopes.clear();self.save_authorization();self.cancel_pending()

    def cancel_pending(self):
        self.pending.clear();self.previews.clear();self.critical_confirmed.clear()
        if self.desktop:self.desktop.snapshot=None
        self.store.write("UPDATE actions SET status='cancelled' WHERE status='proposed'")
        for key,event in self.engine.active.items():
            if key.startswith('tool:'):event.set()

    def history(self):
        return self.store.rows('SELECT id,tool,status,result,created,updated FROM actions ORDER BY created DESC LIMIT 100')

    def conversation_actions(self,cid):
        rows=self.store.rows('SELECT a.* FROM actions a JOIN action_context c ON c.id=a.id WHERE c.conversation_id=? ORDER BY a.created DESC LIMIT 100',(cid,))
        rows.reverse()
        result=[]
        for row in rows:
            payload=json.loads(row['payload'])
            preview=self.previews.get(row['id']) or {key:value for key,value in payload.items() if key in ('tool','path','query','url','app','expression') and value}
            result.append({'id':row['id'],'preview':preview,'state':'proposed' if row['status']=='proposed' else 'complete' if row['status']=='complete' else 'rejected' if row['status']=='rejected' else 'error','result':json.loads(row['result']) if row['result'] else None})
        return result
