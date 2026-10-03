"""Shared age and duration regex (both eval arms), MUAC regex and scope words.

Word lists (README lists each one; only words from the protocol record, PREREGISTRATION.md section 5):
- Age units: m, month(s), y, year(s), d, day(s), week(s); miezi, mwezi (months), mwaka, miaka (years), wiki (weeks),
  siku (days). "miaka" was added on Sat 3 Oct before any test set was opened (source: the pre-event Swahili
  onboarding text "miezi 2 hadi miaka 5", ux_localization.md). "umri" marks an age; "umri N" without a unit is no age.
- Under 2 months: under 60 days, under 9 weeks, under 2 months, or "newborn" (S10). Exactly 2 months is in scope.
- Pregnancy / adult words: "pregnant", "pregnancy", "adult". No Swahili newborn or pregnancy terms are in the sources.
- Symptom words for durations: cough, kikohozi; diarrhoea, diarrhea, kuhara; fever, homa (Swahili words from the
  pre-event ASK_SIGNS option 7, "Siku: kikohozi 14+, kuhara 14+, homa 7+", ux_localization.md).
- "about a week" / "a week" = 7 days. "wiki N" = 7N days. A range takes its upper bound.
- MUAC: read from 50 to 300 mm or 5.0 to 30.0 cm after the word "muac".
A number is a duration when a symptom word comes earlier in the same clause or "for / kwa / since / tangu" comes
just before it; otherwise a number with an age unit is the child's age. Numbers written as words are not read.
"""
from dataclasses import dataclass, field

from app.lexicon import clauses

UNITS_EN = {"m": "months", "month": "months", "months": "months", "y": "years", "year": "years", "years": "years",
            "d": "days", "day": "days", "days": "days", "week": "weeks", "weeks": "weeks"}
UNITS_SW = {"miezi": "months", "mwezi": "months", "mwaka": "years", "miaka": "years", "wiki": "weeks", "siku": "days"}
AGE_MARK = {"umri", "age", "aged"}
DUR_MARK = {"for", "kwa", "since", "tangu"}
SYMPTOM = {"cough": "cough", "kikohozi": "cough", "diarrhoea": "diarrhoea", "diarrhea": "diarrhoea",
           "kuhara": "diarrhoea", "fever": "fever", "homa": "fever"}
NEWBORN = {"newborn"}
PREGNANCY = {"pregnant", "pregnancy"}
ADULT = {"adult"}
DAYS = {"days": 1, "weeks": 7, "months": 30, "years": 365}


def _num(tok):
    try:
        return float(tok.split("-")[-1])          # range: upper bound
    except ValueError:
        return None


@dataclass
class Parsed:
    ages_days: list = field(default_factory=list)   # every age read, in days (approx for months/years)
    ages_months: list = field(default_factory=list)
    u2m: bool = False
    newborn: bool = False
    pregnancy: bool = False
    adult: bool = False
    durations: dict = field(default_factory=dict)  # cough/diarrhoea/fever -> max days
    muac_mm: float | None = None

    @property
    def age_months(self):
        return min(self.ages_months) if self.ages_months else None   # youngest age decides (D9)


def parse(text):
    p = Parsed()
    for toks in clauses(text):
        words = set(toks)
        p.newborn |= bool(words & NEWBORN)
        p.pregnancy |= bool(words & PREGNANCY)
        p.adult |= bool(words & ADULT)
        # MUAC
        for i, t in enumerate(toks):
            if t == "muac":
                for j in range(i + 1, min(i + 4, len(toks))):
                    v = _num(toks[j])
                    if v is None:
                        continue
                    unit = toks[j + 1] if j + 1 < len(toks) else ""
                    mm = v * 10 if (unit == "cm" or (unit != "mm" and v <= 30)) else v
                    if 50 <= mm <= 300:
                        p.muac_mm = mm if p.muac_mm is None else min(p.muac_mm, mm)
                    break
        # "about a week" / "a week"
        for i in range(len(toks) - 1):
            if toks[i] == "a" and toks[i + 1] == "week":
                _add_duration(p, toks, i, 7)
        # number + unit (English order) or unit + number (Swahili order)
        for i, t in enumerate(toks):
            v = _num(t)
            if v is None:
                continue
            unit, ui = None, None
            if i + 1 < len(toks) and toks[i + 1] in UNITS_EN:
                unit, ui = UNITS_EN[toks[i + 1]], i + 1
            elif i > 0 and toks[i - 1] in UNITS_SW:
                unit, ui = UNITS_SW[toks[i - 1]], i - 1
            elif i + 1 < len(toks) and toks[i + 1] in UNITS_SW:
                unit, ui = UNITS_SW[toks[i + 1]], i + 1
            if unit is None:
                continue
            start = min(i, ui)
            after = toks[max(i, ui) + 1] if max(i, ui) + 1 < len(toks) else ""
            age_marked = after == "old" or any(t2 in AGE_MARK for t2 in toks[max(0, start - 2):start])
            dur_marked = any(t2 in DUR_MARK for t2 in toks[max(0, start - 2):start]) or any(
                t2 in SYMPTOM for t2 in toks[:start])
            if dur_marked and not age_marked:
                _add_duration(p, toks, start, v * DAYS[unit])
            else:
                days = v * DAYS[unit]
                months = v if unit == "months" else v * 12 if unit == "years" else days / 30.4375
                p.ages_days.append(days)
                p.ages_months.append(months)
                if (unit == "days" and v < 60) or (unit == "weeks" and v < 9) or (unit == "months" and v < 2):
                    p.u2m = True
    if p.newborn:
        p.u2m = True
    return p


def _add_duration(p, toks, at, days):
    """Attach a duration to the nearest symptom word before it in the clause, else the next one after it."""
    kind = None
    for t in reversed(toks[:at]):
        if t in SYMPTOM:
            kind = SYMPTOM[t]
            break
    if kind is None:
        for t in toks[at:]:
            if t in SYMPTOM:
                kind = SYMPTOM[t]
                break
    if kind:
        p.durations[kind] = max(days, p.durations.get(kind, 0))
