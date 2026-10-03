"""Question suggestions (EXPERIMENTAL). A PURE function: it reads a case state and the bank and returns question ids
with a reason built from fixed parts only (sign name, head score, WHO source; review E6). It never imports or calls
the store or any send function (a test checks this). The health worker approves or declines every suggestion."""

LABEL = {"convulsions": "convulsions", "not_drink_feed": "cannot drink or feed", "vomits_everything": "vomits everything",
         "sleepy_unconscious": "very sleepy or cannot wake", "blood_stool": "blood in stool", "cough_long": "long illness",
         "diarrhoea_long": "long illness", "fever_long": "long illness"}
SIGN_OF_LABEL = {}
for _s, _l in LABEL.items():
    SIGN_OF_LABEL.setdefault(_l, []).append(_s)
MAX_PREARRIVAL = 2          # review SHOULD: at most 2 pre-arrival questions, never chased
MAX_PER_CASE = 3


def eligible(state):
    """Review M1: model drafts are off for under 2 months, no age, 5 years+, pregnancy and adult."""
    age = state.get("age_months")
    return (not state.get("u2m") and age is not None and 2 <= age <= 59
            and not state.get("pregnancy") and not state.get("adult"))


def triggered_signs(state):
    out = []
    for r in state.get("refer_reasons", []):
        for s in SIGN_OF_LABEL.get(r, []):
            if s not in out:
                out.append(s)
    return out


def suggest(state, bank_questions, status):
    """Up to MAX_PREARRIVAL pre-arrival question ids for a REFERRED case (Tier 1), linked to the sign(s) that
    triggered go now, in bank order; skips questions already asked or declined. Each with its fixed-part reason."""
    if status != "REFERRED" or not eligible(state):
        return []
    q = state.get("q") or {}
    done = set(q.get("asked", [])) | set(q.get("declined", []))
    if len(q.get("asked", [])) + len(q.get("own", [])) >= MAX_PER_CASE:   # one shared cap (review E5)
        return []
    pre_asked = sum(1 for e in q.get("asked", []) if e.startswith("PA_"))
    signs = triggered_signs(state)
    heads = (state.get("model") or {}).get("heads") or {}
    out = []
    for item in bank_questions:
        if item["kind"] != "prearrival" or item["id"] in done:
            continue
        hit = [s for s in signs if s in item["trigger_signs"]]
        if not hit:
            continue
        s = hit[0]
        reason = f"Linked to the sign that triggered go now: {LABEL[s]}."
        p = heads.get(s)
        if p is not None and p >= 0.5:                       # E6: never show a low score
            reason += f" Model score for {LABEL[s]}: {p:.2f}."
        reason += f" Source: {item['source']}."
        out.append({"id": item["id"], "reason": reason})
    return out[:max(0, MAX_PREARRIVAL - pre_asked)]
