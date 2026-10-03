"""v2 data: deduped X train + augmentation, after removing every augmentation message that exactly or nearly matches
a CG1-CG18 probe, a must-stay-RED text probe or a Y-dev message (near = same normalised text, or token-set Jaccard
>= 0.8). Test sets are never read. Writes data/x_train_v2.jsonl and a report with the removal counts."""
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import cg_tests  # noqa: E402


def norm_tokens(t):
    return re.findall(r"[a-z]+|\d+", t.lower())


def probe_strings():
    out = {t for t, _ in cg_tests.cg1_inputs()} | set(cg_tests.CG5_TEXTS)
    for f in ("app/cg_tests.py", "app/must_stay_red.py"):
        for node in ast.walk(ast.parse((ROOT / f).read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and " " in node.value and len(node.value) < 200:
                out.add(node.value)
    return out


def main():
    x = [json.loads(l) for l in open(ROOT / "data" / "x_train.dedup.jsonl", encoding="utf-8")]
    aug = [json.loads(l) for l in open(ROOT / "data" / "x_aug.jsonl", encoding="utf-8")]
    probes = [(p, set(norm_tokens(p)), " ".join(norm_tokens(p))) for p in probe_strings()]
    dev = [(r["message"], set(norm_tokens(r["message"])), " ".join(norm_tokens(r["message"])))
           for r in (json.loads(l) for l in open(ROOT / "data" / "y_dev.jsonl", encoding="utf-8"))]
    removed = {"cg_or_t_probe": 0, "ydev": 0, "dup_in_aug_or_x": 0}
    seen = {" ".join(norm_tokens(r["message"])) for r in x}
    kept = []
    for r in aug:
        toks = set(norm_tokens(r["message"]))
        n = " ".join(norm_tokens(r["message"]))

        def near(ref):
            return n == ref[2] or (toks and len(toks & ref[1]) / len(toks | ref[1]) >= 0.8)
        if any(near(p) for p in probes):
            removed["cg_or_t_probe"] += 1
        elif any(near(d) for d in dev):
            removed["ydev"] += 1
        elif n in seen:
            removed["dup_in_aug_or_x"] += 1
        else:
            seen.add(n)
            kept.append(r)
    with open(ROOT / "data" / "x_train_v2.jsonl", "w", encoding="utf-8") as fh:
        for r in x + kept:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    rep = {"x_dedup": len(x), "aug_generated": len(aug), "aug_kept": len(kept), "removed": removed,
           "probe_strings_checked": len(probes), "v2_total": len(x) + len(kept)}
    (ROOT / "data" / "x_train_v2.report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
