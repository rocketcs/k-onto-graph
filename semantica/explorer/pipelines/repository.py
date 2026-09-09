"""SQLite records and immutable artifacts, scoped to one Explorer process."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path


def uid():
    return uuid.uuid4().hex


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class Conflict(ValueError):
    pass


class Repository:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(str(self.root / 'pipeline.sqlite3'), check_same_thread=False)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('PRAGMA foreign_keys=ON')
        version = self.db.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0, 1):
            raise RuntimeError('Unsupported pipeline database version')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS records(kind TEXT, id TEXT, body TEXT NOT NULL, PRIMARY KEY(kind,id));
            CREATE TABLE IF NOT EXISTS events(run_id TEXT, seq INTEGER, body TEXT NOT NULL, PRIMARY KEY(run_id,seq));
            CREATE TABLE IF NOT EXISTS requests(scope TEXT, key TEXT, hash TEXT, result TEXT, PRIMARY KEY(scope,key));
            PRAGMA user_version=1;
        ''')

    @contextmanager
    def transaction(self):
        with self.lock:
            self.db.execute('BEGIN IMMEDIATE')
            try:
                yield
                self.db.commit()
            except BaseException:
                self.db.rollback()
                raise

    def get(self, kind, identity):
        with self.lock:
            row = self.db.execute('SELECT body FROM records WHERE kind=? AND id=?', (kind, identity)).fetchone()
            if not row:
                raise KeyError(identity)
            return json.loads(row[0])

    def put(self, kind, identity, body):
        self.db.execute('INSERT OR REPLACE INTO records VALUES(?,?,?)', (kind, identity, json.dumps(body, ensure_ascii=False)))

    def all(self, kind):
        with self.lock:
            return [json.loads(r[0]) for r in self.db.execute('SELECT body FROM records WHERE kind=? ORDER BY rowid DESC', (kind,))]

    def once(self, scope, key, payload, action):
        if not isinstance(key, str) or not 8 <= len(key) <= 160:
            raise ValueError('request_key must contain 8-160 characters')
        with self.transaction():
            row = self.db.execute('SELECT hash,result FROM requests WHERE scope=? AND key=?', (scope, key)).fetchone()
            if row:
                if row[0] != digest(payload):
                    raise Conflict('request_key was already used with different input')
                return json.loads(row[1])
            result = action()
            self.db.execute('INSERT INTO requests VALUES(?,?,?,?)', (scope, key, digest(payload), json.dumps(result)))
            return result

    def event(self, run, event, **data):
        # Caller holds the transaction: state and its last event are committed together.
        import time
        seq = run.get('last_event_seq', 0) + 1
        item = {'run_id': run['id'], 'seq': seq, 'event': event, 'timestamp': time.time(), **data}
        self.db.execute('INSERT INTO events VALUES(?,?,?)', (run['id'], seq, json.dumps(item, ensure_ascii=False)))
        run['last_event_seq'] = seq
        self.put('run', run['id'], run)

    def events(self, run_id, after, limit):
        with self.lock:
            run = self.get('run', run_id)
            rows = self.db.execute('SELECT body FROM events WHERE run_id=? AND seq>? ORDER BY seq LIMIT ?',
                                   (run_id, after, limit)).fetchall()
            items = [json.loads(r[0]) for r in rows]
            next_seq = items[-1]['seq'] if items else after
            return {'items': items, 'next_seq': next_seq, 'has_more': next_seq < run['last_event_seq'],
                    'snapshot_last_seq': run['last_event_seq']}

    def blob(self, data, suffix='.json'):
        identity = hashlib.sha256(data).hexdigest()
        path = self.root / 'artifacts' / (identity + suffix)
        path.parent.mkdir(exist_ok=True)
        if not path.exists():
            fd, temporary = tempfile.mkstemp(dir=str(path.parent))
            try:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, path)
                directory = os.open(str(path.parent), os.O_RDONLY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        return path.name

    def artifact(self, value):
        return self.blob(json.dumps(value, ensure_ascii=False).encode())

    def read(self, key):
        if Path(key).name != key:
            raise ValueError('Invalid artifact key')
        path = self.root / 'artifacts' / key
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != key.split('.')[0]:
            raise ValueError('Artifact checksum mismatch')
        return json.loads(raw)

    def clear_pipeline_data(self):
        """Remove all run history and generated artifacts, preserving definitions."""
        with self.transaction():
            self.db.execute("DELETE FROM events")
            self.db.execute("DELETE FROM requests WHERE scope LIKE 'pipeline%'")
            self.db.execute("DELETE FROM records WHERE kind IN ('run','document','chunk_result','publication')")
        artifacts = self.root / 'artifacts'
        if artifacts.exists():
            for path in artifacts.iterdir():
                if path.is_file():
                    path.unlink()

    def close(self):
        with self.lock:
            self.db.close()
