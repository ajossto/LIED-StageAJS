"""Rend tous les runs M4.3Live consultables dans `simulation_lab`.

Même mécanisme que `m4_3_credit_soc/scripts/import_to_simulation_lab.py`,
dont la sûreté a déjà été vérifiée dans cette lignée : chaque dossier de run
est SYMLINKÉ dans `simulation_lab_data/runs/<run_id>/`, avec un `run.json`
au format managé écrit à l'intérieur. `RunStorage.delete_run()` déplace le
lien (pas la cible) et la collecte d'artefacts ne descend jamais
destructivement dans un lien : supprimer un run importé depuis l'IHM ne
touche donc jamais les données de la campagne.

Le script génère aussi, pour chaque run, une figure `figures/macro_overview.png`
— sans elle, la page « Résultats » n'aurait qu'un CSV à montrer. Les
interventions du run y sont repérées par un trait vertical.

Idempotent : relançable à tout moment ; `--force-figures` régénère les
figures existantes.

    python3 scripts/import_to_simulation_lab.py
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
JUPYTER_ROOT = ROOT.parent
sys.path.insert(0, str(JUPYTER_ROOT))
sys.path.insert(0, str(ROOT))

from simulation_lab.contracts import collect_artifacts  # noqa: E402
from simulation_lab.plot_utils import apply_style  # noqa: E402
from simulation_lab.settings import RUNS_DIR, ensure_directories  # noqa: E402

MODEL_ID = "m4_3live_v2_credit_soc"

# (racine sous results/, gabarit d'identifiant, étiquette, rôle)
GROUPS = (
    ("campaign/burn", "m4_3live_v2__burn__{seed}", "amorçage/{seed}",
     "amorçage partagé 0 → t₀, source des snapshots"),
    ("campaign/arms", "m4_3live_v2__arm__{cell}__{seed}", "campagne/{cell}/{seed}",
     "bras de la campagne §7"),
    ("ablation_k0", "m4_3live_v2__ablation__{cell}__{seed}", "ablation K0/{cell}/{seed}",
     "ablation sur le capital de naissance"),
    ("tension_sweep", "m4_3live_v2__tension__{cell}__{seed}", "balayage tension/{cell}/{seed}",
     "balayage à trois leviers pour tester la tension comme paramètre d'état"),
    ("time_rescaling", "m4_3live_v2__temps__{cell}__{seed}", "recalage temporel/{cell}/{seed}",
     "covariance de pas de temps : λ×2, δ → 2δ−δ², σ → √2σ"),
)
# Les runs rangés par γ PUIS par bras ont un niveau d'arborescence de plus :
# ils sont traités à part.
NESTED = (
    ("scaling_gamma", "m4_3live_v2__scaling__{gamma}__{cell}__{seed}",
     "loi d'échelle/{gamma}/{cell}/{seed}",
     "test de la loi ε = 1/(1-γ)"),
    ("scaling_theory", "m4_3live_v2__covariance__{gamma}__{cell}__{seed}",
     "covariance d'échelle/{gamma}/{cell}/{seed}",
     "vérification directe de la covariance d'échelle"),
    ("tension_vs_A", "m4_3live_v2__tensionA__{gamma}__{cell}__{seed}",
     "tension contre A/{gamma}/{cell}/{seed}",
     "balayage en A à K0 fixé : l'exposant dlnT/dlnA dépend-il de γ ?"),
)

PANELS = (
    ("prod_tot", None, "production agrégée prod_tot"),
    ("K_tot", "pop", "capital K_tot (gauche) et population pop (droite)"),
    ("deaths", "defaults", "morts (gauche) et défauts de liquidité (droite)"),
    ("loan_volume", "mkt_blocked_dir", "volume de prêt (gauche) et paires bloquées (droite)"),
)


def iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def read_series(path: Path) -> dict[str, np.ndarray]:
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {name: np.array([float(row[name]) for row in rows]) for name in rows[0]}


def make_figure(run_dir: Path, label: str, interventions: list[dict], force: bool) -> bool:
    target = run_dir / "figures" / "macro_overview.png"
    if target.exists() and not force:
        return False
    series_path = run_dir / "series.csv"
    if not series_path.exists():
        return False
    columns = read_series(series_path)
    time_axis = columns["t"]
    figure, axes = plt.subplots(2, 2, figsize=(12, 7))
    for axis, (left, right, title) in zip(axes.ravel(), PANELS):
        axis.plot(time_axis, columns[left], color="#294c60", lw=0.8, label=left)
        axis.set_ylabel(left, color="#294c60")
        if right is not None:
            twin = axis.twinx()
            twin.plot(time_axis, columns[right], color="#c1440e", lw=0.8, label=right)
            twin.set_ylabel(right, color="#c1440e")
        for entry in interventions:
            axis.axvline(float(entry["t"]), color="black", ls=":", lw=0.9)
            axis.text(
                float(entry["t"]), axis.get_ylim()[1], f" {entry['param']}",
                fontsize=6, va="top", ha="left",
            )
        axis.set_title(title, fontsize=9)
        axis.set_xlabel("t (pas)")
        axis.grid(True, alpha=0.2)
    figure.suptitle(f"M4.3Live — {label}  (n={len(time_axis)} pas)")
    figure.tight_layout()
    target.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(target, dpi=130, bbox_inches="tight")
    plt.close(figure)
    return True


def import_one(run_dir: Path, run_id: str, label: str, role: str, force: bool) -> str:
    summary = load_json(run_dir / "summary.json") or load_json(run_dir / "burn.json")
    parameters = summary.get("parameters", {})
    interventions = summary.get("interventions", [])
    if not interventions and (run_dir / "interventions.jsonl").exists():
        interventions = [
            json.loads(line)
            for line in (run_dir / "interventions.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    make_figure(run_dir, label, interventions, force)

    link_path = RUNS_DIR / run_id
    if not link_path.exists():
        link_path.symlink_to(run_dir.resolve(), target_is_directory=True)

    stamp = (run_dir / "series.csv").stat().st_mtime
    plain = {
        key: value
        for key, value in summary.items()
        if key not in ("parameters", "interventions", "plan", "kernel")
    }
    kernel = summary.get("kernel", {})
    if kernel:
        plain["kernel_path_counts"] = kernel.get("path_counts", {})
        plain["kernel_policy"] = kernel.get("policy")
        plain["kernel_n_tech"] = kernel.get("n_tech")
    plain["role"] = role
    plain["n_interventions"] = len(interventions)
    plain["interventions"] = [
        {k: entry.get(k) for k in ("t", "param", "value", "scope", "phi", "n_selected")}
        for entry in interventions
    ]

    metadata = {
        "run_id": run_id,
        "model_id": MODEL_ID,
        "parameters": parameters,
        "seed": parameters.get("seed", 0),
        "label": label,
        "batch_id": None,
        "status": "completed" if summary.get("status", "ok") == "ok" else summary.get("status"),
        "keep": False,
        "important": False,
        "trashed": False,
        "trashed_at": None,
        "archived": False,
        "created_at": iso(stamp),
        "updated_at": iso(datetime.now(timezone.utc).timestamp()),
        "summary": plain,
        "artifacts": [artifact.to_dict() for artifact in collect_artifacts(run_dir)],
        "message": f"Importé depuis {run_dir.relative_to(JUPYTER_ROOT)}",
        "extra": {"source_path": str(run_dir), "role": role},
    }
    (run_dir / "run.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return run_id


def main(argv: list[str]) -> int:
    apply_style()
    ensure_directories()
    force = "--force-figures" in argv
    imported: list[str] = []
    for group, template, label_template, role in GROUPS:
        root = ROOT / "results" / group
        if not root.exists():
            continue
        if group.endswith("burn"):
            for seed_dir in sorted(root.glob("seed*")):
                run_id = template.format(seed=seed_dir.name)
                imported.append(
                    import_one(seed_dir, run_id,
                               label_template.format(seed=seed_dir.name), role, force)
                )
            continue
        for cell_dir in sorted(root.iterdir()):
            if not cell_dir.is_dir():
                continue
            for seed_dir in sorted(cell_dir.glob("seed*")):
                if not (seed_dir / "series.csv").exists():
                    continue
                run_id = template.format(cell=cell_dir.name, seed=seed_dir.name)
                label = label_template.format(cell=cell_dir.name, seed=seed_dir.name)
                imported.append(import_one(seed_dir, run_id, label, role, force))

    for group, template, label_template, role in NESTED:
        root = ROOT / "results" / group
        if not root.exists():
            continue
        for gamma_dir in sorted(root.iterdir()):
            if not gamma_dir.is_dir():
                continue
            for cell_dir in sorted(gamma_dir.iterdir()):
                if not cell_dir.is_dir():
                    continue
                for seed_dir in sorted(cell_dir.glob("seed*")):
                    if not (seed_dir / "series.csv").exists():
                        continue
                    run_id = template.format(gamma=gamma_dir.name, cell=cell_dir.name,
                                             seed=seed_dir.name)
                    label = label_template.format(gamma=gamma_dir.name, cell=cell_dir.name,
                                                  seed=seed_dir.name)
                    imported.append(import_one(seed_dir, run_id, label, role, force))

    index = ROOT / "results" / "analysis" / "simulation_lab_index.csv"
    index.parent.mkdir(parents=True, exist_ok=True)
    with open(index, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["run_id", "chemin_source"])
        for run_id in imported:
            writer.writerow([run_id, str((RUNS_DIR / run_id).resolve().relative_to(JUPYTER_ROOT))])
    for run_id in imported:
        print(f"  {run_id}")
    print(f"\n{len(imported)} runs enregistrés dans simulation_lab (symlink + run.json).")
    print(f"Index écrit dans {index.relative_to(JUPYTER_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
