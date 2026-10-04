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
    QL.load(P, force=False)                                     # the rest of the suite runs with the layer off
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
    QL.load(P)                                                  # bank default: on for the release (experimental)
    import os
    expect = {"0": False, "1": True}.get(os.environ.get("SNS_QUESTIONS"), bank["enabled"] is True)
    assert QL.is_on() == expect and QL.STATE["errors"] == []


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
    assert all(s["id"].startswith("CK_") for s in suggest(st, bank, "ASK_SIGNS"))   # TOLD: Tier 2 checks only
    for bad in ({"age_months": None}, {"u2m": True, "age_months": 1}, {"age_months": 70}, {"pregnancy": True}):
        assert suggest({**st, **bad}, bank, "REFERRED") == []                     # M1
    r = suggest({**st, "rule_terms": {"convulsions": "degedege"}, "model": {"heads": {"convulsions": 0.97}}}, bank, "REFERRED")[0]["reason"]
    assert r.startswith("Linked to the sign the rules found: convulsions ('degedege').") and "WHO/UNICEF" in r
    assert "0.97" not in r and "score" not in r                                   # rules found it: no model score
    from app.suggest import score_text
    assert score_text(0.999) == "above 0.99" and score_text(0.97) == "0.97" and score_text(0.3) is None   # E6


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
    bank = QL.STATE["bank"]
    assert all(("Q_" + q["id"] in M.QL_TEMPLATES) == (q.get("approved") is True) for q in bank["questions"])


# ---------- step 6: her own / edited messages (review E1-E6) ----------
def own(e, code, text, chp=CHP7, from_qid=None):
    before = e.store.last_outbox_id()
    r = qflow.chw_message(e.store, e.reg, PROTO, chp, code, text, from_qid)
    return r, e.store.outbox_since(before)


def test_own_message_has_system_prefixes_and_is_not_a_reply(on):
    e = Env(PROTO)
    code = referred(e)
    c0 = e.store.case(code)
    r, out = own(e, code, "Nijulishe mkifika kliniki.")
    assert r["ok"] and ids(out) == [("parent", "CHW_MSG")]
    assert out[0]["body"] == "Endelea kwenda kliniki. Achieng, your health worker: Nijulishe mkifika kliniki."   # E1, E3
    c1 = e.store.case(code)
    assert (c1["status"], c1["due"]) == (c0["status"], c0["due"]) and not c1["state"].get("chp_replied")       # E4


def test_plain_send_of_chw_msg_is_refused():
    e = Env(PROTO)
    with pytest.raises(ValueError):
        e.store.send(P1, "parent", "CHW_MSG", "Achieng, your health worker: hello", "1234")
    with pytest.raises(ValueError):
        e.store.send_chw_msg(P1, "Mallory, your health worker: hello", "1234", {"Achieng"}, {"Endelea kwenda kliniki."})


@pytest.mark.parametrize("text", ["Mpe panadol", "Subiri kidogo", "Usijali, atakuwa sawa", "Wait for me", "Give ORS"])
def test_own_message_blocked_words_refused(on, text):
    e = Env(PROTO)
    code = referred(e)
    r, out = own(e, code, text)
    assert r["ok"] is False and r["error"] == "Not sent: for medicines or a change of plan, call the parent." and out == []


def test_own_message_too_long_and_system_text_refused(on):
    e = Env(PROTO)
    code = referred(e)
    assert own(e, code, "x " * 120)[0]["error"].startswith("Not sent: too long")
    from app import messages as M
    assert own(e, code, M.QL_TEMPLATES["Q_ACK"][1])[0]["ok"] is False


def test_reply_to_her_message_is_shown_never_parsed(on):
    e = Env(PROTO)
    code = referred(e)
    approve(e, code, "PA_FITS_COUNT")
    own(e, code, "Nijulishe mkifika kliniki.")                                         # E5: ends the bank question
    out = e.send(P1, "parent", "1")
    assert ("facility", "PREARRIVAL") not in ids(out) and ("parent", "Q_ACK") not in ids(out)
    assert ids(out) == [("parent", "CG_GO_NOW")]                                       # the old D23 flow
    assert any("Parent replied: 1" in x for x in qflow.board_lines(e.store.case(code)))


def test_edited_question_logged_and_shared_cap(on):
    e = Env(PROTO)
    code = referred(e)
    r, _ = own(e, code, "Amepata degedege mara ngapi leo? Jibu kwa maneno yako.", from_qid="PA_FITS_COUNT")
    assert r["action"] == "edited"
    approve(e, code, "PA_FITS_COUNT")
    approve(e, code, "PA_AWAKE")
    assert own(e, code, "Nijulishe mkifika.")[0]["ok"] is False                       # 3 per case, shared
    assert any("edited and sent by CHP 07" in x for x in qflow.board_lines(e.store.case(code)))


