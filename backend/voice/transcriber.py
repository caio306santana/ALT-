"""Local speech-to-text with faster-whisper. Audio never leaves the computer; the model is downloaded
only after the owner asks for it, and only from the fixed Hugging Face repository below."""
import asyncio
import os
import threading
import time

REPOSITORY='Systran/faster-whisper-small'
FILES=['config.json','model.bin','tokenizer.json','vocabulary.txt','preprocessor_config.json']
# model.bin is ~484 MB; used only to show download progress.
EXPECTED_BYTES=486_000_000
SAMPLE_RATE=16000
MAX_SECONDS=30

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
                self.model=WhisperModel(str(self.directory),device='cpu',compute_type='int8',cpu_threads=min(8,os.cpu_count() or 4))
            return self.model

    def transcribe(self,pcm,hints=()):
        """pcm: 16 kHz mono signed 16-bit little-endian samples, as the desktop recorder sends them."""
        import numpy
        if len(pcm)%2 or not pcm:raise ValueError('Áudio inválido.')
        if len(pcm)>SAMPLE_RATE*2*MAX_SECONDS:raise ValueError(f'Fale por até {MAX_SECONDS} segundos.')
        audio=numpy.frombuffer(pcm,dtype='<i2').astype(numpy.float32)/32768
        model=self.load();start=time.monotonic()
        # Program names as a vocabulary hint: without it, "Spotify" came back as "os patifai".
        prompt='ALT, Google Chrome, YouTube, Spotify, Discord, WhatsApp, Steam, '+', '.join(list(hints)[:30])
        segments,_=model.transcribe(audio,language='pt',beam_size=5,vad_filter=True,initial_prompt=prompt[:600],condition_on_previous_text=False)
        text=' '.join(segment.text.strip() for segment in segments).strip()
        return {'text':text,'seconds':round(time.monotonic()-start,2),'audio_seconds':round(len(audio)/SAMPLE_RATE,1)}

def install_voice(app,auth,engine,store,data_dir,hints=lambda:()):
    from fastapi import Depends,Request
    transcriber=Transcriber(data_dir);app.state.voice=transcriber

    @app.get('/voice/status',dependencies=[Depends(auth)])
    async def voice_status():return transcriber.status()

    @app.post('/voice/download',dependencies=[Depends(auth)])
    async def voice_download():
        if engine.stopped:raise PermissionError('Ações suspensas.')
        store.audit('voice_model_download',REPOSITORY)
        return transcriber.download()

    @app.post('/voice/transcribe',dependencies=[Depends(auth)])
    async def voice_transcribe(request:Request):
        if engine.stopped:raise PermissionError('Ações suspensas.')
        return await asyncio.to_thread(transcriber.transcribe,await request.body(),hints())
    return transcriber
