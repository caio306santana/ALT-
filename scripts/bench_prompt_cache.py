"""Does Ollama reuse the prompt between turns? Same conversation, three messages, filtered vs stable tools.
Prints the prompt tokens Ollama actually evaluated per turn (cached tokens are not counted). No tool runs."""
import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.personality import system_prompt
from backend.providers.ollama import Ollama
from backend.monitoring.performance import performance_profile
from backend.tools.chat_tools import tool_spec,stable_tool_spec

TURNS=['abre o spotify','qual a capital da França?','pesquise o preço da RTX 5070']

async def run(model,mode):
    ollama=Ollama();history=[];rows=[]
    for text in TURNS:
        status={'level':4}
        spec=stable_tool_spec(text,status)[0] if mode=='stable' else tool_spec(text,status)
        profile=performance_profile('desktop');profile['options']['num_predict']=48
        if spec:profile['tools']=spec
        messages=[{'role':'system','content':system_prompt({},tools=bool(spec))},*history,{'role':'user','content':text}]
        reply='';done={}
        async for chunk in ollama.stream(model,messages,asyncio.Event(),profile):
            reply+=chunk.get('message',{}).get('content','')
            if chunk.get('done'):done=chunk
        history+=[{'role':'user','content':text},{'role':'assistant','content':reply or 'ok'}]
        rows.append({'turn':text,'prompt_tokens_evaluated':done.get('prompt_eval_count'),'prompt_seconds':round((done.get('prompt_eval_duration') or 0)/1e9,3)})
    return rows

async def main():
    model=sys.argv[1] if len(sys.argv)>1 else 'qwen3.5:4b'
    report={mode:await run(model,mode) for mode in ('filtered','stable')}
    print(json.dumps(report,ensure_ascii=False,indent=1))

asyncio.run(main())
