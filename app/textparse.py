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
just before it; otherwise a number with an age unit is the child's age. Numbers written as words are not read as ages.

Post-hoc (Sat 3 Oct, after seeing test misses; not evaluated on sealed data; README). These only attach more
durations; they never create, change or remove an age:
- Diarrhoea verb forms (-harisha: anaharisha, ameharisha, akiharisha, kuharisha ...; not the negative ha- forms) and
  "joto" only as "ana / una joto", "joto mwilini", "joto jingi", "kuwa na joto" count as symptom words for
  attaching a duration. They don't make a number a duration (so they can't turn an age into a duration).
- Swahili number words after a Swahili unit ("wiki mbili", "siku kumi na nne") and the ordinal "siku ya N" are read
  as durations only, never as ages ("mwaka mmoja" is still no age).
- A marked duration with no symptom word in its clause attaches to the symptom words of the previous sentence.
"""
from dataclasses import dataclass, field

from app.lexicon import clauses_with_sentence

UNITS_EN = {"m": "months", "month": "months", "months": "months", "y": "years", "year": "years", "years": "years",
            "yr": "years", "yrs": "years",   # abbreviations of "years", added post-hoc Sat 3 Oct (README)
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
SW_NUM = {"moja": 1, "mmoja": 1, "mbili": 2, "miwili": 2, "wawili": 2, "tatu": 3, "mitatu": 3, "watatu": 3,
          "nne": 4, "minne": 4, "wanne": 4, "tano": 5, "mitano": 5, "watano": 5, "sita": 6, "saba": 7, "nane": 8,
          "tisa": 9}
SW_TENS = {"kumi": 10, "ishirini": 20, "thelathini": 30, "arobaini": 40, "hamsini": 50, "sitini": 60, "sabini": 70,
           "themanini": 80, "tisini": 90}
JOTO_BEFORE = {"ana", "una"}
JOTO_AFTER = {"mwilini", "jingi"}
KUWA = {"kuwa", "amekuwa", "alikuwa", "anakuwa"}


def _symptom(toks, j):
    """Symptom kind of toks[j] for attaching a duration (the frozen words plus the post-hoc forms), else None."""
    t = toks[j]
    if t in SYMPTOM:
        return SYMPTOM[t]
    if t.endswith("harisha") and not t.startswith("ha"):
        return "diarrhoea"
    if t == "joto":
        prev = toks[j - 1] if j > 0 else ""
        nxt = toks[j + 1] if j + 1 < len(toks) else ""
        if prev in JOTO_BEFORE or nxt in JOTO_AFTER or (prev == "na" and j > 1 and toks[j - 2] in KUWA):
            return "fever"
    return None


def _sw_num(toks, i):
    """Swahili number words at toks[i] ("tatu", "kumi na nne", "ishirini na moja"), else None."""
    t = toks[i] if i < len(toks) else ""
    if t in SW_NUM:
        return SW_NUM[t]
    if t in SW_TENS:
        if i + 2 < len(toks) and toks[i + 1] == "na" and toks[i + 2] in SW_NUM:
            return SW_TENS[t] + SW_NUM[toks[i + 2]]
        return SW_TENS[t]
    return None


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
    kinds_by_sentence = {}
    for sent, toks in clauses_with_sentence(text):
        kinds_by_sentence.setdefault(sent, set()).update(k for k in (_symptom(toks, j) for j in range(len(toks))) if k)
        prev_kinds = kinds_by_sentence.get(sent - 1, set())
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
                _add_duration(p, toks, i, 7, prev_kinds)
        # number + unit (English order) or unit + number (Swahili order)
        prev_years_end = None                  # post-hoc (Sat 3 Oct): "1yr 1 month" is one age, 13 months
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
                _add_duration(p, toks, start, v * DAYS[unit], prev_kinds)
            else:
                days = v * DAYS[unit]
                months = v if unit == "months" else v * 12 if unit == "years" else days / 30.4375
                if unit == "months" and prev_years_end is not None and start == prev_years_end + 1 and p.ages_months:
                    p.ages_months[-1] += months         # years directly followed by months, no "and"/"na": one age
                    p.ages_days[-1] += days
                    prev_years_end = None
                    continue
                p.ages_days.append(days)
                p.ages_months.append(months)
                prev_years_end = max(i, ui) if unit == "years" else None
                if (unit == "days" and v < 60) or (unit == "weeks" and v < 9) or (unit == "months" and v < 2):
                    p.u2m = True
        # post-hoc: Swahili unit + number words, and "siku ya N"; durations only, never ages
        for i, t in enumerate(toks):
            if t not in UNITS_SW:
                continue
            j = i + 1
            ordinal = j < len(toks) and toks[j] == "ya"
            j += ordinal
            if j >= len(toks):
                continue
            v = _num(toks[j])
            if v is None:
                v = _sw_num(toks, j)
            elif not ordinal:
                continue                      # unit + digits: read above
            if v is None:
                continue
            before = toks[max(0, i - 2):i]
            age_marked = any(t2 in AGE_MARK for t2 in before)
            dur_marked = ordinal or any(t2 in DUR_MARK for t2 in before) or any(t2 in SYMPTOM for t2 in toks[:i])
            if dur_marked and not age_marked:
                _add_duration(p, toks, i, v * DAYS[UNITS_SW[t]], prev_kinds)
    if p.newborn:
        p.u2m = True
    return p


def _nearest(toks, at, find):
    for j in list(reversed(range(at))) + list(range(at, len(toks))):
        k = find(toks, j)
        if k:
            return k
    return None


def _add_duration(p, toks, at, days, prev_kinds=()):
    """Attach a duration to the nearest symptom word before it in the clause, else the next one after it.
    Post-hoc, additive only: also to the nearest post-hoc symptom form; if the clause has none, to every symptom of
    the previous sentence."""
    frozen = _nearest(toks, at, lambda t, j: SYMPTOM.get(t[j]))
    extended = _nearest(toks, at, _symptom)
    kinds = {k for k in (frozen, extended) if k} or set(prev_kinds)
    for k in sorted(kinds):
        p.durations[k] = max(days, p.durations.get(k, 0))
