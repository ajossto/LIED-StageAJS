from __future__ import annotations

from pathlib import Path

from simulation_lab.models.legacy import LegacyModuleModel


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL = LegacyModuleModel(
    model_id="modele_sans_banque_wip",
    display_name="modele_sans_banque_wip",
    description="Adaptateur historique vers anciens_modeles/Modèle_sans_banque/src.",
    source_dir=str(PROJECT_ROOT / "anciens_modeles" / "Modèle_sans_banque" / "src"),
)
