"""Lot F — qu'est-ce qui détermine la rotation du crédit ?

LA QUESTION (§5 du prompt v2). M4.3Live v1 a établi une régularité forte : sur
109 runs couvrant quatre leviers indépendants, la mortalité suit
`morts/pop ∝ (loan_volume/K_tot)^1,337` avec R² = 0,9982. La **rotation du
crédit** `loan_volume / K_tot` — le principal transféré au pas, rapporté au
stock de capital — aligne les quatre leviers là où la tension échoue. Mais
c'est une variable ENDOGÈNE : on la mesure, on ne la choisit pas. Tant qu'on
ne sait pas la prédire à partir des paramètres, on a une régularité
descriptive et non une loi.

CE QUE CE SCRIPT FAIT, EN DEUX TEMPS
--------------------------------------------------------------------------
**1. La décomposition structurelle**, calculable sur TOUT run déjà terminé,
sans une ligne de moteur ni un calcul neuf. Par construction de la phase de
marché, le volume prêté au pas est la somme des transferts des `R` rondes :

    loan_volume = R · P(traiter) · E[|δ| | traiter],

où R = ⌊η(N)⌋ = ⌊ρN⌋ est le nombre de rondes. En divisant par
K_tot = N·K̄ :

    rotation = (R/N) · P(traiter) · E[|δ|]/K̄
             =    f₁    ·    f₂    ·      f₃.

Les trois facteurs se lisent directement dans `series.csv` :
f₁ = `mkt_rounds`/`pop`, f₂ = `new_loans`/`mkt_rounds`,
f₃ = (`loan_volume`/`new_loans`) / (`K_tot`/`pop`). Le produit est une
identité ; le contenu est que **f₁ vaut ρ exactement** (combinatoire) et que
**f₂ vaut 1 sauf refus**, ce qui reporte toute la question sur f₃.

**2. L'interprétation de f₃, et sa fermeture.** En régime homogène le
transfert optimal est δ = (K_b − K_a)/2, donc

    E|δ| = ½·E|X − Y| = K̄ · G,

où G est le **coefficient de Gini** de la distribution des capitaux — par sa
définition même, G = E|X−Y|/(2·E[X]). Donc **f₃ = G** et
**rotation = ρ·G** : la rotation du crédit N'EST PAS une grandeur de crédit,
c'est l'inégalité des capitaux multipliée par le taux d'appariement.

Une correction est nécessaire et elle est mesurée : les R rondes d'un même
pas ne voient pas la même distribution. Chaque ronde ÉGALISE la paire
(les deux capitaux deviennent leur moyenne), donc le Gini décroît PENDANT la
phase de marché. La prédiction testée est la moyenne logarithmique

    Ḡ = (G_avant − G_après) / ln(G_avant / G_après),

qui est la moyenne exacte d'une décroissance exponentielle entre les deux
valeurs mesurées.

**La fermeture**, elle, doit donner G à partir des paramètres. Bilan de
variance en régime stationnaire, écrit ici comme PRÉDICTION À FALSIFIER,
avant tout ajustement :

- chaque ronde remplace (x, y) par leur moyenne, ce qui retire (x−y)²/2 à la
  somme des écarts au carré ; en moyenne sur les paires, cela retire une
  variance par ronde, donc ρ·N·Var par pas sur un total de N·Var : le marché
  contracte la variance au taux relatif **ρ** par pas ;
- les naissances injectent λ entités à K₀ ≪ K̄, soit λ·(K̄ − K₀)² ;
- le choc multiplicatif injecte ≈ σ²·K̄² par entité.

À l'équilibre ρ·Var ≈ (λ/N)·(K̄ − K₀)² + σ²·K̄², d'où le coefficient de
variation

    CV² ≈ [ (λ/N)·(1 − K₀/K̄)² + σ² ] / ρ,

et, pour une distribution proche de la normale, G ≈ CV/√π. La prédiction est
donc **rotation ≈ ρ·CV/√π** avec le CV ci-dessus — soit, en ordre de
grandeur, rotation ∝ √(ρ·(m + σ²)) où m = λ/N est le taux de renouvellement
par entité. Ce que le script rapporte est l'écart à cette prédiction, quel
qu'il soit.

    python3 scripts/rotation.py sweep     # balayage instrumenté (λ, ρ, σ, K0, δ)
    python3 scripts/rotation.py analyse   # décomposition + fermeture + figures
"""

