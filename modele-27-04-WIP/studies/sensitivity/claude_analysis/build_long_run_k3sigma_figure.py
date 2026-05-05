"""
Génère la figure comparative pour la table 13 (long run k=3 sigma=0.005, 5 seeds).

Format identique à la figure 7 (codex_oat_key_trajectories) :
  - Une ligne par seed.
  - Colonnes : n vivantes (bleu), n prêts (vert), densité prêts/entité (orange),
    coût par pas en ms (rouge).
  - Ligne verticale pour seed=42 (arrêt watchdog à step 1401).

Source : results/claude_long_run_k3sigma0005.json

Sortie :
  report/figures/claude_long_run_k3sigma0005_trajectoires.png
  report/figures/claude_long_run_k3sigma0005_trajectoires.pdf
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

HERE = Path(__file__).resolve().parent.parent
RESULTS = HERE / "results"
FIGURES = HERE / "report" / "figures"

DATA_FILE = RESULTS / "claude_long_run_k3sigma0005.json"
SEEDS_ORDER = [42, 7, 123, 0, 1]


def load_data() -> list[dict]:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    by_seed = {r["seed"]: r for r in data}
    return [by_seed[s] for s in SEEDS_ORDER if s in by_seed]


def make_row(run: dict) -> tuple[str, list[dict]]:
    """Construit la série temporelle à partir du champ probe."""
    probe = run.get("probe", [])
    rows = []
    for p in probe:
        alive = p.get("alive", 0)
        loans = p.get("loans", 0)
        density = loans / alive if alive > 0 else 0.0
        rows.append({
            "step": p.get("step", 0),
            "alive": alive,
            "loans": loans,
            "density": density,
            "ms": p.get("ms_per_step", 0.0),
        })
    stopped = run.get("stopped_early", False)
    label = (f"k=3, σ=0.005 | seed={run['seed']}"
             f" | final: {run['final_alive']} entités, {run['final_loans']} prêts"
             f"{' [ARRÊT WATCHDOG]' if stopped else ''}")
    return label, rows


def plot(cases: list[tuple[str, list[dict]]], path: Path) -> None:
    n = len(cases)
    fig, axes = plt.subplots(n, 4, figsize=(16, max(2.2 * n, 4)), squeeze=False)
    SERIES = [
        ("alive",   "n vivantes",       "tab:blue"),
        ("loans",   "n prêts",          "tab:green"),
        ("density", "prêts / entité",   "tab:orange"),
        ("ms",      "ms/pas",           "tab:red"),
    ]
    seed42_stop = 1401

    for row_i, (ax_row, (label, data)) in enumerate(zip(axes, cases)):
        t = [r["step"] for r in data]
        seed = int(label.split("seed=")[1].split(" ")[0].split("|")[0].strip())
        for ax, (key, ylabel, color) in zip(ax_row, SERIES):
            vals = [r[key] for r in data]
            ax.plot(t, vals, linewidth=1.0, color=color)
            ax.set_ylabel(ylabel, fontsize=8)
            ax.grid(True, alpha=0.25)
            ax.tick_params(labelsize=8)
            if seed == 42:
                ax.axvline(seed42_stop, color="crimson", linewidth=1.2, linestyle="--",
                           alpha=0.7, label=f"arrêt step {seed42_stop}")
        ax_row[0].set_title(label, loc="left", fontsize=8.5)
        run_id = f"sensitivity_claude_long_run_k3sigma0005_seed{seed}_*"
        ax_row[-1].set_title(run_id, loc="right", fontsize=6.5)

    for ax in axes[-1]:
        ax.set_xlabel("pas")

    fig.suptitle("Long run $k=3$, $\\sigma_\\alpha=0.005$ — trajectoires comparées (Table~13)",
                 fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    FIGURES.mkdir(exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → {path}")


def main() -> None:
    records = load_data()
    if not records:
        print(f"Erreur : {DATA_FILE} introuvable ou vide.")
        sys.exit(1)
    cases = [make_row(r) for r in records]
    png_out = FIGURES / "claude_long_run_k3sigma0005_trajectoires.png"
    pdf_out = FIGURES / "claude_long_run_k3sigma0005_trajectoires.pdf"
    plot(cases, png_out)
    plot(cases, pdf_out)
    print(f"Figure long run k3sigma0005 générée ({len(cases)} seeds).")


if __name__ == "__main__":
    main()
