"""Message routing by role. B2 stub: the CHP line answers with fixed strings only; the rules engine arrives in B3/B4."""
from app import messages as M


def handle(store, reg, proto, role, sender, body):
    if proto is None:  # no valid protocol file: service down, never a guess
        if role == "chp":
            store.send(sender, "chp", "SERVICE_DOWN", M.SERVICE_DOWN)
        return
    if role == "chp":
        if sender not in reg.chp_by_phone:
            store.send(sender, "chp", "UNREGISTERED", M.UNREGISTERED)  # E1
            return
        store.send(sender, "chp", "HELP", M.HELP)
    # parent and facility lines: logged only until D1 / B5 wire them
