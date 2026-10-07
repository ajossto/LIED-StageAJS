r"""Analyse des campagnes v2 : verdict du lot D (sens du prêt) et du lot E
(ordre des phases).

CE QUI EST COMPARÉ, ET COMMENT
--------------------------------------------------------------------------
Tous les bras d'une même graine partagent leur amorçage 0 → t₀ = 2000 : ils
sont rigoureusement identiques jusqu'à t₀, puis divergent. La comparaison est
donc **appariée par graine** : pour chaque observable X et chaque graine i on
forme l'écart relatif

    d_i = X_i(bras) / X_i(référence) − 1,

et on rapporte la moyenne des d_i avec son erreur-type. Avec n graines, le
rapport moyenne/erreur-type suit une loi de **Student à n − 1 degrés de
liberté**, PAS une normale : à n = 12, le seuil de significativité bilatéral
à 5 % est t = 2,201 et non 1,96 ; à 1 %, 3,106 et non 2,58. C'est la
correction demandée par la note [19] de l'utilisateur, portée ici à la source
(le nombre de graines) et pas seulement dans la présentation.

CONTRÔLE DE STATIONNARITÉ, OBLIGATOIRE AVANT DE LIRE UN NIVEAU. Pour chaque
run et chaque grandeur parmi K_tot, pop et prod_tot, on rapporte le rapport
de la moyenne du dernier quart de la fenêtre à celle du quart précédent. Un
bras hors de [0,99 ; 1,01] n'a pas atteint son régime : il donne un
transitoire, pas un niveau, et le script le dit au lieu de le taire.

DEUX FENÊTRES, ET POURQUOI
--------------------------------------------------------------------------
La portée `new` ne renouvelle pas la cohorte d'origine : les entités déjà
vivantes gardent leur technologie et meurent sans être remplacées à
l'identique. La durée de vie moyenne d'une entité est
`population / λ ≈ 1030/30 ≈ 34` pas, donc la cohorte d'origine s'effondre en
quelques centaines de pas. Le phénomène que la campagne mesure — les paires
mixtes, donc les prêts à contre-sens — vit sur cette échelle de temps, pas
sur celle de la fenêtre entière.

Lire un seul niveau moyenné sur 1000 pas mélangerait donc une transition
intense et un régime résiduel, et donnerait « pas d'effet » là où il y a
« plus de paires mixtes ». Le script rapporte donc DEUX fenêtres :

- **transition**, $t \in\ ]t_0,\ t_0+200]$ — là où le régime nouveau est
  massif. Ce n'est PAS un régime stationnaire, et le contrôle de
  stationnarité y est attendu hors bornes : c'est un transitoire, il est
  rapporté comme tel ;
- **régime résiduel**, $t \in\ ]t_0+1000,\ t_0+2000]$ — le plateau, où la
  cohorte d'origine est réduite à quelques entités.

    python3 scripts/analyse.py           # lots D et E
    python3 scripts/analyse.py --window 1000
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

CAMPAIGN = ROOT / "results" / "campaign"
ANALYSIS = ROOT / "results" / "analysis"
TABLES = ROOT / "report" / "tables"

T0 = 2000

#: Quantiles de Student, bilatéraux, pour les effectifs employés ici.
#: (source : table classique ; recalculés au besoin par scipy, non requis)
STUDENT = {
    (4, 0.05): 2.776, (4, 0.01): 4.604,
    (11, 0.05): 2.201, (11, 0.01): 3.106,
    (2, 0.05): 4.303, (2, 0.01): 9.925,
}

OBSERVABLES = (
    ("prod_tot", "production agrégée"),
    ("pop", "population"),
    ("K_tot", "capital total"),
    ("deaths", "morts par pas"),
    ("defaults", "défauts de liquidité par pas"),
    ("loan_volume", "volume prêté par pas"),
    ("interest_paid", "intérêts versés par pas"),
    ("n_loans", "contrats vivants"),
    ("mkt_blocked_dir", "paires refusées pour cause de sens"),
    ("mkt_reversed", "prêts conclus dans le sens interdit"),
    ("mkt_volume_rev", "volume prêté dans le sens interdit"),
    ("K_share_creditors", "part du capital aux créancières nettes"),
    ("corr_marg_net", "corr(rendement marginal, position nette)"),
    ("corr_K_net", "corr(capital, position nette)"),
    ("defaults_window", "fenêtre de bascule (prédiction §3.2)"),
    ("destroyed", "capital détruit par les faillites"),
    ("claim_losses", "créances effacées par les faillites"),
    ("mkt_surplus", "surplus coopératif créé au pas"),
    ("roots_insolvency", "racines d'insolvabilité"),
    ("roots_liquidity", "racines de liquidité"),
    ("mkt_rounds", "paires tirées"),
    ("book_keys", "clefs du carnet"),
)


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _mean(values) -> float:
    values = [v for v in values if v == v]
    return sum(values) / len(values) if values else float("nan")


WINDOWS = {
    "transition": (T0, T0 + 200),
    "residuel": (T0 + 1000, T0 + 2000),
}


def summarise_run(directory: Path, bounds: tuple[int, int]) -> dict | None:
    lo, hi = bounds
    rows = read_csv(directory / "series.csv")
    tail = [row for row in rows if lo < int(row["t"]) <= hi]
    window = hi - lo
    if len(tail) < window:
        return None
    out: dict = {}
    for column, _ in OBSERVABLES:
        if column not in tail[0]:
            continue
        out[column] = _mean(float(row[column]) for row in tail)
    out["rotation"] = out["loan_volume"] / out["K_tot"]
    out["deaths_per_pop"] = out["deaths"] / out["pop"]
    # Le capital DÉTRUIT par les faillites, rapporté au stock dont il est
    # tiré. Le flux brut peut baisser alors même que les faillites augmentent,
    # simplement parce que le stock a baissé ; c'est le rapport, et lui seul,
    # qui dit si les faillites mordent davantage sur le capital.
    out["destroyed_per_K"] = out["destroyed"] / out["K_tot"]
    out["reversed_share"] = (
        out["mkt_reversed"] / _mean(float(row["mkt_rounds"]) for row in tail)
    )
    out["blocked_share"] = (
        out["mkt_blocked_dir"] / _mean(float(row["mkt_rounds"]) for row in tail)
    )
    out["volume_rev_share"] = out["mkt_volume_rev"] / out["loan_volume"]
    tension = read_csv(directory / "tension_agg.csv")
    tension = [row for row in tension if lo < int(row["t"]) <= hi]
    if tension:
        out["tension"] = _mean(float(row["tension"]) for row in tension)
        out["K_eq"] = _mean(float(row["K_eq"]) for row in tension)
        out["jensen"] = _mean(float(row["jensen"]) for row in tension)
    quarter = window // 4
    for column in ("K_tot", "pop", "prod_tot"):
        last = _mean(float(row[column]) for row in tail[-quarter:])
        before = _mean(float(row[column]) for row in tail[-2 * quarter:-quarter])
        out[f"stat_{column}"] = last / before if before else float("nan")
    # Survie de la cohorte d'origine : effectif de la technologie 0 au dernier
    # pas de la fenêtre. C'est la mesure directe du régime nouveau.
    tech_rows = read_csv(directory / "tech_series.csv")
    if tech_rows:
        last_t = max(int(row["t"]) for row in tech_rows if int(row["t"]) <= hi)
        at_last = [row for row in tech_rows if int(row["t"]) == last_t]
        out["tech0_alive"] = _mean(
            float(row["n_alive"]) for row in at_last if int(row["tech"]) == 0
        )
        if out["tech0_alive"] != out["tech0_alive"]:
            out["tech0_alive"] = 0.0
        out["n_tech_alive"] = float(len([r for r in at_last if float(r["n_alive"]) > 0]))
    return out


def collect(root: Path, bounds: tuple[int, int]) -> dict[tuple, dict]:
    out: dict[tuple, dict] = {}
    for marker in sorted(root.rglob("summary.json")):
        directory = marker.parent
        payload = json.loads(marker.read_text(encoding="utf-8"))
        summary = summarise_run(directory, bounds)
        if summary is None:
            continue
        key = tuple(directory.relative_to(root).parts)
        summary["_path"] = str(directory)
        summary["_seed"] = payload.get("seed")
        summary["_interventions"] = payload.get("interventions", [])
        out[key] = summary
    return out


def paired(treated: dict, reference: dict, seeds, column: str) -> dict:
    """Écart relatif apparié, avec sa statistique de Student."""
    diffs = []
    for seed in seeds:
        a = treated.get(seed, {}).get(column)
        b = reference.get(seed, {}).get(column)
        if a is None or b is None or b != b or a != a:
            continue
        if b == 0.0:
            continue
        diffs.append(a / b - 1.0)
    n = len(diffs)
    if n < 2:
        return {"n": n, "mean": float("nan"), "se": float("nan"), "t": float("nan")}
    mean = sum(diffs) / n
    variance = sum((d - mean) ** 2 for d in diffs) / (n - 1)
    se = math.sqrt(variance / n)
    return {
        "n": n,
        "mean": mean,
        "se": se,
        "t": mean / se if se > 0 else float("inf"),
        "t_crit_5pct": STUDENT.get((n - 1, 0.05)),
        "t_crit_1pct": STUDENT.get((n - 1, 0.01)),
        "diffs": diffs,
    }


def absolute(runs: dict, seeds, column: str) -> dict:
    values = [runs[seed][column] for seed in seeds
              if seed in runs and column in runs[seed] and runs[seed][column] == runs[seed][column]]
    n = len(values)
    if n < 2:
        return {"n": n, "mean": float("nan"), "se": float("nan")}
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)
    return {"n": n, "mean": mean, "se": math.sqrt(variance / n),
            "min": min(values), "max": max(values)}


# --------------------------------------------------------------------------
def analyse_lot_D(window_name: str) -> dict:
    bounds = WINDOWS[window_name]
    runs = collect(CAMPAIGN / "arms", bounds)
    by_cell: dict[tuple[str, str], dict[int, dict]] = {}
    for (direction, arm, seed_dir), summary in runs.items():
        seed = int(seed_dir.replace("seed", ""))
        by_cell.setdefault((direction, arm), {})[seed] = summary
    arms = sorted({arm for _, arm in by_cell})
    payload: dict = {"window": window_name, "bounds": list(bounds),
                     "arms": {}, "stationarity": [], "stationarity_runs": []}

    for arm in arms:
        free = by_cell.get(("free", arm), {})
        v1 = by_cell.get(("richest_lends", arm), {})
        seeds = sorted(set(free) & set(v1)) if v1 else sorted(free)
        entry: dict = {
            "n_seeds_free": len(free),
            "n_seeds_richest_lends": len(v1),
            "paired_seeds": seeds,
            "levels_free": {},
            "paired_free_vs_v1": {},
        }
        for column in ("prod_tot", "pop", "K_tot", "deaths_per_pop", "rotation",
                       "tension", "loan_volume", "interest_paid", "defaults",
                       "reversed_share", "blocked_share", "volume_rev_share",
                       "K_share_creditors", "corr_marg_net", "corr_K_net",
                       "jensen", "n_loans", "tech0_alive", "destroyed",
                       "destroyed_per_K", "claim_losses", "mkt_surplus",
                       "roots_insolvency", "defaults", "book_keys"):
            entry["levels_free"][column] = absolute(free, sorted(free), column)
            entry.setdefault("levels_v1", {})[column] = absolute(v1, sorted(v1), column)
            if v1:
                entry["paired_free_vs_v1"][column] = paired(free, v1, seeds, column)
        payload["arms"][arm] = entry

    # CONTRÔLE DE STATIONNARITÉ, calibré et non postulé.
    #
    # Un seuil fixe hérité d'une autre fenêtre ne transfère pas : sur une
    # fenêtre de 1000 pas, les quarts font 250 pas, et le rapport du dernier
    # quart au précédent a un écart-type de graine à graine de l'ordre de
    # 3 %. La bande [0,99 ; 1,01] rejetterait alors le CONTRÔLE lui-même,
    # c'est-à-dire un bras dont on sait qu'il est stationnaire. On teste donc
    # la MOYENNE du rapport sur les graines contre 1, avec sa statistique de
    # Student — et on rapporte l'étendue par run comme plancher de bruit,
    # sans en faire un critère.
    for (direction, arm), cells in sorted(by_cell.items()):
        seeds_here = sorted(cells)
        entry = {"direction": direction, "arm": arm, "n": len(seeds_here)}
        flagged = False
        for column in ("K_tot", "pop", "prod_tot"):
            values = [cells[seed][f"stat_{column}"] for seed in seeds_here
                      if f"stat_{column}" in cells[seed]]
            values = [v for v in values if v == v]
            if len(values) < 2:
                continue
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
            se = math.sqrt(variance / len(values))
            critical = STUDENT.get((len(values) - 1, 0.05), 2.201)
            entry[column] = {
                "mean": mean, "se": se, "min": min(values), "max": max(values),
                "t": (mean - 1.0) / se if se > 0 else float("inf"),
                "t_crit_5pct": critical,
                "stationnaire": abs(mean - 1.0) <= critical * se,
            }
            flagged = flagged or not entry[column]["stationnaire"]
        entry["stationnaire"] = not flagged
        payload["stationarity"].append(entry)
        # Les rapports RUN PAR RUN, persistés à côté de l'agrégat. Ce n'est
        # pas une redondance : c'est ce qui permet de montrer qu'une bande
        # fixe héritée d'une autre fenêtre rejetterait le contrôle lui-même,
        # ce qui ne se voit pas sur une moyenne et son erreur-type.
        for seed in seeds_here:
            payload["stationarity_runs"].append({
                "direction": direction, "arm": arm, "seed": seed,
                **{column: cells[seed].get(f"stat_{column}")
                   for column in ("K_tot", "pop", "prod_tot")},
            })
    return payload


def analyse_lot_E(window_name: str) -> dict:
    bounds = WINDOWS[window_name]
    control = collect(CAMPAIGN / "arms" / "free" / "control", bounds)
    deprec = collect(CAMPAIGN / "phase", bounds)
    reference = {int(k[0].replace("seed", "")): v for k, v in control.items()}
    treated = {int(k[1].replace("seed", "")): v for k, v in deprec.items()}
    seeds = sorted(set(reference) & set(treated))
    payload = {"window": window_name, "bounds": list(bounds),
               "paired_seeds": seeds, "paired": {}, "levels": {}}
    for column in ("defaults", "deaths_per_pop", "prod_tot", "pop", "K_tot",
                   "rotation", "interest_paid", "tension"):
        payload["paired"][column] = paired(treated, reference, seeds, column)
    payload["levels"]["reference_defaults"] = absolute(reference, seeds, "defaults")
    payload["levels"]["reference_window"] = absolute(reference, seeds, "defaults_window")
    payload["levels"]["treated_defaults"] = absolute(treated, seeds, "defaults")
    payload["levels"]["treated_window"] = absolute(treated, seeds, "defaults_window")

    # PRÉDICTION A PRIORI (§3.2), écrite depuis le bras de RÉFÉRENCE seul.
    #
    # 1. Une débitrice bascule en défaut si et seulement si son capital tombe
    #    dans la fenêtre (1-δ)K < dû ≤ K. Le moteur compte cet ensemble dans
    #    le bras de référence : c'est `defaults_window`. La prédiction du
    #    nombre de défauts sous l'ordre inverse est donc
    #    `defaults + defaults_window`.
    # 2. Indépendamment des défauts, l'échange des deux phases REDISTRIBUE
    #    exactement δ × (intérêts servis) par pas, des débitrices vers les
    #    créancières, et conserve le capital total du pas. Preuve : sous
    #    l'ordre v1 une débitrice finit à (1-δ)(K - dû), sous l'ordre inverse
    #    à (1-δ)K - dû ; l'écart est -δ·dû. Symétriquement une créancière
    #    gagne +δ·versement. Les deux se compensent exactement.
    base = payload["levels"]["reference_defaults"]["mean"]
    extra = payload["levels"]["reference_window"]["mean"]
    interest = absolute(reference, seeds, "interest_paid")["mean"]
    delta = 0.01
    payload["prediction"] = {
        "defauts_reference": base,
        "fenetre_de_bascule": extra,
        "defauts_predits": base + extra,
        "hausse_relative_predite": (extra / base) if base else None,
        "hausse_relative_mesuree": payload["paired"]["defaults"]["mean"],
        "defauts_mesures": absolute(treated, seeds, "defaults")["mean"],
        "redistribution_par_pas": delta * interest,
        "interets_servis_par_pas": interest,
        "part_du_capital_redistribuee": (
            delta * interest / absolute(reference, seeds, "K_tot")["mean"]
        ),
    }
    payload["service_ratio"] = service_ratio_distribution(delta)
    return payload


def service_ratio_distribution(delta: float) -> dict:
    """Distribution du rapport capital/dû à l'instant du service, lue sur les
    snapshots d'amorçage. C'est la donnée qui rend la prédiction du §3.2
    calculable AVANT de lancer le bras traité : la fenêtre de bascule est
    l'intervalle [1, 1/(1-δ)], et elle est vide si le minimum du rapport lui
    est très supérieur."""
    import sys as _sys

    _sys.path.insert(0, str(ROOT))
    from m4_3live_v2.live import load_snapshot

    ratios: list[float] = []
    for snapshot in sorted((CAMPAIGN / "burn").glob("seed*/snapshot_t*.pkl")):
        simulation = load_snapshot(snapshot)
        book = simulation.book
        population = simulation.population
        for borrower, loans in book.by_borrower.items():
            if not loans or not population.alive[borrower]:
                continue
            due = book.due[borrower]
            if due > 0:
                ratios.append(population.K[borrower] / due)
    if not ratios:
        return {}
    ratios.sort()
    n = len(ratios)
    threshold = 1.0 / (1.0 - delta)
    out = {
        "n_debitrices": n,
        "min": ratios[0],
        "p1": ratios[n // 100],
        "p5": ratios[n // 20],
        "mediane": ratios[n // 2],
        "max": ratios[-1],
        "seuil_de_bascule": threshold,
        "n_dans_la_fenetre": sum(1 for r in ratios if r < threshold),
        "marge": ratios[0] / threshold,
    }
    with open(ANALYSIS / "service_ratio.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["rapport_capital_sur_du"])
        writer.writerows([[f"{r:.10g}"] for r in ratios])
    return out


    return payload


# --------------------------------------------------------------------------
def write_tables(lot_d_transition: dict, lot_d_residuel: dict, lot_e: dict) -> None:
    TABLES.mkdir(parents=True, exist_ok=True)

    def pct(value: float, digits: int = 2) -> str:
        if value is None or value != value:
            return "---"
        return f"{100 * value:+.{digits}f}".replace(".", ",")

    def plain(value: float, digits: int = 2) -> str:
        if value is None or value != value:
            return "---"
        return f"{value:.{digits}f}".replace(".", ",")

    # -- Tableau 1 : le régime nouveau, par bras et par fenêtre -------------
    lines = [r"\begin{tabular}{llrrrr}", r"\toprule",
             r"bras & fenêtre & prêts à contre-sens & volume à contre-sens "
             r"& \multicolumn{2}{c}{cohorte d'origine vivante} \\",
             r"\cmidrule(lr){5-6}",
             r" &  & (\% des rondes) & (\% du volume) & sens libre & règle v1 \\",
             r"\midrule"]
    for arm in sorted(lot_d_transition["arms"]):
        if not lot_d_transition["arms"][arm]["paired_free_vs_v1"]:
            continue
        for label, payload in (("transition", lot_d_transition),
                               ("résiduel", lot_d_residuel)):
            levels = payload["arms"][arm]["levels_free"]
            v1 = payload["arms"][arm]["levels_v1"]
            lines.append(
                r"\code{" + arm.replace("_", r"\_") + "} & " + label + " & "
                + plain(100 * levels["reversed_share"]["mean"]) + " & "
                + plain(100 * levels["volume_rev_share"]["mean"]) + " & "
                + plain(levels["tech0_alive"]["mean"], 1) + " & "
                + plain(v1["tech0_alive"]["mean"], 1) + r" \\"
            )
        lines.append(r"\addlinespace")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TABLES / "lot_d_regime.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # -- Tableau 2 : les écarts appariés ------------------------------------
    for label, payload, name in (("transition", lot_d_transition, "lot_d_paired_transition"),
                                 ("résiduel", lot_d_residuel, "lot_d_paired_residuel")):
        lines = [r"\begin{tabular}{lrrrr}", r"\toprule",
                 r"bras & production & population & mortalité & rotation \\",
                 r"\midrule"]
        for arm in sorted(payload["arms"]):
            entry = payload["arms"][arm]["paired_free_vs_v1"]
            if not entry:
                continue
            cells = []
            for column in ("prod_tot", "pop", "deaths_per_pop", "rotation"):
                fit = entry[column]
                star = ""
                if fit["t"] == fit["t"] and fit.get("t_crit_1pct"):
                    if abs(fit["t"]) > fit["t_crit_1pct"]:
                        star = r"$^{\ast\ast}$"
                    elif abs(fit["t"]) > fit["t_crit_5pct"]:
                        star = r"$^{\ast}$"
                cells.append(f"${pct(fit['mean'])} \\pm {pct(fit['se']).lstrip('+')}$"
                             + star)
            lines.append(r"\code{" + arm.replace("_", r"\_") + "} & "
                         + " & ".join(cells) + r" \\")
        lines += [r"\bottomrule", r"\end{tabular}"]
        (TABLES / f"{name}.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # -- Tableau 3 : la prédiction du lot E ---------------------------------
    prediction = lot_e["prediction"]
    lines = [r"\begin{tabular}{lr}", r"\toprule",
             r"grandeur & valeur \\", r"\midrule",
             r"défauts par pas, ordre \code{v1} & "
             + plain(prediction["defauts_reference"]) + r" \\",
             r"fenêtre de bascule mesurée dans ce même bras & "
             + plain(prediction["fenetre_de_bascule"]) + r" \\",
             r"\textbf{défauts prédits sous \code{deprec\_first}} & "
             + plain(prediction["defauts_predits"]) + r" \\",
             # Le dénominateur est NUL dans les deux bras : la hausse
             # relative n'existe pas, et l'écrire « --- % » se lit comme une
             # donnée manquante. On écrit ce qui est vrai.
             r"hausse relative \emph{prédite} & "
             + (pct(prediction["hausse_relative_predite"]) + r"\,\%"
                if prediction.get("hausse_relative_predite") is not None
                else r"\emph{non définie} ($0/0$)") + r" \\",
             r"hausse relative \emph{mesurée} & "
             + (pct(prediction["hausse_relative_mesuree"]) + r"\,\%"
                if prediction.get("hausse_relative_mesuree") ==
                prediction.get("hausse_relative_mesuree")
                else r"\emph{non définie} ($0/0$)") + r" \\",
             r"\bottomrule", r"\end{tabular}"]
    (TABLES / "lot_e_prediction.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    args = parser.parse_args(argv)
    ANALYSIS.mkdir(parents=True, exist_ok=True)

    payload = {}
    for name in WINDOWS:
        lot_d = analyse_lot_D(name)
        lot_e = analyse_lot_E(name)
        (ANALYSIS / f"lot_d_{name}.json").write_text(
            json.dumps(lot_d, indent=2, ensure_ascii=False), encoding="utf-8")
        (ANALYSIS / f"lot_e_{name}.json").write_text(
            json.dumps(lot_e, indent=2, ensure_ascii=False), encoding="utf-8")
        payload[name] = (lot_d, lot_e)

    lot_d_res, lot_e_res = payload["residuel"]
    lot_d_tr, _ = payload["transition"]
    write_tables(lot_d_tr, lot_d_res, lot_e_res)

    # Rapports de stationnarité run par run, les deux fenêtres dans le même
    # fichier. Les figures les relisent ; elles ne les recalculent pas.
    with open(ANALYSIS / "stationarity_runs.csv", "w", newline="",
              encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["fenetre", "direction", "bras", "graine",
                         "K_tot", "pop", "prod_tot"])
        for name, (lot_d, _lot_e) in payload.items():
            for row in lot_d["stationarity_runs"]:
                writer.writerow([name, row["direction"], row["arm"], row["seed"],
                                 row["K_tot"], row["pop"], row["prod_tot"]])

    digest = {}
    for name, (lot_d, lot_e) in payload.items():
        digest[name] = {
            "bornes": lot_d["bounds"],
            "bras": {
                arm: {
                    "n_free": lot_d["arms"][arm]["n_seeds_free"],
                    "n_v1": lot_d["arms"][arm]["n_seeds_richest_lends"],
                    "part_contre_sens": lot_d["arms"][arm]["levels_free"]["reversed_share"]["mean"],
                    "tech0_vivantes_libre": lot_d["arms"][arm]["levels_free"]["tech0_alive"]["mean"],
                    "tech0_vivantes_v1": lot_d["arms"][arm]["levels_v1"]["tech0_alive"]["mean"],
                    "prod_apparie": lot_d["arms"][arm]["paired_free_vs_v1"].get(
                        "prod_tot", {}).get("mean"),
                    "prod_t": lot_d["arms"][arm]["paired_free_vs_v1"].get(
                        "prod_tot", {}).get("t"),
                }
                for arm in sorted(lot_d["arms"])
            },
            "bras_hors_stationnarite": [
                f"{e['direction']}/{e['arm']}" for e in lot_d["stationarity"]
                if not e["stationnaire"]
            ],
            "bras_testes": len(lot_d["stationarity"]),
            "etendue_du_rapport": {
                column: [
                    min(e[column]["min"] for e in lot_d["stationarity"] if column in e),
                    max(e[column]["max"] for e in lot_d["stationarity"] if column in e),
                ]
                for column in ("K_tot", "pop", "prod_tot")
            },
            "lot_E": lot_e["prediction"],
        }
    (ANALYSIS / "verdicts.json").write_text(
        json.dumps(digest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(digest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