from __future__ import annotations

import csv
import json
import math
import multiprocessing as mp
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JUPYTER = ROOT.parent
V1_ROOT = JUPYTER / "m4_3live_credit_soc"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(JUPYTER))

from m4_3live_v2.live import write_series  # noqa: E402
from m4_3live_v2.model import Config, Simulation  # noqa: E402

ANALYSIS = ROOT / "results" / "analysis"
FIGURES = ROOT / "report" / "figures"
TABLES = ROOT / "report" / "tables"
SWEEP_DIR = ROOT / "results" / "rotation_sweep"

WORKERS = 7
BURN = 2000
WINDOW = 500
SWEEP_SEEDS = (0, 1, 2)

BASE = dict(gamma=0.5, A=1.0, lam=30.0, delta=0.01, sigma=0.01, K0=25.0,
            rho=1.0, pop_max=30_000, record_market_stats=True)

#: Cellules du balayage : un paramètre bougé à la fois autour du régime de
#: référence. λ, ρ et σ ne sont bougés dans AUCUNE campagne v1 — c'est
#: précisément ce qui manque pour tester la fermeture, et le seul calcul neuf
#: que le lot F demande.
SWEEP = {
    "base": {},
    "lam_15": {"lam": 15.0},
    "lam_60": {"lam": 60.0},
    "rho_0.5": {"rho": 0.5},
    "rho_2": {"rho": 2.0},
    "sigma_0.005": {"sigma": 0.005},
    "sigma_0.02": {"sigma": 0.02},
    "K0_6.25": {"K0": 6.25},
    "K0_100": {"K0": 100.0},
    "delta_0.005": {"delta": 0.005},
    "delta_0.02": {"delta": 0.02},
}


# --------------------------------------------------------------------------
# Balayage instrumenté
# --------------------------------------------------------------------------
def run_cell(job: tuple[str, int]) -> dict:
    cell, seed = job
    directory = SWEEP_DIR / cell / f"seed{seed}"
    marker = directory / "summary.json"
    if marker.exists():
        return {"cell": cell, "seed": seed, "skipped": True}
    started = time.time()
    config = Config(**{**BASE, **SWEEP[cell]}, seed=seed, T=BURN + WINDOW)
    simulation = Simulation(config)
    simulation.run()
    write_series(simulation, directory)
    rows = simulation.market_stats
    if rows:
        with open(directory / "market_stats.csv", "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    payload = {
        "cell": cell,
        "seed": seed,
        "t_final": simulation.t,
        "status": simulation.status,
        "wall_seconds": time.time() - started,
        "parameters": config.to_dict(),
        "book_errors": simulation.book.consistency_errors(simulation.population.alive),
    }
    marker.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"cell": cell, "seed": seed, "status": simulation.status,
            "wall_seconds": payload["wall_seconds"], "pop": simulation.series[-1]["pop"]}


def cmd_sweep() -> int:
    SWEEP_DIR.mkdir(parents=True, exist_ok=True)
    jobs = [(cell, seed) for cell in SWEEP for seed in SWEEP_SEEDS]
    started = time.time()
    with mp.Pool(processes=min(len(jobs), WORKERS)) as pool:
        done = 0
        for payload in pool.imap_unordered(run_cell, jobs):
            done += 1
            print(f"[{done}/{len(jobs)}] " + json.dumps(payload, ensure_ascii=False), flush=True)
    print(f"# balayage rotation : {len(jobs)} runs en {time.time() - started:.0f} s")
    return 0


# --------------------------------------------------------------------------
# Lecture des runs (les deux lignées)
# --------------------------------------------------------------------------
def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def parameters_of(directory: Path) -> dict | None:
    for name in ("summary.json", "burn.json", "run.json"):
        path = directory / name
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            params = payload.get("parameters")
            if params:
                return params
    return None


