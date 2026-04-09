from __future__ import annotations

from pathlib import Path

from simulation_lab.models.legacy import LegacyModuleModel


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL = LegacyModuleModel(
    model_id="claude3_v2",
    display_name="claude3_v2",
    description="Adaptateur prioritaire vers claude3-v2/src avec récupération des figures existantes.",
    source_dir=str(PROJECT_ROOT / "claude3-v2" / "src"),
)
