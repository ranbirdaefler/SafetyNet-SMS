"""Writes FREEZE.md for the `freeze` commit (prereg section 4 step 4). Never opens a test set: line counts are git's
insertion counts at each seal commit. Usage: python train/freeze_record.py <registered model dir> <deployed model dir>
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEALS = [("(a)", "tests/caregiver_set_a.csv"), ("(b)", "tests/caregiver_set_b.csv"), ("Y-test", "tests/y_test.jsonl")]


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def main():
    reg, dep = Path(sys.argv[1]), Path(sys.argv[2])
    lines = ["# Freeze record", "", "Written by `train/freeze_record.py` for the `freeze` commit. No test set was opened.", "",
             "## Sealed sets (commit, git insertion count at the seal commit)", "", "| Set | File | Commit | Lines |", "|---|---|---|---|"]
    for name, f in SEALS:
        c = git("log", "--diff-filter=A", "--format=%H", "--", f).splitlines()[-1]
        ins = git("show", "--numstat", "--format=", c, "--", f).split()[0]
        lines.append(f"| {name} | `{f}` | {c} | {ins} |")
    lines += ["| Native | none | none (no native set) | 0 |", ""]
    e2 = json.loads((ROOT / "config" / "e2.json").read_text(encoding="utf-8"))
    sweep = json.loads((ROOT / "data" / "sweep_ydev.json").read_text())
    gate = json.loads((ROOT / "data" / "gate_ydev.json").read_text())
    lines += ["## Keyword list", "", f"- E2 (comparator): T-list rows + mined n-grams, `config/e2.json`, k = {e2['k']} (search {e2['k_search']}).",
              "- Live keyword list: E2 (passed T1-T35 and CG1-CG18 with E2 loaded).", "",
              "## Models", "",
              f"- Registered model (prereg section 7): {sweep['registered'].upper()} ONNX, `{reg}`, git hash-object `{git('hash-object', str(reg / 'model.onnx'))}`.",
              f"- Deployed variant (deployment rule, Y-dev): `{dep}` ({sweep['variants'][dep.name]['label']}), "
              f"{sweep['variants'][dep.name]['model_mb']} MB + tokenizer {sweep['variants'][dep.name]['tokenizer_mb']} MB, "
              f"git hash-object `{git('hash-object', str(dep / 'model.onnx'))}`.",
              "- Base model: Davlan/afro-xlmr-base; generators: X train and Y-dev gpt-5.5; tests claude-opus-5-5.",
              "- Model weights stay out of git.", "",
              "## Board model (board only; never the parent reply)", "",
              "```", (ROOT / "config" / "board_model.json").read_text(), "```", "",
              "## Go-live gate on Y-dev (prereg section 9)", "", "```", json.dumps(gate["gate"], indent=1), "```", "",
              "## Live parent line", "",
              "- Encoder live on the parent line: no (CG1/CG5/CG5b/CG10/CG18 red with the encoder on, and the Y-dev gate "
              "fails on needless go-nows) -> rung 3: the keyword list (E2) runs the parent line live; the encoder is an eval row.", ""]
    (ROOT / "FREEZE.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
