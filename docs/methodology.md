# Le marché des paris sur la Ligue 1 est-il battable ? Étude statistique, 2019-2026

*Ligue 1 Lab · projet éducatif · aucune garantie de gain, aucune mise réelle.*

## Résumé

Nous confrontons des modèles publics de prédiction du résultat (Elo, Dixon-Coles, régression
logistique multinomiale, LightGBM, et leurs combinaisons) aux probabilités implicites des cotes
de clôture, sur 2 436 matchs de Ligue 1 (août 2019 → novembre 2026). Sur un test final unique
de 711 matchs (2024-25 → 2026-27), **aucun modèle ne fait mieux que le marché** : le meilleur,
une combinaison apprise sur la validation, recopie le marché (log-loss 0,9666 contre 0,9658,
écart +0,0009, IC95 [−0,0004 ; +0,0021]) ; LightGBM est significativement moins bon (+0,038,
IC95 [+0,017 ; +0,057]). Les paris « value » simulés ont une Closing Line Value d'environ −5 %
(IC95 entièrement négatif), et aucun des sept biais cognitifs testés n'est significatif après
correction multiple. Conclusion : avec des données publiques, le marché de clôture de la Ligue 1
n'est pas battable ; c'est un résultat négatif, établi avec un protocole conçu pour l'être.

## 1. Données

- **Source** : football-data.co.uk (fichiers `F1`), 2019-20 à 2026-27 : scores, tirs, tirs
  cadrés, corners, cartons, cotes d'ouverture et de clôture (Pinnacle, Bet365, moyenne, max).
  Provenance et dates : `data/README.md`.
- **Nettoyage** : suppression des matchs sans score, normalisation des noms, détection des
  doublons, contrôle que le résultat (`FTR`) concorde avec le score, coup d'envoi = date + heure.
- **Rapport de cohérence** (`sanity_report`) : 306 matchs par saison à 18 clubs, 380 à 20 clubs
  (exception documentée : 279 en 2019-20, saison interrompue) ; marge Pinnacle de clôture de
  2,4 à 3,1 % ; Bet365 de 5,3 à 5,6 % ; écart maximal de calibration du marché 0,018.
- **Rupture de source** : football-data ne publie plus Pinnacle depuis le 16/01/2026. La baseline
  marché prend alors la clôture Bet365 (252 matchs) ; les résultats sont aussi donnés sur les
  459 matchs du test où la baseline est Pinnacle.
- **xG** : non disponibles sur l'historique (Understat en maintenance, FBref ne les affiche plus,
  football-data seulement depuis 2026-27). Les tirs et tirs cadrés servent d'indicateurs de
  qualité des occasions.

## 2. Probabilités du marché

Pour des cotes décimales $o_H, o_D, o_A$, les probabilités implicites $1/o_i$ somment à
$1 + m$, où $m$ est la marge. On retient la normalisation proportionnelle :

$$\hat p_i = \frac{1/o_i}{\sum_j 1/o_j}.$$

Elle ignore le biais favori-outsider de la marge (méthodes de Shin ou puissance) ; la section 6
montre que ce biais est faible et non significatif sur nos données.

## 3. Modèles

**Elo.** Notes mises à jour après chaque créneau de coup d'envoi (les matchs simultanés ne se
voient pas), $k = 20$ multiplié par $1 + \ln(1 + |\Delta\text{buts}|)$, avantage du terrain
60 points, retour de 25 % vers la moyenne entre saisons, promus à 1 450. Le nul est modélisé
par un logit ordonné : $P(H) = \sigma(x - c)$, $P(A) = \sigma(-x - c)$, $P(D) = 1 - P(H) - P(A)$,
avec $x = \ln 10 \cdot (R_h + 60 - R_a)/400$ et $c = 0{,}55$.

**Dixon-Coles (1997).** $X \sim \mathcal P(\lambda)$, $Y \sim \mathcal P(\mu)$ avec
$\lambda = \exp(\alpha_h + \delta_a + \gamma)$, $\mu = \exp(\alpha_a + \delta_h)$, et la correction
des petits scores

