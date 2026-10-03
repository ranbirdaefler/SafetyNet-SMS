"""Every allowlisted parent message, in every language and with every prefix, with each slot at its LONGEST value, is
pure GSM-7 (extension characters count 2) and within its segment limit. Also the health worker's own-message path."""
import pytest

from app import messages as M
from app import questions as QL
from app.engine import Protocol
from app.questions import GSM, GSM_EXT, segments
from app.registry import Registry

PROTO = Protocol.load("config/protocol.yaml", run_suite=False)
REG = Registry("config/registry.yaml")
LONGEST_FACILITY = max((f["name"] for f in REG.facilities.values()), key=len)
MAX_MINUTES = max(PROTO.cfg["timeouts"].get("reply_window_min", 60), 999)       # 3 digits: the allowlist slot maximum
SLOTS = dict(facility=LONGEST_FACILITY, code="9999", time="23:59", minutes=MAX_MINUTES)


def gsm(text):
    bad = sorted({c for c in text if c not in GSM and c not in GSM_EXT})
    return bad


def limit(msg_id, lang):
    if msg_id in M.BILINGUAL and msg_id in M.SW_PARENT:          # always sent Swahili + English, whatever the lang
        return M.SEGMENT_LIMIT["bi"][msg_id]
    if lang == "sw" and msg_id in M.SW_PARENT:
        return M.SEGMENT_LIMIT["sw"][msg_id]
    return M.SEGMENT_LIMIT["en"][msg_id]


@pytest.mark.parametrize("msg_id", sorted(M.PARENT_ALLOWLIST))
@pytest.mark.parametrize("lang", ["en", "sw"])
def test_fixed_parent_messages_gsm7_and_segments(msg_id, lang):
    body = M.parent_text(msg_id, lang, **SLOTS)
    assert gsm(body) == [], (msg_id, lang, gsm(body))
    assert segments(body) <= limit(msg_id, lang), (msg_id, lang, segments(body), len(body))


def test_question_texts_gsm7_one_segment():
    QL.load(PROTO.params, force=True)
    try:
        assert QL.is_on()
        for msg_id, variants in M.QL_TEMPLATES.items():
            for v in variants:
                assert gsm(v) == [], (msg_id, gsm(v))
                assert segments(v) == 1, (msg_id, len(v))
    finally:
        QL.load(PROTO.params)


def test_her_message_start_leaves_room_counted_correctly():
    QL.load(PROTO.params, force=True)
    try:
        longest = max((c["name"] for c in REG.chps.values()), key=len)
        for lang in ("en", "sw"):
            start = QL.STATE["bank"]["prefix_chw_referred"][lang] + " " + longest + ", your health worker: "
            assert gsm(start) == []
            room = 160 - len(start)
            assert segments(start + "x" * room) == 1 and segments(start + "x" * (room + 1)) == 2
            assert segments(start + "^" * (room // 2)) == 1 and segments(start + "^" * (room // 2 + 1)) == 2   # ext = 2
    finally:
        QL.load(PROTO.params)
