"""Lanceur d'un run pilote UNIQUE, câblant les six garde-fous §7
(PROMPT_M4_3_FINAL.md). Pas de pool multiprocessing ici — un seul run, un
seul process, pas de parallélisme à coordonner pour la phase pilote.

Ordre au démarrage (chaque étape peut faire échouer bruyamment le
lancement, jamais silencieusement) :
  1. préflight disque (§7.4) ;
  2. verrou mono-pool (§7.3) — même pour un seul run, protège contre un
     second run/pool lancé par erreur en parallèle ;
  3. enregistrement du PID auprès du garde-fou mémoire indépendant (§7.1,
     `mem_guard.py` doit déjà tourner dans sa propre session tmux — ce
     script ne le lance PAS lui-même, il suppose qu'il tourne déjà, comme
     `mem_watch.py`/`campaign.py` en M4.2B) ;
  4. plafond RLIMIT_AS calculé sur MemAvailable réel (§7.2).

Pendant le run : `on_progress` (appelé à CHAQUE pas par `run_and_save`)
vérifie la sentinelle HALT à chaque pas (lecture de fichier, coût
négligible) et sauvegarde un checkpoint atomique tous les
`CHECKPOINT_EVERY` pas (§3, §7.4 — pas à chaque pas, l'écriture disque
serait dominante). Un HALT détecté arrête proprement le run (le
`RunRecorder` est fermé par `run_and_save`, les fichiers déjà écrits restent
valides) plutôt que d'attendre un SIGKILL du garde-fou mémoire.
"""

from __future__ import annotations

import argparse
import os
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from m4_3 import Config  # noqa: E402
from m4_3.io import run_and_save  # noqa: E402
from safety.disk_preflight import require_disk_preflight  # noqa: E402
from safety.mem_cap import worker_memory_cap  # noqa: E402
from safety.pool_lock import PoolLock  # noqa: E402
from safety.checkpoint import save_checkpoint  # noqa: E402
from safety.halt import is_halted, halt_reason  # noqa: E402
from safety.worker_registry import register_workers, clear_workers  # noqa: E402

RESULTS = ROOT / "results"
CHECKPOINT_EVERY = 200
# Mesuré directement (pas hérité de M4.2B) : premier run pilote M4.3
# (control_geometric seed0, T=3000, individual_series INCLUS) = 941 Mo, dont
# ~450 Mo d'individual_series.csv.gz (~491 Mo hors ce fichier). Avec
# individual_every=0 (défaut pilote) et une durée T=8000 (relaxation
# int_in mesurée, voir JOURNAL.md §9), majoré à 2,5 Go/run pour couvrir
# la mise à l'échelle avec T sans la supposer strictement linéaire.
PER_RUN_BYTES_ESTIMATE = int(2.5e9)


class HaltRequested(Exception):
    pass


def _make_progress_callback(checkpoint_path: Path, sim_holder: dict):
    def _on_progress(sim) -> None:
        sim_holder["sim"] = sim
        if is_halted():
            raise HaltRequested(halt_reason() or "HALT sans raison enregistrée")
        if sim.t % CHECKPOINT_EVERY == 0:
            save_checkpoint(sim, checkpoint_path)

    return _on_progress


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="control_geometric")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--steps", type=int, required=True)
    parser.add_argument("--target-rule", default="geometric", choices=["geometric", "arithmetic"])
    parser.add_argument("--lam", type=float, default=30.0)
    parser.add_argument("--sigma", type=float, default=0.01)
    parser.add_argument("--delta", type=float, default=0.01)
    parser.add_argument("--gamma", type=float, default=0.5)
    parser.add_argument("--k0", type=float, default=25.0)
    parser.add_argument(
        "--individual-every", type=int, default=0,
        help="0 par défaut (runs pilote/exploration) : individual_series.csv.gz "
             "n'est nécessaire qu'aux 28 figures Simulation Lab (report/), "
             "générées seulement pour confirmation/cellules centrales (convention "
             "M4.2B, m4_2_credit_soc/scripts/lib_lab.py) — l'inclure pour un run "
             "candidat à ce statut économise ~50%% du poids disque par run pilote.",
    )
    args = parser.parse_args()

    run_dir = RESULTS / "pilot" / args.label / f"seed{args.seed}"
    run_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = run_dir / "checkpoint.pkl"

    require_disk_preflight(remaining_runs=1, per_run_bytes=PER_RUN_BYTES_ESTIMATE)

    with PoolLock():
        register_workers([os.getpid()], pool_pid=os.getpid())
        try:
            cap = worker_memory_cap(n_workers=1)
            resource.setrlimit(resource.RLIMIT_AS, (cap.cap_per_worker_bytes,) * 2)
            print(cap.message(), flush=True)

            cfg = Config(
                seed=args.seed, T=args.steps, sigma=args.sigma, delta=args.delta,
                gamma=args.gamma, A=1.0, K0=args.k0, lam=args.lam,
                rho=1.0, eta_beta=1.0, eta_n_ref=1.0, target_rule=args.target_rule,
            )
            print(f"run pilote : label={args.label} seed={args.seed} T={args.steps} "
                  f"target_rule={args.target_rule} -> {run_dir}", flush=True)

            sim_holder: dict = {}
            callback = _make_progress_callback(checkpoint_path, sim_holder)
            started = time.perf_counter()
            try:
                simulation, summary = run_and_save(
                    cfg, run_dir, snapshot_every=max(25, args.steps // 120),
                    individual_every=args.individual_every,
                    on_progress=callback,
                )
                elapsed = time.perf_counter() - started
                save_checkpoint(simulation, checkpoint_path)
                print(f"run terminé : t={simulation.t}/{cfg.T}, elapsed={elapsed:.1f}s, "
                      f"status={summary['status']}", flush=True)
            except HaltRequested as exc:
                elapsed = time.perf_counter() - started
                sim = sim_holder.get("sim")
                if sim is not None:
                    save_checkpoint(sim, checkpoint_path)
                print(f"ARRÊTÉ PAR LE GARDE-FOU MÉMOIRE à t={sim.t if sim else '?'} "
                      f"après {elapsed:.1f}s : {exc}", flush=True)
                print(f"checkpoint sauvegardé : {checkpoint_path} — reprise possible plus tard.",
                      flush=True)
        finally:
            clear_workers()


if __name__ == "__main__":
    main()
