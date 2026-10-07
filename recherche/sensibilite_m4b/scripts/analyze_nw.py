"""Analyse dédiée à la valeur nette NW = K + C - D et aux positions nettes.

Extension post-audit de la campagne (aucun nouveau run) : exploite les
stats NW déjà présentes dans les JSON de métriques, les instantanés
(claims/debts/age/K/nw par entité) et deaths.csv.

Produit :
- results/summary/nw_oat.csv, nw_lhs.csv, nw_confirm.csv : métriques NW
  par run (Gini NW, quantiles, part nette débitrice, corrélations de
  rang position-âge, etc.) ;
- results/summary/nw_screening.csv : PRCC des métriques NW sur le plan LHS ;
- results/summary/nw_confirm_contrasts.csv : contrastes appariés
  (graines 11-15, vs centre) avec IC 95 % et comparaison exploratoire ;
- figures/nw_sensibilite.png : sensibilité des inégalités de bilan et du
  mix des causes de décès (axe sigma prolongé à 1 par les sondes) ;
- figures/nw_structure.png : CCDF de NW, cycle de vie de la position
  nette, bilans de décès.

Étiquetage : les contrastes NW sont une extension post-hoc (réponses
nouvelles sur les mêmes runs confirmatoires pré-enregistrés).
"""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_runs as L
import lib_screening as S

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

LAB_RUNS = Path("/home/anatole/jupyter/simulation_lab_data/runs")
SUMMARY = L.CAMPAIGN_ROOT / "results" / "summary"
FIG_DIR = L.CAMPAIGN_ROOT / "figures"
METRICS = L.CAMPAIGN_ROOT / "results" / "metrics"
METRICS_CONFIRM = L.CAMPAIGN_ROOT / "results" / "metrics_confirm"

NW_KEYS = ("gini_nw", "nw_median", "nw_top10", "frac_net_debtor", "spearman_x_age")


def last_snapshot(directory: Path) -> dict | None:
    files = sorted((directory / "snapshots").glob("entities_t*.npz"))
    if not files:
        return None
    with np.load(files[-1]) as data:
        return {key: data[key].copy() for key in data.files}


def nw_row_from_run(directory: Path, metrics_path: Path) -> dict | None:
    """Métriques NW d'un run : stats du JSON + positions nettes du snapshot."""
    if not metrics_path.exists():
        return None
    metrics = json.loads(metrics_path.read_text())
    snap_stats = metrics.get("final_snapshot", {})
    nw_stats = snap_stats.get("nw") or {}
    snap = last_snapshot(directory)
    if snap is None or len(snap.get("id", ())) < 20:
        return None
    x = snap["claims"] - snap["debts"]
    K = snap["K"]
    nw = snap["nw"]
    age = snap["age"]
    ratio = x / np.maximum(K, 1e-9)
    p = metrics["parameters"]
    return {
        "run_id": metrics["run_id"],
        "lam": p["lam"], "delta": p["delta"], "sigma": p["sigma"],
        "K0": p["K0"], "k": p["k"], "seed": p["seed"], "T": p["T"],
        "n_entities": int(len(nw)),
        "gini_nw": nw_stats.get("gini_nonneg"),
        "nw_mean": nw_stats.get("mean"),
        "nw_median": nw_stats.get("median"),
        "nw_q99": nw_stats.get("q99"),
        "nw_max": nw_stats.get("max"),
        "nw_top10": nw_stats.get("top10_share"),
        "nw_log_std": nw_stats.get("log_std"),
        "gini_K": (snap_stats.get("K") or {}).get("gini_nonneg"),
        "frac_net_debtor": float((x < 0).mean()),
        "spearman_x_age": float(stats.spearmanr(x, age).statistic),
        "spearman_nw_age": float(stats.spearmanr(nw, age).statistic),
        "spearman_nw_K": float(stats.spearmanr(nw, K).statistic),
        "x_over_K_q05": float(np.quantile(ratio, 0.05)),
        "x_over_K_q50": float(np.quantile(ratio, 0.50)),
        "x_over_K_q95": float(np.quantile(ratio, 0.95)),
        "nw_min": float(nw.min()),
    }


