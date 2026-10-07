"""Tension du système : l'écart entre l'échelle autarcique et l'échelle réelle.

Motivation
----------
Une entité isolée --- sans marché, sans dette --- a un capital d'équilibre
exact. Chaque pas, son capital devient $(K + A K^{\\gamma})(1-\\delta)$ ; le
point fixe est

    K_aut = [A (1 - delta) / delta]^{1 / (1 - gamma)}.

C'est une échelle de référence purement paramétrique : elle ne dépend ni de
la population, ni du crédit, ni de l'histoire du run.

En face, on veut l'échelle à laquelle le système tourne *réellement*. On la
définit par la production : le **capital équivalent** K_eq est le capital
qu'auraient toutes les entités d'un groupe technologique si, à production
agrégée et effectif identiques, elles étaient toutes au même capital :

    prod = n * A * K_eq^gamma      =>     K_eq = (prod / (n A))^{1/gamma}.

La **tension** est le rapport

    T = K_aut / K_eq.

T = 1 : le système tourne à son échelle autarcique. T > 1 : il tourne
*en dessous*, le capital y est maintenu bas par tout ce que l'autarcie
ignore --- le service des intérêts, la mortalité, le renouvellement par des
naissances petites. T < 1 : le système porte plus de capital que ce que la
technologie seule soutiendrait.

Trois conventions, énoncées parce qu'elles ne sont pas neutres
--------------------------------------------------------------
1. **K_aut ignore le service des intérêts.** C'est sa définition : l'échelle
   autarcique est celle d'une entité sans marché. La tension mesure donc
   exactement l'effet cumulé de tout ce qui n'est pas la technologie.
2. **K_eq n'est pas le capital moyen.** $K^{\\gamma}$ est concave, donc par
   Jensen la moyenne des productions est inférieure à la production de la
   moyenne : K_eq <= K_moyen, avec égalité seulement si tous les capitaux
   sont égaux. Le rapport `jensen = K_eq / K_moyen` est donc une mesure
   d'inégalité interne au groupe, et il est rapporté à côté de la tension.
3. **Le calcul est fait par groupe technologique**, seul niveau où A et
   gamma sont bien définis. L'agrégat d'un run à technologies multiples est
   la moyenne des tensions pondérée par la production, convention explicite.

Les colonnes sont produites à partir de `tech_series.csv` et `series.csv`,
donc calculables a posteriori sur tout run déjà terminé sans le relancer.
"""

from __future__ import annotations

import csv
from pathlib import Path

TENSION_COLUMNS = (
    "t", "tech", "A", "gamma", "n_alive", "n_ref", "K", "prod",
    "K_mean", "K_eq", "K_aut", "tension", "jensen", "basis",
)
AGGREGATE_COLUMNS = (
    "t", "pop", "prod_tot", "K_tot", "K_mean", "K_eq", "K_aut", "tension",
    "jensen", "basis",
)

#: Base de calcul de l'effectif producteur, reportée dans la colonne `basis`.
#:
#: ``prod``       — `tech_series` porte `n_prod`/`K_prod`, l'effectif et le
#:                  capital à l'instant exact de la production. Exact. Le
#:                  moteur v1 ne les émet PAS (il n'a pas été modifié) :
#:                  cette branche est le point d'accroche de la v2, qui doit
#:                  les enregistrer — voir ROADMAP §2.1.
#: ``deaths``     — run antérieur à ces colonnes, mais une seule technologie
#:                  vivante au pas considéré : l'effectif producteur est
#:                  reconstitué exactement par `n_alive + deaths`. K_mean
#:                  reste celui de fin de pas, donc l'écart de Jensen est
#:                  approché.
#: ``deaths_pro`` — plusieurs technologies vivantes : le total des morts est
#:                  connu mais pas sa répartition entre groupes, il est donc
#:                  imputé au prorata de l'effectif. L'erreur est bornée par
#:                  le nombre de morts du pas (≈ 30) et ne peut déplacer
#:                  qu'un groupe minoritaire ; sur les bras `fraction`, le
#:                  groupe traité pèse moins de 2 % de la production.
#: ``survivors``  — aucune des deux : l'effectif de fin de pas est utilisé,
#:                  ce qui SURESTIME K_eq (donc sous-estime la tension) de
#:                  l'ordre de 5 % au régime observé. À éviter : c'est un
#:                  biais systématique, pas du bruit.
BASES = ("prod", "deaths", "deaths_pro", "survivors")


def autarkic_scale(A: float, gamma: float, delta: float) -> float:
    """Point fixe du capital d'une entité isolée : (K + A K^g)(1-d) = K."""
    if delta <= 0.0 or A <= 0.0 or not 0.0 < gamma < 1.0:
        return float("nan")
    return (A * (1.0 - delta) / delta) ** (1.0 / (1.0 - gamma))


