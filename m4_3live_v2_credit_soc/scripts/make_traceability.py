"""Annexe de traçabilité : chaque simulation citée dans un rapport, par son
identifiant `simulation_lab`.

Règle permanente du dépôt (consignes de rédaction) : « toute simulation
mentionnée dans un rapport doit être identifiable par son hash `run_id` », et
le rapport doit se terminer par un tableau donnant, pour chacune : le
`run_id`, l'endroit où elle apparaît, son rôle, ses paramètres principaux, sa
graine, son statut, et son chemin dans `simulation_lab`.

Produit `results/analysis/traceability.csv` (source de vérité, une ligne par
run) et `report/tables/traceability.tex` (l'annexe insérée dans les deux
rapports).

    python3 scripts/make_traceability.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JUPYTER_ROOT = ROOT.parent
sys.path.insert(0, str(JUPYTER_ROOT))

from simulation_lab.settings import RUNS_DIR  # noqa: E402

OUT = ROOT / "results" / "analysis"
TABLES = ROOT / "report" / "tables"

# Où chaque groupe de runs apparaît, et pour quoi faire. Les renvois sont des
# SECTIONS, jamais des numéros de figure : les numéros de figure bougent dès
# qu'une section est insérée, et v1 s'y est fait piéger.
USAGE = {
    "burn": (
        "amorçage",
        "protocole ; source des snapshots à $t_0 = 2000$ de tous les bras",
        "amorçage partagé 0 → 2000, homogène, commun aux deux règles de sens",
    ),
    "free/control": ("lot D", "campagne A/B ; contrôle de stationnarité",
                     "référence inerte sous sens libre"),
    "free/all_A150": ("lot D", "campagne A/B",
                      "hausse globale $A\\times1{,}5$ : reste homogène, donc "
                      "insensible à la règle de sens"),
    "free/new_A150": ("lot D", "campagne A/B ; régime nouveau",
                      "vintage $A\\times1{,}5$, sens libre"),
    "free/new_A075": ("lot D", "campagne A/B",
                      "vintage $A\\times0{,}75$, sens libre"),
    "free/new_g060": ("lot D", "campagne A/B",
                      "vintage $\\gamma : 0{,}5 \\to 0{,}6$, sens libre ; "
                      "exerce le régime (c) du noyau"),
    "richest_lends/new_A150": ("lot D", "campagne A/B",
                               "même bras sous la règle v1 « la plus riche prête »"),
    "richest_lends/new_A075": ("lot D", "campagne A/B",
                               "même bras sous la règle v1"),
    "richest_lends/new_g060": ("lot D", "campagne A/B",
                               "même bras sous la règle v1"),
    "deprec_first": ("lot E", "ordre des phases",
                     "dépréciation avant service des intérêts, apparié au contrôle"),
}

#: Cellules du balayage de rotation : leur rôle se lit sur le levier employé.
ROTATION_LEVERS = {
    "base": "régime de référence, avec le Gini du capital instrumenté",
    "lam": "levier $\\lambda$ (taux de naissance) seul",
    "rho": "levier $\\rho$ (taux d'appariement) seul",
    "sigma": "levier $\\sigma$ (choc multiplicatif) seul",
    "K0": "levier $K_0$ (capital de naissance) seul",
    "delta": "levier $\\delta$ (dépréciation) seul",
}

# Runs d'AUTRES lignées cités par les rapports.
EXTERNAL = [
    {
        "run_id": "m4_3__d1__baseline__seed0",
        "groupe": "référence M4.3",
        "usage": "conception (parité bit à bit sur 8000 pas) ; lots A et B",
        "role": "run M4.3 stocké servant de référence de parité",
        "seed": "0",
        "statut": "completed",
    },
    {
        "run_id": "m4_3__d1__baseline__seed1",
        "groupe": "référence M4.3",
        "usage": "protocole (justification de $t_0$)",
        "role": "t_converge_int_in = 948, lu dans son analysis.json",
        "seed": "1",
        "statut": "completed",
    },
    {
        "run_id": "m4_3__d1__baseline__seed2",
        "groupe": "référence M4.3",
        "usage": "protocole (justification de $t_0$)",
        "role": "t_converge_int_in = 841, lu dans son analysis.json",
        "seed": "2",
        "statut": "completed",
    },
]

KEYS = ("gamma", "A", "lam", "delta", "sigma", "K0", "rho", "loan_direction",
        "phase_order", "rate_rule", "kernel_policy")


def short_parameters(parameters: dict) -> str:
    if not parameters:
        return "—"
    bits = []
    for key in KEYS:
        if key not in parameters:
            continue
        value = parameters[key]
        if isinstance(value, float):
            value = f"{value:g}"
        bits.append(f"{key}={value}")
    return ", ".join(bits)


def cell_of(run_id: str) -> str:
    """Cellule d'un run, lue sur son identifiant.

    Quatre familles : `burn__seedN`, `arm__<règle>__<bras>__seedN`,
    `phase__<ordre>__seedN`, `rotation__<cellule>__seedN`.
    """
    parts = run_id.split("__")
    family = parts[1]
    if family == "burn":
        return "burn"
    if family == "arm":
        return f"{parts[2]}/{parts[3]}"
    return parts[2]


def usage_of(cell: str) -> tuple[str, str, str]:
    if cell in USAGE:
        return USAGE[cell]
    lever = cell.split("_")[0]
    if lever in ROTATION_LEVERS:
        value = cell[len(lever) + 1:].replace(".", ",")
        detail = ROTATION_LEVERS[lever]
        if value:
            detail += f" ($= {value}$)"
        return "lot F", "rotation du crédit (décomposition et fermeture)", detail
    return "—", "—", "—"


def collect() -> list[dict]:
    rows = []
    for meta_path in sorted(RUNS_DIR.glob("m4_3live_v2__*/run.json")):
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
        run_id = payload["run_id"]
        cell = cell_of(run_id)
        group, usage, role = usage_of(cell)
        summary = payload.get("summary", {})
        rows.append(
            {
                "run_id": run_id,
                "groupe": group,
                "usage": usage,
                "role": role,
                "parametres": short_parameters(payload.get("parameters", {})),
                "seed": str(payload.get("seed", "")),
                "statut": summary.get("status", payload.get("status", "")),
                "t_final": str(summary.get("t_final", summary.get("t", ""))),
                "interventions": "; ".join(
                    f"t={i['t']} {i['param']}→{i['value']:g} ({i['scope']}"
                    + (f", φ={i['phi']:g}" if i.get("phi") else "")
                    + ")"
                    for i in summary.get("interventions", [])
                )
                or "aucune",
                "chemin_simulation_lab": f"simulation_lab_data/runs/{run_id}",
            }
        )
    for entry in EXTERNAL:
        rows.append(
            {
                **entry,
                "parametres": "baseline M4.3 : gamma=0.5, A=1, lam=30, delta=0.01, sigma=0.01, K0=25",
                "t_final": "8000",
                "interventions": "aucune",
                "chemin_simulation_lab": f"simulation_lab_data/runs/{entry['run_id']}",
            }
        )
    return rows


def escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("_", r"\_")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("→", r"$\rightarrow$")
        .replace("φ", r"$\varphi$")
        .replace("×", r"$\times$")
        .replace("ε", r"$\varepsilon$")
        .replace("γ", r"$\gamma$")
        .replace("≤", r"$\le$")
        .replace("≥", r"$\ge$")
    )


def main() -> int:
    rows = collect()
    OUT.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    fields = ["run_id", "groupe", "usage", "role", "parametres", "seed", "statut",
              "t_final", "interventions", "chemin_simulation_lab"]
    with open(OUT / "traceability.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        r"{\scriptsize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\begin{longtable}{@{}>{\raggedright\arraybackslash}p{5.3cm}"
        r">{\raggedright\arraybackslash}p{1.9cm}"
        r">{\raggedright\arraybackslash}p{3.2cm}"
        r">{\raggedright\arraybackslash}p{4.9cm}@{}}",
        r"\toprule",
        r"\textbf{run\_id (simulation\_lab)} & \textbf{groupe} & \textbf{apparaît dans} "
        r"& \textbf{rôle / interventions} \\",
        r"\midrule",
        r"\endfirsthead",
        r"\toprule",
        r"\textbf{run\_id (simulation\_lab)} & \textbf{groupe} & \textbf{apparaît dans} "
        r"& \textbf{rôle / interventions} \\",
        r"\midrule",
        r"\endhead",
    ]
    current = None
    for row in rows:
        if row["groupe"] != current:
            if current is not None:
                lines.append(r"\addlinespace")
            current = row["groupe"]
        interventions = row["interventions"]
        detail = escape(row["role"])
        if interventions != "aucune":
            detail += r" \\ \textit{" + escape(interventions) + "}"
        # Les identifiants sont longs : on autorise la coupure après chaque
        # séparateur, sinon la colonne déborde sur la suivante.
        run_id = escape(row["run_id"]).replace("\\_\\_", "\\_\\_\\allowbreak{}")
        lines.append(
            f"\\code{{{run_id}}} & {escape(row['groupe'])} & "
            f"{row['usage']} & {detail} \\\\"
        )
    lines += [
        r"\bottomrule",
        r"\end{longtable}",
        r"}",
        r"",
        r"\noindent Tous ces runs sont ouvrables dans \code{simulation\_lab} "
        r"(\code{python3 -m simulation\_lab.cli gui}, page « Résultats », "
        r"lignée \code{m4\_3live\_v2\_credit\_soc}), avec leur \code{series.csv}, "
        r"leur \code{tech\_series.csv}, leurs \code{tension.csv} et "
        r"\code{tension\_agg.csv}, leur journal d'interventions et une figure "
        r"\code{figures/macro\_overview.png}. Le tableau complet, avec les paramètres "
        r"et le statut de chaque run, est dans "
        r"\code{results/analysis/traceability.csv}.",
    ]
    (TABLES / "traceability.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    orphans = [row["run_id"] for row in rows if row["role"] == "—"]
    if orphans:
        raise SystemExit(
            "annexe de traçabilité incomplète : "
            f"{len(orphans)} run(s) sans rôle, dont {orphans[:3]}"
        )
    print(f"{len(rows)} runs dans l'annexe de traçabilité, 0 sans rôle")
    print(f"  {OUT / 'traceability.csv'}")
    print(f"  {TABLES / 'traceability.tex'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
