"""P2, Y-dev only, nothing adopted: the parent go-now = E2 OR model, where the model may only ADD a go-now.
Candidates: E2 alone; E2 OR v1-deployed (raw p >= 0.5); E2 OR v2-deployed (raw p >= 0.5); E2 OR v2-deployed
(calibrated p >= 0.9, the board's hi). Per candidate: danger caught /60, extra catches vs E2, false go-now /45 and the
change in points vs E2, and T1-T35 + CG1-CG18 pass/fail with that OR loaded."""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import cg_tests, lexicon, must_stay_red  # noqa: E402
from app.door import keyword_extractor, list_extractor  # noqa: E402
from app.encoder import HEADS, Encoder  # noqa: E402
from app.engine import Protocol  # noqa: E402
from app.harness import SETS, load_set, run_arm  # noqa: E402


def or_extractor(e2, enc, temps=None, thr=0.5):
    def f(text):
        found = dict(e2(text))
        p = np.clip(enc.probs(text), 1e-6, 1 - 1e-6)
        if temps is not None:
            p = 1 / (1 + np.exp(-np.log(p / (1 - p)) / temps))
        for h, v in zip(HEADS, p):
            if v >= thr:
                found[h] = "PRESENT"
        return found
    return f


def main():
    proto = Protocol.load(ROOT / "config" / "protocol.yaml", run_suite=False)
    lexicon.use(lexicon.e2_list())
    e2 = list_extractor(lexicon.LIVE)
    bm = json.loads((ROOT / "config" / "board_model.json").read_text())
    temps = np.array([bm["temperatures"][h] for h in HEADS])
    v1 = Encoder(ROOT / "models" / "onnx" / "trim10k_wq8")
    v2 = Encoder(ROOT / "models" / "onnx" / "v2_trim_wq8")
    cands = {"E2 alone": e2,
             "E2 OR v1-deployed (raw p>=0.5)": or_extractor(e2, v1),
             "E2 OR v2-deployed (raw p>=0.5)": or_extractor(e2, v2),
             "E2 OR v2-deployed (calibrated p>=0.9)": or_extractor(e2, v2, temps, 0.9)}
    rows = load_set(SETS["ydev"])
    res, base = {}, None
    for name, ex in cands.items():
        out = run_arm(rows, proto.params, (ex, keyword_extractor))
        d = {r["id"]: r for r in out}
        caught = sum(r["triggered"] for r in out if r["label"] == "danger")
        false = sum(r["triggered"] for r in out if r["label"] == "no_danger")
        if base is None:
            base = d
        extra = sum(r["label"] == "danger" and r["triggered"] and not base[r["id"]]["triggered"] for r in out)
        t_failed = must_stay_red.run(proto)
        cg_failed = cg_tests.run(proto, variants=[(name, (ex, keyword_extractor))])
        res[name] = {"danger_caught": f"{caught}/60", "extra_vs_E2": extra, "false_go_now": f"{false}/45",
                     "false_pts_vs_E2": None, "T1_T35": "pass" if not t_failed else f"fail {t_failed}",
                     "CG1_CG18": "pass" if not cg_failed else "fail " + ", ".join(c.split("(")[0] for c in cg_failed)}
    b = int(res["E2 alone"]["false_go_now"].split("/")[0])
    for r in res.values():
        r["false_pts_vs_E2"] = round(100 * (int(r["false_go_now"].split("/")[0]) - b) / 45, 1)
    (ROOT / "data" / "p2_or_ydev.json").write_text(json.dumps(res, indent=1))
    for k, v in res.items():
        print(k, v)


if __name__ == "__main__":
    main()
