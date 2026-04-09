import csv
import json
import os
import sys
from pathlib import Path


def mean(values):
    return sum(values) / len(values) if values else None


def median(values):
    if not values:
        return None
    values = sorted(values)
    n = len(values)
    m = n // 2
    if n % 2:
        return values[m]
    return 0.5 * (values[m - 1] + values[m])


def read_comment_csv(path):
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(line for line in handle if not line.startswith("#")))


def compute_existing_run_metrics(root):
    stats = list(csv.DictReader((root / "stats_legeres.csv").open(encoding="utf-8")))
    cascades = read_comment_csv(root / "cascades_faillites.csv")
    entity_meta = read_comment_csv(root / "entity_meta.csv")

    watched_lifespans = [
        int(row["death_step"]) - int(row["creation_step"])
        for row in entity_meta
        if row["death_step"]
    ]
    cascade_volumes = [float(row["volume_actifs_detruits"]) for row in cascades]

    return {
        "mean_extraction_total_per_step": mean([float(r["extraction_total"]) for r in stats]),
        "mean_credit_transactions_per_step": mean([float(r["credit_transactions"]) for r in stats]),
        "mean_active_loans": mean([float(r["n_prets_actifs"]) for r in stats]),
        "mean_alive_entities": mean([float(r["n_entities_alive"]) for r in stats]),
        "mean_failures_per_step": mean([float(r["n_failures"]) for r in stats]),
        "watched_entities": len(entity_meta),
        "failed_watched_entities": len(watched_lifespans),
        "mean_lifespan_watched_failed": mean(watched_lifespans),
        "median_lifespan_watched_failed": median(watched_lifespans),
        "mean_cascade_destroyed_volume": mean(cascade_volumes),
        "median_cascade_destroyed_volume": median(cascade_volumes),
        "max_cascade_destroyed_volume": max(cascade_volumes) if cascade_volumes else None,
    }


def simulate_model(src_dir, steps):
    src_dir = str(src_dir)
    old_cwd = os.getcwd()
    old_path = list(sys.path)
    try:
        os.chdir(src_dir)
        sys.path.insert(0, src_dir)
        from config import SimulationConfig
        from simulation import Simulation

        cfg = SimulationConfig(duree_simulation=steps, seed=42)
        sim = Simulation(cfg)
        sim.run(n_steps=steps, verbose=False)

        lifespans = [
            entity.death_step - entity.creation_step
            for entity in sim.entities.values()
            if entity.death_step is not None
        ]
        return {
            "steps": sim.current_step,
            "entities_total": len(sim.entities),
            "alive_final": len(sim.active_entities()),
            "failures_total": sum(s["n_failures"] for s in sim.stats),
            "mean_extraction_total_per_step": mean([s["extraction_total"] for s in sim.stats]),
            "mean_entities_alive": mean([s["n_entities_alive"] for s in sim.stats]),
            "mean_active_loans": mean([s["n_prets_actifs"] for s in sim.stats]),
            "mean_credit_transactions": mean([s["credit_transactions"] for s in sim.stats]),
            "mean_lifespan_failed": mean(lifespans),
            "median_lifespan_failed": median(lifespans),
            "max_lifespan_failed": max(lifespans) if lifespans else None,
            "final_active_loans": sim.stats[-1]["n_prets_actifs"],
            "final_system_actif": sim.stats[-1]["actif_total_systeme"],
            "final_system_passif": sim.stats[-1]["passif_total_systeme"],
        }
    finally:
        os.chdir(old_cwd)
        sys.path[:] = old_path


def main():
    repo = Path("/home/anatole/jupyter")
    data = {
        "model_identification": {
            "first_documented_stable": "arborescence_modeles/stable/v2_modulaire_stable_A_documenter_DONE -> claude3-v2",
            "latest_committed_model": "HEAD:claude3-v3-27-mars",
            "current_wip": "Modèle_sans_banque_wip",
        },
        "v2_simulation_1000": simulate_model(repo / "claude3-v2" / "src", steps=1000),
        "wip_existing_run_1000": compute_existing_run_metrics(
            repo
            / "Modèle_sans_banque_wip"
            / "resultats"
            / "simu_20260403_103200_scenario_base_d6a1d52"
            / "csv"
        ),
    }
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
