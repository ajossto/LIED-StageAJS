"""Figures de synthèse du rapport M4 (baseline vs candidat final, scaling,
dose-réponse volume→branchement). Lit UNIQUEMENT les artefacts disque
(results/<run_id>/) — consignes de traçabilité. Style : conventions des
figures du projet (mpl_figures.py / simulation_lab).

Usage : /home/anatole/jupyter/.venv/bin/python3 make_report_figures.py
Sorties : experiments/m4/report_figures/*.png + sources.json (traçabilité).
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "src"))
sys.path.insert(0, str(HERE))

from m4.metrics import load_avalanches, load_series  # noqa: E402

RESULTS = HERE / "results"
OUT = HERE / "report_figures"
plt.rcParams.update({"figure.dpi": 150, "savefig.bbox": "tight"})


def _sizes(run_id, t_min=None):
    run_dir = RESULTS / run_id
    with open(run_dir / "config.json") as fh:
        T = json.load(fh)["T"]
    if t_min is None:
        t_min = T // 4
    avs = [a for a in load_avalanches(run_dir) if a["t"] >= t_min]
    return np.array([a["size"] for a in avs], dtype=np.int64), avs


def _branching(run_id):
    sizes, avs = _sizes(run_id)
    return 1.0 - sum(a["n_roots"] for a in avs) / sizes.sum()


def _pop_mean(run_id):
    run_dir = RESULTS / run_id
    with open(run_dir / "config.json") as fh:
        T = json.load(fh)["T"]
    rows = load_series(run_dir)
    return float(np.mean([r["pop"] for r in rows if r["t"] >= T // 4]))


def _ccdf(ax, sizes, label, color=None, marker="."):
    v = np.sort(sizes.astype(float))
    ccdf = 1.0 - np.arange(1, len(v) + 1) / (len(v) + 1.0)
    ax.loglog(v, ccdf, marker=marker, ls="none", ms=4, label=label,
              color=color, alpha=0.75)


def fig_baseline_vs_candidate(sources):
    """CCDF des tailles d'avalanches : baseline M4 (moteur L/K, chocs
    sectoriels ρ_s=0,8, d0=28) vs candidat final (moteur fusionné, chocs
    iid, cancel+destroy, un round par tête), à λ=10 (3 seeds chacun)."""
    base_runs = ["a1_lam10p0_s0", "a1_lam10p0_s1", "a1_lam10p0_s2"]
    cand_runs = ["f_lam10_s0", "f_lam10_s1", "f_lam10_s2"]
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    for j, rid in enumerate(base_runs):
        sizes, _ = _sizes(rid)
        _ccdf(ax, sizes, "baseline (fork M3, ρ_s=0,8)" if j == 0 else None,
              color="#7f7f7f", marker="x")
    for j, rid in enumerate(cand_runs):
        sizes, _ = _sizes(rid)
        _ccdf(ax, sizes, "candidat final (cd, iid, 1 round/tête)"
              if j == 0 else None, color="#d62728")
    ax.set_xlabel("taille d'avalanche causale s")
    ax.set_ylabel("P(S > s)")
    ax.set_title("Baseline vs mécanisme candidat — λ=10, T=2000, t ≥ T/4,\n"
                 "3 seeds par variante (courbes superposées, pas de pooling)")
    ax.legend()
    ax.grid(True, which="both", alpha=0.25)
    fig.savefig(OUT / "baseline_vs_candidat_ccdf.png")
    plt.close(fig)
    sources["baseline_vs_candidat_ccdf.png"] = base_runs + cand_runs


def fig_finite_size(sources):
    """CCDF du candidat final par taille de système (λ)."""
    groups = [("f_lam10_s0", "λ=10"), ("f_lam30_s0", "λ=30"),
              ("f_lam100_s0", "λ=100"), ("f_lam300_s0", "λ=300")]
    colors = ["#1f77b4", "#2ca02c", "#ff7f0e", "#d62728"]
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    used = []
    for (rid, lab), col in zip(groups, colors):
        if not (RESULTS / rid / "avalanches.csv").exists():
            continue
        sizes, _ = _sizes(rid)
        pop = _pop_mean(rid)
        _ccdf(ax, sizes, f"{lab} (pop moy. {pop:.0f}, max {sizes.max()})",
              color=col)
        used.append(rid)
    ax.set_xlabel("taille d'avalanche causale s")
    ax.set_ylabel("P(S > s)")
    ax.set_title("Scaling en taille finie du candidat final — le cutoff\n"
                 "suit la taille du système (seed 0 par λ, t ≥ T/4)")
    ax.legend()
    ax.grid(True, which="both", alpha=0.25)
    fig.savefig(OUT / "candidat_scaling_ccdf.png")
    plt.close(fig)
    sources["candidat_scaling_ccdf.png"] = used


def fig_dose_response(sources):
    """b = 1 − Σracines/Σtailles en fonction du volume de marché
    (rounds par tête et par pas), 3 seeds par point."""
    cells = [("v_r6", 1 / 6), ("v_r3", 1 / 3), ("v_r2", 1 / 2),
             ("f_lam30", 1.0)]
    xs, ys, es, used = [], [], [], []
    for name, rpc in cells:
        bs = []
        for s in (0, 1, 2):
            rid = f"{name}_s{s}"
            if (RESULTS / rid / "avalanches.csv").exists():
                bs.append(_branching(rid))
                used.append(rid)
        if bs:
            xs.append(rpc)
            ys.append(np.mean(bs))
            es.append(np.std(bs))
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.errorbar(xs, ys, yerr=es, fmt="o-", capsize=4, color="#1f77b4")
    ax.set_xlabel("rounds de marché par tête et par pas (n_rounds / N)")
    ax.set_ylabel("rapport de branchement b = 1 − Σracines/Σtailles")
    ax.set_title("Dose-réponse volume de crédit → branchement des cascades\n"
                 "(λ=30, T=2000, k=3, cancel+destroy, moy. ± é.-t. sur 3 seeds)")
    ax.grid(True, alpha=0.3)
    fig.savefig(OUT / "dose_reponse_volume_b.png")
    plt.close(fig)
    sources["dose_reponse_volume_b.png"] = used


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    sources = {}
    fig_baseline_vs_candidate(sources)
    fig_finite_size(sources)
    fig_dose_response(sources)
    with open(OUT / "sources.json", "w") as fh:
        json.dump(sources, fh, indent=2)
    print("figures écrites dans", OUT)
    for k, v in sources.items():
        print(f"  {k}: {len(v)} runs")
