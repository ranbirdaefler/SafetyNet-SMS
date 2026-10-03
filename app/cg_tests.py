"""Caregiver must-stay-RED tests CG1-CG18 (CG16 retired) and the two never-output lints.

Run on every load next to T1-T35; any red CG test switches the door flag off (F4). Inputs are generated from the
T-list or written from SPEC.md; none come from (a), (b), Y or native text. The Swahili inputs share their source
with the keyword list, so they prove routing, not Swahili coverage.
"""
import re
import time
from pathlib import Path

from app import lexicon, messages as M
from app.registry import Registry
from app.store import Store

ROOT = Path(__file__).resolve().parent.parent
P1, P2, P3, P4, PU = "+254733000001", "+254733000002", "+254733000003", "+254733000004", "+254799000001"
CHP7, CHP8, FAC, CHA = "+254722000107", "+254722000108", "+254711000100", "+254711000200"
LINES = {"parent": "40100", "chp": "40101", "facility": "40102"}
LATER = 10 ** 6


class Env:
    """A scratch service: in-memory store, the live registry and protocol, the real handlers."""

    def __init__(self, proto, extractors=None):
        from app import service
        self.service, self.proto = service, proto
        self.store, self.reg = Store(":memory:"), Registry(ROOT / "config" / "registry.yaml")
        self.extractors = extractors
        self.all = []

    def send(self, phone, role, body):
        before = self.store.last_outbox_id()
        self.store.log_in(phone, LINES[role], role, body)
        self.service.handle(self.store, self.reg, self.proto, role, phone, body, extractors=self.extractors)
        out = self.store.outbox_since(before)
        self.all += out
        return out

    def fire(self, after=LATER):
        before = self.store.last_outbox_id()
        self.service.tick(self.store, self.reg, self.proto, now=time.time() + after, extractors=self.extractors)
        out = self.store.outbox_since(before)
        self.all += out
        return out


def ids(out):
    return [(m["recipient"], m["msg_id"]) for m in out]


def to(out, phone):
    return [m["msg_id"] for m in out if m["recipient"] == phone]


def alert_body(out):
    return next((m["body"] for m in out if m["msg_id"] == "ALERT"), "")


def go_now_with(out, phone, reason):
    """D3: CG_GO_NOW to the parent, ALERT naming the reason."""
    return to(out, phone) == ["CG_GO_NOW"] and reason in alert_body(out)


# ---------- CG1: every caregiver T-list term, EN and SW frames, registered and unregistered ----------
CG1_COND_B = ["child 18m no he cannot drink", "child 18m he didnt eat cannot drink",
              "mtoto miezi 18 hana nguvu hawezi kunyonya", "mtoto miezi 18 hawezi kula wala hawezi kunywa"]
CG1_DUR = [("kikohozi siku 14", "long illness"), ("kuhara siku 14", "long illness"), ("homa siku 7", "long illness"),
           ("cough 14 days", "long illness"), ("diarrhoea 14 days", "long illness"), ("fever 7 days", "long illness")]
LABEL = {"convulsions": "convulsions", "not_drink_feed": "cannot drink or feed", "vomits_everything": "vomits everything",
         "sleepy_unconscious": "very sleepy or cannot wake", "blood_stool": "blood in stool"}


def cg1_inputs():
    out = []
    for sign, terms in lexicon.T_LIST.items():
        for t in terms:
            out += [(f"child 18m {t}", LABEL[sign]), (f"mtoto miezi 18 {t}", LABEL[sign])]
    for t, lab in CG1_DUR:
        out += [(f"child 18m {t}", lab), (f"mtoto miezi 18 {t}", lab)]
    out += [(t, "cannot drink or feed") for t in CG1_COND_B]
    return out


def cg1(proto, extractors):
    for text, reason in cg1_inputs():
        e = Env(proto, extractors)
        if not go_now_with(e.send(P1, "parent", text), P1, reason):
            return False
        o = Env(proto, extractors).send(PU, "parent", text)
        cha = next((m["body"] for m in o if m["msg_id"] == "CHA_UNREG"), "")
        if to(o, PU) != ["CG_GO_NOW_U"] or reason not in cha:
            return False
    return True