def test_own_message_not_for_unregistered_or_other_chp(on):
    e = Env(PROTO)
    code = referred(e)
    assert own(e, code, "Nijulishe mkifika.", chp=CHP8)[0]["error"] == "not your case"
    code_u = e.send("+254799000001", "parent", FITS)[0]["case_code"]                   # unregistered number
    assert own(e, code_u, "Nijulishe mkifika.")[0]["ok"] is False


def test_own_message_gsm7(on):
    e = Env(PROTO)
    code = referred(e)
    assert own(e, code, "Mtoto akiwa sawa? 🙂")[0]["error"].startswith("Not sent: use plain letters")
    r, out = own(e, code, "Nijulishe mkifika kliniki – asante…")
    assert r["ok"] and out[0]["body"].endswith("Nijulishe mkifika kliniki - asante...")



# ---------- Tier 2: checks on TOLD cases (review M2, M4, M5, M7, M8, E7); every text approved in a temporary bank ----------
@pytest.fixture
def tier2(tmp_path):
    lexicon.use(lexicon.live_list(lexicon.e2_list()))
    bank = yaml.safe_load((ROOT / "config" / "questions.yaml").read_text(encoding="utf-8"))
    for q in bank["questions"]:
        q["approved"] = True
    bank["ack_told"]["approved"] = True
    f = tmp_path / "q.yaml"
    f.write_text(yaml.safe_dump(bank, allow_unicode=True), encoding="utf-8")
    QL.load(P, path=f, force=True)
    assert QL.is_on(), QL.STATE["errors"]
    yield
    QL.load(P, force=False)


RASH = "mtoto wangu wa miaka 2 ana upele"


def told(e, phone=P1, text=RASH):
    code = e.send(phone, "parent", text)[0]["case_code"]
    assert e.store.case(code)["status"] == "ASK_SIGNS"
    return code


def test_tier2_drafts_need_a_signal(tier2):
    bank, table = QL.approved_questions(), QL.STATE["bank"]["symptom_checks"]
    st = {"age_months": 24, "u2m": False}
    assert suggest(st, bank, "ASK_SIGNS", table) == []                                       # no signal: nothing
    st = {**st, "model": {"heads": {"vomits_everything": 0.8, "convulsions": 0.6}}}
    assert [s["id"] for s in suggest(st, bank, "ASK_SIGNS", table)] == ["CK_VOMIT", "CK_FITS"]   # model-ranked
    r = suggest(st, bank, "ASK_SIGNS", table)[0]["reason"]
    assert "score 0.80" in r and "WHO/UNICEF" in r


def test_tier2_table_drives_drafts_and_pair_is_one_slot(tier2):
    bank, table = QL.approved_questions(), QL.STATE["bank"]["symptom_checks"]
    ids = lambda st: [s["id"] for s in suggest(st, bank, "ASK_SIGNS", table)]
    base = {"age_months": 24, "u2m": False}
    assert ids({**base, "symptoms": {"diarrhoea": {"duration": False}}}) == ["CK_WAKE", "CK_BLOOD"]      # pair, then blood
    assert ids({**base, "symptoms": {"fever": {"duration": False}}}) == ["CK_WAKE", "CK_FITS"]           # pair, then fits
    assert ids({**base, "symptoms": {"vomiting": {"duration": True}}}) == ["CK_VOMIT", "CK_WAKE"]        # vomit, then pair
    # the pair is ONE slot: after the wake check was sent, the drink check follows inside the same slot
    st = {**base, "symptoms": {"diarrhoea": {"duration": False}}, "q": {"asked": ["CK_WAKE"]}}
    assert ids(st) == ["CK_DRINK", "CK_BLOOD"]
    st = {**base, "symptoms": {"diarrhoea": {"duration": False}}, "q": {"asked": ["CK_WAKE", "CK_DRINK", "CK_BLOOD"]}}
    assert ids(st) == []                                                       # 2 slots used = 3 SMS: nothing more
    st = {**base, "symptoms": {"diarrhoea": {"duration": False}}, "q": {"declined": ["CK_WAKE"]}}
    assert ids(st) == ["CK_BLOOD"]                                             # a declined pair is not reopened


