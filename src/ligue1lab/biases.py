"""Biais cognitifs des parieurs : créent-ils des inefficiences exploitables dans les cotes ?

Hypothèses fixées AVANT l'analyse (pré-enregistrées dans docs/methodology.md) :

H1  Biais favori-outsider (théorie des perspectives : sur-pondération des petites
    probabilités, Kahneman & Tversky 1979 ; Snowberg & Wolfers 2010) : les outsiders sont
    sur-cotés par les parieurs, donc leur probabilité implicite dépasse leur fréquence réelle.
H2a Main chaude / sur-réaction à la forme (heuristique de représentativité, Tversky &
    Kahneman 1974 ; Gilovich et al. 1985) : une équipe sur 3 victoires ou plus est
    sur-estimée par le marché.
H2b Erreur du joueur (gambler's fallacy) / sur-réaction négative : une équipe sur
    3 défaites ou plus est sous-estimée.
H3  Biais de popularité (Forrest & Simmons 2008) : PSG et OM, clubs les plus suivis, sont
    sur-estimés.
H4  Biais domicile : la victoire à domicile est sur-estimée (préférence pour le scénario saillant).
H5  Matchs très médiatisés (deux clubs parmi PSG, OM, OL, Lille, Monaco, Lens) : le favori y
    est sur-estimé (afflux de parieurs occasionnels, heuristique de disponibilité).

Mesure commune : résidu = issue réalisée (0/1) - probabilité de clôture sans marge, en points
de probabilité. Résidu < 0 => l'issue est sur-estimée par le marché. On rapporte aussi le ROI
d'un pari à mise fixe à la clôture et à l'ouverture Bet365 (ce qu'un parieur obtiendrait).
IC95 par bootstrap ; p-valeurs bilatérales ; corrections de Holm (FWER) et Benjamini-Hochberg (FDR).

Lancer : python -m ligue1lab.biases   (écrit artifacts/biases/results.json)
"""
import json

import numpy as np
import pandas as pd

from .core import PROJECT_ROOT, load_data, market_baseline, outcome_matrix
from .ml import holm
from .strategy import closing_fair

ART = PROJECT_ROOT / "artifacts"
POPULAR = ["Paris SG", "Marseille"]
MEDIA = {"Paris SG", "Marseille", "Lyon", "Lille", "Monaco", "Lens"}
ODDS_BINS = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0, 10.0, 100.0]
N_BOOT = 5000


