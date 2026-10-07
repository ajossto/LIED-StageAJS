"""Journalisation enrichie optionnelle d'un run — sans effet sur la dynamique.

Deux observateurs, activés en les attachant à Simulation AVANT run() :

  sim.dist_log = DistLog()      # stats distributionnelles par pas
  sim.watcher  = Watcher(seed)  # historiques individuels d'entités suivies

DistLog : à chaque pas, quantiles/moyennes de la production Π = α√K, du taux
interne marginal r* = α/(2√K) (dérivée de la production par unité de capital,
équivalent m4 du r* = α/(2√P) du modèle m0/27-04-WIP) et Gini du capital, de
la valeur nette (partie positive) et du revenu brut (Π + intérêts reçus).

Watcher : politique de suivi héritée du Collector m0 — les premières
`cap_first` entités nées sont toutes suivies, les suivantes avec probabilité
`p_watch` jusqu'à `cap_total`. Le tirage utilise un RNG ISOLÉ (jamais
sim.rng : le suivi ne doit pas changer la trajectoire). Chaque entité suivie
est enregistrée à chaque pas tant qu'elle vit : bilan (K, créances, dettes,
NW) et flux du pas (Π, intérêts reçus/payés).

L'invariant I8 (defaultdict du carnet) impose les accès en .get() — voir
simulation.snapshot().
"""
import math
import random


def _gini(values):
    """Gini des valeurs >= 0 (les négatives sont ramenées à 0)."""
    xs = sorted(v if v > 0.0 else 0.0 for v in values)
    n = len(xs)
    total = sum(xs)
    if n < 2 or total <= 0.0:
        return 0.0
    cum = 0.0
    for i, x in enumerate(xs, start=1):
        cum += i * x
    return 2.0 * cum / (n * total) - (n + 1.0) / n


def _quantile(sorted_vals, q):
    """Quantile empirique (interpolation linéaire) d'une liste triée non vide."""
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]
    pos = q * (n - 1)
    lo = int(pos)
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1.0 - frac) + sorted_vals[hi] * frac


DIST_FIELDS = [
    "t", "n",
    "prod_q10", "prod_med", "prod_mean", "prod_q90", "prod_max",
    "r_min", "r_q10", "r_med", "r_mean", "r_q90", "r_max",
    "gini_K", "gini_nw", "gini_income",
]


class DistLog:
    """Stats distributionnelles par pas, accumulées dans self.rows."""

    def __init__(self):
        self.rows = []

    def record(self, sim):
        pop, book, cfg = sim.pop, sim.book, sim.cfg
        ids = pop.alive_ids()
        if not ids:
            return
        prods = sorted(pop.prod[i] for i in ids)
        # r* défini seulement pour K > 0 (les K=0 mourront à la résolution
        # suivante si endettées, sinon r* serait infini)
        rates = sorted(cfg.alpha / (2.0 * math.sqrt(pop.K[i]))
                       for i in ids if pop.K[i] > 0.0)
        K_vals = [pop.K[i] for i in ids]
        nw_vals = [pop.K[i] + book.claims.get(i, 0.0) - book.debts.get(i, 0.0)
                   for i in ids]
        inc_vals = [pop.prod[i] + pop.int_in[i] for i in ids]
        row = dict(t=sim.t, n=len(ids))
        row["prod_q10"] = _quantile(prods, 0.10)
        row["prod_med"] = _quantile(prods, 0.50)
        row["prod_mean"] = sum(prods) / len(prods)
        row["prod_q90"] = _quantile(prods, 0.90)
        row["prod_max"] = prods[-1]
        if rates:
            row["r_min"] = rates[0]
            row["r_q10"] = _quantile(rates, 0.10)
            row["r_med"] = _quantile(rates, 0.50)
            row["r_mean"] = sum(rates) / len(rates)
            row["r_q90"] = _quantile(rates, 0.90)
            row["r_max"] = rates[-1]
        else:
            for k in ("r_min", "r_q10", "r_med", "r_mean", "r_q90", "r_max"):
                row[k] = 0.0
        row["gini_K"] = _gini(K_vals)
        row["gini_nw"] = _gini(nw_vals)
        row["gini_income"] = _gini(inc_vals)
        self.rows.append(row)


WATCH_FIELDS = ["t", "id", "K", "claims", "debts", "nw",
                "prod", "int_in", "int_out"]


class Watcher:
    """Historiques par pas d'un sous-ensemble d'entités suivies.

    Enrôlement : les `cap_first` premières nées sont toutes suivies, puis
    - si `expected_births` est fourni : une naissance sur `stride`
      (déterministe, couvre TOUT le run — sinon le plafond serait atteint
      dès les premières naissances et la fin du run n'aurait aucune suivie) ;
    - sinon : chaque naissance avec probabilité `p_watch` (politique m0,
      RNG isolé du moteur — le suivi n'influence jamais la dynamique).
    """

    def __init__(self, seed, cap_first=20, p_watch=0.03, cap_total=80,
                 expected_births=None):
        self.rng = random.Random(seed ^ 0x57A7C4)
        self.cap_first = cap_first
        self.p_watch = p_watch
        self.cap_total = cap_total
        self.stride = None
        if expected_births is not None:
            self.stride = max(1, int(expected_births
                                     / max(1, cap_total - cap_first)))
        self.watched = set()
        self.rows = []
        self._known = 0  # nombre d'entités déjà vues (ids denses croissants)

    def _enroll_new(self, pop):
        for i in range(self._known, len(pop)):
            if len(self.watched) >= self.cap_total:
                break
            if len(self.watched) < self.cap_first:
                self.watched.add(i)
            elif self.stride is not None:
                if (i - self.cap_first) % self.stride == 0:
                    self.watched.add(i)
            elif self.rng.random() < self.p_watch:
                self.watched.add(i)
        self._known = len(pop)

    def record(self, sim):
        pop, book = sim.pop, sim.book
        self._enroll_new(pop)
        for i in sorted(self.watched):
            if not pop.alive[i]:
                continue
            claims = book.claims.get(i, 0.0)
            debts = book.debts.get(i, 0.0)
            self.rows.append(dict(
                t=sim.t, id=i, K=pop.K[i], claims=claims, debts=debts,
                nw=pop.K[i] + claims - debts,
                prod=pop.prod[i], int_in=pop.int_in[i], int_out=pop.int_out[i],
            ))
