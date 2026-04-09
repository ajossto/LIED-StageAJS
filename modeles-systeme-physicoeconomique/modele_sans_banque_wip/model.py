from __future__ import annotations

from pathlib import Path

from simulation_lab.models.legacy import LegacyModuleModel


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL = LegacyModuleModel(
    model_id="modele_sans_banque_wip",
    display_name="modele_sans_banque_wip",
    description="Adaptateur prioritaire vers Modèle_sans_banque_wip/src avec ses graphiques et sorties historiques.",
    source_dir=str(PROJECT_ROOT / "Modèle_sans_banque_wip" / "src"),
)
