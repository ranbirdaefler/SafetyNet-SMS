"""CHP (health-worker) line: deterministic. Regex + keyword list read PRESENT only; only a numbered reply clears a sign."""
import re
import time

from app import extract, messages as M
from app.engine import ABSENT, PRESENT

OPEN = ("ASK_AGE", "ASK_SIGNS")


def parse_reply(body, code):
    """Numbered reply -> ("zero",) | ("digits", {1..9}) | None (unparseable). A leading case code is ignored."""
    t = body.strip()
    if code and t.startswith(code):
        t = t[len(code):]
    t = t.strip(" ,.;/-\t\n")
    if t == "0":
        return ("zero",)
    m = re.match(r"^([0-9][0-9\s,.;/-]*)", t)
    if not m:
        return None
    digits = {int(ch) for ch in m.group(1) if ch.isdigit() and ch != "0"}
    return ("digits", digits) if digits else None


class ChwFlow:
    def __init__(self, store, reg, proto, notify_referral=None, on_refer=None):
        self.store, self.reg, self.proto = store, reg, proto
        self.notify_referral = notify_referral or (lambda case, reasons: None)
        self.on_refer = on_refer or (lambda case: None)

    def send(self, phone, msg_id, body, code=None):
        self.store.send(phone, "chp", msg_id, body, code)

    def handle(self, phone, body):
        case = self.store.latest_case_for_chp(phone)
        if case and case["status"] in OPEN:
            return self.reply_in_case(phone, case, body)
        if case and case["status"] == "REFERRED" and not self._has_age(body):
            return self.late_reply(phone, case, body)
        if case and case["status"] == "NON_RED" and time.time() - case["updated"] < self.window_s():
            return self.after_non_red(phone, case, body)
        self.new_case(phone, body)

    def window_s(self):
        return self.proto.cfg["timeouts"]["digit_window_h"] * 3600

    def reply_s(self):
        t = self.proto.cfg["timeouts"]
        return t["demo_s"] if self.proto.cfg["profile"].get("demo_mode") else t["reply_min"] * 60

    # ---------- D21 / D22: late replies on a REFERRED case ----------
    def late_reply(self, phone, case, body):
        code, state = case["code"], case["state"]
        r = parse_reply(body, code)
        added = []
        if r and r[0] == "digits":
            for d in sorted(r[1] - {9}):
                for f in self.proto.fields:
                    if f["option"] == d and state["fields"].get(f["id"]) != PRESENT:
                        state["fields"][f["id"]] = PRESENT
                        added.append(f["id"])
        if added:                                    # D21: reasons added; urgency never lowers
            d = self.proto.evaluate(extract.state_to_case(state))
            reasons = d.reasons + [e for e in state.get("extra", []) if e not in d.reasons]
            self.store.update_case(code, state=state)
            case = self.store.case(code)
            self.notify_referral(case, reasons)
            self.send(phone, "REFER_NOW", M.refer_now(code, state.get("age_months"), state.get("u2m"), reasons), code)
            return
        line = M.REFERRED_LINE.format(code=code)     # D22: CHA copied
        self.send(phone, "REFERRED_LINE", line, code)
        chp = self.reg.chp_by_phone.get(phone)
        cha = self.reg.cha_of_chp(chp) if chp else self.reg.default_cha
        self.store.send(cha["phone"], "cha", "REFERRED_LINE", line, code)

    # ---------- A1: for 24 h after NON_RED any digit 1-9 refers ----------
    def after_non_red(self, phone, case, body):
        code, state = case["code"], case["state"]
        r = parse_reply(body, code)
        if r and r[0] == "digits":
            for d in sorted(r[1]):
                if d == 9:
                    state["extra"].append("CHW reported error")
                else:
                    for f in self.proto.fields:
                        if f["option"] == d:
                            state["fields"][f["id"]] = PRESENT
            return self.decide(phone, code, state)
        c = extract.chp_case(body)
        if c.age_months is None and not c.u2m and any(v == PRESENT for v in c.fields.values()):
            state = extract.merge_present(state, c)  # ageless text adding PRESENT goes to that case
            return self.decide(phone, code, state)
        return self.new_case(phone, body)            # never absorbed: a new case (ASK_AGE if ageless)

    def _has_age(self, body):
        return extract.textparse.parse(body).age_months is not None

    # ---------- new case ----------
    def new_case(self, phone, body):
        c = extract.chp_case(body)
        state = extract.case_to_state(c)
        code = self.store.create_case(phone, "chp", state, "NEW")
        self.decide(phone, code, state)

    # ---------- replies ----------
    def reply_in_case(self, phone, case, body):
        code, state = case["code"], case["state"]
        state["chp_replied"] = True
        if case["status"] == "ASK_AGE":
            t = body.strip()
            if t.startswith(code):
                t = t[len(code):].strip()
            if re.fullmatch(r"\d{1,2}", t):
                t = f"{t} months"                       # ASK_AGE asks for months
            c = extract.chp_case(t)
            if c.age_months is not None or c.u2m:
                state["age_months"], state["u2m"] = c.age_months, c.u2m
            state = extract.merge_present(state, c)
            return self.decide(phone, code, state)
        # ASK_SIGNS
        r = parse_reply(body, code)
        if r and r[0] == "zero":
            for f in self.proto.field_ids:
                if state["fields"].get(f) != PRESENT:
                    state["fields"][f] = ABSENT      # only a numbered "0" clears a sign
            return self.decide(phone, code, state)
        if r and r[0] == "digits":
            for d in sorted(r[1]):
                if d == 9:
                    if "not confirmed" not in state["extra"]:
                        state["extra"].append("not confirmed")
                else:
                    for f in self.proto.fields:
                        if f["option"] == d:
                            state["fields"][f["id"]] = PRESENT
            return self.decide(phone, code, state)
        # free text in an open case: PRESENT only (N2)
        c = extract.chp_case(body)
        if c.age_months is not None and c.age_months != state["age_months"]:
            # M4: a new age while the old case waits escalates the old case at once; the text opens a new case
            state["extra"].append("new age")
            self.decide(phone, code, state)
            return self.new_case(phone, body)
        before = dict(state["fields"])
        state = extract.merge_present(state, c)
        d = self.proto.evaluate(extract.state_to_case(state))
        if d.output == "REFER_NOW" or state["fields"] != before:
            return self.decide(phone, code, state)
        n = case["unparseable"] + 1
        self.store.update_case(code, unparseable=n, state=state)
        if n >= 2:                                    # A3: two unparseable replies refer
            state["extra"].append("text not read")
            return self.decide(phone, code, state)

    # ---------- decision ----------
    def decide(self, phone, code, state):
        d = self.proto.evaluate(extract.state_to_case(state))
        extra = state.get("extra", [])
        if d.output == "REFER_NOW" or extra:
            reasons = d.reasons + [e for e in extra if e not in d.reasons]
            self.store.update_case(code, status="REFERRED", state=state)
            case = self.store.case(code)
            self.notify_referral(case, reasons)       # ALERT to facility + CHA first (B5)
            self.send(phone, "REFER_NOW", M.refer_now(code, state["age_months"], d.u2m or state["u2m"], reasons), code)
            self.on_refer(case)                       # D16: a REFER on a parent-opened case also sends CG_GO_NOW
        elif d.output == "REFER_U2M":
            self.store.update_case(code, status="REFERRED", state=state)
            self.notify_referral(self.store.case(code), ["under 2 months"])
            self.send(phone, "REFER_U2M", M.REFER_U2M.format(code=code), code)
            self.on_refer(self.store.case(code))
        elif d.output == "OOS_HUMAN":
            self.store.update_case(code, status="CLOSED", state=state)
            self.send(phone, "OOS_HUMAN", M.OOS_HUMAN.format(code=code, what=d.oos), code)
        elif d.output == "ASK_AGE":
            self.store.update_case(code, status="ASK_AGE", state=state, **self._due(code))
            self.send(phone, "ASK_AGE", M.ASK_AGE.format(code=code), code)
        elif d.output == "ASK_SIGNS":
            self.store.update_case(code, status="ASK_SIGNS", state=state, **self._due(code))
            self.send(phone, "ASK_SIGNS", M.ask_signs(code, state["age_months"], self.proto.params["cough_red_days"]), code)
        elif d.output == "NON_RED":
            self.store.update_case(code, status="NON_RED", state=state)
            self.send(phone, "NON_RED", M.non_red(code, state["age_months"]), code)
        return d

    def _due(self, code):
        """A3 silence timer for CHP-opened cases; on a parent-opened case the door due time stands (R17)."""
        case = self.store.case(code)
        if case["origin"] == "parent":
            return {}
        return {"due": time.time() + self.reply_s()}

    # ---------- A3: silence past the due time refers ----------
    def on_due(self, case):
        state = case["state"]
        state["extra"].append("age not received" if case["status"] == "ASK_AGE" else "no answer")
        self.decide(case["chp_phone"], case["code"], state)
