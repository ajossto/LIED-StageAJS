"""Ré-établit ŝc(λ) sur le moteur M4.2B/M4.3 (k≡2), exigé par
PROMPT_M4_3_FINAL.md §5 (« Ré-établir ŝc(λ) sur le moteur M4.2B (k≡2) avant
de supposer une pente ; si elle diverge de 1,5, le documenter, ne pas
forcer l'accord ») et listé comme limite non close dans
`report/rapport_final.md` §12 (« La coupure d'avalanche ŝc(λ) n'a pas
encore été ré-établie sur ce moteur »).

Analyse pure (AUCUNE nouvelle simulation, aucun pool, aucun garde-fou §7
nécessaire) : les 18 runs D3 (§16/§19-21 du journal, {baseline,
gamma_comp_0.6667} × λ∈{10,30,100} × 3 graines, tous status=ok, aucun
severe_nonstationary) ont leur `avalanches.csv` conservé sur disque
(§7.6/§22 — seul `snapshots/`/`loan_events.csv.gz` sont nettoyés après
analyse). `campaign_d1._run_and_analyze` calcule déjà en interne
`lib_metrics.window_avalanche_metrics` (qui inclut `powerlaw_cutoff`,
donc la coupure s_c elle-même) mais ne persiste dans `analysis.json` qu'un
sous-ensemble tronqué (`branching_ratio`, `tau_hat`, `tau_hat_source`,
`s_c_out_of_range` — PAS la valeur de s_c). Ce script recalcule le même
appel sur les mêmes données/même fenêtre [lo,hi] déjà figée par le run
original (lues depuis `analysis.json`), pour extraire s_c, alpha_pure,
alpha_cutoff, et le LRT tronquée-vs-pure — vérifié bit-identique sur
`branching_ratio`/`tau_hat` avant tout usage (voir `_sanity_check`)."""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import lib_metrics as lm  # noqa: E402

RESULTS_D1 = ROOT / "results" / "d1"
RESULTS_D3 = ROOT / "results" / "d3_size"
OUT_CSV = RESULTS_D3 / "d3_cutoff_scaling_runs.csv"
OUT_CELLS_CSV = RESULTS_D3 / "d3_cutoff_scaling_cells.csv"
OUT_FIG = RESULTS_D3 / "sc_vs_lambda.png"

# (label affiché, dossier, lambda)
RUN_DIRS = [
    ("baseline", 10.0, RESULTS_D3 / "baseline_lam10"),
    ("baseline", 30.0, RESULTS_D1 / "baseline"),
    ("baseline", 100.0, RESULTS_D3 / "baseline_lam100"),
    ("gamma_comp_0.6667", 10.0, RESULTS_D3 / "gamma_comp_0.6667_lam10"),
    ("gamma_comp_0.6667", 30.0, RESULTS_D1 / "gamma_comp_0.6667"),
    ("gamma_comp_0.6667", 100.0, RESULTS_D3 / "gamma_comp_0.6667_lam100"),
]

S_MIN = 2  # convention M4B/M4.2B, identique à campaign_d1.py
rows_by_cell: dict[tuple[str, float], list[dict]] = {}  # peuplé par main(), lu par make_figure()


def _sanity_check(run_dir: Path, stored: dict, recomputed: dict) -> None:
    """Le run original a déjà calculé ces deux valeurs ; on vérifie qu'on
    retombe bit-identique dessus avant de faire confiance au reste
    (powerlaw_cutoff notamment, jamais persisté par le run original)."""
    for key in ("branching_ratio", "tau_hat"):
        a, b = stored.get(key), recomputed.get(key)
        if a is None or b is None:
            continue
        if not math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9):
            raise RuntimeError(f"{run_dir}: {key} stored={a} recomputed={b} — désaccord, "
                                f"fenêtre ou s_min divergents, ne pas faire confiance au reste")


