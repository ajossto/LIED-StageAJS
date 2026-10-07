"""Facteur d'admissibilité continu pour le critère 1 (remplace la
comparaison ponctuelle seuil vs seuil*2 et le pass/fail admissible/non
admissible -- discussion utilisateur du 2026-08-06).

Combine DEUX facteurs demandés explicitement par l'utilisateur :

1. **Incertitude liée à la diminution du nombre de points** : à seuil*x,
   n_tail chute vite (mediane 113 -> 17 seulement pour x=2, cf.
   probe_criterion1_2x.py) -- une "instabilite" a faible n peut n'etre
   que du bruit d'echantillonnage. On ne compare donc pas |Δα| a une
   bande fixe (20%), mais a l'ecart-type BOOTSTRAP de Δα lui-meme, qui
   tient compte de la DEPENDANCE entre les deux estimations (la queue a
   seuil*x est un SOUS-ENSEMBLE de la queue a seuil -- sommer des
   variances analytiques serait faux ; le bootstrap gere ca nativement).

2. **Intervalle sur lequel le seuil peut être choisi** : un run où l'on
   ne peut tester que jusqu'à x_max=1.05 avant de manquer de points
   "a l'air stable" trivialement (on n'a presque rien teste), pas parce
   que la queue est vraiment une loi de puissance. Un terme de
   COUVERTURE explicite penalise ces cas, independamment de la platitude
   mesuree sur le petit intervalle disponible.

A = couverture(x_max) * platitude(1..x_max), dans [0,1]. Litterature
apparentee : Hill plot stability / plateau diagnostics (Drees-de Haan-
Resnick 2000 ; Danielsson-de Haan-Peng-de Vries 2001, MSE-optimal
threshold via bootstrap ; Voitalov-van der Hoorn-Kitsak-Papadopoulos-
Krioukov 2019, intervalle de stabilite explicite -- voir discussion
utilisateur/assistant, pas une citation verifiee a la ligne pres).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import tail_test  # noqa: E402

MIN_N = 80
X_TARGET = 2.0  # facteur cible pour couverture=1 (l'ask original "seuil*2")
N_GRID = 12
N_BOOT = 300


def _hill_alpha(tail: np.ndarray, x_min: float) -> float | None:
    n = len(tail)
    if n < MIN_N:
        return None
    s = np.sum(np.log(tail / x_min))
    if s <= 0:
        return None
    return 1.0 + n / s


def admissibility_factor(positive: np.ndarray, seuil: float, rng: np.random.Generator) -> dict:
    """positive : valeurs > 0 du snapshot. seuil : x_min deja selectionne
    (KS) sur les donnees ORIGINALES -- sert a definir la grille de
    multiplicateurs x et x_max (diagnostic de couverture, sur les
    donnees reelles, pas sur les tirages).

    A CHAQUE tirage bootstrap, on RE-SCANNE le seuil KS-optimal (au lieu
    de le garder fixe) -- preference explicite de l'utilisateur
    (2026-08-06) : ca incorpore aussi la variabilite du CHOIX de seuil,
    pas seulement de alpha a seuil fixe, et c'est plus robuste a un
    "coude" structurel connu juste apres la cassure (l'utilisateur
    signale que toutes ses simulations en ont un) -- si un tirage
    resample le seuil optimal loin du coude, ca se voit dans la
    dispersion plutot que d'etre silencieusement absorbe dans un biais
    fixe. Chaque tirage teste ensuite SA PROPRE grille de multiplicateurs
    x*seuil_b (pas x*seuil_original) : on demande "en repetant toute la
    procedure sur un tirage, retrouve-t-on encore un plateau au-dela du
    point qu'elle choisirait elle-meme ?", pas seulement "alpha a seuil
    fixe est-il stable".
    """
    tail0 = positive[positive >= seuil]
    n0 = len(tail0)
    alpha0 = _hill_alpha(tail0, seuil)
    if alpha0 is None:
        return {"ok": False, "reason": "seuil lui-meme non admissible"}

    # x_max : le plus grand facteur x tel que n_tail(x*seuil) >= MIN_N
    # (diagnostic de couverture sur les donnees REELLES, independant du bootstrap)
    sorted_pos = np.sort(positive)[::-1]
    if len(sorted_pos) < MIN_N:
        x_max = 1.0
    else:
        x_min_reachable = sorted_pos[MIN_N - 1]  # valeur du MIN_N-ieme plus grand point
        x_max = max(1.0, x_min_reachable / seuil)

    if x_max <= 1.0 + 1e-9:
        return {"ok": True, "x_max": float(x_max), "coverage": 0.0, "flatness": None,
                "A": 0.0, "note": "aucune marge au-dela du seuil primaire"}

    grid_x = np.geomspace(1.0, x_max, N_GRID)

    # bootstrap : B tirages, KS RE-SCANNE a chaque tirage, grille de
    # multiplicateurs appliquee au seuil PROPRE a chaque tirage
    n_pos = len(positive)
    boot_alpha = np.full((N_BOOT, N_GRID), np.nan)
    boot_seuil = np.full(N_BOOT, np.nan)
    for b in range(N_BOOT):
        resample = rng.choice(positive, size=n_pos, replace=True)
        best_b = tail_test.fit_powerlaw_xmin(resample, min_tail=MIN_N)
        if best_b is None:
            continue
        seuil_b = best_b["x_min"]
        boot_seuil[b] = seuil_b
        boot_alpha[b, 0] = best_b["alpha"]
        for i, x in enumerate(grid_x[1:], start=1):
            tail_b = resample[resample >= x * seuil_b]
            a = _hill_alpha(tail_b, x * seuil_b)
            boot_alpha[b, i] = a if a is not None else np.nan

    alpha_orig = [alpha0]  # x=1 exactement : reutilise alpha0, evite tout ecart
    # de flottant entre grid_x[0] (geomspace) et seuil qui ferait perdre les
    # points de bord et renvoyer None la ou alpha0 est deja valide
    for x in grid_x[1:]:
        a = _hill_alpha(positive[positive >= x * seuil], x * seuil)
        alpha_orig.append(a if a is not None else np.nan)
    alpha_orig = np.array(alpha_orig, dtype=float)
    delta_orig = alpha_orig - alpha_orig[0]  # relatif au seuil lui-meme (x=1)
    delta_boot = boot_alpha - boot_alpha[:, [0]]
    sd_boot = np.nanstd(delta_boot, axis=0, ddof=1)

    with np.errstate(invalid="ignore", divide="ignore"):
        z = np.abs(delta_orig) / sd_boot
    f = np.exp(-0.5 * z**2)
    valid = np.isfinite(f)
    if valid.sum() < 2:
        flatness = None
        A = 0.0
    else:
        log_x = np.log(grid_x[valid])
        flatness = float(np.trapezoid(f[valid], log_x) / (log_x[-1] - log_x[0]))
        coverage = float(min(1.0, np.log(x_max) / np.log(X_TARGET)))
        A = coverage * flatness

    return {
        "ok": True, "x_max": float(x_max),
        "coverage": float(min(1.0, np.log(x_max) / np.log(X_TARGET))),
        "flatness": flatness, "A": A,
        "n0": n0, "alpha0": float(alpha0),
        "grid_x": grid_x.tolist(), "z": z.tolist(), "f": f.tolist(),
        "boot_seuil": boot_seuil.tolist(), "boot_alpha": boot_alpha.tolist(),
    }


if __name__ == "__main__":
    import interest_income

    RUN_DIR = ROOT / "results" / "campaign" / "baseline" / "seed0"
    snaps = interest_income.load_all_entity_snapshots(RUN_DIR, t_min=750, t_max=3000)
    snap = dict(snaps)[2225]
    p0, positive = interest_income.zero_mass_and_positive(snap["int_in"])
    best = tail_test.fit_powerlaw_xmin(positive, min_tail=MIN_N)
    print(f"seuil={best['x_min']:.2f} alpha0={best['alpha']:.3f} n_tail={best['n_tail']}")

    rng = np.random.default_rng(0)
    result = admissibility_factor(positive, best["x_min"], rng)
    print(f"x_max={result['x_max']:.2f}  coverage={result['coverage']:.3f}  "
          f"flatness={result['flatness']:.3f}  A={result['A']:.3f}")
    print("grille x :", [f"{x:.2f}" for x in result["grid_x"]])
    print("z-scores :", [f"{z:.2f}" for z in result["z"]])
