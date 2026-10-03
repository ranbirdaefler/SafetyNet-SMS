"""Post-fine-tuning vocabulary trim (Ushio et al. 2023 method, custom keep-list), then FP32 ONNX export.

Keep-list, in order: special tokens; every single-character Latin, digit, punctuation or symbol piece; every token produced on X train (deduped), the
keyword lists (T-list, shared stage, C4, cues, condition A, E2) and the fixed outgoing strings; then the most frequent
tokens on a generic corpus (MASSIVE 1.1 train split, sw-KE and en-US, CC BY 4.0) up to the target size.
Y-dev and every test set are never used here. Drift check: <unk> rate and tokens per message on MASSIVE sw-KE
validation (held out from the keep-list).
Usage: .venv/Scripts/python train/trim_vocab.py <target size> <out dir>
"""
import json
import sys
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq
import torch
from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "train"))
from app import lexicon, messages as M, textparse  # noqa: E402
from export import export, keep_piece  # noqa: E402
from model import SignModel  # noqa: E402

SRC = ROOT / "models" / "afroxlmr-8h"


def fixed_texts():
    out = []
    for v in vars(M).values():
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, (list, dict)):
            out += [x for x in (v.values() if isinstance(v, dict) else v) if isinstance(x, str)]
    rows = [lexicon.T_LIST, lexicon.SHARED, lexicon.C4]
    for r in rows:
        for terms in r.values():
            out += terms
    out += list(lexicon.CUES) + lexicon.NEVER_NEGATED
    e2 = json.loads((ROOT / "config" / "e2.json").read_text(encoding="utf-8"))
    for terms in e2["rows"].values():
        out += terms
    for s in (textparse.UNITS_EN, textparse.UNITS_SW, textparse.SYMPTOM):
        out += list(s)
    out += list(textparse.NEWBORN | textparse.PREGNANCY | textparse.ADULT | textparse.AGE_MARK | textparse.DUR_MARK)
    return out


def main():
    target, out_dir = int(sys.argv[1]), Path(sys.argv[2])
    tok_path = SRC / "tokenizer" / "tokenizer.json"
    tok = Tokenizer.from_file(str(tok_path))
    cfg = json.loads(tok_path.read_text(encoding="utf-8"))
    vocab = cfg["model"]["vocab"]
    V = len(vocab)
    keep = {0, 1, 2, 3, V - 1}
    keep |= {i for i, (p, _) in enumerate(vocab) if len(p.replace("▁", "")) <= 1 and keep_piece(p)}
    n_single = len(keep)
    x = [json.loads(l)["message"] for l in open(ROOT / "data" / "x_train.dedup.jsonl", encoding="utf-8")]
    for t in x + fixed_texts():
        keep |= set(tok.encode(t).ids)
        keep |= set(tok.encode(t.lower()).ids)
    n_task = len(keep)
    freq = Counter()
    for loc in ("sw-KE", "en-US"):
        for u in pq.read_table(ROOT / "data" / "ext" / f"massive_{loc}_train.parquet").column("utt").to_pylist():
            freq.update(tok.encode(u).ids)
    for i, _ in freq.most_common():
        if len(keep) >= target:
            break
        keep.add(i)
    keep = sorted(keep)
    # tokenizer rewrite: same order, specials keep their ids
    remap = {old: new for new, old in enumerate(keep)}
    cfg["model"]["vocab"] = [vocab[i] for i in keep]
    for t in cfg.get("added_tokens", []):
        t["id"] = remap[t["id"]]
    for spec in ((cfg.get("post_processor") or {}).get("special_tokens") or {}).values():
        spec["ids"] = [remap[i] for i in spec["ids"]]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "tokenizer.json").write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    # model: slice the embedding rows, export FP32
    model = SignModel()
    model.load_state_dict(torch.load(SRC / "model.pt", map_location="cpu"))
    model.eval()
    emb = model.encoder.embeddings.word_embeddings
    new = torch.nn.Embedding(len(keep), emb.weight.shape[1], padding_idx=emb.padding_idx)
    new.weight.data = emb.weight.data[torch.tensor(keep)].clone()
    model.encoder.embeddings.word_embeddings = new
    model.encoder.config.vocab_size = len(keep)
    export(model, out_dir / "model.onnx")
    # drift check on held-out generic Swahili (MASSIVE sw-KE validation) and on X train
    small = Tokenizer.from_file(str(out_dir / "tokenizer.json"))
    val = pq.read_table(ROOT / "data" / "ext" / "massive_sw-KE_validation.parquet").column("utt").to_pylist()
    report = {"target": target, "kept": len(keep), "single_char_and_specials": n_single, "after_task_text": n_task}
    for name, texts in (("massive_sw_val", val), ("x_train", x)):
        full_len = sum(len(tok.encode(t).ids) for t in texts)
        small_ids = [small.encode(t).ids for t in texts]
        report[name] = {"n": len(texts), "unk": sum(ids.count(3) for ids in small_ids),
                        "tokens_per_msg_full": round(full_len / len(texts), 2),
                        "tokens_per_msg_trim": round(sum(map(len, small_ids)) / len(texts), 2),
                        "identical_segmentation": sum(
                            [tok.id_to_token(i) for i in tok.encode(t).ids] == [small.id_to_token(i) for i in s]
                            for t, s in zip(texts, small_ids))}
    (out_dir / "trim_report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
