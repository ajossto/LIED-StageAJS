"""Écriture des données primaires d'une simulation M4.2B.

Le schéma des tables reprend exactement celui de M4.2 (les 28 recettes de
figures Simulation Lab relisent series.csv/avalanches.csv/snapshots par nom
de colonne, parité §20 du prompt) ; une table supplémentaire
``loan_events.csv`` enregistre, PAR TRANSACTION réussie du marché du crédit,
les diagnostics r, q, rq et rq/K_b', rq/F_γ(K_b') demandés en §3 du prompt
(surveillance explicite du service par rapport au capital/à la production de
l'emprunteuse au moment de la création ou de la fusion d'un contrat).
"""

from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path
from typing import Callable

import numpy as np

from .model import Config, Simulation


MODEL_VERSION = "m4_2b-1"
FIXED_RULES = {
    "phase_order": "births_shock_production_interest_depreciation_market_bankruptcy_measures",
    "shock": "iid_lognormal_mean_one_xi",
    "production": "A_K_gamma_fully_retained",
    "market_objective": "income",
    "market_intensity": "eta_rho_beta_family",
    "pool_size": 2,
    "rate_rule": "geometric_mean_of_marginal_returns",
    "principal_rule": "config.target_rule (arithmetic baseline, geometric = M4.2 ablation)",
    "loan_pairs": "merged_perpetual",
    "bankruptcy": "cancel_and_destroy",
}

SERIES_FIELDS = [
    "t", "births", "deaths", "pop", "K_tot", "nw_tot", "prod_tot",
    "n_loans", "new_loans", "loan_volume", "interest_paid", "defaults",
    "roots_liquidity", "roots_insolvency", "roots_both", "cascade_iters",
    "n_avalanches", "max_avalanche", "claim_losses", "destroyed",
    "injected", "depreciated", "shock_gain",
    "mkt_pool", "mkt_rounds", "mkt_new_edges", "mkt_merges",
]
AVALANCHE_FIELDS = [
    "avalanche_id", "t", "size", "depth", "n_roots", "volume_j", "causes",
]
MEMBER_FIELDS = ["avalanche_id", "t", "id", "is_root", "generation"]
DEATH_FIELDS = [
    "t", "id", "age", "cause", "death_iter", "K", "claims", "debts", "nw",
    "deg_out", "deg_in",
]
ENTITY_FIELDS = ["id", "birth_t", "death_t", "death_cause", "alive_final"]
LOAN_FIELDS = ["loan_id", "lender", "borrower", "q", "r"]
LOAN_EVENT_FIELDS = [
    "t", "loan_id", "lender", "borrower", "merged", "q", "r", "rq",
    "Kb_after", "rq_over_Kb", "rq_over_F",
]
INDIVIDUAL_FIELDS = [
    "t", "id", "birth_t", "age", "alive", "death_cause", "death_iter",
    "K", "claims", "debts", "nw", "prod", "int_in", "int_out", "income",
    "income_net", "defaulted", "deg_out", "deg_in",
]


