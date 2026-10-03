"""Must-stay-RED tests (protocol_spec section 10, updated per SPEC.md and the 3 Oct CHANGELOG overrides).

Structured inputs: each test builds a Case and checks the engine's decision. Run on every load; any failure
rejects the protocol file. Text-level variants (e.g. "wiki 2", "hana degedege") join in B4 once the regex
and keyword list exist.
"""
from pathlib import Path

from app.engine import ABSENT, PRESENT, Case

A18 = 18  # default in-scope age (months)


def _refer(names, u2m=False):
    def check(d):
        return d.output == "REFER_NOW" and all(n in d.reasons for n in names) and d.u2m == u2m
    return check


def _out(output, **kw):
    def check(d):
        return d.output == output and all(getattr(d, k) == v for k, v in kw.items())
    return check


def _with_param(name, value):
    """Run a case under a different allowed parameter value (e.g. cough_red_days 21)."""
    def wrap(proto, case):
        saved = proto.params[name]
        proto.params[name] = value
        try:
            return proto.evaluate(case)
        finally:
            proto.params[name] = saved
    return wrap


def _at_threshold(kind):
    def run(proto, _case):
        days = proto.params[{"cough": "cough_red_days", "diarrhoea": "diarrhoea_red_days", "fever": "fever_red_days"}[kind]]
        return proto.evaluate(Case(age_months=A18, durations={kind: days}))
    return run


ALL_SIGNS = ["convulsions", "not_drink_feed", "vomits_everything", "sleepy_unconscious", "chest_indrawing",
             "blood_stool", "feet_swelling"]
ALL_LABELS = ["convulsions", "cannot drink or feed", "vomits everything", "very sleepy or cannot wake",
              "chest indrawing", "blood in stool", "long illness", "MUAC red or swelling of both feet"]

# (id, description, [(case, check, runner-or-None), ...])
TESTS = [
    ("T1", "R1 cough at cough_red_days alone", [(None, _refer(["long illness"]), _at_threshold("cough"))]),
    ("T2", "R2 diarrhoea 14+ d alone", [(Case(age_months=A18, durations={"diarrhoea": 14}), _refer(["long illness"]), None)]),
    ("T3", "R3 blood in stool alone", [(Case(age_months=A18, fields={"blood_stool": PRESENT}), _refer(["blood in stool"]), None)]),
    ("T4", "R4 fever 7+ d alone", [(Case(age_months=A18, durations={"fever": 7}), _refer(["long illness"]), None)]),
    ("T5", "R5 convulsions alone", [(Case(age_months=A18, fields={"convulsions": PRESENT}), _refer(["convulsions"]), None)]),
    ("T6", "R6 cannot drink or feed alone", [(Case(age_months=A18, fields={"not_drink_feed": PRESENT}), _refer(["cannot drink or feed"]), None)]),
    ("T7", "R7 vomits everything alone", [(Case(age_months=A18, fields={"vomits_everything": PRESENT}), _refer(["vomits everything"]), None)]),
    ("T8", "R8 chest indrawing alone", [(Case(age_months=A18, fields={"chest_indrawing": PRESENT}), _refer(["chest indrawing"]), None)]),
    ("T9", "R9 unusually sleepy alone", [(Case(age_months=A18, fields={"sleepy_unconscious": PRESENT}), _refer(["very sleepy or cannot wake"]), None)]),
    ("T10", "R10 MUAC red alone", [(Case(age_months=A18, fields={"muac_red": PRESENT}), _refer(["MUAC red or swelling of both feet"]), None)]),
    ("T11", "R11 feet alone, at 18 m and at 3 m", [
        (Case(age_months=A18, fields={"feet_swelling": PRESENT}), _refer(["MUAC red or swelling of both feet"]), None),
        (Case(age_months=3, fields={"feet_swelling": PRESENT}), _refer(["MUAC red or swelling of both feet"]), None)]),
    ("T12", "cough 21 d at cough_red_days 14 and 21", [
        (Case(age_months=A18, durations={"cough": 21}), _refer(["long illness"]), _with_param("cough_red_days", 14)),
        (Case(age_months=A18, durations={"cough": 21}), _refer(["long illness"]), _with_param("cough_red_days", 21))]),
    ("T13", "'wiki 2' = 14 d cough (structured; text form in B4)", [(Case(age_months=A18, durations={"cough": 14}), _refer(["long illness"]), _with_param("cough_red_days", 14))]),
    ("T14", "diarrhoea 14 d", [(Case(age_months=A18, durations={"diarrhoea": 14}), _refer(["long illness"]), None)]),
    ("T15", "fever 'about a week' = 7 d", [(Case(age_months=A18, durations={"fever": 7}), _refer(["long illness"]), None)]),
    ("T16", "MUAC 11.4 cm = 114 mm", [(Case(age_months=A18, muac_mm=114), _refer(["MUAC red or swelling of both feet"]), None)]),
    ("T17", "all 11 fields PRESENT", [(Case(age_months=A18, fields={f: PRESENT for f in ALL_SIGNS + ["muac_red"]},
                                            durations={"cough": 21, "diarrhoea": 14, "fever": 7}), _refer(ALL_LABELS), None)]),
    ("T18", "59 days -> REFER_U2M", [(Case(age_months=59 / 30.4375, u2m=True), _out("REFER_U2M"), None)]),
    ("T19", "59 days + convulsions -> REFER_NOW with N3 opening", [(Case(age_months=59 / 30.4375, u2m=True, fields={"convulsions": PRESENT}), _refer(["convulsions"], u2m=True), None)]),
    ("T20", "no age -> ASK_AGE", [(Case(age_months=None), _out("ASK_AGE"), None)]),
    ("T21", "60 m / pregnancy -> OOS_HUMAN; pregnancy + convulsions -> REFER_NOW", [
        (Case(age_months=60), _out("OOS_HUMAN", oos="5 y+"), None),
        (Case(age_months=None, pregnancy=True), _out("OOS_HUMAN", oos="pregnancy"), None),
        (Case(age_months=None, pregnancy=True, fields={"convulsions": PRESENT}), _refer(["convulsions"]), None)]),
]