def equivalent_capital(prod: float, n_alive: float, A: float, gamma: float) -> float:
    """Capital qui reproduirait `prod` si les `n_alive` entités étaient égales."""
    if prod <= 0.0 or n_alive <= 0 or A <= 0.0 or gamma <= 0.0:
        return float("nan")
    return (prod / (n_alive * A)) ** (1.0 / gamma)


def _finite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))


def tension_rows(
    tech_rows: list[dict], delta: float, deaths: dict[int, int] | None = None
) -> list[dict]:
    """Une ligne par (pas, technologie vivante).

    `deaths` (morts par pas, lu dans `series.csv`) sert uniquement à
    reconstituer l'effectif producteur des runs antérieurs aux colonnes
    `n_prod`/`K_prod`, et seulement lorsqu'une seule technologie est vivante
    au pas considéré — sinon on ne saurait pas à quel groupe imputer les
    morts. Voir `BASES`.
    """
    per_step: dict[int, int] = {}
    alive_step: dict[int, int] = {}
    for row in tech_rows:
        step = int(row["t"])
        per_step[step] = per_step.get(step, 0) + 1
        alive_step[step] = alive_step.get(step, 0) + int(float(row["n_alive"]))

    out: list[dict] = []
    for row in tech_rows:
        step = int(row["t"])
        n_alive = int(float(row["n_alive"]))
        A = float(row["A"])
        gamma = float(row["gamma"])
        prod = float(row["prod"])
        capital = float(row["K"])

        if row.get("n_prod") not in (None, ""):
            basis = "prod"
            n_ref = float(row["n_prod"])
            capital_ref = float(row["K_prod"])
        elif deaths is not None and step in deaths:
            total = alive_step[step]
            share = n_alive / total if total else 0.0
            basis = "deaths" if per_step[step] == 1 else "deaths_pro"
            n_ref = n_alive + deaths[step] * share
            capital_ref = capital
        else:
            basis = "survivors"
            n_ref = n_alive
            capital_ref = capital

        K_eq = equivalent_capital(prod, n_ref, A, gamma)
        K_aut = autarkic_scale(A, gamma, delta)
        K_mean = capital_ref / n_ref if n_ref > 0 else float("nan")
        out.append(
            {
                "t": step,
                "tech": int(row["tech"]),
                "A": A,
                "gamma": gamma,
                "n_alive": n_alive,
                "n_ref": n_ref,
                "K": capital,
                "prod": prod,
                "K_mean": K_mean,
                "K_eq": K_eq,
                "K_aut": K_aut,
                "tension": K_aut / K_eq if _finite(K_eq) and K_eq > 0 else float("nan"),
                "jensen": K_eq / K_mean if _finite(K_eq) and K_mean > 0 else float("nan"),
                "basis": basis,
            }
        )
    return out


def aggregate_rows(rows: list[dict]) -> list[dict]:
    """Agrégat par pas : moyenne pondérée par la production (convention §3)."""
    by_step: dict[int, list[dict]] = {}
    for row in rows:
        by_step.setdefault(row["t"], []).append(row)
    out: list[dict] = []
    for step in sorted(by_step):
        group = [row for row in by_step[step] if _finite(row["tension"])]
        weight = sum(row["prod"] for row in group)
        pop = sum(row["n_alive"] for row in by_step[step])
        capital = sum(row["K"] for row in by_step[step])
        production = sum(row["prod"] for row in by_step[step])
        if not group or weight <= 0:
            continue

        def weighted(key: str) -> float:
            return sum(row["prod"] * row[key] for row in group) / weight

        n_ref = sum(row["n_ref"] for row in by_step[step])
        capital_ref = sum(row["K_mean"] * row["n_ref"] for row in by_step[step])
        out.append(
            {
                "t": step,
                "pop": pop,
                "prod_tot": production,
                "K_tot": capital,
                "K_mean": capital_ref / n_ref if n_ref else float("nan"),
                "K_eq": weighted("K_eq"),
                "K_aut": weighted("K_aut"),
                "tension": weighted("tension"),
                "jensen": weighted("jensen"),
                "basis": group[0]["basis"],
            }
        )
    return out


# --------------------------------------------------------------------------
# Entrées/sorties
# --------------------------------------------------------------------------
def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, columns, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        writer.writerows(rows)


def write_tension(directory: str | Path, delta: float) -> Path | None:
    """Écrit `tension.csv` et `tension_agg.csv` dans un dossier de run.

    Lit `tech_series.csv`. Retourne None si le run n'en a pas (aucune
    technologie enregistrée, par exemple un run de zéro pas).
    """
    directory = Path(directory)
    tech_rows = _read_csv(directory / "tech_series.csv")
    if not tech_rows:
        return None
    deaths = {
        int(row["t"]): int(float(row["deaths"]))
        for row in _read_csv(directory / "series.csv")
    }
    rows = tension_rows(tech_rows, delta, deaths or None)
    _write_csv(directory / "tension.csv", TENSION_COLUMNS, rows)
    _write_csv(directory / "tension_agg.csv", AGGREGATE_COLUMNS, aggregate_rows(rows))
    return directory / "tension.csv"
