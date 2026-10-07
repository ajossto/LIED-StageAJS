"""Carnet de contrats de prêt nominaux perpétuels.

Invariants I2/I3 : toutes les mutations passent par add/remove ; claims/debts
sont maintenus incrémentalement ici et nulle part ailleurs. L'itération de
loans suit l'ordre de création (dict Python ordonné, lids croissants) — c'est
la convention C2 pour le service des intérêts.
"""
from collections import defaultdict


class LoanBook:
    def __init__(self, merge_pairs: bool = False):
        self.loans = {}                    # lid -> [lender, borrower, q, r]
        self.by_lender = defaultdict(set)  # id -> {lid}
        self.by_borrower = defaultdict(set)
        self.claims = defaultdict(float)   # id -> somme des q prêtés
        self.debts = defaultdict(float)    # id -> somme des q empruntés
        self.next_lid = 0
        # variante merge_pairs : au plus un contrat par paire (l, b) ; les
        # ajouts fusionnent au taux moyen pondéré par le principal, ce qui
        # préserve exactement le flux d'intérêts total de la paire.
        self.merge_pairs = merge_pairs
        self.by_pair = {}                  # (lender, borrower) -> lid

    def __len__(self):
        return len(self.loans)

    def add(self, lender: int, borrower: int, q: float, r: float) -> int:
        assert lender != borrower and q > 0.0 and r > 0.0
        if self.merge_pairs:
            lid = self.by_pair.get((lender, borrower))
            if lid is not None:
                rec = self.loans[lid]
                q0, r0 = rec[2], rec[3]
                rec[2] = q0 + q
                rec[3] = (q0 * r0 + q * r) / (q0 + q)
                self.claims[lender] += q
                self.debts[borrower] += q
                return lid
        lid = self.next_lid
        self.next_lid += 1
        self.loans[lid] = [lender, borrower, q, r]
        self.by_lender[lender].add(lid)
        self.by_borrower[borrower].add(lid)
        self.claims[lender] += q
        self.debts[borrower] += q
        if self.merge_pairs:
            self.by_pair[(lender, borrower)] = lid
        return lid

    def remove(self, lid: int):
        lender, borrower, q, _ = self.loans.pop(lid)
        self.by_lender[lender].discard(lid)
        self.by_borrower[borrower].discard(lid)
        self.claims[lender] -= q
        self.debts[borrower] -= q
        if self.merge_pairs:
            self.by_pair.pop((lender, borrower), None)

    def rebuild_aggregates(self):
        """Reconstruction de contrôle (I3) — jamais appelée dans la boucle."""
        claims = defaultdict(float)
        debts = defaultdict(float)
        for lender, borrower, q, _ in self.loans.values():
            claims[lender] += q
            debts[borrower] += q
        return claims, debts

    def check_consistency(self, alive) -> list:
        """Retourne la liste des violations d'invariants I2/I3 (vide = OK)."""
        errors = []
        for lid, (lender, borrower, q, r) in self.loans.items():
            if q <= 0:
                errors.append(f"loan {lid}: q={q} <= 0")
            if lender == borrower:
                errors.append(f"loan {lid}: auto-prêt {lender}")
            if not (alive[lender] and alive[borrower]):
                errors.append(f"loan {lid}: partie morte")
            if lid not in self.by_lender[lender] or lid not in self.by_borrower[borrower]:
                errors.append(f"loan {lid}: index inverse incohérent")
        claims, debts = self.rebuild_aggregates()
        for i, v in claims.items():
            if abs(self.claims[i] - v) > 1e-6 * max(1.0, abs(v)):
                errors.append(f"claims[{i}]: incrémental {self.claims[i]} != {v}")
        for i, v in debts.items():
            if abs(self.debts[i] - v) > 1e-6 * max(1.0, abs(v)):
                errors.append(f"debts[{i}]: incrémental {self.debts[i]} != {v}")
        for agg, ref, name in ((self.claims, claims, "claims"), (self.debts, debts, "debts")):
            for i, v in agg.items():
                if i not in ref and abs(v) > 1e-6:
                    errors.append(f"{name}[{i}]: résidu {v} sans contrat actif")
        if self.merge_pairs:
            pairs = [(rec[0], rec[1]) for rec in self.loans.values()]
            if len(pairs) != len(set(pairs)):
                errors.append("merge_pairs : paires (l, b) dupliquées")
        return errors
