"""Per-language rows (exploratory). The language of a message is its generation-time card language (the `lang` field
set by the seeded card sampler, gen/cards.py, committed in 3cec268), never a rule applied to the text.
- Y-dev and Y-test: the card's `lang` (Swahili / English / code-mixed).
- Set (b): Swahili by design (prereg section 3).
- Set (a): no language split. Its pre-registered grid (D01-D12, N01-N13) carries no language, and the label lines
  are not inspected for one.
Same scoring as app/metrics.py: danger caught and false go-now per arm, Clopper-Pearson 95%.
"""
import json
from pathlib import Path

from app.metrics import cp

ROOT = Path(__file__).resolve().parent.parent
CARDS = {"ydev": ROOT / "data" / "y_dev.jsonl", "ytest": ROOT / "tests" / "y_test.jsonl"}


def languages(set_name):
    if set_name == "b":
        return None                       # every row Swahili by design
    if set_name == "a":
        raise ValueError("set (a) has no language split (its grid carries no language)")
    return {c["id"]: c["lang"] for c in (json.loads(l) for l in open(CARDS[set_name], encoding="utf-8"))}


def by_language(set_name, results):
    """results: {id: harness row}. Returns {language: {danger_caught, of, cp95, false_go_now, of, cp95}}."""
    lang = languages(set_name)
    groups = {}
    for i, r in results.items():
        g = "Swahili" if lang is None else lang[i]
        groups.setdefault(g, []).append(r)
    out = {}
    for g, rs in sorted(groups.items()):
        d = [r for r in rs if r["label"] == "danger"]
        n = [r for r in rs if r["label"] == "no_danger"]
        cd, fn = sum(r["triggered"] for r in d), sum(r["triggered"] for r in n)
        out[g] = {"danger_caught": cd, "danger": len(d), "caught_cp95": cp(cd, len(d)),
                  "false_go_now": fn, "no_danger": len(n), "false_cp95": cp(fn, len(n))}
    return out


def run(out_dir, set_name, arm):
    res = {r["id"]: r for r in (json.loads(l) for l in open(Path(out_dir) / f"{set_name}.{arm}.jsonl", encoding="utf-8"))}
    return by_language(set_name, res)
