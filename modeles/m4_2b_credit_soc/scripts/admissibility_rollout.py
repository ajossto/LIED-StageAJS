"""Applique le facteur d'admissibilite (scripts/admissibility_factor.py,
bootstrap avec RE-SCAN KS a chaque tirage) a tous les instantanes
selectionnes par window_selection.csv, sur les 132 runs. Lecture seule
des snapshots bruts deja sur disque -- aucune resimulation, aucune
modification des runs existants.

Parallelise par instantane (pas par run, la charge est tres inegale :
1 a >100 instantanes selon la cellule) via multiprocessing, 6 workers
(convention du projet : 8 coeurs, en laisser 2 libres). Job CPU-bound
leger (pas de simulation, pas de risque memoire comparable a
l'incident de campaign.py, JOURNAL.md).
"""

from __future__ import annotations

import csv
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import interest_income  # noqa: E402
import tail_test  # noqa: E402
from admissibility_factor import admissibility_factor, MIN_N  # noqa: E402

WINDOW_CSV = ROOT / "results" / "window_selection.csv"
OUT_CSV = ROOT / "results" / "admissibility_all_runs.csv"
N_WORKERS = 6

FIELDNAMES = [
    "campaign", "label", "seed", "classification", "t",
    "seuil", "alpha0", "alpha_boot_sd", "n0", "x_max", "coverage", "flatness", "A", "note",
]


def run_dir_for(campaign: str, label: str, seed: int) -> Path:
    base = ROOT / "results" / ("campaign" if campaign == "exploration" else "confirmation")
    return base / label / f"seed{seed}"


def _worker(job):
    campaign, label, seed, classification, t = job
    run_dir = run_dir_for(campaign, label, seed)
    snaps = interest_income.load_all_entity_snapshots(run_dir, t_min=t, t_max=t)
    if not snaps:
        return {"campaign": campaign, "label": label, "seed": seed,
                "classification": classification, "t": t, "note": "snapshot introuvable"}
    _, snap = snaps[0]
    p0, positive = interest_income.zero_mass_and_positive(snap["int_in"])
    best = tail_test.fit_powerlaw_xmin(positive, min_tail=MIN_N)
    if best is None:
        return {"campaign": campaign, "label": label, "seed": seed,
                "classification": classification, "t": t, "note": "seuil KS non admissible"}
    rng = np.random.default_rng(hash((label, seed, t)) % (2**32))
    result = admissibility_factor(positive, best["x_min"], rng)
    boot_alpha0 = np.asarray(result.get("boot_alpha", []))
    alpha_boot_sd = None
    if boot_alpha0.size:
        col0 = boot_alpha0[:, 0]
        col0 = col0[np.isfinite(col0)]
        if len(col0) >= 2:
            alpha_boot_sd = float(np.std(col0, ddof=1))
    row = {"campaign": campaign, "label": label, "seed": seed,
           "classification": classification, "t": t,
           "seuil": best["x_min"], "alpha0": best["alpha"], "alpha_boot_sd": alpha_boot_sd,
           "n0": best["n_tail"],
           "x_max": result.get("x_max"), "coverage": result.get("coverage"),
           "flatness": result.get("flatness"), "A": result.get("A"),
           "note": result.get("note", "")}
    return row


def main():
    rows_in = list(csv.DictReader(open(WINDOW_CSV)))
    jobs = []
    for r in rows_in:
        campaign, label, seed = r["campaign"], r["label"], int(r["seed"])
        classification = r["classification"]
        times = [int(float(t)) for t in r["selected_times"].split(";")]
        for t in times:
            jobs.append((campaign, label, seed, classification, t))

    print(f"{len(jobs)} instantanes a traiter, {N_WORKERS} workers", flush=True)
    t0 = time.time()
    out_rows = []
    with mp.Pool(processes=N_WORKERS) as pool:
        for i, row in enumerate(pool.imap_unordered(_worker, jobs)):
            out_rows.append(row)
            if (i + 1) % 100 == 0:
                elapsed = time.time() - t0
                rate = (i + 1) / elapsed
                eta = (len(jobs) - i - 1) / rate
                print(f"[{i+1}/{len(jobs)}] elapsed={elapsed/60:.1f}min eta={eta/60:.1f}min", flush=True)

    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        for row in out_rows:
            w.writerow({k: row.get(k, "") for k in FIELDNAMES})

    n_ok = sum(1 for r in out_rows if r.get("A") is not None)
    print(f"\n{len(out_rows)} lignes ecrites dans {OUT_CSV} ({n_ok} avec A calcule)")
    print(f"temps total : {(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()