def test_tier2_cough_rule(tier2):
    bank, table = QL.approved_questions(), QL.STATE["bank"]["symptom_checks"]
    ids = lambda st: [s["id"] for s in suggest(st, bank, "ASK_SIGNS", table)]
    base = {"age_months": 24, "u2m": False}
    assert ids({**base, "symptoms": {"cough": {"duration": False}}}) == ["CK_COUGH_DAYS"]   # cough: duration only
    assert ids({**base, "symptoms": {"cough": {"duration": True}}}) == []
    st = {**base, "symptoms": {"cough": {"duration": True}}, "model": {"heads": {"sleepy_unconscious": 0.7}}}
    assert ids(st) == ["CK_WAKE"]                                              # the pair still drafts on a model signal


@pytest.mark.parametrize("text,expect", [
    ("mtoto wangu wa miaka 2 ana homa", {"fever"}), ("mtoto wangu wa miaka 2 hana homa", set()),
    ("my child 2 years has no fever", set()), ("mtoto anaharisha kwa siku 3", {"diarrhoea"}),
    ("mtoto hatapiki", set()), ("he keeps vomiting", {"vomiting"}), ("ana kikohozi", {"cough"})])
def test_tier2_mentions_and_denials(tier2, text, expect):
    from app import textparse
    from app.suggest import mentions
    m = mentions(text, QL.STATE["bank"]["symptom_checks"], lexicon.clauses(text), lexicon.CUES, textparse.parse(text).durations)
    assert set(m) == expect


def test_tier2_denied_symptom_and_no_signal_case_draft_nothing(tier2):
    e = Env(PROTO)
    code = told(e, text="mtoto wangu wa miaka 3 ana kikohozi siku 3, hana homa, anakula na kucheza vizuri")
    assert qflow.suggestions(e.store.case(code)) == []


def test_tier2_at_most_two_checks_offered(tier2):
    bank, table = QL.approved_questions(), QL.STATE["bank"]["symptom_checks"]
    st = {"age_months": 24, "u2m": False, "symptoms": {"fever": {"duration": False}}, "q": {"asked": [], "declined": ["CK_FITS", "CK_WAKE"]}}
    assert suggest(st, bank, "ASK_SIGNS", table) == []


def test_tier2_question_has_no_referred_prefix(tier2):
    e = Env(PROTO)
    code = told(e, text="mtoto wangu wa miaka 2 ana homa")
    r, out = approve(e, code, qflow.suggestions(e.store.case(code))[0]["id"])
    assert r["ok"] and not out[0]["body"].startswith("Endelea kwenda kliniki")


def first_check(e, code, qid):
    c = e.store.case(code)
    st = c["state"]
    st.setdefault("q", {})
    qflow.qstate(st)["asked"].append(qid)                       # bypass the ranking: put this check as pending directly
    st["q"]["pending"] = {"id": qid, "at": time.time()}
    e.store.update_case(code, state=st)


def test_tier2_danger_answer_goes_now_first(tier2):
    e = Env(PROTO)
    code = told(e)
    first_check(e, code, "CK_VOMIT")
    out = e.send(P1, "parent", "1")
    assert ("parent", "CG_GO_NOW") in ids(out) and ("parent", "Q_ACK_TOLD") not in ids(out)     # M2
    assert ("facility", "ALERT") in ids(out)
    c = e.store.case(code)
    assert c["status"] == "REFERRED" and c["state"]["fields"]["vomits_everything"] == "PRESENT"


@pytest.mark.parametrize("qid,go", [("CK_FITS", True), ("CK_WAKE", True), ("CK_DRINK", True), ("CK_VOMIT", True),
                                     ("CK_BLOOD", False), ("CK_COUGH_DAYS", False)])
def test_tier2_not_sure(tier2, qid, go):
    e = Env(PROTO)
    code = told(e)
    first_check(e, code, qid)
    out = e.send(P1, "parent", "3")
    if go:                                                                  # M4: general danger signs -> go now
        assert ("parent", "CG_GO_NOW") in ids(out)
    else:                                                                   # blood / duration -> call now, deadline kept
        c = e.store.case(code)
        assert c["status"] == "ASK_SIGNS" and "Call now" in c["state"]["q"]["alert"]
        assert ids(out) == [("parent", "Q_ACK_TOLD")]


def test_tier2_safe_answer_keeps_deadline_and_timeout_fires(tier2):
    e = Env(PROTO)
    code = told(e)
    due0 = e.store.case(code)["due"]
    first_check(e, code, "CK_FITS")
    out = e.send(P1, "parent", "2")
    assert ids(out) == [("parent", "Q_ACK_TOLD")]
    assert "dakika" in out[0]["body"]                                       # duration form, no clock time
    c = e.store.case(code)
    assert c["status"] == "ASK_SIGNS" and c["due"] == due0 and "convulsions" not in (c["state"].get("fields") or {})
    fired = e.fire()
    assert ("parent", "CG_TIMEOUT") in ids(fired)                           # the deadline still runs


