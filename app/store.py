"""SQLite state: inbound log, outbox, cases. Due times live here so they survive a restart (D28)."""
import sqlite3
import threading
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS inbox (id INTEGER PRIMARY KEY, ts REAL, sender TEXT, line TEXT, role TEXT, body TEXT);
CREATE TABLE IF NOT EXISTS outbox (id INTEGER PRIMARY KEY, ts REAL, recipient TEXT, role TEXT, msg_id TEXT, body TEXT, case_code TEXT);
"""


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.lock = threading.RLock()

    def log_in(self, sender, line, role, body):
        with self.lock:
            self.db.execute("INSERT INTO inbox (ts, sender, line, role, body) VALUES (?,?,?,?,?)",
                            (time.time(), sender, line, role, body))

    def send(self, recipient, role, msg_id, body, case_code=None):
        """Write to the outbox. In this build an outbox write is the 'accepted for sending' event."""
        with self.lock:
            cur = self.db.execute(
                "INSERT INTO outbox (ts, recipient, role, msg_id, body, case_code) VALUES (?,?,?,?,?,?)",
                (time.time(), recipient, role, msg_id, body, case_code))
            return cur.lastrowid

    def outbox_since(self, since_id=0):
        with self.lock:
            rows = self.db.execute("SELECT * FROM outbox WHERE id > ? ORDER BY id", (since_id,)).fetchall()
        return [dict(r) for r in rows]

    def last_outbox_id(self):
        with self.lock:
            r = self.db.execute("SELECT COALESCE(MAX(id), 0) FROM outbox").fetchone()
        return r[0]
