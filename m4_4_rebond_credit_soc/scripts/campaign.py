"""Campagne v2 — protocole, bras, et lancement parallèle.

PROTOCOLE (figé avant tout calcul ; repris de v1, rapport §3, avec les
modifications du §7 du prompt v2)
--------------------------------------------------------------------------
- **t₀ = 2000**, **fenêtre W = 2000 pas** après t₀. Justification lue dans
  les résultats déjà sur disque et non remesurée : les trois graines
  baseline de M4.3 rapportent `t_converge_int_in` = 1016 / 948 / 841 sur
  leur variable la plus lente, et `prod_tot` est stationnaire par blocs de
  500 dès t ≈ 500. t₀ = 2000 laisse un facteur 2 sur la variable la plus
  lente ; W ≈ 38 fois le temps d'autocorrélation intégré de `prod_tot`
  (52 pas).
- **Amorçage PARTAGÉ** : un seul run 0 → t₀ par graine. Tous les bras d'une
  même graine sont branchés sur son snapshot, donc rigoureusement identiques
  jusqu'à t₀. L'amorçage est HOMOGÈNE (une seule technologie), donc les deux
  règles de sens y coïncident bit à bit : le même snapshot sert aux deux.
- **PORTÉE GLOBALE uniquement** (§3.3) : plus de bras `fraction`, donc plus
  de bras `null`. Le contrôle apparié est un bras inerte.
- **12 graines** (§4.5) : avec n graines, moyenne/erreur-type suit une
  Student à n−1 degrés de liberté. À 5 graines le seuil à 5 % est 2,776 ; à
  12 il tombe à 2,201, et l'erreur-type est divisée par √(12/5) = 1,55.

LES BRAS, ET POURQUOI CEUX-LÀ
--------------------------------------------------------------------------
Le sens du prêt ne peut se poser qu'entre technologies DIFFÉRENTES : quand
les deux entités d'une paire partagent la même, l'optimum est le partage
égal et le transfert va toujours de la plus riche vers la moins riche.
Un bras homogène ne distingue donc PAS les deux règles — il les distingue si
peu que les deux trajectoires sont bit à bit identiques (vérifié par
`tests/test_v1_equivalence.py`). C'est pourquoi :

- `control` et `all_A150` restent homogènes après intervention : ils ne sont
  lancés QUE sous le sens libre, et servent de référence appariée et de
  contrôle de stationnarité. Les relancer sous l'autre règle produirait
  exactement les mêmes fichiers.
- les trois bras `new_*` créent DEUX technologies coexistantes — les
  entités déjà nées gardent la leur, les suivantes reçoivent la nouvelle —
  et sont lancés sous LES DEUX règles. C'est là, et seulement là, que la
  campagne A/B a un objet.

La portée `new` n'est pas un traitement partiel de la population vivante
(§3.3) : elle ne tire aucune cohorte au sort, ne consomme aucun tirage, et
son intensité n'est pas un paramètre qu'on prétendrait fixer.

    python3 scripts/campaign.py burn     # amorçages partagés (12 graines)
    python3 scripts/campaign.py arms     # bras du lot D
    python3 scripts/campaign.py phase    # bras du lot E (ordre des phases)
    python3 scripts/campaign.py pilot    # une graine, pour mesurer le coût
"""

from __future__ import annotations

import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from m4_4.live import load_snapshot, save_snapshot, write_series  # noqa: E402
from m4_4.model import Config, Intervention, Simulation  # noqa: E402

T0 = 2000
WINDOW = 2000
SEEDS = tuple(range(12))
#: 8 cœurs sur la machine cible ; l'utilisateur en autorise 7 (21 août 2026).
WORKERS = 7

