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
from app.suggest import LABEL, MAX_PER_CASE, suggest

WINDOW_S = 12 * 3600
PLAIN = {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", "…": "...",
         " ": " "}
PARENT_REPLIED = "{code}: parent replied to your message. Read now."
PREARRIVAL = "{code} PRE-ARRIVAL, parent report, not checked: {label} (answered {time}). Asked via CHP {chp}."


def qstate(st):
    q = st.setdefault("q", {})
    for k, v in (("asked", []), ("declined", []), ("log", []), ("answers", []), ("pending", None), ("own", []),
                 ("replies", []), ("chw_pending", None)):
        q.setdefault(k, v)
    return q


def used(q):
    """One shared cap per case (review E5): bank questions and her own messages together."""
    return len(q.get("asked", [])) + len(q.get("own", []))


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
    if used(q) >= MAX_PER_CASE:
        return {"ok": False, "error": "at most 3 messages per case"}
    lang = reg.parent_lang(parent)
    body = Q.text_for(qid, lang, case["status"] == "REFERRED", proto.params)
    store.send(parent, "parent", "Q_" + qid, body, code)            # allowlisted fixed text (send-time check)
    q["asked"].append(qid)
    q["pending"] = {"id": qid, "at": now}                          # M8: latest wins
    q["chw_pending"] = None
    q["alert"] = None
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
    now = time.time()
    cp = q.get("chw_pending")
    if not pend and cp and now - cp["at"] <= WINDOW_S:              # a reply to HER message: shown, never parsed
        q.setdefault("replies", []).append({"at": now, "text": body[:300]})
        if case["status"] == "ASK_SIGNS" and case.get("chp_phone"):   # E7: on a TOLD case, call her attention
            q["alert"] = "PARENT REPLIED: read now"
            flow.store.send(case["chp_phone"], "chp", "CHP_PARENT_REPLIED", PARENT_REPLIED.format(code=case["code"]), case["code"])
        flow.store.update_case(case["code"], state=st)
        return None                                                 # the existing flow runs (policy, D23 repeat)
    if not pend:
        return None
    if now - pend["at"] > WINDOW_S:
        q["pending"] = None
        flow.store.update_case(case["code"], state=st)
        return None
    item = Q.question(pend["id"])
    if case["status"] in ("ASK_SIGNS", "NON_RED") and item["kind"] == "check":
        return on_check_answer(flow, phone, case, body, item, now)   # Tier 2
    arrived = bool(st.get("arrived_at"))
    if case["status"] != "REFERRED" and not (case["status"] == "CLOSED" and arrived):
        return None
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


def on_check_answer(flow, phone, case, body, item, now):
    """Tier 2 (review M2, M4, M5, M8): an answer to an approved check on a TOLD case (or within 12 h after her '0').
    1 -> the sign is PRESENT and the existing go_now() runs (CG_GO_NOW first; no acknowledgement before it).
    3 on fits / drink / vomit / wake -> go now. 3 on blood or a duration -> 'call now' on her board; deadline unchanged.
    2 -> her board only ('not a check, you still check'). A non-bare reply counts as 3, then the existing flow."""
    from app.engine import PRESENT
    from app.suggest import GENERAL
    st = case["state"]
    q = st["q"]
    n = Q.parse_answer(body)
    bare = n is not None
    n = n or 3
    sign = item["sign"]
    label = str(item["labels"][n]).format(**flow.proto.params)
    q["pending"] = None
    q["answers"].append({"at": now, "qid": item["id"], "n": n, "label": label, "bare": bare, "forwarded": False})
    chp = flow.reg.chp_by_phone.get(case["chp_phone"])
    go = (n == 1) or (n == 3 and sign in GENERAL)
    if go:
        if n == 1:
            st.setdefault("fields", {})[sign] = PRESENT
        reason = f"{LABEL[sign]} (parent check)" if n == 1 else f"not sure: {LABEL[sign]} (parent check)"
        flow.store.update_case(case["code"], state=st)
        flow.go_now(phone, chp, st, [reason], code=case["code"])
        return case["code"]
    if n == 3:
        q["alert"] = f"Parent not sure: {label}. Call now."
    flow.store.update_case(case["code"], state=st)
    if not bare:
        return None                                                 # then the existing flow (awaiting) runs
    if case["status"] == "ASK_SIGNS" and case.get("due"):
        import math
        minutes = max(1, math.ceil((case["due"] - now) / 60))
        t = Q.ack_told_text(flow.reg.parent_lang(phone), minutes, flow.fac())
        if t:                                                       # only once Florian approved the text
            flow.store.send(phone, "parent", "Q_ACK_TOLD", t, case["code"])
    return case["code"]


