from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

from .contracts import ContractBook
from .entities import Entity


@dataclass(slots=True)
class StepMetrics:
    step: int
    population: int
    births: int
    failures: int
    cascade_waves: str
    max_wave_size: int
    total_capital: float
    total_net_worth: float
    active_contracts: int
    total_credit: float
    credit_hhi: float
    market_rounds: int
    loans_created: int
    loan_volume: float
    interest_due: float
    interest_paid: float
    extraction: float
    shock_capital_change: float
    depreciation_loss: float
    canceled_debt: float
    transferred_claims: float
    destroyed_claims: float
    recovered_capital: float
    destroyed_capital: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def balance_maps(book: ContractBook) -> tuple[dict[int, float], dict[int, float]]:
    claims: dict[int, float] = {}
    debts: dict[int, float] = {}
    for contract in book.contracts.values():
        claims[contract.lender_id] = (
            claims.get(contract.lender_id, 0.0) + contract.principal
        )
        debts[contract.borrower_id] = (
            debts.get(contract.borrower_id, 0.0) + contract.principal
        )
    return claims, debts


def credit_concentration(entities: dict[int, Entity], book: ContractBook) -> float:
    claims, _ = balance_maps(book)
    total = math.fsum(claims.values())
    if total <= 0:
        return 0.0
    return math.fsum((amount / total) ** 2 for amount in claims.values())


def snapshot_rows(
    step: int, entities: dict[int, Entity], book: ContractBook
) -> list[dict[str, int | float]]:
    claims, debts = balance_maps(book)
    rows: list[dict[str, int | float]] = []
    for entity_id in sorted(entities):
        entity = entities[entity_id]
        if not entity.alive:
            continue
        claim = claims.get(entity_id, 0.0)
        debt = debts.get(entity_id, 0.0)
        nw = entity.w + claim - debt - entity.d0
        rows.append(
            {
                "step": step,
                "entity_id": entity_id,
                "birth_step": entity.birth_step,
                "age": step - entity.birth_step,
                "w": entity.w,
                "claims": claim,
                "debts": debt,
                "d0": entity.d0,
                "nw": nw,
                "nw_delta": (
                    entity.nw_delta if entity.nw_delta is not None else math.nan
                ),
                "extraction": entity.extraction,
                "interest_received": entity.interest_received,
                "interest_paid": entity.interest_paid,
                "income_gross": entity.extraction + entity.interest_received,
                "income_net": entity.extraction
                + entity.interest_received
                - entity.interest_paid,
            }
        )
    return rows
