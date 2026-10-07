"""Runs longs (T=6000) pour départager Kesten stationnaire vs transitoire
log-normal : si l'exposant de queue du modèle nul (nocredit) dérive avec T
alors que celui du modèle avec crédit (variante cancel, carnet stationnaire)
se stabilise, le crédit stabilise la queue (H2 partiellement soutenue) ;
si les deux dérivent pareil, la « queue de Pareto stable » de E7c était un
transitoire commun."""
from exp_common import M2Config, run_one

if __name__ == "__main__":
    run_one(M2Config(seed=0, T=6000, credit=False), "long_nocredit_s0")
    run_one(M2Config(seed=0, T=6000, fail_lender_loans="cancel"), "long_cancel_s0")
    run_one(M2Config(seed=1, T=6000, credit=False), "long_nocredit_s1")
    run_one(M2Config(seed=1, T=6000, fail_lender_loans="cancel"), "long_cancel_s1")
