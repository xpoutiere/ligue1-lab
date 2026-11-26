# Journal

## 26/11/2026

**Fait.** Validation sur les vraies données (2 436 matchs, 2019-20 → 22/11/2026), corrections,
tests anti-fuite (Elo, walk-forward Dixon-Coles, pipeline, features), import xG multi-source,
130 features point-in-time, restructuration en package, rapport de cohérence, CI.

**Chiffres réels.**
- Marges : Pinnacle clôture 2,4-3,1 %, Bet365 5,3-5,9 % selon la saison. Calibration du marché : écart max 0,018.
- Test 11/08/2023 → 22/11/2026 (1 017 matchs), log-loss : marché 0,980 ; Dixon-Coles 1,005
  (écart +0,024, IC95 [+0,013 ; +0,036]) ; Elo 1,007 (+0,026 [+0,014 ; +0,039]) ; fréquences 1,068.
  Les modèles sont significativement moins bons que le marché.
- Paris value Dixon-Coles aux cotes Bet365 : ROI −8 à −11 %, IC95 contenant 0.

**Surprises.** Pinnacle absent de football-data depuis le 16/01/2026 ; football-data publie
des xG depuis 2026-27 ; FBref n'affiche plus de xG ; Understat en maintenance.

**Problèmes ouverts.** Pas de xG historiques. La baseline marché de la période 2026 repose sur Bet365.

### Phase D (modèles ML)

Test final 2024-25 → 22/11/2026 (711 matchs ; 459 avec Pinnacle), log-loss [IC95], écart au marché :
- Marché 0,966 [0,932 ; 1,000]
- Combinaison 0,967, +0,001 [−0,000 ; +0,002] : le pool met 96 % du poids sur le marché, 0 sur DC, Elo et GBM
- Elo 0,990 (+0,024) ; LightGBM + probas marché 0,991 (+0,026) ; logistique 1,000 (+0,034) ;
  Dixon-Coles 1,001 (+0,035) ; LightGBM 1,004 (+0,038) ; fréquences 1,063
- Aucun modèle n'est meilleur que le marché (p de Holm = 1). Encompassing : poids b du modèle
  au-delà du marché ≈ 0 pour tous (LightGBM b = +0,00, IC95 [−0,31 ; +0,32], p = 0,99).
- Calibration retenue sur validation : aucune. SHAP : écart d'Elo, tirs sur 10 matchs, Elo domicile,
  force du calendrier de l'extérieur.

**Surprise.** Donner les probas du marché au LightGBM le rend *pire* que le marché seul
(+0,026) : avec ~1 400 matchs d'apprentissage, il ajoute surtout du bruit.

**Honnêteté.** Le test a été exécuté deux fois, avec des choix identiques (seul un argument
d'API LightGBM a changé entre les deux) ; résultats identiques au chiffre près.

### Phase E (stratégie et risque)

Test 2024-25 → 22/11/2026, cotes d'exécution Bet365 ouverture, Kelly 1/4 plafonné à 2,5 % :
| Modèle | Seuil (validation) | Paris | ROI mise fixe [IC95] | CLV moyenne [IC95] | Bankroll 100 → | P(ruine −50 %) MC |
|---|---|---|---|---|---|---|
| Dixon-Coles | 4 % | 466 | −1,1 % [−16,9 ; +16,1] | −5,50 % [−6,41 ; −4,54] | 70 | 40 % |
| Elo | 2 % | 557 | −9,3 % [−20,5 ; +2,7] | −5,82 % [−6,60 ; −5,04] | 49 | 64 % |
| LightGBM | 10 % | 506 | −3,7 % [−18,4 ; +11,2] | −4,79 % [−5,71 ; −3,89] | 43 | 74 % |

- **La CLV tranche là où le ROI ne peut pas** : l'IC95 du ROI contient 0 (trop de variance), mais
  la CLV est nettement négative, au niveau d'un pari au hasard chez Bet365 (−5,49 %).
  Les « value bets » des modèles ne battent pas la ligne de clôture.
- Validation 2023-24 : ROI de −16 % à −56 % selon le seuil, pour tous les modèles.
- Sensibilité à la marge : même en pariant à la clôture **sans aucune marge**, le ROI reste
  négatif (DC −1,9 %, Elo −3,8 %, LightGBM −3,0 %). Il n'y a pas d'avantage à faire disparaître.

### Phase F (biais cognitifs), 2 436 matchs 2019-2026, résidu = issue − proba de clôture

| Hypothèse | n | Résidu (pts) [IC95] | p Holm | ROI Bet365 [IC95] | Verdict |
|---|---|---|---|---|---|
| H1 outsiders (cote ≥ 6) sur-estimés | 716 | −1,15 [−3,38 ; +1,17] | 1,00 | −17,2 % [−35,0 ; +1,8] | pas d'effet significatif |
| H1 grands favoris (< 1,5) sous-estimés | 410 | +2,24 [−1,97 ; +6,28] | 1,00 | −0,1 % [−6,0 ; +5,5] | pas d'effet significatif |
| H2a série ≥ 3 victoires sur-estimée | 347 | −1,78 [−6,35 ; +3,03] | 1,00 | −12,5 % | pas d'effet significatif |
| H2b série ≥ 3 défaites sous-estimée | 339 | −2,19 [−6,63 ; +2,20] | 1,00 | −14,9 % | pas d'effet (signe opposé) |
| H3 PSG / OM sur-estimés | 507 | +2,31 [−1,61 ; +6,26] | 1,00 | −1,3 % | pas d'effet (signe opposé) |
| H4 domicile sur-estimé | 2 434 | −0,20 [−2,05 ; +1,70] | 1,00 | −7,5 % | pas d'effet |
| H5 favori des matchs médiatisés | 205 | +1,98 [−4,53 ; +8,83] | 1,00 | +1,4 % [−12,1 ; +15,2] | pas d'effet |

- La forme du biais favori-outsider est là (ROI à la clôture ≈ 0 pour les favoris, −18 % pour
  les cotes 6-10), comme dans la littérature, mais elle n'est **pas significative** sur 2 436 matchs.
- Aucun biais n'est exploitable après la marge Bet365.
