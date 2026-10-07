"""Les DEUX estimateurs du rapport de branchement, et leur réconciliation
(plan M4.4 §3.2).

Le plan exige que le rapport de branchement `b` soit mesuré de deux façons
qui ne sont PAS la même fonctionnelle, et que les deux soient calculées sur
les MÊMES runs avant qu'un seul chiffre ne soit publié.

ESTIMATEUR 1 — par les racines
------------------------------
    b₁ = 1 − R/N

où `N` est le nombre de morts de la fenêtre et `R` le nombre de racines
(entités entrées en faillite sans qu'une autre faillite ne les y ait
poussées). C'est l'estimateur de M4B
(`recherche/sensibilite_m4b/scripts/lib_metrics.py:333`), donc la comparaison
inter-lignées porte sur la même quantité.

Il se lit sur `series.csv` seul : `deaths`, `roots_insolvency`,
`roots_liquidity`, `roots_both` (model.py, colonnes de `Simulation.step`).

\\fait{} Les racines sont la file INITIALE du point fixe de
`_resolve_bankruptcies` (model.py, `ledger["roots"]`), donc exactement les
entités de génération 1 : `death_iteration[e] == 1 ⟺ e ∈ roots`.

ESTIMATEUR 2 — par la descendance
---------------------------------
    b₂ = (nombre de couples parent→enfant) / N

Un couple parent→enfant est une arête de perte (source, victime) telle que
la victime meurt à la génération SUIVANTE de la même cascade :
`gen_victime == gen_source + 1`. C'est la descendance moyenne par mort, lue
sur l'arbre causal — et elle demande `loss_edges`, que le moteur v2 jetait
(plan §4.4).

POURQUOI LES DEUX DIFFÈRENT, ET CE QUE L'ÉCART MESURE
-----------------------------------------------------
Toute mort non racine a AU MOINS un parent : rien d'autre qu'une arête de
perte ne peut faire passer une valeur nette sous zéro pendant la cascade.
Donc

    nombre de couples ≥ nombre de morts non racines = N − R
    b₂ ≥ b₁

avec égalité si et seulement si chaque mort non racine a EXACTEMENT un
parent. L'écart `b₂ − b₁` est donc la mesure de la SUR-DÉTERMINATION : la
part de morts que plusieurs faillites amont suffisaient, chacune, à causer.

Une troisième convention — répartir 1/k entre les k parents — redonne
exactement b₁ et n'est donc pas un estimateur de plus : elle est fournie
sous forme de diagnostic (`mean_in_degree`, `multi_parent_share`).

Aucune fonction de ce module n'est appelée par le moteur : c'est de la
lecture de fichiers déjà écrits.
"""

from __future__ import annotations

from collections import defaultdict

__all__ = [
    "ROOT_COLUMNS",
    "branching_from_counts",
    "branching_from_series",
    "branching_from_edges",
    "reconcile",
]

#: Les trois causes racines écrites par le moteur. `both` compte UNE entité
#: (insolvable ET en défaut de liquidité), pas deux : les additionner donne
#: bien le nombre de racines.
ROOT_COLUMNS = ("roots_insolvency", "roots_liquidity", "roots_both")


def branching_from_counts(deaths: float, roots: float) -> float:
    """b₁ = 1 − racines/morts. Renvoie `nan` si la fenêtre n'a aucune mort."""
    if deaths <= 0:
        return float("nan")
    return 1.0 - roots / deaths


def branching_from_series(rows, t_min: float = None, t_max: float = None) -> dict:
    """Estimateur 1 sur une fenêtre de `series.csv`.

    La fenêtre est ]t_min, t_max] pour coller à la convention du protocole
    (§6 du plan) ; `None` ne borne pas.
    """
    deaths = 0.0
    roots = 0.0
    n_steps = 0
    for row in rows:
        t = float(row["t"])
        if t_min is not None and t <= t_min:
            continue
        if t_max is not None and t > t_max:
            continue
        n_steps += 1
        deaths += float(row["deaths"])
        roots += sum(float(row[column]) for column in ROOT_COLUMNS)
    return {
        "n_steps": n_steps,
        "deaths": deaths,
        "roots": roots,
        "root_share": roots / deaths if deaths > 0 else float("nan"),
        "b1": branching_from_counts(deaths, roots),
    }


def _is_columns(edges) -> bool:
    """Vrai si `edges` est un dictionnaire de COLONNES (`read_edges`) plutôt
    qu'une suite de lignes."""
    return hasattr(edges, "keys") and "gen_victim" in edges


