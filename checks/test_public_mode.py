"""Public demo mode (Hugging Face Space): admin and diagnostic endpoints off, input size limit, reset, fire-timeouts."""
import importlib
import os
import sys
import tempfile

from fastapi.testclient import TestClient


def public_app():
    os.environ["SNS_PUBLIC"] = "1"
    os.environ["SNS_TIMER"] = "0"
    os.environ["SNS_DB"] = os.path.join(tempfile.mkdtemp(), "pub.db")
    sys.modules.pop("app.server", None)
    import app.server as srv
    importlib.reload(srv)
    return srv


def test_public_mode_rules():
    srv = public_app()
    try:
        c = TestClient(srv.app)
        assert c.get("/config").json()["public"] is True
        assert c.post("/admin/reload").status_code == 404
        assert c.post("/phone/report", json={}).status_code == 404
        assert c.post("/phone/parity", json=[]).status_code == 404
        assert c.post("/sms", json={"from": "+254733000001", "to": "40100", "body": "x" * 1001}).status_code == 413
        r = c.post("/sms", json={"from": "+254733000001", "to": "40100", "body": "mtoto miezi 18 ana mafua"})
        assert r.status_code == 200 and r.json()["replies"]
        assert c.post("/demo/fire-timeouts").json()["fired"] == 1                 # the CG_TOLD case times out now
        assert any(m["msg_id"] == "CG_TIMEOUT" for m in c.get("/outbox").json())
        c.post("/demo/reset")
        assert c.get("/outbox").json() == [] and c.get("/inbox").json() == [] and c.get("/log").json() == []
    finally:
        os.environ.pop("SNS_PUBLIC", None)
        sys.modules.pop("app.server", None)