$$\tau(x,y) = \begin{cases} 1 - \lambda\mu\rho & (0,0) \\ 1 + \lambda\rho & (0,1) \\ 1 + \mu\rho & (1,0) \\ 1 - \rho & (1,1) \\ 1 & \text{sinon.} \end{cases}$$

La vraisemblance est pondérée par $w = e^{-\xi\,\Delta t}$ (jours), $\xi = 0{,}0019$ (demi-vie
d'environ un an), avec une légère pénalité ridge. Le modèle est réajusté tous les 28 jours sur
les seuls matchs antérieurs (walk-forward).

**Apprentissage automatique.** 130 features point-in-time (`build_features`) : forme sur 3, 5 et
10 matchs (moyennes et moyennes exponentielles) des buts, tirs, tirs cadrés et points, forme
spécifique domicile / extérieur, jours de repos, classement d'avant-match et écarts à la 3e
place et à la zone de relégation, Elo, force du calendrier (Elo moyen des cinq derniers
adversaires). Régression logistique multinomiale (imputation médiane, standardisation, pénalité
L2) et LightGBM multiclasse.

**Calibration.** Aucune, Platt (régression logistique multinomiale sur les log-probabilités) ou
isotonique un-contre-tous, choisie sur la validation.

**Combinaison.** Pool log-linéaire $p \propto \prod_k p_k^{w_k}$, $w_k \ge 0$, appris par maximum
de vraisemblance sur les prédictions hors-pli de 2023-24.

## 4. Protocole : pas de fuite, un seul test

- Toute feature d'un match n'utilise que des matchs terminés **avant son coup d'envoi**. Des
  tests automatiques le vérifient : brouiller les scores et tirs futurs laisse toutes les
  features et prédictions passées identiques au bit près (sur données synthétiques et sur les
  vraies données) ; le score d'un match ne modifie pas ses propres features ; chaque
  réajustement de Dixon-Coles n'utilise que des dates antérieures au bloc prédit.
- **Découpage temporel** : rodage 2019-20 (jamais utilisé pour apprendre), apprentissage 2020-21
  à 2022-23 (1 140 matchs), validation 2023-24 (306), test 2024-25 → 22/11/2026 (711).
- Tous les choix (régularisation, grille LightGBM avec arrêt précoce, calibration, poids de la
  combinaison, seuil de pari) sont faits par validation croisée temporelle à deux plis
  (valider 2022-23, puis 2023-24). Le test n'a servi qu'à l'évaluation finale.

## 5. Résultats : modèles contre marché

Log-loss multiclasse $-\frac1n\sum_i \ln \hat p_{i,y_i}$ et score de Brier ; IC95 par bootstrap
(2 000 rééchantillons) ; écart au marché par bootstrap apparié ; p-valeur unilatérale de « meilleur
que le marché », corrigée par Holm.

| Modèle | Log-loss [IC95] | Écart au marché [IC95] | Brier | Précision | p Holm |
|---|---|---|---|---|---|
| Marché (clôture sans marge) | 0,9658 [0,932 ; 1,000] | – | 0,5735 | 54,4 % | – |
| Combinaison | 0,9666 [0,934 ; 1,000] | +0,0009 [−0,0004 ; +0,0021] | 0,5740 | 54,4 % | 1,00 |
| Elo | 0,9896 [0,951 ; 1,029] | +0,0239 [+0,0094 ; +0,0385] | 0,5892 | 53,6 % | 1,00 |
| LightGBM + probas marché | 0,9914 [0,956 ; 1,026] | +0,0257 [+0,0091 ; +0,0413] | 0,5879 | 52,3 % | 1,00 |
| Logistique | 0,9998 [0,965 ; 1,036] | +0,0341 [+0,0159 ; +0,0518] | 0,5946 | 52,5 % | 1,00 |
| Dixon-Coles | 1,0008 [0,964 ; 1,042] | +0,0350 [+0,0126 ; +0,0619] | 0,5901 | 54,1 % | 1,00 |
| LightGBM (calibration retenue : aucune) | 1,0037 [0,969 ; 1,039] | +0,0380 [+0,0174 ; +0,0570] | 0,5960 | 51,3 % | 1,00 |
| Fréquences d'apprentissage | 1,0627 [1,050 ; 1,076] | +0,0969 [+0,0676 ; +0,1250] | 0,6428 | 46,1 % | 1,00 |

Sur les 459 matchs à baseline Pinnacle, le classement est le même (marché 0,9564 ; Elo +0,018,
IC95 [−0,001 ; +0,036] ; LightGBM +0,036).

**Information incrémentale.** On ajuste $p \propto p_{\text{marché}}^{a}\,p_{\text{modèle}}^{b}$ ;
sous $H_0 : b = 0$, le modèle n'apporte rien au-delà du marché (test du rapport de
vraisemblance, 1 ddl). LightGBM : $b = +0{,}00$, IC95 [−0,31 ; +0,32], $p = 0{,}99$ ; logistique
$b = -0{,}02$ ($p = 0{,}90$) ; Dixon-Coles $b = -0{,}18$ ($p = 0{,}24$) ; Elo $b = -0{,}14$
($p = 0{,}47$). La combinaison met 96 % de son poids sur le marché et 0 sur les autres modèles.
Donner les probabilités du marché en entrée de LightGBM le rend *moins bon* que le marché seul :
avec 1 446 matchs, il apprend surtout du bruit.

