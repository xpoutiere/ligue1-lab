"""Tests anti-fuite et de cohérence de build_features."""
import numpy as np
import pandas as pd
import pytest

from ligue1lab.features import build_features, table_features
from ligue1lab.synth import make_synthetic
from test_leakage import scramble_results


@pytest.fixture(scope="module")
def df():
    d = make_synthetic(seasons=3, n_teams=12, seed=3)
    rng = np.random.default_rng(0)  # tirs factices pour couvrir les colonnes HS/HST
    d["HS"] = d.FTHG * 3 + rng.integers(2, 10, len(d))
    d["AS"] = d.FTAG * 3 + rng.integers(2, 10, len(d))
    d["HST"], d["AST"] = d.FTHG + rng.integers(0, 4, len(d)), d.FTAG + rng.integers(0, 4, len(d))
    return d


@pytest.fixture(scope="module")
def feats(df):
    return build_features(df, dc_refit_days=56)


def _scramble_all(df, mask, seed=0):
    out = scramble_results(df, mask, seed)
    rng = np.random.default_rng(seed + 1)
    for c in ("HS", "AS", "HST", "AST"):
        out.loc[mask, c] = rng.integers(0, 25, int(mask.sum()))
    return out


def test_features_aligned_on_matches(df, feats):
    assert feats.index.equals(df.index)
    assert {"h_g_for_m5", "a_st_against_ewm5", "diff_elo", "h_rank", "h_sos5",
            "h_rest_days", "h_pts_venue5", "dH"} <= set(feats.columns)


def test_modifying_future_results_never_changes_past_features(df, feats):
    """Cœur du test : on brouille scores ET tirs après la coupure ; toutes les features des
    matchs d'avant (et de la coupure elle-même) doivent rester identiques au bit près."""
    cut = df.Date.iloc[int(len(df) * 0.6)]
    future = df.Date > cut
    alt = build_features(_scramble_all(df, future), dc_refit_days=56)
    past = ~future
    pd.testing.assert_frame_equal(feats[past], alt[past])
    # contrôle positif : des features futures changent bien
    later = future & (df.Date > cut + pd.Timedelta(days=60))
    assert not feats.loc[later, "h_g_for_m5"].equals(alt.loc[later, "h_g_for_m5"])


def test_own_result_is_not_used(df, feats):
    """Changer le score d'UN match ne change aucune de ses propres features."""
    k = len(df) // 2
    alt_df = df.copy()
    alt_df.loc[alt_df.index[k], ["FTHG", "FTAG", "HS", "AS", "HST", "AST"]] = [9, 0, 40, 0, 20, 0]
    alt_df["FTR"] = np.where(alt_df.FTHG > alt_df.FTAG, "H",
                             np.where(alt_df.FTHG < alt_df.FTAG, "A", "D"))
    alt = build_features(alt_df, dc_refit_days=56)
    same_time = df.Date == df.Date.iloc[k]
    pd.testing.assert_frame_equal(feats[same_time], alt[same_time])


def test_rolling_values_by_hand():
    d = pd.DataFrame({
        "Date": pd.to_datetime(["2024-08-01", "2024-08-08", "2024-08-15", "2024-08-22"]),
        "Season": "2425", "HomeTeam": ["A", "B", "A", "C"], "AwayTeam": ["B", "A", "C", "A"],
        "FTHG": [2, 1, 4, 0], "FTAG": [0, 1, 0, 3]})
    d["FTR"] = np.where(d.FTHG > d.FTAG, "H", np.where(d.FTHG < d.FTAG, "A", "D"))
    f = build_features(d, include_dc=False, windows=(2,))
    # 1er match de A : aucun historique
    assert np.isnan(f.loc[0, "h_g_for_m2"])
    # 4e match (A à l'extérieur) : A a marqué 1 puis 4 lors de ses 2 derniers matchs
    assert f.loc[3, "a_g_for_m2"] == pytest.approx(2.5)
    assert f.loc[3, "a_pts_m2"] == pytest.approx(2.0)  # nul (1) puis victoire (3)
    assert f.loc[3, "a_rest_days"] == pytest.approx(7)
    # forme à l'extérieur de A : un seul match à l'extérieur avant (1 but)
    assert f.loc[3, "a_g_for_venue5"] == pytest.approx(1.0)


def test_table_before_match():
    d = pd.DataFrame({
        "Date": pd.to_datetime(["2024-08-01", "2024-08-01", "2024-08-08"]),
        "Season": "2425", "HomeTeam": ["A", "C", "A"], "AwayTeam": ["B", "D", "C"],
        "FTHG": [3, 1, 0], "FTAG": [0, 0, 0]})
    t = table_features(d)
    assert (t.loc[[0, 1], ["h_rank", "a_rank"]].notna()).all().all()
    assert t.loc[0, "h_played"] == 0  # même créneau : personne n'a encore joué
    assert t.loc[2, "h_rank"] == 1 and t.loc[2, "h_ppg"] == 3  # A a battu B 3-0
    assert t.loc[2, "a_rank"] == 2  # C : victoire 1-0, moins bonne différence


def test_rejects_unsorted(df):
    with pytest.raises(ValueError):
        build_features(df.iloc[::-1], include_dc=False)
