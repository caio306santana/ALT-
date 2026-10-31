"""Exact, single requests (open Notepad/Calculator, download X from site Y) need no language-model generation.

Only recognize the owner's entire current message. Quoted instructions,
documents, multi-step requests and tool observations stay on the model path.
Execution still goes through ToolService's normal policy, STOP and approval.
"""
import re
import unicodedata
from backend.tools.service import ToolProposal

# "alt, você consegue abrir…?": asked as a question, meant as a request.
PREFIX=r'(?:(?:alt(?:-ai)?|chat)[ ,:]+)?(?:(?:por favor)[ ,]+)?(?:(?:voc[eê]|vc)\s+)?(?:(?:consegue|pode|poderia|d[aá] pra|d[aá] para)\s+)?'

PATTERN=re.compile(PREFIX+r'(?:abra|abre|abrir|abri|inicie|inicia)(?:\s+(?:o|a|um|uma))?\s+(bloco de notas|bloco notas|notepad|calculadora|calculator)(?:[ ,]+por favor)?[.!?]*',re.I)

# "baixa o manual do 7-Zip do site 7-zip.org": what to fetch and an explicit domain, nothing else.
DOWNLOAD=re.compile(PREFIX+r'(?:baixa|baixe|baixar|fa[çc]a o download d[eoa]s?)\s+(?:(?:o|a|os|as|um|uma)\s+)?'
    r'(?P<what>.{2,120}?)\s+(?:d[oa]|de|no|na|pelo|pela|em)\s+(?:site\s+(?:d[oa]\s+|de\s+)?)?(?P<site>(?:https://)?[\w-]+(?:\.[\w-]+)+(?:/\S*)?)(?:[ ,]+por favor)?[.!?]*',re.I)

# "abre o bloco de notas e digita olá mundo": a new Notepad document with the text, no model needed.
OPEN_TYPE=re.compile(PREFIX+r'(?:abra|abre|abrir|abri)\s+(?:o\s+)?(?:bloco de notas|bloco notas|notepad)\s+e\s+(?:depois\s+)?(?:digit(?:[ae]|ar)|escrev(?:[ae]|er)|coloc(?:[ae]|ar))\s+(?:o texto\s+|isso:?\s+)?(?P<text>.{1,2000}?)\s*[.!?]*',re.I|re.S)

# "abre o youtube e pesquisa lofi", "pesquisa receitas no google": the site opens on its own search page.
SEARCH_SITES={'youtube':'https://www.youtube.com/results?search_query=','google':'https://www.google.com/search?q='}
SITE_SEARCH=re.compile(PREFIX+r'(?:'
    r'(?:abr[ae]|abrir|entra|entre)\s+(?:o\s+)?(?P<site1>youtube|google)\s+e\s+(?:depois\s+)?(?:pesquis[ae]|procur[ae]|busc[ae])\s+(?:por\s+)?(?P<q1>.+?)'
    r'|(?:pesquis[ae]|procur[ae]|busc[ae])\s+(?:por\s+)?(?P<q2>.+?)\s+no\s+(?P<site2>youtube|google))[.!?]*',re.I)

def direct_action(content,attachment_ids=(),tool_result_id=''):
    if attachment_ids or tool_result_id:return None
    text=' '.join(unicodedata.normalize('NFKC',content).strip().split())
    match=PATTERN.fullmatch(text)
    if match:
        app='calculator' if match.group(1).lower() in ('calculadora','calculator') else 'notepad'
        return ToolProposal(tool='open_app',app=app)
    match=OPEN_TYPE.fullmatch(text)
    if match:
        return ToolProposal(tool='windows_type',app='notepad',content=match.group('text').strip().strip('"“”\''))
    match=SITE_SEARCH.fullmatch(text)
    if match:
        import urllib.parse
        site=(match.group('site1') or match.group('site2')).lower();query=(match.group('q1') or match.group('q2')).strip()
        return ToolProposal(tool='open_url',url=SEARCH_SITES[site]+urllib.parse.quote_plus(query))
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
    if result.get('status')!='done':return (result.get('notice') or chat_line(result)) if action.tool in ('find_download','windows_type') else chat_line(result)
    if action.tool=='windows_type':
        return f"Bloco de Notas aberto e texto digitado: \"{action.content[:80]}\"."
    if action.tool=='open_url':
        return f"Aberto no navegador: {result.get('opened') or action.url}"
    if action.tool=='find_download':
        from pathlib import Path
        return f"Baixado: {Path(result['path']).name}, de {result.get('site') or 'um site encontrado na pesquisa'}, salvo em {Path(result['path']).parent}. Não abri nem executei o arquivo." 
    name='Bloco de Notas' if action.app=='notepad' else 'Calculadora'
    return name+' aberto.' if action.app=='notepad' else name+' aberta.'
