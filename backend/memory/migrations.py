"""Ordered, transactional schema upgrades with a pre-upgrade SQLite snapshot."""
import sqlite3
from contextlib import closing
from datetime import datetime,timezone
from uuid import uuid4

SCHEMA_VERSION=2
MIGRATIONS={
1:'''CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY,title TEXT NOT NULL,created TEXT NOT NULL,updated TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY,conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE,role TEXT NOT NULL,content TEXT NOT NULL,model TEXT,status TEXT NOT NULL,created TEXT NOT NULL,metrics TEXT);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,event TEXT NOT NULL,detail TEXT NOT NULL,created TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS messages_conversation ON messages(conversation_id,created);''',
2:'''CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,name TEXT NOT NULL,created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS conversation_projects(conversation_id TEXT PRIMARY KEY REFERENCES conversations(id) ON DELETE CASCADE,project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,last_summary_count INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY,project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,name TEXT NOT NULL,sha256 TEXT NOT NULL,created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS document_chunks(id TEXT PRIMARY KEY,document_id TEXT REFERENCES documents(id) ON DELETE CASCADE,location TEXT NOT NULL,content TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS semantic_vectors(kind TEXT NOT NULL,item_id TEXT NOT NULL,content_hash TEXT NOT NULL,model_digest TEXT NOT NULL,vector TEXT NOT NULL,PRIMARY KEY(kind,item_id));
CREATE TABLE IF NOT EXISTS project_memories(project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,memory_id TEXT REFERENCES memories(id) ON DELETE CASCADE,PRIMARY KEY(project_id,memory_id));
CREATE TABLE IF NOT EXISTS project_summary_drafts(id TEXT PRIMARY KEY,project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE,payload TEXT NOT NULL,status TEXT NOT NULL,created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS agent_runs(id TEXT PRIMARY KEY,conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE,payload TEXT NOT NULL,updated TEXT NOT NULL);'''}

def migrate(connection,path):
    version=connection.execute('PRAGMA user_version').fetchone()[0]
    if version>SCHEMA_VERSION:raise ValueError('Banco criado por versão mais nova da ALT. Instale uma versão compatível; não faça downgrade sem backup.')
    had_data=connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'").fetchone()
    if had_data and version<SCHEMA_VERSION:
        folder=path.parent/'backups';folder.mkdir(exist_ok=True)
        destination=folder/('pre-migration-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+str(uuid4())[:8]+'.sqlite3')
        with closing(sqlite3.connect(destination)) as backup:connection.backup(backup)
    connection.execute('CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY,applied TEXT NOT NULL)');connection.commit()
    for current in range(version+1,SCHEMA_VERSION+1):
        try:
            stamp=datetime.now(timezone.utc).isoformat()
            connection.executescript('BEGIN IMMEDIATE;'+MIGRATIONS[current]+f"INSERT INTO schema_migrations VALUES({current},'{stamp}');PRAGMA user_version={current};COMMIT;")
        except Exception:connection.rollback();raise
