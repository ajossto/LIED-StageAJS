from __future__ import annotations

import argparse
import csv
import importlib
import json
import math
import statistics as py_stats
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "modele-27-04-WIP" / "src"
RESULTS = ROOT / "modele-27-04-WIP" / "experiments" / "results"


def load_model():
    sys.path.insert(0, str(SRC))
    try:
        for name in ("config", "models", "statistics", "simulation"):
            sys.modules.pop(name, None)
        config_m = importlib.import_module("config")
        simulation_m = importlib.import_module("simulation")
    finally:
        sys.path.remove(str(SRC))
    return config_m, simulation_m


CONFIG_M, SIM_M = load_model()
SimulationConfig = CONFIG_M.SimulationConfig
Simulation = SIM_M.Simulation


def gini(values: list[float]) -> float:
    xs = sorted(v for v in values if v >= 0)
    n = len(xs)
    if n == 0:
        return 0.0
    total = sum(xs)
    if total <= 0:
        return 0.0
    weighted = sum((i + 1) * x for i, x in enumerate(xs))
    return (2 * weighted) / (n * total) - (n + 1) / n


def quantile(values: list[float], q: float) -> float:
    xs = sorted(values)
    if not xs:
        return 0.0
    pos = q * (len(xs) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (pos - lo) * (xs[hi] - xs[lo])


def mean_tail(rows: list[dict[str, Any]], key: str, burnin: int) -> float:
    xs = [float(row[key]) for row in rows[burnin:] if key in row]
    return py_stats.fmean(xs) if xs else 0.0


def std_tail(rows: list[dict[str, Any]], key: str, burnin: int) -> float:
    xs = [float(row[key]) for row in rows[burnin:] if key in row]
    return py_stats.pstdev(xs) if len(xs) > 1 else 0.0


def make_rounding_simulation(scale: float):
    class RoundedSimulation(Simulation):
        def _q(self, value: float) -> float:
            return round(value * scale) / scale

        def _quantize_state(self) -> None:
            entity_fields = (
                "alpha",
                "actif_liquide",
                "actif_prete",
                "actif_endoinvesti",
                "actif_exoinvesti",
                "passif_inne",
                "passif_endoinvesti",
                "passif_exoinvesti",
                "passif_credit_detenu",
                "passif_total",
                "charges_interets",
                "revenus_interets",
            )
            loan_fields = ("principal", "rate")
            for entity in self.entities.values():
                for field in entity_fields:
                    setattr(entity, field, self._q(getattr(entity, field)))
            for loan in self.loans.values():
                for field in loan_fields:
                    setattr(loan, field, self._q(getattr(loan, field)))

        def run_step(self) -> dict:
            result = super().run_step()
            self._quantize_state()
            return result

    return RoundedSimulation


def make_no_claim_transfer_simulation():
    class NoClaimTransferSimulation(Simulation):
        def _transfer_claims_for_payment(self, *args, **kwargs) -> float:
            return 0.0

    return NoClaimTransferSimulation


def make_simple_credit_simulation():
    class SimpleCreditSimulation(Simulation):
        def _borrowing_is_acceptable(self, borrower, amount, rate) -> bool:
            return amount > self.config.epsilon and self._gain_borrow(borrower, amount, rate) > 0

        def _debt_ratio_ok(self, borrower, principal, rate) -> bool:
            return True

    return SimpleCreditSimulation


def make_no_credit_simulation():
    class NoCreditSimulation(Simulation):
        def credit_market_iteration(self) -> int:
            return 0

    return NoCreditSimulation


def make_no_reliquefaction_simulation():
    class NoReliquefactionSimulation(Simulation):
        def _ensure_payment_capacity(self, payer, amount_due: float, creditor_id: int) -> float:
            if amount_due <= self.config.epsilon:
                return 0.0
            amount_remaining = amount_due
            paid = 0.0

            liquid_payment = min(payer.actif_liquide, amount_remaining)
            payer.actif_liquide -= liquid_payment
            amount_remaining -= liquid_payment
            paid += liquid_payment
            if amount_remaining <= self.config.epsilon:
                return paid

            r_star = self.compute_internal_rate(payer)
            payer_loan_ids = self._loans_by_lender.get(payer.entity_id, ())
            below_rstar = sorted(
                [self.loans[lid] for lid in payer_loan_ids if self.loans[lid].rate < r_star - self.config.epsilon],
                key=lambda x: (x.rate, x.loan_id),
            )
            if below_rstar:
                paid += self._transfer_claims_for_payment(payer.entity_id, creditor_id, amount_due - paid, below_rstar)

            if amount_due - paid > self.config.epsilon:
                r_star = self.compute_internal_rate(payer)
                payer_loan_ids = self._loans_by_lender.get(payer.entity_id, ())
                above_rstar = sorted(
                    [self.loans[lid] for lid in payer_loan_ids if self.loans[lid].rate >= r_star - self.config.epsilon],
                    key=lambda x: (x.rate, x.loan_id),
                )
                if above_rstar:
                    paid += self._transfer_claims_for_payment(payer.entity_id, creditor_id, amount_due - paid, above_rstar)
            return paid

    return NoReliquefactionSimulation


Variant = tuple[str, Callable[[SimulationConfig], SimulationConfig], type[Simulation]]


def cfg_replace(cfg: SimulationConfig, **kwargs) -> SimulationConfig:
    data = asdict(cfg)
    data.update(kwargs)
    return SimulationConfig(**data)


def variants() -> list[Variant]:
    return [
        ("baseline", lambda c: c, Simulation),
        ("no_brownian_alpha", lambda c: cfg_replace(c, alpha_sigma_brownien=0.0), Simulation),
        ("common_static_alpha", lambda c: cfg_replace(c, alpha_min=1.0, alpha_max=1.0, alpha_sigma_brownien=0.0), Simulation),
        ("no_births", lambda c: cfg_replace(c, lambda_creation=0.0), Simulation),
        ("no_credit", lambda c: c, make_no_credit_simulation()),
        ("k1_pure_arbitrage", lambda c: cfg_replace(c, n_candidats_pool=1), Simulation),
        ("k2_pool", lambda c: cfg_replace(c, n_candidats_pool=2), Simulation),
        ("k5_pool", lambda c: cfg_replace(c, n_candidats_pool=5), Simulation),
        ("no_debt_constraint", lambda c: cfg_replace(c, seuil_ratio_endettement=0.0), Simulation),
        ("no_reliquefaction", lambda c: c, make_no_reliquefaction_simulation()),
        ("no_claim_transfer", lambda c: c, make_no_claim_transfer_simulation()),
        ("no_auto_invest", lambda c: cfg_replace(c, fraction_auto_investissement=0.0), Simulation),
        ("exo_no_depreciation", lambda c: cfg_replace(c, taux_depreciation_exo=0.0), Simulation),
        ("epsilon_1e_3", lambda c: cfg_replace(c, epsilon=1e-3), Simulation),
        ("round_cent", lambda c: c, make_rounding_simulation(100.0)),
        ("round_integer", lambda c: c, make_rounding_simulation(1.0)),
        ("alpha_plus_10pct", lambda c: cfg_replace(c, alpha_min=c.alpha_min * 1.1, alpha_max=c.alpha_max * 1.1), Simulation),
    ]


def run_one(name: str, cfg: SimulationConfig, sim_cls: type[Simulation], steps: int, seed: int, burnin: int) -> dict[str, Any]:
    cfg = cfg_replace(cfg, duree_simulation=steps, seed=seed, freq_snapshot=max(steps + 1, 10))
    sim = sim_cls(cfg)
    started = time.perf_counter()
    sim.run(verbose=False)
    elapsed = time.perf_counter() - started

    alive = sim.active_entities()
    active_loans = sim.active_loans()
    passifs = [e.passif_total for e in alive]
    liquidities = [e.actif_liquide for e in alive]
    charges = [e.charges_interets for e in alive]
    revenues = [e.revenus_interets for e in alive]
    degrees_out = [len(sim._loans_by_lender.get(e.entity_id, ())) for e in alive]
    degrees_in = [len(sim._loans_by_borrower.get(e.entity_id, ())) for e in alive]
    cascades = [c.to_dict() for c in sim.collector.cascades]
    cascade_sizes = [c["nb_entites_faillie"] for c in cascades]

    extraction_mean = mean_tail(sim.stats, "extraction_total", burnin)
    tx_mean = mean_tail(sim.stats, "credit_transactions", burnin)
    loans_mean = mean_tail(sim.stats, "n_prets_actifs", burnin)
    pop_mean = mean_tail(sim.stats, "n_entities_alive", burnin)

    active_edges = len(active_loans)
    possible_edges = max(1, len(alive) * max(1, len(alive) - 1))
    active_both = sum(
        1 for e in alive
        if sim._loans_by_lender.get(e.entity_id) and sim._loans_by_borrower.get(e.entity_id)
    )
    class_gap = quantile(passifs, 0.9) / max(quantile(passifs, 0.1), cfg.epsilon) if passifs else 0.0
    financial_intermediation_share = active_both / len(alive) if alive else 0.0
    interest_class_corr_proxy = (
        py_stats.fmean(revenues) - py_stats.fmean(charges)
        if revenues and charges
        else 0.0
    )

    return {
        "variant": name,
        "seed": seed,
        "steps": steps,
        "elapsed_s": round(elapsed, 4),
        "ms_per_step": round(1000 * elapsed / steps, 4),
        "alive_final": len(alive),
        "created_total": len(sim.entities),
        "failures_total": sum(s["n_failures"] for s in sim.stats),
        "cascade_events": len(cascades),
        "cascade_max": max(cascade_sizes) if cascade_sizes else 0,
        "cascade_mean_size": round(py_stats.fmean(cascade_sizes), 4) if cascade_sizes else 0.0,
        "extraction_tail_mean": round(extraction_mean, 4),
        "extraction_tail_std": round(std_tail(sim.stats, "extraction_total", burnin), 4),
        "credit_tx_tail_mean": round(tx_mean, 4),
        "active_loans_tail_mean": round(loans_mean, 4),
        "population_tail_mean": round(pop_mean, 4),
        "active_loans_final": len(active_loans),
        "loan_density_final": round(active_edges / possible_edges, 8),
        "degree_in_mean": round(py_stats.fmean(degrees_in), 4) if degrees_in else 0.0,
        "degree_out_mean": round(py_stats.fmean(degrees_out), 4) if degrees_out else 0.0,
        "intermediary_share": round(financial_intermediation_share, 6),
        "passif_gini": round(gini(passifs), 6),
        "liquidity_gini": round(gini(liquidities), 6),
        "class_gap_p90_p10": round(class_gap, 4),
        "mean_net_interest_proxy": round(interest_class_corr_proxy, 4),
        "final_extraction": sim.stats[-1]["extraction_total"],
        "final_credit_tx": sim.stats[-1]["credit_transactions"],
        "final_active_loans": sim.stats[-1]["n_prets_actifs"],
        "final_liquidity": sim.stats[-1]["liquidite_totale"],
        "final_passif_system": sim.stats[-1]["passif_total_systeme"],
        "final_actif_system": sim.stats[-1]["actif_total_systeme"],
    }


def aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = [
        "elapsed_s",
        "ms_per_step",
        "alive_final",
        "failures_total",
        "cascade_events",
        "cascade_max",
        "extraction_tail_mean",
        "credit_tx_tail_mean",
        "active_loans_tail_mean",
        "population_tail_mean",
        "active_loans_final",
        "loan_density_final",
        "degree_in_mean",
        "degree_out_mean",
        "intermediary_share",
        "passif_gini",
        "liquidity_gini",
        "class_gap_p90_p10",
        "final_liquidity",
        "final_passif_system",
        "final_actif_system",
    ]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["variant"], []).append(row)

    out = []
    for variant, items in sorted(grouped.items()):
        agg = {"variant": variant, "n": len(items)}
        for key in keys:
            vals = [float(item[key]) for item in items]
            agg[f"{key}_mean"] = round(py_stats.fmean(vals), 6)
            agg[f"{key}_std"] = round(py_stats.pstdev(vals), 6) if len(vals) > 1 else 0.0
        out.append(agg)
    return out


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--burnin", type=int, default=150)
    parser.add_argument("--seeds", nargs="*", type=int, default=[42, 7, 123])
    parser.add_argument("--only", nargs="*", default=None)
    parser.add_argument("--output-stem", default="elagage")
    args = parser.parse_args()

    selected = variants()
    if args.only:
        wanted = set(args.only)
        selected = [v for v in selected if v[0] in wanted]

    rows = []
    base_cfg = SimulationConfig()
    for name, cfg_fn, sim_cls in selected:
        for seed in args.seeds:
            cfg = cfg_fn(base_cfg)
            row = run_one(name, cfg, sim_cls, args.steps, seed, args.burnin)
            rows.append(row)
            print(
                f"{name:22s} seed={seed:<3d} "
                f"extract={row['extraction_tail_mean']:<10.1f} "
                f"tx={row['credit_tx_tail_mean']:<7.2f} "
                f"fail={row['failures_total']:<4d} "
                f"loans={row['active_loans_final']:<6d} "
                f"{row['elapsed_s']:.2f}s",
                flush=True,
            )

    agg = aggregate(rows)
    stem = args.output_stem
    write_csv(RESULTS / f"{stem}_runs.csv", rows)
    write_csv(RESULTS / f"{stem}_aggregate.csv", agg)
    (RESULTS / f"{stem}_runs.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    (RESULTS / f"{stem}_aggregate.json").write_text(json.dumps(agg, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
