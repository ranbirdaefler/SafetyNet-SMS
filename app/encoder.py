"""Encoder extractor (parent text only): AfroXLMR ONNX, 8 yes/no heads, PRESENT at p >= 0.5 (prereg section 7).

Below 0.5 means OPEN, never absent. Over 256 tokens: the first and last 256 tokens are read and PRESENT in either
counts. Needs onnxruntime + tokenizers only (runs on the Pi, CPU, 4 threads).
"""
from pathlib import Path

import numpy as np

HEADS = ["convulsions", "not_drink_feed", "vomits_everything", "sleepy_unconscious",
         "blood_stool", "cough_long", "diarrhoea_long", "fever_long"]
THRESHOLD = 0.5
MAX_LEN = 256


class Encoder:
    def __init__(self, model_dir, threads=4):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        d = Path(model_dir)
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = threads
        self.sess = ort.InferenceSession(str(d / "model.onnx"), opts, providers=["CPUExecutionProvider"])
        self.tok = Tokenizer.from_file(str(d / "tokenizer.json"))
        self.tok.no_truncation()
        self.tok.no_padding()

    def windows(self, text):
        ids = self.tok.encode(text).ids          # includes <s> ... </s>
        if len(ids) <= MAX_LEN:
            return [ids]
        body = ids[1:-1]
        n = MAX_LEN - 2
        return [[ids[0]] + body[:n] + [ids[-1]], [ids[0]] + body[-n:] + [ids[-1]]]

    def probs(self, text):
        p = None
        for ids in self.windows(text):
            a = np.array([ids], dtype=np.int64)
            out = self.sess.run(None, {"input_ids": a, "attention_mask": np.ones_like(a)})[0][0]
            p = out if p is None else np.maximum(p, out)
        return p

    def __call__(self, text):
        """Extractor interface: {sign: "PRESENT"} for each head at p >= 0.5."""
        p = self.probs(text)
        return {h: "PRESENT" for h, v in zip(HEADS, p) if v >= THRESHOLD}
