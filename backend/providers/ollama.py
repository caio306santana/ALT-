import asyncio
import json
import httpx

class ProviderError(Exception):
    def __init__(self, message, code='provider_error'):
        super().__init__(message)
        self.code = code

async def cancellable(source, cancel):
    """Cancel even while connecting/loading a model, before response headers arrive."""
    iterator = source.__aiter__()
    try:
        while not cancel.is_set():
            pending = asyncio.create_task(anext(iterator))
            stopped = asyncio.create_task(cancel.wait())
            try:
                ready,_ = await asyncio.wait([pending,stopped],return_when=asyncio.FIRST_COMPLETED)
                if stopped in ready: return
                try: yield pending.result()
                except StopAsyncIteration: return
            finally:
                for task in (pending,stopped):
                    if not task.done(): task.cancel()
                await asyncio.gather(pending,stopped,return_exceptions=True)
    finally:
        await iterator.aclose()

class Ollama:
    # Fixed loopback endpoint. The renderer cannot supply a URL or credentials.
    base_url = 'http://127.0.0.1:11434'

    async def models(self):
        try:
            async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
                res = await client.get(self.base_url+'/api/tags')
                res.raise_for_status()
                return res.json().get('models', [])
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError('Ollama não está acessível em 127.0.0.1:11434. Instale ou abra o Ollama.', 'connection') from exc

    async def running(self):
        try:
            async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
                res = await client.get(self.base_url+'/api/ps')
                res.raise_for_status()
                return res.json().get('models', [])
        except (httpx.HTTPError, ValueError):
            return None

    async def pull(self, model):
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(600,connect=10),trust_env=False) as client:
                async with client.stream('POST',self.base_url+'/api/pull',json={'model':model,'stream':True}) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            data=json.loads(line)
                            if data.get('error'): raise ProviderError('Ollama informou falha ao baixar o modelo. Verifique conexão e espaço livre.','download')
                            yield data
        except (httpx.HTTPError,ValueError) as exc:
            raise ProviderError('Falha no download. Verifique se o Ollama está aberto e tente novamente.','download') from exc

    async def unload(self,model):
        entries=await self.models()
        if not any(m.get('name')==model and not m.get('remote_host') and not m.get('remote_model') and 'cloud' not in model.lower() for m in entries):raise ProviderError('Modelo local não disponível.','connection')
        async with httpx.AsyncClient(timeout=30,trust_env=False) as client:
            response=await client.post(self.base_url+'/api/generate',json={'model':model,'keep_alive':0,'stream':False})
            response.raise_for_status()

    async def stream(self, model, messages, cancel, profile=None):
        timeout = httpx.Timeout(connect=5, read=300, write=30, pool=5)
        try:
            async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
                profile=profile or {'options':{'num_ctx':8192,'num_predict':4096},'keep_alive':'5m'}
                payload={
                    'model':model, 'messages':messages, 'stream':True,
                    'options':profile['options'], 'keep_alive':profile['keep_alive']
                }
                if 'qwen3.5' in model.lower(): payload['think']=False
                if profile.get('tools'):payload['tools']=profile['tools']
                if profile.get('format'):payload['format']=profile['format']
                async with client.stream('POST', self.base_url+'/api/chat', json=payload) as response:
                    if response.status_code != 200:
                        await response.aread()
                        raise ProviderError('Ollama recusou a geração. Confira o modelo e os logs locais.', 'inference')
                    iterator = response.aiter_lines().__aiter__()
                    while not cancel.is_set():
                        pending = asyncio.create_task(anext(iterator))
                        stopped = asyncio.create_task(cancel.wait())
                        try:
                            ready,_ = await asyncio.wait([pending,stopped],return_when=asyncio.FIRST_COMPLETED)
                            if stopped in ready:
                                return
                            try:
                                line = pending.result()
                            except StopAsyncIteration:
                                return
                            if line:
                                chunk = json.loads(line)
                                if chunk.get('error'):
                                    raise ProviderError('Falha de inferência informada pelo Ollama.', 'inference')
                                yield chunk
                        finally:
                            for task in (pending,stopped):
                                if not task.done():
                                    task.cancel()
                            await asyncio.gather(pending,stopped,return_exceptions=True)
        except httpx.TimeoutException as exc:
            raise ProviderError('Ollama excedeu o tempo de espera. A resposta parcial foi preservada.', 'timeout') from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError('A conexão com o Ollama foi interrompida.', 'connection') from exc

    async def embed(self,texts):
        # Fixed, local-only model; no automatic download or cloud fallback.
        entries=await self.models()
        model=next((m['name'] for m in entries if m.get('name','').split(':')[0]=='embeddinggemma' and not m.get('remote_host')),None)
        if not model:raise ValueError('Instale EmbeddingGemma para ativar a busca semântica local.')
        async with httpx.AsyncClient(timeout=120,trust_env=False) as client:
            response=await client.post(self.base_url+'/api/embed',json={'model':model,'input':texts,'truncate':False,'keep_alive':0})
            response.raise_for_status()
            vectors=response.json().get('embeddings',[])
            if len(vectors)!=len(texts):raise ValueError('O modelo não retornou todos os vetores.')
            return vectors
