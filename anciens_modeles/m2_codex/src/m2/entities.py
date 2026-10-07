from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Entity:
    entity_id: int
    w: float
    d0: float
    birth_step: int
    alive: bool = True
    defaulted: bool = False
    extraction: float = 0.0
    interest_received: float = 0.0
    interest_paid: float = 0.0
    nw_delta: float | None = None

    def reset_step_flows(self) -> None:
        self.defaulted = False
        self.extraction = 0.0
        self.interest_received = 0.0
        self.interest_paid = 0.0
        self.nw_delta = None
