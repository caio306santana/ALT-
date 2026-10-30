"""Listening on this computer: push-to-talk from anywhere in Windows, "Hey Jarvis" (or the experimental
"Ei ALT"), end of speech by an adaptive energy VAD, and no listening while the ALT itself speaks.

Mark LVI ideas: GetAsyncKeyState polling at 30 Hz with a 60 ms debounce (core/hotkey.py), sleep after
120 s without speech and never send audio anywhere while asleep (core/wake_word.py), 700 ms of silence
ends a turn with an adaptive noise floor (providers/engine_pipeline.py), clips under 0.25 s are dropped
because Whisper invents phrases for them (providers/stt_whisper.py). Audio stays in memory."""
import os
import queue
import re
import threading
import time
import numpy as np
from backend.voice.wake import CHUNK

RATE=16000
SILENCE_END=.7
MIN_SPEECH=.25
MAX_SECONDS=30
NO_SPEECH_GIVE_UP=6
AWAKE_SECONDS=120
KEYS={'Control':0x11,'Shift':0x10,'Alt':0x12,'Space':0x20,**{f'F{i}':0x6F+i for i in range(1,13)},**{chr(c):c for c in range(0x41,0x5B)}}
EI_ALT=re.compile(r'^\W*(?:ei|hey|hei|oi|e a[ií])\W+alt\b\W*(.*)$',re.I|re.S)

def hotkey_codes(text):
    parts=(text or '').split('+')
    if not parts or any(p not in KEYS for p in parts):raise ValueError('Atalho de voz inválido.')
    return [KEYS[p] for p in parts]

class Vad:
    """Speech = 3.5x the noise floor (min 0.006 RMS) for 250 ms; 700 ms of quiet ends it."""
    def __init__(self):self.floor=.003;self.speech=0.0;self.quiet=0.0;self.total=0.0

    def update(self,chunk):
        level=float(np.sqrt(np.mean((chunk.astype(np.float32)/32768)**2)))
        seconds=len(chunk)/RATE;self.total+=seconds
        loud=level>max(.006,self.floor*3.5)
        if loud:self.speech+=seconds;self.quiet=0.0
        else:
            self.quiet+=seconds
            self.floor=self.floor*.95+level*.05
        if self.speech>=MIN_SPEECH and self.quiet>=SILENCE_END:return 'end'
        if self.total>=MAX_SECONDS:return 'end'
        if self.speech<MIN_SPEECH and self.total>=NO_SPEECH_GIVE_UP:return 'nothing'
        return 'speaking' if self.speech>=MIN_SPEECH else 'waiting'