def analyze_one(run_dir: Path) -> dict | None:
    analysis_path = run_dir / "analysis.json"
    if not analysis_path.exists():
        return None
    stored = json.loads(analysis_path.read_text())
    if stored.get("status") != "ok" or stored.get("severe_nonstationary"):
        return None
    lo, hi, pop_mean = stored["lo"], stored["hi"], stored["pop_mean"]
    av = lm.read_avalanches(run_dir)
    metrics = lm.window_avalanche_metrics(av, lo, hi, pop_mean, s_min=S_MIN)
    if not metrics.get("identifiable"):
        return None
    _sanity_check(run_dir, stored.get("avalanche") or {}, metrics)

    cutoff = metrics.get("powerlaw_cutoff") or {}
    pure = metrics.get("powerlaw") or {}
    lrt = metrics.get("lrt_cutoff_vs_pure") or {}
    return {
        "run_dir": str(run_dir.relative_to(ROOT)),
        "n_tail": metrics.get("n_tail"),
        "size_max": metrics.get("size_max"),
        "s_c": cutoff.get("cutoff"),
        "alpha_cutoff": cutoff.get("alpha"),
        "alpha_pure": pure.get("alpha"),
        "alpha_pure_se": pure.get("se"),
        "s_c_out_of_range": metrics.get("s_c_out_of_range"),
        "tau_hat": metrics.get("tau_hat"),
        "tau_hat_source": metrics.get("tau_hat_source"),
        "branching_ratio": metrics.get("branching_ratio"),
        "lrt_statistic": lrt.get("statistic"),
        "lrt_p_value": lrt.get("p_value"),
    }


def load_runs() -> list[dict]:
    rows = []
    for branch, lam, cell_dir in RUN_DIRS:
        for seed_dir in sorted(cell_dir.glob("seed*")):
            r = analyze_one(seed_dir)
            if r is None:
                print(f"  [skip] {seed_dir} (absent, échoué, sévère, ou non identifiable)")
                continue
            r["branch"] = branch
            r["lam"] = lam
            r["seed_dir"] = seed_dir.name
            rows.append(r)
    return rows


def write_runs_csv(rows: list[dict], path: Path = OUT_CSV) -> None:
    fieldnames = ["branch", "lam", "seed_dir", "run_dir", "n_tail", "size_max",
                  "s_c", "alpha_cutoff", "alpha_pure", "alpha_pure_se",
                  "s_c_out_of_range", "tau_hat", "tau_hat_source",
                  "branching_ratio", "lrt_statistic", "lrt_p_value"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fieldnames})


def aggregate_cells(rows: list[dict]) -> dict[tuple[str, float], dict]:
    """IMPORTANT (corrigé après relecture, JOURNAL.md §35bis) : ne JAMAIS
    faire la moyenne de s_c sur le sous-ensemble des graines `in_range`
    d'une cellule où certaines graines sont in-range et d'autres non — ce
    serait sélectionner après coup la graine qui donne le résultat
    (interdit §6 du prompt : « ne jamais sélectionner après coup graines,
    snapshots ou seuils »). `s_c_mean` n'est calculé QUE si les 3/3
    graines de la cellule sont in-range (unanime) ; sinon la cellule est
    marquée `reliable=False` et son s_c n'est PAS utilisable pour une
    pente — seule information gardée : la proportion in-range, à titre
    diagnostique."""
    by_cell: dict[tuple[str, float], list[dict]] = {}
    for r in rows:
        by_cell.setdefault((r["branch"], r["lam"]), []).append(r)

    cells = {}
    for key, runs in by_cell.items():
        n = len(runs)
        n_in_range = sum(1 for r in runs if r["s_c_out_of_range"] is False)
        n_out_of_range = sum(1 for r in runs if r["s_c_out_of_range"] is True)
        reliable = (n_in_range == n)  # unanime seulement
        s_c_vals = np.array([r["s_c"] for r in runs if r["s_c"] is not None]) if reliable else np.array([])
        alpha_c_vals = np.array([r["alpha_cutoff"] for r in runs if r["alpha_cutoff"] is not None]) if reliable else np.array([])
        alpha_p_vals = np.array([r["alpha_pure"] for r in runs if r["alpha_pure"] is not None])
        tau_sources = sorted({r["tau_hat_source"] for r in runs if r["tau_hat_source"]})
        tau_vals = np.array([r["tau_hat"] for r in runs if r["tau_hat"] is not None])
        cells[key] = {
            "n_runs": n,
            "n_in_range": n_in_range,
            "n_out_of_range": n_out_of_range,
            "reliable": reliable,
            "s_c_mean": float(s_c_vals.mean()) if len(s_c_vals) else None,
            "s_c_std": float(s_c_vals.std(ddof=1)) if len(s_c_vals) > 1 else None,
            "alpha_cutoff_mean": float(alpha_c_vals.mean()) if len(alpha_c_vals) else None,
            "alpha_pure_mean": float(alpha_p_vals.mean()) if len(alpha_p_vals) else None,
            "alpha_pure_std": float(alpha_p_vals.std(ddof=1)) if len(alpha_p_vals) > 1 else None,
            "tau_hat_sources": "+".join(tau_sources),
            "tau_hat_mean": float(tau_vals.mean()) if len(tau_vals) else None,
            "tau_hat_std": float(tau_vals.std(ddof=1)) if len(tau_vals) > 1 else None,
        }
    return cells


