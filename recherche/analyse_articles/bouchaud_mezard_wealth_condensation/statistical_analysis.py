#!/usr/bin/env python3
"""Campagnes statistiques pour Bouchaud--Mézard."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import recoding


def mean_ci(values: list[float]) -> dict[str, float]:
    x = np.asarray(values, dtype=float)
    m = float(np.mean(x))
    s = float(np.std(x, ddof=1)) if len(x) > 1 else 0.0
    return {
        "mean": m,
        "std": s,
        "ci95_low": float(m - 1.96 * s / np.sqrt(len(x))),
        "ci95_high": float(m + 1.96 * s / np.sqrt(len(x))),
        "n": int(len(x)),
    }


def pareto_campaign(rng: np.random.Generator, reps: int) -> list[dict]:
    rows = []
    for n in [1000, 5000, 20000]:
        for mu in [0.5, 0.8, 1.2, 2.0, 3.0]:
            y2, top1, top5 = [], [], []
            for _ in range(reps):
                w = recoding.pareto_wealth(rng, n, mu)
                y2.append(float(np.sum(w * w)))
                ordered = np.sort(w)[::-1]
                top1.append(float(ordered[0]))
                top5.append(float(np.sum(ordered[: max(1, int(0.05 * n))])))
            rows.append(
                {
                    "N": n,
                    "mu": mu,
                    "Y2": mean_ci(y2),
                    "largest_share": mean_ci(top1),
                    "top5pct_share": mean_ci(top5),
                }
            )
    return rows


def graph_campaign(args: argparse.Namespace) -> list[dict]:
    rows = []
    ratios = [0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0]
    for c in [3, 4, 8]:
        for ratio in ratios:
            mus, y2s = [], []
            for r in range(args.graph_reps):
                rng = np.random.default_rng(args.seed + 100000 * c + int(1000 * ratio) + r)
                mu_hat, y2 = recoding.simulate_graph_exponent(
                    rng,
                    n=args.graph_n,
                    c=c,
                    ratio=ratio,
                    sigma=1.0,
                    dt=args.dt,
                    steps=args.steps,
                    burn=args.burn,
                )
                mus.append(mu_hat)
                y2s.append(y2)
            rows.append({"c": c, "J_over_sigma2": ratio, "mu_hat": mean_ci(mus), "Y2": mean_ci(y2s)})
    return rows


def plot_pareto(rows: list[dict], figures: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for n in sorted({r["N"] for r in rows}):
        subset = [r for r in rows if r["N"] == n]
        mu = np.array([r["mu"] for r in subset])
        y = np.array([r["Y2"]["mean"] for r in subset])
        lo = np.array([r["Y2"]["ci95_low"] for r in subset])
        hi = np.array([r["Y2"]["ci95_high"] for r in subset])
        axes[0].errorbar(mu, y, yerr=[y - lo, hi - y], marker="o", capsize=2, label=f"N={n}")
        top = np.array([r["largest_share"]["mean"] for r in subset])
        lo = np.array([r["largest_share"]["ci95_low"] for r in subset])
        hi = np.array([r["largest_share"]["ci95_high"] for r in subset])
        axes[1].errorbar(mu, top, yerr=[top - lo, hi - top], marker="o", capsize=2, label=f"N={n}")
    axes[0].axvline(1, color="0.4", ls="--")
    axes[1].axvline(1, color="0.4", ls="--")
    axes[0].set_xlabel(r"$\mu$")
    axes[0].set_ylabel(r"$Y_2$")
    axes[1].set_xlabel(r"$\mu$")
    axes[1].set_ylabel("plus grande part")
    axes[0].set_yscale("log")
    axes[1].set_yscale("log")
    for ax in axes:
        ax.grid(alpha=0.25, which="both")
        ax.legend()
    fig.tight_layout()
    fig.savefig(figures / "stat_pareto_condensation.pdf")
    fig.savefig(figures / "stat_pareto_condensation.png", dpi=160)
    plt.close(fig)


def plot_graph(rows: list[dict], figures: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    for c in sorted({r["c"] for r in rows}):
        subset = [r for r in rows if r["c"] == c]
        x = np.array([r["J_over_sigma2"] for r in subset])
        y = np.array([r["mu_hat"]["mean"] for r in subset])
        lo = np.array([r["mu_hat"]["ci95_low"] for r in subset])
        hi = np.array([r["mu_hat"]["ci95_high"] for r in subset])
        ax.errorbar(x, y, yerr=[y - lo, hi - y], marker="o", capsize=2, label=f"c={c}")
    xx = np.logspace(np.log10(0.05), np.log10(2.0), 200)
    ax.plot(xx, 1 + xx, color="k", lw=1, label="champ moyen")
    ax.axhline(1, color="0.4", ls="--")
    ax.set_xscale("log")
    ax.set_xlabel(r"$J/\sigma^2$")
    ax.set_ylabel(r"$\hat\mu$ moyen")
    ax.grid(alpha=0.25, which="both")
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures / "stat_graph_connectivity.pdf")
    fig.savefig(figures / "stat_graph_connectivity.png", dpi=160)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260701)
    parser.add_argument("--pareto-reps", type=int, default=200)
    parser.add_argument("--graph-reps", type=int, default=5)
    parser.add_argument("--graph-n", type=int, default=900)
    parser.add_argument("--dt", type=float, default=0.01)
    parser.add_argument("--steps", type=int, default=9000)
    parser.add_argument("--burn", type=int, default=3000)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    figures = root / "figures"
    results = root / "results"
    figures.mkdir(exist_ok=True)
    results.mkdir(exist_ok=True)
    rng = np.random.default_rng(args.seed)
    pareto = pareto_campaign(rng, args.pareto_reps)
    graph = graph_campaign(args)
    plot_pareto(pareto, figures)
    plot_graph(graph, figures)
    summary = {
        "seed": args.seed,
        "pareto_reps": args.pareto_reps,
        "graph_reps": args.graph_reps,
        "graph_n": args.graph_n,
        "steps": args.steps,
        "burn": args.burn,
        "pareto": pareto,
        "graph": graph,
    }
    (results / "statistical_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
