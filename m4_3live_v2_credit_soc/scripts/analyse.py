"""Analyse des campagnes v2 : verdict du lot D (sens du prêt) et du lot E
(ordre des phases).

CE QUI EST COMPARÉ, ET COMMENT
--------------------------------------------------------------------------
Tous les bras d'une même graine partagent leur amorçage 0 → t₀ = 2000 : ils
sont rigoureusement identiques jusqu'à t₀, puis divergent. La comparaison est
donc **appariée par graine** : pour chaque observable X et chaque graine i on
forme l'écart relatif

    d_i = X_i(bras) / X_i(référence) − 1,

et on rapporte la moyenne des d_i avec son erreur-type. Avec n graines, le
rapport moyenne/erreur-type suit une loi de **Student à n − 1 degrés de
liberté**, PAS une normale : à n = 12, le seuil de significativité bilatéral
à 5 % est t = 2,201 et non 1,96 ; à 1 %, 3,106 et non 2,58. C'est la
correction demandée par la note [19] de l'utilisateur, portée ici à la source
(le nombre de graines) et pas seulement dans la présentation.

CONTRÔLE DE STATIONNARITÉ, OBLIGATOIRE AVANT DE LIRE UN NIVEAU. Pour chaque
run et chaque grandeur parmi K_tot, pop et prod_tot, on rapporte le rapport
de la moyenne du dernier quart de la fenêtre à celle du quart précédent. Un
bras hors de [0,99 ; 1,01] n'a pas atteint son régime : il donne un
transitoire, pas un niveau, et le script le dit au lieu de le taire.

    python3 scripts/analyse.py           # lots D et E
    python3 scripts/analyse.py --window 1000
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

CAMPAIGN = ROOT / "results" / "campaign"
ANALYSIS = ROOT / "results" / "analysis"
FIGURES = ROOT / "report" / "figures"
TABLES = ROOT / "report" / "tables"

T0 = 2000

#: Quantiles de Student, bilatéraux, pour les effectifs employés ici.
#: (source : table classique ; recalculés au besoin par scipy, non requis)
STUDENT = {
    (4, 0.05): 2.776, (4, 0.01): 4.604,
    (11, 0.05): 2.201, (11, 0.01): 3.106,
    (2, 0.05): 4.303, (2, 0.01): 9.925,
}

OBSERVABLES = (
    ("prod_tot", "production agrégée"),
    ("pop", "population"),
    ("K_tot", "capital total"),
    ("deaths", "morts par pas"),
    ("defaults", "défauts de liquidité par pas"),
    ("loan_volume", "volume prêté par pas"),
    ("interest_paid", "intérêts versés par pas"),
    ("n_loans", "contrats vivants"),
    ("mkt_blocked_dir", "paires refusées pour cause de sens"),
    ("mkt_reversed", "prêts conclus dans le sens interdit"),
    ("mkt_volume_rev", "volume prêté dans le sens interdit"),
    ("K_share_creditors", "part du capital aux créancières nettes"),
    ("corr_marg_net", "corr(rendement marginal, position nette)"),
    ("corr_K_net", "corr(capital, position nette)"),
    ("defaults_window", "fenêtre de bascule (prédiction §3.2)"),
)


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _mean(values) -> float:
    values = [v for v in values if v == v]
    return sum(values) / len(values) if values else float("nan")


def summarise_run(directory: Path, window: int) -> dict | None:
    rows = read_csv(directory / "series.csv")
    rows = [row for row in rows if int(row["t"]) > T0]
    if len(rows) < window:
        return None
    tail = rows[-window:]
    out: dict = {}
    for column, _ in OBSERVABLES:
        if column not in tail[0]:
            continue
        out[column] = _mean(float(row[column]) for row in tail)
    out["rotation"] = out["loan_volume"] / out["K_tot"]
    out["deaths_per_pop"] = out["deaths"] / out["pop"]
    out["reversed_share"] = (
        out["mkt_reversed"] / _mean(float(row["mkt_rounds"]) for row in tail)
    )
    out["blocked_share"] = (
        out["mkt_blocked_dir"] / _mean(float(row["mkt_rounds"]) for row in tail)
    )
    out["volume_rev_share"] = out["mkt_volume_rev"] / out["loan_volume"]
    tension = read_csv(directory / "tension_agg.csv")
    tension = [row for row in tension if int(row["t"]) > T0][-window:]
    if tension:
        out["tension"] = _mean(float(row["tension"]) for row in tension)
        out["K_eq"] = _mean(float(row["K_eq"]) for row in tension)
        out["jensen"] = _mean(float(row["jensen"]) for row in tension)
    quarter = window // 4
    for column in ("K_tot", "pop", "prod_tot"):
        last = _mean(float(row[column]) for row in tail[-quarter:])
        before = _mean(float(row[column]) for row in tail[-2 * quarter:-quarter])
        out[f"stat_{column}"] = last / before if before else float("nan")
    return out


def collect(root: Path, window: int) -> dict[tuple, dict]:
    out: dict[tuple, dict] = {}
    for marker in sorted(root.rglob("summary.json")):
        directory = marker.parent
        payload = json.loads(marker.read_text(encoding="utf-8"))
        summary = summarise_run(directory, window)
        if summary is None:
            continue
        key = tuple(directory.relative_to(root).parts)
        summary["_path"] = str(directory)
        summary["_seed"] = payload.get("seed")
        summary["_interventions"] = payload.get("interventions", [])
        out[key] = summary
    return out


def paired(treated: dict, reference: dict, seeds, column: str) -> dict:
    """Écart relatif apparié, avec sa statistique de Student."""
    diffs = []
    for seed in seeds:
        a = treated.get(seed, {}).get(column)
        b = reference.get(seed, {}).get(column)
        if a is None or b is None or b != b or a != a:
            continue
        if b == 0.0:
            continue
        diffs.append(a / b - 1.0)
    n = len(diffs)
    if n < 2:
        return {"n": n, "mean": float("nan"), "se": float("nan"), "t": float("nan")}
    mean = sum(diffs) / n
    variance = sum((d - mean) ** 2 for d in diffs) / (n - 1)
    se = math.sqrt(variance / n)
    return {
        "n": n,
        "mean": mean,
        "se": se,
        "t": mean / se if se > 0 else float("inf"),
        "t_crit_5pct": STUDENT.get((n - 1, 0.05)),
        "t_crit_1pct": STUDENT.get((n - 1, 0.01)),
        "diffs": diffs,
    }


def absolute(runs: dict, seeds, column: str) -> dict:
    values = [runs[seed][column] for seed in seeds
              if seed in runs and column in runs[seed] and runs[seed][column] == runs[seed][column]]
    n = len(values)
    if n < 2:
        return {"n": n, "mean": float("nan"), "se": float("nan")}
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)
    return {"n": n, "mean": mean, "se": math.sqrt(variance / n),
            "min": min(values), "max": max(values)}


# --------------------------------------------------------------------------
def analyse_lot_D(window: int) -> dict:
    runs = collect(CAMPAIGN / "arms", window)
    by_cell: dict[tuple[str, str], dict[int, dict]] = {}
    for (direction, arm, seed_dir), summary in runs.items():
        seed = int(seed_dir.replace("seed", ""))
        by_cell.setdefault((direction, arm), {})[seed] = summary
    arms = sorted({arm for _, arm in by_cell})
    payload: dict = {"window": window, "arms": {}, "stationarity": []}

    for arm in arms:
        free = by_cell.get(("free", arm), {})
        v1 = by_cell.get(("richest_lends", arm), {})
        seeds = sorted(set(free) & set(v1)) if v1 else sorted(free)
        entry: dict = {
            "n_seeds_free": len(free),
            "n_seeds_richest_lends": len(v1),
            "paired_seeds": seeds,
            "levels_free": {},
            "paired_free_vs_v1": {},
        }
        for column in ("prod_tot", "pop", "K_tot", "deaths_per_pop", "rotation",
                       "tension", "loan_volume", "interest_paid", "defaults",
                       "reversed_share", "blocked_share", "volume_rev_share",
                       "K_share_creditors", "corr_marg_net", "corr_K_net",
                       "jensen", "n_loans"):
            entry["levels_free"][column] = absolute(free, sorted(free), column)
            if v1:
                entry["paired_free_vs_v1"][column] = paired(free, v1, seeds, column)
        payload["arms"][arm] = entry

    for (direction, arm), cells in sorted(by_cell.items()):
        for seed, summary in sorted(cells.items()):
            ratios = {c: summary.get(f"stat_{c}") for c in ("K_tot", "pop", "prod_tot")}
            if any(r is None or not (0.99 <= r <= 1.01) for r in ratios.values()):
                payload["stationarity"].append(
                    {"direction": direction, "arm": arm, "seed": seed, **ratios}
                )
    return payload


def analyse_lot_E(window: int) -> dict:
    control = collect(CAMPAIGN / "arms" / "free" / "control", window)
    deprec = collect(CAMPAIGN / "phase", window)
    reference = {int(k[0].replace("seed", "")): v for k, v in control.items()}
    treated = {int(k[1].replace("seed", "")): v for k, v in deprec.items()}
    seeds = sorted(set(reference) & set(treated))
    payload = {"window": window, "paired_seeds": seeds, "paired": {}, "levels": {}}
    for column in ("defaults", "deaths_per_pop", "prod_tot", "pop", "K_tot",
                   "rotation", "interest_paid", "tension"):
        payload["paired"][column] = paired(treated, reference, seeds, column)
    payload["levels"]["reference_defaults"] = absolute(reference, seeds, "defaults")
    payload["levels"]["reference_window"] = absolute(reference, seeds, "defaults_window")
    payload["levels"]["treated_defaults"] = absolute(treated, seeds, "defaults")
    payload["levels"]["treated_window"] = absolute(treated, seeds, "defaults_window")

    # PRÉDICTION A PRIORI (§3.2), écrite depuis le bras de RÉFÉRENCE seul :
    # le nombre de débitrices dans la fenêtre de bascule est le nombre de
    # défauts supplémentaires attendus au premier ordre.
    base = payload["levels"]["reference_defaults"]["mean"]
    extra = payload["levels"]["reference_window"]["mean"]
    payload["prediction"] = {
        "defauts_reference": base,
        "fenetre_de_bascule": extra,
        "defauts_predits": base + extra,
        "hausse_relative_predite": extra / base if base else float("nan"),
        "hausse_relative_mesuree": payload["paired"]["defaults"]["mean"],
    }
    return payload


# --------------------------------------------------------------------------
def figure_lot_D(payload: dict, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    try:
        from simulation_lab.plot_utils import apply_style

        apply_style()
    except Exception:
        pass

    arms = [a for a in sorted(payload["arms"]) if payload["arms"][a]["paired_free_vs_v1"]]
    if not arms:
        return
    columns = [
        ("prod_tot", "production"),
        ("pop", "population"),
        ("deaths_per_pop", "mortalité"),
        ("loan_volume", "volume prêté"),
        ("rotation", "rotation du crédit"),
        ("interest_paid", "intérêts versés"),
    ]
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.4))

    width = 0.8 / len(arms)
    palette = ["#294c60", "#c1440e", "#7a9e9f", "#8f6b9e"]
    for index, arm in enumerate(arms):
        entry = payload["arms"][arm]["paired_free_vs_v1"]
        xs = [i + index * width for i in range(len(columns))]
        values = [100.0 * entry[c]["mean"] for c, _ in columns]
        errors = [100.0 * entry[c]["se"] * (entry[c]["t_crit_5pct"] or 2.201)
                  for c, _ in columns]
        axes[0].bar(xs, values, width=width * 0.92, yerr=errors, capsize=2,
                    color=palette[index % len(palette)], label=arm)
    axes[0].axhline(0.0, color="black", lw=0.8)
    axes[0].set_xticks([i + 0.4 - width / 2 for i in range(len(columns))])
    axes[0].set_xticklabels([label for _, label in columns], rotation=20, fontsize=7)
    axes[0].set_ylabel("écart relatif sens libre / règle v1 (%)")
    axes[0].set_title("(a) effet du sens libre, apparié par graine\n"
                      "(barres : intervalle de Student à 5 %)", fontsize=9)
    axes[0].legend(fontsize=7)

    labels, shares, blocked = [], [], []
    for arm in arms:
        levels = payload["arms"][arm]["levels_free"]
        labels.append(arm)
        shares.append(100.0 * levels["reversed_share"]["mean"])
        blocked.append(100.0 * levels["blocked_share"]["mean"])
    xs = list(range(len(labels)))
    axes[1].bar([x - 0.2 for x in xs], blocked, width=0.4, color="#c1440e",
                label="paires que la règle v1 aurait refusées (contrefactuel)")
    axes[1].bar([x + 0.2 for x in xs], shares, width=0.4, color="#294c60",
                label="prêts effectivement conclus dans ce sens")
    axes[1].set_xticks(xs)
    axes[1].set_xticklabels(labels, fontsize=8)
    axes[1].set_ylabel("part des rondes de marché (%)")
    axes[1].set_title("(b) ce que la règle v1 s'interdisait", fontsize=9)
    axes[1].legend(fontsize=7)
    for axis in axes:
        axis.grid(True, alpha=0.2, axis="y")
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(figure)


def figure_creditors(window: int, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    try:
        from simulation_lab.plot_utils import apply_style

        apply_style()
    except Exception:
        pass

    figure, axes = plt.subplots(1, 2, figsize=(11, 4))
    cases = [
        ("free", "#294c60", "sens libre"),
        ("richest_lends", "#c1440e", "règle v1 (la plus riche prête)"),
    ]
    for direction, colour, label in cases:
        path_series = CAMPAIGN / "arms" / direction / "new_A150" / "seed0" / "series.csv"
        rows = read_csv(path_series)
        if not rows:
            continue
        steps = [int(row["t"]) for row in rows]
        axes[0].plot(steps, [float(row["K_share_creditors"]) for row in rows],
                     color=colour, lw=0.8, label=label)
        axes[1].plot(steps, [float(row["corr_marg_net"]) for row in rows],
                     color=colour, lw=0.8, label=label)
    for axis, title, ylabel in (
        (axes[0], "part du capital détenue par les créancières nettes",
         r"$K_{\rm créancières}/K_{\rm tot}$"),
        (axes[1], "corrélation rendement marginal ↔ position nette", "r de Pearson"),
    ):
        axis.axvline(T0, color="black", lw=0.8, ls=":")
        axis.set_title(title, fontsize=9)
        axis.set_xlabel("t (pas)")
        axis.set_ylabel(ylabel)
        axis.grid(True, alpha=0.2)
        axis.legend(fontsize=7)
    figure.suptitle("Le régime que le sens libre rend possible — bras new_A150, graine 0")
    figure.tight_layout()
    figure.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(figure)


def write_tables(lot_d: dict, lot_e: dict) -> None:
    TABLES.mkdir(parents=True, exist_ok=True)

    def pct(value: float, digits: int = 2) -> str:
        if value != value:
            return "---"
        return f"{100 * value:+.{digits}f}".replace(".", ",")

    lines = [r"\begin{tabular}{lrrrr}", r"\toprule",
             r"bras & production & population & mortalité & rotation \\",
             r"\midrule"]
    for arm in sorted(lot_d["arms"]):
        entry = lot_d["arms"][arm]["paired_free_vs_v1"]
        if not entry:
            continue
        cells = []
        for column in ("prod_tot", "pop", "deaths_per_pop", "rotation"):
            fit = entry[column]
            cells.append(f"${pct(fit['mean'])} \\pm {pct(fit['se']).lstrip('+')}$\\,\\%")
        lines.append(r"\code{" + arm.replace("_", r"\_") + "} & " + " & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TABLES / "lot_d_paired.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    prediction = lot_e["prediction"]
    lines = [r"\begin{tabular}{lr}", r"\toprule",
             r"grandeur & valeur \\", r"\midrule",
             r"défauts par pas, ordre \code{v1} & "
             + f"{prediction['defauts_reference']:.2f}".replace(".", ",") + r" \\",
             r"fenêtre de bascule mesurée dans ce même bras & "
             + f"{prediction['fenetre_de_bascule']:.2f}".replace(".", ",") + r" \\",
             r"\textbf{défauts prédits sous \code{deprec\_first}} & "
             + f"{prediction['defauts_predits']:.2f}".replace(".", ",") + r" \\",
             r"hausse relative \emph{prédite} & "
             + pct(prediction["hausse_relative_predite"]) + r"\,\% \\",
             r"hausse relative \emph{mesurée} & "
             + pct(prediction["hausse_relative_mesuree"]) + r"\,\% \\",
             r"\bottomrule", r"\end{tabular}"]
    (TABLES / "lot_e_prediction.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window", type=int, default=1000)
    args = parser.parse_args(argv)
    ANALYSIS.mkdir(parents=True, exist_ok=True)

    lot_d = analyse_lot_D(args.window)
    (ANALYSIS / "lot_d.json").write_text(
        json.dumps(lot_d, indent=2, ensure_ascii=False), encoding="utf-8")
    figure_lot_D(lot_d, FIGURES / "lot_d_paired.png")
    figure_creditors(args.window, FIGURES / "creditors.png")

    lot_e = analyse_lot_E(args.window)
    (ANALYSIS / "lot_e.json").write_text(
        json.dumps(lot_e, indent=2, ensure_ascii=False), encoding="utf-8")
    write_tables(lot_d, lot_e)

    print(json.dumps({"lot_D": {arm: {
        "n_free": lot_d["arms"][arm]["n_seeds_free"],
        "n_v1": lot_d["arms"][arm]["n_seeds_richest_lends"],
        "prod": lot_d["arms"][arm]["paired_free_vs_v1"].get("prod_tot", {}).get("mean"),
        "reversed_share": lot_d["arms"][arm]["levels_free"]["reversed_share"]["mean"],
    } for arm in sorted(lot_d["arms"])},
        "runs_non_stationnaires": len(lot_d["stationarity"]),
        "lot_E": lot_e["prediction"]},
        indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
