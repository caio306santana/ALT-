"""Real local check of full access with Ollama: does the model pick the right tool and arguments?

Actions are recorded but never executed (dry run), so nothing opens on this computer.
Usage: python scripts/smoke_full_access.py [model ...]. Writes docs/full-access-smoke.json."""
import json
import re
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from backend.api import create_app
from backend.evaluations import automatic_checks

# --routing=stable compares the fixed tool set against keyword routing (default: filtered).
ROUTING=next((a.split('=',1)[1] for a in sys.argv[1:] if a.startswith('--routing=')),'filtered')
MODELS=[a for a in sys.argv[1:] if not a.startswith('--')] or ['qwen3.5:4b']
token='synthetic-full-access-smoke-'+'x'*40
output=Path(__file__).resolve().parents[1]/'docs'/('full-access-smoke.json' if ROUTING=='filtered' else f'full-access-smoke-{ROUTING}.json')
# (message, expected tool, text the arguments must contain)
CASES=[
    ('abra uma nova aba no google','open_url','google'),
    ('abre o youtube','open_url','youtube'),
    ('abre o spotify','open_app','spotify'),
    ('abre a calculadora','open_app','calc'),
    ('abre o chrome','open_app','chrome'),
    ('pesquisa no google o preço da RTX 5070','open_url|web_search','rtx'),
    ('rode ipconfig','run_command','ipconfig'),
    ('fecha o discord','close_app','discord'),
    ('aperta ctrl+t no chrome','windows_keys','ctrl+t'),
    ('olha minha tela e me diz o que tem','screen_look','screen_look'),
    ('abaixa o volume pra 30','system_volume','30'),
    ('me lembra de beber água em 10 minutos','reminder_create','água'),
    ('pausa a música','media_key|windows_keys','pa'),
    ('você lembra qual é a minha cor favorita?','memory_recall','cor'),
]
CHAT=['oi, tudo bem?','me ajuda a organizar meu dia, tenho academia às 7h e trabalho das 9h às 18h']
report={'started':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'dry_run':True,'models':{}}

def save():output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

with tempfile.TemporaryDirectory(prefix='alt-full-access-') as directory:
    app=create_app(Path(directory),token)
    tools=app.state.tools
    tools.execute=lambda body,fingerprint,event:{'dry_run':True}
    with TestClient(app,headers={'Authorization':'Bearer '+token}) as client:
        prefs=client.get('/settings').json();prefs['performance']='desktop';prefs['tool_routing']=ROUTING;client.put('/settings',json=prefs)
        scope=client.get('/permissions').json()['scopes'][0]['id']
        assert client.post('/permissions/grant',json={'level':4,'scope_ids':[scope]}).json()['level']==4
        tools.catalog.entries()
        for model in MODELS:
            rows=[];report['models'][model]=rows
            for message,expected,needle in CASES+[(m,None,None) for m in CHAT]:
                cid=client.post('/conversations').json()['id'];start=time.monotonic()
                response=client.post('/chat',json={'conversation_id':cid,'model':model,'content':message})
                events=[json.loads(line) for line in response.text.splitlines() if line.strip()]
                reply=''.join(e.get('text','') for e in events if e.get('type')=='delta')
                action=next((a for a in tools.conversation_actions(cid)),None)
                tool=action['preview']['tool'] if action else None
                arguments=json.dumps(action['preview'],ensure_ascii=False).casefold() if action else ''
                row={'message':message,'seconds':round(time.monotonic()-start,1),'tool':tool,'state':action['state'] if action else None,
                     'preview':action['preview'] if action else None,'reply':reply,'errors':[e for e in events if e.get('type')=='error']}
                if expected:
                    row['ok']=bool(tool and re.fullmatch(expected,tool) and needle in arguments)
                else:
                    checks=automatic_checks({'checks':['words:120','no_debate']},reply)
                    row['checks']=checks;row['ok']=all(c['ok'] for c in checks)
                rows.append(row);save()
                print(model,'|',message,'->',tool,'|',row['ok'],'|',row['seconds'],'s |',reply[:120].replace('\n',' '),flush=True)
        report['summary']={model:f"{sum(r['ok'] for r in rows)}/{len(rows)}" for model,rows in report['models'].items()}
        save();print(report['summary'])
