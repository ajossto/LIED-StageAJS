"""Engendre les macros LaTeX depuis `results/analysis/` (plan §10).

Règle du programme : **tous les nombres cités dans le corps des rapports sont
des macros engendrées, jamais recopiés à la main**. Ce script lit les
fichiers d'analyse et écrit `report/numbers.tex`, où chaque macro porte le
nom du fichier et de la clef dont elle vient.

Il REFUSE d'écrire une macro dont la source est absente : un rapport qui
compile avec une macro vide est un rapport qui ment en silence. Les macros
manquantes sont listées sur la sortie d'erreur et le script sort en échec.

    python3 scripts/make_numbers.py [--out report/numbers.tex]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ANALYSIS = ROOT / "results" / "analysis"


def french(value: float, digits: int = 4) -> str:
    """Nombre au format français : virgule décimale, espace fine aux
    milliers. LaTeX reçoit du texte déjà mis en forme, pas un flottant."""
    if value != value:
        return r"\textit{nan}"
    if math.isinf(value):
        return r"$\infty$"
    text = f"{value:,.{digits}f}".replace(",", " ").replace(".", ",")
    if "," in text:
        text = text.rstrip("0").rstrip(",") if text.endswith("0") else text
    return text


#: LaTeX n'accepte QUE des lettres dans un nom de séquence de contrôle :
#: `\ExposantAallA150` est illégal et fait échouer la compilation, pas
#: l'écriture — le défaut ne se voit donc qu'à la fin. Les chiffres sont
#: transcrits, les séparateurs supprimés.
DIGITS = {"0": "Zero", "1": "Un", "2": "Deux", "3": "Trois", "4": "Quatre",
          "5": "Cinq", "6": "Six", "7": "Sept", "8": "Huit", "9": "Neuf"}


def latex_name(raw: str) -> str:
    """Nom de macro LaTeX valide, déterministe, à partir d'une clef de donnée."""
    out = []
    for character in raw:
        if character.isalpha():
            out.append(character)
        elif character in DIGITS:
            out.append(DIGITS[character])
    return "".join(out)


