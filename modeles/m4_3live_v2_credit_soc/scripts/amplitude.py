"""Mesure l'amplitude exacte des quatre leviers, et la persiste.

POURQUOI CE SCRIPT EXISTE. L'amplitude `m` et la part traitée `p` sont
enregistrées par le moteur au pas où l'intervention agit
(`intervention_log[-1]["amplitude"]`). `tests/test_amplitude.py` les vérifie
sur des cas dont la réponse est connue d'avance, mais un test IMPRIME ses
valeurs : il ne les écrit nulle part. Les nombres du tableau d'amplitude du
rapport étaient donc recopiés à la main depuis une sortie de test, ce qui
viole la règle du dépôt — aucun nombre du rapport ne doit être porté à la
main. Ce script les écrit dans `results/analysis/amplitude.csv`, d'où
`make_numbers.py` les reprend en macros et `make_figures.py` en figure.

Les quatre leviers sont ceux que le rapport cite, et le troisième est celui
qui justifie toute la mesure : un levier sur γ n'est PAS un cadran de
puissance, son amplitude vaut K^{Δγ} et dépend donc du capital, si bien que
la prédiction naïve « K = 1 » annonce qu'il ne fait rien.

    python3 scripts/amplitude.py        # ~20 s, aucun run de campagne
"""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent.parent))

from m4_3live_v2.model import Config, Intervention, Simulation  # noqa: E402

ANALYSIS = ROOT / "results" / "analysis"

#: Chauffe avant l'intervention. La même que celle du test, pour que les deux
#: mesurent la même chose : l'amplitude dépend du capital, donc de l'instant.
WARMUP = 200

#: (étiquette lisible, paramètre, valeur, portée, φ)
LEVERS = (
    (r"$A \times 1{,}5$, toutes", "A", 1.5, "all", None),
    (r"$A \times 1{,}25$, fraction $\varphi = 0{,}2$", "A", 1.25, "fraction", 0.2),
    (r"$\gamma : 0{,}5 \to 0{,}6$, toutes", "gamma", 0.6, "all", None),
    (r"$A \times 1{,}5$, nouvelles", "A", 1.5, "new", None),
)


def measure(param: str, value: float, scope: str, phi: float | None) -> dict:
    simulation = Simulation(Config(seed=1, T=WARMUP + 1, lam=30.0, sigma=0.01, K0=25.0))
    while simulation.t < WARMUP:
        simulation.step()
    simulation.submit(Intervention(param=param, value=value, scope=scope, phi=phi))
    simulation.step()
    entry = simulation.intervention_log[-1]
    amplitude = entry["amplitude"]
    return {
        "param": param,
        "valeur": value,
        "portee": scope,
        "phi": "" if phi is None else phi,
        "n_traitees": amplitude["n_treated"],
        "m_exact": amplitude["m_exact"],
        "m_naif_capital_unite": amplitude["m_naive_unit_capital"],
        "m_naif_K_eq": amplitude["m_naive_K_eq"],
        "p_ex_ante": amplitude["p_ex_ante"],
        "identite_E": amplitude["identity_E"],
    }


def main() -> int:
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    started = time.time()
    rows = []
    for name, param, value, scope, phi in LEVERS:
        row = {"levier": name}
        row.update(measure(param, value, scope, phi))
        rows.append(row)
        print(f"  {name} : m = {row['m_exact']:.12g}, naïve = "
              f"{row['m_naif_capital_unite']:.6f}, p = {row['p_ex_ante']:.6g}")
    target = ANALYSIS / "amplitude.csv"
    with open(target, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: (f"{v:.17g}" if isinstance(v, float) else v)
                             for k, v in row.items()})
    print(f"# {len(rows)} leviers mesurés en {time.time() - started:.0f} s "
          f"-> {target.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
