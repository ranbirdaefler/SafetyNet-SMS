"""Question layer (experimental): bank lint, suggest purity, the health worker's action, parent answers (review M1-M8).
Each test switches the layer on explicitly and off again; the rest of the suite runs with it off (bank default)."""
import ast
import copy
import time
from pathlib import Path

import pytest
import yaml

from app import cg_tests, lexicon, qflow
from app import questions as QL
from app.cg_tests import CHA, CHP7, CHP8, FAC, P1, P2, P4, Env
from app.engine import Protocol
from app.suggest import suggest

ROOT = Path(__file__).resolve().parent.parent
PROTO = Protocol.load("config/protocol.yaml", run_suite=False)
P = PROTO.params
FITS = "mtoto wangu wa miaka 2 ana degedege"


@pytest.fixture
def on():
    lexicon.use(lexicon.live_list(lexicon.e2_list()))
    QL.load(P, force=True)
    assert QL.is_on(), QL.STATE["errors"]
    yield
    QL.load(P, force=False)
    assert not QL.is_on()


def ids(out):
    return [(m["role"], m["msg_id"]) for m in out]


def referred(e, phone=P1, text=FITS):
    out = e.send(phone, "parent", text)
    code = out[0]["case_code"]
    assert e.store.case(code)["status"] == "REFERRED"
    return code


def approve(e, code, qid, chp=CHP7):
    before = e.store.last_outbox_id()
    r = qflow.chw_action(e.store, e.reg, PROTO, chp, code, qid, "approve")
    return r, e.store.outbox_since(before)


# ---------- bank ----------
def test_bank_passes_lint_and_default_is_off():
    bank = yaml.safe_load((ROOT / "config" / "questions.yaml").read_text(encoding="utf-8"))
    assert QL.lint(bank, P) == []
    QL.load(P)                                                  # bank default: off until Florian approves the texts
    assert not QL.is_on() and QL.STATE["errors"] == []


@pytest.mark.parametrize("mutate,expect", [
    (lambda q: q.update(en=q["en"] + " Give paracetamol."), "medicine"),
    (lambda q: q.update(en="How many fits? Reply 1 more. 2 one."), "1, 2, 3"),
    (lambda q: q.update(labels={1: "a", 2: "b"}), "labels"),
    (lambda q: q.update(en=q["en"] + " x" * 60), "segment"),
    (lambda q: q.update(en=q["en"] + " Is the child fine?"), "banned"),
])
def test_lint_rejects(mutate, expect):
    bank = yaml.safe_load((ROOT / "config" / "questions.yaml").read_text(encoding="utf-8"))
    bad = copy.deepcopy(bank)
    mutate(bad["questions"][0])
    assert any(expect in e for e in QL.lint(bad, P))


def test_failing_bank_switches_layer_off(tmp_path):
    bank = yaml.safe_load((ROOT / "config" / "questions.yaml").read_text(encoding="utf-8"))
    bank["questions"][0]["sw"] = None
    f = tmp_path / "q.yaml"
    f.write_text(yaml.safe_dump(bank, allow_unicode=True), encoding="utf-8")
    QL.load(P, path=f, force=True)
    assert not QL.is_on() and QL.STATE["errors"]
    QL.load(P)