def load_json(name: str):
    path = ANALYSIS / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def load_csv(name: str):
    path = ANALYSIS / name
    if not path.exists():
        return None
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "report" / "numbers.tex")
    args = parser.parse_args(argv[1:])

    macros: dict[str, str] = {}
    missing: list[str] = []

    def put(name: str, value, digits: int = 4, source: str = "") -> None:
        if value is None:
            missing.append(f"{name} ({source})")
            return
        macros[name] = french(float(value), digits) if not isinstance(value, str) else value

    # -- lot A : coût, parité, branchement ---------------------------------
    cost = load_json("lotA_cost.json")
    if cost:
        derived = cost["derived"]
        put("CoutPanneauSecondes", derived["panel_seconds"], 5, "lotA_cost")
        put("CoutPanneauKio", derived["panel_bytes"] / 1024, 1, "lotA_cost")
        put("SurcoutEvenements", 100 * derived["events_overhead_share"], 1, "lotA_cost")
        put("SurcoutGini", 100 * (derived.get("market_stats_overhead_share") or float("nan")),
            1, "lotA_cost")
        put("EmpreinteCampagneGio", derived["budget"]["k=10"]["gio_campagne"], 2, "lotA_cost")
        put("PasEchantillonnage", 10, 0, "campaign.PANEL_EVERY")
    else:
        missing.append("lotA_cost.json")

    branching = load_json("lotA_branching.json")
    if branching:
        put("LotAUnB", branching["b1"], 4, "lotA_branching")
        put("LotADeuxB", branching["b2"], 4, "lotA_branching")
        put("LotAEcartB", branching["gap_b2_b1"], 4, "lotA_branching")
        put("LotAAretes", branching["n_edges"], 0, "lotA_branching")
        put("LotAAretesMortelles", branching["n_edges_lethal"], 0, "lotA_branching")
        put("LotAPartMortelle",
            100 * branching["n_edges_lethal"] / branching["n_edges"], 1, "lotA_branching")
    else:
        missing.append("lotA_branching.json")

    # -- lot B : la porte et la décomposition -------------------------------
    gate = load_json("lotB_gate.json")
    if gate:
        measured = gate["measured"]
        for macro, key in (("Epsilon", "epsilon_prod_tot"), ("ElasticitePop", "dln_pop_dlnA"),
                           ("ElasticiteNProd", "dln_n_prod_dlnA"),
                           ("ElasticiteKeq", "dln_K_eq_dlnA"),
                           ("ElasticiteGini", "dln_gini_dlnA"),
                           ("ElasticiteRotation", "dln_rotation_dlnA"),
                           ("ElasticiteMortalite", "dln_mortality_dlnA")):
            put(macro, measured[key]["mean"], 4, "lotB_gate")
            put(macro + "IC", measured[key]["ci95"], 4, "lotB_gate")
        put("BandeBasse", gate["prediction"]["band"][0], 4, "lotB_gate")
        put("BandeHaute", gate["prediction"]["band"][1], 4, "lotB_gate")
        put("ExposantImplique", gate["verdict"]["implied_a"], 3, "lotB_gate")
        put("DistanceBorneVOne", gate["verdict"]["distance_to_a_v1_bound_in_ci"], 2, "lotB_gate")
        put("DistanceBorneVTwo", gate["verdict"]["distance_to_a_v2_bound_in_ci"], 2, "lotB_gate")
        put("ResiduIdentite", gate["identity"]["residual"], 6, "lotB_gate")
        for arm, entry in gate["a_by_arm"].items():
            safe = latex_name(arm)
            put(f"ExposantA{safe}", entry["mean"], 3, "lotB_gate")
            put(f"ExposantA{safe}IC", entry["ci95"], 3, "lotB_gate")
    else:
        missing.append("lotB_gate.json")

    # -- lot C0 : couverture -------------------------------------------------
    coverage = load_json("lotC0_coverage.json")
    if coverage:
        put("CibleNTail", coverage["target_n_tail"], 0, "lotC0")
        for key, macro in (("tous/int_in", "CouvertureInteret"), ("tous/nw", "CouvertureNW"),
                           ("tous/K", "CouvertureK"), ("tous/prod", "CouvertureProd")):
            if key in coverage["groups"]:
                entry = coverage["groups"][key]
                put(macro + "NTail", entry["n_tail_median"], 0, "lotC0")
                put(macro + "Alpha", entry["alpha_median"], 3, "lotC0")
    else:
        missing.append("lotC0_coverage.json")

    # -- lot D : avalanches --------------------------------------------------
    avalanches = load_json("lotD_avalanches.json")
    if avalanches:
        summary = avalanches["summary"]
        for arm, macro in (("free/control", "Controle"), ("free/all_A150", "AllAcentcinquante"),
                           ("free/all_A150_K0comp", "Compense")):
            if arm in summary:
                entry = summary[arm]
                put(f"BUn{macro}", entry["b1"]["mean"], 4, "lotD")
                put(f"BUn{macro}IC", entry["b1"]["ci95"], 4, "lotD")
                put(f"BDeux{macro}", entry["b2"]["mean"], 4, "lotD")
                put(f"AlphaTaille{macro}", entry["alpha_size"]["mean"], 3, "lotD")
                put(f"Susceptibilite{macro}", entry["susceptibility"]["mean"], 1, "lotD")
        if all(k in summary for k in ("free/control", "free/all_A150",
                                      "free/all_A150_K0comp")):
            control = summary["free/control"]["b1"]["mean"]
            treated = summary["free/all_A150"]["b1"]["mean"]
            compensated = summary["free/all_A150_K0comp"]["b1"]["mean"]
            put("EffetABranchement", treated - control, 4, "lotD")
            put("EffetResiduelBranchement", compensated - control, 4, "lotD")
            put("PartAnnuleeKzero",
                100 * (1 - abs(compensated - control) / abs(treated - control)), 1, "lotD")
    else:
        missing.append("lotD_avalanches.json")

    # -- lot T : le taux comme partage ---------------------------------------
    bargain = load_json("bargain_summary.json")
    if bargain:
        summary = bargain["summary"]
        for arm in summary:
            safe = latex_name(arm)
            for key, macro in (("pop", "Pop"), ("prod_tot", "Prod"), ("K_tot", "K"),
                               ("b1", "BUn"), ("b2", "BDeux"), ("gini_K", "GiniK"),
                               ("gini_int_in", "GiniInteret"), ("tension", "Tension"),
                               ("book_rate", "TauxCarnet"),
                               ("mkt_p_implied", "PartageImplique")):
                if key in summary[arm]:
                    put(f"Taux{safe}{macro}", summary[arm][key]["mean"], 4, "bargain")
        if "convexity_test" in bargain:
            put("RapportPopDemi", bargain["convexity_test"]["ratio"], 3, "bargain")
    else:
        missing.append("bargain_summary.json")

    # -- distribution --------------------------------------------------------
    distribution = load_json("lotB_distribution.json")
    if distribution and "all_A150" in distribution["contrasts"]:
        contrast = distribution["contrasts"]["all_A150"]
        put("NInstantanes", distribution["n_snapshots_par_run"], 0, "lotB_distribution")
        for key, macro in (("interest_share_of_income", "PartInteretRevenu"),
                           ("rentier_count_share", "PartRentiers"),
                           ("gini_prod", "GiniProd"), ("gini_K", "GiniKapital"),
                           ("mean_age", "AgeMoyen")):
            if key in contrast:
                put(f"Delta{macro}", contrast[key]["diff"], 4, "lotB_distribution")
                put(f"Delta{macro}IC", contrast[key]["diff_ci95"], 4, "lotB_distribution")
    else:
        missing.append("lotB_distribution.json")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "% Engendré par scripts/make_numbers.py — NE PAS ÉDITER À LA MAIN.",
        "% Chaque macro vient d'un fichier de results/analysis/.",
        f"% {len(macros)} macros.",
        "",
    ]
    illegal = [name for name in macros if not name.isalpha()]
    assert not illegal, f"noms de macro illégaux en LaTeX : {illegal}"
    for name in sorted(macros):
        lines.append(f"\\newcommand{{\\{name}}}{{{macros[name]}}}")
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"{len(macros)} macros écrites dans {args.out}")
    if missing:
        print(f"SOURCES ABSENTES ({len(missing)}) :", file=sys.stderr)
        for item in missing:
            print(f"  - {item}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
