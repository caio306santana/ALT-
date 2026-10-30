"""Remembered approvals, session taint and undo.

- "Sempre permitir" (OpenJarvis tools/approval_store.py): low-risk targets the owner approved once run by
  themselves in modes 2-3. Commands, closing programs, writing files and downloads are never remembered.
- Taint (OpenJarvis security/taint.py): after a read brings secrets, personal data or chat-template
  tokens into a conversation, actions that could send data out wait for the card again, even in mode 4.
- Undo (Mark LVI core/undo.py): file writes and downloads keep what is needed to revert them."""
import hashlib
import json
import os
import re
import urllib.parse
from pathlib import Path
from uuid import uuid4
from backend.memory.store import now
from backend.memory.library import reject_secrets
from backend.tools.outcome import injected,outcome

REMEMBERABLE={'open_app','open_url','open_folder'}
# Actions that can carry data out of the conversation or change things on its behalf.
SINKS={'open_url','web_search','read_webpage','download_file','find_download','generate_image','write_text','windows_type','windows_keys','windows_invoke',
       'browser_open','browser_type','browser_click','run_command'}
CPF=re.compile(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b')
CARD=re.compile(r'\b(?:\d[ -]?){13,19}\b')

def luhn(number):
    digits=[int(d) for d in re.sub(r'\D','',number)][::-1]
    return len(digits)>=13 and sum(d if i%2==0 else (d*2-9 if d*2>9 else d*2) for i,d in enumerate(digits))%10==0

def sensitive_reason(text):
    """Why outside text makes the conversation sensitive, or ''."""
    text=str(text)
    try:reject_secrets(text)
    except ValueError:return 'uma credencial apareceu no conteúdo lido'
    if CPF.search(text):return 'um CPF apareceu no conteúdo lido'
    if any(luhn(m.group()) for m in CARD.finditer(text)):return 'um número de cartão apareceu no conteúdo lido'
    if injected(text):return 'o conteúdo lido tentou falar como sistema ou usuário'
    return ''

def target_of(tool,payload):
    if tool=='open_app':return payload.get('app','')
    if tool=='open_url':return (urllib.parse.urlsplit(payload.get('url','')).hostname or '').removeprefix('www.')
    if tool=='open_folder':return payload.get('scope_id','')+':'+payload.get('path','')
    return ''

class RememberedApprovals:
    def __init__(self,store):
        self.store=store
        store.db.execute('CREATE TABLE IF NOT EXISTS remembered_approvals(id TEXT PRIMARY KEY,tool TEXT NOT NULL,target TEXT NOT NULL,created TEXT NOT NULL,UNIQUE(tool,target))');store.db.commit()

    def remember(self,tool,payload):
        target=target_of(tool,payload)
        if tool not in REMEMBERABLE or not target:raise ValueError('Esta ação não pode ser permitida para sempre; ela continua pedindo aprovação.')
        self.store.write('INSERT OR IGNORE INTO remembered_approvals VALUES(?,?,?,?)',(str(uuid4()),tool,target,now()))
        self.store.audit('approval_remembered',json.dumps({'tool':tool,'target':target},ensure_ascii=False))
        return {'tool':tool,'target':target}

    def allows(self,tool,payload):
        target=target_of(tool,payload)
        return bool(target) and tool in REMEMBERABLE and bool(self.store.rows('SELECT id FROM remembered_approvals WHERE tool=? AND target=?',(tool,target)))

    def list(self):return self.store.rows('SELECT id,tool,target,created FROM remembered_approvals ORDER BY created DESC')
    def remove(self,rid):self.store.write('DELETE FROM remembered_approvals WHERE id=?',(rid,))

def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).is_file() else None

class Undo:
    """What a file write or a download needs to be reverted, kept per action."""
    def __init__(self,store):
        self.store=store
        store.db.execute('CREATE TABLE IF NOT EXISTS undo_entries(action_id TEXT PRIMARY KEY,kind TEXT NOT NULL,data TEXT NOT NULL,created TEXT NOT NULL,used INTEGER NOT NULL DEFAULT 0)');store.db.commit()

    def record(self,aid,tool,result):
        if not isinstance(result,dict) or result.get('status','done')!='done':return None
        if tool=='write_text' and result.get('path'):
            data={'path':result['path'],'previous':result.get('previous_version'),'written':file_digest(result['path'])}
        elif tool in ('download_file','find_download') and result.get('path'):
            data={'path':result['path'],'written':result.get('sha256')}
        elif tool in ('system_volume','system_brightness') and 'before' in result:
            data={'tool':tool,'before':result['before']}
        else:return None
        self.store.write('INSERT OR REPLACE INTO undo_entries VALUES(?,?,?,?,0)',(aid,tool,json.dumps(data,ensure_ascii=False),now()))
        return aid

    def available(self,aid):return bool(self.store.rows('SELECT action_id FROM undo_entries WHERE action_id=? AND used=0',(aid,)))

    def last(self):
        rows=self.store.rows('SELECT action_id FROM undo_entries WHERE used=0 ORDER BY created DESC LIMIT 1')
        return rows[0]['action_id'] if rows else None

    def run(self,aid,setters=None):
        rows=self.store.rows('SELECT kind,data FROM undo_entries WHERE action_id=? AND used=0',(aid,))
        if not rows:raise ValueError('Não há nada para desfazer nesta ação.')
        kind,data=rows[0]['kind'],json.loads(rows[0]['data'])
        if kind in ('write_text','download_file'):
            path=Path(data['path'])
            # Never clobber a change made after the ALT's own write.
            if file_digest(path)!=data.get('written'):
                return outcome('failed',notice='O arquivo mudou depois da ação da ALT; nada foi desfeito para não perder essa mudança.')
            if data.get('previous') and Path(data['previous']).is_file():
                path.write_bytes(Path(data['previous']).read_bytes());message=f'Versão anterior de {path.name} restaurada.'
            else:
                os.remove(path);message=f'{path.name} removido.'
        else:
            if not setters or kind not in setters:raise ValueError('Desfazer indisponível para esta ação.')
            setters[kind](data['before']);message='Valor anterior restaurado.'
        self.store.write('UPDATE undo_entries SET used=1 WHERE action_id=?',(aid,))
        self.store.audit('action_undone',aid)
        return outcome('done',undone=aid,notice=message)
