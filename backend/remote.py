"""The ALT on the owner's iPhone without the App Store: a PWA served by a second, separate local server
(127.0.0.1:47823) that Tailscale publishes only inside the owner's tailnet, with real HTTPS.

Idea from Mark LVI's remote dashboard (QR pairing) and OpenJarvis (PWA + bearer key), without their weak
points: nothing listens beyond 127.0.0.1, no firewall changes, no secret in a URL that reaches a server
(the one-time code travels in the #fragment), per-device tokens stored hashed in an HttpOnly cookie,
rate-limited pairing, Host/Origin checks, and the phone can never run anything by itself: every action is
a card, and PowerShell commands are approved only on the PC."""
import asyncio
import base64
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
from datetime import datetime,timedelta,timezone
from pathlib import Path
from uuid import uuid4
import httpx
from backend.memory.store import now

PORT=47823
CODE_SECONDS=120
TOKEN_DAYS=30
ALPHABET='ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
COOKIE='alt_device'
STATIC={'':'index.html','index.html':'index.html','app.js':'app.js','sw.js':'sw.js','manifest.webmanifest':'manifest.webmanifest',
        'icon-192.png':'icon-192.png','icon-512.png':'icon-512.png','apple-touch-icon.png':'icon-192.png'}
TYPES={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.webmanifest':'application/manifest+json','.png':'image/png'}

def digest(token):return hashlib.sha256(token.encode()).hexdigest()

class Devices:
    def __init__(self,store,clock=time.monotonic):
        self.store,self.clock=store,clock;self.codes={};self.failures=[]
        store.db.executescript('''CREATE TABLE IF NOT EXISTS remote_devices(id TEXT PRIMARY KEY,name TEXT NOT NULL,token_hash TEXT NOT NULL UNIQUE,created TEXT NOT NULL,last_seen TEXT,expires TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS remote_push(device_id TEXT PRIMARY KEY,subscription TEXT NOT NULL);''');store.db.commit()

    def pair_code(self):
        """One code at a time, valid 2 minutes, single use."""
        code=''.join(secrets.choice(ALPHABET) for _ in range(8))
        self.codes={code:self.clock()+CODE_SECONDS}
        return {'code':code,'expires_in':CODE_SECONDS}

    def locked(self):
        recent=[t for t in self.failures if self.clock()-t<600];self.failures=recent
        return len(recent)>=5

    def claim(self,code,name):
        if self.locked():raise PermissionError('Muitas tentativas. Gere um código novo no PC daqui a 10 minutos.')
        code=(code or '').strip().upper();expires=self.codes.get(code)
        if not expires or expires<self.clock():
            self.failures.append(self.clock());raise PermissionError('Código inválido ou expirado. Gere outro no PC.')
        self.codes.pop(code,None)
        token=secrets.token_urlsafe(32);did=str(uuid4())
        until=(datetime.now(timezone.utc)+timedelta(days=TOKEN_DAYS)).isoformat()
        self.store.write('INSERT INTO remote_devices VALUES(?,?,?,?,?,?)',(did,(name or 'iPhone').strip()[:40] or 'iPhone',digest(token),now(),now(),until))
        self.store.audit('remote_device_paired',did)
        return did,token

    def device(self,token):
        if not token:return None
        rows=self.store.rows('SELECT * FROM remote_devices WHERE token_hash=?',(digest(token),))
        if not rows:return None
        row=rows[0];expires=datetime.fromisoformat(row['expires'])
        if expires<datetime.now(timezone.utc):return None
        # Sliding 30 days: in use, it stays paired.
        until=(datetime.now(timezone.utc)+timedelta(days=TOKEN_DAYS)).isoformat()
        self.store.write('UPDATE remote_devices SET last_seen=?,expires=? WHERE id=?',(now(),until,row['id']))
        return row

    def list(self):return self.store.rows('SELECT id,name,created,last_seen,expires FROM remote_devices ORDER BY created DESC')

    def revoke(self,did):
        self.store.write('DELETE FROM remote_devices WHERE id=?',(did,));self.store.write('DELETE FROM remote_push WHERE device_id=?',(did,))
        self.store.audit('remote_device_revoked',did)

class Tailscale:
    """The Tailscale CLI, if installed. Only `serve` (tailnet-only HTTPS), never `funnel` (public)."""
    def __init__(self,runner=subprocess.run):self.runner=runner

    def path(self):
        found=shutil.which('tailscale')
        if found:return found
        default=Path(os.environ.get('ProgramFiles',r'C:\Program Files'))/'Tailscale'/'tailscale.exe'
        return str(default) if default.is_file() else None

    def run(self,*args):
        cli=self.path()
        if not cli:raise ValueError('Instale o Tailscale no PC e no iPhone (tailscale.com/download) e entre com a mesma conta.')
        return self.runner([cli,*args],capture_output=True,text=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))

    def status(self):
        if not self.path():return {'installed':False,'running':False,'host':''}
        try:
            done=self.run('status','--json');data=json.loads(done.stdout or '{}')
            host=(data.get('Self') or {}).get('DNSName','').rstrip('.')
            return {'installed':True,'running':data.get('BackendState')=='Running','host':host}
        except (ValueError,OSError,subprocess.SubprocessError):return {'installed':True,'running':False,'host':''}

    def serve(self,port=PORT):
        done=self.run('serve','--bg','--https=443',f'http://127.0.0.1:{port}')
        if done.returncode:raise ValueError('O Tailscale recusou publicar a ALT. Confira se o HTTPS está ativado no painel do Tailscale (DNS → HTTPS Certificates).')

    def unserve(self):
        try:self.run('serve','--https=443','off')
        except ValueError:pass

