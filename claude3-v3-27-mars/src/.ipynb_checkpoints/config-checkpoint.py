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
    # Valeur de référence (centre de la distribution initiale).
    alpha: float = 1.0

    # Distribution d'alpha à la création : tirage uniforme dans [alpha_min, alpha_max].
    # Prépare un futur mouvement brownien par entité (alpha_sigma_brownien).
    alpha_min: float = 0.8
    alpha_max: float = 1.2
    alpha_sigma_brownien: float = 0.005  # 0 = statique (mouvement brownien désactivé)

    # ------------------------------------------------------------------
    #  MARCHÉ DU CRÉDIT
    # ------------------------------------------------------------------

    # Seuil de liquidité relative L/P pour participer au marché.
    seuil_ratio_liquide_passif: float = 0.05

    # Fraction de la demande maximale effectivement demandée (0 < θ ≤ 1).
    theta: float = 1

    # Marge minimale relative : l'emprunt n'est accepté que si
    # gain_emprunt / gain_auto_invest ≥ 1 + mu.
    mu: float = 0.05

    # Contrainte d'endettement : (Σ r·q existants + r_new·q_new) / (α√P) ≤ seuil.
    # 0 = pas de contrainte active (désactivé si inf).
    seuil_ratio_endettement: float = 1

    # Taux de transaction : interpolation entre r*_prêteur (0.0) et r*_emprunteur (1.0).
    # 0.5 = moyenne des deux ; >0.5 biaise vers l'emprunteur (taux élevé pour petits emprunteurs).
    fraction_taux_emprunteur: float = 0.2

    # Amortissement géométrique : fraction du principal restant remboursée chaque pas.
    # 0 = prêts perpétuels. 0.01 = demi-vie ≈ 69 pas.
    taux_amortissement: float = 0
    
    # ------------------------------------------------------------------
    #  CRÉATION D'ENTITÉS
    # ------------------------------------------------------------------

    # Nombre d'entités dans la population initiale.
    n_entites_initiales: int = 10

    # Paramètre de Poisson pour l'arrivée de nouvelles entités par pas.
    lambda_creation: float = 1

    # Dotation initiale de chaque nouvelle entité.
    actif_liquide_initial: float = 10.0
    passif_inne_initial: float = 5.0

    # ------------------------------------------------------------------
    #  DÉPRÉCIATION
    # ------------------------------------------------------------------

    taux_depreciation_liquide: float = 0.01
    taux_depreciation_endo: float = 0.1
    taux_depreciation_exo: float = 0.1

    # ------------------------------------------------------------------
    #  ILLIQUIDITÉ
    # ------------------------------------------------------------------

    # c = 0.5 → détruire 1 joule endo-investi génère 0.5 joule liquide.
    coefficient_reliquefaction: float = 0.5

    # ------------------------------------------------------------------
    #  AUTO-INVESTISSEMENT
    # ------------------------------------------------------------------

    # Fraction du surplus liquide (L - seuil*P) auto-investie chaque pas.
    fraction_auto_investissement: float = 0.5

    # ------------------------------------------------------------------
    #  SIMULATION
    # ------------------------------------------------------------------

    duree_simulation: int = 1000
    seed: int = 42

    # ------------------------------------------------------------------
    #  TECHNIQUE
    # ------------------------------------------------------------------

    # Nombre maximal d'itérations du marché du crédit par pas.
    max_credit_iterations: int = 100_000

    # Valeur en dessous de laquelle une quantité est considérée nulle.
    epsilon: float = 1e-6

    # Journalisation détaillée des événements (coûteux en mémoire).
    log_events: bool = False

    # ------------------------------------------------------------------
    #  STATISTIQUES
    # ------------------------------------------------------------------

    # Fréquence des snapshots de distribution (1 = chaque pas).
    freq_snapshot: int = 10
