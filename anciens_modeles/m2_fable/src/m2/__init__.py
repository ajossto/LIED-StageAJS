"""M2 — modèle Boltzmann-Pareto par auto-organisation critique.

Implémentation de la spécification `conception_modele_M2.md` (§2.2), avec les
conventions C1-C10 de `reports/02_technical_spec/`. Workspace isolé m2_fable.
"""
from .config import M2Config
from .simulation import Simulation

__all__ = ["M2Config", "Simulation"]
