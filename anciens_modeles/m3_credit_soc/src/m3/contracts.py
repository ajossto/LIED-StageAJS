"""Carnet de contrats de prêt nominaux perpétuels.

Invariants I2/I3 : toutes les mutations passent par add/remove ; claims/debts
et le service dû par emprunteuse (due) sont maintenus incrémentalement ici et
nulle part ailleurs. merge_pairs (correctif M2 validé, rapport 01 §5) : au plus
un contrat par paire (prêteuse, emprunteuse), fusion au taux moyen pondéré par
le principal — préserve exactement claims/debts et le flux d'intérêts total.
"""
from collections import defaultdict


class LoanBook:
    def __init__(self, merge_pairs: bool = True):
        self.loans = {}                    # lid -> [lender, borrower, q, r]
        self.by_lender = defaultdict(set)  # id -> {lid}
        self.by_borrower = defaultdict(set)
        self.claims = defaultdict(float)   # id -> somme des q prêtés
        self.debts = defaultdict(float)    # id -> somme des q empruntés
        self.due = defaultdict(float)      # id -> somme des r*q dus (service)
        self.next_lid = 0
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
                # le service dû suit exactement le produit q*r du contrat
                self.due[borrower] += rec[2] * rec[3] - q0 * r0
                return lid
        lid = self.next_lid
        self.next_lid += 1
        self.loans[lid] = [lender, borrower, q, r]
        self.by_lender[lender].add(lid)
        self.by_borrower[borrower].add(lid)
        self.claims[lender] += q
        self.debts[borrower] += q
        self.due[borrower] += q * r
        if self.merge_pairs:
            self.by_pair[(lender, borrower)] = lid
        return lid

    def remove(self, lid: int):
        lender, borrower, q, r = self.loans.pop(lid)
        self.by_lender[lender].discard(lid)
        self.by_borrower[borrower].discard(lid)
        self.claims[lender] -= q
        self.debts[borrower] -= q
        self.due[borrower] -= q * r
        if self.merge_pairs:
            self.by_pair.pop((lender, borrower), None)

    def rebuild_aggregates(self):
        """Reconstruction de contrôle (I3) — jamais appelée dans la boucle."""
        claims = defaultdict(float)
        debts = defaultdict(float)
        due = defaultdict(float)
        for lender, borrower, q, r in self.loans.values():
            claims[lender] += q
            debts[borrower] += q
            due[borrower] += q * r
        return claims, debts, due

    def check_consistency(self, alive) -> list:
        """Liste des violations d'invariants I2/I3/I5/I6 (vide = OK)."""
        errors = []
        for lid, (lender, borrower, q, r) in self.loans.items():
            if q <= 0:
                errors.append(f"loan {lid}: q={q} <= 0")
            if r <= 0:
                errors.append(f"loan {lid}: r={r} <= 0")
            if lender == borrower:
                errors.append(f"loan {lid}: auto-prêt {lender}")
            if not (alive[lender] and alive[borrower]):
                errors.append(f"loan {lid}: partie morte")
            if lid not in self.by_lender[lender] or lid not in self.by_borrower[borrower]:
                errors.append(f"loan {lid}: index inverse incohérent")
        claims, debts, due = self.rebuild_aggregates()
        for agg, ref, name in ((self.claims, claims, "claims"),
                               (self.debts, debts, "debts"),
                               (self.due, due, "due")):
            for i, v in ref.items():
                if abs(agg[i] - v) > 1e-6 * max(1.0, abs(v)):
                    errors.append(f"{name}[{i}]: incrémental {agg[i]} != {v}")
            for i, v in agg.items():
                if i not in ref and abs(v) > 1e-6:
                    errors.append(f"{name}[{i}]: résidu {v} sans contrat actif")
        total_c = sum(claims.values())
        total_d = sum(debts.values())
        if abs(total_c - total_d) > 1e-6 * max(1.0, total_c):
            errors.append(f"I5 : total créances {total_c} != total dettes {total_d}")
        if self.merge_pairs:
            pairs = [(rec[0], rec[1]) for rec in self.loans.values()]
            if len(pairs) != len(set(pairs)):
                errors.append("merge_pairs : paires (l, b) dupliquées")
        return errors
