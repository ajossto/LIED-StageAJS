"""Moteur M4.2B : M4.2 avec cible de principal arithmétique (au lieu de géométrique).

Un pas suit toujours le même ordre : naissances, choc, production, intérêts,
dépréciation, marché du crédit, faillites en cascade, mesure. Cet ordre et
toute la mécanique (chocs, service des intérêts, dépréciation, faillites
cancel+destroy, avalanches causales, pool d'appariement k≡2) sont hérités
sans changement de M4.2 (voir m4_2_credit_soc/m4_2/model.py, référence en
lecture seule).

Modification constitutive (PROMPT_M4_2B.md §2) : pour une paire (K_ℓ>K_b>0),
la cible de transfert n'est plus K*=√(K_ℓK_b) mais la moyenne arithmétique
(K_ℓ+K_b)/2, ce qui donne un principal exact q_A=(K_ℓ-K_b)/2 et égalise les
deux capitaux après transaction. Cette règle n'est PAS une instance de
K*(r) : elle est calculée directement, sans passer par le taux. Le taux
lui-même reste inchangé (§3) : r_ℓb=√(m_ℓm_b), m=Aγ·K^(γ-1) — fonction
_pair_rate, strictement séparée de la fonction de principal _pair_principal.

Deux ajouts constitutifs par rapport à M4.2 :
- Config.target_rule ∈ {"arithmetic","geometric"} : bascule d'institution à
  paramètres identiques (§12), "geometric" reproduit exactement M4.2 (testé
  dans test_parity_m4_2.py) ;
- Config.rho, .eta_beta, .eta_n_ref : famille d'intensité de marché
  η_{ρ,β}(N) = ρ·N_ref·(N/N_ref)^β (§8). β=1.0 (défaut) donne η(N)=ρ·N sans
  passer par N_ref (évite toute dérive flottante) ; ρ=1,β=1 reproduit
  exactement η(N)=N de M4.2 (bit-identique, testé).

Un troisième ajout est purement une mesure, sans effet sur la dynamique :
chaque transaction du marché du crédit enregistre ses propres diagnostics
r, q, rq, rq/K_b' et rq/F_γ(K_b') (§3) dans ``Simulation.loan_events`` — la
liste des candidats à l'anomalie de service (« taux extrêmes pour petits
capitaux », etc.) que le prompt demande de surveiller explicitement.

Baseline M4.2B (§4-5, PROMPT_M4_2B.md) : δ=0.01, σ=0.01 (au lieu de
δ=0.05, σ=0.25 en M4.2) — dépréciation et chocs bien plus lents. gamma=0.5,
A=1.0, eta(N)=N (rho=1, eta_beta=1) restent les valeurs de départ héritées
de M4.2. K0=25 n'est PAS sanctuarisé (§5) : voir report/ pour la
discussion de K0/K*_aut(γ) et du temps de relaxation autarcique associé.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import asdict, dataclass

import numpy as np


# Choix constitutifs, retirés de la configuration (identiques à M4.2).
INSOLVENCY_TOL = 1e-9
MIN_LOAN = 1e-9
ZERO_TOL = 1e-12
# Plancher de K dans le rendement marginal (identique à M4.2 / M4B).
K_FLOOR = 1e-9
# k ≡ 2 : pool d'appariement fixé à deux, constitutif, retiré de la config.
POOL_SIZE = 2

TARGET_RULES = ("arithmetic", "geometric")


@dataclass(frozen=True)
class Config:
    """Les paramètres variables du modèle.

    ``target_rule`` bascule l'institution de principal à taux et reste
    inchangés (§12 : comparaison à paramètres identiques). ``rho``,
    ``eta_beta``, ``eta_n_ref`` paramètrent la famille d'intensité de
    marché η_{ρ,β} (§8) ; la baseline (rho=1, eta_beta=1) reproduit η(N)=N.
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
    target_rule: str = "arithmetic"
    rho: float = 1.0
    eta_beta: float = 1.0
    eta_n_ref: float = 1.0

    def __post_init__(self) -> None:
        if not 0.0 < self.gamma < 1.0:
            raise ValueError("gamma doit être dans ]0, 1[")
        if self.A <= 0:
            raise ValueError("A doit être strictement positif")
        if self.lam < 0 or not 0 <= self.delta < 1 or self.sigma < 0:
            raise ValueError("lam et sigma doivent être positifs, delta dans [0, 1[")
        if self.K0 <= 0 or self.T < 0 or self.pop_max < 1:
            raise ValueError("K0 > 0, T >= 0 et pop_max >= 1 requis")
        if self.target_rule not in TARGET_RULES:
            raise ValueError(f"target_rule doit être dans {TARGET_RULES}")
        if self.rho <= 0:
            raise ValueError("rho doit être strictement positif")
        if self.eta_n_ref <= 0:
            raise ValueError("eta_n_ref doit être strictement positif")

    def to_dict(self) -> dict:
        return asdict(self)