class VoiceLoop:
    def __init__(self,transcriber,speaker,settings,hints,wake_factory=None,events=None):
        self.transcriber,self.speaker,self.settings,self.hints=transcriber,speaker,settings,hints
        self.wake_factory=wake_factory;self.wake=None;self.events=events or (lambda event:None)
        self.chunks=queue.Queue(maxsize=200);self.stream=None;self.lock=threading.Lock()
        self.mode='off';self.recording=None;self.vad=None;self.awake_until=0.0;self.state='off'
        self.stopped=False
        self.closed=threading.Event()

    # Device and stream ---------------------------------------------------------------------------
    def open(self):
        with self.lock:
            if self.stream is not None:return
            import sounddevice as sd
            def callback(data,frames,info,status):
                try:self.chunks.put_nowait(np.frombuffer(bytes(data),dtype='<i2').copy())
                except queue.Full:pass  # drop instead of blocking the audio thread
            device=self.settings().get('voice_input') or None
            self.stream=sd.RawInputStream(samplerate=RATE,channels=1,dtype='int16',blocksize=CHUNK,device=device,callback=callback)
            self.stream.start()

    def close(self):
        with self.lock:
            if self.stream is not None:
                try:self.stream.stop();self.stream.close()
                finally:self.stream=None

    def emit(self,**event):self.events(event)

    def set_state(self,state):
        if state!=self.state:self.state=state;self.emit(type='state',state=state)

    # Control -------------------------------------------------------------------------------------
    def start(self):
        """Background threads: audio worker and the push-to-talk key poller."""
        if getattr(self,'threads',None):return
        self.threads=[threading.Thread(target=self.worker,daemon=True,name='voice-worker'),threading.Thread(target=self.hotkey_loop,daemon=True,name='voice-hotkey')]
        for thread in self.threads:thread.start()
        self.configure()

    def configure(self):
        """Apply the wake setting: the microphone stays open only while a wake word is on."""
        mode=self.settings().get('wake_mode','off')
        if mode=='hey_jarvis' and self.wake is None and self.wake_factory:
            try:self.wake=self.wake_factory()
            except Exception as exc:self.emit(type='error',message='Palavra de ativação indisponível: '+str(exc)[:120]);mode='off'
        self.mode=mode
        if mode!='off' and not self.stopped:
            try:self.open();self.set_state('sleeping')
            except Exception as exc:self.emit(type='error',message='Microfone indisponível: '+str(exc)[:120])
        elif self.recording is None:self.close();self.set_state('off')

    def listen(self,source='button'):
        """Start one utterance now (mic button, wake word, or push-to-talk with release=True)."""
        if self.stopped:raise PermissionError('Ações suspensas.')
        if not self.transcriber.installed():raise ValueError('Baixe o modelo de voz local primeiro.')
        self.speaker.stop();self.emit(type='barge')
        self.open();self.recording=[];self.vad=None if source=='ptt' else Vad()
        self.source=source;self.set_state('listening')

    def finish(self):
        """End the current utterance and transcribe it in the background."""
        audio,self.recording=self.recording,None
        if audio is None:return
        if self.mode=='off':self.close()
        samples=np.concatenate(audio) if audio else np.zeros(0,np.int16)
        if len(samples)<RATE*MIN_SPEECH:
            self.set_state('sleeping' if self.mode!='off' else 'off');return
        self.set_state('transcribing')
        threading.Thread(target=self.transcribe,args=(samples,self.source),daemon=True).start()

    def transcribe(self,samples,source):
        try:
            text=self.transcriber.transcribe(samples.astype('<i2').tobytes(),self.hints())['text'].strip()
            if source=='ei_alt':
                match=EI_ALT.match(text)
                if not match:self.set_state('sleeping');return
                self.awake_until=time.monotonic()+AWAKE_SECONDS;text=match.group(1).strip()
                self.emit(type='wake',word='Ei ALT')
                if not text:self.listen('wake');return
            if text:self.emit(type='transcript',text=text,source=source)
            if self.mode!='off':self.awake_until=time.monotonic()+AWAKE_SECONDS
        except Exception as exc:self.emit(type='error',message='Falha ao transcrever: '+str(exc)[:120])
        finally:
            if self.recording is None:self.set_state('awake' if self.mode!='off' and time.monotonic()<self.awake_until else 'sleeping' if self.mode!='off' else 'off')

    def stop(self):
        """STOP: nothing is recorded or spoken until resume."""
        self.stopped=True;self.recording=None;self.speaker.stop();self.close();self.set_state('off')

    def resume(self):self.stopped=False;self.configure()

    def shutdown(self):
        self.closed.set();self.stop()
        for thread in getattr(self,'threads',[]):thread.join(timeout=2)

    # Threads -------------------------------------------------------------------------------------
    def worker(self):
        while not self.closed.is_set():
            try:chunk=self.chunks.get(timeout=.2)
            except queue.Empty:continue
            try:self.process(chunk)
            except Exception as exc:self.emit(type='error',message='Falha no áudio: '+str(exc)[:120])

    def process(self,chunk):
        segment,segment_vad=getattr(self,'segment',None),getattr(self,'segment_vad',None)
        if self.stopped:return
        # The ALT's own voice (plus the output latency tail) is never heard as a command.
        if self.speaker.speaking:self.segment=self.segment_vad=None;return
        if self.recording is not None:
            self.recording.append(chunk)
            if self.vad is not None:
                verdict=self.vad.update(chunk)
                if verdict in ('end','nothing'):self.finish()
            elif sum(len(c) for c in self.recording)>=RATE*MAX_SECONDS:self.finish()
            return
        awake=time.monotonic()<self.awake_until
        if self.mode=='hey_jarvis' and self.wake is not None:
            if awake:self.segment,self.segment_vad=self.follow_up(chunk,segment,segment_vad,'awake');return
            detected,_=self.wake.detect(chunk)
            if detected:self.awake_until=time.monotonic()+AWAKE_SECONDS;self.emit(type='wake',word='Hey Jarvis');self.listen('wake')
        elif self.mode=='ei_alt':
            self.segment,self.segment_vad=self.follow_up(chunk,segment,segment_vad,'awake' if awake else 'ei_alt')
        if self.mode!='off' and not awake and self.state=='awake':self.set_state('sleeping')

    def follow_up(self,chunk,segment,vad,source):
        """While awake (or for "Ei ALT"), every utterance is captured and transcribed."""
        if vad is None:vad=Vad();segment=[]
        segment.append(chunk);verdict=vad.update(chunk)
        if verdict=='end':
            self.recording,self.source=segment,source;self.finish();return None,None
        if verdict=='nothing':return None,None
        return segment,vad

    def hotkey_loop(self):
        if os.name!='nt':return
        import ctypes
        user32=ctypes.WinDLL('user32');user32.GetAsyncKeyState.restype=ctypes.c_short
        held_since=None;active=False;codes=[];checked=0
        while not self.closed.wait(1/30):
            # The setting is reread every 2 s, not on each of the 30 polls per second.
            if time.monotonic()-checked>2:
                checked=time.monotonic()
                try:codes=hotkey_codes(self.settings().get('voice_ptt','Control+Space'))
                except Exception:codes=[]
            if not codes:continue
            down=all(user32.GetAsyncKeyState(c)&0x8000 for c in codes)
            now=time.monotonic()
            if down and not active:
                held_since=held_since or now
                if now-held_since>=.06 and not self.stopped and self.transcriber.installed():
                    active=True
                    try:self.listen('ptt')
                    except Exception as exc:self.emit(type='error',message=str(exc));active=False
            elif not down:
                held_since=None
                if active:active=False;self.finish()

