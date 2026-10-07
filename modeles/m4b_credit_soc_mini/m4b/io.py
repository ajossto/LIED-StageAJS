"""Écriture des données primaires d'une simulation M4B."""

from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path
from typing import Callable

import numpy as np

from .model import ALPHA, Config, Simulation


MODEL_VERSION = "m4b-mini-3"
FIXED_RULES = {
    "shock": "iid_lognormal_mean_one",
    "market_objective": "income",
    "market_rounds": "one_per_living_entity",
    "loan_pairs": "merged",
    "bankruptcy": "cancel_and_destroy",
}

SERIES_FIELDS = [
    "t", "births", "deaths", "pop", "K_tot", "nw_tot", "prod_tot",
    "n_loans", "new_loans", "loan_volume", "interest_paid", "defaults",
    "roots_liquidity", "roots_insolvency", "roots_both", "cascade_iters",
    "n_avalanches", "max_avalanche", "claim_losses", "destroyed",
    "injected", "depreciated", "shock_gain",
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
        provenance = {
            "model_version": MODEL_VERSION,
            "parameters": config.to_dict(),
            "alpha": ALPHA,
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

    def finish(self, simulation: Simulation) -> dict:
        self.close()
        self._write_csv("series.csv", simulation.series, SERIES_FIELDS)
        self._write_csv("avalanches.csv", simulation.avalanches, AVALANCHE_FIELDS)
        self._write_csv("avalanche_members.csv", simulation.avalanche_members, MEMBER_FIELDS)
        self._write_csv("deaths.csv", simulation.deaths, DEATH_FIELDS)
        self._write_entities(simulation)
        self._write_final_loans(simulation)

        total_roots = sum(row["n_roots"] for row in simulation.avalanches)
        total_size = sum(row["size"] for row in simulation.avalanches)
        summary = {
            "model_version": MODEL_VERSION,
            "status": simulation.status,
            "t_final": simulation.t,
            "population_final": simulation.population.n_alive,
            "loans_final": len(simulation.book),
            "births_total": len(simulation.population),
            "deaths_total": len(simulation.deaths),
            "avalanches_total": len(simulation.avalanches),
            "individual_rows": self.individual_rows,
            "branching_ratio": 1.0 - total_roots / total_size if total_size else 0.0,
            "book_errors": simulation.book.consistency_errors(simulation.population.alive),
        }
        self._write_json("summary.json", summary)
        return summary

    def close(self) -> None:
        if not self._individual_stream.closed:
            self._individual_stream.close()

    def _write_entities(self, simulation: Simulation) -> None:
        death_by_id = {row["id"]: row for row in simulation.deaths}
        rows = []
        for entity, born_at in enumerate(simulation.population.birth):
            death = death_by_id.get(entity)
            rows.append(
                {
                    "id": entity,
                    "birth_t": born_at,
                    "death_t": "" if death is None else death["t"],
                    "death_cause": "" if death is None else death["cause"],
                    "alive_final": int(simulation.population.alive[entity]),
                }
            )
        self._write_csv("entities.csv", rows, ENTITY_FIELDS)

    def _write_final_loans(self, simulation: Simulation) -> None:
        rows = []
        for loan_id, (lender, borrower, principal, rate) in simulation.book.loans.items():
            rows.append(
                {
                    "loan_id": loan_id,
                    "lender": lender,
                    "borrower": borrower,
                    "q": principal,
                    "r": rate,
                }
            )
        self._write_csv("final_loans.csv", rows, LOAN_FIELDS)

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
