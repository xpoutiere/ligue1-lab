"""Prédictions de la prochaine journée et journal de paper trading (aucune mise réelle).

- Matchs à venir : fichier public `fixtures.csv` de football-data.co.uk (mis à jour par le
  site quelques jours avant chaque journée, avec les cotes du moment).
- Modèle affiché : Dixon-Coles ajusté sur tout l'historique (et Elo en complément).
- Journal : `data/paper_trading/predictions.csv` (VERSIONNÉ dans git). Chaque prédiction est
  horodatée AVANT le match et n'est jamais réécrite : seul le résultat est ajouté ensuite.
  L'historique git sert de preuve d'antériorité.

Lancer chaque semaine : python -m ligue1lab.predict
"""
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from .core import DATA_DIR, load_data, remove_margin
from .models import DixonColes, elo_probs

FIXTURES_URL = "https://www.football-data.co.uk/fixtures.csv"
JOURNAL = DATA_DIR / "paper_trading" / "predictions.csv"
JOURNAL_COLS = ["predicted_at", "Date", "Time", "HomeTeam", "AwayTeam", "model",
                "m_H", "m_D", "m_A", "mkt_H", "mkt_D", "mkt_A", "mkt_source",
                "odds_H", "odds_D", "odds_A", "FTHG", "FTAG", "FTR"]


def fetch_fixtures(path=None) -> pd.DataFrame:
    """Matchs de Ligue 1 à venir (vide si la journée n'est pas encore publiée)."""
    src = path or FIXTURES_URL
    try:
        f = pd.read_csv(src, encoding="utf-8-sig")
    except Exception as e:  # réseau
        print(f"[fixtures] indisponible : {e}")
        return pd.DataFrame()
    f = f[f["Div"] == "F1"].copy()
    if f.empty:
        return f
    f["Date"] = pd.to_datetime(f["Date"], dayfirst=True)
    for c in ("HomeTeam", "AwayTeam"):
        f[c] = f[c].astype(str).str.strip()
    return f.sort_values(["Date", "Time"]).reset_index(drop=True)


def market_probs(f):
    """Probas sans marge à partir de la moyenne du marché (Avg), sinon Bet365."""
    for pre in ("Avg", "B365"):
        cols = [f"{pre}{o}" for o in "HDA"]
        if all(c in f for c in cols) and f[cols].notna().all().all():
            return remove_margin(f[cols].to_numpy(float)), pre, f[cols].to_numpy(float)
    return np.full((len(f), 3), np.nan), None, np.full((len(f), 3), np.nan)


def predict_fixtures(hist: pd.DataFrame, fixtures: pd.DataFrame) -> pd.DataFrame:
    if fixtures.empty:
        return pd.DataFrame(columns=JOURNAL_COLS)
    dc = DixonColes().fit(hist, ref_date=fixtures["Date"].min())
    p_dc = dc.predict(fixtures.HomeTeam, fixtures.AwayTeam)
    _, ratings = elo_probs(hist)
    mk, src, odds = market_probs(fixtures)
    out = pd.DataFrame({
        "predicted_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Date": fixtures.Date.dt.strftime("%Y-%m-%d"), "Time": fixtures.get("Time", ""),
        "HomeTeam": fixtures.HomeTeam, "AwayTeam": fixtures.AwayTeam, "model": "Dixon-Coles",
        "m_H": p_dc[:, 0], "m_D": p_dc[:, 1], "m_A": p_dc[:, 2],
        "mkt_H": mk[:, 0], "mkt_D": mk[:, 1], "mkt_A": mk[:, 2], "mkt_source": src,
        "odds_H": odds[:, 0], "odds_D": odds[:, 1], "odds_A": odds[:, 2],
        "FTHG": np.nan, "FTAG": np.nan, "FTR": None})
    out["elo_H"] = out.HomeTeam.map(ratings)
    out["elo_A"] = out.AwayTeam.map(ratings)
    return out


def append_journal(pred: pd.DataFrame, journal=JOURNAL) -> int:
    """Ajoute les nouvelles prédictions ; un match déjà journalisé n'est JAMAIS réécrit."""
    journal.parent.mkdir(parents=True, exist_ok=True)
    old = pd.read_csv(journal) if journal.exists() else pd.DataFrame(columns=JOURNAL_COLS)
    key = ["Date", "HomeTeam", "AwayTeam"]
    seen = set(map(tuple, old[key].astype(str).to_numpy())) if len(old) else set()
    new = pred[[tuple(r) not in seen for r in pred[key].astype(str).to_numpy()]]
    if len(new):
        pd.concat([old, new[JOURNAL_COLS]], ignore_index=True).to_csv(journal, index=False)
    return len(new)


def settle_journal(hist: pd.DataFrame, journal=JOURNAL) -> int:
    """Renseigne le score des matchs journalisés désormais joués (seules colonnes modifiées)."""
    if not journal.exists():
        return 0
    j = pd.read_csv(journal)
    j["FTR"] = j["FTR"].astype(object)
    res = hist.assign(Date=hist.Date.dt.strftime("%Y-%m-%d")).set_index(
        ["Date", "HomeTeam", "AwayTeam"])[["FTHG", "FTAG", "FTR"]]
    n = 0
    for i, r in j[j.FTR.isna()].iterrows():
        k = (r.Date, r.HomeTeam, r.AwayTeam)
        if k in res.index:
            j.loc[i, ["FTHG", "FTAG", "FTR"]] = res.loc[k].to_numpy()
            n += 1
    if n:
        j.to_csv(journal, index=False)
    return n


def run():
    hist = load_data(refresh=False)
    settled = settle_journal(hist)
    fx = fetch_fixtures()
    pred = predict_fixtures(hist, fx)
    added = append_journal(pred) if len(pred) else 0
    print(f"{len(fx)} matchs à venir | {added} prédictions ajoutées | {settled} résultats saisis")
    return pred


if __name__ == "__main__":
    run()
