"""Génère l'annexe LaTeX de traçabilité d'un rapport.

Usage :
    make_annexe.py <sortie.tex> <plan> [<plan> ...]

Produit une longtable : run_id, rôle (plan/phase), paramètres, graine,
horizon, statut du modèle, usage (figures/tables où le run apparaît).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_runs as L

USAGE = {
    "benchmark": "benchmark de coût (protocole §9) ; contrôles de neutralité",
    "pilotes": "audit des plages (§3), contrôles temporels (§4), fig. pilotes",
    "pilotes2": "sondes de frontière (§6.1)",
    "oat": "courbes OAT (§5, fig. oat\\_*)",
    "lambda_ext": "carte d'extinction (§6.2)",
    "lhs": "screening global (§7, fig. lhs\\_*)",
    "cut_sigma_k": "coupe 2D $\\sigma\\times k$",
    "cut_sigma_delta": "coupe 2D $\\sigma\\times\\delta$",
    "confirm": "phase confirmatoire",
    "popmax": "diagnostic du garde-fou",
}


def main() -> None:
    output = Path(sys.argv[1])
    plans = sys.argv[2:]
    lines = [
        "% Annexe générée par scripts/make_annexe.py — ne pas éditer à la main.",
        "{\\scriptsize\\setlength{\\tabcolsep}{3.5pt}",
        "\\begin{longtable}{@{}llrrrrrrrl@{}}",
        "\\toprule",
        "run\\_id & plan & $\\lambda$ & $\\delta$ & $\\sigma$ & $K_0$ & $k$ & graine & $T$ & statut \\\\",
        "\\midrule",
        "\\endhead",
    ]
    n = 0
    for plan in plans:
        if plan == "confirm":
            manifest = json.loads(
                (L.CAMPAIGN_ROOT / "manifests" / "confirm_lab.json").read_text())
            for entry in manifest["cells"]:
                p = entry["parameters"]
                for offset, run_id in enumerate(entry["run_ids"]):
                    lab_dir = Path("/home/anatole/jupyter/simulation_lab_data/runs") / run_id
                    status = "?"
                    summary_file = lab_dir / "summary.json"
                    if summary_file.exists():
                        status = json.loads(summary_file.read_text())["status"]
                    if status == "explosion":
                        status = "censure"
                    lines.append(
                        f"\\code{{{run_id.replace('_', '\\_')}}} & "
                        f"conf.~{entry['cell'].replace('_', '\\_')} & "
                        f"{p['lam']:g} & {p['delta']:g} & {p['sigma']:g} & "
                        f"{p['K0']:g} & {p['k']} & {entry['base_seed'] + offset} & "
                        f"{p['T']} & {status} \\\\"
                    )
                    n += 1
            continue
        for spec in L.load_plan(plan):
            manifest_file = L.manifest_path(spec)
            if not manifest_file.exists():
                continue
            manifest = json.loads(manifest_file.read_text())
            p = manifest["parameters"]
            status = manifest["model_status"]
            if status == "explosion":
                status = "censure"
            lines.append(
                f"\\code{{{manifest['run_id'].replace('_', '\\_')}}} & {plan.replace('_', '\\_')} & "
                f"{p['lam']:g} & {p['delta']:g} & {p['sigma']:g} & {p['K0']:g} & "
                f"{p['k']} & {p['seed']} & {p['T']} & {status} \\\\"
            )
            n += 1
    lines += [
        "\\bottomrule",
        "\\end{longtable}",
        "}",
        "",
        "\\noindent Usages par plan : " + " ; ".join(
            f"\\textbf{{{plan.replace('_', '\\_')}}} : {USAGE.get(plan, plan)}"
            for plan in plans) + ".",
        "",
        "\\noindent Chaque run est reproductible depuis son manifeste "
        "(\\path{results/runs/<run_id>/manifest.json}) : moteur "
        "\\code{m4b-mini-3} (condensat \\code{" + L.ENGINE_HASH + "}), "
        "paramètres complets, graine, options d'écriture. Les données "
        "primaires et les métriques dérivées "
        "(\\path{results/metrics/<run_id>.json}) sont conservées.",
    ]
    output.write_text("\n".join(lines))
    print(f"{output} : {n} runs")


if __name__ == "__main__":
    main()
