"""Referral loop: ALERT to facility + CHA with the case code; the facility texts the code on arrival -> ACK, ARRIVED."""
import re

from app import messages as M


class Referral:
    def __init__(self, store, reg):
        self.store, self.reg = store, reg

    def alert(self, case, reasons, parent=False):
        """Written to the outbox before any message that says 'Facility and CHA told'."""
        import time as _t
        fresh = self.store.case(case["code"]) or case
        st0 = fresh["state"]
        st0["refer_reasons"] = list(dict.fromkeys(st0.get("refer_reasons", []) + list(reasons)))
        st0.setdefault("referred_at", _t.time())
        self.store.update_case(case["code"], state=st0)
        case = dict(case, state={**case["state"], **{k: st0[k] for k in ("refer_reasons", "referred_at")}})
        chp = self.reg.chp_by_phone.get(case["chp_phone"])
        cha = self.reg.cha_of_chp(chp) if chp else self.reg.default_cha
        st = case["state"]
        rs = list(reasons)
        if st.get("u2m") and "under 2 months" not in rs:
            rs.insert(0, "under 2 months")
        body = M.alert(case["code"], st.get("age_months"), rs, chp["chu"] if chp else "-", chp["id"] if chp else "-",
                       parent=parent or case.get("origin") == "parent")    # C10: PARENT SMS on parent-opened cases
        self.store.send(self.reg.facility_of_chp(chp)["phone"], "facility", "ALERT", body, case["code"])
        self.store.send(cha["phone"], "cha", "ALERT", body, case["code"])

    def facility_text(self, sender, body):
        """Only registered facility or CHA numbers confirm. An unknown code gets no reply (no ACK = not recorded).
        Counter-referral: exactly "{code} A", "{code} T{n}" or "{code} R" goes to outcome(); any other text is read
        as before (an arrival confirmation)."""
        if sender not in self.reg.facility_phones and sender not in {c["phone"] for c in self.reg.cha.values()}:
            return
        oc = re.fullmatch(r"(\d{4})\s+(?:([AR])|T\s*(\d{1,2}))", body.strip(), flags=re.I)
        if oc:
            return self.outcome(sender, oc.group(1), (oc.group(2) or "T").upper(), oc.group(3))
        m = re.search(r"\b(\d{4})\b", body)
        if not m:
            return
        case = self.store.case(m.group(1))
        if not case or case["status"] != "REFERRED":
            return
        import time as _t
        st_a = case["state"]
        st_a["arrived_at"] = _t.time()
        self.store.update_case(case["code"], status="CLOSED", state=st_a)
        st = case["state"]
        chp = self.reg.chp_by_phone.get(case["chp_phone"])
        cha = self.reg.cha_of_chp(chp) if chp else self.reg.default_cha
        arrived = M.arrived(case["code"], st.get("age_months"), st.get("u2m"))
        if chp:
            self.store.send(chp["phone"], "chp", "ARRIVED", arrived, case["code"])
        self.store.send(cha["phone"], "cha", "ARRIVED", arrived, case["code"])
        self.store.send(sender, "facility", "ACK", M.ack(case["code"]), case["code"])

    def outcome(self, sender, code, kind, n):
        """Counter-referral: registered facility numbers only, after ARRIVED, codes only. Tells the CHP and CHA;
        never messages the parent; never removes the follow-up reminder (board: T n moves it to day n)."""
        import time as _t

        def reject(reason):
            self.store.send(sender, "facility", "OUTCOME_REJECT", M.OUTCOME_REJECT.format(reason=reason), code)
        if sender not in self.reg.facility_phones:
            return reject("facility numbers only")
        case = self.store.case(code)
        if case is None:
            return reject("unknown code")
        st = case["state"]
        if not st.get("arrived_at"):
            return reject("arrival not recorded yet")
        if kind == "T" and not 1 <= int(n) <= 30:
            return reject("T days must be 1-30")
        st["outcome"] = {"kind": kind, "n": int(n) if kind == "T" else None, "at": _t.time()}
        self.store.update_case(code, state=st)
        label = M.OUTCOME_LABEL[kind].format(n=n)
        chp = self.reg.chp_by_phone.get(case["chp_phone"])
        cha = self.reg.cha_of_chp(chp) if chp else self.reg.default_cha
        msg = M.OUTCOME_CHP.format(head=M.head(code, st.get("age_months"), st.get("u2m")), time=M.hhmm(), outcome=label)
        if chp:
            self.store.send(chp["phone"], "chp", "OUTCOME", msg, code)
        self.store.send(cha["phone"], "cha", "OUTCOME", msg, code)
        self.store.send(sender, "facility", "OUTCOME_ACK", M.OUTCOME_ACK.format(code=code, time=M.hhmm()), code)
