"""Population d'entités en structure de tableaux (index = id, jamais réutilisé)."""


class Population:
    """État par entité. Les agrégats de contrats (claims/debts) vivent dans
    LoanBook (contracts.py), seul propriétaire de l'état contractuel."""

    def __init__(self):
        self.w = []          # capital réel scalaire, >= 0 pour les vivantes (I1)
        self.alive = []
        self.birth = []      # pas de naissance
        self.int_in = []     # intérêts reçus au pas courant
        self.int_out = []    # intérêts payés au pas courant
        self.extract = []    # extraction alpha*sqrt(w) du pas courant (revenu C8)
        self.defaulted = []  # défaut de service au pas courant (C2)
        self.n_alive = 0

    def __len__(self):
        return len(self.w)

    def born(self, w0: float, t: int) -> int:
        i = len(self.w)
        self.w.append(w0)
        self.alive.append(True)
        self.birth.append(t)
        self.int_in.append(0.0)
        self.int_out.append(0.0)
        self.extract.append(0.0)
        self.defaulted.append(False)
        self.n_alive += 1
        return i

    def kill(self, i: int):
        assert self.alive[i]
        self.alive[i] = False
        self.w[i] = 0.0
        self.n_alive -= 1

    def alive_ids(self):
        return [i for i in range(len(self.w)) if self.alive[i]]