#: INSTRUMENTATION DES BRAS (plan M4.4 §4). Ces quatre drapeaux étaient
#: éteints dans les 153 runs de v2, d'où l'absence totale de données de
#: décès, d'avalanche et de cascade dans la lignée précédente.
#:
#: `panel_every` n'est PAS un choix de goût : le plan §8 (décision 4) exige
#: qu'il soit mesuré. `scripts/cost_panels.py` l'a fait dans le régime exact
#: de cette campagne (`results/analysis/lotA_cost.json`) :
#:
#:   - un panneau coûte 3,98 ms et 43,9 Kio, à 1031 entités ;
#:   - le TEMPS n'est donc pas la contrainte : même à k = 1, les panneaux
#:     ajoutent 8 s à un run de 220 s ;
#:   - le DISQUE l'est : k = 1 met la campagne à 11,3 Gio, k = 10 à 3,35 Gio.
#:
#: Le critère retenu, écrit avant de choisir : le pas doit rester PETIT
#: DEVANT le temps d'autocorrélation intégré de `prod_tot`, mesuré à 52 pas
#: par la lignée (cité dans le protocole ci-dessus), pour que
#: l'échantillonnage ne replie pas la dynamique ; et l'empreinte de la
#: campagne doit rester de l'ordre du gibioctet. k = 10 est le plus grand
#: pas rond qui satisfasse k ≤ τ/5 = 10,4 — 200 panneaux par run, 1,0 Gio de
#: panneaux pour toute la campagne, 0,3 % de temps en plus.
#:
#: Le lot C pourra le revoir, mais pour une AUTRE raison (la couverture de
#: queue, §5 du plan), et cela devra être écrit comme tel.
PANEL_EVERY = 10
INSTRUMENTATION = dict(
    record_deaths=True,
    record_avalanches=True,
    record_loss_edges=True,
    # Le coefficient de Gini du bassin de marché, à chaque pas : c'est par
    # cette sonde, et non par `rotation = ρ·Ḡ`, que le plan §3.1 exige que Ḡ
    # soit mesuré — le déduire de la rotation referait une identité. Coût
    # mesuré : +1,85 % de temps de mur et 230 Kio par run.
    record_market_stats=True,
    panel_every=PANEL_EVERY,
)

#: L'amorçage, lui, n'est PAS instrumenté : il est partagé par tous les bras
#: d'une graine, il est antérieur à t₀, et aucune mesure du programme ne
#: porte sur lui. L'instrumenter multiplierait l'empreinte disque par le
#: nombre de bras pour des données identiques d'un bras à l'autre.

BASE = dict(
    gamma=0.5,
    A=1.0,
    lam=30.0,
    delta=0.01,
    sigma=0.01,
    K0=25.0,
    pop_max=30_000,
    rate_rule="marginal",
    kernel_policy="exact_lut",
)

RESULTS = ROOT / "results" / "campaign"
BURN_DIR = RESULTS / "burn"
ARM_DIR = RESULTS / "arms"
PHASE_DIR = RESULTS / "phase"


def intervention(**kwargs) -> dict:
    payload = {"t": T0 + 1, "note": ""}
    payload.update(kwargs)
    return payload


#: bras -> (plan, règles de sens sous lesquelles il est lancé)
ARMS: dict[str, tuple[list[dict], tuple[str, ...]]] = {
    "control": ([], ("free",)),
    "all_A150": ([intervention(param="A", value=1.5, scope="all")], ("free",)),
    "new_A150": (
        [intervention(param="A", value=1.5, scope="new")],
        ("free", "richest_lends"),
    ),
    "new_A075": (
        [intervention(param="A", value=0.75, scope="new")],
        ("free", "richest_lends"),
    ),
    "new_g060": (
        [intervention(param="gamma", value=0.6, scope="new")],
        ("free", "richest_lends"),
    ),
    # -- Lot B de M4.4 (plan §6) ------------------------------------------
    # Le bras COMPENSÉ : A monte ET l'échelle de naissance suit, pour que
    # `K0` cesse d'être une longueur fixe pendant que la technologie change
    # d'échelle. v1 a montré que cette compensation annule entièrement la
    # contraction de population (pop ×1,005) et fait passer ε de 0,75 à
    # 2,02. Sans ce bras, une réponse de queue qui ne serait qu'un artefact
    # d'échelle serait découverte à la fin plutôt que détectée.
    # La FORMULE, pas le nombre : K0 · (A'/A)^{1/(1−γ)}, pour que le bras
    # survive à un changement de γ.
    "all_A150_K0comp": (
        [
            intervention(param="A", value=1.5, scope="all"),
            intervention(
                param="K0",
                value=BASE["K0"] * (1.5 / BASE["A"]) ** (1.0 / (1.0 - BASE["gamma"])),
                scope="all",
            ),
        ],
        ("free",),
    ),
}


