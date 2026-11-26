"""Tests du socle : suppression de marge, métriques, choix des cotes, nettoyage."""
import numpy as np
import pandas as pd
import pytest

import core
from core import (
    bootstrap_ci,
    brier,
    calibration_table,
    clean_matches,
    log_loss,
    market_baseline,
    market_odds,
    outcome_matrix,
    overround,
    remove_margin,
)

RNG = np.random.default_rng(42)


def random_odds(n=500, margin=0.05):
    p = RNG.dirichlet([3, 2, 2.5], n)
    return 1.0 / (p * (1 + margin)), p


# ---------------------------------------------------------------- marge
def test_remove_margin_sums_to_one_and_positive():
    odds, _ = random_odds()
    p = remove_margin(odds)
    assert np.allclose(p.sum(axis=1), 1.0)
    assert (p > 0).all() and (p < 1).all()


def test_remove_margin_recovers_true_probs_for_proportional_margin():
    odds, p_true = random_odds(margin=0.07)
    assert np.allclose(remove_margin(odds), p_true)


def test_remove_margin_keeps_order_of_outcomes():
    odds = np.array([[1.5, 4.0, 6.0]])
    p = remove_margin(odds)[0]
    assert p[0] > p[1] > p[2]


def test_overround_known_value():
    assert overround(np.array([[2.0, 2.0, np.inf]]))[0] == pytest.approx(0.0)
    odds, _ = random_odds(margin=0.05)
    assert np.allclose(overround(odds), 0.05)


# ---------------------------------------------------------------- métriques
def test_log_loss_reference_values():
    y = outcome_matrix(pd.Series(["H", "D", "A", "H"]))
    assert log_loss(y, y) == pytest.approx(0.0, abs=1e-9)
    assert log_loss(np.full((4, 3), 1 / 3), y) == pytest.approx(np.log(3))
    # une proba nulle sur l'issue réalisée est bornée (pas d'infini)
    assert np.isfinite(log_loss(np.array([[0.0, 0.0, 1.0]]), y[:1]))


def test_brier_reference_values():
    y = outcome_matrix(pd.Series(["H", "D", "A"]))
    assert brier(y, y) == pytest.approx(0.0)
    assert brier(np.full((3, 3), 1 / 3), y) == pytest.approx(2 / 3)
    assert brier(y[:, ::-1], y) == pytest.approx((2 + 0 + 2) / 3)


def test_outcome_matrix_one_hot():
    y = outcome_matrix(pd.Series(["H", "D", "A"]))
    assert np.array_equal(y, np.eye(3))


def test_calibration_perfect_forecaster_is_on_diagonal():
    p = RNG.dirichlet([2, 2, 2], 20000)
    draws = np.array([RNG.choice(3, p=row) for row in p])
    y = np.eye(3)[draws]
    cal = calibration_table(p, y)
    assert cal["n"].sum() == p.size
    big = cal[cal["n"] > 500]
    assert np.allclose(big["predite"], big["observee"], atol=0.02)


def test_bootstrap_ci_contains_mean_and_shrinks_with_n():
    v_small, v_big = RNG.normal(1, 1, 100), RNG.normal(1, 1, 10000)
    lo, hi = bootstrap_ci(v_small)
    assert lo < v_small.mean() < hi
    lo2, hi2 = bootstrap_ci(v_big)
    assert (hi2 - lo2) < (hi - lo)


# ---------------------------------------------------------------- vraies données
def _raw_matches():
    return pd.DataFrame({
        "Date": ["09/08/2025", "09/08/2025", "16/08/2025", "17/08/2025", "23/08/2025"],
        "Time": ["19:00", "21:00", "17:00", None, "15:00"],
        "HomeTeam": ["Lyon ", "Paris SG", "Lens", "Nice", "Brest"],
        "AwayTeam": ["Lens", "Nice", "Brest", "Lyon", None],  # dernière ligne : à jeter
        "FTHG": [2, 1, 0, 1, 3], "FTAG": [0, 1, 1, 3, 0], "FTR": ["H", "D", "A", "A", "H"],
        "PSCH": [2.0, 1.3, np.nan, np.nan, 2.0], "PSCD": [3.5, 5.5, np.nan, np.nan, 3.4],
        "PSCA": [3.8, 9.0, np.nan, np.nan, 3.6],
        "B365CH": [1.95, 1.28, 2.6, np.nan, 2.0], "B365CD": [3.4, 5.25, 3.2, np.nan, 3.4],
        "B365CA": [3.7, 8.5, 2.7, np.nan, 3.6],
        "Season": "2526",
    })


def test_clean_matches_drops_incomplete_and_strips_names():
    d = clean_matches(_raw_matches())
    assert len(d) == 4
    assert "Lyon" in set(d.HomeTeam) and "Lyon " not in set(d.HomeTeam)
    assert d["Kickoff"].is_monotonic_increasing


def test_clean_matches_rejects_inconsistent_result():
    raw = _raw_matches()
    raw.loc[0, "FTR"] = "A"
    with pytest.raises(ValueError):
        clean_matches(raw)


def test_market_odds_falls_back_row_by_row():
    d = clean_matches(_raw_matches())
    odds, src = market_odds(d)
    assert list(src.fillna("none")) == ["PSC", "PSC", "B365C", "none"]
    assert np.isnan(odds[3]).all()


def test_market_baseline_keeps_matches_without_pinnacle():
    """Régression : avant, toute la saison 2026-27 (sans Pinnacle) était jetée en silence."""
    d, table, prefix, _ = market_baseline(clean_matches(_raw_matches()))
    assert len(d) == 3
    assert set(d["mkt_src"]) == {"PSC", "B365C"}
    assert np.allclose(d[["pH", "pD", "pA"]].sum(axis=1), 1.0)


def test_load_data_offline_with_heterogeneous_seasons(tmp_path, monkeypatch):
    """Deux saisons aux colonnes différentes (Pinnacle absent dans la 2e), lues depuis le cache."""
    monkeypatch.setattr(core, "DATA_DIR", tmp_path)
    monkeypatch.setattr(core, "CURRENT_SEASON_MAX_AGE_H", 1e9)
    raw = _raw_matches().drop(columns="Season")
    raw.to_csv(tmp_path / "F1_2526.csv", index=False)
    raw2 = raw.drop(columns=["PSCH", "PSCD", "PSCA"])
    raw2["Date"] = raw2["Date"].str.replace("2025", "2026")
    raw2.to_csv(tmp_path / "F1_2627.csv", index=False)
    df = core.load_data(["2526", "2627"])
    assert set(df.Season) == {"2526", "2627"}
    d, *_ = market_baseline(df)
    assert (d[d.Season == "2627"]["mkt_src"] == "B365C").all()
