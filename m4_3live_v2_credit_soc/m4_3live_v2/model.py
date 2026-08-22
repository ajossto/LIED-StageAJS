"""Moteur M4.3Live : M4.3 avec technologies (A, γ) PAR ENTITÉ, institution de
principal « maximiser la production jointe », et interventions en direct.

Fork INDÉPENDANT (prompt §3.5) : ce module n'importe rien de
`m4_3_credit_soc`. Il en reprend les conventions structurelles, relues
ligne à ligne dans `m4_3_credit_soc/m4_3/model.py` :

- listes parallèles sur `Population`, identifiant jamais réutilisé
  (m4_3/model.py:105-142) ;
- carnet `LoanBook` à agrégats incrémentaux, fusion de deux prêts d'une
  même paire au taux moyen pondéré (m4_3/model.py:145-202) ;
- RNG `numpy.random.default_rng(seed)` (m4_3/model.py:525) et séquence
  d'appels inchangée : Poisson des naissances, normale du choc, puis
  `_sample` du marché avec son chemin rapide k == 2 (m4_3/model.py:294-313) ;
- ordre des phases : interventions, naissances, choc, production,
  intérêts, dépréciation, marché, faillites en cascade, mesure
  (m4_3/model.py:537-682) ;
- faillites cancel+destroy et avalanches causales (m4_3/model.py:403-517) ;
- pool d'appariement k ≡ 2 et η_{ρ,β}(N) (m4_3/model.py:245-255).

CE QUI CHANGE, et rien d'autre :

1. `A` et `γ` sont des attributs d'entité (`Population.A`, `Population.g`),
   fixés à la naissance, plus des paramètres globaux. Un identifiant entier
   de technologie (`Population.tech`) route le calcul du principal.
2. Le principal n'est plus (K_ℓ - K_b)/2 mais δ* = h(C) - x, le transfert
   qui maximise la production jointe de la paire (voir `kernel.py`). Quand
   les deux entités partagent la MÊME technologie, δ* vaut exactement
   (K_ℓ - K_b)/2 : la baseline homogène de M4.3Live est bit à bit celle de
   M4.3 (vérifié contre un run stocké, `tests/test_resume_divergence.py`).
3. Trois compteurs de marché nouveaux séparent les paires refusées :
   `blocked_dir` (δ* ≤ 0 : l'optimum jointe voudrait faire circuler le
   capital du pauvre vers le riche, sens interdit par le marché,
   m4_3/model.py:357-361), `blocked_tiny` (0 < δ* < MIN_LOAN) et
   `blocked_rate` (taux non strictement positif, possible uniquement sous
   `rate_rule="surplus_share"`). Sans cette séparation, l'effondrement du
   volume de prêt d'un bras traité serait ininterprétable.
4. Une file d'interventions est vidée au TOUT DÉBUT de `step()`, avant les
   naissances, et journalisée avec le t effectif (prompt §2).

Aucun tirage aléatoire n'est consommé par une pause, par la compilation
d'une table du noyau, ni par une intervention de portée `all`/`new`.
"""

from __future__ import annotations

import math
import threading
from collections import defaultdict
from dataclasses import asdict, dataclass, field, replace

import numpy as np

from .kernel import (
    KERNEL_POLICIES,
    PrincipalKernel,
    TechRegistry,
    joint_production_gain,
)


# Choix constitutifs, retirés de la configuration (identiques à M4.3).
INSOLVENCY_TOL = 1e-9
MIN_LOAN = 1e-9
ZERO_TOL = 1e-12
K_FLOOR = 1e-9
POOL_SIZE = 2

RATE_RULES = ("marginal", "surplus_share")

# Sémantique de portée par paramètre (prompt §2). Le champ `degenerate`
# est affiché tel quel par l'IHM : aucun sélecteur ne ment sur ce qu'il fait.
ENTITY_PARAMS = ("A", "gamma")
BIRTH_PARAMS = ("K0",)
POPULATION_PARAMS = ("lam", "delta", "sigma", "rho", "eta_beta", "eta_n_ref")
SCOPES = ("all", "new", "fraction")

PARAM_SEMANTICS: dict[str, dict] = {
    "A": {
        "kind": "entity",
        "scopes": ["all", "new", "fraction"],
        "degenerate": "",
        "note": "Levier primaire d'extraction : multiplie production et rendement marginal.",
    },
    "gamma": {
        "kind": "entity",
        "scopes": ["all", "new", "fraction"],
        "degenerate": "",
        "note": (
            "Levier secondaire NON MONOTONE : pour K < 1, augmenter γ diminue K^γ. "
            "Dans le régime observé K ≫ 1, donc γ ↑ ⇒ production ↑."
        ),
    },
    "K0": {
        "kind": "birth",
        "scopes": ["all", "new"],
        "degenerate": (
            "K0 n'existe qu'à la naissance : « toutes » et « nouvelles » sont "
            "IDENTIQUES par construction. « fraction » n'a pas de sens et n'est "
            "pas implémentée."
        ),
        "note": "",
    },
}
for _name in POPULATION_PARAMS:
    PARAM_SEMANTICS[_name] = {
        "kind": "population",
        "scopes": ["all", "new"],
        "degenerate": (
            "Paramètre de population/marché, pas d'attribut d'entité : "
            "« nouvelles » est un ALIAS explicite de « toutes ». « fraction » "
            "n'a pas de sens et n'est pas implémentée."
        ),
        "note": "",
    }


