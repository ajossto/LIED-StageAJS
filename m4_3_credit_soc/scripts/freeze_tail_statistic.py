"""Choix et gel de la statistique de queue (PROMPT_M4_3_FINAL.md §2), AVANT
le début de la cartographie D1. Critère du prompt : reproductibilité
inter-graines (écart-type le plus faible à paramètres fixés), PAS la
valeur elle-même.

Réutilise `interest_income.fit_income_distribution` (donc `families.py` —
ladder de corps par AIC/BIC — et `tail_test.py` — MLE Pareto à seuil
scanné) SANS RIEN RÉÉCRIRE (§5/§8). Fenêtre d'analyse positionnée PAR RUN
sur son propre temps de convergence mesuré (`relaxation_pilot.py`), pas une
valeur unique partagée entre graines (§3 — le temps de relaxation lui-même
varie sensiblement entre graines à paramètres fixes, JOURNAL.md §10)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import interest_income  # noqa: E402
from renewal_relaxation_all_runs import persistence_curve, fit_fopdt  # noqa: E402


def own_t_converge(run_dir: Path, field: str = "int_in") -> float:
    snaps = interest_income.load_all_entity_snapshots(run_dir)
    t0 = snaps[0][0]
    t, y = persistence_curve(snaps, field)
    fit = fit_fopdt(t, y, t0)
    if not fit["ok"]:
        raise RuntimeError(f"FOPDT n'a pas convergé pour {run_dir} (champ {field})")
    return t0 + fit["t_delay"] + 3 * fit["tau"]


def pooled_post_convergence_int_in(run_dir: Path, t_converge: float) -> np.ndarray:
    snaps = interest_income.load_all_entity_snapshots(run_dir, t_min=int(np.ceil(t_converge)))
    pooled = np.concatenate([snap["int_in"] for _t, snap in snaps]) if snaps else np.array([])
    return pooled


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: freeze_tail_statistic.py <run_dir> [<run_dir> ...]")
        sys.exit(1)

    run_dirs = [Path(p) for p in sys.argv[1:]]
    alphas = []
    dagum_c = []
    print(f"{'run':>40} {'t_conv':>8} {'n_pooled':>9} {'meilleur (AIC)':>16} "
          f"{'alpha_tail':>10} {'x_min':>10} {'n_tail':>8}")
    for run_dir in run_dirs:
        t_conv = own_t_converge(run_dir)
        pooled = pooled_post_convergence_int_in(run_dir, t_conv)
        fit = interest_income.fit_income_distribution(pooled)
        if not fit.get("identifiable"):
            print(f"{str(run_dir):>40} {t_conv:>8.0f} {len(pooled):>9}   NON IDENTIFIABLE "
                  f"(n_positive={fit.get('n_positive')})")
            continue
        best_per_k = fit.get("body_best_per_k", {})
        # argmin AIC sur TOUT le ladder (pas le k le plus parcimonieux) —
        # sert seulement à l'affichage, pas à choisir la statistique gelée.
        aic_best = min(best_per_k.values(), key=lambda e: e.get("aic", float("inf"))) \
            if best_per_k else None
        aic_best_name = aic_best["name"] if aic_best else "?"
        tail = fit.get("tail_powerlaw") or {}
        alpha = tail.get("alpha_density")
        x_min = tail.get("x_min")
        n_tail = tail.get("n_tail")
        print(f"{str(run_dir):>40} {t_conv:>8.0f} {len(pooled):>9} {aic_best_name:>16} "
              f"{alpha:>10.4f} {x_min:>10.3g} {n_tail:>8}")
        if alpha is not None:
            alphas.append(alpha)

        print(f"  ladder complet (k -> famille, AIC) :")
        for k in sorted(best_per_k):
            entry = best_per_k[k]
            print(f"    k={k}: {entry['name']:>16}  AIC={entry.get('aic', float('nan')):.1f}")

        # Candidat B : dagum_3p (Burr Type III, scipy 'burr') — analogue
        # continu d'une loi de puissance avec coude/coupure sur la queue.
        # pdf(x,c,d) = c*d*x^(-c-1)*(1+x^-c)^(-d-1) -> à x grand, le facteur
        # (1+x^-c)^(-d-1) -> 1, donc survie ~ x^-c : l'INDICE DE QUEUE EST
        # c SEUL (pas c*d — c*d est l'exposant de la queue INFÉRIEURE,
        # x->0 ; c*d≈0,9 impliquerait une moyenne infinie, incompatible
        # avec un revenu borné par la production totale d'une économie
        # finie — erreur trouvée et corrigée le 2026-08-07, JOURNAL.md
        # §11bis). `dist.fit(pos, floc=0)` renvoie (c, d, loc, scale) —
        # 4 valeurs, pas 3 ; loc est pinné à 0, PAS le scale.
        ladder = fit.get("body_ladder") or {}
        dagum = ladder.get("dagum_3p")
        if dagum and dagum.get("params"):
            c, d, loc, scale = dagum["params"][:4]
            print(f"  dagum_3p (candidat coude) : c={c:.4f} (indice de queue supérieure) "
                  f"d={d:.4f}  loc={loc:.3g}  scale={scale:.3g}")
            dagum_c.append(c)

    if len(alphas) > 1:
        alphas_arr = np.array(alphas)
        print(f"\nCandidat A — alpha_density (MLE Pareto, seuil scanné) sur "
              f"{len(alphas)} graines : moyenne={alphas_arr.mean():.4f}  "
              f"std={alphas_arr.std(ddof=1):.4f}  "
              f"cv={alphas_arr.std(ddof=1) / alphas_arr.mean():.4f}")
    if len(dagum_c) > 1:
        c_arr = np.array(dagum_c)
        print(f"Candidat B — dagum_3p c (indice de queue supérieure) sur "
              f"{len(dagum_c)} graines : moyenne={c_arr.mean():.4f}  "
              f"std={c_arr.std(ddof=1):.4f}  cv={c_arr.std(ddof=1) / c_arr.mean():.4f}")
        if len(alphas) > 1:
            cv_a = alphas_arr.std(ddof=1) / alphas_arr.mean()
            cv_b = c_arr.std(ddof=1) / c_arr.mean()
            winner = "A (alpha_density, Pareto pur)" if cv_a < cv_b else "B (dagum c, avec coude)"
            print(f"\n=> Statistique la plus reproductible (CV le plus faible) : {winner}")


if __name__ == "__main__":
    main()
