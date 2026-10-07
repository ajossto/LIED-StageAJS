"""M4B : version minimale du modèle de société de crédit M4."""

from .io import run_and_save
from .model import Config, Simulation

__all__ = ["Config", "Simulation", "run_and_save"]
