"""Institution de principal de M4.3Live : le transfert qui maximise la
production jointe d'une paire immédiatement après l'échange.

Problème résolu (rapport `prompts/rapport_architecture_offline_online.pdf`
§1, éq. 1), avec x = K_b (emprunteuse/receveuse), y = K_ℓ (prêteuse/
donneuse), (a, α) = (A_b, γ_b), (b, β) = (A_ℓ, γ_ℓ) :

    max_{-x ≤ δ ≤ y}  a (x+δ)^α + b (y-δ)^β,      0 < α, β < 1, a, b > 0.

L'objectif est strictement concave en δ et sa dérivée diverge vers +∞ en
δ → -x et vers -∞ en δ → y : l'optimum est intérieur et unique. En posant
C = x + y (somme conservée par l'échange) et h(C) = C λ* le capital
optimal attribué à l'emprunteuse, la solution s'écrit exactement

    δ*(x, y) = h(C) - x                                    (rapport éq. 10)

et toute la non-linéarité est portée par la seule variable C, à couple de
technologies fixé (Hessien exactement de rang un, rapport §6, éq. 29).

Trois régimes, routés sur des identifiants ENTIERS de technologie (rapport
§7.1 ; jamais sur une comparaison de flottants) :

- (a) `s_b == s_l` — même technologie exactement. λ* = 1/2 et le transfert
  vaut (K_ℓ - K_b)/2. Ce cas est routé sur l'égalité des identifiants et
  la formule littérale est appliquée telle quelle, ce qui redonne la règle
  arithmétique de M4.3 (`m4_3_credit_soc/m4_3/model.py:288-289`) BIT À BIT
  et par construction, pas par coïncidence numérique.
- (b) `γ_b == γ_l`, `A_b ≠ A_l` — forme fermée exacte (rapport éq. 14) :
      λ* = A_b^{1/(1-γ)} / (A_b^{1/(1-γ)} + A_ℓ^{1/(1-γ)}).
  Le logarithme/exponentielle est payé UNE FOIS à la création du couple de
  technologies, jamais par transaction. λ* ≠ 1/2 dès que A_b ≠ A_ℓ : une
  intervention qui ne change que A fait donc sortir toute paire mixte du
  régime (a) vers un partage PONDÉRÉ du capital.
- (c) `γ_b ≠ γ_l` — pas de forme fermée. Résolution en (t, u, z) :
      t = -z/2 + u L(z),  L(z) = ln(2 cosh(z/2)),  λ* = σ(z)   (éq. 15-17)
  avec u = (γ_ℓ - γ_b)/(2 - γ_b - γ_ℓ) et t = t0 + u ln C. |u| < 1 tant
  que γ ∈ ]0,1[, donc F(z) = -z/2 + u L(z) - t est strictement décroissante
  avec |F'| ≥ (1-|u|)/2 > 0 : Newton est sûr et le repli point fixe
  z ← -2t + 2u L(z) est globalement contractant de facteur |u|.

Politiques de cache (`kernel_policy`) :

- `"exact_lut"` (DÉFAUT) : chemins (a)/(b) en forme fermée, chemin (c) en
  Newton exact, puis LUT 1D de h(C) construite paresseusement par ligne
  d'exposant `frexp` après un seuil d'usages. Les nœuds de la table sont
  des solutions Newton exactes et l'interpolation est une cubique de
  Hermite alimentée par h'(C) = q h / S (rapport éq. 12) : aucune
  approximation grossière n'entre jamais dans la trajectoire.
- `"hybrid"` : architecture littérale du rapport §11 — ajoute un chemin
  TIÈDE (une étape de Newton depuis z0 = -2t, rapport éq. 21) pendant la
  phase d'observation d'une ligne. Plus rapide, mais son erreur sur δ est
  de l'ordre de 10⁻¹ en unités de capital sur le domaine réel (table du
  rapport §8.1) — voir `report/conception_m4_3live_v2.pdf` pour la
  justification du défaut retenu.

DÉTERMINISME. La construction d'une ligne de table est déclenchée par un
compteur d'usages qui ne dépend que de la séquence simulée, et elle est
exécutée EN SYNCHRONE au point de déclenchement. Le rapport suggère de la
déporter sur un thread (§7.2) : cette suggestion est refusée ici, car un
build asynchrone ferait basculer la table à un indice d'appel dépendant de
l'ordonnancement, ce qui casserait le rejeu strictement identique exigé
par le prompt (§4, §8). Aucun tirage aléatoire n'est consommé nulle part
dans ce module.
"""

