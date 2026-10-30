"""Screen, sound, brightness, media keys and reminders, each reporting what it observed.

Ideas from Mark LVI: read the value before and after a change (actions/computer_settings.py), a screen
frame reduced to a JPEG the vision model can read (actions/screen_processor.py), and reminders as
least-privilege Task Scheduler jobs that fire even with the assistant closed (actions/reminder.py)."""
import io
import json
import os
import re
import subprocess
import time
from datetime import datetime,timedelta
from pathlib import Path
from uuid import uuid4
from xml.sax.saxutils import escape
from backend.memory.store import now
from backend.tools.outcome import outcome

SCREEN_COOLDOWN=4
_last_capture=[0.0]

def capture_screen(max_side=1280):
    """Primary screen as JPEG bytes (Pillow's ImageGrab)."""
    if os.name!='nt':raise ValueError('Captura de tela disponível no Windows.')
    wait=SCREEN_COOLDOWN-(time.monotonic()-_last_capture[0])
    if wait>0:raise ValueError(f'Aguarde {wait:.0f} s para uma nova captura da tela.')
    from PIL import ImageGrab
    image=ImageGrab.grab().convert('RGB');_last_capture[0]=time.monotonic()
    image.thumbnail((max_side,max_side))
    buffer=io.BytesIO();image.save(buffer,'JPEG',quality=82)
    return buffer.getvalue(),image.size

def _endpoint():
    from pycaw.pycaw import AudioUtilities
    return AudioUtilities.GetSpeakers().EndpointVolume

def volume_state():
    endpoint=_endpoint()
    return {'level':round(endpoint.GetMasterVolumeLevelScalar()*100),'mute':bool(endpoint.GetMute())}

def set_volume_state(state):
    endpoint=_endpoint()
    endpoint.SetMasterVolumeLevelScalar(max(0,min(100,int(state['level'])))/100,None)
    endpoint.SetMute(int(bool(state['mute'])),None)

def change_volume(value):
    """'50', '+10', '-10', 'mudo', 'desmutar'; done only if the read-back changed."""
    if os.name!='nt':raise ValueError('Volume disponível no Windows.')
    value=(value or '').strip().lower().replace('%','')
    before=volume_state();after=dict(before)
    if value in ('mudo','mute','silenciar'):after['mute']=True
    elif value in ('desmutar','unmute','som'):after['mute']=False
    elif re.fullmatch(r'[+-]\d{1,3}',value):after.update(level=max(0,min(100,before['level']+int(value))),mute=False)
    elif re.fullmatch(r'\d{1,3}',value):after.update(level=max(0,min(100,int(value))),mute=False)
    else:raise ValueError('Diga o volume: um número de 0 a 100, +10, -10, mudo ou desmutar.')
    set_volume_state(after);observed=volume_state()
    if observed==before:return outcome('unverified',before=before,volume=observed,notice='O volume já estava nesse valor ou o Windows não mudou.')
    return outcome('done' if observed==after else 'unverified',before=before,volume=observed)

def brightness_state():
    output=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command','(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness -ErrorAction Stop).CurrentBrightness'],
        capture_output=True,text=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if output.returncode or not output.stdout.strip().isdigit():raise ValueError('Este monitor não permite ajustar o brilho pelo Windows (comum em monitores de desktop).')
    return int(output.stdout.strip())

def set_brightness(level):
    level=max(0,min(100,int(level)))
    subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',f'(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})'],
        capture_output=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))

def change_brightness(value):
    if os.name!='nt':raise ValueError('Brilho disponível no Windows.')
    value=(value or '').strip().replace('%','')
    before=brightness_state()
    if re.fullmatch(r'[+-]\d{1,3}',value):target=before+int(value)
    elif re.fullmatch(r'\d{1,3}',value):target=int(value)
    else:raise ValueError('Diga o brilho: um número de 0 a 100, +10 ou -10.')
    set_brightness(target);observed=brightness_state()
    return outcome('done' if observed!=before else 'unverified',before=before,brightness=observed)

MEDIA={'playpause':0xB3,'pausar':0xB3,'tocar':0xB3,'pause':0xB3,'play':0xB3,'next':0xB0,'proxima':0xB0,'próxima':0xB0,'previous':0xB1,'anterior':0xB1}

def media_key(value):
    """A media key goes to whatever player has the media session; there is nothing to read back."""
    key=MEDIA.get((value or 'playpause').strip().lower())
    if not key:raise ValueError('Use playpause, next ou previous.')
    import ctypes
    user32=ctypes.WinDLL('user32')
    user32.keybd_event(key,0,0,0);user32.keybd_event(key,0,2,0)
    return outcome('done',media_key=value or 'playpause',notice='Tecla de mídia enviada ao player ativo.')

TOAST=r'''$data = Get-Content -Raw -Encoding UTF8 -LiteralPath $args[0] | ConvertFrom-Json
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml('<toast scenario="reminder"><visual><binding template="ToastGeneric"><text></text><text></text></binding></visual><actions><action content="OK" arguments="ok" activationType="system"/></actions></toast>')
$title = if ($data.title) { $data.title } else { 'ALT · lembrete' }
$xml.GetElementsByTagName('text').Item(0).InnerText = $title
$xml.GetElementsByTagName('text').Item(1).InnerText = $data.text
$app = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app).Show([Windows.UI.Notifications.ToastNotification]::new($xml))
'''

