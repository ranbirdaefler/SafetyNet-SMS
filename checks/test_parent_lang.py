"""Parent language (CLAUDE.md rule 8). Uses the gpt-5.5 drafts as a TEST FIXTURE only; the live service stays English
until config/parent_sw.json holds strings Florian approved."""
import json
import re

import pytest

from app import cg_tests, messages as M
from app.cg_tests import Env, P1, P4
from app.engine import Protocol

PROTO = Protocol.load("config/protocol.yaml", run_suite=False)
P_EN = "+254733000005"          # registered with lang: en


@pytest.fixture
def sw_drafts():
    d = json.load(open("gen/swahili/drafts.json", encoding="utf-8"))["swahili"]
    saved = dict(M.SW_PARENT)
    M.SW_PARENT.clear()
    M.SW_PARENT.update({k: v.replace("msimbo", "msimbo (code)") for k, v in d.items()})
    yield
    M.SW_PARENT.clear()
    M.SW_PARENT.update(saved)


def test_live_has_no_swahili_until_approved():
    assert M.SW_PARENT == {} or __import__("pathlib").Path("config/parent_sw.json").exists()


def test_cg_told_follows_registered_language(sw_drafts):
    e = Env(PROTO)
    sw = [m for m in e.send(P1, "parent", "child 18m has a rash") if m["recipient"] == P1][0]["body"]
    en = [m for m in e.send(P_EN, "parent", "child 18m has a rash") if m["recipient"] == P_EN][0]["body"]
    assert sw.startswith("Mhudumu wako") and "Your health worker" not in sw
    assert en.startswith("Your health worker") and "Mhudumu" not in en


def test_go_now_is_bilingual_swahili_first_english_last(sw_drafts):
    e = Env(PROTO)
    for ph in (P1, P_EN):
        body = [m for m in e.send(ph, "parent", "child 18m degedege") if m["recipient"] == ph][0]["body"]
        sw, en = body.split("\n")
        assert sw.startswith("Mpeleke mtoto") and "msimbo (code)" in sw
        assert re.fullmatch(re.escape(M.CG_GO_NOW).replace(re.escape("{facility}"), ".+").replace(re.escape("{code}"), r"\d{4}"), en)


def test_lints_and_cg_suite_pass_with_swahili(sw_drafts):
    assert cg_tests.lint_parent([]) is None
    assert cg_tests.run(PROTO) == []


def test_minutes_slot_renders():
    tpl = "If no one calls or comes within {minutes} minutes, go to {facility}."
    assert tpl.format(minutes=1, facility="X") == "If no one calls or comes within 1 minutes, go to X."
    from app.door import DoorFlow
    from app.registry import Registry
    from app.store import Store
    d = DoorFlow(Store(":memory:"), Registry("config/registry.yaml"), PROTO, None)
    assert d.wait_minutes() == 1          # demo timeout 60 s -> 1 minute
