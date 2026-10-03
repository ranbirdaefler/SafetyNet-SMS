"""English glosses for viewers (display only): exact EN templates for Swahili system messages; never in an SMS."""
import importlib
import os
import sys
import tempfile

from fastapi.testclient import TestClient

from app import messages as M

SW_PARENT, EN_PARENT, CHP = "+254733000001", "+254733000005", "+254722000107"


def fresh():
    os.environ["SNS_TIMER"] = "0"
    os.environ["SNS_DB"] = os.path.join(tempfile.mkdtemp(), "gloss.db")
    os.environ["SNS_QUESTIONS"] = "1"
    sys.modules.pop("app.server", None)
    import app.server as srv
    importlib.reload(srv)
    return srv, TestClient(srv.app)


def test_glosses_are_exact_en_templates_and_never_sent():
    srv, c = fresh()
    try:
        r = c.post("/sms", json={"from": SW_PARENT, "to": "40100", "body": "mtoto wangu wa miaka 2 ana upele"}).json()
        told = [x for x in r["replies"] if x["msg_id"] == "CG_TOLD"][0]
        assert told["en"] is not None and told["en"] != told["body"]
        m = srv._slot_regex(M.SW_PARENT["CG_TOLD"]).fullmatch(told["body"])
        assert told["en"] == M.PARENT_ALLOWLIST["CG_TOLD"].format(**m.groupdict())
        r = c.post("/sms", json={"from": EN_PARENT, "to": "40100", "body": "my child 2 years has a rash"}).json()
        assert [x for x in r["replies"] if x["msg_id"] == "CG_TOLD"][0]["en"] is None      # already English
        r = c.post("/sms", json={"from": "+254733000002", "to": "40100", "body": "mtoto wangu wa miaka 2 ana degedege"}).json()
        go = [x for x in r["replies"] if x["msg_id"] == "CG_GO_NOW"][0]
        assert go["en"] is None                                                           # bilingual: EN already in it
        code = go["case_code"]
        r = c.post("/chw/question", json={"chp": CHP, "code": code, "qid": "PA_FITS_COUNT", "action": "approve"}).json()
        q = [x for x in r["replies"] if x["msg_id"] == "Q_PA_FITS_COUNT"][0]
        v = M.QL_TEMPLATES["Q_PA_FITS_COUNT"]
        assert q["body"] == v[3] and q["en"] == v[2]                                      # prefixed SW -> prefixed EN
        r = c.post("/chw/message", json={"chp": CHP, "code": code, "text": "Nijulishe mkifika kliniki."}).json()
        w = [x for x in r["replies"] if x["msg_id"] == "CHW_MSG"][0]
        assert w["en"] == "Keep going to the clinic. Achieng, your health worker: Nijulishe mkifika kliniki."
        for row in c.get("/outbox").json():                                              # display only
            if row.get("en"):
                assert row["en"] not in row["body"] and row["role"] == "parent"
        assert all("EN (for viewers" not in row["body"] for row in c.get("/outbox").json())
    finally:
        os.environ.pop("SNS_QUESTIONS", None)
        sys.modules.pop("app.server", None)
