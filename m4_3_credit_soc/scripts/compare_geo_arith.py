"""Comparaison geometric/arithmetic (PROMPT_M4_3_FINAL.md §4 : objectif du
tout premier run pilote) sur le plan (τ̂/α̂ tronqué, b=branching_ratio),
avec barres d'erreur inter-graines. Réutilise `lib_metrics.window_avalanche_
metrics`/`compare_laws` (M4B/M4.2B, §5/§8 — aucune récriture) ; fenêtre
positionnée PAR RUN sur son propre temps de convergence de `int_in` (§3,
JOURNAL.md §10 — le temps de relaxation varie sensiblement entre graines,
pas de fenêtre unique partagée)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import lib_metrics  # noqa: E402
import interest_income  # noqa: E402
from renewal_relaxation_all_runs import persistence_curve, fit_fopdt  # noqa: E402

CELLS = {
    "geometric": [ROOT / "results" / "pilot" / "control_geometric" / f"seed{s}" for s in (0, 1, 2)],
    "arithmetic": [ROOT / "results" / "pilot" / "baseline_arithmetic" / f"seed{s}" for s in (0, 1, 2)],
}


def own_t_converge(run_dir: Path, field: str = "int_in") -> float:
    snaps = interest_income.load_all_entity_snapshots(run_dir)
    t0 = snaps[0][0]
    t, y = persistence_curve(snaps, field)
    fit = fit_fopdt(t, y, t0)
    if not fit["ok"]:
        raise RuntimeError(f"FOPDT n'a pas convergé pour {run_dir}")
    return t0 + fit["t_delay"] + 3 * fit["tau"]


def analyze_run(run_dir: Path) -> dict:
    t_conv = own_t_converge(run_dir)
    series = lib_metrics.read_series(run_dir)
    avalanches = lib_metrics.read_avalanches(run_dir)
    T = int(series["t"].max())
    lo, hi = int(np.ceil(t_conv)), T
    mask = (series["t"] >= lo) & (series["t"] <= hi)
    pop_mean = float(series["pop"][mask].mean()) if mask.sum() else float("nan")
    metrics = lib_metrics.window_avalanche_metrics(avalanches, lo, hi, pop_mean, s_min=2)
    metrics["t_converge"] = t_conv
    metrics["lo"] = lo
    metrics["hi"] = hi
    metrics["pop_mean"] = pop_mean
    return metrics


def main() -> None:
    summary = {}
    for regime, run_dirs in CELLS.items():
        print(f"\n=== {regime} ===")
        rows = []
        for run_dir in run_dirs:
            m = analyze_run(run_dir)
            rows.append(m)
            print(f"  {run_dir.name}: lo={m['lo']} hi={m['hi']} pop_mean={m['pop_mean']:.0f} "
                  f"b={m.get('branching_ratio', float('nan')):.4f} "
                  f"tau_hat={m.get('tau_hat', float('nan')):.4f} "
                  f"(source={m.get('tau_hat_source')}) "
                  f"s_c_out_of_range={m.get('s_c_out_of_range')} "
                  f"n_tail={m.get('n_tail')} size_max={m.get('size_max')}")
        b_vals = np.array([r["branching_ratio"] for r in rows if r.get("identifiable", True)])
        tau_vals = np.array([r["tau_hat"] for r in rows if r.get("tau_hat") is not None])
        summary[regime] = {
            "b_mean": float(b_vals.mean()), "b_std": float(b_vals.std(ddof=1)) if len(b_vals) > 1 else float("nan"),
            "tau_mean": float(tau_vals.mean()) if len(tau_vals) else float("nan"),
            "tau_std": float(tau_vals.std(ddof=1)) if len(tau_vals) > 1 else float("nan"),
        }
        print(f"  -> b = {summary[regime]['b_mean']:.4f} +/- {summary[regime]['b_std']:.4f}  "
              f"(n={len(b_vals)})")
        print(f"  -> tau_hat = {summary[regime]['tau_mean']:.4f} +/- {summary[regime]['tau_std']:.4f}  "
              f"(n={len(tau_vals)})")

    print("\n=== Verdict D2 (plan tau_hat/b, geometric vs arithmetic) ===")
    g, a = summary["geometric"], summary["arithmetic"]
    print(f"geometric : tau_hat={g['tau_mean']:.4f}+/-{g['tau_std']:.4f}  "
          f"b={g['b_mean']:.4f}+/-{g['b_std']:.4f}")
    print(f"arithmetic: tau_hat={a['tau_mean']:.4f}+/-{a['tau_std']:.4f}  "
          f"b={a['b_mean']:.4f}+/-{a['b_std']:.4f}")
    d_tau = g["tau_mean"] - a["tau_mean"]
    d_tau_se = (g["tau_std"] ** 2 / 3 + a["tau_std"] ** 2 / 3) ** 0.5
    d_b = g["b_mean"] - a["b_mean"]
    d_b_se = (g["b_std"] ** 2 / 3 + a["b_std"] ** 2 / 3) ** 0.5
    print(f"delta tau_hat (geo-arith) = {d_tau:+.4f} (SE~{d_tau_se:.4f})")
    print(f"delta b (geo-arith) = {d_b:+.4f} (SE~{d_b_se:.4f})")


if __name__ == "__main__":
    main()