**Interprétabilité.** SHAP (LightGBM) : écart d'Elo, tirs sur 10 matchs, Elo de l'équipe à
domicile, force du calendrier de l'équipe à l'extérieur, tirs cadrés récents. Le modèle
redécouvre des informations que le marché intègre déjà.

## 6. Stratégie simulée et risque

Pari sur l'issue d'EV maximale $\text{EV} = \hat p \cdot o - 1$ si EV > seuil, mise de Kelly
fractionnée $f = \tfrac14 \cdot \text{EV}/(o - 1)$ plafonnée à 2,5 % de la bankroll ; exécution aux
cotes d'ouverture Bet365 ; seuil choisi sur la validation. **Closing Line Value** :
$\text{CLV} = p_{\text{clôture}} \cdot o_{\text{exécution}} - 1$, l'espérance du pari si la clôture
est juste ; c'est un indicateur bien moins bruité que le ROI.

| Modèle | Seuil | Paris | ROI à mise fixe [IC95] | CLV [IC95] | P(perdre 50 %) |
|---|---|---|---|---|---|
| Dixon-Coles | 4 % | 466 | −1,1 % [−16,9 ; +16,1] | −5,50 % [−6,41 ; −4,54] | 40 % |
| Elo | 2 % | 557 | −9,3 % [−20,5 ; +2,7] | −5,82 % [−6,60 ; −5,04] | 64 % |
| LightGBM | 10 % | 506 | −3,7 % [−18,4 ; +11,2] | −4,79 % [−5,71 ; −3,89] | 74 % |

Un pari au hasard chez Bet365 a une CLV de −5,49 % : les modèles ne choisissent pas mieux que le
hasard. L'IC95 du ROI contient 0 (la variance de 500 paris est énorme), mais la CLV tranche.
La probabilité de ruine vient d'un Monte Carlo de 10 000 trajectoires (rééchantillonnage des
paris). **Sensibilité à la marge** : en pariant à la clôture sans aucune marge, le ROI reste
négatif (Dixon-Coles −1,9 %, Elo −3,8 %, LightGBM −3,0 %) : il n'existe pas d'avantage que la
marge ferait disparaître.

## 7. Biais cognitifs

