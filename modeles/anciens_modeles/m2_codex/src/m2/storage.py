from __future__ import annotations

import csv
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib
import numpy
import scipy

from .config import M2Config
from .simulation import SimulationRun

SNAPSHOT_FIELDS = [
    "step",
    "entity_id",
    "birth_step",
    "age",
    "w",
    "claims",
    "debts",
    "d0",
    "nw",
    "nw_delta",
    "extraction",
    "interest_received",
    "interest_paid",
    "income_gross",
    "income_net",
]


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_run(
    output_dir: str | Path,
    config: M2Config,
    seed: int,
    run: SimulationRun,
    command: str = "",
) -> Path:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    metadata = {
        "schema_version": 1,
        "model": "M2",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "complete",
        "seed": seed,
        "config": config.to_dict(),
        "command": command,
        "environment": {
            "python": platform.python_version(),
            "numpy": numpy.__version__,
            "scipy": scipy.__version__,
            "matplotlib": matplotlib.__version__,
        },
        "summary": {
            "steps": len(run.timeseries),
            "final_population": run.timeseries[-1].population if run.timeseries else 0,
            "failures_total": sum(row.failures for row in run.timeseries),
            "snapshots": sorted(run.snapshots),
        },
    }
    (root / "run.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    timeseries_rows = [row.to_dict() for row in run.timeseries]
    if timeseries_rows:
        _write_csv(root / "timeseries.csv", timeseries_rows, list(timeseries_rows[0]))
    else:
        _write_csv(root / "timeseries.csv", [], [])
    for step, rows in sorted(run.snapshots.items()):
        _write_csv(
            root / "snapshots" / f"snapshot_{step:06d}.csv",
            rows,
            SNAPSHOT_FIELDS,
        )
    if run.events:
        with (root / "events.jsonl").open("w", encoding="utf-8") as handle:
            for event in run.events:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return root


def read_csv_numeric(path: str | Path) -> list[dict[str, int | float | str]]:
    integer_fields = {"step", "entity_id", "birth_step", "age"}
    rows: list[dict[str, int | float | str]] = []
    with Path(path).open(encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            row: dict[str, int | float | str] = {}
            for key, value in raw.items():
                if key == "cascade_waves":
                    row[key] = value
                elif key in integer_fields:
                    row[key] = int(value)
                else:
                    row[key] = float(value)
            rows.append(row)
    return rows


def read_snapshots(root: str | Path) -> dict[int, list[dict[str, int | float | str]]]:
    snapshots: dict[int, list[dict[str, int | float | str]]] = {}
    for path in sorted((Path(root) / "snapshots").glob("snapshot_*.csv")):
        step = int(path.stem.split("_")[-1])
        snapshots[step] = read_csv_numeric(path)
    return snapshots
