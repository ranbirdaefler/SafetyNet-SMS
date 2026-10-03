"""B10: the prereg INT8 agreement rule on Y-dev, applied to every size variant against FP32.

A variant passes if, on Y-dev, it agrees with FP32 on at least 99% of go-now decisions (with 120 messages: at most
1 disagreement) and misses no danger message that FP32 catches. Go-now = the parent policy's triggered decision,
with the encoder as extractor (the keyword list only reads if the encoder raises, D26).
Run with the training venv: .venv/Scripts/python train/agree.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.door import keyword_extractor  # noqa: E402
from app.encoder import Encoder  # noqa: E402
from app.engine import Protocol  # noqa: E402
from app.harness import load_set, run_arm, SETS  # noqa: E402

VARIANTS = ["fp32", "int8", "int8_emb", "trim_fp32", "trim_int8", "trim_int8_emb"]


def main():
    params = Protocol.load(ROOT / "config" / "protocol.yaml", run_suite=False).params
    rows = load_set(SETS["ydev"])
    sizes = json.loads((ROOT / "data" / "model_sizes.json").read_text())
    res = {}
    for v in VARIANTS:
        d = ROOT / "models" / "onnx" / v
        if not (d / "model.onnx").exists():
            continue
        res[v] = run_arm(rows, params, (Encoder(d), keyword_extractor))
    base = {r["id"]: r for r in res["fp32"]}
    report = {}
    for v, out in res.items():
        dis = [r["id"] for r in out if r["triggered"] != base[r["id"]]["triggered"]]
        missed = [r["id"] for r in out if r["label"] == "danger" and base[r["id"]]["triggered"] and not r["triggered"]]
        ok = len(dis) <= len(out) // 100 and not missed       # >= 99% agreement; 120 messages -> at most 1
        report[v] = {"model_mb": sizes.get(v, {}).get("model_mb"), "tokenizer_mb": sizes.get(v, {}).get("tokenizer_mb"),
                     "disagreements": len(dis), "of": len(out), "danger_missed_vs_fp32": len(missed), "passes": ok,
                     "disagreement_ids": dis}
    passing = [v for v in report if report[v]["passes"]]
    deployed = min(passing, key=lambda v: report[v]["model_mb"] + report[v]["tokenizer_mb"])
    registered = "int8" if report.get("int8", {}).get("passes") else "fp32"
    out = {"variants": report, "deployed": deployed, "registered_choice": registered}
    (ROOT / "data" / "model_agreement.json").write_text(json.dumps(out, indent=1))
    for v, r in report.items():
        print(f"{v:14} {r['model_mb']:7} MB + tok {r['tokenizer_mb']} MB  disagree {r['disagreements']}/{r['of']}  "
              f"danger missed {r['danger_missed_vs_fp32']}  {'PASS' if r['passes'] else 'fail'}")
    print(f"registered (prereg section 7): {registered}; deployed (smallest passing): {deployed}")


if __name__ == "__main__":
    main()
