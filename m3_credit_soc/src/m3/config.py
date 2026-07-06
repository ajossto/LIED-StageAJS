"""Configuration du modèle M3. Toute variante expérimentale est un champ nommé.

Baseline pré-enregistrée : rapport 02 (§ paramètres). Les valeurs de s et c
sont provisoires jusqu'à la calibration pré-enregistrée, puis figées.
"""
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class M3Config:
    # --- paramètres hérités de M2 (rapport 02, tableau des paramètres) ---
    alpha: float = 1.0          # convention d'unité de flux (ne pas régler)
    delta: float = 0.05         # dépréciation du capital réel = unité de temps
    lam: float = 10.0           # intensité Poisson des naissances
    k: int = 6                  # taille d'échantillon du marché (connectivité)
    sigma: float = 0.25         # écart-type total du choc multiplicatif
    d0: float = 28.0            # dette d'amorçage nominale (plancher)

    # --- nouveaux paramètres M3 ---
    L0: float = 5.0             # dotation liquide de naissance
    K0: float = 25.0            # dotation en capital de naissance
    # s et c : figés le 2026-07-04 par la calibration pré-enregistrée
    # (experiments/m3/results/calibration_verdicts.json ; NOTES.md).
    # La cellule provisoire (0.75, 0.05) échoue au critère de régime ;
    # (0.75, 0.10) est la cellule viable la plus proche. Ne plus retoucher.
    s: float = 0.75             # part retenue de la production (K += s*P)
    c: float = 0.10             # consommation de la liquidité (L *= 1-c)
    beta_L: float = 1.0         # tampon de service : prêtable = L - beta_L*du

    # --- variantes nommées (ablations A-J du rapport 02) ---
    credit: bool = True                  # B : False = sans marché
    # Objectif de l'emprunteuse (mini-protocole X1, post-M3) :
    # "wealth" : cible K*(r+delta) — richesse soutenable (baseline M3) ;
    # "income" : cible K*(r) — maximisation myope du revenu net (la
    # dépréciation érode la richesse, pas le revenu). Avec le taux en
    # moyenne géométrique, K*(r) = sqrt(K_l * K_b) : égalisation des
    # capitaux par le crédit, levier et service de dette accrus.
    objective: str = "wealth"            # "wealth" | "income"
    loan_target: str = "K"               # "K" (productif) | "L" (ablation C)
    claim_loss: str = "on"               # "on" | "compensated" (ablation D)
    flow_loss: str = "on"                # "on" | "annuity" (ablation E)
    # "assortative" | "random" (F pré-enregistrée) | "random_lender" (F''
    # EXPLORATOIRE post-hoc : F éteint le marché — volume ÷6,5 — au lieu d'en
    # randomiser la topologie ; F'' garde l'emprunteuse assortative et tire la
    # prêteuse au hasard parmi les faisables, pour casser les hubs créanciers
    # à volume comparable. Documenté rapport 05.)
    market_selection: str = "assortative"
    shock_rho_macro: float = 0.0         # part macro de la variance (G1)
    shock_rho_sector: float = 0.0        # part sectorielle de la variance (G2)
    n_sectors: int = 5                   # nombre de secteurs (G2)
    n_init: int = 0                      # cohorte initiale à t=0 (ablation I)
    rate_rule: str = "geom"              # "geom" | "arith" (M2 : geom constitutif)
    fail_lender_loans: str = "transfer"  # "transfer" | "cancel"
    fail_residual: str = "prorata"       # "prorata" | "destroy"
    merge_pairs: bool = True             # fusion par paire (correctif M2 validé)

    # --- technique ---
    seed: int = 0
    T: int = 2000
    tol_nw: float = 1e-9
    q_min: float = 1e-9
    pop_max: int = 30000        # garde-fou d'ARRÊT — ne borne pas la dynamique
    w_clamp: float = 1e-12      # |x| < w_clamp arrondi à 0 (erreur flottante)

    def __post_init__(self):
        assert self.L0 >= 0.0 and self.K0 > 0.0
        assert self.L0 + self.K0 > self.d0 >= 0.0, "NW de naissance doit être > 0"
        assert 0.0 <= self.s <= 1.0 and 0.0 <= self.c < 1.0
        assert self.k >= 2 and self.delta > 0 and self.sigma >= 0
        assert self.beta_L >= 0.0
        assert self.loan_target in ("K", "L")
        assert self.claim_loss in ("on", "compensated")
        assert self.flow_loss in ("on", "annuity")
        assert self.market_selection in ("assortative", "random", "random_lender")
        assert 0.0 <= self.shock_rho_macro + self.shock_rho_sector <= 1.0
        assert self.rate_rule in ("geom", "arith")
        assert self.objective in ("wealth", "income")
        assert self.fail_lender_loans in ("transfer", "cancel")
        assert self.fail_residual in ("prorata", "destroy")

    @property
    def w0(self) -> float:
        return self.L0 + self.K0

    @property
    def eps0(self) -> float:
        return self.w0 - self.d0

    def to_dict(self) -> dict:
        return asdict(self)
