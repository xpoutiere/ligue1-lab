"""Socle du projet : données Ligue 1 + baseline du marché."""
from pathlib import Path
import numpy as np
import pandas as pd

DATA_DIR = Path("data")
URL = "https://www.football-data.co.uk/mmz4281/{code}/F1.csv"
OUTCOMES = ["H", "D", "A"]


def season_codes(start=2019, end=2026):
    """2019 -> '1920' ... 2026 -> '2627'."""
    return [f"{y % 100:02d}{(y + 1) % 100:02d}" for y in range(start, end + 1)]


def load_data(codes=None, refresh=False) -> pd.DataFrame:
    """Télécharge (et met en cache) les CSV de football-data.co.uk."""
    DATA_DIR.mkdir(exist_ok=True)
    frames = []
    for code in codes or season_codes():
        path = DATA_DIR / f"F1_{code}.csv"
        try:
            if refresh or not path.exists():
                pd.read_csv(URL.format(code=code), encoding="latin-1").to_csv(path, index=False)
            df = pd.read_csv(path)
        except Exception as e:  # saison absente / réseau
            print(f"[skip] {code}: {e}")
            continue
        df["Season"] = code
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Date", "FTR"]).sort_values("Date").reset_index(drop=True)
    return df


def pick_odds(df, prefixes=("PSC", "PS", "B365")):
    """Choisit le 1er jeu de cotes (H/D/A) complet. PSC = Pinnacle à la clôture."""
    for p in prefixes:
        cols = [f"{p}H", f"{p}D", f"{p}A"]
        if all(c in df.columns for c in cols):
            sub = df[cols].dropna()
            if len(sub) > 0.5 * len(df):
                return cols, p
    raise ValueError("Aucune colonne de cotes exploitable")


def remove_margin(odds: np.ndarray) -> np.ndarray:
    """Cotes décimales -> probabilités sans marge (normalisation proportionnelle)."""
    inv = 1.0 / odds
    return inv / inv.sum(axis=1, keepdims=True)


def overround(odds: np.ndarray) -> np.ndarray:
    """Marge du bookmaker : somme des probas implicites - 1."""
    return (1.0 / odds).sum(axis=1) - 1


def outcome_matrix(ftr: pd.Series) -> np.ndarray:
    return np.column_stack([(ftr == o).to_numpy() for o in OUTCOMES]).astype(float)


def log_loss(p, y, eps=1e-12):
    return float(-np.mean(np.sum(y * np.log(np.clip(p, eps, 1)), axis=1)))


def brier(p, y):
    return float(np.mean(np.sum((p - y) ** 2, axis=1)))


def calibration_table(p, y, bins=10):
    """Probabilité prédite vs fréquence observée, toutes issues confondues."""
    pf, yf = p.ravel(), y.ravel()
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(pf, edges) - 1, 0, bins - 1)
    rows = [(pf[idx == b].mean(), yf[idx == b].mean(), int((idx == b).sum()))
            for b in range(bins) if (idx == b).any()]
    return pd.DataFrame(rows, columns=["predite", "observee", "n"])


def market_baseline(df):
    """Probas du marché sans marge + métriques par saison."""
    cols, prefix = pick_odds(df)
    d = df.dropna(subset=cols).copy()
    odds = d[cols].to_numpy(float)
    p, y = remove_margin(odds), outcome_matrix(d["FTR"])
    d[["pH", "pD", "pA"]] = p
    d["margin"] = overround(odds)
    per_season = pd.DataFrame(
        [{"Season": s, "matchs": len(g),
          "log_loss": log_loss(g[["pH", "pD", "pA"]].to_numpy(), outcome_matrix(g["FTR"])),
          "brier": brier(g[["pH", "pD", "pA"]].to_numpy(), outcome_matrix(g["FTR"])),
          "marge_moy_%": 100 * g["margin"].mean()}
         for s, g in d.groupby("Season")])
    return d, per_season, prefix, calibration_table(p, y)


if __name__ == "__main__":
    data = load_data()
    d, table, prefix, calib = market_baseline(data)
    print(f"Cotes utilisées : {prefix}  |  {len(d)} matchs")
    print(table.round(4).to_string(index=False))
    print("\nCalibration :\n", calib.round(3).to_string(index=False))
