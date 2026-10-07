"""Annexe de traçabilité auto-générée (LaTeX) — règle mémoire « par hash ».

Produit report/annexe_tracabilite.tex : un tableau longtable listant, pour
chaque run de campagne cité par les rapports : run_id Simulation Lab, plan,
cellule, rôle, paramètres principaux (γ, A, λ, T), graine, statut,
condensat moteur, et l'usage (tables agrégées où il apparaît). Inclus par
\\input dans les rapports.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lib_lab

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "report" / "annexe_tracabilite.tex"

ROLES = {
    "benchmark": "calibrage de coût (volet 0)",
    "pilotes": "exploration grille $\\gamma$ (volet 1)",
    "taille_finie": "taille finie $\\lambda$ (volet 2)",
    "horizon_double": "robustesse horizon (volet 3)",
    "confirm": "confirmation graines 11-15 (volet 4)",
    "ablation_A": "contrôle d'échelle $A_{\\mathrm{norm}}$ (volet 5, exploration)",
    "ablation_A_confirm": "contrôle d'échelle $A_{\\mathrm{norm}}$, graines 11-15 (volet 5 étendu)",
    "mecanisme": "chaîne causale (volet 6)",
    "hypothese_K0": "hypothèse structurelle $K_0/K^*_{\\mathrm{aut}}$ (test ciblé)",
}


def main() -> None:
    lines = [
        "% Annexe générée par scripts/make_annexe.py — ne pas éditer à la main.",
        "\\section*{Annexe : traçabilité des simulations}",
        "Chaque run est un run Simulation Lab (dossier "
        "\\code{simulation\\_lab\\_data/runs/<run\\_id>}) ; la correspondance "
        "cellule $\\to$ runs est dans \\code{manifests/*.manifest.json}. "
        "Les fits par run sont dans \\code{results/metrics/<run\\_id>.json} "
        "et les agrégats dans \\code{results/tables/}.",
        "\\begin{small}",
        "\\begin{longtable}{llllrrrl}",
        "\\toprule",
        "run\\_id & plan & cellule & graine & $\\gamma$ & $\\lambda$ & $T$ & "
        "statut\\\\",
        "\\midrule",
        "\\endhead",
    ]
    n_runs = 0
    distinct_runs = set()
    engines = set()
    for plan in ROLES:
        if not lib_lab.manifest_path(plan).exists():
            continue
        manifest = lib_lab.load_manifest(plan)
        for entry in manifest["cells"]:
            engines.add(entry["engine_hash"])
            for seed, run_dir in lib_lab.run_dirs(entry):
                meta = json.loads((run_dir / "run.json").read_text())
                params = entry["parameters"]
                n_runs += 1
                distinct_runs.add(run_dir.name)
                lines.append(
                    f"\\code{{{run_dir.name.replace('_', '\\_')}}} & "
                    f"{plan.replace('_', '\\_')} & "
                    f"{entry['cell'].replace('_', '\\_')} & {seed} & "
                    f"{params['gamma']:.3f} & {params['lam']:g} & "
                    f"{params['T']} & {meta.get('status', '?')}\\\\"
                )
    lines += [
        "\\bottomrule",
        "\\end{longtable}",
        "\\end{small}",
        f"\\noindent Total : {n_runs} exécutions de cellule "
        f"({len(distinct_runs)} runs Simulation Lab distincts ; "
        f"{n_runs - len(distinct_runs)} partagés entre plans par "
        f"identifiant de cellule). Condensat(s) moteur : "
        f"{', '.join(sorted(engines))} "
        "(version \\code{m4\\_2-1}). Rôles des plans : "
        + " ; ".join(f"\\emph{{{plan.replace('_', chr(92)+'_')}}} = {role}"
                     for plan, role in ROLES.items()
                     if lib_lab.manifest_path(plan).exists())
        + ".",
    ]
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"annexe écrite : {OUTPUT} ({n_runs} exécutions, "
          f"{len(distinct_runs)} runs distincts)")


if __name__ == "__main__":
    main()
