"""Question layer flow (EXPERIMENTAL): the health worker's approve / decline action, and parent answers.

Only active while app.questions is on. Review rules applied here:
- M1 drafts only for eligible cases; never to unregistered numbers.
- M2 sending a question is never a CHP reply: no status, due time or 'chp_replied' change.
- M3 answers never clear a sign; only danger (1) and not-sure (3) answers go to the facility, labelled
  "parent report, not checked"; a safe answer shows on her board as "not a check, you still check".
- M5 any non-bare reply in the window counts as "not sure" for that question, then the existing flow runs.
- M8 one pending question per case; the latest wins; 12 h window; after arrival answers go to her board only.
- E1 every parent message on a REFERRED case starts with the fixed "Keep going to the clinic." line.
"""
import time

from app import messages as M
from app import questions as Q
from app.suggest import LABEL, suggest

WINDOW_S = 12 * 3600
PREARRIVAL = "{code} PRE-ARRIVAL, parent report, not checked: {label} (answered {time}). Asked via CHP {chp}."


def qstate(st):
    return st.setdefault("q", {"asked": [], "declined": [], "log": [], "answers": [], "pending": None})


def suggestions(case):
    if not Q.is_on() or case is None:
        return []
    return suggest(case["state"], Q.approved_questions(), case["status"])


def chw_action(store, reg, proto, chp_phone, code, qid, action):
    """The ONLY way a bank question reaches a parent: her explicit approve on a suggested question."""
    if not Q.is_on():
        return {"ok": False, "error": "question layer off"}
    case = store.case(code)
    if case is None or case["chp_phone"] != chp_phone:
        return {"ok": False, "error": "not your case"}
    parent = case.get("parent_phone")
    if not parent or reg.parent(parent) is None:
        return {"ok": False, "error": "parent not registered"}
    offered = {s["id"]: s for s in suggestions(case)}
    if qid not in offered:
        return {"ok": False, "error": "not a current suggestion for this case"}
    chp = reg.chp_by_phone[chp_phone]
    st = case["state"]
    q = qstate(st)
    now = time.time()
    if action == "decline":
        q["declined"].append(qid)
        q["log"].append({"at": now, "qid": qid, "action": "declined", "by": chp["id"], "reason": offered[qid]["reason"]})
        store.update_case(code, state=st)
        return {"ok": True, "action": "declined"}
    if action != "approve":
        return {"ok": False, "error": "unknown action"}
    lang = reg.parent_lang(parent)
    body = Q.text_for(qid, lang, case["status"] == "REFERRED", proto.params)
    store.send(parent, "parent", "Q_" + qid, body, code)            # allowlisted fixed text (send-time check)
    q["asked"].append(qid)
    q["pending"] = {"id": qid, "at": now}                          # M8: latest wins
    q["log"].append({"at": now, "qid": qid, "action": "approved", "by": chp["id"], "reason": offered[qid]["reason"],
                     "text": "drafted by model, approved by CHP " + chp["id"]})
    store.update_case(code, state=st)                               # M2: status, due and chp_replied untouched
    return {"ok": True, "action": "approved", "msg_id": "Q_" + qid}


def on_parent_text(flow, phone, case, body):
    """Called from DoorFlow.handle BEFORE the REFERRED / CLOSED branches while the layer is on. Returns the case code
    when the text was a bare answer and fully handled here; None to let the existing flow run unchanged."""
    if case is None:
        return None
    st = case["state"]
    q = st.get("q") or {}
    pend = q.get("pending")
    if not pend:
        return None
    now = time.time()
    if now - pend["at"] > WINDOW_S:
        q["pending"] = None
        flow.store.update_case(case["code"], state=st)
        return None
    arrived = bool(st.get("arrived_at"))
    if case["status"] != "REFERRED" and not (case["status"] == "CLOSED" and arrived):
        return None
    item = Q.question(pend["id"])
    n = Q.parse_answer(body)
    bare = n is not None
    n = n or 3                                                      # M5: non-bare counts as "not sure"
    label = str(item["labels"][n]).format(**flow.proto.params)
    q["pending"] = None
    q["answers"].append({"at": now, "qid": pend["id"], "n": n, "label": label, "bare": bare,
                         "forwarded": (not arrived and n in (1, 3))})
    flow.store.update_case(case["code"], state=st)
    if not arrived and n in (1, 3):                                 # M3: only danger / not sure go to the facility
        chp = flow.reg.chp_by_phone.get(case["chp_phone"])
        fac = flow.reg.facility_of_chp(chp)
        flow.store.send(fac["phone"], "facility", "PREARRIVAL",
                        PREARRIVAL.format(code=case["code"], label=label, time=M.hhmm(now), chp=chp["id"] if chp else "-"),
                        case["code"])
    if not bare:
        return None                                                 # then the existing flow (D23 repeat) runs
    if not arrived:
        flow.store.send(phone, "parent", "Q_ACK", Q.ack_text(flow.reg.parent_lang(phone)), case["code"])
    return case["code"]


def board_lines(case):
    """Lines for her case card: suggestions are added by the server; here the log and the answers."""
    st = case["state"]
    q = st.get("q") or {}
    out = []
    for e in q.get("log", []):
        out.append(f"{M.hhmm(e['at'])} {e['qid']}: " + ("drafted by model, approved by CHP " + e["by"] if e["action"] == "approved"
                                                        else "drafted by model, declined by CHP " + e["by"]))
    for a in q.get("answers", []):
        tail = "" if a["bare"] else " (reply was not a bare 1/2/3: counted as not sure)"
        if a["n"] == 2:
            out.append(f"{M.hhmm(a['at'])} parent answered 2: {a['label']}: not a check, you still check{tail}")
        else:
            out.append(f"{M.hhmm(a['at'])} parent answered {a['n']}: {a['label']}" + (" (sent to facility)" if a["forwarded"] else "") + tail)
    return out
