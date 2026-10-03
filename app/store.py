"""SQLite state: inbound log, outbox, cases. Due times live here so they survive a restart (D28)."""
import json
import random
import sqlite3
import threading
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS inbox (id INTEGER PRIMARY KEY, ts REAL, sender TEXT, line TEXT, role TEXT, body TEXT);
CREATE TABLE IF NOT EXISTS cases (code TEXT PRIMARY KEY, chp_phone TEXT, parent_phone TEXT, origin TEXT,
  status TEXT, state TEXT, created REAL, updated REAL, due REAL, unparseable INTEGER DEFAULT 0);
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

    def inbox_since(self, since_id=0):
        with self.lock:
            rows = self.db.execute("SELECT * FROM inbox WHERE id > ? ORDER BY id", (since_id,)).fetchall()
        return [dict(r) for r in rows]

    def last_outbox_id(self):
        with self.lock:
            r = self.db.execute("SELECT COALESCE(MAX(id), 0) FROM outbox").fetchone()
        return r[0]

    # ---------- cases ----------
    OPEN_STATUSES = ("ASK_AGE", "ASK_SIGNS")

    def new_code(self):
        with self.lock:
            used = {r[0] for r in self.db.execute("SELECT code FROM cases WHERE status != 'CLOSED'")}
        while True:
            c = f"{random.randint(1000, 9999)}"
            if c not in used:
                return c

    def create_case(self, chp_phone, origin, state, status, parent_phone=None, due=None):
        code = self.new_code()
        now = time.time()
        with self.lock:
            self.db.execute("INSERT INTO cases (code, chp_phone, parent_phone, origin, status, state, created, updated, due)"
                            " VALUES (?,?,?,?,?,?,?,?,?)",
                            (code, chp_phone, parent_phone, origin, status, json.dumps(state), now, now, due))
        return code

    def update_case(self, code, **kw):
        if "state" in kw:
            kw["state"] = json.dumps(kw["state"])
        kw["updated"] = time.time()
        cols = ", ".join(f"{k} = ?" for k in kw)
        with self.lock:
            self.db.execute(f"UPDATE cases SET {cols} WHERE code = ?", (*kw.values(), code))

    def _case(self, row):
        if row is None:
            return None
        d = dict(row)
        d["state"] = json.loads(d["state"])
        return d

    def case(self, code):
        with self.lock:
            return self._case(self.db.execute("SELECT * FROM cases WHERE code = ?", (code,)).fetchone())

    def latest_case_for_chp(self, phone):
        with self.lock:
            return self._case(self.db.execute(
                "SELECT * FROM cases WHERE chp_phone = ? ORDER BY created DESC LIMIT 1", (phone,)).fetchone())