def window_means(rows: list[dict], columns, window: int) -> dict:
    """Moyennes sur les `window` derniers pas, plus un contrôle de stationnarité.

    Le contrôle est celui du protocole (§7) : rapport de la moyenne du dernier
    quart de la fenêtre à celle du quart précédent, sur K_tot, pop et
    prod_tot. Un bras hors de [0,99 ; 1,01] est signalé — il donne un
    transitoire, pas un niveau."""
    tail = rows[-window:]
    if len(tail) < window:
        return {}
    out = {}
    for column in columns:
        values = [float(row[column]) for row in tail if row.get(column) not in (None, "")]
        out[column] = sum(values) / len(values) if values else float("nan")
    quarter = window // 4
    for column in ("K_tot", "pop", "prod_tot"):
        last = [float(row[column]) for row in tail[-quarter:]]
        before = [float(row[column]) for row in tail[-2 * quarter:-quarter]]
        mean_last = sum(last) / len(last)
        mean_before = sum(before) / len(before)
        out[f"stat_{column}"] = mean_last / mean_before if mean_before else float("nan")
    return out


COLUMNS = ("loan_volume", "K_tot", "pop", "deaths", "mkt_rounds", "new_loans",
           "mkt_pool", "prod_tot", "births", "defaults")


def collect(root: Path, family: str, window: int) -> list[dict]:
    out = []
    for series_path in sorted(root.rglob("series.csv")):
        directory = series_path.parent
        params = parameters_of(directory)
        if params is None:
            continue
        rows = read_csv(series_path)
        if len(rows) < window:
            continue
        means = window_means(rows, COLUMNS, window)
        if not means:
            continue
        pop = means["pop"]
        if pop <= 0 or means["K_tot"] <= 0 or means["new_loans"] <= 0:
            continue
        rotation = means["loan_volume"] / means["K_tot"]
        f1 = means["mkt_rounds"] / pop
        f2 = means["new_loans"] / means["mkt_rounds"] if means["mkt_rounds"] else float("nan")
        mean_transfer = means["loan_volume"] / means["new_loans"]
        f3 = mean_transfer / (means["K_tot"] / pop)
        record = {
            "family": family,
            "run": str(directory.relative_to(root)),
            "rho": float(params.get("rho", 1.0)),
            "lam": float(params["lam"]),
            "sigma": float(params["sigma"]),
            "delta": float(params["delta"]),
            "K0": float(params["K0"]),
            "A": float(params["A"]),
            "gamma": float(params["gamma"]),
            "loan_direction": params.get("loan_direction", "richest_lends"),
            "pop": pop,
            "K_tot": means["K_tot"],
            "K_mean": means["K_tot"] / pop,
            "deaths_per_pop": means["deaths"] / pop,
            "births_per_pop": means["births"] / pop,
            "rotation": rotation,
            "f1_rounds_per_entity": f1,
            "f2_trade_probability": f2,
            "f3_transfer_over_Kmean": f3,
            "product": f1 * f2 * f3,
            "stat_K_tot": means.get("stat_K_tot", float("nan")),
            "stat_pop": means.get("stat_pop", float("nan")),
            "stat_prod_tot": means.get("stat_prod_tot", float("nan")),
        }
        gini_rows = read_csv(directory / "market_stats.csv")
        if gini_rows:
            tail = gini_rows[-window:]
            before = [float(row["gini_before"]) for row in tail]
            after = [float(row["gini_after"]) for row in tail]
            record["gini_before"] = sum(before) / len(before)
            record["gini_after"] = sum(after) / len(after)
            logmeans = [
                (b - a) / math.log(b / a) if b > 0 and a > 0 and b != a else b
                for b, a in zip(before, after)
            ]
            record["gini_logmean"] = sum(logmeans) / len(logmeans)
        out.append(record)
    return out


