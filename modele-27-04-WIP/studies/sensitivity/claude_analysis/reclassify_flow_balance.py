"""
Reclassification des run.json existants dans simulation_lab_data/runs/.

Ajoute les champs flow_balanced, stationary et failure_lambda_ratio au summary
de chaque run issu de l'étude de sensibilité, en les calculant à partir des
champs already présents dans record.json (ou dans run.json directement).

Critère : flow_balanced = abs(measure_failure_lambda_ratio - 1.0) < 0.15
          stationary = bounded_tail AND flow_balanced

Usage :
  python reclassify_flow_balance.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
JUPYTER_DIR = HERE.parents[2]
RUNS_DIR = JUPYTER_DIR / "simulation_lab_data" / "runs"

FLOW_THRESHOLD = 0.15


def compute_flow_fields(summary: dict, record: dict | None) -> dict:
    """Retourne les champs à ajouter/mettre à jour dans summary."""
    # failure_lambda_ratio peut être dans le summary (si déjà exporté) ou dans record
    ratio = summary.get("failure_lambda_ratio")
    if ratio is None and record:
        ratio = record.get("measure_failure_lambda_ratio")
    if ratio is None:
        return {}

    flow_balanced = abs(ratio - 1.0) < FLOW_THRESHOLD
    bounded_tail = bool(summary.get("bounded_tail", False))
    stationary = bounded_tail and flow_balanced

    return {
        "failure_lambda_ratio": ratio,
        "flow_balanced": flow_balanced,
        "stationary": stationary,
    }


def process_run_dir(run_dir: Path, dry_run: bool) -> str:
    run_json_path = run_dir / "run.json"
    record_json_path = run_dir / "record.json"

    if not run_json_path.exists():
        return "skip_no_run_json"

    run_data = json.loads(run_json_path.read_text(encoding="utf-8"))
    if run_data.get("model_id") != "etude_sensibilite_27_04_wip":
        return "skip_not_study"

    record = None
    if record_json_path.exists():
        try:
            record = json.loads(record_json_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    summary = run_data.get("summary", {})
    updates = compute_flow_fields(summary, record)
    if not updates:
        return "skip_no_ratio"

    # Check if already up-to-date
    already = all(summary.get(k) == v for k, v in updates.items())
    if already:
        return "up_to_date"

    if not dry_run:
        summary.update(updates)
        run_data["summary"] = summary
        run_json_path.write_text(json.dumps(run_data, indent=2, ensure_ascii=False), encoding="utf-8")

    return f"updated flow_balanced={updates['flow_balanced']} stationary={updates['stationary']}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    counts: dict[str, int] = {}
    for run_dir in sorted(RUNS_DIR.iterdir()):
        if not run_dir.is_dir():
            continue
        status = process_run_dir(run_dir, args.dry_run)
        counts[status] = counts.get(status, 0) + 1
        if status.startswith("updated"):
            print(f"  {run_dir.name}: {status}")

    print(f"\nRésumé{'  [DRY-RUN]' if args.dry_run else ''}:")
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
