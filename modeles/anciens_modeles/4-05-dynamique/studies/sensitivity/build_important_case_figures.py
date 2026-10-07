"""
Construit des planches comparatives pour les cas importants de l'etude.

Ces figures sont proches de simulation_lab_regime_examples.pdf, mais ciblees sur
les questions ouvertes de l'etude : seuil k, fenetre alpha_sigma, fragmentation
en microcredits, et effet epsilon. Elles sont ajoutees comme un run consultable
dans Simulation Lab.
"""

from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


STUDY_DIR = Path(__file__).resolve().parent
JUPYTER_DIR = STUDY_DIR.parents[3]
LAB_RUNS_DIR = JUPYTER_DIR / "simulation_lab_data" / "runs"
MODEL_ID = "etude_sensibilite_27_04_wip"
FIGURE_RUN_ID = "sensitivity_important_cases_figures"

IMPORTANT_CASES = {
    "alpha_sigma": [
        ("k=3, sigma=0, sous-critique", "sensitivity_alpha_sigma_hom_alpha_sigmak3sigma0seed42eps0_001steps1500_k3_sigma0_eps0p001_seed42_001"),
        ("k=3, sigma=0.005, entree regime", "sensitivity_alpha_sigma_hom_alpha_sigmak3sigma0_005seed42eps0_001steps1500_k3_sigma0p005_eps0p001_seed42_010"),
        ("k=3, sigma=0.02, fenetre active", "sensitivity_alpha_sigma_hom_alpha_sigmak3sigma0_02seed42eps0_001steps1500_k3_sigma0p02_eps0p001_seed42_016"),
        ("k=3, sigma=0.05, sortie regime", "sensitivity_alpha_sigma_hom_alpha_sigmak3sigma0_05seed42eps0_001steps1500_k3_sigma0p05_eps0p001_seed42_019"),
        ("k=4, sigma=0, regime robuste", "sensitivity_alpha_sigma_hom_alpha_sigmak4sigma0seed42eps0_001steps1500_k4_sigma0_eps0p001_seed42_025"),
        ("k=4, sigma=0.02, densite max", "sensitivity_alpha_sigma_hom_alpha_sigmak4sigma0_02seed42eps0_001steps1500_k4_sigma0p02_eps0p001_seed42_040"),
        ("k=4, sigma=0.05, microcredits", "sensitivity_alpha_sigma_hom_alpha_sigmak4sigma0_05seed42eps0_001steps1500_k4_sigma0p05_eps0p001_seed42_043"),
        ("k=4, sigma=0.1, effondrement volume", "sensitivity_alpha_sigma_hom_alpha_sigmak4sigma0_1seed42eps0_001steps1500_k4_sigma0p1_eps0p001_seed42_046"),
    ],
    "k_threshold": [
        ("k=3, avant seuil", "sensitivity_k_sweep_homogeneous_homogeneousk3seed42eps0_001steps1500_k3_eps0p001_seed42_031"),
        ("k=4, seuil regime", "sensitivity_k_sweep_homogeneous_homogeneousk4seed42eps0_001steps1500_k4_eps0p001_seed42_034"),
        ("k=20, plateau", "sensitivity_k_sweep_homogeneous_homogeneousk20seed42eps0_001steps1500_k20_eps0p001_seed42_046"),
        ("k=50, grand k", "sensitivity_k_sweep_homogeneous_homogeneousk50seed42eps0_001steps1500_k50_eps0p001_seed42_050"),
    ],
    "epsilon": [
        ("eps=1e-6, reference lente", "sensitivity_epsilon_runtime_hom_k4_hom_k4k4steps1000eps1e_06seed42_k4_eps1em06_seed42_010"),
        ("eps=1e-3, compromis", "sensitivity_epsilon_runtime_hom_k4_hom_k4k4steps1000eps0_001seed42_k4_eps0p001_seed42_013"),
        ("eps=1e-2, seuil destructeur", "sensitivity_epsilon_runtime_hom_k4_hom_k4k4steps1000eps0_01seed42_k4_eps0p01_seed42_014"),
    ],
}


def main() -> None:
    run_dir = LAB_RUNS_DIR / FIGURE_RUN_ID
    run_dir.mkdir(parents=True, exist_ok=True)

    produced = []
    for group_name, cases in IMPORTANT_CASES.items():
        rows = []
        for label, run_id in cases:
            case_rows, source_path = read_case_rows(LAB_RUNS_DIR / run_id)
            if not case_rows:
                continue
            rows.append((label, run_id, source_path, case_rows))
        if not rows:
            continue
        output_pdf = run_dir / f"{group_name}_trajectoires.pdf"
        output_png = run_dir / f"{group_name}_trajectoires.png"
        plot_cases(rows, output_pdf, title=title_for_group(group_name))
        plot_cases(rows, output_png, title=title_for_group(group_name))
        produced.extend([output_pdf.name, output_png.name])

    write_notes(run_dir)
    metadata = {
        "run_id": FIGURE_RUN_ID,
        "model_id": MODEL_ID,
        "parameters": {"source": "important_cases", "groups": list(IMPORTANT_CASES)},
        "seed": None,
        "label": "Etude sensibilite - planches cas importants",
        "batch_id": "sensitivity_parameter_study",
        "status": "completed",
        "keep": True,
        "important": True,
        "trashed": False,
        "trashed_at": None,
        "created_at": "2026-04-28T00:00:00+00:00",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "figure_groups": len(produced) // 2,
            "expected_cases": sum(len(v) for v in IMPORTANT_CASES.values()),
            "available_cases": count_available_cases(),
        },
        "artifacts": collect_artifacts(run_dir),
        "preview_artifact": "alpha_sigma_trajectoires.png" if (run_dir / "alpha_sigma_trajectoires.png").exists() else None,
        "message": "Planches comparatives generees depuis les CSV complets des cas importants.",
        "comment": "",
        "extra": {"source": "studies/sensitivity/build_important_case_figures.py"},
    }
    (run_dir / "run.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Figures produites dans {run_dir}: {', '.join(produced) if produced else 'aucune'}")


