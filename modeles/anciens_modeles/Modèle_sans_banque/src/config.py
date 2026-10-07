"""
config.py — Configuration centralisée de la simulation.

Toutes les constantes sont rassemblées dans une unique dataclass typée.
Chaque paramètre est documenté inline avec sa signification physique/économique
et sa valeur calibrée.

Usage :
    from config import SimulationConfig
    config = SimulationConfig()               # valeurs par défaut (Bloc 8)
    config = SimulationConfig(theta=0.5)      # override ponctuel
"""

from dataclasses import dataclass


@dataclass
class SimulationConfig:
    """
    Paramètres de simulation regroupés par domaine fonctionnel.
    Tous les taux sont exprimés par pas de simulation (et non annualisés).
    """

    # ──────────────────────────────────────────────────────────────────────
    #  PRODUCTIVITÉ
    # ──────────────────────────────────────────────────────────────────────

    # Coefficient d'extraction central (non utilisé directement ; la valeur
    # effective est tirée uniformément dans [alpha_min, alpha_max] à la création).
    alpha: float = 1.0

    # Distribution d'alpha à la création de chaque entité : tirage U[α_min, α_max].
    # L'hétérogénéité de productivité est la source principale de la segmentation
    # prêteur/emprunteur (r* = α/(2√P) dépend de α).
    alpha_min: float = 0.8
    alpha_max: float = 1.2

    # Volatilité du mouvement brownien géométrique sur α :
    #   α(t+1) = α(t) * exp(σ * N(0,1)) 
    # 0 = alpha statique (pas de choc de productivité). 0.005 = faible dérive.
    alpha_sigma_brownien: float = 0.005

    # ──────────────────────────────────────────────────────────────────────
    #  MARCHÉ DU CRÉDIT
    # ──────────────────────────────────────────────────────────────────────

    # Seuil minimal de ratio L/P pour qu'une entité participe au marché.
    # Filtre les entités trop illiquides pour prêter ou emprunter utilement.
    seuil_ratio_liquide_passif: float = 0.05

    # Fraction de la demande optimale effectivement empruntée (0 < θ ≤ 1).
    # La demande optimale q_max = (α/2r)² − P − surplus dérive du taux interne.
    # θ = 1 provoque un sur-levier systématique (mortalité > 90 % observée).
    # θ = 0.35 : demande prudente, donne mortalité ≈ 10-27 % selon λ.
    theta: float = 0.35

    # Prime de rendement minimal à l'emprunt : l'emprunt n'est accepté que si
    #   gain_avec_emprunt / gain_sans_emprunt ≥ 1 + μ
    # μ = 0 : neutralité (emprunt accepté dès qu'il n'est pas perdant).
    # μ = 0.05 : exige un gain net de 5 % par rapport à l'auto-investissement seul.
    mu: float = 0.05

    # Contrainte d'endettement : (charges_existantes + r_new * q_new) / revenus_totaux ≤ seuil.
    # 1 = les charges d'intérêts ne peuvent pas dépasser les revenus d'extraction + intérêts reçus.
    # Une valeur ≤ 0 désactive la contrainte.
    seuil_ratio_endettement: float = 1

    # Partage du surplus de rendement entre prêteur et emprunteur :
    #   r_transaction = (1 - f) * r*_prêteur + f * r*_emprunteur
    # f = 0 : prêteur capte tout le surplus (taux = r*_prêteur, neutre pour lui).
    # f = 0.5 : partage symétrique.
    # f = 0.2 : légèrement favorable au prêteur.
    fraction_taux_emprunteur: float = 0.2

    # Amortissement géométrique du principal à chaque pas :
    #   amort = τ × principal_restant
    # 0 = prêts perpétuels (τ = 0 par défaut, Bloc 8).
    # 0.01 = demi-vie ≈ 69 pas.
    taux_amortissement: float = 0

    # ──────────────────────────────────────────────────────────────────────
    #  CRÉATION D'ENTITÉS
    # ──────────────────────────────────────────────────────────────────────

    # Taille de la population initiale (toutes créées à t=0).
    n_entites_initiales: int = 100

    # Paramètre λ du processus de Poisson d'arrivée de nouvelles entités par pas.
    # λ = 10 (version précédente) : population explosait vers 10 000+ sur 1000 pas.
    # λ = 2 (Bloc 8) : flux d'entrée ≈ flux de faillite → population quasi-stationnaire.
    lambda_creation: float = 2

    # Dotation initiale de chaque entité nouvellement créée.
    # NW initial = actif_liquide_initial - passif_inne_initial = 10 > 0.
    actif_liquide_initial: float = 200.0
    passif_inne_initial: float = 190.0

    # ──────────────────────────────────────────────────────────────────────
    #  DÉPRÉCIATION (taux par pas, géométrique)
    # ──────────────────────────────────────────────────────────────────────

    # Dépréciation du liquide : L(t+1) = L(t) * (1 - δ_L).
    # Modélise la perte de valeur d'une réserve en numéraire (inflation, coût de portage).
    taux_depreciation_liquide: float = 0.0

    # Dépréciation du capital endo-investi et de son passif symétrique :
    #   K^endo(t+1) = K^endo(t) * (1 - δ_endo),  P^endo(t+1) = P^endo(t) * (1 - δ_endo).
    # Modélise l'obsolescence du capital autogénéré (équipements, savoir-faire).
    taux_depreciation_endo: float = 0.05

    # Dépréciation du capital exo-investi et de son passif symétrique :
    #   K^exo(t+1) = K^exo(t) * (1 - δ_exo),   P^exo(t+1) = P^exo(t) * (1 - δ_exo).
    # Aussi utilisé pour la réévaluation des prêts :
    #   q_réel = q_nominal * (1 - δ_exo)^âge
    # À δ_exo = 0.1, demi-vie ≈ 7 pas (amortissement implicite des créances).
    taux_depreciation_exo: float = 0.05

    # ──────────────────────────────────────────────────────────────────────
    #  ILLIQUIDITÉ ET RELIQUÉFACTION
    # ──────────────────────────────────────────────────────────────────────

    # Coefficient de conversion endo → liquide lors d'une reliquéfaction forcée :
    #   liquide_généré = c × endo_détruit
    # c = 0.5 : vendre du capital productif à 50 % de sa valeur comptable.
    # Cette décote modélise la perte irréversible liée à une cession forcée.
    coefficient_reliquefaction: float = 0.5

    # ──────────────────────────────────────────────────────────────────────
    #  AUTO-INVESTISSEMENT
    # ──────────────────────────────────────────────────────────────────────

    # Fraction φ du surplus liquide auto-investie en capital endogène à chaque pas :
    #   x = φ * max(0, L - réserve)
    # où réserve = max(s * P, B_innée) garantit L ≥ B après conversion, et donc ne pas faire faillite.
    fraction_auto_investissement: float = 0.5

    # ──────────────────────────────────────────────────────────────────────
    #  SIMULATION
    # ──────────────────────────────────────────────────────────────────────

    duree_simulation: int = 1000   # Nombre de pas à simuler
    seed: int = 42                 # Graine RNG pour reproductibilité

    # ──────────────────────────────────────────────────────────────────────
    #  PARAMÈTRES TECHNIQUES
    # ──────────────────────────────────────────────────────────────────────

    # Nombre maximal d'itérations de la boucle de marché du crédit par pas.
    # La boucle s'arrête bien avant si MAX_IDLE tentatives consécutives échouent.
    max_credit_iterations: int = 100_000

    # Taille du pool de candidats pour l'appariement aléatoire (Bloc 8) :
    #   k = 1 : arbitrage pur (prêteur à r* minimal × emprunteur à r* maximal).
    #           Rôles strictement séparés → pas d'intermédiaires financiers → 0 cascades.
    #   k ≥ 2 : tirage aléatoire dans les k meilleurs de chaque côté.
    #           Une entité médiane peut être prêteuse d'une petite ET emprunteuse
    #           d'une grande → intermédiaires financiers naturels → contagion possible.
    #   k = 3 : point de transition critique (bifurcation stable → SOC).
    #           k ≤ 2 → régime stable (cascades nulles) ;
    #           k ≥ 3 → régime SOC (cascades en loi de puissance potentielle).
    n_candidats_pool: int = 3

    # Valeur en dessous de laquelle un montant est considéré nul (évite les divisions
    # par zéro et les prêts de montant négligeable).
    epsilon: float = 1e-6  #Quel impact cumulé ?

    # Journalisation détaillée de chaque événement (prêt, faillite, etc.) dans event_log.
    # Coûteux en mémoire sur de longues simulations. Désactivé par défaut.
    log_events: bool = False

    # ──────────────────────────────────────────────────────────────────────
    #  STATISTIQUES
    # ──────────────────────────────────────────────────────────────────────

    # Fréquence des snapshots de distribution (en nombre de pas).
    # 1 = snapshot à chaque pas (détaillé mais volumineux).
    # 50 = snapshot toutes les 50 itérations.
    freq_snapshot: int = 50