# --------------------------------------------------------------------------
# Ajustements
# --------------------------------------------------------------------------
def loglog_fit(xs: list[float], ys: list[float]) -> dict:
    """Moindres carrés sur ln y = a·ln x + b, avec R² et étendue de x.

    L'étendue est rapportée parce qu'un ajustement sur une plage étroite ne
    mesure rien (leçon d'analyse §14.1 du prompt : le garde-fou doit porter
    sur l'ÉTENDUE, pas sur le nombre de valeurs distinctes)."""
    pairs = [(math.log(x), math.log(y)) for x, y in zip(xs, ys) if x > 0 and y > 0]
    n = len(pairs)
    if n < 3:
        return {"n": n, "slope": float("nan"), "r2": float("nan"), "span": float("nan")}
    mean_x = sum(p[0] for p in pairs) / n
    mean_y = sum(p[1] for p in pairs) / n
    sxx = sum((p[0] - mean_x) ** 2 for p in pairs)
    sxy = sum((p[0] - mean_x) * (p[1] - mean_y) for p in pairs)
    syy = sum((p[1] - mean_y) ** 2 for p in pairs)
    slope = sxy / sxx if sxx else float("nan")
    intercept = mean_y - slope * mean_x
    r2 = (sxy * sxy) / (sxx * syy) if sxx and syy else float("nan")
    span = math.exp(max(p[0] for p in pairs) - min(p[0] for p in pairs))
    return {"n": n, "slope": slope, "intercept": intercept, "r2": r2,
            "factor": math.exp(intercept), "span": span}


def predicted_cv(record: dict) -> float:
    """CV prédit par le bilan de variance (voir la docstring du module)."""
    renewal = record["births_per_pop"]
    ratio = record["K0"] / record["K_mean"]
    return math.sqrt((renewal * (1.0 - ratio) ** 2 + record["sigma"] ** 2) / record["rho"])


# --------------------------------------------------------------------------
# Analyse
# --------------------------------------------------------------------------
def _write_csv(path: Path, rows: list[dict]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in keys})


