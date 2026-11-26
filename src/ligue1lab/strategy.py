"""Stratégie de paris value (simulation uniquement) et analyse du risque.

Aucune mise réelle n'est jamais placée : tout est calculé a posteriori sur des cotes
historiques (paper trading).

- Cotes d'exécution : ouverture Bet365 (B365H/D/A), proxy d'un bookmaker grand public.
- Ligne de clôture de référence : Pinnacle clôture sans marge (PSC*), sinon Bet365 clôture.
- Closing Line Value (CLV) d'un pari = p_clôture_sans_marge x cote_exécution - 1 : l'espérance
  du pari si la clôture est juste. Indicateur d'avantage bien moins bruité que le ROI.
- Le seuil d'avantage est choisi sur la VALIDATION (2023-24, prédictions hors-pli) ; la
  fraction de Kelly (1/4) et le plafond (2,5 % de la bankroll) sont fixés a priori.

Lancer : python -m ligue1lab.strategy   (après python -m ligue1lab.ml ; écrit artifacts/strategy/)
"""
import json

import numpy as np
import pandas as pd

from .core import OUTCOMES, PROJECT_ROOT, outcome_matrix, remove_margin

ART = PROJECT_ROOT / "artifacts"
EDGE_GRID = [0.02, 0.04, 0.06, 0.08, 0.10, 0.15]
KELLY_FRAC, CAP, MIN_BETS = 0.25, 0.025, 30
MODELS = ["Dixon-Coles", "Elo", "LightGBM"]
RUIN_LEVEL = 0.5  # « ruine » = perdre la moitié de la bankroll


def closing_fair(t: pd.DataFrame) -> np.ndarray:
    """Probas de clôture sans marge : Pinnacle si dispo, sinon Bet365 clôture."""
    out = np.full((len(t), 3), np.nan)
    for pre in ("PSC", "B365C"):
        cols = [f"{pre}{o}" for o in "HDA"]
        if not all(c in t for c in cols):
            continue
        o = t[cols].to_numpy(float)
        ok = np.isnan(out).any(1) & (o > 1).all(1)
        out[ok] = remove_margin(o[ok])
    return out


def simulate(t, model, edge, kelly_frac=KELLY_FRAC, cap=CAP, bank0=100.0,
             exec_prefix="B365"):
    """Journal des paris : au plus un pari par match, sur l'issue au plus fort EV > edge."""
    P = t[[f"{model}|{o}" for o in OUTCOMES]].to_numpy(float)
    O = t[[f"{exec_prefix}{o}" for o in "HDA"]].to_numpy(float)
    Y = outcome_matrix(t["FTR"])
    C = closing_fair(t)
    ok = (O > 1).all(1) & ~np.isnan(P).any(1)
    ev = np.where(ok[:, None], P * O - 1, -np.inf)
    best = ev.argmax(1)
    rows, bank = [], bank0
    for i in np.flatnonzero(ev[np.arange(len(t)), best] > edge):
        b = best[i]
        k = ev[i, b] / (O[i, b] - 1)
        stake = bank * min(kelly_frac * k, cap)
        win = Y[i, b] == 1
        bank += stake * (O[i, b] - 1) if win else -stake
        rows.append({"Date": t["Date"].iloc[i], "match": f"{t.HomeTeam.iloc[i]} - "
                     f"{t.AwayTeam.iloc[i]}", "issue": OUTCOMES[b], "cote": O[i, b],
                     "p_modele": P[i, b], "p_cloture": C[i, b], "ev": ev[i, b],
                     "clv": C[i, b] * O[i, b] - 1, "mise": stake,
                     "gain_flat": (O[i, b] - 1) if win else -1.0, "bankroll": bank})
    return pd.DataFrame(rows)


def boot_ci(x, n=4000, seed=0):
    x = np.asarray(x, float)
    if len(x) < 2:
        return [float("nan"), float("nan")]
    rng = np.random.default_rng(seed)
    m = x[rng.integers(0, len(x), (n, len(x)))].mean(1)
    return [float(np.quantile(m, 0.025)), float(np.quantile(m, 0.975))]


def summarize(log, bank0=100.0):
    if log.empty:
        return {"paris": 0}
    peak = np.maximum.accumulate(np.r_[bank0, log["bankroll"].to_numpy()])
    dd = (peak[1:] - log["bankroll"].to_numpy()) / peak[1:]
    return {"paris": int(len(log)), "roi_flat_%": 100 * float(log.gain_flat.mean()),
            "roi_ic95_%": [100 * v for v in boot_ci(log.gain_flat)],
            "clv_moy_%": 100 * float(np.nanmean(log.clv)),
            "clv_ic95_%": [100 * v for v in boot_ci(log.clv.dropna())],
            "part_clv_positive_%": 100 * float((log.clv > 0).mean()),
            "cote_moy": float(log.cote.mean()), "bankroll_finale": float(log.bankroll.iloc[-1]),
            "drawdown_max_%": 100 * float(dd.max())}


def choose_edge(valid, model):
    """Seuil maximisant le ROI à mise fixe sur la validation (au moins MIN_BETS paris)."""
    table = []
    for e in EDGE_GRID:
        s = summarize(simulate(valid, model, e))
        table.append({"edge": e, **{k: s.get(k) for k in ("paris", "roi_flat_%", "clv_moy_%")}})
    eligible = [r for r in table if (r["paris"] or 0) >= MIN_BETS]
    best = max(eligible, key=lambda r: r["roi_flat_%"]) if eligible else table[0]
    return best["edge"], table