from __future__ import annotations

import math

__all__ = [
    "TechRegistry",
    "PrincipalKernel",
    "newton_z",
    "lambda_star",
    "joint_production_gain",
    "KERNEL_POLICIES",
]


KERNEL_POLICIES = ("exact_lut", "hybrid")

# Tolérance absolue sur F(z). |F'| ≥ (1-|u|)/2, donc l'erreur sur z est au
# plus 2|F|/(1-|u|) : 1e-14 sur F donne un z au niveau du bruit d'arrondi.
NEWTON_TOL = 1e-14
NEWTON_MAX_ITER = 100

# Régimes (valeurs entières : le routage est un test d'entier, pas de str).
KIND_IDENTITY = 0
KIND_SAME_GAMMA = 1
KIND_GENERAL = 2


def _log_two_cosh_half(z: float) -> float:
    """L(z) = ln(2 cosh(z/2)), évalué sans débordement pour |z| grand."""
    az = -z if z < 0.0 else z
    return 0.5 * az + math.log1p(math.exp(-az))


def _sigmoid(z: float) -> float:
    """σ(z) = 1/(1+e^{-z}), sans débordement des deux côtés."""
    if z >= 0.0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def newton_z(t: float, u: float) -> float:
    """Résout exactement t = -z/2 + u·L(z) (rapport éq. 17).

    Newton depuis z0 = -2t (la solution exacte quand u = 0), avec repli sur
    l'itération de point fixe z ← -2t + 2u·L(z) — contractante de facteur
    |u| < 1 sur tout R (rapport §4.2) — dès qu'un pas de Newton n'améliore
    pas |F|. La convergence est donc globale.
    """
    z = -2.0 * t
    if u == 0.0:
        return z
    for _ in range(NEWTON_MAX_ITER):
        el = _log_two_cosh_half(z)
        f = -0.5 * z + u * el - t
        if -NEWTON_TOL <= f <= NEWTON_TOL:
            return z
        df = -0.5 + 0.5 * u * math.tanh(0.5 * z)
        z_new = z - f / df
        if not math.isfinite(z_new):
            z_new = -2.0 * t + 2.0 * u * el
        else:
            f_new = -0.5 * z_new + u * _log_two_cosh_half(z_new) - t
            if not (abs(f_new) < abs(f)):
                z_new = -2.0 * t + 2.0 * u * el
        if z_new == z:
            return z
        z = z_new
    return z


def newton_z_one_step(t: float, u: float) -> float:
    """Une seule étape de Newton depuis z0 = -2t (rapport éq. 21).

    z1 = -2t + 2u ln(2 cosh t) / (1 + u tanh t). Chemin TIÈDE : pas de
    table, pas de boucle, erreur non nulle (voir docstring du module).
    """
    if u == 0.0:
        return -2.0 * t
    return -2.0 * t + 2.0 * u * _log_two_cosh_half(2.0 * t) / (1.0 + u * math.tanh(t))


def lambda_star(a: float, alpha: float, b: float, beta: float, capital_sum: float) -> float:
    """λ* de référence, calculé sans cache — utilisé par les tests (§8).

    (a, α) est la technologie de l'entité qui REÇOIT le capital, (b, β)
    celle qui le donne ; λ* est la part de C = x + y attribuée à la
    receveuse à l'optimum.
    """
    if capital_sum <= 0.0:
        raise ValueError("C = x + y doit être strictement positif")
    if alpha == beta:
        exponent = 1.0 / (1.0 - alpha)
        wa = a**exponent
        wb = b**exponent
        return wa / (wa + wb)
    denom = 2.0 - alpha - beta
    u = (beta - alpha) / denom
    t = (math.log(b * beta / (a * alpha)) + (beta - alpha) * math.log(capital_sum)) / denom
    return _sigmoid(newton_z(t, u))


def joint_production_gain(
    a: float, alpha: float, b: float, beta: float, x: float, y: float, delta: float
) -> float:
    """Surplus coopératif Δ d'un transfert δ (§3.4 du prompt).

    Δ = [a(x+δ)^α + b(y-δ)^β] - [a x^α + b y^β] : gain de production
    JOINTE PAR PAS, l'entité (a,α) recevant δ.
    """
    before = a * x**alpha + b * y**beta
    after = a * (x + delta) ** alpha + b * (y - delta) ** beta
    return after - before


