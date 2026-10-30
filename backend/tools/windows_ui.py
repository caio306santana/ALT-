"""Windows UI Automation with owner-selected window grants and stale-node checks."""
import hashlib
import os
import re
import threading
from uuid import uuid4
import psutil

EXCLUDED={'cmd.exe','powershell.exe','pwsh.exe','windowsterminal.exe','conhost.exe','consent.exe','logonui.exe','winlogon.exe','sechealthui.exe','securityhealthsystray.exe','systemsettings.exe','keepass.exe','keepassxc.exe','1password.exe','bitwarden.exe','alt-ai.exe','alt-backend.exe'}
SECRET=re.compile(r'password|senha|one.?time|credit.?card|cvv|captcha|secret|api.?key|token',re.I)
MODIFIERS={'ctrl':'^','control':'^','shift':'+','alt':'%'}
NAMED_KEYS={'enter':'{ENTER}','esc':'{ESC}','escape':'{ESC}','tab':'{TAB}','space':'{SPACE}','backspace':'{BACKSPACE}',
    'delete':'{DELETE}','del':'{DELETE}','home':'{HOME}','end':'{END}','pageup':'{PGUP}','pagedown':'{PGDN}',
    'up':'{UP}','down':'{DOWN}','left':'{LEFT}','right':'{RIGHT}','volumeup':'{VK_VOLUME_UP}','volumedown':'{VK_VOLUME_DOWN}',
    'mute':'{VK_VOLUME_MUTE}','playpause':'{VK_MEDIA_PLAY_PAUSE}','nexttrack':'{VK_MEDIA_NEXT_TRACK}','prevtrack':'{VK_MEDIA_PREV_TRACK}',
    **{f'f{i}':f'{{F{i}}}' for i in range(1,13)}}
# Combinations that close windows or apps go through the approval card, like close_app.
CLOSING={'alt+f4','ctrl+q','ctrl+shift+w','ctrl+shift+q'}

def parse_keys(text):
    """'ctrl+shift+t' or 'pagedown*3' -> (canonical form, pywinauto sequence). The Windows key is never
    sent: Win+R and similar open a prompt that would bypass the approval card for commands."""
    combo,_,repeat=text.strip().lower().replace(' ','').partition('*')
    count=int(repeat) if repeat.isdigit() else 0 if repeat else 1
    *mods,key=combo.split('+')
    mods=['ctrl' if m=='control' else m for m in mods]
    if not key or not 1<=count<=20 or len(mods)>3:raise ValueError('Atalho inválido. Use, por exemplo, ctrl+t, alt+left ou pagedown*3.')
    if any(m not in MODIFIERS for m in mods) or len(set(mods))!=len(mods):raise ValueError('Use só ctrl, shift e alt como modificadores; a tecla Windows não é enviada.')
    if key in NAMED_KEYS:sent=NAMED_KEYS[key]
    elif re.fullmatch(r'[a-z0-9]',key):sent=key
    else:raise ValueError(f'Tecla "{key}" não reconhecida.')
    mods=sorted(mods,key=['ctrl','shift','alt'].index)
    canonical='+'.join([*mods,key])
    return canonical+(f'*{count}' if count>1 else ''),(''.join(MODIFIERS[m] for m in mods)+sent)*count

