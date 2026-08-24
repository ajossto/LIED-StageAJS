"""Lot J — la sur-détermination des cascades est-elle une SUFFISANCE ?

Le lot D avait mesuré qu'une part importante des victimes de cascade reçoit
plusieurs chocs amont, et le rapport final en tirait une réserve explicite
(§ « ce que ce programme n'établit pas », point 4) :

    « Que plusieurs faillites amont aient atteint une même victime ne dit pas
      que chacune aurait suffi ; le vérifier demanderait de confronter chaque
      principal à la valeur nette d'avant cascade. »

C'est cette confrontation. Elle ne demande aucune campagne : les arêtes
(`loss_edges.npz`, source / victime / principal) et la table des décès
(`deaths.csv`, valeur nette AU MOMENT de la mort) suffisent, et l'encadrement
se déduit du moteur.

**L'encadrement, et pourquoi il est exact.**

Le prédicat de faillite est `net_worth < -INSOLVENCY_TOL` (`model.py:1119`).
Pour une victime `v` qui meurt à l'itération ≥ 2 d'une cascade :

- `nw_avant ≥ -tol` — sinon `v` aurait été mise dans la file INITIALE et
  serait une racine, pas une victime. C'est une borne dure du moteur, pas
  une hypothèse.
- `nw_mort = nw_avant − Σ(créances perdues) + Σ(dettes effacées)`. Le second
  terme existe : quand une créancière meurt, `_fail_one` retire aussi les
  prêts qu'elle avait CONSENTIS, ce qui efface la dette de ses débitrices.
  Ces effacements ne sont pas tracés par `loss_edges` — seules les créances
  perdues le sont.

Donc `nw_avant ≤ nw_mort + Σ(créances perdues)`, et l'arête `i` est
CERTAINEMENT suffisante dès que

    principal_i > nw_mort + Σ(créances perdues)

puisque la vraie valeur d'avant est plus basse encore. Un effacement de dette
ne peut que RENDRE la victime plus fragile au regard de ce test : le compte
obtenu est donc un **plancher** sur le taux de suffisance, jamais un plafond.

Algébriquement, pour une victime sur-déterminée le critère se lit :
*la plus grosse arête suffit à elle seule dès que le déficit final dépasse la
somme des autres chocs.*

    python3 scripts/sufficiency.py [--campaign results/campaign/arms/free]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import multiprocessing as mp
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from m4_4.live import read_edges  # noqa: E402

#: Le moteur (`model.py`). Recopié et non importé : ce script lit des runs
#: déjà écrits et ne doit pas dépendre d'un moteur qui aurait bougé depuis.
#: `tests/test_sufficiency.py` vérifie que la valeur coïncide encore.
INSOLVENCY_TOL = 1e-9

T_CRITICAL = 2.201

#: Huit cœurs, deux laissés libres.
WORKERS = 6


def load_victims(run: Path, t_min: float, t_max: float) -> dict:
    """Pour chaque victime de cascade : ses chocs entrants et sa valeur nette
    de mort. Les racines sont exclues — elles ne sont victimes de personne."""
    deaths_nw: dict[int, float] = {}
    deaths_t: dict[int, int] = {}
    cascade: set[int] = set()
    with open(run / "deaths.csv", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            time = float(row["t"])
            if time <= t_min or time > t_max:
                continue
            entity = int(row["id"])
            deaths_nw[entity] = float(row["nw"])
            deaths_t[entity] = int(row["t"])
            if row["cause"] == "cascade":
                cascade.add(entity)

    edges = read_edges(run / "loss_edges.npz")
    window = (edges["t"] > t_min) & (edges["t"] <= t_max)
    victim = edges["victim"][window]
    principal = edges["principal"][window]
    when = edges["t"][window]

    # SEULES comptent les arêtes du pas où la victime meurt.
    #
    # Une entité perd des créances tout au long de sa vie sans en mourir : sur
    # une fenêtre de mille pas, sommer toutes ses pertes reviendrait à lui
    # attribuer des chocs vieux de plusieurs centaines de pas, absorbés depuis.
    # La cascade est un point fixe DANS UN PAS ; la confrontation doit se faire
    # à l'intérieur de ce pas et nulle part ailleurs.
    death_time = np.array([deaths_t.get(int(entity), -1) for entity in victim],
                          dtype=np.int64)
    lethal = when == death_time
    victim, principal = victim[lethal], principal[lethal]

    # Regroupement par victime sans dictionnaire Python : à ~1,4 million
    # d'arêtes par run, un `defaultdict(list)` coûterait plusieurs centaines
    # de mébioctets pour rien.
    order = np.argsort(victim, kind="stable")
    victim, principal = victim[order], principal[order]
    unique, start = np.unique(victim, return_index=True)
    bounds = np.append(start, victim.size)

    rows = []
    for index, entity in enumerate(unique):
        key = int(entity)
        if key not in cascade:
            continue
        chunk = principal[bounds[index]:bounds[index + 1]]
        total = float(chunk.sum())
        largest = float(chunk.max())
        nw_death = deaths_nw[key]
        # Majorant de la valeur nette d'avant cascade (voir docstring).
        nw_before_upper = nw_death + total
        certain = int((chunk > nw_before_upper + INSOLVENCY_TOL).sum())
        rows.append((chunk.size, total, largest, nw_death, nw_before_upper, certain))
    return {"rows": rows, "n_cascade": len(cascade)}


def measure(run: Path, t_min: float, t_max: float) -> dict | None:
    data = load_victims(run, t_min, t_max)
    rows = data["rows"]
    if not rows:
        return None
    degree = np.array([row[0] for row in rows])
    total = np.array([row[1] for row in rows])
    largest = np.array([row[2] for row in rows])
    nw_death = np.array([row[3] for row in rows])
    upper = np.array([row[4] for row in rows])
    certain = np.array([row[5] for row in rows])

    multi = degree >= 2
    single = degree == 1
    n_multi = int(multi.sum())

    # Chez une victime à UNE seule arête, la suffisance est une tautologie :
    # cette arête est la cascade tout entière. Le test n'a de contenu que sur
    # les sur-déterminées, et c'est sur elles seules que le taux est rapporté.
    out = {
        "n_victimes": int(degree.size),
        "n_sur_determinees": n_multi,
        "part_sur_determinees": float(multi.mean()),
        "degre_moyen": float(degree.mean()),
        "degre_max": int(degree.max()),
        "concentration_moyenne": float((largest / total)[multi].mean()) if n_multi else float("nan"),
        # Le plancher : au moins une arête certainement suffisante.
        "plancher_suffisance": float((certain[multi] >= 1).mean()) if n_multi else float("nan"),
        # Et la forme forte : TOUTES les arêtes suffisantes, c'est-à-dire une
        # sur-détermination où chaque cause aurait effectivement suffi.
        "plancher_toutes_suffisantes": (
            float((certain[multi] == degree[multi]).mean()) if n_multi else float("nan")),
        "nb_causes_suffisantes_moyen": float(certain[multi].mean()) if n_multi else float("nan"),
        # Témoin de degré un — et ce qu'il MESURE, contre ce qu'on attendait.
        #
        # À une seule arête, l'arête EST le choc entier, donc le plancher
        # devrait valoir 1 exactement. Il vaut 0,981. L'écart n'est pas un
        # défaut du calcul : c'est l'effacement de dette pris sur le fait.
        # Dans `_solve_cascade`, la file est constituée d'abord, puis les
        # entités sont abattues une à une ; entre les deux, la mort d'une
        # CRÉANCIÈRE efface la dette de ses débitrices et peut faire remonter
        # la valeur nette d'une entité déjà condamnée au-dessus de zéro. Ces
        # victimes-là meurent avec `nw ≥ 0`, et le majorant ne peut alors rien
        # certifier — conservatisme correct, jamais fausse certification.
        #
        # Le complément à un est donc un ESTIMATEUR de l'incidence des
        # effacements, mesuré et non supposé.
        "temoin_degre_un": float((certain[single] >= 1).mean()) if single.any() else float("nan"),
        "incidence_effacement": float((nw_death >= 0.0).mean()),
        "deficit_median": float(np.median(-nw_death[multi])) if n_multi else float("nan"),
        "choc_median": float(np.median(total[multi])) if n_multi else float("nan"),
        "marge_mediane": float(np.median((largest - upper)[multi])) if n_multi else float("nan"),
    }
    # Histogramme de la marge relative `principal_max / choc_total` — la
    # figure du lot. Bornes fixes pour que les bras soient superposables.
    ratio = (largest / total)[multi] if n_multi else np.array([])
    counts, edges = np.histogram(ratio, bins=25, range=(0.0, 1.0))
    out["histogramme_concentration"] = counts.tolist()
    out["histogramme_bornes"] = edges.tolist()
    return out


def _job(payload):
    arm, run, t_min, t_max = payload
    try:
        result = measure(Path(run), t_min, t_max)
    except Exception as error:  # noqa: BLE001 — un run illisible ne doit pas tuer le lot
        print(f"  échec {run} : {error}", file=sys.stderr)
        return None
    if result is None:
        return None
    return {"arm": arm, "seed": int(Path(run).name[4:]), **result}


def student(values) -> tuple[float, float, int]:
    clean = [value for value in values if value == value and math.isfinite(value)]
    n = len(clean)
    if n < 2:
        return (clean[0] if clean else float("nan")), float("nan"), n
    mean = sum(clean) / n
    variance = sum((value - mean) ** 2 for value in clean) / (n - 1)
    return mean, T_CRITICAL * math.sqrt(variance / n), n


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path,
                        default=ROOT / "results" / "campaign" / "arms" / "free")
    parser.add_argument("--t-min", type=float, default=3000)
    parser.add_argument("--t-max", type=float, default=4000)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "analysis")
    parser.add_argument("--workers", type=int, default=WORKERS)
    args = parser.parse_args(argv[1:])

    jobs = []
    for arm_dir in sorted(args.campaign.iterdir(), key=lambda p: p.name):
        if not arm_dir.is_dir():
            continue
        for run in sorted(arm_dir.iterdir(), key=lambda p: p.name):
            if run.is_dir() and (run / "loss_edges.npz").exists():
                jobs.append((arm_dir.name, str(run), args.t_min, args.t_max))
    if not jobs:
        print("aucun run avec arêtes", file=sys.stderr)
        return 1

    print(f"{len(jobs)} runs, {args.workers} processus")
    with mp.Pool(args.workers) as pool:
        rows = [row for row in pool.map(_job, jobs) if row]

    if not rows:
        print("aucune mesure", file=sys.stderr)
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    scalar = [key for key in rows[0] if not key.startswith("histogramme")]
    with open(args.out / "lotJ_sufficiency_runs.csv", "w", newline="",
              encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=scalar)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in scalar})

    arms = sorted({row["arm"] for row in rows})
    summary = {}
    for arm in arms:
        subset = [row for row in rows if row["arm"] == arm]
        entry = {"n_runs": len(subset)}
        for key in scalar:
            if key in ("arm", "seed"):
                continue
            mean, ci, n = student([row[key] for row in subset])
            entry[key] = {"mean": mean, "ci95": ci, "n": n}
        counts = np.sum([row["histogramme_concentration"] for row in subset], axis=0)
        entry["histogramme_concentration"] = (counts / counts.sum()).tolist()
        entry["histogramme_bornes"] = subset[0]["histogramme_bornes"]
        summary[arm] = entry

    reference = "control" if "control" in summary else arms[0]
    verdict = {
        "bras_reference": reference,
        "plancher": summary[reference]["plancher_suffisance"]["mean"],
        "plancher_ic": summary[reference]["plancher_suffisance"]["ci95"],
        "toutes_suffisantes": summary[reference]["plancher_toutes_suffisantes"]["mean"],
        "temoin_degre_un": summary[reference]["temoin_degre_un"]["mean"],
        "incidence_effacement": summary[reference]["incidence_effacement"]["mean"],
        # Un effacement ne peut qu'ABAISSER la valeur nette d'avant cascade,
        # donc que RENDRE une arête suffisante. Le taux mesuré est un
        # plancher, et l'incidence des effacements borne ce qui l'en sépare.
        "plancher_est_serre": (
            summary[reference]["incidence_effacement"]["mean"] < 0.05),
    }

    payload = {"fenetre": [args.t_min, args.t_max], "campagne": str(args.campaign),
               "resume": summary, "verdict": verdict}
    (args.out / "lotJ_sufficiency.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    for arm in arms:
        entry = summary[arm]
        print(f"{arm:>16} : sur-déterminées {100 * entry['part_sur_determinees']['mean']:5.1f} %  "
              f"plancher de suffisance {100 * entry['plancher_suffisance']['mean']:5.1f} % "
              f"± {100 * entry['plancher_suffisance']['ci95']:.1f}  "
              f"toutes suffisantes {100 * entry['plancher_toutes_suffisantes']['mean']:5.1f} %  "
              f"effacements {100 * entry['incidence_effacement']['mean']:.2f} %")
    print(f"plancher serré (effacements < 5 %) : {verdict['plancher_est_serre']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
