"""B16: tabulate the sealed outputs ONCE (as committed in 357f63a), with the metric code pushed before (d3dd0e9,
1d1d799, 7b9fb58). Pre-registered rows: keyword list E2 vs ours = registered v1 FP32, outcome statement verbatim.
Exploratory rows, labelled: deployed v1, v2, per-language, board, MASSIVE.
Usage: python train/tabulate.py            (sealed sets a, b, ytest -> results/TABLES.md, results/tables.json)
       python train/tabulate.py --dry-run  (Y-dev dev outputs only, to test the code)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import lang_metrics, metrics  # noqa: E402

PI_P95 = {"ours_registered": 126.0, "deployed": 86.3, "v2": None, "ours_fp32": 126.0}   # ms per 64-token message, Pi 5, 4 cores
GRID_CLASS = {"D02": ["hedging", "lay wording"], "D04": ["negation"], "D06": ["lay wording"], "D08": ["hedging"],
              "D09": ["split"], "D10": ["temporal"], "D11": ["hedging", "temporal"], "D04b": ["split"],
              "N01": ["negation"], "N02": ["negation"], "N03": ["negation"], "N04": ["negation"], "N05": ["near-miss"],
              "N06": ["near-miss"], "N07": ["near-miss"], "N08": ["near-miss"], "N09": ["near-miss", "split"],
              "N10": ["near-miss"]}
FORM_CLASS = {"hedged": "hedging", "negative_form": "negation", "lay": "lay wording"}


def classes(set_name, i, cards):
    if set_name in ("a", "b"):
        return GRID_CLASS.get(i, ["plain"])
    c = cards[i]
    out = sorted({FORM_CLASS[f] for f in c.get("forms", {}).values() if f in FORM_CLASS})
    if any("relative time" in f for f in c.get("facts", [])):
        out.append("temporal")
    if c.get("kind") == "negated":
        out.append("negation")
    if c.get("kind") == "near_miss":
        out.append("near-miss")
    if c.get("lang") == "code-mixed":
        out.append("code-mixing")
    if "casual" in c.get("style", []):
        out.append("typo")
    if "two texts" in c.get("style", []):
        out.append("split")
    return out or ["plain"]


def fmt_ci(ci):
    return "" if ci[0] is None else f"({ci[0]}-{ci[1]}%)"


def table_md(t, title, ours_label, p95):
    m_d, m_n = t["danger"], t["no_danger"]
    lines = [f"### {title}", "", f"_{t['header']}_", "",
             "| Row | Missed go-now | Needless go-now | Shared path | {c4} | \"Age not received\" alone | Pi p95 |",
             "|---|---|---|---|---|---|---|"]
    for name, r in t["rows"].items():
        label = ours_label if name == "ours" else name
        if name in ("always go now", "never go now"):
            lines.append(f"| {label} | {r['missed']}/{m_d} | {r['needless']}/{m_n} | | | | |")
        else:
            pp = "" if name != "ours" or p95 is None else f"{p95} ms"
            lines.append(f"| {label} | {r['missed']}/{m_d} {fmt_ci(r['missed_cp95'])} | {r['needless']}/{m_n} {fmt_ci(r['needless_cp95'])} "
                         f"| {r['shared_path']} | {r['c4']} | {r['age_not_received_alone']} | {pp} |")
    dn = t["discordant_no_danger"]
    lines += ["", f"Discordant no-danger messages: b (keyword list only) = {dn['b_keyword_only']}, c (ours only) = {dn['c_ours_only']}; "
                  f"exact McNemar p = {dn['mcnemar_p']}.", ""]
    for name in ("keyword list (E2)", "ours"):
        r = t["rows"][name]
        if r.get("no_better_than_fixed_rule"):
            lines.append(f"Flag: {ours_label if name == 'ours' else name} is no better than a fixed rule (misses + needless >= min(danger, no-danger)).")
    return lines


def main():
    dry = "--dry-run" in sys.argv
    out_dir = ROOT / ("results/dev" if dry else "results/test")
    sets = ["ydev"] if dry else ["a", "b", "ytest"]
    ours = "ours_fp32" if dry else "ours_registered"
    extra = [] if dry else [("deployed", "Exploratory: deployed v1 (vocab trim + 8-bit weights)"), ("v2", "Exploratory: v2 FP32 (second training run)")]
    cards = {}
    for f in ("data/y_dev.jsonl", "tests/y_test.jsonl"):
        p = ROOT / f
        if p.exists() and (dry or "y_test" in f):
            for l in open(p, encoding="utf-8"):
                c = json.loads(l)
                cards[c["id"]] = c
    md = ["# Results", "", "Pre-registered claim (native Swahili): NOT TESTED", "",
          "Tabulated once, on the sealed outputs as committed in 357f63a (freeze 28609b6). Metric code pushed before: "
          "d3dd0e9 (tables), 1d1d799 (language rows), 7b9fb58 (board rows).", ""]
    js = {"sets": {}}
    titles = {"a": "(a) Claude-written from a fixed case grid", "b": "(b) AI-generated Swahili (claude-opus-5-5), not checked by a native speaker",
              "ytest": "Y-test, Claude, caregiver", "ydev": "Y-dev (dry run)"}
    summary = {}
    for s in sets:
        t = metrics.run(out_dir, s, ours, ours_label="FP32 ONNX on the Pi 5 (8 GB)")
        kw = metrics.load(out_dir / f"{s}.keyword_E2.jsonl")
        ours_res = metrics.load(out_dir / f"{s}.{ours}.jsonl")
        md += table_md(t, f"{titles[s]} (pre-registered row)", "ours (registered v1 FP32)", PI_P95.get(ours))
        if s == "b":
            md += ["", "Row note: The keyword list's Swahili words and every test set are Claude-written; this favours the keyword list."]
        errs = []
        for name, res in (("keyword list (E2)", kw), ("ours", ours_res)):
            for i, r in sorted(res.items()):
                if r["label"] == "danger" and not r["triggered"]:
                    errs.append(f"| {name} | {i} | missed go-now | {', '.join(classes(s, i, cards))} |")
                if r["label"] == "no_danger" and r["triggered"]:
                    errs.append(f"| {name} | {i} | needless go-now | {', '.join(classes(s, i, cards))} |")
        md += ["", "Error listing:", "", "| Arm | Message ID | Error | Class |", "|---|---|---|---|"] + (errs or ["| | none | | |"]) + [""]
        js["sets"][s] = {"registered": t}
        summary[s] = t
        for arm, label in extra:
            te = metrics.run(out_dir, s, arm)
            md += table_md(te, f"{titles[s]}: {label}", label.split(": ")[1], PI_P95.get(arm)) + [""]
            js["sets"][s][arm] = te
        # exploratory per-language rows
        if s != "a":
            md += [f"Exploratory, per language (card language, never the text), {titles[s]}:", "",
                   "| Arm | Language | Danger caught | False go-now |", "|---|---|---|---|"]
            js["sets"][s]["language"] = {}
            for arm in ["keyword_E2", ours] + [a for a, _ in extra]:
                lr = lang_metrics.run(out_dir, s, arm)
                js["sets"][s]["language"][arm] = lr
                for g, v in lr.items():
                    md.append(f"| {arm} | {g} | {v['danger_caught']}/{v['danger']} {fmt_ci(v['caught_cp95'])} | "
                              f"{v['false_go_now']}/{v['no_danger']} {fmt_ci(v['false_cp95'])} |")
            md.append("")
        # exploratory board rows
        bpath = ROOT / ("results/dev/board_ydev.json" if dry else f"results/board/{s}.json")
        if bpath.exists():
            br = metrics.board_rows(kw, json.loads(bpath.read_text()))
            js["sets"][s]["board"] = br
            md += [f"_{br['label']}_", "",
                   f"- (a) of the danger messages E2 misses, flagged by the board: {br['a_e2_missed_danger_flagged_by_board']}/{br['a_of']} {fmt_ci(br['a_cp95'])}",
                   f"- (b) no-danger messages flagged by the board (extra reads): {br['b_no_danger_flagged']}/{br['b_of']} {fmt_ci(br['b_cp95'])}", ""]
    if not dry:
        # C11 safety switch: checked first, on every set shown
        switch = [(s, summary[s]["rows"]["ours"]["missed"], summary[s]["danger"], summary[s]["rows"]["keyword list (E2)"]["missed"])
                  for s in sets if summary[s]["safety_switch"]]
        a, b, y = summary["a"], summary["b"], summary["ytest"]

        def caught(t, row):
            return t["danger"] - t["rows"][row]["missed"]
        para = ("No native speaker's texts were sealed in time, so my registered claim is not tested. On three stand-in sets, the model sent "
                f"{caught(a, 'ours')} of 12 children with a danger sign to the clinic in 25 test messages an AI model wrote from a fixed case grid, "
                f"{caught(b, 'ours')} of {b['danger']} in 25 AI-written Swahili texts no native speaker checked, and {caught(y, 'ours')} of 80 in "
                f"{150} AI-written test texts; the keyword list {caught(a, 'keyword list (E2)')}, {caught(b, 'keyword list (E2)')}, "
                f"{caught(y, 'keyword list (E2)')}. Needless trips: model {a['rows']['ours']['needless']} of 13, {b['rows']['ours']['needless']} of "
                f"{b['no_danger']}, {y['rows']['ours']['needless']} of 55; keyword list {a['rows']['keyword list (E2)']['needless']}, "
                f"{b['rows']['keyword list (E2)']['needless']}, {y['rows']['keyword list (E2)']['needless']}. None are real parents' texts, so the "
                "model is not shown to beat a keyword list.")
        out = ["## Outcome (pre-registered, checked in order: safety switch, then Win, then Tie-or-loss; no native set)", ""]
        out.append("Safety switch (C11): " + ("fired on " + ", ".join(f"({x[0]})" for x in switch) if switch else "did not fire") + ".")
        out += ["", "> " + para, "", "On screen with it: \"Test messages written by an AI model from a fixed case grid; no native or human-written test set.\""]
        for s_, k, m_d, k_lex in switch:
            out += ["", "> " + f"Before testing I set a rule that the model may not miss more children with a danger sign than a keyword list; on {titles[s_]} it missed {k} of {m_d}, the keyword list {k_lex}, so the keyword list now runs the parent line."]
        out.append("")
        md = md[:6] + out + md[6:]
        js["outcome"] = {"safety_switch": [list(x) for x in switch], "paragraph": para}
        m = json.loads((ROOT / "results" / "massive_row.json").read_text())
        m2 = json.loads((ROOT / "results" / "massive_row_v2_deployed.json").read_text())
        md += ["## Exploratory, not pre-registered: MASSIVE sw-KE", "", f"_{m['label']}_ Triggered go-now of {m['N']} (seed {m['seed']}):", "",
               "| Arm | Triggered | CP 95% |", "|---|---|---|"]
        for k, v in list(m["arms"].items()) + [(("deployed board model v2 (shipped)" if "v2" in k else k), v) for k, v in m2["arms"].items() if "v2" in k]:
            md.append(f"| {k} | {v['triggered']}/{v['N']} | {fmt_ci(v['cp95_pct'])} |")
        js["massive"] = {"v1": m, "v2_deployed": m2}
    name = "TABLES_dryrun_ydev.md" if dry else "TABLES.md"
    (ROOT / "results" / name).write_text("\n".join(md), encoding="utf-8")
    (ROOT / "results" / name.replace(".md", ".json")).write_text(json.dumps(js, indent=1))
    print(f"wrote results/{name}")


if __name__ == "__main__":
    main()
