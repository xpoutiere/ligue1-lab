"""xG par match : import depuis Understat ou depuis des exports CSV FBref, puis fusion.

Sources (voir data/README.md) :
- Understat : page publique de la ligue, téléchargée poliment (en-tête identifiant le projet,
  délai entre requêtes, cache local). Si le site est indisponible, on s'arrête proprement.
- FBref : PAS de téléchargement automatique (protection anti-bot, conditions d'usage).
  L'utilisateur exporte lui-même la table « Scores & Fixtures » de chaque saison en CSV
  (menu « Share & Export > Get table as CSV ») et l'enregistre sous data/xg/fbref_<code>.csv.

Toutes les équipes sont ramenées aux noms football-data via data/team_names.csv (versionné) ;
un nom inconnu lève une erreur plutôt que d'être ignoré en silence.
"""
import codecs
import io
import json
import re
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from .core import DATA_DIR

XG_DIR = DATA_DIR / "xg"
TEAM_MAP = DATA_DIR / "team_names.csv"
UNDERSTAT_URL = "https://understat.com/league/Ligue_1/{year}"
USER_AGENT = "ligue1lab/0.1 (projet educatif ENSC ; requetes espacees, donnees en cache)"
REQUEST_DELAY_S = 5.0
_last_request = [0.0]


class SourceUnavailable(RuntimeError):
    """La source ne renvoie pas de données exploitables (maintenance, blocage, réseau)."""


# ------------------------------------------------------------------ noms d'équipes
def load_team_map(path=TEAM_MAP) -> pd.DataFrame:
    m = pd.read_csv(path, dtype=str).apply(lambda c: c.str.strip())
    for col in m.columns:
        dup = m[col][m[col].duplicated()]
        if len(dup):
            raise ValueError(f"team_names.csv : doublons dans '{col}' : {list(dup)}")
    return m


def to_canonical(names: pd.Series, source: str, team_map=None) -> pd.Series:
    """Noms d'une source -> noms football-data. Erreur explicite si un nom est inconnu."""
    m = load_team_map() if team_map is None else team_map
    mapping = dict(zip(m[source], m["canonical"], strict=True))
    names = names.astype(str).str.strip()
    unknown = sorted(set(names) - set(mapping))
    if unknown:
        raise KeyError(f"Équipes {source} absentes de team_names.csv : {unknown}")
    return names.map(mapping)


def season_year(code: str) -> int:
    """'2324' -> 2023 (année de début, convention Understat)."""
    return 2000 + int(code[:2])


# ------------------------------------------------------------------ Understat
def _polite_get(url: str) -> str:
    wait = REQUEST_DELAY_S - (time.time() - _last_request[0])
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            html = r.read().decode("utf-8", errors="replace")
    except OSError as e:
        raise SourceUnavailable(f"{url} : {e}") from e
    finally:
        _last_request[0] = time.time()
    return html


def parse_understat_league(html: str) -> pd.DataFrame:
    """Extrait les matchs joués de la variable `datesData` d'une page ligue Understat."""
    m = re.search(r"datesData\s*=\s*JSON\.parse\('(.*?)'\)", html, re.S)
    if not m:
        hint = "page de maintenance" if "come back soon" in html else "format inattendu"
        raise SourceUnavailable(f"Understat : datesData introuvable ({hint})")
    raw = json.loads(codecs.decode(m.group(1), "unicode_escape"))
    rows = [{"Date": pd.Timestamp(r["datetime"]).normalize(),
             "home": r["h"]["title"], "away": r["a"]["title"],
             "hg": int(r["goals"]["h"]), "ag": int(r["goals"]["a"]),
             "HxG": float(r["xG"]["h"]), "AxG": float(r["xG"]["a"])}
            for r in raw if r.get("isResult")]
    return pd.DataFrame(rows)


def fetch_understat(code: str, refresh=False) -> pd.DataFrame:
    """xG Understat d'une saison, avec cache JSON local (data/xg/understat_<code>.json)."""
    XG_DIR.mkdir(parents=True, exist_ok=True)
    cache = XG_DIR / f"understat_{code}.json"
    if cache.exists() and not refresh:
        df = pd.read_json(cache, orient="records", convert_dates=["Date"])
    else:
        df = parse_understat_league(_polite_get(UNDERSTAT_URL.format(year=season_year(code))))
        df.to_json(cache, orient="records", date_format="iso")
    return df.assign(Season=code, xg_src="understat")


# ------------------------------------------------------------------ FBref (export manuel)
def parse_fbref_fixtures(path) -> pd.DataFrame:
    """Lit un export CSV « Scores & Fixtures » de FBref (colonnes Home, xG, Score, xG.1, Away)."""
    # Un copier-coller depuis le navigateur peut laisser des lignes avant l'en-tête.
    lines = Path(path).read_text(encoding="utf-8-sig", errors="replace").splitlines()
    start = next((i for i, ln in enumerate(lines) if ",Home," in ln and ",Away" in ln), 0)
    f = pd.read_csv(io.StringIO("\n".join(lines[start:])))
    f = f.rename(columns={"xG": "HxG", "xG.1": "AxG"})
    need = {"Date", "Home", "Away", "Score", "HxG", "AxG"}
    if missing := need - set(f.columns):
        raise ValueError(f"{path} : colonnes manquantes {sorted(missing)}")
    f = f.dropna(subset=["Score", "HxG", "AxG"])
    goals = f["Score"].astype(str).str.extract(r"(\d+)\s*[–-]\s*(\d+)").astype(int)
    return pd.DataFrame({"Date": pd.to_datetime(f["Date"]).dt.normalize(),
                         "home": f["Home"], "away": f["Away"],
                         "hg": goals[0], "ag": goals[1],
                         "HxG": f["HxG"].astype(float), "AxG": f["AxG"].astype(float)})


