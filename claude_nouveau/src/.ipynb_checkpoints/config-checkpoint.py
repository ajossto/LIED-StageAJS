"""
config.py — Configuration centralisée de la simulation.

Paramètres issus du modèle Claude (référence), durée portée à 3000 pas.
Utilise une dataclass typée pour une meilleure lisibilité et validation.
"""

from dataclasses import dataclass


@dataclass
class SimulationConfig:
    # ------------------------------------------------------------------
    #  PRODUCTIVITÉ
    # ------------------------------------------------------------------

    # Coefficient d'extraction : Π = alpha * sqrt(P)
    alpha: float = 1.0

    # ------------------------------------------------------------------
    #  MARCHÉ DU CRÉDIT
    # ------------------------------------------------------------------

    # Seuil de liquidité relative L/P pour participer au marché.
    seuil_ratio_liquide_passif: float = 0.05

    # Fraction de la demande maximale effectivement demandée (0 < θ ≤ 1).
    theta: float = 0.5

    # Marge minimale relative : l'emprunt n'est accepté que si
    # gain_emprunt / gain_auto_invest ≥ 1 + mu.
    mu: float = 0.05

    # Taux proposé par le prêteur :
    #   True  → taux interne du prêteur (r*_prêteur)
    #   False → moyenne des taux internes prêteur et emprunteur
    use_lender_rate_as_offer_rate: bool = True

    # ------------------------------------------------------------------
    #  CRÉATION D'ENTITÉS
    # ------------------------------------------------------------------

    # Paramètre de Poisson pour l'arrivée de nouvelles entités par pas.
    lambda_creation: float = 0.5

    # Dotation initiale de chaque nouvelle entité.
    actif_liquide_initial: float = 10.0
    passif_inne_initial: float = 5.0

    # ------------------------------------------------------------------
    #  DÉPRÉCIATION
    # ------------------------------------------------------------------

    taux_depreciation_liquide: float = 0.02
    taux_depreciation_endo: float = 0.03
    taux_depreciation_exo: float = 0.03

    # ------------------------------------------------------------------
    #  ILLIQUIDITÉ
    # ------------------------------------------------------------------

    # c = 0.5 → détruire 1 joule endo-investi génère 0.5 joule liquide.
    coefficient_reliquefaction: float = 0.5

    # ------------------------------------------------------------------
    #  AUTO-INVESTISSEMENT
    # ------------------------------------------------------------------

    # Fraction du surplus liquide (L - seuil*P) auto-investie chaque pas.
    fraction_auto_investissement: float = 0.3

    # ------------------------------------------------------------------
    #  SIMULATION
    # ------------------------------------------------------------------

    duree_simulation: int = 10000
    seed: int = 42

    # ------------------------------------------------------------------
    #  TECHNIQUE
    # ------------------------------------------------------------------

    # Nombre maximal d'itérations du marché du crédit par pas.
    max_credit_iterations: int = 100_000

    # Valeur en dessous de laquelle une quantité est considérée nulle.
    epsilon: float = 1e-12

    # Journalisation détaillée des événements (coûteux en mémoire).
    log_events: bool = False

    # ------------------------------------------------------------------
    #  STATISTIQUES
    # ------------------------------------------------------------------

    # Fréquence des snapshots de distribution (1 = chaque pas).
    freq_snapshot: int = 10
