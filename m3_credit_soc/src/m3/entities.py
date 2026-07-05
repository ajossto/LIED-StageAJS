"""Population d'entités en structure de tableaux (index = id, jamais réutilisé).

État réel par entité : liquidité L >= 0 et capital productif K >= 0 (I1).
Les agrégats de contrats (claims/debts/service dû) vivent dans LoanBook
(contracts.py), seul propriétaire de l'état contractuel.
"""


class Population:
    def __init__(self):
        self.L = []          # liquidité, >= 0 pour les vivantes (I1)
        self.K = []          # capital productif réel, >= 0 (I1)
        self.alive = []
        self.birth = []      # pas de naissance
        self.sector = []     # secteur (ablation G2), tiré à la naissance
        self.int_in = []     # intérêts reçus au pas courant
        self.int_out = []    # intérêts payés au pas courant
        self.prod = []       # production alpha*sqrt(K) du pas courant
        self.defaulted = []  # défaut de service au pas courant
        self.annuity = []    # rente fantôme par pas (ablation E), sinon 0
        self.n_alive = 0

    def __len__(self):
        return len(self.L)

    def born(self, L0: float, K0: float, t: int, sector: int = 0) -> int:
        i = len(self.L)
        self.L.append(L0)
        self.K.append(K0)
        self.alive.append(True)
        self.birth.append(t)
        self.sector.append(sector)
        self.int_in.append(0.0)
        self.int_out.append(0.0)
        self.prod.append(0.0)
        self.defaulted.append(False)
        self.annuity.append(0.0)
        self.n_alive += 1
        return i

    def kill(self, i: int):
        assert self.alive[i]
        self.alive[i] = False
        self.L[i] = 0.0
        self.K[i] = 0.0
        self.annuity[i] = 0.0  # rente fantôme éteinte à la mort (ablation E)
        self.n_alive -= 1

    def alive_ids(self):
        return [i for i in range(len(self.L)) if self.alive[i]]
