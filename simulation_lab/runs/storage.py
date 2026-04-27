from __future__ import annotations

import json
import os
import subprocess
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from simulation_lab.contracts import Artifact, SimulationResult
from simulation_lab.contracts import collect_artifacts
from simulation_lab.settings import BASKET_DIR, BATCHES_DIR, CATALOG_FILE, LEGACY_RESULT_SOURCES, ROOT_DIR, RUNS_DIR, ensure_directories


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunStorage:
    def __init__(self) -> None:
        ensure_directories()
        self._catalog = self._load_catalog()

    def create_run(
        self,
        *,
        model_id: str,
        parameters: dict[str, Any],
        seed: int,
        label: str = "",
        batch_id: str | None = None,
    ) -> dict[str, Any]:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:8]
        run_dir = RUNS_DIR / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        metadata = {
            "run_id": run_id,
            "model_id": model_id,
            "parameters": parameters,
            "seed": seed,
            "label": label,
            "batch_id": batch_id,
            "status": "pending",
            "keep": False,
            "important": False,
            "trashed": False,
            "trashed_at": None,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "summary": {},
            "artifacts": [],
            "message": "",
        }
        self.write_metadata(run_dir, metadata)
        return metadata

    def create_batch(self, *, model_id: str, parameters: dict[str, Any], seeds: list[int], label: str = "") -> dict[str, Any]:
        batch_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:8]
        payload = {
            "batch_id": batch_id,
            "model_id": model_id,
            "parameters": parameters,
            "seeds": seeds,
            "label": label,
            "created_at": utc_now(),
            "run_ids": [],
        }
        self.write_batch(payload)
        return payload

    def attach_run_to_batch(self, batch_id: str, run_id: str) -> None:
        payload = self.read_batch(batch_id)
        payload["run_ids"].append(run_id)
        self.write_batch(payload)

    def finalize_run(self, run_id: str, result: SimulationResult) -> dict[str, Any]:
        metadata = self.read_metadata(run_id)
        metadata["status"] = result.status
        metadata["summary"] = result.summary
        metadata["artifacts"] = [artifact.to_dict() for artifact in result.artifacts]
        metadata["message"] = result.message
        metadata["extra"] = result.extra
        metadata["updated_at"] = utc_now()
        self.write_metadata(self.run_dir(run_id), metadata)
        return metadata

    def mark_running(self, run_id: str) -> None:
        metadata = self.read_metadata(run_id)
        metadata["status"] = "running"
        metadata["updated_at"] = utc_now()
        self.write_metadata(self.run_dir(run_id), metadata)

    def mark_failed(self, run_id: str, message: str) -> dict[str, Any]:
        metadata = self.read_metadata(run_id)
        metadata["status"] = "failed"
        metadata["message"] = message
        metadata["updated_at"] = utc_now()
        self.write_metadata(self.run_dir(run_id), metadata)
        return metadata

    def list_runs(self) -> list[dict[str, Any]]:
        ensure_directories()
        runs: list[dict[str, Any]] = []
        for meta_file in sorted(RUNS_DIR.glob("*/run.json"), reverse=True):
            try:
                payload = json.loads(meta_file.read_text(encoding="utf-8"))
                payload.setdefault("origin", "managed")
                payload.setdefault("deletable", True)
                payload.setdefault("keep_supported", True)
                payload.setdefault("preview_artifact", (_select_preview_artifact(payload.get("artifacts", [])) or {}).get("relative_path"))
                payload = self._apply_catalog(payload)
                runs.append(payload)
            except Exception:
                continue
        runs.extend(self.list_external_runs())
        runs.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return runs

    def list_trash(self) -> list[dict[str, Any]]:
        ensure_directories()
        runs: list[dict[str, Any]] = []
        for meta_file in sorted(BASKET_DIR.glob("*/run.json"), reverse=True):
            try:
                payload = json.loads(meta_file.read_text(encoding="utf-8"))
                payload.setdefault("origin", "managed")
                payload.setdefault("deletable", True)
                payload.setdefault("keep_supported", True)
                payload.setdefault("preview_artifact", (_select_preview_artifact(payload.get("artifacts", [])) or {}).get("relative_path"))
                payload.setdefault("trashed", True)
                payload = self._apply_catalog(payload)
                runs.append(payload)
            except Exception:
                continue
        runs.sort(key=lambda item: item.get("trashed_at") or item.get("updated_at", ""), reverse=True)
        return runs

    def read_metadata(self, run_id: str) -> dict[str, Any]:
        if run_id.startswith("external__"):
            return self._build_external_run(self._external_path_from_run_id(run_id))
        payload = json.loads((self._managed_run_dir(run_id) / "run.json").read_text(encoding="utf-8"))
        payload.setdefault("origin", "managed")
        payload.setdefault("deletable", True)
        payload.setdefault("keep_supported", True)
        payload.setdefault("preview_artifact", (_select_preview_artifact(payload.get("artifacts", [])) or {}).get("relative_path"))
        return self._apply_catalog(payload)

    def set_keep(self, run_id: str, keep: bool) -> dict[str, Any]:
        if run_id.startswith("external__"):
            self._set_catalog_fields(run_id, {"keep": keep})
            return self.read_metadata(run_id)
        metadata = self.read_metadata(run_id)
        metadata["keep"] = keep
        metadata["updated_at"] = utc_now()
        self.write_metadata(self._managed_run_dir(run_id), metadata)
        return metadata

    def set_important(self, run_id: str, important: bool) -> dict[str, Any]:
        if run_id.startswith("external__"):
            self._set_catalog_fields(run_id, {"important": important})
            return self.read_metadata(run_id)
        metadata = self.read_metadata(run_id)
        metadata["important"] = important
        metadata["updated_at"] = utc_now()
        self.write_metadata(self._managed_run_dir(run_id), metadata)
        return metadata

    def update_annotations(self, run_id: str, *, label: str | None = None, comment: str | None = None) -> dict[str, Any]:
        if run_id.startswith("external__"):
            updates = {}
            if label is not None:
                updates["label"] = label
            if comment is not None:
                updates["comment"] = comment
            self._set_catalog_fields(run_id, updates)
            return self.read_metadata(run_id)
        metadata = self.read_metadata(run_id)
        if label is not None:
            metadata["label"] = label
        if comment is not None:
            metadata["comment"] = comment
        metadata["updated_at"] = utc_now()
        self.write_metadata(self._managed_run_dir(run_id), metadata)
        return metadata

    def delete_run(self, run_id: str) -> None:
        if run_id.startswith("external__"):
            raise ValueError("Suppression désactivée pour les simulations externes existantes.")
        metadata = self.read_metadata(run_id)
        if metadata.get("trashed"):
            raise ValueError("Cette simulation est déjà dans la corbeille.")
        run_dir = self.run_dir(run_id)
        trash_dir = BASKET_DIR / run_id
        metadata["trashed"] = True
        metadata["trashed_at"] = utc_now()
        metadata["updated_at"] = utc_now()
        shutil.move(str(run_dir), str(trash_dir))
        self.write_metadata(trash_dir, metadata)

    def restore_run(self, run_id: str) -> dict[str, Any]:
        trash_dir = BASKET_DIR / run_id
        if not trash_dir.exists():
            raise FileNotFoundError(run_id)
        target_dir = RUNS_DIR / run_id
        metadata = json.loads((trash_dir / "run.json").read_text(encoding="utf-8"))
        metadata["trashed"] = False
        metadata["trashed_at"] = None
        metadata["updated_at"] = utc_now()
        shutil.move(str(trash_dir), str(target_dir))
        self.write_metadata(target_dir, metadata)
        return metadata

    def locate_run(self, run_id: str) -> dict[str, Any]:
        if run_id.startswith("external__"):
            path = self._external_path_from_run_id(run_id)
        else:
            path = self._managed_run_dir(run_id)
        self._open_path(path)
        return {"run_id": run_id, "path": str(path)}

    def refresh_artifacts(self, run_id: str) -> dict[str, Any]:
        if run_id.startswith("external__"):
            return self.read_metadata(run_id)
        run_dir = self._managed_run_dir(run_id)
        metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        metadata["artifacts"] = [artifact.to_dict() for artifact in collect_artifacts(run_dir)]
        metadata["preview_artifact"] = (_select_preview_artifact(metadata["artifacts"]) or {}).get("relative_path")
        metadata["updated_at"] = utc_now()
        self.write_metadata(run_dir, metadata)
        return self.read_metadata(run_id)

    def empty_trash(self) -> dict[str, Any]:
        count = 0
        for path in list(BASKET_DIR.glob("*")):
            if path.is_dir():
                shutil.rmtree(path)
                count += 1
        return {"deleted_count": count}

    def permanently_delete_from_trash(self, run_id: str) -> None:
        trash_dir = BASKET_DIR / run_id
        if not trash_dir.exists():
            raise FileNotFoundError(run_id)
        shutil.rmtree(trash_dir)

    def run_dir(self, run_id: str) -> Path:
        return RUNS_DIR / run_id

    def artifact_path(self, run_id: str, relative_path: str) -> Path:
        base_dir = self._external_path_from_run_id(run_id) if run_id.startswith("external__") else self._managed_run_dir(run_id)
        candidate = (base_dir / relative_path).resolve()
        base_resolved = base_dir.resolve()
        if not str(candidate).startswith(str(base_resolved)):
            raise ValueError("Chemin d'artefact invalide")
        return candidate

    def write_metadata(self, run_dir: Path, metadata: dict[str, Any]) -> None:
        (run_dir / "run.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    def write_batch(self, payload: dict[str, Any]) -> None:
        (BATCHES_DIR / f"{payload['batch_id']}.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def read_batch(self, batch_id: str) -> dict[str, Any]:
        return json.loads((BATCHES_DIR / f"{batch_id}.json").read_text(encoding="utf-8"))

    def list_external_runs(self) -> list[dict[str, Any]]:
        runs: list[dict[str, Any]] = []
        seen: set[Path] = set()
        for meta_path in sorted(ROOT_DIR.rglob("meta.json"), reverse=True):
            path = meta_path.parent
            if path in seen:
                continue
            if RUNS_DIR in path.parents or BASKET_DIR in path.parents:
                continue
            if not self._looks_like_external_simulation(path, meta_path):
                continue
            seen.add(path)
            try:
                runs.append(self._build_external_run(path))
            except Exception:
                continue
        return runs

    def _build_external_run(self, path: Path, model_id: str | None = None) -> dict[str, Any]:
        meta = json.loads((path / "meta.json").read_text(encoding="utf-8"))
        detected_model_id = model_id or self._detect_model_id_from_path(path)
        run_id = self._external_run_id(path)
        created_at = meta.get("date", "")
        parameters = meta.get("config", meta.get("parametres", {}))
        summary = meta.get("summary", meta.get("resume", {}))
        artifacts = [artifact.to_dict() for artifact in collect_artifacts(path)]
        preview_artifact = _select_preview_artifact(artifacts)
        payload = {
            "run_id": run_id,
            "model_id": detected_model_id,
            "parameters": parameters,
            "seed": parameters.get("seed", parameters.get("graine")),
            "label": meta.get("label", path.name),
            "batch_id": None,
            "status": "completed",
            "keep": False,
            "important": False,
            "created_at": created_at,
            "updated_at": created_at,
            "summary": summary,
            "artifacts": artifacts,
            "message": meta.get("notes", ""),
            "comment": "",
            "extra": {"source_path": str(path)},
            "origin": "external",
            "deletable": False,
            "keep_supported": True,
            "trashed": False,
            "trashed_at": None,
            "preview_artifact": preview_artifact["relative_path"] if preview_artifact else None,
        }
        return self._apply_catalog(payload)

    def _external_run_id(self, path: Path) -> str:
        return f"external__{path.as_posix().replace('/', '__')}"

    def _external_path_from_run_id(self, run_id: str) -> Path:
        _, encoded = run_id.split("external__", 1)
        return Path(encoded.replace("__", "/"))

    def _detect_model_id_from_path(self, path: Path) -> str:
        lower = path.as_posix().lower()
        if "/claude3-v2/" in lower:
            return "claude3_v2"
        if "/modèle_sans_banque_wip/" in lower or "/mod%c3%a8le_sans_banque_wip/" in lower:
            return "modele_sans_banque_wip"
        if "/claude/" in lower or lower.endswith("/claude"):
            return "claude_historique"
        for model_id, roots in LEGACY_RESULT_SOURCES.items():
            for root in roots:
                if root in path.parents:
                    return model_id
        return "external"

    def _managed_run_dir(self, run_id: str) -> Path:
        active = RUNS_DIR / run_id
        if active.exists():
            return active
        trashed = BASKET_DIR / run_id
        if trashed.exists():
            return trashed
        raise FileNotFoundError(run_id)

    def _load_catalog(self) -> dict[str, dict[str, Any]]:
        if not CATALOG_FILE.exists():
            return {}
        try:
            return json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_catalog(self) -> None:
        CATALOG_FILE.write_text(json.dumps(self._catalog, indent=2, ensure_ascii=False), encoding="utf-8")

    def _set_catalog_fields(self, run_id: str, updates: dict[str, Any]) -> None:
        entry = self._catalog.get(run_id, {})
        entry.update(updates)
        entry["updated_at"] = utc_now()
        self._catalog[run_id] = entry
        self._save_catalog()

    def _apply_catalog(self, payload: dict[str, Any]) -> dict[str, Any]:
        entry = self._catalog.get(payload["run_id"], {})
        if "label" in entry:
            payload["label"] = entry["label"]
        if "comment" in entry:
            payload["comment"] = entry["comment"]
        else:
            payload.setdefault("comment", "")
        if "important" in entry:
            payload["important"] = entry["important"]
        if "keep" in entry:
            payload["keep"] = entry["keep"]
        return payload

    def _looks_like_external_simulation(self, path: Path, meta_path: Path) -> bool:
        if path.name.startswith("simu_"):
            return True
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            return False
        return any(key in meta for key in ("config", "summary", "parametres", "resume"))

    def _open_path(self, path: Path) -> None:
        if os.name == "posix":
            if shutil.which("xdg-open"):
                subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            if shutil.which("open"):
                subprocess.Popen(["open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
        raise RuntimeError(f"Impossible d'ouvrir automatiquement {path}")


def _select_preview_artifact(artifacts: list[dict[str, Any]]) -> dict[str, Any] | None:
    images = [item for item in artifacts if item.get("kind") == "image"]
    if not images:
        return None
    preferred_names = [
        "macro_overview.png",
        "indicateurs_systemiques.png",
        "market_overview.png",
        "trajectory.png",
        "distribution.png",
    ]
    for preferred_name in preferred_names:
        match = next((item for item in images if item.get("label") == preferred_name), None)
        if match:
            return match
    return images[0]
