"""Image generation: a local ComfyUI (graphics card or processor) that the owner installs from the ALT, or a paid API.

Local: the official ComfyUI portable package for the detected card (AMD, NVIDIA or Intel; processor mode otherwise)
and the SD-Turbo model, both downloaded from fixed official sources and checked by SHA256 before use. ComfyUI
listens only on 127.0.0.1. Paid API: OpenAI image generation with the owner's key, kept in the Windows DPAPI vault.
Generated images are saved under the ALT's data folder; nothing is uploaded unless the owner chose the API."""
import base64
import hashlib
import json
import os
import shutil
import subprocess
import threading
import time
import urllib.request
from pathlib import Path
from uuid import uuid4
import httpx

RELEASE='https://api.github.com/repos/comfyanonymous/ComfyUI/releases/latest'
PACKAGES={'amd':'ComfyUI_windows_portable_amd.7z','nvidia':'ComfyUI_windows_portable_nvidia.7z','intel':'ComfyUI_windows_portable_intel.7z'}
# SD-Turbo: one-step 512x512 images, small enough for an 8 GB card and usable on a processor.
MODEL={'name':'sd_turbo.safetensors','url':'https://huggingface.co/stabilityai/sd-turbo/resolve/main/sd_turbo.safetensors',
    'sha256':'3f067a1b943cf162f2b8f8588f6cf5824bd5b4c7d1d88d87164b9ca123616549','bytes':5214561328,
    'license':'Licença da Stability AI para o SD-Turbo (uso pessoal/não comercial). Confira em huggingface.co/stabilityai/sd-turbo.'}
PORT=8189  # not ComfyUI's default 8188, so an install the owner already runs is never touched
NEEDED_GB=18
API_URL='https://api.openai.com/v1/images/generations'
API_MODEL='gpt-image-2'

def detect_hardware(runner=subprocess.run):
    """Graphics cards from Windows; a discrete AMD/NVIDIA/Intel Arc card runs ComfyUI, anything else uses the processor."""
    names=[]
    if os.name=='nt':
        try:
            out=runner(['powershell','-NoProfile','-Command','(Get-CimInstance Win32_VideoController).Name'],capture_output=True,text=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).stdout
            names=[line.strip() for line in out.splitlines() if line.strip()]
        except (OSError,subprocess.SubprocessError):names=[]
    text=' | '.join(names)
    lowered=text.casefold()
    if 'nvidia' in lowered:variant,cpu='nvidia',False
    elif any(k in lowered for k in ('radeon rx','radeon pro','radeon(tm) rx')):variant,cpu='amd',False
    elif 'arc' in lowered and 'intel' in lowered:variant,cpu='intel',False
    else:variant,cpu='intel',True  # integrated graphics: the smallest package, run on the processor
    return {'cards':names,'variant':variant,'cpu_mode':cpu,'label':(names[0] if names else 'placa não identificada')}

def sha256_file(path):
    digest=hashlib.sha256()
    with open(path,'rb') as handle:
        while chunk:=handle.read(1<<20):digest.update(chunk)
    return digest.hexdigest()

def fetch(url,target,expected_sha,progress,cancel,opener=urllib.request.urlopen):
    """Download to target.part, check SHA256, then rename. Raises on mismatch or cancel."""
    partial=target.with_name(target.name+'.part');digest=hashlib.sha256()
    request=urllib.request.Request(url,headers={'User-Agent':'ALT-AI image installer'})
    try:
        with opener(request,timeout=60) as response,open(partial,'wb') as out:
            while chunk:=response.read(1<<20):
                if cancel.is_set():raise InterruptedError('Instalação cancelada.')
                out.write(chunk);digest.update(chunk);progress(len(chunk))
        if digest.hexdigest()!=expected_sha:raise ValueError('O arquivo baixado não confere com o hash oficial; nada foi instalado.')
        partial.replace(target)
    finally:
        if partial.exists():partial.unlink()


