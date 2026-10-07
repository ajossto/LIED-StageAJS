"""
Planches comparatives Codex pour le screening OAT.

Lit les runs Simulation Lab enrichis, utilise compact_timeseries.json et produit
des planches de trajectoires pour les cas OAT les plus informatifs.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


STUDY_DIR = Path(__file__).resolve().parent
JUPYTER_DIR = STUDY_DIR.parents[3]
LAB_RUNS_DIR = JUPYTER_DIR / "simulation_lab_data" / "runs"
FIGURES_DIR = STUDY_DIR / "report" / "figures"
MODEL_ID = "etude_sensibilite_27_04_wip"
RUN_ID = "sensitivity_codex_oat_key_figures"

CASES = [
    ("k=3 centre sous-critique", "subcritical_k3", "__center__", None),
    ("k=3 sigma=0.005 entree regime", "subcritical_k3", "alpha_sigma_brownien", 0.005),
    ("k=3 mu=0 regime dense", "subcritical_k3", "mu", 0.0),
    ("k=3 theta=0.5 regime", "subcritical_k3", "theta", 0.5),
    ("k=3 k=4 seuil", "subcritical_k3", "n_candidats_pool", 4),
    ("k=4 centre regime", "regime_k4", "__center__", None),
    ("k=4 theta=0.2 sortie regime", "regime_k4", "theta", 0.2),
    ("k=4 mu=0.1 sortie regime", "regime_k4", "mu", 0.1),
    ("k=4 epsilon=1e-2 destructeur", "regime_k4", "epsilon", 0.01),
    ("k=4 sigma=0.02 densite haute", "regime_k4", "alpha_sigma_brownien", 0.02),
]


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for label, center, parameter, value in CASES:
        found = find_run(center, parameter, value)
        if not found:
            continue
        run_dir, record = found
        compact = run_dir / "compact_timeseries.json"
        payload = json.loads(compact.read_text(encoding="utf-8"))
        rows.append((label, run_dir.name, record, payload.get("rows", [])))

    pdf = FIGURES_DIR / "codex_oat_key_trajectories.pdf"
    png = FIGURES_DIR / "codex_oat_key_trajectories.png"
    plot(rows, pdf)
    plot(rows, png)
    export_lab_run(rows, [pdf, png])
    print(f"Figures OAT Codex: {pdf} ; {png}")


def find_run(center: str, parameter: str, value: Any) -> tuple[Path, dict[str, Any]] | None:
    for run_dir in sorted(LAB_RUNS_DIR.glob("sensitivity_codex_oat_steps1500_seeds42_*")):
        record_path = run_dir / "record.json"
        compact_path = run_dir / "compact_timeseries.json"
        if not record_path.exists() or not compact_path.exists():
            continue
        record = json.loads(record_path.read_text(encoding="utf-8"))
        if record.get("center") != center or record.get("parameter") != parameter:
            continue
        if values_equal(record.get("value"), value):
            return run_dir, record
    return None


def values_equal(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return a is b
    try:
        return abs(float(a) - float(b)) <= 1e-12
    except (TypeError, ValueError):
        return a == b


def plot(cases: list[tuple[str, str, dict[str, Any], list[dict[str, float]]]], path: Path) -> None:
    fig, axes = plt.subplots(len(cases), 4, figsize=(16, max(2.1 * len(cases), 4)), squeeze=False)
    for row_axes, (label, run_id, record, data) in zip(axes, cases):
        t = [r["step"] for r in data]
        series = [
            ("alive", "n_alive", "tab:blue"),
            ("actif", "actif total", "tab:green"),
            ("densite_fin", "densite fin.", "tab:orange"),
            ("loan_density", "prets / entite", "tab:red"),
        ]
        for ax, (key, ylabel, color) in zip(row_axes, series):
            ax.plot(t, [r[key] for r in data], linewidth=1.0, color=color)
            ax.set_ylabel(ylabel, fontsize=8)
            ax.grid(True, alpha=0.25)
            ax.tick_params(labelsize=8)
        row_axes[0].set_title(label, loc="left", fontsize=9)
        row_axes[-1].set_title(short_id(run_id), loc="right", fontsize=7)
    for ax in axes[-1]:
        ax.set_xlabel("pas")
    fig.suptitle("OAT Codex - trajectoires des cas informatifs", fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.985])
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def export_lab_run(cases: list[tuple[str, str, dict[str, Any], list[dict[str, float]]]], figure_paths: list[Path]) -> None:
    run_dir = LAB_RUNS_DIR / RUN_ID
    run_dir.mkdir(parents=True, exist_ok=True)
    for fig in figure_paths:
        target = run_dir / fig.name
        target.write_bytes(fig.read_bytes())
    (run_dir / "cases.json").write_text(
        json.dumps(
            [{"label": label, "run_id": run_id, "record": record} for label, run_id, record, _data in cases],
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    artifacts = []
    for path in sorted(run_dir.iterdir()):
        if path.name == "run.json" or not path.is_file():
            continue
        kind = "image" if path.suffix.lower() == ".png" else "text" if path.suffix.lower() == ".json" else "file"
        artifacts.append({"relative_path": path.name, "kind": kind, "label": path.name, "description": ""})
    meta = {
        "run_id": RUN_ID,
        "model_id": MODEL_ID,
        "parameters": {"source": "codex_oat_screen", "cases": len(cases)},
        "seed": None,
        "label": "Etude sensibilite - OAT Codex trajectoires",
        "batch_id": "sensitivity_parameter_study",
        "status": "completed",
        "keep": True,
        "important": True,
        "trashed": False,
        "trashed_at": None,
        "created_at": "2026-04-28T00:00:00+00:00",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"cases": len(cases)},
        "artifacts": artifacts,
        "preview_artifact": "codex_oat_key_trajectories.png",
        "message": "Planches de trajectoires OAT Codex construites depuis compact_timeseries.json.",
        "comment": "",
        "extra": {"source": "studies/sensitivity/build_codex_oat_figures.py"},
    }
    (run_dir / "run.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def short_id(run_id: str) -> str:
    return run_id.replace("sensitivity_codex_oat_steps1500_seeds42_", "")[-58:]


if __name__ == "__main__":
    main()
