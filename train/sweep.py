"""B10 quantization sweep on Y-dev (never on a test set), all variants from the same fine-tuned model.

Per variant: model + tokenizer size, danger sensitivity, false go-now rate, % go-now agreement with FP32, danger
messages FP32 catches that the variant misses. Deployment rule (extends prereg section 7): deploy the smallest
variant with >= 99% go-now agreement with FP32 on Y-dev and no danger message missed that FP32 catches.
Registered model (prereg section 7): the registered INT8 (MatMul only) if it passes that rule, else FP32.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.door import keyword_extractor  # noqa: E402
from app.encoder import Encoder  # noqa: E402
from app.engine import Protocol  # noqa: E402
from app.harness import SETS, load_set, run_arm  # noqa: E402

VARIANTS = [
    ("fp32", "FP32 (registered default)"),
    ("int8", "INT8 dynamic, MatMul only (registered INT8)"),
    ("search/fp32_mm_pc", "INT8 dynamic, MatMul only, per-channel"),
    ("int8_emb", "INT8 dynamic incl. embeddings (Gather)"),
    ("wq8", "INT8 weight-only (per-channel), FP32 compute"),
    ("trim10k_fp32", "Vocab trim (9,759 tokens), FP32"),
    ("trim10k_int8", "Vocab trim + INT8 dynamic, MatMul only"),
    ("trim10k_int8_emb", "Vocab trim + INT8 dynamic incl. embeddings"),
    ("trim10k_wq8", "Vocab trim + INT8 weight-only (per-channel)"),
]


def mb(d, prefix):
    return round(sum(f.stat().st_size for f in d.iterdir() if f.name.startswith(prefix)) / 2**20, 1)


def main():
    params = Protocol.load(ROOT / "config" / "protocol.yaml", run_suite=False).params
    rows = load_set(SETS["ydev"])
    kw = run_arm(rows, params, (keyword_extractor,))
    res = {}
    for v, label in VARIANTS:
        d = ROOT / "models" / "onnx" / v
        res[v] = (label, d, run_arm(rows, params, (Encoder(d), keyword_extractor)))
    base = {r["id"]: r for r in res["fp32"][2]}
    n_d = sum(r["label"] == "danger" for r in rows)
    n_n = sum(r["label"] == "no_danger" for r in rows)
    table = {}
    for v, (label, d, out) in res.items():
        agree = sum(r["triggered"] == base[r["id"]]["triggered"] for r in out)
        missed = sum(r["label"] == "danger" and base[r["id"]]["triggered"] and not r["triggered"] for r in out)
        table[v] = {"label": label, "model_mb": mb(d, "model"), "tokenizer_mb": mb(d, "tokenizer"),
                    "sensitivity": f"{sum(r['triggered'] for r in out if r['label'] == 'danger')}/{n_d}",
                    "false_go_now": f"{sum(r['triggered'] for r in out if r['label'] == 'no_danger')}/{n_n}",
                    "agreement_with_fp32": f"{agree}/{len(out)}", "agreement_pct": round(100 * agree / len(out), 1),
                    "danger_missed_vs_fp32": missed,
                    "passes_rule": agree >= 0.99 * len(out) and missed == 0}
    table["keyword_list_v0"] = {"label": "Keyword list v0 (no model), for reference",
                                "sensitivity": f"{sum(r['triggered'] for r in kw if r['label'] == 'danger')}/{n_d}",
                                "false_go_now": f"{sum(r['triggered'] for r in kw if r['label'] == 'no_danger')}/{n_n}"}
    passing = [v for v in res if table[v]["passes_rule"]]
    deployed = min(passing, key=lambda v: table[v]["model_mb"] + table[v]["tokenizer_mb"])
    registered = "int8" if table["int8"]["passes_rule"] else "fp32"
    out = {"set": "Y-dev (gpt-5.5, 120)", "variants": table, "registered": registered, "deployed": deployed,
           "int4": "not built: MatMulNBits export failed on the first try (onnxruntime 1.23.2 quantizer API)"}
    (ROOT / "data" / "sweep_ydev.json").write_text(json.dumps(out, indent=1))
    for v, t in table.items():
        print(v, json.dumps({k: t[k] for k in t if k != "label"}))
    print("registered:", registered, "| deployed:", deployed)


if __name__ == "__main__":
    main()
