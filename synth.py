"""Données synthétiques de type Ligue 1 pour tester le pipeline hors ligne.

Les buts sont tirés d'un vrai modèle Poisson avec forces d'équipes qui dérivent.
Le « marché » connaît les vraies probabilités à un bruit près, avec 5 % de marge (Pinnacle)
et 7 % (Bet365) : c'est volontairement un marché difficile à battre.
"""
import numpy as np
import pandas as pd
from scipy.special import gammaln


def _true_probs(lam, mu, G=10):
    k = np.arange(G + 1)
    lf = gammaln(k + 1)
    px = np.exp(k * np.log(lam)[:, None] - lam[:, None] - lf)
    py = np.exp(k * np.log(mu)[:, None] - mu[:, None] - lf)
    M = px[:, :, None] * py[:, None, :]
    i, j = np.meshgrid(k, k, indexing="ij")
    p = np.stack([(M * (i > j)).sum((1, 2)), (M * (i == j)).sum((1, 2)),
                  (M * (i < j)).sum((1, 2))], axis=1)
    return p / p.sum(1, keepdims=True)


def make_synthetic(seasons=6, n_teams=18, seed=0, market_noise=0.05):
    rng = np.random.default_rng(seed)
    teams = [f"Equipe {i + 1:02d}" for i in range(n_teams)]
    att, dfn = rng.normal(0, 0.25, n_teams), rng.normal(0, 0.20, n_teams)
    rows = []
    for s in range(seasons):
        att += rng.normal(0, 0.06, n_teams)  # les forces dérivent
        dfn += rng.normal(0, 0.05, n_teams)
        pairs = [(h, a) for h in range(n_teams) for a in range(n_teams) if h != a]
        rng.shuffle(pairs)
        start = pd.Timestamp(2019 + s, 8, 10)
        dates = start + pd.to_timedelta(np.sort(rng.uniform(0, 280, len(pairs))), unit="D")
        h = np.array([p[0] for p in pairs])
        a = np.array([p[1] for p in pairs])
        lam = np.exp(0.15 + 0.25 + att[h] + dfn[a])
        mu = np.exp(0.15 + att[a] + dfn[h])
        gh, ga = rng.poisson(lam), rng.poisson(mu)
        p = _true_probs(lam, mu)
        for margin, pre in ((0.05, "PSC"), (0.07, "B365")):
            noisy = p * np.exp(rng.normal(0, market_noise, p.shape))
            noisy /= noisy.sum(1, keepdims=True)
            odds = 1.0 / (noisy * (1 + margin))
            rows_odds = {f"{pre}H": odds[:, 0], f"{pre}D": odds[:, 1], f"{pre}A": odds[:, 2]}
            if pre == "PSC":
                psc = rows_odds
            else:
                b365 = rows_odds
        df = pd.DataFrame({"Date": dates.floor("D"), "Season": f"{(2019 + s) % 100:02d}{(2020 + s) % 100:02d}",
                           "HomeTeam": [teams[i] for i in h], "AwayTeam": [teams[i] for i in a],
                           "FTHG": gh, "FTAG": ga, **psc, **b365})
        rows.append(df)
    df = pd.concat(rows, ignore_index=True)
    df["FTR"] = np.where(df.FTHG > df.FTAG, "H", np.where(df.FTHG < df.FTAG, "A", "D"))
    return df.sort_values("Date").reset_index(drop=True)
