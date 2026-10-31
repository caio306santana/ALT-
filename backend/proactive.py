"""The ALT speaking first, at the right time: routines, the morning briefing, check-ins, watched topics
and PC alerts. Everything is opt-in and respects quiet hours and a daily limit.

Ideas: OpenJarvis scheduler (once/interval/daily, run log) and morning digest ("only facts from the
data", self-check, then speech); Mark LVI's check-in rules (15 min of silence, 20 min cooldown, never
interrupt, allowed to stay silent), topic watcher that alerts only when the top headline changes, and
the system monitor (3 high readings in a row, 5 min cooldown per metric)."""
import asyncio
import hashlib
import json
import re
import threading
import time
from datetime import datetime,timedelta
from uuid import uuid4
import httpx
from backend.memory.store import now

WEATHER={0:'céu limpo',1:'quase limpo',2:'parcialmente nublado',3:'nublado',45:'neblina',48:'neblina',51:'garoa fraca',53:'garoa',55:'garoa forte',
    61:'chuva fraca',63:'chuva',65:'chuva forte',66:'chuva congelante',67:'chuva congelante',71:'neve fraca',73:'neve',75:'neve forte',80:'pancadas de chuva',
    81:'pancadas de chuva',82:'pancadas fortes',95:'trovoadas',96:'trovoadas com granizo',99:'trovoadas com granizo'}
DAYS={'seg':0,'ter':1,'qua':2,'qui':3,'sex':4,'sáb':5,'sab':5,'dom':6}
BRIEFING_PROMPT=('Você escreve o resumo da manhã da ALT para ser lido em voz alta. Use SOMENTE os fatos do JSON abaixo; '
    'pule em silêncio o que estiver vazio. Comece com "Bom dia" e o nome, se houver. No máximo 120 palavras, sem markdown, '
    'sem emoji, sem listas, frases curtas, em português do Brasil. Não invente números, horários nem notícias.')
CHECKIN_PROMPT=('Você é a ALT e pode puxar uma conversa curta e útil com o usuário agora. Com base nos dados abaixo, '
    'escreva no máximo duas frases naturais (um lembrete gentil, uma pergunta sobre um projeto, uma sugestão de pausa). '
    'Se não houver nada realmente útil, responda exatamente NADA.')

def hhmm(text):
    match=re.fullmatch(r'([01]?\d|2[0-3]):([0-5]\d)',(text or '').strip())
    if not match:raise ValueError('Use o horário no formato HH:MM.')
    return int(match.group(1)),int(match.group(2))

def in_quiet(moment,start,end):
    start,end=hhmm(start),hhmm(end);value=(moment.hour,moment.minute)
    return start<=value<end if start<end else value>=start or value<end

def parse_schedule(text):
    """'diário 08:00', 'dias úteis 07:30', 'seg,qua,sex 18:00', 'a cada 60 min', 'uma vez 2026-10-30T15:00'."""
    text=(text or '').strip().lower()
    if match:=re.fullmatch(r'a cada (\d{1,4}) ?(min|minutos|h|horas)',text):
        minutes=int(match.group(1))*(60 if match.group(2).startswith('h') else 1)
        if not 15<=minutes<=7*24*60:raise ValueError('Intervalo entre 15 minutos e 7 dias.')
        return {'kind':'interval','minutes':minutes}
    if match:=re.fullmatch(r'uma vez (\S+)',text):
        return {'kind':'once','at':datetime.fromisoformat(match.group(1)).replace(second=0,microsecond=0).isoformat()}
    if match:=re.fullmatch(r'(diário|diario|todo dia|todos os dias|dias úteis|dias uteis|[a-zá,\s]+?)\s+(\d{1,2}:\d{2})',text):
        days,clock=match.group(1).strip(),match.group(2);hhmm(clock)
        if days in ('diário','diario','todo dia','todos os dias'):weekdays=list(range(7))
        elif days in ('dias úteis','dias uteis'):weekdays=[0,1,2,3,4]
        else:
            parts=[p.strip()[:3] for p in days.split(',') if p.strip()]
            if not parts or any(p not in DAYS for p in parts):raise ValueError('Dias: seg, ter, qua, qui, sex, sáb, dom.')
            weekdays=sorted({DAYS[p] for p in parts})
        return {'kind':'weekly','days':weekdays,'time':clock}
    raise ValueError('Agenda não reconhecida. Exemplos: "diário 08:00", "seg,qua 18:00", "a cada 60 min".')

