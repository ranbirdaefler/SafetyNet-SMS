"""Door flag off: a parent text gets the fixed CG_GO_NOW_U and the CHA a copy; the text is not read."""
import os
import tempfile

from fastapi.testclient import TestClient

os.environ.setdefault("SNS_DB", os.path.join(tempfile.mkdtemp(), "t.db"))
os.environ["SNS_TIMER"] = "0"
from app.server import app, STATE, STORE  # noqa: E402

c = TestClient(app)


def test_door_off_fails_safe():
    saved = STATE["door_on"]
    STATE["door_on"] = False
    try:
        for phone in ("+254733000001", "+254799000001"):          # registered and unregistered
            r = c.post("/sms", json={"from": phone, "to": "40100", "body": "mtoto miezi 18 ana mafua"}).json()["replies"]
            assert [(m["recipient"], m["msg_id"]) for m in r] == [("+254711000200", "ALERT"), (phone, "CG_GO_NOW_U")]
            assert "PARENT SMS: text not read" in r[0]["body"]
    finally:
        STATE["door_on"] = saved
        STORE.db.execute("UPDATE cases SET status = 'CLOSED' WHERE status = 'REFERRED_U'")
