"""Mechanical check for the post-hoc parent-line fix (report-only on test sets): every message we have (Y-dev, sets
(a), (b), Y-test, y_test2) through the parent-line rules at two code versions. Every changed decision must be
"no go-now -> go-now"; any other change fails the fix.
Usage: python scripts/posthoc_rules_check.py dump <out.json> [<code dir>]   (code dir: an older checkout; data here)
       python scripts/posthoc_rules_check.py compare <old.json> <new.json>
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE = Path(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[1] == "dump" else ROOT
sys.path.insert(0, str(CODE))
GO = {"GO_NOW", "GO_NOW_NO_AGE"}


def dump(out):
    from app import lexicon
    from app.door import keyword_extractor, parent_policy
    from app.engine import Protocol
    from app.harness import load_set
    params = Protocol.load(CODE / "config" / "protocol.yaml", run_suite=False).params
    kw = lexicon.e2_list()
    lexicon.use(lexicon.live_list(kw) if hasattr(lexicon, "live_list") else kw)   # what the server runs live
    sets = {"ydev": ROOT / "data" / "y_dev.jsonl", "a": ROOT / "tests" / "caregiver_set_a.csv",
            "b": ROOT / "tests" / "caregiver_set_b.csv", "ytest": ROOT / "tests" / "y_test.jsonl",
            "y_test2": ROOT / "tests" / "y_test2.jsonl"}
    res = {}
    for s, path in sets.items():
        for r in load_set(path):
            pol = parent_policy(r["message"], params, (keyword_extractor,))
            res[f"{s}/{r['id']}"] = {"label": r["label"], "action": pol.action, "reasons": pol.reasons,
                                     "age": pol.age_months, "oos": pol.oos}
    Path(out).write_text(json.dumps(res))
    print(len(res), "messages, code from", CODE)


def compare(old_p, new_p):
    old, new = json.loads(Path(old_p).read_text()), json.loads(Path(new_p).read_text())
    assert old.keys() == new.keys()
    table, bad = {}, []
    for k in old:
        s = k.split("/")[0]
        o, n = old[k], new[k]
        t = table.setdefault(s, {"N": 0, "added_go_now_danger": 0, "added_go_now_no_danger": 0, "added_go_now_other": 0,
                                  "go_now_reasons_added": 0, "other_changes": 0})
        t["N"] += 1
        if o == n:
            continue
        if o["action"] not in GO and n["action"] in GO and o["age"] == n["age"]:
            t["added_go_now_" + ("danger" if o["label"] == "danger" else "no_danger" if o["label"] == "no_danger" else "other")] += 1
        elif o["action"] == n["action"] and o["age"] == n["age"] and o["oos"] == n["oos"] \
                and set(o["reasons"]) <= set(n["reasons"]):
            t["go_now_reasons_added"] += 1
        else:
            t["other_changes"] += 1
            bad.append((k, o, n))
    print(json.dumps(table, indent=1))
    print("FAIL" if bad else "PASS: every changed decision is no go-now -> go-now (or go-now with reasons added)")
    for b in bad:
        print(b)
    return table, bad


if __name__ == "__main__":
    if sys.argv[1] == "dump":
        dump(sys.argv[2])
    else:
        t, bad = compare(sys.argv[2], sys.argv[3])
        if len(sys.argv) > 4:
            Path(sys.argv[4]).write_text(json.dumps({"by_set": t, "other_changes": len(bad)}, indent=1))
