"""v3 step 2 (no evaluation split is read here): export v3, re-trim its vocabulary from the TRAIN splits, store weights
as 8-bit, fit per-head temperatures on v3's X-val, choose board thresholds by the rule in v3/CRITERIA.md for v3 and for
re-tuned v2 on the THRESHOLD splits, and check the shipped v3 variant against full-size v3.
Writes config/board_model_v3.json, config/board_model_v2_retuned.json and v3/prepare_report.json.
"""
import csv
import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "train"))
from app import lexicon  # noqa: E402
from app.door import keyword_extractor  # noqa: E402
from app.encoder import HEADS, Encoder  # noqa: E402
from app.engine import Protocol  # noqa: E402
from app.harness import SETS, load_set, run_arm  # noqa: E402
from export import export  # noqa: E402
from model import SignModel  # noqa: E402

ONNX = ROOT / "models" / "onnx"
EXT = ROOT / "data" / "ext"


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def sig(z):
    return 1 / (1 + np.exp(-z))


def bce(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())


def threshold_splits():
    ms = pq.read_table(EXT / "massive_sw-KE_validation.parquet").column("utt").to_pylist()
    fl = [l.strip() for l in open(EXT / "flores200_dataset" / "dev" / "swh_Latn.dev", encoding="utf-8") if l.strip()]
    with open(EXT / "afrisenti_swa_dev.tsv", encoding="utf-8") as fh:
        af = [r["tweet"] for r in csv.DictReader(fh, delimiter="\t") if r.get("tweet")]
    return {"MASSIVE sw-KE dev": ms, "FLORES-200 dev": fl, "AfriSenti swa dev": af}