Hypothèses fixées avant l'analyse, sur les 2 436 matchs. Mesure : résidu
$r = \mathbb 1[\text{issue}] - p_{\text{clôture}}$ (points de probabilité) ; $r < 0$ signifie que
l'issue est sur-estimée. Corrections de Holm (taux d'erreur familial) et de Benjamini-Hochberg.

| Hypothèse (littérature) | n | Résidu [IC95] | p Holm | ROI Bet365 |
|---|---|---|---|---|
| H1 outsiders (cote ≥ 6) sur-estimés (Kahneman & Tversky 1979 ; Snowberg & Wolfers 2010) | 716 | −1,15 [−3,38 ; +1,17] | 1,00 | −17,2 % |
| H1 grands favoris (cote < 1,5) sous-estimés | 410 | +2,24 [−1,97 ; +6,28] | 1,00 | −0,1 % |
| H2a main chaude : série ≥ 3 victoires sur-estimée (Gilovich et al. 1985) | 347 | −1,78 [−6,35 ; +3,03] | 1,00 | −12,5 % |
| H2b erreur du joueur : série ≥ 3 défaites sous-estimée | 339 | −2,19 [−6,63 ; +2,20] | 1,00 | −14,9 % |
| H3 popularité : PSG et OM sur-estimés (Forrest & Simmons 2008) | 507 | +2,31 [−1,61 ; +6,26] | 1,00 | −1,3 % |
| H4 victoire à domicile sur-estimée | 2 434 | −0,20 [−2,05 ; +1,70] | 1,00 | −7,5 % |
| H5 favori des matchs médiatisés sur-estimé | 205 | +1,98 [−4,53 ; +8,83] | 1,00 | +1,4 % |

La forme du biais favori-outsider est visible (ROI à la clôture proche de 0 pour les favoris,
−18 % pour les cotes de 6 à 10), conforme à la littérature, mais non significative ici. Aucun
effet n'est exploitable après la marge.

## 8. Discussion et limites

1. **Taille d'échantillon.** 711 matchs de test : l'IC95 de la log-loss a une demi-largeur
   d'environ 0,035 et celui de l'écart apparié d'environ 0,02. Un avantage réel de 0,005 serait
   invisible. Nos conclusions portent sur l'absence d'avantage *détectable*.
2. **Non-stationnarité.** Passage à 18 clubs en 2023, transferts, entraîneurs, droits TV : les
   relations apprises en 2020-2023 se transposent mal.
3. **Marché et marge.** Bet365 sert de proxy aux bookmakers français (non scrapés, conformément
   à leurs CGU) ; la baseline change de source en 2026 ; la normalisation proportionnelle de la
   marge est une approximation.
4. **Informations manquantes.** Pas de xG, de compositions d'équipe, de blessures ni d'horaires
   de publication des cotes : c'est précisément l'information que le marché intègre.

## 9. Reproduction

```
python -m venv .venv && .venv\Scripts\pip install -e ".[lab,dev]"
python tasks.py all      # données, contrôles, ML, stratégie, biais, artefacts
python tasks.py web      # site statique dans web/out
```

## Références

- Dixon, M. J., & Coles, S. G. (1997). Modelling association football scores and inefficiencies in the football betting market. *JRSS C*, 46(2).
- Kahneman, D., & Tversky, A. (1979). Prospect theory. *Econometrica*, 47(2).
- Tversky, A., & Kahneman, D. (1974). Judgment under uncertainty: heuristics and biases. *Science*, 185.
- Gilovich, T., Vallone, R., & Tversky, A. (1985). The hot hand in basketball. *Cognitive Psychology*, 17(3).
- Snowberg, E., & Wolfers, J. (2010). Explaining the favorite-longshot bias. *Journal of Political Economy*, 118(4).
- Forrest, D., & Simmons, R. (2008). Sentiment in the betting market on Spanish football. *Applied Economics*, 40(1).
- Kelly, J. L. (1956). A new interpretation of information rate. *Bell System Technical Journal*, 35(4).
- Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics*, 6(2).
- Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate. *JRSS B*, 57(1).
