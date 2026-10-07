from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from simulation_lab.contracts import BaseSimulationModel, ParameterSpec, SimulationResult, collect_artifacts


class MarketToyModel(BaseSimulationModel):
    model_id = "market_toy"
    display_name = "Exemple marché"
    description = "Petit modèle agent simple avec prix, offre et demande."
    tags = ["example", "market"]

    def parameter_specs(self):
        return [
            ParameterSpec("steps", "int", 150, label="Nombre de pas", minimum=10),
            ParameterSpec("initial_price", "float", 50.0, label="Prix initial", minimum=1.0),
            ParameterSpec("supply_sensitivity", "float", 0.5, label="Sensibilité offre"),
            ParameterSpec("demand_sensitivity", "float", 0.8, label="Sensibilité demande"),
            ParameterSpec("shock_scale", "float", 2.0, label="Amplitude des chocs", minimum=0.0),
        ]

    def run(self, parameters, output_dir: Path, seed: int, run_label: str = ""):
        import random

        rng = random.Random(seed)
        steps = int(parameters["steps"])
        price = float(parameters["initial_price"])
        supply_sensitivity = float(parameters["supply_sensitivity"])
        demand_sensitivity = float(parameters["demand_sensitivity"])
        shock_scale = float(parameters["shock_scale"])

        rows = []
        for step in range(steps):
            demand = max(0.0, 100 - demand_sensitivity * price + rng.gauss(0, shock_scale))
            supply = max(0.0, 20 + supply_sensitivity * price + rng.gauss(0, shock_scale))
            imbalance = demand - supply
            price = max(1.0, price + 0.05 * imbalance)
            rows.append({"step": step, "price": price, "demand": demand, "supply": supply, "imbalance": imbalance})

        with (output_dir / "market.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot([row["step"] for row in rows], [row["price"] for row in rows], label="Prix", color="#294c60")
        ax.plot([row["step"] for row in rows], [row["demand"] for row in rows], label="Demande", color="#c16630", alpha=0.8)
        ax.plot([row["step"] for row in rows], [row["supply"] for row in rows], label="Offre", color="#5b8e7d", alpha=0.8)
        ax.legend()
        ax.grid(True, alpha=0.2)
        ax.set_title(run_label or "Dynamique marché")
        fig.tight_layout()
        fig.savefig(output_dir / "market_overview.png", dpi=150)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar([row["step"] for row in rows], [row["imbalance"] for row in rows], color="#d1495b")
        ax.set_title("Déséquilibre offre-demande")
        ax.set_xlabel("Pas")
        ax.set_ylabel("Imbalance")
        fig.tight_layout()
        fig.savefig(output_dir / "imbalance.png", dpi=150)
        plt.close(fig)

        return SimulationResult(
            status="completed",
            summary={
                "final_price": rows[-1]["price"],
                "avg_demand": sum(row["demand"] for row in rows) / len(rows),
                "avg_supply": sum(row["supply"] for row in rows) / len(rows),
            },
            artifacts=collect_artifacts(output_dir),
            message="Simulation de marché terminée",
        )


MODEL = MarketToyModel()
