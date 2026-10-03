"""Exploratory row, after `freeze` only: "Exploratory, thresholds set on Y-dev (GPT-written); the test sets are
Claude-written, so the Y-dev guarantee does not formally transfer."

For each sealed set: review load (% of messages in "please read") and the danger messages that got neither "possible"
nor "unsure", n/N with Clopper-Pearson 95%. Writes raw band files under results/board/ and prints counts only.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.board_model import BoardModel  # noqa: E402
from app.harness import SETS, load_set  # noqa: E402
from app.metrics import cp  # noqa: E402

LABEL = ("Exploratory, thresholds set on Y-dev (GPT-written); the test sets are Claude-written, so the Y-dev "
         "guarantee does not formally transfer.")


def main():
    pushed = subprocess.run(["git", "ls-remote", "--tags", "origin", "freeze"], cwd=ROOT, capture_output=True, text=True).stdout
    if "refs/tags/freeze" not in pushed:
        sys.exit("refusing to run: `freeze` is not pushed")
    bm = BoardModel()
    out = {"label": LABEL, "lo": bm.lo, "hi": bm.hi, "sets": {}}
    raw = ROOT / "results" / "board"
    raw.mkdir(parents=True, exist_ok=True)
    for s in ("a", "b", "ytest"):
        rows = load_set(SETS[s])
        bands = {r["id"]: bm.band(r["message"])["band"] for r in rows}
        (raw / f"{s}.json").write_text(json.dumps({r["id"]: {"label": r["label"], "band": bands[r["id"]]} for r in rows}))
        danger = [r["id"] for r in rows if r["label"] == "danger"]
        unsure = sum(b == "unsure" for b in bands.values())
        none_d = sum(bands[i] is None for i in danger)
        out["sets"][s] = {"N": len(rows), "please_read": unsure, "please_read_pct": round(100 * unsure / len(rows), 1),
                          "please_read_cp95": cp(unsure, len(rows)), "danger": len(danger),
                          "danger_with_no_band": none_d, "danger_with_no_band_cp95": cp(none_d, len(danger))}
        print(f"{s}: {len(rows)} messages scored")
    (ROOT / "results" / "board_row.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