def next_run(schedule,after):
    if schedule['kind']=='interval':return after+timedelta(minutes=schedule['minutes'])
    if schedule['kind']=='once':
        at=datetime.fromisoformat(schedule['at']);return at if at>after else None
    hour,minute=hhmm(schedule['time'])
    for offset in range(8):
        candidate=(after+timedelta(days=offset)).replace(hour=hour,minute=minute,second=0,microsecond=0)
        if candidate>after and candidate.weekday() in schedule['days']:return candidate
    return None

def numbers_ok(text,data):
    """Every number in the briefing must come from the data (OpenJarvis self-check, made deterministic)."""
    source=json.dumps(data,ensure_ascii=False)
    return all(n in source for n in re.findall(r'\d+',text))

class Routines:
    def __init__(self,store,clock=datetime.now):
        self.store,self.clock=store,clock
        store.db.execute('CREATE TABLE IF NOT EXISTS routines(id TEXT PRIMARY KEY,name TEXT NOT NULL,schedule TEXT NOT NULL,prompt TEXT NOT NULL,enabled INTEGER NOT NULL,last_run TEXT,next_run TEXT,created TEXT NOT NULL)')
        store.db.execute('CREATE TABLE IF NOT EXISTS routine_runs(id TEXT PRIMARY KEY,routine_id TEXT NOT NULL,started TEXT NOT NULL,result TEXT NOT NULL)');store.db.commit()

    def create(self,name,schedule_text,prompt):
        schedule=parse_schedule(schedule_text);name=(name or prompt or '').strip()[:80];prompt=(prompt or '').strip()[:1000]
        if not prompt:raise ValueError('Diga o que a rotina deve fazer.')
        due=next_run(schedule,self.clock())
        if due is None:raise ValueError('Esse horário já passou.')
        rid=str(uuid4());self.store.write('INSERT INTO routines VALUES(?,?,?,?,1,NULL,?,?)',(rid,name,json.dumps(schedule),prompt,due.isoformat(),now()))
        return self.get(rid)

    def get(self,rid):
        rows=self.store.rows('SELECT * FROM routines WHERE id=?',(rid,))
        if not rows:raise ValueError('Rotina não encontrada.')
        row=rows[0];row['schedule']=json.loads(row['schedule']);row['enabled']=bool(row['enabled']);return row

    def list(self):return [self.get(r['id']) for r in self.store.rows('SELECT id FROM routines ORDER BY created')]
    def delete(self,rid):self.store.write('DELETE FROM routines WHERE id=?',(rid,))
    def toggle(self,rid,enabled):self.store.write('UPDATE routines SET enabled=? WHERE id=?',(int(enabled),rid))

    def due(self):
        moment=self.clock().isoformat()
        return [self.get(r['id']) for r in self.store.rows('SELECT id FROM routines WHERE enabled=1 AND next_run IS NOT NULL AND next_run<=?',(moment,))]

    def mark_run(self,routine,result):
        moment=self.clock();following=next_run(routine['schedule'],moment)
        self.store.write('UPDATE routines SET last_run=?,next_run=? WHERE id=?',(moment.isoformat(),following.isoformat() if following else None,routine['id']))
        self.store.write('INSERT INTO routine_runs VALUES(?,?,?,?)',(str(uuid4()),routine['id'],moment.isoformat(),result[:2000]))

