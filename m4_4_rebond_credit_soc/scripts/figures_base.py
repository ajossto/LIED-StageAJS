"""Socle commun aux figures des rapports M4.4 : style, lecture, écriture.

**Où vont les figures, et pourquoi.** `results/` est ignoré par git (voir
`.gitignore`). Une figure incluse depuis `results/` ferait échouer la
compilation du rapport sur un clone propre, ce qui contredit la règle
d'autonomie du document. Les figures sont donc écrites dans
`report/figures/`, qui est VERSIONNÉ.

**Et la provenance.** Une figure tirée d'un `panels.npz` de 13 Mio non
versionné n'est pas reproductible depuis le dépôt seul. Toute figure de ce
genre dépose donc la série qu'elle trace dans `report/figures/data/`, en CSV,
versionné : c'est le même principe que `make_numbers.py` pour les nombres —
aucune donnée portée à la main, aucune donnée invérifiable.

**Cohérence avec les macros.** `tests/test_figures.py` vérifie que toute
valeur annotée sur une figure coïncide avec la macro correspondante de
`report/numbers.tex`. Une figure qui dérive de son texte est le défaut
silencieux que ce programme s'interdit.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # noqa: E402 — aucun affichage : le script tourne sans écran
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ANALYSIS = ROOT / "results" / "analysis"
CAMPAIGN = ROOT / "results" / "campaign"
FIGURES = ROOT / "report" / "figures"
FIGDATA = FIGURES / "data"

#: Student à onze degrés de liberté — douze graines appariées.
T_CRITICAL = 2.201

#: Palette. Sobre, lisible en noir et blanc par la valeur, et stable d'une
#: figure à l'autre : le même bras porte la même couleur partout.
INK = "#1a1a1a"
GRID = "#d8d8d8"
COLORS = {
    "control": "#3b6ea5",
    "all_A150": "#c1442e",
    "all_A150_K0comp": "#e08a1e",
    "new_A150": "#7a4fa3",
    "new_A075": "#2e8b74",
    "new_g060": "#8a6d3b",
    "marginal": "#c1442e",
    "p=0": "#2e8b74",
    "p=0.25": "#4f9e7f",
    "p=0.5": "#3b6ea5",
    "p=0.75": "#7a4fa3",
    "p=1": "#8a2f2f",
}
CYCLE = ["#3b6ea5", "#c1442e", "#2e8b74", "#7a4fa3", "#e08a1e", "#8a6d3b", "#8a2f2f"]

#: Noms lisibles. Les identifiants de bras sont des clefs de dossier ; un
#: rapport ne doit pas les afficher tels quels.
LABELS = {
    "control": "contrôle",
    "all_A150": r"$A \times 1{,}5$ (toutes)",
    "all_A150_K0comp": r"$A \times 1{,}5$, $K_0$ compensé",
    "new_A150": r"$A \times 1{,}5$ (nouvelles)",
    "new_A075": r"$A \times 0{,}75$ (nouvelles)",
    "new_g060": r"$\gamma = 0{,}60$ (nouvelles)",
    "marginal": "règle historique",
    "prod": "production",
    "income": "revenu",
    "income_net": "revenu net",
    "int_in": "revenu d'intérêt",
    "nw": "valeur nette",
    "K": "capital",
}

_MANIFEST: list[dict] = []


def setup() -> None:
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["DejaVu Serif"],
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "axes.edgecolor": INK,
        "axes.labelcolor": INK,
        "axes.linewidth": 0.7,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.5,
        "xtick.color": INK,
        "ytick.color": INK,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "legend.frameon": False,
        "figure.dpi": 140,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
        "pdf.fonttype": 42,
    })


def label(name: str) -> str:
    return LABELS.get(name, name.replace("_", r"\_") if "\\" not in name else name)


def colour(name: str, index: int = 0) -> str:
    return COLORS.get(name, CYCLE[index % len(CYCLE)])


def read_csv(name: str) -> list[dict]:
    path = ANALYSIS / name if not Path(name).is_absolute() else Path(name)
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_json(name: str):
    path = ANALYSIS / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def number(row: dict, key: str, default: float = float("nan")) -> float:
    """Lecture tolérante. Une cellule VIDE est légitime dans ce dépôt :
    `write_series` prend l'UNION des colonnes entre versions du moteur, si
    bien qu'un bras branché sur un amorçage plus ancien a des colonnes
    absentes. Tout lecteur doit rendre NaN plutôt que lever."""
    raw = row.get(key, "")
    if raw is None or raw == "" or raw == "nan":
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def student(values) -> tuple[float, float, int]:
    clean = [v for v in values if v == v and math.isfinite(v)]
    n = len(clean)
    if n == 0:
        return float("nan"), float("nan"), 0
    mean = sum(clean) / n
    if n < 2:
        return mean, float("nan"), n
    variance = sum((v - mean) ** 2 for v in clean) / (n - 1)
    return mean, T_CRITICAL * math.sqrt(variance / n), n


def loglog_fit(x, y) -> dict:
    """Régression en log-log, avec l'erreur de la pente. Sert partout où le
    rapport cite un exposant : mortalité contre rotation, taille d'avalanche,
    exposant contre intensité de marché."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    good = np.isfinite(x) & np.isfinite(y) & (x > 0) & (y > 0)
    if good.sum() < 3:
        return {}
    lx, ly = np.log(x[good]), np.log(y[good])
    slope, intercept = np.polyfit(lx, ly, 1)
    predicted = slope * lx + intercept
    residual = ly - predicted
    n = int(good.sum())
    sigma2 = float((residual ** 2).sum() / (n - 2))
    sxx = float(((lx - lx.mean()) ** 2).sum())
    se = math.sqrt(sigma2 / sxx) if sxx > 0 else float("nan")
    ss_tot = float(((ly - ly.mean()) ** 2).sum())
    return {
        "pente": float(slope), "pente_se": se, "pente_ci95": T_CRITICAL * se,
        "ordonnee": float(intercept), "n": n,
        "r2": 1.0 - float((residual ** 2).sum()) / ss_tot if ss_tot > 0 else float("nan"),
    }