class WindowsUI:
    def __init__(self,store):
        self.store=store;self.candidates={};self.snapshots={};self.lock=threading.RLock()
        store.db.execute('CREATE TABLE IF NOT EXISTS windows_grants(id TEXT PRIMARY KEY,handle INTEGER NOT NULL,pid INTEGER NOT NULL,created REAL NOT NULL,title TEXT NOT NULL,exe TEXT NOT NULL)');store.db.commit()

    def desktop(self):
        if os.name!='nt':raise ValueError('Controle de janelas disponível no Windows.')
        import comtypes
        # Worker threads need COM; a thread pywinauto already initialized in
        # another apartment mode reports RPC_E_CHANGED_MODE and is usable as is.
        try:comtypes.CoInitializeEx(0)
        except OSError:pass
        from pywinauto import Desktop
        return Desktop(backend='uia')

    def identity(self,window):
        pid=window.element_info.process_id;process=psutil.Process(pid);exe=process.exe()
        if os.path.basename(exe).casefold() in EXCLUDED:raise ValueError('Janela de terminal, segurança, credenciais ou da própria ALT não é automatizada.')
        parent=int(os.environ.get('ALT_PARENT_PID','0'))
        if pid==parent or parent and any(p.pid==parent for p in process.parents()):raise ValueError('A janela da própria ALT não pode ser controlada.')
        title=window.window_text()[:180]
        if re.search(r'controle de conta|user account control|windows security|segurança do windows|gerenciador de credenciais',title,re.I):raise ValueError('Janela protegida; use controle manual.')
        return {'handle':int(window.handle),'pid':pid,'created':process.create_time(),'title':title,'exe':exe}

    def inventory(self):
        result=[];desktop=self.desktop();self.candidates={}
        for window in desktop.windows(visible_only=True):
            try:
                row=self.identity(window)
                if not row['title']:continue
                key=hashlib.sha256(f"{row['handle']}:{row['pid']}:{row['created']}".encode()).hexdigest()[:32]
                self.candidates[key]=row;result.append({'candidate_id':key,**row})
                if len(result)>=100:break
            except (Exception,):continue
        return result

    def candidate(self,key):
        row=self.candidates.get(key)
        if not row:raise ValueError('Atualize a lista de janelas.')
        window=self.desktop().window(handle=row['handle']).wrapper_object()
        identity=self.identity(window)
        if identity['pid']!=row['pid'] or identity['created']!=row['created']:raise ValueError('A janela foi substituída.')
        return identity

    def find(self,name):
        """Full access: grant the open window whose title or program best matches the name the model used."""
        from backend.tools.app_catalog import normalize
        words=set(normalize(name).split())
        if not words:raise ValueError('Diga qual janela usar.')
        best=None
        for row in self.inventory():
            title=set(normalize(row['title']).split());program=normalize(os.path.basename(row['exe']).removesuffix('.exe'))
            score=2 if words<=title else 1 if program in words or words&title else 0
            if score and (not best or score>best[0]):best=(score,row['candidate_id'])
        if not best:raise ValueError(f'Nenhuma janela aberta corresponde a "{name}". Abra o programa primeiro.')
        return self.grant(best[1],evict=True)

    def grant(self,key,evict=False):
        row=self.candidate(key);gid=str(uuid4())
        old=self.store.rows('SELECT id FROM windows_grants WHERE handle=? AND pid=? AND created=?',(row['handle'],row['pid'],row['created']))
        if old:return old[0]['id']
        if evict:self.store.write('DELETE FROM windows_grants WHERE rowid IN (SELECT rowid FROM windows_grants ORDER BY rowid DESC LIMIT -1 OFFSET 29)')
        if len(self.store.rows('SELECT id FROM windows_grants'))>=30:raise ValueError('Remova uma autorização antiga antes de conceder outra.')
        self.store.write('INSERT INTO windows_grants VALUES(?,?,?,?,?,?)',(gid,row['handle'],row['pid'],row['created'],row['title'],row['exe']))
        self.store.audit('window_granted',gid);return gid

    def grants(self):return self.store.rows('SELECT * FROM windows_grants ORDER BY rowid DESC')
    def revoke(self,gid):
        self.store.write('DELETE FROM windows_grants WHERE id=?',(gid,));self.snapshots.pop(gid,None)
    def window(self,gid):
        rows=self.store.rows('SELECT * FROM windows_grants WHERE id=?',(gid,))
        if not rows:raise PermissionError('Autorize esta janela no seletor nativo primeiro.')
        row=rows[0];window=self.desktop().window(handle=row['handle']).wrapper_object();identity=self.identity(window)
        if identity['pid']!=row['pid'] or identity['created']!=row['created'] or identity['exe'].casefold()!=row['exe'].casefold():raise PermissionError('A janela original foi fechada ou substituída. Autorize a janela atual.')
        return window

    @staticmethod
    def signature(control):
        info=control.element_info
        return {'runtime_id':list(info.runtime_id or []),'name':info.name[:180],'automation_id':info.automation_id,'control_type':info.control_type}

    def read(self,gid):
        with self.lock:
            window=self.window(gid);elements=[];nodes=[]
            for control in window.descendants(depth=5):
                try:
                    if not control.is_visible():continue
                    info=control.element_info;sig=self.signature(control)
                    protected=bool(info._element.CurrentIsPassword) or bool(SECRET.search(sig['name']+' '+sig['automation_id']))
                    if protected:continue
                    if not sig['name'] and sig['control_type'] not in ('Edit','Document','ComboBox'):continue
                    value=''
                    if sig['control_type'] in ('Edit','Document'):
                        try:value=str(control.iface_value.CurrentValue)[:3000]
                        except Exception:pass
                    eid='w'+str(len(elements));elements.append({'id':eid,'label':sig['name'],'type':sig['control_type'],'value':value,'enabled':control.is_enabled()})
                    nodes.append(sig)
                    if len(elements)>=160:break
                except Exception:continue
            snapshot={'snapshot_id':str(uuid4()),'window_id':gid,'title':window.window_text(),'elements':elements,'truncated':len(elements)>=160}
            self.snapshots[gid]={'public':snapshot,'nodes':nodes}
            return snapshot

    def press(self,gid,keys):
        """Bring the granted window to the front, confirm it really is in front, then send the keys."""
        _,sequence=parse_keys(keys)
        with self.lock:
            window=self.window(gid)
            import ctypes
            from pywinauto.keyboard import send_keys
            from backend.tools.appidentity import focus
            # AttachThreadInput gets past Windows refusing focus to a background process.
            if not focus(int(window.handle)):
                try:window.set_focus()
                except Exception:pass
            user32=ctypes.WinDLL('user32',use_last_error=True)
            user32.GetForegroundWindow.restype=ctypes.c_void_p
            user32.GetAncestor.argtypes=[ctypes.c_void_p,ctypes.c_uint];user32.GetAncestor.restype=ctypes.c_void_p
            front=user32.GetForegroundWindow()
            # GA_ROOT: a focused child control still belongs to the granted top-level window.
            if user32.GetAncestor(front,2)!=window.handle and front!=window.handle:raise ValueError('O Windows não deixou trazer a janela para frente; clique nela e peça de novo.')
            send_keys(sequence,pause=.03,with_spaces=True)
            self.snapshots.pop(gid,None)
        return {'keys_sent':keys,'observation':self.read(gid)}

    def describe_target(self,gid,sid,target):
        cached=self.snapshots.get(gid)
        if not cached or cached['public']['snapshot_id']!=sid or not re.fullmatch(r'w\d+',target):raise ValueError('Leia a janela novamente antes de interagir.')
        index=int(target[1:])
        if index>=len(cached['nodes']):raise ValueError('Elemento não observado.')
        return cached,index

    def act(self,body):
        with self.lock:
            cached,index=self.describe_target(body.window_id,body.snapshot_id,body.target)
            expected=cached['nodes'][index];window=self.window(body.window_id);matched=None
            for control in window.descendants(depth=5):
                try:
                    if self.signature(control)==expected:matched=control;break
                except Exception:continue
            if matched is None or not matched.is_visible() or not matched.is_enabled():raise ValueError('Elemento alterado/desabilitado. Leia a janela novamente.')
            if bool(matched.element_info._element.CurrentIsPassword) or SECRET.search(expected['name']+' '+expected['automation_id']):raise PermissionError('Campo protegido; use preenchimento manual.')
            if body.tool=='windows_type':
                if expected['control_type'] not in ('Edit','Document'):raise ValueError('Escolha um campo de texto acessível.')
                # Modern editors (e.g. Windows 11 Notepad) expose a Document with ValuePattern.
                try:readonly=matched.iface_value.CurrentIsReadOnly
                except Exception:raise ValueError('Este campo não aceita texto por automação; digite manualmente.')
                if readonly:raise ValueError('Campo somente leitura.')
                matched.iface_value.SetValue(body.content)
                # Some Win32 edits report a trailing line break; compare the text itself.
                if str(matched.iface_value.CurrentValue).rstrip('\r\n')!=body.content.rstrip('\r\n'):raise ValueError('O aplicativo não confirmou o texto solicitado.')
            elif body.tool=='windows_invoke':
                if expected['control_type'] in ('CheckBox','RadioButton'):
                    matched.select() if expected['control_type']=='RadioButton' else matched.toggle()
                elif expected['control_type'] in ('ListItem','TabItem','TreeItem'):matched.select()
                else:matched.invoke()
            else:raise ValueError('Operação de janela não reconhecida.')
            self.snapshots.pop(body.window_id,None)
            return {'interaction_requested':True,'observation':self.read(body.window_id)}
