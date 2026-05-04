"""
Exporte les resultats de l'etude de sensibilite vers Simulation Lab.

Le lab sait afficher les runs presents dans ~/jupyter/simulation_lab_data/runs
si chaque dossier contient un run.json et des artefacts. Les simulations de cette
etude ont ete lancees hors lab; ce script cree donc des runs synthetiques
consultables dans l'interface, avec les metriques brutes et des figures PNG.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


STUDY_DIR = Path(__file__).resolve().parent
RESULTS_DIR = STUDY_DIR / "results"
REPORT_DIR = STUDY_DIR / "report"
REPORT_FIGURES_DIR = REPORT_DIR / "figures"
JUPYTER_DIR = STUDY_DIR.parents[2]
LAB_RUNS_DIR = JUPYTER_DIR / "simulation_lab_data" / "runs"

MODEL_ID = "etude_sensibilite_27_04_wip"
EXPORT_STARTED_AT_UTC = datetime.now(timezone.utc)
EXPORT_STARTED_AT_LOCAL = EXPORT_STARTED_AT_UTC.astimezone()
CREATED_AT = EXPORT_STARTED_AT_UTC.isoformat()

DATASETS = {
    "pilot": {
        "file": "pilot_results.json",
        "label": "Etude sensibilite - pilote",
        "description": "Points pilotes initiaux de l'etude de sensibilite.",
        "study_group": "exploratoire",
    },
    "k_sweep": {
        "file": "k_sweep_steps1500_eps0.001.json",
        "aggregate": "k_sweep_steps1500_eps0.001_aggregate.json",
        "figure_pdf": "k_sweep_steps1500_eps0.001.pdf",
        "label": "Etude sensibilite - balayage k",
        "description": "Balayage de k a epsilon=1e-3, incluant les essais exploratoires historiques.",
        "study_group": "exploratoire",
    },
    "epsilon_runtime": {
        "file": "epsilon_runtime_probe.json",
        "aggregate": "epsilon_runtime_probe_aggregate.json",
        "figure_pdf": "epsilon_runtime_probe.pdf",
        "label": "Etude sensibilite - epsilon et temps de calcul",
        "description": "Sonde epsilon: temps d'execution, microcredits, densite et regime.",
        "study_group": "exploratoire",
    },
    "alpha_sigma": {
        "file": "alpha_sigma_sweep_steps1500_eps0.001.json",
        "aggregate": "alpha_sigma_sweep_steps1500_eps0.001_aggregate.json",
        "figure_pdf": "alpha_sigma_sweep_steps1500_eps0.001.pdf",
        "label": "Etude sensibilite - sigma alpha homogene",
        "description": "Balayage principal: alpha_min=alpha_max=1 et variation de alpha_sigma_brownien.",
        "study_group": "exploratoire",
    },
    "lab_guided_probe": {
        "file": "lab_guided_probe.json",
        "label": "Etude sensibilite - sonde guidee par Simulation Lab",
        "description": "Petite grille inspiree des runs historiques du lab.",
        "study_group": "exploratoire",
    },
    "claude_coupling_lambda_k": {
        "file": "claude_coupling_lambda_k_aggregate.json",
        "figure_pdf": "claude_coupling_lambda_k.pdf",
        "label": "Couplage lambda x k",
        "description": "Carte de phase 2D bounded_share(k, lambda). k est le facteur dominant; fenetre optimale k=4, lambda in [1.4, 2.0].",
        "study_group": "couplages",
        "schema": "coupling_aggregate",
    },
    "claude_coupling_k_mu": {
        "file": "claude_coupling_k_mu_aggregate.json",
        "figure_pdf": "claude_coupling_k_mu.pdf",
        "label": "Couplage k x mu",
        "description": "Carte de phase 2D bounded_share(k, mu). mu=0 deblocage du regime pour k=2,3; mu>=0.10 detruit tout regime.",
        "study_group": "couplages",
        "schema": "coupling_aggregate",
    },
    "claude_coupling_sigma_k": {
        "file": "claude_coupling_sigma_k_aggregate.json",
        "figure_pdf": "claude_coupling_sigma_k.pdf",
        "label": "Couplage sigma x k",
        "description": "Carte de phase 2D bounded_share(k, sigma). sigma ouvre k=3 dans [0.01, 0.02]; sigma=0.05 detruit tous les regimes.",
        "study_group": "couplages",
        "schema": "coupling_aggregate",
    },
    "claude_coupling_theta_depr": {
        "file": "claude_coupling_theta_depr_aggregate.json",
        "figure_pdf": "claude_coupling_theta_depr.pdf",
        "label": "Couplage theta x delta_endo",
        "description": "Carte de phase bounded_share(theta, delta_endo, k). delta_endo=0.10 interdit le regime; delta_endo=0.02 l'ouvre stochastiquement.",
        "study_group": "couplages",
        "schema": "coupling_aggregate",
    },
    "claude_multirun_limits": {
        "file": "claude_multirun_limits_aggregate.json",
        "figure_pdf": "claude_multirun_limits.pdf",
        "label": "Probabilites limites 13 seeds",
        "description": "Estimation de p_borne par IC95% sur 13 seeds pour les 7 cas frontiere. Distingue effets vrais robustes des artefacts seed.",
        "study_group": "multirun",
        "schema": "multirun_aggregate",
    },
    "claude_predictability": {
        "file": "claude_predictability_aggregate.json",
        "label": "Predictabilite par regime",
        "description": "Hurst R/S, autocorrelation lag20, AR(5)/naif, entropie de permutation sur 18 cas. Separateur scalaire: Sp.",
        "study_group": "predictabilite",
        "schema": "predictability_aggregate",
    },
    "claude_long_run_k3sigma0005": {
        "file": "claude_long_run_k3sigma0005.json",
        "label": "Long run k3 sigma=0.005",
        "description": "5 seeds jusqu'a 5000 pas. Croissance explosive (non regime): population oscille sans converger.",
        "study_group": "long_runs",
        "schema": "long_run",
    },
}

KEY_SUMMARY_FIELDS = [
    "n_steps",
    "k",
    "epsilon",
    "alpha_sigma_brownien",
    "converged",
    "bounded_tail",
    "drop_5_detected",
    "t_regime",
    "t_measure",
    "n_alive_mean",
    "actif_mean",
    "densite_fin_mean",
    "loan_density_mean",
    "failure_rate_mean",
    "cascade_event_rate",
    "cascade_size_mean",
    "cascade_size_max",
    "gini_actif_mean",
    "corr_alive_actif_tail",
    "corr_alive_loans_tail",
    "corr_actif_loans_tail",
    "elapsed_s",
]

# Map dataset_name -> study_group label for UI grouping
STUDY_GROUP_LABELS = {
    "exploratoire": "Exploration initiale",
    "oat": "OAT (One-at-a-time)",
    "couplages": "Couplages 2D",
    "multirun": "Multi-seeds probabiliste",
    "predictabilite": "Prédictabilité",
    "long_runs": "Long runs",
    "direct": "Simulations directes",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lab-runs-dir", type=Path, default=LAB_RUNS_DIR)
    parser.add_argument("--clean", action="store_true", help="Supprime d'abord les runs sensitivity_* existants.")
    args = parser.parse_args()

    args.lab_runs_dir.mkdir(parents=True, exist_ok=True)
    if args.clean:
        for path in args.lab_runs_dir.glob("sensitivity_*"):
            if path.is_dir():
                shutil.rmtree(path)

    exported: list[str] = []
    for dataset_name, spec in discover_datasets().items():
        records = load_json(RESULTS_DIR / spec["file"])
        if not isinstance(records, list):
            raise TypeError(f"{spec['file']} doit contenir une liste.")
        exported.append(export_aggregate(dataset_name, spec, records, args.lab_runs_dir))
        for index, record in enumerate(records):
            exported.append(export_record(dataset_name, spec, record, index, args.lab_runs_dir))

    write_manifest(exported, args.lab_runs_dir)
    print(f"Export Simulation Lab termine: {len(exported)} runs crees ou mis a jour dans {args.lab_runs_dir}")


def discover_datasets() -> dict[str, dict[str, str]]:
    datasets = dict(DATASETS)
    for path in sorted(RESULTS_DIR.glob("codex_oat_screen_steps*_seeds*.json")):
        if path.name.endswith("_aggregate.json") or path.name.endswith("_effects.json"):
            continue
        suffix = path.stem.replace("codex_oat_screen_", "")
        dataset_name = f"codex_oat_{suffix}"
        figure_name = f"{path.stem}.pdf"
        aggregate_name = f"{path.stem}_aggregate.json"
        datasets[dataset_name] = {
            "file": path.name,
            "aggregate": aggregate_name,
            "figure_pdf": figure_name,
            "label": f"Etude sensibilite - OAT Codex {suffix}",
            "description": "Screening OAT autour des centres k=3 sous-critique et k=4 en regime.",
            "study_group": "oat",
        }
    for path in sorted(RESULTS_DIR.glob("codex_long_probe_steps*_seeds*.json")):
        if path.name.endswith("_aggregate.json"):
            continue
        suffix = path.stem.replace("codex_long_probe_", "")
        dataset_name = f"codex_long_probe_{suffix}"
        figure_name = f"{path.stem}.pdf"
        aggregate_name = f"{path.stem}_aggregate.json"
        datasets[dataset_name] = {
            "file": path.name,
            "aggregate": aggregate_name,
            "figure_pdf": figure_name,
            "label": f"Etude sensibilite - sonde longue Codex {suffix}",
            "description": "Sonde longue sur les cas ambigus et entrees tardives en regime.",
            "study_group": "long_runs",
        }
    # Robustesse OAT Claude (seeds 7+123)
    for path in sorted(RESULTS_DIR.glob("claude_oat_robustness_seeds*.json")):
        if path.name.endswith("_aggregate.json"):
            continue
        dataset_name = "claude_oat_robustness"
        datasets[dataset_name] = {
            "file": path.name,
            "aggregate": path.stem + "_aggregate.json",
            "figure_pdf": "claude_oat_robustness.pdf",
            "label": "OAT robustesse seeds 7+123",
            "description": "Verification de robustesse OAT sur seeds 7 et 123 pour les 8 parametres les plus impactants.",
            "study_group": "oat",
        }
    # Balayage fin lambda (Claude)
    for path in sorted(RESULTS_DIR.glob("claude_lambda_fine_sweep*.json")):
        if path.name.endswith("_aggregate.json"):
            continue
        datasets["claude_lambda_fine_sweep"] = {
            "file": path.name,
            "aggregate": path.stem + "_aggregate.json",
            "figure_pdf": "claude_lambda_fine_sweep.pdf",
            "label": "Balayage fin lambda (Claude)",
            "description": "lambda in [1.0, 5.0], k=4, 3 seeds. Frontiere robuste k=4 entre lambda=2.0 et lambda=2.5.",
            "study_group": "oat",
        }
    return datasets


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def export_aggregate(dataset_name: str, spec: dict[str, str], records: list[dict[str, Any]], lab_runs_dir: Path) -> str:
    run_id = f"sensitivity_{dataset_name}_aggregate"
    run_dir = recreate_run_dir(lab_runs_dir, run_id)

    (run_dir / "records.json").write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    aggregate_name = spec.get("aggregate")
    if aggregate_name and (RESULTS_DIR / aggregate_name).exists():
        shutil.copy2(RESULTS_DIR / aggregate_name, run_dir / "aggregate.json")
    for report_name in ("rapport_preliminaire_sensibilite.pdf", "rapport_final_sensibilite.pdf"):
        report_pdf = REPORT_DIR / report_name
        if report_pdf.exists():
            shutil.copy2(report_pdf, run_dir / report_name)
    figure_pdf = spec.get("figure_pdf")
    if figure_pdf and (REPORT_FIGURES_DIR / figure_pdf).exists():
        shutil.copy2(REPORT_FIGURES_DIR / figure_pdf, run_dir / figure_pdf)

    plot_aggregate(dataset_name, spec, records, run_dir / "overview.png")
    summary = aggregate_summary(dataset_name, spec, records)
    metadata = run_metadata(
        run_id=run_id,
        label=spec["label"],
        parameters={
            "dataset": dataset_name,
            "records": len(records),
            "exported_at_local": EXPORT_STARTED_AT_LOCAL.isoformat(),
        },
        seed=None,
        summary=summary,
        message=spec["description"],
        artifacts=collect_artifacts(run_dir),
        important=False,
        study_group=spec.get("study_group", "direct"),
    )
    write_metadata(run_dir, metadata)
    return run_id


def export_record(
    dataset_name: str,
    spec: dict[str, str],
    record: dict[str, Any],
    index: int,
    lab_runs_dir: Path,
) -> str:
    run_id = record_run_id(dataset_name, record, index)
    run_dir = recreate_run_dir(lab_runs_dir, run_id)
    (run_dir / "record.json").write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    schema = spec.get("schema", "standard")
    if schema == "predictability_aggregate":
        plot_predictability_record(record, run_dir / "overview.png")
    elif schema == "long_run":
        plot_long_run_record(record, run_dir / "overview.png")
    else:
        plot_record(record, run_dir / "overview.png")
    params = dict(record.get("params") or {})
    params.setdefault("exported_at_local", EXPORT_STARTED_AT_LOCAL.isoformat())
    if record.get("executed_at_local"):
        params.setdefault("executed_at_local", record.get("executed_at_local"))
    params.setdefault("n_candidats_pool", record.get("k"))
    params.setdefault("epsilon", record.get("epsilon"))
    if "alpha_sigma_brownien" in record:
        params.setdefault("alpha_sigma_brownien", record.get("alpha_sigma_brownien"))
    if "n_steps" in record:
        params.setdefault("duree_simulation", record.get("n_steps"))
    label = record_label(dataset_name, record, index)
    metadata = run_metadata(
        run_id=run_id,
        label=label,
        parameters=params,
        seed=record.get("seed"),
        summary=record_summary(spec, record),
        message=spec["description"],
        artifacts=collect_artifacts(run_dir),
        important=False,
        study_group=spec.get("study_group", "direct"),
    )
    write_metadata(run_dir, metadata)
    return run_id


def recreate_run_dir(lab_runs_dir: Path, run_id: str) -> Path:
    run_dir = lab_runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def run_metadata(
    *,
    run_id: str,
    label: str,
    parameters: dict[str, Any],
    seed: Any,
    summary: dict[str, Any],
    message: str,
    artifacts: list[dict[str, str]],
    important: bool,
    study_group: str = "direct",
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "model_id": MODEL_ID,
        "parameters": sanitize(parameters),
        "seed": seed,
        "label": label,
        "batch_id": "sensitivity_parameter_study",
        "study_group": study_group,
        "status": "completed",
        "keep": True,
        "important": important,
        "trashed": False,
        "trashed_at": None,
        "created_at": CREATED_AT,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "summary": sanitize(summary),
        "artifacts": artifacts,
        "preview_artifact": "overview.png",
        "message": message,
        "comment": "",
        "extra": {
            "source": "studies/sensitivity",
            "source_path": str(STUDY_DIR),
            "exported_at_utc": EXPORT_STARTED_AT_UTC.isoformat(),
            "exported_at_local": EXPORT_STARTED_AT_LOCAL.isoformat(),
        },
    }


def write_metadata(run_dir: Path, metadata: dict[str, Any]) -> None:
    (run_dir / "run.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")


def collect_artifacts(run_dir: Path) -> list[dict[str, str]]:
    artifacts = []
    for path in sorted(run_dir.iterdir()):
        if path.name == "run.json" or not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in {".png", ".jpg", ".jpeg"}:
            kind = "image"
        elif suffix == ".csv":
            kind = "csv"
        elif suffix in {".json", ".txt", ".md"}:
            kind = "text"
        else:
            kind = "file"
        artifacts.append({
            "relative_path": path.name,
            "kind": kind,
            "label": path.name,
            "description": "",
        })
    return artifacts


def record_run_id(dataset_name: str, record: dict[str, Any], index: int) -> str:
    parts = ["sensitivity", dataset_name]
    schema = _record_schema(dataset_name)
    if schema == "coupling_aggregate":
        if "k" in record:
            parts.append(f"k{format_token(record['k'])}")
        for key in ("lambda", "mu", "sigma", "theta", "taux_depreciation_endo"):
            if key in record:
                parts.append(f"{slug(key)}{format_token(record[key])}")
    elif schema == "multirun_aggregate":
        if "case" in record:
            parts.append(slug(record["case"]))
    elif schema == "predictability_aggregate":
        if "case" in record:
            parts.append(slug(record["case"]))
    elif schema == "long_run":
        if "seed" in record:
            parts.append(f"seed{format_token(record['seed'])}")
    else:
        if "scenario" in record:
            parts.append(slug(record["scenario"]))
        if "case_key" in record:
            parts.append(slug(record["case_key"]))
        if "case_name" in record:
            parts.append(slug(record["case_name"]))
        if "case" in record:
            parts.append(slug(record["case"]))
        if "k" in record:
            parts.append(f"k{format_token(record['k'])}")
        if "lambda_creation" in record:
            parts.append(f"lam{format_token(record['lambda_creation'])}")
        if "alpha_sigma_brownien" in record:
            parts.append(f"sigma{format_token(record['alpha_sigma_brownien'])}")
        if "epsilon" in record:
            parts.append(f"eps{format_token(record['epsilon'])}")
        if "seed" in record:
            parts.append(f"seed{format_token(record['seed'])}")
    parts.append(f"{index:03d}")
    return "_".join(parts)[:180]


def record_label(dataset_name: str, record: dict[str, Any], index: int) -> str:
    schema = _record_schema(dataset_name)
    bits = [dataset_name]
    if schema == "coupling_aggregate":
        if "k" in record:
            bits.append(f"k={record['k']}")
        for key, sym in (("lambda", "λ"), ("mu", "μ"), ("sigma", "σ"), ("theta", "θ"), ("taux_depreciation_endo", "δ_endo")):
            if key in record:
                bits.append(f"{sym}={record[key]}")
        if "bounded_share" in record:
            bits.append(f"p_borné={record['bounded_share']:.2f}")
    elif schema in ("multirun_aggregate", "predictability_aggregate"):
        if "case" in record:
            bits.append(str(record["case"]))
        if "dominant_class" in record:
            bits.append(str(record["dominant_class"]))
        elif "n_seeds" in record:
            bits.append(f"{record['n_seeds']} seeds")
    elif schema == "long_run":
        if "seed" in record:
            bits.append(f"seed={record['seed']}")
        if "final_alive" in record:
            bits.append(f"alive={record['final_alive']}")
        if record.get("stopped_early"):
            bits.append("stopped_early")
    else:
        if record.get("scenario"):
            bits.append(str(record["scenario"]))
        if record.get("case_key"):
            bits.append(str(record["case_key"]))
        if record.get("case_name"):
            bits.append(str(record["case_name"]))
        if record.get("case"):
            bits.append(str(record["case"]))
        if "k" in record:
            bits.append(f"k={record['k']}")
        if "lambda_creation" in record:
            bits.append(f"λ={record['lambda_creation']}")
        if "alpha_sigma_brownien" in record:
            bits.append(f"σ={record['alpha_sigma_brownien']}")
        if "epsilon" in record:
            bits.append(f"ε={record['epsilon']}")
        if "seed" in record:
            bits.append(f"seed={record['seed']}")
    if len(bits) == 1:
        bits.append(f"run {index}")
    return " | ".join(bits)


def _record_schema(dataset_name: str) -> str:
    """Retourne le schema de record pour ce dataset."""
    spec = DATASETS.get(dataset_name, {})
    return spec.get("schema", "standard")


def record_summary(spec: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    schema = spec.get("schema", "standard")
    summary: dict[str, Any] = {}
    summary["exported_at_local"] = EXPORT_STARTED_AT_LOCAL.isoformat()

    if schema == "coupling_aggregate":
        for key in ("k", "lambda", "mu", "sigma", "theta", "taux_depreciation_endo",
                    "bounded_share", "df_mean", "df_std", "alive_mean", "alive_std",
                    "failure_rate_mean", "gini_mean", "n"):
            if key in record:
                summary[key] = round_float(record[key])
        if "bounded_share" in record:
            summary["bounded_tail"] = record["bounded_share"] >= 0.5
    elif schema == "multirun_aggregate":
        for key in ("case", "n_seeds", "p_bounded", "p_bounded_ic95", "df_mean",
                    "alive_mean", "bounded_count"):
            if key in record:
                summary[key] = round_float(record[key]) if is_number(record[key]) else record[key]
        if "p_bounded" in record:
            summary["bounded_tail"] = record["p_bounded"] >= 0.5
    elif schema == "predictability_aggregate":
        for key in ("case", "n_seeds", "hurst_mean", "ac20_mean", "ar5_ratio_mean",
                    "perm_entropy_mean", "p_bounded", "dominant_class"):
            if key in record:
                summary[key] = record[key]
        if "p_bounded" in record:
            summary["bounded_tail"] = record["p_bounded"] >= 0.5
    elif schema == "long_run":
        for key in ("seed", "final_alive", "final_loans", "final_densite_fin", "final_gini",
                    "bounded_tail", "stopped_early", "avg_ms_per_step", "n_steps_done"):
            if key in record:
                summary[key] = record[key]
    else:
        for key in KEY_SUMMARY_FIELDS:
            if key in record:
                summary[key] = round_float(record[key])
        for key in ["executed_at_utc", "executed_at_local"]:
            if key in record:
                summary[key] = record[key]
        diagnostics = record.get("regime_diagnostics")
        if isinstance(diagnostics, dict):
            for key in [
                "tail_start",
                "alive_tail_slope_rel",
                "actif_tail_slope_rel",
                "densite_fin_tail_slope_rel",
                "failures_tail_slope_abs",
                "alive_tail_iqr_rel",
                "actif_tail_iqr_rel",
            ]:
                if key in diagnostics:
                    summary[key] = round_float(diagnostics[key])
    return summary


def aggregate_summary(dataset_name: str, spec: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {"dataset": dataset_name, "records": len(records)}
    summary["exported_at_local"] = EXPORT_STARTED_AT_LOCAL.isoformat()
    schema = spec.get("schema", "standard")

    if schema == "coupling_aggregate":
        shares = [float(r["bounded_share"]) for r in records if is_number(r.get("bounded_share"))]
        if shares:
            summary["bounded_share_mean"] = round_float(sum(shares) / len(shares))
            summary["bounded_share_max"] = round_float(max(shares))
        dfs = [float(r["df_mean"]) for r in records if is_number(r.get("df_mean"))]
        if dfs:
            summary["df_mean_avg"] = round_float(sum(dfs) / len(dfs))
    elif schema == "multirun_aggregate":
        for r in records:
            summary[r.get("case", f"case_{records.index(r)}")] = round_float(r.get("p_bounded"))
    elif schema == "predictability_aggregate":
        for cls in ("regime_structure", "variation_lente", "tendance_moderee"):
            count = sum(1 for r in records if cls in str(r.get("dominant_class", "")).replace("é", "e").replace("è", "e"))
            if count:
                summary[f"n_{cls}"] = count
    elif schema == "long_run":
        stopped = sum(1 for r in records if r.get("stopped_early"))
        summary["n_stopped_early"] = stopped
        summary["n_converged"] = len(records) - stopped
    else:
        for key in [
            "densite_fin_mean",
            "loan_density_mean",
            "failure_rate_mean",
            "cascade_size_mean",
            "gini_actif_mean",
            "elapsed_s",
        ]:
            values = [float(r[key]) for r in records if is_number(r.get(key))]
            if values:
                summary[f"{key}_avg"] = round_float(sum(values) / len(values))
                summary[f"{key}_min"] = round_float(min(values))
                summary[f"{key}_max"] = round_float(max(values))
        for flag in ["converged", "bounded_tail", "drop_5_detected"]:
            values = [r.get(flag) for r in records if flag in r]
            if values:
                summary[f"{flag}_rate"] = round_float(sum(bool(v) for v in values) / len(values))
    return summary


def plot_predictability_record(record: dict[str, Any], output_path: Path) -> None:
    """Carte radar des 4 indicateurs de prédictabilité pour un cas donné."""
    fig, ax = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
    ax.axis("off")
    cls = record.get("dominant_class", "-")
    lines = [
        f"Cas     : {record.get('case', '-')}",
        f"Classe  : {cls}",
        f"n_seeds : {record.get('n_seeds', '-')}",
        "",
        f"Hurst H       : {record.get('hurst_mean', '-')}",
        f"Autocorr r20  : {record.get('ac20_mean', '-')}",
        f"AR(5)/naif    : {record.get('ar5_ratio_mean', '-')}",
        f"Entropie Sp   : {record.get('perm_entropy_mean', '-')}",
        f"p_borné       : {record.get('p_bounded', '-')}",
    ]
    color = "#59a14f" if "mod" in str(cls) else ("#e15759" if "struct" in str(cls) else "#f28e2b")
    ax.text(0.05, 0.95, "\n".join(lines), ha="left", va="top", fontsize=11,
            family="monospace", transform=ax.transAxes)
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, color=color, alpha=0.08, transform=ax.transAxes))
    fig.suptitle(f"Prédictabilité — {record.get('case', '')}", fontsize=12)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_long_run_record(record: dict[str, Any], output_path: Path) -> None:
    """Résumé textuel pour un seed du long run."""
    fig, ax = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
    ax.axis("off")
    lines = [
        f"Seed            : {record.get('seed', '-')}",
        f"Pas simulés     : {record.get('n_steps_done', '-')} / {record.get('n_steps_requested', '-')}",
        f"Arrêt prématuré : {yes_no(record.get('stopped_early'))}",
        "",
        f"Alive final     : {record.get('final_alive', '-')}",
        f"Loans final     : {record.get('final_loans', '-')}",
        f"Densité fin.    : {record.get('final_densite_fin', '-')}",
        f"Gini            : {record.get('final_gini', '-')}",
        "",
        f"Avg ms/pas      : {record.get('avg_ms_per_step', '-')}",
        f"Max ms/pas      : {record.get('max_ms_per_step', '-')}",
        f"Durée totale    : {record.get('total_wall_s', '-')}s",
    ]
    ax.text(0.05, 0.95, "\n".join(lines), ha="left", va="top", fontsize=11,
            family="monospace", transform=ax.transAxes)
    fig.suptitle(f"Long run k3σ=0.005 — seed={record.get('seed', '')}", fontsize=12)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_record(record: dict[str, Any], output_path: Path) -> None:
    metrics = [
        ("densite_fin_mean", "densite"),
        ("loan_density_mean", "prets/entite"),
        ("failure_rate_mean", "faillites/pas"),
        ("cascade_size_mean", "cascade moy."),
        ("gini_actif_mean", "Gini actif"),
        ("corr_alive_actif_tail", "corr N/actif"),
    ]
    names = []
    values = []
    for key, label in metrics:
        if is_number(record.get(key)):
            names.append(label)
            values.append(float(record[key]))

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    ax = axes[0]
    if values:
        colors = ["#376795", "#f28e2b", "#59a14f", "#b07aa1", "#e15759", "#76b7b2"][: len(values)]
        ax.bar(range(len(values)), values, color=colors)
        ax.set_xticks(range(len(values)), names, rotation=30, ha="right")
        ax.set_title("Metriques mesurees")
        ax.grid(axis="y", alpha=0.25)
    else:
        ax.text(0.5, 0.5, "Aucune metrique numerique", ha="center", va="center")
        ax.axis("off")

    ax = axes[1]
    ax.axis("off")
    lines = [
        f"dataset: {record.get('case_key') or record.get('scenario') or '-'}",
        f"execute local: {record.get('executed_at_local', '-')}",
        f"export local: {EXPORT_STARTED_AT_LOCAL.isoformat()}",
        f"k: {record.get('k', '-')}",
        f"epsilon: {record.get('epsilon', '-')}",
        f"sigma alpha: {record.get('alpha_sigma_brownien', '-')}",
        f"seed: {record.get('seed', '-')}",
        f"regime strict: {yes_no(record.get('converged'))}",
        f"queue bornee: {yes_no(record.get('bounded_tail'))}",
        f"drop 5%: {yes_no(record.get('drop_5_detected'))}",
        f"t_regime: {record.get('t_regime', '-')}",
        f"t_mesure: {record.get('t_measure', '-')}",
    ]
    ax.text(0.02, 0.98, "\n".join(lines), ha="left", va="top", fontsize=11, family="monospace")
    fig.suptitle(record_label("simulation", record, 0), fontsize=12)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_aggregate(dataset_name: str, spec: dict[str, Any], records: list[dict[str, Any]], output_path: Path) -> None:
    schema = spec.get("schema", "standard")
    if dataset_name == "alpha_sigma":
        plot_alpha_sigma(records, output_path)
    elif dataset_name == "k_sweep":
        plot_k_sweep(records, output_path)
    elif dataset_name == "epsilon_runtime":
        plot_epsilon_runtime(records, output_path)
    elif dataset_name.startswith("codex_oat_") or dataset_name in ("claude_oat_robustness", "claude_lambda_fine_sweep"):
        plot_oat(records, output_path)
    elif schema == "coupling_aggregate":
        plot_coupling_heatmap(dataset_name, spec, records, output_path)
    elif schema == "multirun_aggregate":
        plot_multirun_limits(records, output_path)
    elif schema == "predictability_aggregate":
        plot_predictability(records, output_path)
    elif schema == "long_run":
        plot_long_run(records, output_path)
    else:
        plot_generic_aggregate(dataset_name, records, output_path)


def plot_alpha_sigma(records: list[dict[str, Any]], output_path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    grouped = group_by(records, "k")
    for k, rows in sorted(grouped.items(), key=lambda item: float(item[0])):
        agg = aggregate_xy(rows, "alpha_sigma_brownien", ["densite_fin_mean", "loan_density_mean", "bounded_tail", "corr_alive_actif_tail"])
        x = agg["x"]
        label = f"k={k}"
        axes[0, 0].plot(x, agg["densite_fin_mean"], marker="o", label=label)
        axes[0, 1].plot(x, agg["loan_density_mean"], marker="o", label=label)
        axes[1, 0].plot(x, agg["bounded_tail"], marker="o", label=label)
        axes[1, 1].plot(x, agg["corr_alive_actif_tail"], marker="o", label=label)
    axes[0, 0].set_ylabel("densite financiere")
    axes[0, 1].set_ylabel("prets actifs / entite")
    axes[1, 0].set_ylabel("frequence queue bornee")
    axes[1, 1].set_ylabel("corr N_alive / actif")
    for ax in axes.ravel():
        ax.set_xlabel("alpha_sigma_brownien")
        ax.set_xscale("symlog", linthresh=0.001)
        ax.grid(alpha=0.25)
        ax.legend()
    fig.suptitle("Balayage alpha_sigma en regime alpha homogene")
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_k_sweep(records: list[dict[str, Any]], output_path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    grouped = group_by(records, "scenario")
    for scenario, rows in sorted(grouped.items()):
        agg = aggregate_xy(rows, "k", ["densite_fin_mean", "loan_density_mean", "converged", "failure_rate_mean"])
        x = agg["x"]
        axes[0, 0].plot(x, agg["densite_fin_mean"], marker="o", label=scenario)
        axes[0, 1].plot(x, agg["loan_density_mean"], marker="o", label=scenario)
        axes[1, 0].plot(x, agg["converged"], marker="o", label=scenario)
        axes[1, 1].plot(x, agg["failure_rate_mean"], marker="o", label=scenario)
    axes[0, 0].set_ylabel("densite financiere")
    axes[0, 1].set_ylabel("prets actifs / entite")
    axes[1, 0].set_ylabel("frequence regime strict")
    axes[1, 1].set_ylabel("faillites / pas")
    for ax in axes.ravel():
        ax.set_xlabel("k")
        ax.grid(alpha=0.25)
        ax.legend()
    fig.suptitle("Balayage k")
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_epsilon_runtime(records: list[dict[str, Any]], output_path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    grouped = group_by(records, "scenario")
    for scenario, rows in sorted(grouped.items()):
        agg = aggregate_xy(rows, "epsilon", ["elapsed_s", "densite_fin_mean", "loan_density_mean", "converged"])
        x = agg["x"]
        axes[0, 0].plot(x, agg["elapsed_s"], marker="o", label=scenario)
        axes[0, 1].plot(x, agg["densite_fin_mean"], marker="o", label=scenario)
        axes[1, 0].plot(x, agg["loan_density_mean"], marker="o", label=scenario)
        axes[1, 1].plot(x, agg["converged"], marker="o", label=scenario)
    axes[0, 0].set_ylabel("temps execution (s)")
    axes[0, 1].set_ylabel("densite financiere")
    axes[1, 0].set_ylabel("prets actifs / entite")
    axes[1, 1].set_ylabel("frequence regime strict")
    for ax in axes.ravel():
        ax.set_xlabel("epsilon")
        ax.set_xscale("log")
        ax.grid(alpha=0.25)
        ax.legend()
    fig.suptitle("Epsilon, cout numerique et microcredits")
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_oat(records: list[dict[str, Any]], output_path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
    metrics = [
        ("measure_densite_fin_mean", "densite financiere"),
        ("measure_loan_density_mean", "prets / entite"),
        ("measure_n_alive_mean", "n_alive"),
        ("measure_failure_rate_mean", "faillites / pas"),
    ]
    for ax, (metric, label) in zip(axes.ravel(), metrics):
        for center in sorted({r.get("center") for r in records if r.get("center")}):
            base_rows = [
                r for r in records
                if r.get("center") == center and r.get("parameter") == "__center__" and is_number(r.get(metric))
            ]
            if not base_rows:
                continue
            baseline = sum(float(r[metric]) for r in base_rows) / len(base_rows)
            effects = []
            for row in records:
                if row.get("center") != center or row.get("parameter") == "__center__" or not is_number(row.get(metric)):
                    continue
                effects.append((str(row.get("parameter")), float(row[metric]) - baseline))
            effects.sort(key=lambda item: abs(item[1]), reverse=True)
            top = effects[:12]
            x = np.arange(len(top))
            offset = -0.18 if center == "subcritical_k3" else 0.18
            ax.bar(x + offset, [v for _, v in top], width=0.35, label=center)
            ax.set_xticks(x, [name for name, _ in top], rotation=70, ha="right", fontsize=7)
        ax.set_ylabel(f"delta {label}")
        ax.grid(axis="y", alpha=0.25)
        ax.legend(fontsize=7)
    fig.suptitle("Screening OAT Codex")
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_coupling_heatmap(dataset_name: str, spec: dict[str, Any], records: list[dict[str, Any]], output_path: Path) -> None:
    """Heatmap 2D de bounded_share et densite financiere pour les couplages."""
    # Detect the two axes from the record fields
    axis_candidates = [("lambda", "k"), ("mu", "k"), ("sigma", "k"),
                       ("theta", "taux_depreciation_endo"), ("theta", "k")]
    x_key, y_key = "lambda", "k"
    for xc, yc in axis_candidates:
        if any(xc in r for r in records) and any(yc in r for r in records):
            x_key, y_key = xc, yc
            break

    xs = sorted(set(r[x_key] for r in records if x_key in r))
    ys = sorted(set(r[y_key] for r in records if y_key in r))

    bounded = np.full((len(ys), len(xs)), np.nan)
    df_grid = np.full((len(ys), len(xs)), np.nan)
    for r in records:
        if x_key not in r or y_key not in r:
            continue
        xi = xs.index(r[x_key])
        yi = ys.index(r[y_key])
        if is_number(r.get("bounded_share")):
            bounded[yi, xi] = float(r["bounded_share"])
        if is_number(r.get("df_mean")):
            df_grid[yi, xi] = float(r["df_mean"])

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    for ax, data, title, cmap in [
        (axes[0], bounded, "Fraction seeds bornés (bounded_share)", "RdYlGn"),
        (axes[1], df_grid, "Densité financière moyenne (df_mean)", "Blues"),
    ]:
        im = ax.imshow(data, aspect="auto", vmin=0, vmax=1 if "bounded" in title else None,
                       cmap=cmap, origin="lower")
        fig.colorbar(im, ax=ax, shrink=0.8)
        ax.set_xticks(range(len(xs)), [str(x) for x in xs], rotation=45, ha="right")
        ax.set_yticks(range(len(ys)), [str(y) for y in ys])
        ax.set_xlabel(x_key)
        ax.set_ylabel(y_key)
        ax.set_title(title)
        for yi in range(len(ys)):
            for xi in range(len(xs)):
                v = data[yi, xi]
                if not np.isnan(v):
                    ax.text(xi, yi, f"{v:.2f}", ha="center", va="center", fontsize=8,
                            color="white" if v > 0.6 else "black")
    fig.suptitle(spec.get("label", dataset_name))
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_multirun_limits(records: list[dict[str, Any]], output_path: Path) -> None:
    """Barres de probabilité p_borné ± IC95% pour les cas limites."""
    cases = [r.get("case", f"cas_{i}") for i, r in enumerate(records)]
    p_values = [float(r.get("p_bounded", 0)) for r in records]
    ic_values = [float(r.get("p_bounded_ic95", 0.15)) for r in records]

    order = sorted(range(len(cases)), key=lambda i: p_values[i], reverse=True)
    cases = [cases[i] for i in order]
    p_values = [p_values[i] for i in order]
    ic_values = [ic_values[i] for i in order]

    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    colors = ["#59a14f" if p >= 0.5 else "#e15759" for p in p_values]
    ax.barh(range(len(cases)), p_values, xerr=ic_values, color=colors, capsize=4)
    ax.axvline(0.5, color="black", linestyle="--", linewidth=0.8, alpha=0.5, label="p=0.5")
    ax.set_yticks(range(len(cases)), cases)
    ax.set_xlim(0, 1)
    ax.set_xlabel("p_borné ± IC95%")
    ax.set_title("Probabilité de régime borné par cas limite (13 seeds)")
    ax.grid(axis="x", alpha=0.3)
    ax.legend()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_predictability(records: list[dict[str, Any]], output_path: Path) -> None:
    """Scatter Hurst vs Sp coloré par classe dynamique."""
    CLASS_COLORS = {
        "régime_structuré": "#e15759",
        "regime_structure": "#e15759",
        "variation_lente": "#f28e2b",
        "tendance_modérée": "#59a14f",
        "tendance_moderee": "#59a14f",
    }
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)

    for r in records:
        cls = r.get("dominant_class", "")
        color = CLASS_COLORS.get(cls, "#aaaaaa")
        hurst = r.get("hurst_mean")
        sp = r.get("perm_entropy_mean")
        ar = r.get("ar5_ratio_mean")
        case = str(r.get("case", ""))
        if is_number(hurst) and is_number(sp):
            axes[0].scatter([float(hurst)], [float(sp)], color=color, s=60, zorder=3)
            axes[0].annotate(case.replace("long_long|case=", "")[:18], (float(hurst), float(sp)),
                             fontsize=6, ha="left", va="bottom")
        if is_number(ar) and is_number(sp):
            axes[1].scatter([float(ar)], [float(sp)], color=color, s=60, zorder=3)
            axes[1].annotate(case.replace("long_long|case=", "")[:18], (float(ar), float(sp)),
                             fontsize=6, ha="left", va="bottom")

    axes[0].axhline(0.1, color="gray", linestyle=":", linewidth=0.7)
    axes[0].axhline(0.75, color="gray", linestyle=":", linewidth=0.7)
    axes[0].set_xlabel("Exposant de Hurst H (R/S)")
    axes[0].set_ylabel("Entropie de permutation Sp")
    axes[0].set_title("H vs Sp par regime")
    axes[0].grid(alpha=0.2)

    axes[1].axvline(1.0, color="gray", linestyle=":", linewidth=0.7)
    axes[1].axhline(0.75, color="gray", linestyle=":", linewidth=0.7)
    axes[1].set_xlabel("Ratio AR(5)/naif (>1 = AR no edge)")
    axes[1].set_ylabel("Entropie de permutation Sp")
    axes[1].set_title("AR/naif vs Sp par regime")
    axes[1].grid(alpha=0.2)

    for cls, color in CLASS_COLORS.items():
        if "_" not in cls.split("_")[0]:
            continue
        axes[0].scatter([], [], color=color, label=cls, s=40)
    axes[0].legend(fontsize=7)
    fig.suptitle("Prédictabilité par classe dynamique")
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_long_run(records: list[dict[str, Any]], output_path: Path) -> None:
    """Résumé du long run k3σ=0.005 : alive et loans finaux par seed."""
    seeds = [r.get("seed", i) for i, r in enumerate(records)]
    alives = [r.get("final_alive", 0) for r in records]
    loans = [r.get("final_loans", 0) for r in records]
    steps = [r.get("n_steps_done", 0) for r in records]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), constrained_layout=True)
    x = range(len(records))
    axes[0].bar(x, alives, color="#376795", label="n_alive final")
    axes[0].bar(x, loans, bottom=alives, color="#f28e2b", alpha=0.7, label="n_loans final")
    axes[0].set_xticks(x, [f"seed={s}\n{st} pas" for s, st in zip(seeds, steps)], fontsize=8)
    axes[0].set_ylabel("Entités / prêts")
    axes[0].set_title("Population et prêts en fin de run")
    axes[0].legend()
    axes[0].grid(axis="y", alpha=0.3)

    avg_ms = [r.get("avg_ms_per_step", 0) for r in records]
    stopped = [r.get("stopped_early", False) for r in records]
    colors = ["#e15759" if s else "#59a14f" for s in stopped]
    axes[1].bar(x, avg_ms, color=colors)
    axes[1].set_xticks(x, [f"seed={s}" for s in seeds], fontsize=8)
    axes[1].set_ylabel("ms / pas (moyenne)")
    axes[1].set_title("Coût computationnel (rouge = arrêt prématuré)")
    axes[1].grid(axis="y", alpha=0.3)

    fig.suptitle("Long run k=3, σ=0.005 — croissance explosive confirmée sur 5 seeds")
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_generic_aggregate(dataset_name: str, records: list[dict[str, Any]], output_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    keys = ["densite_fin_mean", "loan_density_mean", "failure_rate_mean", "gini_actif_mean"]
    values = []
    labels = []
    for key in keys:
        nums = [float(r[key]) for r in records if is_number(r.get(key))]
        if nums:
            labels.append(key.replace("_mean", ""))
            values.append(sum(nums) / len(nums))
    if values:
        axes[0].bar(range(len(values)), values, color=["#376795", "#f28e2b", "#59a14f", "#e15759"][: len(values)])
        axes[0].set_xticks(range(len(values)), labels, rotation=25, ha="right")
        axes[0].grid(axis="y", alpha=0.25)
    else:
        axes[0].axis("off")
    seeds = [r.get("seed") for r in records]
    density = [r.get("densite_fin_mean") for r in records]
    if all(is_number(x) for x in density):
        axes[1].plot(range(len(density)), [float(x) for x in density], marker="o")
        axes[1].set_ylabel("densite financiere")
        axes[1].set_xlabel("index de run")
        axes[1].grid(alpha=0.25)
        if any(seed is not None for seed in seeds):
            axes[1].set_xticks(range(len(seeds)), [str(seed) for seed in seeds], rotation=30, ha="right")
    else:
        axes[1].axis("off")
    fig.suptitle(dataset_name)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def aggregate_xy(records: list[dict[str, Any]], x_key: str, y_keys: list[str]) -> dict[str, list[float]]:
    buckets: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if is_number(record.get(x_key)):
            buckets[float(record[x_key])].append(record)
    result: dict[str, list[float]] = {"x": []}
    for key in y_keys:
        result[key] = []
    for x in sorted(buckets):
        result["x"].append(x)
        rows = buckets[x]
        for key in y_keys:
            vals = []
            for row in rows:
                value = row.get(key)
                if isinstance(value, bool):
                    vals.append(1.0 if value else 0.0)
                elif is_number(value):
                    vals.append(float(value))
            result[key].append(sum(vals) / len(vals) if vals else math.nan)
    return result


def group_by(records: list[dict[str, Any]], key: str) -> dict[Any, list[dict[str, Any]]]:
    grouped: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record.get(key, "-")].append(record)
    return grouped


def write_manifest(exported: list[str], lab_runs_dir: Path) -> None:
    manifest_dir = recreate_run_dir(lab_runs_dir, "sensitivity_manifest")
    manifest = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "exported_at_local": datetime.now(timezone.utc).astimezone().isoformat(),
        "source": str(STUDY_DIR),
        "run_ids": exported,
    }
    (manifest_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    fig, ax = plt.subplots(figsize=(8, 4), constrained_layout=True)
    ax.axis("off")
    ax.text(
        0.02,
        0.98,
        f"Export etude de sensibilite\n\n{len(exported)} runs exportes\nSource:\n{STUDY_DIR}\n\nOuvrir les groupes {MODEL_ID} dans Simulation Lab.",
        ha="left",
        va="top",
        fontsize=12,
    )
    fig.savefig(manifest_dir / "overview.png", dpi=150)
    plt.close(fig)
    write_metadata(
        manifest_dir,
        run_metadata(
            run_id="sensitivity_manifest",
            label="Etude sensibilite - manifeste",
            parameters={"records": len(exported)},
            seed=None,
            summary={"exported_runs": len(exported), "exported_at_local": EXPORT_STARTED_AT_LOCAL.isoformat()},
            message="Point d'entree vers les runs synthetiques de l'etude de sensibilite.",
            artifacts=collect_artifacts(manifest_dir),
            important=True,
        ),
    )


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    if isinstance(value, tuple):
        return [sanitize(v) for v in value]
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    return value


def round_float(value: Any) -> Any:
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return round(value, 6)
    return value


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def yes_no(value: Any) -> str:
    if value is None:
        return "-"
    return "oui" if bool(value) else "non"


def slug(value: Any) -> str:
    text = str(value).strip().lower()
    keep = []
    for char in text:
        if char.isalnum():
            keep.append(char)
        elif char in {"_", "-", "."}:
            keep.append("_")
    return "".join(keep).strip("_") or "x"


def format_token(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:g}".replace("-", "m").replace(".", "p")
    return str(value).replace("-", "m").replace(".", "p")


if __name__ == "__main__":
    main()
