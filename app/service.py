"""Message routing by role (taken from the `to` line)."""
from app import messages as M
from app.chw import ChwFlow
from app.door import DoorFlow
from app.referral import Referral


def handle(store, reg, proto, role, sender, body, extractors=None, board_model=None):
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
        if board_model is not None:                     # board only: after the reply is decided and sent
            from app.board_model import annotate
            annotate(store, board_model, sender, body)


def tick(store, reg, proto, now=None, extractors=None):
    """Fire every due time that has passed (also at start-up: overdue ones fire at once, D28)."""
    if proto is None:
        return 0
    ref = Referral(store, reg)
    door = DoorFlow(store, reg, proto, ref, **_ex(extractors))
    chw = ChwFlow(store, reg, proto, notify_referral=ref.alert, on_refer=door.on_chp_refer)
    n = 0
    store.purge(proto.params["retention_days"], now=now if now and now < __import__("time").time() + 1 else None)
    for case in store.due_cases(now):
        if case["origin"] == "parent":
            door.on_due(case)
        else:
            chw.on_due(case)
        n += 1
    return n


def _ex(extractors):
    return {"extractors": extractors} if extractors else {}


def door_off(store, reg, sender):
    """Door flag off (a red CG test, or no valid protocol): never silence. The parent gets the fixed CG_GO_NOW_U
    (the text is not read) and the CHA gets an ALERT copy with the reason "text not read"."""
    parent = reg.parent(sender)
    chp = reg.chp_of_parent(sender) if parent else None
    code = store.create_case(chp["phone"] if chp else None, "parent", {"age_months": None, "u2m": False}, "REFERRED_U",
                             parent_phone=sender)
    cha = reg.cha_of_chp(chp) if chp else reg.default_cha
    body = M.alert(code, None, ["text not read"], chp["chu"] if chp else "-", chp["id"] if chp else "-", parent=True)
    store.send(cha["phone"], "cha", "ALERT", body, code)
    store.send(sender, "parent", "CG_GO_NOW_U", M.parent_text("CG_GO_NOW_U", reg.parent_lang(sender), code=code), code)