@dataclass(frozen=True)
class Config:
    """Paramètres variables. `A` et `gamma` sont les VALEURS PAR DÉFAUT à la
    naissance, pas des constantes globales (§2) : une intervention peut les
    changer pour tout ou partie de la population.

    `target_rule` est conservé pour compatibilité de format avec M4.3 mais
    n'a plus d'alternative : M4.3Live n'a qu'une institution de principal
    (§2, §3). Il n'est pas exposé à l'intervention en direct.
    """

    gamma: float = 0.5
    A: float = 1.0
    lam: float = 30.0
    delta: float = 0.01
    sigma: float = 0.01
    K0: float = 25.0
    seed: int = 0
    T: int = 2000
    pop_max: int = 30_000
    rho: float = 1.0
    eta_beta: float = 1.0
    eta_n_ref: float = 1.0
    target_rule: str = "arithmetic"
    # -- M4.3Live -------------------------------------------------------
    rate_rule: str = "marginal"
    surplus_share_p: float = 0.5
    kernel_policy: str = "exact_lut"
    lut_threshold: int = 1800
    lut_points: int = 65
    record_loan_events: bool = False
    record_deaths: bool = False
    record_avalanches: bool = False

    def __post_init__(self) -> None:
        if not 0.0 < self.gamma < 1.0:
            raise ValueError("gamma doit être dans ]0, 1[")
        if self.A <= 0:
            raise ValueError("A doit être strictement positif")
        if self.lam < 0 or not 0 <= self.delta < 1 or self.sigma < 0:
            raise ValueError("lam et sigma doivent être positifs, delta dans [0, 1[")
        if self.K0 <= 0 or self.T < 0 or self.pop_max < 1:
            raise ValueError("K0 > 0, T >= 0 et pop_max >= 1 requis")
        if self.rho <= 0:
            raise ValueError("rho doit être strictement positif")
        if self.eta_n_ref <= 0:
            raise ValueError("eta_n_ref doit être strictement positif")
        if self.rate_rule not in RATE_RULES:
            raise ValueError(f"rate_rule doit être dans {RATE_RULES}")
        if not 0.0 < self.surplus_share_p <= 1.0:
            raise ValueError("surplus_share_p doit être dans ]0, 1]")
        if self.kernel_policy not in KERNEL_POLICIES:
            raise ValueError(f"kernel_policy doit être dans {KERNEL_POLICIES}")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Intervention:
    """Changement de paramètre demandé en direct (§2).

    `scope` :
    - `all`      : toutes les entités vivantes MAINTENANT et toutes les
                   futures (rétroactif et prospectif) ;
    - `new`      : seulement les entités nées APRÈS ; les vivantes gardent
                   leur valeur pour toujours (vintage technologique) ;
    - `fraction` : tirage d'une fraction φ des vivantes, UNE SEULE FOIS, et
                   la valeur par défaut aux naissances futures reste
                   INCHANGÉE — c'est ce qui garde l'intensité de traitement
                   fixe au moment de la mesure.
    """

    param: str
    value: float
    scope: str
    phi: float | None = None
    ids: list[int] | None = None
    note: str = ""
    # rempli à l'application
    t: int = 0
    old_value: float | None = None
    selected_ids: list[int] = field(default_factory=list)
    n_selected: int = 0

    def to_dict(self) -> dict:
        return {
            "t": self.t,
            "param": self.param,
            "value": self.value,
            "scope": self.scope,
            "phi": self.phi,
            "ids": self.ids,
            "note": self.note,
            "old_value": self.old_value,
            "n_selected": self.n_selected,
            "selected_ids": self.selected_ids,
        }

    @staticmethod
    def from_dict(payload: dict) -> "Intervention":
        return Intervention(
            param=str(payload["param"]),
            value=float(payload["value"]),
            scope=str(payload["scope"]),
            phi=None if payload.get("phi") is None else float(payload["phi"]),
            ids=None if payload.get("ids") is None else [int(i) for i in payload["ids"]],
            note=str(payload.get("note", "")),
            t=int(payload.get("t", 0)),
        )


