"""
models.py — Structures de données de la simulation.

Classes :
  - Entity          : bilan comptable d'un agent (dataclass)
  - Loan            : contrat de prêt entre deux agents (dataclass, référence par ID)
  - BankruptcyEstate: masse de redistribution après faillite (dataclass)

Architecture : références par ID entier (pas de pointeurs directs),
               traçabilité des scissions via parent_loan_id.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Entity:
    """
    Bilan comptable d'un agent.

    Actifs  : liquide, prêté, endo-investi, exo-investi
    Passifs : inné, endo-investi, exo-investi
    """
    entity_id: int
    actif_liquide: float
    passif_inne: float
    actif_prete: float = 0.0
    actif_endoinvesti: float = 0.0
    actif_exoinvesti: float = 0.0
    passif_endoinvesti: float = 0.0
    passif_exoinvesti: float = 0.0
    alive: bool = True
    creation_step: int = 0
    death_step: Optional[int] = None

    @property
    def actif_total(self) -> float:
        return self.actif_liquide + self.actif_prete + self.actif_endoinvesti + self.actif_exoinvesti

    @property
    def passif_total(self) -> float:
        return self.passif_inne + self.passif_endoinvesti + self.passif_exoinvesti

    @property
    def ratio_liquide_passif(self) -> float:
        if self.passif_total <= 0:
            return math.inf
        return self.actif_liquide / self.passif_total


@dataclass
class Loan:
    """
    Contrat de prêt entre prêteur et emprunteur, référencés par ID.
    La scission désactive le prêt original et crée deux nouveaux prêts
    (traçabilité via parent_loan_id).
    """
    loan_id: int
    lender_id: int
    borrower_id: int
    principal: float
    rate: float
    active: bool = True
    parent_loan_id: Optional[int] = None

    def interest_due(self) -> float:
        """Intérêt dû sur ce pas (r * q)."""
        return self.principal * self.rate if self.active else 0.0

    def split(
        self,
        new_id_transferred: int,
        new_id_remaining: int,
        transferred_principal: float,
        new_lender_id: int,
    ) -> tuple[Loan, Loan]:
        """
        Scinde ce prêt en deux.
        Ce prêt est désactivé ; retourne (prêt_cédé, prêt_restant).
        """
        if transferred_principal <= 0 or transferred_principal >= self.principal:
            raise ValueError("transferred_principal doit être dans ]0, principal[.")
        transferred = Loan(
            loan_id=new_id_transferred,
            lender_id=new_lender_id,
            borrower_id=self.borrower_id,
            principal=transferred_principal,
            rate=self.rate,
            active=True,
            parent_loan_id=self.loan_id,
        )
        remaining = Loan(
            loan_id=new_id_remaining,
            lender_id=self.lender_id,
            borrower_id=self.borrower_id,
            principal=self.principal - transferred_principal,
            rate=self.rate,
            active=True,
            parent_loan_id=self.loan_id,
        )
        self.active = False
        return transferred, remaining


@dataclass
class BankruptcyEstate:
    """
    Masse de redistribution créée lors de la faillite d'une entité.
    Hérite des prêts que l'entité détenait en tant que prêteuse.
    Les flux futurs sont redistribués aux créanciers au prorata.
    """
    estate_id: int
    failed_entity_id: int
    beneficiary_weights: Dict[int, float]   # {entity_id: poids}
    inherited_loan_ids: List[int] = field(default_factory=list)
    active: bool = True

    def redistribute_interest(self, incoming_interest: float) -> Dict[int, float]:
        """Distribue un flux entrant aux bénéficiaires au prorata."""
        return {
            entity_id: weight * incoming_interest
            for entity_id, weight in self.beneficiary_weights.items()
        }
