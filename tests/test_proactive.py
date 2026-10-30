import asyncio
from datetime import datetime,timedelta
import pytest
from backend.proactive import parse_schedule,next_run,in_quiet,numbers_ok,Routines,Proactive,PcAlerts
from backend.memory.store import Store
from backend.security.permissions import PermissionEngine

class Clock:
    def __init__(self,moment):self.moment=moment
    def __call__(self):return self.moment

def test_schedules_in_portuguese():
    assert parse_schedule('diário 08:00')=={'kind':'weekly','days':list(range(7)),'time':'08:00'}
    assert parse_schedule('dias úteis 07:30')['days']==[0,1,2,3,4]
    assert parse_schedule('seg,qua,sex 18:00')['days']==[0,2,4]
    assert parse_schedule('a cada 2 horas')=={'kind':'interval','minutes':120}
    for bad in ('quando der','a cada 5 min','xyz 10:00'):
        with pytest.raises(ValueError):parse_schedule(bad)
    thursday=datetime(2026,10,29,19,0)
    assert next_run(parse_schedule('seg,qua 18:00'),thursday)==datetime(2026,11,2,18,0)
    assert next_run(parse_schedule('diário 08:00'),thursday)==datetime(2026,10,30,8,0)

def test_quiet_hours_cross_midnight_and_numbers_come_from_data():
    assert in_quiet(datetime(2026,10,30,23,0),'22:00','08:00') and in_quiet(datetime(2026,10,30,7,59),'22:00','08:00')
    assert not in_quiet(datetime(2026,10,30,8,0),'22:00','08:00')
    data={'clima':{'agora_c':21,'maxima_c':27},'hora':'08:00'}
    assert numbers_ok('São 08:00, 21 graus, máxima de 27.',data) and not numbers_ok('Máxima de 35 graus.',data)

class FakeModel:
    def __init__(self,text):self.text=text;self.calls=0
    async def stream(self,model,messages,cancel,profile=None):
        self.calls+=1;yield {'message':{'content':self.text}};yield {'done':True}

class FakeTools:
    class reminders:
        @staticmethod
        def list():return {'reminders':[{'due':'2026-10-30T15:00:00','text':'ligar pro dentista'}]}

def make(tmp_path,text,moment=datetime(2026,10,30,8,5)):
    store=Store(tmp_path/'s.sqlite3');store.set_settings({'model':'fixture:4b','briefing_enabled':True,'user_name':'Caio'})
    from backend.memory.library import MemoryLibrary
    MemoryLibrary(store)
    notes=[];model=FakeModel(text)
    proactive=Proactive(store,model,PermissionEngine(),FakeTools,None,lambda text,title:notes.append((title,text)),lambda q:{'results':[]},Clock(moment))
    return proactive,store,notes,model

def test_the_briefing_uses_only_facts_and_falls_back_to_a_template(tmp_path):
    proactive,store,notes,model=make(tmp_path,'Bom dia, Caio. Hoje vai fazer 35 graus.')
    old=store.create();store.write("UPDATE conversations SET title='Orçamento do PC',updated='2026-10-29T20:00:00+00:00' WHERE id=?",(old['id'],))
    store.add(old['id'],'assistant','Montamos a lista de peças.');store.write("UPDATE conversations SET updated='2026-10-29T20:00:00+00:00' WHERE id=?",(old['id'],))
    assert proactive.briefing_due()
    text=asyncio.run(proactive.briefing())
    # 35 is not in the data: two tries, then the template built only from the data.
    assert model.calls==2 and '35' not in text and 'ligar pro dentista' in text and 'Orçamento do PC' in text
    assert notes[0][0]=='ALT · Resumo da manhã' and not proactive.briefing_due()
    # "Da última vez" is said once.
    assert 'da_ultima_vez' not in asyncio.run(proactive.briefing_data())[0]
    store.db.close()

def test_checkins_respect_silence_quiet_hours_cap_and_may_stay_silent(tmp_path):
    proactive,store,notes,model=make(tmp_path,'Que tal uma pausa para água?',datetime(2026,10,30,15,0))
    assert asyncio.run(proactive.checkin()) is None  # disabled
    store.set_settings({'proactive_enabled':True,'proactive_daily_cap':1})
    assert asyncio.run(proactive.checkin())=='Que tal uma pausa para água?'
    proactive.last_checkin=0
    assert asyncio.run(proactive.checkin()) is None  # daily cap
    proactive.clock.moment=datetime(2026,10,30,23,0);store.set_settings({'proactive_daily_cap':4});proactive.last_checkin=0
    assert asyncio.run(proactive.checkin()) is None  # quiet hours
    proactive.clock.moment=datetime(2026,10,30,16,0);proactive.last_checkin=0;model.text='NADA'
    assert asyncio.run(proactive.checkin()) is None and len(notes)==1
    store.db.close()

def test_topics_alert_only_when_the_headline_changes(tmp_path):
    proactive,store,notes,model=make(tmp_path,'',datetime(2026,10,30,12,0))
    headline={'title':'Lançamento A'};proactive.search=lambda q:{'results':[dict(headline,url='https://n.example')]}
    store.set_settings({'topics':['RTX 5070']})
    assert asyncio.run(proactive.watch_topics())==[]
    assert asyncio.run(proactive.watch_topics())==[]  # once a day
    proactive.clock.moment+=timedelta(days=1);headline['title']='Preço caiu'
    assert asyncio.run(proactive.watch_topics())==['Novidade sobre RTX 5070: Preço caiu']
    store.db.close()

def test_routines_run_when_due(tmp_path):
    clock=Clock(datetime(2026,10,30,7,0));store=Store(tmp_path/'s.sqlite3');routines=Routines(store,clock)
    routine=routines.create('Água','diário 08:00','Lembre de beber água')
    assert routines.due()==[]
    clock.moment=datetime(2026,10,30,8,1)
    due=routines.due();assert [r['id'] for r in due]==[routine['id']]
    routines.mark_run(due[0],'ok');assert routines.due()==[] and routines.get(routine['id'])['next_run']=='2026-10-31T08:00:00'
    store.db.close()

def test_pc_alerts_need_three_readings_and_cool_down():
    alerts=PcAlerts(lambda:{},lambda *a:None,lambda:False);t=[0]
    clock=lambda:t[0]
    assert alerts.check(95,50,clock)==[] and alerts.check(95,50,clock)==[]
    assert alerts.check(95,50,clock)==['O processador está em 95% há 30 segundos.']
    t[0]=100;assert alerts.check(95,50,clock)==[]
    t[0]=400;assert alerts.check(95,50,clock)
