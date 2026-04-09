from __future__ import annotations

import argparse
import json

from simulation_lab.models.discovery import ModelRegistry
from simulation_lab.runs.executor import execute_batch, execute_single, generate_seeds
from simulation_lab.runs.storage import RunStorage
from simulation_lab.settings import DEFAULT_HOST, DEFAULT_PORT, ensure_directories
from simulation_lab.web.app import run_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pilotage local de simulations.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-models", help="Lister les modèles détectés.")
    subparsers.add_parser("list-runs", help="Lister les simulations enregistrées.")

    run_parser = subparsers.add_parser("run", help="Lancer une simulation unique.")
    run_parser.add_argument("--model", required=True, dest="model_id")
    run_parser.add_argument("--params", default="{}", help="JSON des paramètres")
    run_parser.add_argument("--seed", type=int, required=True)
    run_parser.add_argument("--label", default="")

    batch_parser = subparsers.add_parser("batch", help="Lancer un batch parallèle.")
    batch_parser.add_argument("--model", required=True, dest="model_id")
    batch_parser.add_argument("--params", default="{}", help="JSON des paramètres")
    batch_parser.add_argument("--runs", type=int, required=True)
    batch_parser.add_argument("--workers", type=int, required=True)
    batch_parser.add_argument("--base-seed", type=int, default=1000)
    batch_parser.add_argument("--label", default="")

    keep_parser = subparsers.add_parser("keep", help="Marquer ou démarquer une simulation.")
    keep_parser.add_argument("--run-id", required=True)
    keep_parser.add_argument("--value", choices=["true", "false"], default="true")

    delete_parser = subparsers.add_parser("delete", help="Supprimer une simulation.")
    delete_parser.add_argument("--run-id", required=True)

    gui_parser = subparsers.add_parser("gui", help="Lancer l'interface web locale.")
    gui_parser.add_argument("--host", default=DEFAULT_HOST)
    gui_parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    gui_parser.add_argument("--open-browser", action="store_true")

    return parser


def main() -> None:
    ensure_directories()
    parser = build_parser()
    args = parser.parse_args()
    registry = ModelRegistry()
    storage = RunStorage()

    if args.command == "list-models":
        payload = [model.describe() for model in registry.list_models()]
    elif args.command == "list-runs":
        payload = storage.list_runs()
    elif args.command == "run":
        payload = execute_single(
            storage,
            registry,
            model_id=args.model_id,
            parameters=json.loads(args.params),
            seed=args.seed,
            label=args.label,
        )
    elif args.command == "batch":
        payload = execute_batch(
            storage,
            registry,
            model_id=args.model_id,
            parameters=json.loads(args.params),
            seeds=generate_seeds(args.runs, base_seed=args.base_seed),
            label=args.label,
            max_workers=args.workers,
        )
    elif args.command == "keep":
        payload = storage.set_keep(args.run_id, args.value == "true")
    elif args.command == "delete":
        storage.delete_run(args.run_id)
        payload = {"deleted": args.run_id}
    elif args.command == "gui":
        run_server(host=args.host, port=args.port, open_browser=args.open_browser)
        return
    else:
        raise ValueError(f"Commande inconnue: {args.command}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