def monte_carlo(log, n_paths=10000, bank0=100.0, seed=0, null_probs=False):
    """Trajectoires de bankroll en rééchantillonnant les paris (ordre et issues).

    null_probs=True : les issues sont tirées selon les probas de clôture sans marge, c.-à-d.
    le monde où le modèle n'a AUCUN avantage. Montre la variance « pure ».
    """
    rng = np.random.default_rng(seed)
    n = len(log)
    odds = log["cote"].to_numpy()
    frac = (log["mise"] / log["bankroll"].shift(1, fill_value=bank0)).to_numpy()
    if null_probs:
        p = log["p_cloture"].fillna(1 / log["cote"]).to_numpy()
    paths = np.empty((n_paths, n))
    for k in range(n_paths):
        idx = rng.integers(0, n, n)
        if null_probs:
            win = rng.random(n) < p[idx]
        else:
            win = log["gain_flat"].to_numpy()[idx] > 0
        mult = np.where(win, 1 + frac[idx] * (odds[idx] - 1), 1 - frac[idx])
        paths[k] = bank0 * np.cumprod(mult)
    peak = np.maximum.accumulate(np.c_[np.full(n_paths, bank0), paths], axis=1)[:, 1:]
    mdd = ((peak - paths) / peak).max(1)
    q = np.quantile(paths, [0.05, 0.25, 0.5, 0.75, 0.95], axis=0)
    step = max(1, n // 120)
    ruined = paths.min(1) <= RUIN_LEVEL * bank0
    return {"n_paths": n_paths, "p_ruine_%": 100 * float(ruined.mean()),
            "p_perte_%": 100 * float((paths[:, -1] < bank0).mean()),
            "bankroll_finale_q": dict(zip(["q05", "q25", "q50", "q75", "q95"],
                                          map(float, q[:, -1]), strict=True)),
            "drawdown_max_q_%": {f"q{int(100 * a):02d}": 100 * float(np.quantile(mdd, a))
                                 for a in (0.05, 0.5, 0.95)},
            "bands": {"i": list(range(0, n, step)),
                      **{name: q[j, ::step].round(2).tolist()
                         for j, name in enumerate(["q05", "q25", "q50", "q75", "q95"])}}}


MARGINS = np.arange(0, 0.105, 0.005)


def margin_sensitivity(t, model, edge, margins=MARGINS):
    """ROI à mise fixe si l'on pariait à la clôture sans marge augmentée d'une marge m.

    Cote synthétique = 1 / (p_clôture x (1 + m)). On cherche la marge à partir de laquelle
    l'IC95 du ROI passe entièrement sous 0, et le point mort du ROI moyen.
    """
    C = closing_fair(t)
    rows = []
    for m in margins:
        tt = t.copy()
        odds = 1 / (C * (1 + m))
        tt[["SYNH", "SYND", "SYNA"]] = odds
        log = simulate(tt, model, edge, exec_prefix="SYN")
        s = summarize(log)
        rows.append({"marge_%": round(100 * m, 1), "paris": s["paris"],
                     "roi_flat_%": s.get("roi_flat_%"), "roi_ic95_%": s.get("roi_ic95_%")})
    return rows


def run(verbose=True):
    V = pd.read_parquet(ART / "ml" / "valid_predictions.parquet")
    T = pd.read_parquet(ART / "ml" / "test_predictions.parquet")
    log = (lambda *a: print(*a, flush=True)) if verbose else (lambda *a: None)
    out = {"config": {"kelly_frac": KELLY_FRAC, "cap": CAP, "edge_grid": EDGE_GRID,
                      "ruin_level": RUIN_LEVEL, "exec": "B365 ouverture",
                      "closing": "PSC sans marge, sinon B365C"}, "models": {}}
    for m in MODELS:
        edge, vtable = choose_edge(V, m)
        tlog = simulate(T, m, edge)
        s = summarize(tlog)
        res = {"edge": edge, "validation": vtable, "test": s,
               "mc": monte_carlo(tlog) if len(tlog) > 5 else None,
               "mc_null": monte_carlo(tlog, null_probs=True) if len(tlog) > 5 else None,
               "margin": margin_sensitivity(T, m, edge),
               "bankroll": tlog[["Date", "bankroll"]].assign(Date=lambda x: x.Date.astype(str))
               .to_dict(orient="list") if len(tlog) else {}}
        out["models"][m] = res
        if s["paris"]:
            log(f"{m:12s} seuil {edge:.0%} | {s['paris']:3d} paris | ROI {s['roi_flat_%']:+.1f} % "
                f"[{s['roi_ic95_%'][0]:+.1f} ; {s['roi_ic95_%'][1]:+.1f}] | CLV "
                f"{s['clv_moy_%']:+.2f} % [{s['clv_ic95_%'][0]:+.2f} ; {s['clv_ic95_%'][1]:+.2f}]"
                f" | bankroll {s['bankroll_finale']:.0f} | DD max {s['drawdown_max_%']:.0f} %")
            mc = res["mc"]
            log(f"{'':12s} Monte Carlo : P(ruine = -50 %) {mc['p_ruine_%']:.1f} %, "
                f"P(perte) {mc['p_perte_%']:.0f} %, médiane finale "
                f"{mc['bankroll_finale_q']['q50']:.0f}")
    # marge du marché lui-même : un parieur qui suit le marché perd la marge
    C = closing_fair(T)
    O = T[["B365H", "B365D", "B365A"]].to_numpy(float)
    out["market_margin_b365_%"] = 100 * float(np.nanmean((1 / O).sum(1) - 1))
    out["clv_random_bet_b365_%"] = 100 * float(np.nanmean(C * O - 1))
    log(f"\nCLV moyenne d'un pari au hasard chez Bet365 (ouverture) : "
        f"{out['clv_random_bet_b365_%']:+.2f} %")
    (ART / "strategy").mkdir(parents=True, exist_ok=True)
    (ART / "strategy" / "results.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    return out


if __name__ == "__main__":
    run()
