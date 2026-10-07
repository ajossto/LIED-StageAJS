"""Adaptateur Simulation Lab — figures d'un dossier de run M4.

Expose analyze_folder(folder) au format attendu par LegacyModuleModel :
délègue à m4.lab_figures.analyze_run (batterie « façon m0 » : macro,
cascades, histogrammes, taux interne, Gini/Lorenz, revenus, vies d'entités,
réseau final, durées de vie — depuis les artefacts disque uniquement).
"""
import sys
from pathlib import Path

_SRC = str(Path(__file__).resolve().parent.parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from m4.lab_figures import analyze_run  # noqa: E402


def analyze_folder(folder):
    done = analyze_run(folder)
    print(f"Graphiques générés : {len(done)} recettes", flush=True)
    return done
