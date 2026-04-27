from __future__ import annotations

from pathlib import Path

from simulation_lab.models.legacy import LegacyModuleModel


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL = LegacyModuleModel(
    model_id="modele_27_04_wip",
    display_name="Modèle 27-04 WIP",
    description=(
        "Adaptateur Simulation Lab vers modele-27-04-WIP/src. "
        "Version optimisée de travail conservant les paramètres par défaut du WIP."
    ),
    source_dir=str(PROJECT_ROOT / "modele-27-04-WIP" / "src"),
)