class Population:
    """Tableaux d'entités ; un identifiant n'est jamais réutilisé.

    Ajouts M4.3Live : `A`, `g` (technologie effective de l'entité) et
    `tech` (identifiant entier de cette technologie, clef de routage du
    noyau de principal).
    """

    def __init__(self) -> None:
        self.K: list[float] = []
        self.alive: list[bool] = []
        self.birth: list[int] = []
        self.int_in: list[float] = []
        self.int_out: list[float] = []
        self.prod: list[float] = []
        self.defaulted: list[bool] = []
        self.A: list[float] = []
        self.g: list[float] = []
        self.tech: list[int] = []
        self.n_alive = 0
        self.tech_alive: defaultdict[int, int] = defaultdict(int)
        self._alive_ids: set[int] = set()

    def __len__(self) -> int:
        return len(self.K)

    def born(self, capital: float, t: int, coefficient: float, exponent: float, tech: int) -> int:
        entity = len(self.K)
        self.K.append(capital)
        self.alive.append(True)
        self.birth.append(t)
        self.int_in.append(0.0)
        self.int_out.append(0.0)
        self.prod.append(0.0)
        self.defaulted.append(False)
        self.A.append(coefficient)
        self.g.append(exponent)
        self.tech.append(tech)
        self._alive_ids.add(entity)
        self.n_alive += 1
        self.tech_alive[tech] += 1
        return entity

    def kill(self, entity: int) -> None:
        self.alive[entity] = False
        self.K[entity] = 0.0
        self._alive_ids.remove(entity)
        self.n_alive -= 1
        self.tech_alive[self.tech[entity]] -= 1

    def retech(self, entity: int, coefficient: float, exponent: float, tech: int) -> None:
        """Réassigne la technologie d'une entité vivante (portées all/fraction)."""
        self.tech_alive[self.tech[entity]] -= 1
        self.A[entity] = coefficient
        self.g[entity] = exponent
        self.tech[entity] = tech
        self.tech_alive[tech] += 1

    def living(self) -> list[int]:
        return sorted(self._alive_ids)


class LoanBook:
    """Contrats ``id -> [prêteuse, emprunteuse, principal, taux]``.

    Identique à M4.3 (m4_3/model.py:145-238) : agrégats incrémentaux, deux
    prêts successifs d'une même paire fusionnent au taux moyen pondéré par
    leur principal (le service total est préservé exactement).
    """

    def __init__(self) -> None:
        self.loans: dict[int, list[float | int]] = {}
        self.by_lender: defaultdict[int, set[int]] = defaultdict(set)
        self.by_borrower: defaultdict[int, set[int]] = defaultdict(set)
        self.claims: defaultdict[int, float] = defaultdict(float)
        self.debts: defaultdict[int, float] = defaultdict(float)
        self.due: defaultdict[int, float] = defaultdict(float)
        self.by_pair: dict[tuple[int, int], int] = {}
        self.next_id = 0

    def __len__(self) -> int:
        return len(self.loans)

    def add(self, lender: int, borrower: int, principal: float, rate: float) -> tuple[int, bool]:
        loan_id = self.by_pair.get((lender, borrower))
        if loan_id is not None:
            record = self.loans[loan_id]
            old_principal = float(record[2])
            old_rate = float(record[3])
            new_principal = old_principal + principal
            record[2] = new_principal
            record[3] = (old_principal * old_rate + principal * rate) / new_principal
            self.claims[lender] += principal
            self.debts[borrower] += principal
            self.due[borrower] += new_principal * float(record[3]) - old_principal * old_rate
            return loan_id, True

        loan_id = self.next_id
        self.next_id += 1
        self.loans[loan_id] = [lender, borrower, principal, rate]
        self.by_lender[lender].add(loan_id)
        self.by_borrower[borrower].add(loan_id)
        self.claims[lender] += principal
        self.debts[borrower] += principal
        self.due[borrower] += principal * rate
        self.by_pair[(lender, borrower)] = loan_id
        return loan_id, False

    def remove(self, loan_id: int) -> None:
        lender, borrower, principal, rate = self.loans.pop(loan_id)
        lender = int(lender)
        borrower = int(borrower)
        principal = float(principal)
        rate = float(rate)
        self.by_lender[lender].discard(loan_id)
        self.by_borrower[borrower].discard(loan_id)
        self.claims[lender] -= principal
        self.debts[borrower] -= principal
        self.due[borrower] -= principal * rate
        self.by_pair.pop((lender, borrower))

    def forget(self, entity: int) -> None:
        """Efface toute trace d'une entité MORTE (§3.4 du prompt v2).

        Sans cet appel, `by_borrower` conserve une clef à ensemble vide par
        entité jamais créée. La phase de service des intérêts itère sur
        TOUTES les clefs (`Simulation.step`) : son coût par pas croît alors
        comme λ·t et le coût d'un run comme λT²/2. La purge le ramène à la
        population vivante, donc le run redevient linéaire en T.

        DEUX CONDITIONS, toutes deux nécessaires à la parité bit à bit :

        1. l'entité n'a plus aucun contrat — le corps de boucle sauté était
           donc un no-op, aucune opération flottante n'est supprimée ;
        2. l'entité est MORTE, donc elle ne peut plus jamais emprunter et sa
           clef ne sera pas réinsérée. Purger la clef vide d'une entité
           VIVANTE casserait la parité : `defaultdict` réinsère une clef en
           FIN d'ordre d'itération, ce qui changerait la séquence de sommation
           au prochain emprunt.
        """
        if self.by_borrower.get(entity) or self.by_lender.get(entity):
            raise RuntimeError(f"purge de l'entité {entity} qui porte encore des contrats")
        self.by_borrower.pop(entity, None)
        self.by_lender.pop(entity, None)
        self.due.pop(entity, None)
        self.claims.pop(entity, None)
        self.debts.pop(entity, None)

    def consistency_errors(self, alive: list[bool]) -> list[str]:
        """Contrôle hors boucle : contrats valides et agrégats exacts."""
        claims: defaultdict[int, float] = defaultdict(float)
        debts: defaultdict[int, float] = defaultdict(float)
        due: defaultdict[int, float] = defaultdict(float)
        errors: list[str] = []

        for loan_id, (lender, borrower, principal, rate) in self.loans.items():
            lender = int(lender)
            borrower = int(borrower)
            principal = float(principal)
            rate = float(rate)
            if lender == borrower or principal <= 0 or rate <= 0:
                errors.append(f"contrat {loan_id} invalide")
            if not alive[lender] or not alive[borrower]:
                errors.append(f"contrat {loan_id} avec une entité morte")
            claims[lender] += principal
            debts[borrower] += principal
            due[borrower] += principal * rate

        for current, rebuilt, name in (
            (self.claims, claims, "claims"),
            (self.debts, debts, "debts"),
            (self.due, due, "due"),
        ):
            for entity in set(current) | set(rebuilt):
                tolerance = 1e-6 * max(1.0, abs(rebuilt[entity]))
                if abs(current[entity] - rebuilt[entity]) > tolerance:
                    errors.append(f"{name}[{entity}] incohérent")

        if abs(sum(claims.values()) - sum(debts.values())) > 1e-6 * max(
            1.0, sum(claims.values())
        ):
            errors.append("total des créances différent du total des dettes")
        return errors


