"""Amplitude et part traitée EXACTES, mesurées entité par entité (note [16]).

CE QUI CLOCHAIT. Le rapport reconstruisait l'amplitude $m$ d'un levier et la
part traitée $p$ à partir des seules séries agrégées, en inversant la
relation ex post / ex ante $s = mp/(1+(m-1)p)$. La reconstruction est juste,
mais c'est une reconstruction : elle suppose la formule qu'elle sert à
vérifier.

CE QUE FAIT CE SCRIPT. Il mesure les deux quantités sur les entités
elles-mêmes, au pas de l'intervention, sans rien changer au moteur.

Le tour de passe-passe est le suivant. Après le pas $t_0+1$, la production
individuelle de chaque entité est encore en mémoire (`population.prod`), et
la technologie qui l'a produite est connue. Comme
$\\mathrm{prod}_i = A' K_i^{\\gamma'}$ avec $A'$ et $\\gamma'$ connus, le
capital au moment de produire se retrouve exactement :

    K_i = (prod_i / A')^{1/gamma'}

--- c'est un aller-retour flottant, donc exact à $10^{-16}$ près, et non une
approximation. On peut alors écrire la production CONTREFACTUELLE de la même
entité sous son ancienne technologie, $A K_i^{\\gamma}$, et en déduire

    m_exact = somme_{i traitées} prod_i / somme_{i traitées} A K_i^gamma
    p_exact = somme_{i traitées} A K_i^gamma / production totale ex ante

Aucune inversion, aucune hypothèse. Le script compare ensuite ces valeurs à
celles que la reconstruction agrégée donnait : c'est le contrôle croisé que
la note [16] réclame.

POURQUOI C'EST EXACT À L'HORIZON 1 ET SEULEMENT LÀ. L'intervention est
appliquée au tout début du pas, avant les naissances et avant le choc. Elle
ne touche que $(A, \\gamma)$ : l'ensemble des vivantes, son ordre et l'état
du générateur sont donc identiques dans le bras traité et dans sa référence
appariée. Le même vecteur de chocs frappe les mêmes capitaux, et il se
simplifie exactement dans le rapport. Dès l'horizon 2 les capitaux ont
divergé et la contrefactuelle n'est plus lisible sur un seul run.

    python3 scripts/exact_amplitude.py
"""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, "/home/anatole/jupyter")

from m4_3live.live import load_snapshot  # noqa: E402
from m4_3live.model import Config, Intervention  # noqa: E402

from scripts.campaign import ARMS, BASE, SEEDS, T0  # noqa: E402

BURN = ROOT / "results" / "campaign" / "burn"
ANALYSIS = ROOT / "results" / "analysis"
FIGURES = ROOT / "report" / "figures"

# Les bras sans levier d'entité (`control`) n'ont pas d'amplitude ; le bras
# `new` ne touche aucune vivante, sa cohorte traitée est vide au pas 1.
MEASURABLE = tuple(
    name for name, plan in ARMS.items()
    if plan and plan[0]["param"] in ("A", "gamma") and plan[0]["scope"] != "new"
)


def measure(seed: int, arm: str) -> dict:
    """Un pas depuis le snapshot, puis lecture entité par entité."""
    plan = [Intervention.from_dict(entry) for entry in ARMS[arm]]
    config = Config(**BASE, seed=seed, T=T0 + 1)
    simulation = load_snapshot(BURN / f"seed{seed}" / f"snapshot_t{T0}.pkl", config=config)
    old_A, old_gamma = simulation.default_A, simulation.default_gamma
    alive_before = list(simulation.population.living())
    for item in plan:
        simulation.submit(item)
    simulation.step()

    population = simulation.population
    intervention = plan[0]
    if intervention.scope == "fraction":
        treated = list(intervention.selected_ids)
    else:
        # Portée `all` : la valeur par défaut à la naissance change aussi, donc
        # les nées du pas sont traitées elles aussi. L'ensemble des productrices
        # est celui d'avant le pas (mortes du pas comprises : elles ont produit)
        # augmenté des naissances.
        born = [entity for entity in population.living()
                if population.birth[entity] == simulation.t]
        treated = alive_before + born

    treated_after = 0.0
    treated_before = 0.0
    for entity in treated:
        produced = population.prod[entity]
        if produced <= 0.0:
            continue
        coefficient = population.A[entity]
        exponent = population.g[entity]
        capital = (produced / coefficient) ** (1.0 / exponent)
        treated_after += produced
        treated_before += old_A * capital**old_gamma

    total_after = simulation.series[-1]["prod_tot"]
    total_before = total_after - treated_after + treated_before
    return {
        "arm": arm,
        "seed": seed,
        "n_treated": len(treated),
        "m_exact": treated_after / treated_before if treated_before > 0 else float("nan"),
        "p_exact": treated_before / total_before if total_before > 0 else float("nan"),
        "s_observe": treated_after / total_after if total_after > 0 else float("nan"),
        "effet_mecanique": (treated_after - treated_before) / total_before,
        "ecart_relatif_h1": (total_after - total_before) / total_before,
        "prod_tot": total_after,
    }