def write_cells_csv(cells: dict[tuple[str, float], dict], path: Path = OUT_CELLS_CSV) -> None:
    fieldnames = ["branch", "lam", "n_runs", "n_in_range", "n_out_of_range", "reliable",
                  "s_c_mean", "s_c_std", "alpha_cutoff_mean",
                  "alpha_pure_mean", "alpha_pure_std", "tau_hat_sources",
                  "tau_hat_mean", "tau_hat_std"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for (branch, lam), stats in sorted(cells.items()):
            w.writerow({"branch": branch, "lam": lam, **stats})


def leg_slope(lam1: float, sc1: float, lam2: float, sc2: float) -> float:
    """Pente log-log locale entre deux points adjacents (pas un OLS global
    sur 3 points, qui moyennerait sur une éventuelle convexité et masquerait
    un comportement différent par tronçon — voir JOURNAL.md §35bis)."""
    return float(math.log(sc2 / sc1) / math.log(lam2 / lam1))


def make_figure(cells: dict[tuple[str, float], dict], path: Path = OUT_FIG) -> None:
    """Points fiables (3/3 graines in-range) en trait plein ; points non
    fiables (cellule partiellement/totalement hors-portée) en marqueur
    creux, SANS ligne les reliant aux points fiables — une ligne pleine
    suggérerait une pente mesurée là où elle ne l'est pas (JOURNAL.md
    §35bis)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.5, 6))
    colors = {"baseline": "tab:blue", "gamma_comp_0.6667": "tab:orange"}
    for branch in ("baseline", "gamma_comp_0.6667"):
        reliable_pts = [(lam, s["s_c_mean"], s["s_c_std"]) for (b, lam), s in sorted(cells.items())
                        if b == branch and s["reliable"] and s["s_c_mean"] is not None]
        unreliable_pts = [(lam, s) for (b, lam), s in sorted(cells.items())
                          if b == branch and not s["reliable"]]
        c = colors[branch]
        if reliable_pts:
            lams = [p[0] for p in reliable_pts]
            s_cs = [p[1] for p in reliable_pts]
            errs = [p[2] or 0 for p in reliable_pts]
            ax.errorbar(lams, s_cs, yerr=errs, fmt="o-", capsize=3, color=c,
                        label=f"{branch} (fiable, 3/3 graines in-range)")
        for lam, s in unreliable_pts:
            # affiche chaque graine individuellement (pas de moyenne biaisée)
            seed_vals = [r["s_c"] for r in rows_by_cell.get((branch, lam), [])
                        if r["s_c"] is not None]
            ax.scatter([lam] * len(seed_vals), seed_vals, marker="x", color=c, alpha=0.6,
                      label=f"{branch} λ={lam:g} (NON fiable, {s['n_in_range']}/3 in-range, "
                            f"graines individuelles)")
    # repère M4B (k=3), leg 10->30 UNIQUEMENT (seule mesurée dans le prompt §5) :
    # s_c(10)=10.0 -> s_c(30)=51.6, pente 1,49 sur cette jambe précise
    ax.plot([10, 30], [10.0, 51.6], "k--", alpha=0.6,
           label="repère M4B k=3 (jambe 10→30 mesurée, pente≈1,49)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("λ (Config.lam)")
    ax.set_ylabel("ŝc (coupure MLE loi tronquée)")
    ax.set_title("ŝc(λ) ré-établi à k≡2 (M4.3/D3) vs repère M4B (k=3, jambe 10→30 seule)")
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    print(f"figure écrite : {path}")


def main() -> None:
    global rows_by_cell
    print("Chargement + recalcul (aucune simulation, données déjà sur disque)...")
    rows = load_runs()
    print(f"{len(rows)}/18 runs exploitables (identifiables, non sévères).")
    write_runs_csv(rows)
    print(f"table runs écrite : {OUT_CSV}")

    rows_by_cell = {}
    for r in rows:
        rows_by_cell.setdefault((r["branch"], r["lam"]), []).append(r)

    cells = aggregate_cells(rows)
    write_cells_csv(cells)
    print(f"table cellules écrite : {OUT_CELLS_CSV}")

    print(f"\n{'branche':>20} {'λ':>5} {'in_range':>9} {'fiable':>7} {'s_c':>16} "
          f"{'alpha_cutoff':>14} {'alpha_pure':>12}")
    for (branch, lam), s in sorted(cells.items()):
        sc_str = (f"{s['s_c_mean']:.2f}±{s['s_c_std']:.2f}" if s["s_c_std"] is not None
                  else (f"{s['s_c_mean']:.2f} (1 graine)" if s["s_c_mean"] is not None
                        else "non calculé (pas unanime)"))
        ac_str = f"{s['alpha_cutoff_mean']:.3f}" if s["alpha_cutoff_mean"] is not None else "—"
        ap_str = f"{s['alpha_pure_mean']:.3f}" if s["alpha_pure_mean"] is not None else "—"
        print(f"{branch:>20} {lam:>5.0f} {s['n_in_range']:>6}/3  {str(s['reliable']):>7} {sc_str:>16} "
              f"{ac_str:>14} {ap_str:>12}")

    print("\nPentes log-log LOCALES (jambe à jambe, uniquement entre cellules FIABLES) :")
    print(f"  repère M4B k=3, jambe 10->30 (10,0->51,6) : pente={leg_slope(10, 10.0, 30, 51.6):.3f}")
    for branch in ("baseline", "gamma_comp_0.6667"):
        by_lam = {lam: s for (b, lam), s in cells.items() if b == branch}
        lams_sorted = sorted(by_lam)
        for lam1, lam2 in zip(lams_sorted, lams_sorted[1:]):
            s1, s2 = by_lam[lam1], by_lam[lam2]
            if s1["reliable"] and s2["reliable"] and s1["s_c_mean"] and s2["s_c_mean"]:
                sl = leg_slope(lam1, s1["s_c_mean"], lam2, s2["s_c_mean"])
                print(f"  {branch} λ={lam1:g}->{lam2:g}: pente={sl:.3f} (jambe fiable)")
            else:
                print(f"  {branch} λ={lam1:g}->{lam2:g}: NON calculable proprement "
                      f"({'λ='+str(lam1)+' non fiable' if not s1['reliable'] else 'λ='+str(lam2)+' non fiable'}, "
                      f"extrapolation hors fenêtre observable)")

    try:
        make_figure(cells)
    except ImportError:
        print("matplotlib indisponible, figure non générée (tables CSV seules).")


if __name__ == "__main__":
    main()
