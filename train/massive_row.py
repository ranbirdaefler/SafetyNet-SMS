"""Exploratory, not pre-registered: human-written Swahili (translated virtual-assistant commands, no health content);
tests false alarms only, not danger detection.

MASSIVE 1.1 (AmazonScience/massive, CC BY 4.0), sw-KE test split; 1,000 utterances sampled with a fixed seed, all
treated as no-danger. Metric: TRIGGERED (go-now caused by a sign, a C4 word or under 2 months), not raw go-now:
no MASSIVE text has a child's age, so "age not received" would make raw go-now 100% for every arm. n/N with
Clopper-Pearson 95% per arm. Never used for training, k or tuning. Runs after `freeze`; prints counts only.
Usage: python train/massive_row.py <registered model dir> [deployed model dir]
"""
import json
import random
import sys
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import lexicon  # noqa: E402
from app.door import keyword_extractor, list_extractor, parent_policy  # noqa: E402
from app.encoder import Encoder  # noqa: E402
from app.engine import Protocol  # noqa: E402
from app.harness import triggered  # noqa: E402
from app.metrics import cp  # noqa: E402

SEED, N = 20261003, 1000
SRC = ROOT / "data" / "ext" / "massive_sw-KE_test.parquet"


def main():
    utts = pq.read_table(SRC).column("utt").to_pylist()
    sample = random.Random(SEED).sample(range(len(utts)), N)
    params = Protocol.load(ROOT / "config" / "protocol.yaml", run_suite=False).params
    arms = {"keyword_E2": (list_extractor(lexicon.e2_list()),)}
    for d in sys.argv[1:]:
        arms[f"encoder:{Path(d).name}"] = (Encoder(d), keyword_extractor)
    out = {"label": "Exploratory, not pre-registered: human-written Swahili (translated virtual-assistant commands, "
                    "no health content); tests false alarms only, not danger detection.",
           "source": "MASSIVE 1.1 sw-KE test split, CC BY 4.0", "seed": SEED, "N": N, "pool": len(utts), "arms": {}}
    raw = ROOT / "results" / "massive"
    raw.mkdir(parents=True, exist_ok=True)
    for name, ex in arms.items():
        flags = [triggered(parent_policy(utts[i], params, ex)) for i in sample]
        k = sum(flags)
        out["arms"][name] = {"triggered": k, "N": N, "cp95_pct": cp(k, N)}
        (raw / f"{name.replace(':', '_')}.json").write_text(json.dumps({"sample_index": sample, "triggered": flags}))
    (ROOT / "results" / "massive_row.json").write_text(json.dumps(out, indent=1))
    for name, a in out["arms"].items():
        print(f"{name}: {a['triggered']}/{N} triggered")


if __name__ == "__main__":
    main()
