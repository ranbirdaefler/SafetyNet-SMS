"""Board-only model (v2 deployed variant, calibrated). It reads parent text only, never decides what the parent is
told, sends no SMS and changes no case status: it adds a band to the case record for the health worker's board.

Bands, from the calibrated max danger-head probability p (temperatures fit on X-val; lo/hi set on Y-dev):
- p >= hi: "possible" with the head's sign label; lo <= p < hi: "unsure"; p < lo: none.
A model exception gives no band (the case still shows).
"""
import json
import time
from collections import deque
from pathlib import Path

import numpy as np

from app.encoder import HEADS, Encoder

ROOT = Path(__file__).resolve().parent.parent
LABEL = {"convulsions": "convulsions", "not_drink_feed": "cannot drink or feed", "vomits_everything": "vomits everything",
         "sleepy_unconscious": "very sleepy or cannot wake", "blood_stool": "blood in stool", "cough_long": "long illness",
         "diarrhoea_long": "long illness", "fever_long": "long illness"}


class BoardModel:
    def __init__(self, cfg_path=ROOT / "config" / "board_model.json", encoder=None):
        self.cfg = json.loads(Path(cfg_path).read_text())
        self.enc = encoder or Encoder(ROOT / self.cfg["model_dir"])
        self.T = np.array([self.cfg["temperatures"][h] for h in HEADS])
        self.lo, self.hi = self.cfg["lo"], self.cfg["hi"]

    def band(self, text):
        p = np.clip(self.enc.probs(text), 1e-6, 1 - 1e-6)
        cal = 1 / (1 + np.exp(-np.log(p / (1 - p)) / self.T))
        i = int(cal.argmax())
        v = float(cal[i])
        heads = {h: round(float(cal[k]), 4) for k, h in enumerate(HEADS)}   # per-sign scores (question suggestions)
        if v >= self.hi:
            return {"band": "possible", "sign": LABEL[HEADS[i]], "p": round(v, 4), "heads": heads}
        if v >= self.lo:
            return {"band": "unsure", "sign": None, "p": round(v, 4), "heads": heads}
        return {"band": None, "sign": None, "p": round(v, 4), "heads": heads}


LOG = deque(maxlen=50)   # live inset: time, case code, CHP phone (shown as CHP id only), model ms, band; no parent data


def annotate(store, model, parent_phone, text):
    """Store the band on the parent's current case. Never raises: a failure leaves no model line."""
    case = None
    try:
        case = store.latest_case_for_parent(parent_phone)
        if case is None or model is None:
            return
        st = case["state"]
        t0 = time.perf_counter()
        b = model.band(text)
        LOG.append({"time": time.strftime("%H:%M:%S"), "code": case["code"], "chp_phone": case["chp_phone"],
                    "model_ms": round((time.perf_counter() - t0) * 1000), "band": b["band"] or "none"})
        old = st.get("model")
        order = {"possible": 2, "unsure": 1, None: 0}
        if old is None or order[b["band"]] >= order[old.get("band")]:   # a later text never lowers the band
            st["model"] = b
            store.update_case(case["code"], state=st)
    except Exception:
        LOG.append({"time": time.strftime("%H:%M:%S"), "code": case["code"] if case else "-", "chp_phone": None,
                    "model_ms": None, "band": "model error (no line)"})
        return
