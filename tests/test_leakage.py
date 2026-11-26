"""Tests anti-fuite : une prédiction ne doit dépendre que de matchs strictement antérieurs.

Principe : on modifie les résultats FUTURS (après une date de coupure) et on vérifie que
toutes les prédictions antérieures restent identiques au bit près. Contrôle positif : modifier
le PASSÉ doit, lui, changer les prédictions futures (sinon le test ne prouverait rien).
"""
import numpy as np
import pandas as pd
import pytest

from backtest import run_all
from models import DixonColes, elo_probs, walk_forward_dc
from synth import make_synthetic


@pytest.fixture(scope="module")
def df():
    return make_synthetic(seasons=3, n_teams=12, seed=1)


def scramble_results(df, mask, seed=0):
    """Remplace les scores des lignes `mask` par des scores aléatoires (et FTR cohérent)."""
    out = df.copy()
    rng = np.random.default_rng(seed)
    n = int(mask.sum())
    out.loc[mask, "FTHG"] = rng.integers(0, 6, n)
    out.loc[mask, "FTAG"] = rng.integers(0, 6, n)
    out["FTR"] = np.where(out.FTHG > out.FTAG, "H", np.where(out.FTHG < out.FTAG, "A", "D"))
    return out


# ---------------------------------------------------------------- Elo
def test_elo_ignores_future_results(df):
    cut = df.Date.iloc[len(df) // 2]
    future = df.Date >= cut
    p0, _ = elo_probs(df)
    p1, _ = elo_probs(scramble_results(df, future))
    past = (~future).to_numpy()
    assert np.array_equal(p0[past], p1[past])
    # le premier jour « futur » est prédit avant que ses propres résultats ne soient connus
    first_day = (df.Date == cut).to_numpy()
    assert np.array_equal(p0[first_day], p1[first_day])


def test_elo_same_kickoff_matches_do_not_see_each_other():
    d = pd.DataFrame({"Date": pd.to_datetime(["2024-08-10"] * 2 + ["2024-08-17"]),
                      "Season": "2425", "HomeTeam": ["A", "C", "A"], "AwayTeam": ["B", "D", "C"],
                      "FTHG": [5, 0, 1], "FTAG": [0, 0, 1]})
    p0, _ = elo_probs(d)
    d2 = d.copy()
    d2.loc[0, ["FTHG", "FTAG"]] = [0, 5]  # change le match A-B joué au même moment que C-D
    p1, _ = elo_probs(d2)
    assert np.array_equal(p0[1], p1[1])  # C-D inchangé
    assert not np.allclose(p0[2], p1[2])  # contrôle positif : A-C (plus tard) change


def test_elo_rejects_unsorted_input(df):
    with pytest.raises(ValueError):
        elo_probs(df.iloc[::-1])


def test_elo_probs_are_valid(df):
    p, _ = elo_probs(df)
    assert np.allclose(p.sum(axis=1), 1) and (p > 0).all()


# ---------------------------------------------------------------- Dixon-Coles
def test_walk_forward_dc_ignores_future_results(df):
    test_from = df.Date.iloc[len(df) // 2]
    base = walk_forward_dc(df, test_from, refit_days=56, min_train=200)
    # on brouille tout ce qui suit la fin du 2e bloc
    cut = pd.Timestamp(test_from) + pd.Timedelta(days=112)
    alt = walk_forward_dc(scramble_results(df, df.Date >= cut), test_from,
                          refit_days=56, min_train=200)
    before = df.loc[base.index, "Date"] < cut
    assert before.sum() >= 10
    pd.testing.assert_frame_equal(base[before], alt.loc[base.index][before])
    # contrôle positif : les blocs après la coupure, eux, changent
    assert not np.allclose(base[~before].to_numpy(), alt.loc[base.index][~before].to_numpy())


def test_walk_forward_dc_trains_only_on_strict_past(df, monkeypatch):
    """Espionne chaque appel à fit : max(date d'entraînement) < min(date du bloc prédit)."""
    seen = []
    orig_fit, orig_pred = DixonColes.fit, DixonColes.predict

    def spy_fit(self, train, ref_date=None):
        seen.append(["fit", train.Date.max(), ref_date])
        return orig_fit(self, train, ref_date)

    def spy_pred(self, home, away):
        seen[-1].append(df.loc[home.index, "Date"].min())
        return orig_pred(self, home, away)

    monkeypatch.setattr(DixonColes, "fit", spy_fit)
    monkeypatch.setattr(DixonColes, "predict", spy_pred)
    walk_forward_dc(df, df.Date.iloc[len(df) // 2], refit_days=56, min_train=200)
    assert seen
    for _, train_max, ref, block_min in seen:
        assert train_max < block_min and train_max < ref <= block_min


def test_dixon_coles_probs_are_valid(df):
    m = DixonColes().fit(df)
    p = m.predict(df.HomeTeam[:50], df.AwayTeam[:50])
    assert np.allclose(p.sum(axis=1), 1) and (p > 0).all()
    unknown = m.predict(pd.Series(["Promu FC"]), pd.Series([df.HomeTeam.iloc[0]]))
    assert np.allclose(unknown.sum(axis=1), 1)


# ---------------------------------------------------------------- pipeline complet
def test_run_all_test_period_is_out_of_sample(df):
    test_from = df.Date.iloc[len(df) // 2]
    res = run_all(df, test_from, refit_days=56)
    t = res["test"]
    assert t.Date.min() >= pd.Timestamp(test_from)
    # la baseline « fréquences » est calculée sur l'entraînement seulement
    scr = run_all(scramble_results(df, df.Date >= test_from), test_from, refit_days=56)["test"]
    assert np.array_equal(t[["fH", "fD", "fA"]].to_numpy(), scr[["fH", "fD", "fA"]].to_numpy())
    # chaque modèle : probabilités valides sur toute la période de test
    for cols in (["pH", "pD", "pA"], ["eH", "eD", "eA"], ["dH", "dD", "dA"]):
        assert np.allclose(t[cols].sum(axis=1), 1)
