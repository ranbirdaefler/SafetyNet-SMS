"""v3 training set (v3/CRITERIA.md: TRAIN splits only).

- base: data/x_train_v2.jsonl (X train deduped + the v2 additions);
- data/v3_gen.jsonl (gpt-5.5): contrast pairs and duration hard negatives. A duration negative is dropped if the shared
  regex reads a duration at or over its cut-off (the label would be wrong);
- human-written Swahili as no-danger: MASSIVE 1.1 sw-KE TRAIN and AfriSenti swa TRAIN, after the health/illness/child
  filter in CRITERIA.md;
- SMS-noise copies of 500 training messages (never touching denial words, danger-term words or numbers), labels unchanged.
Everything is deduped against the CG/T probes, Y-dev, the D2 diagnosis pairs and each other. No evaluation or
threshold split is read here. Writes data/x_train_v3.jsonl (local only: it contains third-party text) and a report.
"""
import csv
import json
import random
import re
import sys
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "train"))
from app import lexicon, textparse  # noqa: E402
from prep_v2 import norm_tokens, probe_strings  # noqa: E402

HEADS = ["convulsions", "not_drink_feed", "vomits_everything", "sleepy_unconscious", "blood_stool", "cough_long",
         "diarrhoea_long", "fever_long"]
HEALTH = {"mtoto", "watoto", "mtt", "child", "baby", "mgonjwa", "ugonjwa", "kuumwa", "anaumwa", "homa", "kikohozi",
          "kuhara", "damu", "hospitali", "daktari", "dawa", "sick", "ill", "fever", "cough", "doctor", "hospital",
          "medicine", "health", "afya", "kifo", "death"}
DENIAL = {"hana", "hajapata", "hakuna", "bila", "wala", "si", "sio", "no", "not", "never", "without", "isn't", "isnt",
          "doesn't", "doesnt", "didn't", "didnt", "hasn't", "hasnt", "don't", "dont"}
PROTECTED = DENIAL | {w for rows in (lexicon.T_LIST, lexicon.SHARED, lexicon.C4) for terms in rows.values()
                      for t in terms for w in t.split()} | set(lexicon.CUES)
SHORT = {"mtoto": "mtt", "homa": "hm", "sana": "sn"}
CUT = {"cough": 14, "diarrhoea": 14, "fever": 7}
rng = random.Random(9009)


def noise(text):
    words = text.split(" ")
    out = []
    for w in words:
        core = re.sub(r"[^\w']", "", w.lower())
        if not core or core in PROTECTED or any(ch.isdigit() for ch in core):
            out.append(w)
            continue
        r = rng.random()
        if core in SHORT and r < 0.5:
            out.append(w.lower().replace(core, SHORT[core]))
        elif len(core) >= 4 and r < 0.12:
            i = rng.randrange(1, len(w) - 1) if len(w) > 2 else 0
            out.append(w[:i] + w[i + 1:])                                  # dropped letter
        elif len(core) >= 4 and r < 0.20:
            i = rng.randrange(0, len(w) - 1)
            out.append(w[:i] + w[i + 1] + w[i] + w[i + 2:])                # swapped letters
        else:
            out.append(w)
    s = " ".join(out)
    toks = s.split(" ")
    if len(toks) > 3 and rng.random() < 0.3:                               # one missing space, never on protected words
        j = rng.randrange(0, len(toks) - 1)
        a, b = (re.sub(r"[^\w']", "", x.lower()) for x in (toks[j], toks[j + 1]))
        if a not in PROTECTED and b not in PROTECTED and not any(c.isdigit() for c in a + b):
            toks[j:j + 2] = [toks[j] + toks[j + 1]]
    s = " ".join(toks)
    return s.lower() if rng.random() < 0.5 else s


