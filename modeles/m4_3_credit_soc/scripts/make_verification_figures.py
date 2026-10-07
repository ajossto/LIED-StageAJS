"""Figures de VÉRIFICATION sur données réelles (demande explicite de
l'utilisateur, 2026-08-09) : montre les régressions/ajustements
eux-mêmes (courbe + points de données), pas seulement les paramètres
finaux dans une table — pour permettre de juger si les calculs sont
corrects, pas seulement de les croire sur parole.

Trois familles de figures, réutilisant les fonctions de fit déjà
existantes (`lib_metrics`, `families`, `renewal_relaxation_all_runs`)
SANS EN ÉCRIRE DE NOUVELLES :

1. Relaxation FOPDT (`int_in`) : points de persistance + courbe ajustée.
2. Queue d'intérêt (`dagum_3p`) : CCDF empirique de `int_in` (fenêtre
   post-convergence) + survie ajustée.
3. Avalanches : CCDF empirique des tailles + loi ajustée (tronquée ou
   pure selon `tau_hat_source`), même méthodologie M4B/M4.2B.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats as scipy_stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import lib_metrics  # noqa: E402
import interest_income  # noqa: E402
import families  # noqa: E402
from renewal_relaxation_all_runs import persistence_curve, fit_fopdt, fopdt  # noqa: E402

FIGDIR = ROOT / "report" / "figures" / "verification"
FIGDIR.mkdir(parents=True, exist_ok=True)


def fig_fopdt(run_dir: Path, label: str, field: str = "int_in") -> dict:
    snaps = interest_income.load_all_entity_snapshots(run_dir)
    t0 = snaps[0][0]
    t, y = persistence_curve(snaps, field)
    fit = fit_fopdt(t, y, t0)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(t, y, "o", ms=4, color="#1f77b4", label="données (persistance du décile supérieur)")
    if fit["ok"]:
        tt = np.linspace(t.min(), t.max(), 400)
        yy = fopdt(tt, fit["floor"], fit["tau"], fit["t_delay"], t0)
        ax.plot(tt, yy, "-", color="#d62728", lw=2,
                label=f"régression FOPDT (τ={fit['tau']:.0f}, t_delay={fit['t_delay']:.0f}, "
                      f"floor={fit['floor']:.3f}, R²={fit['r2']:.3f})")
        t_conv = t0 + fit["t_delay"] + 3 * fit["tau"]
        ax.axvline(t_conv, color="gray", ls="--", lw=1,
                   label=f"t_converge = {t_conv:.0f}")
    ax.set_xlabel("t (pas de temps)")
    ax.set_ylabel(f"persistance du décile supérieur ({field})")
    ax.set_title(f"Relaxation FOPDT — {label}")
    ax.legend(fontsize=8)
    fig.tight_layout()
    out = FIGDIR / f"fopdt_{label}.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out}")
    return fit


def fig_dagum_tail(run_dir: Path, label: str, t_converge: float) -> dict:
    snaps = interest_income.load_all_entity_snapshots(run_dir, t_min=int(np.ceil(t_converge)))
    pooled = np.concatenate([s["int_in"] for _t, s in snaps])
    p0, positive = interest_income.zero_mass_and_positive(pooled)
    dagum = families.fit_dagum_3p(positive)
    c, d, loc, scale = dagum["params"][:4]

    x_sorted = np.sort(positive)[::-1]
    n = len(x_sorted)
    ccdf_emp = np.arange(1, n + 1) / n

    xx = np.geomspace(max(positive.min(), 1e-3), positive.max(), 400)
    ccdf_fit = scipy_stats.burr.sf(xx, c, d, loc=loc, scale=scale)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.loglog(x_sorted, ccdf_emp, ".", ms=3, alpha=0.4, color="#1f77b4",
              label=f"CCDF empirique (n={n}, fenêtre post-convergence)")
    ax.loglog(xx, ccdf_fit, "-", color="#d62728", lw=2,
              label=f"dagum_3p ajusté (c={c:.3f}, d={d:.3f})")
    ax.set_xlabel("intérêt reçu (int_in)")
    ax.set_ylabel("P(X > x)")
    ax.set_title(f"Queue d'intérêt — {label} (statistique gelée : c={c:.3f})")
    ax.legend(fontsize=8)
    fig.tight_layout()
    out = FIGDIR / f"dagum_tail_{label}.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out}")
    return {"c": c, "d": d, "n": n}


def fig_avalanches(run_dir: Path, label: str, lo: int | None = None, hi: int | None = None) -> dict:
    if lo is None:
        analysis_path = run_dir / "analysis.json"
        if analysis_path.exists():
            a = json.loads(analysis_path.read_text())
            lo, hi = a.get("lo", 0), a.get("hi")
        else:
            lo = 0
    avalanches = lib_metrics.read_avalanches(run_dir)
    sizes = avalanches["size"]
    if hi is not None:
        mask = (avalanches["t"] >= lo) & (avalanches["t"] <= hi)
        sizes = sizes[mask]
    laws = lib_metrics.compare_laws(sizes, s_min=2)

    s_sorted = np.sort(sizes[sizes >= 2])[::-1]
    n = len(s_sorted)
    ccdf_emp = np.arange(1, n + 1) / n

    s_min = 2
    support = np.arange(s_min, int(s_sorted.max()) * 2 + 1, dtype=float)
    if laws.get("s_c_out_of_range") or laws.get("powerlaw_cutoff") is None:
        alpha = laws["powerlaw"]["alpha"]
        weights = support ** (-alpha)
        fit_label = f"loi de puissance pure (τ̂={alpha:.3f})"
    else:
        alpha = laws["powerlaw_cutoff"]["alpha"]
        cutoff = laws["powerlaw_cutoff"]["cutoff"]
        weights = support ** (-alpha) * np.exp(-support / cutoff)
        fit_label = f"loi tronquée (τ̂={alpha:.3f}, s_c={cutoff:.1f})"
    ccdf_fit_support = np.cumsum(weights[::-1])[::-1]
    ccdf_fit_support = ccdf_fit_support / weights.sum()

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.loglog(s_sorted, ccdf_emp, ".", ms=4, alpha=0.5, color="#1f77b4",
              label=f"CCDF empirique (n_tail={n})")
    ax.loglog(support, ccdf_fit_support, "-", color="#d62728", lw=2, label=fit_label)
    ax.set_xlabel("taille d'avalanche s")
    ax.set_ylabel("P(S ≥ s)")
    ax.set_title(f"Tailles d'avalanches — {label}\nτ̂={laws.get('tau_hat', float('nan')):.3f} "
                 f"(source={laws.get('tau_hat_source')})", fontsize=11)
    ax.legend(fontsize=8)
    fig.tight_layout()
    out = FIGDIR / f"avalanches_{label}.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out}")
    return laws


def main() -> None:
    targets = [
        ("baseline_arithmetic (pilote, target_rule)", ROOT / "results" / "pilot" / "baseline_arithmetic" / "seed0"),
        ("control_geometric (pilote, target_rule)", ROOT / "results" / "pilot" / "control_geometric" / "seed0"),
    ]
    gc_verif = ROOT / "results" / "pilot" / "gamma_comp_0.6667_verif" / "seed0"
    if (gc_verif / "summary.json").exists():
        targets.append(("gamma_comp_0.6667 (D1, run de vérification)", gc_verif))
    else:
        print("gamma_comp_0.6667_verif pas encore terminé — figures FOPDT/dagum "
              "pour cette cellule reportées à un prochain passage.")

    print("=== FOPDT + dagum (nécessitent des instantanés bruts) ===")
    t_converge_by_dir: dict[Path, float] = {}
    for label, run_dir in targets:
        print(f"-- {label} --")
        fit = fig_fopdt(run_dir, label.split(" ")[0])
        if fit["ok"]:
            snaps = interest_income.load_all_entity_snapshots(run_dir)
            t0 = snaps[0][0]
            tconv = t0 + fit["t_delay"] + 3 * fit["tau"]
            t_converge_by_dir[run_dir] = tconv
            fig_dagum_tail(run_dir, label.split(" ")[0], tconv)

    print("\n=== Avalanches (utilisent avalanches.csv, dispo pour toutes les cellules D1) ===")
    avalanche_targets = [
        ("baseline_D1", ROOT / "results" / "d1" / "baseline" / "seed0", None, None),
        ("gamma_comp_0.6667_D1", ROOT / "results" / "d1" / "gamma_comp_0.6667" / "seed0", None, None),
        ("control_geometric_pilote", ROOT / "results" / "pilot" / "control_geometric" / "seed0", "auto", 8000),
        ("baseline_arithmetic_pilote", ROOT / "results" / "pilot" / "baseline_arithmetic" / "seed0", "auto", 8000),
    ]
    for label, run_dir, lo, hi in avalanche_targets:
        if not run_dir.exists():
            continue
        print(f"-- {label} --")
        if lo == "auto":
            lo_val = int(np.ceil(t_converge_by_dir.get(run_dir, 0)))
            fig_avalanches(run_dir, label, lo=lo_val, hi=hi)
        else:
            fig_avalanches(run_dir, label)


if __name__ == "__main__":
    main()
