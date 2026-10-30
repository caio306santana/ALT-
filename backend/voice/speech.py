"""Spoken replies on this computer: Kokoro "Dora" (pt-BR, ONNX on the CPU) with the Windows voice as
fallback. Sentence N+1 is synthesised while N plays; playback goes out in 50 ms blocks so STOP or
push-to-talk cut it at once (Mark LVI core/tts.py, providers/audio.py)."""
import json
import os
import queue
import re
import subprocess
import tempfile
import threading
import time
import wave
from pathlib import Path
import numpy as np

KOKORO_URL='https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/'
KOKORO_FILES={'kokoro-v1.0.int8.onnx':KOKORO_URL+'kokoro-v1.0.int8.onnx','voices-v1.0.bin':KOKORO_URL+'voices-v1.0.bin'}
KOKORO_MB=115
BLOCK_SECONDS=.05
TAIL_SECONDS=.25

def pause_cap(samples,rate,limit=.5):
    """Silences longer than 500 ms (after punctuation) are shortened."""
    quiet=np.abs(samples)<.01;limit=int(limit*rate);out=[];run=0
    for start in range(0,len(samples),int(rate*.01)):
        block=samples[start:start+int(rate*.01)]
        if quiet[start:start+len(block)].all():
            run+=len(block)
            if run>limit:continue
        else:run=0
        out.append(block)
    return np.concatenate(out) if out else samples

class Speaker:
    def __init__(self,directory,settings=lambda:{}):
        self.directory=directory;self.settings=settings
        self.kokoro=None;self.lock=threading.Lock();self.jobs=queue.Queue();self.audio=queue.Queue(maxsize=4)
        self.generation=0;self.speaking_until=0.0;self.listeners=[]
        threading.Thread(target=self._synth_loop,daemon=True,name='tts-synth').start()
        threading.Thread(target=self._play_loop,daemon=True,name='tts-play').start()

    def installed(self):return all((self.directory/name).is_file() for name in KOKORO_FILES)

    def engine(self):
        wanted=self.settings().get('voice_engine','dora')
        return 'dora' if wanted=='dora' and self.installed() else 'maria'

    def load(self):
        with self.lock:
            if self.kokoro is None:
                from kokoro_onnx import Kokoro
                self.kokoro=Kokoro(str(self.directory/'kokoro-v1.0.int8.onnx'),str(self.directory/'voices-v1.0.bin'))
            return self.kokoro

    def warmup(self):
        if self.engine()=='dora':
            try:self.synth('Pronto.')
            except Exception:pass

    def synth(self,text):
        speed=float(self.settings().get('voice_speed',1.05) or 1.05)
        if self.engine()=='dora':
            samples,rate=self.load().create(text,voice='pf_dora',speed=speed,lang='pt-br')
            return pause_cap(np.asarray(samples,dtype=np.float32),rate),rate
        return sapi(text,speed)

    @property
    def speaking(self):return time.monotonic()<self.speaking_until

    def say(self,text):
        if text.strip():self.jobs.put((self.generation,text.strip()))

    def stop(self):
        """Cut everything queued or playing (STOP, push-to-talk, wake word)."""
        self.generation+=1
        for q in (self.jobs,self.audio):
            while True:
                try:q.get_nowait()
                except queue.Empty:break
        self.speaking_until=0.0
        self._emit({'type':'speaking','speaking':False})

    def _emit(self,event):
        for listener in list(self.listeners):
            try:listener(event)
            except Exception:pass

    def _synth_loop(self):
        while True:
            generation,text=self.jobs.get()
            if generation!=self.generation:continue
            try:samples,rate=self.synth(text)
            except Exception as exc:
                self._emit({'type':'error','message':'A voz falhou: '+str(exc)[:120]});continue
            if generation==self.generation:self.audio.put((generation,samples,rate))

    def _play_loop(self):
        while True:
            generation,samples,rate=self.audio.get()
            if generation!=self.generation:continue
            try:
                import sounddevice as sd
                device=self.settings().get('voice_output') or None
                self._emit({'type':'speaking','speaking':True})
                with sd.OutputStream(samplerate=rate,channels=1,dtype='float32',device=device) as stream:
                    block=int(rate*BLOCK_SECONDS)
                    for start in range(0,len(samples),block):
                        if generation!=self.generation:break
                        self.speaking_until=time.monotonic()+BLOCK_SECONDS*2+stream.latency+TAIL_SECONDS
                        stream.write(samples[start:start+block].reshape(-1,1))
                if self.audio.empty() and self.jobs.empty():self._emit({'type':'speaking','speaking':False})
            except Exception as exc:
                self._emit({'type':'error','message':'Saída de áudio indisponível: '+str(exc)[:120]})

SAPI=r'''$t = Get-Content -Raw -Encoding UTF8 -LiteralPath $args[0]
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$v = $s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -like 'pt*' } | Select-Object -First 1
if ($v) { $s.SelectVoice($v.VoiceInfo.Name) }
$s.Rate = [int]$args[2]
$s.SetOutputToWaveFile($args[1])
$s.Speak($t); $s.Dispose()
'''

def sapi(text,speed=1.0):
    """Windows voice through PowerShell; the text goes in a UTF-8 file, never on the command line."""
    if os.name!='nt':raise RuntimeError('Voz do Windows indisponível neste sistema.')
    folder=Path(tempfile.mkdtemp(prefix='alt-voice-'))
    try:
        (folder/'say.ps1').write_text(SAPI,encoding='utf-8-sig');(folder/'text.txt').write_text(text,encoding='utf-8')
        rate=max(-10,min(10,round((speed-1)*10)))
        subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(folder/'say.ps1'),str(folder/'text.txt'),str(folder/'out.wav'),str(rate)],
            capture_output=True,timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        target=folder/'out.wav'
        # "Success" with no audio happens when no installed voice covers the text.
        if not target.is_file() or target.stat().st_size<100:raise RuntimeError('a voz do Windows não gerou áudio.')
        with wave.open(str(target)) as w:
            samples=np.frombuffer(w.readframes(w.getnframes()),'<i2').astype(np.float32)/32768;rate=w.getframerate()
        return samples,rate
    finally:
        for f in folder.glob('*'):f.unlink(missing_ok=True)
        folder.rmdir()
