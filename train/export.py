"""B10: FP32 ONNX export (registered default) and smaller variants measured for the brief's model-size rule.

Variants (each a folder under models/onnx/ with model.onnx + tokenizer.json):
- fp32           registered default
- int8           registered INT8: dynamic quantization of MatMul only
- int8_emb       MatMul + Gather (embeddings) quantized
- trim_fp32      vocabulary trimmed to Latin-script and emoji pieces (identical tokenisation on such text)
- trim_int8      trimmed + MatMul INT8
- trim_int8_emb  trimmed + MatMul + Gather INT8
"""
import json
import sys
import unicodedata
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).parent))
from model import BASE, HEADS, ProbModel, SignModel  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "models" / "afroxlmr-8h"
OUT = ROOT / "models" / "onnx"


def export(model, path, opset=17):
    path.parent.mkdir(parents=True, exist_ok=True)
    ids = torch.ones(1, 16, dtype=torch.long)
    torch.onnx.export(ProbModel(model).eval(), (ids, torch.ones_like(ids)), str(path), dynamo=False,
                      input_names=["input_ids", "attention_mask"], output_names=["probs"], opset_version=opset,
                      dynamic_axes={"input_ids": {0: "b", 1: "s"}, "attention_mask": {0: "b", 1: "s"}, "probs": {0: "b"}})


def quantize(src, dst, ops):
    from onnxruntime.quantization import QuantType, quantize_dynamic
    dst.parent.mkdir(parents=True, exist_ok=True)
    quantize_dynamic(str(src), str(dst), op_types_to_quantize=ops, weight_type=QuantType.QInt8)


def keep_piece(piece):
    """Latin-script, digits, punctuation, symbols (emoji) and the SentencePiece space mark."""
    for ch in piece.replace("▁", ""):
        if ch.isascii():
            continue
        cat = unicodedata.category(ch)
        if cat[0] in "PSNZ":
            continue
        try:
            if "LATIN" in unicodedata.name(ch):
                continue
        except ValueError:
            return False
        return False
    return True


def trimmed_tokenizer(tok_json):
    """Return (new tokenizer json, kept old ids). Special tokens keep ids 0-3."""
    cfg = json.loads(tok_json.read_text(encoding="utf-8"))
    vocab = cfg["model"]["vocab"]
    keep = [i for i, (p, _) in enumerate(vocab) if i < 4 or i == len(vocab) - 1 or keep_piece(p)]
    cfg["model"]["vocab"] = [vocab[i] for i in keep]
    remap = {old: new for new, old in enumerate(keep)}
    for t in cfg.get("added_tokens", []):
        t["id"] = remap[t["id"]]
    pp = cfg.get("post_processor") or {}
    for spec in (pp.get("special_tokens") or {}).values():
        spec["ids"] = [remap[i] for i in spec["ids"]]
    return cfg, keep


def main():
    model = SignModel()
    model.load_state_dict(torch.load(SRC / "model.pt", map_location="cpu"))
    model.eval()
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(SRC / "tokenizer")
    tok_json = SRC / "tokenizer" / "tokenizer.json"

    fp32 = OUT / "fp32" / "model.onnx"
    export(model, fp32)
    (OUT / "fp32" / "tokenizer.json").write_bytes(tok_json.read_bytes())
    for name, ops in (("int8", ["MatMul"]), ("int8_emb", ["MatMul", "Gather"])):
        quantize(fp32, OUT / name / "model.onnx", ops)
        (OUT / name / "tokenizer.json").write_bytes(tok_json.read_bytes())

    cfg, keep = trimmed_tokenizer(tok_json)
    emb = model.encoder.embeddings.word_embeddings
    new = torch.nn.Embedding(len(keep), emb.weight.shape[1], padding_idx=emb.padding_idx)
    new.weight.data = emb.weight.data[torch.tensor(keep)].clone()
    model.encoder.embeddings.word_embeddings = new
    model.encoder.config.vocab_size = len(keep)
    tfp = OUT / "trim_fp32" / "model.onnx"
    export(model, tfp)
    (OUT / "trim_fp32" / "tokenizer.json").write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    for name, ops in (("trim_int8", ["MatMul"]), ("trim_int8_emb", ["MatMul", "Gather"])):
        quantize(tfp, OUT / name / "model.onnx", ops)
        (OUT / name / "tokenizer.json").write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")

    sizes = {}
    for d in sorted(OUT.iterdir()):
        files = [f for f in d.iterdir() if f.is_file()]
        sizes[d.name] = {"model_mb": round(sum(f.stat().st_size for f in files if f.name.startswith("model")) / 2**20, 1),
                         "tokenizer_mb": round((d / "tokenizer.json").stat().st_size / 2**20, 1)}
    sizes["_vocab"] = {"full": len(json.loads(tok_json.read_text(encoding='utf-8'))["model"]["vocab"]), "trimmed": len(keep)}
    (ROOT / "data" / "model_sizes.json").write_text(json.dumps(sizes, indent=1))
    print(json.dumps(sizes, indent=1))


if __name__ == "__main__":
    main()
