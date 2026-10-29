"""Deterministic checks of model replies: arithmetic claims and link provenance.

Nothing here asks a model. Calculations are recomputed with the same restricted
evaluator used by the calculate tool; links are compared with URLs that came
from confirmed tool results or from the user. A check that finds nothing says
so; it never certifies facts beyond the arithmetic or the link's origin."""
import json
import re
from backend.tools.service import calculate

NUMBER=r'\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?'
OPERATOR=r'\s*(?:[-+*/×x÷·]|\bvezes\b|\bmais\b|\bmenos\b|\bdividido\s+por\b)\s*'
EQUALS=r'\s*(?:=|≈|\bé\b(?:\s+igual\s+a)?|\bigual\s+a\b|\bdá\b|\bresulta\s+em\b|\bsão\b)\s*'
CLAIM=re.compile(r'(?<![\w.,/])(-?(?:'+NUMBER+r')(?:'+OPERATOR+r'(?:'+NUMBER+r'))+)'+EQUALS+r'(-?(?:'+NUMBER+r'))(?![\w/])',re.I)
PERCENT=re.compile(r'(?<![\w.,])('+NUMBER+r')\s*%\s*de\s*('+NUMBER+r')'+EQUALS+r'(-?(?:'+NUMBER+r'))(?![\w/])',re.I)
URL=re.compile(r'https?://[^\s<>()\[\]"\'`]+',re.I)
WORDS={'vezes':'*','mais':'+','menos':'-','dividido por':'/','×':'*','x':'*','÷':'/','·':'*'}

def number(text):
    """Brazilian notation first: 1.234,5 and 1.234 are thousands; 2.5 is decimal."""
    text=text.strip()
    if ',' in text:return float(text.replace('.','').replace(',','.'))
    if re.fullmatch(r'-?\d{1,3}(?:\.\d{3})+',text):return float(text.replace('.',''))
    return float(text)

def decimals(text):
    text=text.strip()
    if ',' in text:return len(text.split(',')[1])
    if re.fullmatch(r'-?\d{1,3}(?:\.\d{3})+',text):return 0
    return len(text.split('.')[1]) if '.' in text else 0

def expression(text):
    parts=re.split(r'('+OPERATOR+r')',text,flags=re.I);result=[]
    for part in parts:
        token=re.sub(r'\s+',' ',part.strip().lower())
        if not token:continue
        if token in WORDS or token in '+-*/':result.append(WORDS.get(token,token))
        else:result.append(repr(number(token)))
    return ' '.join(result)

def agrees(actual,stated_text):
    stated=number(stated_text);places=decimals(stated_text)
    # A stated value rounded to its own precision is still correct.
    difference=abs(actual-stated);epsilon=1e-9*max(1,abs(actual))
    if difference<=epsilon:return True
    return difference<.5*10**-places-epsilon if places or actual!=int(actual) else False

def check_calculations(text,limit=12):
    found=[];seen=set()
    for match in CLAIM.finditer(text):
        left,right=match.group(1),match.group(2)
        if not re.search(OPERATOR,left.lstrip('-'),re.I) or (left,right) in seen:continue
        # Dates and ranges such as 2024-2025 or 10/11 are not arithmetic claims.
        if re.fullmatch(r'\d{1,4}\s*[-/]\s*\d{1,4}',left) and not re.search(r'[=≈]',match.group(0)):continue
        seen.add((left,right))
        try:
            source=expression(left);actual=calculate(source)
            found.append({'claim':match.group(0).strip(),'expression':source,'stated':right,'actual':round(actual,10),'ok':agrees(actual,right),'rounded':number(right)!=actual})
        except ValueError:continue
        if len(found)>=limit:break
    for match in PERCENT.finditer(text):
        try:
            actual=number(match.group(1))*number(match.group(2))/100
            found.append({'claim':match.group(0).strip(),'expression':f'{match.group(1)}% de {match.group(2)}','stated':match.group(3),'actual':round(actual,10),'ok':agrees(actual,match.group(3))})
        except ValueError:continue
    return found[:limit]

def clean_url(url):return url.rstrip('.,;:!?*_')

def urls_in(value):
    text=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False)
    return {clean_url(u) for u in URL.findall(text)}

def check_sources(text,known):
    normalized={u.rstrip('/').casefold() for u in known}
    result=[]
    for url in dict.fromkeys(clean_url(u) for u in URL.findall(text)):
        result.append({'url':url,'confirmed':url.rstrip('/').casefold() in normalized})
    return result[:20]

def verify_reply(text,known_urls=()):
    calculations=check_calculations(text);sources=check_sources(text,known_urls)
    issues=sum(not c['ok'] for c in calculations)+sum(not s['confirmed'] for s in sources)
    return {'calculations':calculations,'sources':sources,'issues':issues,
        'notice':'Conferência automática: recalcula contas escritas e compara links com resultados confirmados de ferramentas. Não verifica outras afirmações.'}

def conversation_urls(store,cid):
    """URLs the user wrote or that confirmed tool results returned in this conversation."""
    known=set()
    for row in store.rows("SELECT a.result FROM actions a JOIN action_context c ON c.id=a.id WHERE c.conversation_id=? AND a.status='complete'",(cid,)):
        if row['result']:known|=urls_in(row['result'])
    for message in store.messages(cid):
        if message['role']=='user':known|=urls_in(message['content'])
    return known
