"""B10: search INT8 settings that pass the prereg agreement rule on Y-dev (vs registered FP32), cheapest first.

Order (ml-edge notes 2026-10-03 section 3): per-channel; then keep the last encoder layer (and the heads) in FP32.
Usage: .venv/Scripts/python train/quant_search.py <fp32 dir> <out root>
"""
import json
import shutil
import sys
from pathlib import Path

import onnx
from onnxruntime.quantization import QuantType, quantize_dynamic

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.door import keyword_extractor  # noqa: E402
from app.encoder import Encoder  # noqa: E402
from app.engine import Protocol  # noqa: E402
from app.harness import SETS, load_set, run_arm  # noqa: E402


def matmul_nodes(model_path, layers):
    m = onnx.load(str(model_path), load_external_data=False)
    keep = []
    for n in m.graph.node:
        if n.op_type in ("MatMul", "Gemm") and (any(f"/layer.{i}/" in n.name for i in layers) or "head" in n.name.lower()):
            keep.append(n.name)
    return keep


def agreement(variant_dir, base_out, rows, params):
    out = run_arm(rows, params, (Encoder(variant_dir), keyword_extractor))
    dis = sum(r["triggered"] != base_out[r["id"]]["triggered"] for r in out)
    missed = sum(r["label"] == "danger" and base_out[r["id"]]["triggered"] and not r["triggered"] for r in out)
    return dis, missed


def size_mb(d):
    return round(sum(f.stat().st_size for f in Path(d).iterdir() if f.name.startswith("model")) / 2**20, 1)


def main():
    src, root = Path(sys.argv[1]), Path(sys.argv[2])
    params = Protocol.load(ROOT / "config" / "protocol.yaml", run_suite=False).params
    rows = load_set(SETS["ydev"])
    base = {r["id"]: r for r in run_arm(rows, params, (Encoder(src), keyword_extractor))}
    configs = [
        ("mm_pc", ["MatMul"], True, []),
        ("mm_pc_last1", ["MatMul"], True, [11]),
        ("mm_pc_last2", ["MatMul"], True, [10, 11]),
        ("mmg_pc", ["MatMul", "Gather"], True, []),
        ("mmg_pc_last1", ["MatMul", "Gather"], True, [11]),
    ]
    results = {}
    for name, ops, pc, layers in configs:
        d = root / f"{src.name}_{name}"
        d.mkdir(parents=True, exist_ok=True)
        excl = matmul_nodes(src / "model.onnx", layers) if layers else []
        quantize_dynamic(str(src / "model.onnx"), str(d / "model.onnx"), op_types_to_quantize=ops,
                         weight_type=QuantType.QInt8, per_channel=pc, nodes_to_exclude=excl)
        shutil.copy(src / "tokenizer.json", d / "tokenizer.json")
        dis, missed = agreement(d, base, rows, params)
        ok = dis <= 1 and missed == 0
        results[name] = {"dir": str(d), "model_mb": size_mb(d), "disagreements": dis, "of": len(rows),
                         "danger_missed_vs_fp32": missed, "excluded_nodes": len(excl), "passes": ok}
        print(f"{name:14} {results[name]['model_mb']:7} MB  disagree {dis}/{len(rows)}  danger missed {missed}  "
              f"{'PASS' if ok else 'fail'}", flush=True)
    out = ROOT / "data" / f"quant_search_{src.name}.json"
    out.write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