class Push:
    """Web Push with VAPID (iOS 16.4+ for PWAs on the Home Screen). Payloads are short; details stay in the app."""
    def __init__(self,directory,store):
        self.directory,self.store=directory,store;self.key_path=directory/'vapid.pem'

    def vapid(self):
        # Vapid02: the 'vapid t=..., k=...' header that aes128gcm push services (Apple included) expect.
        from py_vapid import Vapid02 as Vapid
        if not self.key_path.is_file():
            self.directory.mkdir(parents=True,exist_ok=True)
            key=Vapid();key.generate_keys();key.save_key(str(self.key_path))
        return Vapid.from_file(str(self.key_path))

    def public_key(self):
        from cryptography.hazmat.primitives import serialization
        raw=self.vapid().public_key.public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)
        return base64.urlsafe_b64encode(raw).decode().rstrip('=')

    def subscribe(self,did,subscription):
        endpoint=str((subscription or {}).get('endpoint',''))
        if not endpoint.startswith('https://') or not (subscription.get('keys') or {}).get('p256dh'):raise ValueError('Inscrição de notificação inválida.')
        self.store.write('INSERT OR REPLACE INTO remote_push VALUES(?,?)',(did,json.dumps(subscription)))

    def payload(self,subscription,title,body):
        import http_ece
        from urllib.parse import urlsplit
        keys=subscription['keys'];message=json.dumps({'title':title[:60],'body':body[:180]},ensure_ascii=False).encode()
        salt=os.urandom(16)
        from cryptography.hazmat.primitives.asymmetric import ec
        local=ec.generate_private_key(ec.SECP256R1())
        encrypted=http_ece.encrypt(message,salt=salt,private_key=local,dh=base64.urlsafe_b64decode(keys['p256dh']+'=='),auth_secret=base64.urlsafe_b64decode(keys['auth']+'=='),version='aes128gcm')
        parts=urlsplit(subscription['endpoint'])
        headers=self.vapid().sign({'aud':f'{parts.scheme}://{parts.netloc}','sub':'mailto:alt-ai@users.noreply.github.com','exp':int(time.time())+12*3600})
        headers.update({'Content-Encoding':'aes128gcm','TTL':'3600','Urgency':'normal'})
        return encrypted,headers

    async def send_all(self,title,body):
        rows=self.store.rows('SELECT device_id,subscription FROM remote_push')
        async with httpx.AsyncClient(timeout=10,trust_env=False) as client:
            for row in rows:
                try:
                    data,headers=self.payload(json.loads(row['subscription']),title,body)
                    response=await client.post(json.loads(row['subscription'])['endpoint'],content=data,headers=headers)
                    if response.status_code in (404,410):self.store.write('DELETE FROM remote_push WHERE device_id=?',(row['device_id'],))
                except Exception:continue

def mobile_dir():
    """The PWA files: next to the packaged backend (resources/mobile) or apps/mobile in the repository."""
    if getattr(sys,'frozen',False):return Path(sys.executable).resolve().parent.parent/'mobile'
    return Path(__file__).resolve().parents[1]/'apps'/'mobile'

