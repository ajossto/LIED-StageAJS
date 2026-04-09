from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from simulation_lab.contracts import Artifact, BaseSimulationModel, ParameterSpec, SimulationResult, collect_artifacts


class LinearGrowthModel(BaseSimulationModel):
    model_id = "linear_growth"
    display_name = "Exemple linéaire"
    description = "Petit modèle de croissance bruitée pour valider le pipeline complet."
    tags = ["example", "reference"]

    def parameter_specs(self):
        return [
            ParameterSpec("steps", "int", 120, label="Nombre de pas", minimum=10),
            ParameterSpec("initial_value", "float", 10.0, label="Valeur initiale"),
            ParameterSpec("growth_rate", "float", 0.8, label="Croissance moyenne"),
            ParameterSpec("noise_scale", "float", 1.0, label="Amplitude du bruit", minimum=0.0),
        ]

    def run(self, parameters, output_dir: Path, seed: int, run_label: str = ""):
        import random

        rng = random.Random(seed)
        steps = int(parameters["steps"])
        value = float(parameters["initial_value"])
        growth = float(parameters["growth_rate"])
        noise = float(parameters["noise_scale"])

        csv_path = output_dir / "series.csv"
        values = []
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["step", "value"])
            writer.writeheader()
            for step in range(steps):
                value += growth + rng.gauss(0.0, noise)
                value = max(value, 0.0)
                values.append(value)
                writer.writerow({"step": step, "value": value})

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(values, color="#294c60", linewidth=2)
        ax.set_title(run_label or "Croissance simulée")
        ax.set_xlabel("Pas")
        ax.set_ylabel("Valeur")
        ax.grid(True, alpha=0.25)
        fig.tight_layout()
        fig.savefig(output_dir / "trajectory.png", dpi=150)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(5, 4))
        ax.hist(values, bins=min(20, max(5, int(math.sqrt(len(values))))), color="#c16630", alpha=0.85)
        ax.set_title("Distribution")
        ax.set_xlabel("Valeur")
        ax.set_ylabel("Fréquence")
        fig.tight_layout()
        fig.savefig(output_dir / "distribution.png", dpi=150)
        plt.close(fig)

        return SimulationResult(
            status="completed",
            summary={"final_value": values[-1], "mean_value": sum(values) / len(values), "steps": steps},
            artifacts=collect_artifacts(output_dir),
            message="Simulation linéaire terminée",
            extra={"seed": seed},
        )


MODEL = LinearGrowthModel()
