"""Modèles ML et évaluation finale contre le marché.

Protocole (fixé AVANT de regarder le test, voir docs/DECISIONS.md) :
- 2019-20 : rodage (Elo, Dixon-Coles et formes se construisent), jamais utilisé pour apprendre ;
- apprentissage : 2020-21 à 2022-23 ;
- validation : 2023-24, et validation croisée temporelle par saison (plis 2022-23 et 2023-24)
  pour TOUS les choix : hyperparamètres, méthode de calibration, poids de la combinaison ;
- test final, utilisé UNE seule fois : 2024-25 -> saison en cours.

Lancer : python -m ligue1lab.ml   (écrit artifacts/ml/)
"""
import json
import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import log_softmax, softmax
from scipy.stats import chi2
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .backtest import evaluate
from .core import (
    PROJECT_ROOT,
    calibration_table,
    load_data,
    market_baseline,
    match_log_loss,
    outcome_matrix,
)
from .features import build_features

SEED = 42
BURN_IN = ["1920"]
TRAIN = ["2021", "2122", "2223"]
VALID = ["2324"]
CV_FOLDS = [(["2021", "2122"], ["2223"]), (["2021", "2122", "2223"], ["2324"])]
ART = PROJECT_ROOT / "artifacts"
ODDS_COLS = [f"{b}{o}" for b in ("B365", "B365C", "PSC", "PS", "Avg", "AvgC", "Max", "MaxC")
             for o in "HDA"]
KEEP_COLS = ["Date", "Kickoff", "Season", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR",
             "mkt_src", "pH", "pD", "pA", *ODDS_COLS]
P3 = {"Marché": ["pH", "pD", "pA"], "Elo": ["eH", "eD", "eA"], "Dixon-Coles": ["dH", "dD", "dA"]}


# ------------------------------------------------------------------ données
def load_dataset(cache=True) -> tuple[pd.DataFrame, list[str]]:
    """Matchs + baseline marché + features (cache parquet dans artifacts/)."""
    ART.mkdir(exist_ok=True)
    path = ART / "dataset.parquet"
    df = load_data()
    d, *_ = market_baseline(df)
    if cache and path.exists():
        cached = pd.read_parquet(path)
        if len(cached) == len(d) and cached["Kickoff"].max() == d["Kickoff"].max():
            return cached, json.loads((ART / "feature_cols.json").read_text(encoding="utf-8"))
    F = build_features(df).loc[d.index]
    feat_cols = [c for c in F.columns if c not in ("dH", "dD", "dA", "eH", "eD", "eA")]
    out = pd.concat([d, F], axis=1)
    out.to_parquet(path)
    (ART / "feature_cols.json").write_text(json.dumps(feat_cols), encoding="utf-8")
    return out, feat_cols


def split(data):
    s = data["Season"]
    test_seasons = sorted(set(s) - set(BURN_IN + TRAIN + VALID))
    return {"train": data[s.isin(TRAIN)], "valid": data[s.isin(VALID)],
            "trainval": data[s.isin(TRAIN + VALID)], "test": data[s.isin(test_seasons)],
            "test_seasons": test_seasons}


def y_of(d):
    return outcome_matrix(d["FTR"]).argmax(1)


def mean_ll(p, y):
    return float(match_log_loss(p, np.eye(3)[y]).mean())


# ------------------------------------------------------------------ modèles
def make_logit(C):
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                         LogisticRegression(C=C, max_iter=5000))


def fit_lgbm(X, y, params, n_estimators):
    m = lgb.LGBMClassifier(objective="multiclass", n_estimators=n_estimators,
                           random_state=SEED, verbose=-1, subsample_freq=1, **params)
    return m.fit(X, y)