def fit_temps(enc, data):
    rows = [json.loads(l) for l in open(data, encoding="utf-8")]
    random.Random(42).shuffle(rows)
    xval = rows[:len(rows) // 10]
    P = np.array([enc.probs(r["message"]) for r in xval])
    Y = np.array([r["present"] for r in xval], dtype=float)
    grid = np.round(np.arange(0.25, 5.01, 0.05), 2)
    return {h: float(grid[int(np.argmin([bce(sig(logit(P[:, i]) / t), Y[:, i]) for t in grid]))]) for i, h in enumerate(HEADS)}, len(xval)


def scorer(enc, temps):
    T = np.array([temps[h] for h in HEADS])
    cache = {}

    def score(text):
        if text not in cache:
            cache[text] = float(sig(logit(enc.probs(text)) / T).max())
        return cache[text]
    return score


def choose(score, dev, everyday):
    """The CRITERIA.md rule. lo: lowest Y-dev danger score. hi: smallest value with <= 2/45 Y-dev no-danger and <= 5% of each
    everyday threshold source at or above it. Flag cap 35% per everyday source at lo; lo is never raised to meet it."""
    d = [score(r["message"]) for r in dev if r["label"] == "danger"]
    n = [score(r["message"]) for r in dev if r["label"] == "no_danger"]
    ev = {k: [score(t) for t in v] for k, v in everyday.items()}
    lo = min(d)
    cands = sorted({v for v in n + [x for vs in ev.values() for x in vs] if v >= lo} | {1.0})
    hi = 1.0
    for c in cands:
        if sum(v >= c for v in n) <= 2 and all(sum(v >= c for v in vs) / len(vs) <= 0.05 for vs in ev.values()):
            hi = c
            break
    flags = {k: round(100 * sum(v >= lo for v in vs) / len(vs), 1) for k, vs in ev.items()}
    return {"lo": lo, "hi": hi, "ydev_danger_below_lo": 0, "ydev_no_danger_possible": sum(v >= hi for v in n),
            "everyday_flagged_pct_at_lo": flags, "flag_cap_35_met": all(f <= 35 for f in flags.values()),
            "everyday_possible_pct": {k: round(100 * sum(v >= hi for v in vs) / len(vs), 1) for k, vs in ev.items()}}


def main():
    rep = {}
    # 1. export full-size v3, re-trim from TRAIN splits, 8-bit weights
    m = SignModel()
    m.load_state_dict(torch.load(ROOT / "models" / "afroxlmr-8h-v3" / "model.pt", map_location="cpu"))
    m.eval()
    export(m, ONNX / "v3_fp32" / "model.onnx")
    shutil.copy(ROOT / "models" / "afroxlmr-8h-v3" / "tokenizer" / "tokenizer.json", ONNX / "v3_fp32" / "tokenizer.json")
    env = {"SNS_SRC": str(ROOT / "models" / "afroxlmr-8h-v3"), "SNS_XDATA": "x_train_v3.jsonl"}
    py = sys.executable
    subprocess.run([py, str(ROOT / "train" / "trim_vocab.py"), "60000", str(ONNX / "v3_trim_fp32")], check=True,
                   env={**__import__("os").environ, **env}, capture_output=True)
    subprocess.run([py, str(ROOT / "train" / "wq.py"), str(ONNX / "v3_trim_fp32"), str(ONNX / "v3_trim_wq8")], check=True,
                   capture_output=True)
    rep["v3_trim_report"] = json.loads((ONNX / "v3_trim_fp32" / "trim_report.json").read_text())
    rep["v3_trim_wq8_mb"] = round((ONNX / "v3_trim_wq8" / "model.onnx").stat().st_size / 2**20, 1)
    full, ship = Encoder(ONNX / "v3_fp32"), Encoder(ONNX / "v3_trim_wq8")
    # 2. temperatures on v3 X-val (shipped variant)
    temps_v3, n_xval = fit_temps(ship, ROOT / "data" / "x_train_v3.jsonl")
    rep["v3_temperatures"] = temps_v3
    rep["v3_xval_n"] = n_xval
    # 3. thresholds by the pre-written rule, on the THRESHOLD splits only
    dev = load_set(SETS["ydev"])
    everyday = threshold_splits()
    rep["threshold_split_sizes"] = {k: len(v) for k, v in everyday.items()}
    s_v3 = scorer(ship, temps_v3)
    rep["v3_thresholds"] = choose(s_v3, dev, everyday)
    v2cfg = json.loads((ROOT / "config" / "board_model.json").read_text())
    v2enc = Encoder(ROOT / v2cfg["model_dir"])
    rep["v2_retuned_thresholds"] = choose(scorer(v2enc, v2cfg["temperatures"]), dev, everyday)
    # 4. shipped v3 variant vs full-size v3: go-now on Y-dev, board flags on each threshold split
    params = Protocol.load(ROOT / "config" / "protocol.yaml", run_suite=False).params
    lexicon.use(lexicon.e2_list())
    a = {r["id"]: r for r in run_arm(dev, params, (full, keyword_extractor))}
    b = run_arm(dev, params, (ship, keyword_extractor))
    agree = sum(r["triggered"] == a[r["id"]]["triggered"] for r in b)
    missed = sum(r["label"] == "danger" and a[r["id"]]["triggered"] and not r["triggered"] for r in b)
    s_full = scorer(full, temps_v3)
    lo, hi = rep["v3_thresholds"]["lo"], rep["v3_thresholds"]["hi"]

    def band(s, t):
        v = s(t)
        return "possible" if v >= hi else "unsure" if v >= lo else None
    flag_agree = {k: round(100 * sum((band(s_v3, t) is None) == (band(s_full, t) is None) for t in v) / len(v), 1)
                  for k, v in {**everyday, "Y-dev": [r["message"] for r in dev]}.items()}
    rep["v3_variant_agreement"] = {"ydev_go_now": f"{agree}/{len(b)}", "ydev_danger_missed_vs_full": missed,
                                   "board_flag_agreement_pct": flag_agree,
                                   "passes": agree >= 0.99 * len(b) and missed == 0 and all(v >= 99 for v in flag_agree.values())}
    for name, model_dir, temps, th in (("v3", "models/onnx/v3_trim_wq8", temps_v3, rep["v3_thresholds"]),
                                       ("v2_retuned", v2cfg["model_dir"], v2cfg["temperatures"], rep["v2_retuned_thresholds"])):
        h = subprocess.run(["git", "hash-object", str(ROOT / model_dir / "model.onnx")], capture_output=True, text=True).stdout.strip()
        (ROOT / "config" / f"board_model_{name}.json").write_text(json.dumps(
            {"model_dir": model_dir, "model_hash": h, "temperatures": temps, "lo": th["lo"], "hi": th["hi"],
             "rule": "v3/CRITERIA.md", "thresholds_on": "Y-dev + MASSIVE sw-KE dev + FLORES-200 dev + AfriSenti swa dev"}, indent=1))
    (ROOT / "v3" / "prepare_report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
