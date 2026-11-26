"use client";
// Dictionnaire simple FR / EN. Le français est la langue par défaut (rendu statique) ;
// la bascule est enregistrée dans localStorage.
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { Lang } from "./format";

const dict = {
  fr: {
    skip: "Aller au contenu",
    nav: { home: "Accueil", matches: "Matchs", models: "Modèles", strategy: "Stratégie", biases: "Biais", teams: "Équipes", journal: "Journal", quiz: "Ma calibration", method: "Méthodo" },
    github: "Code source",
    menu: "Menu", close: "Fermer",
    theme: { toDark: "Passer en thème sombre", toLight: "Passer en thème clair" },
    lang: "English",
    banner: "18+ · Projet éducatif, aucune garantie de gain · Ne misez que ce que vous pouvez vous permettre de perdre · Aide : joueurs-info-service.fr (09 74 75 13 13)",
    footer: { built: "Données football-data.co.uk · Généré le", version: "version du modèle", noAdvice: "Aucun conseil de mise. Aucune mise réelle n'est placée par ce projet : simulation et paper trading uniquement.", rights: "Aucun logo ni photo : les clubs sont représentés par un code et un monogramme." },
    home: {
      kicker: "Ligue 1 Lab",
      title1: "Le marché des paris", title2: "est-il", accent: "battable", title3: " ?",
      pills: ["Statistiques", "Machine learning", "Biais cognitifs"],
      lead: "Une étude honnête sur la Ligue 1 depuis 2019 : des modèles statistiques et d'apprentissage automatique confrontés aux cotes de clôture, avec intervalles de confiance et un test final unique.",
      verdictTitle: "Verdict",
      verdict: (best: string) => `Non, pas avec ces données. Aucun modèle ne fait mieux que le marché ; le meilleur (${best}) se contente de le recopier.`,
      tiles: { market: "Log-loss du marché (test)", gap: "Écart du LightGBM au marché", margin: "Marge moyenne Pinnacle", tested: "Matchs du test final" },
      mosaic: { calib: "Calibration du marché", bankroll: "Bankroll simulée (Dixon-Coles)", gap: "Log-loss cumulée vs marché", pitch: "Issues des matchs" },
      sections: { recent: "Dernière journée", findings: "Ce qu'on a appris" },
      findings: [
        { t: "Le marché est très bien calibré", d: "Les probabilités implicites de clôture collent aux fréquences observées à moins de 2 points près." },
        { t: "Les modèles ne battent pas la clôture", d: "Elo, Dixon-Coles, logistique, LightGBM : tous ont une log-loss significativement moins bonne que le marché." },
        { t: "La CLV tranche", d: "Les « value bets » des modèles ont une Closing Line Value d'environ −5 %, comme un pari au hasard." },
        { t: "Pas de biais exploitable", d: "Favori-outsider, séries, popularité, matchs médiatisés : aucun effet significatif après correction multiple." },
      ],
      more: "Lire la suite",
    },
    common: { model: "Modèle", market: "Marché", gap: "Écart", home: "Domicile", draw: "Nul", away: "Extérieur", vs: "VS", odds: "Cotes", form: "Forme", round: "Journée", ligue1: "Ligue 1", logloss: "Log-loss", brier: "Brier", accuracy: "Précision", ci: "IC95", n: "n", lower: "plus bas = mieux", source: "Source", pts: "pts", empty: "Rien à afficher pour l'instant.", testPeriod: "Période de test", generated: "Généré le", seeMethod: "Voir la méthodologie" },
    matches: {
      title: "Matchs de la journée",
      lead: "Probabilités du modèle (Dixon-Coles) face au marché (cotes sans marge). Lecture seule : aucun conseil de mise, aucun score prédit.",
      upcoming: "Prochaine journée",
      noUpcoming: "La prochaine journée n'est pas encore publiée par football-data.co.uk. Elle apparaîtra ici après la prochaine mise à jour hebdomadaire.",
      recent: "Dernière journée jouée (prédictions hors échantillon)",
      recentNote: "Prédictions walk-forward faites uniquement avec les matchs antérieurs, comparées au résultat.",
      myPick: "Mon pronostic", myPickNote: "Enregistré seulement dans ce navigateur, pour comparer votre lecture au modèle.",
      result: "Résultat", modelVsMarket: "Modèle vs Marché", diff: "Écart modèle − marché",
    },
    models: { title: "Modèles", lead: "Tous les modèles évalués sur le même test final, jamais utilisé pour faire un choix.", table: "Comparatif (test final)", pinnacle: "Sous-échantillon Pinnacle seul", calib: "Calibration", cum: "Log-loss cumulée : marché − modèle", cumNote: "Sous 0 : le marché fait mieux. La courbe descend : l'écart se creuse avec le temps.", enc: "Le modèle apporte-t-il de l'information au-delà du marché ?", encNote: "On ajuste p ∝ p_marché^a · p_modèle^b. Si b est nul, le modèle n'ajoute rien.", shap: "Importance des variables (SHAP, LightGBM)", protocol: "Protocole", choices: "Choix faits sur la validation" },
    strategy: { title: "Stratégie et risque", lead: "Simulation de paris « value » aux cotes Bet365, Kelly 1/4 plafonné. Aucune mise réelle.", clv: "Closing Line Value", bankroll: "Bankroll simulée : 10 000 trajectoires", margin: "Sensibilité à la marge du bookmaker", marginNote: "ROI si l'on pariait à la clôture augmentée d'une marge m. Même à 0 %, il reste négatif : il n'y a pas d'avantage à faire disparaître.", ruin: "Probabilité de perdre la moitié de la bankroll", perte: "Probabilité de finir en perte", random: "CLV d'un pari au hasard chez Bet365" },
    biases: { title: "Biais cognitifs", lead: "Les parieurs ont des biais documentés. Laissent-ils des traces exploitables dans les cotes ?", byOdds: "ROI par tranche de cote (biais favori-outsider)", hyp: "Hypothèse", effect: "Résidu (points de probabilité)", verdict: "Verdict", note: "Résidu = issue réalisée − probabilité de clôture sans marge. Corrections de Holm (taux d'erreur familial) et Benjamini-Hochberg." },
    teams: { title: "Équipes", lead: "Saison en cours : classement, Elo, forces Dixon-Coles (attaque et défense en log-buts) et forme récente.", rank: "Rang", pts: "Pts", played: "J", gd: "Diff.", elo: "Elo", attack: "Attaque", defense: "Défense" },
    journal: { title: "Journal de paper trading", lead: "Chaque semaine, les prédictions sont horodatées AVANT les matchs, puis le résultat est ajouté. Rien n'est réécrit : l'historique git en fait foi.", empty: "Le journal démarre avec la prochaine journée publiée : aucune prédiction n'a encore été enregistrée avant un match. Nous ne remplissons pas le passé après coup.", predictedAt: "Prédit le", match: "Match" },
    quiz: { title: "Ma calibration", lead: "Estimez les probabilités de quelques matchs passés, puis comparez votre score de Brier à celui du modèle et du marché. Tout reste dans votre navigateur.", start: "Voir mon score", reset: "Recommencer", you: "Vous", score: "Score de Brier (plus bas = mieux)", sumWarn: "Les trois probabilités doivent faire 100 %.", answered: "matchs estimés" },
    method: { title: "Méthodologie et limites" },
    design: { title: "Bibliothèque de composants" },
  },
  en: {
    skip: "Skip to content",
    nav: { home: "Home", matches: "Matches", models: "Models", strategy: "Strategy", biases: "Biases", teams: "Teams", journal: "Journal", quiz: "My calibration", method: "Method" },
    github: "Source code",
    menu: "Menu", close: "Close",
    theme: { toDark: "Switch to dark theme", toLight: "Switch to light theme" },
    lang: "Français",
    banner: "18+ · Educational project, no guarantee of profit · Only bet what you can afford to lose · Help (France): joueurs-info-service.fr",
    footer: { built: "Data football-data.co.uk · Generated on", version: "model version", noAdvice: "No betting advice. This project never places real bets: simulation and paper trading only.", rights: "No logos or photos: clubs are shown with a code and a monogram." },
    home: {
      kicker: "Ligue 1 Lab",
      title1: "Can the betting", title2: "market be", accent: "beaten", title3: "?",
      pills: ["Statistics", "Machine learning", "Cognitive biases"],
      lead: "An honest study of Ligue 1 since 2019: statistical and machine-learning models against closing odds, with confidence intervals and a single final test.",
      verdictTitle: "Verdict",
      verdict: (best: string) => `No, not with this data. No model beats the market; the best one (${best}) simply copies it.`,
      tiles: { market: "Market log-loss (test)", gap: "LightGBM gap to market", margin: "Average Pinnacle margin", tested: "Matches in final test" },
      mosaic: { calib: "Market calibration", bankroll: "Simulated bankroll (Dixon-Coles)", gap: "Cumulative log-loss vs market", pitch: "Match outcomes" },
      sections: { recent: "Latest round", findings: "What we learned" },
      findings: [
        { t: "The market is very well calibrated", d: "Closing implied probabilities match observed frequencies within 2 points." },
        { t: "Models do not beat the close", d: "Elo, Dixon-Coles, logistic, LightGBM: all have a significantly worse log-loss than the market." },
        { t: "CLV settles it", d: "The models' value bets have a Closing Line Value around −5%, like random bets." },
        { t: "No exploitable bias", d: "Favourite-longshot, streaks, popularity, big matches: no significant effect after multiple-testing correction." },
      ],
      more: "Read more",
    },
    common: { model: "Model", market: "Market", gap: "Gap", home: "Home", draw: "Draw", away: "Away", vs: "VS", odds: "Odds", form: "Form", round: "Round", ligue1: "Ligue 1", logloss: "Log-loss", brier: "Brier", accuracy: "Accuracy", ci: "95% CI", n: "n", lower: "lower is better", source: "Source", pts: "pts", empty: "Nothing to show yet.", testPeriod: "Test period", generated: "Generated on", seeMethod: "See methodology" },
    matches: {
      title: "Matches of the round",
      lead: "Model (Dixon-Coles) probabilities against the market (margin-free odds). Read only: no betting advice, no predicted score.",
      upcoming: "Next round",
      noUpcoming: "The next round has not been published by football-data.co.uk yet. It will appear after the next weekly update.",
      recent: "Latest round played (out-of-sample predictions)",
      recentNote: "Walk-forward predictions using only earlier matches, compared with the result.",
      myPick: "My pick", myPickNote: "Stored only in this browser, to compare your read with the model.",
      result: "Result", modelVsMarket: "Model vs Market", diff: "Model − market gap",
    },
    models: { title: "Models", lead: "All models evaluated on the same final test, never used to make a choice.", table: "Comparison (final test)", pinnacle: "Pinnacle-only subsample", calib: "Calibration", cum: "Cumulative log-loss: market − model", cumNote: "Below 0: the market does better. A falling curve: the gap widens over time.", enc: "Does the model add information beyond the market?", encNote: "We fit p ∝ p_market^a · p_model^b. If b is zero, the model adds nothing.", shap: "Feature importance (SHAP, LightGBM)", protocol: "Protocol", choices: "Choices made on validation" },
    strategy: { title: "Strategy and risk", lead: "Simulated value betting at Bet365 odds, capped quarter Kelly. No real money.", clv: "Closing Line Value", bankroll: "Simulated bankroll: 10,000 paths", margin: "Sensitivity to bookmaker margin", marginNote: "ROI when betting at the closing line plus a margin m. Even at 0% it stays negative: there is no edge to erode.", ruin: "Probability of losing half the bankroll", perte: "Probability of ending at a loss", random: "CLV of a random Bet365 bet" },
    biases: { title: "Cognitive biases", lead: "Bettors have documented biases. Do they leave exploitable traces in the odds?", byOdds: "ROI by odds band (favourite-longshot bias)", hyp: "Hypothesis", effect: "Residual (probability points)", verdict: "Verdict", note: "Residual = realised outcome − margin-free closing probability. Holm (family-wise) and Benjamini-Hochberg corrections." },
    teams: { title: "Teams", lead: "Current season: table, Elo, Dixon-Coles strengths (attack and defence in log-goals) and recent form.", rank: "Rank", pts: "Pts", played: "P", gd: "GD", elo: "Elo", attack: "Attack", defense: "Defence" },
    journal: { title: "Paper trading journal", lead: "Every week, predictions are time-stamped BEFORE kick-off, then the result is added. Nothing is rewritten: git history is the proof.", empty: "The journal starts with the next published round: no prediction has been logged before a match yet. We do not back-fill the past.", predictedAt: "Predicted at", match: "Match" },
    quiz: { title: "My calibration", lead: "Estimate the probabilities of a few past matches, then compare your Brier score with the model and the market. Everything stays in your browser.", start: "Show my score", reset: "Start again", you: "You", score: "Brier score (lower is better)", sumWarn: "The three probabilities must add up to 100%.", answered: "matches estimated" },
    method: { title: "Methodology and limitations" },
    design: { title: "Component library" },
  },
};

export type Dict = (typeof dict)["fr"];
const Ctx = createContext<{ lang: Lang; t: Dict; setLang: (l: Lang) => void }>({
  lang: "fr", t: dict.fr, setLang: () => {},
});

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("fr");
  useEffect(() => {
    try {
      const saved = localStorage.getItem("lang");
      // eslint-disable-next-line react-hooks/set-state-in-effect -- lecture d'une préférence locale après hydratation
      if (saved === "en" || saved === "fr") setLangState(saved);
    } catch {}
  }, []);
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);
  const setLang = (l: Lang) => {
    setLangState(l);
    try { localStorage.setItem("lang", l); } catch {}
  };
  return <Ctx.Provider value={{ lang, t: dict[lang] as Dict, setLang }}>{children}</Ctx.Provider>;
}

export const useI18n = () => useContext(Ctx);
