"""
Analyse des runs existants dans simulation_lab_data.

Objectif : reperer les simulations qui ont atteint le regime permanent au sens
empirique demande par l'utilisateur : premiere descente consequente simultanee
du nombre d'entites vivantes et de l'actif total apres une phase de croissance.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

LAB_DATA = Path("/home/anatole/jupyter/simulation_lab_data")
HERE = Path(__file__).resolve().parent
RESULTS_DIR = HERE / "results"
FIGURES_DIR = HERE / "report" / "figures"
RESULTS_DIR.mkdir(exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def read_run_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def artifact_path(run_dir: Path, run: dict, filename: str) -> Path | None:
    for artifact in run.get("artifacts", []):
        rel = artifact.get("relative_path", "")
        if rel.endswith(filename):
            p = run_dir / rel
            if p.exists():
                return p
    candidates = list(run_dir.glob(f"**/{filename}"))
    return candidates[0] if candidates else None


def read_stats(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(row for row in f if not row.startswith("#"))
        rows = []
        for row in reader:
            rows.append({
                "step": int(float(row["step"])),
                "n_alive": float(row.get("n_entities_alive") or row.get("nb_entites") or 0.0),
                "actif": float(row.get("actif_total_systeme") or row.get("actif_total") or 0.0),
                "n_loans": float(row.get("n_prets_actifs") or row.get("nb_prets") or 0.0),
                "volume_prets": float(row.get("volume_prets_actifs") or row.get("volume_prets") or 0.0),
                "failures": float(row.get("n_failures") or row.get("nb_faillites") or 0.0),
            })
    return rows


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def std(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


def detect_visual_regime(rows: list[dict]) -> dict:
    """
    Detection volontairement proche du critere visuel :
    - ignorer le tout debut ;
    - trouver le pic de n_alive ;
    - chercher une chute de n_alive < 75 % du pic ;
    - exiger que l'actif ait aussi baisse d'au moins 15 % depuis son pic passe.
    """
    n = len(rows)
    if n < 50:
        return {"regime": False, "t_drop": None, "reason": "too_short"}

    skip = min(50, max(5, n // 20))
    alive = [r["n_alive"] for r in rows]
    actif = [r["actif"] for r in rows]
    loans = [r["n_loans"] for r in rows]
    failures = [r["failures"] for r in rows]

    peak_alive = max(alive[skip:])
    t_peak_alive = alive.index(peak_alive)
    peak_actif_so_far = actif[t_peak_alive]
    t_drop = None
    for t in range(t_peak_alive + 1, n):
        peak_actif_so_far = max(peak_actif_so_far, actif[t])
        alive_drop = alive[t] <= 0.75 * peak_alive
        actif_drop = actif[t] <= 0.85 * peak_actif_so_far
        if alive_drop and actif_drop:
            t_drop = t
            break

    if t_drop is None:
        tail0 = int(0.7 * n)
        return {
            "regime": False,
            "t_drop": None,
            "t_measure": tail0,
            "reason": "no_joint_drop",
            "peak_alive": peak_alive,
            "t_peak_alive": t_peak_alive,
            "final_alive": alive[-1],
            "final_actif": actif[-1],
        }

    t_measure = min(n - 1, t_drop + 100)
    window = rows[t_measure:]
    alive_w = [r["n_alive"] for r in window]
    actif_w = [r["actif"] for r in window]
    loans_w = [r["n_loans"] for r in window]
    volume_w = [r["volume_prets"] for r in window]
    failures_w = [r["failures"] for r in window]
    loan_density = [l / a for l, a in zip(loans_w, alive_w) if a > 0]
    financial_density = [v / a for v, a in zip(volume_w, actif_w) if a > 0]

    return {
        "regime": True,
        "t_drop": t_drop,
        "t_measure": t_measure,
        "reason": "joint_drop",
        "peak_alive": peak_alive,
        "t_peak_alive": t_peak_alive,
        "final_alive": alive[-1],
        "final_actif": actif[-1],
        "n_alive_mean": mean(alive_w),
        "n_alive_cv": std(alive_w) / mean(alive_w) if mean(alive_w) > 0 else 0.0,
        "actif_mean": mean(actif_w),
        "actif_cv": std(actif_w) / mean(actif_w) if mean(actif_w) > 0 else 0.0,
        "loan_density_mean": mean(loan_density),
        "densite_fin_mean": mean(financial_density),
        "failure_rate_mean": mean(failures_w),
    }


def collect_lab_runs() -> list[dict]:
    records = []
    for area in ("runs", "trash"):
        for run_json in sorted((LAB_DATA / area).glob("*/run.json")):
            run_dir = run_json.parent
            run = read_run_json(run_json)
            if run.get("status") != "completed":
                continue
            if run.get("model_id") not in {"modele_27_04_wip", "modele_sans_banque_wip"}:
                continue
            stats_path = artifact_path(run_dir, run, "stats_legeres.csv")
            if stats_path is None:
                continue
            rows = read_stats(stats_path)
            diag = detect_visual_regime(rows)
            p = run.get("parameters", {})
            records.append({
                "area": area,
                "run_id": run.get("run_id"),
                "model_id": run.get("model_id"),
                "label": run.get("label", ""),
                "stats_path": str(stats_path),
                "duree_simulation": p.get("duree_simulation"),
                "seed": p.get("seed"),
                "alpha_min": p.get("alpha_min"),
                "alpha_max": p.get("alpha_max"),
                "alpha_sigma_brownien": p.get("alpha_sigma_brownien"),
                "theta": p.get("theta"),
                "lambda_creation": p.get("lambda_creation"),
                "n_candidats_pool": p.get("n_candidats_pool"),
                "epsilon": p.get("epsilon"),
                "max_credit_iterations": p.get("max_credit_iterations"),
                "taux_depreciation_liquide": p.get("taux_depreciation_liquide"),
                "taux_depreciation_endo": p.get("taux_depreciation_endo"),
                "taux_depreciation_exo": p.get("taux_depreciation_exo"),
                "final_alive_summary": run.get("summary", {}).get("entities_alive_final"),
                "failures_total_summary": run.get("summary", {}).get("failures_total"),
                "loans_active_final_summary": run.get("summary", {}).get("loans_active_final"),
                **diag,
            })
    return records


def write_outputs(records: list[dict]) -> None:
    json_path = RESULTS_DIR / "simulation_lab_regime_scan.json"
    json_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

    csv_path = RESULTS_DIR / "simulation_lab_regime_scan.csv"
    fieldnames = sorted({k for rec in records for k in rec.keys()})
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(records)


def plot_regime_examples(records: list[dict]) -> None:
    selected = [r for r in records if r["model_id"] == "modele_27_04_wip"]
    selected = sorted(selected, key=lambda r: (not r["regime"], r["run_id"]))[:8]
    if not selected:
        return
    fig, axes = plt.subplots(len(selected), 2, figsize=(12, 2.5 * len(selected)), squeeze=False)
    for row_axes, rec in zip(axes, selected):
        rows = read_stats(Path(rec["stats_path"]))
        t = [r["step"] for r in rows]
        alive = [r["n_alive"] for r in rows]
        actif = [r["actif"] for r in rows]
        title = f"{rec['run_id']} | k={rec['n_candidats_pool']} eps={rec['epsilon']} | {rec['reason']}"
        row_axes[0].plot(t, alive, linewidth=1.1)
        row_axes[0].set_title(title, fontsize=9)
        row_axes[0].set_ylabel("n_alive")
        row_axes[1].plot(t, actif, linewidth=1.1)
        row_axes[1].set_ylabel("actif")
        for ax in row_axes:
            if rec.get("t_drop") is not None:
                ax.axvline(rec["t_drop"], color="tab:red", linestyle="--", linewidth=0.8)
            ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "simulation_lab_regime_examples.pdf", bbox_inches="tight", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    rows = collect_lab_runs()
    write_outputs(rows)
    plot_regime_examples(rows)
    print(f"{len(rows)} runs completes analyses")
    for r in rows:
        flag = "REGIME" if r["regime"] else "NO_REGIME"
        print(
            f"{flag:9s} {r['run_id']} {r['model_id']} label={r['label']!r} "
            f"steps={r['duree_simulation']} seed={r['seed']} k={r['n_candidats_pool']} "
            f"eps={r['epsilon']} t_drop={r.get('t_drop')} final_alive={r.get('final_alive')}"
        )
