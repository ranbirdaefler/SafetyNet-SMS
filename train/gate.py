"""B13 go-live gate on Y-dev (prereg section 9), run on the Pi.

Encoder misses <= keyword-list (E2) misses, encoder needless go-nows <= E2's, shared path complete, p95 within
budget. If it fails, the keyword list runs the parent line and the encoder is reported as a table row only.
Also writes the Y-dev table rows (dev, not a test set). Usage: python train/gate.py <registered model dir> [deployed dir]
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import lexicon  # noqa: E402
from app.door import keyword_extractor, list_extractor  # noqa: E402
from app.encoder import Encoder  # noqa: E402
from app.engine import Protocol  # noqa: E402
from app.harness import SETS, load_set, run_arm  # noqa: E402

P95_BUDGET_MS = 300


def summary(out):
    d = [r for r in out if r["label"] == "danger"]
    n = [r for r in out if r["label"] == "no_danger"]
    s = [r for r in out if r["label"] == "shared" and r["kind"] in ("u2m", "breathing")]
    a = [r for r in out if r["label"] == "shared" and r["kind"] == "no_age"]
    return {"missed": sum(not r["triggered"] for r in d), "of_danger": len(d),
            "needless": sum(r["triggered"] for r in n), "of_no_danger": len(n),
            "shared_path": f"{sum(r['triggered'] for r in s)}/{len(s)}",
            "age_not_received_only": sum(r["age_not_received_only"] for r in out),
            "no_age_cards_age_not_received": f"{sum(r['age_not_received_only'] for r in a)}/{len(a)}",
            "c4_on_danger": sum(r["c4"] for r in d)}


def main():
    params = Protocol.load(ROOT / "config" / "protocol.yaml", run_suite=False).params
    rows = load_set(SETS["ydev"])
    e2 = lexicon.e2_list()
    v0 = {"name": "v0", "rows": lexicon.T_LIST, "k": lexicon.V0_K}
    arms = {"keyword_E2": (list_extractor(e2),), "keyword_v0": (list_extractor(v0),)}
    dirs = sys.argv[1:]
    for d in dirs:
        enc = Encoder(d)
        lat = []
        for r in rows:
            t0 = time.perf_counter()
            enc.probs(r["message"])
            lat.append((time.perf_counter() - t0) * 1000)
        lat.sort()
        arms[f"encoder:{Path(d).name}"] = (enc, keyword_extractor)
        arms[f"encoder:{Path(d).name}"] += ()
        globals().setdefault("P95", {})[Path(d).name] = round(lat[int(len(lat) * 0.95) - 1], 1)
    table = {name: summary(run_arm(rows, params, ex)) for name, ex in arms.items()}
    reg = f"encoder:{Path(dirs[0]).name}"
    t, k = table[reg], table["keyword_E2"]
    gate = {"encoder_misses_le_keyword": t["missed"] <= k["missed"],
            "encoder_needless_le_keyword": t["needless"] <= k["needless"],
            "shared_path_complete": t["shared_path"].split("/")[0] == t["shared_path"].split("/")[1],
            "p95_ms_per_message": globals()["P95"][Path(dirs[0]).name], "p95_budget_ms": P95_BUDGET_MS}
    gate["p95_in_budget"] = gate["p95_ms_per_message"] <= P95_BUDGET_MS
    gate["passes"] = all(v for kk, v in gate.items() if isinstance(v, bool))
    out = {"set": "Y-dev (dev, not a test set)", "e2_k": e2["k"], "table": table, "gate": gate,
           "p95_ms_by_model": globals()["P95"], "host": __import__("platform").node()}
    (ROOT / "data" / "gate_ydev.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
