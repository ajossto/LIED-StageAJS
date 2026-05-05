"""
Génère la figure comparative pour le long run k=3 σ=0.005 à 10 000 pas (6 seeds).

Format : une ligne par seed, 4 colonnes :
  n vivantes (bleu), n prêts (vert), densité prêts/entité (orange), Gini actif (violet).
Bandeau de statut par ligne (stationnaire / non-stationnaire).

Source : results/long_run_k3sigma0005_10k.json

Sortie :
  report/figures/long_run_k3sigma0005_10k_trajectoires.png
  report/figures/long_run_k3sigma0005_10k_trajectoires.pdf
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent.parent
DATA_FILE = HERE / "results" / "long_run_k3sigma0005_10k.json"
FIGURES = HERE / "report" / "figures"
SEEDS_ORDER = [7, 123, 0, 1, 2, 3]

SERIES = [
    ("ts_alive",        "n vivantes",      "tab:blue"),
    ("ts_loans_series", "n prêts",         "tab:green"),
    ("_density",        "prêts / entité",  "tab:orange"),
    ("ts_gini",         "Gini actif",      "tab:purple"),
]


def load_data() -> list[dict]:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    by_seed = {r["seed"]: r for r in data}
    return [by_seed[s] for s in SEEDS_ORDER if s in by_seed]


def make_label(r: dict) -> str:
    status = "STATIONNAIRE" if r["stationary"] else (
        "flux OK, non borné" if r["flow_balanced"] else "non-stationnaire"
    )
    flr = r.get("failure_lambda_ratio", 0)
    return (f"k=3, σ=0.005 | seed={r['seed']} | {r['n_steps_done']} pas | "
            f"alive final={r['final_alive']} | flr={flr:.3f} | [{status}]")


def plot(records: list[dict], out: Path) -> None:
    n = len(records)
    fig, axes = plt.subplots(n, 4, figsize=(18, 2.6 * n), squeeze=False)

    for row_i, (r, ax_row) in enumerate(zip(records, axes)):
        ts_alive = r["ts_alive"]
        ts_loans = r["ts_loans_series"]
        ts_densite = r["ts_densite"]
        ts_gini = r["ts_gini"]
        density = [lo / al if al > 0 else 0.0
                   for al, lo in zip(ts_alive, ts_loans)]
        series_data = [ts_alive, ts_loans, density, ts_gini]
        t = list(range(len(ts_alive)))

        stationary = r["stationary"]
        row_color = "#d4edda" if stationary else "#fff3cd"

        for ax, (key, ylabel, color), vals in zip(ax_row, SERIES, series_data):
            ax.plot(t, vals, linewidth=0.7, color=color)
            ax.set_ylabel(ylabel, fontsize=8)
            ax.grid(True, alpha=0.20)
            ax.tick_params(labelsize=7)
            ax.set_facecolor(row_color)

        ax_row[0].set_title(make_label(r), loc="left", fontsize=8)

    for ax in axes[-1]:
        ax.set_xlabel("pas", fontsize=8)

    fig.suptitle(
        r"Long run $k=3$, $\sigma_\alpha=0.005$ — 10\,000 pas — trajectoires comparées (6 seeds)",
        fontsize=13,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    FIGURES.mkdir(exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → {out}")


def main() -> None:
    records = load_data()
    if not records:
        print(f"Erreur : {DATA_FILE} introuvable ou vide.")
        sys.exit(1)
    for ext in ("png", "pdf"):
        out = FIGURES / f"long_run_k3sigma0005_10k_trajectoires.{ext}"
        plot(records, out)
    print(f"Figure long run 10k générée ({len(records)} seeds).")


if __name__ == "__main__":
    main()
