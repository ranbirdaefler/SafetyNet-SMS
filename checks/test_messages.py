from app import messages as M


def segments(s):
    return 1 if len(s) <= 160 else -(-len(s) // 153)


def test_ask_signs_fits_3_segments():
    s = M.ask_signs("5307", 59, 21)
    assert segments(s) <= 3, len(s)
