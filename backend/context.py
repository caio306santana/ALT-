"""Model token budgets and byte-bounded excerpts; preserve explicit user context."""
import json
import sys
import hashlib
from pathlib import Path
from functools import lru_cache


class ContextLimitError(ValueError):
    def __init__(self, required, limit, total, output, components=None):
        self.estimate={'fits':False,'required_tokens':required,'input_tokens':required,
            'input_limit':limit,'total_context':total,'output_reserve':output,
            'history_included':0,'history_total':0}
        if components is not None:self.estimate['components']=dict(components)
        super().__init__(f'Este envio precisa de cerca de {required} tokens de entrada; '
            f'o contexto deste perfil permite {limit}. Reduza a mensagem ou as memórias '
            'selecionadas. O histórico anterior continua salvo.')


def fit_context_blocks(blocks,budget,cost,header=''):
    """Fit complete application observations, never slicing JSON or trust markers.

    The owner's message, instructions and explicit memories are budgeted by the
    caller first. Omitted observations can be read again with the relevant tool.
    """
    selected='';omitted=0
    notice='\n[Dados auxiliares limitados ao contexto. Use ferramentas para obter observações necessárias; não invente os dados omitidos.]'
    for block in blocks:
        candidate=(selected+'\n'+block) if selected else header+block
        if cost(candidate+notice)<=budget:selected=candidate
        else:omitted+=1
    if omitted and cost(selected+notice)<=budget:selected+=notice
    return selected,omitted


def has_qwen_tokenizer(model):
    return bool(model and (model.lower().startswith('qwen3.5:') or model.lower().startswith('huihui_ai/qwen3.5-abliterated:')))


@lru_cache(maxsize=1)
def qwen_tokenizer():
    from tokenizers import Tokenizer
    root=Path(sys.executable).parent/'tokenizers' if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[1]/'assets'/'tokenizers'
    path=root/'qwen3.5.json';metadata=json.loads((root/'provenance.json').read_text(encoding='utf-8'))
    if hashlib.sha256(path.read_bytes()).hexdigest()!=metadata['sha256']:raise ValueError('Metadados de tokenização alterados. Reinstale o pacote validado da ALT.')
    return Tokenizer.from_file(str(path))

def hermes_tokenizer_name(model):
    name=(model or '').lower()
    if name=='hermes3:3b':return 'hermes3-3b'
    if name in ('hermes3','hermes3:latest','hermes3:8b'):return 'hermes3-8b'
    return None

@lru_cache(maxsize=2)
def hermes_tokenizer(name):
    from tokenizers import Tokenizer
    root=Path(sys.executable).parent/'tokenizers' if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[1]/'assets'/'tokenizers'
    path=root/(name+'.json');metadata=json.loads((root/(name+'-provenance.json')).read_text(encoding='utf-8'))
    if hashlib.sha256(path.read_bytes()).hexdigest()!=metadata['sha256']:raise ValueError('Metadados de tokenização alterados. Reinstale o pacote validado da ALT.')
    return Tokenizer.from_file(str(path))

def tokenizer_label(model):
    if has_qwen_tokenizer(model):return 'Qwen 3.5'
    if hermes_tokenizer_name(model):return 'Hermes 3'
    return 'estimativa conservadora'

def message_cost(text,model=None):
    if has_qwen_tokenizer(model):
        # Count the model family's actual BPE tokens, reserving role/template
        # overhead separately. UTF-8 bytes are not treated as individual tokens.
        return len(qwen_tokenizer().encode(text,add_special_tokens=False).ids)+32
    if name:=hermes_tokenizer_name(model):return len(hermes_tokenizer(name).encode(text,add_special_tokens=False).ids)+32
    # Conservative fallback for other models whose tokenizer is not bundled.
    return len(text.encode('utf-8')) + 32


def tool_schema_cost(spec,model=None):
    if not spec:return 0
    # Engines render tools into the chat template. Counting only compact JSON
    # underestimated the real Qwen prompt in the live 0.5.1 smoke; budget for
    # formatted definitions as well, keeping the normal template reserve.
    rendered=max(message_cost(json.dumps(spec,ensure_ascii=False,separators=(',',':')),model),
        message_cost(json.dumps(spec,ensure_ascii=False,indent=2),model))
    # Hermes adds its function-calling/XML instructions around the definitions.
    # Keep a separate conservative allowance until calibrated with real weights.
    return rendered+(256 if hermes_tokenizer_name(model) else 0)


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def clip(text, budget):
    data = str(text).encode('utf-8')
    return data[:max(0, budget)].decode('utf-8', errors='ignore')


