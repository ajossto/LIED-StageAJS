"""Adaptateur Simulation Lab — exécution d'un run M4 avec artefacts complets.

Expose run_and_save(config, label, notes, root, verbose) au format attendu
par LegacyModuleModel : crée <root>/simu_<ts>_<label>_<seed>/, exécute la
simulation avec journalisation enrichie (richlog), écrit tous les artefacts
disque (series.csv, avalanches.csv, dist_series.csv, watch.csv,
death_registry.csv, births.csv, loss_edges.csv, snap/net .npz) puis un
meta.json dont le champ "summary" est repris par l'interface du lab.

Les lignes de progression imprimées ("Démarrage : N pas", "Pas i",
"Simulation terminée", "Graphiques générés") suivent les regex de
simulation_lab/models/legacy.py pour alimenter la barre de progression.
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

_SRC = str(Path(__file__).resolve().parent.parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from m4.metrics import (RunWriter, default_snapshot_times,
                        enable_rich_logging)  # noqa: E402
from m4.simulation import Simulation  # noqa: E402


def run_and_save(config, label="m4", notes="", root="resultats",
                 verbose=False):
    """Exécute un run complet et retourne (sim, chemin du dossier)."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", label).strip("_") or "m4"
    run_id = f"simu_{ts}_{slug}_s{config.seed}"

    sim = Simulation(config)
    enable_rich_logging(sim)
    writer = RunWriter(root, run_id, config)
    folder = writer.dir
    times = default_snapshot_times(config.T)

    if verbose:
        print(f"Démarrage : {config.T} pas", flush=True)

    def on_snapshot(t, snap, net):
        writer.on_snapshot(t, snap, net)
        if verbose:
            print(f"Pas {t} — pop={sim.pop.n_alive} "
                  f"prêts={len(sim.book)}", flush=True)

    sim.run(snapshot_times=times, on_snapshot=on_snapshot)
    writer.write_series(sim.series)
    writer.write_avalanches(sim.avalanche_log)
    writer.write_loss_edges(sim)
    writer.write_richlog(sim)
    summary = writer.write_summary(sim)
    if verbose:
        print("Simulation terminée", flush=True)

    avs = [a["size"] for a in sim.avalanche_log]
    meta = dict(
        label=label, notes=notes, date=datetime.now().isoformat(),
        config=config.to_dict(),
        summary=dict(
            status=summary["status"],
            steps_simulated=summary["t_final"],
            entities_created_total=summary["total_births"],
            entities_alive_final=summary["pop_final"],
            failures_total=summary["total_deaths"],
            loans_active_final=summary["n_loans_final"],
            avalanches_recorded=len(avs),
            avalanche_max_size=max(avs, default=0),
            wall_seconds=summary["wall_seconds"],
        ),
    )
    with open(folder / "meta.json", "w") as fh:
        json.dump(meta, fh, indent=2)
    return sim, str(folder)
