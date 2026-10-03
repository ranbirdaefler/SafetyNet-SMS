"""Card sampler for synthetic caregiver-voice data (X train, Y-dev, Y-test) and the set (b) grid.

A card fixes the label (the 8-bit PRESENT vector, category, age) before any text is generated.
Labels always come from the card, never from the generated text.
"""
import random

HEADS = [
    "convulsions", "not_drink_feed", "vomits_everything", "sleepy_unconscious",
    "blood_stool", "cough_long", "diarrhoea_long", "fever_long",
]

# How each PRESENT sign is described to the generator, per form.
SIGN_TEXT = {
    "convulsions": {
        "plain": "the child had convulsions (fits) during this illness; use the common word (fits / convulsions / degedege)",
        "lay": "the child had convulsions during this illness; describe what the parent saw (body stiffening, jerking or shaking that the child could not control, eyes rolling) without using the words fits, convulsions or degedege",
        "hedged": "the parent thinks the child may have had a fit (convulsion) during this illness but is not sure",
        "negative_form": "the child had a fit (convulsion) during this illness and the parent could not stop the jerking",
    },
    "not_drink_feed": {
        "plain": "the child cannot drink or breastfeed at all; use plain words for it",
        "lay": "the child is not able to drink or feed anything; describe it in the parent's own words (refuses or cannot swallow any water or breast milk, everything offered is refused)",
        "hedged": "the parent thinks the child is not able to drink or breastfeed anything at all, but sounds unsure",
        "negative_form": "the child is not able to drink or feed anything; say it in negative form (for example 'he does not drink anything, not even water', 'hawezi kunyonya')",
    },
    "vomits_everything": {
        "plain": "the child vomits everything; use plain words for it",
        "lay": "the child vomits everything; describe it (every drink or feed comes back up, nothing stays in the stomach)",
        "hedged": "the parent thinks the child is vomiting everything, nothing seems to stay down, but sounds unsure",
        "negative_form": "the child vomits everything; say it in negative form (for example 'nothing stays down', 'hakuna kinachobaki tumboni')",
    },
    "sleepy_unconscious": {
        "plain": "the child is unusually sleepy or very hard to wake; use plain words for it",
        "lay": "the child is unusually sleepy; describe it (keeps falling back asleep, does not respond properly when woken, floppy)",
        "hedged": "the parent thinks the child is unusually sleepy and hard to wake, but is not sure",
        "negative_form": "the child is very hard to wake; say it in negative form (for example 'he does not wake up properly', 'haamki vizuri')",
    },
    "blood_stool": {
        "plain": "there is blood in the child's stool; use plain words for it",
        "lay": "there is blood in the child's stool; describe what the parent saw (red streaks or blood in the poo/diaper)",
        "hedged": "the parent thinks they saw blood in the child's stool but is not sure",
        "negative_form": "there is blood in the child's stool; mention it in passing (for example 'the stool is not normal, it has blood')",
    },
}

DUR_TEXT = {
    "cough_long": ("cough", 14, 30),
    "diarrhoea_long": ("diarrhoea (loose watery stools)", 14, 30),
    "fever_long": ("fever (hot body)", 7, 14),
}

NEAR_MISS = [
    "the child vomits sometimes but keeps water and breast milk down",
    "the child sleeps more than usual but wakes easily and feeds well",
    "the child eats less food than usual but drinks and breastfeeds normally",
    "there is some mucus in the child's stool but no blood",
    "the child shivers and shakes when the fever is high, but has had no fits",
    "the child seems tired and weak but is alert and plays a little",
    "the child vomited a few times today but is drinking",
    "the child is fussy and refuses some food but still breastfeeds",
]

NEGATABLE = {
    "convulsions": "the child has had no fits / convulsions",
    "not_drink_feed": "the child is drinking and breastfeeding well",
    "vomits_everything": "the child is not vomiting",
    "sleepy_unconscious": "the child is not unusually sleepy; awake and alert",
    "blood_stool": "there is no blood in the stool",
}

PLAIN_COMPLAINTS = [
    "a skin rash", "a runny nose", "an ear ache", "red sticky eyes", "a mild fever since yesterday",
    "teething and drooling", "small sores on the skin", "a cold with sneezing", "a little cough since 2 days",
    "loose stool once today", "a small burn on the hand that is healing", "itching skin",
]

MILD = ["a runny nose", "a mild fever", "a little cough", "a rash", "poor appetite", "fussiness"]


def _age(rng):
    m = rng.randint(2, 59)
    if m >= 12 and rng.random() < 0.3:
        y = m // 12
        return m, f"{y} years old (write it in years)" if y > 1 else "1 year old (write it in years)"
    return m, f"{m} months old"


