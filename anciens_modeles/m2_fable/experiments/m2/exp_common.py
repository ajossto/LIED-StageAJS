"""Utilitaires communs aux expériences M2 : chemins, exécution d'un run."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent          # anciens_modeles/m2_fable/
RESULTS = HERE / "results"
sys.path.insert(0, str(ROOT / "src"))

from m2 import M2Config, Simulation           # noqa: E402
from m2.metrics import RunWriter, default_snapshot_times  # noqa: E402


def run_one(cfg, run_id, dense_from=None, dense_len=21, log_every=500):
    """Exécute un run complet et écrit tous ses artefacts.
    dense_from : si non None, ajoute des snapshots à CHAQUE pas sur
    [dense_from, dense_from + dense_len) — pour les incréments 1 pas
    (test mécanistique T ~ B0/A0)."""
    out_dir = RESULTS / run_id
    if (out_dir / "summary.json").exists():
        print(f"[skip] {run_id} déjà fait")
        return out_dir
    times = default_snapshot_times(cfg.T)
    if dense_from is not None:
        times = sorted(set(times) | set(range(dense_from, dense_from + dense_len)))
    writer = RunWriter(RESULTS, run_id, cfg)
    sim = Simulation(cfg)
    sim.run(snapshot_times=times, on_snapshot=writer.on_snapshot,
            log_every=log_every)
    writer.write_series(sim.series)
    summary = writer.write_summary(sim)
    assert summary["book_errors"] == [], f"invariants violés : {summary['book_errors']}"
    print(f"[done] {run_id}: status={summary['status']} pop={summary['pop_final']} "
          f"loans={summary['n_loans_final']} wall={summary['wall_seconds']}s")
    return out_dir
