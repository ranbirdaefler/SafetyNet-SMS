"""Fixed outgoing SMS (English only). Text copied from SPEC.md; no free text is ever sent."""

HELP = "One SMS per sick child 2m-5y: age and signs. No names. No reply in 5 min? Use your chart booklet; any danger sign: refer now."
UNREGISTERED = "Health workers only. If a child is sick, go to a health facility now."
SERVICE_DOWN = "Service down. Use your chart booklet; any danger sign: refer now."

ASK_AGE = "{code}: child's age? Reply in months, e.g. 18."
ASK_SIGNS_HEAD = "{code} {age}m. Reply numbers, eg 2 5. 0=none of 1-8, all checked. 9=not sure."
OPTIONS = [
    "1 Convulsions in this illness",
    "2 Cannot drink or feed at all",
    "3 Vomits everything",
    "4 Unusually sleepy or cannot wake",
    "5 Chest indrawing at every breath (not only when crying)",
    "6 Blood in stool",
    "7 Long illness (cough {cough}+ d, diarrhoea 14+ d, fever 7+ d)",
    "8 MUAC red (age 6 m+), or a dent stays on both feet. Not measured: reply 9.",
]
REFER_NOW = "{head}: REFER NOW: {reasons}. Facility and CHA told. Write code {code} on MOH 100. Do not delay; follow your chart booklet."
REFER_U2M = "{code}: REFER: under 2 months, CHA copied. Facility told."
OOS_HUMAN = "{code}: not for this tool ({what}). Call your CHA. Any danger sign: refer now."
NON_RED = ("{code} {age}m: NO DANGER SIGN REPORTED: you replied 0. Not a diagnosis. Continue your chart booklet. "
           "You still refer if a danger sign appears, the child gets worse, or you are worried. If cough: count "
           "breaths for 60 s. Fast breathing, yellow MUAC or a problem you cannot treat: follow your chart booklet.")
REFERRED_LINE = "{code} is REFER. Problem? Call your CHA. New child? Send age first."


def age_txt(age_months):
    return str(int(age_months)) if age_months is not None else None


def head(code, age_months, u2m):
    """'{code} {age}m', or '{code}' when the age is unknown or under 2 months."""
    if age_months is None or u2m:
        return code
    return f"{code} {age_txt(age_months)}m"


def ask_signs(code, age_months, cough_days):
    opts = "\n".join(o.format(cough=cough_days) for o in OPTIONS)
    return ASK_SIGNS_HEAD.format(code=code, age=age_txt(age_months)) + "\n" + opts


def refer_now(code, age_months, u2m, reasons):
    rs = list(reasons)
    if u2m and "under 2 months" not in rs:
        rs.insert(0, "under 2 months")
    return REFER_NOW.format(head=head(code, age_months, u2m), reasons=", ".join(rs), code=code)


def non_red(code, age_months):
    return NON_RED.format(code=code, age=age_txt(age_months))

ALERT = "REFERRAL {code}: child {age}, {prefix}{reasons}, CHU {chu}, CHP {chp}, {time}. On arrival, text {code} here."
ACK = "{code}: arrival recorded {time}. CHP and CHA told."
ARRIVED = "{head}: child arrived at facility {time}. Follow up per chart booklet anyway."


def hhmm(ts=None):
    import time as _t
    return _t.strftime("%H:%M", _t.localtime(ts))


def alert(code, age_months, reasons, chu, chp_id, parent=False, ts=None):
    age = f"{age_txt(age_months)}m" if age_months is not None else "age unknown"
    return ALERT.format(code=code, age=age, prefix="PARENT SMS: " if parent else "", reasons=", ".join(reasons),
                        chu=chu, chp=chp_id, time=hhmm(ts))


def ack(code, ts=None):
    return ACK.format(code=code, time=hhmm(ts))


def arrived(code, age_months, u2m, ts=None):
    return ARRIVED.format(head=head(code, age_months, u2m), time=hhmm(ts))


# ---------- caregiver door (parent line allowlist: these 5 strings only) ----------
DS = ("fits, difficult or fast breathing, blood in stool, cannot drink or breastfeed, vomits everything, "
      "is very sleepy or hard to wake, or gets worse.")
