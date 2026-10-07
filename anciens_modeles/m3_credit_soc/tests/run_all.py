"""Exécute toute la suite de tests M3 et affiche le décompte final.
Usage : /home/anatole/jupyter/.venv/bin/python3 tests/run_all.py"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE))

import test_core
import test_contracts_market
import test_bankruptcy
import test_invariants
import test_analysis

MODULES = (test_core, test_contracts_market, test_bankruptcy,
           test_invariants, test_analysis)


def main():
    count = 0
    for mod in MODULES:
        print(f"--- {mod.__name__} ---")
        names = sorted(n for n in dir(mod) if n.startswith("test_"))
        for name in names:
            getattr(mod, name)()
            print(f"OK {name}")
            count += 1
    print(f"\n{count} tests OK")
    return count


if __name__ == "__main__":
    main()
