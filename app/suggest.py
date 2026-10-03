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


def score_text(p):
    """E6: a model score is shown only when the model ranked the question; never below 0.5, never as 1.00."""
    if p is None or p < 0.5:
        return None
    return "above 0.99" if p > 0.99 else f"{p:.2f}"


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
    if status == "ASK_SIGNS" and eligible(state):
        return suggest_checks(state, bank_questions)
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
        term = (state.get("rule_terms") or {}).get(s)          # the rules found this sign: credit the rules, no score
        reason = f"Linked to the sign the rules found: {LABEL[s]}" + (f" ('{term}')" if term else "") + "."
        reason += f" Source: {item['source']}."
        out.append({"id": item["id"], "reason": reason})
    return out[:max(0, MAX_PREARRIVAL - pre_asked)]


GENERAL = ("convulsions", "not_drink_feed", "vomits_everything", "sleepy_unconscious")   # WHO general danger signs
DURATION = ("cough_long", "diarrhoea_long", "fever_long")
MAX_CHECKS = 2


def suggest_checks(state, bank_questions):
    """Tier 2: checks on a TOLD case, ranked by the model's per-sign scores; signs already PRESENT, questions already
    asked or declined are skipped; DRINK only after WAKE was asked; duration checks only when the model scores that
    long illness at 0.5 or more. Model unavailable: the bank's fixed order of the general danger signs."""
    q = state.get("q") or {}
    asked = list(q.get("asked", []))
    if len(asked) + len(q.get("own", [])) >= MAX_PER_CASE:
        return []
    done = set(asked) | set(q.get("declined", []))
    offered = [x for x in done if x.startswith("CK_")]
    if len(offered) >= MAX_CHECKS:                               # at most 2 checks offered per case, sent or declined
        return []
    present = {s for s, v in (state.get("fields") or {}).items() if v == "PRESENT"}
    heads = (state.get("model") or {}).get("heads") or {}
    cands = []
    for i, item in enumerate(bank_questions):
        if item["kind"] != "check" or item["id"] in done or item["sign"] in present:
            continue
        if item.get("after") and item["after"] not in asked:
            continue
        p = heads.get(item["sign"])
        if item["sign"] in DURATION and (p is None or p < 0.5):
            continue
        cands.append((-(p if p is not None and p >= 0.5 else 0.0), i, item, p))   # low scores: fixed bank order
    cands.sort(key=lambda c: (c[0], c[1]))
    out = []
    for _, _, item, p in cands[:MAX_CHECKS - len(offered)]:
        st = score_text(p)
        reason = (f"The model ranked it: {LABEL[item['sign']]}, score {st}." if st
                  else "One of the WHO danger signs (fixed order).")
        out.append({"id": item["id"], "reason": reason + f" Source: {item['source']}."})
    return out[:MAX_PER_CASE - len(asked) - len(q.get("own", []))]