def bh(pvals: dict) -> dict:
    """Benjamini-Hochberg (contrôle du taux de fausses découvertes)."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, running = len(items), {}, 1.0
    for rank in range(m, 0, -1):
        k, p = items[rank - 1]
        running = min(running, p * m / rank)
        out[k] = running
    return out


def boot(values, n=N_BOOT, seed=0):
    """Moyenne, IC95 et p-valeur bilatérale (H0 : moyenne nulle) par bootstrap."""
    v = np.asarray(values, float)
    rng = np.random.default_rng(seed)
    m = v[rng.integers(0, len(v), (n, len(v)))].mean(1)
    p = 2 * min((m <= 0).mean(), (m >= 0).mean())
    return {"n": int(len(v)), "moyenne": float(v.mean()),
            "ic95": [float(np.quantile(m, 0.025)), float(np.quantile(m, 0.975))],
            "p": float(max(p, 1 / n))}


def bets_long(df):
    """Une ligne par (match, issue) : proba de clôture sans marge, issue, cotes."""
    C = closing_fair(df)
    Y = outcome_matrix(df["FTR"])
    rows = []
    for k, o in enumerate("HDA"):
        rows.append(pd.DataFrame({
            "match": df.index, "Season": df.Season.to_numpy(), "issue": o,
            "team": np.where(o == "H", df.HomeTeam, np.where(o == "A", df.AwayTeam, "")),
            "p_close": C[:, k], "y": Y[:, k],
            "odds_close": np.where(df["mkt_src"] == "PSC", df.get(f"PSC{o}"), df.get(f"B365C{o}")),
            "odds_b365": df[f"B365{o}"].to_numpy(float)}))
    b = pd.concat(rows, ignore_index=True)
    b["resid"] = b["y"] - b["p_close"]
    b["roi_close"] = np.where(b.y == 1, b.odds_close - 1, -1.0)
    b["roi_b365"] = np.where(b.y == 1, b.odds_b365 - 1, -1.0)
    return b.dropna(subset=["p_close", "odds_close", "odds_b365"])


def streaks(df):
    """Série de victoires / défaites consécutives AVANT chaque match, pour chaque équipe."""
    when = df["Kickoff"] if "Kickoff" in df else df["Date"]
    long = pd.concat([
        pd.DataFrame({"match": df.index, "when": when, "team": df.HomeTeam,
                      "res": np.sign(df.FTHG - df.FTAG)}),
        pd.DataFrame({"match": df.index, "when": when, "team": df.AwayTeam,
                      "res": np.sign(df.FTAG - df.FTHG)})]).sort_values(["when", "match"])
    win_s, loss_s, out = {}, {}, []
    for r in long.itertuples(index=False):
        out.append((r.match, r.team, win_s.get(r.team, 0), loss_s.get(r.team, 0)))
        win_s[r.team] = win_s.get(r.team, 0) + 1 if r.res > 0 else 0
        loss_s[r.team] = loss_s.get(r.team, 0) + 1 if r.res < 0 else 0
    return pd.DataFrame(out, columns=["match", "team", "win_streak", "loss_streak"])


def test_subset(b, mask, label, hypothesis, expected_sign=-1):
    s = b[mask]
    r = {"label": label, "hypothese": hypothesis, "sens_attendu": expected_sign,
         "resid_pts": boot(100 * s.resid), "roi_cloture_%": boot(100 * s.roi_close, seed=1),
         "roi_b365_%": boot(100 * s.roi_b365, seed=2),
         "p_implicite_moy": float(s.p_close.mean()), "frequence": float(s.y.mean())}
    return r


def run(verbose=True):
    df = load_data()
    d, *_ = market_baseline(df)
    b = bets_long(d)
    st = streaks(d)
    b = b.merge(st, on=["match", "team"], how="left")
    log = (lambda *a: print(*a, flush=True)) if verbose else (lambda *a: None)

    # ROI et calibration par tranche de cote (graphique du biais favori-outsider)
    b["tranche"] = pd.cut(b.odds_close, ODDS_BINS, right=False)
    by_bin = []
    for iv, g in b.groupby("tranche", observed=True):
        by_bin.append({"tranche": f"{iv.left:g}-{iv.right:g}", "n": int(len(g)),
                       "p_implicite": float(g.p_close.mean()), "frequence": float(g.y.mean()),
                       "roi_cloture_%": boot(100 * g.roi_close)["moyenne"],
                       "roi_cloture_ic95": boot(100 * g.roi_close)["ic95"],
                       "roi_b365_%": boot(100 * g.roi_b365, seed=2)["moyenne"],
                       "roi_b365_ic95": boot(100 * g.roi_b365, seed=2)["ic95"]})

    # matchs médiatisés : le favori de clôture
    fav = b.loc[b.groupby("match").p_close.idxmax()]
    media_matches = d.index[d.HomeTeam.isin(MEDIA) & d.AwayTeam.isin(MEDIA)]

    tests = [
        test_subset(b, b.odds_close >= 6, "H1 outsiders (cote ≥ 6)",
                    "outsiders sur-estimés (résidu < 0)"),
        test_subset(b, b.odds_close < 1.5, "H1 grands favoris (cote < 1,5)",
                    "favoris sous-estimés (résidu > 0)", +1),
        test_subset(b, (b.issue != "D") & (b.win_streak >= 3), "H2a série ≥ 3 victoires",
                    "équipe en forme sur-estimée (résidu < 0)"),
        test_subset(b, (b.issue != "D") & (b.loss_streak >= 3), "H2b série ≥ 3 défaites",
                    "équipe en crise sous-estimée (résidu > 0)", +1),
        test_subset(b, b.team.isin(POPULAR), "H3 victoire PSG / OM",
                    "clubs populaires sur-estimés (résidu < 0)"),
        test_subset(b, b.issue == "H", "H4 victoire à domicile",
                    "domicile sur-estimé (résidu < 0)"),
        test_subset(fav, fav.match.isin(media_matches), "H5 favori des matchs médiatisés",
                    "favori sur-estimé (résidu < 0)"),
    ]
    p = {t["label"]: t["resid_pts"]["p"] for t in tests}
    ph, pb = holm(p), bh(p)
    for t in tests:
        t["p_holm"], t["p_bh"] = ph[t["label"]], pb[t["label"]]
        lo, hi = t["roi_b365_%"]["ic95"]
        rlo, rhi = t["resid_pts"]["ic95"]
        sign_ok = np.sign(t["resid_pts"]["moyenne"]) == t["sens_attendu"]
        if t["p_holm"] < 0.05 and sign_ok:
            verdict = "effet détecté dans le sens prédit"
        elif t["p_holm"] < 0.05:
            verdict = "effet détecté, mais dans le sens opposé à l'hypothèse"
        else:
            verdict = "pas d'effet significatif après correction"
        exploit = ("exploitable : ROI Bet365 > 0 (IC95)" if lo > 0
                   else "non exploitable après marge")
        t["verdict"], t["exploitable"] = verdict, exploit
        r = t["resid_pts"]
        log(f"{t['label']:34s} n={r['n']:5d} résidu {r['moyenne']:+.2f} pts "
            f"[{rlo:+.2f} ; {rhi:+.2f}] p={t['resid_pts']['p']:.3f} Holm={t['p_holm']:.3f} | "
            f"ROI B365 {t['roi_b365_%']['moyenne']:+.1f} % [{lo:+.1f} ; {hi:+.1f}] | {verdict}")
    out = {"n_matchs": int(d.shape[0]), "periode": [str(d.Date.min().date()),
                                                     str(d.Date.max().date())],
           "tests": tests, "par_tranche_de_cote": by_bin,
           "groupes": {"populaires": POPULAR, "mediatises": sorted(MEDIA)}}
    (ART / "biases").mkdir(parents=True, exist_ok=True)
    (ART / "biases" / "results.json").write_text(json.dumps(out, indent=1, ensure_ascii=False,
                                                           default=float), encoding="utf-8")
    log("\nPar tranche de cote (clôture) :")
    for r in by_bin:
        log(f"  {r['tranche']:>7s} n={r['n']:5d} implicite {r['p_implicite']:.3f} "
            f"observée {r['frequence']:.3f} ROI clôture {r['roi_cloture_%']:+.1f} % "
            f"ROI B365 {r['roi_b365_%']:+.1f} %")
    return out


if __name__ == "__main__":
    run()
