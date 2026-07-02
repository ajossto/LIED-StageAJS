#!/usr/bin/env python3
"""Reproduction numérique de Bouchaud & Mézard (2000).

Le script génère les trois figures centrales de l'article:
1. courbe cumulée de richesse pour une loi de Pareto avec mu=3;
2. même diagnostic pour mu=0.5, régime condensé;
3. estimation de l'exposant de Pareto dans le modèle continu sur graphe aléatoire.

Les simulations utilisent seulement numpy/scipy/matplotlib.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import sparse
from scipy.special import gamma


def ensure_dirs(root: Path) -> tuple[Path, Path]:
    figures = root / "figures"
    results = root / "results"
    figures.mkdir(exist_ok=True)
    results.mkdir(exist_ok=True)
    return figures, results


def pareto_wealth(rng: np.random.Generator, n: int, mu: float) -> np.ndarray:
    # Pareto xm=1: P(W>w)=w^-mu. Normalisation par la richesse totale.
    w = rng.pareto(mu, size=n) + 1.0
    return w / np.sum(w)


def plot_partial_wealth(rng: np.random.Generator, figures: Path, n: int, mu: float, name: str) -> dict:
    w = pareto_wealth(rng, n, mu)
    # L'article trace la somme partielle dans un ordre arbitraire, pas triée.
    partial = np.cumsum(w)
    y2 = float(np.sum(w * w))
    top_share = float(np.max(w))

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(np.arange(1, n + 1), partial, lw=1.0)
    ax.set_xlabel("n")
    ax.set_ylabel(r"$S_n$")
    ax.set_title(fr"Pareto $\mu={mu}$, N={n}")
    ax.grid(alpha=0.25)
    inset = ax.inset_axes([0.12, 0.56, 0.36, 0.36])
    if mu > 1:
        inset.plot(np.arange(1, 81), partial[:80], lw=1.0)
    else:
        start, stop = int(0.30 * n), int(0.40 * n)
        inset.plot(np.arange(start + 1, stop + 1), partial[start:stop], lw=1.0)
    inset.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(figures / f"{name}.pdf")
    fig.savefig(figures / f"{name}.png", dpi=160)
    plt.close(fig)
    return {"mu": mu, "N": n, "Y2": y2, "largest_share": top_share}


def inverse_gamma_pdf(w: np.ndarray, mu: float) -> np.ndarray:
    # Eq. stationnaire mean-field: P(w) = Z exp[-(mu-1)/w] / w^(1+mu)
    z = (mu - 1.0) ** mu / gamma(mu)
    return z * np.exp(-(mu - 1.0) / w) / np.power(w, 1.0 + mu)


def random_regularish_graph(rng: np.random.Generator, n: int, c: int) -> sparse.csr_matrix:
    # Graphe de type Erdős-Rényi conditionné approximativement par degré moyen c.
    # On évite networkx pour rester dans les bibliothèques demandées.
    p = c / (n - 1)
    rows: list[int] = []
    cols: list[int] = []
    block = 512
    for i0 in range(0, n, block):
        i1 = min(n, i0 + block)
        mat = rng.random((i1 - i0, n)) < p
        for local_i, i in enumerate(range(i0, i1)):
            mat[local_i, : i + 1] = False
        rr, cc = np.nonzero(mat)
        rows.extend((rr + i0).tolist())
        cols.extend(cc.tolist())
    data = np.ones(len(rows) * 2, dtype=float)
    all_rows = np.array(rows + cols, dtype=int)
    all_cols = np.array(cols + rows, dtype=int)
    a = sparse.csr_matrix((data, (all_rows, all_cols)), shape=(n, n))
    # Sécurité contre les agents isolés: on les relie à un voisin aléatoire.
    deg = np.asarray(a.sum(axis=1)).ravel()
    isolated = np.flatnonzero(deg == 0)
    if len(isolated):
        lil = a.tolil()
        for i in isolated:
            j = int(rng.integers(0, n - 1))
            if j >= i:
                j += 1
            lil[i, j] = 1.0
            lil[j, i] = 1.0
        a = lil.tocsr()
    return a


def hill_tail_exponent(values: np.ndarray, tail_fraction: float = 0.08) -> float:
    x = np.sort(values[values > 0])
    k = max(20, int(tail_fraction * len(x)))
    threshold = x[-k]
    tail = x[-k:]
    # Estimateur Hill pour la queue P(X>x) ~ x^-mu.
    return float(k / np.sum(np.log(tail / threshold)))


def simulate_graph_exponent(
    rng: np.random.Generator,
    n: int,
    c: int,
    ratio: float,
    sigma: float,
    dt: float,
    steps: int,
    burn: int,
) -> tuple[float, float]:
    j_total = ratio * sigma * sigma
    a = random_regularish_graph(rng, n, c)
    deg = np.asarray(a.sum(axis=1)).ravel()
    # J_ij = J_total / c en moyenne; on utilise le degré local dans le laplacien.
    j_edge = j_total / c
    w = np.ones(n)
    for t in range(steps):
        noise = sigma * np.sqrt(dt) * rng.standard_normal(n)
        # Discrétisation semi-explicite: diffusion multiplicative exacte au premier ordre,
        # puis échange linéaire. Renormalisation: l'article travaille sur les w_i normalisés.
        w *= np.exp(noise - 0.5 * sigma * sigma * dt)
        exchange = j_edge * dt * (a @ w - deg * w)
        w = np.maximum(w + exchange, 1e-300)
        w /= np.mean(w)
        if t == burn:
            # petite remise à l'échelle après le transitoire
            w /= np.mean(w)
    mu_hat = hill_tail_exponent(w)
    y2 = float(np.sum((w / np.sum(w)) ** 2))
    return mu_hat, y2


def plot_graph_exponents(rng: np.random.Generator, figures: Path, args: argparse.Namespace) -> list[dict]:
    ratios = np.array([0.03, 0.06, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0, 5.0, 10.0])
    rows = []
    for ratio in ratios:
        estimates = []
        y2s = []
        for _ in range(args.graph_repeats):
            mu_hat, y2 = simulate_graph_exponent(
                rng,
                n=args.graph_n,
                c=4,
                ratio=float(ratio),
                sigma=args.sigma,
                dt=args.dt,
                steps=args.steps,
                burn=args.burn,
            )
            estimates.append(mu_hat)
            y2s.append(y2)
        rows.append(
            {
                "J_over_sigma2": float(ratio),
                "mu_hat": float(np.mean(estimates)),
                "mu_std": float(np.std(estimates, ddof=1)) if len(estimates) > 1 else 0.0,
                "Y2": float(np.mean(y2s)),
                "mean_field_mu": float(1.0 + ratio),
            }
        )

    x = np.array([r["J_over_sigma2"] for r in rows])
    y = np.array([r["mu_hat"] for r in rows])
    yerr = np.array([r["mu_std"] for r in rows])
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.errorbar(x, y, yerr=yerr, fmt="o", capsize=2, label="simulation graphe c=4")
    xx = np.logspace(np.log10(x.min()), np.log10(x.max()), 200)
    ax.plot(xx, 1 + xx, label=r"champ moyen $\mu=1+J/\sigma^2$")
    ax.axhline(1, color="0.4", ls="--", lw=1)
    ax.set_xscale("log")
    ax.set_xlabel(r"$J/\sigma^2$")
    ax.set_ylabel(r"exposant de queue $\hat\mu$")
    ax.set_title("Modèle sur graphe aléatoire, c=4")
    ax.legend()
    ax.grid(alpha=0.25, which="both")
    fig.tight_layout()
    fig.savefig(figures / "figure3_graph_tail_exponent.pdf")
    fig.savefig(figures / "figure3_graph_tail_exponent.png", dpi=160)
    plt.close(fig)
    return rows


def plot_mean_field(figures: Path) -> dict:
    # Contrôle direct de l'équation stationnaire analytique.
    ws = np.logspace(-2, 2.2, 500)
    mus = [1.2, 2.0, 4.0]
    fig, ax = plt.subplots(figsize=(6, 4))
    for mu in mus:
        ax.plot(ws, inverse_gamma_pdf(ws, mu), label=fr"$\mu={mu}$")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("richesse normalisée w")
    ax.set_ylabel("densité stationnaire")
    ax.set_title("Solution stationnaire mean-field")
    ax.legend()
    ax.grid(alpha=0.25, which="both")
    fig.tight_layout()
    fig.savefig(figures / "mean_field_stationary_density.pdf")
    fig.savefig(figures / "mean_field_stationary_density.png", dpi=160)
    plt.close(fig)
    return {"checked_mu": mus}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260701)
    parser.add_argument("--pareto-n", type=int, default=5000)
    parser.add_argument("--graph-n", type=int, default=900)
    parser.add_argument("--graph-repeats", type=int, default=2)
    parser.add_argument("--sigma", type=float, default=1.0)
    parser.add_argument("--dt", type=float, default=0.01)
    parser.add_argument("--steps", type=int, default=9000)
    parser.add_argument("--burn", type=int, default=3000)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    figures, results = ensure_dirs(root)
    rng = np.random.default_rng(args.seed)

    summary = {
        "seed": args.seed,
        "figure1": plot_partial_wealth(rng, figures, args.pareto_n, 3.0, "figure1_pareto_mu3"),
        "figure2": plot_partial_wealth(rng, figures, args.pareto_n, 0.5, "figure2_pareto_mu05"),
        "mean_field": plot_mean_field(figures),
        "figure3": plot_graph_exponents(rng, figures, args),
        "notes": [
            "La figure 3 dépend d'une discrétisation Euler/renormalisation; l'article ne donne pas N, dt, durée ni méthode d'estimation de mu.",
            "L'estimateur de queue utilisé est l'estimateur de Hill sur les 8% supérieurs.",
        ],
    }
    (results / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
