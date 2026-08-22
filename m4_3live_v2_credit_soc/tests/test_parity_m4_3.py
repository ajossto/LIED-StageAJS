"""Test §3.6 — parité bit à bit avec M4.3 dans le régime homogène.

C'est la vérification la plus large du programme : elle contrôle d'un seul
coup l'ordre des phases, la séquence EXACTE d'appels au générateur (Poisson
des naissances, normale du choc, puis le chemin rapide k=2 de
l'échantillonnage de marché), la fonction de taux, la mécanique du carnet
et le chemin (a) du noyau de principal. Aucune tolérance : l'égalité doit
être bit à bit.

La parité n'est plus exigée par le prompt (§3.6 la qualifie de « souhaitable
si simple »). Elle est conservée parce qu'elle est GRATUITE : elle découle
du routage du régime (a) sur l'identité des identifiants de technologie,
qui applique littéralement (K_ℓ - K_b)/2 — la formule de
`m4_3_credit_soc/m4_3/model.py:288-289`.

    # 500 pas (~1 min), valeur par défaut
    /home/anatole/jupyter/.venv/bin/python3 m4_3live_v2_credit_soc/tests/test_parity_m4_3.py
    # les 8000 pas du run stocké (~17 min) — la mesure citée dans les rapports
    /home/anatole/jupyter/.venv/bin/python3 m4_3live_v2_credit_soc/tests/test_parity_m4_3.py --full
"""

from __future__ import annotations

import csv
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, "/home/anatole/jupyter")

from m4_3live_v2.model import Config, Simulation  # noqa: E402
from simulation_lab.runs.storage import RunStorage  # noqa: E402

REFERENCE_RUN = "m4_3__d1__baseline__seed0"

# Les 26 colonnes que M4.3 écrit dans sa série. Toutes sont comparées : se
# limiter aux agrégats les plus lisses masquerait une divergence de cascade
# ou de comptage de marché.
COLUMNS = (
    "births", "deaths", "pop", "K_tot", "nw_tot", "prod_tot", "n_loans",
    "new_loans", "loan_volume", "interest_paid", "defaults", "roots_liquidity",
    "roots_insolvency", "roots_both", "cascade_iters", "n_avalanches",
    "max_avalanche", "claim_losses", "destroyed", "injected", "depreciated",
    "shock_gain", "mkt_pool", "mkt_rounds", "mkt_new_edges", "mkt_merges",
)


def test_bit_parity(steps: int):
    storage = RunStorage()
    metadata = storage.read_metadata(REFERENCE_RUN)
    parameters = metadata["parameters"]
    assert parameters["target_rule"] == "arithmetic", parameters["target_rule"]
    with open(os.path.join(storage.run_dir(REFERENCE_RUN), "series.csv"), newline="") as handle:
        reference = list(csv.DictReader(handle))
    assert len(reference) >= steps, f"le run de référence n'a que {len(reference)} pas"

    known = set(Config.__dataclass_fields__)
    config = Config(**{**{k: v for k, v in parameters.items() if k in known}, "T": steps})
    simulation = Simulation(config)
    started = time.time()
    simulation.run()
    elapsed = time.time() - started

    assert simulation.status == "ok", simulation.status
    assert len(simulation.series) == steps
    # L'écart pas à pas est ÉCRIT sur disque : c'est la donnée qui soutient
    # l'affirmation de parité dans les deux rapports, elle ne doit pas
    # n'exister que dans un print de terminal.
    deviations = []
    for index, row in enumerate(simulation.series):
        expected = reference[index]
        worst_column, worst = "", 0.0
        for column in COLUMNS:
            obtained = float(row[column])
            target = float(expected[column])
            gap = abs(obtained - target)
            if gap > worst:
                worst, worst_column = gap, column
            assert obtained == target, (
                f"divergence à t={index + 1}, colonne {column} : "
                f"{obtained!r} != {target!r}"
            )
        deviations.append((index + 1, worst, worst_column,
                           float(row["prod_tot"]), float(row["K_tot"])))
    output = Path("/home/anatole/jupyter/m4_3live_v2_credit_soc/results/analysis")
    output.mkdir(parents=True, exist_ok=True)
    with open(output / f"parity_deviations_{steps}.csv", "w", newline="",
              encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["t", "ecart_max_toutes_colonnes", "colonne", "prod_tot", "K_tot"])
        writer.writerows([(t, f"{d:.17g}", c, f"{p:.17g}", f"{k:.17g}")
                          for t, d, c, p, k in deviations])

    described = simulation.kernel.describe()
    assert described["n_tech"] == 1, described["n_tech"]
    counts = described["path_counts"]
    assert counts["identity"] > 0
    for path in ("same_gamma", "lut", "warm", "newton", "build"):
        assert counts[path] == 0, (path, counts[path])
    assert not simulation.book.consistency_errors(simulation.population.alive)

    print(
        f"  {steps} pas × {len(COLUMNS)} colonnes contre {REFERENCE_RUN} : "
        f"écart maximal NUL (égalité bit à bit)"
    )
    calls = f"{counts['identity']:,}".replace(",", " ")  # séparateur français
    print(
        f"  {calls} appels au noyau, tous sur le chemin identité ; "
        f"aucune autre technologie créée ; {elapsed:.0f} s"
    )
    return counts["identity"]


def main():
    full = "--full" in sys.argv
    steps = 8000 if full else 500
    print("test_parity_m4_3.py — parité bit à bit avec M4.3 (prompt §3.6)")
    if not full:
        print("  (mode court ; --full rejoue les 8000 pas cités dans les rapports)")
    test_bit_parity(steps)
    print("test_parity_m4_3.py : tout est passé.")


if __name__ == "__main__":
    main()
