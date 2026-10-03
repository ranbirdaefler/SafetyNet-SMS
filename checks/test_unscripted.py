"""Unscripted on-camera input: empty text, emoji, very long text. Fail-safe reply, no crash, on every line."""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SNS_DB", os.path.join(tempfile.mkdtemp(), "t.db"))
os.environ["SNS_TIMER"] = "0"
from app.server import app, STORE  # noqa: E402

c = TestClient(app)
INPUTS = {"empty": "", "emoji": "\U0001F622\U0001F622 mtoto \U0001F912", "long": ("mtoto wangu ana homa na kikohozi " * 400).strip()}


@pytest.mark.parametrize("kind", list(INPUTS))
def test_parent_line_never_crashes_and_fails_safe(kind):
    STORE.db.execute("UPDATE cases SET status = 'CLOSED' WHERE parent_phone = '+254733000002'")
    r = c.post("/sms", json={"from": "+254733000002", "to": "40100", "body": INPUTS[kind]})
    assert r.status_code == 200
    ids = [m["msg_id"] for m in r.json()["replies"] if m["recipient"] == "+254733000002"]
    assert ids in (["CG_GO_NOW"], ["CG_GO_NOW_U"])      # no age read: go now (age not received)


@pytest.mark.parametrize("kind", list(INPUTS))
def test_chp_and_facility_lines_never_crash(kind):
    assert c.post("/sms", json={"from": "+254722000109", "to": "40101", "body": INPUTS[kind]}).status_code == 200
    assert c.post("/sms", json={"from": "+254711000100", "to": "40102", "body": INPUTS[kind]}).status_code == 200


def test_live_log_has_no_phone_numbers():
    c.post("/sms", json={"from": "+254733000001", "to": "40100", "body": "mtoto miezi 18 ana homa"})
    body = c.get("/log").text
    assert "+254" not in body and "mtoto" not in body
