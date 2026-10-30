"""Turn streamed model text into sentences worth saying aloud.

From Mark LVI (providers/engine_pipeline.py) and OpenJarvis (frontend message-text.ts): drop reasoning
blocks even when a tag is split across chunks, cut at sentence ends that are followed by a space (so
"3.14" survives), force a cut on long unpunctuated runs, and strip code, links, markdown and emoji."""
import re

OPEN_TAGS=('<think>','<thinking>','<reasoning>')
CLOSE_TAGS=('</think>','</thinking>','</reasoning>')
HOLD=11  # longest tag minus one: a tag split across chunks is never spoken
SENTENCE=re.compile(r'(.+?[.!?…:;])(\s+)',re.S)
MAX_RUN=320
EMOJI=re.compile('[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF️]')
APP_LINES=re.compile(r'^(Ferramenta concluída|Preparei uma proposta|Pedido enviado|A ação falhou|Preciso que você escolha|Ação iniciada|Não consegui executar)[^\n]*',re.M)

def speakable(text):
    text=re.sub(r'```.*?```',' (código na tela) ',text,flags=re.S)
    text=re.sub(r'`([^`]*)`',r'\1',text)
    text=re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',text)
    text=re.sub(r'https?://\S+','',text)
    text=APP_LINES.sub('',text)
    text=re.sub(r'^\s{0,3}(#{1,6}|[-*+]|\d+\.)\s+','',text,flags=re.M)
    text=re.sub(r'[*_~#>|]','',text)
    text=EMOJI.sub('',text)
    return re.sub(r'\s+',' ',text).strip()

class SpeechText:
    def __init__(self):self.pending='';self.hidden=False;self.raw=''

    def _visible(self,flush=False):
        """Text outside reasoning blocks that is safe to release now."""
        out=''
        while self.raw:
            lower=self.raw.lower()
            if self.hidden:
                ends=[(lower.find(t),t) for t in CLOSE_TAGS if t in lower]
                if not ends:
                    self.raw='' if flush else self.raw[-HOLD:];break
                index,tag=min(ends);self.raw=self.raw[index+len(tag):];self.hidden=False;continue
            starts=[(lower.find(t),t) for t in OPEN_TAGS if t in lower]
            if starts:
                index,tag=min(starts);out+=self.raw[:index];self.raw=self.raw[index+len(tag):];self.hidden=True;continue
            if flush:out+=self.raw;self.raw=''
            else:
                cut=max(0,len(self.raw)-HOLD);lt=self.raw.rfind('<',cut)
                cut=lt if lt!=-1 else len(self.raw)
                out+=self.raw[:cut];self.raw=self.raw[cut:]
            break
        return out

    def feed(self,delta):
        """New model text -> complete sentences ready to speak."""
        self.raw+=delta;self.pending+=self._visible()
        sentences=[]
        while True:
            match=SENTENCE.match(self.pending)
            if match:
                sentences.append(match.group(1));self.pending=self.pending[match.end():];continue
            if len(self.pending)>MAX_RUN:
                cut=self.pending.rfind(' ',0,MAX_RUN)
                cut=cut if cut>0 else MAX_RUN
                sentences.append(self.pending[:cut]);self.pending=self.pending[cut:];continue
            break
        return [s for s in (speakable(x) for x in sentences) if s]

    def flush(self):
        self.pending+=self._visible(flush=True)
        rest=speakable(self.pending);self.pending=''
        return [rest] if rest else []
