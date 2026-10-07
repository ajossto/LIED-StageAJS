from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from .bankruptcy import net_worth, resolve_cascades
from .config import M2Config
from .contracts import ContractBook
from .entities import Entity
from .market import run_credit_market
from .metrics import StepMetrics, credit_concentration, snapshot_rows


@dataclass(slots=True)
class SimulationRun:
    timeseries: list[StepMetrics]
    snapshots: dict[int, list[dict[str, int | float]]]
    events: list[dict]


class M2Simulation:
    def __init__(self, config: M2Config | None = None, seed: int = 0) -> None:
        if seed < 0:
            raise ValueError("seed doit être positif ou nul")
        self.config = config or M2Config()
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.entities: dict[int, Entity] = {}
        self.book = ContractBook()
        self.current_step = 0
        self.next_entity_id = 0
        self.timeseries: list[StepMetrics] = []
        self.events: list[dict] = []

    def _event(self, event: dict) -> None:
        if self.config.log_events:
            self.events.append(event)

    def alive_ids(self) -> list[int]:
        return sorted(i for i, entity in self.entities.items() if entity.alive)

    def create_entity(
        self,
        w: float | None = None,
        d0: float | None = None,
        birth_step: int | None = None,
    ) -> Entity:
        capital = self.config.w0 if w is None else float(w)
        initial_debt = self.config.d0 if d0 is None else float(d0)
        if not math.isfinite(capital) or capital < 0:
            raise ValueError("capital initial invalide")
        if not math.isfinite(initial_debt) or initial_debt < 0:
            raise ValueError("d0 initial invalide")
        entity = Entity(
            entity_id=self.next_entity_id,
            w=capital,
            d0=initial_debt,
            birth_step=self.current_step if birth_step is None else birth_step,
        )
        self.entities[entity.entity_id] = entity
        self.next_entity_id += 1
        return entity

    def net_worth(self, entity_id: int) -> float:
        return net_worth(self.entities[entity_id], self.book)

    def create_loan(
        self, lender_id: int, borrower_id: int, principal: float, rate: float
    ):
        lender = self.entities[lender_id]
        borrower = self.entities[borrower_id]
        if not lender.alive or not borrower.alive:
            raise ValueError("les deux parties doivent être vivantes")
        if principal > lender.w:
            raise ValueError("le prêteur ne possède pas le principal")
        before = lender.w + borrower.w
        lender.w -= principal
        borrower.w += principal
        contract = self.book.add(
            lender_id,
            borrower_id,
            principal,
            rate,
            creation_step=self.current_step,
        )
        if not math.isclose(
            before, lender.w + borrower.w, rel_tol=1e-12, abs_tol=1e-12
        ):
            raise AssertionError("transfert de principal non conservatif")
        return contract

    def _reset_flows(self) -> None:
        for entity_id in self.alive_ids():
            self.entities[entity_id].reset_step_flows()

    def _births(self, step: int) -> int:
        births = int(self.rng.poisson(self.config.birth_rate))
        for _ in range(births):
            self.create_entity(birth_step=step)
        return births

    def _apply_shocks(self) -> float:
        ids = self.alive_ids()
        if not ids or not self.config.shocks_enabled or self.config.sigma == 0:
            return 0.0
        before = math.fsum(self.entities[i].w for i in ids)
        sigma = self.config.sigma
        shocks = self.rng.normal(-0.5 * sigma * sigma, sigma, size=len(ids))
        for entity_id, eta in zip(ids, shocks, strict=True):
            updated = self.entities[entity_id].w * math.exp(float(eta))
            if not math.isfinite(updated):
                raise FloatingPointError(
                    f"capital non fini après choc pour l'entité {entity_id}"
                )
            self.entities[entity_id].w = updated
        after = math.fsum(self.entities[i].w for i in ids)
        return after - before

    def _extract(self) -> float:
        total = 0.0
        for entity_id in self.alive_ids():
            entity = self.entities[entity_id]
            flow = self.config.alpha * math.sqrt(entity.w)
            entity.extraction = flow
            entity.w += flow
            total += flow
        return total

    def _service_interests_pro_rata(self) -> tuple[float, float]:
        capital_before = math.fsum(self.entities[i].w for i in self.alive_ids())
        by_borrower: dict[int, list] = defaultdict(list)
        for contract in sorted(
            self.book.contracts.values(), key=lambda item: item.contract_id
        ):
            due = contract.rate * contract.principal
            if due > 0:
                by_borrower[contract.borrower_id].append((contract, due))

        deltas: dict[int, float] = defaultdict(float)
        paid_by_borrower: dict[int, float] = defaultdict(float)
        received_by_lender: dict[int, float] = defaultdict(float)
        total_due = 0.0
        total_paid = 0.0
        for borrower_id in sorted(by_borrower):
            obligations = by_borrower[borrower_id]
            due_sum = math.fsum(due for _, due in obligations)
            total_due += due_sum
            available = self.entities[borrower_id].w
            paid_sum = min(available, due_sum)
            if paid_sum < due_sum:
                self.entities[borrower_id].defaulted = True
            allocated = 0.0
            for position, (contract, due) in enumerate(obligations):
                if paid_sum == due_sum:
                    payment = due
                elif position == len(obligations) - 1:
                    payment = paid_sum - allocated
                else:
                    payment = paid_sum * due / due_sum
                    allocated += payment
                if payment <= 0:
                    continue
                deltas[borrower_id] -= payment
                deltas[contract.lender_id] += payment
                paid_by_borrower[borrower_id] += payment
                received_by_lender[contract.lender_id] += payment
                total_paid += payment

        for entity_id, delta in deltas.items():
            self.entities[entity_id].w += delta
            if self.entities[entity_id].w < 0 and self.entities[entity_id].w > -1e-10:
                self.entities[entity_id].w = 0.0
        for entity_id, amount in paid_by_borrower.items():
            self.entities[entity_id].interest_paid += amount
        for entity_id, amount in received_by_lender.items():
            self.entities[entity_id].interest_received += amount
        capital_after = math.fsum(self.entities[i].w for i in self.alive_ids())
        if not math.isclose(capital_before, capital_after, rel_tol=1e-11, abs_tol=1e-9):
            raise AssertionError(
                "le service prorata des intérêts n'est pas conservatif"
            )
        return total_due, total_paid

    def _service_interests_sequential(self) -> tuple[float, float]:
        capital_before = math.fsum(self.entities[i].w for i in self.alive_ids())
        total_due = 0.0
        total_paid = 0.0
        for contract in sorted(
            self.book.contracts.values(), key=lambda item: item.contract_id
        ):
            due = contract.rate * contract.principal
            total_due += due
            borrower = self.entities[contract.borrower_id]
            lender = self.entities[contract.lender_id]
            payment = min(borrower.w, due)
            borrower.w -= payment
            lender.w += payment
            borrower.interest_paid += payment
            lender.interest_received += payment
            total_paid += payment
            if payment < due:
                borrower.defaulted = True
        capital_after = math.fsum(self.entities[i].w for i in self.alive_ids())
        if not math.isclose(capital_before, capital_after, rel_tol=1e-11, abs_tol=1e-9):
            raise AssertionError(
                "le service séquentiel des intérêts n'est pas conservatif"
            )
        return total_due, total_paid

    def service_interests(self) -> tuple[float, float]:
        if self.config.interest_service == "pro_rata":
            return self._service_interests_pro_rata()
        return self._service_interests_sequential()

    def _depreciate(self) -> float:
        before = math.fsum(self.entities[i].w for i in self.alive_ids())
        factor = 1.0 - self.config.delta
        for entity_id in self.alive_ids():
            self.entities[entity_id].w *= factor
        after = math.fsum(self.entities[i].w for i in self.alive_ids())
        return before - after

    def validate_invariants(self, require_stable: bool = False) -> None:
        living = self.alive_ids()
        for entity_id in living:
            capital = self.entities[entity_id].w
            if not math.isfinite(capital) or capital < 0:
                raise AssertionError(f"capital invalide pour {entity_id}: {capital}")
        self.book.validate(living)
        claims = math.fsum(self.book.claims(i) for i in living)
        debts = math.fsum(self.book.debts(i) for i in living)
        principal = self.book.total_principal()
        if not math.isclose(claims, principal, rel_tol=1e-11, abs_tol=1e-9):
            raise AssertionError("somme des créances incohérente")
        if not math.isclose(debts, principal, rel_tol=1e-11, abs_tol=1e-9):
            raise AssertionError("somme des dettes incohérente")
        if require_stable:
            unstable = [
                i for i in living if self.entities[i].defaulted or self.net_worth(i) < 0
            ]
            if unstable:
                raise AssertionError(f"cascade incomplète: {unstable[:5]}")

    def step(self) -> StepMetrics:
        step = self.current_step + 1
        self._reset_flows()
        births = self._births(step)
        nw_start = {
            entity_id: self.net_worth(entity_id) for entity_id in self.alive_ids()
        }

        shock_change = self._apply_shocks()
        extraction = self._extract()
        interest_due, interest_paid = self.service_interests()
        depreciation_loss = self._depreciate()
        market = run_credit_market(
            self.entities,
            self.book,
            self.rng,
            self.config,
            step,
            event_sink=self._event,
        )
        cascade = resolve_cascades(
            self.entities,
            self.book,
            self.config,
            step,
            event_sink=self._event,
        )
        self.current_step = step

        for entity_id in self.alive_ids():
            self.entities[entity_id].nw_delta = (
                self.net_worth(entity_id) - nw_start[entity_id]
            )

        if self.config.check_invariants:
            self.validate_invariants(require_stable=True)

        living = self.alive_ids()
        waves = json.dumps(list(cascade.wave_sizes), separators=(",", ":"))
        metrics = StepMetrics(
            step=step,
            population=len(living),
            births=births,
            failures=cascade.failures,
            cascade_waves=waves,
            max_wave_size=max(cascade.wave_sizes, default=0),
            total_capital=math.fsum(self.entities[i].w for i in living),
            total_net_worth=math.fsum(self.net_worth(i) for i in living),
            active_contracts=len(self.book),
            total_credit=self.book.total_principal(),
            credit_hhi=credit_concentration(self.entities, self.book),
            market_rounds=market.rounds,
            loans_created=market.contracts_created,
            loan_volume=market.volume,
            interest_due=interest_due,
            interest_paid=interest_paid,
            extraction=extraction,
            shock_capital_change=shock_change,
            depreciation_loss=depreciation_loss,
            canceled_debt=cascade.canceled_debt,
            transferred_claims=cascade.transferred_claims,
            destroyed_claims=cascade.destroyed_claims,
            recovered_capital=cascade.recovered_capital,
            destroyed_capital=cascade.destroyed_capital,
        )
        self.timeseries.append(metrics)
        return metrics

    def snapshot(self) -> list[dict[str, int | float]]:
        return snapshot_rows(self.current_step, self.entities, self.book)

    def run(self, steps: int | None = None) -> SimulationRun:
        target = self.config.steps if steps is None else steps
        if target < 0:
            raise ValueError("steps doit être positif ou nul")
        snapshots: dict[int, list[dict[str, int | float]]] = {}
        if target == 0:
            snapshots[0] = self.snapshot()
        for _ in range(target):
            self.step()
            if (
                self.current_step % self.config.snapshot_interval == 0
                or self.current_step == target
            ):
                snapshots[self.current_step] = self.snapshot()
        return SimulationRun(self.timeseries.copy(), snapshots, self.events.copy())