def burn_one(seed: int) -> dict:
    directory = BURN_DIR / f"seed{seed}"
    snapshot = directory / f"snapshot_t{T0}.pkl"
    if snapshot.exists():
        return {"seed": seed, "skipped": True}
    started = time.time()
    simulation = Simulation(Config(**BASE, seed=seed, T=T0))
    simulation.run()
    write_series(simulation, directory)
    save_snapshot(simulation, snapshot)
    payload = {
        "seed": seed,
        "t": simulation.t,
        "status": simulation.status,
        "wall_seconds": time.time() - started,
        "snapshot": str(snapshot),
        "book_errors": simulation.book.consistency_errors(simulation.population.alive),
        "parameters": simulation.config.to_dict(),
    }
    (directory / "burn.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {k: v for k, v in payload.items() if k != "parameters"}


def _run_cell(directory: Path, seed: int, plan: list[dict], overrides: dict,
              label: dict) -> dict:
    marker = directory / "summary.json"
    if marker.exists():
        return {**label, "seed": seed, "skipped": True}
    started = time.time()
    snapshot = BURN_DIR / f"seed{seed}" / f"snapshot_t{T0}.pkl"
    config = Config(**{**BASE, **INSTRUMENTATION, **overrides}, seed=seed, T=T0 + WINDOW)
    simulation = load_snapshot(snapshot, config=config)
    planned: dict[int, list[Intervention]] = {}
    for entry in plan:
        planned.setdefault(int(entry["t"]), []).append(Intervention.from_dict(entry))
    while simulation.t < simulation.config.T and simulation.status == "ok":
        for item in planned.get(simulation.t + 1, ()):
            simulation.submit(item)
        simulation.step()
    write_series(simulation, directory)
    # §4.3 — LE CHECKPOINT DE FIN DE RUN, dette inscrite par M4.2B « pour
    # tous les modèles postérieurs » et jamais payée depuis : sans lui,
    # allonger une cellule demande de la rejouer depuis t=0. `records=False`
    # parce que l'histoire vient d'être écrite en CSV juste au-dessus ; le
    # pickle ne porte que l'ÉTAT, qui est ce qu'on ne peut pas reconstruire.
    checkpoint = save_snapshot(
        simulation, directory / f"snapshot_t{simulation.t}.pkl", records=False
    )
    payload = {
        **label,
        "seed": seed,
        "t_final": simulation.t,
        "status": simulation.status,
        "wall_seconds": time.time() - started,
        "checkpoint": str(checkpoint),
        "checkpoint_bytes": checkpoint.stat().st_size,
        "n_deaths": len(simulation.deaths),
        "n_avalanches": len(simulation.avalanches),
        "n_loss_edges": len(simulation.loss_edges),
        "n_panels": len(simulation.panels),
        "plan": plan,
        "interventions": simulation.intervention_log,
        "kernel": simulation.kernel.describe(),
        "book_errors": simulation.book.consistency_errors(simulation.population.alive),
        "parameters": simulation.config.to_dict(),
    }
    if simulation.intervention_log:
        with open(directory / "interventions.jsonl", "w", encoding="utf-8") as handle:
            for entry in simulation.intervention_log:
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    marker.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return {**label, "seed": seed, "status": simulation.status,
            "wall_seconds": payload["wall_seconds"]}


def run_arm(job: tuple[int, str, str]) -> dict:
    seed, arm, direction = job
    plan, _ = ARMS[arm]
    directory = ARM_DIR / direction / arm / f"seed{seed}"
    return _run_cell(directory, seed, plan, {"loan_direction": direction},
                     {"arm": arm, "direction": direction})


def run_phase(job: tuple[int, str]) -> dict:
    seed, order = job
    directory = PHASE_DIR / order / f"seed{seed}"
    return _run_cell(directory, seed, [], {"phase_order": order, "loan_direction": "free"},
                     {"arm": "control", "phase_order": order})


def arm_jobs() -> list[tuple[int, str, str]]:
    return [
        (seed, arm, direction)
        for arm, (_, directions) in ARMS.items()
        for direction in directions
        for seed in SEEDS
    ]


def _pool(function, jobs, title: str) -> None:
    started = time.time()
    with mp.Pool(processes=min(len(jobs), WORKERS)) as pool:
        done = 0
        for payload in pool.imap_unordered(function, jobs):
            done += 1
            print(f"[{done}/{len(jobs)}] " + json.dumps(payload, ensure_ascii=False),
                  flush=True)
    print(f"# {title} : {len(jobs)} runs en {time.time() - started:.0f} s", flush=True)


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else "all"
    if command in {"burn", "all"}:
        BURN_DIR.mkdir(parents=True, exist_ok=True)
        _pool(burn_one, list(SEEDS), "amorçages")
    if command == "pilot":
        # Une seule cellule sous chaque règle, pour MESURER le coût avant de
        # lancer la campagne entière (et non l'extrapoler depuis v1).
        for direction in ("free", "richest_lends"):
            payload = run_arm((0, "new_A150", direction))
            print(json.dumps(payload, ensure_ascii=False), flush=True)
    if command in {"arms", "all"}:
        ARM_DIR.mkdir(parents=True, exist_ok=True)
        _pool(run_arm, arm_jobs(), "bras du lot D")
    if command in {"phase", "all"}:
        PHASE_DIR.mkdir(parents=True, exist_ok=True)
        _pool(run_phase, [(seed, "deprec_first") for seed in SEEDS], "bras du lot E")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
