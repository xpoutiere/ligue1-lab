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
