"""Exact, single requests (open Notepad/Calculator, download X from site Y) need no language-model generation.

Only recognize the owner's entire current message. Quoted instructions,
documents, multi-step requests and tool observations stay on the model path.
Execution still goes through ToolService's normal policy, STOP and approval.
"""
import re
import unicodedata
from backend.tools.service import ToolProposal

PATTERN=re.compile(r'(?:(?:alt(?:-ai)?|chat)[ ,:]+)?(?:(?:por favor)[ ,]+)?(?:abra|abre|abrir|inicie|inicia)(?:\s+(?:o|a|um|uma))?\s+(bloco de notas|bloco notas|notepad|calculadora|calculator)(?:[ ,]+por favor)?[.!?]*',re.I)

# "baixa o manual do 7-Zip do site 7-zip.org": what to fetch and an explicit domain, nothing else.
DOWNLOAD=re.compile(r'(?:(?:alt(?:-ai)?|chat)[ ,:]+)?(?:(?:por favor)[ ,]+)?(?:baixa|baixe|baixar|fa[çc]a o download d[eoa]s?)\s+(?:(?:o|a|os|as|um|uma)\s+)?'
    r'(?P<what>.{2,120}?)\s+(?:d[oa]|de|no|na|pelo|pela|em)\s+(?:site\s+(?:d[oa]\s+|de\s+)?)?(?P<site>(?:https://)?[\w-]+(?:\.[\w-]+)+(?:/\S*)?)(?:[ ,]+por favor)?[.!?]*',re.I)

def direct_action(content,attachment_ids=(),tool_result_id=''):
    if attachment_ids or tool_result_id:return None
    text=' '.join(unicodedata.normalize('NFKC',content).strip().split())
    match=PATTERN.fullmatch(text)
    if match:
        app='calculator' if match.group(1).lower() in ('calculadora','calculator') else 'notepad'
        return ToolProposal(tool='open_app',app=app)
    match=DOWNLOAD.fullmatch(text)
    # A second step ("e depois abre") stays with the model, which can chain actions.
    if match and not re.search(r'\b(?:e depois|depois|e ent[aã]o|em seguida|e abr|e abra|e abre)',match.group('what'),re.I):
        return ToolProposal(tool='find_download',query=match.group('what').strip(),url=match.group('site').strip())
    return None

def estimate():
    return {'fits':True,'input_tokens':0,'required_tokens':0,'input_limit':0,
        'total_context':0,'output_reserve':0,'history_included':0,'history_total':0,
        'tokenizer':'sem geração','execution':'direct','components':{},'app_context_omitted':0}

async def stream(action):
    yield {'message':{'tool_calls':[{'function':{'name':'alt_propose_action','arguments':action.model_dump(exclude_defaults=True)}}]}}
    yield {'done':True,'eval_count':0,'prompt_eval_count':0}

def reply(action,result):
    from backend.tools.outcome import chat_line
    if result.get('status')!='done':return (result.get('notice') or chat_line(result)) if action.tool=='find_download' else chat_line(result)
    if action.tool=='find_download':
        from pathlib import Path
        return f"Baixado: {Path(result['path']).name}, de {result.get('site') or 'um site encontrado na pesquisa'}, salvo em {Path(result['path']).parent}. Não abri nem executei o arquivo." 
    name='Bloco de Notas' if action.app=='notepad' else 'Calculadora'
    return name+' aberto.' if action.app=='notepad' else name+' aberta.'
