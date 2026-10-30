"""Who else is using the graphics card, and how fast this computer normally generates.

On 29/10/2026 the RX 7600 kept generating at 4.5 tok/s after a driver hang (normal: 57) and nothing in
the app said why. The counters show other programs (a game) competing for the card; the speed reference
catches a card that is slow with no visible competitor."""
import ctypes
import os
import re
import threading
import time

COUNTER='\\GPU Engine(*)\\Utilization Percentage'
PDH_FMT_DOUBLE=0x200
PDH_MORE_DATA=0x800007D2
# Processes that are expected to use the card while the ALT answers.
OWN={'ollama.exe','ollama app.exe','llama-server.exe','dwm.exe','alt-ai.exe','alt-backend.exe','electron.exe','python.exe','pythonw.exe','csrss.exe','system'}
BUSY_PERCENT=40
BUSY_READINGS=3
FREE_SECONDS=60
SLOW_RATIO=.3

if os.name=='nt':
    from ctypes import wintypes
    class _Value(ctypes.Structure):_fields_=[('CStatus',wintypes.DWORD),('doubleValue',ctypes.c_double)]
    class _Item(ctypes.Structure):_fields_=[('szName',wintypes.LPWSTR),('FmtValue',_Value)]

class GpuCounters:
    """Per-process GPU engine utilisation through PDH; one query kept open, sampled on demand."""
    def __init__(self):
        self.query=self.counter=None;self.lock=threading.Lock();self.opened=0
        if os.name!='nt':return
        try:
            self.pdh=ctypes.WinDLL('pdh')
            # PDH status codes such as PDH_MORE_DATA are unsigned; the default int restype makes them negative.
            for name in ('PdhOpenQueryW','PdhAddEnglishCounterW','PdhCollectQueryData','PdhGetFormattedCounterArrayW','PdhCloseQuery'):
                getattr(self.pdh,name).restype=wintypes.DWORD
            self.open()
        except OSError:self.query=None

    def open(self):
        query,counter=ctypes.c_void_p(),ctypes.c_void_p()
        if self.pdh.PdhOpenQueryW(None,None,ctypes.byref(query)):return
        if self.pdh.PdhAddEnglishCounterW(query,COUNTER,None,ctypes.byref(counter)):self.pdh.PdhCloseQuery(query);return
        self.pdh.PdhCollectQueryData(query)
        if self.query is not None:self.pdh.PdhCloseQuery(self.query)
        self.query,self.counter,self.opened=query,counter,time.monotonic()

    def sample(self):
        """{pid: busiest engine type %}; empty when counters are unavailable."""
        if self.query is None:return {}
        with self.lock:
            # The wildcard is expanded when the query is opened: reopen so a game started later is seen.
            if time.monotonic()-self.opened>30:self.open();time.sleep(.2)
            if self.pdh.PdhCollectQueryData(self.query):return {}
            size,count=wintypes.DWORD(0),wintypes.DWORD(0)
            status=self.pdh.PdhGetFormattedCounterArrayW(self.counter,PDH_FMT_DOUBLE,ctypes.byref(size),ctypes.byref(count),None)
            if status!=PDH_MORE_DATA or not size.value:return {}
            buffer=ctypes.create_string_buffer(size.value)
            if self.pdh.PdhGetFormattedCounterArrayW(self.counter,PDH_FMT_DOUBLE,ctypes.byref(size),ctypes.byref(count),buffer):return {}
            items=ctypes.cast(buffer,ctypes.POINTER(_Item))
            engines={}
            for i in range(count.value):
                match=re.match(r'pid_(\d+)_.*engtype_(\w+)',items[i].szName or '')
                if match and items[i].FmtValue.CStatus in (0,1):
                    key=(int(match.group(1)),match.group(2))
                    engines[key]=engines.get(key,0)+items[i].FmtValue.doubleValue
        usage={}
        for (pid,_),value in engines.items():usage[pid]=max(usage.get(pid,0),value)
        return usage

def process_name(pid):
    import psutil
    try:return psutil.Process(pid).name()
    except psutil.Error:return ''

class GpuWatch:
    """A program other than the ALT/Ollama above 40% for 3 readings in a row marks the card as busy;
    60 s without that clears it."""
    def __init__(self,counters=None,clock=time.monotonic,names=process_name):
        self.counters=counters if counters is not None else GpuCounters()
        self.clock,self.names=clock,names
        self.streak={};self.busy_by=None;self.last_busy=0;self.lock=threading.Lock()

    def observe(self):
        usage=self.counters.sample()
        with self.lock:
            heavy={}
            for pid,value in usage.items():
                if value<BUSY_PERCENT:continue
                name=self.names(pid)
                if name.casefold() in OWN or not name:continue
                heavy[pid]=(name,value)
            self.streak={pid:self.streak.get(pid,0)+1 for pid in heavy}
            ready=[heavy[pid] for pid,n in self.streak.items() if n>=BUSY_READINGS]
            if ready:
                self.busy_by=max(ready,key=lambda row:row[1]);self.last_busy=self.clock()
            elif self.busy_by and self.clock()-self.last_busy>=FREE_SECONDS:self.busy_by=None
            return self.state()

    def state(self):
        if not self.busy_by:return {'busy':False}
        return {'busy':True,'process':self.busy_by[0],'percent':round(self.busy_by[1])}

    def start(self,interval=5):
        if getattr(self,'thread',None) or self.counters.query is None:return
        self.closed=threading.Event()
        def loop():
            while not self.closed.is_set():
                try:self.observe()
                except Exception:pass
                self.closed.wait(interval)
        self.thread=threading.Thread(target=loop,daemon=True,name='gpu-watch');self.thread.start()

    def stop(self):
        if getattr(self,'closed',None):self.closed.set();self.thread.join(timeout=2)

class SpeedReference:
    """Best generation speed seen per model on this computer; it only decays slowly, so a bad evening
    does not become the new normal."""
    def __init__(self,store):self.store=store

    def all(self):return dict(self.store.settings().get('speed_reference') or {})

    def observe(self,model,metrics,game=False):
        speed=(metrics or {}).get('tokens_per_second');tokens=(metrics or {}).get('tokens') or 0
        if game or model.startswith('cloud:') or not speed or tokens<40:return None
        references=self.all();reference=references.get(model)
        references[model]=round(max(speed,reference*.995) if reference else speed,2)
        self.store.set_settings({'speed_reference':references})
        if not reference:return {'reference':references[model],'ratio':1.0}
        result={'reference':reference,'ratio':round(speed/reference,2)}
        if speed<reference*SLOW_RATIO:
            result['warning']=(f'Esta resposta saiu a {speed:.1f} tokens/s; o normal deste PC com {model} é {reference:.0f}. '
                'A placa de vídeo está ocupada (jogo?) ou presa num estado lento: fechar o programa pesado ou reiniciar o PC costuma resolver. '
                'O GAME MODE responde pelo processador enquanto isso.')
        return result

def light_notice(state):
    return (f"Placa de vídeo ocupada por {state['process']} ({state['percent']}%): resposta curta no modo leve. "
            'Ative o GAME MODE para conversar pelo processador sem disputar com o jogo.')
