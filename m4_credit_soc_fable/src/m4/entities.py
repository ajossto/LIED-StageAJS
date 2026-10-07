"""Population d'entités en structure de tableaux (index = id, jamais réutilisé).

État réel par entité : capital productif K >= 0 (I1) — une seule variable
d'état réelle depuis la refonte fusionnée (2026-07-14). Les agrégats de
contrats (claims/debts/service dû) vivent dans LoanBook (contracts.py),
seul propriétaire de l'état contractuel.
"""


class Population:
    def __init__(self):
        self.K = []          # capital productif réel, >= 0 (I1)
        self.alive = []
        self.birth = []      # pas de naissance
        self.sector = []     # secteur (chocs sectoriels), tiré à la naissance
        self.int_in = []     # intérêts reçus au pas courant
        self.int_out = []    # intérêts payés au pas courant
        self.prod = []       # production alpha*sqrt(K) du pas courant
        self.defaulted = []  # défaut de service au pas courant
        self.n_alive = 0
        # ensemble des vivantes maintenu incrémentalement : alive_ids() en
        # O(n_alive log n_alive) au lieu de O(total jamais né) — indispensable
        # aux grands lam (leçon prototype, NOTES 2026-07-14)
        self._alive_set = set()

    def __len__(self):
        return len(self.K)

    def born(self, K0: float, t: int, sector: int = 0) -> int:
        i = len(self.K)
        self.K.append(K0)
        self.alive.append(True)
        self.birth.append(t)
        self.sector.append(sector)
        self.int_in.append(0.0)
        self.int_out.append(0.0)
        self.prod.append(0.0)
        self.defaulted.append(False)
        self._alive_set.add(i)
        self.n_alive += 1
        return i

    def kill(self, i: int):
        assert self.alive[i]
        self.alive[i] = False
        self._alive_set.discard(i)
        self.K[i] = 0.0
        self.n_alive -= 1

    def alive_ids(self):
        return sorted(self._alive_set)
