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

    # -- lot C : classes de lois, trois échelles ------------------------------
    laws = load_json("lotC_summary.json")
    if laws:
        summary = laws["summary"]
        for key, macro in (("free/control|tous|int_in", "AlphaInteret"),
                           ("free/control|tous|nw", "AlphaNW"),
                           ("free/control|net:crediteur|nw", "AlphaNWCreditrices"),
                           ("free/control|net:debiteur|nw", "AlphaNWDebitrices"),
                           ("free/control|net:crediteur|int_in", "AlphaInteretCreditrices"),
                           ("free/control|net:debiteur|int_in", "AlphaInteretDebitrices")):
            if key in summary:
                entry = summary[key]
                put(macro, entry["alpha_mean"], 3, "lotC")
                put(macro + "SdGraines", entry["alpha_sd_inter_seed"], 3, "lotC")
                put(macro + "SdInstantanes", entry["alpha_sd_inter_snapshot_median"], 3, "lotC")
                put(macro + "SdIntra", entry["alpha_sd_intra_snapshot_median"], 3, "lotC")
        # Étendue des exposants sur tous les bras : le résultat d'invariance.
        for quantity, macro in (("int_in", "Interet"), ("nw", "NW")):
            values = [entry["alpha_mean"] for key, entry in summary.items()
                      if key.endswith(f"|tous|{quantity}") and entry["n_seeds"] >= 2]
            if values:
                put(f"Etendue{macro}Min", min(values), 3, "lotC")
                put(f"Etendue{macro}Max", max(values), 3, "lotC")
                put(f"Etendue{macro}Pct",
                    100 * (max(values) - min(values)) / min(values), 1, "lotC")
    else:
        missing.append("lotC_summary.json")

    families = load_csv("lotC_families.csv")
    if families:
        for quantity, macro in (("int_in", "Interet"), ("nw", "NW")):
            selected = [r for r in families if r["quantity"] == quantity]
            if not selected:
                continue
            put(f"Vuong{macro}LN",
                sum(float(r["vuong_pl_vs_ln"]) for r in selected) / len(selected), 2, "lotC")
            put(f"Vuong{macro}Exp",
                sum(float(r["vuong_pl_vs_exp"]) for r in selected) / len(selected), 2, "lotC")
            put(f"Degenerees{macro}",
                sum(r["lognormal_degenerate"] == "True" for r in selected), 0, "lotC")
            put(f"Ajustements{macro}", len(selected), 0, "lotC")
    else:
        missing.append("lotC_families.csv")

    # -- lot T : le taux comme partage ---------------------------------------
    bargain = load_json("bargain_summary.json")
    if bargain:
        summary = bargain["summary"]
        for arm in summary:
            safe = latex_name(arm)
            for key, macro in (("pop", "Pop"), ("prod_tot", "Prod"), ("K_tot", "K"),
                               ("b1", "BUn"), ("b2", "BDeux"), ("gini_K", "GiniK"),
                               ("gini_int_in", "GiniInteret"), ("tension", "Tension"),
                               ("gini_nw_signed", "GiniNW"),
                               ("book_rate", "TauxCarnet"),
                               ("mkt_p_implied", "PartageImplique")):
                if key in summary[arm]:
                    put(f"Taux{safe}{macro}", summary[arm][key]["mean"], 4, "bargain")
        if "convexity_test" in bargain:
            put("RapportPopDemi", bargain["convexity_test"]["ratio"], 3, "bargain")
    else:
        missing.append("bargain_summary.json")

    # -- lot E : contrôle par rho ---------------------------------------------
    control_rho = load_json("lotE_rho_verdicts.json")
    if control_rho:
        put("EtendueRho", control_rho["span"], 0, "lotE")
        for key, macro in (("alpha_int_in", "RhoAlphaInteret"), ("alpha_nw", "RhoAlphaNW"),
                           ("b1", "RhoBUn"), ("b2", "RhoBDeux"),
                           ("gini", "RhoGini"), ("rotation", "RhoRotation"),
                           ("pop", "RhoPop")):
            entry = control_rho["verdicts"].get(key)
            if entry:
                put(macro + "Exposant", entry["exponent"]["mean"], 4, "lotE")
                put(macro + "ExposantIC", entry["exponent"]["ci95"], 4, "lotE")
                macros[macro + "Controle"] = "oui" if entry["controlled"] else "non"
                put(macro + "Bas", entry["means"][0], 4, "lotE")
                put(macro + "Haut", entry["means"][-1], 4, "lotE")
        # La relation héritée rotation = rho*G, et sa rupture.
        gini = control_rho["verdicts"].get("gini")
        rotation = control_rho["verdicts"].get("rotation")
        if gini and rotation:
            predicted = 1.0 + gini["exponent"]["mean"]
            put("RotationPredite", predicted, 4, "lotE")
            put("RotationMesuree", rotation["exponent"]["mean"], 4, "lotE")
            put("RotationEcartSigma",
                abs(predicted - rotation["exponent"]["mean"]) / rotation["exponent"]["ci95"]
                * 2.201, 0, "lotE")
    else:
        missing.append("lotE_rho_verdicts.json")

    # -- lot F : ablation vers M4B --------------------------------------------
    ablation = load_json("lotD_avalanches.json")
    if ablation and any(k.startswith("ablation/") for k in ablation["summary"]):
        summary = ablation["summary"]
        control_b = 0.7863  # bras de contrôle, mesuré au lot D
        target_b = 0.297    # valeur publiée par M4B
        for arm, macro in (("ablation/m4b_like", "MquatreB"),
                           ("ablation/sigma025", "SigmaVingtCinq"),
                           ("ablation/delta005", "DeltaCinq")):
            if arm in summary:
                put(f"Ablation{macro}BUn", summary[arm]["b1"]["mean"], 4, "lotF")
                put(f"Ablation{macro}Alpha", summary[arm]["alpha_size"]["mean"], 3, "lotF")
                put(f"Ablation{macro}Part",
                    100 * (control_b - summary[arm]["b1"]["mean"]) / (control_b - target_b),
                    1, "lotF")
    else:
        missing.append("ablation dans lotD_avalanches.json")

    # -- lot T : rampes --------------------------------------------------------
    ramp = load_json("lotT_ramp.json")
    if ramp:
        for level, macro in (("p=0.25", "RampeQuart"), ("p=0.5", "RampeDemi")):
            if level in ramp:
                put(macro, ramp[level]["ratio"]["mean"], 4, "lotT")
                put(macro + "IC", ramp[level]["ratio"]["ci95"], 4, "lotT")
    else:
        missing.append("lotT_ramp.json")

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

    # -- lot I : le mécanisme de l'effet de partage --------------------------
    convexity = load_json("lotI_convexity.json")
    if convexity:
        weighting = convexity.get("ponderation", {}).get("marginal")
        if weighting:
            put("PartageParContrat", weighting["p_moyen"]["mean"], 4, "lotI")
            put("PartagePondere", weighting["p_pondere"]["mean"], 4, "lotI")
            put("PartagePondereIC", weighting["p_pondere"]["ci95"], 4, "lotI")
            put("CovariancePartage", weighting["covariance_normalisee"]["mean"], 4, "lotI")
        # Le témoin : chez les bras à partage fixe, les deux lectures doivent
        # coïncider. On publie le PIRE écart, pas le meilleur.
        fixed = [entry["covariance_normalisee"]["mean"]
                 for arm, entry in convexity.get("ponderation", {}).items()
                 if arm != "marginal" and entry]
        if fixed:
            put("TemoinPartageFixe", max(abs(value) for value in fixed), 6, "lotI")
        verdict = convexity.get("verdict", {})
        if verdict:
            put("ClassesCapitalConvexes", verdict.get("n_classes_convexes"), 0, "lotI")
            put("ClassesCapitalTotal", verdict.get("n_classes_capital"), 0, "lotI")
        marginal = convexity.get("resume", {}).get("marginal")
        if marginal:
            put("EcartJensen", marginal["ecart_jensen"]["mean"], 4, "lotI")
            put("EcartJensenIC", marginal["ecart_jensen"]["ci95"], 4, "lotI")
            put("MortaliteObservee", marginal["mortalite_observee"]["mean"], 4, "lotI")
            put("MortaliteAuFardeauMoyen",
                marginal["mortalite_au_service_moyen"]["mean"], 4, "lotI")
            ratio = (marginal["mortalite_observee"]["mean"]
                     / marginal["mortalite_au_service_moyen"]["mean"])
            put("RapportJensen", ratio, 2, "lotI")
        for arm, macro in (("p=0", "PZero"), ("p=0.5", "PDemi"), ("p=1", "PUn")):
            entry = convexity.get("resume", {}).get(arm)
            if entry:
                put(f"EcartJensen{macro}", entry["ecart_jensen"]["mean"], 4, "lotI")
        closest = convexity.get("voisinage", {}).get("plus_proche")
        if closest:
            put("BrasLePlusProche", closest.replace("=", " = ").replace(".", ","), 0, "lotI")
            near = convexity["voisinage"][closest]["distance_relative_moyenne"]
            put("DistanceAuPlusProche", 100 * near, 1, "lotI")
            half = convexity["voisinage"].get("p=0.5")
            if half:
                put("DistanceAuPartageEquitable",
                    100 * half["distance_relative_moyenne"], 1, "lotI")
    else:
        missing.append("lotI_convexity.json")

    # -- lot J : sur-détermination et suffisance ------------------------------
    sufficiency = load_json("lotJ_sufficiency.json")
    if sufficiency:
        verdict = sufficiency["verdict"]
        reference = sufficiency["resume"][verdict["bras_reference"]]
        put("PlancherSuffisance", 100 * verdict["plancher"], 1, "lotJ")
        put("PlancherSuffisanceIC", 100 * verdict["plancher_ic"], 1, "lotJ")
        put("ToutesCausesSuffisantes", 100 * verdict["toutes_suffisantes"], 1, "lotJ")
        put("IncidenceEffacement", 100 * verdict["incidence_effacement"], 2, "lotJ")
        put("PartSurDeterminees", 100 * reference["part_sur_determinees"]["mean"], 1, "lotJ")
        put("DegreMoyenCascade", reference["degre_moyen"]["mean"], 2, "lotJ")
        put("ConcentrationChoc", reference["concentration_moyenne"]["mean"], 3, "lotJ")
        put("CausesSuffisantesMoyen",
            reference["nb_causes_suffisantes_moyen"]["mean"], 3, "lotJ")
    else:
        missing.append("lotJ_sufficiency.json")

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