def toast(text,title='ALT',directory=None):
    """A Windows notification now (briefings, check-ins, alerts). The text goes through a JSON file."""
    if os.name!='nt':return False
    import tempfile
    folder=Path(directory) if directory else Path(tempfile.mkdtemp(prefix='alt-toast-'))
    folder.mkdir(parents=True,exist_ok=True)
    script=folder/'toast.ps1';script.write_text(TOAST,encoding='utf-8-sig')
    data=folder/f'toast-{uuid4().hex[:8]}.json';data.write_text(json.dumps({'text':text[:600],'title':title[:60]},ensure_ascii=False),encoding='utf-8')
    try:
        done=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script),str(data)],
            capture_output=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        return done.returncode==0
    finally:data.unlink(missing_ok=True)

def parse_when(value,clock=datetime.now):
    """ISO local time ('2026-10-30T15:00') or 'em 10 minutos' / 'em 2 horas'."""
    value=(value or '').strip().lower();moment=None
    relative=re.fullmatch(r'(?:em|daqui a)\s+(\d{1,4})\s*(min|minuto|minutos|h|hora|horas)',value)
    if relative:
        amount=int(relative.group(1));moment=clock()+(timedelta(minutes=amount) if relative.group(2).startswith('min') else timedelta(hours=amount))
    else:
        try:moment=datetime.fromisoformat(value.replace(' ','T'))
        except ValueError:pass
    if not moment:raise ValueError('Diga quando: data e hora (2026-10-30T15:00) ou "em 10 minutos".')
    if moment.tzinfo:moment=moment.astimezone().replace(tzinfo=None)
    if moment<=clock()+timedelta(seconds=30):raise ValueError('O horário do lembrete já passou.')
    if moment>clock()+timedelta(days=366):raise ValueError('Lembretes valem para até um ano.')
    return moment.replace(microsecond=0)

def task_xml(when,script,data):
    """Least privilege, the logged-on user's session, runs late if the PC was off, deleted after."""
    end=(when+timedelta(hours=1)).isoformat()
    command=escape(str(Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32'/'WindowsPowerShell'/'v1.0'/'powershell.exe'))
    arguments=escape(f'-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "{script}" "{data}"')
    return f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>Lembrete da ALT-AI</Description></RegistrationInfo>
  <Triggers><TimeTrigger><StartBoundary>{when.isoformat()}</StartBoundary><EndBoundary>{end}</EndBoundary><Enabled>true</Enabled></TimeTrigger></Triggers>
  <Principals><Principal id="Author"><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings><StartWhenAvailable>true</StartWhenAvailable><DeleteExpiredTaskAfter>PT0S</DeleteExpiredTaskAfter><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><ExecutionTimeLimit>PT1M</ExecutionTimeLimit><Enabled>true</Enabled></Settings>
  <Actions Context="Author"><Exec><Command>{command}</Command><Arguments>{arguments}</Arguments></Exec></Actions>
</Task>'''

def schtasks(*args):
    return subprocess.run(['schtasks.exe',*args],capture_output=True,text=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))

class Reminders:
    def __init__(self,store,data_dir,runner=schtasks):
        self.store,self.runner=store,runner;self.directory=data_dir/'reminders'
        store.db.execute('CREATE TABLE IF NOT EXISTS reminders(id TEXT PRIMARY KEY,due TEXT NOT NULL,text TEXT NOT NULL,task TEXT NOT NULL,created TEXT NOT NULL,cancelled INTEGER NOT NULL DEFAULT 0)');store.db.commit()

    def create(self,text,when):
        text=(text or '').strip()
        if not text:raise ValueError('Diga o texto do lembrete.')
        if len(text)>300:raise ValueError('Lembrete de até 300 caracteres.')
        due=parse_when(when);rid=str(uuid4())[:8];task=f'ALT-AI\\Lembrete {rid}'
        self.directory.mkdir(parents=True,exist_ok=True)
        # The message lives in a JSON file read by the script: never interpolated into a command.
        script=self.directory/'toast.ps1';script.write_text(TOAST,encoding='utf-8-sig')
        data=self.directory/f'{rid}.json';data.write_text(json.dumps({'text':text},ensure_ascii=False),encoding='utf-8')
        xml=self.directory/f'{rid}.xml';xml.write_text(task_xml(due,script,data),encoding='utf-16')
        created=self.runner('/Create','/TN',task,'/XML',str(xml),'/F')
        xml.unlink(missing_ok=True)
        if created.returncode:raise ValueError('O Agendador de Tarefas recusou o lembrete.')
        self.store.write('INSERT INTO reminders VALUES(?,?,?,?,?,0)',(rid,due.isoformat(),text,task,now()))
        confirmed=self.runner('/Query','/TN',task).returncode==0
        return outcome('done' if confirmed else 'unverified',reminder=rid,due=due.isoformat(),text=text,notice='Toca mesmo com a ALT fechada.' if confirmed else 'Criado, mas o Agendador não confirmou a tarefa.')

    def list(self):
        rows=self.store.rows("SELECT id,due,text FROM reminders WHERE cancelled=0 AND due>=? ORDER BY due",(datetime.now().replace(microsecond=0).isoformat(),))
        return outcome('done',reminders=rows)

    def cancel(self,target):
        target=(target or '').strip().lower()
        rows=[r for r in self.store.rows('SELECT * FROM reminders WHERE cancelled=0') if r['id']==target or target and target in r['text'].lower()]
        if not rows:raise ValueError('Nenhum lembrete corresponde.')
        if len(rows)>1:return outcome('ask',options=[f"{r['id']}: {r['text'][:40]}" for r in rows[:5]],notice='Mais de um lembrete corresponde; diga qual.')
        row=rows[0];self.runner('/Delete','/TN',row['task'],'/F')
        self.store.write('UPDATE reminders SET cancelled=1 WHERE id=?',(row['id'],))
        (self.directory/f"{row['id']}.json").unlink(missing_ok=True)
        gone=self.runner('/Query','/TN',row['task']).returncode!=0
        return outcome('done' if gone else 'unverified',cancelled=row['id'],text=row['text'])
