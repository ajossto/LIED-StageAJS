"""Utilitaires communs aux expériences M4 : chemins, exécution d'un run.
Fork de anciens_modeles/m3_credit_soc/experiments/m3/exp_common.py (budget de calcul retiré,
non pertinent pour ce premier run)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent          # m4_credit_soc/
RESULTS = HERE / "results"
sys.path.insert(0, str(ROOT / "src"))

from m4 import M4Config, Simulation           # noqa: E402
from m4.metrics import RunWriter, default_snapshot_times  # noqa: E402


def run_one(cfg, run_id, dense_from=None, dense_len=21, log_every=500,
            snapshot_every=50):
    """Exécute un run complet et écrit tous ses artefacts.
    dense_from : snapshots à chaque pas sur [dense_from, dense_from+dense_len)
    pour les incréments à 1 pas (moments A0/B0)."""
    out_dir = RESULTS / run_id
    if (out_dir / "summary.json").exists():
        print(f"[skip] {run_id} déjà fait")
        return out_dir
    times = default_snapshot_times(cfg.T, every=snapshot_every)
    if dense_from is not None:
        times = sorted(set(times) | set(range(dense_from, dense_from + dense_len)))
    writer = RunWriter(RESULTS, run_id, cfg)
    sim = Simulation(cfg)
    sim.run(snapshot_times=times, on_snapshot=writer.on_snapshot,
            log_every=log_every)
    writer.write_series(sim.series)
    writer.write_avalanches(sim.avalanche_log)
    summary = writer.write_summary(sim)
    assert summary["book_errors"] == [], f"invariants violés : {summary['book_errors']}"
    print(f"[done] {run_id}: status={summary['status']} pop={summary['pop_final']} "
          f"loans={summary['n_loans_final']} wall={summary['wall_seconds']}s")
    return out_dir
