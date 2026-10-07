"""Lot B — décomposition du rebond en agrégats, et LA PORTE du lot.

Ce que ce script mesure, et pourquoi
------------------------------------
Le plan §3.1 pose une prédiction AVANT toute mesure. Elle s'écrit en trois
maillons, tous établis par des lignées antérieures :

    pop_stationnaire = λ / (morts par entité et par pas)      (loi de Little, M4B)
    morts par entité ∝ rotation^a                             (v2 : a = 1,260 ; v1 : a = 1,337)
    rotation = ρ · Ḡ                                          (v2, exact en régime homogène)

d'où, à ρ fixé,

    dln(Ḡ)/dln(A)  =  −dln(pop)/dln(A) / a  =  0,7043 / a  ∈  [0,527 ; 0,559]

la borne basse pour a = 1,337, la haute pour a = 1,260.

**C'est la porte du lot B**, et elle a trois issues, toutes informatives :
dans la bande, elle DISCRIMINE entre les deux exposants — ce qu'aucun des
deux programmes précédents ne pouvait faire ; hors de la bande, c'est la
chaîne Gini → rotation → mortalité → population qui est en défaut ; et si Ḡ
ne répond pas du tout à A, la contraction de population vient d'ailleurs —
le candidat étant l'échelle K0, que le bras compensé est là pour détecter.

Ḡ est lu sur `market_stats.csv` (sonde `record_market_stats`), JAMAIS déduit
de la rotation : le déduire referait une identité.

Ce que le script produit
------------------------
- `lotB_windows.csv`   : une ligne par run et par fenêtre, les moyennes brutes ;
- `lotB_paired.csv`    : une ligne par graine, par bras et par grandeur, le
                         rapport apparié traité/contrôle et son logarithme ;
- `lotB_elasticities.csv` : une ligne par bras et par grandeur, élasticité
                         moyenne, erreur-type, intervalle de Student à 11 ddl ;
- `lotB_gate.json`     : la porte, l'identité du §3.1, les exposants `a`
                         mesurés bras par bras, et le contrôle de stationnarité.

    python3 scripts/decomposition.py [--arms-dir results/campaign/arms/free]
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

T0 = 2000
WINDOW = 2000
#: Les deux fenêtres du protocole (§6.1). La transition n'est PAS
#: stationnaire et n'est jamais lue comme un niveau.
WINDOWS = {
    "transition": (T0, T0 + 200),
    "residuel": (T0 + 1000, T0 + WINDOW),
}
#: Student à 11 degrés de liberté (12 graines appariées).
T_CRITICAL = {0.05: 2.201, 0.01: 3.106}
GAMMA = 0.5
#: Le levier de tous les bras de ce lot : A passe de 1,0 à 1,5.
LOG_A = math.log(1.5)

#: Bande prédite pour dln(Ḡ)/dlnA, écrite dans le plan avant mesure.
PREDICTION = {"a_v1": 1.337, "a_v2": 1.260, "dln_pop_dlnA": -0.7043}
PREDICTED_BAND = (
    -PREDICTION["dln_pop_dlnA"] / PREDICTION["a_v1"],
    -PREDICTION["dln_pop_dlnA"] / PREDICTION["a_v2"],
)


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def window_mean(rows: list[dict], column: str, t_min: float, t_max: float) -> float:
    total = 0.0
    count = 0
    for row in rows:
        t = float(row["t"])
        if t_min < t <= t_max:
            total += float(row[column])
            count += 1
    return total / count if count else float("nan")


def quarter_ratio(rows: list[dict], column: str, t_min: float, t_max: float) -> float:
    """Rapport du dernier quart au premier quart de la fenêtre (§6.2).

    Le contrôle de stationnarité de v2 : une bande fixe [0,99 ; 1,01] sur ce
    rapport rejetait 11 des 12 graines du CONTRÔLE, c'est-à-dire un bras sans
    intervention — elle ne mesurait que la longueur de la fenêtre. Le rapport
    est donc rendu tel quel, et testé par un Student sur sa moyenne.
    """
    span = (t_max - t_min) / 4.0
    first = window_mean(rows, column, t_min, t_min + span)
    last = window_mean(rows, column, t_max - span, t_max)
    return last / first if first else float("nan")


def run_measures(directory: Path, t_min: float, t_max: float) -> dict:
    """Les grandeurs d'un run sur une fenêtre. Une seule lecture par fichier."""
    series = read_csv(directory / "series.csv")
    tension = read_csv(directory / "tension_agg.csv")
    market_path = directory / "market_stats.csv"
    market = read_csv(market_path) if market_path.exists() else []

    pop = window_mean(series, "pop", t_min, t_max)
    deaths = window_mean(series, "deaths", t_min, t_max)
    capital = window_mean(series, "K_tot", t_min, t_max)
    volume = window_mean(series, "loan_volume", t_min, t_max)
    measures = {
        "prod_tot": window_mean(series, "prod_tot", t_min, t_max),
        "pop": pop,
        "K_tot": capital,
        "nw_tot": window_mean(series, "nw_tot", t_min, t_max),
        "loan_volume": volume,
        "n_loans": window_mean(series, "n_loans", t_min, t_max),
        "interest_paid": window_mean(series, "interest_paid", t_min, t_max),
        "deaths": deaths,
        "n_creditors": window_mean(series, "n_creditors", t_min, t_max),
        "K_share_creditors": window_mean(series, "K_share_creditors", t_min, t_max),
        "n_prod": window_mean(tension, "n_prod", t_min, t_max),
        "K_eq": window_mean(tension, "K_eq", t_min, t_max),
        "K_mean": window_mean(tension, "K_mean", t_min, t_max),
        "tension": window_mean(tension, "tension", t_min, t_max),
        "jensen": window_mean(tension, "jensen", t_min, t_max),
        # Grandeurs DÉRIVÉES, définies ici une fois pour toutes :
        # - rotation : le volume de prêts conclus rapporté au capital (§3.1) ;
        # - mortalité : morts par entité vivante et par pas, ce que la loi de
        #   Little relie à l'effectif stationnaire ;
        # - production par entité productrice, l'autre moitié de la découpe.
        "rotation": volume / capital if capital else float("nan"),
        "mortality": deaths / pop if pop else float("nan"),
        "quarter_ratio_prod": quarter_ratio(series, "prod_tot", t_min, t_max),
        "quarter_ratio_pop": quarter_ratio(series, "pop", t_min, t_max),
    }
    measures["prod_per_prod"] = (
        measures["prod_tot"] / measures["n_prod"] if measures["n_prod"] else float("nan")
    )
    if market:
        # Ḡ MESURÉ, et non déduit de la rotation (§3.1). `gini_before` est le
        # Gini du bassin de marché juste avant la phase d'appariement.
        measures["gini"] = window_mean(market, "gini_before", t_min, t_max)
        measures["gini_after"] = window_mean(market, "gini_after", t_min, t_max)
        measures["mkt_pool"] = window_mean(market, "pool", t_min, t_max)
    else:
        measures["gini"] = float("nan")
        measures["gini_after"] = float("nan")
        measures["mkt_pool"] = float("nan")
    return measures


