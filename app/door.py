"""Caregiver door: the parent line.

parent_policy() is the one function the live service and the eval harness both call (F5): regex, C4 list, scope,
shared stage, extractor. Parent text is read PRESENT or OPEN only (C1); the encoder can only add triggers (OR).
The parent only ever receives the 5 allowlisted strings and is never asked a question.
"""
import time
from dataclasses import dataclass, field

from app import lexicon, messages as M, textparse
from app.engine import PRESENT

SIGN_LABEL = {
    "convulsions": "convulsions", "not_drink_feed": "cannot drink or feed", "vomits_everything": "vomits everything",
    "sleepy_unconscious": "very sleepy or cannot wake", "blood_stool": "blood in stool",
    "cough_long": "long illness", "diarrhoea_long": "long illness", "fever_long": "long illness",
}
SIGN_ORDER = ["convulsions", "not_drink_feed", "vomits_everything", "sleepy_unconscious", "blood_stool",
              "cough_long", "diarrhoea_long", "fever_long"]
DURATION_PARAM = {"cough": ("cough_long", "cough_red_days"), "diarrhoea": ("diarrhoea_long", "diarrhoea_red_days"),
                  "fever": ("fever_long", "fever_red_days")}


def keyword_extractor(text):
    """Keyword list v0 on the parent line: caregiver sign rows only (chest, MUAC, feet go through the shared stage)."""
    return lexicon.match(text, lexicon.T_LIST, k=lexicon.V0_K, use_cues=True)


@dataclass
class Policy:
    reasons: list = field(default_factory=list)   # trigger reasons, fixed vocabulary and order
    age_months: float | None = None
    u2m: bool = False
    oos: str | None = None                        # "5 y+" / "pregnancy" / "adult"
    c4: list = field(default_factory=list)
    signs: list = field(default_factory=list)     # PRESENT caregiver signs (regex + extractor)
    text_not_read: bool = False

    @property
    def triggered(self):
        return bool(self.reasons)

    @property
    def action(self):
        """C9 order: trigger, under 2 m, 5 y+/pregnancy/adult, no age, else told."""
        if self.reasons:
            return "GO_NOW"
        if self.oos:
            return "OOS"
        if self.age_months is None:
            return "GO_NOW_NO_AGE"
        return "TOLD"


def parent_policy(text, params, extractors=(keyword_extractor,)):
    """Read one parent text. Extractors are tried in order; the first that runs is used (D26: if the encoder
    raises, the keyword list reads instead; if every extractor fails: go now, "text not read")."""
    p = textparse.parse(text)
    pol = Policy(age_months=p.age_months, u2m=p.u2m)
    found = None
    for ex in extractors:
        try:
            found = ex(text)
            break
        except Exception:
            continue
    signs = set()
    if found is None:
        pol.text_not_read = True
    else:
        signs |= {s for s, v in found.items() if v == PRESENT}
    for kind, days in p.durations.items():                 # shared duration regex (R1, R2, R4)
        fid, par = DURATION_PARAM[kind]
        if days >= params[par]:
            signs.add(fid)
    pol.signs = [s for s in SIGN_ORDER if s in signs]
    reasons = []
    for s in pol.signs:
        if SIGN_LABEL[s] not in reasons:
            reasons.append(SIGN_LABEL[s])
    shared = lexicon.match(text, lexicon.SHARED, use_cues=False)  # shared stage: ignores cues, both arms
    muac_red = p.muac_mm is not None and p.muac_mm < params["muac_red_below_mm"]
    if "muac_red" in shared or "feet_swelling" in shared or muac_red:
        reasons.append("MUAC red or swelling of both feet")
    pol.c4 = lexicon.c4(text)
    if "chest_indrawing" in shared and "breathing complaint" not in pol.c4:
        pol.c4 = ["breathing complaint"] + pol.c4          # a chest reading from parent text is a breathing complaint
    reasons += [r for r in pol.c4 if r not in reasons]
    if p.u2m:
        reasons.append("under 2 months")
    if pol.text_not_read:
        reasons.append("text not read")
    pol.reasons = reasons
    if p.pregnancy:
        pol.oos = "pregnancy"
    elif p.adult:
        pol.oos = "adult"
    elif p.age_months is not None and p.age_months > 59:
        pol.oos = "5 y+"
    return pol


def _order_reasons(reasons):
    """Signs first, then C4, then scope, then system; under 2 months leads in staff messages."""
    rs = list(dict.fromkeys(reasons))
    if "under 2 months" in rs:
        rs.remove("under 2 months")
        rs.insert(0, "under 2 months")
    return rs