def find_stats_path(run_dir: Path) -> Path | None:
    candidates = sorted(run_dir.glob("legacy_output/*/csv/indicateurs_systemiques.csv"))
    return candidates[-1] if candidates else None


def read_case_rows(run_dir: Path) -> tuple[list[dict[str, float]], Path | None]:
    compact = run_dir / "compact_timeseries.json"
    if compact.exists():
        payload = json.loads(compact.read_text(encoding="utf-8"))
        return payload.get("rows", []), compact
    stats_path = find_stats_path(run_dir)
    if stats_path is None:
        return [], None
    return read_system_stats(stats_path), stats_path


def read_system_stats(path: Path) -> list[dict[str, float]]:
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(line for line in f if not line.startswith("#"))
        for row in reader:
            actif = parse_float(row.get("actif_total"))
            volume = parse_float(row.get("volume_prets"))
            alive = parse_float(row.get("nb_entites"))
            loans = parse_float(row.get("nb_prets"))
            rows.append({
                "step": parse_float(row.get("step")),
                "alive": alive,
                "actif": actif,
                "volume_prets": volume,
                "densite_fin": parse_float(row.get("densite_financiere")) if row.get("densite_financiere") else safe_ratio(volume, actif),
                "loan_density": safe_ratio(loans, alive),
                "failures": parse_float(row.get("nb_faillites")),
                "gini": parse_float(row.get("gini_actif_total")),
            })
    return rows


def plot_cases(cases: list[tuple[str, str, Path, list[dict[str, float]]]], output_path: Path, *, title: str) -> None:
    n = len(cases)
    fig, axes = plt.subplots(n, 4, figsize=(16, max(2.4 * n, 4.0)), squeeze=False)
    for row_axes, (label, run_id, _path, rows) in zip(axes, cases):
        t = [r["step"] for r in rows]
        series = [
            ([r["alive"] for r in rows], "n_alive", "tab:blue"),
            ([r["actif"] for r in rows], "actif total", "tab:green"),
            ([r["densite_fin"] for r in rows], "volume prêts / actif", "tab:orange"),
            ([r["loan_density"] for r in rows], "prêts / entité", "tab:red"),
        ]
        for ax, (values, ylabel, color) in zip(row_axes, series):
            ax.plot(t, values, linewidth=1.0, color=color)
            ax.set_ylabel(ylabel, fontsize=8)
            ax.grid(True, alpha=0.25)
            ax.tick_params(labelsize=8)
        row_axes[0].set_title(label, fontsize=9, loc="left")
        row_axes[-1].set_title(short_run(run_id), fontsize=7, loc="right")
    for ax in axes[-1]:
        ax.set_xlabel("pas")
    fig.suptitle(title, fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def title_for_group(group_name: str) -> str:
    return {
        "alpha_sigma": "Cas importants - fenetre alpha_sigma en alpha homogene",
        "k_threshold": "Cas importants - seuil et plateau en k",
        "epsilon": "Cas importants - epsilon, vitesse et microcredits",
    }.get(group_name, group_name)


def write_notes(run_dir: Path) -> None:
    lines = [
        "Planches comparatives des cas importants",
        "========================================",
        "",
        "Chaque ligne correspond a un run enrichi avec les sorties completes du modele.",
        "Colonnes : n_alive, actif total, densite financiere en volume, nombre de prets par entite.",
        "",
        "Si un cas manque, il faut d'abord executer populate_lab_full_graphs.py pour ce run.",
        "",
    ]
    for group, cases in IMPORTANT_CASES.items():
        lines.append(f"[{group}]")
        for label, run_id in cases:
            status = "ok" if find_stats_path(LAB_RUNS_DIR / run_id) else "manquant"
            lines.append(f"  - {status:8s} {label}: {run_id}")
        lines.append("")
    (run_dir / "README.txt").write_text("\n".join(lines), encoding="utf-8")


def collect_artifacts(run_dir: Path) -> list[dict[str, str]]:
    artifacts = []
    for path in sorted(run_dir.iterdir()):
        if not path.is_file() or path.name == "run.json":
            continue
        suffix = path.suffix.lower()
        if suffix in {".png", ".jpg", ".jpeg"}:
            kind = "image"
        elif suffix in {".txt", ".json", ".md"}:
            kind = "text"
        else:
            kind = "file"
        artifacts.append({"relative_path": path.name, "kind": kind, "label": path.name, "description": ""})
    return artifacts


def count_available_cases() -> int:
    return sum(1 for cases in IMPORTANT_CASES.values() for _label, run_id in cases if read_case_rows(LAB_RUNS_DIR / run_id)[0])


def parse_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        result = float(value)
        return result if math.isfinite(result) else 0.0
    except ValueError:
        return 0.0


def safe_ratio(num: float, den: float) -> float:
    return num / den if den else 0.0


def short_run(run_id: str) -> str:
    return run_id.replace("sensitivity_", "")[-52:]


if __name__ == "__main__":
    main()