async def weather(city,cache={}):
    """Open-Meteo (free, no key). Only called when the owner set a city for the briefing."""
    key=(city,datetime.now().strftime('%Y%m%d%H'))
    if key in cache:return cache[key]
    async with httpx.AsyncClient(timeout=10,trust_env=False) as client:
        place=(await client.get('https://geocoding-api.open-meteo.com/v1/search',params={'name':city,'count':1,'language':'pt'})).json().get('results') or []
        if not place:return None
        forecast=(await client.get('https://api.open-meteo.com/v1/forecast',params={'latitude':place[0]['latitude'],'longitude':place[0]['longitude'],
            'current':'temperature_2m,weather_code','daily':'temperature_2m_max,temperature_2m_min,precipitation_probability_max','timezone':'auto','forecast_days':1})).json()
    current,daily=forecast.get('current',{}),forecast.get('daily',{})
    result={'cidade':place[0]['name'],'agora_c':round(current.get('temperature_2m',0)),'condicao':WEATHER.get(current.get('weather_code'),'tempo variável'),
        'maxima_c':round((daily.get('temperature_2m_max') or [0])[0]),'minima_c':round((daily.get('temperature_2m_min') or [0])[0]),
        'chuva_pct':(daily.get('precipitation_probability_max') or [None])[0]}
    cache.clear();cache[key]=result
    return result

