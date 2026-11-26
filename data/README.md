# Données : provenance et état

Les fichiers bruts téléchargés ne sont **pas versionnés** (voir `.gitignore`) : ils sont
régénérables. Seuls `team_names.csv` et ce README le sont.

| Jeu | Source | Fichiers | Récupération | État au 26/11/2026 |
|---|---|---|---|---|
| Résultats, cotes, statistiques de match | [football-data.co.uk](https://www.football-data.co.uk/francem.php), Ligue 1 (`F1`) | `data/F1_<saison>.csv` | automatique (`core.load_data`), cache local, saison en cours re-téléchargée après 12 h | 2019-20 à 2026-27, 2 436 matchs joués (2026-27 jusqu'au 22/11/2026) |
| xG par match | [Understat](https://understat.com/league/Ligue_1) | `data/xg/understat_<saison>.json` | automatique (`xg.fetch_understat`), 1 requête / 5 s, en-tête identifiant le projet, cache local | **indisponible** : le site affiche « We will come back soon » |
| xG par match | [FBref](https://fbref.com/en/comps/13/schedule/) « Scores & Fixtures » | `data/xg/fbref_<saison>.csv` | **export manuel** dans un navigateur (« Share & Export > Get table as CSV »). Aucun téléchargement automatique : le site est protégé contre les robots | non fait |

Codes de saison : `1920` = 2019-20, …, `2627` = 2026-27.

## football-data.co.uk : points d'attention

- **Cotes Pinnacle absentes depuis le 16/01/2026** (`PS*`, `PSC*` vides en fin de 2025-26,
  colonnes inexistantes en 2026-27). La baseline du marché prend, match par match, la
  première source complète parmi `PSC` (Pinnacle clôture) > `PS` > `B365C` (Bet365 clôture)
  > `B365`. La source utilisée est dans la colonne `mkt_src`.
- 2019-20 ne compte que 279 matchs (saison arrêtée en mars 2020, COVID).
- 2019-20 à 2022-23 : 20 clubs (380 matchs) ; depuis 2023-24 : 18 clubs (306 matchs).
- Statistiques disponibles pour 100 % des matchs : tirs (`HS`, `AS`), tirs cadrés (`HST`,
  `AST`), corners (`HC`, `AC`), fautes (`HF`, `AF`), cartons (`HY`, `AY`, `HR`, `AR`).
- Les heures (`Time`) sont celles du fichier source (heure du Royaume-Uni) : elles ne
  servent qu'à ordonner les matchs d'une même journée.

Marges moyennes observées (somme des probabilités implicites - 1) : Pinnacle clôture 2,4 à
3,1 % selon la saison, Bet365 5,3 à 5,9 %.

## Correspondance des noms d'équipes : `team_names.csv`

Une ligne par club, nom de référence = nom football-data (`canonical`), puis le nom utilisé
par chaque source. Tout nom inconnu lève une erreur (`xg.to_canonical`) : on complète la
table plutôt que de perdre des matchs en silence. Les colonnes `understat` et `fbref` seront
vérifiées à la première importation réelle ; la fusion contrôle aussi le score et la date
(écart de 2 jours au plus) de chaque match.

## Exporter les xG depuis FBref (5 minutes)

1. Ouvrir la page « Scores & Fixtures » de la saison, par exemple
   `https://fbref.com/en/comps/13/2023-2024/schedule/2023-2024-Ligue-1-Scores-and-Fixtures`.
2. Au-dessus du tableau : « Share & Export » > « Get table as CSV (for Excel) ».
3. Copier le texte dans `data/xg/fbref_2324.csv` (code de saison au nom du fichier).
4. Lancer `python xg.py` : il affiche la couverture par saison et refuse toute incohérence.
