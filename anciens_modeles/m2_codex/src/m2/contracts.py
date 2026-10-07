from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable


@dataclass(slots=True)
class LoanContract:
    contract_id: int
    lender_id: int
    borrower_id: int
    principal: float
    rate: float
    creation_step: int
    parent_id: int | None = None
    component_count: int = 1


class ContractBook:
    """Carnet nominal avec index bidirectionnels vérifiables."""

    def __init__(self) -> None:
        self.contracts: dict[int, LoanContract] = {}
        self.by_lender: dict[int, set[int]] = defaultdict(set)
        self.by_borrower: dict[int, set[int]] = defaultdict(set)
        self.claim_totals: dict[int, float] = defaultdict(float)
        self.debt_totals: dict[int, float] = defaultdict(float)
        self.by_pair: dict[tuple[int, int], int] = {}
        self.next_contract_id = 0

    def __len__(self) -> int:
        return len(self.contracts)

    def add(
        self,
        lender_id: int,
        borrower_id: int,
        principal: float,
        rate: float,
        creation_step: int,
        parent_id: int | None = None,
    ) -> LoanContract:
        if lender_id == borrower_id:
            raise ValueError("un auto-contrat est interdit")
        if not math.isfinite(principal) or principal <= 0:
            raise ValueError("le principal doit être fini et strictement positif")
        if not math.isfinite(rate) or rate < 0:
            raise ValueError("le taux doit être fini et positif ou nul")
        pair = (lender_id, borrower_id)
        existing_id = self.by_pair.get(pair)
        if existing_id is not None:
            existing = self.contracts[existing_id]
            combined_principal = existing.principal + float(principal)
            existing.rate = (
                existing.rate * existing.principal + float(rate) * float(principal)
            ) / combined_principal
            existing.principal = combined_principal
            existing.creation_step = min(existing.creation_step, creation_step)
            existing.component_count += 1
            # parent_id ne peut représenter plusieurs lignées ; le compteur rend
            # explicite la compression exacte des flux linéaires.
            if existing.parent_id != parent_id:
                existing.parent_id = None
            self.claim_totals[lender_id] += float(principal)
            self.debt_totals[borrower_id] += float(principal)
            return existing
        contract = LoanContract(
            contract_id=self.next_contract_id,
            lender_id=lender_id,
            borrower_id=borrower_id,
            principal=float(principal),
            rate=float(rate),
            creation_step=creation_step,
            parent_id=parent_id,
        )
        self.next_contract_id += 1
        self.contracts[contract.contract_id] = contract
        self.by_lender[lender_id].add(contract.contract_id)
        self.by_borrower[borrower_id].add(contract.contract_id)
        self.by_pair[pair] = contract.contract_id
        self.claim_totals[lender_id] += contract.principal
        self.debt_totals[borrower_id] += contract.principal
        return contract

    def remove(self, contract_id: int) -> LoanContract:
        contract = self.contracts.pop(contract_id)
        del self.by_pair[(contract.lender_id, contract.borrower_id)]
        self.by_lender[contract.lender_id].remove(contract_id)
        self.by_borrower[contract.borrower_id].remove(contract_id)
        self.claim_totals[contract.lender_id] -= contract.principal
        self.debt_totals[contract.borrower_id] -= contract.principal
        if not self.by_lender[contract.lender_id]:
            del self.by_lender[contract.lender_id]
            del self.claim_totals[contract.lender_id]
        if not self.by_borrower[contract.borrower_id]:
            del self.by_borrower[contract.borrower_id]
            del self.debt_totals[contract.borrower_id]
        return contract

    def lent_contracts(self, entity_id: int) -> list[LoanContract]:
        return [
            self.contracts[cid] for cid in sorted(self.by_lender.get(entity_id, ()))
        ]

    def borrowed_contracts(self, entity_id: int) -> list[LoanContract]:
        return [
            self.contracts[cid] for cid in sorted(self.by_borrower.get(entity_id, ()))
        ]

    def claims(self, entity_id: int) -> float:
        return self.claim_totals.get(entity_id, 0.0)

    def debts(self, entity_id: int) -> float:
        return self.debt_totals.get(entity_id, 0.0)

    def total_principal(self) -> float:
        return math.fsum(c.principal for c in self.contracts.values())

    def validate(self, living_ids: Iterable[int]) -> None:
        living = set(living_ids)
        lender_indexed: set[int] = set()
        borrower_indexed: set[int] = set()
        for entity_id, ids in self.by_lender.items():
            if entity_id not in living:
                raise AssertionError(f"prêteur orphelin: {entity_id}")
            lender_indexed.update(ids)
        for entity_id, ids in self.by_borrower.items():
            if entity_id not in living:
                raise AssertionError(f"emprunteur orphelin: {entity_id}")
            borrower_indexed.update(ids)
        expected = set(self.contracts)
        if lender_indexed != expected or borrower_indexed != expected:
            raise AssertionError("index du carnet incohérents")
        for cid, contract in self.contracts.items():
            if contract.lender_id not in living or contract.borrower_id not in living:
                raise AssertionError(f"contrat {cid} relié à une entité morte")
            if contract.lender_id == contract.borrower_id:
                raise AssertionError(f"auto-contrat {cid}")
            if not math.isfinite(contract.principal) or contract.principal <= 0:
                raise AssertionError(f"principal invalide pour {cid}")
            if not math.isfinite(contract.rate) or contract.rate < 0:
                raise AssertionError(f"taux invalide pour {cid}")
            if cid not in self.by_lender[contract.lender_id]:
                raise AssertionError(f"contrat {cid} absent de by_lender")
            if cid not in self.by_borrower[contract.borrower_id]:
                raise AssertionError(f"contrat {cid} absent de by_borrower")
            if self.by_pair.get((contract.lender_id, contract.borrower_id)) != cid:
                raise AssertionError(f"index de paire incohérent pour {cid}")
        if set(self.by_pair.values()) != expected:
            raise AssertionError("index des paires incohérent")
        recalculated_claims: dict[int, float] = defaultdict(float)
        recalculated_debts: dict[int, float] = defaultdict(float)
        for contract in self.contracts.values():
            recalculated_claims[contract.lender_id] += contract.principal
            recalculated_debts[contract.borrower_id] += contract.principal
        for entity_id in set(recalculated_claims) | set(self.claim_totals):
            if not math.isclose(
                recalculated_claims.get(entity_id, 0.0),
                self.claim_totals.get(entity_id, 0.0),
                rel_tol=1e-11,
                abs_tol=1e-9,
            ):
                raise AssertionError(f"cache de créances incohérent pour {entity_id}")
        for entity_id in set(recalculated_debts) | set(self.debt_totals):
            if not math.isclose(
                recalculated_debts.get(entity_id, 0.0),
                self.debt_totals.get(entity_id, 0.0),
                rel_tol=1e-11,
                abs_tol=1e-9,
            ):
                raise AssertionError(f"cache de dettes incohérent pour {entity_id}")