class Proactive:
    def __init__(self,store,ollama,engine,tools,speaker,notify,search,clock=datetime.now):
        self.store,self.ollama,self.engine,self.tools,self.speaker,self.notify,self.search,self.clock=store,ollama,engine,tools,speaker,notify,search,clock
        self.routines=Routines(store,clock);self.task=None;self.last_checkin=0.0

    def settings(self):return self.store.settings()

    def state(self,key,default=None):return self.settings().get('proactive_state',{}).get(key,default)
    def set_state(self,**values):
        current=dict(self.settings().get('proactive_state') or {});current.update(values);self.store.set_settings({'proactive_state':current})

    def quiet(self):
        s=self.settings()
        try:return in_quiet(self.clock(),s.get('quiet_start','22:00'),s.get('quiet_end','08:00'))
        except ValueError:return False

    async def generate(self,system,content,limit=220):
        """One short text from the selected local model; None when there is none (cloud never runs alone)."""
        model=self.settings().get('model','')
        if model=='auto':
            from backend.routing import default_local
            try:model=default_local(await self.ollama.models())
            except Exception:return None
        if not model or model.startswith('cloud:'):return None
        from backend.monitoring.performance import performance_profile
        profile=performance_profile(self.settings().get('performance','auto'),self.engine.game_mode);profile['options']['num_predict']=limit
        text=''
        from backend.providers.ollama import ProviderError
        try:
            async for chunk in self.ollama.stream(model,[{'role':'system','content':system},{'role':'user','content':content}],asyncio.Event(),profile):
                text+=chunk.get('message',{}).get('content','')
        except ProviderError:return None  # the caller uses its fact-only template
        return re.sub(r'<think>.*?</think>','',text,flags=re.S).strip()

    def deliver(self,title,text,speak=True):
        """A conversation entry, a Windows notification and, if chosen, the voice."""
        conversation=self.store.create();self.store.write('UPDATE conversations SET title=? WHERE id=?',(title,conversation['id']))
        self.store.add(conversation['id'],'assistant',text,'alt-proativa','complete')
        self.notify(text,'ALT · '+title)
        if speak and self.settings().get('briefing_voice',True) and self.speaker:self.speaker.say(text)
        self.store.audit('proactive_'+title.lower().replace(' ','_')[:30],conversation['id'])
        return conversation['id']

    def last_session(self):
        """The most recent conversation before today, said once ("da última vez")."""
        today=self.clock().date().isoformat()
        rows=self.store.rows("SELECT id,title FROM conversations WHERE updated<? ORDER BY updated DESC LIMIT 5",(today,))
        for row in rows:
            if row['id']==self.state('last_session_said'):return None
            messages=[m for m in self.store.messages(row['id']) if m['role']=='assistant' and m['status']=='complete' and m['content'].strip()]
            if messages:return {'id':row['id'],'assunto':row['title'],'ultima_resposta':messages[-1]['content'][:200]}
        return None

    async def briefing_data(self):
        s=self.settings();moment=self.clock()
        data={'nome':s.get('user_name',''),'data':moment.strftime('%d/%m/%Y'),'hora':moment.strftime('%H:%M')}
        if s.get('weather_city'):
            try:data['clima']=await weather(s['weather_city'])
            except (httpx.HTTPError,ValueError):pass
        today=moment.date().isoformat()
        try:data['lembretes_hoje']=[{'hora':r['due'][11:16],'texto':r['text']} for r in self.tools.reminders.list().get('reminders',[]) if r['due'].startswith(today)]
        except Exception:pass
        last=self.last_session()
        if last:data['da_ultima_vez']={k:v for k,v in last.items() if k!='id'}
        news=[v for v in (self.state('topics') or {}).values() if v.get('new')]
        if news:data['noticias_dos_topicos']=[{'topico':n['topic'],'manchete':n['title']} for n in news[:3]]
        return data,last

    async def briefing(self,force=False):
        data,last=await self.briefing_data()
        text=await self.generate(BRIEFING_PROMPT,json.dumps(data,ensure_ascii=False))
        if text and not numbers_ok(text,data):
            text=await self.generate(BRIEFING_PROMPT+' Use apenas números que aparecem no JSON.',json.dumps(data,ensure_ascii=False))
        if not text or not numbers_ok(text,data):text=self.template(data)
        self.deliver('Resumo da manhã',text)
        self.set_state(briefing_day=self.clock().date().isoformat(),last_session_said=last['id'] if last else self.state('last_session_said'),
            topics={k:{**v,'new':False} for k,v in (self.state('topics') or {}).items()})
        return text

    def template(self,data):
        parts=[f"Bom dia{', '+data['nome'] if data.get('nome') else ''}. São {data['hora']}."]
        if c:=data.get('clima'):parts.append(f"Em {c['cidade']}, {c['condicao']}, {c['agora_c']} graus agora, máxima de {c['maxima_c']}.")
        for r in data.get('lembretes_hoje',[])[:3]:parts.append(f"Lembrete às {r['hora']}: {r['texto']}.")
        if l:=data.get('da_ultima_vez'):parts.append(f"Da última vez falamos sobre {l['assunto']}.")
        for n in data.get('noticias_dos_topicos',[]):parts.append(f"Novidade sobre {n['topico']}: {n['manchete']}.")
        return ' '.join(parts)

    def briefing_due(self):
        s=self.settings()
        if not s.get('briefing_enabled'):return False
        moment=self.clock()
        try:hour,minute=hhmm(s.get('briefing_time','08:00'))
        except ValueError:return False
        # At the time, or at the first moment the PC is on after it, once a day.
        return (moment.hour,moment.minute)>=(hour,minute) and self.state('briefing_day')!=moment.date().isoformat()

    def last_activity(self):
        rows=self.store.rows("SELECT MAX(created) AS last FROM messages WHERE role='user'")
        try:return datetime.fromisoformat(rows[0]['last']).astimezone().replace(tzinfo=None) if rows and rows[0]['last'] else None
        except ValueError:return None

    async def checkin(self):
        """Mark LVI's rules plus quiet hours and a daily cap; the model may decide to stay silent."""
        s=self.settings()
        if not s.get('proactive_enabled') or self.quiet() or self.engine.active or (self.speaker and self.speaker.speaking):return None
        moment=self.clock();last=self.last_activity()
        if last and moment-last<timedelta(minutes=15):return None
        if time.monotonic()-self.last_checkin<20*60:return None
        today=moment.date().isoformat();count=self.state('checkins',{}).get(today,0)
        if count>=int(s.get('proactive_daily_cap',4)):return None
        self.last_checkin=time.monotonic()
        memories=[r['title'] for r in self.store.rows('SELECT title FROM memories WHERE enabled=1 ORDER BY updated DESC LIMIT 5')]
        recent=self.store.rows('SELECT title FROM conversations ORDER BY updated DESC LIMIT 3')
        context={'hora':moment.strftime('%H:%M'),'dia_da_semana':['segunda','terça','quarta','quinta','sexta','sábado','domingo'][moment.weekday()],
            'nome':s.get('user_name',''),'memorias':memories,'conversas_recentes':[r['title'] for r in recent]}
        text=await self.generate(CHECKIN_PROMPT,json.dumps(context,ensure_ascii=False),120)
        if not text or text.strip().upper().startswith('NADA'):return None
        self.set_state(checkins={today:count+1})
        self.deliver('Lembrete da ALT',text)
        return text

    async def watch_topics(self):
        """Once a day per topic; alert only when the top headline changed."""
        topics=[t for t in self.settings().get('topics',[]) if t.strip()][:10]
        if not topics:return []
        state=dict(self.state('topics') or {});today=self.clock().date().isoformat();alerts=[]
        for topic in topics:
            entry=state.get(topic) or {}
            if entry.get('checked')==today:continue
            try:result=await asyncio.to_thread(self.search,topic+' notícias')
            except Exception:continue
            top=(result.get('results') or [{}])[0];title=(top.get('title') or '').strip()
            digest=hashlib.sha256(title.encode()).hexdigest()[:16]
            changed=bool(title) and entry.get('hash') not in (None,digest)
            state[topic]={'topic':topic,'title':title,'url':top.get('url',''),'hash':digest,'checked':today,'new':changed or entry.get('new',False)}
            if changed:alerts.append(f'Novidade sobre {topic}: {title}')
        self.set_state(topics=state)
        if alerts and not self.quiet():self.deliver('Tópicos',' '.join(alerts[:3]),speak=False)
        return alerts

    async def run_routine(self,routine):
        text=await self.generate('Você é a ALT executando uma rotina agendada pelo usuário. Responda em até 80 palavras, sem markdown.',routine['prompt'])
        text=text or f"Rotina \"{routine['name']}\": {routine['prompt']}"
        self.routines.mark_run(routine,text)
        if not self.quiet():self.deliver('Rotina: '+routine['name'][:40],text)
        return text

    async def tick(self):
        if self.engine.stopped:return
        if self.briefing_due():await self.briefing()
        for routine in self.routines.due():await self.run_routine(routine)
        await self.watch_topics()
        await self.checkin()

    async def loop(self):
        while True:
            await asyncio.sleep(60)
            try:await self.tick()
            except Exception:self.store.audit('proactive_error','tick')

    def start(self):
        if self.task is None:self.task=asyncio.get_event_loop().create_task(self.loop())

