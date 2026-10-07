from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import numpy as np

from .config import M2Config
from .contracts import ContractBook
from .entities import Entity


@dataclass(frozen=True, slots=True)
class CreditTerms:
    rate: float
    effective_cost: float
    target_capital: float
    demand: float
    supply: float
    volume: float


@dataclass(frozen=True, slots=True)
class MarketResult:
    rounds: int = 0
    contracts_created: int = 0
    volume: float = 0.0


def marginal_rate(alpha: float, w: float) -> float:
    if w <= 0:
        return math.inf
    return alpha / (2.0 * math.sqrt(w))


def compute_credit_terms(
    lender_w: float, borrower_w: float, alpha: float, delta: float
) -> CreditTerms | None:
    if lender_w <= 0 or borrower_w <= 0 or lender_w <= borrower_w:
        return None
    lender_rate = marginal_rate(alpha, lender_w)
    borrower_rate = marginal_rate(alpha, borrower_w)
    rate = math.sqrt(lender_rate * borrower_rate)
    effective_cost = rate + delta
    target = (alpha / (2.0 * effective_cost)) ** 2
    demand = max(0.0, target - borrower_w)
    supply = max(0.0, lender_w - target)
    volume = min(demand, supply)
    if not all(
        math.isfinite(x) for x in (rate, effective_cost, target, demand, supply, volume)
    ):
        return None
    return CreditTerms(rate, effective_cost, target, demand, supply, volume)


def run_credit_market(
    entities: dict[int, Entity],
    book: ContractBook,
    rng: np.random.Generator,
    config: M2Config,
    step: int,
    event_sink: Callable[[dict], None] | None = None,
) -> MarketResult:
    if not config.credit_enabled:
        return MarketResult()
    eligible = sorted(
        entity_id
        for entity_id, entity in entities.items()
        if entity.alive and not entity.defaulted
    )
    n = len(eligible)
    rounds = n // config.k
    eligible_array = np.asarray(eligible)
    created = 0
    total_volume = 0.0
    for _ in range(rounds):
        indices = rng.choice(n, size=config.k, replace=False)
        sample = [int(eligible_array[int(index)]) for index in indices]
        lender_id = min(sample, key=lambda i: (-entities[i].w, i))
        borrower_id = min(sample, key=lambda i: (entities[i].w, i))
        if lender_id == borrower_id:
            continue
        lender = entities[lender_id]
        borrower = entities[borrower_id]
        terms = compute_credit_terms(lender.w, borrower.w, config.alpha, config.delta)
        if terms is None or terms.volume <= 0:
            continue
        q = terms.volume
        before = lender.w + borrower.w
        lender.w -= q
        borrower.w += q
        if lender.w < 0 and lender.w > -1e-12:
            lender.w = 0.0
        if lender.w < 0:
            raise AssertionError("le marché a créé un capital négatif")
        contract = book.add(
            lender_id=lender_id,
            borrower_id=borrower_id,
            principal=q,
            rate=terms.rate,
            creation_step=step,
        )
        if not math.isclose(
            before, lender.w + borrower.w, rel_tol=1e-12, abs_tol=1e-12
        ):
            raise AssertionError("le principal n'a pas été transféré conservativement")
        created += 1
        total_volume += q
        if event_sink is not None:
            event_sink(
                {
                    "event": "loan_created",
                    "step": step,
                    "contract_id": contract.contract_id,
                    "lender_id": lender_id,
                    "borrower_id": borrower_id,
                    "principal": q,
                    "rate": terms.rate,
                    "target_capital": terms.target_capital,
                }
            )
    return MarketResult(rounds, created, total_volume)
