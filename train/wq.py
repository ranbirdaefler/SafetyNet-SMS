"""Weight-only 8-bit storage: MatMul weights and the embedding table are stored as INT8 with one scale per output
channel (per row for the embeddings) and dequantized to FP32 by DequantizeLinear; activations stay FP32.
Disk size is close to INT8; the arithmetic is FP32, so only the weight rounding error remains.
Usage: .venv/Scripts/python train/wq.py <fp32 dir> <out dir>
"""
import shutil
import sys
from pathlib import Path

import numpy as np
import onnx
from onnx import helper, numpy_helper


def main():
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    m = onnx.load(str(src / "model.onnx"))
    g = m.graph
    inits = {i.name: i for i in g.initializer}
    targets = {}                                   # initializer name -> quantization axis
    for n in g.node:
        if n.op_type == "MatMul" and n.input[1] in inits and len(inits[n.input[1]].dims) == 2:
            targets[n.input[1]] = 1                # [in, out]: one scale per output column
        if n.op_type == "Gather" and n.input[0] in inits and len(inits[n.input[0]].dims) == 2:
            targets[n.input[0]] = 0                # [vocab, hidden]: one scale per row
    new_nodes = []
    for name, axis in targets.items():
        w = numpy_helper.to_array(inits[name]).astype(np.float32)
        amax = np.abs(w).max(axis=1 - axis)
        scale = np.where(amax > 0, amax / 127.0, 1.0).astype(np.float32)
        q = np.clip(np.round(w / (scale[None, :] if axis == 1 else scale[:, None])), -127, 127).astype(np.int8)
        g.initializer.remove(inits[name])
        g.initializer.extend([numpy_helper.from_array(q, name + "_q"), numpy_helper.from_array(scale, name + "_s"),
                              numpy_helper.from_array(np.zeros_like(scale, dtype=np.int8), name + "_z")])
        new_nodes.append(helper.make_node("DequantizeLinear", [name + "_q", name + "_s", name + "_z"], [name],
                                          axis=axis, name=name + "_dq"))
    for i, n in enumerate(new_nodes):
        g.node.insert(i, n)
    dst.mkdir(parents=True, exist_ok=True)
    onnx.save(m, str(dst / "model.onnx"))
    shutil.copy(src / "tokenizer.json", dst / "tokenizer.json")
    print(f"{len(targets)} weights stored as INT8; {round((dst / 'model.onnx').stat().st_size / 2**20, 1)} MB")


if __name__ == "__main__":
    main()
