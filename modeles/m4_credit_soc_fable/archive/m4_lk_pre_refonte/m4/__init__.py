"""M4 — fork de M3 (m3_credit_soc) figeant deux comportements en baseline :
chocs sectoriels corrélés (loi G, variante G2b : rho_sector=0.8, 5 secteurs)
et maximisation myope du revenu net par l'emprunteuse (protocole X1,
objective="income"). Moteur identique à M3 (reports/03_implementation_report),
seuls les défauts de M4Config diffèrent — voir config.py.
"""
from .config import M4Config
from .simulation import Simulation

__all__ = ["M4Config", "Simulation"]
