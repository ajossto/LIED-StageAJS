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

# Où chaque groupe de runs apparaît, et pour quoi faire.
USAGE = {
    "burn": (
        "amorçage",
        "§3.2 (protocole), source des snapshots à $t_0$ de tous les bras",
        "amorçage partagé 0 → 2000",
    ),
    "control": ("campagne §4", "§4 (résultats), §3.3 (appariement)", "référence inerte"),
    "null": ("campagne §4", "§4, §3.3 (plancher de bruit)", "plancher de bruit, référence des bras fraction"),
    "frac_A150_phi20": ("campagne §4", "§4 (résultats), §3.4 (calibration)", "cellule principale, φ=0,2, A×1,5"),
    "frac_A125_phi20": ("campagne §4", "§4 (résultats)", "échelle d'amplitude, A×1,25"),
    "frac_A150_phi05": ("campagne §4", "§4 (résultats)", "échelle d'intensité, φ=0,05"),
    "frac_A150_phi50": ("campagne §4", "§4 (résultats), §3.4 (calibration)", "échelle d'intensité, φ=0,5"),
    "all_A150": ("campagne §4", "§4 (résultats), §5 (ablation), §6.5", "hausse globale, intensité 1"),
    "new_A150": ("campagne §4", "§4 (résultats), §5 (ablation), §6.5", "vintage technologique"),
    "frac_g060_phi20": ("campagne §4", "§4 (résultats), §3.4 (calibration)", "levier γ, exerce le régime (c) du noyau"),
    "abl_control": ("ablation K0", "§5", "contrôle apparié de l'ablation"),
    "abl_A150": ("ablation K0", "§5", "réplique de all_A150 avec âges au décès"),
    "abl_A150_K0aut": ("ablation K0", "§5", "A×1,5 + K0×2,25 (échelle autarcique)"),
    "abl_A150_K0obs": ("ablation K0", "§5", "A×1,5 + K0×1,45 (échelle observée)"),
    "abl_K0aut": ("ablation K0", "§5", "K0×2,25 seul"),
    "burn_scaling": ("loi d'échelle", "§7.2", "amorçage propre à chaque gamma"),
    "control_scaling": ("loi d'échelle", "§7.2", "contrôle apparié, par γ"),
    "A150_K0comp": ("loi d'échelle", "§7.2",
                    "A×1,5 + K0 compensé à l'échelle autarcique"),
    "sweep_control": ("balayage tension", "§6.4", "contrôle apparié du balayage"),
    "ref_cov": ("covariance", "§7.1", "référence A=1 du test de covariance"),
    "covariant_cov": ("covariance", "§7.1",
                      "A×1,5 et K0×c : la seule compensation exacte"),
    "naif_cov": ("covariance", "§7.1", "A×1,5, K0 inchangé"),
    "lineaire_cov": ("covariance", "§7.1",
                     "A×1,5 et K0×1,5 : mauvais exposant"),
    "ref_temps": ("recalage temporel", "§7.3",
                  "référence : λ=30, δ=0,01, σ=0,01, A=1, ρ=1, 2000 pas"),
    "litteral_temps": ("recalage temporel", "§7.3",
                       "énoncé brut : λ×2, δ→2δ−δ², σ→√2σ, 1000 pas"),
    "sans_marche_temps": ("recalage temporel", "§7.3",
                          "énoncé brut + A×2, ρ inchangé — isole le rôle de ρ"),
    "complet_temps": ("recalage temporel", "§7.3",
                      "recalage complet : + A×2 et ρ×2"),
    "complet_s4_temps": ("recalage temporel", "§7.3",
                         "recalage complet à s=4 : sépare le terme en δ du "
                         "terme de marché"),
    "control_tensA": ("tension contre A", "§6.5",
                      "contrôle apparié du balayage en A, par γ"),
    "ref_dfin_temps": ("recalage temporel", "§7.3",
                       "référence à δ = 0,002 : discriminant des deux sources "
                       "du résidu"),
    "complet_dfin_temps": ("recalage temporel", "§7.3",
                           "recalage complet à δ = 0,002 — écarte la "
                           "discrétisation, désigne le marché"),
}

