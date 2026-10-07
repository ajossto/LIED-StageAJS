"""M3 — crédit productif, liquidité et fragilité nominale (m3_credit_soc).

Spécification pré-enregistrée : reports/02_m3_specification/main.pdf.
"""
from .config import M3Config
from .simulation import Simulation

__all__ = ["M3Config", "Simulation"]
