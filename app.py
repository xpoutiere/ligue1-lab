"""Outil de labo interne (le site public est dans web/). Lancer : streamlit run app.py"""
import pandas as pd
import streamlit as st

from ligue1lab.backtest import COLS, cumulative_logloss_gap, run_all, value_bets
from ligue1lab.core import load_data, market_baseline

st.set_page_config(page_title="Ligue 1 Lab", page_icon="⚽", layout="wide")
st.title("⚽ Ligue 1 Lab")
st.caption("Le marché des paris est-il battable ? Une étude statistique honnête.")

with st.sidebar:
    st.header("Paramètres")
    synthetic = st.checkbox("Données synthétiques (mode hors ligne)", value=False)
    default_from = "2022-08-01" if synthetic else "2023-08-01"
    test_from = st.date_input("Début de la période de test", pd.Timestamp(default_from))
    xi = st.slider("Décroissance Dixon-Coles ξ (par jour)", 0.0, 0.006, 0.0019, 0.0001,
                   help="0 = tous les matchs pèsent pareil. 0.0019 ≈ demi-vie d'un an.")
    st.caption("Jeu responsable : 18+, jamais plus que ce que vous pouvez perdre. "
               "Aide : joueurs-info-service.fr")


@st.cache_data(show_spinner="Chargement des données…")
def get_df(synth):
    if synth:
        from ligue1lab.synth import make_synthetic
        return make_synthetic()
    return load_data()


@st.cache_data(show_spinner="Ajustement des modèles (walk-forward)…")
def get_results(synth, start, xi):
    return run_all(get_df(synth), start, xi=xi)


df = get_df(synthetic)
d, table, prefix, calib = market_baseline(df)
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Baseline marché", "🧠 Modèles", "💰 Paris value", "🏟️ Équipes"])

# ------------------------------------------------------------------ Baseline
with tab1:
    c1, c2, c3 = st.columns(3)
    c1.metric("Matchs analysés", f"{len(d):,}")
    c2.metric("Marge moyenne du bookmaker", f"{100 * d['margin'].mean():.2f} %")
    c3.metric("Log-loss du marché",
              f"{(table['log_loss'] * table['matchs']).sum() / table['matchs'].sum():.4f}")
    st.dataframe(table.round(4), width="stretch", hide_index=True)
    st.subheader("Calibration du marché")
    st.line_chart(calib.set_index("predite")[["observee"]])
    st.caption("Plus la courbe suit la diagonale, plus les cotes sont fiables.")

res = get_results(synthetic, str(test_from), xi)
test = res["test"]

# ------------------------------------------------------------------ Modèles
with tab2:
    st.subheader("Qui prédit le mieux ? (backtest temporel strict)")
    st.caption(f"{len(test)} matchs de test. Chaque prédiction n'utilise que le passé. "
               "Log-loss et Brier : plus bas = mieux.")
    st.dataframe(res["metrics"].round(4), width="stretch", hide_index=True)
    st.bar_chart(res["metrics"].set_index("modèle")[["log_loss"]])

    st.subheader("Écart cumulé de log-loss vs marché")
    gap = pd.DataFrame({"Elo": cumulative_logloss_gap(test, COLS["Elo"]),
                        "Dixon-Coles": cumulative_logloss_gap(test, COLS["Dixon-Coles"])})
    st.line_chart(gap)
    st.caption("Au-dessus de 0 : le modèle bat le marché. Sous 0 : le marché reste meilleur.")

# ------------------------------------------------------------------ Paris
with tab3:
    st.subheader("Simulation de paris 'value' avec Dixon-Coles")
    exec_cols = next(([f"{p}H", f"{p}D", f"{p}A"] for p in ("B365", "PSC")
                      if all(f"{p}{o}" in test.columns for o in "HDA")), None)
    c1, c2, c3 = st.columns(3)
    edge = c1.slider("Seuil d'avantage (EV min)", 0.0, 0.20, 0.05, 0.01)
    kf = c2.slider("Fraction de Kelly", 0.05, 1.0, 0.25, 0.05)
    cap = c3.slider("Mise max (% bankroll)", 0.01, 0.10, 0.05, 0.01)
    log, s = value_bets(test.dropna(subset=exec_cols), COLS["Dixon-Coles"], exec_cols,
                        edge=edge, kelly_frac=kf, max_frac=cap)
    if not s["paris"]:
        st.info("Aucun pari à ce seuil.")
    else:
        lo, hi = s["ic95_roi_flat_%"]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Paris", s["paris"])
        m2.metric("ROI (mise fixe)", f"{s['roi_flat_%']:+.1f} %",
                  help=f"IC95 : [{lo:+.1f} ; {hi:+.1f}]")
        m3.metric("Bankroll finale (base 100)", f"{s['bankroll_finale']:.0f}")
        m4.metric("Drawdown max", f"{s['drawdown_max_%']:.0f} %")
        st.line_chart(log.set_index("Date")[["bankroll"]])
        verdict = ("L'IC95 du ROI contient 0 : **aucun avantage démontré**." if lo <= 0 <= hi
                   else "ROI significativement " + ("positif" if lo > 0 else "négatif") +
                   " sur cet échantillon, à confirmer hors échantillon.")
        st.markdown(f"**IC95 du ROI : [{lo:+.1f} % ; {hi:+.1f} %]** — {verdict}")
    st.caption("Cotes d'exécution : Bet365 (proxy de Betclic/Winamax). Évaluer contre les cotes de "
               "clôture Pinnacle donne la vue la plus stricte (Closing Line Value).")

# ------------------------------------------------------------------ Équipes
with tab4:
    c1, c2 = st.columns(2)
    elo = (pd.Series(res["elo_ratings"], name="Elo").sort_values(ascending=False)
           .round(0).rename_axis("équipe").reset_index())
    c1.subheader("Classement Elo")
    c1.dataframe(elo, hide_index=True, width="stretch")
    c2.subheader("Forces Dixon-Coles")
    c2.dataframe(res["dc"].strengths().round(3), hide_index=True, width="stretch")
    st.caption(f"Avantage domicile estimé : {res['dc'].home_:.3f} (log-buts) | "
               f"ρ Dixon-Coles : {res['dc'].rho_:.3f}")
