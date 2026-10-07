"""Entrées/sorties d'un run : series.csv, snapshots .npz, réseau .npz,
avalanches.csv, config/summary JSON. Les figures sont générées depuis ces
fichiers, jamais depuis l'état mémoire."""
import csv
import json
import time
from pathlib import Path

import numpy as np

SERIES_FIELDS = [
    "t", "births", "deaths", "pop", "L_tot", "K_tot", "nw_tot", "prod_tot",
    "n_loans", "new_loans", "loan_volume", "interest_paid", "defaults",
    "roots_liquidity", "roots_insolvency", "roots_both", "cascade_iters",
    "n_avalanches", "max_avalanche", "claim_losses", "recovered", "destroyed",
    "injected", "depreciated", "consumed", "shock_gain", "top_decile_deaths",
]

AVALANCHE_FIELDS = ["t", "size", "depth", "n_roots", "causes"]


def default_snapshot_times(T, start=500, every=50, transient=(100, 250)):
    times = [t for t in transient if t <= T]
    times += list(range(start, T + 1, every))
    return sorted(set(times))


class RunWriter:
    """Écrit les artefacts d'un run dans <base_dir>/<run_id>/."""

    def __init__(self, base_dir, run_id, cfg):
        self.dir = Path(base_dir) / run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "figures").mkdir(exist_ok=True)
        self.t0 = time.time()
        with open(self.dir / "config.json", "w") as fh:
            json.dump(cfg.to_dict(), fh, indent=2)

    def on_snapshot(self, t, snap, net):
        np.savez_compressed(self.dir / f"snap_t{t:05d}.npz", **snap)
        np.savez_compressed(self.dir / f"net_t{t:05d}.npz", **net)

    def write_series(self, series):
        with open(self.dir / "series.csv", "w", newline="") as fh:
            wr = csv.DictWriter(fh, fieldnames=SERIES_FIELDS)
            wr.writeheader()
            wr.writerows(series)

    def write_avalanches(self, avalanche_log):
        with open(self.dir / "avalanches.csv", "w", newline="") as fh:
            wr = csv.DictWriter(fh, fieldnames=AVALANCHE_FIELDS)
            wr.writeheader()
            wr.writerows(avalanche_log)

    def write_summary(self, sim, extra=None):
        summary = dict(
            status=sim.status, t_final=sim.t, pop_final=sim.pop.n_alive,
            n_loans_final=len(sim.book),
            total_births=sum(s["births"] for s in sim.series),
            total_deaths=sum(s["deaths"] for s in sim.series),
            wall_seconds=round(time.time() - self.t0, 1),
            book_errors=sim.book.check_consistency(sim.pop.alive),
        )
        if extra:
            summary.update(extra)
        with open(self.dir / "summary.json", "w") as fh:
            json.dump(summary, fh, indent=2)
        return summary


def write_run(base_dir, run_id, sim, snapshot_times=None, log_every=0,
              extra_summary=None):
    """Exécute sim jusqu'à cfg.T avec écriture complète des artefacts."""
    cfg = sim.cfg
    times = (default_snapshot_times(cfg.T) if snapshot_times is None
             else snapshot_times)
    writer = RunWriter(base_dir, run_id, cfg)
    sim.run(snapshot_times=times, on_snapshot=writer.on_snapshot,
            log_every=log_every)
    writer.write_series(sim.series)
    writer.write_avalanches(sim.avalanche_log)
    return writer.write_summary(sim, extra_summary)


def load_series(run_dir):
    rows = []
    with open(Path(run_dir) / "series.csv") as fh:
        for row in csv.DictReader(fh):
            rows.append({k: (int(v) if "." not in v and "e" not in v.lower()
                             else float(v)) for k, v in row.items()})
    return rows


def load_avalanches(run_dir):
    rows = []
    path = Path(run_dir) / "avalanches.csv"
    if not path.exists():
        return rows
    with open(path) as fh:
        for row in csv.DictReader(fh):
            rows.append(dict(t=int(row["t"]), size=int(row["size"]),
                             depth=int(row["depth"]),
                             n_roots=int(row["n_roots"]),
                             causes=row["causes"]))
    return rows


def load_snapshots(run_dir, t_min=None, t_max=None, prefix="snap"):
    """{t: dict d'arrays} pour t dans [t_min, t_max). prefix "net" = réseau."""
    out = {}
    for p in sorted(Path(run_dir).glob(f"{prefix}_t*.npz")):
        t = int(p.stem.split("t")[-1])
        if (t_min is not None and t < t_min) or (t_max is not None and t >= t_max):
            continue
        with np.load(p) as z:
            out[t] = {k: z[k].copy() for k in z.files}
    return out