def ccdf(values) -> tuple[np.ndarray, np.ndarray]:
    """Fonction de survie empirique, points distincts seulement.

    `P(X ≥ x)` et non `P(X > x)` : sur des tailles d'avalanche entières, la
    seconde convention décale la queue d'un cran et fausse l'exposant lu à
    l'œil sur la figure.
    """
    values = np.asarray(values, dtype=float)
    values = np.sort(values[np.isfinite(values) & (values > 0)])
    if values.size == 0:
        return np.array([]), np.array([])
    unique, counts = np.unique(values, return_counts=True)
    survival = 1.0 - (np.cumsum(counts) - counts) / values.size
    return unique, survival


def percent(axis, decimals: int = 0) -> None:
    axis.set_major_formatter(FuncFormatter(
        lambda v, _: f"{100 * v:.{decimals}f} %".replace(".", ",")))


def fr(value: float, digits: int = 3, math: bool = False) -> str:
    """Nombre au format français. En contexte mathtext, la virgule DOIT être
    protégée par des accolades : `$0,411$` insère une espace de ponctuation
    après la virgule et donne « 0, 411 »."""
    if value != value:
        return "---"
    text = f"{value:.{digits}f}"
    return text.replace(".", "{,}" if math else ",")


def french_axis(axis, decimals: int = 2) -> None:
    axis.set_major_formatter(FuncFormatter(
        lambda v, _: f"{v:.{decimals}f}".replace(".", ",")))


def dump(name: str, header: list[str], rows: list[list]) -> Path:
    """Dépose la série tracée, pour les figures dont la source n'est pas
    versionnée. Voir la docstring du module."""
    FIGDATA.mkdir(parents=True, exist_ok=True)
    path = FIGDATA / f"{name}.csv"
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def save(figure, name: str, caption: str = "", values: dict | None = None) -> Path:
    """Écrit la figure et enregistre ce qu'elle affirme.

    `values` porte les grandeurs ANNOTÉES sur la figure. Elles sont écrites
    dans le manifeste et confrontées aux macros de `numbers.tex` par
    `tests/test_figures.py` : c'est ce qui empêche une figure de dériver
    silencieusement du texte qu'elle illustre.
    """
    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / f"{name}.pdf"
    figure.savefig(path)
    plt.close(figure)
    _MANIFEST.append({"nom": name, "legende": caption, "valeurs": values or {}})
    print(f"  {name}.pdf")
    return path


def write_manifest() -> Path:
    """Écrit le manifeste en FUSIONNANT avec l'existant.

    Un `--only` ne produit qu'une figure ; écraser le manifeste avec cette
    seule entrée le rendrait partiel, et `tests/test_figures.py` — qui s'en
    sert pour confronter les figures aux macros — signalerait absentes des
    figures parfaitement présentes. Les entrées régénérées remplacent les
    anciennes, les autres sont conservées.
    """
    path = FIGURES / "manifest.json"
    merged: dict[str, dict] = {}
    if path.exists():
        for entry in json.loads(path.read_text(encoding="utf-8")):
            merged[entry["nom"]] = entry
    for entry in _MANIFEST:
        merged[entry["nom"]] = entry
    # Les figures dont le PDF a disparu n'ont plus à figurer au manifeste.
    ordered = [merged[name] for name in sorted(merged)
               if (FIGURES / f"{name}.pdf").exists()]
    path.write_text(json.dumps(ordered, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def manifest() -> list[dict]:
    return _MANIFEST
