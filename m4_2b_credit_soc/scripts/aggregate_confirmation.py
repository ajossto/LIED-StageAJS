"""Applique les critères de confirmation pré-enregistrés (report/
protocole.md, repris et expliqués en clair dans report/rapport_interim.md
§4) aux 45 runs de la campagne de confirmation (9 cellules × 5 graines
disjointes 10-14, results/confirmation/). Écrit deux tables :
- results/confirmation/confirmation_runs.csv (un run = une ligne, mêmes
  colonnes qu'exploration_summary.csv, réutilise load_run) ;
- results/confirmation/confirmation_verdicts.csv (une cellule = une
  ligne : verdict par critère + verdict global objectif A).

Opérationnalisations décidées ICI, PAS dans le protocole (à documenter
comme telles dans le rapport final, pas comme des règles héritées) :

- Critères 1/2/4 sont naturellement des scalaires PAR GRAINE (moyenne ou
  fraction sur les instantanés de cette graine). "Sur au moins 3 graines"
  est appliqué à la CONJONCTION des critères 1+2+3+4 : une graine
  "réussit" seulement si les 4 tiennent SIMULTANÉMENT pour elle, et la
  cellule passe si ≥3 des 5 graines réussissent ainsi. Lecture plus
  stricte qu'exiger seulement ≥3 graines par critère indépendamment, mais
  plus fidèle au texte ("si, sur au moins 3 graines... 1. ... 2. ... 3.
  ... 4. ...").
- Critère 1 par graine : majorité des instantanés de CETTE graine
  stables au seuil (frac_under_20pct ≥ 0,5) — pas la moyenne du écart.
- Critère 3 (signe/ordre de grandeur cohérent) : direction de référence
  = signe de (moyenne exploration de la cellule − moyenne exploration de
  la baseline) sur alpha_density_mean (3 graines d'exploration, jamais
  celles de confirmation — pas de fuite). Une graine de confirmation
  "réussit" si le signe de (sa valeur − moyenne exploration baseline)
  correspond à cette direction de référence.
- Critère 4 par graine : majorité des instantanés favorisant la loi de
  puissance À LA FOIS contre l'exponentielle ET contre la lognormale.
- Critère 5 (l'effet ne se réduit pas à Gini ou deg_out seul) : PAS de
  test automatique dans le protocole. Ici, calculé au niveau CELLULE
  (pas par graine) : Δgini = moyenne confirmation − moyenne exploration
  baseline (idem Δshare_deg_out, Δalpha_density). "Co-monotone" = le
  signe de Δalpha_density est cohérent avec une explication par la seule
  hausse/baisse d'inégalité ou de deg_out (Δalpha et Δgini de même signe,
  ou Δalpha et Δshare_deg_out de même signe) sur les DEUX à la fois -> si
  co-monotone sur les deux, critère 5 ÉCHOUE (l'effet est explicable par
  Gini+deg_out seuls) ; sinon, critère 5 PASSE. Reporté comme un
  diagnostic à lire, pas une vérité automatique.

Objectif B (indépendance de taille des avalanches) : les 3 critères du
protocole exigent de comparer les tailles de population les PLUS PETITES
et les PLUS GRANDES observées "à paramètres autrement identiques" (même
λ, même tout sauf la taille). AUCUNE des 9 cellules de confirmation ne
fait varier la taille du système à paramètres autrement identiques (λ=30
partout) : K0_1 vs K0_2000 changent la taille via K0 lui-même (facteur
2000, Gini ×8, plancher de renouvellement 0,000->0,796, share_from_mean_rq
0,24 d'écart) - ce n'est PAS "paramètres autrement identiques", et
utiliser cette paire comme axe de taille serait une comparaison non
interprétable. CE SCRIPT NE CALCULE DONC PAS de verdict Objectif B : la
seule évidence de taille du programme entier est le balayage λ du pilote
(resume.md), déjà conclu "aucun exposant indépendant de la taille établi
sur cette plage". Le script reporte seulement, par cellule, l'écart de
population final ENTRE LES 5 GRAINES (bruit stochastique à paramètres
strictement identiques) comme repère de dispersion - explicitement
signalé comme trop étroit pour trancher l'indépendance de taille.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from aggregate_exploration import CAMPAIGN_DIR, load_run  # noqa: E402

CONFIRM_DIR = ROOT / "results" / "confirmation"
CONFIRM_SEEDS = (10, 11, 12, 13, 14)

RUN_FIELDS = [
    "label", "seed", "T", "gamma", "delta", "sigma", "K0", "lam", "rho",
    "eta_beta", "eta_n_ref", "target_rule",
    "population_final", "alpha_density_mean",
    "threshold_reldiff_frac_under_20pct", "interest_n_tail_mean",
    "frac_snapshots_favor_powerlaw_vs_exp", "frac_snapshots_favor_powerlaw_vs_lognormal",
    "tau_hat", "branching_ratio", "gini_K_mean",
    "share_from_deg_out_mean", "share_from_mean_rq_mean",
]

VERDICT_FIELDS = [
    "label", "n_seeds",
    "ref_direction_alpha", "n_seeds_crit1", "n_seeds_crit2", "n_seeds_crit3", "n_seeds_crit4",
    "n_seeds_joint_1234", "objA_criteria_1_to_4_pass",
    "delta_alpha_vs_baseline", "delta_gini_vs_baseline", "delta_share_deg_out_vs_baseline",
    "crit5_co_monotone_with_gini", "crit5_co_monotone_with_deg_out", "crit5_pass",
    "objA_robuste",
    "pop_min", "pop_max", "pop_spread_ratio",
]


def _sign(x: float) -> int:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def _mean(xs: list[float]) -> float | None:
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def load_confirmation_runs() -> list[dict]:
    rows = []
    for p in sorted(CONFIRM_DIR.glob("*/seed*/analysis.json")):
        row = load_run(p)
        if row is not None and row["seed"] in CONFIRM_SEEDS:
            rows.append(row)
    return rows


def load_exploration_baseline() -> dict:
    rows = []
    for p in sorted(CAMPAIGN_DIR.glob("baseline/seed*/analysis.json")):
        row = load_run(p)
        if row is not None:
            rows.append(row)
    return {
        "alpha_density_mean": _mean([r["alpha_density_mean"] for r in rows]),
        "gini_K_mean": _mean([r["gini_K_mean"] for r in rows]),
        "share_from_deg_out_mean": _mean([r["share_from_deg_out_mean"] for r in rows]),
    }


def load_exploration_cell_mean(label: str) -> dict:
    """Moyenne exploration (3 graines 0-2) pour une cellule, utilisee comme
    reference de direction (critere 3) - jamais les graines de confirmation
    elles-memes, pour ne pas fuiter le test dans sa propre reference."""
    rows = []
    for p in sorted(CAMPAIGN_DIR.glob(f"{label}/seed*/analysis.json")):
        row = load_run(p)
        if row is not None and row["seed"] in (0, 1, 2):
            rows.append(row)
    return {
        "alpha_density_mean": _mean([r["alpha_density_mean"] for r in rows]),
    }


def compute_verdicts(runs: list[dict], baseline: dict) -> list[dict]:
    by_label: dict[str, list[dict]] = {}
    for r in runs:
        by_label.setdefault(r["label"], []).append(r)

    verdicts = []
    for label, rs in sorted(by_label.items()):
        rs = sorted(rs, key=lambda r: r["seed"])
        expl_cell = load_exploration_cell_mean(label)
        ref_alpha_expl = expl_cell["alpha_density_mean"]
        ref_direction = None
        if ref_alpha_expl is not None and baseline["alpha_density_mean"] is not None:
            ref_direction = _sign(ref_alpha_expl - baseline["alpha_density_mean"])

        n_c1 = n_c2 = n_c3 = n_c4 = n_joint = 0
        for r in rs:
            c1 = (r["threshold_reldiff_frac_under_20pct"] or 0) >= 0.5
            c2 = (r["interest_n_tail_mean"] or 0) >= 100
            c3 = False
            if ref_direction is not None and r["alpha_density_mean"] is not None and baseline["alpha_density_mean"] is not None:
                c3 = _sign(r["alpha_density_mean"] - baseline["alpha_density_mean"]) == ref_direction
            c4 = (r["frac_snapshots_favor_powerlaw_vs_exp"] or 0) >= 0.5 and \
                 (r["frac_snapshots_favor_powerlaw_vs_lognormal"] or 0) >= 0.5
            n_c1 += c1
            n_c2 += c2
            n_c3 += c3
            n_c4 += c4
            n_joint += c1 and c2 and c3 and c4

        objA_1to4 = n_joint >= 3

        cell_alpha = _mean([r["alpha_density_mean"] for r in rs])
        cell_gini = _mean([r["gini_K_mean"] for r in rs])
        cell_deg_out = _mean([r["share_from_deg_out_mean"] for r in rs])
        d_alpha = (cell_alpha - baseline["alpha_density_mean"]) if cell_alpha is not None and baseline["alpha_density_mean"] is not None else None
        d_gini = (cell_gini - baseline["gini_K_mean"]) if cell_gini is not None and baseline["gini_K_mean"] is not None else None
        d_deg = (cell_deg_out - baseline["share_from_deg_out_mean"]) if cell_deg_out is not None and baseline["share_from_deg_out_mean"] is not None else None

        co_gini = (d_alpha is not None and d_gini is not None and _sign(d_alpha) == _sign(d_gini) and d_alpha != 0)
        co_deg = (d_alpha is not None and d_deg is not None and _sign(d_alpha) == _sign(d_deg) and d_alpha != 0)
        crit5_pass = not (co_gini and co_deg)

        pops = [r["population_final"] for r in rs if r["population_final"] is not None]
        pop_min, pop_max = (min(pops), max(pops)) if pops else (None, None)

        verdicts.append({
            "label": label, "n_seeds": len(rs),
            "ref_direction_alpha": ref_direction,
            "n_seeds_crit1": n_c1, "n_seeds_crit2": n_c2,
            "n_seeds_crit3": n_c3, "n_seeds_crit4": n_c4,
            "n_seeds_joint_1234": n_joint, "objA_criteria_1_to_4_pass": objA_1to4,
            "delta_alpha_vs_baseline": d_alpha, "delta_gini_vs_baseline": d_gini,
            "delta_share_deg_out_vs_baseline": d_deg,
            "crit5_co_monotone_with_gini": co_gini, "crit5_co_monotone_with_deg_out": co_deg,
            "crit5_pass": crit5_pass,
            "objA_robuste": objA_1to4 and crit5_pass,
            "pop_min": pop_min, "pop_max": pop_max,
            "pop_spread_ratio": (pop_max / pop_min) if pop_min else None,
        })
    return verdicts


def main() -> None:
    runs = load_confirmation_runs()
    baseline = load_exploration_baseline()
    print(f"Baseline exploration (3 graines) : alpha={baseline['alpha_density_mean']:.3f} "
          f"gini={baseline['gini_K_mean']:.4f} share_deg_out={baseline['share_from_deg_out_mean']:.3f}")

    runs_path = CONFIRM_DIR / "confirmation_runs.csv"
    with open(runs_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RUN_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for r in runs:
            writer.writerow(r)
    print(f"{len(runs)} runs -> {runs_path}")

    verdicts = compute_verdicts(runs, baseline)
    verdicts_path = CONFIRM_DIR / "confirmation_verdicts.csv"
    with open(verdicts_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=VERDICT_FIELDS)
        writer.writeheader()
        for v in verdicts:
            writer.writerow(v)
    print(f"{len(verdicts)} cellules -> {verdicts_path}")

    print(f"\n{'label':22}{'j1234':>7}{'objA1-4':>9}{'crit5':>7}{'ROBUSTE':>9}{'d_alpha':>9}{'d_gini':>9}{'d_dego':>8}{'pop_ratio':>10}")
    for v in verdicts:
        print(f"{v['label']:22}{v['n_seeds_joint_1234']:>3}/5  {str(v['objA_criteria_1_to_4_pass']):>7}"
              f"{str(v['crit5_pass']):>9}{str(v['objA_robuste']):>9}"
              f"{(v['delta_alpha_vs_baseline'] or 0):>9.3f}{(v['delta_gini_vs_baseline'] or 0):>9.4f}"
              f"{(v['delta_share_deg_out_vs_baseline'] or 0):>8.3f}"
              f"{(v['pop_spread_ratio'] or 0):>10.3f}")


if __name__ == "__main__":
    main()
