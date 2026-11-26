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
