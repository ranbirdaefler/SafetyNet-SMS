"""B6: dedupe X train (exact match after lowercasing and whitespace folding; also drops any X message equal to a
Y-dev message) and log PRESENT counts per head (X4). Test sets are never read here."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "gen"))
from cards import HEADS  # noqa: E402


def norm(t):
    return re.sub(r"\s+", " ", t.lower()).strip()


def load(p):
    return [json.loads(l) for l in open(p, encoding="utf-8")]


def main():
    x, dev = load(ROOT / "data" / "x_train.jsonl"), load(ROOT / "data" / "y_dev.jsonl")
    dev_texts = {norm(r["message"]) for r in dev}
    seen, kept, dup_x, dup_dev = set(), [], 0, 0
    for r in x:
        n = norm(r["message"])
        if n in dev_texts:
            dup_dev += 1
            continue
        if n in seen:
            dup_x += 1
            continue
        seen.add(n)
        kept.append(r)
    with open(ROOT / "data" / "x_train.dedup.jsonl", "w", encoding="utf-8") as fh:
        for r in kept:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    counts = {h: sum(r["present"][i] for r in kept) for i, h in enumerate(HEADS)}
    dev_counts = {h: sum(r["present"][i] for r in dev) for i, h in enumerate(HEADS)}
    report = {"x_in": len(x), "x_kept": len(kept), "dropped_dup_in_x": dup_x, "dropped_equal_to_ydev": dup_dev,
              "x_present_per_head": counts, "x_min_per_head": min(counts.values()),
              "ydev_present_per_head": dev_counts, "x_categories": dict(Counter(r["category"] for r in kept))}
    (ROOT / "data" / "x_train.dedup.report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))
    assert report["x_min_per_head"] >= 40, "a head has fewer than 40 PRESENT examples"


if __name__ == "__main__":
    main()
