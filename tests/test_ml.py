"""Tests des briques ML : découpage temporel, calibration, combinaison, tests statistiques."""
import numpy as np
import pandas as pd
import pytest

from ligue1lab import ml


def test_split_is_temporal_and_disjoint():
    seasons = ["1920", "2021", "2122", "2223", "2324", "2425", "2526"]
    d = pd.DataFrame({"Season": np.repeat(seasons, 3),
                      "Date": pd.date_range("2019-08-01", periods=21, freq="120D")})
    sp = ml.split(d[~d.Season.isin(ml.BURN_IN)])
    assert sp["train"].Date.max() < sp["valid"].Date.min() < sp["test"].Date.min()
    assert sp["test_seasons"] == ["2425", "2526"]
    for tr, va in ml.CV_FOLDS:  # chaque pli valide sur une saison postérieure
        assert max(tr) < min(va)
    assert not set(sp["test_seasons"]) & set(sum((tr + va for tr, va in ml.CV_FOLDS), []))


@pytest.mark.parametrize("method", ["platt", "isotonic"])
def test_calibrator_outputs_probabilities_and_fixes_overconfidence(method):
    rng = np.random.default_rng(0)
    true = rng.dirichlet([3, 2, 2.5], 6000)
    y = np.array([rng.choice(3, p=r) for r in true])
    over = np.exp(2.0 * np.log(true))  # sur-confiant
    over /= over.sum(1, keepdims=True)
    cal = ml.Calibrator(method).fit(over[:4000], y[:4000])
    q = cal.transform(over[4000:])
    assert np.allclose(q.sum(1), 1) and (q > 0).all()
    assert ml.mean_ll(q, y[4000:]) < ml.mean_ll(over[4000:], y[4000:])


def _true_vs_noisy(n=4000, seed=1):
    rng = np.random.default_rng(seed)
    true = rng.dirichlet([3, 2, 2.5], n)
    y = np.array([rng.choice(3, p=r) for r in true])
    noisy = true * np.exp(rng.normal(0, 0.5, true.shape))
    return true, noisy / noisy.sum(1, keepdims=True), y


def test_encompassing_detects_information_and_its_absence():
    true, noisy, y = _true_vs_noisy()
    # « marché » bruité, « modèle » = vraies probas : le modèle apporte de l'information
    e = ml.encompassing_test(noisy, true, y, n_boot=50)
    assert e["b_modele"] > 0.3 and e["p_value"] < 0.001
    # modèle = bruit pur indépendant : aucune information au-delà du marché vrai
    rng = np.random.default_rng(5)
    junk = rng.dirichlet([1, 1, 1], len(y))
    e2 = ml.encompassing_test(true, junk, y, n_boot=50)
    assert e2["p_value"] > 0.01


def test_log_pool_puts_weight_on_informative_forecast():
    true, noisy, y = _true_vs_noisy()
    w, _ = ml.fit_log_pool([noisy, true], y)
    assert w[1] > w[0]
    p = ml.apply_log_pool(w, [noisy, true])
    assert np.allclose(p.sum(1), 1)


def test_holm_matches_definition():
    adj = ml.holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adj["a"] == pytest.approx(0.03)
    assert adj["c"] == pytest.approx(0.06)
    assert adj["b"] == pytest.approx(0.06)  # monotonie imposée


def test_bootstrap_p_better():
    rng = np.random.default_rng(0)
    base = rng.normal(1.0, 0.3, 2000)
    assert ml.bootstrap_p_better(base - 0.05, base) < 0.01   # nettement meilleur
    assert ml.bootstrap_p_better(base + 0.05, base) > 0.99   # nettement pire
