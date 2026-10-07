"""M4.3Live — moteur pilotable en direct, institution de principal « production
jointe maximale », technologies (A, γ) par entité.

Paquet AUTONOME (prompt §3.5) : aucune importation d'un autre moteur du
dépôt. `m4_3_credit_soc/m4_3/model.py` en est la référence structurelle,
lue, pas importée.
"""

from .kernel import PrincipalKernel, TechRegistry, lambda_star, newton_z
from .model import (
    PARAM_SEMANTICS,
    SCOPES,
    Config,
    Intervention,
    LoanBook,
    Population,
    Simulation,
    pair_rate,
    surplus_rate,
)

__all__ = [
    "Config",
    "Intervention",
    "LoanBook",
    "Population",
    "PrincipalKernel",
    "Simulation",
    "TechRegistry",
    "PARAM_SEMANTICS",
    "SCOPES",
    "lambda_star",
    "newton_z",
    "pair_rate",
    "surplus_rate",
]

MODEL_VERSION = "m4_3live_v2-1"
