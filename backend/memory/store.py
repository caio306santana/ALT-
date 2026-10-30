import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from backend.memory.migrations import migrate

def now():
    return datetime.now(timezone.utc).isoformat()

class Store:
    def __init__(self, path: Path):
        self.path=path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON');migrate(self.db,path)
        self.db.executescript('''
          PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;
          CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY,title TEXT NOT NULL,created TEXT NOT NULL,updated TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY,conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE,role TEXT NOT NULL,content TEXT NOT NULL,model TEXT,status TEXT NOT NULL,created TEXT NOT NULL,metrics TEXT);
          CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,event TEXT NOT NULL,detail TEXT NOT NULL,created TEXT NOT NULL);
        ''')
        self.db.execute("UPDATE messages SET status='interrupted' WHERE status='streaming'")
        self.db.commit()

    def rows(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.db.execute(sql, args).fetchall()]

    def close(self):
        # sqlite must not be closed while a native worker is inside execute.
        with self.lock:self.db.close()

    def write(self, sql, args=()):
        with self.lock:
            self.db.execute(sql, args)
            self.db.commit()

    def create(self):
        cid = str(uuid4())
        self.write('INSERT INTO conversations VALUES(?,?,?,?)', (cid,'Nova conversa',now(),now()))
        return self.conversation(cid)

    def conversation(self, cid):
        rows = self.rows('SELECT * FROM conversations WHERE id=?', (cid,))
        return rows[0] if rows else None

    def messages(self, cid):
        result = self.rows('SELECT * FROM messages WHERE conversation_id=? ORDER BY rowid', (cid,))
        for row in result:
            row['metrics'] = json.loads(row['metrics']) if row['metrics'] else None
        return result

    def add(self, cid, role, content, model=None, status='complete'):
        mid = str(uuid4())
        self.write('INSERT INTO messages VALUES(?,?,?,?,?,?,?,?)', (mid,cid,role,content,model,status,now(),None))
        self.write('UPDATE conversations SET updated=? WHERE id=?', (now(),cid))
        return mid

    def checkpoint(self, mid, text, status, metrics=None):
        self.write('UPDATE messages SET content=?,status=?,metrics=? WHERE id=?', (text,status,json.dumps(metrics) if metrics else None,mid))

    def audit(self, event, detail=''):
        self.write('INSERT INTO audit(event,detail,created) VALUES(?,?,?)', (event,detail,now()))

    def settings(self):
        return {r['key']:json.loads(r['value']) for r in self.rows('SELECT * FROM settings')}

    def set_settings(self, settings):
        for key,value in settings.items():
            self.write('INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key,json.dumps(value)))