def _duration(sign, form, rng):
    name, lo, hi = DUR_TEXT[sign]
    d = rng.randint(lo, hi)
    if form == "hedged":
        d = lo  # a hedged count at the threshold counts as present
        txt = f"{name} for about {d} days" if sign != "fever_long" else f"{name} for about a week"
    elif d % 7 == 0 and rng.random() < 0.5:
        txt = f"{name} for {d // 7} weeks"
    else:
        txt = f"{name} for {d} days"
    if form in ("lay", "negative_form"):
        txt += " (say it with relative time)"
    return txt


def _present_line(sign, form, rng):
    if sign in DUR_TEXT:
        return _duration(sign, form, rng)
    return SIGN_TEXT[sign][form]


def _lang(rng, weights=(0.45, 0.30, 0.25)):
    return rng.choices(["Swahili", "English", "code-mixed"], weights=weights)[0]


def _style(rng):
    s = []
    if rng.random() < 0.3:
        s.append("casual")
    if rng.random() < 0.10:
        s.append("two texts")
    return s


def _form(rng):
    return rng.choices(["plain", "lay", "hedged", "negative_form"], weights=(0.40, 0.30, 0.20, 0.10))[0]


def danger_card(rng, primary):
    signs = [primary]
    if rng.random() < 0.25:
        signs.append(rng.choice([h for h in HEADS if h != primary]))
    age_m, age_txt = _age(rng)
    forms = {s: _form(rng) for s in signs}
    facts = [_present_line(s, forms[s], rng) for s in signs]
    if rng.random() < 0.4:
        mild = [m for m in MILD if not (("cough" in m and "cough_long" in signs) or ("fever" in m and "fever_long" in signs))]
        facts.append(f"also {rng.choice(mild)}")
    return {"category": "danger", "signs": signs, "forms": forms, "age_months": age_m,
            "age_text": age_txt, "facts": facts, "lang": _lang(rng), "style": _style(rng)}


def no_danger_card(rng, kind):
    age_m, age_txt = _age(rng)
    if kind == "negated":
        neg = rng.sample(sorted(NEGATABLE), rng.choice([1, 1, 2]))
        facts = [rng.choice(PLAIN_COMPLAINTS)] + [NEGATABLE[n] + " (say this as a denial, e.g. 'no fits', 'hana degedege')" for n in neg]
    elif kind == "near_miss":
        r = rng.random()
        if r < 0.5:
            facts = [rng.choice(NEAR_MISS)]
        else:
            sign = rng.choice(sorted(DUR_TEXT))
            name, lo, _ = DUR_TEXT[sign]
            facts = [f"{name} for {rng.randint(max(1, lo - 9), lo - 2)} days"]
    else:
        facts = [rng.choice(PLAIN_COMPLAINTS)]
    return {"category": "no_danger", "kind": kind, "signs": [], "age_months": age_m, "age_text": age_txt,
            "facts": facts, "lang": _lang(rng), "style": _style(rng)}


def shared_card(rng, kind):
    if kind == "u2m":
        r = rng.random()
        if r < 0.4:
            d = rng.randint(3, 50)
            age_m, age_txt = 0, f"{d} days old"
        elif r < 0.8:
            w = rng.randint(1, 7)
            age_m, age_txt = 0, f"{w} weeks old"
        else:
            age_m, age_txt = 0, "1 month old"
        facts = [rng.choice(["a mild fever", "a skin rash", "a runny nose", "sticky eyes", "a little cough"])]
    elif kind == "breathing":
        age_m, age_txt = _age(rng)
        facts = ["breathing complaint: the child is breathing fast or with difficulty (say it in the parent's words)"]
    else:  # no_age
        age_m, age_txt = None, "no age"
        facts = [rng.choice(PLAIN_COMPLAINTS)]
    return {"category": "shared", "kind": kind, "signs": [], "age_months": age_m, "age_text": age_txt,
            "facts": facts, "lang": _lang(rng), "style": _style(rng)}


def sample_split(name, n_danger, n_no, n_shared, seed, min_per_sign=0):
    rng = random.Random(seed)
    cards = []
    primaries = [HEADS[i % 8] for i in range(n_danger)]
    rng.shuffle(primaries)
    for p in primaries:
        cards.append(danger_card(rng, p))
    # top up to min_per_sign by adding a second sign where needed
    for h in HEADS:
        while sum(h in c["signs"] for c in cards if c["category"] == "danger") < min_per_sign:
            c = rng.choice([c for c in cards if c["category"] == "danger" and len(c["signs"]) == 1 and h not in c["signs"]])
            f = _form(rng)
            c["signs"].append(h)
            c["forms"][h] = f
            c["facts"].insert(1, _present_line(h, f, rng))
    kinds = ["negated"] * round(n_no * 0.4) + ["near_miss"] * round(n_no * 0.4)
    kinds += ["plain"] * (n_no - len(kinds))
    for k in kinds:
        cards.append(no_danger_card(rng, k))
    sk = ["u2m", "breathing", "no_age"]
    for i in range(n_shared):
        cards.append(shared_card(rng, sk[i % 3]))
    rng.shuffle(cards)
    for i, c in enumerate(cards):
        c["id"] = f"{name}-{i + 1:04d}"
        c["present"] = [int(h in c["signs"]) for h in HEADS]
    return cards


