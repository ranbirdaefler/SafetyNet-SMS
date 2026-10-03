"""B16 metric code (prereg section 8 and 11). Written and run on Y-dev, pushed before any test output is opened.

Reads the harness's raw output files (one per set and arm) and builds one table per set, never pooled:
rows always go now / never go now / keyword list (E2) / ours; columns missed go-now (CP 95%), needless go-now (CP 95%),
shared path n of s, {c4}, "age not received" alone; plus discordant no-danger counts (b, c) and the exact McNemar p.
Shared-path messages (under 2 months, breathing complaint, no age) are left out of both denominators.
"""
import json
from math import comb
from pathlib import Path

def _binom_cdf(k, n, p):
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(0, k + 1))


def _solve(f, target):
    lo, hi = 0.0, 1.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if f(mid) > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def cp(k, n, alpha=0.05):
    """Clopper-Pearson 95% interval for k of n (exact, by bisection on the binomial tail)."""
    if n == 0:
        return (None, None)
    hi = 1.0 if k == n else _solve(lambda p: _binom_cdf(k, n, p), alpha / 2)          # P(X <= k) = alpha/2
    lo = 0.0 if k == 0 else _solve(lambda p: -(1 - _binom_cdf(k - 1, n, p)), -alpha / 2)  # P(X >= k) = alpha/2
    return (round(100 * lo, 1), round(100 * hi, 1))


def mcnemar_exact(b, c):
    """Exact two-sided McNemar p on the discordant pairs (binomial, p = 0.5)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return round(min(1.0, 2 * p), 4)


def load(path):
    return {r["id"]: r for r in (json.loads(l) for l in open(path, encoding="utf-8"))}


def is_shared(r):
    return r["label"] == "shared"


def table(kw, ours, set_name, ours_label):
    ids = sorted(kw)
    danger = [i for i in ids if kw[i]["label"] == "danger"]
    nodanger = [i for i in ids if kw[i]["label"] == "no_danger"]
    shared = [i for i in ids if is_shared(kw[i]) and kw[i].get("kind") in (None, "u2m", "breathing")]
    m_d, m_n = len(danger), len(nodanger)

    def arm(res):
        missed = sum(not res[i]["triggered"] for i in danger)
        needless = sum(res[i]["triggered"] for i in nodanger)
        return {"missed": missed, "missed_cp95": cp(missed, m_d), "needless": needless, "needless_cp95": cp(needless, m_n),
                "shared_path": f"{sum(res[i]['triggered'] for i in shared)}/{len(shared)}",
                "c4": sum(res[i]["c4"] for i in danger),
                "age_not_received_alone": sum(res[i]["age_not_received_only"] for i in ids),
                "no_better_than_fixed_rule": missed + needless >= min(m_d, m_n) if m_d and m_n else None,
                "errors": [i for i in danger if not res[i]["triggered"]] + [i for i in nodanger if res[i]["triggered"]]}

    b = sum(kw[i]["triggered"] and not ours[i]["triggered"] for i in nodanger)   # keyword list only
    c = sum(ours[i]["triggered"] and not kw[i]["triggered"] for i in nodanger)   # ours only
    return {
        "set": set_name, "danger": m_d, "no_danger": m_n, "shared_path_messages": len(shared),
        "header": "Single pass: each message read once, first reply scored; dialogue not replayed. "
                  f"Registered senders only. Ours = {ours_label}.",
        "rows": {
            "always go now": {"missed": 0, "needless": m_n},
            "never go now": {"missed": m_d, "needless": 0},
            "keyword list (E2)": arm(kw),
            "ours": arm(ours),
        },
        "discordant_no_danger": {"b_keyword_only": b, "c_ours_only": c, "mcnemar_p": mcnemar_exact(b, c)},
        "safety_switch": arm(ours)["missed"] > arm(kw)["missed"],
    }


def run(out_dir, set_name, ours_arm, kw_arm="keyword_E2", ours_label="FP32 ONNX on the Pi 5 (8 GB)"):
    d = Path(out_dir)
    return table(load(d / f"{set_name}.{kw_arm}.jsonl"), load(d / f"{set_name}.{ours_arm}.jsonl"), set_name, ours_label)
