"""
models.py — Structures de données de la simulation.

Classes :
  - Entity : bilan comptable d'un agent (dataclass)
  - Loan   : contrat de prêt entre deux agents (dataclass, référence par ID)

Architecture : références par ID entier (pas de pointeurs directs),
               traçabilité des scissions via parent_loan_id.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


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
    alpha: float = 1.0
    actif_prete: float = 0.0
    actif_endoinvesti: float = 0.0
    actif_exoinvesti: float = 0.0
    passif_endoinvesti: float = 0.0
    passif_exoinvesti: float = 0.0
    passif_credit_detenu: float = 0.0
    alive: bool = True
    creation_step: int = 0
    death_step: Optional[int] = None
    # Attributs maintenus en temps réel (Bloc 8) pour éviter les calculs O(N) répétés.
    # Initialisés dans create_entity(), mis à jour à chaque opération qui les modifie.
    passif_total: float = 0.0       # = passif_inne + passif_endoinvesti + passif_exoinvesti
    charges_interets: float = 0.0   # Σ r·q sur les prêts dont cette entité est emprunteur
    revenus_interets: float = 0.0   # Σ r·q sur les prêts dont cette entité est prêteur

    @property
    def actif_total(self) -> float:
        return self.actif_liquide + self.actif_prete + self.actif_endoinvesti + self.actif_exoinvesti

    @property
    def passif_bilan(self) -> float:
        """Passif total bilanciel (utilisé pour le test de faillite)."""
        return self.passif_total + self.passif_credit_detenu

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
    creation_step: int = 0

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
            creation_step=self.creation_step,
        )
        remaining = Loan(
            loan_id=new_id_remaining,
            lender_id=self.lender_id,
            borrower_id=self.borrower_id,
            principal=self.principal - transferred_principal,
            rate=self.rate,
            active=True,
            parent_loan_id=self.loan_id,
            creation_step=self.creation_step,
        )
        self.active = False
        return transferred, remaining


