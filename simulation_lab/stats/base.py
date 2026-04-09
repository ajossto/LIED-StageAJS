from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class StatisticsContext:
    model_id: str
    run_ids: list[str]
    parameters: dict[str, Any]
    output_dir: Path


class StatisticsPlugin:
    plugin_id: str = "base"
    display_name: str = "Base statistics plugin"

    def supports(self, model_id: str) -> bool:
        return True

    def run(self, context: StatisticsContext) -> dict[str, Any]:
        raise NotImplementedError
