"""Runner sans dépendance : exécute toutes les fonctions ``test_*``."""
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))


if __name__ == "__main__":
    count = 0
    for module_name in ("test_engine", "test_analysis"):
        module = importlib.import_module(module_name)
        for name in sorted(n for n in dir(module) if n.startswith("test_")):
            getattr(module, name)()
            count += 1
            print(f"OK {module_name}.{name}")
    print(f"{count} tests OK")
