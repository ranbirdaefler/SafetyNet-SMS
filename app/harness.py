"""Single-pass evaluation harness (F5): calls the service's parent_policy(), never a copy.

Each message is read once, first reply scored, dialogue not replayed (X1); every message is scored as from a
registered sender whose health worker is idle (X6). Runs write raw output files and print a count only: the
harness never prints message text. Labels come from the grid ID (sets a, b) or the card (Y), never the text.

Format line (prereg section 3): set (a) and (b) are CSV with columns id,label_line,message; " || " separates the two
texts of a two-text row. Y sets are JSONL cards with "id", "category" (danger / no_danger / shared) and "message".
"""
import csv
import json
from pathlib import Path

from app.door import keyword_extractor, parent_policy

ROOT = Path(__file__).resolve().parent.parent
SETS = {
    "ydev": ROOT / "data" / "y_dev.jsonl",
    "ytest": ROOT / "tests" / "y_test.jsonl",
    "a": ROOT / "tests" / "caregiver_set_a.csv",
    "b": ROOT / "tests" / "caregiver_set_b.csv",
}


def load_set(path):
    path = Path(path)
    rows = []
    if path.suffix == ".csv":
        with open(path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                gid = r["id"].strip()
                label = "danger" if gid.upper().startswith("D") else "no_danger" if gid.upper().startswith("N") else None
                if label is None:
                    raise ValueError("row id is not a D/N grid id")
                rows.append({"id": gid, "label": label, "message": r["message"]})
    else:
        for line in open(path, encoding="utf-8"):
            c = json.loads(line)
            rows.append({"id": c["id"], "label": c["category"], "kind": c.get("kind"), "message": c["message"]})
    return rows


def triggered(pol):
    """Go now with a sign, a C4 word or under 2 months among its reasons ('age not received' alone is not)."""
    return any(r not in ("age not received", "no CHP assigned", "CHP busy") for r in pol.reasons)


def run_arm(rows, params, extractors):
    out = []
    for r in rows:
        pol = parent_policy(r["message"], params, extractors)
        out.append({"id": r["id"], "label": r["label"], "kind": r.get("kind"), "action": pol.action,
                    "reasons": pol.reasons, "triggered": triggered(pol),
                    "age_not_received_only": pol.action == "GO_NOW_NO_AGE",
                    "c4": bool(pol.c4)})
    return out


def run(set_name, params, arms, out_dir):
    """arms: {name: extractors}. Writes <out_dir>/<set>.<arm>.jsonl; prints counts only."""
    rows = load_set(SETS[set_name])
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for arm, ex in arms.items():
        res = run_arm(rows, params, ex)
        with open(out_dir / f"{set_name}.{arm}.jsonl", "w", encoding="utf-8") as fh:
            for x in res:
                fh.write(json.dumps(x) + "\n")
        print(f"{set_name}.{arm}: {len(res)} rows written")
