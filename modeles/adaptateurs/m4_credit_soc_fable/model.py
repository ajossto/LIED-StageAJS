from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

from simulation_lab.contracts import collect_artifacts
from simulation_lab.models.legacy import LegacyModuleModel
from simulation_lab.progress import emit_progress


PROJECT_ROOT = Path(__file__).resolve().parents[2]
M4_ROOT = PROJECT_ROOT / "m4_credit_soc_fable"
REPORT_MODULE_NAME = "simulation_lab_m4_batch_report"
FIGURES_MODULE_NAME = "simulation_lab_m4_individual_figures"


def _load_figures_module():
    if FIGURES_MODULE_NAME in sys.modules:
        return sys.modules[FIGURES_MODULE_NAME]
    path = Path(__file__).with_name("individual_figures.py")
    spec = importlib.util.spec_from_file_location(FIGURES_MODULE_NAME, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Impossible de charger {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[FIGURES_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


def _load_report_module():
    """Charge paresseusement les recettes SOC utilisées par les lots M4."""
    if REPORT_MODULE_NAME in sys.modules:
        return sys.modules[REPORT_MODULE_NAME]
    path = M4_ROOT / "lab" / "batch_report.py"
    spec = importlib.util.spec_from_file_location(REPORT_MODULE_NAME, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Impossible de charger {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[REPORT_MODULE_NAME] = module
    spec.loader.exec_module(module)
    module.fig_cascades = _fig_cascades_rank_size_with_volume
    module.fig_volume_double_pareto = _fig_volume_dpln
    module.fig_revenue_fits = _fig_revenue_empirical
    module.fig_lifespan = _fig_lifespan_all_entities
    return module


def _fig_cascades_rank_size_with_volume(members, out_dir, extra):
    """Ajoute au rank-size le double-Pareto tronqué des volumes en joules."""
    report = sys.modules[REPORT_MODULE_NAME]
    return _load_figures_module().fig_cascades(report, members, out_dir, extra)


def _fig_volume_dpln(members, out_dir, extra):
    """Volume des avalanches : densité dPlN et CCDF empirique séparée."""
    report = sys.modules[REPORT_MODULE_NAME]
    figures = _load_figures_module()
    figures.fig_volume_dpln(report, members, out_dir, extra)
    figures.fig_volume_ccdf(report, members, out_dir, extra)


def _fig_revenue_empirical(members, out_dir, extra):
    """Revenus SOC : données empiriques seules, sans aucun ajustement."""
    report = sys.modules[REPORT_MODULE_NAME]
    return _load_figures_module().fig_revenue_empirical(
        report, members, out_dir, extra
    )


def _fig_lifespan_all_entities(members, out_dir, extra):
    """Durées de vie exhaustives depuis le registre des décès M4."""
    report = sys.modules[REPORT_MODULE_NAME]
    figures = _load_figures_module()
    figures.fig_lifespan_heatmaps(report, members, out_dir, extra)
    figures.fig_instantaneous_life_expectancy(
        report, members, out_dir, extra
    )


def _run_folder(output_dir: Path) -> Path:
    candidates = sorted((output_dir / "legacy_output").glob("simu_*"))
    if len(candidates) != 1:
        raise RuntimeError(
            f"Un unique dossier M4 était attendu dans {output_dir / 'legacy_output'}"
        )
    return candidates[0]


def _generate_single_soc_figures(folder: Path, seed: int) -> tuple[list[str], list[str]]:
    """Ajoute les variantes exactes des figures de lot, préfixées ``soc_``."""
    report = _load_report_module()
    config = json.loads((folder / "config.json").read_text(encoding="utf-8"))
    members = [(seed, folder, "single")]
    extra = (
        f"λ={config['lam']:g}, k={config['k']}, σ={config['sigma']}, "
        f"T={config['T']}, seed {seed}"
    )
    figure_dir = folder / "figures"
    temporary = figure_dir / "_soc_single"
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.mkdir(parents=True)

    recipes = (
        report.fig_macro,
        report.fig_destruction,
        report.fig_gini,
        report.fig_lorenz,
        report.fig_branching,
        report.fig_structure,
        report.fig_accumulation,
        report.fig_revenue_fits,
        report.fig_distribution_fits,
        report.fig_age_fits,
        report.fig_top_renewal,
    )
    errors = []
    for index, recipe in enumerate(recipes, start=1):
        emit_progress(
            {
                "progress": 99.0,
                "message": f"Figures SOC M4 {index}/{len(recipes) + 2}",
            }
        )
        try:
            recipe(members, temporary, extra)
        except Exception as exc:
            errors.append(f"{recipe.__name__}: {exc}")

    stat_recipes = (
        (
            "prod",
            f"Production Π = α√K  (α = {config['alpha']})",
            "Puissance productive des entités",
            "extraction_power.png",
        ),
        (
            "r",
            "Taux interne marginal r* = α/(2√K)",
            "Évolution du taux interne marginal r*",
            "internal_rate_evolution.png",
        ),
    )
    for prefix, ylabel, title, filename in stat_recipes:
        try:
            report._fig_stat_evolution(
                members, temporary, prefix, ylabel, title, filename, extra
            )
        except Exception as exc:
            errors.append(f"{filename}: {exc}")

    generated = []
    for source in sorted(temporary.glob("*.png")):
        destination = figure_dir / f"soc_{source.name}"
        source.replace(destination)
        generated.append(destination.name)
    shutil.rmtree(temporary)
    return generated, errors


def _generate_individual_figures(folder: Path, seed: int):
    report = _load_report_module()
    return _load_figures_module().generate_individual(report, folder, seed)


class M4SimulationLabModel(LegacyModuleModel):
    """Adaptateur M4 enrichi des recettes SOC mono-run et multi-seeds."""

    def run(self, parameters, output_dir, seed, run_label=""):
        result = super().run(parameters, output_dir, seed, run_label)
        folder = _run_folder(output_dir)
        individual = []
        individual_errors = []
        try:
            emit_progress(
                {
                    "progress": 99.0,
                    "message": "Génération des figures individuelles M4",
                }
            )
            individual, individual_errors = _generate_individual_figures(
                folder, seed
            )
        except Exception as exc:
            individual_errors = [str(exc)]
        result.extra["individual_figures"] = individual
        if individual_errors:
            result.extra["individual_figure_errors"] = individual_errors
            result.message += (
                f" — {len(individual_errors)} figure(s) individuelle(s) "
                "ignorée(s)"
            )
        try:
            generated, errors = _generate_single_soc_figures(
                folder, seed
            )
            result.extra["soc_figures"] = generated
            if errors:
                result.extra["soc_figure_errors"] = errors
                result.message += f" — {len(errors)} recette(s) SOC ignorée(s)"
            else:
                result.message += f" — {len(generated)} figures SOC ajoutées"
        except Exception as exc:
            result.extra["soc_figure_errors"] = [str(exc)]
            result.message += f" — génération SOC impossible: {exc}"
        result.artifacts = collect_artifacts(output_dir)
        return result

    def finalize_batch(self, batch: dict, progress_callback=None) -> dict:
        """Crée le dossier lot et actualise la synthèse SOC inter-lots."""
        report = _load_report_module()
        batch_id = batch["batch_id"]
        if progress_callback is not None:
            progress_callback(
                {
                    "progress": 93.0,
                    "message": "Figures SOC agrégées du lot M4",
                }
            )
        lot_id = report.export_batch(batch_id, force=True)
        completed_batches = []
        for candidate in report.m4_batches():
            try:
                if report.batch_members(report.load_batch(candidate)):
                    completed_batches.append(candidate)
            except (FileNotFoundError, json.JSONDecodeError, KeyError):
                continue
        synthesis_id = None
        synthesis_error = None
        if len(completed_batches) >= 2:
            if progress_callback is not None:
                progress_callback(
                    {
                        "progress": 97.0,
                        "message": "Actualisation de la synthèse SOC inter-lots",
                    }
                )
            try:
                synthesis_id = report.export_synthesis(
                    completed_batches, force=True
                )
            except Exception as exc:
                synthesis_error = str(exc)
        return {
            "lot_run_id": lot_id,
            "synthesis_run_id": synthesis_id,
            "synthesis_error": synthesis_error,
        }


MODEL = M4SimulationLabModel(
    model_id="m4_credit_soc_fable",
    display_name="M4 crédit-société (fable)",
    description=(
        "Moteur fusionné M4 (m4_credit_soc_fable/src/m4) : une variable "
        "d'état K par entité, faillite cancel+destroy, avalanches causales "
        "en loi de puissance (régime SOC validé, rapport 01_soc_final). "
        "Figures historiques et variantes SOC générées par run ; figures "
        "agrégées et synthèse inter-lots générées après chaque batch. Les "
        "cascades rank-size suivent une loi de puissance à troncature "
        "exponentielle."
    ),
    source_dir=str(M4_ROOT / "lab"),
    config_class_name="M4Config",
)
