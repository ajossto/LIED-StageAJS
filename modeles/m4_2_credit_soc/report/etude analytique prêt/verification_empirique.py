#!/usr/bin/env python3
"""Vérification Monte-Carlo minimale de l'étude analytique à deux entités.

Le programme reproduit exactement l'ordre choc -> production -> intérêts
-> dépréciation -> faillite de M4.2 après l'émission de l'unique prêt.
Il ne sert pas à établir les résultats : il compare notamment la fréquence
de T_B=1 à la formule normale fermée du rapport et exporte les lois
empiriques arrêtées dans un fichier NPZ.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np


def phi_gamma(z: np.ndarray | float, gamma: float) -> np.ndarray | float:
    """Capital après choc et production, avant service et dépréciation."""
    return z + np.power(z, gamma)


def inverse_phi(value: float, gamma: float) -> float:
    """Résout z + z**gamma = value par dichotomie monotone."""
    if value <= 0.0:
        return 0.0
    lower = 0.0
    upper = max(1.0, value)
    for _ in range(100):
        middle = 0.5 * (lower + upper)
        if middle + middle**gamma < value:
            lower = middle
        else:
            upper = middle
    return 0.5 * (lower + upper)


def standard_normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def loan_terms(k1: float, k2: float, scheme: str) -> tuple[float, float, float]:
    """Renvoie (q, capital prêteuse, capital emprunteuse) après transfert."""
    if scheme == "arithmetic":
        q = 0.5 * (k1 - k2)
    elif scheme == "geometric":
        q = math.sqrt(k1 * k2) - k2
    else:  # garde défensive, argparse contrôle déjà la valeur
        raise ValueError(f"Règle inconnue: {scheme}")
    return q, k1 - q, k2 + q


def first_step_death_probability(
    borrower_initial: float,
    q: float,
    r: float,
    gamma: float,
    delta: float,
    sigma: float,
) -> float:
    """Formule (risque conditionnel) du rapport au premier pas."""
    d = 1.0 - delta
    z_star = inverse_phi(q * (r + 1.0 / d), gamma)
    threshold = z_star / borrower_initial
    if sigma == 0.0:
        return float(1.0 < threshold)
    argument = (math.log(threshold) + 0.5 * sigma**2) / sigma
    return standard_normal_cdf(argument)


def simulate(args: argparse.Namespace) -> dict[str, np.ndarray | float | str]:
    q, lender0, borrower0 = loan_terms(args.k1, args.k2, args.scheme)
    d = 1.0 - args.delta
    c = args.rate * q
    rng = np.random.default_rng(args.seed)

    lender = np.full(args.paths, lender0, dtype=np.float64)
    borrower = np.full(args.paths, borrower0, dtype=np.float64)
    borrower_alive = np.ones(args.paths, dtype=bool)

    borrower_death_time = np.full(args.paths, np.inf, dtype=np.float64)
    lender_at_borrower_death = np.full(args.paths, np.nan, dtype=np.float64)
    borrower_pre_liquidation = np.full(args.paths, np.nan, dtype=np.float64)
    # 0 = censurée, 1 = défaut de liquidité, 2 = insolvabilité avec service complet
    death_cause = np.zeros(args.paths, dtype=np.int8)

    for step in range(1, args.max_steps + 1):
        # La prêteuse vit toujours, y compris après la mort de l'emprunteuse.
        xi_lender = rng.normal(-0.5 * args.sigma**2, args.sigma, args.paths)
        resources_lender = phi_gamma(lender * np.exp(xi_lender), args.gamma)
        payment = np.zeros(args.paths, dtype=np.float64)

        indices = np.flatnonzero(borrower_alive)
        if indices.size:
            xi_borrower = rng.normal(
                -0.5 * args.sigma**2, args.sigma, indices.size
            )
            resources_borrower = phi_gamma(
                borrower[indices] * np.exp(xi_borrower), args.gamma
            )
            payment_alive = np.minimum(c, resources_borrower)
            payment[indices] = payment_alive

            candidate_borrower = d * np.maximum(resources_borrower - c, 0.0)
            survives = resources_borrower >= c + q / d
            dying_indices = indices[~survives]
            surviving_indices = indices[survives]

            borrower[surviving_indices] = candidate_borrower[survives]
            if dying_indices.size:
                borrower_death_time[dying_indices] = step
                borrower_pre_liquidation[dying_indices] = candidate_borrower[~survives]
                liquidity = resources_borrower[~survives] < c
                death_cause[dying_indices] = np.where(liquidity, 1, 2)
                borrower[dying_indices] = 0.0
                borrower_alive[dying_indices] = False

        lender = d * (resources_lender + payment)

        # Le capital de la prêteuse est enregistré après réception du paiement
        # et dépréciation, au même instant que le capital pré-liquidation de B.
        newly_dead = borrower_death_time == step
        lender_at_borrower_death[newly_dead] = lender[newly_dead]

    analytic_p1 = first_step_death_probability(
        borrower0, q, args.rate, args.gamma, args.delta, args.sigma
    )
    empirical_p1 = float(np.mean(borrower_death_time == 1.0))

    return {
        "scheme": args.scheme,
        "q": q,
        "lender_initial": lender0,
        "borrower_initial": borrower0,
        "borrower_death_time": borrower_death_time,
        "lender_death_time": np.full(args.paths, np.inf, dtype=np.float64),
        "lender_at_borrower_death": lender_at_borrower_death,
        "borrower_pre_liquidation": borrower_pre_liquidation,
        "death_cause": death_cause,
        "lender_at_horizon": lender,
        "borrower_at_horizon": borrower,
        "analytic_first_step_death_probability": analytic_p1,
        "empirical_first_step_death_probability": empirical_p1,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k1", type=float, required=True, help="Capital riche pré-prêt")
    parser.add_argument("--k2", type=float, required=True, help="Capital pauvre pré-prêt")
    parser.add_argument("--gamma", type=float, default=0.5)
    parser.add_argument("--delta", type=float, default=0.05)
    parser.add_argument("--sigma", type=float, default=0.25)
    parser.add_argument("--rate", type=float, default=0.1, help="Taux r dans [0,1]")
    parser.add_argument(
        "--scheme", choices=("arithmetic", "geometric"), default="arithmetic"
    )
    parser.add_argument("--paths", type=int, default=100_000)
    parser.add_argument("--max-steps", type=int, default=2_000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--output", type=Path, default=Path("distributions_empiriques.npz")
    )
    args = parser.parse_args()

    if not (args.k1 > args.k2 > 0.0):
        parser.error("Il faut k1 > k2 > 0.")
    if not (0.0 < args.gamma < 1.0):
        parser.error("Il faut 0 < gamma < 1.")
    if not (0.0 <= args.delta < 1.0):
        parser.error("Il faut 0 <= delta < 1.")
    if args.sigma < 0.0:
        parser.error("Il faut sigma >= 0.")
    if not (0.0 <= args.rate <= 1.0):
        parser.error("Il faut 0 <= rate <= 1.")
    if args.paths < 1 or args.max_steps < 1:
        parser.error("paths et max-steps doivent être positifs.")
    return args


def main() -> None:
    args = parse_args()
    result = simulate(args)
    arrays = {key: value for key, value in result.items() if isinstance(value, np.ndarray)}
    metadata = {key: value for key, value in result.items() if not isinstance(value, np.ndarray)}
    metadata.update(
        {
            "k1": args.k1,
            "k2": args.k2,
            "gamma": args.gamma,
            "delta": args.delta,
            "sigma": args.sigma,
            "rate": args.rate,
            "paths": args.paths,
            "max_steps": args.max_steps,
            "seed": args.seed,
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output, metadata=json.dumps(metadata), **arrays)

    finite = np.isfinite(arrays["borrower_death_time"])
    summary = dict(metadata)
    summary.update(
        {
            "observed_death_fraction": float(np.mean(finite)),
            "censored_paths": int(np.sum(~finite)),
            "mean_death_time_uncensored": (
                float(np.mean(arrays["borrower_death_time"][finite]))
                if np.any(finite)
                else None
            ),
            "output": str(args.output),
        }
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
