from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


PARAMETER_TYPES = {"int", "float", "str", "bool"}


@dataclass(slots=True)
class ParameterSpec:
    name: str
    param_type: str
    default: Any
    label: str = ""
    description: str = ""
    minimum: float | int | None = None
    maximum: float | int | None = None
    choices: list[Any] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Artifact:
    relative_path: str
    kind: str
    label: str = ""
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SimulationResult:
    status: str
    summary: dict[str, Any] = field(default_factory=dict)
    artifacts: list[Artifact] = field(default_factory=list)
    message: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "summary": self.summary,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "message": self.message,
            "extra": self.extra,
        }


class BaseSimulationModel:
    model_id: str
    display_name: str
    description: str
    tags: list[str]

    def __init__(self) -> None:
        if not getattr(self, "model_id", ""):
            raise ValueError("model_id est requis.")
        self.display_name = getattr(self, "display_name", self.model_id)
        self.description = getattr(self, "description", "")
        self.tags = list(getattr(self, "tags", []))

    def parameter_specs(self) -> list[ParameterSpec]:
        raise NotImplementedError

    def run(
        self,
        parameters: dict[str, Any],
        output_dir: Path,
        seed: int,
        run_label: str = "",
    ) -> SimulationResult:
        raise NotImplementedError

    def describe(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "display_name": self.display_name,
            "description": self.description,
            "tags": self.tags,
            "parameters": [spec.to_dict() for spec in self.parameter_specs()],
        }

    def validate_parameters(self, raw_parameters: dict[str, Any]) -> dict[str, Any]:
        specs = {spec.name: spec for spec in self.parameter_specs()}
        validated: dict[str, Any] = {}
        unknown = sorted(set(raw_parameters) - set(specs))
        if unknown:
            raise ValueError(f"Paramètres inconnus: {', '.join(unknown)}")
        for name, spec in specs.items():
            raw_value = raw_parameters.get(name, spec.default)
            value = _coerce_value(spec, raw_value)
            if spec.minimum is not None and value < spec.minimum:
                raise ValueError(f"{name} doit être >= {spec.minimum}")
            if spec.maximum is not None and value > spec.maximum:
                raise ValueError(f"{name} doit être <= {spec.maximum}")
            if spec.choices and value not in spec.choices:
                raise ValueError(f"{name} doit être dans {spec.choices}")
            validated[name] = value
        return validated


def _coerce_value(spec: ParameterSpec, raw_value: Any) -> Any:
    if spec.param_type not in PARAMETER_TYPES:
        raise ValueError(f"Type de paramètre non supporté: {spec.param_type}")
    if spec.param_type == "bool":
        if isinstance(raw_value, bool):
            return raw_value
        lowered = str(raw_value).strip().lower()
        if lowered in {"1", "true", "oui", "yes", "on"}:
            return True
        if lowered in {"0", "false", "non", "no", "off"}:
            return False
        raise ValueError(f"{spec.name}: booléen invalide")
    if spec.param_type == "int":
        return int(raw_value)
    if spec.param_type == "float":
        return float(raw_value)
    return str(raw_value)


def collect_artifacts(root: Path) -> list[Artifact]:
    artifacts: list[Artifact] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(root).parts
        if any(part.startswith(".") or part == "__pycache__" for part in relative_parts):
            continue
        if path.name == "run.json":
            continue
        suffix = path.suffix.lower()
        if suffix in {".png", ".jpg", ".jpeg", ".gif"}:
            kind = "image"
        elif suffix == ".csv":
            kind = "csv"
        elif suffix in {".json", ".txt", ".md"}:
            kind = "text"
        else:
            kind = "file"
        artifacts.append(Artifact(relative_path=str(path.relative_to(root)), kind=kind, label=path.name))
    return artifacts
