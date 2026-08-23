"""Réconciliation des DEUX estimateurs du rapport de branchement sur un run.

Porte du lot A (plan §3.2) : « les deux estimateurs doivent être recalculés
sur les MÊMES runs avant qu'un seul chiffre ne soit publié ». Ce script est
l'outil qui le fait, et il sert tel quel au lot D.

Il lit `series.csv` (estimateur 1, par les racines) et `loss_edges.csv`
(estimateur 2, par la descendance) d'un même répertoire de run, sur une
fenêtre explicite, et écrit le tout en JSON.

LA FENÊTRE N'EST PAS UN DÉTAIL. Un bras branché sur un amorçage hérite de la
série de l'amorçage (`load_snapshot` restaure `series`), mais pas de ses
arêtes de perte, puisque l'amorçage n'est pas instrumenté. Compter les morts
sur 0..T et les arêtes sur t₀..T donnerait un b₂ faux d'un facteur 2. Le
champ `closes` du résultat est là pour que cette erreur soit IMPOSSIBLE à
commettre en silence : il vérifie que le nombre de victimes mortelles vues
dans l'arbre vaut bien `morts − racines` de la série.

    python3 scripts/branching.py RUN_DIR [--t-min 2000] [--t-max 4000] [--out FICHIER]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from m4_4.cascades import reconcile  # noqa: E402
from m4_4.live import read_edges  # noqa: E402


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_edges(run_dir: Path):
    """`loss_edges.npz` (format courant) ou `loss_edges.csv` (format des
    premiers essais du lot A), selon ce qui est là."""
    npz = run_dir / "loss_edges.npz"
    if npz.exists():
        return read_edges(npz)
    csv_path = run_dir / "loss_edges.csv"
    if csv_path.exists():
        return read_csv(csv_path)
    raise SystemExit(
        f"ni {npz.name} ni {csv_path.name} dans {run_dir} : le run a-t-il été "
        "lancé avec record_loss_edges ?"
    )


def measure(run_dir: Path, t_min: float | None, t_max: float | None) -> dict:
    series = read_csv(run_dir / "series.csv")
    payload = reconcile(series, load_edges(run_dir), t_min, t_max)
    return {"run": str(run_dir), "t_min": t_min, "t_max": t_max, **payload}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--t-min", type=float, default=None)
    parser.add_argument("--t-max", type=float, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv[1:])

    payload = measure(args.run_dir, args.t_min, args.t_max)
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    print(text)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    if not payload["closes"]:
        print(
            "ATTENTION : l'arbre causal ne ferme pas sur la série. La fenêtre "
            "demandée déborde probablement la période instrumentée.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
