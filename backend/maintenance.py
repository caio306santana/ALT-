"""Consistent local backups and validated restoration; never export credentials."""
import hashlib
import io
import json
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4
from backend.memory.migrations import SCHEMA_VERSION,migrate

class Maintenance:
    def __init__(self,store,data_dir,engine,tools):
        self.store,self.data_dir,self.engine,self.tools=store,data_dir,engine,tools
        self.folder=data_dir/'backups';self.folder.mkdir(exist_ok=True)
        self.daily()

    def snapshot(self,prefix='manual'):
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
        destination=self.folder/f'{prefix}-{stamp}-{str(uuid4())[:8]}.sqlite3'
        with self.store.lock,closing(sqlite3.connect(destination)) as backup:self.store.db.backup(backup)
        return destination

    def daily(self):
        today=datetime.now(timezone.utc).strftime('%Y%m%d')
        if not list(self.folder.glob('daily-'+today+'*.sqlite3')):self.snapshot('daily')
        files=sorted(self.folder.glob('daily-*.sqlite3'),key=lambda p:p.name,reverse=True)
        for old in files[7:]:old.unlink()

    def export(self):
        snapshot=self.snapshot();raw=snapshot.read_bytes()
        if len(raw)>60_000_000:raise ValueError('Backup excede o limite de exportação de 60 MB. Use uma cópia privada do diretório de dados com a ALT encerrada.')
        metadata={'format':'alt-ai-backup','version':1,'app_version':'0.5.5','db_schema':SCHEMA_VERSION,'sha256':hashlib.sha256(raw).hexdigest(),'created':datetime.now(timezone.utc).isoformat(),'credentials_included':False}
        output=io.BytesIO()
        with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('database.sqlite3',raw);archive.writestr('manifest.json',json.dumps(metadata))
        self.store.audit('backup_exported');return output.getvalue()

    def status(self):
        rows=self.store.rows('SELECT * FROM schema_migrations ORDER BY version')
        return {'schema':SCHEMA_VERSION,'migrations':rows,'backups':len(list(self.folder.glob('*.sqlite3'))),'active_operations':len(self.engine.active),'credentials_in_backup':False}

    def restore(self,data):
        if self.engine.active:raise ValueError('Interrompa as tarefas e aguarde o encerramento antes de restaurar.')
        if len(data)>64_000_000:raise ValueError('Backup grande demais.')
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if sorted(archive.namelist())!=['database.sqlite3','manifest.json']:raise ValueError('Formato de backup não reconhecido.')
                if sum(i.file_size for i in archive.infolist())>64_000_000:raise ValueError('Backup expandido excede o limite.')
                metadata=json.loads(archive.read('manifest.json'));raw=archive.read('database.sqlite3')
        except (zipfile.BadZipFile,json.JSONDecodeError,KeyError) as exc:raise ValueError('Arquivo não é um backup válido da ALT.') from exc
        if metadata.get('format')!='alt-ai-backup' or metadata.get('version')!=1 or metadata.get('credentials_included') is not False:raise ValueError('Manifesto de backup inválido.')
        if hashlib.sha256(raw).hexdigest()!=metadata.get('sha256'):raise ValueError('Backup alterado ou corrompido.')
        with tempfile.TemporaryDirectory(prefix='alt-restore-') as directory:
            path=Path(directory)/'database.sqlite3';path.write_bytes(raw)
            with closing(sqlite3.connect(path)) as restored:
                if restored.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Banco do backup está corrompido.')
                version=restored.execute('PRAGMA user_version').fetchone()[0]
                if version>SCHEMA_VERSION or version!=metadata.get('db_schema'):raise ValueError('Versão de banco incompatível.')
                if restored.execute("SELECT name FROM sqlite_master WHERE type IN ('trigger','view')").fetchone():raise ValueError('Backup contém estruturas não suportadas.')
                tables={r[0] for r in restored.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if not {'conversations','messages','settings','memories','schema_migrations'}.issubset(tables):raise ValueError('Faltam tabelas do aplicativo no backup.')
                for key,value in restored.execute('SELECT key,value FROM settings'):json.loads(value)
                # Device/window access is never carried over from an imported backup.
                for table in ('tool_authorization','windows_grants','scopes'):
                    if table in tables:restored.execute('DELETE FROM '+table)
                if 'actions' in tables:restored.execute("UPDATE actions SET status='interrupted' WHERE status IN ('running','proposed')")
                restored.commit();self.snapshot('pre-restore');self.engine.stop();self.tools.revoke()
                with self.store.lock:
                    self.store.db.commit();restored.backup(self.store.db);migrate(self.store.db,self.store.path)
            self.store.audit('backup_restored')
        return {'restored':True,'restart_required':True,'permissions_reset':True,'credentials_restored':False}
