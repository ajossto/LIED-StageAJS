"""Configuration du modèle M2. Toute variante expérimentale est un champ nommé."""
from dataclasses import dataclass, asdict, field


@dataclass(frozen=True)
class M2Config:
    # --- paramètres du modèle (§4 du rapport de conception) ---
    alpha: float = 1.0          # convention d'unité de flux (ne pas régler)
    delta: float = 0.05         # dépréciation du capital réel = unité de temps
    lam: float = 10.0           # intensité Poisson des naissances (taille N*)
    k: int = 6                  # taille d'échantillon du marché (connectivité)
    sigma: float = 0.25         # écart-type du choc multiplicatif commun en loi
    w0: float = 30.0            # dotation de naissance
    d0: float = 28.0            # dette d'amorçage nominale (eps0 = w0 - d0)

    # --- variantes nommées (C5/C6, ablations §7 de la spec) ---
    rate_rule: str = "geom"             # "geom" | "arith"
    fail_lender_loans: str = "transfer" # "transfer" (M2 §2.2) | "cancel" (proto E7c)
    fail_residual: str = "prorata"      # "prorata" (M2 §2.2) | "destroy"
    credit: bool = True                 # False = modèle nul sans marché
    # Fusion des contrats d'une même paire (prêteur, emprunteur) au taux moyen
    # pondéré par le principal. Préserve exactement NW, créances/dettes, flux
    # d'intérêts totaux et prorata de faillite ; borne le carnet (correctif de
    # la prolifération par scission, rapport 05 §3.1). MODIFIE l'objet contrat
    # de la spec (taux figé à la création) — variante, pas un correctif muet.
    merge_pairs: bool = False

    # --- technique ---
    seed: int = 0
    T: int = 2000
    tol_nw: float = 1e-9        # tolérance du critère de faillite NW < -tol
    q_min: float = 1e-9         # principal minimal d'un contrat actif
    pop_max: int = 30000        # garde-fou d'ARRÊT (I9) — ne borne pas la dynamique
    w_clamp: float = 1e-12      # |w| < w_clamp arrondi à 0 (erreur flottante)

    def __post_init__(self):
        assert self.w0 > self.d0 >= 0.0, "eps0 = w0 - d0 doit être > 0"
        assert self.k >= 2 and self.delta > 0 and self.sigma >= 0
        assert self.rate_rule in ("geom", "arith")
        assert self.fail_lender_loans in ("transfer", "cancel")
        assert self.fail_residual in ("prorata", "destroy")

    @property
    def eps0(self) -> float:
        return self.w0 - self.d0

    def to_dict(self) -> dict:
        return asdict(self)
