"""Referral loop: ALERT to facility + CHA with the case code; the facility texts the code on arrival -> ACK, ARRIVED."""
import re

from app import messages as M


class Referral:
    def __init__(self, store, reg):
        self.store, self.reg = store, reg

    def alert(self, case, reasons, parent=False):
        """Written to the outbox before any message that says 'Facility and CHA told'."""
        chp = self.reg.chp_by_phone.get(case["chp_phone"])
        cha = self.reg.cha_of_chp(chp) if chp else self.reg.default_cha
        st = case["state"]
        rs = list(reasons)
        if st.get("u2m") and "under 2 months" not in rs:
            rs.insert(0, "under 2 months")
        body = M.alert(case["code"], st.get("age_months"), rs, chp["chu"] if chp else "-", chp["id"] if chp else "-",
                       parent=parent)
        self.store.send(self.reg.facility["phone"], "facility", "ALERT", body, case["code"])
        self.store.send(cha["phone"], "cha", "ALERT", body, case["code"])

    def facility_text(self, sender, body):
        """Only registered facility or CHA numbers confirm. An unknown code gets no reply (no ACK = not recorded)."""
        if sender != self.reg.facility["phone"] and sender not in {c["phone"] for c in self.reg.cha.values()}:
            return
        m = re.search(r"\b(\d{4})\b", body)
        if not m:
            return
        case = self.store.case(m.group(1))
        if not case or case["status"] != "REFERRED":
            return
        self.store.update_case(case["code"], status="CLOSED")
        st = case["state"]
        chp = self.reg.chp_by_phone.get(case["chp_phone"])
        cha = self.reg.cha_of_chp(chp) if chp else self.reg.default_cha
        arrived = M.arrived(case["code"], st.get("age_months"), st.get("u2m"))
        if chp:
            self.store.send(chp["phone"], "chp", "ARRIVED", arrived, case["code"])
        self.store.send(cha["phone"], "cha", "ARRIVED", arrived, case["code"])
        self.store.send(sender, "facility", "ACK", M.ack(case["code"]), case["code"])