def net_worth(population: Population, book: LoanBook, entity: int) -> float:
    return population.K[entity] + book.claims[entity] - book.debts[entity]


def eta(pool_size: int, rho: float = 1.0, beta: float = 1.0, n_ref: float = 1.0) -> float:
    """η_{ρ,β}(N) = ρ·N_ref·(N/N_ref)^β. β=1 court-circuite pour rendre ρ·N
    exactement (identique à m4_3/model.py:245-255)."""
    if beta == 1.0:
        return rho * pool_size
    return rho * n_ref * (pool_size / n_ref) ** beta


def pair_rate(
    lender_capital: float,
    borrower_capital: float,
    lender_gamma: float,
    lender_A: float,
    borrower_gamma: float,
    borrower_A: float,
) -> float:
    """Taux négocié : moyenne géométrique des rendements marginaux.

    m = A·γ·K^(γ-1), chaque côté avec SA technologie. Généralisation
    directe et sans ambiguïté de `_pair_rate` (m4_3/model.py:258-266) ;
    quand les deux entités partagent la même technologie, l'expression est
    littéralement celle de M4.3.
    """
    lender_marginal = lender_A * lender_gamma * max(lender_capital, K_FLOOR) ** (lender_gamma - 1.0)
    borrower_marginal = (
        borrower_A * borrower_gamma * max(borrower_capital, K_FLOOR) ** (borrower_gamma - 1.0)
    )
    return math.sqrt(lender_marginal * borrower_marginal)


def surplus_rate(
    principal: float,
    surplus: float,
    share: float,
) -> float:
    """Taux dérivé du partage du surplus coopératif (prompt §3.4).

    HYPOTHÈSE DE CONVERSION, explicitée ici plutôt qu'enterrée dans le
    code : dans ce modèle la production A·K^γ est un FLUX PAR PAS, donc le
    surplus Δ créé par la réallocation est lui aussi un flux par pas, et il
    persiste tant que l'allocation persiste. On le gèle au moment du
    contrat — exactement comme le taux marginal `pair_rate` est déjà gelé
    au contrat — et on demande que le service perpétuel r·q verse à la
    prêteuse sa part p du surplus par pas :

        r · q = p · Δ      soit      r = p Δ / q.

    C'est cette hypothèse (« rente perpétuelle au surplus gelé »), et non le
    partage lui-même, qui rend le problème bien posé. Δ ≤ 0 ⇒ pas de
    contrat (un taux nul ou négatif serait rejeté par
    `LoanBook.consistency_errors`).
    """
    if principal <= 0.0 or surplus <= 0.0:
        return 0.0
    return share * surplus / principal


def _sample(rng: np.random.Generator, n: int, k: int) -> np.ndarray:
    """Échantillon uniforme sans remise. Séquence RNG STRICTEMENT identique à
    M4.3 (m4_3/model.py:294-313), chemin rapide k == 2 compris."""
    if k * 8 >= n:
        return rng.permutation(n)[:k]
    if k == 2:
        while True:
            indices = rng.integers(0, n, size=2)
            if indices[0] != indices[1]:
                return indices
    while True:
        indices = rng.integers(0, n, size=k)
        if len(set(indices.tolist())) == k:
            return indices


