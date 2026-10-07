"""Runner de tests stdlib (pytest absent du venv). Usage :
    /home/anatole/jupyter/.venv/bin/python3 tests/run_all.py
Découvre les fonctions test_* des fichiers test_*.py et les exécute.
Compatible pytest si celui-ci est installé un jour (`pytest tests/`).
"""
import importlib.util
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))


def main():
    n_ok, n_fail = 0, 0
    failures = []
    for path in sorted(HERE.glob("test_*.py")):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for name in sorted(dir(mod)):
            if not name.startswith("test_"):
                continue
            fn = getattr(mod, name)
            if not callable(fn):
                continue
            try:
                fn()
                n_ok += 1
                print(f"PASS {path.stem}::{name}")
            except Exception:
                n_fail += 1
                failures.append((f"{path.stem}::{name}", traceback.format_exc()))
                print(f"FAIL {path.stem}::{name}")
    print(f"\n{n_ok} passed, {n_fail} failed")
    for name, tb in failures:
        print(f"\n=== {name} ===\n{tb}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