LOGIT_GRID = [0.001, 0.003, 0.01, 0.03, 0.1, 0.3]
LGBM_GRID = [{"num_leaves": nl, "learning_rate": lr, "min_child_samples": mcs,
              "subsample": 0.8, "colsample_bytree": 0.5, "reg_lambda": 5.0}
             for nl in (4, 8, 16) for lr in (0.01, 0.03) for mcs in (40, 100)]


def tune_logit(data, cols):
    scores = {}
    for C in LOGIT_GRID:
        lls = [mean_ll(make_logit(C).fit(data[data.Season.isin(tr)][cols],
                                         y_of(data[data.Season.isin(tr)]))
                       .predict_proba(data[data.Season.isin(va)][cols]),
                       y_of(data[data.Season.isin(va)])) for tr, va in CV_FOLDS]
        scores[C] = float(np.mean(lls))
    best = min(scores, key=scores.get)
    return best, scores


def tune_lgbm(data, cols):
    """Grille + arrêt précoce sur chaque pli ; nombre d'arbres = moyenne des meilleurs."""
    results = []
    for params in LGBM_GRID:
        lls, iters = [], []
        for tr, va in CV_FOLDS:
            a, b = data[data.Season.isin(tr)], data[data.Season.isin(va)]
            m = lgb.LGBMClassifier(objective="multiclass", n_estimators=3000,
                                   random_state=SEED, verbose=-1, subsample_freq=1, **params)
            m.fit(a[cols], y_of(a), eval_X=b[cols], eval_y=y_of(b),
                  callbacks=[lgb.early_stopping(100, verbose=False)])
            iters.append(m.best_iteration_ or 3000)
            lls.append(mean_ll(m.predict_proba(b[cols], num_iteration=m.best_iteration_),
                               y_of(b)))
        results.append({"params": params, "cv_log_loss": float(np.mean(lls)),
                        "n_estimators": int(np.mean(iters))})
    best = min(results, key=lambda r: r["cv_log_loss"])
    return best, results


def oof_predictions(data, factory, cols):
    """Prédictions hors-pli des saisons de validation des plis temporels."""
    parts = []
    for tr, va in CV_FOLDS:
        a, b = data[data.Season.isin(tr)], data[data.Season.isin(va)]
        parts.append(pd.DataFrame(factory().fit(a[cols], y_of(a)).predict_proba(b[cols]),
                                  index=b.index))
    return pd.concat(parts)


# ------------------------------------------------------------------ calibration
class Calibrator:
    """'platt' : régression logistique multinomiale sur les log-probas (vector scaling) ;
    'isotonic' : isotonique un-contre-tous puis renormalisation."""

    def __init__(self, method):
        self.method = method

    def fit(self, p, y):
        if self.method == "platt":
            self.m = LogisticRegression(C=1.0, max_iter=2000).fit(np.log(np.clip(p, 1e-6, 1)), y)
        else:
            self.m = [IsotonicRegression(out_of_bounds="clip", y_min=1e-4, y_max=1 - 1e-4)
                      .fit(p[:, k], (y == k).astype(float)) for k in range(3)]
        return self

    def transform(self, p):
        if self.method == "platt":
            return self.m.predict_proba(np.log(np.clip(p, 1e-6, 1)))
        q = np.column_stack([iso.predict(p[:, k]) for k, iso in enumerate(self.m)])
        return q / q.sum(1, keepdims=True)


def choose_calibration(oof, data):
    """Calibrateur ajusté sur le pli 2022-23, évalué sur 2023-24 (hors-pli) ; on garde le
    meilleur entre aucun / Platt / isotonique."""
    s = data.loc[oof.index, "Season"]
    fit_idx, ev_idx = oof.index[s == "2223"], oof.index[s == "2324"]
    yf, ye = y_of(data.loc[fit_idx]), y_of(data.loc[ev_idx])
    scores = {"aucune": mean_ll(oof.loc[ev_idx].to_numpy(), ye)}
    for meth in ("platt", "isotonic"):
        cal = Calibrator(meth).fit(oof.loc[fit_idx].to_numpy(), yf)
        scores[meth] = mean_ll(cal.transform(oof.loc[ev_idx].to_numpy()), ye)
    return min(scores, key=scores.get), scores