def cg2(proto, ex):
    for text in ["child 59 days old fever", "mtoto wiki 6 ana homa", "newborn has a rash", "mtoto mwezi 1 ana homa"]:
        o = Env(proto, ex).send(P1, "parent", text)
        if to(o, P1) != ["CG_GO_NOW"] or "PARENT SMS: under 2 months" not in alert_body(o):
            return False
    return True


def cg3(proto, ex):
    words = ["child 18m breathing fast", "child 18m short of breath", "child 18m chest", "mtoto miezi 18 kifua kinaingia",
             "mtoto miezi 18 anapumua haraka"]
    for w in words:
        o = Env(proto, ex).send(P1, "parent", w)
        b = alert_body(o)
        if to(o, P1) != ["CG_GO_NOW"] or "breathing complaint" not in b or "chest indrawing" in b:
            return False
        e = Env(proto, ex)                                     # second text, while AWAITING
        e.send(P1, "parent", "child 18m has a rash")
        o = e.send(P1, "parent", w.split(" ", 2)[-1])
        if to(o, P1) != ["CG_GO_NOW"] or "breathing complaint" not in alert_body(o):
            return False
    return True


def cg3b(proto, ex):
    for w in ["child 18m getting worse", "child 18m sicker"]:
        o = Env(proto, ex).send(P1, "parent", w)
        if not go_now_with(o, P1, "parent says worse"):
            return False
        e = Env(proto, ex)
        e.send(P1, "parent", "child 18m has a rash")
        if not go_now_with(e.send(P1, "parent", w.split(" ", 2)[-1]), P1, "parent says worse"):
            return False
    return True


def cg4(proto, ex):
    cases = []
    for sign, terms in lexicon.SHARED.items():
        lab = "breathing complaint" if sign == "chest_indrawing" else "MUAC red or swelling of both feet"
        for t in terms:
            cases += [(f"child 18m {t}", lab), (f"mtoto miezi 18 {t}", lab)]
    cases.append(("child 18m MUAC 11.4 cm", "MUAC red or swelling of both feet"))
    for text, lab in cases:
        o = Env(proto, ex).send(P1, "parent", text)
        b = alert_body(o)
        if not go_now_with(o, P1, lab) or "chest indrawing" in b or b.endswith("age not received, CHU 3"):
            return False
    return True


CG5_TEXTS = ["child 18m no fits, no blood in stool, not vomiting everything, drinks well, awake and playing, fever 2 days",
             "mtoto miezi 18 hana degedege, hakuna damu kwenye kinyesi, hana kutapika kila kitu, anakunywa vizuri, anaamka"]


def _cg5_ok(e, o, text):
    if ids(o) != [(CHP7, "CHP_CALL"), (CHP7, "ASK_SIGNS"), (P1, "CG_TOLD")]:
        return False
    code = o[0]["case_code"]
    case = e.store.case(code)
    call = M.CHP_CALL.format(head=f"{code} 18m", phone=P1, time=M.hhmm(case["due"]), code=code)
    signs = M.ask_signs(code, 18, e.proto.params["cough_red_days"])
    return o[0]["body"] == call and o[1]["body"] == signs and all(v != "ABSENT" for v in case["state"]["fields"].values())


def cg5(proto, ex):
    for text in CG5_TEXTS:
        e = Env(proto, ex)
        if not _cg5_ok(e, e.send(P1, "parent", text), text):
            return False
    return True


def cg5b(proto, ex):
    e = Env(proto, ex)
    e.send(P1, "parent", CG5_TEXTS[1])
    return e.send(P1, "parent", "hana degedege sasa") == []


def _awaiting(proto, ex):
    e = Env(proto, ex)
    o = e.send(P1, "parent", "child 18m has a rash")
    return e, o[0]["case_code"]