def figure_decomposition(records: list[dict], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    try:
        from simulation_lab.plot_utils import apply_style

        apply_style()
    except Exception:
        pass

    figure, axes = plt.subplots(1, 3, figsize=(13, 4))
    families = sorted({row["family"] for row in records})
    colours = {"v1": "#c1440e", "v2": "#294c60", "balayage v2": "#7a9e9f"}
    for family in families:
        subset = [row for row in records if row["family"] == family]
        colour = colours.get(family, "#888888")
        axes[0].scatter([row["rho"] for row in subset],
                        [row["f1_rounds_per_entity"] for row in subset],
                        s=12, alpha=0.6, color=colour, label=family)
        axes[1].scatter([row["rotation"] for row in subset],
                        [row["f2_trade_probability"] for row in subset],
                        s=12, alpha=0.6, color=colour, label=family)
        axes[2].scatter([row["f3_transfer_over_Kmean"] for row in subset],
                        [row["rotation"] / row["rho"] for row in subset],
                        s=12, alpha=0.6, color=colour, label=family)
    lo = min(row["f3_transfer_over_Kmean"] for row in records)
    hi = max(row["f3_transfer_over_Kmean"] for row in records)
    axes[2].plot([lo, hi], [lo, hi], color="black", lw=0.8, ls="--", label="identité")

    axes[0].set_xlabel(r"$\rho$ (paramètre)")
    axes[0].set_ylabel(r"$f_1$ = rondes / entité")
    axes[0].set_title(r"(a) $f_1 = \lfloor \rho N\rfloor / N$ : combinatoire pure", fontsize=9)
    axes[1].set_xlabel("rotation du crédit")
    axes[1].set_ylabel(r"$f_2$ = prêts conclus / rondes")
    axes[1].set_title("(b) $f_2$ : probabilité de traiter", fontsize=9)
    axes[2].set_xlabel(r"$f_3 = \mathbb{E}|\delta| / \bar K$")
    axes[2].set_ylabel(r"rotation $/\ \rho$")
    axes[2].set_title(r"(c) toute la variation est dans $f_3$", fontsize=9)
    for axis in axes:
        axis.grid(True, alpha=0.2)
        axis.legend(fontsize=7)
    figure.suptitle("Décomposition de la rotation du crédit en trois facteurs")
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(figure)


def figure_closure(records: list[dict], path: Path, fit: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    try:
        from simulation_lab.plot_utils import apply_style

        apply_style()
    except Exception:
        pass

    with_gini = [row for row in records if "gini_logmean" in row]
    figure, axes = plt.subplots(1, 2, figsize=(11, 4.2))

    if with_gini:
        for row in with_gini:
            pass
        axes[0].scatter([row["gini_logmean"] for row in with_gini],
                        [row["f3_transfer_over_Kmean"] for row in with_gini],
                        s=22, color="#294c60", label=r"$\bar G$ (moyenne logarithmique)")
        axes[0].scatter([row["gini_before"] for row in with_gini],
                        [row["f3_transfer_over_Kmean"] for row in with_gini],
                        s=16, color="#c1440e", marker="^", alpha=0.7,
                        label=r"$G$ avant la phase de marché")
        lo = min(row["gini_logmean"] for row in with_gini) * 0.9
        hi = max(row["gini_before"] for row in with_gini) * 1.05
        axes[0].plot([lo, hi], [lo, hi], color="black", lw=0.8, ls="--", label="identité")
    axes[0].set_xlabel("coefficient de Gini des capitaux")
    axes[0].set_ylabel(r"$f_3 = \mathbb{E}|\delta|/\bar K$ mesuré")
    axes[0].set_title(r"(a) $f_3$ EST le Gini des capitaux", fontsize=9)

    if with_gini:
        xs = [predicted_cv(row) for row in with_gini]
        ys = [row["f3_transfer_over_Kmean"] for row in with_gini]
        labels = [row["run"].split("/")[0] for row in with_gini]
        axes[1].scatter(xs, ys, s=22, color="#294c60")
        for x, y, label in zip(xs, ys, labels):
            axes[1].annotate(label, (x, y), fontsize=5, alpha=0.7,
                             textcoords="offset points", xytext=(3, 3))
        if fit.get("n", 0) >= 3:
            grid = [min(xs), max(xs)]
            axes[1].plot(grid, [fit["factor"] * x ** fit["slope"] for x in grid],
                         color="#c1440e", lw=1.2,
                         label=(f"ajustement : pente {fit['slope']:.3f}, "
                                f"$R^2$ = {fit['r2']:.4f}"))
        axes[1].plot([min(xs), max(xs)],
                     [x / math.sqrt(math.pi) for x in (min(xs), max(xs))],
                     color="black", lw=0.8, ls="--", label=r"prédiction $CV/\sqrt{\pi}$")
        axes[1].legend(fontsize=7)
    axes[1].set_xlabel(r"$CV$ prédit $= \sqrt{[(\lambda/N)(1-K_0/\bar K)^2 + \sigma^2]/\rho}$")
    axes[1].set_ylabel(r"$f_3$ mesuré")
    axes[1].set_title("(b) la fermeture par le bilan de variance", fontsize=9)
    axes[0].legend(fontsize=7)
    for axis in axes:
        axis.grid(True, alpha=0.2)
        axis.set_xscale("log")
        axis.set_yscale("log")
    figure.suptitle("Ce qui détermine la rotation du crédit")
    figure.tight_layout()
    figure.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(figure)


def write_table(path: Path, payload: dict) -> None:
    def number(value: float, digits: int = 3) -> str:
        if value != value:
            return "---"
        return f"{value:.{digits}f}".replace(".", ",")

    lines = [
        r"\begin{tabular}{lrrr}",
        r"\toprule",
        r"relation ajustée & exposant & $R^2$ & étendue de $x$ \\",
        r"\midrule",
    ]
    for label, fit in payload["fits"]:
        lines.append(
            f"{label} & {number(fit['slope'])} & {number(fit['r2'], 4)} & "
            f"$\\times{number(fit['span'], 1)}$ \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_analyse(window: int = 1000) -> int:
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    records = []
    records += collect(V1_ROOT / "results", "v1", window)
    records += collect(ROOT / "results" / "campaign", "v2", window)
    records += collect(SWEEP_DIR, "balayage v2", min(window, WINDOW))
    if not records:
        print("aucun run exploitable", file=sys.stderr)
        return 1
    _write_csv(ANALYSIS / "rotation_runs.csv", records)

    homogeneous = [
        row for row in records
        if row["family"] != "v1" or "frac_" not in row["run"]
    ]
    stationary = [
        row for row in records
        if 0.99 <= row["stat_K_tot"] <= 1.01 and 0.99 <= row["stat_pop"] <= 1.01
    ]
    with_gini = [row for row in records if "gini_logmean" in row]

    fits = []
    fits.append((
        r"mortalité $\sim$ rotation (tous runs)",
        loglog_fit([row["rotation"] for row in records],
                   [row["deaths_per_pop"] for row in records]),
    ))
    fits.append((
        r"mortalité $\sim$ rotation (runs stationnaires)",
        loglog_fit([row["rotation"] for row in stationary],
                   [row["deaths_per_pop"] for row in stationary]),
    ))
    if with_gini:
        fits.append((
            r"$f_3 \sim \bar G$ (Gini, moyenne logarithmique)",
            loglog_fit([row["gini_logmean"] for row in with_gini],
                       [row["f3_transfer_over_Kmean"] for row in with_gini]),
        ))
        fits.append((
            r"$f_3 \sim CV$ prédit (bilan de variance)",
            loglog_fit([predicted_cv(row) for row in with_gini],
                       [row["f3_transfer_over_Kmean"] for row in with_gini]),
        ))
        fits.append((
            r"rotation $\sim CV$ prédit $\times\ \rho$",
            loglog_fit([predicted_cv(row) * row["rho"] for row in with_gini],
                       [row["rotation"] for row in with_gini]),
        ))

    closure = fits[-1][1] if with_gini else {}
    summary = {
        "window": window,
        "n_runs": len(records),
        "n_stationary": len(stationary),
        "n_with_gini": len(with_gini),
        "f1_vs_rho_max_gap": max(
            abs(row["f1_rounds_per_entity"] - row["rho"]) for row in records
        ),
        "f2_min": min(row["f2_trade_probability"] for row in records),
        "f2_max": max(row["f2_trade_probability"] for row in records),
        "identity_max_gap": max(
            abs(row["product"] / row["rotation"] - 1.0) for row in records
        ),
        "fits": {label: fit for label, fit in fits},
    }
    if with_gini:
        gaps = [row["f3_transfer_over_Kmean"] / row["gini_logmean"] - 1.0 for row in with_gini]
        summary["f3_over_gini_logmean"] = {
            "median": sorted(gaps)[len(gaps) // 2],
            "min": min(gaps),
            "max": max(gaps),
        }
        before = [row["f3_transfer_over_Kmean"] / row["gini_before"] - 1.0 for row in with_gini]
        summary["f3_over_gini_before"] = {
            "median": sorted(before)[len(before) // 2],
            "min": min(before),
            "max": max(before),
        }
        predicted = [
            row["rotation"] / (row["rho"] * predicted_cv(row) / math.sqrt(math.pi)) - 1.0
            for row in with_gini
        ]
        summary["rotation_over_closed_form"] = {
            "median": sorted(predicted)[len(predicted) // 2],
            "min": min(predicted),
            "max": max(predicted),
        }
    (ANALYSIS / "rotation_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    figure_decomposition(records, FIGURES / "rotation_decomposition.png")
    figure_closure(records, FIGURES / "rotation_closure.png", closure)
    write_table(TABLES / "rotation.tex", {"fits": fits})

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else "analyse"
    if command == "sweep":
        return cmd_sweep()
    if command == "analyse":
        window = int(argv[2]) if len(argv) > 2 else 1000
        return cmd_analyse(window)
    print(f"commande inconnue : {command}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