def student(values: list[float]) -> dict:
    """Moyenne, erreur-type et demi-intervalle à 5 % d'une série appariée."""
    clean = [value for value in values if value == value]
    n = len(clean)
    if n == 0:
        return {"n": 0, "mean": float("nan"), "se": float("nan"), "ci95": float("nan")}
    mean = sum(clean) / n
    if n < 2:
        return {"n": n, "mean": mean, "se": float("nan"), "ci95": float("nan")}
    variance = sum((value - mean) ** 2 for value in clean) / (n - 1)
    se = math.sqrt(variance / n)
    return {"n": n, "mean": mean, "se": se, "ci95": T_CRITICAL[0.05] * se}


QUANTITIES = (
    "prod_tot", "pop", "n_prod", "prod_per_prod", "K_tot", "K_eq", "K_mean",
    "nw_tot", "loan_volume", "n_loans", "rotation", "mortality", "deaths",
    "gini", "gini_after", "interest_paid", "n_creditors", "mkt_pool", "tension",
)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arms-dir", type=Path,
                        default=ROOT / "results" / "campaign" / "arms" / "free")
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "analysis")
    args = parser.parse_args(argv[1:])

    arms = sorted(path.name for path in args.arms_dir.iterdir() if path.is_dir())
    assert "control" in arms, f"aucun bras `control` dans {args.arms_dir}"
    seeds = sorted(
        int(path.name[4:])
        for path in (args.arms_dir / "control").iterdir()
        if path.is_dir() and path.name.startswith("seed")
    )
    args.out.mkdir(parents=True, exist_ok=True)

    # 1. Les moyennes de fenêtre, brutes.
    windows: dict[tuple[str, str, int], dict] = {}
    flat = []
    for arm in arms:
        for seed in seeds:
            directory = args.arms_dir / arm / f"seed{seed}"
            if not (directory / "series.csv").exists():
                continue
            for name, (t_min, t_max) in WINDOWS.items():
                measures = run_measures(directory, t_min, t_max)
                windows[(arm, name, seed)] = measures
                flat.append({"arm": arm, "window": name, "seed": seed, **measures})
    with open(args.out / "lotB_windows.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat[0]))
        writer.writeheader()
        writer.writerows(flat)

    # 2. Les rapports appariés, graine par graine.
    paired_rows = []
    elasticities: dict[tuple[str, str, str], dict] = {}
    for arm in arms:
        if arm == "control":
            continue
        for name in WINDOWS:
            for quantity in QUANTITIES:
                logs = []
                for seed in seeds:
                    treated = windows.get((arm, name, seed))
                    control = windows.get(("control", name, seed))
                    if treated is None or control is None:
                        continue
                    a, b = treated[quantity], control[quantity]
                    if not (a == a and b == b) or a <= 0 or b <= 0:
                        continue
                    ratio = a / b
                    logs.append(math.log(ratio))
                    paired_rows.append({
                        "arm": arm, "window": name, "quantity": quantity, "seed": seed,
                        "treated": a, "control": b, "ratio": ratio,
                        "elasticity": math.log(ratio) / LOG_A,
                    })
                statistics = student([value / LOG_A for value in logs])
                elasticities[(arm, name, quantity)] = statistics
    with open(args.out / "lotB_paired.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(paired_rows[0]))
        writer.writeheader()
        writer.writerows(paired_rows)

    with open(args.out / "lotB_elasticities.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["arm", "window", "quantity", "n", "mean", "se", "ci95"]
        )
        writer.writeheader()
        for (arm, name, quantity), statistics in sorted(elasticities.items()):
            writer.writerow({"arm": arm, "window": name, "quantity": quantity, **statistics})

    # 3. LA PORTE, sur le bras de référence du rebond.
    gate_arm = "all_A150"
    residual = "residuel"
    gini = elasticities[(gate_arm, residual, "gini")]
    pop = elasticities[(gate_arm, residual, "pop")]
    n_prod = elasticities[(gate_arm, residual, "n_prod")]
    K_eq = elasticities[(gate_arm, residual, "K_eq")]
    prod = elasticities[(gate_arm, residual, "prod_tot")]
    rotation = elasticities[(gate_arm, residual, "rotation")]
    mortality = elasticities[(gate_arm, residual, "mortality")]

    low, high = PREDICTED_BAND
    inside = low <= gini["mean"] <= high
    # La bande REFAITE avec l'élasticité de population mesurée ici, plutôt
    # qu'avec le 0,7043 de v2 : si les deux bandes diffèrent, c'est que le
    # bras ne reproduit pas v2, et il faut le savoir avant de conclure.
    remade = (
        -pop["mean"] / PREDICTION["a_v1"],
        -pop["mean"] / PREDICTION["a_v2"],
    )
    # L'exposant `a` que ces données impliquent, si la chaîne tient.
    implied_a = -pop["mean"] / gini["mean"] if gini["mean"] else float("nan")

    # 4. `a` mesuré bras par bras, en CONTRASTE APPARIÉ et non en régression
    #    groupée (piège §14.2 : un balayage à un levier autour d'un point
    #    unique rend un R² qui n'est que la droite joignant les lignes de base).
    a_by_arm = {}
    for arm in arms:
        if arm == "control":
            continue
        ratios = []
        for seed in seeds:
            treated = windows.get((arm, residual, seed))
            control = windows.get(("control", residual, seed))
            if treated is None or control is None:
                continue
            dm = math.log(treated["mortality"] / control["mortality"])
            dr = math.log(treated["rotation"] / control["rotation"])
            if abs(dr) > 1e-6:
                ratios.append(dm / dr)
        a_by_arm[arm] = student(ratios)

    # 5. Contrôle de stationnarité (§6.2) : Student sur le rapport de quarts.
    stationarity = {}
    for arm in arms:
        for column in ("quarter_ratio_prod", "quarter_ratio_pop"):
            values = [
                windows[(arm, residual, seed)][column]
                for seed in seeds if (arm, residual, seed) in windows
            ]
            statistics = student(values)
            statistics["t_vs_one"] = (
                (statistics["mean"] - 1.0) / statistics["se"] if statistics["se"] else float("nan")
            )
            statistics["range"] = [min(values), max(values)] if values else []
            stationarity[f"{arm}/{column}"] = statistics

    gate = {
        "seeds": seeds,
        "arms": arms,
        "window": WINDOWS[residual],
        "prediction": {
            "band": [low, high],
            "source": "plan §3.1, écrite avant mesure",
            "band_remade_with_measured_pop": list(remade),
        },
        "measured": {
            "dln_gini_dlnA": gini,
            "dln_pop_dlnA": pop,
            "dln_n_prod_dlnA": n_prod,
            "dln_K_eq_dlnA": K_eq,
            "epsilon_prod_tot": prod,
            "dln_rotation_dlnA": rotation,
            "dln_mortality_dlnA": mortality,
        },
        "verdict": {
            "gini_in_band": inside,
            "implied_a": implied_a,
            # « Dans la bande » ou « hors » est une lecture binaire d'un
            # nombre continu : ce qui compte est la DISTANCE à chaque borne,
            # en unités d'incertitude de la mesure. Une valeur qui manque une
            # borne d'un centième d'erreur-type ne la contredit pas.
            "distance_to_a_v1_bound_in_ci": (
                (gini["mean"] - low) / gini["ci95"] if gini["ci95"] else float("nan")
            ),
            "distance_to_a_v2_bound_in_ci": (
                (gini["mean"] - high) / gini["ci95"] if gini["ci95"] else float("nan")
            ),
            "closer_to": (
                "a_v2 (1,260)"
                if abs(implied_a - PREDICTION["a_v2"]) < abs(implied_a - PREDICTION["a_v1"])
                else "a_v1 (1,337)"
            ),
        },
        # Le premier maillon de la chaîne, VÉRIFIÉ et non supposé : la
        # rotation est lue sur `series.csv` (volume/K_tot) et Ḡ sur
        # `market_stats.csv` (Gini du bassin avant appariement). Ce sont deux
        # fichiers différents ; leur accord mesure `rotation = ρ·Ḡ`.
        "chain_link_rotation_equals_rho_gini": {
            "dln_rotation": rotation["mean"],
            "dln_gini": gini["mean"],
            "difference": rotation["mean"] - gini["mean"],
        },
        # Le maillon de Little, qui est une IDENTITÉ à l'état stationnaire :
        # les morts par pas y valent λ, donc mortalité = λ/pop et
        # dln(mortalité) = −dln(pop) par construction. Le rapporter comme une
        # vérification serait malhonnête ; on le rapporte comme un contrôle
        # de stationnarité déguisé — s'il s'écarte, c'est que la fenêtre
        # n'est pas stationnaire.
        "little_identity": {
            "dln_mortality": mortality["mean"],
            "minus_dln_pop": -pop["mean"],
            "difference": mortality["mean"] + pop["mean"],
        },
        # L'identité de définition de K_eq (§3.1). Elle NE PEUT PAS être
        # fausse : elle ne confirme rien, elle sépare l'effectif de l'échelle.
        "identity": {
            "sum": n_prod["mean"] + 1.0 + GAMMA * K_eq["mean"],
            "epsilon_measured": prod["mean"],
            "residual": n_prod["mean"] + 1.0 + GAMMA * K_eq["mean"] - prod["mean"],
        },
        "a_by_arm": {arm: statistics for arm, statistics in a_by_arm.items()},
        "stationarity": stationarity,
    }
    (args.out / "lotB_gate.json").write_text(
        json.dumps(gate, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"# bras : {', '.join(arms)} ; graines : {len(seeds)}")
    print(f"# fenêtre résiduelle ]{WINDOWS[residual][0]}, {WINDOWS[residual][1]}]")
    print()
    verdict = gate["verdict"]
    print(f"  PORTE   dln(Ḡ)/dlnA = {gini['mean']:+.4f} ± {gini['ci95']:.4f} "
          f"(bande prédite [{low:.4f} ; {high:.4f}])")
    print(f"          borne a = 1,337 : à {verdict['distance_to_a_v1_bound_in_ci']:+.2f} "
          f"demi-intervalle ; borne a = 1,260 : à "
          f"{verdict['distance_to_a_v2_bound_in_ci']:+.2f}")
    print(f"          exposant `a` impliqué : {implied_a:.3f} → {verdict['closer_to']}")
    print(f"  chaîne  rotation {rotation['mean']:+.4f} contre Ḡ {gini['mean']:+.4f} "
          f"(deux fichiers différents, écart "
          f"{gate['chain_link_rotation_equals_rho_gini']['difference']:+.1e})")
    print(f"  Little  dln(mortalité) {mortality['mean']:+.4f} contre −dln(pop) "
          f"{-pop['mean']:+.4f} — IDENTITÉ à l'état stationnaire, écart "
          f"{gate['little_identity']['difference']:+.1e}")
    print()
    for label, key in (("ε (prod_tot)", "epsilon_prod_tot"), ("pop", "dln_pop_dlnA"),
                       ("n_prod", "dln_n_prod_dlnA"), ("K_eq", "dln_K_eq_dlnA"),
                       ("rotation", "dln_rotation_dlnA"), ("mortalité", "dln_mortality_dlnA")):
        statistics = gate["measured"][key]
        print(f"  {label:<14} {statistics['mean']:+.4f} ± {statistics['ci95']:.4f}")
    print(f"  identité      {gate['identity']['sum']:+.4f} contre ε = "
          f"{gate['identity']['epsilon_measured']:+.4f} "
          f"(résidu {gate['identity']['residual']:+.2e})")
    print()
    print("  exposant `a` par bras (contraste apparié, pas régression groupée) :")
    for arm, statistics in sorted(a_by_arm.items()):
        print(f"    {arm:<18} a = {statistics['mean']:+.3f} ± {statistics['ci95']:.3f} "
              f"(n={statistics['n']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
