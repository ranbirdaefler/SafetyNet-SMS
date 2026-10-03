"""Board model (v2, deployed variant): per-head temperature scaling fit on X-val (the 10% held out in train.py, same
seed and shuffle), never on Y-dev or a test set. Then the three-band thresholds on Y-dev:
- lo = the largest value at which no Y-dev danger message falls below lo (= the lowest danger score);
  with 60 danger messages this bounds the miss rate at roughly 1/61 on data like Y-dev;
- hi = the smallest value with no Y-dev no-danger message above it (= the highest no-danger score).
Score = the calibrated max danger-head probability. Writes config/board_model.json and data/board_calibration.json.
Usage: .venv/Scripts/python train/calibrate.py models/onnx/v2_trim_wq8 data/x_train_v2.jsonl
"""
import json
import math
import random
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.encoder import HEADS, Encoder  # noqa: E402
from app.harness import SETS, load_set  # noqa: E402


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def sig(z):
    return 1 / (1 + np.exp(-z))


def bce(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())


def ece(p, y, bins=10):
    e, n = 0.0, len(p)
    for b in range(bins):
        m = (p >= b / bins) & (p < (b + 1) / bins if b < bins - 1 else p <= 1)
        if m.any():
            e += m.sum() / n * abs(p[m].mean() - y[m].mean())
    return round(float(e), 4)


def main():
    model_dir, data = Path(sys.argv[1]), Path(sys.argv[2])
    rows = [json.loads(l) for l in open(data, encoding="utf-8")]
    rng = random.Random(42)
    rng.shuffle(rows)
    xval = rows[:len(rows) // 10]
    enc = Encoder(model_dir)
    P = np.array([enc.probs(r["message"]) for r in xval])
    Y = np.array([r["present"] for r in xval], dtype=float)
    Z = logit(P)
    temps, report = {}, {}
    grid = np.round(np.arange(0.25, 5.01, 0.05), 2)
    for i, h in enumerate(HEADS):
        losses = [bce(sig(Z[:, i] / t), Y[:, i]) for t in grid]
        t = float(grid[int(np.argmin(losses))])
        temps[h] = t
        report[h] = {"T": t, "positives": int(Y[:, i].sum()), "ece_before": ece(P[:, i], Y[:, i]),
                     "ece_after": ece(sig(Z[:, i] / t), Y[:, i]), "bce_before": round(bce(P[:, i], Y[:, i]), 4),
                     "bce_after": round(min(losses), 4)}
    T = np.array([temps[h] for h in HEADS])

    def score(text):
        return float(sig(logit(enc.probs(text)) / T).max())

    dev = load_set(SETS["ydev"])
    s = {r["id"]: score(r["message"]) for r in dev}
    d = sorted(s[r["id"]] for r in dev if r["label"] == "danger")
    n = sorted(s[r["id"]] for r in dev if r["label"] == "no_danger")
    lo = d[0]
    hi = n[-1] + 1e-6
    sweep = []
    for lo_c in sorted({round(x, 3) for x in [0.01, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, lo]}):
        for hi_c in sorted({round(x, 3) for x in [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, min(hi, 0.999)]}):
            if hi_c <= lo_c:
                continue
            band = [lo_c <= v < hi_c for v in s.values()]
            sweep.append({"lo": lo_c, "hi": hi_c, "please_read_pct": round(100 * sum(band) / len(band), 1),
                          "danger_below_lo": sum(v < lo_c for v in d),
                          "no_danger_possible": sum(v >= hi_c for v in n)})
    h = subprocess.run(["git", "hash-object", str(model_dir / "model.onnx")], capture_output=True, text=True).stdout.strip()
    cfg = {"model_dir": str(model_dir.relative_to(ROOT) if model_dir.is_absolute() else model_dir).replace("\\", "/"),
           "model_hash": h, "temperatures": temps, "lo": round(lo, 6), "hi": round(hi, 6),
           "fit_on": f"X-val ({len(xval)} messages, held out from {data.name} with seed 42)",
           "thresholds_on": "Y-dev (gpt-5.5, 120)",
           "note": f"lo = lowest Y-dev danger score; with {len(d)} danger messages this bounds the miss rate at roughly "
                   f"1/{len(d) + 1} on data like Y-dev. hi = highest Y-dev no-danger score."}
    (ROOT / "config" / "board_model.json").write_text(json.dumps(cfg, indent=1))
    review = sum(lo <= v < hi for v in s.values())
    out = {"calibration_xval": report, "lo": lo, "hi": hi, "ydev_review_load_pct": round(100 * review / len(s), 1),
           "ydev_danger_below_lo": 0, "ydev_no_danger_possible": sum(v >= hi for v in n), "sweep": sweep}
    (ROOT / "data" / "board_calibration.json").write_text(json.dumps(out, indent=1))
    for h_, r in report.items():
        print(h_, r)
    print(f"lo={lo:.4f} hi={hi:.4f} review load on Y-dev {out['ydev_review_load_pct']}%")


if __name__ == "__main__":
    main()
