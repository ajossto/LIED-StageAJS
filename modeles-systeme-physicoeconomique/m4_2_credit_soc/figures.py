"""Point d'entrée des figures M4.2 sélectionnées par l'utilisateur."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _reporting():
    name = "simulation_lab_m4_2_reporting"
    if name in sys.modules:
        return sys.modules[name]
    path = Path(__file__).with_name("reporting.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Impossible de charger {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def generate_figures(directory: Path, title: str) -> list[str]:
    return _reporting().generate_run(Path(directory), title)


def generate_batch_figures(members, directory: Path, title: str) -> list[str]:
    return _reporting().generate_batch(members, Path(directory), title)


def generate_synthesis_figures(lots, directory: Path, title: str) -> bool:
    return _reporting().generate_synthesis(lots, Path(directory), title)


SELECTED_FAMILIES = _reporting().SELECTED_FAMILIES
