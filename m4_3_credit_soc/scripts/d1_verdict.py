"""Compile le verdict D1 (PROMPT_M4_3_FINAL.md §1, livrable §10) : agrège
tous les `analysis.json` de `results/d1/<label>/seed<N>/` en une table par
cellule (moyenne/std inter-graines de la statistique gelée `dagum_c`, de
`branching_ratio` et de `tau_hat`), et une figure (un point par cellule,
barres d'erreur). `tau_hat` (exposant tronqué des avalanches) est déjà
calculé par `campaign_d1._run_and_analyze` et persisté dans chaque
`analysis.json` (`avalanche.tau_hat`) — ajouté ici en agrégation seule,
sans recalcul, pour satisfaire §5 du prompt (« b et l'exposant tronqué α̂
... sont les métriques primaires du plan D1/D2/D3 côté avalanches »),
manquant de la table jusqu'ici (JOURNAL.md §35).
Fonctionne sur une campagne partielle (utile pour suivre l'avancement) ou
complète — signale explicitement le nombre de graines dispo par cellule.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results" / "d1"
OUT_CSV = RESULTS / "d1_verdict_cells.csv"
OUT_FIG = RESULTS / "d1_verdict_plan.png"


def load_all() -> list[dict]:
    rows = []
    for label_dir in sorted(p for p in RESULTS.iterdir() if p.is_dir()):
        for seed_dir in sorted(label_dir.glob("seed*")):
            analysis_path = seed_dir / "analysis.json"
            if not analysis_path.exists():
                continue
            try:
                data = json.loads(analysis_path.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            data["_label"] = label_dir.name
            data["_seed_dir"] = seed_dir.name
            rows.append(data)
    return rows


def aggregate(rows: list[dict]) -> dict[str, dict]:
    by_label: dict[str, list[dict]] = {}
    for r in rows:
        by_label.setdefault(r["_label"], []).append(r)

    cells = {}
    for label, runs in by_label.items():
        ok_runs = [r for r in runs if r.get("status") == "ok"]
        n_severe = sum(1 for r in ok_runs if r.get("severe_nonstationary"))
        c_vals = np.array([r["dagum_c"] for r in ok_runs
                            if r.get("dagum_c") is not None and not r.get("severe_nonstationary")])
        b_vals = np.array([
            (r.get("avalanche") or {}).get("branching_ratio") for r in ok_runs
            if (r.get("avalanche") or {}).get("branching_ratio") is not None
        ])
        tau_vals = np.array([
            (r.get("avalanche") or {}).get("tau_hat") for r in ok_runs
            if (r.get("avalanche") or {}).get("tau_hat") is not None
        ])
        cells[label] = {
            "n_runs_ok": len(ok_runs),
            "n_runs_total": len(runs),
            "n_severe_nonstationary": n_severe,
            "n_c": len(c_vals),
            "dagum_c_mean": float(c_vals.mean()) if len(c_vals) else None,
            "dagum_c_std": float(c_vals.std(ddof=1)) if len(c_vals) > 1 else None,
            "n_b": len(b_vals),
            "b_mean": float(b_vals.mean()) if len(b_vals) else None,
            "b_std": float(b_vals.std(ddof=1)) if len(b_vals) > 1 else None,
            "n_tau": len(tau_vals),
            "tau_hat_mean": float(tau_vals.mean()) if len(tau_vals) else None,
            "tau_hat_std": float(tau_vals.std(ddof=1)) if len(tau_vals) > 1 else None,
        }
    return cells


def write_csv(cells: dict[str, dict], path: Path = OUT_CSV) -> None:
    fieldnames = ["label", "n_runs_ok", "n_runs_total", "n_severe_nonstationary",
                  "n_c", "dagum_c_mean", "dagum_c_std", "n_b", "b_mean", "b_std",
                  "n_tau", "tau_hat_mean", "tau_hat_std"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for label, stats in sorted(cells.items()):
            w.writerow({"label": label, **stats})


def make_figure(cells: dict[str, dict], path: Path = OUT_FIG) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plottable = {k: v for k, v in cells.items() if v["dagum_c_mean"] is not None and v["b_mean"] is not None}
    if not plottable:
        print("Rien à tracer (aucune cellule avec dagum_c ET b disponibles).")
        return

    fig, ax = plt.subplots(figsize=(9, 7))
    for label, s in plottable.items():
        ax.errorbar(s["dagum_c_mean"], s["b_mean"],
                     xerr=s["dagum_c_std"] or 0, yerr=s["b_std"] or 0,
                     fmt="o", capsize=3, label=label)
        ax.annotate(label, (s["dagum_c_mean"], s["b_mean"]), fontsize=7,
                    xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("dagum c (indice de queue supérieure, intérêt — statistique gelée §2)")
    ax.set_ylabel("branching ratio b (avalanches)")
    ax.set_title(f"Plan D1 (dagum_c, b) — {len(plottable)}/{len(cells)} cellules avec données")
    ax.invert_xaxis()  # c decroissant = queue plus epaisse, vers la droite visuellement usuelle
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    print(f"figure écrite : {path}")


OUT_FIG_TAU = RESULTS / "d1_verdict_plan_tau.png"


def make_figure_tau(cells: dict[str, dict], path: Path = OUT_FIG_TAU) -> None:
    """Figure complémentaire (dagum_c, tau_hat) — vérifie que la
    classification D1 (JOURNAL.md §16) tient quel que soit le choix de
    métrique de criticité côté avalanches (b ou tau_hat, toutes deux
    déclarées « primaires » par §5 du prompt). Note : tau_hat est plus
    élevé = queue d'avalanches PLUS FINE (moins critique), sens opposé à
    b — axe non inversé ici pour rester lisible tel quel."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plottable = {k: v for k, v in cells.items()
                 if v["dagum_c_mean"] is not None and v["tau_hat_mean"] is not None}
    if not plottable:
        print("Rien à tracer (aucune cellule avec dagum_c ET tau_hat disponibles).")
        return

    fig, ax = plt.subplots(figsize=(9, 7))
    for label, s in plottable.items():
        ax.errorbar(s["dagum_c_mean"], s["tau_hat_mean"],
                     xerr=s["dagum_c_std"] or 0, yerr=s["tau_hat_std"] or 0,
                     fmt="o", capsize=3, label=label)
        ax.annotate(label, (s["dagum_c_mean"], s["tau_hat_mean"]), fontsize=7,
                    xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("dagum c (indice de queue supérieure, intérêt — statistique gelée §2)")
    ax.set_ylabel("tau_hat (exposant tronqué, avalanches — plus haut = queue plus FINE)")
    ax.set_title(f"Plan D1 (dagum_c, tau_hat) — métrique avalanche alternative à b — "
                 f"{len(plottable)}/{len(cells)} cellules")
    ax.invert_xaxis()
    ax.invert_yaxis()  # tau_hat plus bas = plus critique, même sens visuel que b plus haut
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    print(f"figure écrite : {path}")


def main() -> None:
    rows = load_all()
    cells = aggregate(rows)
    write_csv(cells)
    print(f"{len(rows)} runs chargés, {len(cells)} cellules.")
    print(f"{'cellule':>20} {'n_ok':>5} {'n_c':>4} {'dagum_c':>18} {'n_b':>4} {'b':>18} {'tau_hat':>16} {'sévère':>7}")
    for label, s in sorted(cells.items()):
        c_str = (f"{s['dagum_c_mean']:.3f}±{s['dagum_c_std']:.3f}" if s["dagum_c_std"] is not None
                 else (f"{s['dagum_c_mean']:.3f} (1 graine)" if s["dagum_c_mean"] is not None else "—"))
        b_str = (f"{s['b_mean']:.4f}±{s['b_std']:.4f}" if s["b_std"] is not None
                 else (f"{s['b_mean']:.4f} (1 graine)" if s["b_mean"] is not None else "—"))
        tau_str = (f"{s['tau_hat_mean']:.4f}±{s['tau_hat_std']:.4f}" if s["tau_hat_std"] is not None
                   else (f"{s['tau_hat_mean']:.4f} (1 graine)" if s["tau_hat_mean"] is not None else "—"))
        print(f"{label:>20} {s['n_runs_ok']:>5} {s['n_c']:>4} {c_str:>18} {s['n_b']:>4} {b_str:>18} {tau_str:>16} "
              f"{s['n_severe_nonstationary']:>7}")
    print(f"\ntable écrite : {OUT_CSV}")
    try:
        make_figure(cells)
        make_figure_tau(cells)
    except ImportError:
        print("matplotlib indisponible, figure non générée (table CSV seule).")


if __name__ == "__main__":
    main()
