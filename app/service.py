"""Message routing by role (taken from the `to` line)."""
from app import messages as M
from app.chw import ChwFlow
from app.door import DoorFlow
from app.referral import Referral


def handle(store, reg, proto, role, sender, body, extractors=None):
    if proto is None:  # no valid protocol file: service down, never a guess
        if role == "chp":
            store.send(sender, "chp", "SERVICE_DOWN", M.SERVICE_DOWN)
        return
    if role == "chp":
        if sender not in reg.chp_by_phone:
            store.send(sender, "chp", "UNREGISTERED", M.UNREGISTERED)  # E1
            return
        ref = Referral(store, reg)
        door = DoorFlow(store, reg, proto, ref, **_ex(extractors))
        ChwFlow(store, reg, proto, notify_referral=ref.alert, on_refer=door.on_chp_refer).handle(sender, body)
    elif role == "facility":
        Referral(store, reg).facility_text(sender, body)
    elif role == "parent":
        DoorFlow(store, reg, proto, Referral(store, reg), **_ex(extractors)).handle(sender, body)


def tick(store, reg, proto, now=None, extractors=None):
    """Fire every due time that has passed (also at start-up: overdue ones fire at once, D28)."""
    if proto is None:
        return 0
    ref = Referral(store, reg)
    door = DoorFlow(store, reg, proto, ref, **_ex(extractors))
    chw = ChwFlow(store, reg, proto, notify_referral=ref.alert, on_refer=door.on_chp_refer)
    n = 0
    for case in store.due_cases(now):
        if case["origin"] == "parent":
            door.on_due(case)
        else:
            chw.on_due(case)
        n += 1
    return n


def _ex(extractors):
    return {"extractors": extractors} if extractors else {}
