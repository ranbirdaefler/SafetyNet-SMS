"""Case board for one health worker: built only from stored case records (no free text, nothing generated).

Columns: code, age, danger flag, signs recorded (fixed vocabulary), status, time, and a follow-up reminder.
Status: to check / referred / no reply / arrived / closed. Sort: danger first, then oldest first.
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
    elif status == "NON_RED":
        shown = "closed"
        reminder = M.FOLLOWUP_HOME.format(date=_date(case["updated"] + n * DAY))
    else:
        shown = "closed"
    age = st.get("age_months")
    return {
        "code": case["code"],
        "age": "under 2m" if st.get("u2m") else (f"{int(age)}m" if age is not None else "age unknown"),
        "danger": bool(set(labels) & SIGN_REASONS),
        "signs": labels,
        "status": shown,
        "opened": M.hhmm(case["created"]),
        "time": M.hhmm(event_ts),
        "reminder": reminder,
        "created": case["created"],
    }


def board(store, chp_phone, proto):
    with store.lock:
        rows = store.db.execute("SELECT * FROM cases WHERE chp_phone = ? AND status != 'REFERRED_U'", (chp_phone,)).fetchall()
    out = [row(store._case(r), proto) for r in rows]
    out.sort(key=lambda r: (not r["danger"], r["created"]))
    return out
