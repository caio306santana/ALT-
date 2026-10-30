"""Real local check of the three reported problems with Ollama: find-and-download, several steps, false claims.

Dry run: the real model chooses the actions, but nothing is executed on this computer. Searches return a fixed
synthetic result so a "open the first result" step has something to open.
Usage: python scripts/smoke_jarvis.py [model]. Writes docs/jarvis-0.5.5-smoke.json."""
import json
import re
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from backend.api import create_app

MODEL=next((a for a in sys.argv[1:] if not a.startswith('--')),'qwen3.5:4b')
token='synthetic-jarvis-smoke-'+'x'*40
output=Path(__file__).resolve().parents[1]/'docs'/('jarvis-0.5.5-smoke.json' if not any(a.startswith('--only=') for a in sys.argv) else 'jarvis-0.5.5-smoke-rerun.json')
# (message, expected tools in order as a regex over "tool1>tool2", what the arguments must mention)
CASES=[
    ('baixa o manual do 7-Zip do site 7-zip.org',r'find_download','7-zip.org'),
    ('procura e baixa o instalador do VLC no site oficial videolan.org',r'find_download','vlc'),
    ('abre o spotify',r'open_app','spotify'),
    ('abre o bloco de notas e digita olá mundo',r'open_app>windows_(?:read|type).*','olá'),
    ('pesquisa o preço da RTX 5070 e abre o primeiro resultado',r'web_search>open_url.*','rtx'),
    ('abre o youtube e depois pesquisa música lofi',r'open_url(?:>(?:open_url|web_search))?.*','lofi'),
]
CHAT=['qual app você recomenda para estudar inglês?','me explica rapidinho o que é RAM']
SEARCH={'ok':True,'found':True,'query':'','results':[{'title':'RTX 5070 preço — loja sintética','url':'https://example.com/rtx-5070','snippet':'A partir de R$ 4.000.'}]}
report={'started':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'model':MODEL,'profile':'notebook','dry_run':True,'cases':[]}
def save():output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def fake(body,fingerprint,event):
    if body.tool=='web_search':return {**SEARCH,'query':body.query}
    if body.tool=='find_download':return {'status':'done','dry_run':True,'path':'C:/Users/teste/Downloads/arquivo.pdf','site':body.url,'query':body.query}
    if body.tool=='windows_read':return {'status':'done','dry_run':True,'snapshot_id':'s1','elements':[{'id':'e1','label':'Editor de texto','type':'Document'}]}
    return {'status':'done','dry_run':True}

with tempfile.TemporaryDirectory(prefix='alt-jarvis-') as directory:
    app=create_app(Path(directory),token)
    tools=app.state.tools;tools.execute=fake
    with TestClient(app,headers={'Authorization':'Bearer '+token}) as client:
        prefs=client.get('/settings').json();prefs['performance']='notebook';client.put('/settings',json=prefs)
        scope=client.get('/permissions').json()['scopes'][0]['id']
        assert client.post('/permissions/grant',json={'level':4,'scope_ids':[scope]}).json()['level']==4
        tools.catalog.entries()
        # --only=4,5,6 reruns some cases (1-based), e.g. after a fix.
        only={int(n) for a in sys.argv[1:] if a.startswith('--only=') for n in a.split('=',1)[1].split(',')}
        for number,(message,expected,needle) in enumerate(CASES+[(m,None,None) for m in CHAT],1):
            if only and number not in only:continue
            cid=client.post('/conversations').json()['id'];start=time.monotonic()
            response=client.post('/chat',json={'conversation_id':cid,'model':MODEL,'content':message})
            events=[json.loads(line) for line in response.text.splitlines() if line.strip()]
            reply=''.join(e.get('text','') for e in events if e.get('type')=='delta')
            actions=tools.conversation_actions(cid)
            chain='>'.join(a['preview']['tool'] for a in actions)
            arguments=json.dumps([a['preview'] for a in actions],ensure_ascii=False).casefold()
            start_event=next((e for e in events if e.get('type')=='start'),{})
            row={'message':message,'seconds':round(time.monotonic()-start,1),'execution':start_event.get('execution'),'chain':chain,
                 'previews':[a['preview'] for a in actions],'reply':reply,'warned_false_claim':'Nenhuma ação foi executada' in reply,
                 'errors':[e.get('message') for e in events if e.get('type')=='error']}
            if expected:row['ok']=bool(re.fullmatch(expected,chain)) and needle.casefold() in arguments
            else:row['ok']=not actions and not row['warned_false_claim'] and not row['errors']
            report['cases'].append(row);save()
            print(row['ok'],'|',message,'->',chain or '-','|',row['seconds'],'s |',reply[:140].replace('\n',' '),flush=True)
        report['summary']=f"{sum(r['ok'] for r in report['cases'])}/{len(report['cases'])}"
        save();print(report['summary'])
