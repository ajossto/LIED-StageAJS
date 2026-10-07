"""Validation M4 depuis les seuls artefacts disque.

Écrit un ``validation.json`` par run, un agrégat et les figures comparatives.
L'échelle de 13 familles est importée depuis ``recherche/`` (réutilisation,
pas réimplémentation).
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
JUPYTER = ROOT.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(JUPYTER / "recherche/analyse_distributions_taille_revenu/scripts"))

import families as family_ladder  # noqa: E402
from m4.analysis import (avalanche_powerlaw_diagnostics, fit_body,
                         fit_full_families, renewal_diagnostics)  # noqa: E402
from m4.metrics import load_avalanches, load_snapshots  # noqa: E402

RESULTS = HERE / "results"
REPORT = ROOT / "reports" / "m4_research"
FIGURES = REPORT / "figures"


def _jsonable(x):
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, np.generic):
        return x.item()
    return x


def _series(path):
    with open(path) as fh:
        return [{k: float(v) for k, v in row.items()}
                for row in csv.DictReader(fh)]


def _family_summary(values):
    fits = family_ladder.fit_all(values)
    if not fits:
        return None
    best = min(fits, key=lambda k: fits[k]["aic"])
    per_k = family_ladder.best_per_k(fits)
    compact = {
        name: {"k": int(fit["k"]), "aic": float(fit["aic"]),
               "bic": float(fit["bic"])}
        for name, fit in fits.items()
    }
    return {"best_aic": best, "fits": compact,
            "best_per_k": {str(k): fit["name"] for k, fit in per_k.items()}}


def analyze_run(run_dir):
    config = json.loads((run_dir / "config.json").read_text())
    summary = json.loads((run_dir / "summary.json").read_text())
    T = int(summary["t_final"])
    burn = max(400, T // 4)
    series = _series(run_dir / "series.csv")
    post = [r for r in series if r["t"] >= burn]
    pop = np.array([r["pop"] for r in post])
    t = np.array([r["t"] for r in post])
    pop_slope = float(np.polyfit(t, pop, 1)[0]) if len(pop) > 2 else None
    avalanches = load_avalanches(run_dir)
    sizes = np.array([a["size"] for a in avalanches if a["t"] >= burn], dtype=int)
    avalanche = avalanche_powerlaw_diagnostics(avalanches, burn)
    if avalanche:
        avalanche.update({
            "fraction_multi": float(np.mean(sizes > 1)),
            "p99": float(np.quantile(sizes, 0.99)),
            "p999": float(np.quantile(sizes, 0.999)),
            "p99_multi": (float(np.quantile(sizes[sizes > 1], 0.99))
                          if np.any(sizes > 1) else None),
            "max_over_median_population": float(np.max(sizes) / np.median(pop)),
        })
    snaps = load_snapshots(run_dir, t_min=burn)
    snap_times = sorted(snaps)
    final_snap = snaps[snap_times[-1]] if snap_times else None
    renewal = None
    if len(snap_times) >= 2:
        target = (burn + T) / 2
        ta = min(snap_times[:-1], key=lambda x: abs(x - target))
        tb = snap_times[-1]
        renewal = renewal_diagnostics(snaps[ta], snaps[tb], ta, tb)
        if renewal:
            renewal.update({"t_a": ta, "t_b": tb})
    distributions = {}
    if final_snap is not None:
        for var in ("nw", "K", "income"):
            values = final_snap[var]
            distributions[var] = {
                "n": int(len(values)),
                "ladder_13": _family_summary(values),
                "body_truncated": fit_body(values),
                "full_core_ladder": fit_full_families(values),
            }
    validation = {
        "run_id": run_dir.name, "burn_in": burn,
        "facts": {
            "status": summary["status"], "T": T,
            "population_mean_post_burn": float(np.mean(pop)),
            "population_median_post_burn": float(np.median(pop)),
            "population_slope_per_step": pop_slope,
            "loan_volume_mean_post_burn": float(np.mean([r["loan_volume"] for r in post])),
            "n_loans_mean_post_burn": float(np.mean([r["n_loans"] for r in post])),
            "avalanche": avalanche, "renewal": renewal,
            "distributions_final_snapshot": distributions,
        },
        "inferences": {
            "stationary_population": (abs(pop_slope) < 0.05 if pop_slope is not None else None),
            "not_systemic_collapse": (avalanche["max_over_median_population"] < 0.5
                                      if avalanche else None),
            "r2_marker_pass": (
                avalanche["regression_no_singletons"] is not None
                and avalanche["regression_no_singletons"]["r2"] > 0.90
                if avalanche else None),
            "lr_powerlaw_not_rejected": (
                avalanche["lr_powerlaw_vs_truncated_lognormal"] is not None
                and (avalanche["lr_powerlaw_vs_truncated_lognormal"]["p"] >= 0.05
                     or avalanche["lr_powerlaw_vs_truncated_lognormal"]["R"] >= 0)
                if avalanche else None),
        },
    }
    (run_dir / "validation.json").write_text(
        json.dumps(_jsonable(validation), indent=2), encoding="utf-8")
    return validation


def _selected_runs():
    names = ["m4_first_s0"]
    for pattern in ("m4_contract_iid_T4000_lam10p0_s*",
                    "m4_contract_sector_T4000_lam10p0_s*",
                    "m4_contract_sector_T2500_lam5p0_s*",
                    "m4_contract_sector_T2500_lam20p0_s*"):
        names.extend(p.name for p in sorted(RESULTS.glob(pattern)))
    return [RESULTS / n for n in names if (RESULTS / n / "summary.json").exists()]


def _group(v):
    n = v["run_id"]
    if n == "m4_first_s0": return "baseline_d0"
    if "_iid_" in n: return "iid"
    if "lam5p0" in n: return "sector_lam5"
    if "lam20p0" in n: return "sector_lam20"
    return "sector_lam10"


def make_figures(validations):
    FIGURES.mkdir(parents=True, exist_ok=True)
    groups = defaultdict(list)
    for v in validations:
        groups[_group(v)].append(v)

    # Scaling : médianes inter-seeds et étendue, sans pooling des ajustements.
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    Ns, max_med, max_lo, max_hi, p99_med = [], [], [], [], []
    for key in ("sector_lam5", "sector_lam10", "sector_lam20"):
        rows = groups[key]
        n = [r["facts"]["population_mean_post_burn"] for r in rows]
        m = [r["facts"]["avalanche"]["max"] for r in rows]
        q = [r["facts"]["avalanche"]["p99_multi"] for r in rows]
        Ns.append(float(np.median(n))); max_med.append(float(np.median(m)))
        max_lo.append(float(np.min(m))); max_hi.append(float(np.max(m)))
        p99_med.append(float(np.median(q)))
    yerr = [np.array(max_med) - np.array(max_lo),
            np.array(max_hi) - np.array(max_med)]
    axes[0].errorbar(Ns, max_med, yerr=yerr, marker="o", capsize=4,
                     label="max (médiane, étendue seeds)")
    axes[0].plot(Ns, p99_med, "s--", label="p99 multi (médiane)")
    axes[0].set(xlabel="population moyenne post burn-in", ylabel="taille",
                title="Scaling en taille finie")
    axes[0].legend(); axes[0].grid(alpha=.25)
    ratios = [[r["facts"]["avalanche"]["max_over_median_population"]
               for r in groups[k]] for k in ("sector_lam5", "sector_lam10", "sector_lam20")]
    axes[1].boxplot(ratios, tick_labels=["λ=5", "λ=10", "λ=20"])
    axes[1].axhline(.5, color="r", ls="--", label="effondrement 50 %")
    axes[1].set(ylabel="max / population médiane",
                title="Pas d'extinction systémique")
    axes[1].legend(); axes[1].grid(alpha=.25)
    fig.tight_layout(); fig.savefig(FIGURES / "finite_size_scaling.png", dpi=160)
    plt.close(fig)

    # Comparaison exacte des fréquences sur les runs seed 0 représentatifs.
    fig, ax = plt.subplots(figsize=(8, 5.5))
    representatives = [
        ("baseline M4 (d0, N≈155)", RESULTS / "m4_first_s0", 500),
        ("sans d0, λ=10 (N≈320)", RESULTS / "m4_contract_sector_T4000_lam10p0_s0", 1000),
        ("sans d0, λ=20 (N≈640)", RESULTS / "m4_contract_sector_T2500_lam20p0_s0", 625),
    ]
    for label, path, burn in representatives:
        sizes = np.array([a["size"] for a in load_avalanches(path) if a["t"] >= burn])
        vals, counts = np.unique(sizes, return_counts=True)
        ax.loglog(vals, counts / counts.sum(), "o-", ms=4, label=label)
    ax.set(xlabel="taille d'avalanche", ylabel="fréquence empirique",
           title="Baseline vs mécanisme contractuel (artefacts disque)")
    ax.grid(which="both", alpha=.25); ax.legend(); fig.tight_layout()
    fig.savefig(FIGURES / "baseline_candidate_cascades.png", dpi=160)
    plt.close(fig)

    # Comptage des familles gagnantes à λ=10 (5 seeds).
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, var in zip(axes, ("nw", "K", "income")):
        wins = Counter(r["facts"]["distributions_final_snapshot"][var]
                       ["ladder_13"]["best_aic"] for r in groups["sector_lam10"])
        ax.bar(list(wins), list(wins.values()))
        ax.set_title(var); ax.set_ylim(0, 5); ax.tick_params(axis="x", rotation=30)
    fig.suptitle("Famille AIC gagnante (échelle réutilisée de 13 familles, 5 seeds)")
    fig.tight_layout(); fig.savefig(FIGURES / "distribution_family_winners.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    vals = []
    for run in _selected_runs():
        print(f"[analyse] {run.name}", flush=True)
        vals.append(analyze_run(run))
    make_figures(vals)
    groups = defaultdict(list)
    for v in vals:
        groups[_group(v)].append(v)
    aggregate = {"runs": vals, "groups": {k: [v["run_id"] for v in x]
                                            for k, x in groups.items()}}
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "validation_aggregate.json").write_text(
        json.dumps(_jsonable(aggregate), indent=2), encoding="utf-8")
    print(f"[done] {len(vals)} validations -> {REPORT}")