def build_plan_table(plan: str, out_name: str) -> list[dict]:
    rows = []
    for spec in L.load_plan(plan):
        directory = L.run_dir(spec)
        row = nw_row_from_run(directory, METRICS / f"{L.run_id(spec)}.json")
        if row:
            rows.append(row)
    _write(SUMMARY / out_name, rows)
    return rows


def build_confirm_table() -> tuple[list[dict], dict]:
    manifest = json.loads((L.CAMPAIGN_ROOT / "manifests" / "confirm_lab.json").read_text())
    rows, deaths_info = [], {}
    for entry in manifest["cells"]:
        if entry["cell"] == "lam2_ext":
            continue
        for run_id in entry["run_ids"]:
            directory = LAB_RUNS / run_id
            row = nw_row_from_run(directory, METRICS_CONFIRM / f"{run_id}.json")
            if not row:
                continue
            row["cell"] = entry["cell"]
            row["lab_run_id"] = run_id
            # bilans de décès dans la fenêtre
            burn = entry["parameters"]["T"] // 4
            with (directory / "deaths.csv").open() as stream:
                deaths = [r for r in csv.DictReader(stream) if int(r["t"]) >= burn]
            nw_death = np.array([float(r["nw"]) for r in deaths])
            causes = [r["cause"] for r in deaths]
            row["n_deaths"] = len(deaths)
            row["death_nw_median"] = float(np.median(nw_death))
            row["death_nw_q05"] = float(np.quantile(nw_death, 0.05))
            row["death_frac_nw_neg"] = float((nw_death < 0).mean())
            row["death_frac_liquidity"] = causes.count("liquidity") / len(causes)
            rows.append(row)
            deaths_info.setdefault(entry["cell"], []).append((nw_death, causes))
    _write(SUMMARY / "nw_confirm.csv", rows)
    return rows, deaths_info


def _write(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)
    print(path, len(rows), "lignes")


def screening_lhs(rows: list[dict]) -> None:
    X = np.array([[r["delta"], r["sigma"], np.log10(r["K0"]), r["k"]] for r in rows])
    groups = np.array([hash((r["delta"], r["sigma"], r["K0"], r["k"])) for r in rows])
    out = []
    for metric in ("gini_nw", "nw_median", "nw_top10", "frac_net_debtor",
                   "spearman_x_age", "nw_log_std"):
        y = np.array([r[metric] if r[metric] is not None else np.nan for r in rows])
        keep = np.isfinite(y)
        prcc = S.prcc(X[keep], y[keep])
        decomposition = S.variance_decomposition(y[keep], groups[keep])
        r2cv = S.cv_r2_by_group(S.QuadraticSurface, X[keep], y[keep], groups[keep])
        out.append({"metric": metric, "n": int(keep.sum()),
                    "prcc_delta": round(float(prcc[0]), 3),
                    "prcc_sigma": round(float(prcc[1]), 3),
                    "prcc_logK0": round(float(prcc[2]), 3),
                    "prcc_k": round(float(prcc[3]), 3),
                    "r2_cv_quadratic": round(float(r2cv), 3),
                    "var_between_frac": round(float(decomposition["var_between_frac"]), 3)})
        print(out[-1])
    _write(SUMMARY / "nw_screening.csv", out)