SPLITS = {
    # name: (danger, no_danger, shared, seed, min_per_sign)
    "x_train": (660, 420, 120, 1001, 40),
    "y_dev": (60, 45, 15, 2002, 8),
    "y_test": (80, 55, 15, 3003, 10),
    # fresh test set for v3 (Sat 3 Oct): claude-opus-5-5, new seed, Y-test size and mix; 40% of no-danger cards are denials
    "y_test2": (80, 55, 15, 7007, 10),
}

# Set (b): the D01-D12 / N01-N13 grid from PREREGISTRATION.md section 3, Swahili, 12/13/0.
GRID_B = [
    ("D01", "convulsions", ["the child had convulsions (fits) during this illness; use the common word"], 1),
    ("D02", "convulsions", ["the child had convulsions during this illness; describe what the parent saw without naming it, and hedge (the parent is not sure)"], 1),
    ("D03", "not_drink_feed", ["the child cannot drink or breastfeed at all"], 1),
    ("D04", "not_drink_feed", ["the child cannot drink or feed anything, said in negative form (e.g. does not drink anything, not even water)"], 2),
    ("D05", "vomits_everything", ["the child vomits everything"], 1),
    ("D06", "vomits_everything", ["the child vomits everything; describe it (every drink or feed comes back up)"], 1),
    ("D07", "sleepy_unconscious", ["the child is very sleepy, unusually so"], 1),
    ("D08", "sleepy_unconscious", ["the child is hard to wake; the parent hedges (not sure)"], 1),
    ("D09", "blood_stool", ["there is blood in the child's stool"], 2),
    ("D10", "cough_long", ["cough for 16 days, said with relative time (say it with relative time)"], 1),
    ("D11", "fever_long", ["fever for about a week"], 1),
    ("D12", "diarrhoea_long", ["diarrhoea (loose watery stools) for 3 weeks"], 1),
    ("N01", None, ["a mild fever", "the child has had no fits / convulsions (say this as a denial)"], 1),
    ("N02", None, ["loose stool", "there is no blood in the stool (say this as a denial)"], 1),
    ("N03", None, ["a runny nose", "the child is not unusually sleepy (say this as a denial)"], 1),
    ("N04", None, ["a mild fever", "the child is drinking and breastfeeding well (say it as a denial of a problem, e.g. no problem drinking)"], 1),
    ("N05", None, ["the child vomits sometimes but keeps water and breast milk down"], 1),
    ("N06", None, ["the child sleeps more than usual but wakes easily and feeds well"], 1),
    ("N07", None, ["fever for 5 days"], 1),
    ("N08", None, ["cough for 10 days"], 1),
    ("N09", None, ["diarrhoea (loose watery stools) for 4 days"], 2),
    ("N10", None, ["the child eats less food than usual but drinks and breastfeeds normally"], 1),
    ("N11", None, ["fever for 2 days"], 1),
    ("N12", None, ["a skin rash"], 1),
    ("N13", None, ["a runny nose"], 1),
]


def grid_b_cards(seed=4004):
    rng = random.Random(seed)
    cards = []
    for gid, sign, facts, n_texts in GRID_B:
        age_m, age_txt = _age(rng)
        cards.append({
            "id": gid, "category": "danger" if gid.startswith("D") else "no_danger",
            "signs": [sign] if sign else [], "age_months": age_m, "age_text": age_txt,
            "facts": facts, "lang": "Swahili", "style": ["two texts"] if n_texts == 2 else [],
        })
    return cards


def render(card):
    """The user prompt for one card."""
    lines = ["Case card:", f"- Language: {card['lang']}"]
    if card["age_text"] == "no age":
        lines.append("- Age: no age (do not state the child's age)")
    else:
        lines.append(f"- Age: the child is {card['age_text']}")
    for f in card["facts"]:
        lines.append(f"- {f}")
    if "casual" in card["style"]:
        lines.append("- Style: casual")
    lines.append("- Number of SMS: two texts" if "two texts" in card["style"] else "- Number of SMS: one")
    lines.append("Write the SMS now. Output only the JSON.")
    return "\n".join(lines)
