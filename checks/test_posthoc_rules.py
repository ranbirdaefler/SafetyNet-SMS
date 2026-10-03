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


def test_new_symptom_word_never_turns_an_age_into_a_duration():
    p = textparse.parse("mtoto anaharisha ana miezi 8")
    assert p.age_months == 8 and not p.durations


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