def load_fbref(code: str) -> pd.DataFrame:
    path = XG_DIR / f"fbref_{code}.csv"
    if not path.exists():
        raise SourceUnavailable(f"{path} absent (export manuel FBref non fait)")
    return parse_fbref_fixtures(path).assign(Season=code, xg_src="fbref")


# ------------------------------------------------------------------ fusion
def load_xg(codes, sources=("understat", "fbref"), verbose=True) -> pd.DataFrame:
    """xG de chaque saison depuis la première source disponible (ordre de `sources`)."""
    loaders = {"understat": fetch_understat, "fbref": load_fbref}
    parts, down = [], set()
    for code in codes:
        for s in sources:
            if s in down:
                continue
            try:
                x = loaders[s](code)
            except SourceUnavailable as e:
                if verbose:
                    print(f"[xg] {code} {s} indisponible : {e}")
                if "maintenance" in str(e) or "Errno" in str(e):
                    down.add(s)  # site hors service : inutile d'insister sur les autres saisons
                continue
            x["home"] = to_canonical(x["home"], s)
            x["away"] = to_canonical(x["away"], s)
            parts.append(x)
            break
    cols = ["Season", "Date", "home", "away", "hg", "ag", "HxG", "AxG", "xg_src"]
    return pd.concat(parts, ignore_index=True)[cols] if parts else pd.DataFrame(columns=cols)


def merge_xg(df: pd.DataFrame, xg: pd.DataFrame, max_day_gap=2) -> pd.DataFrame:
    """Ajoute HxG / AxG / xg_src aux matchs football-data.

    Clé : (saison, domicile, extérieur), unique dans un championnat aller-retour. On vérifie
    ensuite que le score concorde et que les dates diffèrent d'au plus `max_day_gap` jours
    (fuseaux horaires) ; toute incohérence lève une erreur.
    """
    key = ["Season", "HomeTeam", "AwayTeam"]
    # football-data publie lui-même des xG depuis 2026-27 : ils sont prioritaires.
    if {"HxG", "AxG"} <= set(df.columns):
        fd = df[["HxG", "AxG"]].astype(float)
        fd_src = pd.Series(np.where(fd["HxG"].notna(), "football-data", None), index=df.index)
    else:
        fd = pd.DataFrame(np.nan, index=df.index, columns=["HxG", "AxG"])
        fd_src = pd.Series(None, index=df.index, dtype=object)
    if xg.empty:
        return df.drop(columns=["HxG", "AxG", "xg_src"], errors="ignore").assign(
            HxG=fd["HxG"], AxG=fd["AxG"], xg_src=fd_src)
    x = xg.rename(columns={"home": "HomeTeam", "away": "AwayTeam", "Date": "xg_date"})
    if x.duplicated(key).any():
        raise ValueError(f"xG : matchs en double {x[x.duplicated(key)][key].values.tolist()}")
    out = df.drop(columns=["HxG", "AxG", "xg_src"], errors="ignore").merge(
        x[key + ["xg_date", "hg", "ag", "HxG", "AxG", "xg_src"]], on=key, how="left",
        validate="one_to_one")
    has = out["HxG"].notna()
    bad_score = has & ((out["hg"] != out["FTHG"]) | (out["ag"] != out["FTAG"]))
    bad_date = has & ((out["xg_date"] - out["Date"]).abs().dt.days > max_day_gap)
    if bad_score.any() or bad_date.any():
        raise ValueError(f"Réconciliation xG : {int(bad_score.sum())} scores et "
                         f"{int(bad_date.sum())} dates incohérents")
    out.index = df.index
    use_fd = fd["HxG"].notna()
    out.loc[use_fd, ["HxG", "AxG"]] = fd.loc[use_fd].to_numpy()
    out.loc[use_fd, "xg_src"] = "football-data"
    return out.drop(columns=["xg_date", "hg", "ag"])


def coverage(df: pd.DataFrame, cols=("HS", "HST", "HxG")) -> pd.DataFrame:
    """Part des matchs disposant de chaque statistique, par saison."""
    present = [c for c in cols if c in df.columns]
    return df.groupby("Season")[present].agg(lambda s: s.notna().mean()).round(3)


if __name__ == "__main__":
    from .core import load_data, season_codes

    data = load_data()
    merged = merge_xg(data, load_xg(season_codes()))
    print("Couverture (part des matchs) :")
    print(coverage(merged).to_string())
    print("Sources xG :", merged["xg_src"].value_counts(dropna=False).to_dict())
