from __future__ import annotations

from pathlib import Path
from typing import Any

from simulation_lab.contracts import ParameterSpec, SimulationResult
from simulation_lab.models.legacy import LegacyModuleModel


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class MinimalCandidateModel(LegacyModuleModel):
    """Variante candidate issue du rapport d'élagage: alpha hétérogène mais statique."""

    def parameter_specs(self) -> list[ParameterSpec]:
        specs = super().parameter_specs()
        for spec in specs:
            if spec.name == "alpha_sigma_brownien":
                spec.default = 0.0
                spec.label = "alpha sigma brownien (désactivé)"
                spec.description = (
                    "Défaut de la variante minimale candidate: pas de Brownien temporel "
                    "sur alpha, tout en conservant l'hétérogénéité initiale."
                )
        return specs

    def run(
        self,
        parameters: dict[str, Any],
        output_dir: Path,
        seed: int,
        run_label: str = "",
    ) -> SimulationResult:
        params = dict(parameters)
        params.setdefault("alpha_sigma_brownien", 0.0)
        return super().run(params, output_dir, seed, run_label=run_label)


MODEL = MinimalCandidateModel(
    model_id="modele_27_04_minimal_candidate",
    display_name="Modèle 27-04 candidat minimal",
    description=(
        "Variante exploratoire du WIP 27-04 recommandée par le rapport d'élagage: "
        "même moteur, alpha individuel fixe par défaut, k=3, crédit perpétuel, "
        "auto-investissement et dépréciation exogène conservés."
    ),
    source_dir=str(PROJECT_ROOT / "modele-27-04-WIP" / "src"),
)
MODEL.tags = ["legacy", "elagage", "candidate"]
