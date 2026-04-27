from __future__ import annotations

import importlib.util
import sys
import threading
from contextlib import redirect_stderr, redirect_stdout
from contextlib import contextmanager
from dataclasses import MISSING, fields, is_dataclass
from pathlib import Path
import re
from typing import Any

from simulation_lab.progress import emit_progress, ensure_not_cancelled
from simulation_lab.contracts import BaseSimulationModel, ParameterSpec, SimulationResult, collect_artifacts


_LEGACY_EXECUTION_LOCK = threading.Lock()


@contextmanager
def _prepend_sys_path(path: Path):
    as_str = str(path)
    sys.path.insert(0, as_str)
    try:
        yield
    finally:
        try:
            sys.path.remove(as_str)
        except ValueError:
            pass


class LegacyModuleModel(BaseSimulationModel):
    def __init__(
        self,
        *,
        model_id: str,
        display_name: str,
        description: str,
        source_dir: str,
        config_module: str = "config",
        output_module: str = "output",
        analysis_module: str = "analysis",
        config_class_name: str = "SimulationConfig",
    ) -> None:
        self.model_id = model_id
        self.display_name = display_name
        self.description = description
        self.tags = ["legacy"]
        self.source_dir = Path(source_dir).resolve()
        self.config_module_name = config_module
        self.output_module_name = output_module
        self.analysis_module_name = analysis_module
        self.config_class_name = config_class_name
        super().__init__()

    def _load_modules(self) -> tuple[type[Any], Any, Any | None]:
        with _prepend_sys_path(self.source_dir):
            config_module = _load_module_from_path(
                self.source_dir / f"{self.config_module_name}.py",
                f"{self.model_id}_{self.config_module_name}",
            )
            output_module = _load_module_from_path(
                self.source_dir / f"{self.output_module_name}.py",
                f"{self.model_id}_{self.output_module_name}",
            )
            try:
                analysis_module = _load_module_from_path(
                    self.source_dir / f"{self.analysis_module_name}.py",
                    f"{self.model_id}_{self.analysis_module_name}",
                )
            except Exception:
                analysis_module = None
        config_class = getattr(config_module, self.config_class_name)
        return config_class, output_module, analysis_module

    def parameter_specs(self) -> list[ParameterSpec]:
        config_class, _, _ = self._load_modules()
        if not is_dataclass(config_class):
            raise TypeError(f"{config_class.__name__} doit être une dataclass.")
        specs: list[ParameterSpec] = []
        for field_info in fields(config_class):
            default = None if field_info.default is MISSING else field_info.default
            param_type = _map_type(field_info.type, default)
            specs.append(
                ParameterSpec(
                    name=field_info.name,
                    param_type=param_type,
                    default=default,
                    label=field_info.name.replace("_", " "),
                    description=f"Paramètre legacy importé depuis {self.source_dir.name}",
                )
            )
        return specs

    def run(
        self,
        parameters: dict[str, Any],
        output_dir: Path,
        seed: int,
        run_label: str = "",
    ) -> SimulationResult:
        config_class, output_module, analysis_module = self._load_modules()
        full_parameters = dict(parameters)
        full_parameters["seed"] = seed
        config = config_class(**full_parameters)
        output_dir.mkdir(parents=True, exist_ok=True)
        legacy_root = output_dir / "legacy_output"
        log_path = output_dir / "legacy_execution.log"
        with _LEGACY_EXECUTION_LOCK:
            with _prepend_sys_path(self.source_dir):
                run_and_save = getattr(output_module, "run_and_save")
                with log_path.open("w", encoding="utf-8") as log_handle:
                    stream = _ProgressLogStream(log_handle)
                    with redirect_stdout(stream), redirect_stderr(stream):
                        _, folder = run_and_save(
                            config=config,
                            label=run_label or self.model_id,
                            notes="Run lancé via Simulation Lab",
                            root=str(legacy_root),
                            verbose=True,
                        )
                        if analysis_module and hasattr(analysis_module, "analyze_folder"):
                            try:
                                analysis_module.analyze_folder(folder)
                            except Exception:
                                pass
        summary = {}
        meta_path = Path(folder) / "meta.json"
        if meta_path.exists():
            import json

            summary = json.loads(meta_path.read_text(encoding="utf-8")).get("summary", {})
        return SimulationResult(
            status="completed",
            summary=summary,
            artifacts=collect_artifacts(output_dir),
            message=f"Run legacy exécuté dans {folder}",
        )


def _map_type(annotation: Any, default: Any) -> str:
    origin = getattr(annotation, "__name__", str(annotation))
    if annotation is bool or isinstance(default, bool) or origin == "bool":
        return "bool"
    if annotation is int or ((isinstance(default, int) and not isinstance(default, bool))) or origin == "int":
        return "int"
    if annotation is float or isinstance(default, float) or origin == "float":
        return "float"
    return "str"


def _load_module_from_path(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Impossible de charger {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _ProgressLogStream:
    def __init__(self, handle) -> None:
        self.handle = handle
        self.buffer = ""
        self.total_steps: int | None = None

    def write(self, text: str) -> int:
        ensure_not_cancelled()
        self.handle.write(text)
        self.handle.flush()
        self.buffer += text
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            self._process_line(line.rstrip())
        return len(text)

    def flush(self) -> None:
        self.handle.flush()

    def _process_line(self, line: str) -> None:
        ensure_not_cancelled()
        if not line.strip():
            return
        emit_progress({"log": line})
        start_match = re.search(r"Démarrage\s*:\s*(\d+)\s+pas", line)
        if start_match:
            self.total_steps = int(start_match.group(1))
            emit_progress({"progress": 3.0, "message": line})
            return
        step_match = re.search(r"Pas\s+(\d+)", line)
        if step_match and self.total_steps:
            current = int(step_match.group(1))
            ratio = min(95.0, max(5.0, (current / self.total_steps) * 100.0))
            emit_progress({"progress": ratio, "message": line})
            return
        if "Simulation terminée" in line:
            emit_progress({"progress": 97.0, "message": line})
            return
        if "Graphiques générés" in line:
            emit_progress({"progress": 99.0, "message": line})
