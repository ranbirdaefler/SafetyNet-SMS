"""Shared regex, keyword list v0 (k = 2) and the shared stage."""
import pytest

from app import lexicon, textparse
from app.extract import chp_case, keyword_rows


@pytest.mark.parametrize("text", ["child 59 days old fever", "mtoto wiki 6 homa", "newborn has a rash",
                                  "mtoto mwezi 1 ana homa", "baby 3 weeks old", "1 month"])
def test_under_2_months(text):          # CG2 inputs at regex level (CG2 itself runs in D2b)
    assert textparse.parse(text).u2m


@pytest.mark.parametrize("text", ["child 2 months cough", "mtoto miezi 2", "60 days old"])
def test_exactly_2_months_in_scope(text):
    assert not textparse.parse(text).u2m


@pytest.mark.parametrize("text,months", [("18m homa siku 3", 18), ("mtoto miezi 18 kikohozi siku 14", 18),
                                         ("child 2 years", 24), ("mwaka 3", 36), ("miaka 2", 24), ("umri miezi 7", 7),
                                         ("my son is 18-24 months", 24), ("3 y and 1 m", 1)])
def test_age(text, months):
    assert textparse.parse(text).age_months == pytest.approx(months)


@pytest.mark.parametrize("text,kind,days", [("18m homa siku 3", "fever", 3), ("kikohozi wiki 2", "cough", 14),
                                            ("fever about a week", "fever", 7), ("cough for 3 weeks", "cough", 21),
                                            ("kuhara siku 10-14", "diarrhoea", 14), ("diarrhea for 2 months", "diarrhoea", 60)])
def test_duration(text, kind, days):
    assert textparse.parse(text).durations.get(kind) == days


def test_duration_is_not_age():
    p = textparse.parse("child 18m cough for 3 weeks")
    assert p.age_months == 18 and not p.u2m


@pytest.mark.parametrize("text,mm", [("MUAC 11.4 cm", 114), ("muac 13.5cm", 135), ("muac 112 mm", 112), ("muac 400", None)])
def test_muac(text, mm):
    assert textparse.parse(text).muac_mm == mm


def test_scope_words():
    p = textparse.parse("she is pregnant and an adult")
    assert p.pregnancy and p.adult


def kw(text):
    return lexicon.match(text, keyword_rows(), k=2)


@pytest.mark.parametrize("text,sign", [("18m degedege", "convulsions"), ("child has fits", "convulsions"),
                                       ("he can't drink", "not_drink_feed"), ("nothing stays down", "vomits_everything"),
                                       ("haamki", "sleepy_unconscious"), ("damu kwenye kinyesi", "blood_stool")])
def test_present(text, sign):
    assert kw(text).get(sign) == "PRESENT"


@pytest.mark.parametrize("text,sign", [("hana degedege", "convulsions"), ("no fits", "convulsions"),
                                       ("there is no blood in stool", "blood_stool"), ("not very sleepy", "sleepy_unconscious")])
def test_negated_is_open(text, sign):
    assert sign not in kw(text)


@pytest.mark.parametrize("text", ["child 18m no he cannot drink", "child 18m he didnt eat cannot drink",
                                  "mtoto miezi 18 hana nguvu hawezi kunyonya", "mtoto miezi 18 hawezi kula wala hawezi kunywa"])
def test_condition_a_never_negated(text):   # CG1 condition-B inputs
    assert kw(text).get("not_drink_feed") == "PRESENT"


def test_cue_outside_window_or_clause():
    assert kw("no, he has fits").get("convulsions") == "PRESENT"           # clause break
    assert kw("no fever but fits").get("convulsions") == "PRESENT"         # "but" breaks the clause
    assert kw("hana homa kali sana degedege").get("convulsions") == "PRESENT"  # cue 4 tokens back > k=2


def test_si_sio_not_cues():
    assert kw("si degedege").get("convulsions") == "PRESENT"


def test_shared_stage_ignores_cues_c4():
    assert lexicon.match("hana kifua kinaingia", lexicon.SHARED, use_cues=False).get("chest_indrawing") == "PRESENT"
    assert lexicon.c4("he is not breathing well, getting worse") == ["breathing complaint", "parent says worse"]


def test_hana_degedege_case_has_nothing_absent():
    c = chp_case("18m hana degedege, homa siku 3, MUAC 13.5 cm, miguu sawa")
    assert c.fields == {} and c.age_months == 18 and c.durations == {"fever": 3} and c.muac_mm == 135


def test_umri_without_unit_is_no_age():
    assert textparse.parse("mtoto umri 7 ana homa").age_months is None


def test_miaka_6_out_of_scope():
    from app.door import parent_policy
    from app.engine import Protocol
    params = Protocol.load("config/protocol.yaml", run_suite=False).params
    assert parent_policy("mtoto miaka 6 ana mafua", params).oos == "5 y+"
    assert parent_policy("mtoto miaka 2 ana mafua", params).action == "TOLD"


def test_age_text_is_not_a_numbered_reply():
    from app.chw import parse_reply
    assert parse_reply("18m homa siku 3", "1234") is None
    assert parse_reply("1234 2 years", "1234") is None
    assert parse_reply("3 asante", "1234") == ("digits", {3})
    assert parse_reply("1234 18", "1234") == ("digits", {1, 8})
