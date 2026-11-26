"""Socle du projet : données Ligue 1 + baseline du marché."""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

# Console Windows (cp1252) : évite les accents illisibles dans les sorties.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA_DIR = Path("data")
URL = "https://www.football-data.co.uk/mmz4281/{code}/F1.csv"
OUTCOMES = ["H", "D", "A"]
# Ordre de préférence des cotes « marché », appliqué LIGNE PAR LIGNE.
# football-data.co.uk ne publie plus les cotes Pinnacle depuis mi-janvier 2026 :
# on retombe alors sur la clôture Bet365 (B365C), puis l'ouverture Bet365.
MARKET_PREFIXES = ("PSC", "PS", "B365C", "B365")
CURRENT_SEASON_MAX_AGE_H = 12  # le CSV de la saison en cours est re-téléchargé au-delà


def season_codes(start=2019, end=2026):
    """2019 -> '1920' ... 2026 -> '2627'."""
    return [f"{y % 100:02d}{(y + 1) % 100:02d}" for y in range(start, end + 1)]


def _is_stale(path: Path, code: str, codes) -> bool:
    """Le cache de la dernière saison demandée (saison en cours) expire."""
    if code != list(codes)[-1]:
        return False
    return (time.time() - path.stat().st_mtime) / 3600 > CURRENT_SEASON_MAX_AGE_H


def clean_matches(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoyage des vraies données : dates, NaN, noms d'équipes, doublons, cohérence FTR."""
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    for c in ("HomeTeam", "AwayTeam"):
        df[c] = df[c].astype("string").str.strip()
    # Matchs non joués / lignes vides : pas de résultat => inutilisables.
    df = df.dropna(subset=["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"])
    df["FTHG"] = df["FTHG"].astype(int)
    df["FTAG"] = df["FTAG"].astype(int)
    expected = np.where(df.FTHG > df.FTAG, "H", np.where(df.FTHG < df.FTAG, "A", "D"))
    bad = (df["FTR"] != expected).sum()
    if bad:
        raise ValueError(f"{bad} matchs avec FTR incohérent avec le score")
    df = df.drop_duplicates(subset=["Date", "HomeTeam", "AwayTeam"])
    # Coup d'envoi : sert à ordonner les matchs d'une même journée (Elo séquentiel).
    t = df["Time"] if "Time" in df.columns else pd.Series("00:00", index=df.index)
    df["Kickoff"] = df["Date"] + pd.to_timedelta(
        pd.to_datetime(t.fillna("00:00"), format="%H:%M", errors="coerce")
        .dt.strftime("%H:%M:00").fillna("00:00:00"))
    return df.sort_values(["Kickoff", "HomeTeam"]).reset_index(drop=True)


def load_data(codes=None, refresh=False) -> pd.DataFrame:
    """Télécharge (et met en cache dans data/) les CSV de football-data.co.uk."""
    codes = list(codes or season_codes())
    DATA_DIR.mkdir(exist_ok=True)
    frames, seasons = [], []
    for code in codes:
        path = DATA_DIR / f"F1_{code}.csv"
        try:
            if refresh or not path.exists() or _is_stale(path, code, codes):
                pd.read_csv(URL.format(code=code), encoding="latin-1").to_csv(path, index=False)
            df = pd.read_csv(path)
        except Exception as e:  # saison absente / réseau
            print(f"[skip] {code}: {e}")
            continue
        frames.append(df)
        seasons.append(code)
    if not frames:
        raise RuntimeError("Aucune saison chargée (réseau ? cache data/ vide ?)")
    df = pd.concat(frames, ignore_index=True).copy()  # copy() consolide les blocs
    df["Season"] = np.repeat(seasons, [len(f) for f in frames])
    return clean_matches(df)


def _cols(prefix):
    return [f"{prefix}H", f"{prefix}D", f"{prefix}A"]


def _valid_odds(df, prefix):
    """Masque des lignes où les 3 cotes du préfixe existent et sont > 1."""
    if not all(c in df.columns for c in _cols(prefix)):
        return pd.Series(False, index=df.index)
    o = df[_cols(prefix)].apply(pd.to_numeric, errors="coerce")
    return (o > 1.0).all(axis=1)


def pick_odds(df, prefixes=MARKET_PREFIXES):
    """Choisit le 1er jeu de cotes (H/D/A) complet sur plus de la moitié des lignes.

    Conservé pour compatibilité ; préférer `market_odds`, qui choisit ligne par ligne.
    """
    for p in prefixes:
        if _valid_odds(df, p).mean() > 0.5:
            return _cols(p), p
    raise ValueError("Aucune colonne de cotes exploitable")


def market_odds(df, prefixes=MARKET_PREFIXES):
    """Cotes du marché ligne par ligne selon l'ordre de préférence.

    Retourne (cotes n x 3 avec NaN si aucune source, Series de la source utilisée).
    """
    odds = np.full((len(df), 3), np.nan)
    src = pd.Series(pd.NA, index=df.index, dtype="string")
    for p in prefixes:
        m = (_valid_odds(df, p) & src.isna()).to_numpy()
        if m.any():
            odds[m] = df.loc[m, _cols(p)].to_numpy(float)
            src[m] = p
    return odds, src


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


def match_log_loss(p, y, eps=1e-12):
    """Log-loss de chaque match (vecteur), pour les bootstraps appariés."""
    return -np.sum(y * np.log(np.clip(p, eps, 1)), axis=1)


def bootstrap_ci(values, n_boot=2000, level=0.95, seed=0):
    """IC bootstrap (percentile) de la moyenne d'un vecteur de pertes par match."""
    v = np.asarray(values, float)
    rng = np.random.default_rng(seed)
    means = v[rng.integers(0, len(v), (n_boot, len(v)))].mean(axis=1)
    a = (1 - level) / 2
    return float(np.quantile(means, a)), float(np.quantile(means, 1 - a))


def calibration_table(p, y, bins=10):
    """Probabilité prédite vs fréquence observée, toutes issues confondues."""
    pf, yf = p.ravel(), y.ravel()
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(pf, edges) - 1, 0, bins - 1)
    rows = [(pf[idx == b].mean(), yf[idx == b].mean(), int((idx == b).sum()))
            for b in range(bins) if (idx == b).any()]
    return pd.DataFrame(rows, columns=["predite", "observee", "n"])