class DoorFlow:
    def __init__(self, store, reg, proto, referral, extractors=(keyword_extractor,)):
        self.store, self.reg, self.proto, self.ref = store, reg, proto, referral
        self.extractors = extractors

    def fac(self):
        return self.reg.facility["name"]

    def due_seconds(self):
        t = self.proto.cfg["timeouts"]
        return t["demo_s"] if self.proto.cfg["profile"].get("demo_mode") else t["reply_window_min"] * 60

    def head(self, code, st):
        return M.head(code, st.get("age_months"), st.get("u2m"))

    # ---------- entry ----------
    def handle(self, phone, body):
        case = self.store.latest_case_for_parent(phone)
        parent = self.reg.parent(phone)
        if parent is None:
            return self.unregistered(phone, body, case)
        if case and case["status"] == "REFERRED":
            return self.send_parent(phone, "CG_GO_NOW", case["code"])          # D23 / CG18: repeat only
        if case and case["status"] == "ASK_SIGNS":
            return self.awaiting(phone, case, body)
        return self.new(phone, body)                                          # NEW, or CLOSED -> new code (D25)

    def send_parent(self, phone, msg_id, code, time_txt=None):
        body = M.PARENT_ALLOWLIST[msg_id].format(facility=self.fac(), code=code, time=time_txt or "")
        self.store.send(phone, "parent", msg_id, body, code)

    # ---------- D1 / D2: unregistered ----------
    def unregistered(self, phone, body, case):
        if case and case["status"] == "REFERRED_U" and time.time() - case["created"] < 24 * 3600:
            return self.send_parent(phone, "CG_GO_NOW_U", case["code"])      # D2: repeat only
        pol = parent_policy(body, self.proto.params, self.extractors)
        state = {"age_months": pol.age_months, "u2m": pol.u2m, "reasons": pol.reasons}
        code = self.store.create_case(None, "parent", state, "REFERRED_U", parent_phone=phone)
        cha = self.reg.default_cha
        reasons = ", ".join(_order_reasons(pol.reasons)) if pol.reasons else "signs not checked"
        self.store.send(cha["phone"], "cha", "CHA_UNREG", M.CHA_UNREG.format(code=code, reasons=reasons, phone=phone), code)
        self.send_parent(phone, "CG_GO_NOW_U", code)

    # ---------- NEW ----------
    def new(self, phone, body):
        pol = parent_policy(body, self.proto.params, self.extractors)
        chp = self.reg.chp_of_parent(phone)
        state = {"fields": {}, "age_months": pol.age_months, "u2m": pol.u2m, "pregnancy": False, "adult": False,
                 "durations": {}, "muac_mm": None, "extra": [], "parent_reasons": pol.reasons}
        act = pol.action
        if act == "GO_NOW":                                                   # D3
            return self.go_now(phone, chp, state, pol.reasons)
        if act == "OOS":                                                      # D6
            code = self.store.create_case(chp["phone"] if chp else None, "parent", state, "CLOSED", parent_phone=phone)
            if chp:
                cha = self.reg.cha_of_chp(chp)
                b = M.CHP_OOS.format(code=code, what=pol.oos, facility=self.fac(), phone=phone)
                self.store.send(chp["phone"], "chp", "CHP_OOS", b, code)
                self.store.send(cha["phone"], "cha", "CHP_OOS", b, code)
            return self.send_parent(phone, "CG_OOS", code)
        if act == "GO_NOW_NO_AGE":                                            # D5: no age -> go now at once
            return self.go_now(phone, chp, state, ["age not received"])
        if chp is None:                                                       # D7
            return self.go_now(phone, None, state, ["no CHP assigned"])
        if self.chp_busy(chp["phone"]):                                       # D8 / C6
            return self.go_now(phone, chp, state, ["CHP busy"])
        return self.told(phone, chp, state)                                   # D4

    def chp_busy(self, chp_phone):
        c = self.store.latest_case_for_chp(chp_phone)
        return bool(c and c["status"] in ("ASK_AGE", "ASK_SIGNS"))

    def go_now(self, phone, chp, state, reasons, code=None):
        """ALERT and CHP_GO_NOW are written first; then CG_GO_NOW ('Your health worker has been told')."""
        reasons = _order_reasons(reasons)
        if code is None:
            code = self.store.create_case(chp["phone"] if chp else None, "parent", state, "REFERRED", parent_phone=phone)
        else:
            self.store.update_case(code, status="REFERRED", state=state)
        case = self.store.case(code)
        self.ref.alert(case, reasons, parent=True)
        if chp:
            b = M.CHP_GO_NOW.format(head=self.head(code, state), reasons=", ".join(reasons), facility=self.fac(), phone=phone)
            self.store.send(chp["phone"], "chp", "CHP_GO_NOW", b, code)
        self.send_parent(phone, "CG_GO_NOW", code)
        return code

    def told(self, phone, chp, state):
        """D4: the CHP case opens all-open (never with the parent's readings); CHP_CALL + full ASK_SIGNS, then CG_TOLD."""
        due = time.time() + self.due_seconds()
        code = self.store.create_case(chp["phone"], "parent", state, "ASK_SIGNS", parent_phone=phone, due=due)
        hh = M.hhmm(due)
        call = M.CHP_CALL.format(head=self.head(code, state), phone=phone, time=hh, code=code)
        self.store.send(chp["phone"], "chp", "CHP_CALL", call, code)
        self.store.send(chp["phone"], "chp", "ASK_SIGNS",
                        M.ask_signs(code, state["age_months"], self.proto.params["cough_red_days"]), code)
        self.send_parent(phone, "CG_TOLD", code, time_txt=hh)
        return code

    # ---------- AWAITING ----------
    def awaiting(self, phone, case, body):
        pol = parent_policy(body, self.proto.params, self.extractors)
        st = case["state"]
        chp = self.reg.chp_by_phone.get(case["chp_phone"])
        if pol.triggered:                                                     # D13
            return self.go_now(phone, chp, st, pol.reasons, code=case["code"])
        if pol.age_months is not None and st.get("age_months") is not None and pol.age_months != st["age_months"]:
            return self.go_now(phone, chp, st, ["new age"], code=case["code"])  # D14
        return None                                                           # D15: nothing; no sign cleared

    # ---------- link: a CHP REFER on a parent-opened case also tells the parent (D16) ----------
    def on_chp_refer(self, case):
        if case.get("parent_phone") and self.reg.parent(case["parent_phone"]):
            self.send_parent(case["parent_phone"], "CG_GO_NOW", case["code"])
