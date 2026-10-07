"""Extrait les métriques de tous les runs des manifestes de campagne M4.2.

Pour chaque run référencé par un manifeste (manifests/*.manifest.json),
calcule lib_metrics.compute_run_metrics (fenêtres T/8, T/4, T/2, fits
d'avalanches, stationnarité, intégrité) et écrit
results/metrics/<run_id>.json. Idempotent : un run déjà extrait avec le
même condensat moteur est sauté (--force pour recalculer).

Usage : extract_metrics.py [--plan NOM[,NOM...]] [--force] [--bootstrap]

--bootstrap ajoute les IC bootstrap (τ, s_c, s_min) sur la fenêtre par
défaut. Il est OBLIGATOIRE pour l'extraction des runs confirmatoires
(protocole §critères, condition 7 : incertitude d'ajustement de la
métrique primaire) ; analyze_confirm.py refuse un run confirmatoire sans
bloc bootstrap. Facultatif (coûteux) pour l'exploration.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lib_lab
import lib_metrics

RESULTS = Path(__file__).resolve().parents[1] / "results" / "metrics"


def extract_run(run_dir: Path, force: bool, bootstrap: bool) -> str:
    run_id = run_dir.name
    output = RESULTS / f"{run_id}.json"
    engine = "lab:" + json.loads(
        (run_dir / "config.json").read_text()
    ).get("model_version", "?")
    if output.exists() and not force:
        cached = json.loads(output.read_text())
        if cached.get("engine_hash") == engine and (
            not bootstrap or "bootstrap" in cached
        ):
            return "cache"
    metrics = lib_metrics.compute_run_metrics(run_dir)
    if bootstrap:
        avalanches = lib_metrics.read_avalanches(run_dir)
        T = metrics["parameters"]["T"]
        lo = int(0.25 * T)
        mask = (avalanches["t"] >= lo) & (avalanches["t"] <= metrics["t_final"])
        metrics["bootstrap"] = lib_metrics.bootstrap_avalanche_fits(
            avalanches["size"][mask], n_boot=200, seed=0
        )
    RESULTS.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(lib_metrics._to_jsonable(metrics), indent=1,
                                 ensure_ascii=False))
    return "extrait"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", default="", help="plans (noms, virgules) — défaut : tous")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--bootstrap", action="store_true")
    args = parser.parse_args()

    selected = [s for s in args.plan.split(",") if s]
    manifests = sorted(lib_lab.MANIFESTS.glob("*.manifest.json"))
    counts = {"extrait": 0, "cache": 0}
    for path in manifests:
        manifest = json.loads(path.read_text())
        if selected and manifest["plan"] not in selected:
            continue
        for entry in manifest["cells"]:
            for _, run_dir in lib_lab.run_dirs(entry):
                counts[extract_run(run_dir, args.force, args.bootstrap)] += 1
    print(f"métriques : {counts['extrait']} extraites, {counts['cache']} en cache")


if __name__ == "__main__":
    main()
