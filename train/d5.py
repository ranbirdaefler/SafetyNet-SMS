"""D5 (diagnosis, exploratory, no training): "everyday human-written Swahili, not about sick children".
False alarms per source for the keyword list E2, v1 (registered FP32) and the shipped v2 (trimmed, 8-bit weights):
- triggered (parent-line rule: go now from a sign, a C4 word or under 2 months; raw p >= 0.5 per head);
- board flagged (shipped v2 only: "possible" or "unsure" at the board thresholds lo 0.068 / hi 0.9).
Sources (evaluation splits only): MASSIVE 1.1 sw-KE test (the same 1,000, seed 20261003; CC BY 4.0), FLORES-200
swh_Latn devtest (1,012; CC BY-SA 4.0), AfriSenti swa test (tweets; CC BY 4.0). Prints counts only.
"""
import csv
import json
import random
import sys
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import lexicon  # noqa: E402
from app.board_model import BoardModel  # noqa: E402
from app.door import keyword_extractor, list_extractor, parent_policy  # noqa: E402
from app.encoder import Encoder  # noqa: E402
from app.engine import Protocol  # noqa: E402
from app.harness import triggered  # noqa: E402
from app.metrics import cp  # noqa: E402

EXT = ROOT / "data" / "ext"


def sources():
    utts = pq.read_table(EXT / "massive_sw-KE_test.parquet").column("utt").to_pylist()
    idx = random.Random(20261003).sample(range(len(utts)), 1000)
    flores = [l.strip() for l in open(EXT / "flores200_dataset" / "devtest" / "swh_Latn.devtest", encoding="utf-8") if l.strip()]
    with open(EXT / "afrisenti_swa_test.tsv", encoding="utf-8") as fh:
        afri = [r["tweet"] for r in csv.DictReader(fh, delimiter="\t") if r.get("tweet")]
    return {"MASSIVE sw-KE test (same 1,000)": [utts[i] for i in idx], "FLORES-200 swh_Latn devtest": flores,
            "AfriSenti swa test (tweets)": afri}


def main():
    params = Protocol.load(ROOT / "config" / "protocol.yaml", run_suite=False).params
    lexicon.use(lexicon.e2_list())
    bm = BoardModel()
    arms = {"keyword list E2": (list_extractor(lexicon.LIVE),),
            "v1 FP32 (registered)": (Encoder(ROOT / "models" / "onnx" / "fp32"), keyword_extractor),
            "v2 shipped (trim, 8-bit)": (bm.enc, keyword_extractor)}
    out = {"label": "everyday human-written Swahili, not about sick children", "sources": {}}
    for name, texts in sources().items():
        r = {"N": len(texts)}
        for arm, ex in arms.items():
            k = sum(triggered(parent_policy(t, params, ex)) for t in texts)
            r[f"triggered: {arm}"] = {"n": k, "cp95": cp(k, len(texts))}
        bands = [bm.band(t)["band"] for t in texts]
        k = sum(b in ("possible", "unsure") for b in bands)
        r["board flagged: v2 shipped"] = {"n": k, "cp95": cp(k, len(texts)), "possible": bands.count("possible"),
                                          "unsure": bands.count("unsure")}
        out["sources"][name] = r
        print(name, {a: (v["n"] if isinstance(v, dict) else v) for a, v in r.items()}, flush=True)
    (ROOT / "results" / "d5_everyday_swahili.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
