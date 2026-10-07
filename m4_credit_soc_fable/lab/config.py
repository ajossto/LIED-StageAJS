"""Adaptateur Simulation Lab — ré-export de la config du moteur M4.

Le lab (LegacyModuleModel) charge ce fichier par chemin et lit la dataclass
M4Config pour construire le formulaire de paramètres. Le moteur vit dans
../src/m4 ; on l'ajoute au sys.path ici (idempotent).
"""
import sys
from pathlib import Path

_SRC = str(Path(__file__).resolve().parent.parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from m4.config import M4Config  # noqa: E402,F401
