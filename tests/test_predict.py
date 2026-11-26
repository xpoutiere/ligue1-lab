"""Le journal de paper trading n'écrase jamais une prédiction déjà enregistrée."""
import numpy as np
import pandas as pd

from ligue1lab import predict as P


def _pred(p_home, when="2026-11-28T10:00:00Z"):
    row = dict.fromkeys(P.JOURNAL_COLS, np.nan)
    row.update({"predicted_at": when, "Date": "2026-11-29", "Time": "17:00",
                "HomeTeam": "Lens", "AwayTeam": "Lille", "model": "Dixon-Coles",
                "m_H": p_home, "m_D": 0.3, "m_A": 0.7 - p_home, "FTR": None})
    return pd.DataFrame([row])


def test_journal_is_append_only_and_settles_results(tmp_path):
    j = tmp_path / "predictions.csv"
    assert P.append_journal(_pred(0.45), j) == 1
    assert P.append_journal(_pred(0.60, "2026-11-29T16:00:00Z"), j) == 0  # pas de réécriture
    saved = pd.read_csv(j)
    assert len(saved) == 1 and saved.m_H.iloc[0] == 0.45
    hist = pd.DataFrame({"Date": pd.to_datetime(["2026-11-29"]), "HomeTeam": ["Lens"],
                         "AwayTeam": ["Lille"], "FTHG": [2], "FTAG": [1], "FTR": ["H"]})
    assert P.settle_journal(hist, j) == 1
    saved = pd.read_csv(j)
    assert saved.FTR.iloc[0] == "H" and saved.m_H.iloc[0] == 0.45
    assert saved.predicted_at.iloc[0] == "2026-11-28T10:00:00Z"


def test_fetch_fixtures_filters_ligue1(tmp_path):
    f = tmp_path / "fixtures.csv"
    f.write_text("﻿Div,Date,Time,HomeTeam,AwayTeam,B365H,B365D,B365A\n"
                 "E1,28/11/2026,15:00,Leeds,Hull,2,3,4\n"
                 "F1,29/11/2026,17:00,Lens,Lille,2.1,3.3,3.6\n", encoding="utf-8")
    fx = P.fetch_fixtures(f)
    assert fx.HomeTeam.tolist() == ["Lens"]
    p, src, _ = P.market_probs(fx)
    assert src == "B365" and np.isclose(p.sum(), 1)
