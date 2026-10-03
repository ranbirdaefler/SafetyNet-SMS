"""Case board for one health worker: built only from stored case records (no free text, nothing generated).

Columns: code, age, danger flag, signs recorded (fixed vocabulary), status, time, and a follow-up reminder.
Status: to check / referred / no reply / arrived / closed. Sort: rule-flagged danger first, then model
"possible", then model "unsure", then the rest; oldest first within each group. Model lines are band words only.
Reminders (board only, never sent as SMS) say only when to go back: arrived -> "follow-up visit due {date}";
closed with "0" -> "check on child due {date}"; date = stored arrival or close time + followup_days.
"""
import time

from app import messages as M
from app.engine import PRESENT

SIGN_REASONS = {"convulsions", "cannot drink or feed", "vomits everything", "very sleepy or cannot wake",
                "chest indrawing", "blood in stool", "long illness", "MUAC red or swelling of both feet",
                "breathing complaint", "parent says worse", "under 2 months", "not confirmed"}
DAY = 86400


def _date(ts):
    return time.strftime("%a %d %b", time.localtime(ts))


def row(case, proto):
    st = case["state"]
    labels = []
    for f in proto.fields:
        if st.get("fields", {}).get(f["id"]) == PRESENT and f["label"] not in labels:
            labels.append(f["label"])
    for r in st.get("refer_reasons", []):
        if r in SIGN_REASONS and r not in labels:
            labels.append(r)
    if st.get("u2m") and "under 2 months" not in labels:
        labels.insert(0, "under 2 months")
    status = case["status"]
    reminder, event_ts = None, case["updated"]
    n = proto.params["followup_days"]
    if status in ("ASK_AGE", "ASK_SIGNS"):
        shown = "to check"
    elif status == "REFERRED":
        shown = "no reply" if st.get("no_reply") else "referred"
        event_ts = st.get("referred_at", case["updated"])
    elif status == "CLOSED" and st.get("arrived_at"):
        shown, event_ts = "arrived", st["arrived_at"]
        reminder = M.FOLLOWUP_REFERRED.format(date=_date(st["arrived_at"] + n * DAY))
        oc = st.get("outcome")
        if oc:                                   # an outcome never removes the reminder; "T n" moves it to day n
            shown, event_ts = M.OUTCOME_LABEL[oc["kind"]].format(n=oc["n"]), oc["at"]
            if oc["kind"] == "T":
                reminder = M.FOLLOWUP_REFERRED.format(date=_date(oc["at"] + oc["n"] * DAY))
    elif status == "NON_RED":
        shown = "closed"
        reminder = M.FOLLOWUP_HOME.format(date=_date(case["updated"] + n * DAY))
    else:
        shown = "closed"
    age = st.get("age_months")
    m = st.get("model") or {}
    model_line = (M.BOARD_POSSIBLE.format(sign=m["sign"]) if m.get("band") == "possible"
                  else M.BOARD_UNSURE if m.get("band") == "unsure" else None)
    return {
        "code": case["code"],
        "age": "under 2m" if st.get("u2m") else (f"{int(age)}m" if age is not None else "age unknown"),
        "danger": bool(set(labels) & SIGN_REASONS),
        "signs": labels,
        "status": shown,
        "opened": M.hhmm(case["created"]),
        "time": M.hhmm(event_ts),
        "reminder": reminder,
        "model": model_line,
        **(_questions(case) if _ql_on() else {}),
        "model_band": m.get("band"),
        "created": case["created"],
    }


def board(store, chp_phone, proto):
    with store.lock:
        rows = store.db.execute("SELECT * FROM cases WHERE chp_phone = ? AND status != 'REFERRED_U'", (chp_phone,)).fetchall()
    out = [row(store._case(r), proto) for r in rows]
    group = {"possible": 1, "unsure": 2}
    out.sort(key=lambda r: (0 if r["danger"] else group.get(r["model_band"], 3), r["created"]))
    return out


def _ql_on():
    from app import questions as QL
    return QL.is_on()


def _questions(case):
    """Question layer (experimental): suggested questions with their reasons, the responsibility log and answers."""
    from app import qflow
    from app import questions as QL
    sugg = [{"id": s["id"], "reason": s["reason"], "text_en": QL.question(s["id"])["en"]} for s in qflow.suggestions(case)]
    from app.registry import Registry
    from pathlib import Path
    import os
    reg = _REG.get("r") or _REG.setdefault("r", Registry(os.environ.get(
        "SNS_REGISTRY", Path(__file__).resolve().parent.parent / "config" / "registry.yaml")))
    return {"q_suggestions": sugg, "q_lines": qflow.board_lines(case), "q_write": qflow.write_info(case, reg),
            "q_alert": (case["state"].get("q") or {}).get("alert")}


_REG = {}
