"""What an action really did, and the boundary around text that came from outside.

Idea from Mark LVI (core/outcome.py): a tool says `done` only when it observed the result. Small models
round "request sent" up to "done", so every other state carries a fixed instruction for the model."""
import re

STATES=('done','unverified','failed','ask','started')
NOTES={
    'done':'',
    'unverified':'NÃO CONFIRMADO: o pedido foi enviado, mas o resultado não pôde ser observado. Não diga que foi feito; diga que foi pedido e não confirmado.',
    'failed':'FALHOU: diga ao usuário o que falhou, em uma frase, sem fingir sucesso.',
    'ask':'NADA FOI FEITO: falta uma escolha do usuário. Faça uma pergunta curta com as opções.',
    'started':'EM ANDAMENTO: ainda não terminou. Não diga que terminou.',
}

def outcome(state,**facts):
    if state not in STATES:raise ValueError('Estado de ação desconhecido.')
    return {'status':state,**facts}

def note(result):
    """Instruction appended for the model next to an action result."""
    return NOTES.get((result or {}).get('status','done'),'')

def chat_line(result):
    """Line the chat adds after an action that ran by itself."""
    state=(result or {}).get('status','done')
    if state=='done':return 'Ferramenta concluída conforme suas autorizações. O resultado confirmado está no cartão abaixo.'
    if state=='unverified':return 'Pedido enviado, mas não consegui confirmar o resultado. Detalhes no cartão abaixo.'
    if state=='ask':return 'Preciso que você escolha antes de continuar: veja o cartão abaixo.'
    if state=='started':return 'Ação iniciada; ela continua em segundo plano.'
    return 'A ação falhou. Detalhes no cartão abaixo.'

# Short on purpose: the notebook profile has little room left for a page or tool observation.
OPEN='<<<DADOS {source}>>>'
CLOSE='<<<FIM DADOS>>>'
MARKERS=re.compile(r'<<<\s*/?\s*(?:FIM\s+)?DADOS[^>]*>>>',re.I)
TEMPLATE=re.compile(r'<\|(?:im_start|im_end|endoftext|system|user|assistant)\|>',re.I)

def untrusted(source,text):
    """Wrap outside content as data. Markers or chat-template tokens inside it are defanged, so a page
    cannot close the boundary early and speak as the user or the system."""
    clean=MARKERS.sub('[marcador removido]',str(text))
    clean=TEMPLATE.sub('[token removido]',clean)
    return OPEN.format(source=re.sub(r'[^\w.:/ -]','',source)[:60])+'\n'+clean+'\n'+CLOSE

def unwrap(text):
    """For display only: drop the boundary markers."""
    return re.sub(r'<<<DADOS [^>]*>>>\n?|\n?<<<FIM DADOS>>>','',text)

def injected(text):
    """True when outside text tries to speak with chat-template tokens or boundary markers."""
    return bool(TEMPLATE.search(str(text)) or MARKERS.search(str(text)))
