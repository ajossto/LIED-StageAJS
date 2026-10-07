"""Avalanches causales INTER-PAS : la mesure au même pas tronque-t-elle les
cascades ?

La mesure de référence (bankruptcy._build_avalanches) relie les morts d'une
même résolution ; une prêteuse amenée à NW = epsilon par une perte, qui meurt
au pas suivant, compte comme nouvelle racine. Ici on relie mort(i, t) ->
mort(j, t') si j a subi une perte de créance issue de la mort de i et
t' - t <= tau (clustering temporel, standard en avalanches neuronales /
sismiques). tau = 0 redonne la composante même-pas (à la nuance près que la
mesure de référence exige les DEUX extrémités mortes — identique ici).

Usage :
  depuis le disque (runs avec loss_edges.csv, mode traçable) :
    /home/anatole/jupyter/.venv/bin/python3 causal_window.py <run_dir> ...
  en mémoire (exploratoire) :
    /home/anatole/jupyter/.venv/bin/python3 causal_window.py --sim [lam] [T] [seed]
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "src"))
sys.path.insert(0, str(HERE))

from m4 import M4Config, Simulation  # noqa: E402
from soc_stats import (fit_pl_cutoff, loglog_regression,  # noqa: E402
                       lr_plcutoff_vs_lognormal)


def load_logs(run_dir):
    """(death_log, loss_edge_log) depuis deaths.csv / loss_edges.csv."""
    run_dir = Path(run_dir)
    deaths, edges = [], []
    with open(run_dir / "deaths.csv") as fh:
        for row in csv.DictReader(fh):
            deaths.append((int(row["t"]), int(row["id"])))
    with open(run_dir / "loss_edges.csv") as fh:
        for row in csv.DictReader(fh):
            edges.append((int(row["t"]), int(row["src"]), int(row["dst"]),
                          float(row["q"])))
    return deaths, edges


def coincidence_rate(death_log, loss_edge_log, t_min):
    """Taux de liens fortuits attendus par mort : morts/pas moyens x
    prêteuses par morte / population n'est pas connu ici — on rapporte le
    ratio brut arêtes-vers-mortes-en-t+1 / arêtes totales comme borne."""
    deaths_by_t = {}
    for t, i in death_log:
        deaths_by_t.setdefault(t, set()).add(i)
    linked = sum(1 for t, _s, d, _q in loss_edge_log
                 if t >= t_min and d in deaths_by_t.get(t + 1, ()))
    total = sum(1 for t, *_ in loss_edge_log if t >= t_min)
    return linked / total if total else float("nan")


def windowed_avalanches(death_log, loss_edge_log, tau, t_min):
    """Composantes des morts reliées par une arête de perte avec délai <= tau.
    Retourne la liste des tailles."""
    death_t = {i: t for t, i in death_log if t >= t_min - tau}
    parent = {i: i for t, i in death_log if t >= t_min}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for t, src, dst, _q in loss_edge_log:
        if src in parent and dst in parent:
            td = death_t.get(dst)
            if td is not None and 0 <= td - t <= tau:
                ra, rb = find(src), find(dst)
                if ra != rb:
                    parent[rb] = ra
    comps = {}
    for i in parent:
        comps.setdefault(find(i), 0)
        comps[find(i)] += 1
    return np.array(sorted(comps.values(), reverse=True), dtype=np.int64)


def _analyse(death_log, loss_edge_log, t_min, taus=(0, 1, 2)):
    out = {}
    for tau in taus:
        sizes = windowed_avalanches(death_log, loss_edge_log, tau, t_min)
        plc = fit_pl_cutoff(sizes, 1)
        reg = loglog_regression(sizes, exclude_one=True)
        lr = lr_plcutoff_vs_lognormal(sizes, 1)
        out[tau] = dict(n=int(len(sizes)), max=int(sizes.max()),
                        plc=plc, reg=reg, lr_plc=lr)
        xc = plc["x_c"] if plc else float("nan")
        print(f"tau={tau:2d}: n={len(sizes)} max={sizes.max()}",
              f"alpha={plc['alpha']:.2f} "
              f"xc={'inf' if xc > 1e6 else round(xc)}" if plc else "",
              f"r2={reg['r2']:.3f}" if reg else "",
              f"LRplc z={lr['z']:.2f}" if lr else "", flush=True)
    out["coincidence_rate"] = coincidence_rate(death_log, loss_edge_log, t_min)
    print(f"taux de liaison t+1 (borne coïncidence+réel) : "
          f"{out['coincidence_rate']:.3f}")
    return out


def main_sim(lam=30.0, T=2000, seed=0):
    cfg = M4Config(lam=lam, T=T, seed=seed)
    sim = Simulation(cfg)
    sim.log_loss_edges = True
    sim.run()
    _analyse(sim.death_log, sim.loss_edge_log, T // 4,
             taus=(0, 1, 2, 3, 5, 10))


def main_dir(run_dir):
    run_dir = Path(run_dir)
    with open(run_dir / "config.json") as fh:
        T = json.load(fh)["T"]
    deaths, edges = load_logs(run_dir)
    print(f"--- {run_dir.name} ---")
    out = _analyse(deaths, edges, T // 4)
    fig_dir = run_dir / "figures"
    fig_dir.mkdir(exist_ok=True)
    with open(fig_dir / "causal_window.json", "w") as fh:
        json.dump(out, fh, indent=2, default=float)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--sim":
        lam = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
        T = int(sys.argv[3]) if len(sys.argv) > 3 else 2000
        seed = int(sys.argv[4]) if len(sys.argv) > 4 else 0
        main_sim(lam, T, seed)
    else:
        for arg in sys.argv[1:]:
            main_dir(arg)
