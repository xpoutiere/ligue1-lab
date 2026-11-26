"""Tests de l'analyse des biais : séries point-in-time, corrections multiples, bootstrap."""
import numpy as np
import pandas as pd
import pytest

from ligue1lab import biases as B


def test_streaks_use_only_previous_matches():
    d = pd.DataFrame({"Date": pd.date_range("2024-08-01", periods=4, freq="7D"),
                      "HomeTeam": ["A", "A", "A", "A"], "AwayTeam": ["B", "C", "D", "E"],
                      "FTHG": [1, 2, 3, 0], "FTAG": [0, 0, 0, 1]})
    s = B.streaks(d)
    a = s[s.team == "A"].sort_values("match")
    assert a.win_streak.tolist() == [0, 1, 2, 3]  # avant chaque match
    assert a.loss_streak.tolist() == [0, 0, 0, 0]


def test_bh_and_boot():
    adj = B.bh({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adj["a"] == pytest.approx(0.03) and adj["b"] == pytest.approx(0.04)
    assert adj["c"] == pytest.approx(0.04)
    r = B.boot(np.r_[np.ones(50), -np.ones(50)])
    assert r["ic95"][0] < 0 < r["ic95"][1] and r["p"] > 0.5
    assert B.boot(np.ones(30) + 0.01 * np.arange(30))["p"] < 0.01


def test_residual_is_zero_on_average_for_a_calibrated_market():
    rng = np.random.default_rng(0)
    n = 4000
    p = rng.dirichlet([3, 2, 2.5], n)
    y = np.array([rng.choice(3, p=r) for r in p])
    d = pd.DataFrame({"Season": "2425", "HomeTeam": "A", "AwayTeam": "B",
                      "FTR": np.array(["H", "D", "A"])[y], "mkt_src": "PSC"})
    d[["PSCH", "PSCD", "PSCA"]] = 1 / (p * 1.025)
    d[["B365H", "B365D", "B365A"]] = 1 / (p * 1.055)
    b = B.bets_long(d)
    assert abs(b.resid.mean()) < 0.01
    assert b.roi_b365.mean() < b.roi_close.mean()  # la marge Bet365 coûte plus cher
