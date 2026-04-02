"""
simulation.py — Moteur de simulation multi-agents.

Architecture ChatGPT :
  - Références par ID entier (pas de pointeurs directs entre objets)
  - Conteneurs : Dict[int, Entity], Dict[int, Loan], Dict[int, BankruptcyEstate]
  - RNG isolé (random.Random(seed), pas de random global)
  - Séparation nette des responsabilités

Paramètres : ceux du modèle Claude (alpha=1.0, seuil=0.05, passif_inne=5.0…)
Durée       : 3000 pas
Taux crédit : configurable (taux prêteur ou moyenne prêteur/emprunteur)
Auto-invest : fraction du surplus (L - seuil*P) uniquement

Statistiques : le Collector est instancié dans Simulation et appelé
               à chaque pas — voir statistics.py pour le détail.
"""

from __future__ import annotations

import csv
import math
import random
from typing import Dict, List, Optional, Tuple

from config import SimulationConfig
from models import BankruptcyEstate, Entity, Loan
from statistics import CascadeEvent, Collector

_P_WATCH_NEW = 0.03


class Simulation:
    def __init__(self, config: Optional[SimulationConfig] = None) -> None:
        self.config = config or SimulationConfig()
        self.rng = random.Random(self.config.seed)

        self.entities: Dict[int, Entity] = {}
        self.loans: Dict[int, Loan] = {}
        self.estates: Dict[int, BankruptcyEstate] = {}

        self.current_step: int = 0
        self.next_entity_id: int = 1
        self.next_loan_id: int = 1
        self.next_estate_id: int = 1

        # Statistiques légères (une ligne par pas)
        self.stats: List[Dict] = []
        self.event_log: List[str] = []

        # Collecteur statistique riche
        self.collector = Collector(freq_snapshot=self.config.freq_snapshot)

        self._step_flows: dict = {}  # eid -> flow dict (reset each step)

        self._create_initial_population(10)

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
        return self.config.alpha / (2.0 * math.sqrt(p))

    # ------------------------------------------------------------------
    #  CRÉATION D'ENTITÉS
    # ------------------------------------------------------------------

    def create_entity(
        self,
        actif_liquide: Optional[float] = None,
        passif_inne: Optional[float] = None,
    ) -> Entity:
        entity = Entity(
            entity_id=self.next_entity_id,
            actif_liquide=self.config.actif_liquide_initial if actif_liquide is None else actif_liquide,
            passif_inne=self.config.passif_inne_initial if passif_inne is None else passif_inne,
            creation_step=self.current_step,
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
            extracted = self.config.alpha * math.sqrt(max(e.passif_total, 0.0))
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
        Mobilise la capacité de paiement de payer dans l'ordre :
          1) Actif liquide disponible
          2) Cession de créances (les moins rémunératrices en premier)
          3) Reliquéfaction de l'endo-investi
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

        # 2) Cession de créances
        if amount_remaining > self.config.epsilon:
            transferred = self._transfer_claims_for_payment(
                payer.entity_id, creditor_id, amount_remaining
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

        return paid

    def _transfer_claims_for_payment(
        self, from_entity_id: int, to_entity_id: int, amount_needed: float
    ) -> float:
        """
        Cède des créances de from_entity vers to_entity pour couvrir amount_needed.
        Priorité : créances à plus faible taux (puis loan_id pour stabilité).
        Retourne le montant effectivement transféré.
        """
        payer = self.get_entity(from_entity_id)
        transferable = sorted(
            [loan for loan in self.active_loans() if loan.lender_id == from_entity_id],
            key=lambda x: (x.rate, x.loan_id),
        )
        transferred_total = 0.0

        for loan in transferable:
            if transferred_total >= amount_needed - self.config.epsilon:
                break
            remain = amount_needed - transferred_total
            transfer_amount = min(loan.principal, remain)
            if transfer_amount <= self.config.epsilon:
                continue

            payer.actif_prete -= transfer_amount
            receiver = self.get_entity(to_entity_id)
            receiver.actif_prete += transfer_amount

            if abs(transfer_amount - loan.principal) <= self.config.epsilon:
                # Cession totale : simple changement de prêteur
                loan.lender_id = to_entity_id
            else:
                # Cession partielle : scission du prêt
                t_id = self.next_loan_id
                r_id = self.next_loan_id + 1
                transferred, remaining = loan.split(t_id, r_id, transfer_amount, to_entity_id)
                self.loans[transferred.loan_id] = transferred
                self.loans[remaining.loan_id] = remaining
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
    #  ÉTAPE 3b — Redistribution depuis les masses de faillite
    # ------------------------------------------------------------------

    def redistribute_estate_interest(self) -> float:
        """
        Collecte les intérêts des prêts portés par les masses de faillite
        et les redistribue aux créanciers bénéficiaires au prorata.
        """
        total = 0.0
        failed_to_estate = {
            estate.failed_entity_id: estate
            for estate in self.estates.values()
            if estate.active
        }
        for loan in self.active_loans():
            estate = failed_to_estate.get(loan.lender_id)
            if estate is None:
                continue
            interest = loan.interest_due()
            if interest <= self.config.epsilon:
                continue
            borrower = self.get_entity(loan.borrower_id)
            # Utiliser le premier bénéficiaire comme proxy pour la capacité de paiement
            first_beneficiary_id = next(iter(estate.beneficiary_weights), None)
            if first_beneficiary_id is None:
                continue
            payment = self._ensure_payment_capacity(borrower, interest, first_beneficiary_id)
            distribution = estate.redistribute_interest(payment)
            for beneficiary_id, amount in distribution.items():
                beneficiary = self.get_entity(beneficiary_id)
                if beneficiary.alive and amount > self.config.epsilon:
                    beneficiary.actif_liquide += amount
                    total += amount
        return total

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

    # ------------------------------------------------------------------
    #  ÉTAPE 5 — Marché du crédit
    # ------------------------------------------------------------------

    def _select_active_credit_entities(self) -> List[Entity]:
        s = self.config.seuil_ratio_liquide_passif
        return [
            e for e in self.active_entities()
            if e.passif_total > self.config.epsilon and e.ratio_liquide_passif > s
        ]

    def _lender_offer(self, lender: Entity) -> float:
        return max(
            0.0,
            lender.actif_liquide - self.config.seuil_ratio_liquide_passif * lender.passif_total,
        )

    def _borrower_qmax(self, borrower: Entity, rate: float) -> float:
        if rate <= self.config.epsilon:
            return 0.0
        qmax = (self.config.alpha / (2.0 * rate)) ** 2 - borrower.passif_total
        return max(0.0, qmax)

    def _gain_auto_invest(self, borrower: Entity, amount: float) -> float:
        if amount <= self.config.epsilon:
            return 0.0
        p = borrower.passif_total
        return self.config.alpha * (math.sqrt(p + amount) - math.sqrt(p))

    def _gain_borrow(self, borrower: Entity, amount: float, rate: float) -> float:
        if amount <= self.config.epsilon:
            return 0.0
        p = borrower.passif_total
        gross = self.config.alpha * (math.sqrt(p + amount) - math.sqrt(p))
        return gross - rate * amount

    def _gain_lend(self, lender: Entity, amount: float, rate: float) -> float:
        if amount <= self.config.epsilon:
            return 0.0
        p = lender.passif_total
        gross = self.config.alpha * (math.sqrt(p + amount) - math.sqrt(p))
        return rate * amount - gross 

    def _borrowing_is_acceptable(self, borrower: Entity, amount: float, rate: float) -> bool:
        if amount <= self.config.epsilon:
            return False
        gain_b = self._gain_borrow(borrower, amount, rate)
        auto_amount = min(amount, borrower.actif_liquide)
        gain_a = self._gain_auto_invest(borrower, auto_amount)
        if gain_a <= self.config.epsilon:
            return gain_b > self.config.epsilon
        return gain_b / gain_a >= 1.0 + self.config.mu

    def _lending_is_acceptable(self, lender: Entity, amount: float, rate: float) -> bool:
        if amount <= self.config.epsilon:
            return False
        gain_lend = self._gain_lend(lender, amount, rate)
        auto_amount = min(amount, lender.actif_liquide)
        gain_auto_invest = self._gain_auto_invest(lender, auto_amount)
        if gain_auto_invest <= self.config.epsilon:
            return gain_lend > self.config.epsilon
        return gain_lend / gain_auto_invest >= 1.0 + self.config.mu

    def execute_loan(self, lender: Entity, borrower: Entity, principal: float, rate: float) -> Loan:
        lender.actif_liquide -= principal
        lender.actif_prete += principal
        borrower.actif_exoinvesti += principal
        borrower.passif_exoinvesti += principal
        loan = self.create_loan(lender.entity_id, borrower.entity_id, principal, rate)
        self.log(
            f"Prêt {loan.loan_id}: {lender.entity_id} -> {borrower.entity_id}, "
            f"q={principal:.4f}, r={rate:.4f}"
        )
        return loan

    def credit_market_iteration(self) -> int:
        """
        Appariement itératif prêteur/emprunteur.
        Taux : configurable (taux prêteur seul ou moyenne des deux taux internes).
        Arrêt si aucune transaction productive.
        """
        transactions = 0
        for _ in range(self.config.max_credit_iterations):
            active = self._select_active_credit_entities()
            if len(active) < 2:
                break

            active_sorted = sorted(active, key=self.compute_internal_rate)
            lender = active_sorted[0]    # taux le plus faible → prêteur
            borrower = active_sorted[-1] # taux le plus élevé → emprunteur

            if lender.entity_id == borrower.entity_id:
                break

            lender_rate = self.compute_internal_rate(lender)
            borrower_rate = self.compute_internal_rate(borrower)
            if borrower_rate <= lender_rate + self.config.epsilon:
                break

            offer = self._lender_offer(lender)
            if offer <= self.config.epsilon:
                break

            if self.config.use_lender_rate_as_offer_rate:
                rate = lender_rate
            else:
                rate = 0.5 * (lender_rate + borrower_rate)

            qmax = self._borrower_qmax(borrower, rate)
            demand = self.config.theta * qmax
            principal = min(offer, demand)

            if principal <= self.config.epsilon:
                break
            if not self._borrow_is_acceptable(borrower, principal, rate):
                break

            self.execute_loan(lender, borrower, principal, rate)
            transactions += 1
        return transactions

    # ------------------------------------------------------------------
    #  ÉTAPE 6 — Auto-investissement
    # ------------------------------------------------------------------

    def auto_invest_end_of_turn(self) -> float:
        """
        Convertit une fraction du surplus liquide en investissement endogène.
        Surplus = max(0, L - seuil * P)
        """
        total = 0.0
        for e in self.active_entities():
            surplus = max(0.0, e.actif_liquide - self.config.seuil_ratio_liquide_passif * e.passif_total)
            x = self.config.fraction_auto_investissement * surplus
            if x > self.config.epsilon:
                e.actif_liquide -= x
                e.actif_endoinvesti += x
                e.passif_endoinvesti += x
                total += x
        return total

    # ------------------------------------------------------------------
    #  ÉTAPE 7 — Faillites et cascades
    # ------------------------------------------------------------------

    def is_bankrupt(self, entity: Entity) -> bool:
        return entity.alive and entity.actif_total + self.config.epsilon < entity.passif_total

    def _capture_system_state(self) -> dict:
        """Snapshot du système avant résolution des faillites."""
        alive = self.active_entities()
        return {
            "actif_total": sum(e.actif_total for e in alive),
            "passif_total": sum(e.passif_total for e in alive),
            "liquidite": sum(e.actif_liquide for e in alive),
            "nb_entites": len(alive),
        }

    def create_bankruptcy_estate(self, failed_entity_id: int) -> Optional[BankruptcyEstate]:
        """Crée une masse de faillite pour les créanciers de l'entité faillie."""
        creditors: Dict[int, float] = {}
        for loan in self.active_loans():
            if loan.borrower_id == failed_entity_id:
                creditors[loan.lender_id] = creditors.get(loan.lender_id, 0.0) + loan.principal

        total_claims = sum(creditors.values())
        if total_claims <= self.config.epsilon:
            return None

        weights = {cid: claim / total_claims for cid, claim in creditors.items()}
        inherited_loan_ids = [
            loan.loan_id for loan in self.active_loans()
            if loan.lender_id == failed_entity_id
        ]
        estate = BankruptcyEstate(
            estate_id=self.next_estate_id,
            failed_entity_id=failed_entity_id,
            beneficiary_weights=weights,
            inherited_loan_ids=inherited_loan_ids,
            active=True,
        )
        self.estates[estate.estate_id] = estate
        self.next_estate_id += 1
        return estate

    def process_single_failure(self, failed_entity: Entity) -> Dict[str, float]:
        """
        Traite la faillite d'une entité :
          - Crée une masse de faillite pour les prêts qu'elle portait
          - Annule les prêts dont elle était emprunteuse
          - La marque comme morte
        Retourne {destroyed_assets (créances annulées), redirected_claims}.
        """
        destroyed_assets = 0.0
        redirected_claims = 0.0

        estate = self.create_bankruptcy_estate(failed_entity.entity_id)
        if estate is not None:
            for loan_id in estate.inherited_loan_ids:
                redirected_claims += self.loans[loan_id].principal

        # Annuler les prêts dont l'entité est emprunteuse
        for loan in list(self.active_loans()):
            if loan.borrower_id == failed_entity.entity_id:
                lender = self.get_entity(loan.lender_id)
                lender.actif_prete -= loan.principal
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
    #  STATISTIQUES LÉGÈRES
    # ------------------------------------------------------------------

    def _collect_light_stats(
        self,
        spawn_count: int,
        extraction_total: float,
        interest_paid: float,
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
        spawn_count = self.spawn_new_entities()
        extraction_total = self.extract_from_nature()

        interest_paid = self.pay_interest_phase()
        redistributed = self.redistribute_estate_interest()
        interest_paid += redistributed

        self.apply_depreciation()
        credit_transactions = self.credit_market_iteration()
        auto_invest_total = self.auto_invest_end_of_turn()
        cascade_totals, cascade_event = self.resolve_cascades()

        light_stats = self._collect_light_stats(
            spawn_count, extraction_total, interest_paid,
            credit_transactions, auto_invest_total, cascade_totals,
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
            "estates_created": len(self.estates),
            "cascades_recorded": len(self.collector.cascades),
        }