# ------------------------------------------------------------------ combinaison / encompassing
def fit_log_pool(P_list, y):
    """Poids w >= 0 d'un mélange log-linéaire softmax(sum w_k log p_k), ajusté par MV."""
    L = np.stack([np.log(np.clip(p, 1e-9, 1)) for p in P_list])  # k x n x 3

    def nll(w):
        z = np.tensordot(w, L, 1)
        return -log_softmax(z, axis=1)[np.arange(len(y)), y].sum()

    res = minimize(nll, np.full(len(P_list), 1 / len(P_list)), method="L-BFGS-B",
                   bounds=[(0, 3)] * len(P_list))
    return res.x, res.fun


def apply_log_pool(w, P_list):
    return softmax(np.tensordot(w, np.stack([np.log(np.clip(p, 1e-9, 1)) for p in P_list]), 1),
                   axis=1)


def encompassing_test(p_market, p_model, y, n_boot=1000, seed=SEED):
    """Le modèle apporte-t-il de l'information au-delà du marché ?

    On ajuste p ∝ p_marché^a · p_modèle^b par maximum de vraisemblance, puis test du rapport
    de vraisemblance de H0 : b = 0 (1 ddl). IC95 bootstrap de b.
    """
    def nll(params, Lm, Lo, yy):
        z = params[0] * Lm + params[1] * Lo
        return -log_softmax(z, axis=1)[np.arange(len(yy)), yy].sum()

    Lm, Lo = np.log(np.clip(p_market, 1e-9, 1)), np.log(np.clip(p_model, 1e-9, 1))
    full = minimize(nll, [1.0, 0.0], args=(Lm, Lo, y), method="BFGS")
    null = minimize(lambda a: nll([a[0], 0.0], Lm, Lo, y), [1.0], method="BFGS")
    lr = 2 * (null.fun - full.fun)
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(n_boot):
        i = rng.integers(0, len(y), len(y))
        bs.append(minimize(nll, full.x, args=(Lm[i], Lo[i], y[i]), method="BFGS").x[1])
    return {"a_marche": float(full.x[0]), "b_modele": float(full.x[1]),
            "b_ic95": [float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))],
            "lr_stat": float(lr), "p_value": float(chi2.sf(max(lr, 0), 1))}


def holm(pvals: dict) -> dict:
    """Correction de Holm-Bonferroni (contrôle du taux d'erreur familial)."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, running = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out


def bootstrap_p_better(ll_model, ll_market, n_boot=5000, seed=SEED):
    """p-valeur unilatérale bootstrap de H0 : le modèle n'est pas meilleur que le marché."""
    d = np.asarray(ll_model) - np.asarray(ll_market)
    rng = np.random.default_rng(seed)
    means = d[rng.integers(0, len(d), (n_boot, len(d)))].mean(1)
    return float((means >= 0).mean())  # part des rééchantillons où le modèle n'est pas meilleur


