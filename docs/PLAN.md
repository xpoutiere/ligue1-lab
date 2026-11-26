# Plan de travail

Légende : [x] fait · [ ] à faire. Mis à jour à chaque commit.

## A. Validation et fondations
- [x] `core.py` et `backtest.py` lancés sur la vraie Ligue 1 (2019-20 à 2026-27)
- [x] Bugs vraies données : repli des cotes ligne par ligne (Pinnacle absent depuis le 16/01/2026), NaN, noms, doublons, saison en cours, coups d'envoi simultanés dans l'Elo
- [x] `sanity_report()` (marges, nombre de matchs, calibration, doublons)
- [x] Package `src/ligue1lab/`, `tests/` (dont anti-fuite), `ruff`, `.gitignore`, `Makefile` + `tasks.py`, GitHub Actions
- [x] git initialisé, un commit par étape

## B. Données enrichies
- [x] Import xG multi-source (Understat poli + cache, exports FBref), table de noms versionnée, `data/README.md`
- [x] Repli : tirs / tirs cadrés football-data (100 % des matchs). Understat en maintenance, FBref sans xG
- [ ] Réessayer Understat avant la version finale

## C. Features point-in-time
- [x] `build_features(df)` : 130 features, test « modifier le futur ne change pas le passé »

## D. Modèles ML
- [x] Découpage temporel : rodage 2019-20, apprentissage 2020-21 → 2022-23, validation 2023-24 (+ CV temporelle par saison), test final unique 2024-25 → aujourd'hui
- [x] Logistique multinomiale, LightGBM, calibration (Platt / isotonique) choisie sur validation
- [x] Information incrémentale vs marché (encompassing + LightGBM avec probas marché)
- [x] SHAP, tableau comparatif unique avec IC95 bootstrap et correction de Holm

## E. Stratégie et risque
- [x] EV, Kelly fractionné (1/4), plafond 2,5 %, seuil choisi sur validation
- [x] Closing Line Value, Monte Carlo de bankroll (monde réel et monde sans avantage), sensibilité à la marge

## F. Biais cognitifs
- [x] Favori-outsider, forme / séries, popularité (PSG, OM), domicile, médiatisation ; corrections Holm et BH

## G. Site public (`web/`, Next.js)
- [x] `make_artifacts.py` → `web/public/data/*.json` (validés par zod au build)
- [x] DA sombre néon + clair dashboard, composants, page `/design`
- [x] Pages : Accueil, Matchs, Modèles, Stratégie, Biais, Équipes, Paper trading, Ma calibration, Méthodologie
- [x] Responsive vérifié à 375 px (aucun débordement), console sans erreur ; déploiement GitHub Pages préparé (workflow manuel, pas lancé)
- [ ] Lighthouse ≥ 90 : audit automatique bloqué par mon garde-fou, à lancer dans Chrome DevTools

## H. Documentation
- [x] README (captures sombre et clair), `docs/methodology.md`, licence MIT, tâches `tasks.py` / `Makefile`
- [ ] Premier enregistrement réel du journal de paper trading (dès que football-data publie la journée)