def measure_input(settings,seconds=2.0,on_level=lambda level:None):
    """Live level for the TEST button and a verdict (Mark LVI core/audio_devices.py)."""
    import sounddevice as sd
    peak=0;levels=[]
    with sd.InputStream(samplerate=RATE,channels=1,dtype='int16',device=settings().get('voice_input') or None) as stream:
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            data,_=stream.read(800)
            value=int(np.abs(data).max()) if len(data) else 0
            peak=max(peak,value);levels.append(value);on_level(value)
    verdict='Nada chegou do microfone: confira se é o dispositivo certo e se não está mudo.' if peak<100 else 'Baixo demais: aproxime o microfone ou aumente o volume de entrada.' if peak<1500 else 'Microfone funcionando.'
    return {'peak':peak,'ok':peak>=1500,'verdict':verdict}

def devices():
    """Input and output devices by name (MME resamples to 16 kHz; duplicates across host APIs removed)."""
    import sounddevice as sd
    apis=sd.query_hostapis();mme=next((i for i,a in enumerate(apis) if 'MME' in a['name']),0)
    rows=[d for d in sd.query_devices() if d['hostapi']==mme]
    inputs=sorted({d['name'] for d in rows if d['max_input_channels']>0 and 'Mapeador' not in d['name'] and 'Mapper' not in d['name']})
    outputs=sorted({d['name'] for d in rows if d['max_output_channels']>0 and 'Mapeador' not in d['name'] and 'Mapper' not in d['name']})
    return {'inputs':inputs,'outputs':outputs}
