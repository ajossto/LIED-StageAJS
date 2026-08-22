"""Pilote sans tête : amorçage jusqu'à t₀, branchement d'un bras, rejeu.

Sous-commandes :

  burn    — simule de 0 à t₀ et écrit un snapshot réutilisable par plusieurs
            bras (§4, §7 : contrôle et traitements partagent leur amorçage).
  arm     — repart d'un snapshot, applique un plan d'interventions et
            poursuit N pas, puis écrit series.csv / interventions.jsonl.
  replay  — rejoue (paramètres, graine, journal) depuis t=0 et compare la
            trajectoire obtenue à une série de référence (§8).
  resume  — reprend un run M4.3 STOCKÉ dans simulation_lab_data jusqu'à t₀
            et rapporte obligatoirement l'écart mesuré (§4).

Exemples :
  python3 driver/headless.py burn --seed 0 --t0 4000 --out results/burn/seed0
  python3 driver/headless.py arm --snapshot results/burn/seed0/snapshot_t4000.pkl \\
        --plan plans/fraction_A.json --steps 2000 --out results/arms/seed0_fracA
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from m4_3live_v2.live import (  # noqa: E402
    divergence_report,
    load_snapshot,
    read_journal,
    read_series_csv,
    replay,
    save_snapshot,
    write_series,
)
from m4_3live_v2.model import Config, Intervention, Simulation  # noqa: E402


def build_config(**kwargs) -> Config:
    known = set(Config.__dataclass_fields__)
    unknown = sorted(set(kwargs) - known)
    if unknown:
        raise ValueError(f"paramètres inconnus : {unknown}")
    return Config(**kwargs)


def write_outputs(simulation: Simulation, directory: Path, extra: dict | None = None) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    write_series(simulation, directory)
    payload = {
        "model_version": "m4_3live_v2-1",
        "parameters": simulation.config.to_dict(),
        "t_final": simulation.t,
        "status": simulation.status,
        "n_interventions": len(simulation.intervention_log),
        "kernel": simulation.kernel.describe(),
        "book_errors": simulation.book.consistency_errors(simulation.population.alive),
    }
    if extra:
        payload.update(extra)
    (directory / "summary.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    if simulation.intervention_log:
        with open(directory / "interventions.jsonl", "w", encoding="utf-8") as handle:
            for entry in simulation.intervention_log:
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    # Tension K_aut/K_eq : colonnes + figure, à chaque run. L'import de
    # matplotlib est fait ici et pas en tête de module pour que la session
    # pilotable (qui n'écrit pas de figures) n'en paie pas le coût.
    try:
        from scripts.tension_figures import plot_tension

        plot_tension(directory, simulation.config.delta)
    except Exception as error:  # une figure manquante ne perd pas un run
        print(f"    [tension] figure non produite : {error}", flush=True)


def run_plan(
    simulation: Simulation,
    plan: list[dict],
    steps: int,
    progress_every: int = 0,
) -> Simulation:
    """Exécute `steps` pas en soumettant chaque intervention du plan au pas
    voulu, par le même `submit` que l'IHM."""
    planned: dict[int, list[Intervention]] = {}
    for entry in plan:
        planned.setdefault(int(entry["t"]), []).append(Intervention.from_dict(entry))
    target = simulation.t + steps
    started = time.time()
    while simulation.t < target and simulation.status == "ok":
        for intervention in planned.get(simulation.t + 1, ()):
            simulation.submit(intervention)
        simulation.step()
        if progress_every and simulation.t % progress_every == 0:
            elapsed = time.time() - started
            print(
                f"    t={simulation.t} pop={simulation.series[-1]['pop']} "
                f"prod={simulation.series[-1]['prod_tot']:.1f} ({elapsed:.0f}s)",
                flush=True,
            )
    return simulation


# --------------------------------------------------------------------------
def cmd_burn(args) -> int:
    config = build_config(
        seed=args.seed,
        T=args.t0,
        gamma=args.gamma,
        A=args.A,
        lam=args.lam,
        delta=args.delta,
        sigma=args.sigma,
        K0=args.K0,
        rate_rule=args.rate_rule,
        kernel_policy=args.kernel_policy,
    )
    directory = Path(args.out)
    simulation = Simulation(config)
    started = time.time()
    run_plan(simulation, [], args.t0, progress_every=args.progress)
    write_outputs(simulation, directory, {"wall_seconds": time.time() - started})
    path = save_snapshot(simulation, directory / f"snapshot_t{simulation.t}.pkl")
    print(json.dumps({"snapshot": str(path), "t": simulation.t, "status": simulation.status}))
    return 0


