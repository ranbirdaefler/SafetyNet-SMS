"""RED-only rules engine over the ministry protocol file.

Signs are PRESENT, OPEN or ABSENT. Only a numbered CHP reply ("0") makes a sign ABSENT; no text is ever read ABSENT.
First match wins: E1, Z0, O1, O3, O4, O2, F1, F3.
"""
from dataclasses import dataclass, field
from pathlib import Path

import yaml

PRESENT, OPEN, ABSENT = "PRESENT", "OPEN", "ABSENT"
OUTPUTS = {"REFER_NOW"}
DURATION_FIELD = {"cough": "cough_long", "diarrhoea": "diarrhoea_long", "fever": "fever_long"}
DURATION_PARAM = {"cough": "cough_red_days", "diarrhoea": "diarrhoea_red_days", "fever": "fever_red_days"}


class ProtocolRejected(Exception):
    pass


@dataclass
class Case:
    registered: bool = True
    fields: dict = field(default_factory=dict)      # field id -> PRESENT / OPEN / ABSENT (missing = OPEN)
    age_months: float | None = None                  # None: no attributable age
    u2m: bool = False                                # under 2 months (regex: < 60 d, < 9 wk, < 2 m, or newborn word)
    pregnancy: bool = False
    adult: bool = False
    durations: dict = field(default_factory=dict)   # cough/diarrhoea/fever -> days (hedged count at threshold counts)
    muac_mm: float | None = None
    text_not_read: bool = False


@dataclass
class Decision:
    output: str                    # UNREGISTERED, REFER_NOW, REFER_U2M, OOS_HUMAN, ASK_AGE, ASK_SIGNS, NON_RED
    rule: str
    reasons: list = field(default_factory=list)   # sign labels, option order, no duplicates
    u2m: bool = False
    present: list = field(default_factory=list)
    open_fields: list = field(default_factory=list)
    oos: str | None = None


class Protocol:
    def __init__(self, cfg):
        self.cfg = cfg
        self.params = {k: v["value"] for k, v in cfg["parameters"].items()}
        self.fields = sorted(cfg["fields"], key=lambda f: f["option"])
        self.field_ids = [f["id"] for f in self.fields]
        self.label = {f["id"]: f["label"] for f in self.fields}
        self.rules = cfg["rules"]
        self.scope = cfg["scope"]["age_months"]

    # ---------- loading ----------
    @classmethod
    def load(cls, path, suite_ids=None, run_suite=True):
        cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        cls.validate(cfg)
        proto = cls(cfg)
        if run_suite:
            from app import must_stay_red
            failed = must_stay_red.run(proto, suite_ids)
            if failed:
                raise ProtocolRejected(f"must-stay-RED tests failed: {', '.join(failed)}")
        return proto

    @staticmethod
    def validate(cfg):
        for key in ("profile", "scope", "parameters", "timeouts", "fields", "rules"):
            if key not in cfg:
                raise ProtocolRejected(f"missing section: {key}")
        for name, p in cfg["parameters"].items():
            if p["value"] not in p["allowed"]:
                raise ProtocolRejected(f"parameter {name}={p['value']} not in allowed {p['allowed']}")
        ids = [f["id"] for f in cfg["fields"]]
        if len(ids) != len(set(ids)):
            raise ProtocolRejected("duplicate field id")
        for f in cfg["fields"]:
            if f.get("observer") not in ("caregiver", "chp"):
                raise ProtocolRejected(f"field {f['id']}: observer must be caregiver or chp")
            if not 1 <= int(f["option"]) <= 8:
                raise ProtocolRejected(f"field {f['id']}: option must be 1-8")
        for r in cfg["rules"]:
            if r["then"] not in OUTPUTS:
                raise ProtocolRejected(f"rule {r['id']}: output {r['then']} not allowed (RED only)")
            for fid, state in r["if"].items():
                if fid not in ids or state != PRESENT:
                    raise ProtocolRejected(f"rule {r['id']}: condition must be an existing field PRESENT")

    # ---------- evaluation ----------
    def derive(self, case):
        """Field states from the case: durations and MUAC can only raise a field to PRESENT."""
        st = {fid: case.fields.get(fid, OPEN) for fid in self.field_ids}
        for kind, days in case.durations.items():
            if days is not None and days >= self.params[DURATION_PARAM[kind]]:
                st[DURATION_FIELD[kind]] = PRESENT
        if case.muac_mm is not None and case.muac_mm < self.params["muac_red_below_mm"]:
            st["muac_red"] = PRESENT
        return st

    def evaluate(self, case):
        st = self.derive(case)
        present = [fid for fid in self.field_ids if st[fid] == PRESENT]
        open_ = [fid for fid in self.field_ids if st[fid] == OPEN]
        u2m = case.u2m or (case.age_months is not None and case.age_months < self.scope["min"])
        if not case.registered:
            return Decision("UNREGISTERED", "E1", present=present, open_fields=open_)
        fired = [r for r in self.rules if all(st[f] == s for f, s in r["if"].items())]
        if fired:
            reasons = []
            for fid in present:
                if self.label[fid] not in reasons:
                    reasons.append(self.label[fid])
            return Decision("REFER_NOW", "Z0", reasons=reasons, u2m=u2m, present=present, open_fields=open_)
        if u2m:
            return Decision("REFER_U2M", "O1", reasons=["under 2 months"], u2m=True, open_fields=open_)
        if case.pregnancy or case.adult:
            return Decision("OOS_HUMAN", "O3", oos="pregnancy" if case.pregnancy else "adult", open_fields=open_)
        if case.age_months is None:
            return Decision("ASK_AGE", "O4", open_fields=open_)
        if case.age_months > self.scope["max"]:
            return Decision("OOS_HUMAN", "O2", oos="5 y+", open_fields=open_)
        if open_:
            return Decision("ASK_SIGNS", "F1", open_fields=open_)
        return Decision("NON_RED", "F3")

    def evaluate_text(self, extract, text, **kw):
        """Run an extractor; if it raises, every sign stays OPEN (the checklist is asked), never ABSENT."""
        try:
            case = extract(text, **kw)
        except Exception:
            case = Case(registered=kw.get("registered", True), text_not_read=True)
        for fid, s in list(case.fields.items()):
            if s == ABSENT:  # no text is ever read ABSENT
                case.fields[fid] = OPEN
        return self.evaluate(case)
