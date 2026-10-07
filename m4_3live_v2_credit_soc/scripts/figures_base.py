"""Socle commun aux figures des rapports M4.3Live-v2 : style, lecture, écriture.

**Où vont les figures, et pourquoi.** `results/` est ignoré par git
(`m4_3live_v2_credit_soc/.gitignore:2`). Une figure incluse depuis `results/`
ferait échouer la compilation du rapport sur un clone propre, ce qui contredit
la règle d'autonomie du document. Les figures sont donc écrites dans
`report/figures/`, qui est VERSIONNÉ.

**Et la provenance.** Une figure tirée d'une série de campagne de 1,4 Mio non
versionnée n'est pas reproductible depuis le dépôt seul. Toute figure de ce
genre dépose donc la série qu'elle trace — l'agrégat réellement dessiné, pas
la source de 8000 lignes — dans `report/figures/data/`, en CSV, versionné.
C'est le même principe que `make_numbers.py` pour les nombres : aucune donnée
portée à la main, aucune donnée invérifiable.

**Cohérence avec les macros.** `tests/test_figures.py` vérifie que toute
valeur ANNOTÉE sur une figure coïncide avec la macro correspondante de
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
SWEEP = ROOT / "results" / "rotation_sweep"
HETERO = ROOT / "results" / "rotation_hetero"
FIGURES = ROOT / "report" / "figures"
FIGDATA = FIGURES / "data"

#: Premier pas après l'amorçage partagé : toutes les interventions ont lieu
#: à t0 + 1, et toutes les fenêtres de lecture sont comptées depuis là.
T0 = 2000

#: Student à onze degrés de liberté — douze graines appariées.
T_CRITICAL = 2.201

#: Palette. Sobre, lisible en noir et blanc par la valeur, et surtout STABLE :
#: le sens libre est bleu et la règle ancienne rouge sur TOUTES les figures des
#: deux rapports, si bien qu'aucune légende n'est nécessaire pour les
#: reconnaître d'une figure à l'autre.
INK = "#1a1a1a"
GRID = "#d8d8d8"
FREE = "#3b6ea5"
V1 = "#c1442e"
COLORS = {
    "free": FREE,
    "richest_lends": V1,
    "v1": V1,
    "v2": FREE,
    "control": "#6b6b6b",
    "all_A150": "#e08a1e",
    "new_A150": "#c1442e",
    "new_A075": "#2e8b74",
    "new_g060": "#7a4fa3",
    "tech0": "#c1442e",
    "tech1": "#3b6ea5",
    "rho": "#3b6ea5",
    "K0": "#c1442e",
    "sigma": "#2e8b74",
    "lam": "#7a4fa3",
    "delta": "#e08a1e",
    "base": "#6b6b6b",
}
CYCLE = ["#3b6ea5", "#c1442e", "#2e8b74", "#7a4fa3", "#e08a1e", "#8a6d3b", "#8a2f2f"]

#: Noms lisibles. Les identifiants de bras et de colonnes sont des clefs de
#: dossier ou de CSV ; un rapport ne doit pas les afficher tels quels.
LABELS = {
    "free": "sens libre",
    "richest_lends": "règle ancienne",
    "control": "contrôle",
    "all_A150": r"$A \times 1{,}5$ (toutes)",
    "new_A150": r"$A \times 1{,}5$ (nouvelles)",
    "new_A075": r"$A \times 0{,}75$ (nouvelles)",
    "new_g060": r"$\gamma = 0{,}60$ (nouvelles)",
    "prod_tot": "production",
    "pop": "population",
    "K_tot": "capital total",
    "deaths_per_pop": "mortalité",
    "rotation": "rotation du crédit",
    "loan_volume": "volume prêté",
    "interest_paid": "intérêts versés",
    "n_loans": "contrats vivants",
    "defaults": "défauts de liquidité",
    "K_share_creditors": "part du capital aux créancières",
    "corr_marg_net": r"corr(rendement marginal, position nette)",
    "corr_K_net": r"corr(capital, position nette)",
    "tension": "tension",
    "destroyed": "capital détruit",
    "mkt_surplus": "surplus coopératif",
    "rho": r"$\rho$", "K0": r"$K_0$", "sigma": r"$\sigma$",
    "lam": r"$\lambda$", "delta": r"$\delta$", "base": "référence",
}

_MANIFEST: list[dict] = []


def setup() -> None:
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["DejaVu Serif"],
        "font.size": 9,
        "axes.titlesize": 9.5,
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


def read_csv(name) -> list[dict]:
    path = ANALYSIS / name if not Path(name).is_absolute() else Path(name)
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_json(name):
    path = ANALYSIS / name if not Path(name).is_absolute() else Path(name)
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


def series(direction: str, arm: str, seed: int, name: str = "series.csv") -> list[dict]:
    """Une série de campagne, par son adresse dans `results/campaign/arms/`."""
    return read_csv(CAMPAIGN / "arms" / direction / arm / f"seed{seed}" / name)


def column(rows: list[dict], key: str) -> np.ndarray:
    return np.array([number(row, key) for row in rows], dtype=float)


def blocks(values: np.ndarray, size: int) -> np.ndarray:
    """Moyenne par blocs de `size` points. Une part de rondes à contre-sens
    est trop bruitée pas à pas pour qu'on y voie une décroissance ; c'est le
    bloc qui montre la forme."""
    usable = (len(values) // size) * size
    if usable == 0:
        return np.array([])
    return values[:usable].reshape(-1, size).mean(axis=1)


def student(values) -> tuple[float, float, int]:
    """Moyenne, demi-intervalle de Student à 5 %, effectif."""
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
    rapport cite un exposant : mortalité contre rotation, $f_3$ contre Gini,
    rotation contre la forme fermée."""
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
        "pente": float(slope), "pente_se": se, "ordonnee": float(intercept),
        "n": n, "r2": 1.0 - float((residual ** 2).sum()) / ss_tot if ss_tot > 0 else float("nan"),
        "span": float(x[good].max() / x[good].min()) if x[good].min() > 0 else float("nan"),
    }


