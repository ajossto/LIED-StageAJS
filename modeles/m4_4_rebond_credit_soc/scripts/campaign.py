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
BARGAIN_DIR = RESULTS / "bargain"

#: LE TAUX COMME VARIABLE DE PARTAGE (demande du 24 août 2026).
#:
#: Chaque bras branche le MÊME amorçage sur une valeur du partage p, en
#: changeant la règle de taux à t₀. Les contrats hérités de l'amorçage gardent
#: leur taux (ils sont perpétuels et leur taux est gelé au contrat) : l'effet
#: ne se propage qu'au rythme du renouvellement du carnet, ce qui est le
#: mécanisme même qu'on veut observer.
#:
#: `marginal` est le bras de référence : c'est la règle de toute la lignée
#: antérieure. Il est relancé ici avec `record_rate_split` armé pour mesurer
#: où elle se situe sur l'échelle — mesuré à p ≈ 0,52 sur 150 pas hors
#: campagne (`tests/test_bargain_rate.py`), donc presque exactement au
#: partage équitable, ce que personne n'avait établi.
BARGAIN_SHARES = (0.0, 0.25, 0.5, 0.75, 1.0)


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


#: LOT C — COUVERTURE DE QUEUE. Le pilote C0 mesure `n_tail` ≈ 247 par
#: instantané sur le revenu d'intérêt à λ = 30, contre une cible dérivée de
#: 400 (erreur-type de Hill ≤ 0,10 à α̂ ≈ 3). Le facteur manquant est 1,62.
#:
#: λ est de la PURE TAILLE FINIE selon M4B (intensivité à ±2 %) : le monter
#: n'change pas la physique, seulement la statistique. Cette lignée le
#: VÉRIFIE au lieu de l'hériter — c'est à cela que sert le bras `control` de
#: cette campagne, comparé à son homologue à λ = 30.
LAMBDA_COVERAGE = 50.0
COVERAGE_DIR = RESULTS / "coverage"
COVERAGE_BURN = COVERAGE_DIR / "burn"
COVERAGE_ARMS = ("control", "all_A150")


def burn_coverage(seed: int) -> dict:
    directory = COVERAGE_BURN / f"seed{seed}"
    snapshot = directory / f"snapshot_t{T0}.pkl"
    if snapshot.exists():
        return {"seed": seed, "skipped": True}
    started = time.time()
    simulation = Simulation(Config(**{**BASE, "lam": LAMBDA_COVERAGE},
                                   seed=seed, T=T0))
    simulation.run()
    write_series(simulation, directory)
    save_snapshot(simulation, snapshot)
    return {"seed": seed, "t": simulation.t, "status": simulation.status,
            "pop": simulation.series[-1]["pop"],
            "wall_seconds": time.time() - started}


def run_coverage(job: tuple[int, str]) -> dict:
    seed, arm = job
    plan, _ = ARMS[arm]
    directory = COVERAGE_DIR / arm / f"seed{seed}"
    return _run_cell(directory, seed, plan,
                     {"loan_direction": "free", "lam": LAMBDA_COVERAGE},
                     {"arm": arm, "lot": "coverage"},
                     burn_dir=COVERAGE_BURN)


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
              label: dict, burn_dir: Path | None = None,
              window: int = WINDOW) -> dict:
    marker = directory / "summary.json"
    if marker.exists():
        return {**label, "seed": seed, "skipped": True}
    started = time.time()
    snapshot = (burn_dir or BURN_DIR) / f"seed{seed}" / f"snapshot_t{T0}.pkl"
    config = Config(**{**BASE, **INSTRUMENTATION, **overrides}, seed=seed, T=T0 + window)
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


