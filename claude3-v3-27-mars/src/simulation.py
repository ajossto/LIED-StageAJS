"""
simulation.py — Moteur de simulation multi-agents.

Architecture :
  - Références par ID entier (pas de pointeurs directs entre objets)
  - Conteneurs : Dict[int, Entity], Dict[int, Loan]
  - RNG isolé (random.Random(seed), pas de random global)
  - Redistribution directe des créances lors des faillites (pas de masses de faillite)

Mécanismes clés :
  - Extraction : Π = α√P (passif productif)
  - Cession de créances réévaluées à la valeur réelle avant transfert
  - Arbitrage vente-de-créance / reliquéfaction guidé par r* interne
  - Contrainte d'endettement sur revenus totaux (extraction + intérêts reçus)

Statistiques : le Collector est instancié dans Simulation et appelé
               à chaque pas — voir statistics.py pour le détail.
"""

from __future__ import annotations

import csv
import math
import random
from typing import Dict, List, Optional, Tuple

from config import SimulationConfig
from models import Entity, Loan
from statistics import CascadeEvent, Collector

_P_WATCH_NEW = 0.03


class Simulation:
    def __init__(self, config: Optional[SimulationConfig] = None) -> None:
        self.config = config or SimulationConfig()
        self.rng = random.Random(self.config.seed)

        self.entities: Dict[int, Entity] = {}
        self.loans: Dict[int, Loan] = {}

        self.current_step: int = 0
        self.next_entity_id: int = 1
        self.next_loan_id: int = 1

        # Statistiques légères (une ligne par pas)
        self.stats: List[Dict] = []
        self.event_log: List[str] = []

        # Collecteur statistique riche
        self.collector = Collector(freq_snapshot=self.config.freq_snapshot)

        self._step_flows: dict = {}  # eid -> flow dict (reset each step)

        self._create_initial_population(self.config.n_entites_initiales)

        # Watch all initial entities
        for eid in list(self.entities.keys()):
            self.collector.register_entity(eid)
            self._step_flows[eid] = {'extraction': 0.0, 'interest_received': 0.0,
                                      'interest_paid': 0.0, 'depreciation': 0.0}

    # ------------------------------------------------------------------
    #  UTILITAIRES GÉNÉRAUX
    # ------------------------------------------------------------------

    def log(self, message: str) -> None:
        if self.config.log_events:
            self.event_log.append(f"[t={self.current_step}] {message}")

    def _reset_step_flows(self) -> None:
        for eid in self.collector.watched_entity_ids:
            self._step_flows[eid] = {'extraction': 0.0, 'interest_received': 0.0,
                                      'interest_paid': 0.0, 'depreciation': 0.0}

    def active_entities(self) -> List[Entity]:
        return [e for e in self.entities.values() if e.alive]

    def active_loans(self) -> List[Loan]:
        return [loan for loan in self.loans.values() if loan.active]

    def get_entity(self, entity_id: int) -> Entity:
        return self.entities[entity_id]

    def compute_internal_rate(self, entity: Entity) -> float:
        """r* = alpha / (2 * sqrt(P))"""
        p = max(entity.passif_total, self.config.epsilon)
        return entity.alpha / (2.0 * math.sqrt(p))

    # ------------------------------------------------------------------
    #  CRÉATION D'ENTITÉS
    # ------------------------------------------------------------------

    def create_entity(
        self,
        actif_liquide: Optional[float] = None,
        passif_inne: Optional[float] = None,
    ) -> Entity:
        p_inne = self.config.passif_inne_initial if passif_inne is None else passif_inne
        entity = Entity(
            entity_id=self.next_entity_id,
            actif_liquide=self.config.actif_liquide_initial if actif_liquide is None else actif_liquide,
            passif_inne=p_inne,
            alpha=self.rng.uniform(self.config.alpha_min, self.config.alpha_max),
            creation_step=self.current_step,
            passif_total=p_inne,  # passif_endoinvesti=0, passif_exoinvesti=0 à la création
        )
        self.entities[entity.entity_id] = entity
        # Watch newly born entities with probability _P_WATCH_NEW (but not initial ones, watched separately)
        if self.current_step > 0 and self.rng.random() < _P_WATCH_NEW:
            self.collector.register_entity(entity.entity_id)
            self._step_flows[entity.entity_id] = {'extraction': 0.0, 'interest_received': 0.0,
                                                    'interest_paid': 0.0, 'depreciation': 0.0}
        self.next_entity_id += 1
        self.log(f"Création entité {entity.entity_id}")
        return entity

    def _create_initial_population(self, n: int) -> None:
        for _ in range(n):
            self.create_entity()

    # ------------------------------------------------------------------
    #  CRÉATION DE PRÊTS
    # ------------------------------------------------------------------

    def create_loan(
        self,
        lender_id: int,
        borrower_id: int,
        principal: float,
        rate: float,
        parent_loan_id: Optional[int] = None,
    ) -> Loan:
        if principal <= self.config.epsilon:
            raise ValueError("Le principal doit être strictement positif.")
        loan = Loan(
            loan_id=self.next_loan_id,
            lender_id=lender_id,
            borrower_id=borrower_id,
            principal=principal,
            rate=rate,
            active=True,
            parent_loan_id=parent_loan_id,
            creation_step=self.current_step,
        )
        self.loans[loan.loan_id] = loan
        self.next_loan_id += 1
        return loan

    # ------------------------------------------------------------------
    #  TIRAGE DE POISSON
    # ------------------------------------------------------------------

    def poisson(self, lam: float) -> int:
        """Algorithme de Knuth pour un tirage Poisson(lam)."""
        if lam <= 0:
            return 0
        l_val = math.exp(-lam)
        k = 0
        p = 1.0
        while p > l_val:
            k += 1
            p *= self.rng.random()
        return k - 1

    # ------------------------------------------------------------------
    #  ÉTAPE 1 — Création de nouvelles entités
    # ------------------------------------------------------------------

    def spawn_new_entities(self) -> int:
        n = self.poisson(self.config.lambda_creation)
        for _ in range(n):
            self.create_entity()
        return n

    # ------------------------------------------------------------------
    #  ÉTAPE 2 — Extraction depuis la nature
    # ------------------------------------------------------------------

    def extract_from_nature(self) -> float:
        """Π = alpha * sqrt(P) ajouté au liquide de chaque entité vivante."""
        total = 0.0
        for e in self.active_entities():
            extracted = e.alpha * math.sqrt(max(e.passif_total, 0.0))
            e.actif_liquide += extracted
            total += extracted
            if e.entity_id in self.collector.watched_entity_ids:
                self._step_flows[e.entity_id]['extraction'] += extracted
        return total

    # ------------------------------------------------------------------
    #  ÉTAPE 3 — Paiement des intérêts
    # ------------------------------------------------------------------

    def pay_interest_phase(self) -> float:
        """
        Paiement des intérêts pour tous les prêts actifs.
        En cas d'illiquidité : liquide → cession de créances → reliquéfaction endo.
        """
        total_paid = 0.0
        for loan in sorted(self.active_loans(), key=lambda x: x.loan_id):
            total_paid += self._pay_single_interest(loan)
        return total_paid

    def _pay_single_interest(self, loan: Loan) -> float:
        if not loan.active:
            return 0.0
        borrower = self.get_entity(loan.borrower_id)
        due = loan.interest_due()
        if due <= self.config.epsilon:
            return 0.0
        payment = self._ensure_payment_capacity(borrower, due, loan.lender_id)
        if borrower.entity_id in self.collector.watched_entity_ids:
            self._step_flows[borrower.entity_id]['interest_paid'] += payment
        self._route_interest_to_lender(loan, payment)
        return payment

    def _ensure_payment_capacity(self, payer: Entity, amount_due: float, creditor_id: int) -> float:
        """
        Mobilise la capacité de paiement de payer via un arbitrage en quatre étapes :
          1) Actif liquide disponible.
          2) Cession des créances dont le taux < r* (moins rentables que la capacité
             extractive marginale — vendre en priorité).
          3) Reliquéfaction de l'endo-investi (décote c, perte de capacité extractive).
          4) Cession des créances dont le taux ≥ r* (plus rentables — dernier recours).
        Chaque cession réévalue le prêt à sa valeur réelle avant transfert.
        Retourne le montant effectivement payé.
        """
        if amount_due <= self.config.epsilon:
            return 0.0

        amount_remaining = amount_due
        paid = 0.0

        # 1) Liquide
        liquid_payment = min(payer.actif_liquide, amount_remaining)
        payer.actif_liquide -= liquid_payment
        amount_remaining -= liquid_payment
        paid += liquid_payment

        if amount_remaining <= self.config.epsilon:
            return paid

        # Taux interne marginal courant du payeur
        r_star = self.compute_internal_rate(payer)

        # 2) Cession des créances sous r* (faible rendement relatif)
        below_rstar = sorted(
            [l for l in self.active_loans()
             if l.lender_id == payer.entity_id and l.rate < r_star - self.config.epsilon],
            key=lambda x: (x.rate, x.loan_id),
        )
        if amount_remaining > self.config.epsilon and below_rstar:
            transferred = self._transfer_claims_for_payment(
                payer.entity_id, creditor_id, amount_remaining, below_rstar
            )
            paid += transferred
            amount_remaining = amount_due - paid

        # 3) Reliquéfaction endo
        if amount_remaining > self.config.epsilon:
            c = max(self.config.coefficient_reliquefaction, self.config.epsilon)
            y_needed = amount_remaining / c
            y = min(payer.actif_endoinvesti, payer.passif_endoinvesti, y_needed)
            if y > self.config.epsilon:
                payer.actif_endoinvesti -= y
                payer.passif_endoinvesti -= y
                liquid_generated = c * y
                payer.actif_liquide += liquid_generated
                final_payment = min(payer.actif_liquide, amount_due - paid)
                payer.actif_liquide -= final_payment
                paid += final_payment
                amount_remaining = amount_due - paid

        # 4) Cession des créances au-dessus de r* (haut rendement — dernier recours)
        if amount_remaining > self.config.epsilon:
            # r* a pu changer après reliquéfaction (P^endo a diminué) : recalcul
            r_star = self.compute_internal_rate(payer)
            above_rstar = sorted(
                [l for l in self.active_loans()
                 if l.lender_id == payer.entity_id and l.rate >= r_star - self.config.epsilon],
                key=lambda x: (x.rate, x.loan_id),
            )
            if above_rstar:
                transferred = self._transfer_claims_for_payment(
                    payer.entity_id, creditor_id, amount_remaining, above_rstar
                )
                paid += transferred

        return paid

    def _revalue_loan(self, loan: Loan) -> Optional[Loan]:
        """
        Calcule la valeur économique réelle d'un prêt : principal × (1−δ_exo)^âge.
        Si la valeur réelle diffère du nominal courant (> ε) :
          - écrit le delta (négatif) dans actif_prete et passif_credit_detenu du prêteur ;
          - désactive le prêt original, crée un nouveau prêt à valeur réelle.
        Le bilan de l'emprunteur n'est PAS modifié : K^exo et P^exo ont déjà
        décru via apply_depreciation() et restent alignés sur la valeur réelle.
        Retourne le prêt actif à valeur réelle (nouveau ou inchangé), ou None si nul.
        """
        factor = max(0.0, 1.0 - self.config.taux_depreciation_exo)
        age = self.current_step - loan.creation_step
        real_value = loan.principal * (factor ** age)

        if real_value <= self.config.epsilon:
            lender = self.get_entity(loan.lender_id)
            lender.actif_prete -= loan.principal
            lender.passif_credit_detenu -= loan.principal
            lender.revenus_interets -= loan.rate * loan.principal
            borrower = self.entities.get(loan.borrower_id)
            if borrower and borrower.alive:
                borrower.charges_interets -= loan.rate * loan.principal
            loan.active = False
            return None

        delta = real_value - loan.principal
        if abs(delta) <= self.config.epsilon:
            return loan  # valeur nominale déjà alignée, pas de correction

        # Write-down chez le prêteur (delta < 0 : réduction)
        lender = self.get_entity(loan.lender_id)
        lender.actif_prete += delta
        lender.passif_credit_detenu += delta
        delta_flow = loan.rate * delta
        lender.revenus_interets += delta_flow
        borrower = self.entities.get(loan.borrower_id)
        if borrower and borrower.alive:
            borrower.charges_interets += delta_flow
        loan.active = False
        new_loan = self.create_loan(
            lender_id=loan.lender_id,
            borrower_id=loan.borrower_id,
            principal=real_value,
            rate=loan.rate,
            parent_loan_id=loan.loan_id,
        )
        return new_loan

    def _transfer_claims_for_payment(
        self,
        from_entity_id: int,
        to_entity_id: int,
        amount_needed: float,
        sorted_loans: Optional[List[Loan]] = None,
    ) -> float:
        """
        Cède des créances de from_entity vers to_entity pour couvrir amount_needed.
        Chaque créance est réévaluée à sa valeur réelle avant cession (write-down
        chez le prêteur si la valeur a décru depuis l'émission).
        Si sorted_loans est fourni (liste pré-triée/filtrée), l'utilise directement.
        Sinon, trie toutes les créances actives par taux croissant.
        Retourne le montant effectivement transféré (en valeur réelle).
        """
        payer = self.get_entity(from_entity_id)
        if sorted_loans is None:
            sorted_loans = sorted(
                [loan for loan in self.active_loans() if loan.lender_id == from_entity_id],
                key=lambda x: (x.rate, x.loan_id),
            )
        transferred_total = 0.0

        for loan in sorted_loans:
            if transferred_total >= amount_needed - self.config.epsilon:
                break
            if not loan.active:
                continue

            # Réévaluation à la valeur réelle avant cession
            revalued = self._revalue_loan(loan)
            if revalued is None:
                continue  # prêt sans valeur résiduelle

            remain = amount_needed - transferred_total
            transfer_amount = min(revalued.principal, remain)
            if transfer_amount <= self.config.epsilon:
                continue

            payer.actif_prete -= transfer_amount
            payer.passif_credit_detenu -= transfer_amount
            receiver = self.get_entity(to_entity_id)
            receiver.actif_prete += transfer_amount
            receiver.passif_credit_detenu += transfer_amount
            # Cache : le prêteur change, l'emprunteur reste identique → seuls les revenus bougent.
            flow = revalued.rate * transfer_amount
            payer.revenus_interets -= flow
            receiver.revenus_interets += flow

            if abs(transfer_amount - revalued.principal) <= self.config.epsilon:
                # Cession totale : changement de prêteur
                revalued.lender_id = to_entity_id
            else:
                # Cession partielle : scission du prêt réévalué
                t_id = self.next_loan_id
                r_id = self.next_loan_id + 1
                transferred_frag, remaining_frag = revalued.split(t_id, r_id, transfer_amount, to_entity_id)
                self.loans[transferred_frag.loan_id] = transferred_frag
                self.loans[remaining_frag.loan_id] = remaining_frag
                self.next_loan_id += 2

            transferred_total += transfer_amount

        return transferred_total

    def _route_interest_to_lender(self, loan: Loan, amount: float) -> None:
        """Crédite le prêteur du montant d'intérêt reçu."""
        lender = self.get_entity(loan.lender_id)
        lender.actif_liquide += amount
        if lender.entity_id in self.collector.watched_entity_ids:
            self._step_flows[lender.entity_id]['interest_received'] += amount


    # ------------------------------------------------------------------
    #  ÉTAPE 4 — Dépréciation
    # ------------------------------------------------------------------

    def apply_depreciation(self) -> None:
        for e in self.active_entities():
            if e.entity_id in self.collector.watched_entity_ids:
                dep = (e.actif_liquide * self.config.taux_depreciation_liquide +
                       e.actif_endoinvesti * self.config.taux_depreciation_endo)
                self._step_flows[e.entity_id]['depreciation'] += dep

            e.actif_liquide *= max(0.0, 1.0 - self.config.taux_depreciation_liquide)

            factor_endo = max(0.0, 1.0 - self.config.taux_depreciation_endo)
            e.actif_endoinvesti *= factor_endo
            e.passif_endoinvesti *= factor_endo

            factor_exo = max(0.0, 1.0 - self.config.taux_depreciation_exo)
            e.actif_exoinvesti *= factor_exo
            e.passif_exoinvesti *= factor_exo

            # Bloc 8 : recalcul du cache passif_total après dépréciations
            e.passif_total = e.passif_inne + e.passif_endoinvesti + e.passif_exoinvesti

    # ------------------------------------------------------------------
    #  ÉTAPE 5 — Marché du crédit
    # ------------------------------------------------------------------

    def _rebuild_interest_cache(self) -> None:
        """
        Recalcule charges_interets et revenus_interets pour toutes les entités
        vivantes à partir des prêts actifs. O(N_loans) une seule fois par pas,
        appelé juste avant la phase de marché de crédit.
        Évite les itérations O(N_loans) répétées dans _debt_ratio_ok/_existing_interest_burden.
        """
        for e in self.active_entities():
            e.charges_interets = 0.0
            e.revenus_interets = 0.0
        for loan in self.active_loans():
            borrower = self.entities.get(loan.borrower_id)
            lender = self.entities.get(loan.lender_id)
            flow = loan.rate * loan.principal
            if borrower and borrower.alive:
                borrower.charges_interets += flow
            if lender and lender.alive:
                lender.revenus_interets += flow

    def _select_active_credit_entities(self) -> List[Entity]:
        s = self.config.seuil_ratio_liquide_passif
        return [
            e for e in self.active_entities()
            if e.passif_total > self.config.epsilon and e.ratio_liquide_passif > s
        ]

    def _lender_offer(self, lender: Entity) -> float:
        # Réserve = max(s·P, B_innée) : protège la solvabilité (L ≥ B) quand s·P < B.
        # Sans cette contrainte, un prêteur avec P < B/s prête sous son seuil de faillite.
        return max(0.0, lender.actif_liquide - self._liquidity_reserve(lender))

    def _liquidity_reserve(self, entity: Entity) -> float:
        """Réserve de liquidité minimale : max(s·P, B_innée). Cohérente avec
        _lender_offer et auto_invest_end_of_turn."""
        return max(
            self.config.seuil_ratio_liquide_passif * entity.passif_total,
            entity.passif_inne,
        )

    def _borrower_qmax(self, borrower: Entity, rate: float) -> float:
        """
        Volume optimal à emprunter étant donné que le surplus sera auto-investi.
        L'emprunteur cherche le q tel que le rendement marginal à (P + surplus + q) = rate.
        qmax = (α/2r)² - P - surplus
        Le surplus planifié utilise la même réserve que auto_invest_end_of_turn.
        """
        if rate <= self.config.epsilon:
            return 0.0
        surplus = max(0.0, borrower.actif_liquide - self._liquidity_reserve(borrower))
        qmax = (borrower.alpha / (2.0 * rate)) ** 2 - borrower.passif_total - surplus
        return max(0.0, qmax)

    def _gain_auto_invest(self, borrower: Entity, amount: float) -> float:
        if amount <= self.config.epsilon:
            return 0.0
        p = borrower.passif_total
        return borrower.alpha * (math.sqrt(p + amount) - math.sqrt(p))

    def _gain_borrow(self, borrower: Entity, amount: float, rate: float) -> float:
        if amount <= self.config.epsilon:
            return 0.0
        p = borrower.passif_total
        gross = borrower.alpha * (math.sqrt(p + amount) - math.sqrt(p))
        return gross - rate * amount

    def _gain_lend(self, lender: Entity, amount: float, rate: float) -> float:
        if amount <= self.config.epsilon:
            return 0.0 
        return rate * amount

    def _borrowing_is_acceptable(self, borrower: Entity, amount: float, rate: float) -> bool:
        """
        Comparaison marginale : l'emprunteur auto-investira son surplus de toute façon.
        La question est : vaut-il la peine d'emprunter amount EN PLUS de ce surplus ?

        gain_sans_emprunt = α*(√(P + surplus) − √P)
        gain_avec_emprunt = α*(√(P + surplus + amount) − √P) − rate*amount

        On accepte si gain_avec >= (1 + mu) * gain_sans.
        """
        if amount <= self.config.epsilon:
            return False
        p = borrower.passif_total
        surplus = max(0.0, borrower.actif_liquide - self._liquidity_reserve(borrower))
        gain_b = borrower.alpha * (math.sqrt(p + surplus + amount) - math.sqrt(p)) \
                 - rate * amount
        gain_a = borrower.alpha * (math.sqrt(p + surplus) - math.sqrt(p)) \
                 if surplus > self.config.epsilon else 0.0
        if gain_a <= self.config.epsilon:
            return gain_b > self.config.epsilon
        return gain_b / gain_a >= 1.0 + self.config.mu

    def _lending_is_acceptable(self, lender: Entity, amount: float, rate: float) -> bool:
        """
        Le prêteur prête son excédent de liquidité à son propre taux r*.
        Prêter à r* est neutre avec l'auto-invest à la marge ; on accepte si
        rate >= r*_prêteur (toujours vérifié quand use_lender_rate_as_offer_rate=True).
        """
        if amount <= self.config.epsilon:
            return False
        return rate >= self.compute_internal_rate(lender) - self.config.epsilon

    def _existing_interest_burden(self, borrower: Entity) -> float:
        """Somme des intérêts annuels (r·q) sur les prêts existants de l'emprunteur.
        Utilise le cache charges_interets (initialisé par _rebuild_interest_cache)."""
        return borrower.charges_interets

    def _debt_ratio_ok(self, borrower: Entity, principal: float, rate: float) -> bool:
        """
        Contrainte d'endettement : (intérêts existants + r_new·q_new) / revenus_totaux ≤ seuil.
        Les revenus totaux comprennent l'extraction et les intérêts financiers reçus.
        Utilise les caches charges_interets / revenus_interets (O(1)).
        Retourne True si le prêt est admissible.
        """
        seuil = self.config.seuil_ratio_endettement
        if seuil <= 0:
            return True
        p = max(borrower.passif_total, self.config.epsilon)
        revenus = borrower.alpha * math.sqrt(p) + borrower.revenus_interets
        if revenus <= self.config.epsilon:
            return False
        return (borrower.charges_interets + rate * principal) / revenus <= seuil

    def execute_loan(self, lender: Entity, borrower: Entity, principal: float, rate: float) -> Loan:
        lender.actif_liquide -= principal
        lender.actif_prete += principal
        lender.passif_credit_detenu += principal
        borrower.actif_exoinvesti += principal
        borrower.passif_exoinvesti += principal
        borrower.passif_total += principal             # Bloc 8 : cache passif_total
        lender.revenus_interets  += rate * principal   # Bloc 8 : cache intérêts
        borrower.charges_interets += rate * principal  # Bloc 8 : cache intérêts
        loan = self.create_loan(lender.entity_id, borrower.entity_id, principal, rate)
        self.log(
            f"Prêt {loan.loan_id}: {lender.entity_id} -> {borrower.entity_id}, "
            f"q={principal:.4f}, r={rate:.4f}"
        )
        return loan

    def credit_market_iteration(self) -> int:
        """
        Appariement itératif prêteur/emprunteur avec matching aléatoire (Bloc 8).

        Si n_candidats_pool == 1 : arbitrage pur (prêteur r* minimal, emprunteur r* maximal).
        Si n_candidats_pool > 1  : tirage aléatoire parmi les k meilleurs candidats de chaque
          côté. Cela permet à une entité médiane d'être prêteur d'une petite et emprunteur
          d'une grande → intermédiaires financiers naturels → contagion en cascade.

        Optimisation : le tri est refait uniquement après une transaction réussie
        (seules les transactions modifient les r*). Entre deux transactions, on re-tire
        aléatoirement dans les pools existants. L'arrêt intervient si MAX_IDLE tentatives
        consécutives échouent.
        """
        transactions = 0
        k = max(1, self.config.n_candidats_pool)
        MAX_IDLE = max(20, k * k)  # tentatives max sans transaction avant arrêt
        idle = 0
        need_resort = True
        active_sorted: List[Entity] = []
        pool_lenders: List[Entity] = []
        pool_borrowers: List[Entity] = []

        # charges_interets / revenus_interets initialisés par _rebuild_interest_cache()
        # avant cet appel (O(1) par accès, O(N_loans) une fois par pas).
        seuil = self.config.seuil_ratio_endettement
        eps   = self.config.epsilon
        f     = self.config.fraction_taux_emprunteur

        for _ in range(self.config.max_credit_iterations):
            if need_resort:
                active = self._select_active_credit_entities()
                if len(active) < 2:
                    break
                # Échantillonnage O(k log k) : marché décentralisé avec information locale.
                sample_size = min(len(active), 2 * k)
                sample = self.rng.sample(active, sample_size)
                active_sorted = sorted(sample, key=self.compute_internal_rate)
                n = len(active_sorted)
                pool_lenders = active_sorted[:max(1, n // 2)]
                pool_borrowers = active_sorted[n // 2:]
                if not pool_lenders or not pool_borrowers:
                    break
                need_resort = False

            lender = self.rng.choice(pool_lenders)
            pool_b = [e for e in pool_borrowers if e.entity_id != lender.entity_id]
            if not pool_b:
                idle += 1
                if idle >= MAX_IDLE:
                    break
                continue
            borrower = self.rng.choice(pool_b)

            lender_rate = self.compute_internal_rate(lender)
            borrower_rate = self.compute_internal_rate(borrower)
            if borrower_rate <= lender_rate + eps:
                idle += 1
                if idle >= MAX_IDLE:
                    break
                continue

            offer = self._lender_offer(lender)
            if offer <= eps:
                idle += 1
                if idle >= MAX_IDLE:
                    break
                continue

            rate = (1.0 - f) * lender_rate + f * borrower_rate

            qmax = self._borrower_qmax(borrower, rate)
            demand = self.config.theta * qmax
            principal = min(offer, demand)

            if principal <= eps:
                idle += 1
                if idle >= MAX_IDLE:
                    break
                continue
            if not self._borrowing_is_acceptable(borrower, principal, rate):
                idle += 1
                if idle >= MAX_IDLE:
                    break
                continue

            # Contrainte d'endettement via attributs Entity (O(1), initialisés par _rebuild_interest_cache)
            if seuil > 0:
                p = max(borrower.passif_total, eps)
                revenus = borrower.alpha * math.sqrt(p) + borrower.revenus_interets
                if revenus <= eps or (borrower.charges_interets + rate * principal) / revenus > seuil:
                    idle += 1
                    if idle >= MAX_IDLE:
                        break
                    continue

            self.execute_loan(lender, borrower, principal, rate)
            # execute_loan met déjà à jour charges_interets / revenus_interets
            transactions += 1
            idle = 0
            need_resort = True  # r* et offres ont changé → ré-échantillonner

        return transactions

    # ------------------------------------------------------------------
    #  ÉTAPE 6 — Auto-investissement
    # ------------------------------------------------------------------

    def auto_invest_end_of_turn(self) -> float:
        """
        Convertit une fraction du surplus liquide en investissement endogène.
        Surplus = max(0, L - reserve) où reserve = max(s·P, B_innée).
        La réserve minimale est max(s·P, B) pour garantir L ≥ B après conversion,
        cohérent avec _lender_offer qui applique la même contrainte.
        """
        total = 0.0
        for e in self.active_entities():
            surplus = max(0.0, e.actif_liquide - self._liquidity_reserve(e))
            x = self.config.fraction_auto_investissement * surplus
            if x > self.config.epsilon:
                e.actif_liquide -= x
                e.actif_endoinvesti += x
                e.passif_endoinvesti += x
                e.passif_total += x   # Bloc 8 : cache passif_total
                total += x
        return total

    # ------------------------------------------------------------------
    #  ÉTAPE 7 — Faillites et cascades
    # ------------------------------------------------------------------

    def is_bankrupt(self, entity: Entity) -> bool:
        return entity.alive and entity.actif_total + self.config.epsilon < entity.passif_bilan

    def _capture_system_state(self) -> dict:
        """Snapshot du système avant résolution des faillites."""
        alive = self.active_entities()
        return {
            "actif_total": sum(e.actif_total for e in alive),
            "passif_total": sum(e.passif_total for e in alive),
            "liquidite": sum(e.actif_liquide for e in alive),
            "nb_entites": len(alive),
        }

    def compute_hidden_fragility(self) -> Dict[int, float]:
        """
        Calcule, pour chaque entité vivante prêteuse, l'écart entre la valeur
        nominale portée au bilan (actif_prete, via loan.principal) et la valeur
        économique réelle de ses créances (principal × (1−δ_exo)^âge).
        Ne modifie aucun bilan. Utilisé uniquement à des fins statistiques.
        Retourne {entity_id: perte_cachée_totale}.
        """
        factor = max(0.0, 1.0 - self.config.taux_depreciation_exo)
        fragility: Dict[int, float] = {}
        for loan in self.active_loans():
            lender = self.get_entity(loan.lender_id)
            if not lender.alive:
                continue
            age = self.current_step - loan.creation_step
            real_value = loan.principal * (factor ** age)
            hidden_loss = loan.principal - real_value
            if hidden_loss > self.config.epsilon:
                fragility[loan.lender_id] = fragility.get(loan.lender_id, 0.0) + hidden_loss
        return fragility

    def process_single_failure(self, failed_entity: Entity) -> Dict[str, float]:
        """
        Traite la faillite d'une entité en trois phases :
          1) Identification des créanciers (poids proportionnels aux encours).
          2) Redistribution directe des créances où l'entité était prêteuse :
             chaque prêt est réévalué à sa valeur réelle (principal×(1−δ)^âge) puis
             fractionné entre les créanciers au prorata de leurs poids.
             Le bilan de l'emprunteur n'est pas modifié : K^exo et P^exo ont déjà
             décru via apply_depreciation(). Si pas de créanciers éligibles, la
             créance est annulée symétriquement (K^exo et P^exo réduits).
          3) Annulation des prêts dont l'entité était emprunteuse (perte pour prêteurs).
        Retourne {destroyed_assets, redirected_claims}.
        """
        destroyed_assets = 0.0
        redirected_claims = 0.0

        # Phase 1 : calcul des poids créanciers (avant annulation des emprunts)
        creditors: Dict[int, float] = {}
        for loan in self.active_loans():
            if loan.borrower_id == failed_entity.entity_id:
                creditors[loan.lender_id] = creditors.get(loan.lender_id, 0.0) + loan.principal
        total_claims = sum(creditors.values())
        weights: Dict[int, float] = {}
        if total_claims > self.config.epsilon:
            weights = {cid: amt / total_claims for cid, amt in creditors.items()}

        # Phase 2 : redistribution des prêts où l'entité faillie était prêteuse
        factor = max(0.0, 1.0 - self.config.taux_depreciation_exo)
        for loan in list(self.active_loans()):
            if loan.lender_id != failed_entity.entity_id:
                continue
            age = self.current_step - loan.creation_step
            real_value = loan.principal * (factor ** age)

            # Créanciers éligibles : exclure les auto-prêts (cid == borrower)
            eligible = {cid: w for cid, w in weights.items() if cid != loan.borrower_id}
            total_eligible = sum(eligible.values())

            if real_value <= self.config.epsilon or total_eligible <= self.config.epsilon:
                # Annulation symétrique : l'emprunteur perd la contrepartie exo
                borrower = self.get_entity(loan.borrower_id)
                cancel = min(real_value, borrower.actif_exoinvesti)
                borrower.actif_exoinvesti -= cancel
                exo_cancel = min(real_value, borrower.passif_exoinvesti)
                borrower.passif_exoinvesti -= exo_cancel
                borrower.passif_total -= exo_cancel  # Bloc 8 : cache passif_total
                # Cache : le prêt disparaît → l'emprunteur ne doit plus ces charges.
                if borrower.alive:
                    borrower.charges_interets -= loan.rate * loan.principal
                # Le prêteur est l'entité faillie (morte) → son cache n'importe pas.
                loan.active = False
                continue

            # Redistribution fractionnée à valeur réelle
            loan.active = False
            borrower = self.get_entity(loan.borrower_id)
            # Cache : supprime la contribution du prêt original (prêteur = entité faillie).
            # La somme redistribuée = real_value ; la différence avec loan.principal
            # (dépreciation non réévaluée) est absorbée par l'emprunteur.
            if borrower.alive:
                borrower.charges_interets += loan.rate * (real_value - loan.principal)
            for cid, w in eligible.items():
                share = (w / total_eligible) * real_value
                if share <= self.config.epsilon:
                    continue
                creditor = self.get_entity(cid)
                if not creditor.alive:
                    continue
                self.create_loan(
                    lender_id=cid,
                    borrower_id=loan.borrower_id,
                    principal=share,
                    rate=loan.rate,
                    parent_loan_id=loan.loan_id,
                )
                creditor.actif_prete += share
                creditor.passif_credit_detenu += share
                creditor.revenus_interets += loan.rate * share
                redirected_claims += share

        # Phase 3 : annulation des prêts dont l'entité faillie était emprunteuse
        for loan in list(self.active_loans()):
            if loan.borrower_id == failed_entity.entity_id:
                lender = self.get_entity(loan.lender_id)
                lender.actif_prete -= loan.principal
                lender.passif_credit_detenu -= loan.principal
                # Cache : le prêteur perd ses revenus sur ce prêt.
                lender.revenus_interets -= loan.rate * loan.principal
                # L'emprunteur (entité faillie) perd ses charges ; inutile de mettre à
                # jour son cache car elle sera marquée morte juste après.
                destroyed_assets += loan.principal
                loan.active = False

        failed_entity.alive = False
        failed_entity.death_step = self.current_step
        self.log(f"Faillite entité {failed_entity.entity_id}")
        return {"destroyed_assets": destroyed_assets, "redirected_claims": redirected_claims}

    def resolve_cascades(self) -> Tuple[Dict[str, float], Optional[CascadeEvent]]:
        """
        Détecte et résout les faillites en cascade.
        Retourne (totals_dict, cascade_event_ou_None).
        """
        state_before = self._capture_system_state()
        # Entités solvables avant la cascade (pour détecter la contagion)
        solvent_before = {
            eid for eid, e in self.entities.items()
            if e.alive and e.actif_total >= e.passif_total - self.config.epsilon
        }

        totals = {"destroyed_assets": 0.0, "redirected_claims": 0.0, "failures": 0.0}
        faillis_info = []

        changed = True
        while changed:
            changed = False
            bankrupts = [e for e in self.active_entities() if self.is_bankrupt(e)]
            if not bankrupts:
                break
            for entity in bankrupts:
                if not entity.alive:
                    continue
                faillis_info.append({
                    "actif_total": entity.actif_total,
                    "passif_total": entity.passif_total,
                    "etait_solvable": entity.entity_id in solvent_before,
                })
                result = self.process_single_failure(entity)
                totals["destroyed_assets"] += result["destroyed_assets"]
                totals["redirected_claims"] += result["redirected_claims"]
                totals["failures"] += 1.0
                changed = True

        cascade_event = None
        if faillis_info:
            cascade_event = Collector.build_cascade(
                self.current_step,
                state_before,
                faillis_info,
                totals["destroyed_assets"],
            )

        return totals, cascade_event

    # ------------------------------------------------------------------
    #  ÉTAPE 4b — Amortissement du principal
    # ------------------------------------------------------------------

    def pay_amortization_phase(self) -> float:
        """
        Remboursement géométrique du principal pour tous les prêts actifs :
          amort = taux_amortissement × principal_restant
        Le borrower verse ce montant au lender ; principal et passif_exoinvesti
        diminuent en conséquence. actif_exoinvesti reste inchangé : l'investissement
        subsiste, la dette seule décroît, ce qui crée de l'équité graduellement.
        Les prêts avec un prêteur mort (cas résiduel défensif) sont ignorés.
        """
        tau = self.config.taux_amortissement
        if tau <= self.config.epsilon:
            return 0.0
        total = 0.0
        for loan in sorted(self.active_loans(), key=lambda x: x.loan_id):
            total += self._pay_single_amortization(loan, tau)
        return total

    def _pay_single_amortization(self, loan: Loan, tau: float) -> float:
        if not loan.active:
            return 0.0
        lender = self.get_entity(loan.lender_id)
        if not lender.alive:
            return 0.0   # garde défensif (ne devrait pas survenir après redistribution)
        due = tau * loan.principal
        if due <= self.config.epsilon:
            return 0.0
        borrower = self.get_entity(loan.borrower_id)
        payment = self._ensure_payment_capacity(borrower, due, loan.lender_id)

        # Réduction du principal (proportionnelle au paiement effectif)
        reduction = min(payment, loan.principal)
        loan.principal -= reduction
        borrower.passif_exoinvesti -= reduction   # la dette fond
        borrower.passif_total -= reduction         # Bloc 8 : cache passif_total
        lender.actif_prete -= reduction            # créance réduite d'autant
        lender.passif_credit_detenu -= reduction   # passif miroir réduit
        lender.actif_liquide += payment            # cash reçu par le prêteur
        # Cache intérêts : la réduction de principal diminue les flux futurs r·q.
        delta_flow = loan.rate * reduction
        borrower.charges_interets -= delta_flow
        lender.revenus_interets -= delta_flow

        if loan.principal <= self.config.epsilon:
            loan.active = False

        return payment

    # ------------------------------------------------------------------
    #  MOUVEMENT BROWNIEN DES ALPHAS
    # ------------------------------------------------------------------

    def _update_alphas(self) -> None:
        """Mise à jour géométrique de alpha pour chaque entité vivante.
        alpha_t = alpha_{t-1} * exp(sigma * N(0,1))
        Sans effet si alpha_sigma_brownien == 0.
        """
        sigma = self.config.alpha_sigma_brownien
        if sigma <= 0:
            return
        for e in self.active_entities():
            e.alpha *= math.exp(self.rng.gauss(0.0, sigma))

    # ------------------------------------------------------------------
    #  STATISTIQUES LÉGÈRES
    # ------------------------------------------------------------------

    def _collect_light_stats(
        self,
        spawn_count: int,
        extraction_total: float,
        interest_paid: float,
        amortissement_total: float,
        credit_transactions: int,
        auto_invest_total: float,
        cascade_totals: Dict,
    ) -> Dict:
        alive = self.active_entities()
        active_loans = self.active_loans()
        passifs = [e.passif_total for e in alive]
        rates = [
            self.compute_internal_rate(e)
            for e in alive if e.passif_total > self.config.epsilon
        ]
        data = {
            "step": self.current_step,
            "n_entities_alive": len(alive),
            "n_entities_total": len(self.entities),
            "n_spawned": spawn_count,
            "extraction_total": round(extraction_total, 4),
            "interest_paid_total": round(interest_paid, 4),
            "amortissement_total": round(amortissement_total, 4),
            "credit_transactions": credit_transactions,
            "auto_invest_total": round(auto_invest_total, 4),
            "n_failures": int(cascade_totals["failures"]),
            "destroyed_assets": round(cascade_totals["destroyed_assets"], 4),
            "redirected_claims": round(cascade_totals["redirected_claims"], 4),
            "volume_prets_actifs": round(sum(l.principal for l in active_loans), 4),
            "n_prets_actifs": len(active_loans),
            "actif_total_systeme": round(sum(e.actif_total for e in alive), 4),
            "passif_total_systeme": round(sum(e.passif_total for e in alive), 4),
            "liquidite_totale": round(sum(e.actif_liquide for e in alive), 4),
            "mean_passif": round(sum(passifs) / len(passifs), 4) if passifs else 0.0,
            "mean_internal_rate": round(sum(rates) / len(rates), 6) if rates else 0.0,
        }
        self.stats.append(data)
        return data

    # ------------------------------------------------------------------
    #  PAS DE SIMULATION
    # ------------------------------------------------------------------

    def run_step(self) -> Dict:
        self._reset_step_flows()
        self._update_alphas()
        spawn_count = self.spawn_new_entities()
        extraction_total = self.extract_from_nature()

        interest_paid = self.pay_interest_phase()

        amortissement_total = self.pay_amortization_phase()

        self.apply_depreciation()
        self._rebuild_interest_cache()  # Bloc 8 : O(N_loans) une seule fois par pas
        credit_transactions = self.credit_market_iteration()
        cascade_totals, cascade_event = self.resolve_cascades()
        auto_invest_total = self.auto_invest_end_of_turn()

        light_stats = self._collect_light_stats(
            spawn_count, extraction_total, interest_paid,
            amortissement_total, credit_transactions, auto_invest_total, cascade_totals,
        )

        # Collecteur statistique riche
        self.collector.record_step(self, cascade_event, self._step_flows)

        self.current_step += 1
        return light_stats

    # ------------------------------------------------------------------
    #  EXÉCUTION COMPLÈTE
    # ------------------------------------------------------------------

    def run(self, n_steps: Optional[int] = None, verbose: bool = True) -> List[Dict]:
        n = self.config.duree_simulation if n_steps is None else n_steps
        report_interval = max(1, n // 10)

        if verbose:
            print(f"Démarrage : {n} pas, {len(self.entities)} entités initiales")

        for k in range(n):
            self.run_step()
            if verbose and (k + 1) % report_interval == 0:
                s = self.stats[-1]
                print(
                    f"  Pas {k+1:5d} | Entités: {s['n_entities_alive']:4d} | "
                    f"Faillites: {s['n_failures']:3d} | "
                    f"Prêts actifs: {s['n_prets_actifs']:5d} | "
                    f"Vol. prêts: {s['volume_prets_actifs']:10.1f}"
                )

        if verbose:
            print("Simulation terminée.")
        return self.stats

    # ------------------------------------------------------------------
    #  EXPORTS
    # ------------------------------------------------------------------

    def export_stats_csv(self, filepath: str) -> None:
        if not self.stats:
            return
        fieldnames = list(self.stats[0].keys())
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.stats)

    def export_event_log(self, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            for line in self.event_log:
                f.write(line + "\n")

    def summary(self) -> dict:
        if not self.stats:
            return {}
        total_failures = sum(s["n_failures"] for s in self.stats)
        max_cascade = max(s["n_failures"] for s in self.stats)
        return {
            "steps_simulated": self.current_step,
            "entities_created_total": len(self.entities),
            "entities_alive_final": self.stats[-1]["n_entities_alive"],
            "failures_total": total_failures,
            "cascade_max_size": max_cascade,
            "loans_created_total": len(self.loans),
            "loans_active_final": self.stats[-1]["n_prets_actifs"],
            "cascades_recorded": len(self.collector.cascades),
        }