def board_lines(case):
    """Lines for her case card: suggestions are added by the server; here the log and the answers."""
    st = case["state"]
    q = st.get("q") or {}
    out = []
    for e in q.get("log", []):
        what = {"approved": "drafted by model, approved by CHP ", "declined": "drafted by model, declined by CHP ",
                "edited": "edited and sent by CHP ", "written": "written and sent by CHP "}[e["action"]]
        out.append(f"{M.hhmm(e['at'])} {e['qid']}: " + what + e["by"])
    for o in q.get("own", []):
        out.append(f"{M.hhmm(o['at'])} her message: {o['text']} (replies are shown, not read automatically)")
    for r in q.get("replies", []):
        out.append(f"{M.hhmm(r['at'])} Parent replied: {r['text']}")
    for a in q.get("answers", []):
        tail = "" if a["bare"] else " (reply was not a bare 1/2/3: counted as not sure)"
        if a["n"] == 2:
            out.append(f"{M.hhmm(a['at'])} parent answered 2: {a['label']}: not a check, you still check{tail}")
        else:
            out.append(f"{M.hhmm(a['at'])} parent answered {a['n']}: {a['label']}" + (" (sent to facility)" if a["forwarded"] else "") + tail)
    return out


def write_info(case, reg):
    """What the 'write your own' box needs: the fixed, system-added start of the SMS and the room left (or None)."""
    if not Q.is_on() or case is None or case["status"] not in ("REFERRED", "ASK_SIGNS"):
        return None
    parent = case.get("parent_phone")
    chp = reg.chp_by_phone.get(case["chp_phone"])
    if not parent or reg.parent(parent) is None or chp is None or not chp.get("name"):
        return None
    if used(case["state"].get("q") or {}) >= MAX_PER_CASE:
        return None
    lang = reg.parent_lang(parent)
    lang = lang if lang in ("en", "sw") else "sw"
    first = Q.STATE["bank"]["prefix_chw_referred"][lang] + " " if case["status"] == "REFERRED" else ""   # E1
    start = first + chp["name"] + ", your health worker: "
    return {"start": start, "room": 160 - len(start)}


def chw_message(store, reg, proto, chp_phone, code, text, from_qid=None):
    """Her own (or edited) message to a parent, review E1-E6. Never parsed when the parent replies."""
    if not Q.is_on():
        return {"ok": False, "error": "question layer off"}
    case = store.case(code)
    if case is None or case["chp_phone"] != chp_phone:
        return {"ok": False, "error": "not your case"}
    info = write_info(case, reg)
    if info is None:
        return {"ok": False, "error": "not available for this case"}
    text = " ".join((text or "").split())
    for a_, b_ in PLAIN.items():                                       # GSM-7: typographic marks to plain ones
        text = text.replace(a_, b_)
    if not text:
        return {"ok": False, "error": "empty message"}
    if any(c not in Q.GSM and c not in Q.GSM_EXT for c in text):
        return {"ok": False, "error": "Not sent: use plain letters only (no emoji or special symbols)."}
    if Q.blocked_hits(text):                                          # E2
        return {"ok": False, "error": Q.STATE["bank"]["blocked"]["refuse_text"]}
    system = set(M.PARENT_ALLOWLIST.values()) | {t for v in M.QL_TEMPLATES.values() for t in v}
    if text in system:                                                # E3: never a system message as her whole text
        return {"ok": False, "error": "Not sent: this is a system message; use Approve instead."}
    body = info["start"] + text
    if Q.segments(body) > 1:
        return {"ok": False, "error": f"Not sent: too long for one SMS (at most {info['room']} plain characters)."}
    chp = reg.chp_by_phone[chp_phone]
    bank = Q.STATE["bank"]
    store.send_chw_msg(case["parent_phone"], body, code, {c["name"] for c in reg.chps.values() if c.get("name")},
                       set(bank["prefix_chw_referred"].values()))
    st = case["state"]
    q = qstate(st)
    now = time.time()
    q["own"].append({"at": now, "text": text, "from_qid": from_qid})
    q["pending"] = None                                               # E5: her message ends parsing of a bank question
    q["chw_pending"] = {"at": now}
    q["alert"] = None
    q["log"].append({"at": now, "qid": from_qid or "OWN", "action": "edited" if from_qid else "written", "by": chp["id"],
                     "reason": "", "text": ("edited" if from_qid else "written") + " by CHP " + chp["id"]})
    store.update_case(code, state=st)                                 # E4: status, due, chp_replied untouched
    return {"ok": True, "action": "edited" if from_qid else "written", "msg_id": "CHW_MSG"}
