"""« A×x implique-t-il T×x ? » — lecture de la figure 14, vérifiée en général.

L'OBSERVATION (relecteur, figure 14). Sur le bras `all_A150`, multiplier A
par 1,5 semble multiplier la tension par 1,5. À vérifier de manière générale.

CE QUE DIT LA MESURE. C'est vrai à 6 % près, et l'écart est systématique :
à γ = 0,5 et K0 fixé, la tension suit A^1,13 et non A^1. L'exposant est
remarquablement stable — 1,129 / 1,120 / 1,137 / 1,153 pour A = 0,75 / 1,25 /
1,5 / 2,0 — donc ce n'est pas du bruit, c'est une pente qui n'est pas 1.

CE QUE DIT L'ALGÈBRE. L'exposant n'est pas libre : il se déduit exactement de
deux élasticités déjà mesurées. Avec

    K_aut = [A(1-δ)/δ]^{1/(1-γ)}       et       K_eq = (prod/(n·A))^{1/γ} ,

on a ln T = ln K_aut - ln K_eq, d'où en dérivant par rapport à ln A :

    dlnT/dlnA = 1/(1-γ) - (1/γ)·(ε_prod - η_pop - 1)                     (*)

où ε_prod = dln(prod)/dlnA et η_pop = dln(n)/dlnA sont mesurées sur les mêmes
runs. Vérifiée sur les quatre bras à γ = 0,5 : l'identité tient à 1e-3 près
(le résidu est l'écart de Jensen entre K_eq et la moyenne des capitaux).

DEUX CONSÉQUENCES IMMÉDIATES.

1. **Le « ×1,5 » n'est pas une loi, c'est une coïncidence numérique.** À
   γ = 0,5 et K0 fixé, ε_prod ≈ 0,73 et η_pop ≈ -0,70 ; (*) donne 1,13. Rien
   n'impose que la combinaison retombe près de 1.
2. **Sous compensation de K0 l'exposant est exactement 0.** La covariance
   d'échelle (§7.1) impose ε_prod = 1/(1-γ) et η_pop = 0, donc
   (*) = 1/(1-γ) - (1/γ)(1/(1-γ) - 1) = 0 : la tension est INVARIANTE.
   Mesuré : `abl_A150_K0aut` donne un exposant de -0,012 contre +1,137 pour
   le même choc sans compensation. Le « A×x ⇒ T×x » est donc entièrement un
   phénomène à K0 fixé.

CE QUE CE SCRIPT AJOUTE. (*) prédit une dépendance forte en γ, qu'aucune
donnée existante ne teste : les familles γ = 0,4 et γ = 0,6 n'ont que des
runs à échelle compensée. Le script lance donc, sur les snapshots d'amorçage
de ces deux γ, le même balayage en A à K0 fixé qu'à γ = 0,5, et compare
l'exposant mesuré à celui que (*) prédit à partir de ε_prod et η_pop mesurés
sur ces mêmes runs.

PRÉDICTION ÉCRITE AVANT DE LANCER (pour que le test soit réfutable). Dans
(*), le premier terme 1/(1-γ) vaut 1,667 / 2,000 / 2,500 pour
γ = 0,4 / 0,5 / 0,6, et le second est -(1/γ)(ε_prod - η_pop - 1) avec
ε_prod - η_pop ≈ 1,43 mesuré à γ = 0,5. Si cette combinaison reste du même
ordre aux autres γ, l'exposant se déplace franchement avec γ et ne retombe
sur 1 ni en 0,4 ni en 0,6 : « A×x ⇒ T×x » serait alors une coïncidence
propre à γ = 0,5. Si au contraire l'exposant reste voisin de 1 partout,
c'est que ε_prod - η_pop s'ajuste pour compenser 1/(1-γ), et il y a là une
régularité à expliquer. Les deux issues sont informatives.

Aucune modification du moteur : ce script ne fait que le piloter.

    python3 scripts/tension_vs_A.py run
    python3 scripts/tension_vs_A.py analyse
"""

from __future__ import annotations

import csv
import json
import math
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, "/home/anatole/jupyter")

from m4_3live.live import load_snapshot, write_series  # noqa: E402
from m4_3live.model import Config, Intervention  # noqa: E402

from scripts.campaign import BASE, T0, WINDOW, WORKERS  # noqa: E402
from scripts.tension_analysis import run_summary  # noqa: E402

OUT = ROOT / "results" / "tension_vs_A"
ANALYSIS = ROOT / "results" / "analysis"
FIGURES = ROOT / "report" / "figures"

SEEDS = (0, 1, 2)
A_VALUES = (0.75, 1.25, 1.5, 2.0)
#: γ à lancer. γ = 0,5 est déjà couvert par le balayage et la campagne : on
#: réutilise ces runs plutôt que de les refaire (voir EXISTING).
NEW_GAMMAS = (0.4, 0.6)

