"""Door timeouts (D19, D20), late replies (D21, D22), A1 window, restart reload (D28)."""
import os
import tempfile
import time

from fastapi.testclient import TestClient

os.environ["SNS_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")
os.environ["SNS_TIMER"] = "0"
from app import service  # noqa: E402
from app.server import app, STORE, REGISTRY, STATE  # noqa: E402

c = TestClient(app)
P1, P2 = "+254733000001", "+254733000002"
CHP7, FAC, CHA = "+254722000107", "+254711000100", "+254711000200"
LATER = time.time() + 10 ** 6


def send(ph, line, body):
    return [(m["recipient"], m["msg_id"], m["body"]) for m in
            c.post("/sms", json={"from": ph, "to": line, "body": body}).json()["replies"]]


def fire():
    before = STORE.last_outbox_id()
    service.tick(STORE, REGISTRY, STATE["protocol"], now=LATER)
    return [(m["recipient"], m["msg_id"], m["body"]) for m in STORE.outbox_since(before)]


def ids(r):
    return [(to, mid) for to, mid, _ in r]


def close_all():
    for row in STORE.db.execute("SELECT code FROM cases").fetchall():
        STORE.update_case(row[0], status="CLOSED")


def test_d19_no_chp_reply_then_late_replies():
    close_all()
    r = send(P1, "40100", "mtoto miezi 18 ana mafua")
    code = r[0][2].split()[0]
    assert service.tick(STORE, REGISTRY, STATE["protocol"]) == 0          # not due yet
    r = fire()
    assert ids(r) == [(FAC, "ALERT"), (CHA, "ALERT"), (CHP7, "CHP_TIMEOUT"), (P1, "CG_TIMEOUT")]
    assert "no CHP reply" in r[0][2]
    assert ids(send(CHP7, "40101", f"{code} 0")) == [(CHP7, "REFERRED_LINE"), (CHA, "REFERRED_LINE")]   # D22
    r = send(CHP7, "40101", f"{code} 5")                                     # D21: reasons added, parent not re-sent
    assert ids(r) == [(FAC, "ALERT"), (CHA, "ALERT"), (CHP7, "REFER_NOW")] and "chest indrawing" in r[2][2]
    assert ids(send(P1, "40100", "asante")) == [(P1, "CG_GO_NOW")]          # CG18: repeat only


def test_d20_started_not_finished():
    close_all()
    r = send(P2, "40100", "mtoto miezi 18 ana mafua")
    code = r[0][2].split()[0]
    send(CHP7, "40101", f"{code} sawa")                                    # one unparseable reply: still open
    r = fire()
    assert ids(r) == [(FAC, "ALERT"), (CHA, "ALERT"), (CHP7, "CHP_GO_NOW"), (P2, "CG_GO_NOW")]
    assert "not finished by due time" in r[0][2]


def test_chp_silence_a3_and_non_red_window():
    close_all()
    r = send(CHP7, "40101", "18m homa siku 3")
    r = fire()
    assert ids(r)[-1] == (CHP7, "REFER_NOW") and "no answer" in r[-1][2]
    close_all()
    r = send(CHP7, "40101", "18m homa siku 3")
    code = r[0][2].split()[0]
    assert ids(send(CHP7, "40101", f"{code} 0")) == [(CHP7, "NON_RED")]
    assert fire() == []                                                     # a closed case never times out
    r = send(CHP7, "40101", "4")                                            # A1: a digit within 24 h refers
    assert ids(r)[-1] == (CHP7, "REFER_NOW")
