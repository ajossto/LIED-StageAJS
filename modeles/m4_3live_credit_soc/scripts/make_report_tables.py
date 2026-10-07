"""Fabrique les fragments LaTeX insérés dans les deux rapports.

Aucun chiffre n'est recopié à la main dans les `.tex` : tout ce qui vient
d'une mesure passe par ici, depuis les JSON produits par `bench_kernel.py`,
`analyse.py` et `nonregression.sh`.

    python3 scripts/make_report_tables.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ANALYSIS = ROOT / "results" / "analysis"
TABLES = ROOT / "report" / "tables"

PATH_LABELS = {
    "identite": "(a) même technologie",
    "gamma_egaux": "(b) $\\gamma$ égaux, forme fermée",
    "newton_exact": "(c) Newton exact (froid)",
    "tiede_newton_1": "(c) tiède, une étape de Newton",
    "lut_hermite_33": "(c) table Hermite, 33 nœuds",
    "lut_hermite_65": "(c) table Hermite, 65 nœuds",
}


def french(value: float, digits: int = 2) -> str:
    text = f"{value:,.{digits}f}".replace(",", "\\,").replace(".", ",")
    return text


def scientific(value: float) -> str:
    if value == 0:
        return "0"
    exponent = int(math.floor(math.log10(abs(value))))
    mantissa = value / 10**exponent
    return f"${mantissa:.2f}".replace(".", ",") + f"\\cdot10^{{{exponent}}}$"


def write(name: str, content: str) -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    (TABLES / name).write_text(content, encoding="utf-8")


def bench_tables() -> None:
    source = ANALYSIS / "bench_kernel.json"
    if not source.exists():
        write("bench_kernel.tex", "\\emph{(banc non exécuté)}\n")
        write("bench_threshold.tex", "n.d.")
        write("bench_share.tex", "n.d.")
        return
    data = json.loads(source.read_text(encoding="utf-8"))
    lines = [
        "\\begin{center}",
        "\\begin{tabular}{@{}lrl@{}}",
        "\\toprule",
        "\\textbf{Chemin} & \\textbf{Mreq/s} & \\textbf{Erreur max sur $\\delta$} \\\\",
        "\\midrule",
    ]
    for key, label in PATH_LABELS.items():
        entry = data["chemins"].get(key)
        if entry is None:
            continue
        error = entry.get("erreur_max_capital")
        if error is None:
            error_text = entry.get("erreur", "---")
            error_text = {"exacte": "exacte", "référence": "référence"}.get(error_text, error_text)
        else:
            error_text = scientific(error) + " unité de capital"
        lines.append(f"{label} & {french(entry['mreq_s'], 2)} & {error_text} \\\\")
    lines += [
        "\\midrule",
        "\\multicolumn{3}{@{}l@{}}{\\footnotesize "
        f"{data['machine']['appels']:,}".replace(",", "\\,")
        + " appels, meilleur de "
        + str(data["machine"]["repetitions"])
        + " répétitions ; compilation d'une ligne de table : "
        + french(data["construction"]["seconds_par_ligne"] * 1000, 2)
        + "\\,ms} \\\\",
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{center}",
    ]
    write("bench_kernel.tex", "\n".join(lines) + "\n")
    write("bench_threshold.tex", french(data["seuil_amortissement_mesure"], 0))
    share = data.get("part_du_pas", {}).get("fraction_du_pas_estimee")
    write(
        "bench_share.tex",
        "n.d." if share is None else french(100.0 * share, 1) + "\\,\\%",
    )


def nonregression_table() -> None:
    source = ANALYSIS / "nonregression.txt"
    if not source.exists():
        write("nonregression.tex", "\\emph{(vérification non exécutée)}\n")
        return
    body = source.read_text(encoding="utf-8").strip()
    write(
        "nonregression.tex",
        "\\begin{quote}\\footnotesize\\begin{verbatim}\n" + body + "\n\\end{verbatim}\\end{quote}\n",
    )


def campaign_tables() -> None:
    source = ANALYSIS / "metrics.json"
    if not source.exists():
        for name in ("campaign_windows.tex", "campaign_impact.tex", "campaign_global.tex"):
            write(name, "\\emph{(campagne non analysée)}\n")
        return
    data = json.loads(source.read_text(encoding="utf-8"))
    arms = data["arms"]

    # -- table 1 : validation de l'appariement à l'horizon 1 ---------------
    lines = [
        "\\begin{center}",
        "\\begin{tabular}{@{}lrrrr@{}}",
        "\\toprule",
        "\\textbf{Bras} & \\textbf{écart relatif} & \\textbf{part ex ante} "
        "& \\textbf{amplitude mesurée} & \\textbf{amplitude imposée} \\\\",
        "\\midrule",
    ]
    for arm, entry in arms.items():
        impact = entry["impact_h1"]
        measured = entry.get("amplitude_measured_h1")
        measured_text = "---" if measured is None or math.isnan(measured) else french(measured, 4)
        imposed = (
            "\\emph{aucune}" if entry["amplitude_source"] != "imposée"
            else french(entry["amplitude"], 2)
        )
        lines.append(
            f"\\code{{{arm.replace('_', chr(92) + '_')}}} & "
            f"{french(100 * impact['relative'], 3)}\\,\\% & "
            f"{french(impact['share_prod_treated_ante'], 4)} & "
            f"{measured_text} & {imposed} \\\\"
        )
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{center}"]
    write("campaign_impact.tex", "\n".join(lines) + "\n")

    # -- table 2 : fenêtres ------------------------------------------------
    lines = [
        "\\begin{center}\\footnotesize",
        "\\begin{tabular}{@{}llrrrr@{}}",
        "\\toprule",
        "\\textbf{Bras} & \\textbf{fenêtre} & \\textbf{$\\Delta$prod (\\%)} & "
        "\\textbf{part ex ante} & \\textbf{élasticité} & \\textbf{part bloquée} \\\\",
        "\\midrule",
    ]
    for arm, entry in arms.items():
        for index, (name, window) in enumerate(entry["windows"].items()):
            elasticity = window.get("elasticity")
            elasticity_text = "---" if elasticity is None else french(elasticity, 2)
            label = f"\\code{{{arm.replace('_', chr(92) + '_')}}}" if index == 0 else ""
            lines.append(
                f"{label} & {name} & "
                f"{french(100 * window['relative'], 2)} $\\pm$ "
                f"{french(100 * window['relative_sem'], 2)} & "
                f"{french(window.get('share_prod_treated_ante', 0.0), 3)} & "
                f"{elasticity_text} & "
                f"{french(100 * window['blocked_dir_share'], 1)}\\,\\% \\\\"
            )
        lines.append("\\addlinespace")
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{center}"]
    write("campaign_windows.tex", "\n".join(lines) + "\n")

    # -- table 3 : élasticité globale -------------------------------------
    lines = [
        "\\begin{center}",
        "\\begin{tabular}{@{}lrr@{}}",
        "\\toprule",
        "\\textbf{Bras} & $\\varepsilon_{\\mathrm{prod},A}$ & $\\varepsilon_{K,A}$ \\\\",
        "\\midrule",
    ]
    for arm in ("all_A150", "new_A150"):
        entry = arms.get(arm, {})
        if "log_elasticity_prod_A" not in entry:
            continue
        lines.append(
            f"\\code{{{arm.replace('_', chr(92) + '_')}}} & "
            f"{french(entry['log_elasticity_prod_A'], 3)} & "
            f"{french(entry['log_elasticity_K_A'], 3)} \\\\"
        )
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{center}"]
    write("campaign_global.tex", "\n".join(lines) + "\n")

    noise = data.get("noise_floor", {})
    write(
        "noise_floor.tex",
        "médiane "
        + (french(100 * noise.get("median", float("nan")), 2) if noise else "n.d.")
        + "\\,\\%, maximum "
        + (french(100 * noise.get("max", float("nan")), 2) if noise else "n.d.")
        + "\\,\\%",
    )


def ablation_table() -> None:
    source = ANALYSIS / "ablation_k0.json"
    if not source.exists():
        write("ablation_k0.tex", "\\emph{(ablation non exécutée)}\n")
        return
    data = json.loads(source.read_text(encoding="utf-8"))
    lines = [
        "\\begin{center}\\footnotesize",
        "\\begin{tabular}{@{}lrrrrrr@{}}",
        "\\toprule",
        "\\textbf{Bras} & \\textbf{population} & \\textbf{production} & "
        "$K_0/(K/\\text{ent.})$ & \\textbf{durée de vie} & "
        "\\textbf{morts $\\le$ 10 pas} & $\\varepsilon_{\\mathrm{prod},A}$ \\\\",
        "\\midrule",
    ]
    for arm, entry in data["arms"].items():
        ratio = entry["prod_tot_ratio"]
        epsilon = (
            french(math.log(ratio) / math.log(1.5), 3)
            if "A150" in arm and ratio > 0 else "---"
        )
        lines.append(
            f"{entry['label']} & "
            f"$\\times${french(entry['pop_ratio'], 3)} $\\pm$ {french(entry['pop_ratio_sem'], 3)} & "
            f"$\\times${french(entry['prod_tot_ratio'], 3)} $\\pm$ {french(entry['prod_tot_ratio_sem'], 3)} & "
            f"{french(entry['K0_over_K_per_entity'], 4)} & "
            f"{french(entry['mean_lifetime'], 1)} & "
            f"{french(entry['share_deaths_age_le_10'], 3)} & {epsilon} \\\\"
        )
    lines += [
        "\\midrule",
        "\\multicolumn{7}{@{}l@{}}{\\footnotesize Rapports au bras "
        "\\code{abl\\_control}, fenêtre $h \\in [1001, 2000]$, "
        f"{len(data['seeds'])} graines. $K_0$ : {french(data['K0']['base'], 2)} "
        f"(base), {french(data['K0']['autarcique'], 2)} (autarcique), "
        f"{french(data['K0']['observe'], 2)} (observée).}} \\\\",
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{center}",
    ]
    write("ablation_k0.tex", "\n".join(lines) + "\n")


def main() -> int:
    bench_tables()
    ablation_table()
    nonregression_table()
    campaign_tables()
    print("fragments écrits dans", TABLES)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
