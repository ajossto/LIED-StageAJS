from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from simulation_lab.contracts import BaseSimulationModel
from simulation_lab.settings import MODELS_DIR, ensure_directories, model_is_archived


class ModelRegistry:
    def __init__(self, models_dir: Path | None = None) -> None:
        ensure_directories()
        self.models_dir = models_dir or MODELS_DIR
        self._models: dict[str, BaseSimulationModel] = {}
        self.reload()

    def reload(self) -> None:
        self._models = {}
        for model_file in sorted(self.models_dir.glob("*/model.py")):
            model = _load_model_from_file(model_file)
            if model.model_id in self._models:
                raise ValueError(f"model_id dupliqué: {model.model_id}")
            model.archived = model_is_archived(model.model_id)
            self._models[model.model_id] = model

    def list_models(self, scope: str = "active") -> list[BaseSimulationModel]:
        if scope not in {"active", "archived", "all"}:
            raise ValueError(f"Périmètre de modèles inconnu: {scope}")
        models = self._models.values()
        if scope == "active":
            models = (model for model in models if not model.archived)
        elif scope == "archived":
            models = (model for model in models if model.archived)
        priority = {"m4b_credit_soc_mini": 0}
        return sorted(
            models,
            key=lambda item: (priority.get(item.model_id, 10), item.display_name.lower()),
        )

    def get(self, model_id: str) -> BaseSimulationModel:
        try:
            return self._models[model_id]
        except KeyError as exc:
            raise KeyError(f"Modèle introuvable: {model_id}") from exc

    def get_launchable(self, model_id: str) -> BaseSimulationModel:
        model = self.get(model_id)
        if model.archived:
            raise ValueError(f"Le modèle {model_id} est archivé et ne peut plus être lancé.")
        return model


def _load_model_from_file(model_file: Path) -> BaseSimulationModel:
    module_name = f"simulation_lab_dynamic_{model_file.parent.name}"
    spec = importlib.util.spec_from_file_location(module_name, model_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Impossible de charger {model_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    model = _extract_model(module)
    if not isinstance(model, BaseSimulationModel):
        raise TypeError(f"{model_file} doit exposer MODEL ou get_model() renvoyant BaseSimulationModel.")
    return model


def _extract_model(module: Any) -> BaseSimulationModel:
    if hasattr(module, "MODEL"):
        return module.MODEL
    if hasattr(module, "get_model"):
        return module.get_model()
    raise AttributeError("MODEL ou get_model() manquant")
