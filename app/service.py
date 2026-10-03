"""Message routing by role (taken from the `to` line)."""
from app import messages as M
from app.chw import ChwFlow


def handle(store, reg, proto, role, sender, body):
    if proto is None:  # no valid protocol file: service down, never a guess
        if role == "chp":
            store.send(sender, "chp", "SERVICE_DOWN", M.SERVICE_DOWN)
        return
    if role == "chp":
        if sender not in reg.chp_by_phone:
            store.send(sender, "chp", "UNREGISTERED", M.UNREGISTERED)  # E1
            return
        ChwFlow(store, reg, proto).handle(sender, body)
    # parent and facility lines: wired in D1 / B5
