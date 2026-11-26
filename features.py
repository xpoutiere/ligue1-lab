"""Features d'avant-match, strictement point-in-time.

Une seule entrée : `build_features(df)`. Chaque feature d'un match n'utilise que des matchs
dont le coup d'envoi est STRICTEMENT antérieur (jamais le match lui-même, ni un match joué
au même moment). Le test tests/test_features.py le vérifie en brouillant les résultats futurs.

Conventions de nommage : préfixe `h_` (équipe à domicile), `a_` (extérieur), `diff_` = h - a.
"""
import numpy as np
import pandas as pd

from models import elo_probs, walk_forward_dc

# statistique de match -> (colonne domicile, colonne extérieur)
STATS = {"g": ("FTHG", "FTAG"), "s": ("HS", "AS"), "st": ("HST", "AST"), "xg": ("HxG", "AxG")}


def _when(df):
    return df["Kickoff"] if "Kickoff" in df.columns else df["Date"]


def to_long(df: pd.DataFrame, min_coverage=0.5) -> pd.DataFrame:
    """Une ligne par (match, équipe) : stats « pour » et « contre » du point de vue de l'équipe.

    Une statistique présente sur moins de `min_coverage` des matchs est ignorée (ex. les xG
    football-data, publiés seulement depuis 2026-27). Les buts sont toujours gardés.
    """
    stats = {k: v for k, v in STATS.items()
             if v[0] in df.columns and v[1] in df.columns
             and (k == "g" or df[[v[0], v[1]]].notna().all(axis=1).mean() >= min_coverage)}
    base = {"match": df.index.to_numpy(), "when": _when(df).to_numpy(),
            "Season": df["Season"].to_numpy()}
    sides = []
    for is_home, (me, opp) in ((1, ("HomeTeam", "AwayTeam")), (0, ("AwayTeam", "HomeTeam"))):
        part = pd.DataFrame({**base, "team": df[me].to_numpy(), "opp": df[opp].to_numpy(),
                             "is_home": is_home})
        for k, (hc, ac) in stats.items():
            mine, theirs = (hc, ac) if is_home else (ac, hc)
            part[f"{k}_for"] = df[mine].to_numpy(float)
            part[f"{k}_against"] = df[theirs].to_numpy(float)
        gd = part["g_for"] - part["g_against"]
        part["pts"] = np.select([gd > 0, gd == 0], [3.0, 1.0], 0.0)
        sides.append(part)
    return (pd.concat(sides, ignore_index=True)
            .sort_values(["when", "match", "is_home"], kind="mergesort").reset_index(drop=True))


def _past_rolling(long, keys, cols, windows, span):
    """Moyennes mobiles et EWMA des matchs PRÉCÉDENTS (shift(1)) par groupe `keys`."""
    g = long.groupby(keys, sort=False)[cols]
    prev = g.shift(1)  # le match courant est exclu
    prev[keys] = long[keys]
    gp = prev.groupby(keys, sort=False)[cols]
    out = {}
    for w in windows:
        r = gp.rolling(w, min_periods=1).mean().reset_index(level=list(range(len(keys))),
                                                              drop=True)
        for c in cols:
            out[f"{c}_m{w}"] = r[c]
    if span:
        e = gp.transform(lambda s: s.ewm(span=span, ignore_na=True).mean())
        for c in cols:
            out[f"{c}_ewm{span}"] = e[c]
    return pd.DataFrame(out, index=long.index)


def table_features(df: pd.DataFrame) -> pd.DataFrame:
    """Classement AVANT chaque match : rang, points par match, écarts à la 3e place et à la
    zone de relégation (enjeu approximatif). Les matchs d'un même coup d'envoi voient tous
    le classement d'avant ce créneau."""
    when = _when(df).to_numpy()
    out = np.full((len(df), 10), np.nan)
    teams_by_season = {s: sorted(set(g.HomeTeam) | set(g.AwayTeam))
                       for s, g in df.groupby("Season")}  # composition connue avant la saison
    table, season, i, n = {}, None, 0, len(df)
    rows = df[["Season", "HomeTeam", "AwayTeam", "FTHG", "FTAG"]].to_numpy()
    while i < n:
        j = i
        while j < n and when[j] == when[i]:
            j += 1
        if rows[i][0] != season:
            season = rows[i][0]
            table = {t: [0, 0, 0, 0] for t in teams_by_season[season]}  # pts, gd, gf, joués
        order = sorted(table, key=lambda t: (-table[t][0], -table[t][1], -table[t][2], t))
        rank = {t: r + 1 for r, t in enumerate(order)}
        nt = len(order)
        pts_3rd = table[order[2]][0]
        pts_releg = table[order[nt - 3]][0]  # dernier non relégable direct (16e sur 18, 18e sur 20)
        for k in range(i, j):
            _, h, a, hg, ag = rows[k]
            vals = []
            for t in (h, a):
                p, _, _, played = table[t]
                vals += [rank[t], p / played if played else np.nan, p - pts_3rd, p - pts_releg,
                         played]
            out[k] = vals
        for k in range(i, j):  # mise à jour après le créneau
            _, h, a, hg, ag = rows[k]
            for t, gf, ga in ((h, hg, ag), (a, ag, hg)):
                table[t][0] += 3 if gf > ga else 1 if gf == ga else 0
                table[t][1] += gf - ga
                table[t][2] += gf
                table[t][3] += 1
        i = j
    cols = [f"{s}_{c}" for s in ("h", "a")
            for c in ("rank", "ppg", "gap_top3", "gap_releg", "played")]
    return pd.DataFrame(out, index=df.index, columns=cols)


