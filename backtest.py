"""Comparaison des modèles vs marché + simulation de paris « value ».

Usage :
    python backtest.py                      # vraies données (football-data.co.uk)
    python backtest.py --synthetic          # données simulées (hors ligne)
    python backtest.py --test-from 2023-08-01
"""
import argparse

import numpy as np
import pandas as pd

from core import (
    OUTCOMES,
    bootstrap_ci,
    brier,
    load_data,
    market_baseline,
    match_log_loss,
    outcome_matrix,
)
from models import DixonColes, elo_probs, walk_forward_dc

COLS = {"Marché": ["pH", "pD", "pA"], "Elo": ["eH", "eD", "eA"],
        "Dixon-Coles": ["dH", "dD", "dA"], "Fréquences": ["fH", "fD", "fA"]}


def evaluate(test, cols=COLS, n_boot=2000):
    """Log-loss / Brier / accuracy de chaque modèle, avec IC95 bootstrap.

    `delta_vs_marché` = log-loss(modèle) - log-loss(marché), IC95 par bootstrap APPARIÉ
    (mêmes matchs rééchantillonnés) : > 0 = le modèle fait moins bien que le marché.
    """
    y = outcome_matrix(test["FTR"])
    ll_mkt = match_log_loss(test[cols["Marché"]].to_numpy(), y)
    rows = []
    for name, c in cols.items():
        p = test[c].to_numpy()
        ll = match_log_loss(p, y)
        lo, hi = bootstrap_ci(ll, n_boot)
        dlo, dhi = bootstrap_ci(ll - ll_mkt, n_boot)
        rows.append({"modèle": name, "log_loss": ll.mean(), "ll_ic95_bas": lo, "ll_ic95_haut": hi,
                     "delta_vs_marché": (ll - ll_mkt).mean(), "delta_ic95_bas": dlo,
                     "delta_ic95_haut": dhi, "brier": brier(p, y),
                     "accuracy_%": 100 * np.mean(p.argmax(1) == y.argmax(1))})
    return pd.DataFrame(rows).sort_values("log_loss").reset_index(drop=True)


def run_all(df, test_from, xi=0.0019, refit_days=28):
    """Calcule les probas de chaque modèle sur la période de test (sans fuite de données)."""
    d, _, prefix, _ = market_baseline(df)
    test_from = pd.Timestamp(test_from)

    elo, elo_ratings = elo_probs(df)
    elo_df = pd.DataFrame(elo, index=df.index, columns=["eH", "eD", "eA"])
    dc_df = walk_forward_dc(df, test_from, refit_days=refit_days, xi=xi)

    train_freq = outcome_matrix(df[df.Date < test_from]["FTR"]).mean(0)
    test = d[d.Date >= test_from].join(elo_df).join(dc_df, how="inner")
    for c, v in zip(["fH", "fD", "fA"], train_freq, strict=True):
        test[c] = v

    metrics = evaluate(test)

    final_dc = DixonColes(xi=xi).fit(df)
    return {"test": test, "metrics": metrics, "prefix": prefix,
            "elo_ratings": elo_ratings, "dc": final_dc}


def cumulative_logloss_gap(test, model_cols, market_cols=("pH", "pD", "pA")):
    """Cumul de (log-loss marché - log-loss modèle) : > 0 = le modèle bat le marché."""
    y = outcome_matrix(test["FTR"])
    ll = lambda cols: -np.sum(y * np.log(np.clip(test[list(cols)].to_numpy(), 1e-12, 1)), axis=1)
    return pd.Series((ll(market_cols) - ll(model_cols)).cumsum(), index=test["Date"].to_numpy())


