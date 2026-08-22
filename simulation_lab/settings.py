from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "Simulation Lab"
ROOT_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT_DIR / "modeles-systeme-physicoeconomique"
DATA_DIR = ROOT_DIR / "simulation_lab_data"
RUNS_DIR = DATA_DIR / "runs"
BASKET_DIR = DATA_DIR / "trash"
BATCHES_DIR = DATA_DIR / "batches"
CATALOG_FILE = DATA_DIR / "catalog.json"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8777
ACTIVE_MODEL_IDS = frozenset({"m4b_credit_soc_mini", "m4_2_credit_soc", "m4_2b_credit_soc", "m4_3_credit_soc", "m4_3live_credit_soc"})
LEGACY_RESULT_SOURCES = {
    "modele_sans_banque_wip": [
        ROOT_DIR / "anciens_modeles" / "Modèle_sans_banque" / "resultats",
        ROOT_DIR / "anciens_modeles" / "Modèle_sans_banque" / "src" / "resultats",
    ],
    "claude3_v2": [
        ROOT_DIR / "anciens_modeles" / "claude3-v2" / "src" / "resultats",
    ],
}


def model_is_archived(model_id: str | None) -> bool:
    """Classe tous les modèles hors cibles actives (M4B, M4.2) dans les archives."""
    return model_id not in ACTIVE_MODEL_IDS


def ensure_directories() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    BASKET_DIR.mkdir(parents=True, exist_ok=True)
    BATCHES_DIR.mkdir(parents=True, exist_ok=True)


def cpu_count() -> int:
    return os.cpu_count() or 1


def recommended_workers(reserve_cores: int = 2) -> int:
    return max(1, cpu_count() - reserve_cores)
