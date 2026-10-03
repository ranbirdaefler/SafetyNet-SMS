"""E2 keyword list by the fixed recipe (PREREGISTRATION.md section 5). Mined from deduped X train only.

1. Tokens lowercased, split on spaces and punctuation except apostrophes; clause breaks as in the matching rule,
   including the join between the two parts of a two-text message.
2. Candidates for sign s: 1- to 3-grams within one clause, no digits, from messages whose label has s present.
3. pos = messages labelled s with a non-negated occurrence (no cue within 3 tokens before it in the same clause);
   tot = all messages with a non-negated occurrence.
4. Keep if pos >= 5 and pos/tot >= 0.90. Drop any n-gram that is or contains a cue. Rank by precision, then pos,
   then fewer tokens, then alphabetical. Top 20 per sign (R3, R5, R6, R7, R9 only).
5. R8, R10, R11 get T-list terms only; the C4 words stay in the C4 list only.
k for E2 is set later on Y-dev (B13).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import lexicon  # noqa: E402

SIGNS = ["convulsions", "not_drink_feed", "vomits_everything", "sleepy_unconscious", "blood_stool"]
HEAD_INDEX = {"convulsions": 0, "not_drink_feed": 1, "vomits_everything": 2, "sleepy_unconscious": 3, "blood_stool": 4}


def ngrams_nonneg(text):
    """Set of non-negated 1-3-grams (no digits) in the message."""
    found = set()
    for toks in lexicon.clauses(text):
        for n in (1, 2, 3):
            for i in range(len(toks) - n + 1):
                g = toks[i:i + n]
                if any(ch.isdigit() for t in g for ch in t) or g == ["?"]:
                    continue
                if any(t in lexicon.CUES for t in toks[max(0, i - 3):i]):
                    continue
                found.add(" ".join(g))
    return found


def main():
    rows = [json.loads(l) for l in open(ROOT / "data" / "x_train.dedup.jsonl", encoding="utf-8")]
    occ = [ngrams_nonneg(r["message"]) for r in rows]
    tot = {}
    for s in occ:
        for g in s:
            tot[g] = tot.get(g, 0) + 1
    mined = {}
    for sign in SIGNS:
        idx = HEAD_INDEX[sign]
        pos = {}
        for r, s in zip(rows, occ):
            if r["present"][idx]:
                for g in s:
                    pos[g] = pos.get(g, 0) + 1
        keep = []
        for g, p in pos.items():
            if p >= 5 and p / tot[g] >= 0.90 and not any(t in lexicon.CUES for t in g.split()):
                keep.append((-(p / tot[g]), -p, len(g.split()), g))
        keep.sort()
        mined[sign] = [{"ngram": g, "pos": -p, "tot": tot[g], "precision": round(-pr, 3)} for pr, p, _, g in keep[:20]]
    rows_e2 = {s: list(lexicon.T_LIST[s]) for s in SIGNS}
    for s in SIGNS:
        rows_e2[s] += [m["ngram"] for m in mined[s] if m["ngram"] not in rows_e2[s]]
    out = {"recipe": "PREREGISTRATION.md section 5", "source": "data/x_train.dedup.jsonl", "n_messages": len(rows),
           "mined": mined, "rows": rows_e2, "k": None}
    (ROOT / "config" / "e2.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    for s in SIGNS:
        print(s, [m["ngram"] for m in mined[s]])


if __name__ == "__main__":
    main()
