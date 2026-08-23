"""Lance toute la suite et RAPPORTE les échecs.

La convention du dépôt est « assertions Python simples, pas de pytest » : un
test est un fichier qui s'exécute et lève si quelque chose ne va pas. Le
piège, rencontré au lot A, est la boucle shell habituelle

    for t in tests/test_*.py; do python3 "$t" | tail -8; echo "rc=$?"; done

où `$?` est le code de `tail`, jamais celui du test : la suite paraît verte
alors qu'un fichier a levé. Ce script exécute chaque fichier, garde son code
de sortie, et sort en erreur si un seul a échoué.

    python3 scripts/run_tests.py [--full] [--only motif]

`--full` passe `--full` à `test_parity_m4_3.py` (8000 pas, ~17 min).
Sortie : `results/analysis/suite.log`, et le détail sur la sortie standard.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON = "/home/anatole/jupyter/.venv/bin/python3"
LOG = ROOT / "results" / "analysis" / "suite.log"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true",
                        help="parité complète sur 8000 pas au lieu de 500")
    parser.add_argument("--only", default="", help="ne garder que les tests dont le nom contient ce motif")
    args = parser.parse_args(argv[1:])

    tests = sorted((ROOT / "tests").glob("test_*.py"))
    if args.only:
        tests = [path for path in tests if args.only in path.name]
    LOG.parent.mkdir(parents=True, exist_ok=True)

    results = []
    with open(LOG, "w", encoding="utf-8") as log:
        for path in tests:
            command = [PYTHON, str(path)]
            if args.full and path.name == "test_parity_m4_3.py":
                command.append("--full")
            started = time.time()
            print(f"===== {path.name} =====", flush=True)
            log.write(f"===== {path.name} =====\n")
            completed = subprocess.run(command, capture_output=True, text=True)
            elapsed = time.time() - started
            output = completed.stdout + (
                "\n--- stderr ---\n" + completed.stderr if completed.returncode else ""
            )
            print(output.rstrip(), flush=True)
            log.write(output)
            verdict = "OK" if completed.returncode == 0 else "ÉCHEC"
            line = f"# {path.name} : {verdict} (code {completed.returncode}, {elapsed:.0f} s)"
            print(line, flush=True)
            log.write(line + "\n\n")
            results.append((path.name, completed.returncode, elapsed))

        failed = [name for name, code, _ in results if code != 0]
        summary = (
            f"# SUITE : {len(results) - len(failed)}/{len(results)} verts, "
            f"{sum(seconds for _, _, seconds in results):.0f} s au total"
        )
        if failed:
            summary += " — ÉCHECS : " + ", ".join(failed)
        print(summary, flush=True)
        log.write(summary + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
