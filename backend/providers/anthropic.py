import json
import time
import secrets
from datetime import datetime
from pydantic import BaseModel,Field,ConfigDict
import httpx
from backend.providers.ollama import ProviderError

class AnthropicConfig(BaseModel):
    model_config=ConfigDict(extra='forbid')
    enabled:bool=False
    model:str=Field(default='',max_length=100,pattern=r'^[a-zA-Z0-9._:-]*$')
    input_usd_per_million:float=Field(default=0,ge=0,le=1000)
    output_usd_per_million:float=Field(default=0,ge=0,le=1000)
    request_limit_usd:float=Field(default=.10,gt=0,le=100)
    session_limit_usd:float=Field(default=.25,gt=0,le=1000)
    daily_limit_usd:float=Field(default=1,gt=0,le=10000)
    monthly_limit_usd:float=Field(default=5,gt=0,le=100000)

class AnthropicProvider:
    def __init__(self,store,vault):
        self.store,self.vault=store,vault;self.session=secrets.token_hex(16)
        store.db.executescript('CREATE TABLE IF NOT EXISTS cloud_usage(id TEXT PRIMARY KEY,provider TEXT,day TEXT,month TEXT,session TEXT,amount REAL,estimated INTEGER,tokens_in INTEGER,tokens_out INTEGER);')
        store.db.commit()
    def config(self):
        rows=self.store.rows("SELECT value FROM settings WHERE key='anthropic'")
        return AnthropicConfig(**json.loads(rows[0]['value'])) if rows else AnthropicConfig()
    def save(self,body):self.store.set_settings({'anthropic':body.model_dump()});return body.model_dump()
    def status(self):
        config=self.config();available=config.enabled and bool(config.model) and self.vault.configured() and self.vault.validated() and self.vault.model_available(config.model) and config.input_usd_per_million>0 and config.output_usd_per_million>0
        return {'id':'anthropic','name':'Claude · API Anthropic','available':available,'location':'cloud','billing':'api','reason':'API configurada; cobrança por uso e confirmação a cada envio.' if available else 'API desativada ou sem chave/modelo/preços configurados. Assinatura Claude não é usada.'}
    async def verify_key(self):
        try:
            async with httpx.AsyncClient(timeout=15,trust_env=False) as client:
                response=await client.get('https://api.anthropic.com/v1/models',params={'limit':1000},headers={'x-api-key':self.vault.get(),'anthropic-version':'2023-06-01'})
                response.raise_for_status();models=[m['id'] for m in response.json().get('data',[]) if m.get('lifecycle')!='retired']
                self.vault.validate(models)
                return {'configured':True,'verified':bool(models),'models':models,'message':'Chave verificada. Configure um modelo listado e os limites de gasto.' if models else 'Chave salva, mas nenhum modelo disponível foi confirmado.'}
        except (httpx.HTTPError,ValueError,OSError):
            self.vault.validate([])
            return {'configured':True,'verified':False,'models':[],'message':'Chave protegida no Windows, mas autenticação/modelos não foram confirmados. A API permanece indisponível.'}
    def estimate(self,messages):
        config=self.config();input_bound=len(json.dumps(messages,ensure_ascii=False).encode('utf-8'))+1000
        return round((input_bound*config.input_usd_per_million+768*config.output_usd_per_million)/1e6,6)
    def totals(self):
        today=datetime.now().astimezone().strftime('%Y-%m-%d');month=today[:7]
        def amount(where,value):return self.store.rows('SELECT COALESCE(SUM(amount),0) AS amount FROM cloud_usage WHERE '+where+'=?',(value,))[0]['amount']
        return {'session':amount('session',self.session),'daily':amount('day',today),'monthly':amount('month',month),'currency':'USD','estimated':True}
    def reserve(self,messages):
        config=self.config();estimate=self.estimate(messages)
        if not self.status()['available']:raise ProviderError('API Anthropic não configurada.','authentication')
        with self.store.lock:
            totals=self.totals()
            if estimate>config.request_limit_usd or any(totals[key]+estimate>limit for key,limit in [('session',config.session_limit_usd),('daily',config.daily_limit_usd),('monthly',config.monthly_limit_usd)]):
                raise ProviderError('Estimativa excede o orçamento configurado. Nenhum pedido enviado.','budget')
            uid=secrets.token_hex(16);today=datetime.now().astimezone().strftime('%Y-%m-%d')
            self.store.write('INSERT INTO cloud_usage VALUES(?,?,?,?,?,?,?,?,?)',(uid,'anthropic',today,today[:7],self.session,estimate,1,None,None))
            return uid
    async def stream(self,messages,cancel):
        uid=self.reserve(messages);config=self.config();tokens_in=tokens_out=0;complete=False
        payload={'model':config.model,'max_tokens':768,'stream':True,'system':'\n'.join(m['content'] for m in messages if m['role']=='system'),'messages':[m for m in messages if m['role']!='system']}
        # Normalize consecutive same-role entries (e.g. an interrupted previous request).
        normalized=[]
        for msg in payload['messages']:
            if normalized and normalized[-1]['role']==msg['role']:normalized[-1]['content']+='\n\n'+msg['content']
            else:normalized.append(dict(msg))
        payload['messages']=normalized
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(120,connect=10),trust_env=False) as client:
                async with client.stream('POST','https://api.anthropic.com/v1/messages',json=payload,headers={'x-api-key':self.vault.get(),'anthropic-version':'2023-06-01'}) as response:
                    if response.status_code!=200:
                        if response.status_code in (401,403):self.vault.validate([])
                        code='usage_limit' if response.status_code==429 else 'authentication' if response.status_code in (401,403) else 'provider_error'
                        raise ProviderError('A API Anthropic recusou o pedido. Verifique autenticação, disponibilidade e limites.',code)
                    async for line in response.aiter_lines():
                        if cancel.is_set():return
                        if not line.startswith('data: '):continue
                        event=json.loads(line[6:]);kind=event.get('type')
                        if kind=='message_start':tokens_in=event.get('message',{}).get('usage',{}).get('input_tokens',0)
                        elif kind=='content_block_delta' and event.get('delta',{}).get('type')=='text_delta':yield {'message':{'content':event['delta']['text']}}
                        elif kind=='message_delta':tokens_out=event.get('usage',{}).get('output_tokens',tokens_out)
                        elif kind=='error':raise ProviderError('Falha de geração informada pela API Anthropic.','provider_error')
                        elif kind=='message_stop':complete=True;break
            if not complete:raise ProviderError('Resposta da API incompleta. Reserva de orçamento mantida como estimativa.','incomplete')
            amount=(tokens_in*config.input_usd_per_million+tokens_out*config.output_usd_per_million)/1e6
            self.store.write('UPDATE cloud_usage SET amount=?,tokens_in=?,tokens_out=? WHERE id=?',(amount,tokens_in,tokens_out,uid))
            yield {'done':True,'eval_count':tokens_out,'prompt_eval_count':tokens_in}
        except httpx.TimeoutException as exc:raise ProviderError('A API excedeu o tempo de espera.','timeout') from exc
        except (httpx.HTTPError,ValueError,OSError) as exc:raise ProviderError('Falha de comunicação com a API Anthropic.','connection') from exc