def _forced_exception(proto):
    """FX1: an extractor that raises leaves every sign OPEN: never NON_RED, never a sign dropped."""
    def boom(text, **kw):
        raise RuntimeError("forced")
    d = proto.evaluate_text(boom, "18m degedege", registered=True)
    return d.output in ("ASK_AGE", "ASK_SIGNS") and not any(f for f in d.present)


def _no_text_absent(proto):
    """FX2: an extractor that claims ABSENT is overridden to OPEN (only a numbered reply clears a sign)."""
    def lying(text, **kw):
        return Case(age_months=A18, fields={f: ABSENT for f in proto.field_ids})
    d = proto.evaluate_text(lying, "18m hana degedege")
    return d.output == "ASK_SIGNS" and len(d.open_fields) == len(proto.field_ids)


def _flow(proto, texts, phone="+254722000107"):
    """Run CHP texts through the real CHP flow on a scratch in-memory store; returns the replies to the last text."""
    from app.chw import ChwFlow
    from app.registry import Registry
    from app.store import Store
    root = Path(__file__).resolve().parent.parent
    store, reg = Store(":memory:"), Registry(root / "config" / "registry.yaml")
    flow = ChwFlow(store, reg, proto)
    out = []
    for t in texts:
        before = store.last_outbox_id()
        flow.handle(phone, t)
        out = store.outbox_since(before)
    return out


def _ids(out):
    return [m["msg_id"] for m in out]


def _full_ask_signs(proto, out):
    from app import messages as M
    if _ids(out) != ["ASK_SIGNS"]:
        return False
    code = out[0]["case_code"]
    return out[0]["body"] == M.ask_signs(code, 18, proto.params["cough_red_days"])


