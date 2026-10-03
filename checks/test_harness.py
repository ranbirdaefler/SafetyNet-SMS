"""Harness loaders, tested on dummy files only (never on a test set)."""
import json

from app import harness
from app.engine import Protocol


def test_loaders_and_run_on_dummy_files(tmp_path):
    csv_p = tmp_path / "dummy.csv"
    csv_p.write_text('id,label_line,message\nD01,"D01 danger: x","child 18m degedege"\n'
                     'N02,"N02 no danger: none","child 18m runny nose || still eating"\n', encoding="utf-8")
    rows = harness.load_set(csv_p)
    assert [(r["id"], r["label"]) for r in rows] == [("D01", "danger"), ("N02", "no_danger")]
    js = tmp_path / "dummy.jsonl"
    js.write_text("\n".join(json.dumps({"id": f"y-{i}", "category": c, "kind": k, "message": m}) for i, (c, k, m) in
                            enumerate([("danger", None, "child 18m fits"), ("shared", "no_age", "mtoto ana homa")])) + "\n",
                  encoding="utf-8")
    params = Protocol.load("config/protocol.yaml", run_suite=False).params
    res = harness.run_arm(harness.load_set(js), params, (harness.keyword_extractor,))
    assert res[0]["triggered"] and not res[1]["triggered"] and res[1]["age_not_received_only"]