def tool_excerpt(raw, budget):
    """Return valid JSON within budget, retaining complete source URLs.

    Excerpts are deterministic data reduction, not a model-written summary.
    The original result remains unchanged in the database and action card.
    """
    data = json.loads(raw)
    full = compact(data)
    if len(full.encode('utf-8')) <= budget:
        return full, bool(isinstance(data, dict) and data.get('truncated'))
    if budget < 128:
        raise ValueError('Falta espaço para analisar o resultado. Reduza as memórias selecionadas ou as instruções pessoais e tente novamente.')

    def fits(value):
        return len(compact(value).encode('utf-8')) <= budget

    if isinstance(data, dict) and isinstance(data.get('results'), list):
        # Keep a useful snippet for each selected source; do not cut a URL.
        base = {key: clip(data[key], 100) for key in ('query', 'retrieved_at') if key in data}
        for count in range(min(3, len(data['results'])), 0, -1):
            for size in (240, 120, 48, 0):
                sources = [{'url': row.get('url', ''), 'title': clip(row.get('title', ''), 100),
                            'snippet': clip(row.get('snippet', ''), size)} for row in data['results'][:count]]
                excerpt = {**base, 'results': sources, 'truncated': True}
                if fits(excerpt):
                    return compact(excerpt), True
        raise ValueError('Os links da pesquisa não cabem no contexto atual. Reduza as memórias ou as instruções pessoais e tente novamente.')

    if isinstance(data, dict) and ('text' in data or 'content' in data):
        field = 'text' if 'text' in data else 'content'
        excerpt = {key: data[key] for key in ('url', 'retrieved_at') if key in data}
        if 'title' in data:
            excerpt['title'] = clip(data['title'], 120)
        excerpt.update({field: '', 'truncated': True})
        # JSON escaping can expand bytes. Binary search the *serialized* size.
        content = str(data[field]); low, high = 0, len(content)
        while low < high:
            middle = (low + high + 1) // 2
            excerpt[field] = content[:middle]
            if fits(excerpt): low = middle
            else: high = middle - 1
        excerpt[field] = content[:low]
        if low and fits(excerpt):
            return compact(excerpt), True
        raise ValueError('A fonte não cabe no contexto atual. Reduza as memórias ou as instruções pessoais e tente novamente.')

    if isinstance(data, dict) and isinstance(data.get('entries'), list):
        excerpt = {'entries': [], 'truncated': True}
        for entry in data['entries']:
            candidate = {**excerpt, 'entries': [*excerpt['entries'], entry]}
            if not fits(candidate): break
            excerpt = candidate
        if excerpt['entries']:
            return compact(excerpt), True

    # Other results are small in normal use. Keep a clearly identified raw
    # excerpt if an unusually large future tool has no structured formatter.
    excerpt = {'excerpt': '', 'truncated': True}
    low, high = 0, min(len(full.encode('utf-8')), budget)
    while low < high:
        middle = (low + high + 1) // 2
        excerpt['excerpt'] = clip(full, middle)
        if fits(excerpt): low = middle
        else: high = middle - 1
    excerpt['excerpt'] = clip(full, low)
    if fits(excerpt): return compact(excerpt), True
    raise ValueError('Resultado grande demais para o contexto atual.')


class RoundLimitError(ValueError):
    """A later model call of the same reply no longer fits; the reply ends with guidance."""


def fit_round(messages, limit, cost, fixed, shrink, image_tokens=0):
    """Keep every model call of one reply inside the context window, not only the first.

    `fixed` is the index of the owner's current message. The system prompt, that message
    and everything after it (this reply's tool rounds) are never dropped. In order:
    older tool results of this reply are reduced (`shrink(message)` returns a smaller
    copy or None), then older history/examples are dropped oldest first, then the newest
    tool result is reduced too. Messages marked `alt_keep` are dropped last.
    Returns (messages, used, changes) or raises RoundLimitError.
    """
    def size(message):
        total = cost(message.get('content') or '')
        if message.get('tool_calls'):
            total += cost(json.dumps(message['tool_calls'], ensure_ascii=False))
        return total + image_tokens * len(message.get('images') or [])

    messages = list(messages)
    used = sum(size(m) for m in messages)
    changes = {'shrunk': 0, 'dropped': 0}
    if used <= limit:
        return messages, used, changes

    def reduce(index):
        nonlocal used
        smaller = shrink(messages[index])
        if smaller is None:
            return
        used += size(smaller) - size(messages[index])
        messages[index] = smaller
        changes['shrunk'] += 1

    results = [i for i, m in enumerate(messages) if i > fixed and m.get('role') == 'tool']
    for index in results[:-1]:
        reduce(index)
        if used <= limit:
            return messages, used, changes
    # Oldest history first; a message marked alt_keep (the continuity summary) outlives the raw messages.
    while used > limit:
        index = next((i for i in range(1, fixed) if not messages[i].get('alt_keep')), None)
        if index is None:
            break
        used -= size(messages.pop(index))
        fixed -= 1
        changes['dropped'] += 1
    if used > limit and results:
        reduce(results[-1] - changes['dropped'])
    while used > limit and fixed > 1:
        used -= size(messages.pop(1))
        fixed -= 1
        changes['dropped'] += 1
    if used > limit:
        raise RoundLimitError(
            'Os resultados das ferramentas desta resposta não cabem mais no contexto deste perfil. '
            'O que já foi obtido está nos cartões acima; peça a próxima etapa numa nova mensagem '
            'ou escolha um perfil com mais contexto.')
    return messages, used, changes
