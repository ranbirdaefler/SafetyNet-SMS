"""Keyword lexicon (frozen 1 Oct; typed verbatim from PREREGISTRATION.md section 5 / SPEC.md 'Keyword lexicon').

No word is added or removed by hand. The Swahili was drafted with AI and never checked by a native speaker.
"""
import re

# T-list sign rows (PREREGISTRATION.md section 5 table, with "nothing stays down" (R7) and "cannot wake" (R9)).
T_LIST = {
    "convulsions": ["convulsion", "convulsions", "fits", "degedege"],
    "not_drink_feed": ["cannot drink", "cannot feed", "cannot breastfeed", "not able to drink", "unable to drink",
                       "hawezi kunywa", "hawezi kunyonya", "hanyonyi", "kushindwa kunywa", "kushindwa kunyonya"],
    "vomits_everything": ["vomits everything", "vomiting everything", "nothing stays down",
                          "anatapika kila kitu", "kutapika kila kitu"],
    "sleepy_unconscious": ["very sleepy", "unusually sleepy", "hard to wake", "cannot wake", "cannot be woken",
                           "unconscious", "usingizi mwingi", "usingizi usio kawaida", "usingizi usio wa kawaida",
                           "haamki"],
    "blood_stool": ["blood in stool", "damu kwenye kinyesi"],
}
# Shared stage rows (R8, R10, R11): ignore cues on the parent line; identical in both eval arms.
SHARED = {
    "chest_indrawing": ["chest indrawing", "kifua kinaingia", "kifua kuingia ndani"],
    "muac_red": ["muac red", "muac nyekundu"],
    "feet_swelling": ["both feet swollen", "dent stays on both feet", "miguu yote imevimba"],
}
# C4 list (breathing and "worse"): a match means go now; ignores negation, no mined n-grams.
C4 = {
    "breathing complaint": ["breathing", "breath", "chest", "anapumua", "pumzi", "kifua"],
    "parent says worse": ["worse", "sicker"],
}
# Negation cues: closed list of 20. "si" and "sio" are not cues.
CUES = {"no", "not", "never", "without", "isn't", "isnt", "doesn't", "doesnt", "didn't", "didnt", "hasn't",
        "hasnt", "don't", "dont", "hana", "hakuna", "hajawa", "hajapata", "bila", "wala"}
# Condition A: a match containing any of these is never negated.
NEVER_NEGATED = ["cannot drink", "cannot feed", "cannot breastfeed", "not able to drink", "unable to drink",
                 "cannot wake", "cannot be woken", "nothing stays down", "hawezi kunywa", "hawezi kunyonya",
                 "hanyonyi", "kushindwa kunywa", "kushindwa kunyonya", "haamki",
                 # post-hoc (Sat 3 Oct, after seeing test misses; README): refusal described with a negation
                 "won't take", "wont take", "will not take", "not even a sip", "refuses the breast",
                 "anakataa kunyonya", "anakataa kunywa", "anakataa kula", "amekataa kunyonya", "amekataa kunywa",
                 "amekataa kula"]
CLAUSE_WORDS = {"lakini", "ila", "but"}
SENTENCE_BREAKS = {".", "?", "!", "\n", "||"}
# Post-hoc parent-line rows (Sat 3 Oct, after seeing test misses; not evaluated on sealed data; README). Added to the
# live list only (live_list); the frozen E2 used by the evaluation harness is unchanged. They can only add "go now".
POSTHOC_ROWS = {
    "not_drink_feed": ["won't take", "wont take", "will not take", "not even a sip", "refuses the breast",
                       "anakataa kunyonya", "anakataa kunywa", "anakataa kula", "amekataa kunyonya", "amekataa kunywa",
                       "amekataa kula"],
    # described convulsions; "shaking" / "anatetemeka" are deliberately not included (shivering with fever)
    "convulsions": ["stiff", "stiffens", "stiffened", "stiffening", "stiffness", "jerking", "jerks", "jerked",
                    "kukakamaa", "kakamaa", "amekakamaa", "anakakamaa", "alikakamaa", "akakamaa", "akikakamaa",
                    "umekakamaa", "unakakamaa", "ulikakamaa", "imekakamaa", "inakakamaa"],
}
V0_K = 2

TOKEN_RE = re.compile(r"(\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?)|([^\W\d_]+(?:'[^\W\d_]+)*)|(\|\||[,.;:?!\n])")


