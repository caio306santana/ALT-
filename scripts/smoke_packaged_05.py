"""0.5 features in the packaged backend: Whisper, Kokoro "Dora", the wake word, PDF OCR, screen capture and
volume, i.e. the native libraries PyInstaller has to bring along. Models are copied from local test
folders into a temporary data directory; nothing is downloaded. Usage: python scripts/smoke_packaged_05.py"""
import io
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path
import httpx

root=Path(__file__).resolve().parents[1]
executable=root/'release'/'win-unpacked'/'resources'/'backend'/'alt-backend.exe'
token=secrets.token_hex(32);report={}
whisper=next((p for p in [Path(os.environ.get('APPDATA',''))/'ALT-AI-dev-voice'/'faster-whisper-small',*root.glob('.local/**/faster-whisper-small')] if (p/'model.bin').is_file()),None)

def speech_wav():
    """Portuguese test phrase from the Windows voice, 16 kHz mono."""
    folder=Path(tempfile.mkdtemp());target=folder/'voz.wav'
    script=("Add-Type -AssemblyName System.Speech;$f=New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000,"
            "[System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,[System.Speech.AudioFormat.AudioChannel]::Mono);"
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;$s.SetOutputToWaveFile('"+str(target)+"',$f);$s.Speak('Abre o navegador e pesquisa a previsão do tempo');$s.Dispose()")
    subprocess.run(['powershell.exe','-NoProfile','-Command',script],capture_output=True,timeout=60)
    with wave.open(str(target)) as w:return w.readframes(w.getnframes())

def scanned_pdf():
    """A PDF that is only an image of text: extraction finds nothing, OCR must read it."""
    from PIL import Image,ImageDraw,ImageFont
    image=Image.new('RGB',(1400,500),'white');draw=ImageDraw.Draw(image)
    try:font=ImageFont.truetype('arial.ttf',72)
    except OSError:font=ImageFont.load_default()
    draw.text((60,180),'RELATORIO TESTE ALT 2026',fill='black',font=font)
    buffer=io.BytesIO();image.save(buffer,'PDF',resolution=150);return buffer.getvalue()

with tempfile.TemporaryDirectory(prefix='alt-packaged-05-') as directory:
    data=Path(directory)
    if whisper:shutil.copytree(whisper,data/'voice'/'faster-whisper-small')
    if (root/'.local'/'kokoro').is_dir():shutil.copytree(root/'.local'/'kokoro',data/'voice'/'kokoro')
    if (root/'.local'/'wake').is_dir():shutil.copytree(root/'.local'/'wake',data/'voice'/'wake')
    env={**os.environ,'ALT_SESSION_TOKEN':token,'ALT_DATA_DIR':directory,'ALT_PARENT_PID':str(os.getpid())}
    child=subprocess.Popen([str(executable)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',env=env,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        line=child.stdout.readline();assert line.startswith('ALT_READY:'),(line,child.stderr.read())
        port=json.loads(line.split(':',1)[1])['port'];headers={'Authorization':'Bearer '+token}
        with httpx.Client(base_url=f'http://127.0.0.1:{port}',trust_env=False,timeout=120,headers=headers) as client:
            for _ in range(50):
                try:client.get('/health');break
                except httpx.ConnectError:time.sleep(.2)
            status=client.get('/voice/status').json()
            report['voice_models']={k:status[k]['installed'] for k in ('whisper','dora','wake')}
            if status['whisper']['installed']:
                start=time.monotonic();text=client.post('/voice/transcribe',content=speech_wav(),headers={'Content-Type':'application/octet-stream'}).json()['text']
                report['whisper']={'text':text,'seconds':round(time.monotonic()-start,1)}
            if status['dora']['installed']:
                settings=client.get('/settings').json();settings['voice_engine']='dora';client.put('/settings',json=settings)
                client.post('/voice/speak',json={'text':'Backend empacotado da ALT funcionando.'})
                time.sleep(6);report['dora']=client.get('/voice/status').json()['engine']
            if status['wake']['installed']:
                settings=client.get('/settings').json();settings['wake_mode']='hey_jarvis';client.put('/settings',json=settings)
                time.sleep(2);report['wake_state']=client.get('/voice/status').json()['state']
                settings['wake_mode']='off';client.put('/settings',json=settings)
            pdf=client.post('/attachments',content=scanned_pdf(),headers={'Content-Type':'application/octet-stream','X-Alt-Name':'digitalizado.pdf'})
            report['ocr']=pdf.json() if pdf.status_code==200 else pdf.text
            client.put('/permissions',json={'level':2})
            def run(**body):
                proposal=client.post('/tools/propose',json=body);assert proposal.status_code==200,proposal.text
                return client.post('/tools/approve/'+proposal.json()['id']).json()
            report['screen']=run(tool='screen_look')['result']
            volume=run(tool='system_volume',value='+0')['result']
            report['volume_read']=volume.get('volume') or volume
            report['remote_status']=client.get('/remote/status').json().get('installed')
            report['routing']=client.post('/chat/route',json={'content':'oi'}).json().get('band')
    finally:
        child.terminate()
        try:child.wait(10)
        except subprocess.TimeoutExpired:child.kill()
print(json.dumps(report,ensure_ascii=False,indent=1))
