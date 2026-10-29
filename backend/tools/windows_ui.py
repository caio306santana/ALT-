"""Windows UI Automation with owner-selected window grants and stale-node checks."""
import hashlib
import os
import re
import threading
from uuid import uuid4
import psutil

EXCLUDED={'cmd.exe','powershell.exe','pwsh.exe','windowsterminal.exe','conhost.exe','consent.exe','logonui.exe','winlogon.exe','sechealthui.exe','securityhealthsystray.exe','systemsettings.exe','keepass.exe','keepassxc.exe','1password.exe','bitwarden.exe','alt-ai.exe','alt-backend.exe'}
SECRET=re.compile(r'password|senha|one.?time|credit.?card|cvv|captcha|secret|api.?key|token',re.I)

class WindowsUI:
    def __init__(self,store):
        self.store=store;self.candidates={};self.snapshots={};self.lock=threading.RLock()
        store.db.execute('CREATE TABLE IF NOT EXISTS windows_grants(id TEXT PRIMARY KEY,handle INTEGER NOT NULL,pid INTEGER NOT NULL,created REAL NOT NULL,title TEXT NOT NULL,exe TEXT NOT NULL)');store.db.commit()

    def desktop(self):
        if os.name!='nt':raise ValueError('Controle de janelas disponível no Windows.')
        import comtypes
        comtypes.CoInitializeEx(0)
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

    def grant(self,key):
        row=self.candidate(key);gid=str(uuid4())
        old=self.store.rows('SELECT id FROM windows_grants WHERE handle=? AND pid=? AND created=?',(row['handle'],row['pid'],row['created']))
        if old:return old[0]['id']
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
                    if not sig['name'] and sig['control_type'] not in ('Edit','ComboBox'):continue
                    value=''
                    if sig['control_type']=='Edit':
                        try:value=str(control.iface_value.CurrentValue)[:3000]
                        except Exception:pass
                    eid='w'+str(len(elements));elements.append({'id':eid,'label':sig['name'],'type':sig['control_type'],'value':value,'enabled':control.is_enabled()})
                    nodes.append(sig)
                    if len(elements)>=160:break
                except Exception:continue
            snapshot={'snapshot_id':str(uuid4()),'window_id':gid,'title':window.window_text(),'elements':elements,'truncated':len(elements)>=160}
            self.snapshots[gid]={'public':snapshot,'nodes':nodes}
            return snapshot

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
                if expected['control_type']!='Edit':raise ValueError('Escolha um campo de texto acessível.')
                if matched.iface_value.CurrentIsReadOnly:raise ValueError('Campo somente leitura.')
                matched.iface_value.SetValue(body.content)
                if matched.iface_value.CurrentValue!=body.content:raise ValueError('O aplicativo não confirmou o texto solicitado.')
            elif body.tool=='windows_invoke':
                if expected['control_type'] in ('CheckBox','RadioButton'):
                    matched.select() if expected['control_type']=='RadioButton' else matched.toggle()
                elif expected['control_type'] in ('ListItem','TabItem','TreeItem'):matched.select()
                else:matched.invoke()
            else:raise ValueError('Operação de janela não reconhecida.')
            self.snapshots.pop(body.window_id,None)
            return {'interaction_requested':True,'observation':self.read(body.window_id)}
