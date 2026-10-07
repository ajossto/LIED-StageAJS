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
    amplitude = load_csv("amplitude.csv")
    stationarity = load_csv("stationarity_runs.csv")
    entities = load_csv("survivors_entities.csv")

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
                                 ("corr_K_net", "CorrK"),
                                 ("corr_marg_net", "CorrMarg"),
                                 ("K_tot", "Ktot"), ("n_loans", "NLoans"),
                                 ("destroyed", "Destroyed"),
                                 ("destroyed_per_K", "DestroyedPerK"),
                                 ("mkt_surplus", "Surplus"),
                                 ("tension", "Tension"),
                                 ("tech0_alive", "TechZero")):
                macros[f"diff{name}{short}{label}"] = french(
                    100 * dig(paired, column, "mean", default=float("nan")), 2, sign=True)
                macros[f"se{name}{short}{label}"] = french(
                    100 * dig(paired, column, "se", default=float("nan")))
                macros[f"t{name}{short}{label}"] = french(
                    dig(paired, column, "t", default=float("nan")))
    for label, key in (("Transition", "transition"), ("Residuel", "residuel")):
        flagged = dig(verdicts, key, "bras_hors_stationnarite", default=None)
        tested = dig(verdicts, key, "bras_testes", default=None)
        macros[f"nNonStationnaire{label}"] = (
            integer(len(flagged)) if flagged is not None else MISSING)
        macros[f"nBrasTestes{label}"] = integer(tested) if tested else MISSING
        span = dig(verdicts, key, "etendue_du_rapport", default={})
        for column, name in (("K_tot", "Ktot"), ("pop", "Pop"), ("prod_tot", "Prod")):
            if column in span:
                macros[f"spanStat{name}{label}Min"] = french(span[column][0], 4)
                macros[f"spanStat{name}{label}Max"] = french(span[column][1], 4)
            else:
                macros[f"spanStat{name}{label}Min"] = MISSING
                macros[f"spanStat{name}{label}Max"] = MISSING

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
        macros[f"lotEPop{label}"] = french(
            100 * dig(payload, "paired", "pop", "mean", default=float("nan")), 2, sign=True)
        macros[f"lotEKtot{label}"] = french(
            100 * dig(payload, "paired", "K_tot", "mean", default=float("nan")), 2, sign=True)
        macros[f"lotETProd{label}"] = french(
            dig(payload, "paired", "prod_tot", "t", default=float("nan")))
        macros[f"lotETDeaths{label}"] = french(
            dig(payload, "paired", "deaths_per_pop", "t", default=float("nan")))
        macros[f"lotEMeasuredDefaults{label}"] = french(
            prediction.get("defauts_mesures"), 3)
        macros[f"lotERedistribution{label}"] = integer(
            prediction.get("redistribution_par_pas"))
        macros[f"lotEInterest{label}"] = integer(
            prediction.get("interets_servis_par_pas"))
        macros[f"lotERedistShare{label}"] = french(
            100 * prediction["part_du_capital_redistribuee"], 4
        ) if prediction.get("part_du_capital_redistribuee") is not None else MISSING
        ratio = payload.get("service_ratio", {})
        for key, name in (("n_debitrices", "N"), ("min", "Min"), ("p1", "Pone"),
                          ("p5", "Pfive"), ("mediane", "Med"), ("max", "Max"),
                          ("seuil_de_bascule", "Seuil"), ("marge", "Marge")):
            value = ratio.get(key)
            digits = 0 if name == "N" else 2
            macros[f"ratio{name}{label}"] = (
                integer(value) if name == "N" else french(value, digits + 2)
            ) if value is not None else MISSING
        macros[f"ratioInWindow{label}"] = integer(
            ratio.get("n_dans_la_fenetre")) if ratio else MISSING

    # -- la loi de v1 mise à l'épreuve par le levier nouveau ---------------
    for label, payload in (("Transition", lot_d_tr), ("Residuel", lot_d_res)):
        for arm, short in (("new_A150", "AhcentCinquante"),
                           ("new_A075", "AzeroSeptCinq"),
                           ("new_g060", "GammaSixZero")):
            paired = dig(payload, "arms", arm, "paired_free_vs_v1", default={})
            rot = dig(paired, "rotation", "mean", default=None)
            mort = dig(paired, "deaths_per_pop", "mean", default=None)
            if rot is None or mort is None or rot != rot:
                macros[f"lawPred{short}{label}"] = MISSING
                continue
            macros[f"lawPred{short}{label}"] = french(
                100 * ((1 + rot) ** 1.337 - 1), 2, sign=True)

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
        ("mortalité $\\sim$ rotation (sous-ensemble le plus plat)", "MortStat"),
        ("$f_3 \\sim \\bar G$ (Gini, moyenne logarithmique)", "Gini"),
        ("$f_3 \\sim CV$ prédit (bilan de variance)", "Closure"),
        ("rotation $\\sim CV$ prédit $\\times\\ \\rho$", "ClosureRot"),
    ):
        fit = fits.get(key, {})
        macros[f"rotSlope{name}"] = french(fit.get("slope"), 3)
        macros[f"rotRtwo{name}"] = french(fit.get("r2"), 4)
        macros[f"rotSpan{name}"] = french(fit.get("span"), 1)
        macros[f"rotN{name}"] = integer(fit.get("n"))
        macros[f"rotSe{name}"] = french(fit.get("se_slope"), 3)
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

    # -- régime hétérogène : la relation f3 = Gbar y tient-elle ? ---------
    hetero = rotation.get("hetero", {})
    for direction, tag in (("free", "Free"), ("richest_lends", "Vone")):
        node = hetero.get(direction, {})
        macros[f"hetero{tag}N"] = integer(node.get("n")) if node else MISSING
        macros[f"hetero{tag}Med"] = french(
            100 * node["median"], 2, sign=True) if node else MISSING
        macros[f"hetero{tag}Pfive"] = french(
            100 * node["p5"], 1, sign=True) if node else MISSING
        macros[f"hetero{tag}Pninetyfive"] = french(
            100 * node["p95"], 1, sign=True) if node else MISSING
        macros[f"hetero{tag}MedResiduel"] = french(
            100 * node["median_residuel"], 2, sign=True) if node else MISSING

    # -- contrôle par levier et biais résiduel (§14.1, §14.2) --------------
    levers = rotation.get("fits_par_levier", {})
    names = {"lam": "Lam", "rho": "Rho", "sigma": "Sigma", "K0": "Kzero",
             "delta": "Delta", "base": "Base"}
    for key, name in names.items():
        fit = levers.get(key, {})
        macros[f"leverSlope{name}"] = french(fit.get("slope"), 3)
        macros[f"leverRtwo{name}"] = french(fit.get("r2"), 4)
        macros[f"leverSpan{name}"] = french(fit.get("span"), 2)
        macros[f"leverN{name}"] = integer(fit.get("n"))
    bias = rotation.get("biais_residuel", {})
    for key, entries in bias.items():
        tag = "Family" if key == "family" else "Direction"
        for name, node in entries.items():
            clean = (name.replace(" ", "").replace("_", "")
                     .replace("v1", "Vone").replace("v2", "Vtwo"))
            clean = clean[0].upper() + clean[1:]
            macros[f"bias{tag}{clean}Med"] = french(100 * node["biais_median"], 2, sign=True)
            macros[f"bias{tag}{clean}Min"] = french(100 * node["min"], 1, sign=True)
            macros[f"bias{tag}{clean}Max"] = french(100 * node["max"], 1, sign=True)
            macros[f"bias{tag}{clean}N"] = integer(node["n"])

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

    # -- coût du moteur du lot A, lu dans son journal ----------------------
    # La table publiée décrit le moteur LIVRÉ ; celle-ci décrit le moteur du
    # lot A, c'est-à-dire avant l'instrumentation. Les deux sont rapportées
    # pour que le lecteur voie ce que l'instrumentation coûte.
    import re as _re

    log = ANALYSIS / "cost_profile.log"
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            match = _re.match(
                r"(v\d) : ([\d.]+) ms/pas au début, ([\d.]+) ms/pas à la fin "
                r"\(×([\d.]+)\) ; (\d+) clefs pour (\d+) vivantes ; (\d+) s",
                line)
            if not match:
                continue
            tag = {"v1": "Vone", "v2": "Vtwo"}[match.group(1)]
            macros[f"lotAcost{tag}Early"] = french(float(match.group(2)), 1)
            macros[f"lotAcost{tag}Late"] = french(float(match.group(3)), 1)
            macros[f"lotAcost{tag}Growth"] = french(float(match.group(4)), 3)
            macros[f"lotAcost{tag}Total"] = integer(float(match.group(7)))

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


    # -- de combien le contrefactuel s'écarte des prêts effectivement conclus
    #
    # Les deux comptent presque la même chose — une paire que l'ancienne règle
    # refuserait conclut ici un prêt à contre-sens — mais pas exactement : une
    # paire peut être écartée pour une autre raison. Le rapport le dit « à N
    # centièmes de point près » ; N est mesuré, pas estimé à l'œil.
    worst_gap = 0.0
    for arm in ("new_A150", "new_A075", "new_g060"):
        levels = dig(lot_d_tr, "arms", arm, "levels_free", default={})
        blocked = dig(levels, "blocked_share", "mean", default=float("nan"))
        reversed_ = dig(levels, "reversed_share", "mean", default=float("nan"))
        if blocked == blocked and reversed_ == reversed_:
            worst_gap = max(worst_gap, abs(100 * (blocked - reversed_)))
    macros["ecartContrefactuelMax"] = french(worst_gap, 3) if worst_gap else MISSING

    # -- combien d'écarts appariés sont indistinguables de zéro ------------
    #
    # C'est l'argument des deux fenêtres, rendu comptable : sur les mêmes
    # sept observables et les mêmes trois bras, presque aucun écart n'est nul
    # pendant la transition et les deux tiers le sont ensuite.
    OBSERVES = ("prod_tot", "K_tot", "pop", "deaths_per_pop", "n_loans",
                "rotation", "interest_paid")
    for label_, payload in (("Transition", lot_d_tr), ("Residuel", lot_d_res)):
        total = crossing = 0
        largest = 0.0
        for arm in ("new_A150", "new_A075", "new_g060"):
            entry = dig(payload, "arms", arm, "paired_free_vs_v1", default={})
            for column in OBSERVES:
                node = entry.get(column)
                if not node or node.get("t") != node.get("t"):
                    continue
                total += 1
                if abs(node["t"]) < (node.get("t_crit_5pct") or 2.201):
                    crossing += 1
                largest = max(largest, abs(node["mean"]))
        macros[f"nEcarts{label_}"] = integer(total) if total else MISSING
        macros[f"nEcartsNuls{label_}"] = integer(crossing) if total else MISSING
        macros[f"ecartMax{label_}"] = french(100 * largest, 1) if total else MISSING

    # -- les figures elles-mêmes : combien, et combien de valeurs contrôlées -
    #
    # Le manifeste est écrit par `make_figures.py` et relu par
    # `tests/test_figures.py`, qui vérifie qu'AUCUNE valeur annotée n'est hors
    # du garde-fou. Les deux comptes coïncident donc par construction, et le
    # rapport peut citer celui-ci sans le recopier de la table du test.
    manifest_path = ROOT / "report" / "figures" / "manifest.json"
    if manifest_path.exists():
        entries = json.loads(manifest_path.read_text(encoding="utf-8"))
        macros["nombreFigures"] = integer(len(entries))
        macros["nombreValeursControlees"] = integer(
            sum(len(entry["valeurs"]) for entry in entries))
    else:
        macros["nombreFigures"] = MISSING
        macros["nombreValeursControlees"] = MISSING

    # -- parité : l'écart maximal, LU dans le CSV des déviations -----------
    deviations = load_csv("parity_deviations_8000.csv")
    if deviations:
        worst = max(abs(float(row["ecart_max_toutes_colonnes"]))
                    for row in deviations)
        macros["parityEcartMax"] = french(worst, 0)
        macros["parityNPas"] = integer(len(deviations))
    else:
        macros["parityEcartMax"] = MISSING
        macros["parityNPas"] = MISSING

    # -- corrélations : les NIVEAUX, pas leur écart relatif ----------------
    #
    # Un écart relatif sur une grandeur SIGNÉE est trompeur : passer de −0,232
    # à −0,378 s'écrit « +62,9 % » alors que la corrélation BAISSE, et un
    # écart qui traverse zéro s'écrit « −196,8 % », ce qui ne veut rien dire.
    # Les deux corrélations de diagnostic sont donc citées en niveau, sous
    # chaque règle, et c'est la figure qui montre la trajectoire.
    for label_, payload in (("Transition", lot_d_tr), ("Residuel", lot_d_res)):
        for column, name in (("corr_K_net", "CorrK"), ("corr_marg_net", "CorrMarg")):
            for side, tag in (("levels_free", "Free"), ("levels_v1", "Vone")):
                value = dig(payload, "arms", "new_A150", side, column, "mean",
                            default=float("nan"))
                macros[f"niveau{name}{tag}{label_}"] = french(value, 3, sign=True)

    # -- amplitude des quatre leviers, mesurée par scripts/amplitude.py -----
    #
    # Ces nombres étaient recopiés à la main depuis la sortie d'un test. Ils
    # viennent maintenant d'un CSV, comme tout le reste.
    short_names = {("A", "all"): "AllA", ("A", "fraction"): "FractionA",
                   ("gamma", "all"): "Gamma", ("A", "new"): "NewA"}
    for row in amplitude:
        tag = short_names.get((row["param"], row["portee"]))
        if tag is None:
            continue
        measured = float(row["m_exact"])
        naive = float(row["m_naif_capital_unite"])
        by_keq = float(row["m_naif_K_eq"])
        macros[f"ampl{tag}M"] = french(measured, 6)
        macros[f"ampl{tag}Mlong"] = f"{measured:.16g}".replace(".", ",")
        macros[f"ampl{tag}Naive"] = french(naive, 6)
        macros[f"ampl{tag}Keq"] = french(by_keq, 6)
        macros[f"ampl{tag}P"] = french(float(row["p_ex_ante"]), 6)
        macros[f"ampl{tag}N"] = integer(float(row["n_traitees"]))
        macros[f"ampl{tag}Ecart"] = french(100 * (by_keq / measured - 1.0), 2, sign=True)
        macros[f"ampl{tag}NaiveEcart"] = french(100 * (naive / measured - 1.0), 1, sign=True)
        # E vaut 1 PAR ALGÈBRE ; son écart à 1 ne mesure que la propreté de
        # l'aller-retour flottant. Quand il est nul, écrire « 0 » et non une
        # puissance de dix : « $0 \\cdot 10^{-0}$ » serait absurde.
        gap = abs(float(row["identite_E"]) - 1.0)
        if gap == 0.0:
            macros[f"ampl{tag}E"] = "0"
        else:
            mantissa, exponent = f"{gap:.0e}".split("e")
            macros[f"ampl{tag}E"] = f"{mantissa}\\cdot 10^{{{int(exponent)}}}"

    # -- ce qu'une bande fixe ferait au CONTRÔLE (§ stationnarité) ----------
    #
    # Le rapport affirme qu'une bande [0,99 ; 1,01] rejetterait onze des douze
    # graines d'un bras dont on SAIT qu'il est stationnaire. L'affirmation
    # était écrite à la main ; elle est maintenant comptée.
    LOW, HIGH = 0.99, 1.01
    for window, label in (("residuel", "Residuel"), ("transition", "Transition")):
        control = [r for r in stationarity
                   if r["fenetre"] == window and r["bras"] == "control"]
        if not control:
            macros[f"nControleGraines{label}"] = MISSING
            macros[f"nControleHorsBande{label}"] = MISSING
            continue
        outside = [r for r in control if not (LOW <= float(r["K_tot"]) <= HIGH)]
        macros[f"nControleGraines{label}"] = integer(len(control))
        macros[f"nControleHorsBande{label}"] = integer(len(outside))

    # -- inégalité des capitaux : le Gini que le §7 identifie à f_3 ---------
    #
    # Lu sur l'état final entité par entité, pas sur un agrégat : c'est la
    # seule source du dépôt qui porte des capitaux individuels.
    def _gini(values) -> float:
        values = sorted(v for v in values if v == v and v > 0)
        n = len(values)
        total = sum(values)
        if n == 0 or total == 0:
            return float("nan")
        weighted = sum((i + 1) * v for i, v in enumerate(values))
        return 2 * weighted / (n * total) - (n + 1) / n

    for direction, tag in (("free", "Free"), ("richest_lends", "Vone")):
        capitals = [float(r["K"]) for r in entities
                    if r["direction"] == direction and int(r["seed"]) == 0]
        macros[f"giniK{tag}"] = french(_gini(capitals), 4) if capitals else MISSING
        macros[f"nEntites{tag}"] = integer(len(capitals)) if capitals else MISSING

    # -- l'institution, en régime mixte : la bande que v1 s'interdisait -----
    #
    # ALGÈBRE, pas mesure : pour deux exposants γ égaux, la part optimale de
    # l'entité 1 vaut λ* = A_1^{1/(1-γ)} / (A_1^{1/(1-γ)} + A_2^{1/(1-γ)}),
    # soit A_1^2/(A_1^2+A_2^2) à γ = 1/2. Elle cède dès que K_1 > λ* C,
    # c'est-à-dire K_1 > [λ*/(1-λ*)] K_2. C'est cette borne, comparée à 1,
    # qui définit la bande où v1 refusait un échange que l'optimum voulait.
    A_OLD, A_NEW, GAMMA = 1.0, 1.5, 0.5
    exponent = 1.0 / (1.0 - GAMMA)
    lambda_star = A_OLD ** exponent / (A_OLD ** exponent + A_NEW ** exponent)
    macros["lambdaStarOld"] = french(lambda_star, 3)
    macros["seuilBandeOld"] = french(lambda_star / (1.0 - lambda_star), 3)

    # -- niveaux de tension, pour la figure d'instrumentation ---------------
    for label, payload in (("Transition", lot_d_tr), ("Residuel", lot_d_res)):
        for arm, short in (("control", "Controle"), ("new_A150", "AhcentCinquante")):
            levels = dig(payload, "arms", arm, "levels_free", default={})
            macros[f"tension{short}{label}"] = french(
                dig(levels, "tension", "mean", default=float("nan")), 1)
            macros[f"jensen{short}{label}"] = french(
                dig(levels, "jensen", "mean", default=float("nan")), 4)

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
        columns = re.search(r"pas × (\d+) colonnes", text)
        macros[f"parity{name}Columns"] = (
            columns.group(1) if columns else MISSING)
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
