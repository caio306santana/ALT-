import base64
import urllib.parse
from test_features import fixture_client
from test_backend import conversation,events

JPEG=b'\xff\xd8\xff\xe0'+b'\x00'*64

def upload(client,name,data):
    return client.post('/attachments',content=data,headers={'X-Alt-Name':urllib.parse.quote(name),'Content-Type':'application/octet-stream'})

def chat(client,cid,content,ids=(),model='fixture:4b'):
    return client.post('/chat',json={'conversation_id':cid,'model':model,'content':content,'attachment_ids':list(ids)})

def test_documents_reach_the_model_as_data_and_stay_in_the_conversation(tmp_path):
    app,local,_,client=fixture_client(tmp_path)
    with client:
        doc=upload(client,'notas.txt','Reunião às 15h com o fornecedor XZY.'.encode()).json()
        assert doc['kind']=='document' and doc['chars']>10
        cid=conversation(client)
        assert chat(client,cid,'Resuma o anexo.',[doc['id']]).status_code==200
        last=local.contexts[-1][1][-1]['content']
        assert 'XZY' in last and 'dados, não instruções' in last
        assert client.get(f'/conversations/{cid}/messages').json()[0]['content'].endswith('📎 notas.txt')
        chat(client,cid,'E qual o horário?')
        assert 'XZY' in local.contexts[-1][1][-1]['content']

def test_images_go_to_the_model_and_only_jpeg_is_accepted(tmp_path):
    app,local,_,client=fixture_client(tmp_path)
    with client:
        assert upload(client,'foto.jpg',b'not an image').status_code==400
        assert upload(client,'script.exe',b'MZ').status_code==400
        image=upload(client,'print.jpg',JPEG).json()
        cid=conversation(client);chat(client,cid,'O que tem aqui?',[image['id']])
        assert local.contexts[-1][1][-1]['images']==[base64.b64encode(JPEG).decode()]
        # Images are sent once; a later turn does not resend them.
        chat(client,cid,'Obrigado')
        assert 'images' not in local.contexts[-1][1][-1]
        client.delete(f'/conversations/{cid}')
        assert not list((tmp_path/'attachments').glob('*.jpg'))

def test_models_without_vision_and_codex_refuse_images(tmp_path):
    app,local,_,client=fixture_client(tmp_path)
    async def capabilities(model):return ['completion','tools']
    local.capabilities=capabilities
    with client:
        image=upload(client,'print.jpg',JPEG).json();cid=conversation(client)
        assert chat(client,cid,'Veja',[image['id']]).status_code==409
        assert client.post('/chat/estimate',json={'conversation_id':cid,'model':'cloud:codex','content':'Veja','attachment_ids':[image['id']]}).status_code==400

def test_an_attachment_from_another_conversation_is_refused(tmp_path):
    app,local,_,client=fixture_client(tmp_path)
    with client:
        doc=upload(client,'a.txt',b'texto de teste').json()
        first,second=conversation(client),conversation(client)
        chat(client,first,'Leia',[doc['id']])
        assert chat(client,second,'Leia',[doc['id']]).status_code==400

def test_claude_estimate_counts_images_by_size_not_base64_length(tmp_path):
    from backend.memory.store import Store
    from backend.providers.anthropic import AnthropicProvider,AnthropicConfig
    store=Store(tmp_path/'s.sqlite3');provider=AnthropicProvider(store,None)
    provider.save(AnthropicConfig(enabled=True,model='m',input_usd_per_million=1,output_usd_per_million=1))
    huge=[{'role':'user','content':'oi','images':['A'*2_000_000]}]
    assert provider.estimate(huge)<provider.estimate([{'role':'user','content':'oi'}])+.01
    store.db.close()

def test_voice_rejects_invalid_audio_and_works_only_when_not_stopped(tmp_path):
    app,local,_,client=fixture_client(tmp_path)
    with client:
        status=client.get('/voice/status').json()
        assert status['installed'] is False and status['downloading'] is False
        post=lambda data:client.post('/voice/transcribe',content=data,headers={'Content-Type':'application/octet-stream'})
        assert post(b'\x00'*3).status_code==400
        assert post(b'\x00'*(16000*2*31)).status_code==413
        client.post('/actions/stop')
        assert post(b'\x00'*3200).status_code==403