#: Bras du balayage : leur rôle se lit sur le levier employé.
SWEEP_LEVERS = {
    "K0": ("balayage tension", "§6.4", "levier K0 seul, niveau de tension"),
    "delta": ("balayage tension", "§6.4", "levier δ seul, niveau de tension"),
    "A": ("balayage tension", "§6.4", "levier A seul, niveau de tension"),
}

# Runs d'AUTRES lignées cités par les rapports.
EXTERNAL = [
    {
        "run_id": "m4_3__d1__baseline__seed0",
        "groupe": "référence M4.3",
        "usage": "conception §5.2 (parité bit à bit) ; §4 (reprise)",
        "role": "run M4.3 stocké servant de référence de parité et de divergence",
        "seed": "0",
        "statut": "completed",
    },
    {
        "run_id": "m4_3__d1__baseline__seed1",
        "groupe": "référence M4.3",
        "usage": "rapport §3.1 (justification de $t_0$)",
        "role": "t_converge_int_in = 948, lu dans son analysis.json",
        "seed": "1",
        "statut": "completed",
    },
    {
        "run_id": "m4_3__d1__baseline__seed2",
        "groupe": "référence M4.3",
        "usage": "rapport §3.1 (justification de $t_0$)",
        "role": "t_converge_int_in = 841, lu dans son analysis.json",
        "seed": "2",
        "statut": "completed",
    },
    {
        "run_id": "m4_3__d1__rho_2__seed0",
        "groupe": "référence M4.3",
        "usage": "conception §6 (falsification du rapport de divergence)",
        "role": "série volontairement discordante, pour vérifier que l'écart est détecté",
        "seed": "0",
        "statut": "completed",
    },
]

KEYS = ("gamma", "A", "lam", "delta", "sigma", "K0", "rate_rule", "kernel_policy")


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
    parts = run_id.split("__")
    if parts[1] == "burn":
        return "burn"
    if parts[1] == "scaling":
        # m4_3live_v2__scaling__<gamma>__<cellule>__<graine>
        return "burn_scaling" if parts[3] == "burn" else f"{parts[3]}_scaling" \
            if parts[3] == "control" else parts[3]
    if parts[1] == "covariance":
        # m4_3live_v2__covariance__<gamma>__<variante>__<graine>
        return f"{parts[3]}_cov"
    if parts[1] == "tensionA":
        # m4_3live_v2__tensionA__<gamma>__<bras>__<graine>
        return f"{parts[3]}_tensA"
    if parts[1] == "temps":
        # m4_3live_v2__temps__<variante>__<graine> — le suffixe évite la collision
        # avec les cellules `ref` / `control` des autres familles.
        return f"{parts[2]}_temps"
    return parts[2]


def usage_of(cell: str) -> tuple[str, str, str]:
    """Les bras du balayage sont paramétrés (`K0_400`, `delta_0.02`…) : leur
    rôle se déduit du levier, pas d'une table exhaustive."""
    if cell in USAGE:
        return USAGE[cell]
    if cell.endswith("_tensA"):
        # A_0.75_tensA, A_2_tensA… : la valeur imposée de A est dans le nom.
        value = cell[len("A_"):-len("_tensA")]
        return ("tension contre A", "§6.5",
                f"A = {value.replace('.', ',')} à K0 fixé, exposant dlnT/dlnA")
    lever = cell.split("_")[0]
    if lever in SWEEP_LEVERS:
        group, usage, role = SWEEP_LEVERS[lever]
        return group, usage, f"{role} ({cell.replace('_', ' = ')})"
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
        r"lignée \code{m4\_3live\_credit\_soc}), avec leur \code{series.csv}, "
        r"leur \code{tech\_series.csv}, leur journal d'interventions et une figure "
        r"\code{figures/macro\_overview.png}. Le tableau complet, avec les paramètres "
        r"et le statut de chaque run, est dans "
        r"\code{results/analysis/traceability.csv}.",
    ]
    (TABLES / "traceability.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(rows)} runs dans l'annexe de traçabilité")
    print(f"  {OUT / 'traceability.csv'}")
    print(f"  {TABLES / 'traceability.tex'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
