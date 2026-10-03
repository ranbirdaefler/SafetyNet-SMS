"""B7: one training run, the pre-registered recipe (PREREGISTRATION.md section 7).

BCE, no class weights, learning rate 3e-5, bf16, 3 epochs, max length 256. Labels: the card's 8-bit PRESENT vector.
Fixed here (not in the prereg, chosen before the run): AdamW, linear decay with no warmup, batch 16, seed 42,
10% of deduped X held out for the X-val F1 log only.
"""
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn
from transformers import AutoTokenizer, get_linear_schedule_with_warmup

sys.path.insert(0, str(Path(__file__).parent))
from model import BASE, HEADS, MAX_LEN, THRESHOLD, SignModel  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "models" / "afroxlmr-8h"
DATA = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "x_train.dedup.jsonl"
SEED, BATCH, EPOCHS, LR = 42, 16, 3, 3e-5


def load(p):
    return [json.loads(l) for l in open(p, encoding="utf-8")]


def batches(rows, tok, shuffle, rng):
    idx = list(range(len(rows)))
    if shuffle:
        rng.shuffle(idx)
    for i in range(0, len(idx), BATCH):
        b = [rows[j] for j in idx[i:i + BATCH]]
        enc = tok([r["message"] for r in b], truncation=True, max_length=MAX_LEN, padding=True, return_tensors="pt")
        y = torch.tensor([r["present"] for r in b], dtype=torch.float32)
        yield enc["input_ids"], enc["attention_mask"], y


def f1s(model, rows, tok, dev):
    model.eval()
    P, Y = [], []
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
        for ids, am, y in batches(rows, tok, False, None):
            P.append(torch.sigmoid(model(ids.to(dev), am.to(dev)).float()).cpu())
            Y.append(y)
    P, Y = torch.cat(P).numpy() >= THRESHOLD, torch.cat(Y).numpy() >= 0.5
    out = {}
    for i, h in enumerate(HEADS):
        tp = int((P[:, i] & Y[:, i]).sum()); fp = int((P[:, i] & ~Y[:, i]).sum()); fn = int((~P[:, i] & Y[:, i]).sum())
        out[h] = {"f1": round(2 * tp / max(1, 2 * tp + fp + fn), 3), "tp": tp, "fp": fp, "fn": fn}
    model.train()
    return out


def main():
    random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
    rows = load(DATA)
    rng = random.Random(SEED)
    rng.shuffle(rows)
    n_val = len(rows) // 10
    val, train = rows[:n_val], rows[n_val:]
    dev = "cuda"
    tok = AutoTokenizer.from_pretrained(BASE)
    model = SignModel().to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=LR)
    steps = EPOCHS * ((len(train) + BATCH - 1) // BATCH)
    sched = get_linear_schedule_with_warmup(opt, 0, steps)
    loss_fn = nn.BCEWithLogitsLoss()
    t0, log = time.time(), []
    for ep in range(EPOCHS):
        tot = 0.0
        for ids, am, y in batches(train, tok, True, rng):
            with torch.autocast("cuda", dtype=torch.bfloat16):
                logits = model(ids.to(dev), am.to(dev))
            loss = loss_fn(logits.float(), y.to(dev))
            loss.backward()
            opt.step(); sched.step(); opt.zero_grad()
            tot += loss.item()
        f = f1s(model, val, tok, dev)
        log.append({"epoch": ep + 1, "train_loss": round(tot, 3), "xval": f})
        print(f"epoch {ep + 1}: loss {tot:.2f}; X-val F1 " + " ".join(f"{h}={v['f1']}" for h, v in f.items()), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), OUT / "model.pt")
    tok.save_pretrained(OUT / "tokenizer")
    meta = {"base": BASE, "heads": HEADS, "threshold": THRESHOLD, "max_len": MAX_LEN, "epochs": EPOCHS, "lr": LR,
            "batch": BATCH, "seed": SEED, "n_train": len(train), "n_xval": len(val), "minutes": round((time.time() - t0) / 60, 1),
            "log": log}
    meta["data"] = str(DATA.relative_to(ROOT))
    (ROOT / "data" / ("train_log.json" if OUT.name == "afroxlmr-8h" else f"train_log_{OUT.name}.json")).write_text(json.dumps(meta, indent=1))
    print(f"saved {OUT}; {meta['minutes']} min")


if __name__ == "__main__":
    main()
