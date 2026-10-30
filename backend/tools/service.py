"""Small typed tools with per-action approval. PowerShell commands always need an explicit approval card."""
import ast
import re
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
from backend.tools.research import read_page,search_web,download
from backend.memory.library import reject_secrets
from backend.security.policy import Policy
from backend.tools.windows_ui import WindowsUI,parse_keys,CLOSING
from backend.tools.app_catalog import AppCatalog,normalize
from backend.tools import appidentity
from backend.tools.outcome import outcome
from backend.security.guard import RememberedApprovals,Undo,SINKS,sensitive_reason
from backend.tools import system
from backend.tools.system import Reminders

# Tools whose results bring outside content into the conversation (checked for taint).
READERS={'read_text','read_webpage','web_search','windows_read','browser_read','list_files','find_files'}
import fnmatch
import threading

TEXT_EXTENSIONS={'.txt','.md','.json','.csv','.ts','.tsx','.js','.jsx','.py','.css','.html','.yaml','.yml','.sql','.toml'}
SENSITIVE={'.env','.ssh','.codex','.claude','.aws','.azure','.git','credentials','credentials.json','id_rsa','id_ed25519','appdata','ntuser.dat','ntuser.ini','secrets.txt','passwords.txt','senhas.txt'}

class ToolProposal(BaseModel):
    model_config=ConfigDict(extra='forbid')
    tool:Literal['calculate','list_files','find_files','read_text','write_text','open_folder','open_app','close_app','open_url','web_search','read_webpage','browser_open','browser_read','browser_back','browser_click','browser_type','windows_read','windows_invoke','windows_type','windows_keys','download_file','run_command','undo',
        'screen_look','system_volume','system_brightness','media_key','reminder_create','reminder_list','reminder_cancel','memory_recall','routine_create','routine_list']
    scope_id:str=Field(default='',max_length=64)
    path:str=Field(default='',max_length=500)
    content:str=Field(default='',max_length=30000)
    expression:str=Field(default='',max_length=200)
    # No default: a missing name used to open Notepad instead of what the user asked for.
    app:str=Field(default='',max_length=120,pattern=r'^[^\x00-\x1f]*$')
    command:str=Field(default='',max_length=4000)
    target:str=Field(default='',max_length=160)
    snapshot_id:str=Field(default='',max_length=64)
    window_id:str=Field(default='',max_length=64)
    keys:str=Field(default='',max_length=40)
    value:str=Field(default='',max_length=40)
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

SITES={'google':'google.com','youtube':'youtube.com','gmail':'mail.google.com','netflix':'netflix.com','twitch':'twitch.tv',
    'github':'github.com','instagram':'instagram.com','facebook':'facebook.com','twitter':'x.com','x':'x.com','reddit':'reddit.com',
    'linkedin':'linkedin.com','amazon':'amazon.com.br','mercado livre':'mercadolivre.com.br','chatgpt':'chatgpt.com','wikipedia':'pt.wikipedia.org'}

def site_for(name):
    """A program name that is really a website, or a bare domain: the URL to open instead."""
    key=normalize(name or '').removeprefix('o ').removeprefix('a ').strip()
    if key in SITES:return SITES[key]
    if re.fullmatch(r'[a-z0-9-]+(\.[a-z0-9-]+)+',(name or '').strip().lower()):return name.strip().lower()
    return None

BROWSERS=('chrome','edge','firefox','brave','opera','navegador')

def site_in_request(body,message):
    """open_app(chrome) for "abre o youtube" / "nova aba no google": the site the user named, as open_url."""
    if body.tool!='open_app' or not any(b in normalize(body.app or '') for b in BROWSERS):return body
    text=' '+re.sub(r'[^a-z0-9 ]',' ',normalize(message or ''))+' '
    site=next((url for key,url in SITES.items() if len(key)>1 and f' {key} ' in text),None)
    return ToolProposal(tool='open_url',url=site) if site else body

def normalize_url(url,query=''):
    """'google.com' -> https://google.com; only a query -> a Google search in the default browser."""
    url=url.strip()
    if not url and query.strip():return 'https://www.google.com/search?q='+urllib.parse.quote_plus(query.strip())
    if url.startswith('http://'):return 'https://'+url[7:]
    if url and '://' not in url:return 'https://'+url.lstrip('/')
    return url

