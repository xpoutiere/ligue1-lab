"""Modèles de prédiction : Elo et Dixon-Coles (avec décroissance temporelle)."""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit, gammaln


# --------------------------------------------------------------------------
# 1. ELO
# --------------------------------------------------------------------------
def elo_probs(df, k=20.0, home_adv=60.0, draw_c=0.55, init=1500.0,
              newcomer=1450.0, regress=0.25, return_pre=False):
    """Elo séquentiel. Retourne (probas pré-match [H,D,A], notes finales).

    Avec `return_pre=True`, renvoie aussi les notes pré-match (n x 2 : domicile, extérieur).

    Les probas de chaque match n'utilisent QUE les matchs terminés avant son coup d'envoi
    (pas de fuite) : les matchs d'un même coup d'envoi (colonne `Kickoff`, sinon `Date`)
    sont prédits ensemble, puis les notes sont mises à jour.
    Le nul est modélisé par un logit ordonné : plus l'écart est faible, plus le nul est probable.
    `df` doit être trié chronologiquement.
    """
    when = (df["Kickoff"] if "Kickoff" in df.columns else df["Date"]).to_numpy()
    if len(when) > 1 and (when[1:] < when[:-1]).any():
        raise ValueError("elo_probs : df doit être trié par date")
    ratings, out, pre = {}, np.zeros((len(df), 3)), np.zeros((len(df), 2))
    rows = list(df[["Season", "HomeTeam", "AwayTeam", "FTHG", "FTAG"]].itertuples(index=False))
    last_season, i = None, 0
    while i < len(rows):
        j = i
        while j < len(rows) and when[j] == when[i]:
            j += 1
        if last_season is not None and rows[i].Season != last_season:
            for t in ratings:  # retour à la moyenne entre saisons
                ratings[t] = init + (1 - regress) * (ratings[t] - init)
        last_season = rows[i].Season
        deltas = []
        for n in range(i, j):  # 1) prédire tout le créneau avec les notes d'avant
            r = rows[n]
            rh = ratings.setdefault(r.HomeTeam, newcomer)
            ra = ratings.setdefault(r.AwayTeam, newcomer)
            x = (rh + home_adv - ra) / 400.0 * np.log(10)
            pH, pA = expit(x - draw_c), expit(-x - draw_c)
            pD = 1.0 - pH - pA
            out[n] = (pH, pD, pA)
            pre[n] = (rh, ra)
            gd = r.FTHG - r.FTAG
            s = 1.0 if gd > 0 else 0.5 if gd == 0 else 0.0
            mult = 1.0 + np.log1p(abs(gd)) if gd != 0 else 1.0
            deltas.append((r.HomeTeam, r.AwayTeam, k * mult * (s - (pH + 0.5 * pD))))
        for h, a, delta in deltas:  # 2) puis mettre à jour
            ratings[h] += delta
            ratings[a] -= delta
        i = j
    return (out, ratings, pre) if return_pre else (out, ratings)


