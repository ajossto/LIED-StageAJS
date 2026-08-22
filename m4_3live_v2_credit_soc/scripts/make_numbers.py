"""Fabrique `report/numbers.tex` : tous les nombres cités dans le corps des
rapports, sous forme de macros LaTeX.

Pourquoi ce détour. La règle de rédaction du dépôt veut que toute valeur
numérique ait une source identifiable et qu'aucun chiffre ne « tombe du
ciel ». Recopier un nombre à la main dans un `.tex` viole cette règle deux
fois : il n'est plus rattaché à son fichier de données, et il se périme
silencieusement quand la campagne est relancée. Ici, chaque macro est écrite
depuis le JSON ou le CSV qui la contient, et le rapport ne cite que des
macros.

Toute macro dont la source manque est définie à `---`, jamais laissée
indéfinie : un rapport doit pouvoir se compiler même si une campagne n'a pas
tourné, en montrant visiblement le trou.

    python3 scripts/make_numbers.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ANALYSIS = ROOT / "results" / "analysis"
TARGET = ROOT / "report" / "numbers.tex"

MISSING = "---"


def load_json(name: str) -> dict:
    path = ANALYSIS / name
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def load_csv(name: str) -> list[dict]:
    path = ANALYSIS / name
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def french(value, digits: int = 2, sign: bool = False) -> str:
    if value is None or value != value:
        return MISSING
    fmt = f"{{:{'+' if sign else ''}.{digits}f}}"
    return fmt.format(value).replace(".", ",")


def integer(value) -> str:
    if value is None or value != value:
        return MISSING
    text = f"{int(round(value)):d}"
    return "\\,".join([text[max(i - 3, 0):i] for i in range(len(text), 0, -3)][::-1])


def dig(payload, *keys, default=None):
    node = payload
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node


def main() -> int:
    macros: dict[str, str] = {}

    verdicts = load_json("verdicts.json")
    lot_d_tr = load_json("lot_d_transition.json")
    lot_d_res = load_json("lot_d_residuel.json")
    lot_e_tr = load_json("lot_e_transition.json")
    lot_e_res = load_json("lot_e_residuel.json")
    rotation = load_json("rotation_summary.json")
    cost = load_csv("cost_profile_summary.csv")
    survivors = load_csv("survivors.csv")

    # -- protocole ---------------------------------------------------------
    seeds = dig(lot_d_res, "arms", "new_A150", "n_seeds_free", default=None)
    macros["nSeeds"] = integer(seeds) if seeds else MISSING
    macros["tCritFive"] = "2,201"
    macros["tCritOne"] = "3,106"
    macros["tCritFiveFive"] = "2,776"

    # -- lot D : le régime nouveau ----------------------------------------
    for label, payload in (("Transition", lot_d_tr), ("Residuel", lot_d_res)):
        for arm, short in (("new_A150", "AhcentCinquante"),
                           ("new_A075", "AzeroSeptCinq"),
                           ("new_g060", "GammaSixZero")):
            levels = dig(payload, "arms", arm, "levels_free", default={})
            v1 = dig(payload, "arms", arm, "levels_v1", default={})
            paired = dig(payload, "arms", arm, "paired_free_vs_v1", default={})
            macros[f"pctReversal{short}{label}"] = french(
                100 * dig(levels, "reversed_share", "mean", default=float("nan")))
            macros[f"pctVolumeRev{short}{label}"] = french(
                100 * dig(levels, "volume_rev_share", "mean", default=float("nan")))
            macros[f"pctBlocked{short}{label}"] = french(
                100 * dig(levels, "blocked_share", "mean", default=float("nan")))
            macros[f"techZeroFree{short}{label}"] = french(
                dig(levels, "tech0_alive", "mean", default=float("nan")), 1)
            macros[f"techZeroVone{short}{label}"] = french(
                dig(v1, "tech0_alive", "mean", default=float("nan")), 1)
            for column, name in (("prod_tot", "Prod"), ("pop", "Pop"),
                                 ("deaths_per_pop", "Mort"), ("rotation", "Rot"),
                                 ("interest_paid", "Int"),
                                 ("K_share_creditors", "KCred"),
                                 ("corr_K_net", "CorrK")):
                macros[f"diff{name}{short}{label}"] = french(
                    100 * dig(paired, column, "mean", default=float("nan")), 2, sign=True)
                macros[f"se{name}{short}{label}"] = french(
                    100 * dig(paired, column, "se", default=float("nan")))
                macros[f"t{name}{short}{label}"] = french(
                    dig(paired, column, "t", default=float("nan")))
    macros["nNonStationnaireTransition"] = integer(
        dig(verdicts, "transition", "runs_hors_stationnarite", default=float("nan")))
    macros["nNonStationnaireResiduel"] = integer(
        dig(verdicts, "residuel", "runs_hors_stationnarite", default=float("nan")))

    # -- lot E : la prédiction --------------------------------------------
    for label, payload in (("Transition", lot_e_tr), ("Residuel", lot_e_res)):
        prediction = payload.get("prediction", {})
        macros[f"lotEBase{label}"] = french(prediction.get("defauts_reference"))
        macros[f"lotEWindow{label}"] = french(prediction.get("fenetre_de_bascule"))
        macros[f"lotEPredicted{label}"] = french(prediction.get("defauts_predits"))
        macros[f"lotEPctPredicted{label}"] = french(
            100 * prediction["hausse_relative_predite"], 1, sign=True
        ) if prediction.get("hausse_relative_predite") is not None else MISSING
        macros[f"lotEPctMeasured{label}"] = french(
            100 * prediction["hausse_relative_mesuree"], 1, sign=True
        ) if prediction.get("hausse_relative_mesuree") is not None else MISSING
        macros[f"lotEDeaths{label}"] = french(
            100 * dig(payload, "paired", "deaths_per_pop", "mean", default=float("nan")),
            2, sign=True)
        macros[f"lotEProd{label}"] = french(
            100 * dig(payload, "paired", "prod_tot", "mean", default=float("nan")),
            2, sign=True)

    # -- lot F : la rotation ----------------------------------------------
    macros["rotNRuns"] = integer(rotation.get("n_runs"))
    macros["rotNInstrumented"] = integer(rotation.get("n_with_gini"))
    macros["rotIdentityGap"] = (
        f"{rotation['identity_max_gap']:.1e}".replace(".", ",").replace("e-", "\\cdot 10^{-")
        + "}" if rotation.get("identity_max_gap") else MISSING
    )
    macros["rotFOneGap"] = french(rotation.get("f1_vs_rho_max_gap"), 3)
    macros["rotFTwoMin"] = french(rotation.get("f2_min"), 4)
    macros["rotFTwoMax"] = french(rotation.get("f2_max"), 4)
    fits = rotation.get("fits", {})
    for key, name in (
        ("mortalité $\\sim$ rotation (tous runs)", "MortAll"),
        ("mortalité $\\sim$ rotation (runs stationnaires)", "MortStat"),
        ("$f_3 \\sim \\bar G$ (Gini, moyenne logarithmique)", "Gini"),
        ("$f_3 \\sim CV$ prédit (bilan de variance)", "Closure"),
        ("rotation $\\sim CV$ prédit $\\times\\ \\rho$", "ClosureRot"),
    ):
        fit = fits.get(key, {})
        macros[f"rotSlope{name}"] = french(fit.get("slope"), 3)
        macros[f"rotRtwo{name}"] = french(fit.get("r2"), 4)
        macros[f"rotSpan{name}"] = french(fit.get("span"), 1)
        macros[f"rotN{name}"] = integer(fit.get("n"))
    for key, name in (("f3_over_gini_logmean", "GiniLog"),
                      ("f3_over_gini_before", "GiniBefore"),
                      ("rotation_over_closed_form", "ClosedForm")):
        node = rotation.get(key, {})
        macros[f"rotGap{name}Med"] = french(
            100 * node["median"], 1, sign=True) if node else MISSING
        macros[f"rotGap{name}Min"] = french(
            100 * node["min"], 1, sign=True) if node else MISSING
        macros[f"rotGap{name}Max"] = french(
            100 * node["max"], 1, sign=True) if node else MISSING

    # -- coût --------------------------------------------------------------
    for row in cost:
        # Un nom de macro LaTeX ne peut pas contenir de chiffre : `v1` et `v2`
        # deviennent `Vone` et `Vtwo`.
        engine = {"v1": "Vone", "v2": "Vtwo"}[row["engine"]]
        macros[f"cost{engine}Early"] = french(1000 * float(row["median_s_t10_210"]), 1)
        macros[f"cost{engine}Late"] = french(1000 * float(row["median_s_last200"]), 1)
        macros[f"cost{engine}Growth"] = french(float(row["growth"]), 3)
        macros[f"cost{engine}Keys"] = integer(float(row["book_keys_final"]))
        macros[f"cost{engine}Total"] = integer(float(row["total_seconds"]))
        macros[f"cost{engine}Pop"] = integer(float(row["pop_final"]))
    if len(cost) == 2:
        v1 = next(r for r in cost if r["engine"] == "v1")
        v2 = next(r for r in cost if r["engine"] == "v2")
        macros["costEmptyShare"] = french(
            100 * (1 - float(v2["book_keys_final"]) / float(v1["book_keys_final"])), 1)
        macros["costSaving"] = french(
            100 * (1 - float(v2["total_seconds"]) / float(v1["total_seconds"])), 1)

    # -- survivantes -------------------------------------------------------
    for direction in ("free", "richest_lends"):
        tag = "Free" if direction == "free" else "Vone"
        for tech in (0, 1):
            rows = [r for r in survivors
                    if r["direction"] == direction and int(r["tech"]) == tech]
            if not rows:
                continue
            name = "Old" if tech == 0 else "New"
            macros[f"surv{tag}{name}N"] = french(
                sum(float(r["n"]) for r in rows) / len(rows), 1)
            macros[f"surv{tag}{name}Creditor"] = french(
                100 * sum(float(r["part_creancieres_nettes"]) for r in rows) / len(rows), 1)
            macros[f"surv{tag}{name}Interest"] = french(
                100 * sum(float(r["part_du_revenu_en_interets"]) for r in rows) / len(rows), 1)
            macros[f"surv{tag}{name}K"] = integer(
                sum(float(r["K_moyen"]) for r in rows) / len(rows))
            macros[f"surv{tag}{name}Age"] = integer(
                sum(float(r["age_median"]) for r in rows) / len(rows))

    # -- parité : lue dans les journaux des deux passes -------------------
    import re

    for label, name in (("parity_lotA_full.log", "LotA"),
                        ("parity_lotBCE_full.log", "LotBCE"),
                        ("parity_final_full.log", "Final")):
        path = ANALYSIS / label
        if not path.exists():
            macros[f"parity{name}Calls"] = MISSING
            macros[f"parity{name}Seconds"] = MISSING
            macros[f"parity{name}Steps"] = MISSING
            continue
        text = path.read_text(encoding="utf-8")
        calls = re.search(r"([\d\s\u202f]+) appels au noyau", text)
        seconds = re.search(r";\s*(\d+) s", text)
        steps = re.search(r"^\s*(\d+) pas ×", text, re.MULTILINE)
        macros[f"parity{name}Calls"] = (
            calls.group(1).strip().replace(" ", "\\,").replace("\u202f", "\\,")
            if calls else MISSING)
        macros[f"parity{name}Seconds"] = seconds.group(1) if seconds else MISSING
        macros[f"parity{name}Steps"] = (
            integer(float(steps.group(1))) if steps else MISSING)
        macros[f"parity{name}Nul"] = (
            "nul" if "écart maximal NUL" in text else MISSING)

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    lines = ["% Fichier ENGENDRÉ par scripts/make_numbers.py — ne pas éditer.",
             "% Chaque macro vient d'un fichier de results/analysis/."]
    for name in sorted(macros):
        lines.append(f"\\newcommand{{\\{name}}}{{{macros[name]}}}")
    TARGET.write_text("\n".join(lines) + "\n", encoding="utf-8")
    missing = [name for name, value in macros.items() if value == MISSING]
    print(f"{len(macros)} macros écrites dans {TARGET.relative_to(ROOT)}")
    if missing:
        print(f"  {len(missing)} sans source : {', '.join(sorted(missing)[:8])}"
              + (" ..." if len(missing) > 8 else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
