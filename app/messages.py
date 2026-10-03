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