# --------------------------------------------------------------------------
# 2. DIXON-COLES
# --------------------------------------------------------------------------
class DixonColes:
    """Dixon & Coles (1997) : buts ~ Poisson(attaque x défense x domicile),
    correction de dépendance rho sur les petits scores, pondération temporelle exp(-xi * jours).

    xi = 0.0019 -> demi-vie ~ 1 an.
    """

    def __init__(self, xi=0.0019, max_goals=10, ridge=1e-3):
        self.xi, self.max_goals, self.ridge = xi, max_goals, ridge
        self.params_ = None

    # -- ajustement ---------------------------------------------------------
    def fit(self, df, ref_date=None):
        teams = sorted(set(df.HomeTeam) | set(df.AwayTeam))
        self.teams_, n = teams, len(teams)
        idx = {t: i for i, t in enumerate(teams)}
        h = df.HomeTeam.map(idx).to_numpy()
        a = df.AwayTeam.map(idx).to_numpy()
        x, y = df.FTHG.to_numpy(float), df.FTAG.to_numpy(float)
        ref = ref_date if ref_date is not None else df.Date.max()
        w = np.exp(-self.xi * (ref - df.Date).dt.days.to_numpy(float))
        m00, m01 = (x == 0) & (y == 0), (x == 0) & (y == 1)
        m10, m11 = (x == 1) & (y == 0), (x == 1) & (y == 1)
        const = -gammaln(x + 1) - gammaln(y + 1)

        def unpack(p):
            return (p[:n] - p[:n].mean(), p[n:2 * n] - p[n:2 * n].mean(), p[2 * n], p[2 * n + 1])

        def nll(p):
            att, dfn, home, rho = unpack(p)
            lam = np.exp(att[h] + dfn[a] + home)
            mu = np.exp(att[a] + dfn[h])
            tau = np.ones_like(lam)
            tau[m00] = 1 - lam[m00] * mu[m00] * rho
            tau[m01] = 1 + lam[m01] * rho
            tau[m10] = 1 + mu[m10] * rho
            tau[m11] = 1 - rho
            ll = (np.log(np.clip(tau, 1e-10, None)) + x * np.log(lam) - lam
                  + y * np.log(mu) - mu + const)
            return -np.sum(w * ll) + self.ridge * np.sum(p[:2 * n] ** 2)

        # démarrage à chaud si on refit sur les mêmes équipes
        if self.params_ is not None and self.params_[0] == teams:
            x0 = self.params_[1]
        else:
            x0 = np.concatenate([np.zeros(2 * n), [0.25, -0.05]])
        bounds = [(None, None)] * (2 * n) + [(None, None), (-0.3, 0.3)]
        res = minimize(nll, x0, method="L-BFGS-B", bounds=bounds)
        self.params_ = (teams, res.x)
        att, dfn, self.home_, self.rho_ = unpack(res.x)
        self.att_ = dict(zip(teams, att, strict=True))
        self.dfn_ = dict(zip(teams, dfn, strict=True))
        # équipe inconnue (promue) : moyenne des 3 plus faibles
        weakest = sorted(teams, key=lambda t: self.att_[t] - self.dfn_[t])[:3]
        self.default_ = (np.mean([self.att_[t] for t in weakest]),
                         np.mean([self.dfn_[t] for t in weakest]))
        return self

    # -- prédiction ---------------------------------------------------------
    def _get(self, team):
        return (self.att_.get(team, self.default_[0]), self.dfn_.get(team, self.default_[1]))

    def predict(self, home_teams, away_teams):
        """Probabilités [H, D, A] pour chaque match (via la matrice de scores)."""
        ah = np.array([self._get(t) for t in home_teams])
        aa = np.array([self._get(t) for t in away_teams])
        lam = np.exp(ah[:, 0] + aa[:, 1] + self.home_)
        mu = np.exp(aa[:, 0] + ah[:, 1])
        G = self.max_goals
        k = np.arange(G + 1)
        lf = gammaln(k + 1)
        px = np.exp(k[None, :] * np.log(lam)[:, None] - lam[:, None] - lf)
        py = np.exp(k[None, :] * np.log(mu)[:, None] - mu[:, None] - lf)
        M = px[:, :, None] * py[:, None, :]
        rho = self.rho_
        M[:, 0, 0] *= 1 - lam * mu * rho
        M[:, 0, 1] *= 1 + lam * rho
        M[:, 1, 0] *= 1 + mu * rho
        M[:, 1, 1] *= 1 - rho
        M /= M.sum(axis=(1, 2), keepdims=True)
        i, j = np.meshgrid(k, k, indexing="ij")
        return np.stack([(M * (i > j)).sum((1, 2)),
                         (M * (i == j)).sum((1, 2)),
                         (M * (i < j)).sum((1, 2))], axis=1)

    def strengths(self):
        """Tableau attaque / défense / force globale par équipe."""
        t = pd.DataFrame({"equipe": self.teams_,
                          "attaque": [self.att_[x] for x in self.teams_],
                          "defense": [-self.dfn_[x] for x in self.teams_]})
        t["force"] = t["attaque"] + t["defense"]
        return t.sort_values("force", ascending=False).reset_index(drop=True)


def walk_forward_dc(df, test_from, refit_days=28, min_train=300, **kw):
    """Backtest temporel strict : à chaque bloc de `refit_days`, on réajuste le modèle
    uniquement sur les matchs antérieurs au bloc, puis on prédit le bloc."""
    test_from = pd.Timestamp(test_from)
    test = df[df.Date >= test_from]
    model, parts = DixonColes(**kw), []
    start, end = test_from, df.Date.max()
    while start <= end:
        stop = start + pd.Timedelta(days=refit_days)
        block = test[(test.Date >= start) & (test.Date < stop)]
        train = df[df.Date < start]
        if len(block) and len(train) >= min_train:
            model.fit(train, ref_date=start)
            parts.append(pd.DataFrame(model.predict(block.HomeTeam, block.AwayTeam),
                                      index=block.index, columns=["dH", "dD", "dA"]))
        start = stop
    if not parts:
        raise ValueError("walk_forward_dc : aucun bloc prédit (pas assez d'historique ?)")
    return pd.concat(parts)
