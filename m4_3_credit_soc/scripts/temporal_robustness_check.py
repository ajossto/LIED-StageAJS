"""Robustesse TEMPORELLE (§10 du prompt : « niveau de preuve exact
[...] robustesse temporelle ») du candidat `gamma_comp_0.6667`, distincte
de la reproductibilité inter-graines déjà établie (D1/D3). Découpe la
fenêtre post-convergence [t_converge, T] de chaque run en deux moitiés
temporelles et compare `b` (branching ratio) entre les deux — si le motif
`gamma_comp` > `baseline` tient dans CHAQUE moitié séparément, ce n'est
pas un artefact d'une sous-période particulière de la fenêtre.

`dagum_c` n'est pas re-testable ici : les instantanés bruts nécessaires
ont été supprimés après analyse (§7.6/nettoyage post-analyse, disque).
Seul `b` (avalanches.csv, conservé) est vérifiable sans re-simuler."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import lib_metrics  # noqa: E402
import json  # noqa: E402

CELLS = {
    "baseline": [ROOT / "results" / "d1" / "baseline" / f"seed{s}" for s in (0, 1, 2)],
    "gamma_comp_0.6667": [ROOT / "results" / "d1" / "gamma_comp_0.6667" / f"seed{s}" for s in (0, 1, 2)],
}


def b_halves(run_dir: Path) -> tuple[float | None, float | None]:
    analysis = json.loads((run_dir / "analysis.json").read_text())
    lo, hi = analysis["lo"], analysis["hi"]
    mid = (lo + hi) // 2
    series = lib_metrics.read_series(run_dir)
    avalanches = lib_metrics.read_avalanches(run_dir)

    def pop_mean(a, b):
        mask = (series["t"] >= a) & (series["t"] <= b)
        return float(series["pop"][mask].mean()) if mask.sum() else float("nan")

    m1 = lib_metrics.window_avalanche_metrics(avalanches, lo, mid, pop_mean(lo, mid), s_min=2)
    m2 = lib_metrics.window_avalanche_metrics(avalanches, mid + 1, hi, pop_mean(mid + 1, hi), s_min=2)
    return m1.get("branching_ratio"), m2.get("branching_ratio")


def main() -> None:
    results = {}
    for label, run_dirs in CELLS.items():
        firsts, seconds = [], []
        for run_dir in run_dirs:
            b1, b2 = b_halves(run_dir)
            print(f"{label}/{run_dir.name}: b(premiere moitie)={b1}, b(seconde moitie)={b2}")
            if b1 is not None:
                firsts.append(b1)
            if b2 is not None:
                seconds.append(b2)
        results[label] = (np.array(firsts), np.array(seconds))

    print()
    for label, (f, s) in results.items():
        print(f"{label}: 1ere moitie b={f.mean():.4f}+/-{f.std(ddof=1):.4f}  "
              f"2eme moitie b={s.mean():.4f}+/-{s.std(ddof=1):.4f}")

    bf, bs = results["baseline"]
    gf, gs = results["gamma_comp_0.6667"]
    print(f"\nEcart gamma_comp-baseline, 1ere moitie: {gf.mean()-bf.mean():+.4f}")
    print(f"Ecart gamma_comp-baseline, 2eme moitie: {gs.mean()-bs.mean():+.4f}")


if __name__ == "__main__":
    main()
