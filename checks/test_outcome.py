"""Counter-referral: facility outcome codes after ARRIVED. One test per rule; the parent never receives anything."""
from app import board, messages as M
from app.board import DAY, _date
from app.cg_tests import CHA, CHP7, FAC, P2, Env
from app.engine import Protocol

PROTO = Protocol.load("config/protocol.yaml", run_suite=False)
N = PROTO.params["followup_days"]


def arrived_case(e):
    code = e.send(P2, "parent", "child 2 years has fits")[0]["case_code"]
    e.send(FAC, "facility", code)
    return code


def ids(out):
    return [(m["recipient"], m["msg_id"]) for m in out]


def row(e, code):
    return [r for r in board.board(e.store, CHP7, PROTO) if r["code"] == code][0]


def test_admitted_recorded_and_check_in_kept():
    e = Env(PROTO)
    code = arrived_case(e)
    arrived_at = e.store.case(code)["state"]["arrived_at"]
    assert ids(e.send(FAC, "facility", f"{code} A")) == [(CHP7, "OUTCOME"), (CHA, "OUTCOME"), (FAC, "OUTCOME_ACK")]
    r = row(e, code)
    assert r["status"] == "admitted"
    assert r["reminder"] == M.FOLLOWUP_REFERRED.format(date=_date(arrived_at + N * DAY))     # 3-day check-in kept


def test_referred_on_keeps_check_in():
    e = Env(PROTO)
    code = arrived_case(e)
    arrived_at = e.store.case(code)["state"]["arrived_at"]
    e.send(FAC, "facility", f"{code} r")
    r = row(e, code)
    assert r["status"] == "referred on"
    assert r["reminder"] == M.FOLLOWUP_REFERRED.format(date=_date(arrived_at + N * DAY))


def test_treated_moves_reminder_to_day_n():
    e = Env(PROTO)
    code = arrived_case(e)
    e.send(FAC, "facility", f"{code} T5")
    at = e.store.case(code)["state"]["outcome"]["at"]
    r = row(e, code)
    assert r["status"] == "treated, sent home, follow-up day 5"
    assert r["reminder"] == M.FOLLOWUP_REFERRED.format(date=_date(at + 5 * DAY))


def test_rejected_before_arrival():
    e = Env(PROTO)
    code = e.send(P2, "parent", "child 2 years has fits")[0]["case_code"]
    assert ids(e.send(FAC, "facility", f"{code} A")) == [(FAC, "OUTCOME_REJECT")]
    case = e.store.case(code)
    assert "outcome" not in case["state"] and case["status"] == "REFERRED"   # not taken as an arrival either


def test_facility_numbers_only():
    e = Env(PROTO)
    code = arrived_case(e)
    assert ids(e.send(CHA, "facility", f"{code} A")) == [(CHA, "OUTCOME_REJECT")]
    assert e.send("+254700000999", "facility", f"{code} A") == []              # unregistered: ignored as before
    assert "outcome" not in e.store.case(code)["state"]


def test_unknown_code_rejected():
    e = Env(PROTO)
    assert ids(e.send(FAC, "facility", "9999 A")) == [(FAC, "OUTCOME_REJECT")]


def test_t_days_out_of_range_rejected():
    e = Env(PROTO)
    code = arrived_case(e)
    for t in (f"{code} T0", f"{code} T31", f"{code} T99"):
        assert ids(e.send(FAC, "facility", t)) == [(FAC, "OUTCOME_REJECT")]
    assert "outcome" not in e.store.case(code)["state"]


def test_codes_only_free_text_is_not_an_outcome():
    e = Env(PROTO)
    code = e.send(P2, "parent", "child 2 years has fits")[0]["case_code"]
    out = e.send(FAC, "facility", f"{code} arrived")                          # free text still confirms arrival
    assert "ACK" in [m["msg_id"] for m in out]
    for t in (f"{code} child is better", f"{code} admitted", f"{code} A please"):
        assert all(m["msg_id"] != "OUTCOME_ACK" for m in e.send(FAC, "facility", t))
    assert "outcome" not in e.store.case(code)["state"]


def test_parent_never_messaged():
    e = Env(PROTO)
    code = arrived_case(e)
    for t in (f"{code} A", f"{code} T5", f"{code} R", f"{code} T99", f"{code} child is better"):
        assert all(m["role"] != "parent" for m in e.send(FAC, "facility", t))


def test_chw_reply_unaffected():
    e = Env(PROTO)
    code = e.send(P2, "parent", "child 18m has a rash")[0]["case_code"]
    assert "REFER_NOW" in [m["msg_id"] for m in e.send(CHP7, "chp", f"{code} 5")]