def gini(values) -> float:
    """Coefficient de Gini, forme triée. `G = E|X-Y| / (2 E[X])`, c'est-à-dire
    exactement la définition employée au §7 du rapport de résultats."""
    v = np.sort(np.asarray([x for x in values if x == x and x > 0], dtype=float))
    n = v.size
    if n == 0 or v.sum() == 0:
        return float("nan")
    index = np.arange(1, n + 1)
    return float((2 * (index * v).sum()) / (n * v.sum()) - (n + 1) / n)


def lorenz(values) -> tuple[np.ndarray, np.ndarray]:
    v = np.sort(np.asarray([x for x in values if x == x and x > 0], dtype=float))
    if v.size == 0:
        return np.array([0.0]), np.array([0.0])
    cumulative = np.concatenate([[0.0], np.cumsum(v) / v.sum()])
    return np.linspace(0.0, 1.0, v.size + 1), cumulative


def percent(axis, decimals: int = 0) -> None:
    axis.set_major_formatter(FuncFormatter(
        lambda v, _: f"{100 * v:.{decimals}f} %".replace(".", ",")))


def fr(value: float, digits: int = 3, math_mode: bool = False) -> str:
    """Nombre au format français. En contexte mathtext, la virgule DOIT être
    protégée par des accolades : `$0,411$` insère une espace de ponctuation
    après la virgule et donne « 0, 411 »."""
    if value is None or value != value:
        return "---"
    text = f"{value:.{digits}f}"
    return text.replace(".", "{,}" if math_mode else ",")


def french_axis(axis, decimals: int = 2) -> None:
    axis.set_major_formatter(FuncFormatter(
        lambda v, _: f"{v:.{decimals}f}".replace(".", ",")))


def windows(axes, transition=(T0, T0 + 200), residual=(T0 + 1000, T0 + 2000)) -> None:
    """Ombre les deux fenêtres de lecture. Elles reviennent sur toutes les
    figures temporelles : les tracer de la même façon partout évite au lecteur
    de relire une légende à chaque fois."""
    axes.axvspan(*transition, color="#c1442e", alpha=0.09, lw=0)
    axes.axvspan(*residual, color="#3b6ea5", alpha=0.09, lw=0)


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
