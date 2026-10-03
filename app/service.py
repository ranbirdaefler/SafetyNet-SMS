"""Message routing by role (taken from the `to` line)."""
from app import messages as M
from app.chw import ChwFlow
from app.referral import Referral


def handle(store, reg, proto, role, sender, body):
    if proto is None:  # no valid protocol file: service down, never a guess
        if role == "chp":
            store.send(sender, "chp", "SERVICE_DOWN", M.SERVICE_DOWN)
        return
    if role == "chp":
        if sender not in reg.chp_by_phone:
            store.send(sender, "chp", "UNREGISTERED", M.UNREGISTERED)  # E1
            return
        ref = Referral(store, reg)
        ChwFlow(store, reg, proto, notify_referral=ref.alert).handle(sender, body)
    elif role == "facility":
        Referral(store, reg).facility_text(sender, body)
    # parent line: wired in D1
