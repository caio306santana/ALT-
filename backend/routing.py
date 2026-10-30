"""Automatic model choice for the owner's hybrid setup: the small local model for simple requests, the
larger one for medium ones, and Claude for hard ones only when it is configured. The cloud is never
used silently: the desktop still shows the preview and asks for consent before anything is sent.

From OpenJarvis (learning/routing/complexity.py, router.py, learned_router.py): a 0-1 score from cheap
rules (length, code/math, multi-step reasoning, several questions, creative writing), score bands mapped
to models, and per-band success counts that override the default after 5 samples."""
import re

RULES=[
    (.3,re.compile(r'(?i)```|\b(código|script|função|python|javascript|typescript|sql|regex|bug|erro de compila|stack trace|algoritmo|equação|derivada|integral|matriz|probabilidade)\b')),
    (.25,re.compile(r'(?i)\b(passo a passo|compare|comparar|analise|analisar|planeje|planejar|estratégia|prós e contras|vantagens e desvantagens|explique detalhadamente|por que .{0,40}\?|justifique|avalie|resuma e|em detalhes)\b')),
    (.15,re.compile(r'(?i)\b(escreva um|escreva uma|crie uma história|poema|roteiro|redação|letra de música|conto)\b')),
]
ACTION=re.compile(r'(?i)^\s*(abr[ae]|abre|fech[ae]|toca|pausa|aumenta|abaixa|pesquis[ae]|procura|lembr[ae]|olha|desfaz|rode|executa|volume|brilho)\b')

def complexity(text):
    """0-1 score and the reasons behind it."""
    text=text or '';score=0.0;reasons=[]
    if len(text)>400:score+=.2;reasons.append('pedido longo')
    for weight,rule in RULES:
        if rule.search(text):score+=weight;reasons.append({RULES[0][1]:'código ou matemática',RULES[1][1]:'raciocínio em etapas',RULES[2][1]:'texto criativo'}[rule])
    if text.count('?')>2:score+=.15;reasons.append('várias perguntas')
    return round(min(score,1.0),2),reasons

def band(score):return 'simples' if score<.25 else 'médio' if score<.55 else 'complexo'

class ModelRouter:
    def __init__(self,store,ollama,anthropic,engine,gpu):
        self.store,self.ollama,self.anthropic,self.engine,self.gpu=store,ollama,anthropic,engine,gpu
        store.db.execute('CREATE TABLE IF NOT EXISTS routing_stats(band TEXT NOT NULL,model TEXT NOT NULL,ok INTEGER NOT NULL,total INTEGER NOT NULL,PRIMARY KEY(band,model))');store.db.commit()

    async def local_models(self):
        rows=[m for m in await self.ollama.models() if not m.get('remote_host') and not m.get('remote_model') and 'cloud' not in m.get('name','').lower() and not m.get('name','').startswith('embeddinggemma')]
        return sorted(rows,key=lambda m:m.get('size',0))

    def stats(self,name):
        rows=self.store.rows('SELECT model,ok,total FROM routing_stats WHERE band=?',(name,))
        return {r['model']:(r['ok'],r['total']) for r in rows}

    def record(self,name,model,ok):
        self.store.write('INSERT INTO routing_stats VALUES(?,?,?,1) ON CONFLICT(band,model) DO UPDATE SET ok=ok+excluded.ok,total=total+1',(name,model,int(bool(ok))))

    async def choose(self,content):
        local=await self.local_models()
        if not local:return {'model':'','reason':'Nenhum modelo local instalado.','score':0,'band':'simples'}
        small,large=local[0]['name'],local[-1]['name']
        score,reasons=complexity(content);name=band(score)
        if ACTION.search(content or '') and name!='complexo':name,reasons='simples',['ação direta']
        if self.engine.game_mode:return {'model':small,'reason':'Game Mode: o modelo menor, no processador.','score':score,'band':name}
        if self.gpu and self.gpu.state().get('busy'):return {'model':small,'reason':'Placa de vídeo ocupada: o modelo menor.','score':score,'band':name}
        cloud=self.store.settings().get('auto_cloud',True) and self.anthropic.status()['available']
        choice={'simples':small,'médio':large,'complexo':'cloud:anthropic' if cloud else large}[name]
        why=', '.join(reasons) or 'conversa simples'
        # Learned override: with 5+ samples, a clearly better option for this band wins.
        stats=self.stats(name)
        def rate(model):
            ok,total=stats.get(model,(0,0));return ok/total if total>=5 else None
        current=rate(choice)
        for alternative in {small,large,'cloud:anthropic' if cloud else large}-{choice}:
            alt=rate(alternative)
            if alt is not None and current is not None and alt-current>=.2:choice=alternative;why+=f'; histórico melhor com {alternative}'
        label={small:'modelo menor',large:'modelo maior','cloud:anthropic':'Claude (pede sua aprovação)'}.get(choice,choice)
        return {'model':choice,'reason':f'{label}: {why}','score':score,'band':name}