def cg6(proto, ex):
    e, code = _awaiting(proto, ex)
    if e.fire(after=-5) != []:                     # nothing before the due time (no A3 REFER_NOW, R17)
        return False
    o = e.fire()
    if to(o, P1) != ["CG_TIMEOUT"] or to(o, CHP7) != ["CHP_TIMEOUT"] or "no CHP reply" not in alert_body(o):
        return False
    e, code = _awaiting(proto, ex)
    e.send(CHP7, "chp", f"{code} sawa")
    o = e.fire()
    return to(o, P1) == ["CG_GO_NOW"] and "not finished by due time" in alert_body(o)


def cg7(proto, ex):
    for late, expect in [("0", "REFERRED_LINE"), ("9", "REFERRED_LINE"), ("asante", "REFERRED_LINE"), ("5", "REFER_NOW")]:
        e, code = _awaiting(proto, ex)
        e.fire()
        o = e.send(CHP7, "chp", f"{code} {late}")
        if to(o, P1) != [] or expect not in to(o, CHP7):
            return False
    return True


def cg8(proto, ex):
    for replies in (["9"], ["5"], ["sawa", "asante"], ["child 3 years"]):
        e, code = _awaiting(proto, ex)
        o = []
        for r in replies:
            o = e.send(CHP7, "chp", f"{code} {r}")
        if "CG_GO_NOW" not in to(o, P1) or "REFER_NOW" not in to(o, CHP7):
            return False
    e, code = _awaiting(proto, ex)                  # CG8b: "0" -> NON_RED, nothing to the parent, no timeout later
    o = e.send(CHP7, "chp", f"{code} 0")
    return to(o, CHP7) == ["NON_RED"] and to(o, P1) == [] and e.fire() == []


def cg9(proto, ex):
    for text in ["my child has a cough", "mtoto ana kikohozi"]:
        e = Env(proto, ex)
        o = e.send(P1, "parent", text)
        if to(o, P1) != ["CG_GO_NOW"] or to(o, CHP7) != ["CHP_GO_NOW"] or "age not received" not in alert_body(o):
            return False
        if ids(e.send(P1, "parent", "child 18m")) != [(P1, "CG_GO_NOW")]:
            return False
    o = Env(proto, ex).send(P4, "parent", "mtoto ana kikohozi")
    return to(o, P4) == ["CG_GO_NOW"] and "no CHP assigned" in alert_body(o)


def cg9b(proto, ex):
    o = Env(proto, ex).send(PU, "parent", "child 18m has a rash")
    return ids(o) == [(CHA, "CHA_UNREG"), (PU, "CG_GO_NOW_U")]


def cg9c(proto, ex):
    for second in ["child 18m", "no fits", "degedege"]:
        e = Env(proto, ex)
        e.send(PU, "parent", "child has a rash")
        if ids(e.send(PU, "parent", second)) != [(PU, "CG_GO_NOW_U")]:
            return False
    return True


def cg10(proto, ex):
    for text in ["child 60 months has a rash", "my wife is pregnant and has fever", "an adult with fever"]:
        o = Env(proto, ex).send(P1, "parent", text)
        if to(o, P1) != ["CG_OOS"] or to(o, CHP7) != ["CHP_OOS"]:
            return False
        o = Env(proto, ex).send(P1, "parent", text + " and fits")
        if to(o, P1) != ["CG_GO_NOW"]:
            return False
    return True


def cg11(proto, ex):
    return to(Env(proto, ex).send(P1, "parent", "3 y and 1 m"), P1) == ["CG_GO_NOW"]


def cg12(proto, ex):
    e, code = _awaiting(proto, ex)
    o = e.send(P1, "parent", "child 3 years")
    return to(o, P1) == ["CG_GO_NOW"] and "new age" in alert_body(o)


def cg13(proto, ex):
    e = Env(proto, ex)
    e.send(CHP7, "chp", "18m homa siku 3")                       # CHP busy with its own child
    o = e.send(P1, "parent", "child 18m has a rash")
    if to(o, P1) != ["CG_GO_NOW"] or "CHP busy" not in alert_body(o):
        return False
    e, code = _awaiting(proto, ex)                              # CHP starts another child while the parent waits
    o = e.send(CHP7, "chp", "child 3 years cough")
    return "CG_GO_NOW" in to(o, P1)