def value_bets(test, prob_cols, odds_cols, edge=0.03, kelly_frac=0.25, max_frac=0.05,
               bankroll0=100.0):
    """Simule des paris 'value' : on mise sur l'issue au plus fort EV si EV > edge.

    EV = p x cote - 1 ;  Kelly = (p x cote - 1) / (cote - 1), fractionné et plafonné.
    Retourne (journal des paris, résumé).
    """
    P = test[list(prob_cols)].to_numpy()
    O = test[list(odds_cols)].to_numpy(float)
    Y = outcome_matrix(test["FTR"])
    ev = P * O - 1
    best = ev.argmax(1)
    rows, bank = [], bankroll0
    for i in range(len(test)):
        b = best[i]
        if ev[i, b] <= edge:
            continue
        kelly = ev[i, b] / (O[i, b] - 1)
        stake = bank * min(kelly_frac * kelly, max_frac)
        win = Y[i, b] == 1
        profit = stake * (O[i, b] - 1) if win else -stake
        flat = (O[i, b] - 1) if win else -1.0
        bank += profit
        rows.append({"Date": test["Date"].iloc[i], "issue": OUTCOMES[b], "cote": O[i, b],
                     "p_modele": P[i, b], "ev": ev[i, b], "mise": stake, "gain": profit,
                     "gain_flat": flat, "bankroll": bank})
    log = pd.DataFrame(rows)
    if log.empty:
        return log, {"paris": 0}
    peak = log["bankroll"].cummax()
    rng = np.random.default_rng(0)
    flat = log["gain_flat"].to_numpy()
    boot = [rng.choice(flat, len(flat)).mean() for _ in range(2000)]
    summary = {"paris": len(log), "roi_flat_%": 100 * flat.mean(),
               "ic95_roi_flat_%": (100 * np.percentile(boot, 2.5), 100 * np.percentile(boot, 97.5)),
               "roi_kelly_%": 100 * log["gain"].sum() / log["mise"].sum(),
               "bankroll_finale": bank,
               "drawdown_max_%": 100 * ((peak - log["bankroll"]) / peak).max()}
    return log, summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--test-from", default="2023-08-01")
    ap.add_argument("--xi", type=float, default=0.0019)
    a = ap.parse_args()

    if a.synthetic:
        from synth import make_synthetic
        df = make_synthetic()
        a.test_from = "2022-08-01" if a.test_from == "2023-08-01" else a.test_from
    else:
        df = load_data()

    res = run_all(df, a.test_from, xi=a.xi)
    test = res["test"]
    src = test["mkt_src"].value_counts() if "mkt_src" in test else {}
    print(f"\nPériode de test : {test.Date.min().date()} -> {test.Date.max().date()} "
          f"({len(test)} matchs) | cotes marché : "
          + ", ".join(f"{k} {v}" for k, v in dict(src).items()))
    print("\n=== Qualité des probabilités (plus bas = mieux, IC95 bootstrap) ===")
    print(res["metrics"].round(4).to_string(index=False))
    if "mkt_src" in test and test["mkt_src"].nunique() > 1:
        print("\n=== Même tableau par source de cotes marché ===")
        for s, g in test.groupby("mkt_src"):
            m = evaluate(g)[["modèle", "log_loss", "delta_vs_marché", "delta_ic95_bas",
                             "delta_ic95_haut"]]
            print(f"-- {s} ({len(g)} matchs)\n" + m.round(4).to_string(index=False))

    print("\n=== Paris 'value' (Dixon-Coles), cotes d'exécution Bet365 si dispo ===")
    exec_cols = next(([f"{p}H", f"{p}D", f"{p}A"] for p in ("B365", "PSC")
                      if all(f"{p}{o}" in test.columns for o in "HDA")), None)
    for edge in (0.0, 0.03, 0.05, 0.10):
        _, s = value_bets(test.dropna(subset=exec_cols), COLS["Dixon-Coles"], exec_cols, edge=edge)
        if s["paris"]:
            lo, hi = s["ic95_roi_flat_%"]
            print(f"edge>{edge:>4.0%} | {s['paris']:>4} paris | ROI flat {s['roi_flat_%']:+6.1f} % "
                  f"[IC95 {lo:+.1f} ; {hi:+.1f}] | Kelly/4 : bankroll finale "
                  f"{s['bankroll_finale']:.0f}, "
                  f"drawdown max {s['drawdown_max_%']:.0f} %")
    print("\nLecture : si l'IC95 du ROI contient 0, on ne peut pas conclure à un avantage réel.")


if __name__ == "__main__":
    main()
