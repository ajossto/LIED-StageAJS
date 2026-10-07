"""Adaptateur Simulation Lab du moteur M4.2B (copie adaptée de l'adaptateur M4.2).

Différences avec l'adaptateur M4.2 : moteur m4_2b, quatre paramètres
supplémentaires (``target_rule``, ``rho``, ``eta_beta``, ``eta_n_ref`` —
voir m4_2b_credit_soc/m4_2b/model.py) et baseline scientifique changée
(``delta``=0.01, ``sigma``=0.01 au lieu de 0.05/0.25 — PROMPT_M4_2B.md §4).
Les 28 figures M4.2/M4B sont réutilisées sans changement (reporting.py
copié tel quel, cf. sa docstring de provenance).
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import sys
import time
from contextlib import contextmanager
from pathlib import Path

from simulation_lab.contracts import (
    BaseSimulationModel,
    ParameterSpec,
    SimulationResult,
    collect_artifacts,
)
from simulation_lab.progress import emit_progress, ensure_not_cancelled
from simulation_lab.runs.storage import RunStorage, utc_now
from simulation_lab.settings import BATCHES_DIR, RUNS_DIR


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = PROJECT_ROOT / "m4_2b_credit_soc"


@contextmanager
def _engine_on_path():
    path = str(ENGINE_ROOT)
    sys.path.insert(0, path)
    try:
        yield
    finally:
        if path in sys.path:
            sys.path.remove(path)


def _load_engine():
    with _engine_on_path():
        return importlib.import_module("m4_2b")


def _load_figures_module():
    module_name = "simulation_lab_m4_2b_figures"
    if module_name in sys.modules:
        return sys.modules[module_name]
    path = Path(__file__).with_name("figures.py")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Impossible de charger {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class M42BCreditSocModel(BaseSimulationModel):
    model_id = "m4_2b_credit_soc"
    display_name = "M4.2B crédit-société (principal arithmétique)"
    description = (
        "Successeur expérimental de M4.2 : cible de principal ARITHMÉTIQUE "
        "(K_target=(K_ℓ+K_b)/2, égalise les capitaux) au lieu de la cible "
        "géométrique K*=√(K_ℓK_b) — taux inchangé (moyenne géométrique des "
        "rendements marginaux). Baseline lente : δ=0.01, σ=0.01. Bascule "
        "target_rule=geometric disponible pour reproduire M4.2 à l'identique "
        "(ablation §12). Famille d'intensité de marché η_ρ,β(N) explicite "
        "(rho, eta_beta, eta_n_ref). Mesures agrégées, individuelles, réseau "
        "et avalanches identiques à M4.2/M4B (+ table loan_events : r,q,rq "
        "par transaction)."
    )
    tags = ["m4_2b", "credit", "soc", "arithmetic", "active"]

    def parameter_specs(self) -> list[ParameterSpec]:
        return [
            ParameterSpec(
                "gamma", "float", 0.5, "Exposant de concavité γ",
                minimum=0.05, maximum=0.95,
            ),
            ParameterSpec(
                "A", "float", 1.0,
                "Échelle productive A (1.0 hors ablation d'échelle)",
                minimum=1e-9,
            ),
            ParameterSpec("lam", "float", 30.0, "Naissances λ", minimum=0.0),
            ParameterSpec(
                "delta", "float", 0.01, "Dépréciation δ (baseline M4.2B lente)",
                minimum=0.0, maximum=0.999999,
            ),
            ParameterSpec(
                "sigma", "float", 0.01, "Volatilité σ (baseline M4.2B faible)",
                minimum=0.0,
            ),
            ParameterSpec("K0", "float", 25.0, "Capital de naissance K₀", minimum=1e-12),
            ParameterSpec("T", "int", 2000, "Nombre de pas", minimum=0),
            ParameterSpec("pop_max", "int", 30_000, "Limite de population", minimum=1),
            ParameterSpec(
                "target_rule", "str", "arithmetic",
                "Institution de principal : arithmetic (M4.2B) ou geometric (M4.2)",
                choices=["arithmetic", "geometric"],
            ),
            ParameterSpec(
                "rho", "float", 1.0, "Intensité de marché η_ρ,β(N) : facteur ρ",
                minimum=1e-9,
            ),
            ParameterSpec(
                "eta_beta", "float", 1.0,
                "Élasticité β de η_ρ,β(N) à la population (1.0 = linéaire ρ·N)",
            ),
            ParameterSpec(
                "eta_n_ref", "float", 1.0,
                "Échelle de référence N_ref pour β≠1 (sans effet si eta_beta=1.0)",
                minimum=1e-9,
            ),
            ParameterSpec(
                "snapshot_every", "int", 50, "Fréquence des instantanés", minimum=0
            ),
            ParameterSpec(
                "individual_every",
                "int",
                1,
                "Fréquence des mesures individuelles",
                minimum=0,
            ),
            ParameterSpec(
                "figures",
                "bool",
                True,
                "Générer les 28 figures du run (post-traitement)",
            ),
        ]

    def run(
        self,
        parameters: dict,
        output_dir: Path,
        seed: int,
        run_label: str = "",
    ) -> SimulationResult:
        engine = _load_engine()
        config = engine.Config(
            gamma=parameters["gamma"],
            A=parameters["A"],
            lam=parameters["lam"],
            delta=parameters["delta"],
            sigma=parameters["sigma"],
            K0=parameters["K0"],
            seed=seed,
            T=parameters["T"],
            pop_max=parameters["pop_max"],
            target_rule=parameters.get("target_rule", "arithmetic"),
            rho=parameters.get("rho", 1.0),
            eta_beta=parameters.get("eta_beta", 1.0),
            eta_n_ref=parameters.get("eta_n_ref", 1.0),
        )
        started_at = time.monotonic()
        report_every = max(1, config.T // 100) if config.T else 1
        last_report_at = started_at
        max_avalanche_seen = 0

        def report(current) -> None:
            nonlocal last_report_at, max_avalanche_seen
            ensure_not_cancelled()
            now = time.monotonic()
            checkpoint = (
                current.t == 1
                or current.t == config.T
                or current.status != "ok"
                or current.t % report_every == 0
            )
            if not checkpoint and now - last_report_at < 1.0:
                return
            last_report_at = now
            row = current.series[-1]
            elapsed = max(now - started_at, 1e-9)
            speed = current.t / elapsed
            eta_seconds = max(0.0, config.T - current.t) / speed if speed > 0 else None
            debt = float(sum(current.book.debts.values()))
            assets = float(row["K_tot"] + debt)
            debt_ratio = debt / assets if assets > 0 else 0.0
            max_avalanche_seen = max(max_avalanche_seen, int(row["max_avalanche"]))
            lookback = current.series[max(0, len(current.series) - 20)]
            population_load = 100.0 * row["pop"] / config.pop_max
            alerts = []
            if population_load >= 80.0:
                alerts.append(f"Population à {population_load:.1f} % de la limite d’explosion")
            if debt_ratio >= 0.9:
                alerts.append(f"Dette élevée : {100.0 * debt_ratio:.1f} % des actifs")
            if row["pop"] == 0 or current.status == "extinction":
                alerts.append("Extinction de la population")
            elif current.status == "explosion":
                alerts.append("Limite de population dépassée")
            if row["max_avalanche"] >= max(10, 0.1 * max(1, row["pop"])):
                alerts.append(f"Avalanche importante au dernier pas : {row['max_avalanche']} entités")
            if row["n_loans"] >= 50 * max(1, row["pop"]):
                alerts.append(
                    f"Réseau très dense : {row['n_loans']} prêts pour {row['pop']} entités"
                )

            progress = 5.0 + 87.0 * current.t / max(1, config.T)
            emit_progress(
                {
                    "progress": min(progress, 92.0),
                    "message": (
                        f"Pas {current.t}/{config.T} — {row['pop']} entités, "
                        f"{len(current.book)} prêts"
                    ),
                    "telemetry": {
                        "phase": "simulation",
                        "t": current.t,
                        "t_total": config.T,
                        "gamma": config.gamma,
                        "target_rule": config.target_rule,
                        "rho": config.rho,
                        "elapsed_seconds": elapsed,
                        "eta_seconds": eta_seconds,
                        "steps_per_second": speed,
                        "population": int(row["pop"]),
                        "population_limit": config.pop_max,
                        "population_load_pct": population_load,
                        "population_change_20": int(row["pop"] - lookback["pop"]),
                        "loans": len(current.book),
                        "capital_j": float(row["K_tot"]),
                        "net_worth_j": float(row["nw_tot"]),
                        "net_worth_change_20_j": float(row["nw_tot"] - lookback["nw_tot"]),
                        "debt_j": debt,
                        "debt_assets_ratio": debt_ratio,
                        "births_total": len(current.population),
                        "deaths_total": len(current.deaths),
                        "deaths_step": int(row["deaths"]),
                        "avalanches_total": len(current.avalanches),
                        "avalanches_step": int(row["n_avalanches"]),
                        "max_avalanche_step": int(row["max_avalanche"]),
                        "max_avalanche_seen": max_avalanche_seen,
                        "market_rounds_step": int(row["mkt_rounds"]),
                        "model_status": current.status,
                    },
                    "alerts": alerts,
                }
            )

        emit_progress(
            {
                "progress": 5.0,
                "message": (
                    f"Initialisation de la simulation M4.2B (γ={config.gamma:g}, "
                    f"target_rule={config.target_rule})"
                ),
                "telemetry": {
                    "phase": "initialisation",
                    "t": 0,
                    "t_total": config.T,
                    "gamma": config.gamma,
                    "target_rule": config.target_rule,
                    "elapsed_seconds": 0.0,
                },
                "alerts": [],
            }
        )
        simulation, summary = engine.run_and_save(
            config,
            output_dir,
            snapshot_every=parameters["snapshot_every"],
            individual_every=parameters["individual_every"],
            on_progress=report,
        )

        figure_errors: list[str] = []
        if parameters.get("figures", True):
            emit_progress(
                {
                    "progress": 94.0,
                    "message": "Calcul des figures statiques M4.2B",
                    "telemetry": {
                        "phase": "figures",
                        "t": simulation.t,
                        "t_total": config.T,
                        "elapsed_seconds": time.monotonic() - started_at,
                        "eta_seconds": None,
                        "population": simulation.population.n_alive,
                        "loans": len(simulation.book),
                        "deaths_total": len(simulation.deaths),
                        "avalanches_total": len(simulation.avalanches),
                        "model_status": simulation.status,
                    },
                    "alerts": [],
                }
            )
            figure_errors = _load_figures_module().generate_figures(
                output_dir, run_label or self.display_name
            )
        message = f"Simulation M4.2B terminée à t={simulation.t}"
        if figure_errors:
            message += f" — {len(figure_errors)} figure(s) ignorée(s)"
        return SimulationResult(
            status="completed",
            summary=summary,
            artifacts=collect_artifacts(output_dir),
            message=message,
            extra={
                "seed": seed,
                "model_status": simulation.status,
                **({"figure_errors": figure_errors} if figure_errors else {}),
            },
        )

    def finalize_batch(self, batch: dict, progress_callback=None) -> dict:
        """Crée les vues de lot choisies, puis actualise la synthèse inter-lots."""
        storage = RunStorage()
        members = []
        for run_id in batch.get("run_ids", []):
            metadata = storage.read_metadata(run_id)
            if metadata.get("status") == "completed":
                members.append((int(metadata.get("seed", 0)), storage.run_dir(run_id)))
        members.sort(key=lambda item: item[0])
        if not members:
            return {"status": "skipped", "reason": "aucun run M4.2B complet"}

        export = storage.create_run(
            model_id=self.model_id,
            parameters=batch.get("parameters", {}),
            seed=-1,
            label=f"Lot M4.2B — {batch.get('label') or batch['batch_id']}",
            batch_id=batch["batch_id"],
        )
        export_id = export["run_id"]
        storage.mark_running(export_id)
        export_dir = storage.run_dir(export_id)
        figure_module = _load_figures_module()
        errors = figure_module.generate_batch_figures(
            members,
            export_dir / "figures",
            batch.get("label") or batch["batch_id"],
        )
        (export_dir / "aggregate.json").write_text(
            json.dumps(
                {
                    "batch_id": batch["batch_id"],
                    "member_run_ids": batch.get("run_ids", []),
                    "seeds": [seed for seed, _ in members],
                    "selected_families": ["L02", "L04", "L12", "L13", "L14", "L15"],
                    "figure_errors": errors,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        result = SimulationResult(
            status="completed",
            summary={"runs": len(members), "seeds": [seed for seed, _ in members]},
            artifacts=collect_artifacts(export_dir),
            message=f"Figures agrégées de {len(members)} seeds",
            extra={"figure_errors": errors} if errors else {},
        )
        storage.finalize_run(export_id, result)

        synthesis = self._refresh_synthesis(figure_module, storage)
        if progress_callback is not None:
            progress_callback({
                "completed_runs": len(members),
                "total_runs": len(members),
                "progress": 100.0,
                "message": "Figures de lot et synthèse M4.2B actualisées",
            })
        return {"status": "completed", "export_run_id": export_id, "errors": errors, **synthesis}

    def _refresh_synthesis(self, figure_module, storage: RunStorage) -> dict:
        lots = []
        for path in sorted(BATCHES_DIR.glob("*.json")):
            try:
                batch = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if batch.get("model_id") != self.model_id:
                continue
            members = []
            for run_id in batch.get("run_ids", []):
                try:
                    metadata = storage.read_metadata(run_id)
                except (OSError, ValueError):
                    continue
                if metadata.get("status") == "completed" and metadata.get("seed", -1) >= 0:
                    members.append((int(metadata["seed"]), storage.run_dir(run_id)))
            if members:
                lots.append((batch.get("label") or batch["batch_id"], members))
        if len(lots) < 2:
            return {"synthesis_status": "skipped", "synthesis_reason": "moins de deux lots M4.2B"}

        run_id = "m4_2b_soc_synthese_lots"
        directory = RUNS_DIR / run_id
        figures = directory / "figures"
        figures.mkdir(parents=True, exist_ok=True)
        generated = figure_module.generate_synthesis_figures(
            lots, figures, "ensemble des lots M4.2B"
        )
        if not generated:
            return {"synthesis_status": "skipped", "synthesis_reason": "lots non comparables"}
        metadata = {
            "run_id": run_id,
            "model_id": self.model_id,
            "parameters": {},
            "seed": -1,
            "label": "Synthèse SOC inter-lots M4.2B",
            "batch_id": None,
            "status": "completed",
            "keep": True,
            "important": True,
            "trashed": False,
            "trashed_at": None,
            "archived": False,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "summary": {"lots": len(lots)},
            "artifacts": [artifact.to_dict() for artifact in collect_artifacts(directory)],
            "message": "Invariant SOC actualisé",
        }
        storage.write_metadata(directory, metadata)
        return {"synthesis_status": "completed", "synthesis_run_id": run_id}


MODEL = M42BCreditSocModel()