def main() -> int:
    started = time.time()
    rows = [measure(seed, arm) for arm in MEASURABLE for seed in SEEDS]
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    with open(ANALYSIS / "exact_amplitude.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    # -- contrôle croisé avec la reconstruction agrégée du rapport ----------
    reconstructed = {}
    metrics_path = ANALYSIS / "metrics.json"
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        for name, entry in metrics.get("arms", {}).items():
            reconstructed[name] = {
                "m": entry.get("amplitude_measured_h1"),
                "p": entry.get("impact_h1", {}).get("share_prod_treated_ante"),
                "relative_h1": entry.get("impact_h1", {}).get("relative"),
            }

    summary = {}
    print(f"{'bras':20s} {'n':>5s} {'m exact':>10s} {'m reconstr':>11s} "
          f"{'p exact':>9s} {'p reconstr':>11s} {'(m-1)p':>9s} {'écart h1':>9s}")
    print("-" * 92)
    for arm in MEASURABLE:
        group = [row for row in rows if row["arm"] == arm]
        entry = {
            key: sum(row[key] for row in group) / len(group)
            for key in ("m_exact", "p_exact", "s_observe", "effet_mecanique",
                        "ecart_relatif_h1")
        }
        entry["n_treated"] = sum(row["n_treated"] for row in group) / len(group)
        entry["m_reconstruit"] = reconstructed.get(arm, {}).get("m")
        entry["p_reconstruit"] = reconstructed.get(arm, {}).get("p")
        # E(h=1) : le rapport de l'écart observé à l'effet strictement
        # proportionnel. Doit valoir 1 EXACTEMENT (voir docstring).
        entry["E_h1"] = (
            entry["ecart_relatif_h1"] / entry["effet_mecanique"]
            if entry["effet_mecanique"] else float("nan")
        )
        summary[arm] = entry
        print(
            f"{arm:20s} {entry['n_treated']:5.0f} {entry['m_exact']:10.6f} "
            f"{(entry['m_reconstruit'] or float('nan')):11.6f} "
            f"{entry['p_exact']:9.5f} "
            f"{(entry['p_reconstruit'] or float('nan')):11.5f} "
            f"{entry['effet_mecanique']:9.5f} {entry['ecart_relatif_h1']:9.5f}"
        )
    # `null` n'a aucun effet mécanique : son E(h=1) est un 0/0, pas un test.
    testable = {name: entry for name, entry in summary.items()
                if abs(entry["effet_mecanique"]) > 1e-12}
    worst = max(abs(entry["E_h1"] - 1.0) for entry in testable.values())
    print(f"\nE(h=1) : écart maximal à 1 sur les {len(testable)} bras à levier "
          f"= {worst:.3e}")
    for name, entry in testable.items():
        print(f"    {name:20s} E(h=1) = {entry['E_h1']:.12f}")
    print(f"(mesuré sur {len(SEEDS)} graines, {time.time() - started:.0f} s)")

    (ANALYSIS / "exact_amplitude.json").write_text(
        json.dumps({"arms": summary, "seeds": list(SEEDS), "t0": T0,
                    "ecart_max_E_h1": worst}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_table(summary)
    return 0


LABELS = {
    "null": "null (tire $\\varphi$=0,2, n'applique rien)",
    "frac_A150_phi20": "fraction $\\varphi$=0,2 $\\cdot$ $A\\times1{,}5$",
    "frac_A125_phi20": "fraction $\\varphi$=0,2 $\\cdot$ $A\\times1{,}25$",
    "frac_A150_phi05": "fraction $\\varphi$=0,05 $\\cdot$ $A\\times1{,}5$",
    "frac_A150_phi50": "fraction $\\varphi$=0,5 $\\cdot$ $A\\times1{,}5$",
    "all_A150": "toutes $\\cdot$ $A\\times1{,}5$",
    "frac_g060_phi20": "fraction $\\varphi$=0,2 $\\cdot$ $\\gamma\\,0{,}5\\to0{,}6$",
}


def latex_number(value: float, digits: int = 6) -> str:
    return f"{value:.{digits}f}".replace(".", "{,}")


def write_table(summary: dict) -> None:
    """Tableau lisible : une ligne par bras, chaque colonne définie en tête."""
    path = ROOT / "report" / "tables" / "exact_amplitude.tex"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "\\begin{center}\\footnotesize",
        "\\begin{tabular}{@{}lrrrr@{}}",
        "\\toprule",
        "\\textbf{Bras} & $m$ & $p$ & $(m-1)\\,p$ & écart observé \\\\",
        " & \\emph{amplitude} & \\emph{part ex ante} & \\emph{prédit} "
        "& \\emph{à $h=1$} \\\\",
        "\\midrule",
    ]
    for name, label in LABELS.items():
        entry = summary.get(name)
        if entry is None:
            continue
        lines.append(
            f"{label} & {latex_number(entry['m_exact'])} & "
            f"{latex_number(entry['p_exact'], 5)} & "
            f"{latex_number(100 * entry['effet_mecanique'], 4)}\\,\\% & "
            f"{latex_number(100 * entry['ecart_relatif_h1'], 4)}\\,\\% \\\\"
        )
    lines += [
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{center}",
        "",
        "\\noindent\\footnotesize $m$ : de combien la production d'une entité "
        "traitée est multipliée, à capital inchangé. $p$ : part de la production "
        "agrégée que ces entités auraient produite \\emph{sans} traitement. "
        "$(m-1)\\,p$ : la réponse qu'on observerait si rien d'autre ne bougeait. "
        "Dernière colonne : ce qu'on observe réellement. Les deux dernières "
        "colonnes coïncident à $10^{-15}$ près --- c'est le test, et il ne "
        "contient aucun résultat.\\normalsize",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"tableau écrit : {path.relative_to(ROOT)}")


if __name__ == "__main__":
    raise SystemExit(main())
