"""Génère les surfaces 3D pour les 4 campagnes coarse de couplage."""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa
from pathlib import Path

RESULTS = Path("/home/anatole/jupyter/modele-27-04-WIP/studies/sensitivity/results")
FIGURES = Path("/home/anatole/jupyter/modele-27-04-WIP/studies/sensitivity/report/figures")


def _surface_3d(ax, xs, ys, zs, ns, xlabel, ylabel, title):
    """Plot a 3D scatter with size ∝ n_seeds and color = fraction."""
    sc = ax.scatter(
        xs, ys, zs,
        c=zs,
        cmap="viridis",
        vmin=0.0, vmax=1.0,
        s=[max(20, 15 * n) for n in ns],
        alpha=0.75,
        depthshade=True,
        edgecolors="none",
    )
    # Add vertical drops to the z=0 plane
    for x, y, z in zip(xs, ys, zs):
        ax.plot([x, x], [y, y], [0, z], color="gray", alpha=0.2, linewidth=0.5)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_zlabel("fraction bornée", fontsize=9)
    ax.set_zlim(0, 1)
    ax.set_title(title, fontsize=10)
    return sc


def plot_lambda_k():
    with open(RESULTS / "claude_coupling_lambda_k_aggregate.json") as f:
        data = json.load(f)
    xs = [d["lambda"] for d in data]
    ys = [d["k"] for d in data]
    zs = [d["bounded_share"] for d in data]
    ns = [d["n"] for d in data]

    fig = plt.figure(figsize=(7, 5))
    ax = fig.add_subplot(111, projection="3d")
    sc = _surface_3d(ax, xs, ys, zs, ns, r"$\lambda$", r"$k$",
                     r"Carte coarse $\lambda\times k$ : fraction bornée (3 seeds)")
    fig.colorbar(sc, ax=ax, shrink=0.5, label="fraction bornée")
    fig.tight_layout()
    out = FIGURES / "claude_surface_3d_lambda_k.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Saved {out}")


def plot_k_mu():
    with open(RESULTS / "claude_coupling_k_mu_aggregate.json") as f:
        data = json.load(f)
    xs = [d["k"] for d in data]
    ys = [d["mu"] for d in data]
    zs = [d["bounded_share"] for d in data]
    ns = [d["n"] for d in data]

    fig = plt.figure(figsize=(7, 5))
    ax = fig.add_subplot(111, projection="3d")
    sc = _surface_3d(ax, xs, ys, zs, ns, r"$k$", r"$\mu$",
                     r"Carte coarse $k\times\mu$ : fraction bornée (3 seeds)")
    fig.colorbar(sc, ax=ax, shrink=0.5, label="fraction bornée")
    fig.tight_layout()
    out = FIGURES / "claude_surface_3d_k_mu.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Saved {out}")


def plot_sigma_k():
    with open(RESULTS / "claude_coupling_sigma_k_aggregate.json") as f:
        data = json.load(f)
    xs = [d["sigma"] for d in data]
    ys = [d["k"] for d in data]
    zs = [d["bounded_share"] for d in data]
    ns = [d["n"] for d in data]

    fig = plt.figure(figsize=(7, 5))
    ax = fig.add_subplot(111, projection="3d")
    sc = _surface_3d(ax, xs, ys, zs, ns, r"$\sigma_\alpha$", r"$k$",
                     r"Carte coarse $\sigma_\alpha\times k$ : fraction bornée (3 seeds)")
    fig.colorbar(sc, ax=ax, shrink=0.5, label="fraction bornée")
    fig.tight_layout()
    out = FIGURES / "claude_surface_3d_sigma_k.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Saved {out}")


def plot_theta_delta():
    with open(RESULTS / "claude_coupling_theta_depr_aggregate.json") as f:
        data = json.load(f)
    # Use k=4 centre only if both k=3 and k=4 present, or all together
    xs = [d["theta"] for d in data]
    ys = [d["depr_endo"] for d in data]
    zs = [d["bounded_share"] for d in data]
    ns = [d["n"] for d in data]
    ks = [d["k"] for d in data]

    # Separate by centre k
    k_vals = sorted(set(ks))
    if len(k_vals) > 1:
        fig, axes = plt.subplots(1, len(k_vals), figsize=(7 * len(k_vals), 5),
                                 subplot_kw={"projection": "3d"})
        if len(k_vals) == 1:
            axes = [axes]
        for ax, kv in zip(axes, k_vals):
            mask = [k == kv for k in ks]
            xm = [x for x, m in zip(xs, mask) if m]
            ym = [y for y, m in zip(ys, mask) if m]
            zm = [z for z, m in zip(zs, mask) if m]
            nm = [n for n, m in zip(ns, mask) if m]
            sc = _surface_3d(ax, xm, ym, zm, nm, r"$\theta$", r"$\delta_{\rm endo}$",
                             rf"Carte coarse $\theta\times\delta$ (centre $k={kv}$, 3 seeds)")
        fig.colorbar(sc, ax=axes[-1], shrink=0.5, label="fraction bornée")
    else:
        fig = plt.figure(figsize=(7, 5))
        ax = fig.add_subplot(111, projection="3d")
        sc = _surface_3d(ax, xs, ys, zs, ns, r"$\theta$", r"$\delta_{\rm endo}$",
                         r"Carte coarse $\theta\times\delta$ : fraction bornée (3 seeds)")
        fig.colorbar(sc, ax=ax, shrink=0.5, label="fraction bornée")
    fig.tight_layout()
    out = FIGURES / "claude_surface_3d_theta_delta.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Saved {out}")


if __name__ == "__main__":
    plot_lambda_k()
    plot_k_mu()
    plot_sigma_k()
    plot_theta_delta()
    print("Done.")