def human_swahili():
    ms = pq.read_table(ROOT / "data" / "ext" / "massive_sw-KE_train.parquet").column("utt").to_pylist()
    with open(ROOT / "data" / "ext" / "afrisenti_swa_train.tsv", encoding="utf-8") as fh:
        af = [r["tweet"] for r in csv.DictReader(fh, delimiter="\t") if r.get("tweet")]

    def ok(t):
        return not (set(norm_tokens(t)) & HEALTH)
    ms, af = [t for t in ms if ok(t)], [t for t in af if ok(t)]
    rng.shuffle(ms)
    return ms[:1000], af, len(ms), len(af)


def main():
    base = [json.loads(l) for l in open(ROOT / "data" / "x_train_v2.jsonl", encoding="utf-8")]
    gen = [json.loads(l) for l in open(ROOT / "data" / "v3_gen.jsonl", encoding="utf-8")]
    rep = {"base": len(base), "gen": len(gen)}
    kept_gen, dropped_dur = [], 0
    for r in gen:
        if r["source"] == "duration_negative":
            d = textparse.parse(r["message"]).durations
            if any(d.get(k, 0) >= CUT[k] for k in CUT):
                dropped_dur += 1
                continue
        kept_gen.append(r)
    rep["duration_negatives_dropped_regex_at_or_over_cutoff"] = dropped_dur
    ms, af, ms_ok, af_ok = human_swahili()
    human = ([{"id": f"v3m-{i:04d}", "message": t, "present": [0] * 8, "category": "no_danger", "source": "massive_train"} for i, t in enumerate(ms)]
             + [{"id": f"v3a-{i:04d}", "message": t, "present": [0] * 8, "category": "no_danger", "source": "afrisenti_train"} for i, t in enumerate(af)])
    rep.update({"massive_train_after_filter": ms_ok, "massive_train_used": len(ms), "afrisenti_train_after_filter": af_ok,
                "afrisenti_train_used": len(af)})
    noised = []
    for r in rng.sample(base + [g for g in kept_gen if g["source"].startswith("contrast")], 500):
        noised.append({**r, "id": r["id"] + "-noise", "message": noise(r["message"]), "source": "sms_noise"})
    probes = [set(norm_tokens(p)) for p in probe_strings()]
    probe_norm = {" ".join(norm_tokens(p)) for p in probe_strings()}
    dev = {" ".join(norm_tokens(json.loads(l)["message"])) for l in open(ROOT / "data" / "y_dev.jsonl", encoding="utf-8")}
    diag = set()
    for l in open(ROOT / "data" / "diag_contrast_pairs.jsonl", encoding="utf-8"):
        d = json.loads(l)
        diag |= {" ".join(norm_tokens(d["present"])), " ".join(norm_tokens(d["denied"]))}
    seen, out, removed = set(), [], {"probe": 0, "ydev": 0, "diag": 0, "dup": 0}
    for r in base + kept_gen + human + noised:
        n = " ".join(norm_tokens(r["message"]))
        toks = set(n.split())
        if r not in base and (n in probe_norm or any(toks and len(toks & p) / len(toks | p) >= 0.8 for p in probes)):
            removed["probe"] += 1
        elif n in dev:
            removed["ydev"] += 1
        elif n in diag:
            removed["diag"] += 1
        elif n in seen:
            removed["dup"] += 1
        else:
            seen.add(n)
            out.append(r)
    rep["removed"] = removed
    rep["total"] = len(out)
    rep["by_source"] = {}
    for r in out:
        s = r.get("source", "x_train_or_v2")
        rep["by_source"][s] = rep["by_source"].get(s, 0) + 1
    rep["present_per_head"] = {h: sum(r["present"][i] for r in out) for i, h in enumerate(HEADS)}
    with open(ROOT / "data" / "x_train_v3.jsonl", "w", encoding="utf-8") as fh:
        for r in out:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    (ROOT / "data" / "x_train_v3.report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))
    print("noise examples:", [r["message"] for r in noised[:3]])


if __name__ == "__main__":
    main()
