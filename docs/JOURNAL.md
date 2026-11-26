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