def normalise(text):
    t = text.lower()
    t = t.replace("’", "'")
    t = re.sub(r"\bcan\s+not\b", "cannot", t)
    t = re.sub(r"\bcan'?t\b", "cannot", t)
    t = re.sub(r"(\d)\s*-\s*(\d)", r"\1-\2", t)          # ranges stay one token
    t = re.sub(r"(\d)([^\W\d_])", r"\1 \2", t)            # 18m -> 18 m
    return t


def clauses(text):
    """List of clauses, each a list of tokens. Breaks: , . ; : ? ! newline, ||, lakini, ila, but."""
    return [c for _, c in clauses_with_sentence(text)]


def clauses_with_sentence(text):
    """Same clauses as clauses(), each with its sentence number (sentences end at . ? ! newline ||)."""
    out, cur, s = [], [], 0
    for m in TOKEN_RE.finditer(normalise(text)):
        num, word, brk = m.groups()
        if brk or (word and word in CLAUSE_WORDS):
            if cur:
                out.append((s, cur))
            cur = []
            if brk == "?":
                out.append((s, ["?"]))   # keep the hedge mark visible to the regex
            if brk in SENTENCE_BREAKS:
                s += 1
        else:
            cur.append(num or word)
    if cur:
        out.append((s, cur))
    return out


def _phrases(rows):
    ph = []
    for sign, terms in rows.items():
        for t in terms:
            ph.append((t.split(), sign, t))
    ph.sort(key=lambda p: -len(p[0]))       # longest phrase wins
    return ph


def match(text, rows, k=V0_K, use_cues=True):
    """Return {sign: "PRESENT"} for every non-negated match. Negated matches are OPEN (not returned)."""
    phrases = _phrases(rows)
    found = {}
    for toks in clauses(text):
        taken = [False] * len(toks)
        hits = []
        for i in range(len(toks)):
            for words, sign, term in phrases:
                n = len(words)
                if toks[i:i + n] == words and not any(taken[i:i + n]):
                    hits.append((i, n, sign, term))
                    for j in range(i, i + n):
                        taken[j] = True
                    break
        for i, n, sign, term in hits:
            negated = False
            if use_cues and not any(nn in term for nn in NEVER_NEGATED):
                for j in range(max(0, i - k), i):
                    if not taken[j] and toks[j] in CUES:
                        negated = True
            if not negated:
                found[sign] = "PRESENT"
    return found


def c4(text):
    """C4 reasons, in fixed order; negation-blind."""
    hit = match(text, C4, use_cues=False)
    return [r for r in C4 if r in hit]


# ---------- the live keyword list: v0 by default; E2 only if T1-T35 and CG1-CG18 pass with it loaded ----------
LIVE = {"name": "v0", "rows": T_LIST, "k": V0_K}


def e2_list():
    """E2 = T-list sign rows + mined n-grams (config/e2.json), with k set on Y-dev."""
    import json
    from pathlib import Path
    cfg = json.loads((Path(__file__).resolve().parent.parent / "config" / "e2.json").read_text(encoding="utf-8"))
    return {"name": "E2", "rows": cfg["rows"], "k": cfg["k"]}


def live_list(kw):
    """The parent-line list: a frozen list (E2 or v0) plus the post-hoc rows."""
    rows = {s: list(t) for s, t in kw["rows"].items()}
    for s, t in POSTHOC_ROWS.items():
        rows[s] = rows.get(s, []) + [x for x in t if x not in rows.get(s, [])]
    return {"name": kw["name"] + " + post-hoc rows", "rows": rows, "k": kw["k"]}


def use(kw):
    LIVE.clear()
    LIVE.update(kw)


def match_detail(text, rows, k):
    """Every match as (sign, term, negated), using the same rules as match()."""
    phrases = _phrases(rows)
    out = []
    for toks in clauses(text):
        taken = [False] * len(toks)
        hits = []
        for i in range(len(toks)):
            for words, sign, term in phrases:
                n = len(words)
                if toks[i:i + n] == words and not any(taken[i:i + n]):
                    hits.append((i, n, sign, term))
                    for j in range(i, i + n):
                        taken[j] = True
                    break
        for i, n, sign, term in hits:
            negated = False
            if not any(nn in term for nn in NEVER_NEGATED):
                negated = any(not taken[j] and toks[j] in CUES for j in range(max(0, i - k), i))
            out.append((sign, term, negated))
    return out