def confirm_contrasts(rows: list[dict], oat_rows: list[dict]) -> None:
    by_cell: dict[str, dict[int, dict]] = defaultdict(dict)
    for row in rows:
        by_cell[row["cell"]][row["seed"]] = row
    center = by_cell["centre_lam30"]

    def explo_mean(params: tuple, metric: str) -> float:
        values = [r[metric] for r in oat_rows
                  if (r["lam"], r["delta"], r["sigma"], r["K0"], r["k"]) == params
                  and r[metric] is not None]
        return float(np.mean(values)) if values else np.nan

    center_params = (30.0, 0.05, 0.25, 25.0, 3)
    out = []
    for cell, seeds in by_cell.items():
        if cell == "centre_lam30":
            continue
        sample = next(iter(seeds.values()))
        params = (sample["lam"], sample["delta"], sample["sigma"],
                  sample["K0"], sample["k"])
        for metric in NW_KEYS:
            pairs = [seeds[s][metric] - center[s][metric]
                     for s in seeds if s in center
                     and seeds[s][metric] is not None and center[s][metric] is not None]
            if len(pairs) < 3:
                continue
            pairs = np.asarray(pairs, dtype=float)
            mean = float(pairs.mean())
            half = float(stats.t.ppf(0.975, len(pairs) - 1)
                         * pairs.std(ddof=1) / np.sqrt(len(pairs)))
            d_explo = explo_mean(params, metric) - explo_mean(center_params, metric)
            ci_excl = (mean - half) * (mean + half) > 0
            same_sign = np.isfinite(d_explo) and d_explo * mean > 0
            mag = (np.isfinite(d_explo) and abs(d_explo) > 0
                   and 0.5 <= abs(mean) / abs(d_explo) <= 2.0)
            if not np.isfinite(d_explo):
                verdict = "sans-explo"
            elif ci_excl and same_sign and mag:
                verdict = "CONFIRMÉ"
            elif ci_excl and same_sign:
                verdict = "signe-ok"
            elif not ci_excl and abs(d_explo) < 2 * half:
                verdict = "nul-cohérent"
            else:
                verdict = "NON-CONF"
            out.append({"cell": cell, "metric": metric,
                        "delta_confirm": round(mean, 5), "ci_half": round(half, 5),
                        "delta_explo": round(float(d_explo), 5) if np.isfinite(d_explo) else "",
                        "verdict": verdict, "n_pairs": len(pairs)})
    _write(SUMMARY / "nw_confirm_contrasts.csv", out)
    counts = defaultdict(int)
    for row in out:
        counts[row["verdict"]] += 1
    print("verdicts NW :", dict(counts))


# ------------------------------------------------------------------ figures

