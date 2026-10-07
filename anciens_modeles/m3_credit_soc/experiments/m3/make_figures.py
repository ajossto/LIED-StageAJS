"""Figures de validation générées depuis les fichiers de résultats.

Usage :
  make_figures.py overview <run_dir> [...]      -> figures/<run>_overview.png
  make_figures.py compare <out.png> <var> <label=run_dir> [...]
       CCDF superposées de la variable au dernier snapshot de chaque run
  make_figures.py avalanches <out.png> <label=run_dir> [...]
  make_figures.py alphadrift <out.png> <var> <label=run_dir> [...]
       exposant de queue par fenêtres de snapshots (x_min commun par run)
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "src"))

from m3 import analysis as an                      # noqa: E402
from m3.metrics import load_series, load_snapshots, load_avalanches  # noqa: E402
from m3.plots import (plot_series_overview, plot_ccdf_comparison,  # noqa: E402
                      plot_avalanche_ccdf)

FIGDIR = HERE.parent.parent / "reports" / "04_validation_report" / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)


def _parse_labeled(args):
    out = []
    for a in args:
        label, _, rd = a.partition("=")
        out.append((label, Path(rd if rd else label)))
    return out


def cmd_overview(run_dirs):
    for rd in run_dirs:
        rd = Path(rd)
        series = load_series(rd)
        out = FIGDIR / f"{rd.name}_overview.png"
        plot_series_overview(series, out, title=rd.name)
        print(f"[fig] {out}")


def cmd_compare(out_name, var, labeled):
    data = {}
    for label, rd in labeled:
        snaps = load_snapshots(rd)
        if not snaps:
            continue
        t_last = max(snaps)
        data[f"{label} (t={t_last})"] = snaps[t_last][var]
    out = FIGDIR / out_name
    plot_ccdf_comparison(data, out, title=f"CCDF {var}")
    print(f"[fig] {out}")


def cmd_avalanches(out_name, labeled):
    data = {}
    for label, rd in labeled:
        av = load_avalanches(rd)
        sizes = [a["size"] for a in av if a["t"] >= 500]
        if sizes:
            data[label] = sizes
    out = FIGDIR / out_name
    plot_avalanche_ccdf(data, out, title="Tailles d'avalanches causales (t >= 500)")
    print(f"[fig] {out}")


def cmd_alphadrift(out_name, var, labeled):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 5))
    for label, rd in labeled:
        snaps = load_snapshots(rd)
        ts = sorted(t for t in snaps if t >= 500)
        if len(ts) < 3:
            continue
        fits = [an.fit_tail_csn(snaps[t][var]) for t in (ts[len(ts)//2], ts[-1])]
        fits = [f for f in fits if f]
        if not fits:
            continue
        x_common = float(np.median([f["x_min"] for f in fits]))
        pts_t, pts_a, lo, hi = [], [], [], []
        for t in ts:
            fit = an.fit_tail_fixed_xmin(snaps[t][var], x_common)
            if not fit:
                continue
            boot = an.bootstrap_tail_alpha(snaps[t][var], x_common, seed=2,
                                           n_boot=100)
            pts_t.append(t)
            pts_a.append(fit["alpha"])
            lo.append(boot["alpha_lo"] if boot else fit["alpha"])
            hi.append(boot["alpha_hi"] if boot else fit["alpha"])
        if pts_t:
            ax.plot(pts_t, pts_a, marker="o", ms=3, label=label)
            ax.fill_between(pts_t, lo, hi, alpha=0.15)
    ax.set_xlabel("t")
    ax.set_ylabel(f"exposant de queue de {var} (x_min commun)")
    ax.legend()
    fig.tight_layout()
    out = FIGDIR / out_name
    fig.savefig(out, dpi=120)
    print(f"[fig] {out}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "overview":
        cmd_overview(sys.argv[2:])
    elif cmd == "compare":
        cmd_compare(sys.argv[2], sys.argv[3], _parse_labeled(sys.argv[4:]))
    elif cmd == "avalanches":
        cmd_avalanches(sys.argv[2], _parse_labeled(sys.argv[3:]))
    elif cmd == "alphadrift":
        cmd_alphadrift(sys.argv[2], sys.argv[3], _parse_labeled(sys.argv[4:]))
    else:
        raise SystemExit(__doc__)