class RunRecorder:
    """Écrit les instantanés pendant le run, puis les tables finales."""

    def __init__(
        self,
        directory: str | Path,
        config: Config,
        snapshot_every: int,
        individual_every: int,
    ) -> None:
        self.directory = Path(directory)
        self.snapshots = self.directory / "snapshots"
        self.individual_every = individual_every
        self.final_t = config.T
        self.individual_rows = 0
        self.directory.mkdir(parents=True, exist_ok=True)
        self.snapshots.mkdir(exist_ok=True)
        self._individual_stream = gzip.open(
            self.directory / "individual_series.csv.gz",
            "wt",
            newline="",
            encoding="utf-8",
        )
        self._individual_writer = csv.DictWriter(
            self._individual_stream, fieldnames=INDIVIDUAL_FIELDS
        )
        self._individual_writer.writeheader()
        self._loan_events_stream = gzip.open(
            self.directory / "loan_events.csv.gz",
            "wt",
            newline="",
            encoding="utf-8",
        )
        self._loan_events_writer = csv.DictWriter(
            self._loan_events_stream, fieldnames=LOAN_EVENT_FIELDS
        )
        self._loan_events_writer.writeheader()
        self.loan_events_total = 0

        self._deaths_stream = (self.directory / "deaths.csv").open("w", newline="", encoding="utf-8")
        self._deaths_writer = csv.DictWriter(self._deaths_stream, fieldnames=DEATH_FIELDS)
        self._deaths_writer.writeheader()
        self.deaths_total = 0
        self._death_lookup: dict[int, tuple[int, str]] = {}

        self._avalanches_stream = (self.directory / "avalanches.csv").open("w", newline="", encoding="utf-8")
        self._avalanches_writer = csv.DictWriter(self._avalanches_stream, fieldnames=AVALANCHE_FIELDS)
        self._avalanches_writer.writeheader()
        self.avalanches_total = 0
        self.avalanche_roots_total = 0
        self.avalanche_size_total = 0

        self._avalanche_members_stream = (self.directory / "avalanche_members.csv").open(
            "w", newline="", encoding="utf-8"
        )
        self._avalanche_members_writer = csv.DictWriter(
            self._avalanche_members_stream, fieldnames=MEMBER_FIELDS
        )
        self._avalanche_members_writer.writeheader()

        provenance = {
            "model_version": MODEL_VERSION,
            "parameters": config.to_dict(),
            "fixed_rules": FIXED_RULES,
            "recording": {
                "snapshot_every": snapshot_every,
                "individual_every": individual_every,
            },
        }
        self._write_json("config.json", provenance)

    def snapshot(self, t: int, entities: dict, network: dict) -> None:
        np.savez_compressed(self.snapshots / f"entities_t{t:05d}.npz", **entities)
        np.savez_compressed(self.snapshots / f"network_t{t:05d}.npz", **network)

    def record_individuals(self, simulation: Simulation) -> None:
        """Écrit les trajectoires sans les accumuler dans la mémoire du moteur."""
        if self.individual_every == 0:
            return
        include_living = (
            simulation.t % self.individual_every == 0
            or simulation.t == self.final_t
            or simulation.status != "ok"
        )
        rows = simulation.individual_records(include_living=include_living)
        self._individual_writer.writerows(rows)
        self.individual_rows += len(rows)

    def record_loan_events(self, simulation: Simulation) -> None:
        """Écrit puis vide les événements de prêt du pas, sans les accumuler
        en mémoire (liste non bornée sinon : cf. JOURNAL.md, garde-fous mémoire)."""
        events = simulation.loan_events
        if events:
            self._loan_events_writer.writerows(events)
            self.loan_events_total += len(events)
            events.clear()

    def record_deaths(self, simulation: Simulation) -> None:
        """Écrit puis vide les décès du pas (même motif que record_loan_events,
        JOURNAL.md §11 : deaths/avalanches/avalanche_members n'étaient pas
        streamés alors qu'ils grossissent avec T comme loan_events)."""
        rows = simulation.deaths
        if rows:
            self._deaths_writer.writerows(rows)
            self.deaths_total += len(rows)
            for row in rows:
                self._death_lookup[row["id"]] = (row["t"], row["cause"])
            rows.clear()

    def record_avalanches(self, simulation: Simulation) -> None:
        """Écrit puis vide avalanches+avalanche_members du pas ; conserve les
        sommes nécessaires à branching_ratio (total_roots/total_size) sans
        garder les lignes elles-mêmes."""
        rows = simulation.avalanches
        if rows:
            self._avalanches_writer.writerows(rows)
            self.avalanches_total += len(rows)
            self.avalanche_roots_total += sum(row["n_roots"] for row in rows)
            self.avalanche_size_total += sum(row["size"] for row in rows)
            rows.clear()
        members = simulation.avalanche_members
        if members:
            self._avalanche_members_writer.writerows(members)
            members.clear()

    def finish(self, simulation: Simulation) -> dict:
        self.record_loan_events(simulation)
        self.record_deaths(simulation)
        self.record_avalanches(simulation)
        self.close()
        self._write_csv("series.csv", simulation.series, SERIES_FIELDS)
        self._write_entities(simulation)
        self._write_final_loans(simulation)

        summary = {
            "model_version": MODEL_VERSION,
            "gamma": simulation.config.gamma,
            "A": simulation.config.A,
            "target_rule": simulation.config.target_rule,
            "rho": simulation.config.rho,
            "eta_beta": simulation.config.eta_beta,
            "status": simulation.status,
            "t_final": simulation.t,
            "population_final": simulation.population.n_alive,
            "loans_final": len(simulation.book),
            "births_total": len(simulation.population),
            "deaths_total": self.deaths_total,
            "avalanches_total": self.avalanches_total,
            "loan_events_total": self.loan_events_total,
            "individual_rows": self.individual_rows,
            "branching_ratio": (
                1.0 - self.avalanche_roots_total / self.avalanche_size_total
                if self.avalanche_size_total else 0.0
            ),
            "book_errors": simulation.book.consistency_errors(simulation.population.alive),
        }
        self._write_json("summary.json", summary)
        return summary

    def close(self) -> None:
        if not self._individual_stream.closed:
            self._individual_stream.close()
        if not self._loan_events_stream.closed:
            self._loan_events_stream.close()
        if not self._deaths_stream.closed:
            self._deaths_stream.close()
        if not self._avalanches_stream.closed:
            self._avalanches_stream.close()
        if not self._avalanche_members_stream.closed:
            self._avalanche_members_stream.close()

    def _write_entities(self, simulation: Simulation) -> None:
        rows = []
        for entity, born_at in enumerate(simulation.population.birth):
            death = self._death_lookup.get(entity)
            rows.append(
                {
                    "id": entity,
                    "birth_t": born_at,
                    "death_t": "" if death is None else death[0],
                    "death_cause": "" if death is None else death[1],
                    "alive_final": int(simulation.population.alive[entity]),
                }
            )
        self._write_csv("entities.csv", rows, ENTITY_FIELDS)

    def _write_final_loans(self, simulation: Simulation) -> None:
        """Écrit directement sans matérialiser de liste intermédiaire : à K0
        élevé, `simulation.book.loans` compte plusieurs centaines de
        milliers d'entrées et dupliquer cette taille en `rows` double le pic
        mémoire exactement au moment du bilan final (JOURNAL.md, §11)."""
        path = self.directory / "final_loans.csv"
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=LOAN_FIELDS)
            writer.writeheader()
            for loan_id, (lender, borrower, principal, rate) in simulation.book.loans.items():
                writer.writerow(
                    {
                        "loan_id": loan_id,
                        "lender": lender,
                        "borrower": borrower,
                        "q": principal,
                        "r": rate,
                    }
                )

    def _write_csv(self, filename: str, rows: list[dict], fields: list[str]) -> None:
        path = self.directory / filename
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def _write_json(self, filename: str, data: dict) -> None:
        with (self.directory / filename).open("w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)


def run_and_save(
    config: Config,
    directory: str | Path,
    snapshot_every: int = 50,
    individual_every: int = 1,
    on_progress: Callable[[Simulation], None] | None = None,
) -> tuple[Simulation, dict]:
    """Exécute une simulation et enregistre toutes ses données primaires.

    ``snapshot_every=0`` désactive les instantanés intermédiaires ; l'état
    final est toujours sauvegardé. ``individual_every=1`` enregistre chaque
    entité à chaque pas ; zéro désactive la table longitudinale.
    """
    if snapshot_every < 0:
        raise ValueError("snapshot_every doit être positif ou nul")
    if individual_every < 0:
        raise ValueError("individual_every doit être positif ou nul")
    recorder = RunRecorder(directory, config, snapshot_every, individual_every)
    simulation = Simulation(config)
    times = range(snapshot_every, config.T + 1, snapshot_every) if snapshot_every else ()

    def record_step(current: Simulation) -> None:
        recorder.record_individuals(current)
        recorder.record_loan_events(current)
        recorder.record_deaths(current)
        recorder.record_avalanches(current)
        if on_progress is not None:
            on_progress(current)

    try:
        simulation.run(
            snapshot_times=times,
            on_snapshot=recorder.snapshot,
            on_step=record_step,
        )
        recorder.snapshot(
            simulation.t, simulation.entity_snapshot(), simulation.network_snapshot()
        )
        return simulation, recorder.finish(simulation)
    except Exception:
        recorder.close()
        raise