def run_bargain(job: tuple[int, str]) -> dict:
    """Un bras du lot « taux » : `marginal` (référence) ou `p=…`."""
    seed, label = job
    directory = BARGAIN_DIR / label / f"seed{seed}"
    if label == "marginal":
        overrides = {"rate_rule": "marginal", "record_rate_split": True}
    else:
        overrides = {
            "rate_rule": "bargain",
            "bargain_p": float(label.split("=")[1]),
            "record_rate_split": True,
        }
    return _run_cell(directory, seed, [], {"loan_direction": "free", **overrides},
                     {"arm": label, "lot": "bargain"})


def bargain_jobs() -> list[tuple[int, str]]:
    labels = ["marginal"] + [f"p={share:g}" for share in BARGAIN_SHARES]
    return [(seed, label) for label in labels for seed in SEEDS]


#: LE PARTAGE QUI ÉVOLUE EN COURS DE TRAJECTOIRE.
#:
#: Les bras statiques ci-dessus sont déjà des expériences de CHANGEMENT
#: BRUSQUE : ils passent de la règle historique (p ≈ 0,52) à un p fixe, à t₀.
#: Ce que la rampe ajoute, et qu'eux ne peuvent pas donner, c'est
#: l'HYSTÉRÉSIS : le partage monte par paliers dans un bras, descend par les
#: mêmes paliers dans l'autre, et l'on compare l'état aux mêmes valeurs de p.
#: S'ils diffèrent, le système a une mémoire — ce qui est attendu, puisque les
#: contrats déjà signés gardent leur taux, mais dont l'ampleur n'est pas
#: connue.
RAMP_LEVELS = (0.0, 0.25, 0.5, 0.75, 1.0)
RAMP_STEP = WINDOW // len(RAMP_LEVELS)


def ramp_plan(levels) -> list[dict]:
    return [
        intervention(param="bargain_p", value=level, scope="all",
                     t=T0 + 1 + index * RAMP_STEP,
                     note=f"palier {index + 1}/{len(levels)}")
        for index, level in enumerate(levels)
    ]


def run_ramp(job: tuple[int, str]) -> dict:
    seed, direction = job
    levels = RAMP_LEVELS if direction == "up" else tuple(reversed(RAMP_LEVELS))
    directory = BARGAIN_DIR / f"ramp_{direction}" / f"seed{seed}"
    return _run_cell(
        directory, seed, ramp_plan(levels),
        {"loan_direction": "free", "rate_rule": "bargain",
         "bargain_p": levels[0], "record_rate_split": True},
        {"arm": f"ramp_{direction}", "lot": "bargain"},
    )


#: LOT E — TENTATIVE DE CONTRÔLE (plan §3.3).
#:
#: Un levier CONTRÔLE une grandeur si, et seulement si : sa réponse appariée
#: a un signe constant sur toutes les graines ; elle est monotone sur une
#: étendue mesurée d'au moins ×3 du levier ; et son exposant intra-famille
#: survit au contrôle §14.2. Tout ce qui est plus faible est une corrélation.
#:
#: ρ est le candidat n°1 : M4.2B le désigne comme le levier le plus
#: systématique sur α̂, et v2 établit `rotation = ρ·Ḡ`. L'étendue balayée est
#: ×6, largement au-delà du ×3 exigé.
RHO_LEVELS = (0.5, 1.0, 1.5, 2.0, 3.0)
CONTROL_DIR = RESULTS / "control_rho"


def run_rho(job: tuple[int, float]) -> dict:
    seed, rho = job
    directory = CONTROL_DIR / f"rho={rho:g}" / f"seed{seed}"
    plan = [] if rho == 1.0 else [
        intervention(param="rho", value=rho, scope="all")
    ]
    return _run_cell(directory, seed, plan, {"loan_direction": "free"},
                     {"arm": f"rho={rho:g}", "lot": "control"})