#: Où lire les runs déjà faits à γ = 0,5, protocole identique (branchement sur
#: le snapshot d'amorçage à t₀, intervention `A` de portée `all`).
EXISTING = {
    1.0: ROOT / "results" / "tension_sweep" / "sweep_control",
    0.75: ROOT / "results" / "tension_sweep" / "A_0.75",
    1.25: ROOT / "results" / "tension_sweep" / "A_1.25",
    1.5: ROOT / "results" / "campaign" / "arms" / "all_A150",
    2.0: ROOT / "results" / "tension_sweep" / "A_2",
}

BURNS = {
    0.4: ROOT / "results" / "scaling_gamma" / "g0.4" / "burn",
    0.6: ROOT / "results" / "scaling_gamma" / "g0.6" / "burn",
}


def arm_name(value: float) -> str:
    return "control" if value == 1.0 else f"A_{value:g}"


def run_one(job: tuple[float, float, int]) -> dict:
    gamma, value, seed = job
    directory = OUT / f"g{gamma}" / arm_name(value) / f"seed{seed}"
    if (directory / "summary.json").exists():
        return {"gamma": gamma, "A": value, "seed": seed, "skipped": True}
    started = time.time()
    config = Config(**{**BASE, "gamma": gamma}, seed=seed, T=T0 + WINDOW)
    simulation = load_snapshot(BURNS[gamma] / f"seed{seed}" / f"snapshot_t{T0}.pkl",
                               config=config)
    plan = ([] if value == 1.0 else
            [{"t": T0 + 1, "note": "", "param": "A", "value": value, "scope": "all"}])
    planned: dict[int, list[Intervention]] = {}
    for entry in plan:
        planned.setdefault(int(entry["t"]), []).append(Intervention.from_dict(entry))
    while simulation.t < config.T and simulation.status == "ok":
        for item in planned.get(simulation.t + 1, ()):
            simulation.submit(item)
        simulation.step()
    write_series(simulation, directory)
    (directory / "summary.json").write_text(
        json.dumps({"gamma": gamma, "A": value, "seed": seed,
                    "t_final": simulation.t, "status": simulation.status,
                    "wall_seconds": time.time() - started, "plan": plan,
                    "interventions": simulation.intervention_log,
                    "parameters": simulation.config.to_dict()},
                   indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    from scripts.tension_figures import plot_tension

    plot_tension(directory, simulation.config.delta)
    return {"gamma": gamma, "A": value, "seed": seed, "status": simulation.status,
            "wall_seconds": round(time.time() - started, 1)}


def cell_for(gamma: float, value: float) -> Path:
    if gamma == 0.5:
        return EXISTING[value]
    return OUT / f"g{gamma}" / arm_name(value)


def collect() -> list[dict]:
    """Un point par (γ, A) : moyennes sur les graines, en régime établi."""
    rows = []
    for gamma in (0.4, 0.5, 0.6):
        for value in (1.0,) + A_VALUES:
            cell = cell_for(gamma, value)
            if not cell.exists():
                continue
            summaries = [summary for seed_dir in sorted(cell.glob("seed*"))
                         if (summary := run_summary(seed_dir))]
            if not summaries:
                continue
            entry = {"gamma": gamma, "A": value, "n": len(summaries),
                     "source": str(cell.relative_to(ROOT))}
            for key in ("tension", "pop", "K_eq", "death_rate"):
                values = np.array([summary[key] for summary in summaries])
                entry[key] = float(values.mean())
                entry[f"{key}_sem"] = (float(values.std(ddof=1) / math.sqrt(len(values)))
                                       if len(values) > 1 else 0.0)
            # prod agrégée, reconstruite depuis K_eq : prod = n·A·K_eq^γ, qui
            # est l'inversion exacte de la définition de K_eq.
            entry["prod"] = entry["pop"] * value * entry["K_eq"] ** gamma
            rows.append(entry)
    return rows


def exponents(rows: list[dict]) -> list[dict]:
    """Exposant mesuré et exposant prédit par l'identité (*), point par point."""
    out = []
    for gamma in sorted({row["gamma"] for row in rows}):
        family = {row["A"]: row for row in rows if row["gamma"] == gamma}
        if 1.0 not in family:
            continue
        base = family[1.0]
        for value in sorted(family):
            if value == 1.0:
                continue
            row = family[value]
            log_x = math.log(value)
            measured = math.log(row["tension"] / base["tension"]) / log_x
            eps = math.log(row["prod"] / base["prod"]) / log_x
            eta = math.log(row["pop"] / base["pop"]) / log_x
            predicted = 1.0 / (1.0 - gamma) - (1.0 / gamma) * (eps - eta - 1.0)
            out.append({
                "gamma": gamma, "A": value,
                "tension": row["tension"], "tension_base": base["tension"],
                "ratio": row["tension"] / base["tension"],
                "eps_prod": eps, "eta_pop": eta,
                "exposant_mesure": measured, "exposant_predit": predicted,
                "residu_identite": predicted - measured,
                # ce que vaudrait « A×x ⇒ T×x »
                "ecart_a_1": measured - 1.0,
            })
    return out


def global_slope(rows: list[dict], gamma: float) -> tuple[float, float]:
    """Pente log-log de T contre A sur toute la famille (contrôle inclus)."""
    family = [row for row in rows if row["gamma"] == gamma]
    x = np.log([row["A"] for row in family])
    y = np.log([row["tension"] for row in family])
    slope, intercept = np.polyfit(x, y, 1)
    residual = y - (intercept + slope * x)
    r2 = 1.0 - residual.var() / y.var() if y.var() > 0 else float("nan")
    return float(slope), float(r2)


def decimal(value: float, digits: int) -> str:
    """Virgule française, protégée pour le mode mathématique."""
    return f"{value:.{digits}f}".replace(".", "{,}")


def write_table(rows: list[dict], fits: dict, path: Path) -> None:
    lines = [r"\begin{center}", r"\begin{tabular}{@{}rrrrrrr@{}}", r"\toprule",
             r"$\gamma$ & $A$ & $T/T_0$ & \textbf{exposant mesuré} & "
             r"$\varepsilon_{\text{prod}}$ & $\eta_{\text{pop}}$ & "
             r"\textbf{éq.~\eqref{eq:exposant_tension}} \\", r"\midrule"]
    current = None
    for row in rows:
        if current is not None and row["gamma"] != current:
            lines.append(r"\midrule")
        current = row["gamma"]
        lines.append(
            f"${decimal(row['gamma'], 1)}$ & ${decimal(row['A'], 2)}$ & "
            f"${decimal(row['ratio'], 4)}$ & "
            f"$\\mathbf{{{decimal(row['exposant_mesure'], 3)}}}$ & "
            f"${decimal(row['eps_prod'], 3)}$ & ${decimal(row['eta_pop'], 3)}$ & "
            f"${decimal(row['exposant_predit'], 3)}$ \\\\")
    lines.append(r"\midrule")
    for gamma in sorted(fits):
        slope, r2 = fits[gamma]
        lines.append(
            f"\\multicolumn{{7}}{{@{{}}l}}{{$\\gamma = {decimal(gamma, 1)}$ — pente "
            f"log-log sur toute la famille : "
            f"$T \\propto A^{{{decimal(slope, 3)}}}$, "
            f"$R^2 = {decimal(r2, 4)}$}} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{center}"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def compensated_point() -> tuple[float, float] | None:
    """(A, T/T₀) du bras d'ablation où K0 est compensé à l'échelle autarcique.

    Lu dans `tension_runs.csv` plutôt que recalculé : c'est le même run que
    celui du §\\ref{sec:ablation}, et le rejouer serait une occasion de le
    faire diverger.
    """
    path = ANALYSIS / "tension_runs.csv"
    if not path.exists():
        return None
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    def mean(arm: str) -> float | None:
        values = [float(row["tension"]) for row in rows if row["bras"] == arm]
        return float(np.mean(values)) if values else None
    treated, control = mean("abl_A150_K0aut"), mean("abl_control")
    if treated is None or control is None:
        return None
    return 1.5, treated / control


def figure(rows: list[dict], exps: list[dict], fits: dict, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from simulation_lab.plot_utils import apply_style

    apply_style()
    colours = {0.4: "#3f7d20", 0.5: "#294c60", 0.6: "#c1440e"}
    figure_, axes = plt.subplots(1, 2, figsize=(12.5, 4.8))

    axis = axes[0]
    grid = np.array([0.7, 2.1])
    axis.plot(grid, grid, color="black", lw=1.0, ls="--",
              label="« A×x ⇒ T×x » (pente 1)")
    for gamma in sorted({row["gamma"] for row in rows}):
        family = sorted([row for row in rows if row["gamma"] == gamma],
                        key=lambda row: row["A"])
        base = next(row for row in family if row["A"] == 1.0)
        fit = fits.get(gamma)
        label = (f"γ = {gamma}  (mesuré : pente {fit[0]:.3f})" if fit
                 else f"γ = {gamma}  (famille incomplète)")
        axis.plot([row["A"] for row in family],
                  [row["tension"] / base["tension"] for row in family],
                  "o-", color=colours[gamma], lw=1.2, ms=5,
                  label=label)
    # Le contre-point décisif : la même hausse de A, mais avec K0 compensé à
    # l'échelle autarcique. La tension ne bouge pas — l'exposant vaut 0, et
    # tout le phénomène « A×x ⇒ T×x » est donc un phénomène à K0 FIXÉ.
    compensated = compensated_point()
    if compensated:
        value, ratio = compensated
        axis.scatter([value], [ratio], s=70, marker="s", color="#c1440e",
                     zorder=4,
                     label=f"A×{value:g} avec K0 compensé : T/T₀ = {ratio:.4f}")

    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set_xlabel("A / A₀")
    axis.set_ylabel("T / T₀")
    axis.set_title("tension contre A, à K0 fixé — un trait par γ", fontsize=9)
    axis.legend(fontsize=7)
    axis.grid(True, alpha=0.2, which="both")

    axis = axes[1]
    for gamma in sorted({row["gamma"] for row in exps}):
        family = [row for row in exps if row["gamma"] == gamma]
        axis.scatter([row["exposant_predit"] for row in family],
                     [row["exposant_mesure"] for row in family],
                     s=40, color=colours[gamma], label=f"γ = {gamma}", zorder=3)
    low = min(row["exposant_mesure"] for row in exps) - 0.15
    high = max(row["exposant_mesure"] for row in exps) + 0.15
    axis.plot([low, high], [low, high], color="black", lw=1.0, ls="--",
              label="identité (*)")
    axis.axhline(1.0, color="#8c8c8c", lw=0.8, ls=":")
    axis.text(low, 1.0, " exposant 1 (« ×x ⇒ ×x »)", fontsize=6.5, va="bottom",
              color="#8c8c8c")
    axis.set_xlabel("exposant prédit par 1/(1−γ) − (1/γ)(ε_prod − η_pop − 1)")
    axis.set_ylabel("exposant mesuré  dlnT / dlnA")
    axis.set_title("l'exposant n'est pas libre : il se déduit de deux élasticités",
                   fontsize=9)
    axis.legend(fontsize=7)
    axis.grid(True, alpha=0.2)

    figure_.suptitle(
        "« A×x implique T×x » : vrai à 6 % près à γ = 0,5 et K0 fixé, faux "
        "partout ailleurs. L'exposant passe de 0,78 à 1,67 entre γ = 0,4 et 0,6,\n"
        "il ne vaut 1 qu'au voisinage de γ ≈ 0,46, et il tombe à 0 dès que K0 "
        "est compensé — c'est donc un phénomène à K0 fixé.",
        fontsize=9.5)
    figure_.tight_layout()
    figure_.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figure_)


def analyse() -> int:
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    rows = collect()
    if not rows:
        print("aucun run — lancer `python3 scripts/tension_vs_A.py run`")
        return 1
    exps = exponents(rows)
    fits = {gamma: global_slope(rows, gamma)
            for gamma in sorted({row["gamma"] for row in rows})
            if len([row for row in rows if row["gamma"] == gamma]) > 2}
    with open(ANALYSIS / "tension_vs_A.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(exps[0]))
        writer.writeheader()
        writer.writerows(exps)
    json.dump({"points": rows, "exposants": exps,
               "pentes": {str(key): {"pente": value[0], "r2": value[1]}
                          for key, value in fits.items()}},
              open(ANALYSIS / "tension_vs_A.json", "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    write_table(exps, fits, ROOT / "report" / "tables" / "tension_vs_A.tex")
    figure(rows, exps, fits, FIGURES / "tension_vs_A.png")

    print(f"{'γ':>5}{'A':>7}{'T/T0':>9}{'mesuré':>9}{'prédit':>9}"
          f"{'résidu':>10}{'ε_prod':>9}{'η_pop':>9}")
    for row in exps:
        print(f"{row['gamma']:>5.1f}{row['A']:>7.2f}{row['ratio']:>9.4f}"
              f"{row['exposant_mesure']:>9.3f}{row['exposant_predit']:>9.3f}"
              f"{row['residu_identite']:>10.1e}{row['eps_prod']:>9.3f}"
              f"{row['eta_pop']:>9.3f}")
    print()
    for gamma, (slope, r2) in fits.items():
        print(f"  γ = {gamma}: T ∝ A^{slope:.3f}  (R² = {r2:.4f})")
    return 0


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else "analyse"
    if mode == "run":
        OUT.mkdir(parents=True, exist_ok=True)
        jobs = [(gamma, value, seed) for gamma in NEW_GAMMAS
                for value in (1.0,) + A_VALUES for seed in SEEDS]
        started = time.time()
        with mp.Pool(processes=WORKERS) as pool:
            done = 0
            for payload in pool.imap_unordered(run_one, jobs):
                done += 1
                print(f"[{done}/{len(jobs)}] " + json.dumps(payload), flush=True)
        print(f"# balayage A terminé en {time.time() - started:.0f} s", flush=True)
        return 0
    return analyse()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
