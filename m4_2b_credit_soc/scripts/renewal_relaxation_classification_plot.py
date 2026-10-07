"""Figure de classification des 37 cellules (exploration+confirmation)
par leur temps de convergence estime (FOPDT, champ 'income') relatif au
burn-in du pipeline (T/4). Lit results/renewal_relaxation_all_runs.csv
(produit par renewal_relaxation_all_runs.py), n'effectue aucun calcul
nouveau. Marque separement les cellules ou le fit est degenere
(tau > plage temporelle observee : decroissance insuffisante pour
identifier tau de facon fiable, ex. K0_2000 -- voir JOURNAL.md)."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
import statistics as st

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "results" / "renewal_relaxation_all_runs.csv"
OUT = ROOT / "report" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 130, "font.size": 9.5,
    "axes.grid": True, "grid.alpha": 0.25,
})


def main():
    rows = list(csv.DictReader(open(CSV_PATH)))
    cells = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r["field"] != "income":
            continue
        span = float(r["t_last"]) - float(r["t0"])
        tau = float(r["tau"])
        key = (r["campaign"], r["label"])
        cells[key]["tau"].append(tau)
        cells[key]["burn_in"].append(float(r["burn_in"]))
        cells[key]["degenerate"].append(tau > span)

    entries = []
    for (camp, label), d in cells.items():
        n = len(d["tau"])
        n_deg = sum(d["degenerate"])
        burn = st.mean(d["burn_in"])
        clean_tau = [t for t, deg in zip(d["tau"], d["degenerate"]) if not deg]
        all_degenerate = len(clean_tau) == 0
        tau_m = st.mean(clean_tau) if clean_tau else st.mean(d["tau"])
        tconv = tau_m * 3
        ratio = tconv / burn
        entries.append((f"{label} ({camp[:4]})", ratio, all_degenerate, n_deg, n))

    entries.sort(key=lambda x: x[1])
    labels = [e[0] for e in entries]
    ratios = [e[1] for e in entries]
    colors = ["#7f0000" if e[2] else ("crimson" if e[1] > 1 else "#1f77b4") for e in entries]

    fig, ax = plt.subplots(figsize=(9, 10.5))
    y = range(len(entries))
    ax.barh(y, ratios, color=colors, height=0.7)
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=7.5)
    ax.set_xscale("log")
    ax.axvline(1.0, color="black", ls="--", lw=1.2,
               label="t_delay+3·tau = burn-in (T/4)")
    ax.set_xlabel("(t_delay+3·tau) / burn-in du pipeline  (log)\n"
                  "bleu = burn-in suffisant | rouge = transitoire depasse le burn-in | "
                  "rouge fonce = fit degenere (decroissance insuffisante pour identifier tau)")
    ax.set_title("Classification des 37 cellules par temps de relaxation du\n"
                 "renouvellement du décile supérieur (revenu), vs burn-in du pipeline")
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    out_path = OUT / "fig9_classification_relaxation.png"
    fig.savefig(out_path, bbox_inches="tight")
    print(f"ecrit : {out_path}")


if __name__ == "__main__":
    main()