def cg14(proto, ex):
    from app.door import keyword_extractor

    def boom(text):
        raise RuntimeError("forced")
    o = Env(proto, (boom, keyword_extractor)).send(P1, "parent", "child 18m degedege")
    if not go_now_with(o, P1, "convulsions"):
        return False
    o = Env(proto, (boom, boom)).send(P1, "parent", "child 18m has a rash")
    return go_now_with(o, P1, "text not read")


def cg15(proto, ex):
    import os
    import tempfile
    path = os.path.join(tempfile.mkdtemp(), "cg15.db")
    e = Env(proto, ex)
    e.store = Store(path)
    e.send(P1, "parent", "child 18m has a rash")
    e.store = Store(path)                                       # restart: due times reload from SQLite
    if e.fire(after=-5) != []:
        return False
    return to(e.fire(), P1) == ["CG_TIMEOUT"]


def cg17(proto, ex):
    e = Env(proto, ex)
    real = e.store.send

    def rejecting(recipient, role, *a, **k):
        if role == "chp":
            raise IOError("rejected after retries")
        return real(recipient, role, *a, **k)
    e.store.send = rejecting
    o = e.send(P1, "parent", "child 18m has a rash")
    return to(o, P1) == ["CG_GO_NOW"] and "CHP send failed" in alert_body(o)


def cg18(proto, ex):
    e = Env(proto, ex)
    e.send(P1, "parent", "child 18m degedege")
    if ids(e.send(P1, "parent", "asante")) != [(P1, "CG_GO_NOW")]:
        return False
    e, code = _awaiting(proto, ex)
    e.fire()
    return ids(e.send(P1, "parent", "child 18m has a rash")) == [(P1, "CG_GO_NOW")]


CG_TESTS = [("CG1", cg1), ("CG2", cg2), ("CG3", cg3), ("CG3b", cg3b), ("CG4", cg4), ("CG5", cg5), ("CG5b", cg5b),
            ("CG6", cg6), ("CG7", cg7), ("CG8", cg8), ("CG9", cg9), ("CG9b", cg9b), ("CG9c", cg9c), ("CG10", cg10),
            ("CG11", cg11), ("CG12", cg12), ("CG13", cg13), ("CG14", cg14), ("CG15", cg15), ("CG17", cg17),
            ("CG18", cg18)]


# ---------- lints ----------
BLOCKED = ["fine", "normal", "not serious", "don't worry", "safe", "all clear", "ok", "wait until", "tomorrow", "later",
           "home care", "give", "medicine", "mg", "ml", "tablet", "syrup", "fluids", "ors", "zinc", "amoxicillin",
           "paracetamol", "keep warm", "pneumonia", "malaria", "dehydration", "malnutrition", "%", "likely", "maybe",
           "probably", "reply 0", "reply 9", "="]
GSM7 = set("@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà")
SIGN_WORDS = ["fits", "breathing", "blood", "drink", "breastfeed", "vomits", "sleepy", "wake", "worse", "convulsions",
              "stool", "feed"]
PHONE_OK = {"CHP_CALL", "CHP_GO_NOW", "CHP_TIMEOUT", "CHP_OOS", "CHA_UNREG"}
STRIP = ["cannot drink or feed", "cannot wake", "not only when crying", "very sleepy or cannot wake"]
STAFF_SIGN = ["convulsions", "drink", "feed", "vomits", "sleepy", "wake", "indrawing", "blood", "stool", "illness",
              "muac", "feet", "breathing", "worse", "degedege", "fits"]