def _branching_from_columns(edges, n_deaths: float, t_min, t_max) -> dict:
    """Chemin vectorisé, pour les 1,4 million d'arêtes d'un run de campagne.

    Le regroupement par victime passe par une clef entière `t·2³² + victime`
    plutôt que par un dictionnaire : une victime n'est identifiée qu'AU SEIN
    d'un pas — deux cascades de deux pas différents sont deux cascades — et
    les identifiants ne se réutilisent jamais, donc la clef est injective.
    """
    import numpy as np  # noqa: PLC0415 — dépendance du seul chemin colonnes

    t = edges["t"].astype(np.int64)
    keep = np.ones(t.shape, dtype=bool)
    if t_min is not None:
        keep &= t > t_min
    if t_max is not None:
        keep &= t <= t_max
    gen_victim = edges["gen_victim"][keep].astype(np.int64)
    gen_source = edges["gen_source"][keep].astype(np.int64)
    lethal = gen_victim > 0
    causal = gen_victim == gen_source + 1
    key = (t[keep] << np.int64(32)) + edges["victim"][keep].astype(np.int64)
    _, counts = np.unique(key[causal], return_counts=True)
    n_children = int(counts.size)
    return {
        "n_edges": int(keep.sum()),
        "n_edges_lethal": int(lethal.sum()),
        "n_pairs": int(causal.sum()),
        "n_non_roots_seen": n_children,
        "mean_in_degree": float(counts.mean()) if n_children else float("nan"),
        "multi_parent_share": float((counts > 1).mean()) if n_children else float("nan"),
        "b2": (int(causal.sum()) / n_deaths) if n_deaths > 0 else float("nan"),
    }


def branching_from_edges(edges, n_deaths: float, t_min: float = None,
                         t_max: float = None) -> dict:
    """Estimateur 2 sur les arêtes de perte, plus les diagnostics d'écart.

    `edges` : soit une suite de LIGNES (dictionnaires `t`, `source`,
    `victim`, `principal`, `gen_source`, `gen_victim`), soit un dictionnaire
    de COLONNES tel que le rend `m4_4.live.read_edges`. Les deux chemins
    calculent la même chose ; `tests/test_branching.py` les compare sur les
    mêmes données.

    `gen_victim == 0` signale une victime qui a SURVÉCU au pas : l'arête
    existe (la créance est perdue), mais elle n'engendre pas de descendance.

    `n_deaths` doit être le nombre de morts de la MÊME fenêtre, lu sur
    `series.csv` : le dénominateur des deux estimateurs est le même, sans
    quoi l'écart mesuré ne serait plus celui de la sur-détermination.
    """
    if _is_columns(edges):
        return _branching_from_columns(edges, n_deaths, t_min, t_max)
    pairs = 0
    parents_of: dict[tuple[float, int], set[int]] = defaultdict(set)
    n_edges = 0
    n_edges_lethal = 0
    for row in edges:
        t = float(row["t"])
        if t_min is not None and t <= t_min:
            continue
        if t_max is not None and t > t_max:
            continue
        n_edges += 1
        gen_victim = int(row["gen_victim"])
        if gen_victim == 0:
            continue
        n_edges_lethal += 1
        gen_source = int(row["gen_source"])
        if gen_victim == gen_source + 1:
            pairs += 1
            parents_of[(t, int(row["victim"]))].add(int(row["source"]))
    children_counts = [len(parents) for parents in parents_of.values()]
    n_children = len(children_counts)
    return {
        "n_edges": n_edges,
        "n_edges_lethal": n_edges_lethal,
        "n_pairs": pairs,
        "n_non_roots_seen": n_children,
        "mean_in_degree": (sum(children_counts) / n_children) if n_children else float("nan"),
        "multi_parent_share": (
            sum(count > 1 for count in children_counts) / n_children
        ) if n_children else float("nan"),
        "b2": (pairs / n_deaths) if n_deaths > 0 else float("nan"),
    }


def reconcile(series_rows, edge_rows, t_min: float = None, t_max: float = None) -> dict:
    """Les deux estimateurs sur la même fenêtre, plus leur écart.

    `n_non_roots_seen` (arbre causal) doit valoir `deaths − roots` (série) :
    c'est un contrôle d'intégrité, pas un résultat. S'il est faux, l'une des
    deux sources est incomplète — typiquement `record_loss_edges` armé en
    cours de run.
    """
    first = branching_from_series(series_rows, t_min, t_max)
    second = branching_from_edges(edge_rows, first["deaths"], t_min, t_max)
    expected_non_roots = first["deaths"] - first["roots"]
    return {
        **first,
        **second,
        "expected_non_roots": expected_non_roots,
        "closes": abs(second["n_non_roots_seen"] - expected_non_roots) < 0.5,
        "gap_b2_b1": second["b2"] - first["b1"],
    }
