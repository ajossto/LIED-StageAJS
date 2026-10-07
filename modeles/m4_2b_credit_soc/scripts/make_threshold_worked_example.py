"""Exemple travaillé : comment le seuil (x_min) et la régression de queue
sont calculés (scripts/tail_test.py::fit_powerlaw_xmin), et à quoi
ressemble la régression à seuil/2 (scripts/interest_income.py::
_alpha_hill_at_threshold) sur les VRAIES données d'un instantané.

Ne réimplémente aucun calcul : appelle directement tail_test.py et
interest_income.py sur un run brut (results/campaign/baseline/seed0),
pour garantir que la figure montre exactement ce que le pipeline de
confirmation calcule (mêmes fonctions, mêmes paramètres). Réponse
illustrée à une question utilisateur sur le sens du critère 1 (voir
JOURNAL.md §18).

Snapshot choisi : t=2225 (baseline, seed0, fenêtre confirmation
[750,3000]), le plus proche de la moyenne des 91 instantanés
identifiables sur ce run (alpha_density_mean=3.7798) — ni un cas
particulièrement stable ni particulièrement instable, un exemple
représentatif.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import interest_income  # noqa: E402
import tail_test  # noqa: E402

RUN_DIR = ROOT / "results" / "campaign" / "baseline" / "seed0"
T_MIN, T_MAX = 750, 3000
T_CHOSEN = 2225
OUT = ROOT / "report" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 130, "font.size": 10.5,
    "axes.grid": True, "grid.alpha": 0.25,
})


def _ks_scan(pos: np.ndarray, n_candidates: int = 40, min_tail: int = 80):
    """Reproduit la boucle interne de tail_test.fit_powerlaw_xmin, mais en
    gardant tous les candidats (pas seulement le meilleur) pour pouvoir
    tracer la courbe KS(x_min)."""
    pos_sorted = np.sort(pos[pos > 0])
    n = len(pos_sorted)
    qs = np.linspace(0, 0.90, n_candidates)
    candidates = np.unique(np.quantile(pos_sorted, qs))
    rows = []
    for x_min in candidates:
        tail = pos_sorted[pos_sorted >= x_min]
        if len(tail) < min_tail:
            continue
        alpha = 1 + len(tail) / np.sum(np.log(tail / x_min))
        if not np.isfinite(alpha) or alpha <= 1.0:
            continue
        ks = tail_test._pareto_ks(tail, x_min, alpha - 1)
        rows.append((x_min, alpha, ks, len(tail)))
    return rows


def _ccdf(values: np.ndarray):
    x = np.sort(values)
    n = len(x)
    ccdf = 1.0 - np.arange(0, n) / n  # P(X >= x_i)
    return x, ccdf


def main():
    snaps = interest_income.load_all_entity_snapshots(RUN_DIR, t_min=T_MIN, t_max=T_MAX)
    snap = dict(snaps)[T_CHOSEN]
    values = snap["int_in"]
    p0, positive = interest_income.zero_mass_and_positive(values)

    scan = _ks_scan(positive, min_tail=80)
    best = tail_test.fit_powerlaw_xmin(positive, min_tail=80)
    x_min, alpha_xmin, ks_xmin, n_tail_xmin = best["x_min"], best["alpha"], best["ks"], best["n_tail"]

    half = interest_income._alpha_hill_at_threshold(positive, x_min * 0.5)
    x_min_half = half["x_min"]
    alpha_half = half["alpha_density"]
    n_tail_half = half["n_tail"]
    tail_half = positive[positive >= x_min_half]
    ks_half = tail_test._pareto_ks(tail_half, x_min_half, alpha_half - 1)

    reldiff = abs(alpha_xmin - alpha_half) / abs(alpha_xmin)

    fig, (ax_scan, ax_ccdf) = plt.subplots(1, 2, figsize=(11.5, 4.6))

    # --- panneau A : comment le seuil est choisi (scan KS) ---
    xs = np.array([r[0] for r in scan])
    kss = np.array([r[2] for r in scan])
    ax_scan.plot(xs, kss, "o-", color="#444444", ms=4, lw=1.2, label="distance KS(seuil candidat)")
    ax_scan.axvline(x_min, color="crimson", ls="--", lw=1.6, label=f"seuil retenu = {x_min:.1f} (KS min)")
    ax_scan.axvline(x_min_half, color="#1f77b4", ls=":", lw=1.6, label=f"seuil/2 = {x_min_half:.1f}")
    ax_scan.set_xscale("log")
    ax_scan.set_xlabel("seuil candidat x_min (J/pas, log)")
    ax_scan.set_ylabel("distance de Kolmogorov-Smirnov\n(ajustement Pareto vs empirique, sur la queue)")
    ax_scan.set_title("A. Comment le seuil est choisi\n(balayage de quantiles, minimum KS)")
    ax_scan.legend(fontsize=8, loc="upper right")

    # --- panneau B : régressions sur les données réelles ---
    x_ccdf, y_ccdf = _ccdf(positive)
    ax_ccdf.plot(x_ccdf, y_ccdf, ".", color="#888888", ms=3, alpha=0.6, label=f"données (n={len(positive)}, instantané t={T_CHOSEN})")

    xr = np.geomspace(x_min, positive.max(), 100)
    yr = (x_min / xr) ** (alpha_xmin - 1) * (n_tail_xmin / len(positive))
    ax_ccdf.plot(xr, yr, "-", color="crimson", lw=2,
                 label=f"régression au seuil : α̂={alpha_xmin:.2f}, n_tail={n_tail_xmin}, KS={ks_xmin:.3f}")

    xr2 = np.geomspace(x_min_half, positive.max(), 100)
    yr2 = (x_min_half / xr2) ** (alpha_half - 1) * (n_tail_half / len(positive))
    ax_ccdf.plot(xr2, yr2, "-", color="#1f77b4", lw=2,
                 label=f"régression à seuil/2 : α̂={alpha_half:.2f}, n_tail={n_tail_half}, KS={ks_half:.3f}")

    ax_ccdf.axvline(x_min, color="crimson", ls="--", lw=1.2, alpha=0.7)
    ax_ccdf.axvline(x_min_half, color="#1f77b4", ls=":", lw=1.2, alpha=0.7)
    ax_ccdf.set_xscale("log")
    ax_ccdf.set_yscale("log")
    ax_ccdf.set_xlabel("intérêts reçus (J/pas, log)")
    ax_ccdf.set_ylabel("CCDF P(X ≥ x) (log)")
    ax_ccdf.set_title(f"B. Les deux régressions sur les données réelles\n"
                       f"écart relatif |α̂(seuil)−α̂(seuil/2)|/α̂(seuil) = {reldiff:.0%} "
                       f"({'< 20% : critère 1 passe' if reldiff < 0.20 else '≥ 20% : critère 1 échoue'})")
    ax_ccdf.legend(fontsize=7.6, loc="lower left")

    fig.suptitle("Baseline, seed 0, instantané t=2225 (exemple représentatif, "
                  "α̂ proche de la moyenne sur les 91 instantanés de la fenêtre de confirmation)",
                  fontsize=9.5, y=1.02)
    fig.tight_layout()
    out_path = OUT / "fig7_seuil_exemple_travaille.png"
    fig.savefig(out_path, bbox_inches="tight")
    print(f"écrit : {out_path}")
    print(f"x_min={x_min:.3f} alpha_xmin={alpha_xmin:.4f} n_tail={n_tail_xmin} ks={ks_xmin:.4f}")
    print(f"x_min_half={x_min_half:.3f} alpha_half={alpha_half:.4f} n_tail_half={n_tail_half} ks_half={ks_half:.4f}")
    print(f"reldiff={reldiff:.4f}")


if __name__ == "__main__":
    main()
