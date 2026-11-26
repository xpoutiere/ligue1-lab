"""Tests de la simulation de stratégie (aucune mise réelle : calcul a posteriori)."""
import numpy as np
import pandas as pd
import pytest

from ligue1lab import strategy as S


def _frame(n=600, seed=0, model_noise=0.0, margin=0.05):
    rng = np.random.default_rng(seed)
    p = rng.dirichlet([3, 2, 2.5], n)
    y = np.array([rng.choice(3, p=r) for r in p])
    t = pd.DataFrame({"Date": pd.date_range("2024-08-01", periods=n, freq="D"),
                      "HomeTeam": "A", "AwayTeam": "B",
                      "FTR": np.array(["H", "D", "A"])[y]})
    q = p * np.exp(rng.normal(0, model_noise, p.shape)) if model_noise else p
    q /= q.sum(1, keepdims=True)
    t[["M|H", "M|D", "M|A"]] = q
    t[["PSCH", "PSCD", "PSCA"]] = 1 / (p * 1.02)
    t[["B365H", "B365D", "B365A"]] = 1 / (p * (1 + margin))
    return t


def test_stakes_respect_cap_and_edge():
    t = _frame(model_noise=0.4)
    log = S.simulate(t, "M", edge=0.05, cap=0.02)
    assert len(log) > 0 and (log.ev > 0.05).all()
    prev = np.r_[100.0, log.bankroll.to_numpy()[:-1]]
    assert (log.mise <= 0.02 * prev + 1e-9).all()


def test_clv_equals_minus_margin_when_execution_is_closing_plus_margin():
    t = _frame(model_noise=0.4, margin=0.05)
    log = S.simulate(t, "M", edge=0.0)
    assert np.allclose(log.clv, 1 / 1.05 - 1)  # cote = 1/(p*1.05), clôture juste = p


def test_true_model_without_margin_has_zero_clv_and_no_bets_with_margin():
    t = _frame(margin=0.05)
    assert S.simulate(t, "M", edge=0.0).empty  # vraie proba + marge : jamais d'EV > 0


def test_choose_edge_uses_only_given_data_and_min_bets():
    t = _frame(model_noise=0.4)
    edge, table = S.choose_edge(t, "M")
    assert edge in S.EDGE_GRID and len(table) == len(S.EDGE_GRID)
    chosen = next(r for r in table if r["edge"] == edge)
    assert chosen["paris"] >= S.MIN_BETS


def test_monte_carlo_null_world_loses_on_average():
    t = _frame(model_noise=0.4, margin=0.05)
    log = S.simulate(t, "M", edge=0.0)
    mc = S.monte_carlo(log, n_paths=500, null_probs=True)
    assert mc["bankroll_finale_q"]["q50"] < 100  # sans avantage, la marge fait perdre
    assert 0 <= mc["p_ruine_%"] <= 100 and len(mc["bands"]["q50"]) == len(mc["bands"]["i"])


def test_margin_sensitivity_is_monotone_in_bet_count():
    t = _frame(model_noise=0.4)
    rows = S.margin_sensitivity(t, "M", 0.02, margins=np.array([0.0, 0.05, 0.10]))
    counts = [r["paris"] for r in rows]
    assert counts == sorted(counts, reverse=True)
    assert rows[0]["marge_%"] == pytest.approx(0.0)
