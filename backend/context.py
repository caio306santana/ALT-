"""Byte-bounded tool excerpts. Never trim user instructions or selected memories."""
import json
import sys
import hashlib
from pathlib import Path
from functools import lru_cache


@lru_cache(maxsize=1)
def qwen_tokenizer():
    from tokenizers import Tokenizer
    root=Path(sys.executable).parent/'tokenizers' if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[1]/'assets'/'tokenizers'
    path=root/'qwen3.5.json';metadata=json.loads((root/'provenance.json').read_text(encoding='utf-8'))
    if hashlib.sha256(path.read_bytes()).hexdigest()!=metadata['sha256']:raise ValueError('Metadados de tokenização alterados. Reinstale o pacote validado da ALT.')
    return Tokenizer.from_file(str(path))

def message_cost(text,model=None):
    if model and (model.lower().startswith('qwen3.5:') or model.lower().startswith('huihui_ai/qwen3.5-abliterated:')):
        # Count the model family's actual BPE tokens, reserving role/template
        # overhead separately. UTF-8 bytes are not treated as individual tokens.
        return len(qwen_tokenizer().encode(text,add_special_tokens=False).ids)+32
    # Conservative fallback for other models whose tokenizer is not bundled.
    return len(text.encode('utf-8')) + 32


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
