"""Ajustement de familles de lois sur la valeur nette NW = K + C - D.

Extension post-audit de la campagne (aucun nouveau run) : les runs OAT et
les cellules de confirmation sont déjà sur disque avec un instantané final
`entities_t*.npz` contenant `nw` par entité vivante. `analyze_nw.py` calcule
déjà le Gini de NW, sa CCDF et la structure des bilans ; ce script ajoute la
sélection de famille par MLE/AIC (échelle à 13 familles de
`recherche/analyse_distributions_taille_revenu/scripts/families.py`,
réutilisée telle quelle) et un test de queue Clauset-Shalizi-Newman
(`tail_test.py`, même dossier), pour évaluer comment la distribution de NW
(pas seulement son Gini) répond aux cinq paramètres.

Toutes les entités survivantes ont NW >= 0 (invariant du moteur, vérifié
dans le rapport final) ; les fits utilisent le support strictement positif
de la echelle de familles (NW == 0 exclu, rare).

Produit :
- results/summary/nw_fit_oat.csv : un fit par run OAT (grille dense par axe,
  1-3 graines, T=2000).
- results/summary/nw_fit_confirm.csv : un fit par graine des 16 cellules de
  confirmation (5 graines, T=4000).
- figures/nw_fit_sensibilite.png : famille gagnante et exposant de queue CSN
  par axe (sigma, k, K0, delta, lambda), grille OAT + cellules confirmées.
- figures/nw_fit_ccdf_examples.png : CCDF empirique de NW + ajustement pour
  quelques cellules confirmées représentatives.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_runs as L  # noqa: E402

sys.path.insert(
    0, "/home/anatole/jupyter/recherche/analyse_distributions_taille_revenu/scripts"
)
import families as F  # noqa: E402
import tail_test as T  # noqa: E402

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, "/home/anatole/jupyter/simulation_lab")
import plot_utils as PU  # noqa: E402

LAB_RUNS = Path("/home/anatole/jupyter/simulation_lab_data/runs")
SUMMARY = L.CAMPAIGN_ROOT / "results" / "summary"
FIG_DIR = L.CAMPAIGN_ROOT / "figures"
OAT_MANIFEST = L.CAMPAIGN_ROOT / "manifests" / "oat.json"
CONFIRM_MANIFEST = L.CAMPAIGN_ROOT / "manifests" / "confirm_lab.json"

CENTER = dict(lam=30.0, delta=0.05, sigma=0.25, K0=25.0, k=3)
AXES = ("sigma", "k", "K0", "delta", "lam")
AXIS_LABEL = {"sigma": r"$\sigma$", "k": "$k$", "K0": "$K_0$", "delta": r"$\delta$", "lam": r"$\lambda$"}


def gini(x: np.ndarray) -> float:
    x = np.sort(np.asarray(x, dtype=float))
    n = len(x)
    cum = np.cumsum(x)
    return float((n + 1 - 2 * np.sum(cum) / cum[-1]) / n)


def load_final_nw(run_dir: Path) -> np.ndarray | None:
    snap_dir = run_dir / "snapshots"
    if not snap_dir.is_dir():
        return None
    files = sorted(snap_dir.glob("entities_t*.npz"))
    if not files:
        return None
    with np.load(files[-1]) as d:
        nw = np.asarray(d["nw"], dtype=float)
    return nw[nw > 0]


def fit_row(nw: np.ndarray, extra: dict) -> dict | None:
    fits = F.fit_all(nw, min_n=30)
    if not fits:
        return None
    ranked = sorted(fits.items(), key=lambda kv: kv[1]["aic"])
    best_name, best = ranked[0]
    row = dict(extra)
    row["n_survivors"] = len(nw)
    row["gini_nw"] = gini(nw)
    row["best_family"] = best_name
    row["best_aic"] = best["aic"]
    row["best_params"] = json.dumps(
        {str(k): float(v) for k, v in (
            best["params"].items() if isinstance(best["params"], dict)
            else enumerate(best["params"])
        )}
    )
    row["second_family"] = ranked[1][0] if len(ranked) > 1 else ""
    row["delta_aic_2nd"] = (ranked[1][1]["aic"] - best["aic"]) if len(ranked) > 1 else float("nan")

    pl = T.fit_powerlaw_xmin(nw)
    if pl:
        row["csn_alpha"] = pl["alpha"]
        row["csn_xmin"] = pl["x_min"]
        row["csn_ks"] = pl["ks"]
        row["csn_ntail"] = pl["n_tail"]
        lr = T.lognormal_vs_powerlaw_lr(nw, pl["x_min"], pl["alpha"])
        row["csn_z_vs_lognorm"] = lr["z"] if lr and "z" in lr else float("nan")
        row["csn_p_vs_lognorm"] = lr["p"] if lr and "p" in lr else float("nan")
    else:
        for key in ("csn_alpha", "csn_xmin", "csn_ks", "csn_ntail", "csn_z_vs_lognorm", "csn_p_vs_lognorm"):
            row[key] = float("nan")
    return row


def which_axis(cell: dict):
    diffs = [k for k in AXES if float(cell[k]) != float(CENTER[k])]
    if len(diffs) == 0:
        return "centre", None
    if len(diffs) == 1:
        return diffs[0], diffs[0]
    return None, None


def write_csv(path: Path, rows: list[dict]):
    import csv

    if not rows:
        return
    cols = list(rows[0].keys())
    for r in rows[1:]:
        for k in r:
            if k not in cols:
                cols.append(k)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def run_oat() -> list[dict]:
    manifest = json.loads(OAT_MANIFEST.read_text())
    rows = []
    for cell in manifest["cells"]:
        axis_key, axis_name = which_axis(cell)
        if axis_key is None:
            continue  # not a pure OAT deviation (shouldn't happen for this plan)
        run_dir = L.RESULTS_ROOT / cell["run_id"]
        nw = load_final_nw(run_dir)
        if nw is None or len(nw) < 30:
            continue
        extra = dict(
            axis=axis_key, lam=cell["lam"], delta=cell["delta"], sigma=cell["sigma"],
            K0=cell["K0"], k=cell["k"], seed=cell["seed"], run_id=cell["run_id"],
        )
        row = fit_row(nw, extra)
        if row is not None:
            rows.append(row)
        print(f"  oat {cell['run_id']} axis={axis_key} -> "
              f"{row['best_family'] if row else 'FIT_FAILED'}")
    return rows


def run_confirm() -> list[dict]:
    manifest = json.loads(CONFIRM_MANIFEST.read_text())
    rows = []
    for cell in manifest["cells"]:
        p = cell["parameters"]
        for seed_idx, run_id in enumerate(cell["run_ids"]):
            run_dir = LAB_RUNS / run_id
            nw = load_final_nw(run_dir)
            if nw is None or len(nw) < 30:
                continue
            extra = dict(
                cell=cell["cell"], lam=p["lam"], delta=p["delta"], sigma=p["sigma"],
                K0=p["K0"], k=p["k"], seed=cell["base_seed"] + seed_idx, run_id=run_id,
            )
            row = fit_row(nw, extra)
            if row is not None:
                rows.append(row)
        print(f"  confirm cell={cell['cell']} n_fits="
              f"{sum(1 for r in rows if r['cell'] == cell['cell'])}")
    return rows


def fig_sensibilite(oat_rows: list[dict], confirm_rows: list[dict]):
    PU.apply_style()
    fig, axes = plt.subplots(2, 5, figsize=(21, 8), sharex=False)
    families_seen = sorted({r["best_family"] for r in oat_rows + confirm_rows})
    fam_color = {f: c for f, c in zip(families_seen, plt.cm.tab10.colors)}

    for col, axis in enumerate(AXES):
        oat_pts = [r for r in oat_rows if r["axis"] == axis] + \
                  [r for r in oat_rows if r["axis"] == "centre"]
        confirm_pts_by_x = {}
        for r in confirm_rows:
            x = r[axis]
            confirm_pts_by_x.setdefault(x, []).append(r)

        ax_top = axes[0, col]
        for r in oat_pts:
            ax_top.scatter(r[axis], r["best_family"], color=fam_color[r["best_family"]],
                            s=25, alpha=0.55, marker="o")
        for x, rs in confirm_pts_by_x.items():
            fams = [r["best_family"] for r in rs]
            mode_fam = max(set(fams), key=fams.count)
            ax_top.scatter([x] * len(rs), fams, color="black", s=70, marker="D",
                           edgecolor="white", linewidth=0.6, zorder=5)
        ax_top.set_title(AXIS_LABEL[axis])
        ax_top.tick_params(axis="y", labelsize=7)
        if col == 0:
            ax_top.set_ylabel("Famille gagnante (AIC)")

        ax_bot = axes[1, col]
        if oat_pts:
            xs = np.array([r[axis] for r in oat_pts], dtype=float)
            ys = np.array([r["csn_alpha"] for r in oat_pts], dtype=float)
            ax_bot.scatter(xs, ys, color="tab:blue", s=20, alpha=0.5, label="OAT (1-3 graines)")
        if confirm_pts_by_x:
            xs_c, ys_c, ys_err = [], [], []
            for x, rs in sorted(confirm_pts_by_x.items()):
                vals = np.array([r["csn_alpha"] for r in rs], dtype=float)
                vals = vals[np.isfinite(vals)]
                if len(vals) == 0:
                    continue
                xs_c.append(x)
                ys_c.append(vals.mean())
                ys_err.append(vals.std())
            ax_bot.errorbar(xs_c, ys_c, yerr=ys_err, fmt="D", color="black",
                             capsize=3, label="confirmation (5 graines)")
        ax_bot.set_xlabel(AXIS_LABEL[axis])
        if col == 0:
            ax_bot.set_ylabel(r"Exposant de queue CSN $\hat\alpha$")
        if axis == "sigma":
            ax_bot.legend(fontsize=7, loc="best")

    fig.suptitle("Sensibilité de l'ajustement de NW : famille gagnante (AIC) et exposant de "
                  "queue CSN, par axe", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG_DIR / "nw_fit_sensibilite.png")
    plt.close(fig)


def fig_ccdf_examples(confirm_rows: list[dict], confirm_manifest: dict):
    PU.apply_style()
    examples = ["centre_lam30", "sigma0", "sigma050", "k2", "k10"]
    fig, axes = plt.subplots(1, len(examples), figsize=(4.2 * len(examples), 4.2))
    cell_by_name = {c["cell"]: c for c in confirm_manifest["cells"]}

    for ax, name in zip(axes, examples):
        cell = cell_by_name[name]
        run_id0 = cell["run_ids"][0]
        nw = load_final_nw(LAB_RUNS / run_id0)
        if nw is None:
            ax.set_title(f"{name} (pas de données)")
            continue
        for run_id in cell["run_ids"]:
            nw_s = load_final_nw(LAB_RUNS / run_id)
            if nw_s is None:
                continue
            xs = np.sort(nw_s)
            ccdf = 1.0 - np.arange(1, len(xs) + 1) / len(xs)
            ax.plot(xs, ccdf, color="tab:blue", alpha=0.35, linewidth=1)

        row0 = next((r for r in confirm_rows if r["cell"] == name and r["run_id"] == run_id0), None)
        if row0 is not None:
            fits = F.fit_all(nw, min_n=30)
            best_name, best = min(fits.items(), key=lambda kv: kv[1]["aic"])
            xs_grid = np.linspace(nw.min(), np.quantile(nw, 0.999), 400)
            dist_map = {
                "gengamma_3p": ("gengamma", best["params"]),
                "gamma_2p": ("gamma", best["params"]),
                "gb2_4p": None,
                "weibull_2p": ("weibull_min", best["params"]),
                "lognorm_3p": ("lognorm", best["params"]),
                "lognorm_2p": ("lognorm", best["params"]),
                "singhmaddala_3p": ("burr12", best["params"]),
                "dagum_3p": ("burr", best["params"]),
                "fisk_2p": ("fisk", best["params"]),
                "expon_1p": ("expon", best["params"]),
                "pareto_1p": None,
            }
            entry = dist_map.get(best_name)
            if entry is not None:
                from scipy import stats as sstats
                dist = getattr(sstats, entry[0])
                params = entry[1]
                sf = dist.sf(xs_grid, *params) if not isinstance(params, dict) else None
                if sf is not None:
                    ax.plot(xs_grid, sf, color="tab:red", linewidth=1.8,
                            label=f"fit: {best_name}")
            ax.legend(fontsize=7, loc="lower left")
        ax.set_yscale("log")
        ax.set_xlabel("NW (J)")
        if ax is axes[0]:
            ax.set_ylabel("CCDF")
        ax.set_title(name)

    fig.suptitle("CCDF empirique de NW (une courbe par graine) et meilleur ajustement AIC "
                  "(1ère graine) — cellules confirmées", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIG_DIR / "nw_fit_ccdf_examples.png")
    plt.close(fig)


def main():
    SUMMARY.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    print("Fits OAT...")
    oat_rows = run_oat()
    write_csv(SUMMARY / "nw_fit_oat.csv", oat_rows)
    print(f"  {len(oat_rows)} fits OAT écrits")

    print("Fits confirmation...")
    confirm_rows = run_confirm()
    write_csv(SUMMARY / "nw_fit_confirm.csv", confirm_rows)
    print(f"  {len(confirm_rows)} fits confirmation écrits")

    print("Figures...")
    fig_sensibilite(oat_rows, confirm_rows)
    confirm_manifest = json.loads(CONFIRM_MANIFEST.read_text())
    fig_ccdf_examples(confirm_rows, confirm_manifest)
    print("done")


if __name__ == "__main__":
    main()
