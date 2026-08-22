"""Figures de tension pour un dossier de run, et regénération en masse.

La tension `T = K_aut / K_eq` est DÉFINIE ET CALCULÉE DANS LE MOTEUR
(`m4_3live_v2/tension.py`, §4.1 du prompt v2) et écrite dans `tension.csv` /
`tension_agg.csv` par `write_series`. Ce module ne fait que la tracer : il ne
recalcule rien et ne reconstruit rien. C'est la différence avec v1, où la
tension était un dérivé a posteriori de `tech_series.csv`, avec une colonne
`basis` pour dire de quelle reconstruction elle provenait.

Appelé automatiquement à la fin de chaque run par `driver/headless.py` ;
relançable sur des runs déjà terminés :

    python3 scripts/tension_figures.py                 # tous les runs de results/
    python3 scripts/tension_figures.py results/campaign/burn/seed0
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _column(rows: list[dict], name: str) -> list[float]:
    return [float(row[name]) for row in rows]


def _rolling(values: list[float], window: int) -> list[float]:
    """Moyenne glissante centrée, fenêtre tronquée aux bords."""
    half = window // 2
    out = []
    for index in range(len(values)):
        low = max(0, index - half)
        high = min(len(values), index + half + 1)
        chunk = [value for value in values[low:high] if value == value]
        out.append(sum(chunk) / len(chunk) if chunk else float("nan"))
    return out


def _relaxation_cut(time_axis: list[float]) -> int:
    """Début de la phase relaxée : 10 % de l'horizon, au moins 200 pas.

    C'est une convention d'affichage, pas une mesure : elle sert seulement à
    ne pas laisser le transitoire initial (tension > 100) écraser l'échelle.
    """
    return int(max(200, 0.1 * (time_axis[-1] if time_axis else 0)))


def plot_tension(directory: str | Path) -> Path | None:
    """Écrit `figures/tension.png` à partir de `tension_agg.csv` et `tension.csv`.

    Retourne None si le run ne porte pas ces fichiers (run de zéro pas, ou run
    d'une lignée antérieure)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    try:
        from simulation_lab.plot_utils import apply_style

        apply_style()
    except Exception:  # le style est un confort, pas une dépendance dure
        pass

    directory = Path(directory)
    per_tech = _read(directory / "tension.csv")
    aggregate = _read(directory / "tension_agg.csv")
    series = _read(directory / "series.csv")
    if not aggregate:
        return None

    figure, axes = plt.subplots(2, 2, figsize=(12, 7))
    time_axis = _column(aggregate, "t")

    # (a) évolution de la tension, par technologie et en agrégat
    axis = axes[0][0]
    techs = sorted({int(row["tech"]) for row in per_tech})
    if len(techs) > 1:
        for tech in techs:
            subset = [row for row in per_tech if int(row["tech"]) == tech]
            axis.plot(_column(subset, "t"), _column(subset, "tension"), lw=0.8,
                      label=f"tech {tech} (A={float(subset[0]['A']):.3g}, "
                            f"γ={float(subset[0]['gamma']):.3g})")
        axis.plot(time_axis, _column(aggregate, "tension"), color="black", lw=1.2,
                  label="agrégat (pondéré production)")
        axis.legend(fontsize=6)
    else:
        axis.plot(time_axis, _column(aggregate, "tension"), color="#294c60", lw=0.8)
    axis.axhline(1.0, color="#c1440e", ls="--", lw=1.0)
    axis.text(time_axis[0], 1.0, " T = 1 : échelle autarcique", fontsize=6,
              color="#c1440e", va="bottom")
    axis.set_yscale("log")
    axis.set_title("tension T = K_aut / K_eq", fontsize=9)
    axis.set_xlabel("t (pas)")
    axis.set_ylabel("T (échelle log)")
    axis.grid(True, alpha=0.2)

    # (b) les trois échelles superposées
    axis = axes[0][1]
    axis.plot(time_axis, _column(aggregate, "K_aut"), color="#c1440e", lw=1.0,
              label="K_aut (échelle autarcique)")
    axis.plot(time_axis, _column(aggregate, "K_mean"), color="#7a9e9f", lw=0.8,
              label="K moyen")
    axis.plot(time_axis, _column(aggregate, "K_eq"), color="#294c60", lw=0.8,
              label="K_eq (capital équivalent)")
    axis.set_yscale("log")
    axis.set_title("les trois échelles de capital", fontsize=9)
    axis.set_xlabel("t (pas)")
    axis.set_ylabel("capital (échelle log)")
    axis.legend(fontsize=7)
    axis.grid(True, alpha=0.2)

    # (c) l'écart de Jensen : inégalité interne
    axis = axes[1][0]
    jensen = _column(aggregate, "jensen")
    axis.plot(time_axis, jensen, color="#294c60", lw=0.4, alpha=0.35,
              label="pas à pas")
    axis.plot(time_axis, _rolling(jensen, 51), color="#294c60", lw=1.2,
              label="moyenne glissante (51 pas)")
    axis.axhline(1.0, color="#c1440e", ls="--", lw=1.0)
    axis.set_title("K_eq / K_moyen — écart de Jensen (1 = capitaux égaux)", fontsize=9)
    axis.set_xlabel("t (pas)")
    axis.set_ylabel("K_eq / K_moyen")
    axis.legend(fontsize=7)
    axis.grid(True, alpha=0.2)

    # (d) tension contre mortalité — la lecture demandée par la note [22].
    # Le transitoire initial (tension > 100, mortalité nulle faute de dettes)
    # écrase tout : on ne trace que la phase relaxée, et les deux quantités
    # sont lissées sur 51 pas pour que la relation, s'il y en a une, soit
    # lisible sous le bruit de Poisson des morts.
    axis = axes[1][1]
    death_rate = {}
    for row in series:
        pop = float(row["pop"])
        if pop > 0:
            death_rate[int(row["t"])] = float(row["deaths"]) / pop
    cut = _relaxation_cut(time_axis)
    pairs = [
        (int(row["t"]), float(row["tension"]), death_rate.get(int(row["t"])))
        for row in aggregate
        if int(row["t"]) >= cut and death_rate.get(int(row["t"])) is not None
    ]
    if pairs:
        steps = [step for step, _, _ in pairs]
        smooth_tension = _rolling([value for _, value, _ in pairs], 51)
        smooth_rate = _rolling([value for _, _, value in pairs], 51)
        scatter = axis.scatter(smooth_tension, smooth_rate, c=steps, s=4, cmap="viridis")
        figure.colorbar(scatter, ax=axis, label="t (pas)")
        axis.set_title(
            f"mortalité par entité et par pas contre tension (t ≥ {cut}, lissé 51 pas)",
            fontsize=9,
        )
    else:
        axis.set_title("mortalité contre tension — données insuffisantes", fontsize=9)
    axis.set_xlabel("tension T")
    axis.set_ylabel("morts / population")
    axis.grid(True, alpha=0.2)

    figure.suptitle(
        f"Tension — {directory.name}  "
        "(effectif producteur exact, mesuré à l'instant de la production)"
    )
    figure.tight_layout()
    target = directory / "figures" / "tension.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(target, dpi=130, bbox_inches="tight")
    plt.close(figure)
    return target


def main(argv: list[str]) -> int:
    targets = [Path(arg) for arg in argv[1:] if not arg.startswith("-")]
    if not targets:
        targets = sorted(
            path.parent for path in (ROOT / "results").rglob("tension_agg.csv")
        )
    written = 0
    for directory in targets:
        if plot_tension(directory) is not None:
            written += 1
    print(f"{written} run(s) : figures/tension.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
