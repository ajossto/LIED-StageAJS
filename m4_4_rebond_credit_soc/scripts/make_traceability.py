"""Annexe de traçabilité — un run, une ligne, un rôle (plan §10).

La règle, et c'est elle qui donne son sens à l'annexe : **le script REFUSE de
produire une annexe dont une ligne serait sans rôle**. Un run qui a tourné,
qui occupe du disque, et dont personne ne sait à quelle question il répond,
est un run qui n'aurait pas dû tourner ; le signaler est plus utile que de
l'inscrire dans un tableau.

Chaque run est identifié par son chemin, et son rôle est déduit de la famille
de campagne à laquelle il appartient. Les rôles sont écrits ici, en un seul
endroit, et la table est vérifiée exhaustive à chaque exécution.

Sorties : `results/analysis/traceability.csv` (une ligne par run) et
`report/traceability.tex` (le tableau des familles, à inclure).

    python3 scripts/make_traceability.py
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAMPAIGN = ROOT / "results" / "campaign"

#: famille de campagne -> (lot, rôle scientifique). Toute famille présente sur
#: le disque doit figurer ici, sans quoi le script échoue.
ROLES = {
    "burn": ("A/B", "amorçage partagé à t_0 = 2000, une trajectoire par graine ; "
                    "aucun bras n'existe sans lui"),
    "arms": ("B, C, D", "bras du rebond : contrôle, leviers de productivité et "
                        "d'exposant, bras compensé en dotation de naissance"),
    "coverage": ("C", "couverture de queue : même protocole à taux de naissance "
                      "porté de 30 à 50, pour mesurer si l'exposant en dépend"),
    "bargain": ("T", "le taux comme partage : balayage de p de l'altruisme à "
                     "l'asservissement, plus les rampes montante et descendante"),
    "control_rho": ("E", "tentative de contrôle : balayage du levier de marché ρ "
                         "sur une étendue de ×6"),
    "ablation": ("F", "ablation vers le régime de la lignée M4B, un facteur à la "
                      "fois, sur une fenêtre doublée"),
    "phase": ("—", "ordre des phases, hérité de la lignée précédente ; non "
                   "exploité par ce programme"),
}


def find_runs(root: Path):
    """Tout répertoire contenant une série est un run."""
    for path in sorted(root.rglob("series.csv")):
        yield path.parent


def describe(run_dir: Path) -> dict:
    relative = run_dir.relative_to(CAMPAIGN)
    family = relative.parts[0]
    summary_path = run_dir / "summary.json"
    burn_path = run_dir / "burn.json"
    payload = {}
    if summary_path.exists():
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
    elif burn_path.exists():
        payload = json.loads(burn_path.read_text(encoding="utf-8"))
    parameters = payload.get("parameters", {})
    files = {p.name for p in run_dir.iterdir() if p.is_file()}
    return {
        "famille": family,
        "chemin": str(relative),
        "bras": payload.get("arm", relative.parts[1] if len(relative.parts) > 2 else ""),
        "graine": payload.get("seed", ""),
        "t_final": payload.get("t_final", payload.get("t", "")),
        "statut": payload.get("status", ""),
        "secondes": round(float(payload.get("wall_seconds", 0.0)), 1),
        "lam": parameters.get("lam", ""),
        "sigma": parameters.get("sigma", ""),
        "delta": parameters.get("delta", ""),
        "rho": parameters.get("rho", ""),
        "rate_rule": parameters.get("rate_rule", ""),
        "bargain_p": parameters.get("bargain_p", ""),
        "panneaux": int("panels.npz" in files),
        "aretes": int("loss_edges.npz" in files),
        "avalanches": int("avalanches.csv" in files),
        "checkpoint": int(any(name.startswith("snapshot_t") for name in files)),
        "interventions": len(payload.get("interventions", [])),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "analysis")
    parser.add_argument("--tex", type=Path, default=ROOT / "report" / "traceability.tex")
    args = parser.parse_args(argv[1:])

    if not CAMPAIGN.exists():
        print(f"aucune campagne sous {CAMPAIGN}", file=sys.stderr)
        return 1
    rows = [describe(run_dir) for run_dir in find_runs(CAMPAIGN)]
    if not rows:
        print("aucun run trouvé", file=sys.stderr)
        return 1

    families = sorted({row["famille"] for row in rows})
    orphans = [family for family in families if family not in ROLES]
    if orphans:
        print("REFUS : familles de runs sans rôle déclaré : "
              + ", ".join(orphans), file=sys.stderr)
        print("Ajouter leur rôle dans ROLES, ou les retirer du disque.",
              file=sys.stderr)
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    with open(args.out / "traceability.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "% Engendré par scripts/make_traceability.py — NE PAS ÉDITER À LA MAIN.",
        "\\begin{longtable}{@{}p{0.13\\textwidth}p{0.07\\textwidth}rr"
        "p{0.50\\textwidth}@{}}",
        "\\toprule",
        "\\textbf{famille} & \\textbf{lot} & \\textbf{runs} & \\textbf{heures} & "
        "\\textbf{rôle} \\\\",
        "\\midrule",
        "\\endhead",
    ]
    total_runs = 0
    total_hours = 0.0
    for family in families:
        selected = [row for row in rows if row["famille"] == family]
        hours = sum(row["secondes"] for row in selected) / 3600.0
        lot, role = ROLES[family]
        total_runs += len(selected)
        total_hours += hours
        safe = family.replace("_", "\\_")
        lines.append(f"\\code{{{safe}}} & {lot} & {len(selected)} & "
                     f"{hours:.1f} & {role} \\\\")
    lines += [
        "\\midrule",
        f"\\textbf{{total}} & & \\textbf{{{total_runs}}} & "
        f"\\textbf{{{total_hours:.1f}}} & \\\\",
        "\\bottomrule",
        "\\end{longtable}",
    ]
    args.tex.parent.mkdir(parents=True, exist_ok=True)
    args.tex.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"{total_runs} runs, {len(families)} familles, "
          f"{total_hours:.1f} heures de calcul cumulées")
    for family in families:
        selected = [row for row in rows if row["famille"] == family]
        instrumented = sum(row["panneaux"] for row in selected)
        checkpoints = sum(row["checkpoint"] for row in selected)
        print(f"  {family:<14} {len(selected):>4} runs, "
              f"{instrumented:>4} avec panneaux, {checkpoints:>4} avec checkpoint, "
              f"{sum(r['secondes'] for r in selected) / 3600:.1f} h")
    bad = [row for row in rows if row["statut"] not in ("ok", "")]
    if bad:
        print(f"ATTENTION : {len(bad)} runs de statut anormal : "
              + ", ".join(sorted({row['statut'] for row in bad})), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