def build_features(df: pd.DataFrame, windows=(3, 5, 10), ewm_span=5, venue_window=5,
                   sos_window=5, include_dc=True, dc_from=None, dc_refit_days=28,
                   elo_kw=None, dc_kw=None, min_coverage=0.5) -> pd.DataFrame:
    """DataFrame de features aligné sur `df` (même index), sans fuite de données.

    - forme : moyennes sur `windows` matchs et EWMA (span `ewm_span`) des buts, tirs, tirs
      cadrés (et xG si présents) pour/contre, et des points ;
    - forme spécifique au lieu : domicile pour l'équipe qui reçoit, extérieur pour l'autre ;
    - jours de repos depuis le dernier match de championnat ;
    - classement d'avant-match (rang, points par match, écarts à la 3e place / relégation) ;
    - Elo d'avant-match et probabilités Elo ;
    - force du calendrier : Elo moyen d'avant-match des `sos_window` derniers adversaires ;
    - probabilités Dixon-Coles walk-forward (NaN avant `dc_from`, faute d'historique).
    `df` doit être trié chronologiquement (cf. core.clean_matches).
    """
    if not _when(df).is_monotonic_increasing:
        raise ValueError("build_features : df doit être trié chronologiquement")
    long = to_long(df, min_coverage)
    stat_cols = [c for c in long.columns if c.endswith(("_for", "_against"))] + ["pts"]

    # Elo d'avant-match (sert aussi à la force du calendrier)
    eprob, _, pre = elo_probs(df, return_pre=True, **(elo_kw or {}))
    elo_pre = pd.Series(pre[:, 0], index=df.index), pd.Series(pre[:, 1], index=df.index)
    long["elo_opp"] = np.where(long["is_home"] == 1, elo_pre[1].reindex(long["match"]).to_numpy(),
                               elo_pre[0].reindex(long["match"]).to_numpy())

    form = _past_rolling(long, ["team"], stat_cols, windows, ewm_span)
    venue = _past_rolling(long, ["team", "is_home"], stat_cols, (venue_window,), 0)
    venue.columns = [c.replace(f"_m{venue_window}", f"_venue{venue_window}") for c in venue]
    sos = _past_rolling(long, ["team"], ["elo_opp"], (sos_window,), 0)
    sos.columns = [f"sos{sos_window}"]
    rest = long.groupby("team")["when"].diff().dt.total_seconds() / 86400
    feats = pd.concat([long[["match", "is_home"]], form, venue, sos,
                       rest.rename("rest_days")], axis=1)

    home = feats[feats.is_home == 1].set_index("match").drop(columns="is_home")
    away = feats[feats.is_home == 0].set_index("match").drop(columns="is_home")
    out = pd.concat([home.add_prefix("h_"), away.add_prefix("a_")], axis=1).reindex(df.index)
    for c in home.columns:
        out[f"diff_{c}"] = out[f"h_{c}"] - out[f"a_{c}"]

    out = pd.concat([out, table_features(df)], axis=1)
    out["h_elo"], out["a_elo"] = elo_pre
    out["diff_elo"] = out["h_elo"] - out["a_elo"]
    out[["eH", "eD", "eA"]] = eprob

    if include_dc:
        start = dc_from or (_when(df).iloc[0] + pd.Timedelta(days=330)).normalize()
        dc = walk_forward_dc(df, start, refit_days=dc_refit_days, **(dc_kw or {}))
        out = out.join(dc)
    return out


if __name__ == "__main__":
    import time

    from core import load_data

    data = load_data()
    t0 = time.time()
    F = build_features(data)
    print(f"{F.shape[1]} features x {len(F)} matchs en {time.time() - t0:.0f} s")
    nan = F.isna().mean().sort_values(ascending=False)
    print("Colonnes les plus incomplètes (part de NaN) :\n", nan.head(8).round(3).to_string())
    y = np.select([data.FTHG > data.FTAG, data.FTHG == data.FTAG], [1, 0], -1)
    corr = F.select_dtypes("number").corrwith(pd.Series(y, index=data.index), method="spearman")
    print("\nCorrélation de Spearman avec le résultat (1 / 0 / -1), top 12 :")
    print(corr.abs().sort_values(ascending=False).head(12).round(3).to_string())
