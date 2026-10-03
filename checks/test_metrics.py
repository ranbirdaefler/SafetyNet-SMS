"""Metric code reproduces the pre-registered Clopper-Pearson bounds and exact McNemar values (prereg section 8)."""
from app.metrics import cp, mcnemar_exact


def test_cp_upper_bounds_match_prereg():
    assert [cp(k, n)[1] for k, n in [(0, 11), (1, 11), (2, 11), (0, 12), (0, 80), (0, 10), (1, 10), (2, 10)]] == \
        [28.5, 41.3, 51.8, 26.5, 4.5, 30.8, 44.5, 55.6]


def test_mcnemar_win_thresholds_match_prereg():
    assert mcnemar_exact(6, 0) < 0.05 and mcnemar_exact(8, 1) < 0.05 and mcnemar_exact(9, 1) < 0.05
    assert mcnemar_exact(5, 0) >= 0.05 and mcnemar_exact(7, 1) >= 0.05