def _run_market(
    population: Population,
    book: LoanBook,
    config: Config,
    kernel: PrincipalKernel,
    rng: np.random.Generator,
    t: int,
) -> tuple[dict, list[dict]]:
    """Phase de marché : R_t = floor(η(N)) rounds sur un pool figé à deux."""
    pool = [entity for entity in population.living() if not population.defaulted[entity]]
    n = len(pool)
    market = {
        "pool": n,
        "rounds": 0,
        "new_loans": 0,
        "new_edges": 0,
        "merges": 0,
        "volume": 0.0,
        "blocked_dir": 0,
        "blocked_tiny": 0,
        "blocked_rate": 0,
        "surplus": 0.0,
    }
    events: list[dict] = []
    if n < 2:
        return market, events

    rounds = int(math.floor(eta(n, config.rho, config.eta_beta, config.eta_n_ref)))
    market["rounds"] = rounds
    # Alias locaux : évitent l'attribut-lookup répété dans la boucle chaude
    # (jusqu'à ~1e6 itérations/run). Aucun changement de valeur ni d'appel RNG.
    K = population.K
    pop_A = population.A
    pop_g = population.g
    pop_tech = population.tech
    solve = kernel.solve
    use_surplus_rate = config.rate_rule == "surplus_share"
    share = config.surplus_share_p
    record_events = config.record_loan_events
    for _ in range(rounds):
        indices = _sample(rng, n, POOL_SIZE)
        a = pool[indices[0]]
        b = pool[indices[1]]
        # Reproduit EXACTEMENT max(sample,key=K)/min(sample,key=K) de M4.3.
        if K[a] >= K[b]:
            lender, borrower = a, b
        else:
            lender, borrower = b, a
        if lender == borrower or K[lender] <= K[borrower]:
            continue

        borrower_capital = K[borrower]
        lender_capital = K[lender]
        principal = solve(pop_tech[borrower], pop_tech[lender], borrower_capital, lender_capital)
        if principal <= 0.0:
            # L'optimum de production jointe voudrait faire circuler le
            # capital de l'emprunteuse (pauvre) vers la prêteuse (riche) :
            # sens interdit par le marché, la paire ne traite pas.
            market["blocked_dir"] += 1
            continue
        if principal < MIN_LOAN:
            market["blocked_tiny"] += 1
            continue

        surplus = joint_production_gain(
            pop_A[borrower],
            pop_g[borrower],
            pop_A[lender],
            pop_g[lender],
            borrower_capital,
            lender_capital,
            principal,
        )
        if use_surplus_rate:
            rate = surplus_rate(principal, surplus, share)
            if rate <= 0.0:
                market["blocked_rate"] += 1
                continue
        else:
            rate = pair_rate(
                lender_capital,
                borrower_capital,
                pop_g[lender],
                pop_A[lender],
                pop_g[borrower],
                pop_A[borrower],
            )

        borrower_capital_after = borrower_capital + principal
        loan_id, merged = book.add(lender, borrower, principal, rate)
        K[lender] = lender_capital - principal
        K[borrower] = borrower_capital_after
        market["new_loans"] += 1
        market["merges" if merged else "new_edges"] += 1
        market["volume"] += principal
        market["surplus"] += surplus
        if record_events:
            rq = rate * principal
            production_after = pop_A[borrower] * max(borrower_capital_after, K_FLOOR) ** pop_g[borrower]
            events.append(
                {
                    "t": t,
                    "loan_id": loan_id,
                    "lender": lender,
                    "borrower": borrower,
                    "merged": int(merged),
                    "q": principal,
                    "r": rate,
                    "rq": rq,
                    "surplus": surplus,
                    "Kb_before": borrower_capital,
                    "Kl_before": lender_capital,
                    "tech_b": pop_tech[borrower],
                    "tech_l": pop_tech[lender],
                    "Kb_after": borrower_capital_after,
                    "rq_over_Kb": rq / borrower_capital_after if borrower_capital_after > 0 else float("nan"),
                    "rq_over_F": rq / production_after if production_after > 0 else float("nan"),
                }
            )
    return market, events


def _fail_one(population: Population, book: LoanBook, entity: int, ledger: dict) -> None:
    ledger["dead_info"][entity] = {
        "K": population.K[entity],
        "claims": book.claims[entity],
        "debts": book.debts[entity],
        "nw": net_worth(population, book, entity),
        "deg_out": len(book.by_lender.get(entity, ())),
        "deg_in": len(book.by_borrower.get(entity, ())),
    }

    for loan_id in list(book.by_borrower[entity]):
        lender, _, principal, _ = book.loans[loan_id]
        book.remove(loan_id)
        ledger["claim_losses"] += principal
        ledger["loss_edges"].append((entity, lender, principal))

    for loan_id in list(book.by_lender[entity]):
        book.remove(loan_id)

    ledger["destroyed"] += max(population.K[entity], 0.0)
    population.kill(entity)
    # §3.4 : la clef morte est retirée ICI, au moment de la mort, et
    # nulle part ailleurs (voir `LoanBook.forget`).
    book.forget(entity)


def _build_avalanches(ledger: dict) -> list[dict]:
    death_iteration = ledger["death_iteration"]
    if not death_iteration:
        return []

    parent = {entity: entity for entity in death_iteration}

    def find(entity: int) -> int:
        while parent[entity] != entity:
            parent[entity] = parent[parent[entity]]
            entity = parent[entity]
        return entity

    for source, victim, _ in ledger["loss_edges"]:
        if source in parent and victim in parent:
            source_root, victim_root = find(source), find(victim)
            if source_root != victim_root:
                parent[victim_root] = source_root

    components: dict[int, list[int]] = {}
    for entity in death_iteration:
        components.setdefault(find(entity), []).append(entity)

    avalanches = []
    for members in components.values():
        member_set = set(members)
        volume_j = sum(
            float(principal)
            for source, _, principal in ledger["loss_edges"]
            if source in member_set
        )
        causes = sorted(ledger["roots"][entity] for entity in members if entity in ledger["roots"])
        avalanches.append(
            {
                "size": len(members),
                "depth": max(death_iteration[entity] for entity in members),
                "n_roots": sum(entity in ledger["roots"] for entity in members),
                "volume_j": volume_j,
                "causes": causes,
                "members": sorted(members),
            }
        )
    avalanches.sort(key=lambda avalanche: -avalanche["size"])
    return avalanches