def gateway_app(main_app,token,devices,push,settings,static_dir=None,port=PORT):
    from fastapi import FastAPI,Request,HTTPException,Depends
    from fastapi.responses import JSONResponse,Response
    static_dir=static_dir or mobile_dir()
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
    internal=lambda:httpx.AsyncClient(transport=httpx.ASGITransport(app=main_app),base_url='http://127.0.0.1',headers={'Authorization':'Bearer '+token},timeout=httpx.Timeout(600))

    def hosts():
        configured=settings().get('remote_host','')
        return {f'127.0.0.1:{port}',f'localhost:{port}','testserver',*([configured] if configured else [])}

    @app.middleware('http')
    async def guard(request,call_next):
        host=request.headers.get('host','')
        if host not in hosts():return JSONResponse({'detail':'Host não autorizado.'},403)
        if request.method not in ('GET','HEAD'):
            origin=request.headers.get('origin')
            allowed={f'https://{h}' for h in hosts()}|{f'http://{h}' for h in hosts() if h.startswith(('127.0.0.1','localhost','testserver'))}
            if origin not in allowed:return JSONResponse({'detail':'Origem não autorizada.'},403)
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff';response.headers['Referrer-Policy']='no-referrer'
        if request.url.path.startswith('/api'):response.headers['Cache-Control']='no-store'
        return response

    def device(request:Request):
        row=devices.device(request.cookies.get(COOKIE,''))
        if not row:raise HTTPException(401,'Pareie este aparelho no PC (Controle e regras → Celular).')
        return row

    @app.post('/pair')
    async def pair(request:Request):
        data=json.loads(await request.body() or b'{}')
        try:did,secret=devices.claim(str(data.get('code','')),str(data.get('name','')))
        except PermissionError as exc:raise HTTPException(403,str(exc))
        response=JSONResponse({'paired':True,'device':did})
        response.set_cookie(COOKIE,secret,max_age=TOKEN_DAYS*86400,httponly=True,secure=True,samesite='strict',path='/')
        return response

    async def call(method,path,**kw):
        async with internal() as client:
            response=await client.request(method,path,**kw)
        if response.status_code>=400:
            try:detail=response.json().get('detail')
            except ValueError:detail=None
            raise HTTPException(response.status_code,detail or 'Falha no PC.')
        return response

    @app.get('/api/me')
    async def me(row=Depends(device)):
        s=settings();return {'device':row['name'],'user_name':s.get('user_name',''),'model':s.get('model','')}

    @app.get('/api/conversations')
    async def conversations(row=Depends(device)):return (await call('GET','/conversations')).json()[:20]

    @app.post('/api/conversations')
    async def new_conversation(row=Depends(device)):return (await call('POST','/conversations')).json()

    @app.get('/api/conversations/{cid}/messages')
    async def messages(cid:str,row=Depends(device)):return (await call('GET',f'/conversations/{cid}/messages')).json()

    @app.get('/api/conversations/{cid}/actions')
    async def actions(cid:str,row=Depends(device)):return (await call('GET',f'/conversations/{cid}/actions')).json()

    @app.post('/api/chat')
    async def chat(request:Request,row=Depends(device)):
        data=json.loads(await request.body() or b'{}')
        model=settings().get('model','')
        if model=='auto' or model.startswith('cloud:'):
            # The cloud consent preview lives on the PC; from the phone the reply stays local.
            choice=await main_app.state.router.choose(str(data.get('content','')))
            model=choice['model'] if not choice['model'].startswith('cloud:') else (await main_app.state.router.local_models())[-1]['name']
        body={'conversation_id':str(data.get('conversation_id','')),'model':model,'content':str(data.get('content',''))[:16000],
              'attachment_ids':list(data.get('attachment_ids') or [])[:4],'origin':'phone'}
        response=await call('POST','/chat',json=body)
        events=[json.loads(line) for line in response.text.splitlines() if line.strip()]
        return {'text':''.join(e.get('text','') for e in events if e.get('type')=='delta'),
                'proposals':[e['proposal'] for e in events if e.get('type')=='tool_proposal'],
                'notices':[e['message'] for e in events if e.get('type') in ('notice','error') and e.get('message')],
                'status':next((e.get('status') for e in events if e.get('type')=='done'),'error')}

    @app.post('/api/actions/{aid}/approve')
    async def approve(aid:str,row=Depends(device)):
        preview=(await call('GET',f'/tools/proposal/{aid}')).json()
        if preview.get('tool')=='run_command' or preview.get('critical'):raise HTTPException(403,'Esta ação só pode ser aprovada no PC.')
        devices.store.audit('remote_action_approved',json.dumps({'action':aid,'device':row['id']}))
        return (await call('POST',f'/tools/approve/{aid}')).json()

    @app.post('/api/actions/{aid}/reject')
    async def reject(aid:str,row=Depends(device)):return (await call('POST',f'/tools/reject/{aid}')).json()

    @app.post('/api/transcribe')
    async def transcribe(request:Request,row=Depends(device)):
        return (await call('POST','/voice/transcribe',content=await request.body(),headers={'Content-Type':'application/octet-stream'})).json()

    @app.post('/api/attachments')
    async def attach(request:Request,row=Depends(device)):
        return (await call('POST','/attachments',content=await request.body(),headers={'Content-Type':'application/octet-stream','X-Alt-Name':request.headers.get('x-alt-name','')})).json()

    @app.post('/api/speak')
    async def speak(request:Request,row=Depends(device)):
        """The reply in the Dora voice as WAV, played on the phone."""
        import io,wave,numpy as np
        text=str(json.loads(await request.body() or b'{}').get('text',''))[:800]
        from backend.voice.text import speakable
        text=speakable(text)
        if not text:raise HTTPException(400,'Nada para falar.')
        samples,rate=await asyncio.to_thread(main_app.state.speaker.synth,text)
        buffer=io.BytesIO()
        with wave.open(buffer,'wb') as out:
            out.setnchannels(1);out.setsampwidth(2);out.setframerate(rate);out.writeframes((np.clip(samples,-1,1)*32767).astype('<i2').tobytes())
        return Response(buffer.getvalue(),media_type='audio/wav')

    @app.get('/api/push/key')
    async def push_key(row=Depends(device)):return {'key':push.public_key()}

    @app.post('/api/push/subscribe')
    async def push_subscribe(request:Request,row=Depends(device)):
        push.subscribe(row['id'],json.loads(await request.body() or b'{}'));return {'ok':True}

    @app.delete('/api/session')
    async def logout(row=Depends(device)):
        devices.revoke(row['id']);response=JSONResponse({'ok':True});response.delete_cookie(COOKIE,path='/');return response

    # Registered last so it never shadows the /api routes.
    @app.get('/{name:path}')
    async def files(name:str):
        if name.startswith('api/'):raise HTTPException(404,'Não encontrado.')
        target=STATIC.get(name)
        if not target or not (static_dir/target).is_file():raise HTTPException(404,'Não encontrado.')
        headers={'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"}
        if target=='sw.js':headers['Service-Worker-Allowed']='/'
        return Response((static_dir/target).read_bytes(),media_type=TYPES[Path(target).suffix],headers=headers)

    return app

class RemoteManager:
    """Starts and stops the gateway server and the Tailscale publication, on the owner's request."""
    def __init__(self,main_app,token,store,data_dir,tailscale=None):
        self.store=store;self.devices=Devices(store);self.push=Push(data_dir/'remote',store);self.tailscale=tailscale or Tailscale()
        self.app=gateway_app(main_app,token,self.devices,self.push,store.settings);self.server=None;self.task=None

    async def start_server(self):
        if self.task and not self.task.done():return
        import uvicorn
        self.server=uvicorn.Server(uvicorn.Config(self.app,host='127.0.0.1',port=PORT,log_level='warning',access_log=False))
        self.task=asyncio.get_event_loop().create_task(self.server.serve())

    async def stop_server(self):
        if self.server:self.server.should_exit=True
        if self.task:
            try:await asyncio.wait_for(self.task,5)
            except (asyncio.TimeoutError,Exception):pass
        self.server=self.task=None

    def status(self):
        tailscale=self.tailscale.status();enabled=bool(self.store.settings().get('remote_enabled'))
        host=self.store.settings().get('remote_host','')
        return {**tailscale,'enabled':enabled,'url':f'https://{host}/' if enabled and host else '','devices':self.devices.list(),'serving':bool(self.task and not self.task.done())}

    async def enable(self):
        status=self.tailscale.status()
        if not status['installed']:raise ValueError('Instale o Tailscale no PC e no iPhone (tailscale.com/download) e entre com a mesma conta.')
        if not status['running'] or not status['host']:raise ValueError('Abra o Tailscale no PC e entre na sua conta.')
        await self.start_server()
        await asyncio.to_thread(self.tailscale.serve)
        self.store.set_settings({'remote_enabled':True,'remote_host':status['host']})
        self.store.audit('remote_enabled',status['host'])
        return self.status()

    async def disable(self):
        await asyncio.to_thread(self.tailscale.unserve);await self.stop_server()
        self.store.set_settings({'remote_enabled':False});self.store.audit('remote_disabled','')
        return self.status()

    def pair(self):
        host=self.store.settings().get('remote_host','')
        if not host or not self.store.settings().get('remote_enabled'):raise ValueError('Ligue o acesso pelo celular primeiro.')
        code=self.devices.pair_code();url=f'https://{host}/#pair={code["code"]}'
        import segno
        return {**code,'url':url,'qr':segno.make(url,error='m').svg_data_uri(scale=6,dark='#111',light='#fff')}
