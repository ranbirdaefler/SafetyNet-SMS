"""v3 step 4: the ONE joint evaluation (after results, exploratory). Boards: v2 as shipped (lo 0.068 / hi 0.9), v2
re-tuned (rule thresholds), v3 (rule thresholds). EVALUATION splits only: sealed y_test2, MASSIVE sw-KE test (same
1,000), FLORES-200 devtest, AfriSenti swa test. Decides the board by the pre-declared order in v3/CRITERIA.md.
Report-only extra: the shipped board file(s) on the old sealed sets (a), (b), Y-test.
"""
import csv
import json
import random
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import cg_tests, lexicon, must_stay_red  # noqa: E402
from app.board_model import BoardModel  # noqa: E402
from app.door import keyword_extractor, list_extractor, parent_policy  # noqa: E402
from app.engine import Protocol  # noqa: E402
from app.harness import SETS, load_set, triggered  # noqa: E402
from app.metrics import cp  # noqa: E402

EXT = ROOT / "data" / "ext"
BOARDS = {"v2 as shipped": "config/board_model.json", "v2 re-tuned": "config/board_model_v2_retuned.json",
          "v3": "config/board_model_v3.json"}


def everyday_eval():
    utts = pq.read_table(EXT / "massive_sw-KE_test.parquet").column("utt").to_pylist()
    idx = random.Random(20261003).sample(range(len(utts)), 1000)
    fl = [l.strip() for l in open(EXT / "flores200_dataset" / "devtest" / "swh_Latn.devtest", encoding="utf-8") if l.strip()]
    with open(EXT / "afrisenti_swa_test.tsv", encoding="utf-8") as fh:
        af = [r["tweet"] for r in csv.DictReader(fh, delimiter="\t") if r.get("tweet")]
    return {"MASSIVE sw-KE test (1,000)": [utts[i] for i in idx], "FLORES-200 devtest": fl, "AfriSenti swa test": af}


def flagged(b):
    return b in ("possible", "unsure")


def main():
    proto = Protocol.load(ROOT / "config" / "protocol.yaml", run_suite=False)
    params = proto.params
    lexicon.use(lexicon.e2_list())
    e2 = list_extractor(lexicon.LIVE)
    boards = {k: BoardModel(cfg_path=ROOT / v) for k, v in BOARDS.items()}
    out = {"label": "after results, exploratory", "boards": {k: {"model_dir": b.cfg["model_dir"], "lo": b.lo, "hi": b.hi}
                                                              for k, b in boards.items()}}
    # (a) T1-T35 and CG1-CG18 with each board model on
    out["a_tests"] = {}
    for k, b in boards.items():
        cg_tests.BOARD_MODEL = b
        try:
            out["a_tests"][k] = {"T": must_stay_red.run(proto), "CG": cg_tests.run(proto)}
        finally:
            cg_tests.BOARD_MODEL = None
    # (b) y_test2: keywords + board
    y2 = load_set(ROOT / "tests" / "y_test2.jsonl")
    kw = {r["id"]: triggered(parent_policy(r["message"], params, (e2,))) for r in y2}
    danger = [r for r in y2 if r["label"] == "danger"]
    nod = [r for r in y2 if r["label"] == "no_danger"]
    out["y_test2"] = {"N": len(y2), "danger": len(danger), "no_danger": len(nod),
                      "keywords_alone": {"missed": sum(not kw[r["id"]] for r in danger), "needless": sum(kw[r["id"]] for r in nod)}}
    bands = {}
    for k, b in boards.items():
        bands[k] = {r["id"]: b.band(r["message"])["band"] for r in y2}
        miss = sum(not kw[r["id"]] and not flagged(bands[k][r["id"]]) for r in danger)
        out["y_test2"][f"keywords + {k} board"] = {"missed": miss, "missed_cp95": cp(miss, len(danger)),
                                                   "no_danger_flagged": sum(flagged(bands[k][r["id"]]) for r in nod)}
    # research row: the model alone on the parent-line rule (raw p >= 0.5) vs keywords
    for k in ("v2 as shipped", "v3"):
        enc = boards[k].enc
        res = {r["id"]: triggered(parent_policy(r["message"], params, (enc, keyword_extractor))) for r in y2}
        out["y_test2"][f"{k} alone (parent-line rule)"] = {"missed": sum(not res[r["id"]] for r in danger),
                                                           "needless": sum(res[r["id"]] for r in nod)}
    # (c) everyday Swahili evaluation splits: board flagged, and triggered (parent-line rule)
    ev = everyday_eval()
    out["everyday"] = {}
    for src, texts in ev.items():
        r = {"N": len(texts), "triggered: keywords E2": sum(triggered(parent_policy(t, params, (e2,))) for t in texts)}
        for k, b in boards.items():
            bs = [b.band(t)["band"] for t in texts]
            f = sum(flagged(x) for x in bs)
            r[f"board flagged: {k}"] = {"n": f, "pct": round(100 * f / len(texts), 1), "cp95": cp(f, len(texts))}
        for k in ("v2 as shipped", "v3"):
            r[f"triggered: {k} (parent-line rule)"] = sum(triggered(parent_policy(t, params, (boards[k].enc, keyword_extractor))) for t in texts)
        out["everyday"][src] = r
        print(src, "done", flush=True)
    # decision, pre-declared order: v3 -> v2 re-tuned -> v2 as shipped
    base_miss = out["y_test2"]["keywords + v2 as shipped board"]["missed"]
    verdict = {}
    for k in ("v3", "v2 re-tuned"):
        a = not out["a_tests"][k]["T"] and not out["a_tests"][k]["CG"]
        b = out["y_test2"][f"keywords + {k} board"]["missed"] <= base_miss
        c = all(out["everyday"][s][f"board flagged: {k}"]["pct"] <= 35 for s in ev)
        verdict[k] = {"a": a, "b": b, "c": c, "passes": a and b and c}
    out["verdict"] = verdict
    out["board_ships"] = "v3" if verdict["v3"]["passes"] else "v2 re-tuned" if verdict["v2 re-tuned"]["passes"] else "v2 as shipped"
    # report-only: the shipped board file(s) on the old sealed sets, keywords + board
    out["old_sets_report_only"] = {}
    for k in sorted({"v2 as shipped", out["board_ships"]}):
        b = boards[k]
        rows = {}
        for s in ("a", "b", "ytest"):
            data = load_set(SETS[s])
            kws = {r["id"]: triggered(parent_policy(r["message"], params, (e2,))) for r in data}
            bb = {r["id"]: b.band(r["message"])["band"] for r in data}
            d = [r for r in data if r["label"] == "danger"]
            n = [r for r in data if r["label"] == "no_danger"]
            rows[s] = {"keywords + board missed": sum(not kws[r["id"]] and not flagged(bb[r["id"]]) for r in d), "danger": len(d),
                       "no_danger flagged": sum(flagged(bb[r["id"]]) for r in n), "no_danger": len(n)}
        out["old_sets_report_only"][k] = rows
    (ROOT / "v3" / "evaluation.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("verdict", "board_ships")}, indent=1))


if __name__ == "__main__":
    main()
