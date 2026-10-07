"""Les quatre partitions d'entités du plan §4.5, définies UNE FOIS.

La règle, et c'est la seule : une partition est calculée sur le MÊME
instantané que la distribution qu'elle découpe. Un groupe défini sur un
instantané et appliqué à un autre ne partitionne rien — la population a
changé entre les deux.

| groupe | définition | pourquoi (source) |
|---|---|---|
| position nette | `claims − debts` > 0 / < 0 / ≈ 0 | M4B : l'inégalité est dans les bilans, pas dans le capital ; Gini NW 0,44 contre Gini K 0,07. Cycle de vie débiteur → créancier |
| technologie | `tech` | seul groupe où A et γ sont définis ; n'existe que si une portée `new` a agi |
| cohorte d'âge | déciles de `age` | M4B : l'horloge des fluctuations est démographique |
| décile de capital | déciles de `K` | raccord avec le Gini, qui pilote la rotation |

`ZERO_TOL` reprend la tolérance du moteur (`model.ZERO_TOL`) : une position
nette de 10⁻¹³ joule n'est pas une position.
"""

from __future__ import annotations

import numpy as np

__all__ = ["NET_POSITIONS", "net_position", "decile", "partitions", "shares"]

ZERO_TOL = 1e-12

NET_POSITIONS = ("debiteur", "neutre", "crediteur")


def net_position(panel: dict) -> np.ndarray:
    """Étiquette 0/1/2 par entité : débitrice nette, neutre, créancière nette."""
    net = panel["claims"] - panel["debts"]
    labels = np.full(net.shape, 1, dtype=np.int8)
    labels[net > ZERO_TOL] = 2
    labels[net < -ZERO_TOL] = 0
    return labels


def decile(values: np.ndarray) -> np.ndarray:
    """Décile (0 à 9) de chaque entité, par rang et non par valeur.

    Le rang, parce que les distributions de ce modèle sont très étalées : des
    tranches de valeur égales mettraient 99 % de la population dans la
    première. Les ex æquo sont départagés par l'ordre d'apparition, qui est
    l'ordre des identifiants — arbitraire mais reproductible.
    """
    n = values.size
    if n == 0:
        return np.empty(0, dtype=np.int8)
    order = np.argsort(values, kind="stable")
    ranks = np.empty(n, dtype=np.int64)
    ranks[order] = np.arange(n)
    return np.minimum((ranks * 10) // n, 9).astype(np.int8)


def partitions(panel: dict) -> dict[str, np.ndarray]:
    """Les quatre partitions du §4.5, sur l'instantané fourni."""
    return {
        "net_position": net_position(panel),
        "tech": panel["tech"],
        "age_decile": decile(panel["age"].astype(float)),
        "K_decile": decile(panel["K"]),
    }


def shares(panel: dict, labels: np.ndarray, quantity: str,
           levels=None) -> dict[int, float]:
    """Part d'une grandeur totale détenue par chaque groupe.

    Renvoie des PARTS, pas des niveaux : c'est ce qui permet de comparer deux
    bras dont les populations diffèrent de 25 % sans que la comparaison ne
    soit dominée par l'effectif.
    """
    values = panel[quantity]
    total = float(values.sum())
    if levels is None:
        levels = np.unique(labels)
    if total == 0.0:
        return {int(level): float("nan") for level in levels}
    return {int(level): float(values[labels == level].sum()) / total for level in levels}