def figure_sensibilite(oat_rows: list[dict]) -> None:
    with (SUMMARY / "oat.csv").open() as stream:
        oat_flat = list(csv.DictReader(stream))
    with (SUMMARY / "pilotes2.csv").open() as stream:
        p2_flat = list(csv.DictReader(stream))

    def axis_cells(axis: str):
        centre = dict(lam=30.0, delta=0.05, sigma=0.25, K0=25.0, k=3)
        grouped = defaultdict(list)
        for r in oat_rows:
            key = dict(lam=r["lam"], delta=r["delta"], sigma=r["sigma"],
                       K0=r["K0"], k=r["k"])
            diffs = [n for n in centre if float(key[n]) != centre[n]]
            if diffs == [] or diffs == [axis]:
                grouped[float(key[axis])].append(r)
        return dict(sorted(grouped.items()))

    fig, axes = plt.subplots(2, 3, figsize=(16.5, 8.6))

    for panel, axis_name, xlabel, logx in (
        (axes[0][0], "sigma", "σ", False), (axes[0][1], "k", "k", False),
        (axes[0][2], "K0", "K₀", True), (axes[1][0], "delta", "δ", False),
    ):
        cells = axis_cells(axis_name)
        xs = list(cells)
        for metric, label, color in (("gini_nw", "Gini de NW", "C3"),
                                     ("gini_K", "Gini de K", "C0")):
            means = [np.mean([r[metric] for r in cells[v]]) for v in xs]
            sds = [np.std([r[metric] for r in cells[v]]) for v in xs]
            panel.errorbar(xs, means, yerr=sds, marker="o", ms=4, capsize=3,
                           color=color, label=label)
        panel.set_xlabel(xlabel); panel.grid(alpha=0.25); panel.legend(fontsize=8)
        if logx:
            panel.set_xscale("log")
        panel.set_title(f"Inégalités de bilan le long de {xlabel}", fontsize=10)

    # position nette et cycle de vie le long de sigma
    panel = axes[1][1]
    cells = axis_cells("sigma")
    xs = list(cells)
    for metric, label, color in (("frac_net_debtor", "part nette débitrice", "C2"),
                                 ("spearman_x_age", "Spearman(C−D, âge)", "C4")):
        means = [np.mean([r[metric] for r in cells[v]]) for v in xs]
        sds = [np.std([r[metric] for r in cells[v]]) for v in xs]
        panel.errorbar(xs, means, yerr=sds, marker="s", ms=4, capsize=3,
                       color=color, label=label)
    panel.set_xlabel("σ"); panel.grid(alpha=0.25); panel.legend(fontsize=8)
    panel.set_title("Position nette C−D le long de σ", fontsize=10)

    # mix des causes de décès, sigma 0 -> 1 (OAT + sondes pilotes2)
    panel = axes[1][2]
    mix = defaultdict(lambda: defaultdict(list))
    for r in oat_flat + p2_flat:
        if (float(r["lam"]), float(r["delta"]), float(r["K0"]), int(r["k"])) \
                != (30.0, 0.05, 25.0, 3):
            continue
        s = float(r["sigma"])
        for cause in ("cause_liquidity", "cause_insolvency", "cause_cascade"):
            if r.get(cause):
                mix[s][cause].append(float(r[cause]))
    xs = sorted(mix)
    bottom = np.zeros(len(xs))
    colors = {"cause_insolvency": "#b53d3d", "cause_cascade": "#e0a13c",
              "cause_liquidity": "#3d6fb5"}
    labels = {"cause_insolvency": "insolvabilité (racine)",
              "cause_cascade": "cascade (induite)",
              "cause_liquidity": "défaut de service"}
    for cause in ("cause_insolvency", "cause_cascade", "cause_liquidity"):
        values = np.array([np.mean(mix[s][cause]) if mix[s][cause] else 0.0
                           for s in xs])
        panel.bar([f"{s:g}" for s in xs], values, bottom=bottom,
                  color=colors[cause], label=labels[cause], width=0.75)
        bottom += values
    panel.set_xlabel("σ"); panel.set_ylabel("part des décès")
    panel.set_title("Causes de décès, σ de 0 à 1\n(σ>0,5 : sondes, 2 graines)",
                    fontsize=10)
    panel.legend(fontsize=8); panel.grid(alpha=0.2, axis="y")

    fig.suptitle("Valeur nette et positions de crédit — sensibilité "
                 "(OAT graines 1-3, T=2000, instantané final ; exploratoire)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "nw_sensibilite.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


def figure_structure(confirm_rows: list[dict], deaths_info: dict) -> None:
    manifest = json.loads((L.CAMPAIGN_ROOT / "manifests" / "confirm_lab.json").read_text())
    cells = {entry["cell"]: entry for entry in manifest["cells"]}
    fig, axes = plt.subplots(2, 2, figsize=(14.5, 10))

    # (a) CCDF de NW par graine
    panel = axes[0][0]
    for index, cell in enumerate(("centre_lam30", "sigma0", "k2", "k10")):
        for pos, run_id in enumerate(cells[cell]["run_ids"]):
            snap = last_snapshot(LAB_RUNS / run_id)
            values = np.sort(snap["nw"][snap["nw"] > 0])[::-1]
            ccdf = np.arange(1, len(values) + 1) / len(values)
            panel.loglog(values, ccdf, lw=0.8, alpha=0.6, color=f"C{index}",
                         label=cell if pos == 0 else None)
    panel.set_xlabel("NW (J)"); panel.set_ylabel("CCDF")
    panel.set_title("CCDF de la valeur nette — une courbe par graine", fontsize=10)
    panel.grid(alpha=0.25, which="both"); panel.legend(fontsize=8)

    # (b) position nette relative par âge (médane par tranche, par graine)
    panel = axes[0][1]
    for index, cell in enumerate(("centre_lam30", "sigma0", "k10")):
        for pos, run_id in enumerate(cells[cell]["run_ids"]):
            snap = last_snapshot(LAB_RUNS / run_id)
            x = (snap["claims"] - snap["debts"]) / np.maximum(snap["K"], 1e-9)
            age = snap["age"]
            edges = np.quantile(age, np.linspace(0, 1, 13))
            edges = np.unique(edges)
            centres, medians = [], []
            for lo, hi in zip(edges[:-1], edges[1:]):
                mask = (age >= lo) & (age <= hi)
                if mask.sum() >= 5:
                    centres.append((lo + hi) / 2)
                    medians.append(np.median(x[mask]))
            panel.plot(centres, medians, lw=0.9, alpha=0.6, color=f"C{index}",
                       label=cell if pos == 0 else None)
    panel.axhline(0, color="k", lw=0.7)
    panel.set_xlabel("âge (pas)"); panel.set_ylabel("médiane de (C−D)/K par tranche d'âge")
    panel.set_title("Cycle de vie de la position nette de crédit", fontsize=10)
    panel.grid(alpha=0.25); panel.legend(fontsize=8)

    # (c) NW au décès par cause (centre)
    panel = axes[1][0]
    for pos, (nw_death, causes) in enumerate(deaths_info["centre_lam30"]):
        causes = np.array(causes)
        for cause, color in (("insolvency", "#b53d3d"), ("cascade", "#e0a13c")):
            values = nw_death[causes == cause]
            hist, edges = np.histogram(values, bins=np.linspace(-45, 5, 51),
                                       density=True)
            panel.plot((edges[:-1] + edges[1:]) / 2, hist, lw=0.8, alpha=0.6,
                       color=color,
                       label=f"{cause}" if pos == 0 else None)
    panel.axvline(0, color="k", lw=0.7)
    panel.set_xlabel("NW au décès (J)"); panel.set_ylabel("densité")
    panel.set_title("Bilan au décès, centre (5 graines superposées)", fontsize=10)
    panel.grid(alpha=0.25); panel.legend(fontsize=8)

    # (d) synthèse par cellule
    panel = axes[1][1]
    order = ["sigma0", "sigma010", "centre_lam30", "sigma050", "k2", "k10",
             "delta002", "delta010", "K0_5", "K0_100"]
    by_cell = defaultdict(list)
    for row in confirm_rows:
        by_cell[row["cell"]].append(row)
    names = [c for c in order if c in by_cell]
    for metric, color, label in (("gini_nw", "C3", "Gini NW"),
                                 ("gini_K", "C0", "Gini K"),
                                 ("frac_net_debtor", "C2", "part nette débitrice")):
        means = [np.mean([r[metric] for r in by_cell[c]]) for c in names]
        sds = [np.std([r[metric] for r in by_cell[c]]) for c in names]
        panel.errorbar(range(len(names)), means, yerr=sds, marker="o", ms=4,
                       capsize=3, color=color, label=label, lw=1)
    panel.set_xticks(range(len(names)), names, rotation=35, fontsize=8)
    panel.set_title("Bilans par cellule confirmatoire (5 graines)", fontsize=10)
    panel.grid(alpha=0.25); panel.legend(fontsize=8)

    fig.suptitle("Structure de la valeur nette — cellules confirmatoires "
                 "(graines 11-15, T=4000)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "nw_structure.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    oat_rows = build_plan_table("oat", "nw_oat.csv")
    lhs_rows = build_plan_table("lhs", "nw_lhs.csv")
    confirm_rows, deaths_info = build_confirm_table()
    print("\n--- screening PRCC (LHS) des métriques NW ---")
    screening_lhs(lhs_rows)
    print("\n--- contrastes confirmatoires NW (extension post-hoc) ---")
    confirm_contrasts(confirm_rows, oat_rows)
    figure_sensibilite(oat_rows)
    figure_structure(confirm_rows, deaths_info)
    print("\nfigures :", FIG_DIR / "nw_sensibilite.png", FIG_DIR / "nw_structure.png")


if __name__ == "__main__":
    main()
