"""Tests de la simulation de paris et de l'évaluation."""
import numpy as np
import pandas as pd

from backtest import COLS, evaluate, value_bets


def _toy(n=400, seed=0):
    rng = np.random.default_rng(seed)
    p = rng.dirichlet([3, 2, 2.5], n)
    res = np.array([rng.choice(3, p=r) for r in p])
    t = pd.DataFrame(p, columns=["mH", "mD", "mA"])
    t["Date"] = pd.date_range("2024-01-01", periods=n, freq="D")
    t["FTR"] = np.array(["H", "D", "A"])[res]
    odds = 1 / (p * 1.05)
    t[["oH", "oD", "oA"]] = odds
    return t


def test_value_bets_respects_edge_and_stake_cap():
    t = _toy()
    t[["mH", "mD", "mA"]] = np.random.default_rng(1).dirichlet([2, 2, 2], len(t))
    log, s = value_bets(t, ["mH", "mD", "mA"], ["oH", "oD", "oA"], edge=0.05, max_frac=0.03)
    assert s["paris"] == len(log) > 0
    assert (log["ev"] > 0.05).all()
    bank_before = np.r_[100.0, log["bankroll"].to_numpy()[:-1]]
    assert (log["mise"] <= 0.03 * bank_before + 1e-9).all()


def test_value_bets_no_bet_when_model_equals_fair_market():
    """Avec la vraie proba et 5 % de marge, aucun EV n'est positif : zéro pari."""
    t = _toy()
    _, s = value_bets(t, ["mH", "mD", "mA"], ["oH", "oD", "oA"], edge=0.0)
    assert s == {"paris": 0}


def test_evaluate_market_delta_is_zero_and_ci_ordered():
    t = _toy()
    for c in COLS.values():
        t[c] = t[["mH", "mD", "mA"]].to_numpy()
    t[COLS["Fréquences"]] = 1 / 3
    m = evaluate(t, n_boot=300).set_index("modèle")
    assert m.loc["Marché", "delta_vs_marché"] == 0
    assert (m["ll_ic95_bas"] <= m["log_loss"]).all() and (m["log_loss"] <= m["ll_ic95_haut"]).all()
    assert m.loc["Fréquences", "delta_ic95_bas"] > 0  # proba uniforme : nettement pire
