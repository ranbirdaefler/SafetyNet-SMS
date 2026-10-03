"""Post-hoc parent-line rules (Sat 3 Oct, after seeing test misses; not evaluated on sealed data). Sentences are
written from Swahili/English grammar for these tests, not copied from any test set. The rules may only add "go now"."""
import pytest

from app import lexicon, textparse
from app.door import keyword_extractor, parent_policy
from app.engine import Protocol

PARAMS = Protocol.load("config/protocol.yaml", run_suite=False).params


@pytest.fixture(autouse=True)
def live():
    saved = dict(lexicon.LIVE)
    lexicon.use(lexicon.live_list(lexicon.e2_list()))
    yield
    lexicon.use(saved)


def act(text):
    return parent_policy(text, PARAMS, (keyword_extractor,)).action


GO = [
    # (a) -harisha verb forms carry a duration
    "Mwanangu wa miaka 3 amekuwa anaharisha kwa siku 15",
    "Binti yangu wa miezi 30 ameharisha kwa wiki 3",
    "mtoto wa miaka 2 alianza kuharisha tangu siku 20",
    # (b) "joto" as fever only in fixed phrases
    "Mtoto wa miaka 4 ana joto kwa siku 8",
    "mtoto wa miezi 40, joto mwilini kwa wiki 2",
    "mtoto wa miaka 2 amekuwa na joto kwa siku 9",
    # (c) number words and "siku ya N", durations only
    "Mtoto wa miaka 2 ana homa kwa siku tisa",
    "mtoto wa miezi 20 ana kikohozi kwa wiki tatu",
    "mtoto wa miaka 3 ana kuhara kwa siku kumi na tano",
    "Mtoto wa miaka 2, leo ni siku ya 9 ana homa",
    # (d) the previous sentence names the symptom
    "Mtoto wa miaka 2 ana kuhara. Imeendelea kwa siku 16.",
    # (e) refusal described with a negation
    "baby 6 months won't take the breast since morning",
    "mtoto wa miezi 8 anakataa kunyonya tangu jana",
    "my girl is 10 months, not even a sip of milk today",
    # (f) described convulsions
    "my boy 20 months went stiff for a minute",
    "mtoto wa miaka 3 mwili wake umekakamaa",
    "son 2 years, arms jerking and eyes rolled",
]
TOLD = [
    "Mtoto wa miaka 2 ana kuhara kwa siku 10",              # below 14 days
    "mtoto wa miaka 3 ana homa kwa siku tano",              # below 7 days
    "Leo joto kali sana kwa wiki 2, mtoto wa miaka 3 ana upele",   # bare "joto" (weather) is not fever
    "mtoto wa miaka 2 haharishi, ana upele kwa siku 20",    # negative form is not a symptom word
    "Mtoto wa miaka 2 ana kuhara. Anacheza vizuri. Ni kwa siku 16.",  # two sentences back: not attached
    "mtoto wa miezi 10 anakunywa vizuri",
    "my son 2 years drinks well",
    "mtoto wa miaka 2 hana degedege",
    "mtoto wa miaka 2 hatapiki",
    "my son 2 years, his neck is not stiff",
    "mtoto wa miaka 3 anatetemeka akiwa na homa",           # shivering is not in the list
    "girl 3 years is shaking with fever",
]


@pytest.mark.parametrize("text", GO)
def test_go_now(text):
    assert act(text) == "GO_NOW", parent_policy(text, PARAMS, (keyword_extractor,))


@pytest.mark.parametrize("text", TOLD)
def test_not_triggered(text):
    assert act(text) == "TOLD", parent_policy(text, PARAMS, (keyword_extractor,))


@pytest.mark.parametrize("text", ["mtoto wangu wa mwaka mmoja ana upele", "mtoto wa miezi miwili ana upele",
                                  "mtoto wa miaka mitatu ana kikohozi"])
def test_number_words_are_never_ages(text):
    assert textparse.parse(text).age_months is None
    assert act(text) == "GO_NOW_NO_AGE"                    # "go now, age not received" stays


def test_age_before_a_symptom_verb_is_kept_and_after_it_is_a_duration():
    # age first (the usual order): kept
    assert textparse.parse("mtoto wa miezi 8 anaharisha").age_months == 8
    # a number after a symptom verb is a duration (age-verb fix); with no other age the parent gets go now, no age
    p = textparse.parse("mtoto anaharisha ana miezi 8")
    assert p.age_months is None and p.durations.get("diarrhoea") == 240
    assert act("mtoto anaharisha ana miezi 8") in ("GO_NOW", "GO_NOW_NO_AGE")


def test_frozen_attachment_kept():
    # fever named first, a nearer diarrhoea verb: fever still gets the 10 days (additive attachment)
    assert textparse.parse("ana homa na anaharisha kwa siku 10").durations["fever"] == 10


# "kuna" exception (post-hoc): the mined E2 term "kuna" counts for blood in stool only with "damu"
@pytest.mark.parametrize("text", ["Mtoto wangu wa miaka 2 ana kikohozi, kuna mvua nyingi hapa",
                                  "mtoto wa miezi 30 ana upele, je kuna dawa?"])
def test_kuna_alone_is_not_blood(text):
    assert "blood_stool" not in keyword_extractor(text)


@pytest.mark.parametrize("text", ["mtoto wa miaka 2, kuna damu kwenye choo", "mtoto wa miaka 2 kuna choo chenye damu leo",
                                  "mtoto wa miezi 20 ana damu kwenye kinyesi"])
def test_blood_still_read(text):
    assert keyword_extractor(text).get("blood_stool") == "PRESENT"
    assert act(text) == "GO_NOW"


# symptom verbs (post-hoc): a number after a Swahili symptom verb is a duration, never a second (younger) age
@pytest.mark.parametrize("text", ["mtoto wangu wa miezi 18 anaharisha siku 3", "mtoto wangu wa miezi 18 anatapika siku 2",
                                  "mtoto wangu wa miezi 18 anakohoa siku 4"])
def test_symptom_verb_number_is_not_an_age(text):
    assert textparse.parse(text).age_months == 18
    assert act(text) == "TOLD"


@pytest.mark.parametrize("text", ["mtoto wa siku 5 anatapika", "mtoto wa wiki 3 anatapika siku 2",
                                  "mtoto wa miezi 1 anaharisha siku 2"])
def test_real_newborn_ages_still_go_now(text):
    pol = parent_policy(text, PARAMS, (keyword_extractor,))
    assert pol.action == "GO_NOW" and "under 2 months" in pol.reasons


def test_no_age_still_go_now_no_age():
    assert act("anatapika siku 2") == "GO_NOW_NO_AGE"


def test_cough_verb_duration_long_illness():
    pol = parent_policy("mtoto wa miaka 2 alianza kukohoa siku 16 zilizopita", PARAMS, (keyword_extractor,))
    assert pol.action == "GO_NOW" and "long illness" in pol.reasons
