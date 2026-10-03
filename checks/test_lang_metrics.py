"""Language rows read the card language, never the text; (b) is Swahili; (a) has no split. Tested on Y-dev only."""
import pytest

from app import lang_metrics as L


def test_ydev_split_uses_card_language():
    res = L.run("results/dev", "ydev", "keyword_E2")
    assert set(res) <= {"Swahili", "English", "code-mixed"} and sum(v["danger"] for v in res.values()) == 60


def test_set_a_has_no_split():
    with pytest.raises(ValueError):
        L.languages("a")


def test_set_b_is_swahili_by_design():
    assert L.by_language("b", {"D01": {"label": "danger", "triggered": True}}) == {
        "Swahili": {"danger_caught": 1, "danger": 1, "caught_cp95": (2.5, 100.0), "false_go_now": 0, "no_danger": 0,
                    "false_cp95": (None, None)}}
