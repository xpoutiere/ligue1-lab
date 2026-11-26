# Décisions prises en autonomie

Format : date · décision · alternatives · raison.

| Date | Décision | Alternatives | Raison |
|---|---|---|---|
| 26/11/2026 | Cotes « marché » choisies **ligne par ligne** : PSC > PS > B365C > B365, source tracée dans `mkt_src` | Une seule source pour tout le jeu ; moyenne `AvgC` | football-data ne publie plus Pinnacle depuis le 16/01/2026 : l'ancienne logique jetait 252 matchs en silence. B365C reste une clôture ; les résultats sont aussi donnés par source |
| 26/11/2026 | Elo : les matchs d'un même coup d'envoi sont prédits ensemble avant mise à jour | Ordre des lignes du CSV | Un match ne doit pas voir le résultat d'un match simultané |
| 26/11/2026 | xG : Understat (requêtes espacées, en-tête honnête) sinon exports FBref manuels ; repli sur les tirs / tirs cadrés de football-data | Contourner les protections anti-bot de FBref | Respect des CGU (règle 4). Understat en maintenance, FBref n'affiche plus de xG |
| 26/11/2026 | Statistiques couvrant < 50 % des matchs ignorées dans `build_features` | Imputer | Les xG football-data n'existent que depuis 2026-27 (4 %) |
| 26/11/2026 | Environnement virtuel `.venv` dans le projet, versions figées dans `requirements.lock` | Python global | Reproductibilité, rien installé hors du dossier |
| 26/11/2026 | Package `src/ligue1lab/` ; `core.py` et `backtest.py` à la racine gardés comme raccourcis | Tout casser | Compatibilité des commandes existantes |
| 26/11/2026 | `tasks.py` (multiplateforme) + `Makefile` qui y délègue | Makefile seul | `make` absent sous Windows |
| 26/11/2026 | Images de référence (`docs/design/*.png`) exclues de git | Les versionner | Ce sont des photos sous droits (règle 8) |
| 26/11/2026 | Site public en Next.js (export statique) dans `web/`, Streamlit gardé comme labo | Streamlit seul | Imposé par la DA du brief |
| 26/11/2026 | Protocole ML : 2019-20 = rodage ; apprentissage 2020-21 → 2022-23 ; validation 2023-24 ; CV temporelle à 2 plis (valider 2022-23, puis 2023-24) ; test unique 2024-25 → 2026-27 | CV aléatoire ; test sur 2023-24 | Splits temporels uniquement (règle 1), test le plus récent et le plus long possible (711 matchs) |
| 26/11/2026 | Calibration : aucune / Platt (vector scaling) / isotonique, choisie sur le pli 2022-23 → 2023-24 | Choisir sur le test | Règle 2. Résultat : « aucune » (isotonique sur-apprend avec 306 matchs) |
| 26/11/2026 | Combinaison = pool log-linéaire (poids ≥ 0) appris sur les prédictions hors-pli de 2023-24 | Moyenne simple ; stacking GBM | Peu de paramètres, interprétable ; les poids montrent directement l'apport de chaque modèle |
| 26/11/2026 | Information incrémentale : test d'encompassing p ∝ p_marché^a · p_modèle^b, rapport de vraisemblance H0 : b = 0, IC bootstrap | Diebold-Mariano seul | Répond directement à « le modèle apporte-t-il quelque chose au-delà du marché ? » |
| 26/11/2026 | p-valeurs « meilleur que le marché » par bootstrap unilatéral, corrigées par Holm | Bonferroni ; aucune correction | Contrôle du taux d'erreur familial, moins conservateur que Bonferroni |
| 26/11/2026 | Stratégie : exécution aux cotes d'ouverture Bet365, clôture de référence Pinnacle sans marge (sinon B365C) ; Kelly 1/4 et plafond 2,5 % fixés a priori ; seuil d'EV choisi sur validation (ROI à mise fixe, ≥ 30 paris) | Régler Kelly sur le test | Règle 2 ; Bet365 = proxy d'un bookmaker grand public (Betclic / Winamax non scrapés) |
| 26/11/2026 | CLV = p_clôture_sans_marge × cote d'exécution − 1 | Ratio de cotes brut | Espérance du pari si la clôture est juste ; comparable entre cotes |
| 26/11/2026 | « Ruine » = bankroll divisée par 2 au moins une fois | Bankroll à 0 | Kelly fractionné plafonné n'atteint jamais 0 ; −50 % est un seuil parlant |
| 26/11/2026 | Biais : 7 tests pré-spécifiés (H1 ×2, H2a, H2b, H3, H4, H5) sur toute la période 2019-2026 (pas d'apprentissage, donc pas de split) ; mesure = résidu issue − proba de clôture sans marge ; Holm (principal) et BH | Tester beaucoup de seuils | Limiter les degrés de liberté du chercheur ; seuils (cote ≥ 6, < 1,5, séries ≥ 3) fixés avant de regarder |
| 26/11/2026 | Groupes : populaires = PSG, OM ; médiatisés = matchs entre deux clubs parmi PSG, OM, OL, Lille, Monaco, Lens | Classement par audiences TV | Pas de source ouverte d'audiences ; choix fixé avant l'analyse |