def _resolve_bankruptcies(population: Population, book: LoanBook) -> tuple[list[int], dict]:
    ledger = {
        "loss_edges": [],
        "claim_losses": 0.0,
        "destroyed": 0.0,
        "roots": {},
        "death_iteration": {},
        "dead_info": {},
    }

    queue = []
    for entity in population.living():
        insolvent = net_worth(population, book, entity) < -INSOLVENCY_TOL
        if population.defaulted[entity] and insolvent:
            ledger["roots"][entity] = "both"
        elif population.defaulted[entity]:
            ledger["roots"][entity] = "liquidity"
        elif insolvent:
            ledger["roots"][entity] = "insolvency"
        else:
            continue
        queue.append(entity)

    dead: list[int] = []
    iteration = 0
    max_iterations = population.n_alive + 1
    while queue:
        iteration += 1
        if iteration > max_iterations:
            raise RuntimeError("la cascade n'atteint pas de point fixe")
        for entity in queue:
            if population.alive[entity]:
                _fail_one(population, book, entity, ledger)
                dead.append(entity)
                ledger["death_iteration"][entity] = iteration
        queue = sorted(
            entity
            for entity in population.living()
            if net_worth(population, book, entity) < -INSOLVENCY_TOL
        )

    ledger["iterations"] = iteration
    ledger["avalanches"] = _build_avalanches(ledger)
    return dead, ledger