class Population:
    """Tableaux d'entités ; un identifiant n'est jamais réutilisé."""

    def __init__(self) -> None:
        self.K: list[float] = []
        self.alive: list[bool] = []
        self.birth: list[int] = []
        self.int_in: list[float] = []
        self.int_out: list[float] = []
        self.prod: list[float] = []
        self.defaulted: list[bool] = []
        self.n_alive = 0
        self._alive_ids: set[int] = set()

    def __len__(self) -> int:
        return len(self.K)

    def born(self, capital: float, t: int) -> int:
        entity = len(self.K)
        self.K.append(capital)
        self.alive.append(True)
        self.birth.append(t)
        self.int_in.append(0.0)
        self.int_out.append(0.0)
        self.prod.append(0.0)
        self.defaulted.append(False)
        self._alive_ids.add(entity)
        self.n_alive += 1
        return entity

    def kill(self, entity: int) -> None:
        self.alive[entity] = False
        self.K[entity] = 0.0
        self._alive_ids.remove(entity)
        self.n_alive -= 1

    def living(self) -> list[int]:
        return sorted(self._alive_ids)


class LoanBook:
    """Contrats ``id -> [prêteuse, emprunteuse, principal, taux]``.

    Identique à M4.2 : les agrégats sont mis à jour avec chaque contrat, deux
    prêts successifs entre la même paire fusionnent au taux moyen pondéré
    par leur principal (le service total est préservé exactement).
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
    """Fonction d'intensité du marché η_{ρ,β} : tentatives d'appariement par pas.

    Famille (PROMPT_M4_2B.md §8) : η_{ρ,β}(N) = ρ·N_ref·(N/N_ref)^β.
    β=1 (défaut) court-circuite la reparamétrisation en N_ref pour retourner
    exactement ρ·N — évite toute dérive flottante sur la baseline. ρ=1,β=1
    reproduit bit-à-bit η(N)=N de M4.2.
    """
    if beta == 1.0:
        return rho * pool_size
    return rho * n_ref * (pool_size / n_ref) ** beta


def _pair_rate(lender_capital: float, borrower_capital: float, gamma: float, A: float) -> float:
    """Taux négocié de la paire : moyenne géométrique des rendements marginaux.

    m = A·γ·K^(γ-1). Institution INCHANGÉE par rapport à M4.2 (§3) : le
    principal ne dérive plus de cette fonction (voir _pair_principal).
    """
    lender_rate = A * gamma * max(lender_capital, K_FLOOR) ** (gamma - 1.0)
    borrower_rate = A * gamma * max(borrower_capital, K_FLOOR) ** (gamma - 1.0)
    return math.sqrt(lender_rate * borrower_rate)


def _pair_principal(
    lender_capital: float,
    borrower_capital: float,
    rate: float,
    gamma: float,
    A: float,
    target_rule: str,
) -> float:
    """Principal transféré de la prêteuse à l'emprunteuse.

    - "arithmetic" (M4.2B, §2) : cible K_target=(K_ℓ+K_b)/2, calculée
      DIRECTEMENT (pas d'appel à K*(r)). q_A=(K_ℓ-K_b)/2 exactement : les
      deux bras (K_ℓ-K_target) et (K_target-K_b) sont égaux par
      construction, donc min(bras_prêteuse, bras_emprunteuse)=q_A sans
      ambiguïté (testé).
    - "geometric" (M4.2, conservée pour l'ablation §12) : cible
      K*(r)=(Aγ/r)^(1/(1-γ))=√(K_ℓK_b) pour tout γ avec ce taux (démontré
      dans M4.2) ; seul le bras de l'emprunteuse borne en général.
    """
    if target_rule == "arithmetic":
        return 0.5 * (lender_capital - borrower_capital)
    target = (A * gamma / rate) ** (1.0 / (1.0 - gamma))
    return min(lender_capital - target, max(0.0, target - borrower_capital))


def _sample(rng: np.random.Generator, n: int, k: int) -> np.ndarray:
    """Échantillon uniforme sans remise, avec la séquence RNG de M4/M4B/M4.2.

    Optimisation de profilage (2026-07-30 soir, appelé ~1 fois par round de
    marché, dominant du coût CPU) : le cas k==2 (POOL_SIZE, seule valeur
    jamais utilisée) évite la construction d'un ``set``/``list`` Python pour
    tester l'unicité. Mêmes appels RNG dans le même ordre exact que
    l'implémentation générale ci-dessous (aucun changement de la suite
    pseudo-aléatoire — vérifié par les tests de parité)."""
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
    population: Population, book: LoanBook, config: Config, rng: np.random.Generator, t: int
) -> tuple[dict, list[dict]]:
    """Phase de marché : R_t = floor(η(N)) rounds sur un pool figé à deux.

    Retourne les compteurs de marché (identiques à M4.2) et la liste des
    événements de prêt (r, q, rq et diagnostics §3, un par transaction
    réussie) pour Simulation.loan_events.
    """
    pool = [entity for entity in population.living() if not population.defaulted[entity]]
    n = len(pool)
    market = {
        "pool": n,
        "rounds": 0,
        "new_loans": 0,
        "new_edges": 0,
        "merges": 0,
        "volume": 0.0,
    }
    events: list[dict] = []
    if n < 2:
        return market, events

    rounds = int(math.floor(eta(n, config.rho, config.eta_beta, config.eta_n_ref)))
    market["rounds"] = rounds
    # Alias locaux (profilage 2026-07-30 soir) : évitent l'attribut-lookup
    # répété de population.K / config.gamma / config.A / config.target_rule
    # dans la boucle chaude (jusqu'à ~1e6 itérations/run). Aucun changement
    # de valeur ni d'appel RNG — même séquence, mêmes résultats (parité
    # revérifiée après ce changement).
    K = population.K
    gamma = config.gamma
    A = config.A
    target_rule = config.target_rule
    for _ in range(rounds):
        indices = _sample(rng, n, POOL_SIZE)
        a = pool[indices[0]]
        b = pool[indices[1]]
        # Reproduit EXACTEMENT max(sample,key=K)/min(sample,key=K) : en cas
        # d'égalité, Python renvoie le premier élément pour max ET pour min
        # (donc lender==borrower==a), ce que >= capture aussi ci-dessous.
        if K[a] >= K[b]:
            lender, borrower = a, b
        else:
            lender, borrower = b, a
        if lender == borrower or K[lender] <= K[borrower]:
            continue

        rate = _pair_rate(K[lender], K[borrower], gamma, A)
        principal = _pair_principal(
            K[lender],
            K[borrower],
            rate,
            gamma,
            A,
            target_rule,
        )
        if principal < MIN_LOAN:
            continue

        borrower_capital_after = K[borrower] + principal
        rq = rate * principal
        production_after = A * max(borrower_capital_after, K_FLOOR) ** gamma
        loan_id, merged = book.add(lender, borrower, principal, rate)
        K[lender] -= principal
        K[borrower] = borrower_capital_after
        market["new_loans"] += 1
        market["merges" if merged else "new_edges"] += 1
        market["volume"] += principal
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
                "Kb_after": borrower_capital_after,
                "rq_over_Kb": rq / borrower_capital_after if borrower_capital_after > 0 else float("nan"),
                "rq_over_F": rq / production_after if production_after > 0 else float("nan"),
            }
        )
    return market, events


def _fail_one(
    population: Population, book: LoanBook, entity: int, ledger: dict
) -> None:
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
    """État et boucle d'une simulation M4.2B."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.rng = np.random.default_rng(config.seed)
        self.population = Population()
        self.book = LoanBook()
        self.t = 0
        self.status = "ok"
        self.series: list[dict] = []
        self.avalanches: list[dict] = []
        self.avalanche_members: list[dict] = []
        self.deaths: list[dict] = []
        self.loan_events: list[dict] = []
        self._avalanche_id_counter = 0

    def step(self) -> str:
        config = self.config
        population = self.population
        book = self.book
        self.t += 1

        births = int(self.rng.poisson(config.lam))
        for entity in population.living():
            population.int_in[entity] = 0.0
            population.int_out[entity] = 0.0
            population.prod[entity] = 0.0
            population.defaulted[entity] = False
        injected = 0.0
        for _ in range(births):
            population.born(config.K0, self.t)
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
        for entity in alive:
            produced = config.A * population.K[entity] ** config.gamma
            population.prod[entity] = produced
            population.K[entity] += produced
            production += produced

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

        market, events = _run_market(population, book, config, self.rng, self.t)
        self.loan_events.extend(events)
        dead, ledger = _resolve_bankruptcies(population, book)

        for entity in dead:
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
        for avalanche in ledger["avalanches"]:
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
        self.series.append(
            {
                "t": self.t,
                "births": births,
                "deaths": len(dead),
                "pop": population.n_alive,
                "K_tot": sum(population.K[entity] for entity in alive),
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
                "mkt_pool": market["pool"],
                "mkt_rounds": market["rounds"],
                "mkt_new_edges": market["new_edges"],
                "mkt_merges": market["merges"],
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

    def individual_records(self, include_living: bool = True) -> list[dict]:
        """Mesures de fin de pas des vivantes et état terminal des mortes du pas."""
        pop = self.population
        book = self.book
        rows = []

        for entity in pop.living() if include_living else ():
            claims = book.claims.get(entity, 0.0)
            debts = book.debts.get(entity, 0.0)
            production = pop.prod[entity]
            interest_in = pop.int_in[entity]
            interest_out = pop.int_out[entity]
            rows.append(
                {
                    "t": self.t,
                    "id": entity,
                    "birth_t": pop.birth[entity],
                    "age": self.t - pop.birth[entity],
                    "alive": 1,
                    "death_cause": "",
                    "death_iter": "",
                    "K": pop.K[entity],
                    "claims": claims,
                    "debts": debts,
                    "nw": pop.K[entity] + claims - debts,
                    "prod": production,
                    "int_in": interest_in,
                    "int_out": interest_out,
                    "income": production + interest_in,
                    "income_net": production + interest_in - interest_out,
                    "defaulted": int(pop.defaulted[entity]),
                    "deg_out": len(book.by_lender.get(entity, ())),
                    "deg_in": len(book.by_borrower.get(entity, ())),
                }
            )

        for death in reversed(self.deaths):
            if death["t"] != self.t:
                break
            entity = death["id"]
            production = pop.prod[entity]
            interest_in = pop.int_in[entity]
            interest_out = pop.int_out[entity]
            rows.append(
                {
                    "t": self.t,
                    "id": entity,
                    "birth_t": pop.birth[entity],
                    "age": death["age"],
                    "alive": 0,
                    "death_cause": death["cause"],
                    "death_iter": death["death_iter"],
                    "K": death["K"],
                    "claims": death["claims"],
                    "debts": death["debts"],
                    "nw": death["nw"],
                    "prod": production,
                    "int_in": interest_in,
                    "int_out": interest_out,
                    "income": production + interest_in,
                    "income_net": production + interest_in - interest_out,
                    "defaulted": int(pop.defaulted[entity]),
                    "deg_out": death["deg_out"],
                    "deg_in": death["deg_in"],
                }
            )

        rows.sort(key=lambda row: row["id"])
        return rows

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