def bookmaker_margins(df, prefixes=("PSC", "PS", "B365C", "B365", "AvgC")):
    """Marge moyenne par bookmaker et par saison, sur les lignes où ses cotes existent."""
    rows = []
    for p in prefixes:
        m = _valid_odds(df, p)
        for s, g in df[m].groupby("Season"):
            rows.append({"cotes": p, "Season": s, "matchs": len(g),
                         "marge_moy_%": 100 * overround(g[_cols(p)].to_numpy(float)).mean()})
    t = pd.DataFrame(rows)
    return t.pivot(index="Season", columns="cotes", values="marge_moy_%")[list(
        dict.fromkeys(c for c in prefixes if c in set(t["cotes"])))]


def market_baseline(df):
    """Probas du marché sans marge + métriques par saison.

    Retourne (matchs avec pH/pD/pA, margin, mkt_src ; tableau par saison ; description
    des sources ; table de calibration).
    """
    odds, src = market_odds(df)
    keep = src.notna().to_numpy()
    d = df[keep].copy()
    odds = odds[keep]
    p, y = remove_margin(odds), outcome_matrix(d["FTR"])
    d[["pH", "pD", "pA"]] = p
    d["margin"] = overround(odds)
    d["mkt_src"] = src[keep].to_numpy()
    per_season = pd.DataFrame(
        [{"Season": s, "matchs": len(g),
          "source": "/".join(f"{k}:{v}" for k, v in g["mkt_src"].value_counts().items()),
          "log_loss": log_loss(g[["pH", "pD", "pA"]].to_numpy(), outcome_matrix(g["FTR"])),
          "brier": brier(g[["pH", "pD", "pA"]].to_numpy(), outcome_matrix(g["FTR"])),
          "marge_moy_%": 100 * g["margin"].mean()}
         for s, g in d.groupby("Season")])
    counts = d["mkt_src"].value_counts()
    prefix = counts.index[0] if len(counts) == 1 else " + ".join(
        f"{k} ({v})" for k, v in counts.items())
    return d, per_season, prefix, calibration_table(p, y)


if __name__ == "__main__":
    data = load_data()
    d, table, prefix, calib = market_baseline(data)
    print(f"Matchs joués chargés : {len(data)}  |  avec cotes marché : {len(d)}")
    print(f"Cotes utilisées : {prefix}")
    print(table.round(4).to_string(index=False))
    print("\nMarge moyenne par bookmaker (%) :")
    print(bookmaker_margins(data).round(2).to_string())
    print("\nCalibration du marché :\n", calib.round(3).to_string(index=False))
