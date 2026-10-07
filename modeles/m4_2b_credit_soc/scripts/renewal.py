"""Diagnostic de vitesse de renouvellement du système (demandé par l'utilisateur
le 2026-07-30, après la phase pilote) : suit, à partir du PREMIER snapshot
enregistré d'un run, la part que représentent des cohortes identifiées à ce
premier instant dans les snapshots suivants.

Deux découpages complémentaires du "premier décile", tous deux calculés :

- ``age`` : les 10% d'entités les plus JEUNES au premier snapshot (cohorte
  démographique — le découpage le plus direct pour une vitesse de
  renouvellement au sens propre) ;
- ``capital`` : les 10% d'entités les plus PAUVRES en capital K au premier
  snapshot (découpage économique usuel du "premier décile").

Pour chaque découpage, on identifie l'ensemble d'identifiants (id) présents
dans ce décile au premier snapshot, puis on mesure, à CHAQUE snapshot
ultérieur :

- la part de POPULATION que cet ensemble représente encore (survivants /
  population totale du snapshot courant) ;
- la part de CAPITAL total qu'il détient encore.

Les deux parts décroissent nécessairement (mortalité + le décile n'est plus
"marqué" comme tel dans les snapshots suivants, seule sa composition
initiale est trackée) ; le temps caractéristique de cette décroissance est
une mesure directe de la vitesse de renouvellement, complémentaire (et plus
directe) du diagnostic de stationnarité agrégée déjà utilisé
(``lib_metrics.window_series_metrics``), qui ne dit rien sur le TURNOVER
des individus.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import interest_income  # noqa: E402


def cohort_renewal_curve(directory, cut: str = "age", decile: float = 0.10) -> dict:
    """Courbe de renouvellement pour un run : identifie le décile au premier
    snapshot disponible, puis mesure sa part de population/capital à chaque
    snapshot ultérieur (y compris le premier lui-même, part=1.0 par
    construction pour la population du décile)."""
    snaps = interest_income.load_all_entity_snapshots(directory)
    if len(snaps) < 2:
        return {"available": False, "reason": "moins de 2 snapshots"}

    t0, snap0 = snaps[0]
    ids0 = snap0["id"]
    if cut == "age":
        key = snap0["age"]
        # les plus JEUNES = age le plus petit
        threshold = np.quantile(key, decile)
        cohort_mask = key <= threshold
    elif cut == "capital":
        key = snap0["K"]
        # les plus PAUVRES = K le plus petit
        threshold = np.quantile(key, decile)
        cohort_mask = key <= threshold
    else:
        raise ValueError("cut doit être 'age' ou 'capital'")

    cohort_ids = set(ids0[cohort_mask].tolist())
    n_cohort0 = len(cohort_ids)

    curve = []
    for t, snap in snaps:
        ids = snap["id"]
        K = snap["K"]
        in_cohort = np.array([entity in cohort_ids for entity in ids.tolist()])
        pop_total = len(ids)
        K_total = float(K.sum())
        pop_share = float(in_cohort.sum() / pop_total) if pop_total > 0 else float("nan")
        K_share = float(K[in_cohort].sum() / K_total) if K_total > 0 else float("nan")
        curve.append({
            "t": int(t), "n_survivors": int(in_cohort.sum()), "pop_total": int(pop_total),
            "pop_share": pop_share, "K_share": K_share,
        })

    return {
        "available": True, "cut": cut, "decile": decile, "t0": int(t0),
        "n_cohort0": n_cohort0, "curve": curve,
    }


def half_life_step(curve: list[dict], field: str = "pop_share") -> float | None:
    """Premier t où field est passé sous la moitié de sa valeur au premier
    snapshot -- estimateur grossier mais robuste du temps caractéristique de
    renouvellement, sans supposer de forme fonctionnelle (exponentielle ou
    non)."""
    if not curve:
        return None
    initial = curve[0][field]
    if not np.isfinite(initial) or initial <= 0:
        return None
    for row in curve:
        if row[field] <= 0.5 * initial:
            return row["t"] - curve[0]["t"]
    return None  # jamais retombé sous la moitié dans la fenêtre observée


def summarize_renewal(directory) -> dict:
    out = {}
    for cut in ("age", "capital"):
        result = cohort_renewal_curve(directory, cut=cut)
        if not result.get("available"):
            out[cut] = result
            continue
        out[cut] = {
            "t0": result["t0"], "n_cohort0": result["n_cohort0"],
            "half_life_pop_share_steps": half_life_step(result["curve"], "pop_share"),
            "half_life_K_share_steps": half_life_step(result["curve"], "K_share"),
            "curve_tail": result["curve"][:12],  # les ~12 premiers points pour inspection
        }
    return out


if __name__ == "__main__":
    import json
    import sys as _sys

    directory = _sys.argv[1] if len(_sys.argv) > 1 else "results/pilot_baseline_seed0"
    summary = summarize_renewal(directory)
    print(json.dumps(summary, indent=1, ensure_ascii=False))
