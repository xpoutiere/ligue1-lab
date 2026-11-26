"""Tests de l'import xG : correspondance des noms, parseurs, réconciliation."""
import json

import numpy as np
import pandas as pd
import pytest

import xg
from core import clean_matches

FD_TEAMS_SEEN = {  # noms football-data observés en 2019-20 à 2026-27 (contrôle du 26/11/2026)
    "Ajaccio", "Amiens", "Angers", "Auxerre", "Bordeaux", "Brest", "Clermont", "Dijon",
    "Le Havre", "Le Mans", "Lens", "Lille", "Lorient", "Lyon", "Marseille", "Metz", "Monaco",
    "Montpellier", "Nantes", "Nice", "Nimes", "Paris FC", "Paris SG", "Reims", "Rennes",
    "St Etienne", "Strasbourg", "Toulouse", "Troyes"}


def test_team_map_is_unique_and_covers_football_data():
    m = xg.load_team_map()
    assert FD_TEAMS_SEEN <= set(m["canonical"])
    assert m.notna().all().all()


def test_to_canonical_maps_and_rejects_unknown():
    s = xg.to_canonical(pd.Series(["Paris Saint Germain", "Saint-Etienne"]), "understat")
    assert list(s) == ["Paris SG", "St Etienne"]
    with pytest.raises(KeyError, match="Olympique"):
        xg.to_canonical(pd.Series(["Olympique Inconnu"]), "fbref")


def _understat_html(matches):
    payload = json.dumps(matches).replace("'", "\\'")
    escaped = "".join(f"\\x{ord(c):02x}" if c in '"{}:,' else c for c in payload)
    return f"<script>var datesData = JSON.parse('{escaped}');</script>"


def test_parse_understat_keeps_played_matches_only():
    html = _understat_html([
        {"isResult": True, "datetime": "2023-08-11 19:00:00", "h": {"title": "Nice"},
         "a": {"title": "Lille"}, "goals": {"h": "1", "a": "1"}, "xG": {"h": "1.23", "a": "0.8"}},
        {"isResult": False, "datetime": "2023-08-12 15:00:00", "h": {"title": "Lens"},
         "a": {"title": "Brest"}, "goals": {"h": None, "a": None}, "xG": {"h": None, "a": None}},
    ])
    d = xg.parse_understat_league(html)
    assert len(d) == 1
    assert d.iloc[0]["HxG"] == pytest.approx(1.23) and d.iloc[0]["home"] == "Nice"


def test_parse_understat_detects_maintenance_page():
    with pytest.raises(xg.SourceUnavailable, match="maintenance"):
        xg.parse_understat_league("<p>We will come back soon</p>")


def test_parse_fbref_export(tmp_path):
    p = tmp_path / "fbref_2324.csv"
    pd.DataFrame({"Wk": [1, 1], "Date": ["2023-08-11", "2023-08-12"],
                  "Home": ["Nice", "Paris S-G"], "xG": [1.2, np.nan], "Score": ["1–1", np.nan],
                  "xG.1": [0.8, np.nan], "Away": ["Lille", "Lorient"]}).to_csv(p, index=False)
    d = xg.parse_fbref_fixtures(p)
    assert len(d) == 1 and (d.iloc[0]["hg"], d.iloc[0]["ag"]) == (1, 1)


def _fd_matches():
    return clean_matches(pd.DataFrame({
        "Date": ["11/08/2023", "12/08/2023"], "Time": ["20:00", "17:00"],
        "HomeTeam": ["Nice", "Paris SG"], "AwayTeam": ["Lille", "Lorient"],
        "FTHG": [1, 0], "FTAG": [1, 0], "FTR": ["D", "D"], "Season": "2324"}))


def _xg_rows(**over):
    x = pd.DataFrame({"Season": "2324", "Date": pd.to_datetime(["2023-08-11"]),
                      "home": ["Nice"], "away": ["Lille"], "hg": [1], "ag": [1],
                      "HxG": [1.2], "AxG": [0.8], "xg_src": "understat"})
    for k, v in over.items():
        x[k] = v
    return x


def test_merge_xg_aligns_and_keeps_unmatched_as_nan():
    df = _fd_matches()
    out = xg.merge_xg(df, _xg_rows())
    assert out.index.equals(df.index) and len(out) == len(df)
    nice = out[out.HomeTeam == "Nice"].iloc[0]
    assert nice["HxG"] == pytest.approx(1.2)
    assert out[out.HomeTeam == "Paris SG"]["HxG"].isna().all()


def test_merge_xg_rejects_score_mismatch():
    with pytest.raises(ValueError, match="scores"):
        xg.merge_xg(_fd_matches(), _xg_rows(hg=[3]))


def test_merge_xg_rejects_far_dates():
    with pytest.raises(ValueError, match="dates"):
        xg.merge_xg(_fd_matches(), _xg_rows(Date=pd.to_datetime(["2023-12-01"])))


def test_merge_xg_with_no_source_available():
    out = xg.merge_xg(_fd_matches(), xg.load_xg([], verbose=False))
    assert out["HxG"].isna().all()


def test_load_xg_falls_back_to_fbref(tmp_path, monkeypatch):
    monkeypatch.setattr(xg, "XG_DIR", tmp_path)

    def down(code):
        raise xg.SourceUnavailable("maintenance")

    monkeypatch.setattr(xg, "fetch_understat", down)
    pd.DataFrame({"Date": ["2023-08-11"], "Home": ["Nice"], "xG": [1.2], "Score": ["1–1"],
                  "xG.1": [0.8], "Away": ["Lille"]}).to_csv(tmp_path / "fbref_2324.csv",
                                                           index=False)
    x = xg.load_xg(["2324"], verbose=False)
    assert list(x["xg_src"]) == ["fbref"]