TEXT_TESTS = [
    ("T13", "text: '18m kikohozi wiki 2' -> REFER_NOW long illness",
     lambda p: _ids(o := _flow(p, ["18m kikohozi wiki 2"])) == ["REFER_NOW"] and "long illness" in o[0]["body"]
     if p.params["cough_red_days"] == 14 else True),
    ("T15", "text: 'child 18m fever about a week' -> REFER_NOW",
     lambda p: _ids(_flow(p, ["child 18m fever about a week"])) == ["REFER_NOW"]),
    ("T16", "text: 'child 18m MUAC 11.4 cm' -> REFER_NOW",
     lambda p: _ids(_flow(p, ["child 18m MUAC 11.4 cm"])) == ["REFER_NOW"]),
    ("T18", "text: 'child 59 days old' -> REFER_U2M",
     lambda p: _ids(_flow(p, ["child 59 days old"])) == ["REFER_U2M"]),
    ("T20", "text: 'homa siku 3' (no age) -> ASK_AGE",
     lambda p: _ids(_flow(p, ["homa siku 3"])) == ["ASK_AGE"]),
    ("T22", "text: '18m hana degedege, homa siku 3, MUAC 13.5 cm, miguu sawa' -> full ASK_SIGNS, byte-identical",
     lambda p: _full_ask_signs(p, _flow(p, ["18m hana degedege, homa siku 3, MUAC 13.5 cm, miguu sawa"]))),
    ("T23", "all OPEN -> ASK_SIGNS with all 8 options",
     lambda p: _full_ask_signs(p, _flow(p, ["18m"]))),
    ("T25", "two unparseable replies -> REFER_NOW",
     lambda p: _ids(_flow(p, ["18m", "asante", "sawa"])) == ["REFER_NOW"]),
    ("T26", "'9' -> REFER_NOW not confirmed",
     lambda p: "not confirmed" in (_flow(p, ["18m", "9"]) or [{"body": ""}])[0]["body"]),
    ("T27", "'hana degedege' in an open case -> still OPEN, nothing sent",
     lambda p: _flow(p, ["18m", "hana degedege"]) == []),
    ("T28", "'0 3' -> REFER_NOW",
     lambda p: _ids(_flow(p, ["18m", "0 3"])) == ["REFER_NOW"]),
    ("T29", "'3 asante' -> REFER_NOW",
     lambda p: _ids(_flow(p, ["18m", "3 asante"])) == ["REFER_NOW"]),
    ("T35", "REFER + any input never lowers urgency",
     lambda p: all(_ids(_flow(p, ["18m degedege", x])) in (["REFERRED_LINE"], ["REFER_NOW"])
                   for x in ["0", "9", "hana degedege", "asante", "5"])),
]

EXTRA = [("FX1", "forced extractor exception", _forced_exception),
         ("FX2", "text never read ABSENT", _no_text_absent)]


def listed_ids():
    path = Path(__file__).resolve().parent.parent / "config" / "must_stay_red.list"
    return [l.strip() for l in path.read_text().splitlines() if l.strip() and not l.startswith("#")]


def run(proto, ids=None, verbose=False):
    """Returns the list of failed test IDs (empty = all pass)."""
    ids = ids or listed_ids()
    failed = []
    for tid, desc, cases in TESTS:
        if tid not in ids:
            continue
        ok = True
        for case, check, runner in cases:
            try:
                d = runner(proto, case) if runner else proto.evaluate(case)
                ok = ok and check(d)
            except Exception:
                ok = False
        if verbose:
            print(f"{tid:4} {'PASS' if ok else 'FAIL'}  {desc}")
        if not ok:
            failed.append(tid)
    for tid, desc, fn in TEXT_TESTS:
        if tid not in ids:
            continue
        try:
            ok = fn(proto)
        except Exception:
            ok = False
        if verbose:
            print(f"{tid:4} {'PASS' if ok else 'FAIL'}  {desc}")
        if not ok and tid not in failed:
            failed.append(tid)
    for tid, desc, fn in EXTRA:
        try:
            ok = fn(proto)
        except Exception:
            ok = False
        if verbose:
            print(f"{tid:4} {'PASS' if ok else 'FAIL'}  {desc}")
        if not ok:
            failed.append(tid)
    missing = [i for i in ids if i not in {t[0] for t in TESTS} | {t[0] for t in TEXT_TESTS}]
    return failed + [f"{m} (no test defined)" for m in missing]
