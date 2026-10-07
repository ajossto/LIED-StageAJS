"""Ablations et variantes de convention (spec §7.7, lecture critique §5) :

- proto_e7c  : fail_lender_loans='cancel' — la règle du prototype qui a produit
               les résultats E7c du rapport (test de réplication) ;
- destroy    : fail_residual='destroy' — contrôle anti-condensation (la queue
               survit-elle sans le transfert du résiduel aux grosses ?) ;
- nocredit   : credit=False — modèle nul GBM + extraction + d0 (ce que le
               crédit ajoute réellement) ;
- arith      : rate_rule='arith' — sensibilité à la convention de taux ;
- lam30      : extensivité N* ~ lambda (X5).
"""
from exp_common import M2Config, run_one

VARIANTS = {
    "proto_e7c": dict(fail_lender_loans="cancel"),
    "destroy": dict(fail_residual="destroy"),
    "nocredit": dict(credit=False),
    "arith": dict(rate_rule="arith"),
    "lam30": dict(lam=30.0),
    # ajoutée après coup (validation du correctif de prolifération) : règle
    # M2 (transfer) + fusion par paire — carnet borné, distribution inchangée
    "merge": dict(merge_pairs=True),
}

if __name__ == "__main__":
    for name, kw in VARIANTS.items():
        for seed in (0, 1):
            cfg = M2Config(seed=seed, T=2000, **kw)
            run_one(cfg, f"abl_{name}_s{seed}", dense_from=1500)
