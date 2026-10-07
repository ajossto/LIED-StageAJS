"""Exécute un plan de campagne M4.2 (cellules → lots Simulation Lab).

Usage :
    run_campaign.py --plan pilotes [--cell-workers 3] [--parallel-cells 2]
                    [--keep] [--only NOM[,NOM...]]

Budget machine : cell_workers × parallel_cells ≤ 6 (8 cœurs, 2 laissés
libres). Reprise : une cellule dont le cell_id figure dans
manifests/cells_index.json avec des runs complets est réutilisée telle
quelle (jamais relancée) ; le manifeste du plan est réécrit après chaque
cellule.
"""

from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lib_lab


def process_cell(plan_name: str, cell: dict, workers: int, keep: bool,
                 index: dict) -> tuple[dict, bool]:
    identifier = lib_lab.cell_id(cell)
    cached = index.get(identifier)
    if cached and lib_lab.runs_completed(cached.get("run_ids", [])):
        return cached, True
    entry = lib_lab.launch_cell(plan_name, cell, workers, keep=keep)
    if not lib_lab.runs_completed(entry["run_ids"]):
        raise RuntimeError(
            f"{cell['name']}: lot terminé mais runs incomplets {entry['run_ids']}"
        )
    return entry, False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, help="nom du plan (manifests/<plan>.json)")
    parser.add_argument("--cell-workers", type=int, default=3)
    parser.add_argument("--parallel-cells", type=int, default=2)
    parser.add_argument("--keep", action="store_true",
                        help="marque les runs « à conserver » (confirmation)")
    parser.add_argument("--only", default="", help="cellules à exécuter (noms, virgules)")
    args = parser.parse_args()

    if args.cell_workers * args.parallel_cells > 6:
        parser.error("cell_workers × parallel_cells doit rester ≤ 6")

    plan = lib_lab.load_plan(args.plan)
    selected = [s for s in args.only.split(",") if s]
    cells = [cell for cell in plan["cells"]
             if not selected or cell["name"] in selected]
    if not cells:
        parser.error("aucune cellule sélectionnée")

    manifest = lib_lab.load_manifest(args.plan)
    done_names = {entry["cell"] for entry in manifest["cells"]}
    index = lib_lab.load_index()
    started = time.monotonic()
    print(f"plan {args.plan}: {len(cells)} cellules "
          f"({len(done_names & {c['name'] for c in cells})} déjà au manifeste)",
          flush=True)

    pending = [cell for cell in cells if cell["name"] not in done_names]
    with ThreadPoolExecutor(max_workers=max(1, args.parallel_cells)) as pool:
        futures = {
            pool.submit(process_cell, args.plan, cell, args.cell_workers,
                        args.keep, index): cell
            for cell in pending
        }
        for future in as_completed(futures):
            cell = futures[future]
            entry, reused = future.result()
            manifest["cells"].append(entry)
            index[entry["cell_id"]] = entry
            lib_lab.save_manifest(args.plan, manifest)
            lib_lab.save_index(index)
            status = "réutilisée" if reused else f"{entry['duration_seconds']:.0f}s"
            print(f"  {cell['name']}: {len(entry['run_ids'])} runs — {status}",
                  flush=True)

    print(f"plan {args.plan} terminé en {time.monotonic() - started:.0f}s "
          f"({len(manifest['cells'])} cellules au manifeste)", flush=True)


if __name__ == "__main__":
    main()