class ToolService:
    def __init__(self,store,engine,data_dir,desktop=None):
        self.store,self.engine=store,engine
        self.policy=Policy(store);self.desktop=desktop;self.launched={};self.launch_lock=threading.RLock()
        self.gui=WindowsUI(store);self.catalog=AppCatalog()
        self.remembered=RememberedApprovals(store);self.undo=Undo(store);self.taint={}
        self.reminders=Reminders(store,data_dir);self.captures={};self.memory_search=lambda query:[];self.routines=None
        self.setters={'system_volume':system.set_volume_state,'system_brightness':system.set_brightness}
        self.level=1;self.pending={};self.previews={};self.critical_confirmed=set();self.auto_scopes=set()
        self.workspace=(data_dir/'workspace').resolve();self.workspace.mkdir(parents=True,exist_ok=True)
        self.file_history=data_dir/'file-history'
        store.db.executescript('''
          CREATE TABLE IF NOT EXISTS scopes(id TEXT PRIMARY KEY,path TEXT NOT NULL UNIQUE,created TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS actions(id TEXT PRIMARY KEY,tool TEXT NOT NULL,payload TEXT NOT NULL,status TEXT NOT NULL,result TEXT,created TEXT NOT NULL,updated TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS action_context(id TEXT PRIMARY KEY,conversation_id TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS action_reviews(id TEXT PRIMARY KEY,preview TEXT NOT NULL,fingerprint TEXT);
          CREATE TABLE IF NOT EXISTS tool_authorization(id INTEGER PRIMARY KEY CHECK(id=1),level INTEGER NOT NULL,scopes TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS programs(id TEXT PRIMARY KEY,name TEXT NOT NULL,path TEXT NOT NULL UNIQUE,sha256 TEXT NOT NULL);
        ''')
        store.db.commit()
        store.write("UPDATE actions SET status='interrupted' WHERE status='running' OR (status='proposed' AND id NOT IN (SELECT id FROM action_reviews))")
        recover=store.rows("SELECT a.id,a.payload,r.preview,r.fingerprint FROM actions a JOIN action_reviews r ON r.id=a.id WHERE a.status='proposed' ORDER BY a.created")
        for row in recover:
            payload=json.loads(row['payload'])
            # UI snapshots and launched process handles belong to the old session.
            if payload['tool'].startswith(('browser_','windows_')) or payload['tool']=='close_app':
                store.write("UPDATE actions SET status='interrupted' WHERE id=?",(row['id'],));continue
            self.pending[row['id']]=(None,payload,row['fingerprint'])
            self.previews[row['id']]=json.loads(row['preview'])
        self.add_scope(self.workspace,internal=True)
        saved=store.rows('SELECT level,scopes FROM tool_authorization WHERE id=1')
        if saved and saved[0]['level'] in (1,2,3,4):
            self.level=saved[0]['level']
            valid={s['id'] for s in store.rows('SELECT id FROM scopes')}
            self.auto_scopes=set(json.loads(saved[0]['scopes'])) & valid
            if self.level==4:self.auto_scopes.add('windows-profile');self.catalog.prewarm()

    def save_authorization(self):
        self.store.write('INSERT INTO tool_authorization VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET level=excluded.level,scopes=excluded.scopes',(self.level,json.dumps(sorted(self.auto_scopes))))

    def status(self):
        scopes=self.store.rows('SELECT * FROM scopes ORDER BY created')
        if self.level==4:scopes.append({'id':'windows-profile','path':str(Path.home()),'label':'Computador · acesso total (caminhos relativos ao seu perfil ou completos)'})
        return {'level':self.level,'expires_in':None,'persistent':True,'scopes':scopes,'auto_scopes':list(self.auto_scopes),'tools':list(ToolProposal.model_fields['tool'].annotation.__args__),'windows_scope':'Acesso total: internet, sites no seu navegador padrão, downloads, arquivos do computador, qualquer programa instalado e janelas abertas executam sem aprovação, salvo o que você bloquear. Comandos do PowerShell sempre mostram um cartão para você aprovar. Arquivos de credenciais e privilégios administrativos ficam excluídos; downloads nunca são executados.'}

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
        if level==4:self.auto_scopes.add('windows-profile');self.catalog.prewarm()
        self.save_authorization()
        self.store.audit('supervised_session_granted',json.dumps({'level':level,'scopes':sorted(self.auto_scopes),'persistent':True}))
        return self.status()

    def can_auto(self,body,conversation_id=''):
        level=self.status()['level']
        decision=self.policy.decision(body.tool)
        # Reading the owner's own memories and reminders is part of conversation, at any level.
        if body.tool in ('memory_recall','reminder_list','routine_list'):return decision!='deny'
        if level<2 or decision=='deny':return False
        # A command is free-form code: it always waits for the owner's approval card.
        if body.tool=='run_command':return False
        # After sensitive content was read here, anything that could carry it out waits for the card.
        if conversation_id in self.taint and body.tool in SINKS:return False
        if level in (2,3) and self.remembered.allows(body.tool,body.model_dump()):return True
        if level==2:return False
        if body.tool=='undo':return level==4
        # Full access: everything the owner did not block runs without review.
        # Closing a program the ALT did not open can lose unsaved work, so it is reviewed.
        if level==4:
            if body.tool=='windows_keys':return parse_keys(body.keys)[0].split('*')[0] not in CLOSING
            return body.tool!='close_app' or body.app in self.launched
        if body.tool in ('list_files','find_files','read_text','write_text','open_folder'):
            if body.scope_id not in self.auto_scopes:return False
            if body.tool=='write_text' and body.scope_id=='windows-profile':return False
        if body.tool=='close_app':return False
        if decision=='allow':return True
        return body.tool=='calculate' or body.tool in ('list_files','find_files','read_text') and body.scope_id in self.auto_scopes

    def programs(self):
        return [{'id':'notepad','name':'Bloco de Notas'},{'id':'calculator','name':'Calculadora'}]+self.store.rows('SELECT id,name,path FROM programs ORDER BY name')

    def resolve_app(self,name):
        """Registered id, a registered name, or (full access) any program installed in the Start Menu."""
        if not name.strip():raise ValueError('Diga qual aplicativo abrir.')
        programs=self.programs()
        if name in {p['id'] for p in programs}:return name
        wanted=normalize(name)
        builtin={'bloco de notas':'notepad','notepad':'notepad','calculadora':'calculator','calculator':'calculator','calc':'calculator'}
        match=next((p['id'] for p in programs if normalize(p['name'])==wanted),None) or builtin.get(wanted)
        if self.status()['level']==4 and match in (None,'notepad','calculator'):
            try:return 'catalog:'+self.catalog.resolve(name)['name']
            except ValueError:
                if not match:raise
        if match:return match
        raise ValueError('Ative o Acesso total para abrir qualquer programa pelo nome, ou registre este aplicativo em Controle e regras.')

    def catalog_entry(self,app):
        name=app.removeprefix('catalog:');entry=self.catalog.resolve(name)
        if entry['name']!=name:raise ValueError('O programa mudou desde a prévia. Peça novamente.')
        return entry

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
        if not entry:raise ValueError('Esta proposta foi encerrada ou pertence a uma sessão anterior. Prepare uma nova proposta para revisar.')
        if entry[0] is not None and entry[0]<time.monotonic():raise ValueError('Proposta expirada.')
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
            roots=[{'path':str(Path.home())}];absolute=PureWindowsPath(relative)
            if Path(relative).is_absolute() or absolute.drive:
                # Full access reaches any local drive; network shares stay out.
                if relative.startswith(('\\\\','//')) or absolute.drive.startswith('\\\\') or not Path(relative).is_absolute():raise ValueError('Use um caminho local completo, como C:\\Pasta\\arquivo.txt.')
                anchor=Path(relative).anchor;roots=[{'path':anchor}];relative=str(Path(relative).relative_to(anchor))
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

    def scope_name(self,sid,child):
        """Path as the scope expects it: relative, or complete outside the profile in full access."""
        root=Path.home() if sid=='windows-profile' else Path(self.store.rows('SELECT path FROM scopes WHERE id=?',(sid,))[0]['path'])
        try:return str(child.relative_to(root))
        except ValueError:
            if sid!='windows-profile':raise
            return str(child)

    def file_state(self,path):
        if not path.exists():return None
        if not path.is_file() or path.stat().st_size>120000:raise ValueError('Escolha um arquivo de texto de até 120 KB.')
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def proposal(self,body,conversation_id=''):
        if self.engine.stopped:raise PermissionError('Ações suspensas.')
        if len(self.pending)>=100:raise ValueError('Há 100 propostas pendentes. Recuse ou execute algumas antes de criar outras.')
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
        elif body.tool=='download_file':
            reject_secrets(body.url)
            parsed=urllib.parse.urlsplit(body.url)
            if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or any(c.isspace() for c in body.url):raise ValueError('Use uma URL HTTPS pública, sem credenciais.')
            if not body.scope_id:
                if self.status()['level']!=4:raise ValueError('Escolha a pasta de destino do download.')
                body.scope_id='windows-profile'
            name=PureWindowsPath(urllib.parse.unquote(parsed.path)).name or 'download'
            if not body.path:body.path=('Downloads/' if body.scope_id=='windows-profile' else '')+name
            elif body.path=='.' or body.path.endswith(('/','\\')):body.path=body.path.rstrip('/\\.')+'/'+name if body.path!='.' else name
            path=self.scoped(body.scope_id,body.path)
            if not path.parent.is_dir():raise ValueError('A pasta de destino precisa existir.')
            payload=body.model_dump()
            preview.update({'url':body.url,'path':str(path),'external_notice':'O arquivo será baixado da internet e salvo sem ser aberto ou executado.'})
        elif body.tool=='calculate':preview['expression']=body.expression;calculate(body.expression)
        elif body.tool in ('open_app','close_app'):
            try:body.app=self.resolve_app(body.app)
            except ValueError:
                # The small model sometimes picks open_app for a site ("abre o youtube"): open the site instead.
                site=site_for(body.app) if body.tool=='open_app' else None
                if not site:raise
                return self.proposal(ToolProposal(tool='open_url',url=site),conversation_id)
            payload=body.model_dump()
            preview['app']=body.app.removeprefix('catalog:')
            if body.tool=='close_app':
                tracked=body.app in self.launched
                preview['notice']=('Solicita fechamento normal da janela aberta pela ALT' if tracked else 'Solicita fechamento normal das janelas abertas deste programa')+'; o programa pode pedir para salvar documentos.'
        elif body.tool=='screen_look':
            preview['external_notice']='Captura da tela inteira; a imagem vai só para o modelo escolhido nesta conversa.'
        elif body.tool in ('system_volume','system_brightness','media_key'):
            preview['value']=body.value or ('playpause' if body.tool=='media_key' else '')
            if body.tool!='media_key' and not body.value:raise ValueError('Diga o valor, por exemplo 50, +10 ou mudo.')
        elif body.tool=='reminder_create':
            due=system.parse_when(body.value)
            if not body.content.strip():raise ValueError('Diga o texto do lembrete.')
            preview.update({'due':due.isoformat(),'text':body.content.strip()[:300]})
        elif body.tool=='reminder_cancel':preview['target']=body.target or body.content
        elif body.tool=='routine_create':
            from backend.proactive import parse_schedule
            parse_schedule(body.value)
            if not body.content.strip():raise ValueError('Diga o que a rotina deve fazer.')
            preview.update({'schedule':body.value,'text':body.content.strip()[:1000],'external_notice':'A rotina roda sozinha no horário e só responde com texto (sem executar ações).'})
        elif body.tool=='memory_recall':
            if not body.query.strip():raise ValueError('Diga o que procurar na memória.')
            preview['query']=body.query
        elif body.tool=='undo':
            target=body.target or self.undo.last()
            if not target or not self.undo.available(target):raise ValueError('Não há ação recente da ALT para desfazer.')
            body.target=target;payload=body.model_dump()
            row=self.store.rows('SELECT tool FROM actions WHERE id=?',(target,))
            preview.update({'undo_action':target,'undone_tool':row[0]['tool'] if row else ''})
        elif body.tool=='run_command':
            command=body.command.strip() or body.content.strip()
            if not command:raise ValueError('Informe o comando do PowerShell.')
            reject_secrets(command);body.command=command;body.content='';payload=body.model_dump()
            preview.update({'command':command,'external_notice':'Comando do PowerShell com os direitos do seu usuário Windows (sem administrador). Confira o comando inteiro antes de aprovar.'})
        elif body.tool.startswith('windows_'):
            grant=next((g for g in self.gui.grants() if g['id']==body.window_id),None)
            if not grant and self.status()['level']==4 and body.window_id:
                # Full access reaches any open window by title or program; exclusions in WindowsUI still apply.
                body.window_id=self.gui.find(body.window_id);payload=body.model_dump()
                grant=next((g for g in self.gui.grants() if g['id']==body.window_id),None)
            if not grant:raise PermissionError('Autorize uma janela no seletor nativo.')
            preview.update({'window_id':body.window_id,'window_title':grant['title']})
            if body.tool=='windows_keys':
                body.keys=parse_keys(body.keys)[0];payload=body.model_dump();preview['keys']=body.keys
                if body.keys.split('*')[0] in CLOSING:preview['notice']='Este atalho fecha a janela ou o programa; ele pode pedir para salvar.'
            elif body.tool!='windows_read':
                cached,index=self.gui.describe_target(body.window_id,body.snapshot_id,body.target)
                preview['element']=cached['public']['elements'][index]
                if body.tool=='windows_type':reject_secrets(body.content);preview['text']=body.content
                preview['external_notice']='Interagir com este aplicativo pode modificar dados. Confira janela, elemento e conteúdo.'
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
            body.url=normalize_url(body.url,body.query);payload=body.model_dump()
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
        # In full access the owner already accepted unattended writes.
        preview['critical']=body.tool=='write_text' and body.scope_id=='windows-profile' and self.status()['level']!=4
        if conversation_id in self.taint and body.tool in SINKS:preview['taint']=self.taint[conversation_id]+'; por isso esta ação espera sua aprovação.'
        aid=str(uuid4())
        # Critical cards (writing in the Windows profile) expire after 90 s, like Mark LVI's confirmations.
        self.pending[aid]=(time.monotonic()+90 if preview['critical'] else None,payload,fingerprint)
        self.previews[aid]=preview
        self.store.write('INSERT INTO actions VALUES(?,?,?,?,?,?,?)',(aid,body.tool,json.dumps(payload), 'proposed',None,now(),now()))
        self.store.write('INSERT INTO action_context VALUES(?,?)',(aid,conversation_id))
        self.store.write('INSERT INTO action_reviews VALUES(?,?,?)',(aid,json.dumps(preview,ensure_ascii=False),fingerprint))
        return {'id':aid,'preview':preview,'expires_in':90 if preview['critical'] else None,'requires_approval':True}

    def renew(self,aid):
        rows=self.store.rows('SELECT payload,status FROM actions WHERE id=?',(aid,))
        if not rows:raise ValueError('Proposta não encontrada.')
        if rows[0]['status'] not in ('proposed','interrupted','error'):raise ValueError('Esta ação já foi concluída, recusada ou cancelada.')
        if aid in self.pending:return {'id':aid,'preview':self.describe(aid),'expires_in':None,'requires_approval':True}
        contexts=self.store.rows('SELECT conversation_id FROM action_context WHERE id=?',(aid,))
        # Recreate only the proposal and show its fresh preview; never execute here.
        result=self.proposal(ToolProposal(**json.loads(rows[0]['payload'])),contexts[0]['conversation_id'] if contexts else '')
        self.store.write("UPDATE actions SET status='superseded' WHERE id=?",(aid,))
        return result

    async def approve(self,aid):
        pending=self.pending.get(aid)
        if self.status()['level']<2 and (not pending or pending[1]['tool'] not in ('memory_recall','reminder_list','routine_list')):raise PermissionError('Ative uma sessão autorizada para aprovar esta ação.')
        preview=self.describe(aid)
        self.policy.check(self.pending[aid][1]['tool'])
        if preview.get('critical') and aid not in self.critical_confirmed:raise PermissionError('Gravação ampla exige confirmação adicional na janela nativa.')
        entry=self.pending.pop(aid,None)
        if not entry or entry[0] is not None and entry[0]<time.monotonic():raise ValueError('Proposta expirada ou já utilizada.')
        event=self.engine.begin('tool:'+aid)
        self.store.write("UPDATE actions SET status='running',updated=? WHERE id=?",(now(),aid))
        try:
            result=await asyncio.to_thread(self.execute,ToolProposal(**entry[1]),entry[2],event)
            if isinstance(result,dict):
                if entry[1]['tool']=='screen_look':
                    self.captures[aid]=self.captures.pop('last',None)
                    while len(self.captures)>3:self.captures.pop(next(iter(self.captures)))
                if self.undo.record(aid,entry[1]['tool'],result):result['undo_available']=True
                contexts=self.store.rows('SELECT conversation_id FROM action_context WHERE id=?',(aid,))
                cid=contexts[0]['conversation_id'] if contexts else ''
                if cid and entry[1]['tool'] in READERS:
                    reason=sensitive_reason(json.dumps(result,ensure_ascii=False))
                    if reason:self.taint[cid]=reason;result['taint']=reason+'; a partir daqui, ações que enviam dados para fora pedem aprovação nesta conversa.'
            self.store.write("UPDATE actions SET status='complete',result=?,updated=? WHERE id=?",(json.dumps(result,ensure_ascii=False),now(),aid))
            self.store.audit('tool_complete',aid)
            return {'id':aid,'status':'complete','result':result}
        except Exception:
            self.store.write("UPDATE actions SET status='error',updated=? WHERE id=?",(now(),aid));raise
        finally:self.engine.active.pop('tool:'+aid,None);self.previews.pop(aid,None);self.critical_confirmed.discard(aid)

    def execute(self,body,fingerprint,event):
        """Every result carries a status (done/unverified/failed/ask); tools that cannot observe
        their effect say so instead of claiming success."""
        result=self.run(body,fingerprint,event)
        if isinstance(result,dict) and 'status' not in result:result={'status':'done',**result}
        return result

    def run(self,body,fingerprint,event):
        if event.is_set() or self.engine.stopped:raise PermissionError('Ação interrompida.')
        self.policy.check(body.tool)
        if body.tool.startswith('windows_'):
            if body.tool=='windows_keys':return self.gui.press(body.window_id,body.keys)
            return self.gui.read(body.window_id) if body.tool=='windows_read' else self.gui.act(body)
        if body.tool.startswith('browser_'):
            if not self.desktop:raise ValueError('Abra o aplicativo desktop.')
            return self.desktop.request(body.model_dump(),event)
        if body.tool=='calculate':return {'value':calculate(body.expression)}
        if body.tool=='web_search':return search_web(body.query)
        if body.tool=='read_webpage':return read_page(body.url)
        if body.tool=='download_file':return download(body.url,self.scoped(body.scope_id,body.path),event)
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
                            relative=self.scope_name(body.scope_id,child);self.scoped(body.scope_id,relative)
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
                        self.scoped(body.scope_id,self.scope_name(body.scope_id,p))
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
                    previous=None
                    if fingerprint:
                        # Keep the replaced version so unattended edits can be undone.
                        self.file_history.mkdir(parents=True,exist_ok=True)
                        previous=self.file_history/(time.strftime('%Y%m%d-%H%M%S')+'-'+str(uuid4())[:8]+'-'+path.name)
                        previous.write_bytes(path.read_bytes())
                    os.replace(temporary,path)
                finally:
                    if temporary.exists():temporary.unlink()
                return {'path':str(path),'bytes':path.stat().st_size,**({'previous_version':str(previous)} if previous else {})}
            if os.name!='nt':raise ValueError('Abertura de pastas disponível no Windows.')
            os.startfile(str(path));return {'open_requested':str(path)}
        if body.tool=='run_command':return self.run_command(body.command,event)
        if body.tool=='undo':return self.undo.run(body.target,self.undo_setters())
        if body.tool=='screen_look':
            image,size=system.capture_screen()
            # Kept in memory for the follow-up answer only; never written to the database.
            self.captures['last']=image
            return outcome('done',screen=list(size),notice='Tela capturada.')
        if body.tool=='system_volume':return system.change_volume(body.value)
        if body.tool=='system_brightness':return system.change_brightness(body.value)
        if body.tool=='media_key':return system.media_key(body.value)
        if body.tool=='reminder_create':return self.reminders.create(body.content,body.value)
        if body.tool=='reminder_list':return self.reminders.list()
        if body.tool=='routine_create':
            routine=self.routines.create(body.target or body.content[:60],body.value,body.content)
            return outcome('done',routine=routine['id'],next_run=routine['next_run'])
        if body.tool=='routine_list':return outcome('done',routines=[{'nome':r['name'],'agenda':r['schedule'],'proxima':r['next_run'],'ativa':r['enabled']} for r in self.routines.list()])
        if body.tool=='memory_recall':
            found=self.memory_search(body.query)[:5]
            return outcome('done' if found else 'unverified',memories=[{'title':m['title'],'content':m['content'][:600]} for m in found],notice='' if found else 'Nada salvo sobre isso.')
        if body.tool=='reminder_cancel':return self.reminders.cancel(body.target or body.content)
        if body.tool=='open_app':
            if os.name!='nt':raise ValueError('Aplicativos disponíveis no Windows.')
            if body.app.startswith('catalog:'):return self.open_catalog(self.catalog_entry(body.app))
            if body.app in ('notepad','calculator'):
                executable=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32'/('notepad.exe' if body.app=='notepad' else 'calc.exe')
            else:
                rows=self.store.rows('SELECT path,sha256 FROM programs WHERE id=?',(body.app,))
                if not rows:raise ValueError('Aplicativo não registrado.')
                executable=Path(rows[0]['path']);self.reject_links(executable)
                if self.executable_hash(executable)!=rows[0]['sha256']:raise ValueError('Executável alterado. Registre novamente pelo seletor nativo.')
            import psutil
            before={p.pid for p in psutil.process_iter()};windows_before={h for h,_,_ in appidentity.windows()}
            process=subprocess.Popen([str(executable)],creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                with self.launch_lock:self.launched[body.app]=(process.pid,psutil.Process(process.pid).create_time())
            except psutil.NoSuchProcess:pass
            # Calculator hands over to a Store process and exits, so a new window also counts as opened.
            deadline=time.monotonic()+8
            while time.monotonic()<deadline:
                if any(h not in windows_before and (pid==process.pid or pid not in before) for h,pid,_ in appidentity.windows()):
                    return outcome('done',launch_requested=body.app,pid=process.pid,window_seen=True)
                time.sleep(.25)
            alive=process.poll() is None
            return outcome('unverified' if alive else 'failed',launch_requested=body.app,pid=process.pid,notice='O programa foi iniciado, mas nenhuma janela nova apareceu.' if alive else 'O programa fechou logo depois de abrir.')
        if body.tool=='close_app':
            if body.app not in self.launched and self.status()['level']==4:return self.close_by_name(body.app.removeprefix('catalog:'))
            return self.close_launched(body.app)
        if body.tool=='open_url':
            opened=webbrowser.open(body.url)
            if not opened:raise ValueError('O sistema não confirmou a abertura do navegador.')
            return self.confirm_browser(body.url)
        raise ValueError('Ferramenta indisponível.')

    def undo_setters(self):
        """Inverse operations for system settings, filled in by the system tools."""
        return getattr(self,'setters',{})

    def open_catalog(self,entry):
        """Already running: bring its window forward instead of starting a second copy. Otherwise open
        it and watch for the new process (Mark LVI: at most 12 s, polled every 0.25 s)."""
        import psutil
        target=appidentity.link_target(entry['target']) if entry['kind']=='lnk' else ''
        exe=appidentity.stem_of(target)
        running=appidentity.matches(exe or entry['name'])
        if running and running[0]['score']>=60:
            hwnd,title=running[0]['windows'][0]
            return outcome('done',app=entry['name'],already_running=True,focused=appidentity.focus(hwnd),window=title[:80])
        before={p.pid for p in psutil.process_iter()}
        self.catalog.open(entry)
        if exe and exe not in ('explorer',):
            pid=appidentity.wait_for_new(before,lambda name:appidentity.stem_of(name)==exe)
        else:
            words=set(normalize(entry['name']).split())
            deadline=time.monotonic()+12;pid=None
            while pid is None and time.monotonic()<deadline:
                pid=next((p for _,p,title in appidentity.windows() if p not in before and words&set(normalize(title).split())),None)
                time.sleep(.25)
        if pid:return outcome('done',launch_requested=entry['name'],pid=pid)
        return outcome('unverified',launch_requested=entry['name'],notice='Pedido enviado ao Windows, mas o programa não apareceu em 12 s.')

    def confirm_browser(self,url):
        """The browser does not report back; the tab counts as opened when the default browser comes
        to the front within 3 s."""
        from backend.tools.app_catalog import default_browser
        exe={'Google Chrome':'chrome.exe','Microsoft Edge':'msedge.exe','Firefox':'firefox.exe','Brave':'brave.exe','Opera':'opera.exe','Vivaldi':'vivaldi.exe'}.get(default_browser() or '')
        if os.name!='nt' or not exe:return outcome('unverified',opened=url,notice='Pedido enviado ao navegador padrão; abertura não confirmada.')
        import ctypes
        user32=ctypes.WinDLL('user32');user32.GetForegroundWindow.restype=ctypes.c_void_p
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            front=user32.GetForegroundWindow()
            if front and any(h==front and appidentity.exe_name(pid).casefold()==exe for h,pid,_ in appidentity.windows()):return outcome('done',opened=url)
            time.sleep(.2)
        return outcome('unverified',opened=url,notice='Pedido enviado ao navegador padrão; ele não apareceu na frente em 3 s.')

    def run_command(self,command,event):
        if os.name!='nt':raise ValueError('Comandos disponíveis no Windows.')
        process=subprocess.Popen(['powershell.exe','-NoProfile','-NonInteractive','-Command','[Console]::OutputEncoding=[Text.Encoding]::UTF8;'+command],
            cwd=str(Path.home()),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
        chunks=[];reader=threading.Thread(target=lambda:chunks.append(process.stdout.read()),daemon=True);reader.start()
        deadline=time.monotonic()+60;stopped=None
        while process.poll() is None:
            if event.is_set() or self.engine.stopped:stopped='Interrompido pelo STOP.'
            elif time.monotonic()>deadline:stopped='Tempo limite de 60 s atingido.'
            if stopped:
                subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW);break
            time.sleep(.1)
        code=process.wait();reader.join(5)
        output=b''.join(chunks).decode('utf-8','replace')
        result=outcome('failed' if stopped or code else 'done',command=command,exit_code=code,output=output[-8000:],truncated=len(output)>8000)
        if stopped:result['stopped']=stopped
        return result

    def close_by_name(self,name):
        """Normal close (WM_CLOSE) of a program the ALT did not launch, ranked like Mark LVI. Two
        different programs tied on the best score is a question, not a guess; the ALT and Ollama are
        never targets; done only when the processes are gone."""
        if os.name!='nt':raise ValueError('Aplicativos disponíveis no Windows.')
        if not normalize(name):raise ValueError('Diga qual aplicativo fechar.')
        found=appidentity.matches(name)
        if not found:raise ValueError(f'Nenhuma janela aberta de "{name}" foi encontrada.')
        best=[group for group in found if group['score']==found[0]['score']]
        # Store apps show up twice: the app itself and the Windows frame host around it. One program.
        host=[g for g in best if g['stem'].casefold()=='applicationframehost'];others=[g for g in best if g not in host]
        if host and len(others)==1:others[0]['windows']+=host[0]['windows'];best=others
        if len(best)>1:return outcome('ask',options=[group['stem'] for group in best[:5]],notice='Mais de um programa corresponde ao nome; diga qual fechar.')
        group=best[0];sent=appidentity.post_close([h for h,_ in group['windows']])
        alive=appidentity.wait_closed(group['pids'])
        windows=[title for _,title in group['windows']][:10]
        if not alive:return outcome('done',close_requested=True,program=group['stem'],windows=windows)
        return outcome('unverified',close_requested=bool(sent),program=group['stem'],windows=windows,notice='Fechamento pedido; o programa continua aberto e pode estar perguntando se você quer salvar.')

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
        alive=appidentity.wait_closed({pid}) if sent else {pid}
        return outcome('done' if not alive else 'unverified',close_requested=bool(sent),windows=len(sent),notice='Fechado.' if not alive else 'Fechamento normal solicitado; o programa pode aguardar confirmação para salvar. Nenhum processo foi forçado.')

    def revoke(self):
        self.level=1;self.auto_scopes.clear();self.save_authorization();self.cancel_pending();self.taint.clear()

    def cancel_pending(self):
        self.pending.clear();self.previews.clear();self.critical_confirmed.clear()
        if self.desktop:self.desktop.snapshot=None
        self.gui.snapshots.clear()
        self.store.write("UPDATE actions SET status='cancelled' WHERE status='proposed'")
        for key,event in self.engine.active.items():
            if key.startswith('tool:'):event.set()

    def history(self):
        return self.store.rows('SELECT id,tool,status,result,created,updated FROM actions ORDER BY created DESC LIMIT 100')

    def artifact(self,aid):
        """A file the ALT itself wrote or downloaded, for "show in folder" or "export a copy".
        The path comes from the stored action, never from the renderer, and must still be a regular file."""
        rows=self.store.rows("SELECT tool,result FROM actions WHERE id=? AND status='complete'",(aid,))
        if not rows or rows[0]['tool'] not in ('write_text','download_file'):raise ValueError('Arquivo não disponível para esta ação.')
        try:result=json.loads(rows[0]['result'] or '{}')
        except ValueError:result={}
        if not isinstance(result,dict) or not result.get('path'):raise ValueError('Arquivo não disponível para esta ação.')
        path=Path(result['path'])
        if path.is_symlink() or not path.is_file():raise ValueError('O arquivo foi movido ou apagado desde a ação.')
        return {'path':str(path.resolve()),'name':path.name,'bytes':path.stat().st_size,'sha256':result.get('sha256')}

    def sources(self,aid):
        """HTTPS links a completed search or page read returned; a source link opens only if it is one of them."""
        rows=self.store.rows("SELECT tool,result FROM actions WHERE id=? AND status='complete'",(aid,))
        if not rows or rows[0]['tool'] not in ('web_search','read_webpage'):raise ValueError('Fontes não disponíveis para esta ação.')
        try:result=json.loads(rows[0]['result'] or '{}')
        except ValueError:result={}
        urls=[row.get('url') for row in result.get('results',[]) if isinstance(row,dict)] if rows[0]['tool']=='web_search' else [result.get('url')]
        return {'urls':[url for url in urls if isinstance(url,str) and url.startswith('https://')]}

    def conversation_actions(self,cid):
        rows=self.store.rows('SELECT a.* FROM actions a JOIN action_context c ON c.id=a.id WHERE c.conversation_id=? ORDER BY a.created DESC LIMIT 100',(cid,))
        rows.reverse()
        result=[]
        for row in rows:
            payload=json.loads(row['payload'])
            if row['status']=='superseded':continue
            preview=self.previews.get(row['id']) or {key:(str(value)[:200] if key=='content' else value) for key,value in payload.items() if key in ('tool','path','query','url','app','expression','value','keys','command','window_id','target','content') and value}
            state='proposed' if row['status']=='proposed' and row['id'] in self.pending else 'complete' if row['status']=='complete' else 'rejected' if row['status']=='rejected' else 'cancelled' if row['status']=='cancelled' else 'interrupted' if row['status'] in ('proposed','interrupted') else 'error'
            result.append({'id':row['id'],'preview':preview,'state':state,'result':json.loads(row['result']) if row['result'] else None})
        return result