class Images:
    def __init__(self,data_dir,store,vault_factory=None,runner=subprocess.run,popen=subprocess.Popen):
        self.root=data_dir/'images';self.store=store;self.runner=runner;self.popen=popen
        self.install_dir=self.root/'comfyui';self.output=self.root/'generated'
        self.thread=None;self.cancel=threading.Event();self.process=None
        self.state={'stage':'','done':0,'total':0,'error':''};self._hardware=None
        self.vault=vault_factory(data_dir) if vault_factory else ApiVault(data_dir)

    # ---------- status and settings
    def hardware(self):
        if self._hardware is None:self._hardware=detect_hardware(self.runner)
        return self._hardware

    def portable(self):return self.install_dir/'ComfyUI_windows_portable'
    def model_path(self):return self.portable()/'ComfyUI'/'models'/'checkpoints'/MODEL['name']
    def installed(self):return (self.portable()/'python_embeded'/'python.exe').is_file() and self.model_path().is_file()
    def provider(self):return self.store.settings().get('image_provider','')

    def running(self):
        if not self.process or self.process.poll() is not None:return False
        try:return httpx.get(f'http://127.0.0.1:{PORT}/system_stats',timeout=2,trust_env=False).status_code==200
        except httpx.HTTPError:return False

    def status(self):
        busy=bool(self.thread and self.thread.is_alive())
        free=shutil.disk_usage(self.root.parent if self.root.parent.exists() else Path.home()).free/1e9
        return {'provider':self.provider(),'hardware':self.hardware(),
            'local':{'installed':self.installed(),'installing':busy,'running':self.running(),**self.state,'disk_free_gb':round(free,1),
                'needed_gb':NEEDED_GB,'model':MODEL['name'],'license':MODEL['license']},
            'api':{'configured':self.vault.configured(),'model':self.store.settings().get('image_api_model',API_MODEL)}}

    def choose(self,provider,model=''):
        if provider not in ('','local','openai'):raise ValueError('Escolha local, API ou desligado.')
        if provider=='local' and not self.installed():raise ValueError('Instale o gerador local primeiro.')
        if provider=='openai' and not self.vault.configured():raise ValueError('Salve a chave da API primeiro.')
        update={'image_provider':provider}
        if model:update['image_api_model']=model.strip()[:60]
        self.store.set_settings(update);self.store.audit('image_provider',provider or 'off');return self.status()

    # ---------- local install
    def install(self):
        if self.thread and self.thread.is_alive():return self.status()
        free=shutil.disk_usage(self.root.parent if self.root.parent.exists() else Path.home()).free/1e9
        if free<NEEDED_GB:raise ValueError(f'Espaço insuficiente: precisa de cerca de {NEEDED_GB} GB livres, há {free:.0f} GB.')
        self.cancel.clear();self.state={'stage':'preparando','done':0,'total':0,'error':''}
        self.thread=threading.Thread(target=self._install,daemon=True);self.thread.start()
        self.store.audit('image_install_started',self.hardware()['variant'])
        return self.status()

    def _install(self):
        try:
            self.root.mkdir(parents=True,exist_ok=True)
            hardware=self.hardware()
            if not (self.portable()/'python_embeded'/'python.exe').is_file():
                with urllib.request.urlopen(urllib.request.Request(RELEASE,headers={'User-Agent':'ALT-AI image installer','Accept':'application/vnd.github+json'}),timeout=30) as response:
                    release=json.load(response)
                asset=next((a for a in release.get('assets',[]) if a.get('name')==PACKAGES[hardware['variant']]),None)
                if not asset or not str(asset.get('digest','')).startswith('sha256:'):raise ValueError('Pacote oficial do ComfyUI não encontrado com hash publicado.')
                if not asset['browser_download_url'].startswith('https://github.com/comfyanonymous/ComfyUI/releases/download/'):raise ValueError('Endereço de download inesperado.')
                archive=self.root/asset['name']
                self.state.update(stage=f"baixando ComfyUI {release.get('tag_name','')} ({hardware['variant']})",done=0,total=asset['size'])
                fetch(asset['browser_download_url'],archive,asset['digest'].split(':',1)[1],self._advance,self.cancel)
                self.state.update(stage='extraindo o ComfyUI',done=0,total=0)
                self.install_dir.mkdir(parents=True,exist_ok=True)
                tar=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32'/'tar.exe'
                result=self.runner([str(tar),'-xf',str(archive),'-C',str(self.install_dir)],capture_output=True,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                archive.unlink(missing_ok=True)
                if result.returncode or not (self.portable()/'python_embeded'/'python.exe').is_file():raise ValueError('Não consegui extrair o ComfyUI (o tar do Windows precisa ler .7z; Windows 11 atualizado).')
            if not self.model_path().is_file():
                self.model_path().parent.mkdir(parents=True,exist_ok=True)
                self.state.update(stage='baixando o modelo SD-Turbo',done=0,total=MODEL['bytes'])
                fetch(MODEL['url'],self.model_path(),MODEL['sha256'],self._advance,self.cancel)
            self.state.update(stage='instalado',done=0,total=0)
            self.store.audit('image_install_done',hardware['variant'])
        except InterruptedError as exc:self.state.update(stage='',error=str(exc))
        except Exception as exc:
            self.state.update(stage='',error=str(exc) if isinstance(exc,ValueError) else 'Falha ao instalar. Verifique a conexão e tente de novo.')
            self.store.audit('image_install_failed',type(exc).__name__)

    def _advance(self,size):self.state['done']+=size

    def cancel_install(self):self.cancel.set();return self.status()

    # ---------- local server
    def start(self,wait=180):
        if self.running():return self.status()
        if not self.installed():raise ValueError('Instale o gerador local primeiro.')
        root=self.portable();log=open(self.root/'comfyui.log','ab')
        args=[str(root/'python_embeded'/'python.exe'),'-s',str(root/'ComfyUI'/'main.py'),'--windows-standalone-build',
            '--listen','127.0.0.1','--port',str(PORT),'--disable-auto-launch','--output-directory',str(self.root/'comfy-output')]
        if self.hardware()['cpu_mode']:args.append('--cpu')
        self.process=self.popen(args,cwd=str(root),stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        deadline=time.monotonic()+wait
        while time.monotonic()<deadline:
            if self.process.poll() is not None:raise ValueError('O ComfyUI fechou ao iniciar. Veja images/comfyui.log na pasta de dados da ALT.')
            if self.running():return self.status()
            time.sleep(1)
        raise ValueError('O ComfyUI não respondeu a tempo.')

    def stop(self):
        # Only the process this ALT started, by its handle.
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(10)
            except subprocess.TimeoutExpired:self.process.kill()
        self.process=None;return self.status()

    # ---------- generation
    def generate(self,prompt,cancel=None):
        prompt=prompt.strip()
        if not prompt:raise ValueError('Descreva a imagem.')
        provider=self.provider()
        if provider=='local':data,meta=self._local(prompt,cancel)
        elif provider=='openai':data,meta=self._api(prompt)
        else:raise ValueError('Escolha como gerar imagens em Configurações → Imagens.')
        self.output.mkdir(parents=True,exist_ok=True)
        image_id=str(uuid4());path=self.output/f'{image_id}.png';path.write_bytes(data)
        return {'status':'done','image_id':image_id,'path':str(path),'bytes':len(data),'provider':provider,'prompt':prompt[:500],**meta}

    def _local(self,prompt,cancel):
        if not self.running():self.start()
        started=time.monotonic();seed=int.from_bytes(os.urandom(4),'big')
        workflow={
            '4':{'class_type':'CheckpointLoaderSimple','inputs':{'ckpt_name':MODEL['name']}},
            '5':{'class_type':'EmptyLatentImage','inputs':{'width':512,'height':512,'batch_size':1}},
            '6':{'class_type':'CLIPTextEncode','inputs':{'text':prompt,'clip':['4',1]}},
            '7':{'class_type':'CLIPTextEncode','inputs':{'text':'','clip':['4',1]}},
            '3':{'class_type':'KSampler','inputs':{'seed':seed,'steps':1,'cfg':1.0,'sampler_name':'euler_ancestral','scheduler':'normal','denoise':1.0,
                'model':['4',0],'positive':['6',0],'negative':['7',0],'latent_image':['5',0]}},
            '8':{'class_type':'VAEDecode','inputs':{'samples':['3',0],'vae':['4',2]}},
            '9':{'class_type':'SaveImage','inputs':{'filename_prefix':'ALT','images':['8',0]}},
        }
        base=f'http://127.0.0.1:{PORT}'
        with httpx.Client(timeout=30,trust_env=False) as client:
            queued=client.post(base+'/prompt',json={'prompt':workflow,'client_id':str(uuid4())})
            if queued.status_code!=200:raise ValueError('O ComfyUI recusou o pedido de imagem.')
            pid=queued.json()['prompt_id'];deadline=time.monotonic()+(900 if self.hardware()['cpu_mode'] else 300)
            while time.monotonic()<deadline:
                if cancel is not None and cancel.is_set():
                    client.post(base+'/interrupt');raise InterruptedError('Geração interrompida.')
                entry=client.get(base+f'/history/{pid}').json().get(pid)
                if entry and entry.get('outputs'):
                    image=entry['outputs']['9']['images'][0]
                    data=client.get(base+'/view',params={'filename':image['filename'],'subfolder':image.get('subfolder',''),'type':image.get('type','output')}).content
                    return data,{'model':'SD-Turbo','seconds':round(time.monotonic()-started,1),'size':'512x512','device':'processador' if self.hardware()['cpu_mode'] else 'placa de vídeo'}
                if entry and entry.get('status',{}).get('status_str')=='error':raise ValueError('O ComfyUI falhou ao gerar a imagem.')
                time.sleep(1)
        raise ValueError('A imagem demorou demais para ficar pronta.')

    def _api(self,prompt):
        model=self.store.settings().get('image_api_model',API_MODEL);started=time.monotonic()
        response=httpx.post(API_URL,headers={'Authorization':'Bearer '+self.vault.get()},json={'model':model,'prompt':prompt,'size':'1024x1024','n':1},timeout=180,trust_env=False)
        if response.status_code!=200:
            try:detail=response.json().get('error',{}).get('message','')[:200]
            except ValueError:detail=''
            raise ValueError(f'A API recusou ({response.status_code}). {detail}'.strip())
        item=response.json()['data'][0]
        if not item.get('b64_json'):raise ValueError('A API não devolveu a imagem.')
        return base64.b64decode(item['b64_json']),{'model':model,'seconds':round(time.monotonic()-started,1),'size':'1024x1024','device':'API paga (OpenAI)'}

    def image(self,image_id):
        if not all(c in '0123456789abcdef-' for c in image_id) or len(image_id)!=36:raise ValueError('Imagem inválida.')
        path=self.output/f'{image_id}.png'
        if not path.is_file():raise ValueError('Imagem não encontrada.')
        return {'data':'data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()}


class ApiVault:
    """OpenAI key in the Windows DPAPI vault of this user; never in settings, history or logs."""
    def __init__(self,data_dir):self.path=data_dir/'openai-key.dpapi'
    def configured(self):return self.path.exists()
    def save(self,key):
        from backend.security.vault import transform
        key=key.strip()
        if not key.startswith('sk-') or key.startswith('sk-ant-') or not 30<=len(key)<=300:raise ValueError('Chave da OpenAI inválida (começa com sk-).')
        self.path.write_bytes(transform(json.dumps({'key':key}).encode(),True))
    def get(self):
        from backend.security.vault import transform
        return json.loads(transform(self.path.read_bytes(),False).decode())['key']
    def clear(self):self.path.unlink(missing_ok=True)


def install_images(app,auth,store,data_dir,engine):
    from fastapi import Depends,HTTPException
    from pydantic import BaseModel
    images=Images(data_dir,store);app.state.images=images
    class Choice(BaseModel):
        provider:str
        model:str=''
    class Key(BaseModel):
        key:str
    import asyncio
    def guard(fn):
        try:return fn()
        except ValueError as exc:raise HTTPException(409,str(exc))
    @app.get('/images/status',dependencies=[Depends(auth)])
    async def image_status():return await asyncio.to_thread(images.status)
    # Native-only (main process asks the owner first): starts a multi-GB download.
    @app.post('/images/install',dependencies=[Depends(auth)])
    async def image_install():
        if engine.stopped:raise HTTPException(403,'Ações suspensas.')
        return await asyncio.to_thread(guard,images.install)
    @app.post('/images/install/cancel',dependencies=[Depends(auth)])
    async def image_install_cancel():return images.cancel_install()
    @app.post('/images/start',dependencies=[Depends(auth)])
    async def image_start():return await asyncio.to_thread(guard,images.start)
    @app.post('/images/stop',dependencies=[Depends(auth)])
    async def image_stop():return await asyncio.to_thread(images.stop)
    @app.put('/images/provider',dependencies=[Depends(auth)])
    async def image_provider(body:Choice):return guard(lambda:images.choose(body.provider,body.model))
    # Native-only, after the owner confirms in a native dialog.
    @app.put('/credentials/openai',dependencies=[Depends(auth)])
    async def openai_key(body:Key):
        guard(lambda:images.vault.save(body.key));store.audit('openai_key_saved','');return images.status()
    @app.delete('/credentials/openai',dependencies=[Depends(auth)])
    async def openai_key_clear():
        images.vault.clear()
        if images.provider()=='openai':store.set_settings({'image_provider':''})
        return images.status()
    @app.get('/images/{image_id}',dependencies=[Depends(auth)])
    async def image_data(image_id:str):return guard(lambda:images.image(image_id))
    return images
