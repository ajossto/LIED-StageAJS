"""Moteur M4.3Live-v2 : technologies (A, γ) par entité, institution de
principal « maximiser la production jointe », SENS DU PRÊT LIBRE, et
interventions en direct.

Fork de `m4_3live_credit_soc/m4_3live/model.py`, qui est GELÉ : ce paquet en
est une COPIE modifiée, jamais un import. Le moteur v1 a produit 203 runs
enregistrés et deux rapports publiés ; le modifier invaliderait
rétroactivement des résultats cités.

Conventions structurelles héritées de M4.3, relues ligne à ligne dans
`m4_3_credit_soc/m4_3/model.py` :

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

CE QUE M4.3Live (v1) A CHANGÉ, et qui reste :

1. `A` et `γ` sont des attributs d'entité (`Population.A`, `Population.g`),
   fixés à la naissance, plus des paramètres globaux. Un identifiant entier
   de technologie (`Population.tech`) route le calcul du principal.
2. Le principal n'est plus (K_ℓ - K_b)/2 mais δ* = h(C) - K_a, le transfert
   qui maximise la production jointe de la paire (voir `kernel.py`). Quand
   les deux entités partagent la MÊME technologie, δ* vaut exactement
   (K_b - K_a)/2 : la baseline homogène est bit à bit celle de M4.3.
3. Des compteurs de marché séparent les paires refusées.
4. Une file d'interventions est vidée au TOUT DÉBUT de `step()`, avant les
   naissances, et journalisée avec le t effectif.

CE QUE v2 CHANGE, et rien d'autre :

5. LE SENS DU PRÊT N'EST PLUS IMPOSÉ (`loan_direction`, §3.1 du prompt v2).
   La paire est non ordonnée (`a`, `b`) et le transfert δ* = h(C) - K_a est
   de signe libre : celle qui cède détient la créance, celle qui reçoit porte
   la dette, indépendamment de laquelle est la plus riche. La valeur
   `richest_lends` rejoue la règle de v1 pour que la comparaison soit
   appariée. Voir `_run_market`.
6. LES CLEFS MORTES DU CARNET SONT PURGÉES à la mort de leur entité
   (`LoanBook.forget`, §3.4). Sans cette purge, la phase de service des
   intérêts parcourt une clef vide par entité jamais créée : le coût par pas
   croît comme λ·t et le coût d'un run comme λT²/2.
7. LA BORNE `transfer_cap="equalization"` EST SUPPRIMÉE (§3.5). Elle n'a
   jamais mordu : `mkt_capped` cumulé vaut exactement 0 sur les 203 runs de
   v1. Il ne reste que l'énoncé littéral de l'institution.
8. L'ORDRE DES PHASES est configurable (`phase_order`, §3.2) : `"v1"` (par
   défaut) sert les intérêts puis déprécie, `"deprec_first"` fait l'inverse.
9. LA TENSION EST NATIVE (§4.1) : l'effectif producteur `n_prod` et son
   capital `K_prod` sont enregistrés à l'instant exact de la production,
   d'où K_eq, K_aut et T = K_aut/K_eq exacts et non reconstruits.
10. L'AMPLITUDE D'UNE INTERVENTION EST ENREGISTRÉE au moment où elle est
   appliquée (§4.2), avec la prédiction naïve du levier γ (§4.3).

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
from .tension import aggregate_rows, autarkic_scale, tension_row


# Choix constitutifs, retirés de la configuration (identiques à M4.3).
INSOLVENCY_TOL = 1e-9
MIN_LOAN = 1e-9
ZERO_TOL = 1e-12
K_FLOOR = 1e-9
POOL_SIZE = 2

RATE_RULES = ("marginal", "surplus_share")

#: Sens du prêt à l'intérieur d'une paire (§3.1 du prompt v2).
#:
#: ``free``           — DÉFAUT et raison d'être de v2 : le sens est celui que
#:                      donne l'optimum de production jointe. Le transfert
#:                      δ* = h(C) − K_a est de signe libre ; celle qui cède
#:                      devient créancière, celle qui reçoit devient débitrice,
#:                      quelle que soit laquelle est la plus riche.
#: ``richest_lends``  — règle de M4.3 et de M4.3Live v1 : dans chaque paire la
#:                      plus riche prête ; si l'optimum voudrait faire circuler
#:                      le capital dans l'autre sens (δ* ≤ 0), la paire est
#:                      refusée. Conservé pour que la campagne A/B du §3.1 soit
#:                      APPARIÉE — même moteur, même graine, même amorçage —
#:                      et non une comparaison entre deux lignées.
LOAN_DIRECTIONS = ("free", "richest_lends")

#: Ordre relatif du service des intérêts et de la dépréciation (§3.2).
#:
#: ``v1``            — DÉFAUT : production → service des intérêts →
#:                     dépréciation. Ordre de M4.3 et de M4.3Live v1 ; c'est
#:                     lui qui rend la parité bit à bit atteignable.
#: ``deprec_first``  — production → dépréciation → service des intérêts. Le
#:                     capital disponible au moment de payer est réduit d'un
#:                     facteur (1 − δ) ; toute débitrice dont le capital était
#:                     compris entre `dû` et `dû/(1 − δ)` bascule en défaut de
#:                     liquidité. La parité N'EST PAS préservée sous cette
#:                     valeur, et c'est le but.
PHASE_ORDERS = ("v1", "deprec_first")

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
    loan_direction: str = "free"
    phase_order: str = "v1"
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
        if self.loan_direction not in LOAN_DIRECTIONS:
            raise ValueError(f"loan_direction doit être dans {LOAN_DIRECTIONS}")
        if self.phase_order not in PHASE_ORDERS:
            raise ValueError(f"phase_order doit être dans {PHASE_ORDERS}")
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
    capital_1: float,
    capital_2: float,
    gamma_1: float,
    A_1: float,
    gamma_2: float,
    A_2: float,
) -> float:
    """Taux négocié : moyenne géométrique des rendements marginaux.

    Le rendement marginal d'une entité est m = A·γ·K^(γ-1), chaque côté avec
    SA technologie et son capital d'AVANT l'échange. Le taux du contrat est
    √(m₁·m₂). Généralisation directe de `_pair_rate`
    (m4_3/model.py:258-266) ; quand les deux entités partagent la même
    technologie, l'expression est littéralement celle de M4.3.

    SYMÉTRIE — et c'est ce qui tranche la question ouverte §12.2 du prompt
    v2 (« le taux a-t-il encore un sens quand la créancière est la plus
    fragile des deux ? »). La formule ne distingue pas les deux côtés : elle
    ne contient ni le rôle de créancière, ni celui de débitrice, ni aucune
    comparaison de capitaux. Échanger (capital_1, gamma_1, A_1) et
    (capital_2, gamma_2, A_2) laisse le résultat BIT À BIT identique, car la
    seule opération qui les mêle est un produit, et le produit flottant est
    commutatif (vérifié par `tests/test_loan_direction.py`). Libérer le sens
    du prêt (§3.1) ne change donc rien à la règle de taux, et il n'y avait
    rien à y changer.

    Les paramètres portent des noms neutres — `1` et `2`, pas « prêteuse » et
    « emprunteuse » — précisément pour que cette symétrie soit lisible.
    """
    marginal_1 = A_1 * gamma_1 * max(capital_1, K_FLOOR) ** (gamma_1 - 1.0)
    marginal_2 = A_2 * gamma_2 * max(capital_2, K_FLOOR) ** (gamma_2 - 1.0)
    return math.sqrt(marginal_1 * marginal_2)


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


def _pearson(n: int, sum_x: float, sum_y: float,
             sum_xx: float, sum_yy: float, sum_xy: float) -> float:
    """Coefficient de corrélation de Pearson à partir des sommes cumulées.

        r = (n Σxy − Σx Σy) / √[(n Σx² − (Σx)²)(n Σy² − (Σy)²)]

    Forme « une passe » : elle évite de garder les deux vecteurs en mémoire à
    chaque pas. Elle est numériquement moins stable que la forme centrée, ce
    qui est acceptable ici parce que r n'entre dans AUCUN calcul de la
    trajectoire — c'est un diagnostic écrit dans la série, jamais relu par le
    moteur. Retourne NaN si l'une des deux variables est constante (variance
    nulle), cas où la corrélation n'est pas définie.
    """
    if n < 2:
        return float("nan")
    var_x = n * sum_xx - sum_x * sum_x
    var_y = n * sum_yy - sum_y * sum_y
    if var_x <= 0.0 or var_y <= 0.0:
        return float("nan")
    return (n * sum_xy - sum_x * sum_y) / math.sqrt(var_x * var_y)


def _run_market(
    population: Population,
    book: LoanBook,
    config: Config,
    kernel: PrincipalKernel,
    rng: np.random.Generator,
    t: int,
) -> tuple[dict, list[dict]]:
    """Phase de marché : R_t = floor(η(N)) rondes sur un pool figé à deux.

    LE SENS DU PRÊT N'EST PLUS IMPOSÉ (§3.1 du prompt v2). La paire est
    NON ORDONNÉE : ses deux membres s'appellent `a` et `b`, de capitaux
    `K_a` et `K_b`, et aucun des deux n'est prêteuse a priori. Le noyau
    retourne le transfert optimal δ* = h(C) − K_a, de SIGNE LIBRE, où
    C = K_a + K_b est le capital joint. Si δ* > 0, `a` reçoit ; si δ* < 0,
    c'est `b`. Celle qui cède détient la créance, celle qui reçoit porte la
    dette.

    ORDRE DE CALCUL CANONIQUE. `a` est l'entité de plus petit capital de la
    paire tirée, `b` celle de plus grand (départage sur l'ordre du tirage en
    cas d'égalité exacte). Ce n'est plus un rôle, c'est un ordre de
    présentation au noyau, et il est conservé de v1 pour deux raisons :

    1. `kernel.solve(s_a, s_b, K_a, K_b)` et `kernel.solve(s_b, s_a, K_b, K_a)`
       sont deux entrées DIFFÉRENTES de la matrice de noyaux, dont les tables
       d'interpolation sont construites séparément : mathématiquement
       h_ab(C) + h_ba(C) = C, mais rien ne le garantit au dernier bit. Fixer
       l'ordre rend le transfert univoque.
    2. Il rend la requête au noyau octet pour octet identique à celle de v1,
       donc `loan_direction="richest_lends"` rejoue v1 exactement, ce qui est
       la condition pour que la campagne A/B du §3.1 soit appariée.

    Compteurs de refus, et un compteur CONTREFACTUEL :

    - `blocked_tiny` : |δ*| < MIN_LOAN, transfert sans portée numérique ;
    - `blocked_rate` : taux non strictement positif (possible sous
      `rate_rule="surplus_share"` seulement) ;
    - `blocked_dir` : sous `richest_lends`, les paires réellement refusées
      parce que l'optimum voulait faire remonter le capital vers la plus
      riche. Sous `free`, PLUS AUCUNE paire n'est refusée pour cette raison,
      et le compteur devient CONTREFACTUEL : il compte les paires que la
      règle v1 aurait refusées **dans l'état où v2 se trouve à cette
      ronde**. Ce n'est pas le compteur d'une trajectoire v1 — les deux
      trajectoires divergent dès le premier prêt inversé — et toute lecture
      de ce nombre doit le dire.
    - `reversed` : les prêts effectivement conclus dans le sens que v1
      interdisait (la plus pauvre cède à la plus riche), avec leur volume
      `volume_rev`. C'est le régime nouveau du §3.1.
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
        "blocked_dir": 0,
        "blocked_tiny": 0,
        "blocked_rate": 0,
        "reversed": 0,
        "volume_rev": 0.0,
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
    free_direction = config.loan_direction == "free"
    use_surplus_rate = config.rate_rule == "surplus_share"
    share = config.surplus_share_p
    record_events = config.record_loan_events
    for _ in range(rounds):
        indices = _sample(rng, n, POOL_SIZE)
        first = pool[indices[0]]
        second = pool[indices[1]]
        # Reproduit EXACTEMENT max(sample,key=K)/min(sample,key=K) de M4.3 :
        # `b` est le côté de plus grand capital, `a` l'autre.
        if K[first] >= K[second]:
            b, a = first, second
        else:
            b, a = second, first
        K_a = K[a]
        K_b = K[b]
        if not free_direction and K_b <= K_a:
            # Règle v1, telle quelle : capitaux égaux, rien à égaliser. Le
            # test précède l'appel au noyau, comme dans v1 — appeler le noyau
            # ferait avancer ses compteurs d'usage et pourrait déplacer la
            # compilation d'une table.
            continue

        delta = solve(pop_tech[a], pop_tech[b], K_a, K_b)

        if free_direction:
            # Compteur contrefactuel : la règle v1 aurait refusé cette paire.
            # Le garde `K_b > K_a` reproduit son arbre de décision exact (elle
            # écartait les capitaux égaux AVANT de compter un refus de sens).
            if delta <= 0.0 and K_b > K_a:
                market["blocked_dir"] += 1
            if delta >= 0.0:
                receiver, donor = a, b
                principal = delta
                inverted = False
            else:
                receiver, donor = b, a
                principal = -delta
                inverted = True
        else:
            if delta <= 0.0:
                # L'optimum de production jointe voudrait faire circuler le
                # capital de la moins riche vers la plus riche : sens interdit
                # par cette règle, la paire ne traite pas.
                market["blocked_dir"] += 1
                continue
            receiver, donor = a, b
            principal = delta
            inverted = False

        if principal < MIN_LOAN:
            market["blocked_tiny"] += 1
            continue

        receiver_capital = K[receiver]
        donor_capital = K[donor]
        surplus = joint_production_gain(
            pop_A[receiver],
            pop_g[receiver],
            pop_A[donor],
            pop_g[donor],
            receiver_capital,
            donor_capital,
            principal,
        )
        if use_surplus_rate:
            rate = surplus_rate(principal, surplus, share)
            if rate <= 0.0:
                market["blocked_rate"] += 1
                continue
        else:
            rate = pair_rate(
                donor_capital,
                receiver_capital,
                pop_g[donor],
                pop_A[donor],
                pop_g[receiver],
                pop_A[receiver],
            )

        receiver_capital_after = receiver_capital + principal
        loan_id, merged = book.add(donor, receiver, principal, rate)
        K[donor] = donor_capital - principal
        K[receiver] = receiver_capital_after
        market["new_loans"] += 1
        market["merges" if merged else "new_edges"] += 1
        market["volume"] += principal
        market["surplus"] += surplus
        if inverted:
            market["reversed"] += 1
            market["volume_rev"] += principal
        if record_events:
            rq = rate * principal
            production_after = pop_A[receiver] * max(receiver_capital_after, K_FLOOR) ** pop_g[receiver]
            events.append(
                {
                    "t": t,
                    "loan_id": loan_id,
                    "creditor": donor,
                    "debtor": receiver,
                    "inverted": int(inverted),
                    "merged": int(merged),
                    "q": principal,
                    "r": rate,
                    "rq": rq,
                    "surplus": surplus,
                    "K_receiver_before": receiver_capital,
                    "K_donor_before": donor_capital,
                    "tech_receiver": pop_tech[receiver],
                    "tech_donor": pop_tech[donor],
                    "K_receiver_after": receiver_capital_after,
                    "rq_over_K": rq / receiver_capital_after if receiver_capital_after > 0 else float("nan"),
                    "rq_over_F": rq / production_after if production_after > 0 else float("nan"),
                }
            )
    return market, events


def _service_interest(
    population: Population, book: LoanBook, config: Config, already_depreciated: bool
) -> tuple[int, float, int]:
    """Service des intérêts. Retourne (défauts, intérêts versés, fenêtre).

    Une débitrice paie `dû = Σ q·r` sur ses contrats. Si son capital
    disponible ne suffit pas, elle verse tout ce qu'elle a au prorata et est
    marquée en DÉFAUT DE LIQUIDITÉ.

    La troisième valeur retournée, la FENÊTRE DE BASCULE, est la prédiction
    a priori du §3.2 : le nombre de débitrices qui changeraient de statut si
    l'on échangeait cette phase et la dépréciation. C'est le même ensemble
    dans les deux ordres — celles dont le capital d'avant dépréciation K
    vérifie (1−δ)·K < dû ≤ K — mais il s'exprime différemment selon que
    `available` est déjà déprécié ou non. Aucune division n'est employée :
    dû ≤ available/(1−δ) est écrit dû·(1−δ) ≤ available.

    Cette valeur n'entre dans aucun calcul de trajectoire : c'est un
    diagnostic, écrit dans la série, qui permet d'écrire la prédiction AVANT
    de lancer le bras `deprec_first`.
    """
    defaults = 0
    interest_paid = 0.0
    window = 0
    one_minus_delta = 1.0 - config.delta
    for borrower in list(book.by_borrower.keys()):
        loan_ids = book.by_borrower[borrower]
        if not loan_ids:
            continue
        due = book.due[borrower]
        available = population.K[borrower]
        if available >= due:
            ratio = 1.0
            population.K[borrower] = available - due
            if due > 0.0 and not already_depreciated and available * one_minus_delta < due:
                window += 1
        else:
            ratio = available / due if due > 0 else 0.0
            population.K[borrower] = 0.0
            population.defaulted[borrower] = True
            defaults += 1
            if due > 0.0 and already_depreciated and due * one_minus_delta <= available:
                window += 1
        if ratio > 0:
            for loan_id in loan_ids:
                lender, _, principal, rate = book.loans[loan_id]
                payment = ratio * principal * rate
                population.K[lender] += payment
                population.int_in[lender] += payment
                population.int_out[borrower] += payment
                interest_paid += payment
    return defaults, interest_paid, window


def _depreciate(population: Population, alive: list[int], config: Config) -> float:
    """Dépréciation du capital de toutes les vivantes. Retourne le total détruit."""
    depreciated = 0.0
    delta = config.delta
    one_minus_delta = 1.0 - delta
    for entity in alive:
        capital = population.K[entity]
        depreciated += delta * capital
        capital *= one_minus_delta
        population.K[entity] = capital if capital > ZERO_TOL else 0.0
    return depreciated


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
        self.tension_series: list[dict] = []
        self.avalanches: list[dict] = []
        self.avalanche_members: list[dict] = []
        self.deaths: list[dict] = []
        self.loan_events: list[dict] = []
        self.intervention_log: list[dict] = []
        self._avalanche_id_counter = 0
        self._pending: list[Intervention] = []
        # §4.2 : {identifiant -> (A, γ) d'AVANT l'intervention}, rempli par
        # `_apply` et consommé par la phase de production du MÊME pas.
        self._amplitude_probe: dict[int, tuple[float, float]] = {}
        #: (A, γ) de naissance d'AVANT l'intervention, quand celle-ci a changé
        #: la technologie par défaut : les entités NÉES au pas de
        #: l'intervention la portent déjà, elles font donc partie de la
        #: cohorte traitée au sens du contrefactuel (§4.2).
        self._birth_probe: tuple[float, float] | None = None
        self._amplitude_log: list[dict] = []
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
        self._amplitude_probe = {}
        self._amplitude_log = []
        self._birth_probe = None
        for intervention in pending:
            probe, changed_default = self._apply(intervention)
            entry = intervention.to_dict()
            self.intervention_log.append(entry)
            if probe or changed_default:
                # `setdefault` : si deux interventions du même pas touchent la
                # même entité, l'état de référence reste celui d'AVANT le pas.
                for entity, previous in probe.items():
                    self._amplitude_probe.setdefault(entity, previous)
                self._amplitude_log.append(entry)

    def _close_amplitude(
        self, production: float, treated: float, treated_cf: float
    ) -> None:
        """Amplitude EXACTE d'une intervention, à l'instant de la production.

        Mesurée (§4.2), pas reconstruite. Notations, toutes évaluées au pas où
        l'intervention agit pour la première fois (horizon h = 1) et sur le
        capital réel de ce pas, choc multiplicatif compris :

        - ``prod_treated`` = Σ_{i traitée} A'_i K_i^{γ'_i} — ce que les entités
          traitées ont réellement produit ;
        - ``prod_treated_cf`` = Σ_{i traitée} A_i K_i^{γ_i} — ce qu'elles
          auraient produit sans l'intervention, MÊME capital ;
        - ``m`` = prod_treated / prod_treated_cf — l'amplitude du levier ;
        - ``p`` = prod_treated_cf / prod_total_cf — la part de production de la
          cohorte traitée, EX ANTE (avant application du levier).

        Le rapport ``E = (Π/Π_cf − 1) / ((m − 1) p)`` vaut 1 par ALGÈBRE, pas
        par mesure : c'est une réécriture des définitions ci-dessus. Son écart
        à 1 ne mesure que la propreté de l'aller-retour flottant, et il est
        rapporté à ce titre — jamais comme une confirmation empirique.
        """
        entries = self._amplitude_log
        n_probe = len(self._amplitude_probe)
        self._amplitude_probe = {}
        self._amplitude_log = []
        if not entries:
            return
        nan = float("nan")
        total_cf = production - treated + treated_cf
        m = treated / treated_cf if treated_cf > 0.0 else nan
        p = treated_cf / total_cf if total_cf > 0.0 else nan
        ratio = production / total_cf if total_cf > 0.0 else nan
        denominator = (m - 1.0) * p
        identity = (ratio - 1.0) / denominator if denominator not in (0.0,) else nan
        # Capital équivalent du pas PRÉCÉDENT : la seule échelle disponible
        # au moment où l'on prédit, et celle de la prédiction naïve de §4.3.
        previous = [row for row in self.tension_series if row["t"] == self.t - 1]
        aggregate = aggregate_rows(previous) if previous else []
        K_eq = aggregate[-1]["K_eq"] if aggregate else nan
        for entry in entries:
            old_value = entry.get("old_value")
            value = entry.get("value")
            if entry.get("param") == "gamma" and old_value is not None:
                # §4.3 : la prédiction qu'on ferait en supposant K = 1, où
                # K^{Δγ} = 1 quel que soit Δγ — donc « le levier ne fait rien ».
                naive_unit = 1.0
                naive_K_eq = K_eq ** (value - old_value) if K_eq == K_eq else nan
            elif old_value:
                naive_unit = value / old_value
                naive_K_eq = naive_unit
            else:
                naive_unit = nan
                naive_K_eq = nan
            entry["amplitude"] = {
                "h": 1,
                # Effectif de la cohorte contrefactuelle : les entités
                # rebasculées par l'intervention PLUS celles nées au même pas
                # quand la technologie de naissance a changé.
                "n_treated": n_probe,
                "n_retech": entry.get("n_selected"),
                "prod_total": production,
                "prod_total_cf": total_cf,
                "prod_treated": treated,
                "prod_treated_cf": treated_cf,
                "m_exact": m,
                "p_ex_ante": p,
                "identity_E": identity,
                "m_naive_unit_capital": naive_unit,
                "m_naive_K_eq": naive_K_eq,
                "K_eq_previous_step": K_eq,
                "joint": len(entries) > 1,
            }

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

    def _apply(
        self, intervention: Intervention
    ) -> tuple[dict[int, tuple[float, float]], bool]:
        """Applique une intervention. Retourne (sonde, défaut modifié).

        La SONDE est {identifiant traité -> (A, γ) d'avant} : elle est vide
        pour un paramètre de population, pour K0, et pour la portée `new` —
        qui ne touche aucune vivante. Le second membre dit si la technologie
        de NAISSANCE a changé : si oui, les entités nées au même pas portent
        déjà la nouvelle valeur et appartiennent à la cohorte traitée."""
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
            return {}, False

        if param == "K0":
            # `all` et `new` sont identiques par construction : K0 n'existe
            # qu'au moment de la naissance.
            intervention.old_value = self.config.K0
            self.config = replace(self.config, K0=value)
            intervention.n_selected = 0
            return {}, False

        # -- paramètres d'entité : A et gamma --------------------------------
        if param == "A":
            intervention.old_value = self.default_A
            new_of = lambda entity: (value, population.g[entity])  # noqa: E731
            new_default = (value, self.default_gamma)
        else:
            intervention.old_value = self.default_gamma
            new_of = lambda entity: (population.A[entity], value)  # noqa: E731
            new_default = (self.default_A, value)

        changed_default = False
        if scope in {"all", "new"} and new_default != (self.default_A, self.default_gamma):
            if self._birth_probe is None:
                self._birth_probe = (self.default_A, self.default_gamma)
            changed_default = True
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

        probe: dict[int, tuple[float, float]] = {}
        for entity in targets:
            probe[entity] = (population.A[entity], population.g[entity])
            coefficient, exponent = new_of(entity)
            population.retech(entity, coefficient, exponent, self.registry.intern(coefficient, exponent))

        self.kernel.sync_matrix()
        intervention.selected_ids = targets if scope == "fraction" else []
        intervention.n_selected = len(targets)
        return probe, changed_default

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
        birth_probe = self._birth_probe
        for _ in range(births):
            entity = population.born(config.K0, self.t, birth_A, birth_gamma, birth_tech)
            injected += config.K0
            if birth_probe is not None:
                self._amplitude_probe[entity] = birth_probe
        self._birth_probe = None

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
        # §4.1 : effectif et capital À L'INSTANT DE PRODUIRE, par technologie.
        # Ce sont les seules bases exactes de K_eq et de l'écart de Jensen ;
        # l'effectif de fin de pas, lui, a déjà perdu les morts du pas.
        n_prod_by_tech: defaultdict[int, int] = defaultdict(int)
        capital_prod_by_tech: defaultdict[int, float] = defaultdict(float)
        pop_A = population.A
        pop_g = population.g
        pop_tech = population.tech
        # §4.2 : contrefactuel d'amplitude, actif seulement au pas où une
        # intervention vient d'être appliquée (dictionnaire vide sinon).
        probe = self._amplitude_probe
        probe_treated = 0.0
        probe_treated_cf = 0.0
        for entity in alive:
            capital = population.K[entity]
            produced = pop_A[entity] * capital ** pop_g[entity]
            population.prod[entity] = produced
            population.K[entity] = capital + produced
            production += produced
            tech = pop_tech[entity]
            prod_by_tech[tech] += produced
            n_prod_by_tech[tech] += 1
            capital_prod_by_tech[tech] += capital
            if probe:
                previous = probe.get(entity)
                if previous is not None:
                    probe_treated += produced
                    probe_treated_cf += previous[0] * capital ** previous[1]
        if probe:
            self._close_amplitude(production, probe_treated, probe_treated_cf)

        # §3.2 : l'ordre relatif de ces deux phases est configurable. Sous
        # `v1` (défaut), on sert les intérêts sur le capital d'après
        # production, puis on déprécie ; sous `deprec_first`, l'inverse.
        if config.phase_order == "deprec_first":
            depreciated = _depreciate(population, alive, config)
            defaults, interest_paid, defaults_window = _service_interest(
                population, book, config, True
            )
        else:
            defaults, interest_paid, defaults_window = _service_interest(
                population, book, config, False
            )
            depreciated = _depreciate(population, alive, config)

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
        # Diagnostics du régime que le sens libre rend possible (§4.4) : une
        # entité de grand capital mais de faible rendement marginal peut
        # désormais céder son capital et vivre de l'intérêt. On mesure donc
        # (i) qui détient le capital et (ii) si la position nette est liée au
        # rendement marginal. `position nette` = créances − dettes ; une
        # entité est CRÉANCIÈRE NETTE si elle est strictement positive.
        # Les accès au carnet passent par `.get` : `claims` et `debts` sont des
        # `defaultdict`, une lecture par indice y créerait la clef.
        claims = book.claims
        debts = book.debts
        n_creditors = 0
        capital_creditors = 0.0
        sum_m = sum_net = sum_mm = sum_nn = sum_mn = 0.0
        sum_k = sum_kk = sum_kn = 0.0
        for entity in alive:
            capital = population.K[entity]
            exponent = pop_g[entity]
            capital_by_tech[pop_tech[entity]] += capital
            coefficient_sum += pop_A[entity]
            exponent_sum += exponent
            net = claims.get(entity, 0.0) - debts.get(entity, 0.0)
            if net > 0.0:
                n_creditors += 1
                capital_creditors += capital
            marginal = pop_A[entity] * exponent * max(capital, K_FLOOR) ** (exponent - 1.0)
            sum_m += marginal
            sum_net += net
            sum_mm += marginal * marginal
            sum_nn += net * net
            sum_mn += marginal * net
            sum_k += capital
            sum_kk += capital * capital
            sum_kn += capital * net
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
                "defaults_window": defaults_window,
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
                "mkt_reversed": market["reversed"],
                "mkt_volume_rev": market["volume_rev"],
                "n_creditors": n_creditors,
                "K_share_creditors": (
                    capital_creditors / capital_total if capital_total > 0 else float("nan")
                ),
                "corr_marg_net": _pearson(n_alive, sum_m, sum_net, sum_mm, sum_nn, sum_mn),
                "corr_K_net": _pearson(n_alive, sum_k, sum_net, sum_kk, sum_nn, sum_kn),
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
            coefficient = self.registry.A[tech]
            exponent = self.registry.gamma[tech]
            n_prod = n_prod_by_tech.get(tech, 0)
            capital_prod = capital_prod_by_tech.get(tech, 0.0)
            produced = prod_by_tech.get(tech, 0.0)
            capital = capital_by_tech.get(tech, 0.0)
            self.tech_series.append(
                {
                    "t": self.t,
                    "tech": tech,
                    "A": coefficient,
                    "gamma": exponent,
                    "n_alive": count,
                    "n_prod": n_prod,
                    "K": capital,
                    "K_prod": capital_prod,
                    "prod": produced,
                }
            )
            # §4.1 : la tension est une colonne NATIVE, calculée sur l'état
            # exact du pas et avec le δ courant (une intervention peut l'avoir
            # changé au début de ce pas — un dérivé a posteriori, qui ne lit
            # qu'un δ de fichier de configuration, ne le verrait pas).
            self.tension_series.append(
                tension_row(
                    self.t, tech, coefficient, exponent, config.delta,
                    count, n_prod, capital, capital_prod, produced,
                )
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