class PcAlerts:
    """CPU or memory above 90% three readings in a row (every 10 s); 5 minutes between alerts per metric."""
    def __init__(self,settings,notify,quiet):self.settings,self.notify,self.quiet=settings,notify,quiet;self.high={};self.sent={};self.closed=threading.Event()
    def check(self,cpu,ram,clock=time.monotonic):
        alerts=[]
        for metric,value,label in (('cpu',cpu,'O processador'),('ram',ram,'A memória')):
            self.high[metric]=self.high.get(metric,0)+1 if value>=90 else 0
            if self.high[metric]>=3 and clock()-self.sent.get(metric,-1e9)>=300:
                self.sent[metric]=clock();alerts.append(f'{label} está em {value:.0f}% há 30 segundos.')
        return alerts
    def start(self):
        def loop():
            import psutil
            psutil.cpu_percent(None)
            while not self.closed.wait(10):
                try:
                    if not self.settings().get('pc_alerts') or self.quiet():self.high.clear();continue
                    for alert in self.check(psutil.cpu_percent(None),psutil.virtual_memory().percent):self.notify(alert,'ALT · PC')
                except Exception:pass
        self.thread=threading.Thread(target=loop,daemon=True,name='pc-alerts');self.thread.start()

    def stop(self):
        self.closed.set()
        if getattr(self,'thread',None):self.thread.join(timeout=2)
