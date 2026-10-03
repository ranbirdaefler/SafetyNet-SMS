"""Encoder benchmark on the box: cold load, p50/p95 per message at ~64 and ~200 tokens, peak RSS.
Usage: python scripts/bench.py models/onnx/<variant> [runs] [threads]   (default 50 runs, 4 threads, CPU)"""
import json
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.encoder import Encoder  # noqa: E402


def text_of(enc, n_tokens):
    base = "mtoto wangu wa miezi 18 ana homa na kikohozi tangu jana usiku na hataki kula vizuri "
    t = base
    while len(enc.tok.encode(t).ids) < n_tokens:
        t += base
    ids = enc.tok.encode(t).ids[1:n_tokens - 1]
    return enc.tok.decode(ids)


def main():
    d = Path(sys.argv[1])
    runs = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    threads = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    t0 = time.time()
    enc = Encoder(d, threads=threads)
    load_s = time.time() - t0
    out = {"variant": d.name, "threads": threads, "load_s": round(load_s, 2),
           "model_mb": round((d / "model.onnx").stat().st_size / 2**20, 1)}
    for n in (64, 200):
        txt = text_of(enc, n)
        enc.probs(txt)
        ts = []
        for _ in range(runs):
            a = time.perf_counter()
            enc.probs(txt)
            ts.append((time.perf_counter() - a) * 1000)
        ts.sort()
        out[f"p50_ms_{n}"] = round(ts[len(ts) // 2], 1)
        out[f"p95_ms_{n}"] = round(ts[int(len(ts) * 0.95) - 1], 1)
    out["peak_rss_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 0)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
