"""
parametres.py — Fichier centralisé des paramètres de la simulation.

Modifier ce fichier pour ajuster le comportement du modèle.
Tous les paramètres sont documentés en ligne.
"""

PARAMS = {
    # -------------------------------------------------------
    #  PRODUCTIVITÉ
    # -------------------------------------------------------

    # Coefficient d'extraction : Π = alpha * sqrt(P)
    # Plus alpha est grand, plus les entités extraient rapidement.
    "alpha": 1.0,

    # -------------------------------------------------------
    #  MARCHÉ DU CRÉDIT
    # -------------------------------------------------------

    # Seuil de liquidité relative pour agir sur le marché.
    # Une entité participe si L / P > seuil.
    # Augmenter ce seuil rend le marché plus restrictif.
    "seuil_ratio_liquide_passif": 0.05,

    # Fraction de la demande maximale effectivement demandée (0 < theta <= 1).
    # theta = 1 → l'emprunteur demande le maximum théorique.
    # theta = 0.5 → demande la moitié.
    "theta": 0.5,

    # Marge minimale relative pour accepter un emprunt vs auto-investissement.
    # L'emprunt n'est accepté que si gain_emprunt / gain_auto >= 1 + mu.
    # mu = 0 → critère neutre. mu = 0.1 → il faut 10% de mieux.
    "mu": 0.05,

    # Spread ajouté au taux interne du prêteur comme taux proposé.
    # 0 = le prêteur propose exactement son taux interne marginal.
    "spread_taux_preteur": 0.0,

    # -------------------------------------------------------
    #  CRÉATION D'ENTITÉS
    # -------------------------------------------------------

    # Paramètre de la loi de Poisson pour l'arrivée de nouvelles entités.
    # lambda_creation = 0.5 → en moyenne 0.5 nouvelle entité par pas.
    "lambda_creation": 0.5,

    # Dotation initiale de chaque nouvelle entité.
    "actif_liquide_initial": 10.0,
    "passif_inne_initial": 5.0,

    # -------------------------------------------------------
    #  DÉPRÉCIATION
    # -------------------------------------------------------

    # Taux de dépréciation de l'actif liquide par pas (fraction perdue).
    "taux_depreciation_liquide": 0.02,

    # Taux de dépréciation de l'actif et du passif endo-investis.
    "taux_depreciation_endo": 0.03,

    # Taux de dépréciation de l'actif et du passif exo-investis.
    "taux_depreciation_exo": 0.03,

    # -------------------------------------------------------
    #  ILLIQUIDITÉ
    # -------------------------------------------------------

    # Coefficient de reliquéfaction lors de la destruction d'endo-investi.
    # c = 0.5 → détruire 1 joule endo-investi génère 0.5 joule liquide.
    "coefficient_reliquefaction": 0.5,

    # -------------------------------------------------------
    #  AUTO-INVESTISSEMENT
    # -------------------------------------------------------

    # Fraction de l'actif liquide auto-investie en fin de tour.
    # 0.3 → 30% du liquide est immobilisé chaque pas.
    "fraction_auto_investissement": 0.3,

    # -------------------------------------------------------
    #  SIMULATION
    # -------------------------------------------------------

    # Nombre de pas de simulation.
    "nb_pas": 200,

    # Graine aléatoire. None = aléatoire à chaque exécution.
    "graine": 42,
}
