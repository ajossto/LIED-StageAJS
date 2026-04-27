from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

from simulation_lab.contracts import SimulationResult
from simulation_lab.models.discovery import ModelRegistry
from simulation_lab.progress import CancelledByUser
from simulation_lab.runs.storage import RunStorage, _select_preview_artifact
from simulation_lab.settings import recommended_workers


def generate_seeds(run_count: int, base_seed: int | None = None) -> list[int]:
    origin = 1000 if base_seed is None else int(base_seed)
    return [origin + index for index in range(run_count)]


def execute_single(storage: RunStorage, registry: ModelRegistry, *, model_id: str, parameters: dict[str, Any], seed: int, label: str = "") -> dict[str, Any]:
    model = registry.get(model_id)
    validated = model.validate_parameters(parameters)
    effective_parameters = _effective_parameters(model, validated, seed)
    metadata = storage.create_run(model_id=model_id, parameters=effective_parameters, seed=seed, label=label)
    try:
        storage.mark_running(metadata["run_id"])
        result = _run_model(model_id=model_id, parameters=effective_parameters, seed=seed, run_dir=str(storage.run_dir(metadata["run_id"])), run_label=label)
        finalized = storage.finalize_run(metadata["run_id"], result)
        finalized["origin"] = "managed"
        finalized["deletable"] = True
        finalized["keep_supported"] = True
        finalized["preview_artifact"] = (_select_preview_artifact(finalized["artifacts"]) or {}).get("relative_path")
        storage.write_metadata(storage.run_dir(metadata["run_id"]), finalized)
        return finalized
    except Exception as exc:
        return storage.mark_failed(metadata["run_id"], str(exc))


def execute_batch(
    storage: RunStorage,
    registry: ModelRegistry,
    *,
    model_id: str,
    parameters: dict[str, Any],
    seeds: list[int],
    label: str = "",
    max_workers: int = 1,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    model = registry.get(model_id)
    validated = model.validate_parameters(parameters)
    effective_parameters = _effective_parameters(model, validated, None)
    batch = storage.create_batch(model_id=model_id, parameters=effective_parameters, seeds=seeds, label=label)
    run_ids: list[str] = []
    futures = {}
    if max_workers <= 0:
        max_workers = recommended_workers()
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        for seed in seeds:
            if should_cancel is not None and should_cancel():
                raise CancelledByUser("Batch interrompu par l'utilisateur.")
            run_parameters = _effective_parameters(model, validated, seed)
            metadata = storage.create_run(model_id=model_id, parameters=run_parameters, seed=seed, label=label, batch_id=batch["batch_id"])
            storage.attach_run_to_batch(batch["batch_id"], metadata["run_id"])
            storage.mark_running(metadata["run_id"])
            run_ids.append(metadata["run_id"])
            futures[executor.submit(_run_model, model_id=model_id, parameters=run_parameters, seed=seed, run_dir=str(storage.run_dir(metadata["run_id"])), run_label=label)] = metadata["run_id"]
        for future in as_completed(futures):
            if should_cancel is not None and should_cancel():
                executor.shutdown(wait=False, cancel_futures=True)
                raise CancelledByUser("Batch interrompu par l'utilisateur.")
            run_id = futures[future]
            try:
                result = future.result()
                storage.finalize_run(run_id, result)
            except Exception as exc:
                storage.mark_failed(run_id, str(exc))
            if progress_callback is not None:
                completed = sum(1 for candidate in run_ids if storage.read_metadata(candidate).get("status") in {"completed", "failed"})
                progress_callback({
                    "completed_runs": completed,
                    "total_runs": len(run_ids),
                    "progress": (completed / len(run_ids)) * 100.0 if run_ids else 100.0,
                    "message": f"Batch {completed}/{len(run_ids)} terminé",
                })
    batch["run_ids"] = run_ids
    storage.write_batch(batch)
    return batch


def _run_model(*, model_id: str, parameters: dict[str, Any], seed: int, run_dir: str, run_label: str = "") -> SimulationResult:
    registry = ModelRegistry()
    model = registry.get(model_id)
    output_dir = Path(run_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    return model.run(parameters=parameters, output_dir=output_dir, seed=seed, run_label=run_label)


def _effective_parameters(model, validated: dict[str, Any], seed: int | None) -> dict[str, Any]:
    effective = dict(validated)
    if seed is None:
        return effective
    if any(spec.name == "seed" for spec in model.parameter_specs()):
        effective["seed"] = seed
    return effective
