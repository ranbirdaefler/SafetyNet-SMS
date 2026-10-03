"""Must-stay privacy tests: (a) no name is stored or sent; (b) closed-case content is purged after retention_days."""
import re
import time

from app import messages as M
from app.cg_tests import CHP7, Env, P1, P2
from app.engine import Protocol

PROTO = Protocol.load("config/protocol.yaml", run_suite=False)


def test_no_name_field_anywhere():
    e = Env(PROTO)
    cols = [r[1] for t in ("cases", "outbox", "inbox") for r in e.store.db.execute(f"PRAGMA table_info({t})")]
    assert not any("name" in c.lower() for c in cols)
    for v in vars(M).values():                                  # no template has a slot for a name
        if isinstance(v, str):
            assert not re.search(r"\{[^}]*name[^}]*\}", v)
    e.send(P1, "parent", "Mtoto wangu Amina Wanjiku miezi 18 ana degedege")
    e.send(P2, "parent", "My son Baraka 18m has a rash")
    code = e.store.latest_case_for_parent(P2)["code"]
    e.send(CHP7, "chp", f"{code} Baraka is fine 0")
    for m in e.all:                                             # no outgoing SMS repeats a parent's words
        assert "Amina" not in m["body"] and "Baraka" not in m["body"] and "Wanjiku" not in m["body"]
    for r in e.store.db.execute("SELECT state FROM cases"):     # case records keep no free text
        assert "Amina" not in r[0] and "Baraka" not in r[0]


def test_retention_purge():
    e = Env(PROTO)
    e.send(P1, "parent", "mtoto miezi 18 ana degedege")         # referred
    e.send(P2, "parent", "child 18m has a rash")                # open (ASK_SIGNS)
    days = PROTO.params["retention_days"]
    assert e.store.purge(days) == {"cases": 0, "outbox": 0, "inbox": 0}      # nothing old yet
    later = time.time() + (days + 1) * 86400
    n = e.store.purge(days, now=later)
    assert n["cases"] == 1 and n["outbox"] >= 3
    remaining = [r[0] for r in e.store.db.execute("SELECT status FROM cases")]
    assert remaining == ["ASK_SIGNS"]                           # the open case is kept
    senders = [r[0] for r in e.store.db.execute("SELECT sender FROM inbox")]
    assert senders == [P2]                                      # only the open case's inbound text is kept
