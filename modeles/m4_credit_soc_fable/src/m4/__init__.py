"""M4 — moteur fusionné (refonte 2026-07-14, voir config.py et NOTES.md).

Une variable d'état réelle (K), pas de d0 (plancher purement contractuel),
règle de faillite simple cancel+destroy (le mécanisme de cascade candidat),
chocs iid par défaut, objectif de revenu myope (X1). Le moteur L/K du fork
M3 est archivé dans archive/m4_lk_pre_refonte/.
"""
from .config import M4Config
from .simulation import Simulation

__all__ = ["M4Config", "Simulation"]
