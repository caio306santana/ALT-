"""One-use receipts bind the exact previewed provider, context and request."""
import hashlib
import json
import secrets
import time

def digest(payload):return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

class ConsentReceipts:
    def __init__(self):self.pending={}
    def issue(self,payload):
        self.pending={k:v for k,v in self.pending.items() if v[0]>time.monotonic()}
        if len(self.pending)>=100:self.pending.pop(next(iter(self.pending)))
        receipt=secrets.token_urlsafe(32)
        self.pending[receipt]=(time.monotonic()+300,digest(payload))
        return receipt
    def consume(self,receipt,payload):
        entry=self.pending.pop(receipt,None)
        if not entry or entry[0]<time.monotonic() or not secrets.compare_digest(entry[1],digest(payload)):
            raise PermissionError('A prévia expirou ou o contexto mudou. Revise e autorize novamente.')
    def revoke_all(self):self.pending.clear()
