"""Produit les données du site (web/public/data/*.json) à partir des résultats calculés.

Aucun chiffre du site n'est codé en dur : tout vient d'ici. Prérequis :
    python -m ligue1lab.ml && python -m ligue1lab.strategy && python -m ligue1lab.biases
Lancer : python make_artifacts.py
"""
import json
import subprocess
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from ligue1lab import __version__
from ligue1lab.core import PROJECT_ROOT, bookmaker_margins, load_data, market_baseline
from ligue1lab.ml import ART
from ligue1lab.models import DixonColes, elo_probs
from ligue1lab.predict import JOURNAL, fetch_fixtures, predict_fixtures
from ligue1lab.xg import load_team_map

OUT = PROJECT_ROOT / "web" / "public" / "data"
QUIZ_SIZE = 12


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=PROJECT_ROOT,
                                       text=True).strip()
    except Exception:
        return "inconnu"


def clean(o):
    """NaN / numpy -> JSON propre."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, list | tuple):
        return [clean(v) for v in o]
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, float | np.floating):
        return None if not np.isfinite(o) else round(float(o), 6)
    if isinstance(o, pd.Timestamp):
        return o.strftime("%Y-%m-%d")
    return o


def write(name, payload, meta):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(clean({"meta": meta, **payload}),
                                                 ensure_ascii=False, indent=1), encoding="utf-8")


def form_letters(df, team, n=5):
    g = df[(df.HomeTeam == team) | (df.AwayTeam == team)].tail(n)
    out = []
    for r in g.itertuples():
        gf, ga = (r.FTHG, r.FTAG) if r.HomeTeam == team else (r.FTAG, r.FTHG)
        out.append("V" if gf > ga else "N" if gf == ga else "D")
    return out


def team_card(tm, name):
    row = tm[tm.canonical == name]
    return {"name": name, "code": row.code.iloc[0] if len(row) else name[:3].upper(),
            "stadium": row.stade.iloc[0] if len(row) else None}


def main():
    ml = json.loads((ART / "ml" / "results.json").read_text(encoding="utf-8"))
    st = json.loads((ART / "strategy" / "results.json").read_text(encoding="utf-8"))
    bi = json.loads((ART / "biases" / "results.json").read_text(encoding="utf-8"))
    T = pd.read_parquet(ART / "ml" / "test_predictions.parquet")
    df = load_data()
    d, per_season, _, calib_mkt = market_baseline(df)
    tm = load_team_map()
    meta = {"generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "model_version": f"{__version__}+{git_commit()}",
            "data_period": [d.Date.min(), d.Date.max()],
            "test_period": ml["protocol"]["test_period"],
            "source": "football-data.co.uk"}

    # ---------- modèles
    metrics = ml["metrics"]
    by_name = {m["modèle"]: m for m in metrics}
    y = np.eye(3)[T["FTR"].map({"H": 0, "D": 1, "A": 2}).to_numpy()]
    cum = {}
    for name in ("Dixon-Coles", "Elo", "LightGBM", "Combinaison"):
        ll = lambda n: -np.sum(y * np.log(np.clip(T[[f"{n}|H", f"{n}|D", f"{n}|A"]]
                                                  .to_numpy(), 1e-12, 1)), 1)
        cum[name] = np.cumsum(ll("Marché") - ll(name)).round(4).tolist()
    write("models", {"protocol": ml["protocol"], "choices": ml["choices"], "metrics": metrics,
                     "metrics_pinnacle_only": ml["metrics_pinnacle_only"],
                     "encompassing": ml["encompassing"], "calibration": ml["calibration"],
                     "shap_top": ml["shap_top"],
                     "cumulative_gap": {"dates": T.Date.dt.strftime("%Y-%m-%d").tolist(),
                                        "series": cum}}, meta)

    # ---------- stratégie, biais
    write("strategy", st, meta)
    write("biases", bi, meta)

    # ---------- données / marché
    margins = bookmaker_margins(df).reset_index()
    write("market", {"per_season": per_season.to_dict(orient="records"),
                     "margins": margins.to_dict(orient="records"),
                     "calibration": calib_mkt.to_dict(orient="list"),
                     "n_matches": len(d),
                     "sources": d["mkt_src"].value_counts().to_dict()}, meta)

    # ---------- équipes (saison en cours)
    cur = df[df.Season == df.Season.max()]
    teams = sorted(set(cur.HomeTeam) | set(cur.AwayTeam))
    dc = DixonColes().fit(df)
    _, elo = elo_probs(df)
    table = {}
    for r in cur.itertuples():
        for t, gf, ga in ((r.HomeTeam, r.FTHG, r.FTAG), (r.AwayTeam, r.FTAG, r.FTHG)):
            s = table.setdefault(t, {"j": 0, "pts": 0, "bp": 0, "bc": 0})
            s["j"] += 1
            s["pts"] += 3 if gf > ga else 1 if gf == ga else 0
            s["bp"] += gf
            s["bc"] += ga
    team_rows = [{**team_card(tm, t), "elo": elo[t], "attack": dc.att_[t], "defense": -dc.dfn_[t],
                  "form": form_letters(df, t), **table[t]} for t in teams]
    team_rows.sort(key=lambda r: (-r["pts"], -(r["bp"] - r["bc"]), -r["bp"]))
    for i, r in enumerate(team_rows):
        r["rank"] = i + 1
    write("teams", {"season": df.Season.max(), "teams": team_rows,
                    "home_advantage": dc.home_, "rho": dc.rho_}, meta)

    # ---------- matchs : prochaine journée (si publiée) + dernière journée rejouée hors échantillon
    fx = fetch_fixtures()
    up = predict_fixtures(df, fx)
    upcoming = [{"date": r.Date, "time": r.Time, "home": {**team_card(tm, r.HomeTeam),
                                                          "form": form_letters(df, r.HomeTeam)},
                 "away": {**team_card(tm, r.AwayTeam), "form": form_letters(df, r.AwayTeam)},
                 "model": [r.m_H, r.m_D, r.m_A], "market": [r.mkt_H, r.mkt_D, r.mkt_A],
                 "odds": [r.odds_H, r.odds_D, r.odds_A], "market_source": r.mkt_source}
                for r in up.itertuples()]
    last_day = T.Date.max()
    last = T[T.Date >= last_day - pd.Timedelta(days=3)].merge(
        d[["Date", "HomeTeam", "AwayTeam", "Time"]], on=["Date", "HomeTeam", "AwayTeam"],
        how="left")
    DC = ["Dixon-Coles|H", "Dixon-Coles|D", "Dixon-Coles|A"]
    recent = []
    for r in last.to_dict("records"):
        before = df[df.Date < r["Date"]]
        recent.append({
            "date": r["Date"].strftime("%Y-%m-%d"), "time": r["Time"],
            "home": {**team_card(tm, r["HomeTeam"]), "form": form_letters(before, r["HomeTeam"])},
            "away": {**team_card(tm, r["AwayTeam"]), "form": form_letters(before, r["AwayTeam"])},
            "model": [r[k] for k in DC], "market": [r["pH"], r["pD"], r["pA"]],
            "odds": [r["B365H"], r["B365D"], r["B365A"]], "market_source": r["mkt_src"],
            "result": r["FTR"], "score": [int(r["FTHG"]), int(r["FTAG"])]})
    write("matches", {"model_name": "Dixon-Coles", "upcoming": upcoming, "recent": recent}, meta)

    # ---------- journal de paper trading
    j = pd.read_csv(JOURNAL) if JOURNAL.exists() else pd.DataFrame()
    write("paper_trading", {"entries": j.to_dict(orient="records")}, meta)

    # ---------- « Ma calibration » : matchs passés tirés au hasard (graine fixe) dans le test
    q = T.sample(QUIZ_SIZE, random_state=7).sort_values("Date")
    quiz = [{"id": i, "date": r["Date"].strftime("%Y-%m-%d"),
             "home": team_card(tm, r["HomeTeam"]), "away": team_card(tm, r["AwayTeam"]),
             "model": [r[k] for k in DC], "market": [r["pH"], r["pD"], r["pA"]],
             "result": r["FTR"]}
            for i, r in enumerate(q.to_dict("records"))]
    write("quiz", {"matches": quiz}, meta)

    # ---------- chiffres clés de l'accueil
    mk, best = by_name["Marché"], min((m for m in metrics if m["modèle"] != "Marché"),
                                      key=lambda m: m["log_loss"])
    lgbm = by_name["LightGBM"]
    clvs = {k: v["test"].get("clv_moy_%") for k, v in st["models"].items()}
    write("summary", {
        "n_matches": len(d), "n_test": ml["protocol"]["n_test"],
        "market_log_loss": mk["log_loss"], "market_ll_ci": [mk["ll_ic95_bas"], mk["ll_ic95_haut"]],
        "best_model": best["modèle"], "best_model_delta": best["delta_vs_marché"],
        "best_model_delta_ci": [best["delta_ic95_bas"], best["delta_ic95_haut"]],
        "lgbm_log_loss": lgbm["log_loss"], "lgbm_delta": lgbm["delta_vs_marché"],
        "lgbm_delta_ci": [lgbm["delta_ic95_bas"], lgbm["delta_ic95_haut"]],
        "pinnacle_margin_pct": float(np.nanmean(margins["PSC"])),
        "b365_margin_pct": float(np.nanmean(margins["B365"])),
        "clv_pct": clvs, "n_bias_tests": len(bi["tests"]),
        "n_bias_significant": sum(t["p_holm"] < 0.05 for t in bi["tests"]),
        "accuracy_market_pct": mk["accuracy_%"],
        "outcome_shares": d["FTR"].value_counts(normalize=True).reindex(["H", "D", "A"]).tolist(),
    }, meta)
    print(f"Artefacts écrits dans {OUT} : " + ", ".join(sorted(p.stem for p in OUT.glob("*.json"))))


if __name__ == "__main__":
    main()
