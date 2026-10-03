"""slice (three-actor) and the main door paths."""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

os.environ["SNS_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")
from app.server import app, STORE  # noqa: E402

c = TestClient(app)
P1, P2, P3, P4, PU = "+254733000001", "+254733000002", "+254733000003", "+254733000004", "+254799000001"
CHP7, CHP8, FAC, CHA = "+254722000107", "+254722000108", "+254711000100", "+254711000200"


def send(ph, line, body):
    return [(m["recipient"], m["msg_id"], m["body"]) for m in
            c.post("/sms", json={"from": ph, "to": line, "body": body}).json()["replies"]]


def ids(r):
    return [(to, mid) for to, mid, _ in r]


def test_slice_three_actor():
    r = send(P1, "40100", "mtoto wangu miezi 18 ana homa siku 3")
    assert ids(r) == [(CHP7, "CHP_CALL"), (CHP7, "ASK_SIGNS"), (P1, "CG_TOLD")]
    code = r[0][2].split()[0]
    assert "homa" not in r[0][2] and "ana" not in r[1][2]          # C5: brief never has the parent's words
    r = send(CHP7, "40101", f"{code} 5")
    assert ids(r) == [(FAC, "ALERT"), (CHA, "ALERT"), (CHP7, "REFER_NOW"), (P1, "CG_GO_NOW")]
    assert "PARENT SMS: chest indrawing" in r[0][2]
    r = send(FAC, "40102", code)
    assert ids(r) == [(CHP7, "ARRIVED"), (CHA, "ARRIVED"), (FAC, "ACK")]


def test_parent_degedege_go_now():
    r = send(P2, "40100", "mtoto miezi 18 ana degedege")
    assert ids(r) == [(FAC, "ALERT"), (CHA, "ALERT"), (CHP7, "CHP_GO_NOW"), (P2, "CG_GO_NOW")]
    assert "PARENT SMS: convulsions" in r[0][2]
    assert ids(send(P2, "40100", "hana degedege sasa")) == [(P2, "CG_GO_NOW")]     # CG18 repeat only


def test_chp_zero_closes_without_telling_parent():
    r = send(P3, "40100", "mtoto miezi 12 ana mafua")
    code = r[0][2].split()[0]
    r = send(CHP8, "40101", f"{code} 0")
    assert ids(r) == [(CHP8, "NON_RED")]


def test_no_age_go_now():
    r = send(P3, "40100", "mtoto ana kikohozi")
    assert (P3, "CG_GO_NOW") in ids(r) and "age not received" in r[0][2] and "child age unknown" in r[0][2]


def test_no_chp_assigned():
    r = send(P4, "40100", "mtoto miezi 10 ana mafua")
    assert ids(r)[-1] == (P4, "CG_GO_NOW") and "no CHP assigned" in r[0][2]


def test_unregistered():
    r = send(PU, "40100", "mtoto miezi 10 hana degedege")
    assert ids(r) == [(CHA, "CHA_UNREG"), (PU, "CG_GO_NOW_U")]
    assert ids(send(PU, "40100", "degedege")) == [(PU, "CG_GO_NOW_U")]


def test_parent_allowlist_guard():
    with pytest.raises(ValueError):
        STORE.send(P1, "parent", "FREE_TEXT", "Give ORS and wait")
    with pytest.raises(ValueError):
        STORE.send(P1, "parent", "CG_GO_NOW", "Take the child home. It is fine.")


def test_umri_without_unit_goes_now_age_not_received():
    old = STORE.latest_case_for_parent(P3)
    if old:
        STORE.update_case(old["code"], status="CLOSED")          # D25: a closed case never absorbs
    r = send(P3, "40100", "mtoto umri 7 ana mafua")
    assert ids(r)[-1] == (P3, "CG_GO_NOW") and "age not received" in r[0][2]