class Simulation:
    """État et boucle d'une simulation M4.3Live."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.rng = np.random.default_rng(config.seed)
        self.population = Population()
        self.book = LoanBook()
        self.registry = TechRegistry()
        self.kernel = PrincipalKernel(
            self.registry,
            policy=config.kernel_policy,
            threshold=config.lut_threshold,
            points=config.lut_points,
        )
        self.default_A = config.A
        self.default_gamma = config.gamma
        self.default_tech = self.registry.intern(config.A, config.gamma)
        self.kernel.sync_matrix()
        self.t = 0
        self.status = "ok"
        self.series: list[dict] = []
        self.tech_series: list[dict] = []
        self.avalanches: list[dict] = []
        self.avalanche_members: list[dict] = []
        self.deaths: list[dict] = []
        self.loan_events: list[dict] = []
        self.intervention_log: list[dict] = []
        self._avalanche_id_counter = 0
        self._pending: list[Intervention] = []
        self._lock = threading.Lock()

    # -- interventions -----------------------------------------------------
    def submit(self, intervention: Intervention) -> None:
        """Met une intervention en file. Appelable depuis un autre thread
        (IHM) ou depuis un script sans tête : c'est le MÊME point d'entrée
        (§4), donc le même chemin de code est vérifié par le rejeu."""
        self._validate(intervention)
        with self._lock:
            self._pending.append(intervention)

    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)

    @staticmethod
    def _validate(intervention: Intervention) -> None:
        semantics = PARAM_SEMANTICS.get(intervention.param)
        if semantics is None:
            raise ValueError(f"paramètre inconnu ou non intervenable : {intervention.param}")
        if intervention.scope not in semantics["scopes"]:
            raise ValueError(
                f"portée {intervention.scope!r} sans objet pour {intervention.param!r} "
                f"(portées valides : {semantics['scopes']})"
            )
        if intervention.scope == "fraction":
            if intervention.ids is None:
                if intervention.phi is None or not 0.0 < intervention.phi <= 1.0:
                    raise ValueError("fraction : phi doit être dans ]0, 1] (ou fournir ids)")

    def _apply_pending(self) -> None:
        with self._lock:
            pending = self._pending
            self._pending = []
        for intervention in pending:
            self._apply(intervention)
            self.intervention_log.append(intervention.to_dict())

    def _select_fraction(self, phi: float) -> list[int]:
        """Tirage de ⌈φ·N⌋ vivantes AVEC LE RNG DE LA SIMULATION (§2), donc
        déterministe et rejouable."""
        living = self.population.living()
        n = len(living)
        if n == 0:
            return []
        count = int(round(phi * n))
        if count < 1:
            count = 1
        if count > n:
            count = n
        order = self.rng.permutation(n)[:count]
        return sorted(living[int(index)] for index in order)

    def _apply(self, intervention: Intervention) -> None:
        param = intervention.param
        scope = intervention.scope
        value = float(intervention.value)
        intervention.t = self.t
        semantics = PARAM_SEMANTICS[param]
        population = self.population

        if semantics["kind"] == "population":
            # `new` est un alias explicite de `all` : ce ne sont pas des
            # attributs d'entité, il n'y a pas de cohorte à distinguer.
            intervention.old_value = getattr(self.config, param)
            self.config = replace(self.config, **{param: value})
            intervention.n_selected = population.n_alive
            return

        if param == "K0":
            # `all` et `new` sont identiques par construction : K0 n'existe
            # qu'au moment de la naissance.
            intervention.old_value = self.config.K0
            self.config = replace(self.config, K0=value)
            intervention.n_selected = 0
            return

        # -- paramètres d'entité : A et gamma --------------------------------
        if param == "A":
            intervention.old_value = self.default_A
            new_of = lambda entity: (value, population.g[entity])  # noqa: E731
            new_default = (value, self.default_gamma)
        else:
            intervention.old_value = self.default_gamma
            new_of = lambda entity: (population.A[entity], value)  # noqa: E731
            new_default = (self.default_A, value)

        if scope in {"all", "new"}:
            self.default_A, self.default_gamma = new_default
            self.default_tech = self.registry.intern(self.default_A, self.default_gamma)

        if scope == "all":
            targets = population.living()
        elif scope == "new":
            targets = []
        else:
            if intervention.ids is not None:
                alive = population._alive_ids
                targets = sorted(entity for entity in intervention.ids if entity in alive)
            else:
                targets = self._select_fraction(float(intervention.phi))

        for entity in targets:
            coefficient, exponent = new_of(entity)
            population.retech(entity, coefficient, exponent, self.registry.intern(coefficient, exponent))

        self.kernel.sync_matrix()
        intervention.selected_ids = targets if scope == "fraction" else []
        intervention.n_selected = len(targets)

    # -- boucle ------------------------------------------------------------
    def step(self) -> str:
        self.t += 1
        # Les interventions sont appliquées au TOUT DÉBUT du pas, AVANT les
        # naissances (§2), donc avec le t effectif enregistré ci-dessus.
        self._apply_pending()

        config = self.config
        population = self.population
        book = self.book

        births = int(self.rng.poisson(config.lam))
        for entity in population.living():
            population.int_in[entity] = 0.0
            population.int_out[entity] = 0.0
            population.prod[entity] = 0.0
            population.defaulted[entity] = False
        injected = 0.0
        birth_A = self.default_A
        birth_gamma = self.default_gamma
        birth_tech = self.default_tech
        for _ in range(births):
            population.born(config.K0, self.t, birth_A, birth_gamma, birth_tech)
            injected += config.K0

        alive = population.living()
        capital_before_shock = sum(population.K[entity] for entity in alive)
        if config.sigma > 0 and alive:
            variance = config.sigma**2
            xi = self.rng.normal(-0.5 * variance, config.sigma, size=len(alive))
            for index, entity in enumerate(alive):
                population.K[entity] *= math.exp(xi[index])
        shock_gain = sum(population.K[entity] for entity in alive) - capital_before_shock

        production = 0.0
        prod_by_tech: defaultdict[int, float] = defaultdict(float)
        pop_A = population.A
        pop_g = population.g
        pop_tech = population.tech
        for entity in alive:
            produced = pop_A[entity] * population.K[entity] ** pop_g[entity]
            population.prod[entity] = produced
            population.K[entity] += produced
            production += produced
            prod_by_tech[pop_tech[entity]] += produced

        defaults = 0
        interest_paid = 0.0
        for borrower in list(book.by_borrower.keys()):
            loan_ids = book.by_borrower[borrower]
            if not loan_ids:
                continue
            due = book.due[borrower]
            available = population.K[borrower]
            if available >= due:
                ratio = 1.0
                population.K[borrower] = available - due
            else:
                ratio = available / due if due > 0 else 0.0
                population.K[borrower] = 0.0
                population.defaulted[borrower] = True
                defaults += 1
            if ratio > 0:
                for loan_id in loan_ids:
                    lender, _, principal, rate = book.loans[loan_id]
                    payment = ratio * principal * rate
                    population.K[lender] += payment
                    population.int_in[lender] += payment
                    population.int_out[borrower] += payment
                    interest_paid += payment

        depreciated = 0.0
        for entity in alive:
            capital = population.K[entity]
            depreciated += config.delta * capital
            capital *= 1.0 - config.delta
            population.K[entity] = capital if capital > ZERO_TOL else 0.0

        market, events = _run_market(population, book, config, self.kernel, self.rng, self.t)
        if events:
            self.loan_events.extend(events)
        dead, ledger = _resolve_bankruptcies(population, book)

        for entity in dead if config.record_deaths else ():
            info = ledger["dead_info"][entity]
            self.deaths.append(
                {
                    "t": self.t,
                    "id": entity,
                    "age": self.t - population.birth[entity],
                    "cause": ledger["roots"].get(entity, "cascade"),
                    "death_iter": ledger["death_iteration"][entity],
                    **info,
                }
            )
        for avalanche in ledger["avalanches"] if config.record_avalanches else ():
            avalanche_id = self._avalanche_id_counter
            self._avalanche_id_counter += 1
            self.avalanches.append(
                {
                    "avalanche_id": avalanche_id,
                    "t": self.t,
                    "size": avalanche["size"],
                    "depth": avalanche["depth"],
                    "n_roots": avalanche["n_roots"],
                    "volume_j": avalanche["volume_j"],
                    "causes": ",".join(avalanche["causes"]),
                }
            )
            for entity in avalanche["members"]:
                self.avalanche_members.append(
                    {
                        "avalanche_id": avalanche_id,
                        "t": self.t,
                        "id": entity,
                        "is_root": int(entity in ledger["roots"]),
                        "generation": ledger["death_iteration"][entity],
                    }
                )

        alive = population.living()
        roots = ledger["roots"]
        step_avalanches = ledger["avalanches"]
        capital_total = sum(population.K[entity] for entity in alive)
        capital_by_tech: defaultdict[int, float] = defaultdict(float)
        coefficient_sum = 0.0
        exponent_sum = 0.0
        for entity in alive:
            capital_by_tech[pop_tech[entity]] += population.K[entity]
            coefficient_sum += pop_A[entity]
            exponent_sum += pop_g[entity]
        n_alive = population.n_alive
        self.series.append(
            {
                "t": self.t,
                "births": births,
                "deaths": len(dead),
                "pop": n_alive,
                "K_tot": capital_total,
                "nw_tot": sum(net_worth(population, book, entity) for entity in alive),
                "prod_tot": production,
                "n_loans": len(book),
                "new_loans": market["new_loans"],
                "loan_volume": market["volume"],
                "interest_paid": interest_paid,
                "defaults": defaults,
                "roots_liquidity": sum(cause == "liquidity" for cause in roots.values()),
                "roots_insolvency": sum(cause == "insolvency" for cause in roots.values()),
                "roots_both": sum(cause == "both" for cause in roots.values()),
                "cascade_iters": ledger["iterations"],
                "n_avalanches": len(step_avalanches),
                "max_avalanche": max((a["size"] for a in step_avalanches), default=0),
                "claim_losses": ledger["claim_losses"],
                "destroyed": ledger["destroyed"],
                "injected": injected,
                "depreciated": depreciated,
                "shock_gain": shock_gain,
                "book_keys": len(book.by_borrower),
                "mkt_pool": market["pool"],
                "mkt_rounds": market["rounds"],
                "mkt_new_edges": market["new_edges"],
                "mkt_merges": market["merges"],
                # -- M4.3Live ---------------------------------------------
                "mkt_blocked_dir": market["blocked_dir"],
                "mkt_blocked_tiny": market["blocked_tiny"],
                "mkt_blocked_rate": market["blocked_rate"],
                "mkt_surplus": market["surplus"],
                "n_tech_alive": sum(1 for count in population.tech_alive.values() if count > 0),
                "mean_A": coefficient_sum / n_alive if n_alive else float("nan"),
                "mean_gamma": exponent_sum / n_alive if n_alive else float("nan"),
            }
        )
        for tech in sorted(population.tech_alive):
            count = population.tech_alive[tech]
            if count <= 0 and tech not in prod_by_tech:
                continue
            self.tech_series.append(
                {
                    "t": self.t,
                    "tech": tech,
                    "A": self.registry.A[tech],
                    "gamma": self.registry.gamma[tech],
                    "n_alive": count,
                    "K": capital_by_tech.get(tech, 0.0),
                    "prod": prod_by_tech.get(tech, 0.0),
                }
            )

        if population.n_alive == 0:
            self.status = "extinction"
        elif population.n_alive > config.pop_max:
            self.status = "explosion"
        return self.status

    def run(self, snapshot_times=(), on_snapshot=None, on_step=None) -> str:
        requested = set(snapshot_times)
        while self.t < self.config.T and self.status == "ok":
            self.step()
            if on_step is not None:
                on_step(self)
            if self.t in requested and on_snapshot is not None:
                on_snapshot(self.t, self.entity_snapshot(), self.network_snapshot())
        return self.status

    # -- mesures -----------------------------------------------------------
    def entity_snapshot(self) -> dict[str, np.ndarray]:
        ids = self.population.living()
        pop = self.population
        book = self.book
        claims = np.array([book.claims.get(entity, 0.0) for entity in ids])
        debts = np.array([book.debts.get(entity, 0.0) for entity in ids])
        capital = np.array([pop.K[entity] for entity in ids])
        interest_in = np.array([pop.int_in[entity] for entity in ids])
        interest_out = np.array([pop.int_out[entity] for entity in ids])
        production = np.array([pop.prod[entity] for entity in ids])
        return {
            "id": np.array(ids, dtype=np.int64),
            "K": capital,
            "claims": claims,
            "debts": debts,
            "nw": capital + claims - debts,
            "prod": production,
            "int_in": interest_in,
            "int_out": interest_out,
            "income": production + interest_in,
            "income_net": production + interest_in - interest_out,
            "A": np.array([pop.A[entity] for entity in ids]),
            "gamma": np.array([pop.g[entity] for entity in ids]),
            "tech": np.array([pop.tech[entity] for entity in ids], dtype=np.int64),
            "age": np.array([self.t - pop.birth[entity] for entity in ids], dtype=np.int64),
            "deg_out": np.array(
                [len(book.by_lender.get(entity, ())) for entity in ids], dtype=np.int64
            ),
            "deg_in": np.array(
                [len(book.by_borrower.get(entity, ())) for entity in ids], dtype=np.int64
            ),
        }

    def network_snapshot(self) -> dict[str, np.ndarray]:
        loans = list(self.book.loans.values())
        return {
            "lender": np.array([loan[0] for loan in loans], dtype=np.int64),
            "borrower": np.array([loan[1] for loan in loans], dtype=np.int64),
            "q": np.array([loan[2] for loan in loans], dtype=float),
            "r": np.array([loan[3] for loan in loans], dtype=float),
        }
