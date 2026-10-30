import time
import numpy as np
from backend.voice.loop import Vad,VoiceLoop,hotkey_codes,RATE,CHUNK,AWAKE_SECONDS
from backend.voice.text import SpeechText,speakable
from test_features import fixture_client
from test_backend import conversation

def chunks(seconds,amplitude):
    total=int(seconds*RATE);t=np.arange(total)/RATE
    signal=(np.sin(2*np.pi*220*t)*amplitude*32767).astype(np.int16)
    return [signal[i:i+CHUNK] for i in range(0,total-CHUNK+1,CHUNK)]

def test_vad_ends_after_silence_and_gives_up_without_speech():
    vad=Vad();verdicts=[vad.update(c) for c in chunks(1,.2)+chunks(1,0)]
    assert 'speaking' in verdicts and verdicts[-1]=='end'
    vad=Vad();assert [vad.update(c) for c in chunks(7,0)][-1]=='nothing'

def test_reasoning_split_across_chunks_is_never_spoken_and_decimals_survive():
    text=SpeechText();said=[]
    for delta in ['<thi','nk>plano secreto</th','ink>Abrindo o Spotify. O valor é 3.14 ','agora.']:said+=text.feed(delta)
    said+=text.flush()
    assert said==['Abrindo o Spotify.','O valor é 3.14 agora.']
    assert speakable('Veja https://x.com e `código` **forte** 😀')=='Veja e código forte'
    assert speakable('Ferramenta concluída conforme suas autorizações.')==''

def test_hotkeys_parse():
    assert hotkey_codes('Control+Space')==[0x11,0x20]

class FakeSpeaker:
    def __init__(self):self.speaking=False;self.stops=0;self.said=[]
    def stop(self):self.stops+=1
    def say(self,text):self.said.append(text)

class FakeTranscriber:
    def __init__(self,text='abre o spotify'):self.calls=0;self.text=text
    def installed(self):return True
    def transcribe(self,pcm,hints):self.calls+=1;return {'text':self.text}

class FakeWake:
    def __init__(self):self.fire=False
    def detect(self,chunk):return self.fire,1.0 if self.fire else 0.0

def make_loop(mode='hey_jarvis',text='abre o spotify'):
    events=[];speaker,transcriber,wake=FakeSpeaker(),FakeTranscriber(text),FakeWake()
    loop=VoiceLoop(transcriber,speaker,lambda:{'wake_mode':mode},lambda:(),lambda:wake,events.append)
    loop.open=lambda:None;loop.close=lambda:None
    loop.mode=mode;loop.wake=wake
    return loop,events,speaker,transcriber,wake

def wait_for(predicate,timeout=2):
    end=time.monotonic()+timeout
    while time.monotonic()<end and not predicate():time.sleep(.02)
    return predicate()

def test_asleep_no_audio_reaches_whisper_until_hey_jarvis():
    loop,events,speaker,transcriber,wake=make_loop()
    for c in chunks(3,.3):loop.process(c)
    assert transcriber.calls==0
    wake.fire=True;loop.process(chunks(.1,.3)[0]);wake.fire=False
    assert any(e['type']=='wake' for e in events) and speaker.stops==1 and loop.state=='listening'
    for c in chunks(1,.3)+chunks(1,0):loop.process(c)
    assert wait_for(lambda:any(e['type']=='transcript' and e['text']=='abre o spotify' for e in events))

def test_the_alts_own_voice_is_not_heard_and_it_falls_asleep():
    loop,events,speaker,transcriber,wake=make_loop()
    loop.listen('wake');speaker.speaking=True
    for c in chunks(1,.3):loop.process(c)
    assert loop.recording==[]
    speaker.speaking=False;loop.recording=None;loop.awake_until=time.monotonic()-1;loop.state='awake'
    loop.process(chunks(.1,0)[0])
    assert loop.state=='sleeping'

def test_ei_alt_wakes_only_on_the_name_and_keeps_the_command():
    loop,events,speaker,transcriber,wake=make_loop('ei_alt','Ei, ALT, abre o Discord')
    for c in chunks(1,.3)+chunks(1,0):loop.process(c)
    assert wait_for(lambda:any(e['type']=='transcript' and e['text']=='abre o Discord' for e in events))
    loop2,events2,_,t2,_=make_loop('ei_alt','fala sobre o jogo de ontem')
    for c in chunks(1,.3)+chunks(1,0):loop2.process(c)
    assert wait_for(lambda:t2.calls==1) and not any(e['type']=='transcript' for e in events2)

def test_stop_silences_everything():
    loop,events,speaker,transcriber,wake=make_loop()
    loop.listen('button');loop.stop()
    assert loop.recording is None and speaker.stops>=2
    for c in chunks(1,.3):loop.process(c)
    assert transcriber.calls==0

def test_a_spoken_request_is_answered_aloud_sentence_by_sentence(tmp_path):
    app,local,_,client=fixture_client(tmp_path)
    async def model_stream(model,messages,cancel,profile=None):
        for part in ['Claro. ','Aqui vai: o ','dia está bom. ','Até mais']:yield {'message':{'content':part}}
        yield {'done':True,'eval_count':9}
    local.stream=model_stream
    with client:
        said=[];app.state.speaker.say=said.append
        cid=conversation(client)
        client.post('/chat',json={'conversation_id':cid,'model':'fixture:4b','content':'como está o dia?','speak':True})
        assert said==['Claro.','Aqui vai:','o dia está bom.','Até mais']
        client.post('/chat',json={'conversation_id':cid,'model':'fixture:4b','content':'e amanhã?'})
        assert len(said)==4
