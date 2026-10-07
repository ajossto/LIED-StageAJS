"""Tension du système : l'écart entre l'échelle autarcique et l'échelle réelle.

Ce module fait partie du MOTEUR (§4.1 du prompt v2). En v1 la tension était
un dérivé a posteriori (`m4_3live_credit_soc/scripts/tension.py`), parce que
le moteur était gelé et ne pouvait plus enregistrer l'effectif producteur ;
il fallait le reconstituer, et une colonne `basis` disait laquelle des trois
reconstructions avait servi. En v2 la mesure est prise à l'instant exact de
la production : la colonne `basis` disparaît, faute d'ambiguïté à documenter.

Les trois grandeurs
-------------------
**Échelle autarcique** ``K_aut``. Une entité isolée — sans marché, sans dette
— voit son capital devenir ``(K + A K^γ)(1 − δ)`` à chaque pas. Le point fixe
de cette récurrence est

    K_aut = [A (1 − δ) / δ]^{1 / (1 − γ)}.

C'est une échelle purement paramétrique : elle ne dépend ni de la population,
ni du crédit, ni de l'histoire du run. `A` est le coefficient de production,
`γ` son exposant (0 < γ < 1), `δ` le taux de dépréciation par pas.

**Capital équivalent** ``K_eq``. L'échelle à laquelle le système tourne
réellement, définie par la production : c'est le capital qu'auraient toutes
les entités d'un groupe technologique si, à production agrégée et effectif
producteur identiques, elles étaient toutes au même capital :

    prod = n_prod · A · K_eq^γ      ⇒     K_eq = (prod / (n_prod · A))^{1/γ}.

**Tension** ``T = K_aut / K_eq``. T = 1 : le système tourne à son échelle
autarcique. T > 1 : il tourne *en dessous* — le capital y est maintenu bas
par tout ce que l'autarcie ignore (service des intérêts, mortalité,
renouvellement par des naissances petites). T < 1 : il porte plus de capital
que la technologie seule ne soutiendrait.

Trois conventions, énoncées parce qu'elles ne sont pas neutres
--------------------------------------------------------------
1. **K_aut ignore le service des intérêts.** C'est sa définition. La tension
   mesure donc exactement l'effet cumulé de tout ce qui n'est pas la
   technologie.
2. **K_eq n'est pas le capital moyen.** ``K^γ`` est concave, donc par Jensen
   la moyenne des productions est inférieure à la production de la moyenne :
   K_eq ≤ K_moyen, avec égalité seulement si tous les capitaux sont égaux. Le
   rapport ``jensen = K_eq / K_moyen`` est donc une mesure d'inégalité interne
   au groupe, rapportée à côté de la tension. En v2 il est EXACT : les deux
   termes sont pris au même instant du pas, celui de la production, alors
   qu'en v1 le numérateur venait de la production et le dénominateur du
   capital de fin de pas.
3. **Le calcul est fait par groupe technologique**, seul niveau où A et γ sont
   bien définis. L'agrégat d'un run à technologies multiples est la moyenne
   des tensions pondérée par la production — convention explicite, pas une
   moyenne « naturelle ».
"""

from __future__ import annotations

__all__ = [
    "TENSION_COLUMNS",
    "AGGREGATE_COLUMNS",
    "autarkic_scale",
    "equivalent_capital",
    "tension_row",
    "aggregate_rows",
]

TENSION_COLUMNS = (
    "t", "tech", "A", "gamma", "n_alive", "n_prod", "K", "K_prod", "prod",
    "K_mean", "K_eq", "K_aut", "tension", "jensen",
)
AGGREGATE_COLUMNS = (
    "t", "pop", "n_prod", "prod_tot", "K_tot", "K_mean", "K_eq", "K_aut",
    "tension", "jensen",
)

_NAN = float("nan")


def autarkic_scale(A: float, gamma: float, delta: float) -> float:
    """Point fixe du capital d'une entité isolée : (K + A K^γ)(1 − δ) = K."""
    if delta <= 0.0 or A <= 0.0 or not 0.0 < gamma < 1.0:
        return _NAN
    return (A * (1.0 - delta) / delta) ** (1.0 / (1.0 - gamma))


def equivalent_capital(prod: float, n_prod: float, A: float, gamma: float) -> float:
    """Capital qui reproduirait `prod` si les `n_prod` entités étaient égales."""
    if prod <= 0.0 or n_prod <= 0 or A <= 0.0 or gamma <= 0.0:
        return _NAN
    return (prod / (n_prod * A)) ** (1.0 / gamma)


def _finite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))


def tension_row(
    t: int,
    tech: int,
    A: float,
    gamma: float,
    delta: float,
    n_alive: int,
    n_prod: int,
    capital: float,
    capital_prod: float,
    prod: float,
) -> dict:
    """Une ligne (pas, technologie). Toutes les entrées sont EXACTES.

    `n_prod` et `capital_prod` sont l'effectif et le capital cumulé du groupe
    à l'instant de la production — c'est-à-dire après le choc multiplicatif et
    avant que la production ne soit ajoutée au capital. `n_alive` et `capital`
    sont ceux de la fin du pas, après les faillites : ils sont conservés parce
    qu'ils répondent à une autre question (« que reste-t-il ? »).
    """
    K_eq = equivalent_capital(prod, n_prod, A, gamma)
    K_aut = autarkic_scale(A, gamma, delta)
    K_mean = capital_prod / n_prod if n_prod > 0 else _NAN
    return {
        "t": t,
        "tech": tech,
        "A": A,
        "gamma": gamma,
        "n_alive": n_alive,
        "n_prod": n_prod,
        "K": capital,
        "K_prod": capital_prod,
        "prod": prod,
        "K_mean": K_mean,
        "K_eq": K_eq,
        "K_aut": K_aut,
        "tension": K_aut / K_eq if _finite(K_eq) and K_eq > 0 else _NAN,
        "jensen": K_eq / K_mean if _finite(K_eq) and K_mean > 0 else _NAN,
    }


def aggregate_rows(rows: list[dict]) -> list[dict]:
    """Agrégat par pas : moyenne pondérée par la production (convention 3)."""
    by_step: dict[int, list[dict]] = {}
    for row in rows:
        by_step.setdefault(row["t"], []).append(row)
    out: list[dict] = []
    for step in sorted(by_step):
        group = [row for row in by_step[step] if _finite(row["tension"])]
        weight = sum(row["prod"] for row in group)
        if not group or weight <= 0:
            continue

        def weighted(key: str) -> float:
            return sum(row["prod"] * row[key] for row in group) / weight

        n_prod = sum(row["n_prod"] for row in by_step[step])
        capital_prod = sum(row["K_prod"] for row in by_step[step])
        out.append(
            {
                "t": step,
                "pop": sum(row["n_alive"] for row in by_step[step]),
                "n_prod": n_prod,
                "prod_tot": sum(row["prod"] for row in by_step[step]),
                "K_tot": sum(row["K"] for row in by_step[step]),
                "K_mean": capital_prod / n_prod if n_prod else _NAN,
                "K_eq": weighted("K_eq"),
                "K_aut": weighted("K_aut"),
                "tension": weighted("tension"),
                "jensen": weighted("jensen"),
            }
        )
    return out