def cmd_arm(args) -> int:
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8")) if args.plan else []
    if isinstance(plan, dict):
        plan = plan.get("interventions", [])
    simulation = load_snapshot(args.snapshot)
    simulation.config = build_config(
        **{**simulation.config.to_dict(), "T": simulation.t + args.steps}
    )
    # Les séries de l'amorçage sont conservées : le bras s'y raccorde
    # exactement, et le contrôle apparié partage ces lignes à l'identique.
    started = time.time()
    run_plan(simulation, plan, args.steps, progress_every=args.progress)
    directory = Path(args.out)
    write_outputs(
        simulation,
        directory,
        {
            "wall_seconds": time.time() - started,
            "snapshot": str(args.snapshot),
            "plan": plan,
        },
    )
    print(
        json.dumps(
            {"out": str(directory), "t": simulation.t, "status": simulation.status,
             "n_interventions": len(simulation.intervention_log)}
        )
    )
    return 0


def cmd_replay(args) -> int:
    config_payload = json.loads(Path(args.config).read_text(encoding="utf-8"))
    parameters = config_payload.get("parameters", config_payload)
    config = build_config(**{**parameters, "T": args.steps or parameters.get("T", 0)})
    journal = read_journal(args.journal)
    simulation = replay(config, journal, steps=None)
    report = {"status": simulation.status, "t": simulation.t}
    if args.reference:
        report["divergence"] = divergence_report(
            simulation, read_series_csv(args.reference), simulation.t
        )
    if args.out:
        write_outputs(simulation, Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def cmd_resume(args) -> int:
    sys.path.insert(0, "/home/anatole/jupyter")
    from simulation_lab.runs.storage import RunStorage

    storage = RunStorage()
    metadata = storage.read_metadata(args.run_id)
    series_path = Path(storage.run_dir(args.run_id)) / "series.csv"
    from m4_3live_v2.live import resume_from_series

    simulation, report = resume_from_series(metadata["parameters"], series_path, args.t0)
    directory = Path(args.out)
    write_outputs(simulation, directory, {"origin_run": args.run_id, "divergence": report})
    save_snapshot(simulation, directory / f"snapshot_t{simulation.t}.pkl")
    print(json.dumps({"run_id": args.run_id, "t0": args.t0, "divergence": report}, indent=2))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Pilote sans tête M4.3Live")
    sub = parser.add_subparsers(dest="command", required=True)

    burn = sub.add_parser("burn", help="amorçage jusqu'à t0 puis snapshot")
    burn.add_argument("--seed", type=int, required=True)
    burn.add_argument("--t0", type=int, required=True)
    burn.add_argument("--out", required=True)
    burn.add_argument("--gamma", type=float, default=0.5)
    burn.add_argument("--A", type=float, default=1.0)
    burn.add_argument("--lam", type=float, default=30.0)
    burn.add_argument("--delta", type=float, default=0.01)
    burn.add_argument("--sigma", type=float, default=0.01)
    burn.add_argument("--K0", type=float, default=25.0)
    burn.add_argument("--rate-rule", dest="rate_rule", default="marginal")
    burn.add_argument("--kernel-policy", dest="kernel_policy", default="exact_lut")
    burn.add_argument("--progress", type=int, default=0)
    burn.set_defaults(func=cmd_burn)

    arm = sub.add_parser("arm", help="branche un bras sur un snapshot")
    arm.add_argument("--snapshot", required=True)
    arm.add_argument("--plan", default="")
    arm.add_argument("--steps", type=int, required=True)
    arm.add_argument("--out", required=True)
    arm.add_argument("--progress", type=int, default=0)
    arm.set_defaults(func=cmd_arm)

    rep = sub.add_parser("replay", help="rejoue un journal")
    rep.add_argument("--config", required=True)
    rep.add_argument("--journal", required=True)
    rep.add_argument("--steps", type=int, default=0)
    rep.add_argument("--reference", default="")
    rep.add_argument("--out", default="")
    rep.set_defaults(func=cmd_replay)

    res = sub.add_parser("resume", help="reprend un run M4.3 stocké jusqu'à t0")
    res.add_argument("--run-id", dest="run_id", required=True)
    res.add_argument("--t0", type=int, required=True)
    res.add_argument("--out", required=True)
    res.set_defaults(func=cmd_resume)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
