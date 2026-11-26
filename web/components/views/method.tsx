"use client";
import { Card, PageHeader } from "@/components/ui";
import { useI18n } from "@/lib/i18n";

const FR = [
  ["Question", "Les cotes de clôture de la Ligue 1, une fois la marge retirée, sont-elles des probabilités qu'un modèle public peut battre ? Une réponse négative bien démontrée est un résultat valable."],
  ["Données", "football-data.co.uk, saisons 2019-20 à 2026-27 : résultats, tirs, cotes d'ouverture et de clôture. Pinnacle n'y est plus publié depuis le 16/01/2026 : la baseline prend alors la clôture Bet365, et les résultats sont aussi donnés sur le sous-échantillon Pinnacle. Pas de xG historiques (Understat indisponible, FBref n'en affiche plus) : les tirs et tirs cadrés les remplacent."],
  ["Probabilités du marché", "p_i = (1/o_i) / Σ_j (1/o_j) : normalisation proportionnelle. La marge (somme des 1/o − 1) vaut environ 2,8 % chez Pinnacle et 5,5 % chez Bet365."],
  ["Modèles", "Elo séquentiel (logit ordonné pour le nul) ; Dixon-Coles (Poisson attaque × défense × domicile, correction ρ des petits scores, pondération temporelle e^(−ξ·jours), ξ = 0,0019) réajusté tous les 28 jours en walk-forward ; régression logistique multinomiale et LightGBM sur 130 features point-in-time ; calibration de Platt ou isotonique ; pool log-linéaire des modèles."],
  ["Protocole sans fuite", "Toute feature d'un match n'utilise que des matchs terminés avant son coup d'envoi. Des tests automatiques le prouvent : brouiller les résultats futurs ne change aucune prédiction passée. Rodage 2019-20, apprentissage 2020-21 à 2022-23, validation 2023-24 (et validation croisée temporelle), test final unique de 2024-25 à aujourd'hui."],
  ["Évaluation", "Log-loss et Brier avec IC95 par bootstrap, écart apparié au marché, p-valeurs corrigées par Holm ; test d'encompassing p ∝ p_marché^a · p_modèle^b (rapport de vraisemblance sur b = 0)."],
  ["Stratégie", "Simulation seulement : EV = p·o − 1, Kelly fractionné (1/4) plafonné à 2,5 %, seuil choisi sur validation. Closing Line Value = p_clôture · o_exécution − 1. Monte Carlo de 10 000 trajectoires."],
  ["Biais cognitifs", "Sept hypothèses fixées à l'avance (favori-outsider, main chaude, erreur du joueur, popularité, domicile, matchs médiatisés). Mesure : issue − probabilité de clôture. Corrections de Holm et Benjamini-Hochberg."],
  ["Limites", "Taille d'échantillon (711 matchs de test : un écart de 0,01 de log-loss reste difficile à détecter) ; non-stationnarité (effectifs, entraîneurs, format à 18 clubs depuis 2023) ; marge et cotes réellement disponibles pour un parieur différentes de Bet365 ; absence de xG et de compositions d'équipe ; changement de baseline en 2026."],
] as const;

const EN = [
  ["Question", "Once the margin is removed, are Ligue 1 closing odds probabilities that a public model can beat? A well-demonstrated negative answer is a valid result."],
  ["Data", "football-data.co.uk, seasons 2019-20 to 2026-27: results, shots, opening and closing odds. Pinnacle has not been published since 16/01/2026: the baseline then uses Bet365 closing odds, and results are also reported on the Pinnacle-only subsample. No historical xG (Understat unavailable, FBref no longer shows it): shots and shots on target replace it."],
  ["Market probabilities", "p_i = (1/o_i) / Σ_j (1/o_j): proportional normalisation. The margin (sum of 1/o − 1) is about 2.8% at Pinnacle and 5.5% at Bet365."],
  ["Models", "Sequential Elo (ordered logit for draws); Dixon-Coles (Poisson attack × defence × home, ρ low-score correction, time decay e^(−ξ·days), ξ = 0.0019) refitted every 28 days walk-forward; multinomial logistic regression and LightGBM on 130 point-in-time features; Platt or isotonic calibration; log-linear pool."],
  ["Leakage-free protocol", "Every feature only uses matches finished before kick-off, proven by automated tests: scrambling future results changes no past prediction. Burn-in 2019-20, training 2020-21 to 2022-23, validation 2023-24 (plus temporal cross-validation), single final test from 2024-25 to today."],
  ["Evaluation", "Log-loss and Brier with bootstrap 95% CIs, paired gap to market, Holm-corrected p-values; encompassing test p ∝ p_market^a · p_model^b (likelihood ratio on b = 0)."],
  ["Strategy", "Simulation only: EV = p·o − 1, quarter Kelly capped at 2.5%, threshold chosen on validation. Closing Line Value = p_close · o_exec − 1. Monte Carlo with 10,000 paths."],
  ["Cognitive biases", "Seven pre-specified hypotheses (favourite-longshot, hot hand, gambler's fallacy, popularity, home, big matches). Measure: outcome − closing probability. Holm and Benjamini-Hochberg corrections."],
  ["Limitations", "Sample size (711 test matches: a 0.01 log-loss gap is hard to detect); non-stationarity (squads, coaches, 18-club format since 2023); prices really available to a bettor differ from Bet365; no xG or line-ups; baseline change in 2026."],
] as const;

export function MethodView() {
  const { t, lang } = useI18n();
  const items = lang === "fr" ? FR : EN;
  return (
    <>
      <PageHeader title={t.method.title} />
      <div className="grid gap-4">
        {items.map(([h, p]) => <Card key={h} title={h}><p className="max-w-4xl leading-relaxed text-muted">{p}</p></Card>)}
      </div>
    </>
  );
}
