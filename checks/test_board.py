"""Case board: rendered from stored records only; danger first, then oldest; reminders computed from stored times."""
import time

from app import board, messages as M
from app.cg_tests import CHP7, Env, P1, P2, P3
from app.engine import Protocol

PROTO = Protocol.load("config/protocol.yaml", run_suite=False)


def test_board_from_records_sorted_with_reminders():
    e = Env(PROTO)
    a = e.send(P1, "parent", "child 18m has a rash")[0]["case_code"]           # to check (no sign)
    e.send(CHP7, "chp", f"{a} 0")                                             # closed with 0
    b = e.send(P2, "parent", "child 2 years has fits")[0]["case_code"]        # referred, danger
    e.send("+254711000100", "facility", b)                                    # arrived
    c = e.send(CHP7, "chp", "18m homa siku 3")[0]["case_code"]                # CHP's own case, to check
    rows = board.board(e.store, CHP7, PROTO)
    assert [r["code"] for r in rows] == [b, a, c]                             # danger first, then oldest
    rb, ra, rc = rows
    assert rb["danger"] and rb["status"] == "arrived" and rb["signs"] == ["convulsions"]
    assert ra["status"] == "closed" and not ra["danger"] and rc["status"] == "to check"
    n = PROTO.params["followup_days"] * 86400
    arrived_at = e.store.case(b)["state"]["arrived_at"]
    assert rb["reminder"] == M.FOLLOWUP_REFERRED.format(date=time.strftime("%a %d %b", time.localtime(arrived_at + n)))
    closed_at = e.store.case(a)["updated"]
    assert ra["reminder"] == M.FOLLOWUP_HOME.format(date=time.strftime("%a %d %b", time.localtime(closed_at + n)))
    assert rc["reminder"] is None


def test_no_reply_status():
    e = Env(PROTO)
    e.send(P3, "parent", "mtoto miezi 12 ana mafua")
    e.fire()
    rows = board.board(e.store, "+254722000108", PROTO)
    assert rows[0]["status"] == "no reply"


def test_reminder_strings_say_only_when():
    from app.cg_tests import BLOCKED, SIGN_WORDS
    import re
    for s in (M.FOLLOWUP_REFERRED, M.FOLLOWUP_HOME):
        low = s.lower()
        assert not any(re.search(r"(?<!\w)" + re.escape(b) + r"(?!\w)", low) for b in BLOCKED)
        assert not any(re.search(r"\b" + w + r"\b", low) for w in SIGN_WORDS)
        assert s.endswith("Follow your chart booklet.")