# ---------- suggest ----------
def test_suggest_is_pure():
    tree = ast.parse((ROOT / "app" / "suggest.py").read_text(encoding="utf-8"))
    names = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | \
            {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not any(x and ("store" in x or "server" in x or "door" in x or "service" in x or "qflow" in x) for x in names)
    calls = {getattr(n.func, "attr", getattr(n.func, "id", "")) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    assert not any("send" in c or "update_case" in c or "create_case" in c for c in calls)


def test_suggest_tier1_and_m1(on):
    bank = QL.STATE["bank"]["questions"]
    st = {"age_months": 24, "u2m": False, "refer_reasons": ["convulsions"]}
    assert [s["id"] for s in suggest(st, bank, "REFERRED")] == ["PA_FITS_COUNT", "PA_AWAKE"]
    assert suggest(st, bank, "ASK_SIGNS") == []                                   # Tier 1: referred cases only
    for bad in ({"age_months": None}, {"u2m": True, "age_months": 1}, {"age_months": 70}, {"pregnancy": True}):
        assert suggest({**st, **bad}, bank, "REFERRED") == []                     # M1
    r = suggest({**st, "model": {"heads": {"convulsions": 0.97}}}, bank, "REFERRED")[0]["reason"]
    assert "Model score for convulsions: 0.97" in r and "WHO/UNICEF" in r
    low = suggest({**st, "model": {"heads": {"convulsions": 0.2}}}, bank, "REFERRED")[0]["reason"]
    assert "0.2" not in low and "unlikely" not in low                             # E6


# ---------- the health worker's action ----------
def test_nothing_sent_without_her_action_and_layer_off_sends_nothing(on):
    e = Env(PROTO)
    code = referred(e)
    assert not any(m["msg_id"].startswith("Q_") for m in e.all)
    QL.load(P, force=False)
    r, out = approve(e, code, "PA_FITS_COUNT")
    assert r["ok"] is False and out == []
    QL.load(P, force=True)


def test_approve_sends_prefixed_fixed_text_and_is_not_a_chp_reply(on):
    e = Env(PROTO)
    code = referred(e)
    before = dict(e.store.case(code))
    r, out = approve(e, code, "PA_FITS_COUNT")
    assert r["ok"] and ids(out) == [("parent", "Q_PA_FITS_COUNT")]
    assert out[0]["body"].startswith("Endelea kwenda kliniki.")                  # E1 (Swahili registered parent)
    after = e.store.case(code)
    assert after["status"] == before["status"] and after["due"] == before["due"]   # M2
    assert not after["state"].get("chp_replied")
    assert "drafted by model, approved by CHP 07" in after["state"]["q"]["log"][0]["text"]


def test_not_her_case_unregistered_and_not_suggested_are_refused(on):
    e = Env(PROTO)
    code = referred(e)
    assert approve(e, code, "PA_FITS_COUNT", chp=CHP8)[0]["error"] == "not your case"
    assert approve(e, code, "PA_DRINK_SINCE")[0]["error"] == "not a current suggestion for this case"
    code4 = referred(e, phone=P4)                                                  # registered, no CHP: no chp_phone
    assert approve(e, code4, "PA_FITS_COUNT")[0]["ok"] is False


def test_decline_is_logged_and_removed(on):
    e = Env(PROTO)
    code = referred(e)
    r = qflow.chw_action(e.store, e.reg, PROTO, CHP7, code, "PA_FITS_COUNT", "decline")
    assert r["ok"] and r["action"] == "declined"
    st = e.store.case(code)["state"]["q"]
    assert st["log"][0]["action"] == "declined" and "PA_FITS_COUNT" not in [s["id"] for s in qflow.suggestions(e.store.case(code))]
    assert not any(m["msg_id"].startswith("Q_") for m in e.all)


# ---------- parent answers ----------
def answered(e, code, reply, qid="PA_FITS_COUNT"):
    approve(e, code, qid)
    return e.send(P1, "parent", reply)


def test_danger_answer_ack_and_facility_note_no_duplicate_go_now(on):
    e = Env(PROTO)
    code = referred(e)
    out = answered(e, code, "1")
    assert ("parent", "CG_GO_NOW") not in ids(out)
    assert ("parent", "Q_ACK") in ids(out) and ("facility", "PREARRIVAL") in ids(out)
    note = [m for m in out if m["msg_id"] == "PREARRIVAL"][0]["body"]
    assert "parent report, not checked" in note and "more than one fit" in note    # M3


def test_safe_answer_never_clears_and_stays_off_the_facility(on):
    e = Env(PROTO)
    code = referred(e)
    st0 = e.store.case(code)
    out = answered(e, code, "2")
    assert ids(out) == [("parent", "Q_ACK")]                                        # M3: no facility note
    st1 = e.store.case(code)
    assert st1["status"] == st0["status"] and st1["state"]["refer_reasons"] == st0["state"]["refer_reasons"]
    assert any("not a check, you still check" in x for x in qflow.board_lines(st1))


def test_not_sure_goes_to_facility(on):
    e = Env(PROTO)
    code = referred(e)
    out = answered(e, code, "tatu")
    assert ("facility", "PREARRIVAL") in ids(out)


@pytest.mark.parametrize("reply", ["yes", "ndiyo", "hapana", "1 2", "no", "asante sana"])
def test_non_bare_reply_counts_as_not_sure_then_old_flow(on, reply):
    e = Env(PROTO)
    code = referred(e)
    out = answered(e, code, reply)
    assert ("facility", "PREARRIVAL") in ids(out)                                   # M5: not sure, forwarded
    assert ("parent", "CG_GO_NOW") in ids(out) and ("parent", "Q_ACK") not in ids(out)   # then D23 as before


def test_latest_question_wins(on):
    e = Env(PROTO)
    code = referred(e)
    approve(e, code, "PA_FITS_COUNT")
    approve(e, code, "PA_AWAKE")
    out = e.send(P1, "parent", "1")
    note = [m for m in out if m["msg_id"] == "PREARRIVAL"][0]["body"]
    assert "not awake or fitting now" in note and "fit" not in note.replace("fitting", "")   # M8
    assert e.send(P1, "parent", "1")[0]["msg_id"] == "CG_GO_NOW"                    # no pending: old D23 path


def test_bare_digit_without_pending_question_is_old_flow(on):
    e = Env(PROTO)
    referred(e)
    assert ids(e.send(P1, "parent", "1")) == [("parent", "CG_GO_NOW")]


def test_after_arrival_answers_go_to_her_board_only(on):
    e = Env(PROTO)
    code = referred(e)
    approve(e, code, "PA_FITS_COUNT")
    e.send(FAC, "facility", code)                                                    # ARRIVED
    out = e.send(P1, "parent", "1")
    assert out == []                                                                 # no facility note, no ack
    assert any("parent answered 1" in x for x in qflow.board_lines(e.store.case(code)))


def test_window_expiry(on):
    e = Env(PROTO)
    code = referred(e)
    approve(e, code, "PA_FITS_COUNT")
    c = e.store.case(code)
    c["state"]["q"]["pending"]["at"] -= qflow.WINDOW_S + 1
    e.store.update_case(code, state=c["state"])
    assert ids(e.send(P1, "parent", "1")) == [("parent", "CG_GO_NOW")]


def test_cap_two_prearrival(on):
    e = Env(PROTO)
    code = referred(e)
    approve(e, code, "PA_FITS_COUNT")
    approve(e, code, "PA_AWAKE")
    assert qflow.suggestions(e.store.case(code)) == []


def test_cg_suite_identical_with_layer_on(on):
    assert cg_tests.run(PROTO) == []


# ---------- E2 blocked words (used by her own messages) ----------
@pytest.mark.parametrize("text", [
    "Give him panadol now", "Give 5 ml of the syrup", "ORS will help",                      # medicine EN
    "Mpe dawa sasa", "Mpe vidonge viwili", "antibiotiki zitasaidia",                        # medicine SW
    "Wait for me, I will come", "No need to go tonight", "Go tomorrow",                     # change of plan EN
    "Subiri nije", "Tusubiri kidogo", "Ngojeni hapo", "Usiende hospitali", "Msimpeleke leo", "nenda kesho",   # SW
    "Don't worry, he'll be fine", "It is nothing serious",                                  # reassurance EN
    "Usijali", "Atakuwa sawa", "Hana shida",                                                # reassurance SW
    "Mtoto ana homa, mpe panadol",                                                          # code-mixed
])
def test_blocked_words_refuse(on, text):
    assert QL.blocked_hits(text)


@pytest.mark.parametrize("text", ["Did the child drink this morning?", "Mtoto amekunywa maji asubuhi?",
                                  "I am coming to see you now", "Ninakuja sasa hivi kumwona mtoto"])
def test_normal_messages_pass(on, text):
    assert QL.blocked_hits(text) == []


def test_only_approved_texts_reach_the_allowlist(on):
    from app import messages as M
    assert "Q_PA_FITS_COUNT" in M.QL_TEMPLATES and "Q_CK_FITS" not in M.QL_TEMPLATES   # Tier 2 not approved