CG_GO_NOW = "Take the child to {facility} NOW. Do not wait for the health worker. Show code {code} there. Your health worker has been told."
CG_GO_NOW_U = "Take the child to the nearest health facility NOW. Do not wait for the health worker. Show code {code} there. A health worker has been told."
CG_TOLD = "Your health worker has been told and will contact you. If no one calls or comes within {minutes} minutes, go to {facility}. Go there NOW if the child has " + DS
CG_TIMEOUT = "Your health worker has not replied. Take the child to {facility} NOW. Do not wait. Show code {code} there. The health team has been told."
CG_OOS = "This number is only for sick children under 5 years. Anyone else who is sick: go to {facility} NOW. Your health worker has been told."
PARENT_ALLOWLIST = {"CG_GO_NOW": CG_GO_NOW, "CG_GO_NOW_U": CG_GO_NOW_U, "CG_TOLD": CG_TOLD,
                    "CG_TIMEOUT": CG_TIMEOUT, "CG_OOS": CG_OOS}
# Question layer (experimental): msg_id -> the exact fixed texts allowed (bank texts approved by Florian, with and
# without the referred-case prefix). Filled by app.questions.load only while the layer is on; empty otherwise.
QL_TEMPLATES = {}

# ---------- staff strings the door adds ({phone} only in these five) ----------
CHP_CALL = "{head}: PARENT SMS, not checked. Call {phone} now; see the child by {time}. Start replies with {code}. Cannot see the child? Reply {code} 9."
CHP_GO_NOW = "{head}: PARENT SMS: {reasons}. Parent told: go to {facility} NOW. Facility and CHA told. Call {phone} now; follow your chart booklet."
CHP_TIMEOUT = "{head}: no reply by {time}; parent told to go to {facility}. Facility and CHA told. Call {phone}."
CHP_OOS = "{code}: PARENT SMS, not for this tool ({what}). Parent told: go to {facility} NOW. CHA copied. Call {phone}."
CHA_UNREG = "PARENT SMS {code}: number not registered, no facility told. Parent told: go now. {reasons}. Call {phone}."


# ---------- case board (shown on the board only; never sent as SMS) ----------
FOLLOWUP_REFERRED = "follow-up visit due {date}. Follow your chart booklet."
FOLLOWUP_HOME = "check on child due {date}. Follow your chart booklet."

BOARD_POSSIBLE = "model: possible {sign}, check"
BOARD_UNSURE = "model unsure: please read"


# ---------- parent language (CLAUDE.md rule 8, Florian 3 Oct) ----------
# Swahili parent strings are loaded only from config/parent_sw.json (fixed strings approved by Florian). Until that
# file exists every parent SMS stays English. CG_TOLD goes in the parent's registered language (sw default, or en);
# CG_GO_NOW, CG_GO_NOW_U, CG_TIMEOUT and CG_OOS are bilingual: Swahili first, English below (authoritative).
SW_PARENT = {}
BILINGUAL = ("CG_GO_NOW", "CG_GO_NOW_U", "CG_TIMEOUT", "CG_OOS")
SEGMENT_LIMIT = {"en": {"CG_TOLD": 3, "CG_GO_NOW": 1, "CG_GO_NOW_U": 1, "CG_TIMEOUT": 1, "CG_OOS": 1},
                 "sw": {"CG_TOLD": 3},
                 "bi": {"CG_GO_NOW": 2, "CG_GO_NOW_U": 2, "CG_TIMEOUT": 2, "CG_OOS": 3}}


def load_sw(path=None):
    import json
    from pathlib import Path
    p = Path(path) if path else Path(__file__).resolve().parent.parent / "config" / "parent_sw.json"
    SW_PARENT.clear()
    if p.exists():
        SW_PARENT.update(json.loads(p.read_text(encoding="utf-8")))


def parent_template(msg_id, lang="sw"):
    en = PARENT_ALLOWLIST[msg_id]
    if msg_id not in SW_PARENT:
        return en
    if msg_id == "CG_TOLD":
        return SW_PARENT[msg_id] if lang == "sw" else en
    return SW_PARENT[msg_id] + "\n" + en


def parent_text(msg_id, lang="sw", **slots):
    return parent_template(msg_id, lang).format(**slots)


def parent_variants(msg_id):
    """Every template the parent line may send for this message ID."""
    if msg_id in QL_TEMPLATES:
        return list(QL_TEMPLATES[msg_id])
    v = [PARENT_ALLOWLIST[msg_id]]
    if msg_id in SW_PARENT:
        v.append(parent_template(msg_id, "sw"))
    return v


load_sw()

# ---------- counter-referral (facility outcome; staff only, never to the parent) ----------
OUTCOME_ACK = "{code}: outcome recorded {time}. CHP and CHA told."
OUTCOME_CHP = "{head}: facility outcome {time}: {outcome}. Follow your chart booklet."
OUTCOME_REJECT = "Not recorded: {reason}. After arrival, send the code then A (admitted), T and days 1-30 (treated, sent home, e.g. T5) or R (referred on)."
OUTCOME_LABEL = {"A": "admitted", "T": "treated, sent home, follow-up day {n}", "R": "referred on"}