class TechRegistry:
    """Internalise les couples (A, γ) exacts en identifiants entiers.

    Le support technologique de M4.3Live est discret et fini : une
    intervention crée au plus une valeur nouvelle. On indexe donc sur
    l'égalité EXACTE des flottants (rapport §6.1 : ce sont des catégories,
    pas des perturbations continues), jamais sur une distance.
    """

    def __init__(self) -> None:
        self.A: list[float] = []
        self.gamma: list[float] = []
        self._index: dict[tuple[float, float], int] = {}

    def __len__(self) -> int:
        return len(self.A)

    def intern(self, coefficient: float, exponent: float) -> int:
        key = (coefficient, exponent)
        tech_id = self._index.get(key)
        if tech_id is not None:
            return tech_id
        tech_id = len(self.A)
        self.A.append(coefficient)
        self.gamma.append(exponent)
        self._index[key] = tech_id
        return tech_id

    def describe(self, tech_id: int) -> dict:
        return {"tech": tech_id, "A": self.A[tech_id], "gamma": self.gamma[tech_id]}


class _Entry:
    """Noyau d'un couple ORDONNÉ (technologie receveuse, technologie donneuse)."""

    __slots__ = (
        "kind",
        "lam",
        "p",
        "q",
        "u",
        "t0",
        "rows",
        "counts",
        "points",
        "threshold",
    )

    def __init__(self, kind: int) -> None:
        self.kind = kind
        self.lam = 0.5
        self.p = 0.0
        self.q = 0.0
        self.u = 0.0
        self.t0 = 0.0
        # ligne d'exposant frexp -> (c0, c1, c2, c3, inv_step) ; c* listes.
        self.rows: dict[int, tuple] = {}
        self.counts: dict[int, int] = {}
        self.points = 65
        self.threshold = 1800

    # -- régime (c) : résolution exacte -----------------------------------
    def h_exact(self, capital_sum: float) -> float:
        t = self.t0 + self.u * math.log(capital_sum)
        return _sigmoid(newton_z(t, self.u)) * capital_sum

    def h_warm(self, capital_sum: float) -> float:
        t = self.t0 + self.u * math.log(capital_sum)
        return _sigmoid(newton_z_one_step(t, self.u)) * capital_sum

    def h_prime(self, capital_sum: float, h: float) -> float:
        """h'(C) = q h / S, S = p (C-h) + q h (rapport éq. 12)."""
        s = self.p * (capital_sum - h) + self.q * h
        return self.q * h / s

    def build_row(self, exponent: int) -> None:
        """Compile la ligne frexp d'exposant ``exponent`` (aucun RNG)."""
        n = self.points
        step = 0.5 / (n - 1)
        scale = math.ldexp(1.0, exponent)
        values: list[float] = []
        slopes: list[float] = []
        for index in range(n):
            mantissa = 0.5 + index * step
            capital_sum = math.ldexp(mantissa, exponent)
            h = self.h_exact(capital_sum)
            values.append(h)
            # dérivée par rapport à la mantisse, remise à l'échelle du pas
            slopes.append(self.h_prime(capital_sum, h) * scale * step)
        c0: list[float] = []
        c1: list[float] = []
        c2: list[float] = []
        c3: list[float] = []
        for index in range(n - 1):
            y0 = values[index]
            y1 = values[index + 1]
            d0 = slopes[index]
            d1 = slopes[index + 1]
            c0.append(y0)
            c1.append(d0)
            c2.append(-3.0 * y0 - 2.0 * d0 + 3.0 * y1 - d1)
            c3.append(2.0 * y0 + d0 - 2.0 * y1 + d1)
        self.rows[exponent] = (c0, c1, c2, c3, (n - 1) / 0.5)


