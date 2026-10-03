"""slice-chw: CHP text -> ASK_SIGNS -> numbered reply -> ALERT (facility + CHA) before REFER_NOW -> facility code -> ACK + ARRIVED."""
import os
import tempfile

from fastapi.testclient import TestClient

os.environ["SNS_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")
from app.server import app  # noqa: E402

c = TestClient(app)
CHP, FAC, CHA = "+254722000107", "+254711000100", "+254711000200"


def send(ph, line, body):
    return c.post("/sms", json={"from": ph, "to": line, "body": body}).json()["replies"]


def test_slice_chw():
    r = send(CHP, "40101", "18m homa siku 3")
    assert [m["msg_id"] for m in r] == ["ASK_SIGNS"]
    code = r[0]["case_code"]
    r = send(CHP, "40101", f"{code} 5")
    assert [(m["recipient"], m["msg_id"]) for m in r] == [(FAC, "ALERT"), (CHA, "ALERT"), (CHP, "REFER_NOW")]
    assert "chest indrawing" in r[2]["body"] and "PARENT SMS" not in r[0]["body"]
    assert send(FAC, "40102", "0000") == []                       # unknown code: no reply
    r = send(FAC, "40102", code)
    assert [(m["recipient"], m["msg_id"]) for m in r] == [(CHP, "ARRIVED"), (CHA, "ARRIVED"), (FAC, "ACK")]
    assert send(FAC, "40102", code) == []                         # closed: no second ACK


def test_unregistered_cannot_confirm_arrival():
    r = send(CHP, "40101", "18m degedege")
    code = r[-1]["case_code"]
    assert send("+254700000999", "40102", code) == []
