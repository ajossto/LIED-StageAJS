from __future__ import annotations

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
DEFAULT_PORT = 8765
LEGACY_RESULT_SOURCES = {
    "modele_sans_banque_wip": [
        ROOT_DIR / "Modèle_sans_banque_wip" / "resultats",
        ROOT_DIR / "Modèle_sans_banque_wip" / "src" / "resultats",
    ],
    "claude3_v2": [
        ROOT_DIR / "claude3-v2" / "src" / "resultats",
    ],
}


def ensure_directories() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    BASKET_DIR.mkdir(parents=True, exist_ok=True)
    BATCHES_DIR.mkdir(parents=True, exist_ok=True)