def test_tier2_non_bare_is_not_sure_then_old_flow(tier2):
    e = Env(PROTO)
    code = told(e)
    first_check(e, code, "CK_FITS")
    out = e.send(P1, "parent", "ndiyo")
    assert ("parent", "CG_GO_NOW") in ids(out)                              # M5 + M4


def test_tier2_late_danger_after_her_zero(tier2):
    e = Env(PROTO)
    code = told(e)
    first_check(e, code, "CK_VOMIT")
    e.send(CHP7, "chp", f"{code} 0")                                        # she closes the case
    assert e.store.case(code)["status"] == "NON_RED"
    out = e.send(P1, "parent", "1")
    assert ("parent", "CG_GO_NOW") in ids(out)                              # M8: within 12 h goes now


def test_tier2_e7_reply_to_her_message(tier2):
    e = Env(PROTO)
    code = told(e)
    r, out = own(e, code, "Nitakupigia simu sasa hivi.")
    assert r["ok"] and out[0]["body"] == "Achieng, your health worker: Nitakupigia simu sasa hivi."   # no E1 line on TOLD
    out = e.send(P1, "parent", "sawa")
    assert (CHP7, "CHP_PARENT_REPLIED") in [(m["recipient"], m["msg_id"]) for m in out]
    c = e.store.case(code)
    assert c["state"]["q"]["alert"] == "PARENT REPLIED: read now" and c["status"] == "ASK_SIGNS"
    out = e.send(P1, "parent", "mtoto ana degedege sasa")                    # the keyword policy still runs underneath
    assert ("parent", "CG_GO_NOW") in ids(out)


def test_tier2_m1_no_drafts_for_newborn_or_no_age(tier2):
    e = Env(PROTO)
    code = e.send(P1, "parent", "mtoto wa wiki 3 ana upele")[0]["case_code"]
    assert qflow.suggestions(e.store.case(code)) == []


# ---------- answers stay open for upgrades (only raising urgency) ----------
def test_upgrade_2_then_1_sends_changed_note_no_double_go_now(on):
    e = Env(PROTO)
    code = referred(e)
    answered(e, code, "2")
    out = e.send(P1, "parent", "1")
    assert ("parent", "CG_GO_NOW") not in ids(out)                                   # consumed: no repeated go-now
    note = [m for m in out if m["msg_id"] == "PREARRIVAL"][0]["body"]
    assert "(answer changed): more than one fit" in note and ("parent", "Q_ACK") in ids(out)


def test_downgrade_1_then_2_is_ignored(on):
    e = Env(PROTO)
    code = referred(e)
    answered(e, code, "1")
    out = e.send(P1, "parent", "2")
    assert ("facility", "PREARRIVAL") not in ids(out) and ids(out) == [("parent", "CG_GO_NOW")]   # old D23 path
    assert any("ignored, earlier answer stands" in x for x in qflow.board_lines(e.store.case(code)))


def test_upgrade_3_then_1_fits_note(on):
    e = Env(PROTO)
    code = referred(e)
    answered(e, code, "3")
    out = e.send(P1, "parent", "1")
    assert any("(answer changed)" in m["body"] for m in out if m["msg_id"] == "PREARRIVAL")


def test_upgrade_after_arrival_board_only(on):
    e = Env(PROTO)
    code = referred(e)
    answered(e, code, "2")
    e.send(FAC, "facility", code)
    out = e.send(P1, "parent", "1")
    assert out == [] and any("changed the answer to 1" in x for x in qflow.board_lines(e.store.case(code)))


def test_upgrade_tier2_safe_then_danger_goes_now_first(tier2):
    e = Env(PROTO)
    code = told(e)
    first_check(e, code, "CK_VOMIT")
    assert ids(e.send(P1, "parent", "2")) == [("parent", "Q_ACK_TOLD")]
    out = e.send(P1, "parent", "1")
    assert ("parent", "CG_GO_NOW") in ids(out) and ("parent", "Q_ACK_TOLD") not in ids(out)
    assert e.store.case(code)["status"] == "REFERRED"


def test_non_digit_after_answer_is_old_path(on):
    e = Env(PROTO)
    code = referred(e)
    answered(e, code, "2")
    assert ids(e.send(P1, "parent", "asante")) == [("parent", "CG_GO_NOW")]