class PrincipalKernel:
    """Matrice dense de noyaux, créée à la volée (rapport §7.1, §11).

    ``solve(s_b, s_l, x, y)`` retourne le transfert optimal NON CONTRAINT
    δ* (il peut être négatif : voir `model.py`, qui compte séparément les
    paires refusées parce que l'optimum jointe voudrait faire circuler le
    capital du pauvre vers le riche, sens interdit par le marché).
    """

    def __init__(
        self,
        registry: TechRegistry,
        policy: str = "exact_lut",
        threshold: int = 1800,
        points: int = 65,
    ) -> None:
        if policy not in KERNEL_POLICIES:
            raise ValueError(f"kernel_policy doit être dans {KERNEL_POLICIES}")
        if points < 3:
            raise ValueError("lut_points >= 3 requis")
        self.registry = registry
        self.policy = policy
        self.threshold = int(threshold)
        self.points = int(points)
        self.matrix: list[list[_Entry | None]] = []
        self.path_counts = {
            "identity": 0,
            "same_gamma": 0,
            "lut": 0,
            "warm": 0,
            "newton": 0,
            "build": 0,
        }
        self.sync_matrix()

    # -- structure ---------------------------------------------------------
    def sync_matrix(self) -> None:
        """Étend la matrice dense après l'apparition de technologies."""
        size = len(self.registry)
        for row in self.matrix:
            while len(row) < size:
                row.append(None)
        while len(self.matrix) < size:
            self.matrix.append([None] * size)

    def _entry(self, receiver: int, donor: int) -> _Entry:
        entry = self.matrix[receiver][donor]
        if entry is not None:
            return entry
        a = self.registry.A[receiver]
        alpha = self.registry.gamma[receiver]
        b = self.registry.A[donor]
        beta = self.registry.gamma[donor]
        if alpha == beta:
            entry = _Entry(KIND_SAME_GAMMA)
            exponent = 1.0 / (1.0 - alpha)
            wa = a**exponent
            wb = b**exponent
            entry.lam = wa / (wa + wb)
        else:
            entry = _Entry(KIND_GENERAL)
            denom = 2.0 - alpha - beta
            entry.p = 1.0 - alpha
            entry.q = 1.0 - beta
            entry.u = (beta - alpha) / denom
            entry.t0 = math.log(b * beta / (a * alpha)) / denom
            entry.points = self.points
            entry.threshold = self.threshold
        self.matrix[receiver][donor] = entry
        return entry

    # -- résolution --------------------------------------------------------
    def solve(self, receiver: int, donor: int, x: float, y: float) -> float:
        """Transfert optimal non contraint δ* de la donneuse vers la receveuse."""
        if receiver == donor:
            # Régime (a), routé sur l'identité des technologies : formule
            # littérale de M4.3 (m4_3/model.py:289), bit à bit.
            self.path_counts["identity"] += 1
            return 0.5 * (y - x)

        entry = self._entry(receiver, donor)
        capital_sum = x + y
        if entry.kind == KIND_SAME_GAMMA:
            self.path_counts["same_gamma"] += 1
            return entry.lam * capital_sum - x

        if capital_sum <= 0.0:
            return 0.0

        mantissa, exponent = math.frexp(capital_sum)
        row = entry.rows.get(exponent)
        if row is not None:
            self.path_counts["lut"] += 1
            c0, c1, c2, c3, inv_step = row
            position = (mantissa - 0.5) * inv_step
            index = int(position)
            if index >= entry.points - 1:
                index = entry.points - 2
            elif index < 0:
                index = 0
            s = position - index
            h = ((c3[index] * s + c2[index]) * s + c1[index]) * s + c0[index]
            return h - x

        count = entry.counts.get(exponent, 0) + 1
        entry.counts[exponent] = count
        if count >= entry.threshold:
            # Compilation synchrone, déterministe, sans RNG.
            self.path_counts["build"] += 1
            entry.build_row(exponent)
            return self.solve(receiver, donor, x, y)
        if self.policy == "hybrid" and count > 1:
            self.path_counts["warm"] += 1
            return entry.h_warm(capital_sum) - x
        self.path_counts["newton"] += 1
        return entry.h_exact(capital_sum) - x

    def solve_exact(self, receiver: int, donor: int, x: float, y: float) -> float:
        """Référence exacte, sans cache : utilisée par les tests (§8)."""
        if receiver == donor:
            return 0.5 * (y - x)
        entry = self._entry(receiver, donor)
        capital_sum = x + y
        if entry.kind == KIND_SAME_GAMMA:
            return entry.lam * capital_sum - x
        return entry.h_exact(capital_sum) - x

    def describe(self) -> dict:
        """État du cache, pour le journal de run et le rapport de conception."""
        tables = []
        for receiver, row in enumerate(self.matrix):
            for donor, entry in enumerate(row):
                if entry is None or entry.kind != KIND_GENERAL:
                    continue
                tables.append(
                    {
                        "receiver": receiver,
                        "donor": donor,
                        "u": entry.u,
                        "rows": sorted(entry.rows),
                        "observed": dict(sorted(entry.counts.items())),
                    }
                )
        return {
            "policy": self.policy,
            "threshold": self.threshold,
            "points": self.points,
            "n_tech": len(self.registry),
            "path_counts": dict(self.path_counts),
            "tables": tables,
        }
