"""M4.3 : moteur repris tel quel de M4.2B (`model.py`/`io.py` copiés
octet pour octet, `diff` vide contre `m4_2b_credit_soc/m4_2b/`, vérifié par
`tests/test_parity_m4_2b.py`) — PROMPT_M4_3_FINAL.md §8. Aucune modification
de mécanique tant qu'une ablation n'est pas explicitement décidée et
justifiée (§4)."""

from .io import run_and_save
from .model import Config, Simulation

__all__ = ["Config", "Simulation", "run_and_save"]