#: LOT F — POURQUOI b DÉPASSE LA VALEUR σ = 0 DE M4B.
#:
#: Le plan §3.2 énumère QUATRE différences de régime entre cette lignée et
#: M4B : σ (0,01 contre 0,25), δ (0,01 contre 0,05), la taille du bassin
#: d'appariement (2 contre [2 ; 10]) et l'institution de principal (production
#: jointe contre arithmétique).
#:
#: \fait{} La quatrième est VIDE dans un régime homogène, et c'est
#: démontrable : quand les deux entités d'une paire partagent la même
#: technologie, l'optimum de production jointe vaut exactement (K_b − K_a)/2,
#: c'est-à-dire la règle arithmétique. C'est le mécanisme même de la parité
#: bit à bit avec M4.3. Les bras de ce lot étant homogènes, il ne reste que
#: trois différences.
#:
#: \incertitude{} La troisième n'est pas balayable : `POOL_SIZE` est un choix
#: constitutif du moteur, pas un paramètre, et le rendre variable serait une
#: modification de comportement — hors de la discipline additive du fork.
#: Elle est donc documentée comme non tentée, et non silencieusement omise.
#:
#: Restent σ et δ, tous deux intervenables. La fenêtre est DOUBLÉE pour ces
#: bras : σ = 0,25 est un changement de régime, pas une perturbation, et
#: 2000 pas ne suffiraient pas à y converger.
ABLATION_DIR = RESULTS / "ablation"
ABLATION_WINDOW = 4000
ABLATION_ARMS = {
    "sigma005": [intervention(param="sigma", value=0.05, scope="all")],
    "sigma010": [intervention(param="sigma", value=0.10, scope="all")],
    "sigma025": [intervention(param="sigma", value=0.25, scope="all")],
    "delta005": [intervention(param="delta", value=0.05, scope="all")],
    "m4b_like": [intervention(param="sigma", value=0.25, scope="all"),
                 intervention(param="delta", value=0.05, scope="all")],
}


def run_ablation(job: tuple[int, str]) -> dict:
    seed, arm = job
    directory = ABLATION_DIR / arm / f"seed{seed}"
    return _run_cell(directory, seed, ABLATION_ARMS[arm], {"loan_direction": "free"},
                     {"arm": arm, "lot": "ablation"}, window=ABLATION_WINDOW)


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
    if command == "bargain_pilot":
        # Les deux extrêmes sur UNE graine, avant d'engager 72 cellules : le
        # cas altruiste peut faire enfler la population, et `pop_max` est à
        # 30 000. On mesure avant de lancer.
        BARGAIN_DIR.mkdir(parents=True, exist_ok=True)
        for label in ("p=0", "p=1"):
            print(json.dumps(run_bargain((0, label)), ensure_ascii=False), flush=True)
    if command in {"bargain", "all"}:
        BARGAIN_DIR.mkdir(parents=True, exist_ok=True)
        _pool(run_bargain, bargain_jobs(), "bras du lot « taux »")
    if command in {"coverage", "all"}:
        COVERAGE_BURN.mkdir(parents=True, exist_ok=True)
        _pool(burn_coverage, list(SEEDS), f"amorçages λ = {LAMBDA_COVERAGE:g}")
        _pool(run_coverage, [(seed, arm) for arm in COVERAGE_ARMS for seed in SEEDS],
              "bras de couverture")
    if command in {"rho", "all"}:
        CONTROL_DIR.mkdir(parents=True, exist_ok=True)
        _pool(run_rho, [(seed, rho) for rho in RHO_LEVELS for seed in SEEDS],
              "bras du lot E (contrôle par ρ)")
    if command in {"ablation", "all"}:
        ABLATION_DIR.mkdir(parents=True, exist_ok=True)
        _pool(run_ablation, [(seed, arm) for arm in ABLATION_ARMS for seed in SEEDS],
              "bras du lot F (ablation vers M4B)")
    if command in {"ramp", "all"}:
        BARGAIN_DIR.mkdir(parents=True, exist_ok=True)
        _pool(run_ramp, [(seed, direction) for direction in ("up", "down")
                         for seed in SEEDS], "rampes de partage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
