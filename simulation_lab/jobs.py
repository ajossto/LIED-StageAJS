from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from simulation_lab.models.discovery import ModelRegistry
from simulation_lab.progress import CancelledByUser, progress_reporting
from simulation_lab.runs.executor import execute_batch, _effective_parameters, _run_model, generate_seeds
from simulation_lab.runs.storage import RunStorage, _select_preview_artifact


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class JobState:
    job_id: str
    job_type: str
    status: str
    model_id: str
    created_at: str
    label: str = ""
    progress: float = 0.0
    message: str = ""
    run_id: str | None = None
    batch_id: str | None = None
    run_ids: list[str] = field(default_factory=list)
    logs: deque[str] = field(default_factory=lambda: deque(maxlen=200))
    error: str = ""
    finished_at: str | None = None
    cancel_requested: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status,
            "model_id": self.model_id,
            "created_at": self.created_at,
            "label": self.label,
            "progress": self.progress,
            "message": self.message,
            "run_id": self.run_id,
            "batch_id": self.batch_id,
            "run_ids": self.run_ids,
            "logs": list(self.logs),
            "error": self.error,
            "finished_at": self.finished_at,
            "cancel_requested": self.cancel_requested,
        }


class JobManager:
    def __init__(self, storage: RunStorage, registry: ModelRegistry) -> None:
        self.storage = storage
        self.registry = registry
        self._jobs: dict[str, JobState] = {}
        self._lock = threading.Lock()

    def list_jobs(self) -> list[dict[str, Any]]:
        with self._lock:
            jobs = [job.to_dict() for job in self._jobs.values()]
        jobs.sort(key=lambda item: item["created_at"], reverse=True)
        return jobs

    def get_job(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            return self._jobs[job_id].to_dict()

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs[job_id]
            job.cancel_requested = True
            if job.status in {"queued", "running"}:
                job.message = "Annulation demandée"
        return job.to_dict()

    def submit_single(self, *, model_id: str, parameters: dict[str, Any], seed: int, label: str = "") -> dict[str, Any]:
        job = JobState(
            job_id=self._new_job_id(),
            job_type="single",
            status="queued",
            model_id=model_id,
            created_at=_utc_now(),
            label=label,
            message="En attente",
        )
        with self._lock:
            self._jobs[job.job_id] = job
        thread = threading.Thread(
            target=self._run_single_job,
            args=(job.job_id, model_id, parameters, seed, label),
            daemon=True,
        )
        thread.start()
        return job.to_dict()

    def submit_batch(
        self,
        *,
        model_id: str,
        parameters: dict[str, Any],
        run_count: int,
        max_workers: int,
        base_seed: int | None,
        label: str = "",
    ) -> dict[str, Any]:
        job = JobState(
            job_id=self._new_job_id(),
            job_type="batch",
            status="queued",
            model_id=model_id,
            created_at=_utc_now(),
            label=label,
            message="En attente",
        )
        with self._lock:
            self._jobs[job.job_id] = job
        thread = threading.Thread(
            target=self._run_batch_job,
            args=(job.job_id, model_id, parameters, run_count, max_workers, base_seed, label),
            daemon=True,
        )
        thread.start()
        return job.to_dict()

    def _run_single_job(self, job_id: str, model_id: str, parameters: dict[str, Any], seed: int, label: str) -> None:
        self._update_job(job_id, status="running", message="Lancement de la simulation", progress=2.0)
        model = self.registry.get(model_id)
        validated = model.validate_parameters(parameters)
        effective_parameters = _effective_parameters(model, validated, seed)
        metadata = self.storage.create_run(model_id=model_id, parameters=effective_parameters, seed=seed, label=label)
        self.storage.mark_running(metadata["run_id"])
        self._update_job(job_id, run_id=metadata["run_id"], message="Simulation en cours", progress=5.0)

        def callback(payload: dict) -> None:
            if "log" in payload and payload["log"]:
                self._append_log(job_id, payload["log"])
            progress = payload.get("progress")
            message = payload.get("message")
            updates: dict[str, Any] = {}
            if progress is not None:
                updates["progress"] = progress
            if message:
                updates["message"] = message
            if updates:
                self._update_job(job_id, **updates)

        try:
            with progress_reporting(callback, cancel_callback=lambda: self._is_cancel_requested(job_id)):
                result = _run_model(
                    model_id=model_id,
                    parameters=effective_parameters,
                    seed=seed,
                    run_dir=str(self.storage.run_dir(metadata["run_id"])),
                    run_label=label,
                )
            finalized = self.storage.finalize_run(metadata["run_id"], result)
            finalized["origin"] = "managed"
            finalized["deletable"] = True
            finalized["keep_supported"] = True
            finalized["preview_artifact"] = (_select_preview_artifact(finalized["artifacts"]) or {}).get("relative_path")
            self.storage.write_metadata(self.storage.run_dir(metadata["run_id"]), finalized)
            self._update_job(
                job_id,
                status="completed",
                progress=100.0,
                message="Simulation terminée",
                finished_at=_utc_now(),
            )
        except CancelledByUser as exc:
            self.storage.mark_failed(metadata["run_id"], str(exc))
            self._append_log(job_id, str(exc))
            self._update_job(
                job_id,
                status="cancelled",
                error=str(exc),
                message="Simulation interrompue",
                finished_at=_utc_now(),
            )
        except Exception as exc:
            self.storage.mark_failed(metadata["run_id"], str(exc))
            self._append_log(job_id, str(exc))
            self._update_job(
                job_id,
                status="failed",
                error=str(exc),
                message="Échec de la simulation",
                finished_at=_utc_now(),
            )

    def _run_batch_job(
        self,
        job_id: str,
        model_id: str,
        parameters: dict[str, Any],
        run_count: int,
        max_workers: int,
        base_seed: int | None,
        label: str,
    ) -> None:
        self._update_job(job_id, status="running", message="Préparation du batch", progress=1.0)
        seeds = generate_seeds(run_count, base_seed=base_seed)
        try:
            payload = execute_batch(
                self.storage,
                self.registry,
                model_id=model_id,
                parameters=parameters,
                seeds=seeds,
                label=label,
                max_workers=max_workers,
                progress_callback=lambda update: self._update_job(
                    job_id,
                    progress=update.get("progress", 0.0),
                    message=update.get("message", "Batch en cours"),
                ),
                should_cancel=lambda: self._is_cancel_requested(job_id),
            )
            self._update_job(
                job_id,
                status="completed",
                progress=100.0,
                message="Batch terminé",
                batch_id=payload["batch_id"],
                run_ids=payload["run_ids"],
                finished_at=_utc_now(),
            )
        except CancelledByUser as exc:
            self._append_log(job_id, str(exc))
            self._update_job(
                job_id,
                status="cancelled",
                error=str(exc),
                message="Batch interrompu",
                finished_at=_utc_now(),
            )
        except Exception as exc:
            self._append_log(job_id, str(exc))
            self._update_job(
                job_id,
                status="failed",
                error=str(exc),
                message="Échec du batch",
                finished_at=_utc_now(),
            )

    def _new_job_id(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:8]

    def _append_log(self, job_id: str, message: str) -> None:
        clean = message.rstrip()
        if not clean:
            return
        with self._lock:
            self._jobs[job_id].logs.append(clean)

    def _update_job(self, job_id: str, **updates: Any) -> None:
        with self._lock:
            job = self._jobs[job_id]
            for key, value in updates.items():
                setattr(job, key, value)

    def _is_cancel_requested(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs[job_id]
            return job.cancel_requested
