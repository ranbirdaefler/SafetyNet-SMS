"""Text readers. CHP text: shared regex + keyword list only (PRESENT or nothing); the encoder never reads CHP text."""
from app import lexicon, textparse
from app.engine import PRESENT, Case


def keyword_rows():
    """The live keyword list (v0 = T-list sign rows + cues, k = 2; or E2) plus the R8, R10, R11 T-list terms."""
    rows = dict(lexicon.LIVE["rows"])
    rows.update(lexicon.SHARED)
    return rows


def chp_case(text, registered=True):
    p = textparse.parse(text)
    fields = lexicon.match(text, keyword_rows(), k=lexicon.LIVE["k"], use_cues=True)
    return Case(registered=registered, fields=fields, age_months=p.age_months, u2m=p.u2m,
                pregnancy=p.pregnancy, adult=p.adult, durations=dict(p.durations), muac_mm=p.muac_mm)


def case_to_state(c):
    return {"fields": c.fields, "age_months": c.age_months, "u2m": c.u2m, "pregnancy": c.pregnancy,
            "adult": c.adult, "durations": c.durations, "muac_mm": c.muac_mm, "extra": []}


def state_to_case(s, registered=True):
    return Case(registered=registered, fields=dict(s["fields"]), age_months=s["age_months"], u2m=s["u2m"],
                pregnancy=s["pregnancy"], adult=s["adult"], durations=dict(s["durations"]), muac_mm=s["muac_mm"])


def merge_present(state, c):
    """Text inside an open case can only add PRESENT (N2); it never clears a sign."""
    for f, v in c.fields.items():
        if v == PRESENT:
            state["fields"][f] = PRESENT
    for k, d in c.durations.items():
        state["durations"][k] = max(d, state["durations"].get(k, 0))
    if c.muac_mm is not None:
        state["muac_mm"] = c.muac_mm if state["muac_mm"] is None else min(c.muac_mm, state["muac_mm"])
    state["pregnancy"] |= c.pregnancy
    state["adult"] |= c.adult
    return state
