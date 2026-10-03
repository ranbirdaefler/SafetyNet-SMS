"""Post-freeze test runs (prereg section 4 step 5): every set sealed before the `freeze` push, three arms each:
keyword list E2 (comparator), ours = the registered model, and the deployed variant (its own labelled row).
Writes raw output files under results/test/ and prints a file count only. Never prints message text.
Usage (only after `freeze` is pushed): python train/run_tests.py <registered dir> <deployed dir> [v2 dir]
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import harness, lexicon  # noqa: E402
from app.door import keyword_extractor, list_extractor  # noqa: E402
from app.encoder import Encoder  # noqa: E402
from app.engine import Protocol  # noqa: E402


def main():
    tags = subprocess.run(["git", "tag", "--points-at", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    pushed = subprocess.run(["git", "ls-remote", "--tags", "origin", "freeze"], cwd=ROOT, capture_output=True, text=True).stdout
    if "freeze" not in tags or "refs/tags/freeze" not in pushed:
        sys.exit("refusing to run: HEAD is not the pushed `freeze` tag")
    params = Protocol.load(ROOT / "config" / "protocol.yaml", run_suite=False).params
    reg, dep = sys.argv[1], sys.argv[2]
    arms = {"keyword_E2": (list_extractor(lexicon.e2_list()),),
            "ours_registered": (Encoder(reg), keyword_extractor),
            "deployed": (Encoder(dep), keyword_extractor)}
    if len(sys.argv) > 3:                                  # v2: its own labelled row (not the registered model)
        arms["v2"] = (Encoder(sys.argv[3]), keyword_extractor)
    for s in ("a", "b", "ytest"):
        harness.run(s, params, arms, ROOT / "results" / "test")
    print(f"{len(list((ROOT / 'results' / 'test').glob('*.jsonl')))} raw files written")


if __name__ == "__main__":
    main()
