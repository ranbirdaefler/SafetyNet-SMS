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


def suggest(state, bank_questions, status, table=None):
    """Up to MAX_PREARRIVAL pre-arrival question ids for a REFERRED case (Tier 1), linked to the sign(s) that
    triggered go now, in bank order; skips questions already asked or declined. Each with its fixed-part reason."""
    if status == "ASK_SIGNS" and eligible(state):
        return suggest_checks(state, bank_questions, table)
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


DUR_KIND = {"diarrhoea": "diarrhoea", "fever": "fever", "cough": "cough"}
SIGN_WHO = {"convulsions": "convulsions", "not_drink_feed": "not able to drink or feed", "vomits_everything": "vomits everything",
            "sleepy_unconscious": "unusually sleepy or unconscious", "blood_stool": "blood in stool",
            "cough_long": "long illness", "diarrhoea_long": "long illness", "fever_long": "long illness"}


def mentions(text, table, clauses, cues, durations, k=4):
    """Pure: which symptoms the text mentions WITHOUT a negation cue in the k words before (a denied symptom counts as
    not mentioned), and whether each has a readable duration. Returns {symptom: {"duration": bool}}."""
    out = {}
    for toks in clauses:
        for kind, row in table.items():
            phrases = [w.split() for w in row.get("words") or []]
            for i in range(len(toks)):
                hit = any(toks[i:i + len(p)] == p for p in phrases) or any(
                    st in toks[i] and not toks[i].startswith("ha") for st in row.get("verb_stems") or [])
                if not hit:
                    continue
                if any(t in cues for t in toks[max(0, i - k):i]):
                    continue                                          # denied: "hana homa", "no fever"
                out[kind] = {"duration": DUR_KIND.get(kind) in durations if DUR_KIND.get(kind) else True}
    return out


SLOT = {"CK_WAKE": "PAIR", "CK_DRINK": "PAIR"}           # the wake check, then the drink check: one slot
SLOT_ORDER = ["PAIR", "CK_VOMIT", "CK_FITS", "CK_BLOOD", "CK_DIARRHOEA_DAYS", "CK_FEVER_DAYS", "CK_COUGH_DAYS"]
MAX_SLOTS = 2                                            # at most 2 slots per case = at most 3 SMS


def suggest_checks(state, bank_questions, table=None):
    """Tier 2 (review M6 + Addendum B): checks on a TOLD case, ONLY with a signal: (a) the model scores the check's sign
    >= 0.5 (a wake or drink signal drafts the whole pair), (b) a mentioned, not denied symptom links to it in the bank's
    symptom table, (c) a mentioned symptom has no readable duration. No signal: nothing. Slots: the wake-then-drink
    pair is one slot; at most 2 slots per case (sent or declined). Order: model signals first, then PAIR, CK_VOMIT,
    CK_FITS, CK_BLOOD, then duration checks. Signs already PRESENT are skipped. Reasons from fixed parts (E6)."""
    q = state.get("q") or {}
    asked = list(q.get("asked", []))
    declined = list(q.get("declined", []))
    if len(asked) + len(q.get("own", [])) >= MAX_PER_CASE:
        return []
    done = set(asked) | set(declined)
    present = {s for s, v in (state.get("fields") or {}).items() if v == "PRESENT"}
    by_id = {it["id"]: it for it in bank_questions if it["kind"] == "check"}
    heads = (state.get("model") or {}).get("heads") or {}
    out = []
    if "CK_WAKE" in asked and "CK_DRINK" not in done and "CK_DRINK" in by_id and "not_drink_feed" not in present:
        out.append({"id": "CK_DRINK", "reason": "Second part of the pair: the drink check, after the wake check. "
                                                f"Source: {by_id['CK_DRINK']['source']}."})
    used = {SLOT.get(x, x) for x in done if x.startswith("CK_")}
    room = MAX_SLOTS - len(used)
    if room <= 0:
        return out[:MAX_PER_CASE - len(asked) - len(q.get("own", []))]
    reasons = {}                                             # slot -> reason (first rule that drew it)
    model_slots = []
    for qid, item in sorted(by_id.items(), key=lambda kv: -(heads.get(kv[1]["sign"]) or 0)):
        p = heads.get(item["sign"])
        if p is not None and p >= 0.5:
            slot = SLOT.get(qid, qid)
            if slot not in model_slots:
                model_slots.append(slot)
                reasons.setdefault(slot, f"The model ranked it: {LABEL[item['sign']]}, score {score_text(p)}.")
    linked = []
    for kind, info in (state.get("symptoms") or {}).items():
        row = (table or {}).get(kind) or {}
        for qid in row.get("checks") or []:
            linked.append(qid)
            if qid == "PAIR":
                reasons.setdefault("PAIR", f"Suggested because {kind} was mentioned; WHO lists 'unusually sleepy' and "
                                            "'not able to drink' as danger signs.")
            elif qid in by_id:
                reasons.setdefault(qid, f"Suggested because {kind} was mentioned; WHO lists "
                                        f"'{SIGN_WHO[by_id[qid]['sign']]}' as a danger sign.")
        if not info.get("duration") and row.get("duration_check"):
            linked.append(row["duration_check"])
            reasons.setdefault(row["duration_check"], f"Suggested because {kind} was mentioned without how long it has lasted.")
    rest = [x for x in dict.fromkeys(linked) if x not in model_slots]
    if len(state.get("symptoms") or {}) > 1:                 # several symptoms: the fixed global order
        rest.sort(key=lambda x: SLOT_ORDER.index(x) if x in SLOT_ORDER else 99)
    order = model_slots + rest                               # one symptom: its own order (vomiting: CK_VOMIT, PAIR)
    for slot in order:
        if room <= 0:
            break
        if slot in used:
            continue
        qid = "CK_WAKE" if slot == "PAIR" else slot
        item = by_id.get(qid)
        if item is None or item["sign"] in present:
            continue
        reason = reasons[slot] + (" Asked as a pair: the wake check first, then the drink check." if slot == "PAIR" else "")
        out.append({"id": qid, "reason": reason + f" Source: {item['source']}."})
        used.add(slot)
        room -= 1
    return out[:MAX_PER_CASE - len(asked) - len(q.get("own", []))]
