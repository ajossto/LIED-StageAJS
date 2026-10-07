"""Cycles agrégés de M4B : périodes de croissance/récession de l'activité.

Extension post-audit sans nouveau run. Série primaire historique : la
production totale par pas (prod_tot, analogue du PIB). Contrôle ajouté
le 27 juillet 2026 : énergie totale présente dans le système (K_tot),
conformément au critère de validation retenu par l'auteur. Série
secondaire : la population. Fenêtre [T/4, t_fin], analyse en log.

Définitions figées :
- épisode : suite maximale de variations de même signe de log(prod_tot)
  (expansion : signe +, récession : signe -) ; une variation nulle
  prolonge l'épisode en cours ;
- taille « indicielle » d'un épisode : son amplitude en log-niveau
  A = |log X_fin - log X_début| ; taille « temporelle » : sa durée en pas ;
- fréquence temporelle : épisodes par millier de pas, et temps de
  mémoire tau_int du log-niveau (autocorrélation intégrée) ;
- lissage : les mêmes statistiques sont recalculées sur la moyenne
  mobile à w = 5 et w = 25 pas (robustesse et structure multi-échelle) ;
  sous l'hypothèse nulle d'accroissements i.i.d. symétriques (w=1),
  la durée moyenne d'un épisode vaut 2 pas exactement.

Sorties : results/summary/cycles_{oat,lhs,confirm}.csv,
cycles_screening.csv (PRCC LHS), cycles_confirm_contrasts.csv
(contrastes appariés graines 11-15, extension post-hoc étiquetée),
figures/cycles_sensibilite.png, figures/cycles_structure.png.
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
from lib_metrics import integrated_autocorr

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

LAB_RUNS = Path("/home/anatole/jupyter/simulation_lab_data/runs")
SUMMARY = L.CAMPAIGN_ROOT / "results" / "summary"
FIG_DIR = L.CAMPAIGN_ROOT / "figures"

WINDOWS = (1, 5, 25)


# ----------------------------------------------------------- extraction

def episodes(y: np.ndarray, w: int) -> list[tuple[int, int, float]]:
    """Épisodes (signe, durée, amplitude log) de la série y, lissée à w."""
    if w > 1:
        y = np.convolve(y, np.ones(w) / w, mode="valid")
    d = np.sign(np.diff(y))
    for i in range(1, len(d)):
        if d[i] == 0:
            d[i] = d[i - 1]
    out, start = [], 0
    for i in range(1, len(d)):
        if d[i] != d[start]:
            out.append((int(d[start]), i - start, float(abs(y[i] - y[start]))))
            start = i
    out.append((int(d[start]), len(d) - start, float(abs(y[-1] - y[start]))))
    return out


def _phase_stats(runs, sign):
    durations = np.array([l for s, l, _ in runs if s == sign])
    amplitudes = np.array([a for s, _, a in runs if s == sign])
    if len(durations) == 0:
        return {}
    return {
        "n": int(len(durations)),
        "dur_mean": float(durations.mean()),
        "dur_q90": float(np.quantile(durations, 0.9)),
        "dur_max": int(durations.max()),
        "amp_mean": float(amplitudes.mean()),
        "amp_q90": float(np.quantile(amplitudes, 0.9)),
        "amp_max": float(amplitudes.max()),
        "slope_mean": float(amplitudes.sum() / durations.sum()),
    }


def cycle_metrics(series_path: Path, T: int, t_final: int) -> dict | None:
    with series_path.open() as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        return None
    prod = np.array([float(r["prod_tot"]) for r in rows])
    energy = np.array([float(r["K_tot"]) for r in rows])
    pop = np.array([float(r["pop"]) for r in rows])
    burn = T // 4
    if (t_final - burn < 300 or np.any(prod[burn:] <= 0)
            or np.any(energy[burn:] <= 0)):
        return None
    y = np.log(prod[burn:])
    dy = np.diff(y)
    steps = len(dy)

    out = {
        "sd_dlog": float(dy.std()),
        "acf1_dlog": float(np.corrcoef(dy[:-1], dy[1:])[0, 1]),
        "skew_dlog": float(stats.skew(dy)),
        "tau_int_logprod": float(integrated_autocorr(y)),
        "sd_dlog_pop": float(np.diff(np.log(np.maximum(pop[burn:], 1))).std()),
    }
    for w in WINDOWS:
        runs = episodes(y, w)
        exp_stats = _phase_stats(runs, +1)
        rec_stats = _phase_stats(runs, -1)
        if not exp_stats or not rec_stats:
            return None
        prefix = f"w{w}_"
        for name, block in (("exp", exp_stats), ("rec", rec_stats)):
            for key, value in block.items():
                out[f"{prefix}{name}_{key}"] = value
        out[f"{prefix}rate_per_1000"] = 1000.0 * (exp_stats["n"] + rec_stats["n"]) / steps
        out[f"{prefix}cycle_len"] = exp_stats["dur_mean"] + rec_stats["dur_mean"]
        out[f"{prefix}slope_ratio_rec_exp"] = rec_stats["slope_mean"] / exp_stats["slope_mean"]
        out[f"{prefix}dur_ratio_exp_rec"] = exp_stats["dur_mean"] / rec_stats["dur_mean"]
        # exposant amplitude-durée (tous épisodes, MCO log-log)
        durations = np.array([l for _, l, a in runs if a > 0])
        amplitudes = np.array([a for _, l, a in runs if a > 0])
        if len(durations) > 20 and len(np.unique(durations)) > 3:
            slope, _ = np.polyfit(np.log(durations), np.log(amplitudes), 1)
            out[f"{prefix}amp_dur_exponent"] = float(slope)

    # Même protocole sur l'énergie totale présente E_t = sum_i K_i.
    # Les noms sont préfixés pour préserver sans ambiguïté toutes les
    # sorties historiques calculées sur la production.
    y_energy = np.log(energy[burn:])
    dy_energy = np.diff(y_energy)
    out.update({
        "energy_sd_dlog": float(dy_energy.std()),
        "energy_acf1_dlog": float(
            np.corrcoef(dy_energy[:-1], dy_energy[1:])[0, 1]),
        "energy_skew_dlog": float(stats.skew(dy_energy)),
        "energy_tau_int_logK": float(integrated_autocorr(y_energy)),
    })
    for w in WINDOWS:
        runs = episodes(y_energy, w)
        exp_stats = _phase_stats(runs, +1)
        rec_stats = _phase_stats(runs, -1)
        if not exp_stats or not rec_stats:
            return None
        prefix = f"energy_w{w}_"
        for name, block in (("exp", exp_stats), ("rec", rec_stats)):
            for key, value in block.items():
                out[f"{prefix}{name}_{key}"] = value
        out[f"{prefix}rate_per_1000"] = (
            1000.0 * (exp_stats["n"] + rec_stats["n"]) / steps)
        out[f"{prefix}cycle_len"] = (
            exp_stats["dur_mean"] + rec_stats["dur_mean"])
        out[f"{prefix}slope_ratio_rec_exp"] = (
            rec_stats["slope_mean"] / exp_stats["slope_mean"])
        out[f"{prefix}dur_ratio_exp_rec"] = (
            exp_stats["dur_mean"] / rec_stats["dur_mean"])
        durations = np.array([l for _, l, a in runs if a > 0])
        amplitudes = np.array([a for _, l, a in runs if a > 0])
        if len(durations) > 20 and len(np.unique(durations)) > 3:
            slope, _ = np.polyfit(
                np.log(durations), np.log(amplitudes), 1)
            out[f"{prefix}amp_dur_exponent"] = float(slope)
    return out


# ------------------------------------------------------------- tables

def build_plan(plan: str, out_name: str) -> list[dict]:
    rows = []
    for spec in L.load_plan(plan):
        directory = L.run_dir(spec)
        manifest_path = directory / "manifest.json"
        if not manifest_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text())
        metrics = cycle_metrics(directory / "series.csv",
                                manifest["parameters"]["T"], manifest["t_final"])
        if metrics is None:
            continue
        rows.append({**{k: manifest["parameters"][k] for k in
                        ("lam", "delta", "sigma", "K0", "k", "seed", "T")},
                     "run_id": manifest["run_id"], **metrics})
    _write(SUMMARY / out_name, rows)
    return rows


def build_confirm() -> list[dict]:
    manifest = json.loads((L.CAMPAIGN_ROOT / "manifests" / "confirm_lab.json").read_text())
    rows = []
    for entry in manifest["cells"]:
        if entry["cell"] == "lam2_ext":
            continue
        p = entry["parameters"]
        for offset, run_id in enumerate(entry["run_ids"]):
            summary = json.loads((LAB_RUNS / run_id / "summary.json").read_text())
            metrics = cycle_metrics(LAB_RUNS / run_id / "series.csv",
                                    p["T"], summary["t_final"])
            if metrics is None:
                continue
            rows.append({"cell": entry["cell"], "lab_run_id": run_id,
                         "lam": p["lam"], "delta": p["delta"], "sigma": p["sigma"],
                         "K0": p["K0"], "k": p["k"],
                         "seed": entry["base_seed"] + offset, "T": p["T"],
                         **metrics})
    _write(SUMMARY / "cycles_confirm.csv", rows)
    return rows


def _write(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    keys = list(rows[0].keys())
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader(); writer.writerows(rows)
    print(path, len(rows), "lignes")


KEY_METRICS = ("sd_dlog", "acf1_dlog", "skew_dlog",
               "w1_slope_ratio_rec_exp", "w1_dur_ratio_exp_rec",
               "w1_rate_per_1000", "w25_cycle_len", "tau_int_logprod",
               "energy_sd_dlog", "energy_acf1_dlog", "energy_skew_dlog",
               "energy_w1_rate_per_1000", "energy_w1_rec_dur_mean",
               "energy_w1_rec_amp_mean",
               "energy_w1_slope_ratio_rec_exp", "energy_tau_int_logK")


def screening(lhs_rows: list[dict]) -> None:
    X = np.array([[r["delta"], r["sigma"], np.log10(r["K0"]), r["k"]]
                  for r in lhs_rows])
    groups = np.array([hash((r["delta"], r["sigma"], r["K0"], r["k"]))
                       for r in lhs_rows])
    out = []
    for metric in KEY_METRICS:
        y = np.array([r.get(metric, np.nan) for r in lhs_rows], dtype=float)
        keep = np.isfinite(y)
        prcc = S.prcc(X[keep], y[keep])
        r2cv = S.cv_r2_by_group(S.QuadraticSurface, X[keep], y[keep], groups[keep])
        decomposition = S.variance_decomposition(y[keep], groups[keep])
        out.append({"metric": metric, "n": int(keep.sum()),
                    "prcc_delta": round(float(prcc[0]), 3),
                    "prcc_sigma": round(float(prcc[1]), 3),
                    "prcc_logK0": round(float(prcc[2]), 3),
                    "prcc_k": round(float(prcc[3]), 3),
                    "r2_cv_quadratic": round(float(r2cv), 3),
                    "var_between_frac": round(float(decomposition["var_between_frac"]), 3)})
        print(out[-1])
    _write(SUMMARY / "cycles_screening.csv", out)


def confirm_contrasts(confirm_rows: list[dict], oat_rows: list[dict]) -> None:
    by_cell = defaultdict(dict)
    for row in confirm_rows:
        by_cell[row["cell"]][row["seed"]] = row
    center = by_cell["centre_lam30"]
    center_params = (30.0, 0.05, 0.25, 25.0, 3)

    def explo_mean(params, metric):
        values = [r[metric] for r in oat_rows
                  if (r["lam"], r["delta"], r["sigma"], r["K0"], r["k"]) == params
                  and np.isfinite(r.get(metric, np.nan))]
        return float(np.mean(values)) if values else np.nan

    out = []
    for cell, seeds in by_cell.items():
        if cell == "centre_lam30":
            continue
        sample = next(iter(seeds.values()))
        params = (sample["lam"], sample["delta"], sample["sigma"],
                  sample["K0"], sample["k"])
        for metric in KEY_METRICS:
            pairs = [seeds[s][metric] - center[s][metric] for s in seeds
                     if s in center and np.isfinite(seeds[s].get(metric, np.nan))
                     and np.isfinite(center[s].get(metric, np.nan))]
            if len(pairs) < 3:
                continue
            pairs = np.asarray(pairs)
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
                        "delta_explo": round(d_explo, 5) if np.isfinite(d_explo) else "",
                        "verdict": verdict, "n_pairs": len(pairs)})
    _write(SUMMARY / "cycles_confirm_contrasts.csv", out)
    counts = defaultdict(int)
    for row in out:
        counts[row["verdict"]] += 1
    print("verdicts cycles :", dict(counts))


# ------------------------------------------------------------- figures

CENTER = dict(lam=30.0, delta=0.05, sigma=0.25, K0=25.0, k=3)


def _axis_cells(rows, axis):
    grouped = defaultdict(list)
    for r in rows:
        key = dict(lam=r["lam"], delta=r["delta"], sigma=r["sigma"],
                   K0=r["K0"], k=r["k"])
        diffs = [n for n in CENTER if float(key[n]) != CENTER[n]]
        if diffs == [] or diffs == [axis]:
            grouped[float(key[axis])].append(r)
    return dict(sorted(grouped.items()))


def figure_sensibilite(oat_rows, confirm_rows):
    fig, axes = plt.subplots(2, 3, figsize=(16.5, 8.6))
    panels = [
        ("sigma", "skew_dlog", "asymétrie (skewness) de Δlog prod", False),
        ("sigma", "acf1_dlog", "autocorrélation ACF1 de Δlog prod", False),
        ("sigma", "w1_slope_ratio_rec_exp", "raideur récession / expansion", False),
        ("sigma", "sd_dlog", "volatilité de la croissance sd(Δlog)", False),
    ]
    for panel, (axis_name, metric, title, logx) in zip(np.ravel(axes), panels):
        cells = _axis_cells(oat_rows, axis_name)
        xs = list(cells)
        means = [np.nanmean([r.get(metric, np.nan) for r in cells[v]]) for v in xs]
        sds = [np.nanstd([r.get(metric, np.nan) for r in cells[v]]) for v in xs]
        panel.errorbar(xs, means, yerr=sds, marker="o", ms=4, capsize=3, color="C3")
        if metric == "skew_dlog":
            panel.axhline(0, color="k", lw=0.7)
        if metric == "w1_slope_ratio_rec_exp":
            panel.axhline(1, color="k", lw=0.7)
        if metric == "acf1_dlog":
            panel.axhline(0, color="k", lw=0.7)
        panel.set_xlabel(axis_name if axis_name != "sigma" else "σ")
        panel.set_title(title, fontsize=10); panel.grid(alpha=0.25)
        if logx:
            panel.set_xscale("log")

    # mémoire de l'activité et durée de vie le long de sigma (OAT)
    panel = np.ravel(axes)[4]
    cells = _axis_cells(oat_rows, "sigma")
    xs = list(cells)
    means = [np.nanmean([r.get("tau_int_logprod", np.nan) for r in cells[v]])
             for v in xs]
    sds = [np.nanstd([r.get("tau_int_logprod", np.nan) for r in cells[v]])
           for v in xs]
    panel.errorbar(xs, means, yerr=sds, marker="o", ms=4, capsize=3,
                   color="C3", label="τ_int(log prod)")
    with (SUMMARY / "oat.csv").open() as stream:
        oat_flat = list(csv.DictReader(stream))
    nol = defaultdict(list)
    for r in oat_flat:
        key = dict(lam=float(r["lam"]), delta=float(r["delta"]),
                   sigma=float(r["sigma"]), K0=float(r["K0"]), k=float(r["k"]))
        diffs = [n for n in CENTER if key[n] != CENTER[n]]
        if (diffs == [] or diffs == ["sigma"]) and r["N_over_lambda"]:
            nol[key["sigma"]].append(float(r["N_over_lambda"]))
    xs2 = sorted(nol)
    panel.errorbar(xs2, [np.mean(nol[v]) for v in xs2],
                   yerr=[np.std(nol[v]) for v in xs2], marker="s", ms=4,
                   capsize=3, color="C0", label="durée de vie N/λ")
    panel.set_xlabel("σ")
    panel.set_title("mémoire de l'activité et durée de vie", fontsize=10)
    panel.grid(alpha=0.25); panel.legend(fontsize=8)

    # volatilité vs taille (confirm λ=10/30/100), pente -1/2 attendue
    panel = np.ravel(axes)[5]
    by_cell = defaultdict(list)
    for r in confirm_rows:
        by_cell[r["cell"]].append(r)
    lams, sds = [], []
    for cell, lam in (("ref_lam10", 10), ("centre_lam30", 30), ("lam100", 100)):
        for r in by_cell[cell]:
            lams.append(lam); sds.append(r["sd_dlog"])
    lams = np.array(lams, dtype=float); sds = np.array(sds)
    panel.loglog(lams, sds, "o", ms=5, alpha=0.7)
    slope, intercept = np.polyfit(np.log(lams), np.log(sds), 1)
    grid = np.linspace(np.log(8), np.log(120), 10)
    panel.plot(np.exp(grid), np.exp(intercept + slope * grid), "r--",
               label=f"pente = {slope:.2f} (−0,5 attendu)")
    panel.set_xlabel("λ"); panel.set_title("volatilité vs taille du système",
                                           fontsize=10)
    panel.legend(fontsize=8); panel.grid(alpha=0.25, which="both")
    fig.suptitle("Cycles de l'activité agrégée — sensibilité (OAT graines 1-3 "
                 "T=2000 ; taille : confirmatoire graines 11-15)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "cycles_sensibilite.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


def figure_structure(confirm_rows):
    manifest = json.loads((L.CAMPAIGN_ROOT / "manifests" / "confirm_lab.json").read_text())
    cells = {e["cell"]: e for e in manifest["cells"]}
    fig, axes = plt.subplots(2, 2, figsize=(14.5, 9.5))

    # (a) extraits de trajectoires
    panel = axes[0][0]
    for index, (cell, span) in enumerate((("sigma0", (2000, 2600)),
                                          ("centre_lam30", (2000, 2600)))):
        run_id = cells[cell]["run_ids"][0]
        with (LAB_RUNS / run_id / "series.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        prod = np.array([float(r["prod_tot"]) for r in rows])
        t = np.arange(1, len(prod) + 1)
        mask = (t >= span[0]) & (t <= span[1])
        y = np.log(prod[mask])
        panel.plot(t[mask], y - y.mean(), lw=0.9, label=f"{cell} (graine 11)",
                   color=f"C{index}")
    panel.set_xlabel("t"); panel.set_ylabel("log prod_tot (centré)")
    panel.set_title("Extraits : dents de scie du régime corrélé", fontsize=10)
    panel.grid(alpha=0.25); panel.legend(fontsize=8)

    # (b) CCDF des durées par phase (brut, une courbe par graine)
    panel = axes[0][1]
    for index, cell in enumerate(("sigma0", "centre_lam30")):
        for pos, run_id in enumerate(cells[cell]["run_ids"]):
            with (LAB_RUNS / run_id / "series.csv").open() as stream:
                rows = list(csv.DictReader(stream))
            prod = np.array([float(r["prod_tot"]) for r in rows])
            y = np.log(prod[len(prod) // 4:])
            runs = episodes(y, 1)
            for sign, style in ((+1, "-"), (-1, "--")):
                durations = np.sort([l for s, l, _ in runs if s == sign])[::-1]
                ccdf = np.arange(1, len(durations) + 1) / len(durations)
                panel.semilogy(durations, ccdf, style, lw=0.7, alpha=0.5,
                               color=f"C{index}",
                               label=(f"{cell} {'exp' if sign > 0 else 'réc'}"
                                      if pos == 0 else None))
    grid = np.arange(1, 14)
    panel.semilogy(grid, 2.0 ** (1 - grid), "k:", lw=1.2,
                   label="géométrique i.i.d.")
    panel.set_xlabel("durée (pas)"); panel.set_ylabel("CCDF")
    panel.set_title("Durées des phases (brut) contre la référence i.i.d.",
                    fontsize=10)
    panel.grid(alpha=0.25); panel.legend(fontsize=7)

    # (c) amplitude vs durée
    panel = axes[1][0]
    for index, cell in enumerate(("sigma0", "centre_lam30")):
        run_id = cells[cell]["run_ids"][0]
        with (LAB_RUNS / run_id / "series.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        prod = np.array([float(r["prod_tot"]) for r in rows])
        y = np.log(prod[len(prod) // 4:])
        runs = episodes(y, 5)
        durations = np.array([l for _, l, a in runs if a > 0])
        amplitudes = np.array([a for _, l, a in runs if a > 0])
        jitter = 1 + 0.06 * (np.random.default_rng(index).random(len(durations)) - 0.5)
        panel.loglog(durations * jitter, amplitudes, "o", ms=2.5, alpha=0.4,
                     color=f"C{index}", label=cell)
    panel.set_xlabel("durée (pas, lissage w=5)")
    panel.set_ylabel("amplitude |Δ log prod|")
    panel.set_title("Taille indicielle contre taille temporelle", fontsize=10)
    panel.grid(alpha=0.25, which="both"); panel.legend(fontsize=8)

    # (d) synthèse par cellule
    panel = axes[1][1]
    order = ["sigma0", "sigma005_k2", "sigma010", "centre_lam30", "sigma050",
             "k2", "k10", "delta002", "delta010", "K0_5", "K0_100",
             "ref_lam10", "lam100"]
    by_cell = defaultdict(list)
    for r in confirm_rows:
        by_cell[r["cell"]].append(r)
    names = [c for c in order if c in by_cell]
    for metric, color, label in (("skew_dlog", "C3", "skewness Δlog"),
                                 ("acf1_dlog", "C0", "ACF1 Δlog"),
                                 ("w1_slope_ratio_rec_exp", "C2",
                                  "raideur réc/exp − 1")):
        means = [np.mean([r[metric] for r in by_cell[c]]) for c in names]
        if metric == "w1_slope_ratio_rec_exp":
            means = [m - 1 for m in means]
        sds = [np.std([r[metric] for r in by_cell[c]], ddof=1) for c in names]
        panel.errorbar(range(len(names)), means, yerr=sds, marker="o", ms=4,
                       capsize=3, color=color, label=label, lw=1)
    panel.axhline(0, color="k", lw=0.7)
    panel.set_xticks(range(len(names)), names, rotation=40, fontsize=7)
    panel.set_title("Signatures cycliques par cellule (5 graines)", fontsize=10)
    panel.grid(alpha=0.25); panel.legend(fontsize=8)

    fig.suptitle("Structure des cycles — cellules confirmatoires "
                 "(graines 11-15, T=4000, fenêtre [1000, 4000])")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "cycles_structure.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    oat_rows = build_plan("oat", "cycles_oat.csv")
    lhs_rows = build_plan("lhs", "cycles_lhs.csv")
    confirm_rows = build_confirm()
    print("\n--- screening PRCC (LHS) des métriques de cycle ---")
    screening(lhs_rows)
    print("\n--- contrastes confirmatoires (extension post-hoc) ---")
    confirm_contrasts(confirm_rows, oat_rows)
    figure_sensibilite(oat_rows, confirm_rows)
    figure_structure(confirm_rows)
    print("\nfigures :", FIG_DIR / "cycles_sensibilite.png",
          FIG_DIR / "cycles_structure.png")


if __name__ == "__main__":
    main()
