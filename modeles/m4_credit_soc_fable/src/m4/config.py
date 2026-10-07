"""Configuration du modèle M4 (moteur fusionné, refonte du 2026-07-14).

Refonte par rapport au fork M3 (archive : archive/m4_lk_pre_refonte/) :
- UNE variable d'état réelle par entité : le capital productif K (fusion
  L/K du brief — les intérêts se paient depuis K, les prêts transfèrent K) ;
  les champs L0, s, c, beta_L, loan_target disparaissent avec L.
- d0 est RETIRÉ DU CODE (objectif explicite du brief) : la valeur nette est
  NW = K + créances - dettes, le plancher d'absorption est purement
  contractuel (une entité sans dette ne meurt jamais — c'est le régime H
  de M3, validé ici en sweep B avant la refonte).
- la règle de faillite par défaut est la PLUS SIMPLE : contrats de la morte
  annulés (« cancel »), actifs résiduels détruits (« destroy ») — c'est
  aussi la seule combinaison qui produit de vraies cascades propagées
  (racines/taille ≈ 0,45, profondeur ≥ 7 ; NOTES.md 2026-07-14). Les
  variantes M3 (« transfer », « prorata ») restent disponibles en ablation.
- le taux est en moyenne géométrique, constitutif (M2) — plus d'option.
- merge_pairs est constitutif (correctif M2 validé) — plus d'option.
- naissance par emprunt (birth_loan) : la dotation K0 peut être financée
  par une prêteuse réelle (piste « dette de subsistance » de M3), avec
  apport en fonds propres birth_equity*K0 et repli fonds propres si aucune
  prêteuse faisable.
"""
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class M4Config:
    # --- noyau hérité de M2 ---
    alpha: float = 1.0          # convention d'unité de flux (ne pas régler)
    delta: float = 0.05         # dépréciation du capital réel = unité de temps
    lam: float = 10.0           # intensité Poisson des naissances
    k: int = 3                  # taille d'échantillon du marché (tri)
    sigma: float = 0.25         # écart-type total du choc multiplicatif
    K0: float = 25.0            # dotation en capital de naissance

    # --- marché ---
    credit: bool = True                  # False = ablation sans marché
    # "income" : cible commune K*(r) = (alpha/2r)^2 = sqrt(K_l*K_b) —
    # maximisation myope du revenu (X1 de M3, baseline M4) ;
    # "wealth" : cible K*(r+delta) — richesse soutenable (contrôle bas levier)
    objective: str = "income"
    # dénominateur du nombre de rounds par pas (n // rounds_div) ; 0 = k.
    # C'est le levier du rapport de branchement des cascades b (dose-réponse
    # mesurée, NOTES 2026-07-14) : n/6 → b=0,14 ; n/3 → 0,20 ; n/2 → 0,24 ;
    # n → 0,30 ; 2n → 0,34 (la distribution se dégrade au-delà de n).
    # Défaut 1 = UN round par tête et par pas : b s'y épingle à 0,300
    # (indépendant de N et du seed) et le cutoff des avalanches est au-delà
    # de la taille du système à toutes les tailles testées.
    rounds_div: int = 1                  # 0 = utiliser k

    # --- naissances ---
    birth_loan: bool = False             # dotation financée par une prêteuse
    birth_equity: float = 0.2            # part en fonds propres (si birth_loan)
    birth_lender: str = "random"         # "random" | "rich" (choix prêteuse)
    n_init: int = 0                      # cohorte initiale à t=1 (ablation I)

    # --- structure du choc (comparaisons G1/G2 de M3) ---
    shock_rho_macro: float = 0.0         # part macro de la variance
    shock_rho_sector: float = 0.0        # part sectorielle de la variance
    n_sectors: int = 5

    # --- règle de faillite (le mécanisme SOC candidat, NOTES 2026-07-14) ---
    fail_lender_loans: str = "cancel"    # "cancel" | "transfer" (règle M3)
    fail_residual: str = "destroy"       # "destroy" | "prorata" (règle M3)

    # --- technique ---
    seed: int = 0
    T: int = 2000
    tol_nw: float = 1e-9
    q_min: float = 1e-9
    pop_max: int = 30000        # garde-fou d'ARRÊT — ne borne pas la dynamique
    w_clamp: float = 1e-12      # |x| < w_clamp arrondi à 0 (erreur flottante)

    def __post_init__(self):
        assert self.K0 > 0.0
        assert self.k >= 2 and self.delta > 0 and self.sigma >= 0
        assert self.rounds_div >= 0
        assert self.objective in ("wealth", "income")
        assert 0.0 <= self.birth_equity <= 1.0
        assert self.birth_lender in ("random", "rich")
        assert 0.0 <= self.shock_rho_macro + self.shock_rho_sector <= 1.0
        assert self.fail_lender_loans in ("cancel", "transfer")
        assert self.fail_residual in ("destroy", "prorata")

    @property
    def effective_rounds_div(self) -> int:
        return self.rounds_div if self.rounds_div > 0 else self.k

    def to_dict(self) -> dict:
        return asdict(self)
