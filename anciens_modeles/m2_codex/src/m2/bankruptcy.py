from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

from .config import M2Config
from .contracts import ContractBook, LoanContract
from .entities import Entity


@dataclass(frozen=True, slots=True)
class LiquidationResult:
    entity_id: int
    canceled_debt: float
    transferred_claims: float
    destroyed_claims: float
    recovered_capital: float
    destroyed_capital: float


@dataclass(frozen=True, slots=True)
class CascadeResult:
    failures: int = 0
    wave_sizes: tuple[int, ...] = ()
    canceled_debt: float = 0.0
    transferred_claims: float = 0.0
    destroyed_claims: float = 0.0
    recovered_capital: float = 0.0
    destroyed_capital: float = 0.0


def net_worth(entity: Entity, book: ContractBook) -> float:
    return (
        entity.w
        + book.claims(entity.entity_id)
        - book.debts(entity.entity_id)
        - entity.d0
    )


def _positive_split(total: float, weights: dict[int, float]) -> list[tuple[int, float]]:
    """Partage déterministe ; la dernière part absorbe l'arrondi flottant."""
    if total <= 0 or not weights:
        return []
    ordered = [(key, value) for key, value in sorted(weights.items()) if value > 0]
    denominator = math.fsum(value for _, value in ordered)
    if denominator <= 0:
        return []
    result: list[tuple[int, float]] = []
    allocated = 0.0
    for position, (key, weight) in enumerate(ordered):
        if position == len(ordered) - 1:
            share = total - allocated
        else:
            share = total * weight / denominator
            allocated += share
        if share > 0:
            result.append((key, share))
    return result


def liquidate_entity(
    entity_id: int,
    entities: dict[int, Entity],
    book: ContractBook,
    config: M2Config,
    step: int,
    event_sink: Callable[[dict], None] | None = None,
) -> LiquidationResult:
    failed = entities[entity_id]
    if not failed.alive:
        return LiquidationResult(entity_id, 0.0, 0.0, 0.0, 0.0, 0.0)

    borrowed = book.borrowed_contracts(entity_id)
    creditor_amounts: dict[int, float] = defaultdict(float)
    for contract in borrowed:
        lender = entities[contract.lender_id]
        if lender.alive:
            creditor_amounts[contract.lender_id] += contract.principal
    canceled_debt = math.fsum(contract.principal for contract in borrowed)

    transferred_claims = 0.0
    destroyed_claims = 0.0
    lent = book.lent_contracts(entity_id)
    for contract in lent:
        book.remove(contract.contract_id)
        eligible = {
            creditor_id: amount
            for creditor_id, amount in creditor_amounts.items()
            if creditor_id != contract.borrower_id and entities[creditor_id].alive
        }
        if config.bankruptcy_transfer == "pro_rata" and eligible:
            for creditor_id, share in _positive_split(contract.principal, eligible):
                book.add(
                    lender_id=creditor_id,
                    borrower_id=contract.borrower_id,
                    principal=share,
                    rate=contract.rate,
                    creation_step=step,
                    parent_id=contract.contract_id,
                )
                transferred_claims += share
        else:
            destroyed_claims += contract.principal

    alive_creditors = {
        creditor_id: amount
        for creditor_id, amount in creditor_amounts.items()
        if entities[creditor_id].alive
    }
    residual = max(0.0, failed.w)
    recovered_capital = 0.0
    for creditor_id, share in _positive_split(residual, alive_creditors):
        entities[creditor_id].w += share
        recovered_capital += share
    destroyed_capital = max(0.0, residual - recovered_capital)

    for contract in list(book.borrowed_contracts(entity_id)):
        book.remove(contract.contract_id)

    nw_before_removal = net_worth(failed, book) if failed.alive else math.nan
    failed.w = 0.0
    failed.d0 = 0.0
    failed.alive = False
    failed.defaulted = False

    result = LiquidationResult(
        entity_id=entity_id,
        canceled_debt=canceled_debt,
        transferred_claims=transferred_claims,
        destroyed_claims=destroyed_claims,
        recovered_capital=recovered_capital,
        destroyed_capital=destroyed_capital,
    )
    if event_sink is not None:
        event_sink(
            {
                "event": "bankruptcy",
                "step": step,
                "entity_id": entity_id,
                "nw_after_contract_disposal": nw_before_removal,
                "canceled_debt": canceled_debt,
                "transferred_claims": transferred_claims,
                "destroyed_claims": destroyed_claims,
                "recovered_capital": recovered_capital,
                "destroyed_capital": destroyed_capital,
            }
        )
    return result


def resolve_cascades(
    entities: dict[int, Entity],
    book: ContractBook,
    config: M2Config,
    step: int,
    event_sink: Callable[[dict], None] | None = None,
) -> CascadeResult:
    results: list[LiquidationResult] = []
    wave_sizes: list[int] = []
    while True:
        failing = sorted(
            entity_id
            for entity_id, entity in entities.items()
            if entity.alive and (entity.defaulted or net_worth(entity, book) < 0)
        )
        if not failing:
            break
        processed = 0
        for entity_id in failing:
            entity = entities[entity_id]
            if not entity.alive:
                continue
            # Une récupération reçue plus tôt dans la vague peut sauver une
            # insolvabilité non défaillante. Un défaut de paiement reste fatal.
            if not entity.defaulted and net_worth(entity, book) >= 0:
                continue
            results.append(
                liquidate_entity(
                    entity_id, entities, book, config, step, event_sink=event_sink
                )
            )
            processed += 1
        if processed == 0:
            raise RuntimeError("cascade bloquée sans liquidation possible")
        wave_sizes.append(processed)

    return CascadeResult(
        failures=len(results),
        wave_sizes=tuple(wave_sizes),
        canceled_debt=math.fsum(item.canceled_debt for item in results),
        transferred_claims=math.fsum(item.transferred_claims for item in results),
        destroyed_claims=math.fsum(item.destroyed_claims for item in results),
        recovered_capital=math.fsum(item.recovered_capital for item in results),
        destroyed_capital=math.fsum(item.destroyed_capital for item in results),
    )
