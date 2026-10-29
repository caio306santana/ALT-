"""Authenticated queue consumed only by Electron main, never by web content."""
import threading
import time
from uuid import uuid4

class DesktopBridge:
    def __init__(self, engine):
        self.engine = engine; self.jobs = {}; self.lock = threading.RLock();self.snapshot=None

    def request(self, payload, cancel, timeout=30):
        jid = str(uuid4()); done = threading.Event()
        job = {'id':jid, 'payload':payload, 'claimed':False, 'done':done,
               'cancel':cancel, 'deadline':time.monotonic()+timeout, 'result':None, 'error':None}
        with self.lock: self.jobs[jid] = job
        try:
            while not done.wait(.1):
                if cancel.is_set() or self.engine.stopped: raise PermissionError('Ação interrompida.')
                if time.monotonic() > job['deadline']: raise ValueError('O navegador não respondeu. Abra a ALT desktop e tente novamente.')
            if cancel.is_set() or self.engine.stopped: raise PermissionError('Ação interrompida.')
            if job['error']: raise ValueError(job['error'])
            return job['result']
        finally:
            with self.lock: self.jobs.pop(jid, None)

    def alive(self, job):
        return not self.engine.stopped and not job['cancel'].is_set() and time.monotonic()<job['deadline'] and not job['done'].is_set()

    def claim(self):
        with self.lock:
            for job in self.jobs.values():
                if not job['claimed'] and self.alive(job):
                    job['claimed'] = True
                    return {'id':job['id'], 'payload':job['payload']}
        return None

    def active(self, jid):
        with self.lock:
            return jid in self.jobs and self.alive(self.jobs[jid])

    def finish(self, jid, result=None, error=None):
        with self.lock:
            job = self.jobs.get(jid)
            if not job or not self.alive(job): return False
            if result and result.get('snapshot_id') and isinstance(result.get('elements'),list):self.snapshot=result
            job['result'], job['error'] = result, error
            job['done'].set(); return True
