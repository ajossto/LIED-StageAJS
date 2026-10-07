"""Importe les runs déjà calculés de la campagne M4.2B (results/campaign/)
dans simulation_lab, pour consultation via l'interface web locale
(python3 -m simulation_lab.cli gui --open-browser).

Ne relance AUCUNE simulation : symlinke les fichiers bruts déjà produits
(schéma M4.2B standard, déjà écrits par scripts/campaign.py) dans un
nouveau run managé simulation_lab, puis génère les 28 figures standard sur
ces fichiers (modeles-systeme-physicoeconomique/m4_2b_credit_soc/reporting.py
— lecture seule par nom de colonne, cf. sa docstring de provenance ;
n'importe pas le moteur, ne relance rien).

Idempotent : results/campaign/simlab_import_map.json retient le mapping
<label>/seed<N> -> run_id simulation_lab déjà importé ; relancer ce script
n'importe que les runs nouvellement complétés (status="ok").
"""

from __future__ import annotations

import json
import multiprocessing as mp
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
CAMPAIGN_ROOT = SCRIPTS_DIR.parent  # m4_2b_credit_soc/
ROOT = CAMPAIGN_ROOT.parents[1]  # jupyter/
CAMPAIGN_DIR = CAMPAIGN_ROOT / "results" / "campaign"
MAP_PATH = CAMPAIGN_DIR / "simlab_import_map.json"
ADAPTER_DIR = ROOT / "modeles" / "adaptateurs" / "m4_2b_credit_soc"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ADAPTER_DIR))

from simulation_lab.contracts import SimulationResult, collect_artifacts  # noqa: E402
from simulation_lab.runs.storage import RunStorage  # noqa: E402
import figures as m4_2b_figures  # noqa: E402  (adapter figures.py, cf. ADAPTER_DIR)

MODEL_ID = "m4_2b_credit_soc"


def _load_map() -> dict:
    if MAP_PATH.exists():
        return json.loads(MAP_PATH.read_text())
    return {}


def _save_map(mapping: dict) -> None:
    MAP_PATH.write_text(json.dumps(mapping, indent=1, ensure_ascii=False))


def import_run(run_dir_src: Path, label: str, storage: RunStorage) -> tuple[str, list[str]]:
    config = json.loads((run_dir_src / "config.json").read_text())
    summary = json.loads((run_dir_src / "summary.json").read_text())
    params = config["parameters"]
    seed = params["seed"]
    run_label = f"campagne_M4.2B_{label}_seed{seed}"

    metadata = storage.create_run(model_id=MODEL_ID, parameters=params, seed=seed, label=run_label)
    run_id = metadata["run_id"]
    run_dir = storage.run_dir(run_id)

    for item in run_dir_src.iterdir():
        (run_dir / item.name).symlink_to(item.resolve())

    figure_errors = m4_2b_figures.generate_figures(run_dir, run_label)
    artifacts = collect_artifacts(run_dir)
    message = f"Import campagne M4.2B (label={label}, seed={seed})"
    if figure_errors:
        message += f" -- {len(figure_errors)} figure(s) ignoree(s)"
    result = SimulationResult(
        status="completed",
        summary=summary,
        artifacts=artifacts,
        message=message,
        extra={
            "seed": seed, "campaign_label": label, "source_path": str(run_dir_src),
            **({"figure_errors": figure_errors} if figure_errors else {}),
        },
    )
    storage.finalize_run(run_id, result)
    return run_id, figure_errors


def _import_one(task: tuple[str, str]) -> tuple[str, str | None, str, list[str]]:
    """Wrapper picklable pour le Pool : une RunStorage par worker (chacun
    n'écrit que sous son propre run_id, pas de concurrence d'écriture)."""
    key, label = task
    run_dir_src = CAMPAIGN_DIR / key
    storage = RunStorage()
    try:
        run_id, figure_errors = import_run(run_dir_src, label, storage)
        return key, run_id, "ok", figure_errors
    except Exception as exc:  # noqa: BLE001
        return key, None, f"error: {exc}", []


def main(n_workers: int = 8) -> None:
    mapping = _load_map()
    tasks = []
    for analysis_path in sorted(CAMPAIGN_DIR.glob("*/seed*/analysis.json")):
        run_dir_src = analysis_path.parent
        key = str(run_dir_src.relative_to(CAMPAIGN_DIR))
        if key in mapping:
            continue
        try:
            d = json.loads(analysis_path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if d.get("status") != "ok":
            continue
        tasks.append((key, run_dir_src.parent.name))

    print(f"{len(tasks)} runs a importer ({len(mapping)} deja importes), {n_workers} workers")
    imported = 0
    with mp.Pool(processes=n_workers) as pool:
        for key, run_id, status, figure_errors in pool.imap_unordered(_import_one, tasks):
            if status != "ok":
                print(f"ECHEC : {key} -> {status}", flush=True)
                continue
            mapping[key] = run_id
            _save_map(mapping)
            imported += 1
            suffix = f" ({len(figure_errors)} figure(s) ignoree(s))" if figure_errors else ""
            print(f"[{imported}/{len(tasks)}] importe : {key} -> {run_id}{suffix}", flush=True)
    print(f"\n{imported} nouveaux runs importes dans simulation_lab ({len(mapping)} au total).")


if __name__ == "__main__":
    main()