# ------------------------------------------------------------------ pipeline complet
def run(verbose=True):
    warnings.filterwarnings("ignore", category=UserWarning)
    data, feat_cols = load_dataset()
    data = data[~data.Season.isin(BURN_IN)]
    sp = split(data)
    tv, test = sp["trainval"], sp["test"]
    y_test = y_of(test)
    log = (lambda *a: print(*a, flush=True)) if verbose else (lambda *a: None)
    log(f"apprentissage {len(sp['train'])} | validation {len(sp['valid'])} | "
        f"test {len(test)} matchs ({', '.join(sp['test_seasons'])})")

    # 1) choix sur validation uniquement
    C, logit_cv = tune_logit(tv, feat_cols)
    log(f"logistique : C = {C}")
    best_lgbm, lgbm_cv = tune_lgbm(tv, feat_cols)
    log(f"LightGBM : {best_lgbm['params']} | {best_lgbm['n_estimators']} arbres")
    mk_lgbm = lambda: lgb.LGBMClassifier(objective="multiclass", random_state=SEED, verbose=-1,
                                         subsample_freq=1,
                                         n_estimators=best_lgbm["n_estimators"],
                                         **best_lgbm["params"])
    oof_lgbm = oof_predictions(tv, mk_lgbm, feat_cols)
    cal_method, cal_scores = choose_calibration(oof_lgbm, tv)
    log(f"calibration retenue : {cal_method} {cal_scores}")
    # combinaison : poids appris sur les prédictions hors-pli de 2023-24
    va_idx = oof_lgbm.index[tv.loc[oof_lgbm.index, "Season"] == "2324"]
    va = tv.loc[va_idx]
    pool_inputs_va = [va[P3["Marché"]].to_numpy(), va[P3["Dixon-Coles"]].to_numpy(),
                      va[P3["Elo"]].to_numpy(), oof_lgbm.loc[va_idx].to_numpy()]
    w_pool, _ = fit_log_pool(pool_inputs_va, y_of(va))
    V = va[KEEP_COLS].copy()  # prédictions hors-pli de validation (pour la stratégie)
    for name, arr in zip(["Marché", "Dixon-Coles", "Elo", "LightGBM"], pool_inputs_va,
                         strict=True):
        V[[f"{name}|H", f"{name}|D", f"{name}|A"]] = arr
    log(f"poids combinaison (marché, DC, Elo, GBM) : {np.round(w_pool, 3)}")
    mkt_cols = feat_cols + ["pH", "pD", "pA"]
    mk_lgbm_mkt = lambda: lgb.LGBMClassifier(objective="multiclass", random_state=SEED,
                                             verbose=-1, subsample_freq=1,
                                             n_estimators=best_lgbm["n_estimators"],
                                             **best_lgbm["params"])

    # 2) modèles finaux réentraînés sur apprentissage + validation, test UNE fois
    ytv = y_of(tv)
    p = {}
    freq = np.bincount(ytv, minlength=3) / len(ytv)
    p["Fréquences"] = np.tile(freq, (len(test), 1))
    for k, cols in P3.items():
        p[k] = test[cols].to_numpy()
    logit = make_logit(C).fit(tv[feat_cols], ytv)
    p["Logistique"] = logit.predict_proba(test[feat_cols])
    gbm = mk_lgbm().fit(tv[feat_cols], ytv)
    p["LightGBM"] = gbm.predict_proba(test[feat_cols])
    if cal_method != "aucune":
        p["LightGBM calibré"] = (Calibrator(cal_method)
                                 .fit(oof_lgbm.to_numpy(), y_of(tv.loc[oof_lgbm.index]))
                                 .transform(p["LightGBM"]))
    else:
        p["LightGBM calibré"] = p["LightGBM"]
    p["Combinaison"] = apply_log_pool(w_pool, [p["Marché"], p["Dixon-Coles"], p["Elo"],
                                               p["LightGBM"]])
    p["LightGBM + marché"] = mk_lgbm_mkt().fit(tv[mkt_cols], ytv).predict_proba(test[mkt_cols])

    # 3) évaluation
    names = list(p)
    cols = {n: [f"{n}|H", f"{n}|D", f"{n}|A"] for n in names}
    T = test[KEEP_COLS].copy()
    for n in names:
        T[cols[n]] = p[n]
    metrics = evaluate(T, cols={"Marché": cols["Marché"],
                                **{n: cols[n] for n in names if n != "Marché"}})
    yoh = np.eye(3)[y_test]
    ll_mkt = match_log_loss(p["Marché"], yoh)
    pv = {n: bootstrap_p_better(match_log_loss(p[n], yoh), ll_mkt)
          for n in names if n != "Marché"}
    pv_holm = holm(pv)
    metrics["p_mieux_que_marché"] = metrics["modèle"].map(pv)
    metrics["p_holm"] = metrics["modèle"].map(pv_holm)
    psc = (test["mkt_src"] == "PSC").to_numpy()
    metrics_psc = evaluate(T[psc], cols={"Marché": cols["Marché"],
                                         **{n: cols[n] for n in names if n != "Marché"}})
    enc = {n: encompassing_test(p["Marché"], p[n], y_test)
           for n in ("Elo", "Dixon-Coles", "Logistique", "LightGBM calibré")}
    calib = {n: calibration_table(p[n], yoh).to_dict(orient="list")
             for n in ("Marché", "LightGBM", "LightGBM calibré", "Dixon-Coles")}

    # 4) SHAP (LightGBM final, sur le test)
    import shap

    sv = shap.TreeExplainer(gbm).shap_values(test[feat_cols])
    sv = np.stack(sv, axis=-1) if isinstance(sv, list) else sv  # n x f x 3
    imp = pd.Series(np.abs(sv).mean(axis=(0, 2)), index=feat_cols).sort_values(ascending=False)
    gain = pd.Series(gbm.booster_.feature_importance("gain"), index=feat_cols)

    out = {"protocol": {"burn_in": BURN_IN, "train": TRAIN, "valid": VALID,
                        "test": sp["test_seasons"], "n_train": len(sp["train"]),
                        "n_valid": len(sp["valid"]), "n_test": len(test),
                        "test_period": [str(test.Date.min().date()), str(test.Date.max().date())],
                        "n_test_pinnacle": int(psc.sum())},
           "choices": {"logit_C": C, "logit_cv": logit_cv, "lgbm": best_lgbm,
                       "lgbm_cv_top5": sorted(lgbm_cv, key=lambda r: r["cv_log_loss"])[:5],
                       "calibration": cal_method, "calibration_scores": cal_scores,
                       "pool_weights": dict(zip(["Marché", "Dixon-Coles", "Elo", "LightGBM"],
                                                map(float, w_pool), strict=True))},
           "metrics": metrics.to_dict(orient="records"),
           "metrics_pinnacle_only": metrics_psc.to_dict(orient="records"),
           "encompassing": enc, "calibration": calib,
           "shap_top": imp.head(20).round(5).to_dict(),
           "gain_top": (gain / gain.sum()).sort_values(ascending=False).head(20).round(4).to_dict()}
    (ART / "ml").mkdir(parents=True, exist_ok=True)
    (ART / "ml" / "results.json").write_text(json.dumps(out, indent=1, ensure_ascii=False,
                                                        default=float), encoding="utf-8")
    T.to_parquet(ART / "ml" / "test_predictions.parquet")
    V.to_parquet(ART / "ml" / "valid_predictions.parquet")
    log("\n=== Test final (log-loss, IC95, écart apparié au marché, p Holm) ===")
    show = metrics[["modèle", "log_loss", "ll_ic95_bas", "ll_ic95_haut", "delta_vs_marché",
                    "delta_ic95_bas", "delta_ic95_haut", "brier", "accuracy_%", "p_holm"]]
    log(show.round(4).to_string(index=False))
    log("\nPinnacle seulement :")
    log(metrics_psc[["modèle", "log_loss", "delta_vs_marché", "delta_ic95_bas",
                     "delta_ic95_haut"]].round(4).to_string(index=False))
    log("\nEncompassing (b = poids du modèle en plus du marché) :")
    for n, e in enc.items():
        log(f"  {n:18s} a={e['a_marche']:.2f} b={e['b_modele']:+.2f} "
            f"IC95 [{e['b_ic95'][0]:+.2f} ; {e['b_ic95'][1]:+.2f}] p={e['p_value']:.3f}")
    log("\nSHAP, top 10 :\n" + imp.head(10).round(4).to_string())
    return out


if __name__ == "__main__":
    run()
