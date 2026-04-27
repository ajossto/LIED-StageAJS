"""
models.py — Structures de données de la simulation.

Ce module définit les deux briques de base du modèle :

  Entity — bilan comptable complet d'un agent économique
  Loan   — contrat de prêt entre deux agents, identifiés par leur ID entier

Principes d'architecture :
  - Pas de pointeurs directs entre objets : les prêts référencent les entités
    par leur ID entier. Cela évite les cycles de référence et simplifie
    la sérialisation / la copie.
  - Traçabilité des scissions : chaque prêt fractionné conserve le loan_id
    du prêt parent via parent_loan_id.
  - Attributs de cache (Bloc 8) : passif_total, charges_interets et
    revenus_interets sont maintenus en temps réel pour un accès O(1) là où
    une itération sur tous les prêts était nécessaire auparavant.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class Entity:
    """
    Bilan comptable d'un agent économique.

    ┌─────────────────────────────────────────────────────────┐
    │  ACTIFS                     │  PASSIFS                  │
    ├─────────────────────────────┼───────────────────────────┤
    │  L   actif_liquide          │  B   passif_inne          │
    │  R   actif_prete            │  P^e passif_endoinvesti   │
    │  K^e actif_endoinvesti      │  P^x passif_exoinvesti    │
    │  K^x actif_exoinvesti       │  C   passif_credit_detenu │
    └─────────────────────────────┴───────────────────────────┘

    Invariant bilanciel (hors faillite) :
        K^endo = P^endo  et  K^exo = P^exo
    => Valeur nette : NW = L + R - B - C

    La faillite survient quand NW < 0, i.e. L + R < B + C.

    Attributs de cache (Bloc 8)
    ---------------------------
    passif_total        = B + P^endo + P^exo   (hors passif miroir C)
                          Mis à jour lors de : auto-investissement, exécution
                          d'un prêt, amortissement, dépréciation, faillite.

    charges_interets    = Σ r·q  pour les prêts où cette entité est emprunteur.
                          Mis à jour dans : execute_loan, _revalue_loan,
                          _transfer_claims_for_payment, _pay_single_amortization,
                          process_single_failure.

    revenus_interets    = Σ r·q  pour les prêts où cette entité est prêteur.
                          Mêmes points de mise à jour.

    Ces caches évitent des itérations O(N_prêts) répétées dans
    _debt_ratio_ok() et _existing_interest_burden() lors du marché du crédit.
    """

    # Identité
    entity_id: int
    alpha: float = 1.0          # Productivité : Π = alpha * sqrt(P), tiré dans [α_min, α_max]
    creation_step: int = 0      # Pas de naissance (pour calcul de durée de vie)
    death_step: Optional[int] = None   # Pas de mort (None si toujours vivante)
    alive: bool = True

    # ── Actifs ────────────────────────────────────────────────────────────
    actif_liquide: float = 0.0        # L : numéraire mobilisable instantanément
    actif_prete: float = 0.0          # R : Σ nominaux des prêts accordés
    actif_endoinvesti: float = 0.0    # K^endo : capital issu de l'auto-investissement
    actif_exoinvesti: float = 0.0     # K^exo : capital issu des prêts reçus

    # ── Passifs ───────────────────────────────────────────────────────────
    passif_inne: float = 0.0          # B : dette d'amorçage (constante, non remboursée)
    passif_endoinvesti: float = 0.0   # P^endo : contrepartie de K^endo (K^endo = P^endo)
    passif_exoinvesti: float = 0.0    # P^exo : contrepartie de K^exo  (K^exo = P^exo)
    passif_credit_detenu: float = 0.0 # C : passif miroir de R (R = C par construction)

    # ── Caches Bloc 8 ─────────────────────────────────────────────────────
    # NE PAS modifier directement : utiliser les méthodes de Simulation.
    passif_total: float = 0.0       # B + P^endo + P^exo  (hors C)
    charges_interets: float = 0.0   # Σ r·q  (prêts empruntés actifs)
    revenus_interets: float = 0.0   # Σ r·q  (prêts prêtés actifs)

    # ── Propriétés dérivées ───────────────────────────────────────────────

    @property
    def actif_total(self) -> float:
        """A = L + R + K^endo + K^exo."""
        return self.actif_liquide + self.actif_prete + self.actif_endoinvesti + self.actif_exoinvesti

    @property
    def passif_bilan(self) -> float:
        """
        Passif bilanciel total P^bilan = passif_total + C.
        Utilisé pour le test de faillite : faillite ⟺ A < P^bilan.
        Note : passif_total = B + P^endo + P^exo  (attribut de cache).
        """
        return self.passif_total + self.passif_credit_detenu

    @property
    def ratio_liquide_passif(self) -> float:
        """
        L / P (ratio de liquidité relative).
        Seuil de participation au marché du crédit : ratio > s (config.seuil_ratio_liquide_passif).
        Retourne +∞ si P = 0 (entité sans passif productif).
        """
        if self.passif_total <= 0:
            return math.inf
        return self.actif_liquide / self.passif_total


@dataclass
class Loan:
    """
    Contrat de prêt entre un prêteur et un emprunteur, référencés par ID entier.

    Cycle de vie :
      1. Création via Simulation.execute_loan() ou Simulation.create_loan()
         → active = True, parent_loan_id = None (ou ID du prêt parent)
      2. Réévaluation via _revalue_loan() si la valeur nominale diverge de la valeur
         réelle (dépréciation cumulée) : l'ancien prêt est désactivé, un nouveau est créé.
      3. Scission via split() lors d'une cession partielle de créance :
         le prêt original est désactivé, deux fragments sont créés.
      4. Désactivation définitive : active = False lors d'une faillite (phase 3)
         ou d'un amortissement complet.

    Réévaluation de la valeur réelle :
        q_réel = q_nominal × (1 - δ_exo)^âge
        Cette valeur est calculée à la volée dans _revalue_loan() ; le prêt stocke
        uniquement le nominal courant (déjà aligné après la dernière réévaluation).
    """

    loan_id: int
    lender_id: int      # ID de l'entité prêteuse (actif_prete, passif_credit_detenu)
    borrower_id: int    # ID de l'entité emprunteuse (actif_exoinvesti, passif_exoinvesti)
    principal: float    # Nominal courant du prêt (réduit par amortissement ou réévaluation)
    rate: float         # Taux d'intérêt r (par pas) : flux = r × principal à chaque pas
    active: bool = True
    parent_loan_id: Optional[int] = None  # Traçabilité : ID du prêt dont celui-ci est issu
    creation_step: int = 0                # Pas de création (pour calcul de l'âge)

    def interest_due(self) -> float:
        """
        Intérêt dû sur ce pas : r × q.
        Retourne 0 si le prêt est inactif (désactivé ou amorti).
        """
        return self.principal * self.rate if self.active else 0.0

    def split(
        self,
        new_id_transferred: int,
        new_id_remaining: int,
        transferred_principal: float,
        new_lender_id: int,
    ) -> tuple[Loan, Loan]:
        """
        Scinde ce prêt en deux fragments lors d'une cession partielle.

        Contexte : lors d'un paiement d'intérêts par cession de créances,
        si l'emprunteur ne peut céder qu'une fraction d'un prêt, celui-ci est
        fractionné en (prêt_cédé, prêt_restant). Le prêt original est désactivé.

        Paramètres :
            new_id_transferred  — loan_id du fragment cédé au nouveau prêteur
            new_id_remaining    — loan_id du fragment conservé par l'ancien prêteur
            transferred_principal — montant cédé (doit être dans ]0, principal[)
            new_lender_id       — ID du récepteur de la fraction cédée

        Retourne (prêt_cédé, prêt_restant). Ce prêt est désactivé.
        Les deux fragments héritent du même taux, du même emprunteur, et
        du même parent_loan_id (ce prêt) pour la traçabilité.
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
