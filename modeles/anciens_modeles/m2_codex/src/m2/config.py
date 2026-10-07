from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

INTEREST_SERVICE_RULES = {"pro_rata", "sequential_contract_id"}
BANKRUPTCY_TRANSFER_RULES = {"pro_rata", "cancel"}


@dataclass(frozen=True, slots=True)
class M2Config:
    """Paramètres explicites du modèle et conventions structurelles nommées."""

    alpha: float = 1.0
    delta: float = 0.05
    k: int = 6
    sigma: float = 0.25
    birth_rate: float = 10.0
    w0: float = 30.0
    d0: float = 28.0
    steps: int = 2_000
    snapshot_interval: int = 50
    interest_service: str = "pro_rata"
    bankruptcy_transfer: str = "pro_rata"
    credit_enabled: bool = True
    shocks_enabled: bool = True
    check_invariants: bool = True
    log_events: bool = False

    def __post_init__(self) -> None:
        if not self.alpha > 0:
            raise ValueError("alpha doit être strictement positif")
        if not 0 <= self.delta < 1:
            raise ValueError("delta doit appartenir à [0, 1[")
        if self.k < 2:
            raise ValueError("k doit être un entier >= 2")
        if self.sigma < 0:
            raise ValueError("sigma doit être positif ou nul")
        if self.birth_rate < 0:
            raise ValueError("birth_rate doit être positif ou nul")
        if self.w0 < 0 or self.d0 < 0 or self.w0 < self.d0:
            raise ValueError("le bilan de naissance exige w0 >= d0 >= 0")
        if self.steps < 0:
            raise ValueError("steps doit être positif ou nul")
        if self.snapshot_interval <= 0:
            raise ValueError("snapshot_interval doit être strictement positif")
        if self.interest_service not in INTEREST_SERVICE_RULES:
            raise ValueError(f"règle de service inconnue: {self.interest_service}")
        if self.bankruptcy_transfer not in BANKRUPTCY_TRANSFER_RULES:
            raise ValueError(f"règle de transfert inconnue: {self.bankruptcy_transfer}")

    @property
    def epsilon0(self) -> float:
        return self.w0 - self.d0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
