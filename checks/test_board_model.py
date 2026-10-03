"""Board-only model: bands render from stored outputs, sort order, parent reply unchanged with the model on vs off,
and a model exception leaves no model line (the case still shows)."""
import re

from app import board, cg_tests, messages as M
from app.cg_tests import CHP7, Env, P1, P2, P3, BLOCKED
from app.engine import Protocol

PROTO = Protocol.load("config/protocol.yaml", run_suite=False)


class FakeModel:
    """Stands in for the calibrated model: fixed bands by keyword, so the test does not depend on weights."""
    def band(self, text):
        if "rash" in text:
            return {"band": "possible", "sign": "convulsions", "p": 0.99}
        if "mafua" in text:
            return {"band": "unsure", "sign": None, "p": 0.5}
        return {"band": None, "sign": None, "p": 0.01}


class Boom:
    def band(self, text):
        raise RuntimeError("model failed")


def test_bands_render_and_sort():
    e = Env(PROTO, board_model=FakeModel())
    e.send(P2, "parent", "child 18m has a cough")          # no band (CHP 07)
    e.send(P1, "parent", "mtoto miezi 18 ana mafua")       # unsure (CHP 07, busy -> go now, still on her board)
    e.send(P3, "parent", "child 18m has a rash")           # possible (CHP 08)
    rows8 = board.board(e.store, "+254722000108", PROTO)
    assert rows8[0]["model"] == M.BOARD_POSSIBLE.format(sign="convulsions")
    rows = board.board(e.store, CHP7, PROTO)
    assert {r["model"] for r in rows} == {M.BOARD_UNSURE, None}
    assert all(not re.search(r"\d\.\d", r["model"] or "") for r in rows + rows8)   # band words only, no numbers


def test_sort_groups():
    import time as _t
    now = _t.time()
    e = Env(PROTO)

    def case(age, band, danger, created):
        code = e.store.create_case(CHP7, "parent", {"fields": {"convulsions": "PRESENT"} if danger else {}, "age_months": age,
                                                     "u2m": False, "model": {"band": band, "sign": "convulsions"}}, "ASK_SIGNS")
        e.store.db.execute("UPDATE cases SET created = ? WHERE code = ?", (created, code))
        return code
    rest, unsure, possible, danger_old, danger_new = (case(12, None, False, now - 50), case(12, "unsure", False, now - 40),
                                                      case(12, "possible", False, now - 30), case(12, None, True, now - 20),
                                                      case(12, "unsure", True, now - 10))
    assert [r["code"] for r in board.board(e.store, CHP7, PROTO)] == [danger_old, danger_new, possible, unsure, rest]


def test_board_strings_pass_the_never_output_words():
    for s in (M.BOARD_POSSIBLE, M.BOARD_UNSURE):
        low = s.lower()
        assert not any(re.search(r"(?<!\w)" + re.escape(b) + r"(?!\w)", low) for b in BLOCKED)
        assert not any(w in low for w in ("diagnos", "treat", "dose", "medicine", "give"))


def test_parent_reply_identical_with_model_on_and_off():
    texts = [(P1, "mtoto miezi 18 ana mafua"), (P2, "child 18m has a rash"), (P3, "child 18m degedege"),
             ("+254799000001", "child 18m has a rash")]

    def run(model):
        e = Env(PROTO, board_model=model)
        out = []
        for ph, t in texts:
            out += [(m["recipient"], m["msg_id"], re.sub(r"\b\d{4}\b", "CODE", re.sub(r"\d\d:\d\d", "HH:MM", m["body"])))
                    for m in e.send(ph, "parent", t)]
        return out
    assert run(None) == run(FakeModel()) == run(Boom())


def test_cg_suite_unchanged_with_board_model_on():
    cg_tests.BOARD_MODEL = FakeModel()
    try:
        assert cg_tests.run(PROTO) == []
    finally:
        cg_tests.BOARD_MODEL = None


def test_model_exception_gives_no_line_and_case_shows():
    e = Env(PROTO, board_model=Boom())
    e.send(P1, "parent", "child 18m has a rash")
    rows = board.board(e.store, CHP7, PROTO)
    assert len(rows) == 1 and rows[0]["model"] is None
