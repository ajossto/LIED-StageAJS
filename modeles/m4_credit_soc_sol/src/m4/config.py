"""Configuration M4 sans dette abstraite ``d0``.

Le candidat par défaut combine chocs sectoriels, objectif de revenu myope et
crédit productif. Les quelques commutateurs non nuls seulement en expérience
reproduisent les hypothèses négatives consignées dans ``NOTES.md`` ; ils restent
désactivés dans le mécanisme retenu.
"""
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class M4Config:
    # --- paramètres hérités de M2 (rapport 02, tableau des paramètres) ---
    alpha: float = 1.0          # convention d'unité de flux (ne pas régler)
    delta: float = 0.05         # dépréciation du capital réel = unité de temps
    lam: float = 10.0           # intensité Poisson des naissances
    k: int = 6                  # taille d'échantillon du marché (connectivité)
    sigma: float = 0.25         # écart-type total du choc multiplicatif

    # --- bilan réel et flux ---
    L0: float = 5.0             # dotation liquide de naissance
    K0: float = 25.0            # dotation en capital de naissance
    s: float = 0.75             # part retenue de la production (K += s*P)
    c: float = 0.10             # consommation de la liquidité (L *= 1-c)
    beta_L: float = 1.0         # tampon de service : prêtable = L - beta_L*du
    # Hypothèses expérimentales infirmées, OFF par défaut (traçabilité des runs).
    adaptive_credit: bool = False
    credit_drive: float = 0.002    # hausse de l'appétit par pas
    credit_relax: float = 5.0      # baisse par décès propagé / population
    credit_appetite_max: float = 3.0
    portfolio_limit: int = 0        # 0=illimité ; sinon contreparties/prêteuse
    capital_ratio: float = 0.0      # coussin NW/dette minimal ; 0=désactivé

    # --- variantes nommées (ablations A-J du rapport 02) ---
    credit: bool = True                  # B : False = sans marché
    # Objectif de l'emprunteuse (mini-protocole X1 de M3, baseline ici) :
    # "wealth" : cible K*(r+delta) — richesse soutenable (baseline M3) ;
    # "income" : cible K*(r) — maximisation myope du revenu net (la
    # dépréciation érode la richesse, pas le revenu). Avec le taux en
    # moyenne géométrique, K*(r) = sqrt(K_l * K_b) : égalisation des
    # capitaux par le crédit, levier et service de dette accrus.
    objective: str = "income"            # "wealth" | "income" — M4 : "income"
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
    # M4 : chocs sectoriels fortement corrélés (variante G2b de M3, celle qui
    # produisait les premières avalanches non triviales, max 36-72).
    shock_rho_sector: float = 0.8        # part sectorielle de la variance (G2)
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
        assert self.L0 + self.K0 > 0.0
        assert 0.0 <= self.s <= 1.0 and 0.0 <= self.c < 1.0
        assert self.k >= 2 and self.delta > 0 and self.sigma >= 0
        assert self.beta_L >= 0.0
        assert self.credit_drive >= 0.0 and self.credit_relax >= 0.0
        assert self.credit_appetite_max >= 1.0
        assert self.portfolio_limit >= 0
        assert 0.0 <= self.capital_ratio < 1.0
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

    def to_dict(self) -> dict:
        return asdict(self)
