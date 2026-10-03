"""'Why this reply?' (display only) and the story's rule-check card claims."""
import importlib
import os
import sys
import tempfile

from fastapi.testclient import TestClient

from app import lexicon
from app.door import keyword_extractor, parent_policy
from app.engine import Protocol

SENDS = [("+254733000001", "mtoto wangu wa miezi 14 kila kitu anachokula anatapika hata maji"),
         ("+254733000001", "sasa ana degedege"),
         ("+254733000002", "mtoto wa miezi 20 ana kikohozi kwa wiki tatu"),
         ("+254733000003", "my baby has a rash"),
         ("+254733000005", "mtoto wa miaka 2 hana degedege")]


def fresh_app():
    os.environ["SNS_TIMER"] = "0"
    os.environ["SNS_DB"] = os.path.join(tempfile.mkdtemp(), "why.db")
    sys.modules.pop("app.server", None)
    import app.server as srv
    importlib.reload(srv)
    return srv


def run(explain):
    srv = fresh_app()
    srv.EXPLAIN = explain
    c = TestClient(srv.app)
    for ph, m in SENDS:
        c.post("/sms", json={"from": ph, "to": "40100", "body": m})
    c.post("/demo/fire-timeouts")
    rows = c.get("/outbox").json()
    sys.modules.pop("app.server", None)
    return rows


def test_decisions_identical_with_and_without_explanation():
    on, off = run(True), run(False)
    import re
    key = lambda rows: [(r["recipient"], r["role"], r["msg_id"], re.sub(r"\d", "#", r["body"])) for r in rows]
    assert key(on) == key(off)
    assert any(r.get("why") for r in on) and not any(r.get("why") for r in off)


def test_explanation_never_in_any_sms():
    rows = run(True)
    for r in rows:
        assert "Rules:" not in r["body"] and "Model (" not in r["body"]
        if r.get("why"):
            assert r["role"] == "parent" and r["why"] not in r["body"]
            assert "+254" not in r["why"]                       # no phone numbers in the explanation
    whys = {r["msg_id"]: r["why"] for r in rows if r.get("why")}
    assert any("matched 'degedege' (convulsions)" in (r.get("why") or "") for r in rows)
    assert any("no age found" in (r.get("why") or "") for r in rows)
    assert any("age found: 14 months" in (r.get("why") or "") for r in rows)
    assert whys.get("CG_TIMEOUT", "").startswith("Rules: the health worker did not reply in time")


def test_rule_check_card_claims():
    p = Protocol.load("config/protocol.yaml", run_suite=False).params
    lexicon.use(lexicon.live_list(lexicon.e2_list()))
    assert "anatapika kila kitu" in lexicon.LIVE["rows"]["vomits_everything"]
    act = lambda t: parent_policy(t, p, (keyword_extractor,)).action
    assert act("mtoto wangu wa miezi 14 kila kitu anachokula anatapika hata maji") == "TOLD"
    assert act("mtoto wangu wa miezi 14 anatapika kila kitu hata maji") == "GO_NOW"
    assert act("mtoto wangu wa miezi 14 kila kitu anatapika") == "TOLD"
