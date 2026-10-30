"""Local speech-to-text with faster-whisper, and the voice routes. Audio never leaves the computer;
models are downloaded only after the owner asks, from the fixed sources below."""
import asyncio
import json
import os
import threading
import time
import urllib.request

REPOSITORY='Systran/faster-whisper-small'
FILES=['config.json','model.bin','tokenizer.json','vocabulary.txt','preprocessor_config.json']
# model.bin is ~484 MB; used only to show download progress.
EXPECTED_BYTES=486_000_000
SAMPLE_RATE=16000
MAX_SECONDS=30
MIN_SECONDS=.25

class Transcriber:
    def __init__(self,data_dir):
        self.directory=data_dir/'voice'/'faster-whisper-small'
        self.model=None;self.lock=threading.Lock();self.download_thread=None;self.error=''

    def installed(self):return all((self.directory/name).is_file() for name in FILES if name!='preprocessor_config.json')

    def status(self):
        downloading=bool(self.download_thread and self.download_thread.is_alive())
        size=sum(f.stat().st_size for f in self.directory.rglob('*') if f.is_file()) if downloading and self.directory.exists() else 0
        return {'installed':self.installed(),'downloading':downloading,'progress':min(.99,size/EXPECTED_BYTES) if downloading else None,
                'error':self.error,'model':'Whisper small (local, pt-BR)','size_mb':480,'loaded':self.model is not None}

    def download(self):
        if self.installed():return self.status()
        if self.download_thread and self.download_thread.is_alive():return self.status()
        self.error=''
        def run():
            try:
                from huggingface_hub import snapshot_download
                self.directory.mkdir(parents=True,exist_ok=True)
                snapshot_download(REPOSITORY,local_dir=str(self.directory),allow_patterns=FILES)
            except Exception:
                self.error='Falha ao baixar o modelo de voz. Verifique a conexão e o espaço livre e tente de novo.'
        self.download_thread=threading.Thread(target=run,daemon=True);self.download_thread.start()
        return self.status()

    def load(self):
        with self.lock:
            if self.model is None:
                if not self.installed():raise ValueError('Baixe o modelo de voz local primeiro.')
                from faster_whisper import WhisperModel
                # Half the cores, so playback and the UI keep running while it transcribes.
                self.model=WhisperModel(str(self.directory),device='cpu',compute_type='int8',cpu_threads=max(2,min(8,(os.cpu_count() or 4)//2)))
            return self.model

    def warmup(self):
        """The first transcription took 8.5 s cold and ~1 s warm (Mark LVI); pay it at startup."""
        if self.installed():
            try:self.transcribe(b'\x00\x00'*1600*int(SAMPLE_RATE/16000),())
            except Exception:pass

    def transcribe(self,pcm,hints=()):
        """pcm: 16 kHz mono signed 16-bit little-endian samples."""
        import numpy
        if len(pcm)%2 or not pcm:raise ValueError('Áudio inválido.')
        if len(pcm)>SAMPLE_RATE*2*MAX_SECONDS:raise ValueError(f'Fale por até {MAX_SECONDS} segundos.')
        audio=numpy.frombuffer(pcm,dtype='<i2').astype(numpy.float32)/32768
        model=self.load();start=time.monotonic()
        # Under 0.25 s Whisper invents phrases ("Obrigado."); a warm-up clip is the only exception.
        if len(audio)<SAMPLE_RATE*MIN_SECONDS and audio.any():return {'text':'','seconds':0,'audio_seconds':round(len(audio)/SAMPLE_RATE,2)}
        # Program names as a vocabulary hint: without it, "Spotify" came back as "os patifai".
        prompt='ALT, Google Chrome, YouTube, Spotify, Discord, WhatsApp, Steam, '+', '.join(list(hints)[:30])
        segments,_=model.transcribe(audio,language='pt',beam_size=5,vad_filter=True,initial_prompt=prompt[:600],condition_on_previous_text=False)
        text=' '.join(segment.text.strip() for segment in segments).strip()
        return {'text':text,'seconds':round(time.monotonic()-start,2),'audio_seconds':round(len(audio)/SAMPLE_RATE,1)}

class FileDownload:
    """A fixed set of model files from fixed URLs, with progress, started only by the owner."""
    def __init__(self,directory,files,expected_mb):
        self.directory,self.files,self.expected=directory,files,expected_mb*1_000_000;self.thread=None;self.error=''

    def installed(self):return all((self.directory/n).is_file() for n in self.files)

    def status(self):
        busy=bool(self.thread and self.thread.is_alive())
        size=sum(f.stat().st_size for f in self.directory.glob('*') if f.is_file()) if self.directory.exists() else 0
        return {'installed':self.installed(),'downloading':busy,'progress':min(.99,size/self.expected) if busy else None,'error':self.error,'size_mb':round(self.expected/1e6)}

    def start(self):
        if self.installed() or self.thread and self.thread.is_alive():return self.status()
        self.error=''
        def run():
            try:
                self.directory.mkdir(parents=True,exist_ok=True)
                for name,url in self.files.items():
                    target=self.directory/name
                    if target.is_file():continue
                    partial=target.with_suffix(target.suffix+'.part')
                    with urllib.request.urlopen(url,timeout=60) as response,open(partial,'wb') as out:
                        while chunk:=response.read(1<<20):out.write(chunk)
                    partial.replace(target)
            except Exception:self.error='Falha ao baixar. Verifique a conexão e tente de novo.'
        self.thread=threading.Thread(target=run,daemon=True);self.thread.start()
        return self.status()

class VoiceEvents:
    """Fan-out of voice events (state, transcript, speaking, levels) to the desktop's event stream."""
    def __init__(self):self.subscribers=[];self.lock=threading.Lock()
    def publish(self,event):
        with self.lock:subscribers=list(self.subscribers)
        for loop,queue in subscribers:
            try:loop.call_soon_threadsafe(queue.put_nowait,event)
            except RuntimeError:pass
    def subscribe(self):
        queue=asyncio.Queue(maxsize=200);entry=(asyncio.get_running_loop(),queue)
        with self.lock:self.subscribers.append(entry)
        return entry
    def unsubscribe(self,entry):
        with self.lock:
            if entry in self.subscribers:self.subscribers.remove(entry)

def install_voice(app,auth,engine,store,data_dir,hints=lambda:()):
    from fastapi import Depends,Request
    from fastapi.responses import StreamingResponse
    from backend.voice.speech import Speaker,KOKORO_FILES,KOKORO_MB
    from backend.voice.wake import WakeWord,FILES as WAKE_FILES
    from backend.voice.loop import VoiceLoop,measure_input,devices
    settings=store.settings
    transcriber=Transcriber(data_dir);app.state.voice=transcriber
    events=VoiceEvents()
    dora=FileDownload(data_dir/'voice'/'kokoro',KOKORO_FILES,KOKORO_MB)
    wake=FileDownload(data_dir/'voice'/'wake',WAKE_FILES,4)
    speaker=Speaker(dora.directory,settings);speaker.listeners.append(events.publish)
    loop=VoiceLoop(transcriber,speaker,settings,hints,lambda:WakeWord(wake.directory) if wake.installed() else None,events.publish)
    app.state.speaker=speaker;app.state.voice_loop=loop

    def start():
        loop.start()
        threading.Thread(target=lambda:(transcriber.warmup(),speaker.warmup()),daemon=True,name='voice-warmup').start()
    app.state.voice_start=start

    def status():
        return {**transcriber.status(),'whisper':transcriber.status(),'dora':dora.status(),'wake':wake.status(),
                'state':loop.state,'engine':speaker.engine(),'speaking':speaker.speaking}

    @app.get('/voice/status',dependencies=[Depends(auth)])
    async def voice_status():return status()

    @app.post('/voice/download',dependencies=[Depends(auth)])
    async def voice_download(request:Request):
        if engine.stopped:raise PermissionError('Ações suspensas.')
        try:kind=(json.loads(await request.body() or b'{}') or {}).get('kind','whisper')
        except ValueError:kind='whisper'
        store.audit('voice_model_download',kind)
        if kind=='dora':dora.start()
        elif kind=='wake':wake.start()
        else:transcriber.download()
        return status()

    @app.post('/voice/listen',dependencies=[Depends(auth)])
    async def voice_listen():loop.listen('button');return status()

    @app.post('/voice/stop',dependencies=[Depends(auth)])
    async def voice_stop():speaker.stop();loop.finish() if loop.recording is not None else None;return status()

    @app.post('/voice/speak',dependencies=[Depends(auth)])
    async def voice_speak(request:Request):
        text=str((json.loads(await request.body() or b'{}') or {}).get('text',''))[:400]
        speaker.say(text or 'Olá. Esta é a minha voz.');return {'ok':True}

    @app.get('/voice/devices',dependencies=[Depends(auth)])
    async def voice_devices():
        try:return await asyncio.to_thread(devices)
        except Exception:return {'inputs':[],'outputs':[]}

    @app.post('/voice/test',dependencies=[Depends(auth)])
    async def voice_test():
        return await asyncio.to_thread(measure_input,settings,2.0,lambda level:events.publish({'type':'level','level':level}))

    @app.get('/voice/events',dependencies=[Depends(auth)])
    async def voice_events(request:Request):
        entry=events.subscribe()
        async def stream():
            try:
                yield json.dumps({'type':'state','state':loop.state})+'\n'
                while not await request.is_disconnected():
                    try:event=await asyncio.wait_for(entry[1].get(),15)
                    except asyncio.TimeoutError:event={'type':'ping'}
                    yield json.dumps(event,ensure_ascii=False)+'\n'
            finally:events.unsubscribe(entry)
        return StreamingResponse(stream(),media_type='application/x-ndjson',headers={'Cache-Control':'no-store'})

    @app.post('/voice/transcribe',dependencies=[Depends(auth)])
    async def voice_transcribe(request:Request):
        if engine.stopped:raise PermissionError('Ações suspensas.')
        return await asyncio.to_thread(transcriber.transcribe,await request.body(),hints())
    return transcriber