def _segments(s):
    return 1 if len(s) <= 160 else -(-len(s) // 153)


def lint_parent(msgs, facility_max="X" * 28):
    """1-4: allowlist, GSM-7, segments at max fill, blocked tokens, sign words only inside DS, repeats after go-now."""
    for mid, tpl in M.PARENT_ALLOWLIST.items():
        full = tpl.format(facility=facility_max, code="9999", time="23:59")
        if not set(full) <= GSM7 or _segments(full) > (2 if mid == "CG_TOLD" else 1):
            return f"{mid}: GSM-7 or segment count"
        low = tpl.lower()
        for b in BLOCKED:
            if re.search(r"(?<!\w)" + re.escape(b) + r"(?!\w)", low):
                return f"{mid}: blocked token '{b}'"
        outside = low.replace(M.DS.lower(), "")
        if any(re.search(r"\b" + w + r"\b", outside) for w in SIGN_WORDS):
            return f"{mid}: sign word outside DS"
    gone = set()                                   # case codes that already got a go-now or timeout
    for m in msgs:
        if m["role"] != "parent":
            continue
        if m["msg_id"] not in M.PARENT_ALLOWLIST:
            return f"parent got {m['msg_id']}"
        if m["case_code"] in gone and m["msg_id"] not in ("CG_GO_NOW", "CG_GO_NOW_U"):
            return f"after go-now, case {m['case_code']} got {m['msg_id']}"
        if m["msg_id"] in ("CG_GO_NOW", "CG_GO_NOW_U", "CG_TIMEOUT"):
            gone.add(m["case_code"])
    return None


def lint_staff(msgs):
    """6: no cue before a sign word within 2 tokens (no comma), no 'no danger sign', PARENT SMS in door ALERTs,
    {phone} only in the five door strings."""
    door_codes = {m["case_code"] for m in msgs if m["role"] == "parent"}
    for m in msgs:
        if m["role"] == "parent":
            continue
        body = m["body"]
        if re.search(r"\+254\d{9}", body) and m["msg_id"] not in PHONE_OK:
            return f"{m['msg_id']}: phone number outside the door strings"
        if m["msg_id"] == "ALERT" and m["case_code"] in door_codes and "PARENT SMS: " not in body:
            return "door ALERT without PARENT SMS"
        if m["msg_id"] in ("CHP_CALL", "CHP_GO_NOW", "CHP_TIMEOUT", "CHP_OOS", "CHA_UNREG", "ALERT"):
            if "no danger sign" in body.lower():
                return f"{m['msg_id']}: 'no danger sign'"
            low = body.lower()
            for s in STRIP:
                low = low.replace(s, " ")
            for seg in low.split(","):
                toks = re.findall(r"[a-z']+", seg)
                for i, t in enumerate(toks):
                    if t in lexicon.CUES and any(w in STAFF_SIGN for w in toks[i + 1:i + 3]):
                        return f"{m['msg_id']}: negation before a sign word"
    return None


def run(proto, extractors=None, verbose=False, variants=None):
    """Returns failed IDs. Runs every CG test once per variant [(tag, extractors)]; default: the live keyword list."""
    from app import lexicon
    from app.door import keyword_extractor
    variants = variants or [(lexicon.LIVE["name"], extractors or (keyword_extractor,))]
    failed, all_msgs = [], []
    for tag, ex in variants:
        for cid, fn in CG_TESTS:
            try:
                ok = fn(proto, ex)
            except Exception as err:
                ok = False
                if verbose:
                    print(f"{cid} raised {type(err).__name__}: {err}")
            if verbose:
                print(f"{cid:5} {'PASS' if ok else 'FAIL'}  ({tag})")
            if not ok:
                failed.append(f"{cid}({tag})")
    # lints over the messages a full scenario produces
    e = Env(proto, variants[0][1])
    for text in ["child 18m degedege", "mtoto ana kikohozi", "child 18m has a rash"]:
        e.send(P1, "parent", text)
        e.send(P2, "parent", text)
    e.send(PU, "parent", "child 18m has a rash")
    code = e.store.latest_case_for_parent(P2)["code"]
    e.send(CHP7, "chp", f"{code} 5")
    e.fire()
    for name, err in (("LINT-parent", lint_parent(e.all)), ("LINT-staff", lint_staff(e.all))):
        if verbose:
            print(f"{name} {'PASS' if err is None else 'FAIL: ' + err}")
        if err:
            failed.append(name)
    return failed
