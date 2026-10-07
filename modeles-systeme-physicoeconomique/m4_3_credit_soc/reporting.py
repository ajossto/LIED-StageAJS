"""Recettes des 28 figures M4.2/M4.2B/M4.3 (copie adaptée des recettes M4B).

Copié de modeles-systeme-physicoeconomique/m4_2b_credit_soc/reporting.py le
2026-08-09 (PROMPT_M4_3_FINAL.md §8 : réutiliser simulation_lab tel quel).
Vérifié avant la copie par un import réel sur un run M4.3 déjà terminé
(results/pilot/control_geometric/seed0, 8000 pas) : generate_run() produit
22 PNG + figures GIF, 0 erreur, en ~4m20 — le module ne connaît pas le
moteur, ne lit que config.json/series.csv/snapshots/*.npz/avalanches.csv
par nom de champ, donc directement réutilisable sans changement pour le
moteur M4.3 (byte-identique à m4_2b/, cf. JOURNAL.md). individual_series.csv.gz
n'est utilisé que par entity_lives() (vies individuelles) — absent pour
les runs M4.3 en individual_every=0 (même convention que TOUTE la
campagne M4.2B, cf. results/campaign/*/seed*/config.json) : ces figures
sont légitimement absentes pour ces runs-là, pas un défaut d'import.

DIVERGENCE avec l'original M4.2B (2026-08-09, demande utilisateur) :
`temporal_density()` utilisait `np.logspace(..., bins=32)` — un nombre de
bins FIXE et des bornes uniformes en log, pas adaptées à la densité réelle
des données. Sur des champs à queue lourde (K, revenus...), les bins
pauvres en effectif produisaient un bruit de comptage qui dominait le
signal (courbe en dents de scie sur plusieurs ordres de grandeur — visible
sur toutes les figures `*_evolution.gif`/`*_temporal_mean.png` d'avant ce
correctif). Remplacé par les mêmes bornes adaptatives aux quantiles que
`adaptive_hist()` (déjà utilisées par `cascades_rank_size.png`,
factorisées dans `_quantile_edges()`). Vérifié avant/après sur
control_geometric/seed0 (`entity_size_histo_temporal_mean.png`) : la
version corrigée donne une courbe lisse et unimodale là où l'originale
oscillait sur 2-3 ordres de grandeur d'un point à l'autre. **Ce fichier
n'est donc plus une copie strictement identique** à l'original M4.2B —
correctif non reporté sur m4_2b_credit_soc/reporting.py (hors périmètre de
la demande, CLAUDE.md : ne pas modifier un autre modèle sans accord
explicite).

REFONTE DU 2026-09-17 (demande utilisateur, figures destinées à un article) :
- plus aucun titre dessiné ; l'identité de la figure (run, modèle, paramètres,
  burn-in, sources, ajustements) part en métadonnées PNG/SVG et dans
  `figures_metadata.json` du dossier de figures ;
- chaque figure est écrite en PNG *et* en SVG (`svg.fonttype = "none"` : le
  texte reste du texte, donc traduisible sans retoucher le tracé), les
  couches denses étant rastérisées avant l'écriture SVG seulement ;
- tous les textes passent par `LABELS` (+ `LANG`), y compris les légendes
  portant des valeurs calculées, écrites comme gabarits `str.format` dont les
  noms de champ sont ceux des métadonnées ;
- les figures à panneaux multiples sont séparées en figures autonomes
  (cascades, structure d'avalanche, Gini/Lorenz, réseau de prêts) ; les noms
  fusionnés partent dans OBSOLETE_OUTPUTS ;
- les ajustements dPlN de branche descendante sont remplacés par des Pareto
  (`fit_pareto_tail`, convention de scripts/pareto_convention.py) — pour les
  figures de run comme pour la figure de lot (`volume_pareto`).
"""

from __future__ import annotations

import csv
import gzip
import re
import json
import math
import shutil
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib import colors as mcolors
from matplotlib.colors import LogNorm
from mpl_toolkits.axes_grid1 import make_axes_locatable
from scipy import stats
from matplotlib.patches import ConnectionPatch, Rectangle
from scipy.optimize import curve_fit, minimize


COLORS = plt.cm.tab10.colors
REVENUES = (
    ("prod", "Production Π", "revenue_distribution_prod", "#2ca02c"),
    ("int_in", "Intérêts reçus", "revenue_distribution_int_in", "#1f77b4"),
    ("int_out", "Intérêts payés", "revenue_distribution_int_out", "#d62728"),
    ("income", "Revenu total brut", "revenue_distribution_income", "#ff7f0e"),
    ("income_net", "Revenu net positif", "revenue_distribution_income_net", "#9467bd"),
)

# Copie machine-readable de la sélection validée dans l'ODS. Cette liste est
# volontairement explicite : ajouter une figure redevient une décision visible.
SELECTED_FAMILIES = (
    "R01", "R02", "R03", "R05", "R06", "R07", "R08", "R09", "R10",
    "R11", "R12", "R14", "R15", "R17", "R18", "R19", "R20",
    "S06", "S08", "S10", "S11", "L02", "L04", "L12", "L13", "L14",
    "L15", "Y03",
)

OBSOLETE_OUTPUTS = (
    # Figures fusionnées, remplacées par des figures séparées le 2026-09-17.
    "cascades_rank_size.png", "soc_avalanche_structure.png", "gini_evolution.png",
    "gini_lorenz_snapshots.png", "loan_network_final.png",
    "avalanche_sizes.png", "avalanche_sizes_semilog.png",
    "avalanche_sizes_linear.png", "entity_distributions_final.png",
    "entity_distributions_final_semilog.png",
    "entity_distributions_final_linear.png", "entity_size_histos.png",
    "revenue_distributions.png", "soc_revenue_fit.png",
)


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", newline="") as stream:
        rows = []
        for row in csv.DictReader(stream):
            converted = {}
            for key, value in row.items():
                if value in (None, ""):
                    converted[key] = ""
                    continue
                try:
                    converted[key] = float(value)
                except ValueError:
                    converted[key] = value
            rows.append(converted)
        return rows


def iter_csv(path: Path):
    """Même lecture que `read_csv`, mais EN FLUX : les lignes sont rendues une
    à une et jamais accumulées. Indispensable pour `individual_series.csv.gz`,
    qui pèse près d'un gigaoctet compressé quand individual_every=1 à T=8000 :
    le charger en liste de dictionnaires demandait plusieurs gigaoctets et
    dépassait le plafond mémoire des workers (constaté le 2026-09-17 — la
    figure des vies individuelles échouait sur un MemoryError, dont le message
    vide explique le « <lambda>:  » sans texte des figure_errors)."""
    if not path.exists():
        return
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            converted = {}
            for key, value in row.items():
                if value in (None, ""):
                    converted[key] = ""
                    continue
                try:
                    converted[key] = float(value)
                except ValueError:
                    converted[key] = value
            yield converted


def config(folder: Path) -> dict:
    payload = json.loads((folder / "config.json").read_text(encoding="utf-8"))
    return payload.get("parameters", payload)


def snapshots(folder: Path) -> dict[int, dict[str, np.ndarray]]:
    result = {}
    for path in sorted((folder / "snapshots").glob("entities_t*.npz")):
        step = int(path.stem.split("t")[-1])
        with np.load(path) as data:
            result[step] = {key: np.asarray(data[key]) for key in data.files}
    return result


# Le texte SVG reste du vrai texte (et non des tracés) : indispensable pour
# traduire une figure sans la regénérer, et pour l'éditer dans un logiciel
# vectoriel. Demande utilisateur 2026-09-17 (publication d'article).
matplotlib.rcParams["svg.fonttype"] = "none"
# Cadre de légende translucide : là où une légende recouvre des données,
# celles-ci restent lisibles au travers (demande utilisateur 2026-09-17).
matplotlib.rcParams["legend.framealpha"] = 0.6

# TYPOGRAPHIE (demande utilisateur 2026-09-17) : TOUS les textes plus grands et
# de taille quasi uniforme — légendes, étiquettes d'axes, nombres sur les axes.
# Destination : un article, où la figure est réduite à la largeur d'une colonne ;
# un texte de 10 pt dans une figure de 24 cm devient illisible à 8 cm.
# Un seul endroit décide : les `fontsize=` par appel ont été retirés des recettes
# (ils se contredisaient entre eux — 7, 11, 12, 14 et 16 coexistaient). Les rares
# survivants encodent un RÔLE, pas une préférence : les isocourbes « k/x », texte
# de fond volontairement effacé.
BASE_FONT = 16.0
matplotlib.rcParams.update({
    "font.size": BASE_FONT,
    "axes.labelsize": BASE_FONT + 1,
    "axes.titlesize": BASE_FONT + 1,
    "figure.titlesize": BASE_FONT + 2,
    "xtick.labelsize": BASE_FONT - 1,
    "ytick.labelsize": BASE_FONT - 1,
    "legend.fontsize": BASE_FONT - 1,
})

#: Contexte du run en cours d'illustration, injecté dans les métadonnées de
#: CHAQUE fichier produit (et dans figures_metadata.json). Renseigné par
#: `describe_run()` ; les titres ayant été retirés des figures, c'est ici que
#: vit désormais tout ce qui identifie la figure.
RUN_METADATA: dict = {}

#: Toutes les chaînes visibles des figures, en un seul endroit. Traduire une
#: langue = fournir un autre dictionnaire ici, sans toucher aux recettes.
LANG = "fr"
LABELS = {
    "step": "Pas",
    "density": "Densité",
    "entities": "Entités",
    "entities_log": "Entités (log)",
    "count_log": "Effectif (log)",
    "size_ge2": "Taille d'avalanche s ≥ 2",
    "ccdf_size": "P(S ≥ s)",
    "volume": "Volume d'avalanche (pertes de créances, J)",
    "capital": "Capital K (J)",
    "new_credit": "Nouveau crédit (J/pas)",
    "population": "Population",
    "debt_ratio": "ΣDettes / ΣCapital (aux instantanés)",
    "gini": "Gini",
    "cumulative_share": "Part cumulée",
    "cumulative_entities": "Part cumulée des entités",
    "seed": "graine",
    # Gabarits des légendes qui portent des valeurs calculées. Ils vivent ici
    # comme le reste du vocabulaire : une traduction remplace le dictionnaire,
    # sans toucher aux recettes (demande utilisateur 2026-09-17). Les valeurs
    # elles-mêmes sont dans les métadonnées de chaque figure, sous les mêmes
    # noms de champ que les accolades ci-dessous.
    # SIMPLIFIÉS le 2026-09-17 (demande utilisateur) : la légende intra-figure
    # ne porte plus que l'identité de la courbe ; α, R², τ, plages et effectifs
    # vivent dans les métadonnées, d'où la légende LaTeX de l'article les
    # reprendra. Les gabarits gardent leurs accolades là où une valeur reste
    # indispensable à la lecture immédiate (la graine, qui distingue deux
    # courbes de même nature sur une même figure).
    # Les PARAMÈTRES AJUSTÉS restent dans la légende (demande utilisateur
    # 2026-09-17) : exposants, temps caractéristique, R² — tout ce sans quoi la
    # figure ne se suffirait plus à elle-même. Seule la comptabilité part en
    # métadonnées : effectifs, bornes de plage, distance KS, constantes A et B.
    "fit_pareto": "Pareto : α={alpha:.2f}±{stderr:.2f}",
    "fit_tail": "queue ∝ x^−α : α={alpha:.2f}±{stderr:.2f}, R²={r2:.3f}",
    "fit_truncated": "s^−α e^(−s/s_c) : α={alpha:.2f}, s_c={cutoff:.1f}",
    "fit_relaxation": "A·e^(−t/τ)+B : τ={tau:.0f}±{tau_stderr:.0f} pas, R²={r2:.3f}",
    "fit_relaxation_extrapolated": "prolongement hors ajustement",
    "fit_lognormal": "log-normale : μ={mu:.2f}, σ={sigma:.2f}, R²={r2:.3f}",
    "fit_ols": "régression linéaire : pente={slope:.2f}, R²={r2:.3f}",
    "temporal_mean": "moyenne temporelle",
    "sample_seed": "{seed_label} {seed}",
    "renewal_measured": "mesure retenue",
    "renewal_excluded": "mesure écartée",
    "renewal_tau": "τ",
    "life_production": "Production",
    "life_interest_in": "Intérêts reçus",
    "life_interest_out": "Intérêts payés",
    "life_erosion": "Érosion δ·K (δ={delta:g})",
    "life_net_flow": "Flux net",
    "lorenz_equality": "égalité parfaite",
    "diagonal_equal_power": "y = x (puissance prêtée = puissance empruntée)",
    # Les pas des instantanés ne sont plus écrits dans la légende (demande
    # utilisateur 2026-09-17) : ils allongeaient l'entrée au point de déformer
    # la figure, et vivent désormais dans les métadonnées (champs
    # `intermediate_steps`, `first_step`, `last_step`, `final_step`).
    "lorenz_intermediate": "{count} instantanés intermédiaires",
    "lorenz_final": "{seed_label} {seed}, état final t={step} : G={gini:.3f}",
}


def describe_run(folder: Path, name: str = "", **extra) -> dict:
    """Métadonnées communes : ce que portait le titre est désormais ici."""
    folder = Path(folder)
    parameters = config(folder)
    total_steps = int(parameters.get("T", 0))
    RUN_METADATA.clear()
    RUN_METADATA.update({
        "run": name or folder.name,
        "run_path": str(folder),
        "model": "m4_3_credit_soc",
        "engine_version": json.loads((folder / "config.json").read_text(encoding="utf-8")).get("model_version", ""),
        "parameters": parameters,
        "steps_total": total_steps,
        "burn_in_steps": total_steps // 4,
        "language": LANG,
        **extra,
    })
    return RUN_METADATA


#: Retrait du DOCTYPE/DTD en tête des SVG (cf. save()).
_STRIP_DOCTYPE = re.compile(r"<!DOCTYPE[^>]*(?:\[[^\]]*\])?>\s*", re.IGNORECASE)


def _rasterize_dense_artists(fig, path_limit=400, point_limit=5000):
    """Avant l'export SVG : passe en raster les seuls tracés massifs (nuages
    hexbin, semis de points, aplats de séries longues). Le texte, les axes et
    les légendes restent vectoriels — donc la figure reste traduisible et
    éditable, sans peser des dizaines de mégaoctets."""
    from matplotlib.collections import Collection
    from matplotlib.lines import Line2D
    for artist in fig.findobj(Collection):
        try:
            paths = artist.get_paths()
            # Trois façons d'être massif : beaucoup de formes (hexbin), beaucoup
            # de positions (semis de points), ou peu de formes mais à très
            # nombreux sommets (aplats de séries longues, fill_between).
            weight = max(len(paths), len(artist.get_offsets()) if hasattr(artist, "get_offsets") else 0,
                         sum(len(path.vertices) for path in paths) // 4)
            if weight > path_limit:
                artist.set_rasterized(True)
        except (AttributeError, TypeError, ValueError):
            continue
    for artist in fig.findobj(Line2D):
        data = artist.get_xdata()
        if data is not None and len(data) > point_limit:
            artist.set_rasterized(True)


def _fit_legend_inside(fig, floor=13.0, shrink=0.94, attempts=12) -> None:
    """Aucune légende ne doit déborder du cadre de son graphique (demande
    utilisateur 2026-09-17).

    Le défaut constaté : une légende plus large que ses axes déborde de la
    figure, et l'enregistrement en cadrage serré (`bbox_inches="tight"`)
    élargit alors l'image pour l'inclure — le graphique lui-même paraît
    écrasé dans un canevas devenu très large (mesuré sur lorenz_capital :
    rapport 1,575 au lieu de 1,09 attendu).

    On mesure donc chaque légende D'AXES et on réduit sa police par crans tant
    qu'elle dépasse, avec un plancher : mieux vaut une légende un peu plus
    petite que doublée mais hors cadre. Les légendes de FIGURE (`fig.legend`,
    utilisées volontairement hors des axes pour les vies individuelles) ne sont
    pas touchées."""
    axes_with_legend = [axis for axis in fig.axes if axis.get_legend() is not None]
    if not axes_with_legend:
        return
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for axis in axes_with_legend:
        legend = axis.get_legend()
        for _ in range(attempts):
            box, frame = legend.get_window_extent(renderer), axis.get_window_extent(renderer)
            if box.width <= frame.width and box.height <= frame.height:
                break
            sizes = [text.get_fontsize() for text in legend.get_texts()]
            if not sizes or min(sizes) <= floor:
                break
            for text in legend.get_texts():
                text.set_fontsize(max(floor, text.get_fontsize() * shrink))
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()


def save(fig, path: Path, *, sources=(), note="", **fields) -> None:
    """Écrit la figure en PNG (lecture rapide) ET en SVG (vectoriel, texte
    éditable), toutes deux porteuses des mêmes métadonnées. `sources` liste
    les tables lues, `note` décrit ce que montre la figure, `fields` reçoit
    les valeurs propres à la figure (fenêtres, ajustements…)."""
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    # Toutes les figures passent par ici : c'est donc le seul endroit où
    # garantir qu'aucune légende ne déborde de son cadre, plutôt que de
    # raccourcir les libellés figure par figure.
    _fit_legend_inside(fig)
    payload = {"figure": path.stem, **RUN_METADATA, "sources": list(sources), **fields}
    if note:
        payload["description"] = note
    text = json.dumps(payload, ensure_ascii=False, sort_keys=False, default=float)
    # ORDRE IMPORTANT : le PNG s'écrit AVANT la rastérisation, sinon les
    # couches denses seraient rastérisées deux fois (sans effet visible) et,
    # surtout, inverser ces deux lignes ferait perdre au SVG son intérêt.
    fig.savefig(path, dpi=145, bbox_inches="tight",
                metadata={"Title": path.stem, "Description": text, "Software": "m4_3 reporting.py"})
    _rasterize_dense_artists(fig)
    svg_path = path.with_suffix(".svg")
    fig.savefig(svg_path, bbox_inches="tight",
                metadata={"Title": path.stem, "Description": text, "Creator": "m4_3 reporting.py", "Date": None})
    # Le DOCTYPE SVG 1.1 écrit par matplotlib est inutile (il est même
    # déconseillé depuis SVG 1.1 SE) et il est refusé par les hébergeurs qui
    # interdisent toute DTD. On l'enlève : le fichier reste un SVG valide.
    svg_path.write_text(_STRIP_DOCTYPE.sub("", svg_path.read_text(encoding="utf-8"), count=1), encoding="utf-8")
    index = path.parent / "figures_metadata.json"
    catalogue = {}
    if index.exists():
        try:
            catalogue = json.loads(index.read_text(encoding="utf-8"))
        except ValueError:
            catalogue = {}
    catalogue[path.stem] = payload
    index.write_text(json.dumps(catalogue, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    plt.close(fig)


def rolling(values, window: int) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if not len(values):
        return values
    window = max(1, min(window, len(values)))
    return np.convolve(values, np.ones(window) / window, mode="same")


def gini(values) -> float:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values) & (values >= 0)]
    if not len(values) or values.sum() <= 0:
        return 0.0
    values.sort()
    n = len(values)
    return float((2 * np.dot(np.arange(1, n + 1), values) / values.sum() - n - 1) / n)


def lorenz(values):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values) & (values >= 0)]
    if not len(values) or values.sum() <= 0:
        return None
    cumulative = np.r_[0.0, np.cumsum(np.sort(values))]
    return np.linspace(0, 1, len(cumulative)), cumulative / cumulative[-1], gini(values)


def wilson(counts, total, widths):
    p = counts / total
    denominator = 1.0 + 1.0 / total
    midpoint = (p + 1.0 / (2.0 * total)) / denominator
    radius = np.sqrt(p * (1.0 - p) / total + 1.0 / (4.0 * total**2)) / denominator
    density = p / widths
    return density, np.maximum(0, midpoint - radius) / widths, np.minimum(1, midpoint + radius) / widths


def _quantile_edges(values, *, max_bins=42):
    """Bornes de bins de TAILLE ADAPTATIVE (nombre de bins ~sqrt(n), bornes
    aux quantiles empiriques plutôt qu'espacées uniformément) : chaque bin
    reçoit un effectif comparable, y compris dans la queue où un pas
    linéaire ou log fixe laisserait des bins presque vides (bruit Poisson
    dominant). Factorisé pour être partagé entre `adaptive_hist` (déjà
    ainsi) et `temporal_density` (corrigé le 2026-08-09 — utilisait un
    `np.logspace` à nombre de bins FIXE, cf. JOURNAL.md)."""
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values) & (values > 0)]
    if len(values) < 2 or values.min() == values.max():
        return None
    bins = max(5, min(max_bins, int(np.sqrt(len(values)))))
    quantiles = np.linspace(0, 1, bins + 1)
    return np.unique(np.quantile(values, quantiles))


def adaptive_hist(values, *, integer=False, max_bins=42):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values) & (values > 0)]
    edges = _quantile_edges(values, max_bins=max_bins)
    if edges is None:
        return None
    if integer:
        edges = np.unique(np.r_[max(0.5, edges[0] - 0.5), np.floor(edges[1:-1]) + 0.5, edges[-1] + 0.5])
    else:
        edges[0] = max(np.nextafter(0.0, 1.0), edges[0] * 0.999999)
        edges[-1] *= 1.000001
    if len(edges) < 3:
        return None
    counts, _ = np.histogram(values, edges)
    widths = np.diff(edges)
    centres = np.sqrt(edges[:-1] * edges[1:])
    density, lower, upper = wilson(counts, len(values), widths)
    return edges, centres, counts, density, lower, upper


def nl_logpdf(y, nu, tau, a, b):
    z = (y - nu) / tau
    left = a * (nu - y) + 0.5 * (a * tau) ** 2 + stats.norm.logcdf(z - a * tau)
    right = b * (y - nu) + 0.5 * (b * tau) ** 2 + stats.norm.logcdf(-(z + b * tau))
    return math.log(a) + math.log(b) - math.log(a + b) + np.logaddexp(left, right)


def dpln_logpdf(x, nu, tau, a, b):
    x = np.asarray(x, dtype=float)
    return nl_logpdf(np.log(x), nu, tau, a, b) - np.log(x)


def fit_dpln(values):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values) & (values > 0)]
    if len(values) < 40:
        return None
    if len(values) > 50_000:
        values = np.random.default_rng(0).choice(values, 50_000, replace=False)
    y = np.log(values)
    mean, sd = float(y.mean()), max(float(y.std()), 1e-3)

    def objective(theta):
        nu, lt, la, lb = theta
        tau, a, b = np.exp([lt, la, lb])
        if tau > 50 or a > 1e4 or b > 1e4:
            return 1e100
        value = -float(nl_logpdf(y, nu, tau, a, b).sum())
        return value if np.isfinite(value) else 1e100

    starts = (
        (mean, math.log(sd), math.log(2 / sd), math.log(2 / sd)),
        (mean, math.log(sd / 2), math.log(1 / sd), math.log(3 / sd)),
        (mean - sd, math.log(sd), math.log(3 / sd), math.log(1 / sd)),
    )
    results = [minimize(objective, start, method="Nelder-Mead", options={"maxiter": 1800}) for start in starts]
    best = min(results, key=lambda result: result.fun)
    if not np.isfinite(best.fun) or best.fun >= 1e99:
        return None
    nu, lt, la, lb = best.x
    return {"nu": float(nu), "tau": float(np.exp(lt)), "a": float(np.exp(la)), "b": float(np.exp(lb))}


def fit_cutoff_powerlaw(values):
    """MLE discrète de p(s) ∝ s^-alpha exp(-s/s_c), s >= 2."""
    values=np.asarray(values,dtype=int); values=values[values>=2]
    if len(values)<20: return None
    maximum=int(values.max()); support=np.arange(2,max(maximum+1,4),dtype=float)
    def objective(theta):
        alpha,log_cutoff=theta; cutoff=math.exp(log_cutoff); logw=-alpha*np.log(support)-support/cutoff; logz=np.logaddexp.reduce(logw)
        return float(np.sum(alpha*np.log(values)+values/cutoff+logz))
    result=minimize(objective,(1.5,math.log(max(2,maximum))),method="Nelder-Mead",options={"maxiter":1200})
    if not result.success or not np.isfinite(result.fun): return None
    alpha,log_cutoff=result.x; cutoff=math.exp(log_cutoff)
    if alpha<=0 or cutoff<=0: return None
    logw=-alpha*np.log(support)-support/cutoff; pmf=np.exp(logw-np.logaddexp.reduce(logw))
    return {"alpha":float(alpha),"cutoff":float(cutoff),"support":support,"pmf":pmf}


def fit_pareto_tail(values, lower=None, n_candidates=40, min_tail=30, at_lower=False):
    """Pareto continue sur la queue x ≥ x_min (méthode Clauset-Shalizi-Newman).

    Deux façons de fixer x_min :
    - `at_lower=True` : x_min EST `lower`, sans recherche. C'est le cas des
      densités de volumes d'avalanches (demande utilisateur 2026-09-17), où la
      plage utile se lit directement sur la figure — tout ce qui suit le
      maximum de la densité — et où un x_min choisi par ajustement déplacerait
      le début de la régression sans raison lisible par le lecteur ;
    - sinon, x_min est cherché sur une grille de quantiles des valeurs ≥
      `lower` en minimisant la distance de Kolmogorov-Smirnov.
    Dans les deux cas la distance KS est calculée et rapportée, ce qui reste la
    mesure de qualité de l'ajustement. Convention de
    `scripts/pareto_convention.py` de M4.3 : α est l'exposant de DENSITÉ,
    p(x) ∝ x^-α, α = 1 + n/Σln(x/x_min), erreur-type (α-1)/√n ; l'exposant de
    CCDF vaut κ = α - 1. `share` = part de l'échantillon complet dans la queue,
    pour normaliser la densité tracée sur le même axe que l'histogramme de tout
    l'échantillon."""
    values = np.sort(np.asarray(values, dtype=float))
    values = values[np.isfinite(values) & (values > 0)]
    pool = values if lower is None else values[values >= lower]
    if len(pool) < 2 * min_tail:
        return None
    if at_lower and lower is not None:
        candidates = np.asarray([float(lower)])
    else:
        candidates = np.unique(np.quantile(pool, np.linspace(0, .9, n_candidates)))
    best = None
    for x_min in candidates:
        tail = values[values >= x_min]
        if len(tail) < min_tail:
            continue
        logs = np.log(tail / x_min).sum()
        if logs <= 0:
            continue
        alpha = 1 + len(tail) / logs
        empirical = np.arange(1, len(tail) + 1) / len(tail)
        model = 1 - (x_min / tail) ** (alpha - 1)
        ks = float(np.max(np.abs(empirical - model)))
        if best is None or ks < best["ks"]:
            best = {"alpha": float(alpha), "x_min": float(x_min), "ks": ks, "n_tail": len(tail),
                    "stderr": float((alpha - 1) / math.sqrt(len(tail))), "share": len(tail) / len(values)}
    return best


def _plot_pareto_tail(axis, values, histogram, color, prefix=""):
    """Trace la densité Pareto ajustée sur la branche descendante.

    La régression part EXACTEMENT du maximum de la densité (demande
    utilisateur 2026-09-17) : sur ces distributions de volumes, la plage se
    lit à l'œil sur la figure, et faire commencer la droite ailleurs que là
    où le lecteur voit le sommet serait injustifiable dans un article."""
    edges, centres, counts, density, _, _ = histogram
    mode_edge = float(edges[int(np.argmax(density))])
    fit = fit_pareto_tail(values, lower=mode_edge, at_lower=True)
    if not fit:
        return None
    grid = np.logspace(np.log10(fit["x_min"]), np.log10(np.max(values)), 200)
    model = fit["share"] * (fit["alpha"] - 1) / fit["x_min"] * (grid / fit["x_min"]) ** (-fit["alpha"])
    axis.plot(grid, model, ":", lw=1.6, color=color,
              label=prefix + LABELS["fit_pareto"].format(**fit))
    return fit


def _plot_adaptive(axis, values, color, label=None, integer=False):
    result = adaptive_hist(values, integer=integer)
    if result is None:
        return None
    edges, centres, counts, density, lower, upper = result
    keep = counts > 0
    axis.errorbar(
        centres[keep], density[keep],
        xerr=np.vstack((centres - edges[:-1], edges[1:] - centres))[:, keep],
        yerr=np.vstack((density - lower, upper - density))[:, keep],
        fmt="o", ms=3.1, capsize=2, elinewidth=.7, alpha=.72, color=color,
        label=label,
    )
    return result


def macro(members, out: Path, title: str):
    # Un seul graphe, trois échelles superposées (host + 2 axes parasites) :
    # capital (J), crédit nouveau (J/pas), population (effectif), plus
    # ΣDettes/ΣCapital (sans unité). nw_tot est omis : par identité comptable
    # (créances = dettes agrégées) il est égal à K_tot au bruit numérique près,
    # donc redondant avec la courbe K. Le ratio ΣD/ΣK n'est pas stocké pas à
    # pas dans series.csv (seuls des flux y figurent) — il est reconstruit ici
    # à partir des instantanés (npz), donc à la cadence (plus lâche) de
    # snapshot_every : c'est pourquoi il apparaît en pointillés/marqueurs
    # plutôt qu'en trait continu comme les séries pas-à-pas.
    #
    # Sous-graphique de zoom (demande utilisateur 2026-09-15) : la vue
    # complète écrase les fluctuations sous la tendance ; une fenêtre courte
    # (T/20 pas, prise aux 3/4 du run, donc après le burn-in T/4) est
    # agrandie en dessous, et un cadre sur la vue complète la localise.
    loaded = []
    for index, (seed, folder) in enumerate(members):
        rows = read_csv(folder / "series.csv")
        if not rows:
            continue
        snaps = snapshots(folder)
        steps = sorted(snaps)
        ratio = []
        for step in steps:
            k_sum = float(np.sum(snaps[step]["K"]))
            ratio.append(float(np.sum(snaps[step]["debts"])) / k_sum if k_sum > 0 else np.nan)
        loaded.append((index, seed, np.asarray([row["t"] for row in rows]), np.asarray([row["K_tot"] for row in rows]),
                       np.asarray([row["loan_volume"] for row in rows]), np.asarray([row["pop"] for row in rows]),
                       np.asarray(steps), np.asarray(ratio)))
    if not loaded:
        return
    t_end = max(float(item[2].max()) for item in loaded)

    # DISPOSITION (refaite le 2026-09-17, signalement utilisateur) : la courbe
    # mère occupe le haut de la figure avec ses limites NATURELLES — origine en
    # bas du cadre — et les deux encarts vivent SOUS elle, dans leurs propres
    # axes. Auparavant la place des encarts était prise sur les axes de la mère,
    # étendus vers le bas : le zéro se retrouvait à 51 % de la hauteur et l'axe
    # du capital descendait à −4,5·10⁶ J, une valeur dénuée de sens.
    # L'isotropie stricte a été ABANDONNÉE le 2026-09-17 : à cadre figé elle
    # liait la brièveté de la fenêtre à la hauteur disponible et n'était
    # satisfaite qu'à partir de 400 pas, incompatible avec le plafond de 300
    # pas demandé. Elle est remplacée par une contrainte de position relative
    # (même fraction d'axe pour le capital et la population), toujours
    # satisfiable et plus proche de ce que le lecteur compare réellement.
    # Largeur ramenée de .72 à .66 (2026-09-17) : avec les polices agrandies et
    # les axes de droite écartés de 78 et 160 pt, l'étiquette du troisième axe
    # sortait de la figure — mesuré au rapport d'image, 1,464 pour 1,354 visé.
    MAIN_BOX = (.06, .42, .66, .50)          # gauche, bas, largeur, hauteur (fractions de figure)
    # Encarts resserrés et mieux écartés : à 0,30 de large et 0,10/0,50 de
    # marge, l'étiquette droite du premier (« Population ») recouvrait
    # l'étiquette gauche du second (« Nouveau crédit »).
    INSET_ZOOM_BOX = (.09, .055, .28, .30)
    INSET_CREDIT_BOX = (.57, .055, .28, .30)
    fig = plt.figure(figsize=(13, 9.6))
    host = fig.add_axes(MAIN_BOX)
    c_k, c_credit, c_pop, c_ratio = "#1f77b4", "#d62728", "#2ca02c", "#7f2aa3"
    ax_credit, ax_pop, ax_ratio = host.twinx(), host.twinx(), host.twinx()
    # Écartement des axes de droite : recalculé après l'agrandissement général
    # des polices (2026-09-17). À 55/110, dimensionnés pour de petites
    # graduations, les nombres du troisième axe recouvraient l'étiquette du
    # deuxième dès que la police passait à 15 pt.
    ax_pop.spines["right"].set_position(("outward", 78))
    ax_ratio.spines["right"].set_position(("outward", 160))
    for twin in (ax_pop, ax_ratio):
        twin.set_frame_on(True); twin.patch.set_visible(False)
    host.set_ylabel(LABELS["capital"], color=c_k)
    ax_credit.set_ylabel(LABELS["new_credit"], color=c_credit)
    ax_pop.set_ylabel(LABELS["population"], color=c_pop)
    ax_ratio.set_ylabel(LABELS["debt_ratio"], color=c_ratio)
    for twin, color in ((host, c_k), (ax_credit, c_credit), (ax_pop, c_pop), (ax_ratio, c_ratio)):
        twin.tick_params(axis="y", colors=color)
    handles = []; any_ratio = False
    for index, seed, t, k, credit, pop, steps, ratio in loaded:
        fade = 1.0 if index == 0 else 0.5
        h1, = host.plot(t, k, color=c_k, alpha=.85 * fade, label=f"K — {LABELS['seed']} {seed}")
        h3, = ax_credit.plot(t, credit, color=c_credit, alpha=.55 * fade, lw=.7, label=f"{LABELS['new_credit']} — {LABELS['seed']} {seed}")
        h4, = ax_pop.plot(t, pop, color=c_pop, alpha=.8 * fade, label=f"{LABELS['population']} — {LABELS['seed']} {seed}")
        handles += [h1, h3, h4]
        if len(steps):
            h5, = ax_ratio.plot(steps, ratio, color=c_ratio, ls=":", marker="o", ms=2.6, lw=1.0, alpha=.8 * fade, label=f"ΣD/ΣK — {LABELS['seed']} {seed}")
            handles.append(h5); any_ratio = True
    if not any_ratio:
        ax_ratio.set_visible(False)
    host.set_xlim(0, t_end); host.set_xlabel(LABELS["step"]); host.grid(True, alpha=.22)
    # Légende hors du cadre : les deux zooms occupent le bas de la figure.
    host.legend(handles=handles, loc="lower center", bbox_to_anchor=(.5, 1.005), ncol=4, frameon=False)

    # Étendues réellement affichées, SANS aucune réserve : les axes gardent
    # leurs limites naturelles. C'est sur elles que sont calculées les
    # fractions d'axe des encarts — donc à mesurer avant tout artiste.
    axis_spans = {}
    for axis, key in ((host, "capital"), (ax_pop, "population"), (ax_credit, "credit")):
        low, high = axis.get_ylim()
        axis_spans[key] = float(high - low) or 1.0

    # Rapports géométriques encart / courbe mère, en fractions de FIGURE : ce
    # sont eux qui fixent le grandissement, les cadres étant désormais figés.
    WIDTH_RATIO = INSET_ZOOM_BOX[2] / MAIN_BOX[2]
    HEIGHT_RATIO = INSET_ZOOM_BOX[3] / MAIN_BOX[3]
    _, _, t_ref, k_ref, credit_ref, pop_ref, steps_ref, ratio_ref = loaded[0]

    # FENÊTRE DE ZOOM (demande utilisateur 2026-09-17) : au plus 300 pas. Le
    # repli d'autrefois valait T/20, soit 400 pas à T=8000 — il violait le
    # plafond, il est donc lui aussi borné.
    MAX_ZOOM_STEPS = 300
    width = float(min(MAX_ZOOM_STEPS, max(20.0, round(t_end / 20))))
    z0 = float(round(.75 * t_end - width / 2)); z1 = z0 + width
    inside = (t_ref >= z0) & (t_ref <= z1)
    if inside.sum() < 5:  # instantanés trop clairsemés : on colle à la fin du run.
        z0 = float(t_ref.max() - width); z1 = z0 + width
        inside = t_ref >= z0

    # POSITION RELATIVE : une SEULE fraction d'axe pour le capital et la
    # population, donc deux rectangles de même taille relative dans leurs
    # courbes mères respectives. `axis_spans` a été mesuré sur les limites
    # naturelles des axes, avant tout artiste.
    MIN_FRACTION = .02
    axis_of = {"capital": host, "population": ax_pop}
    fractions, centres_rel = {}, {}
    for name, series in (("capital", k_ref), ("population", pop_ref)):
        window = series[inside]
        low, high = float(window.min()), float(window.max())
        fractions[name] = max(MIN_FRACTION, (high - low) * 1.12 / axis_spans[name])
        centres_rel[name] = ((low + high) / 2 - axis_of[name].get_ylim()[0]) / axis_spans[name]
    span_fraction = max(fractions.values())

    # Même hauteur relative aussi, quand c'est possible : si les deux grandeurs
    # fluctuent à des hauteurs voisines de leurs axes, on impose le même centre
    # relatif et les deux rectangles se superposent EXACTEMENT — lecture
    # littérale de la consigne. Sinon les forcer ensemble sortirait l'une des
    # deux de son axe ; chacune garde alors sa hauteur et les métadonnées le
    # disent, plutôt que de produire un cadre faux.
    shared_centre = abs(centres_rel["capital"] - centres_rel["population"]) <= .10
    limits = {}
    for name in ("capital", "population"):
        centre_rel = sum(centres_rel.values()) / 2 if shared_centre else centres_rel[name]
        centre_rel = min(max(centre_rel, span_fraction / 2), 1 - span_fraction / 2)
        centre = axis_of[name].get_ylim()[0] + centre_rel * axis_spans[name]
        half = span_fraction * axis_spans[name] / 2
        limits[name] = (centre - half, centre + half)
    zoom = {"start": z0, "end": z1, "width": width, "limits": limits, "inside": inside,
            "magnification": WIDTH_RATIO * t_end / width}

    # Encart 1 : capital et population, vrai zoom. Plus de rapport ΣD/ΣK ici,
    # il reste sur la vue complète (2026-09-17).
    inset = fig.add_axes(INSET_ZOOM_BOX)
    inset.plot(t_ref[inside], k_ref[inside], color=c_k, lw=1.0)
    inset.set_xlim(z0, z1); inset.set_ylim(*zoom["limits"]["capital"]); inset.grid(True, alpha=.18)
    inset.tick_params(axis="y", colors=c_k)
    inset.set_ylabel(LABELS["capital"], color=c_k)
    inset_pop = inset.twinx()
    inset_pop.plot(t_ref[inside], pop_ref[inside], color=c_pop, lw=1.0)
    inset_pop.set_ylim(*zoom["limits"]["population"])
    inset_pop.tick_params(colors=c_pop)
    inset_pop.set_ylabel(LABELS["population"], color=c_pop)

    # Encart 2 : nouveau crédit, MÊMES abscisses, sans contrainte d'isotropie
    # — ses fluctuations sont trop amples pour tenir dans un cadre isotrope.
    inset_credit = fig.add_axes(INSET_CREDIT_BOX)
    window_credit = credit_ref[inside]
    pad = .06 * float(window_credit.max() - window_credit.min() or 1)
    credit_limits = (float(window_credit.min()) - pad, float(window_credit.max()) + pad)
    inset_credit.plot(t_ref[inside], window_credit, color=c_credit, lw=.9)
    inset_credit.set_xlim(z0, z1); inset_credit.set_ylim(*credit_limits); inset_credit.grid(True, alpha=.18)
    inset_credit.tick_params(axis="y", colors=c_credit)
    inset_credit.set_ylabel(LABELS["new_credit"], color=c_credit)

    # Repères sur la vue complète : un rectangle par grandeur, tracé SUR SON
    # PROPRE axe vertical. `indicate_inset_zoom` les plaçait tous sur l'axe du
    # capital, donc juste en abscisse mais faux en ordonnée (2026-09-17).
    def mark(axis, limits, color, target):
        low, high = limits
        axis.add_patch(Rectangle((z0, low), z1 - z0, high - low, fill=False, ec=color, lw=1.0, alpha=.9, zorder=6))
        for corner in (0, 1):
            fig.add_artist(ConnectionPatch(xyA=(z0 if corner == 0 else z1, high), coordsA=axis.transData,
                                           xyB=(corner, 1), coordsB=target.transAxes, color=color, lw=.6, alpha=.4))

    mark(host, zoom["limits"]["capital"], c_k, inset)
    mark(ax_pop, zoom["limits"]["population"], c_pop, inset)
    mark(ax_credit, credit_limits, c_credit, inset_credit)

    # Les rectangles et leurs traits de liaison ré-étirent les axes (marges
    # d'autoscale de matplotlib) : la vue complète repartait alors nettement
    # sous 0. On réaffirme l'origine à 0 APRÈS tous les artistes (2026-09-17).
    for axis in (host, ax_credit, ax_pop, ax_ratio):
        axis.set_xlim(0, t_end)

    credit_span_full = axis_spans["credit"]
    zoom_meta = {
        "zoom_window": [z0, z1], "zoom_width_steps": width,
        "horizontal_magnification": round(zoom["magnification"], 2),
        # Contrainte réellement appliquée : même fraction d'axe pour les deux
        # grandeurs (et même hauteur relative si `shared_relative_centre`).
        "zoom_max_steps": MAX_ZOOM_STEPS,
        "relative_span_fraction": round(float(span_fraction), 4),
        "shared_relative_centre": bool(shared_centre),
        "relative_centres": {name: round(float(value), 4) for name, value in centres_rel.items()},
        "capital_population_isotropic": False,
        # Limites montrées par les encarts : ce sont EXACTEMENT celles des
        # rectangles tracés sur la courbe mère, en abscisse comme en ordonnée.
        "capital_window": [float(v) for v in zoom["limits"]["capital"]],
        "population_window": [float(v) for v in zoom["limits"]["population"]],
        "credit_window": [float(v) for v in credit_limits],
        # Grandissement vertical commun aux deux grandeurs : une bande de
        # `span_fraction` d'axe remplit un cadre HEIGHT_RATIO fois plus petit.
        "capital_population_vertical_magnification": round(HEIGHT_RATIO / span_fraction, 2),
        "credit_isotropic": False,
        "credit_vertical_magnification": round(HEIGHT_RATIO * credit_span_full / (credit_limits[1] - credit_limits[0]), 2),
    }
    # Pas de `subplots_adjust` ici : les trois cadres sont posés explicitement
    # (MAIN_BOX, INSET_ZOOM_BOX, INSET_CREDIT_BOX) et un réajustement global
    # les déplacerait, ruinant le calcul des fractions d'axe qui en dépend.
    save(fig, out / "macro_overview.png",
         sources=["series.csv", "snapshots/entities_t*.npz"],
         note="Capital total, nouveau crédit, population et rapport dettes/capital (ce dernier mesuré aux instantanés). Encart de gauche : zoom sur le capital et la population, sur une fenêtre d'au plus 300 pas ; les deux grandeurs y sont encadrées sur la même fraction de leur axe, donc à la même position relative dans leur courbe mère. Encart de droite : même fenêtre d'abscisses pour le nouveau crédit, cadré sur ses propres données. Les rectangles de la vue complète repèrent la fenêtre, chacun sur l'axe vertical de sa grandeur.",
         **zoom_meta)


def avalanche_samples(folder: Path):
    rows = read_csv(folder / "avalanches.csv")
    burn = int(config(folder).get("T", 0)) // 4
    selected = [row for row in rows if row.get("t", 0) >= burn and row.get("size", 0) >= 2]
    sizes = np.asarray([row["size"] for row in selected], dtype=int)
    if selected and "volume_j" not in selected[0]:
        # Migration en lecture seule des runs m4b-mini-2 : la dette capturée
        # juste avant chaque décès est exactement le principal détruit.
        debts = {(int(row["t"]), int(row["id"])): float(row["debts"]) for row in read_csv(folder / "deaths.csv")}
        members = defaultdict(float)
        for row in read_csv(folder / "avalanche_members.csv"):
            members[int(row["avalanche_id"])] += debts.get((int(row["t"]), int(row["id"])), 0.0)
        volumes = np.asarray([members[int(row["avalanche_id"])] for row in selected], dtype=float)
    else:
        volumes = np.asarray([row.get("volume_j", 0) for row in selected], dtype=float)
    return selected, sizes, volumes[volumes > 0]


def avalanche_figures(members, out: Path, title: str, volume_ccdf_output=True):
    """Trois figures distinctes (demande utilisateur 2026-09-17) : densité des
    tailles, CCDF des tailles, densité des volumes. Plus aucun titre dessiné —
    tout ce qui identifiait la figure est dans ses métadonnées."""
    burn = int(config(members[0][1]).get("T", 0)) // 4 if members else 0
    fig_size, ax_size = plt.subplots(figsize=(9.5, 6.2))
    fig_ccdf, ax_ccdf = plt.subplots(figsize=(9.5, 6.2))
    fig_volume, ax_volume = plt.subplots(figsize=(9.5, 6.2))
    any_size = any_volume = False
    fits_size, fits_volume = {}, {}
    for index, (seed, folder) in enumerate(members):
        _, sizes, volumes = avalanche_samples(folder)
        color = COLORS[index % len(COLORS)]
        if len(sizes) >= 2:
            any_size = True
            histogram=_plot_adaptive(ax_size, sizes, color, LABELS["sample_seed"].format(seed_label=LABELS["seed"], seed=seed, n=len(sizes)), integer=True)
            ordered = np.sort(sizes); ccdf = (len(ordered) - np.arange(len(ordered))) / len(ordered)
            ax_ccdf.plot(ordered, ccdf, ".", ms=2.2, alpha=.55, color=color, label=LABELS["sample_seed"].format(seed_label=LABELS["seed"], seed=seed, n=len(ordered)))
            fit_size=fit_cutoff_powerlaw(sizes)
            if fit_size and histogram is not None:
                fits_size[seed] = {"alpha": fit_size["alpha"], "cutoff": fit_size["cutoff"], "n": len(sizes)}
                edges,centres,_,_,_,_=histogram; model=[]
                for lower,upper in zip(edges[:-1],edges[1:]):
                    inside=(fit_size["support"]>=lower)&(fit_size["support"]<upper); model.append(fit_size["pmf"][inside].sum()/(upper-lower))
                model=np.asarray(model); keep=model>0
                ax_size.plot(centres[keep],model[keep],"--",color=color,lw=1.3,label=LABELS["fit_truncated"].format(**fit_size))
                survival=np.cumsum(fit_size["pmf"][::-1])[::-1]
                ax_ccdf.plot(fit_size["support"],survival,"--",color=color,lw=1.3)
        if len(volumes) >= 2:
            any_volume = True
            histogram = _plot_adaptive(ax_volume, volumes, color, LABELS["sample_seed"].format(seed_label=LABELS["seed"], seed=seed, n=len(volumes)))
            # Pareto (x_min par KS) sur la branche descendante seule, en
            # pointillés (2026-09-17) ; remplace la dPlN (2026-09-15).
            if histogram is not None:
                fit = _plot_pareto_tail(ax_volume, volumes, histogram, color)
                if fit: fits_volume[seed] = fit
    for axis in (ax_size, ax_ccdf, ax_volume):
        axis.set_xscale("log"); axis.set_yscale("log"); axis.grid(True, which="both", alpha=.2)
    ax_size.set(xlabel=LABELS["size_ge2"], ylabel=LABELS["density"]); ax_size.legend()
    ax_ccdf.set(xlabel=LABELS["size_ge2"], ylabel=LABELS["ccdf_size"]); ax_ccdf.legend()
    ax_volume.set(xlabel=LABELS["volume"], ylabel=LABELS["density"]); ax_volume.legend()
    common = {"burn_in_applied": burn, "size_min": 2, "sources": ["avalanches.csv", "deaths.csv", "avalanche_members.csv"]}
    if any_size:
        fig_size.tight_layout()
        save(fig_size, out / "avalanche_size_density.png", note="Densité des tailles d'avalanches (bins adaptatifs, IC Wilson 68 %) et ajustement en loi de puissance tronquée s^-alpha exp(-s/s_c).", fits=fits_size, **common)
        fig_ccdf.tight_layout()
        save(fig_ccdf, out / "avalanche_size_ccdf.png", note="Probabilité de survie des tailles d'avalanches, et survie du même ajustement tronqué.", fits=fits_size, **common)
    else:
        plt.close(fig_size); plt.close(fig_ccdf)
    if any_volume:
        fig_volume.tight_layout()
        save(fig_volume, out / "avalanche_volume_density.png", note="Densité des volumes d'avalanches (pertes de créances) et ajustement de Pareto sur la branche descendante, x_min choisi par minimisation de la distance de Kolmogorov-Smirnov. alpha est l'exposant de densité ; l'exposant de CCDF vaut alpha - 1.", fits=fits_volume, **common)
    else:
        plt.close(fig_volume)

    if not volume_ccdf_output:
        return
    fig, axis = plt.subplots(figsize=(9.5, 6))
    plotted = False
    for index, (seed, folder) in enumerate(members):
        _, _, volumes = avalanche_samples(folder)
        if len(volumes) < 2: continue
        plotted = True; ordered = np.sort(volumes)
        axis.plot(ordered, (len(ordered) - np.arange(len(ordered))) / len(ordered), ".", ms=2.3, alpha=.58, color=COLORS[index % 10], label=f"{LABELS['seed']} {seed}")
    if plotted:
        axis.set(xscale="log", yscale="log", xlabel=LABELS["volume"], ylabel="P(V ≥ v)")
        axis.grid(True, which="both", alpha=.22); axis.legend()
        fig.tight_layout(); save(fig, out / "volume_ccdf.png", sources=["avalanches.csv"],
             note="Probabilité de survie des volumes d'avalanches de taille ≥ 2, après burn-in.")
    else: plt.close(fig)


def temporal_density(snaps, key, max_bins=42):
    steps = sorted(snaps)
    arrays = []
    for step in steps:
        values = np.asarray(snaps[step][key], dtype=float)
        arrays.append(values[np.isfinite(values) & (values > 0)])
    nonempty = [values for values in arrays if len(values)]
    if not nonempty: return None
    pooled = np.concatenate(nonempty)
    if len(pooled) < 10 or pooled.min() == pooled.max(): return None
    # Bornes aux quantiles du pool (bins de taille adaptative, cf.
    # _quantile_edges) au lieu d'un np.logspace à nombre de bins FIXE :
    # mêmes bornes réutilisées pour chaque instantané (comparabilité de
    # l'enveloppe temporelle et du GIF), mais l'effectif par bin ne
    # s'effondre plus dans la queue. Corrigé le 2026-08-09 (JOURNAL.md).
    edges = _quantile_edges(pooled, max_bins=max_bins)
    if edges is None or len(edges) < 3: return None
    edges[0] = max(np.nextafter(0.0, 1.0), edges[0] * 0.999999)
    edges[-1] *= 1.000001
    widths = np.diff(edges); centres = np.sqrt(edges[:-1] * edges[1:])
    densities = np.asarray([np.histogram(values, edges)[0] / (max(1, len(values)) * widths) for values in arrays])
    return np.asarray(steps), centres, densities, np.asarray([len(values) for values in arrays]), edges


def _time_weights(steps):
    steps = np.asarray(steps, dtype=float)
    if len(steps) == 1: return np.ones(1)
    weights = np.r_[steps[1] - steps[0], steps[2:] - steps[:-2], steps[-1] - steps[-2]] / 2
    return weights / weights.sum()


def _weighted_quantile(values, weights, quantile):
    order = np.argsort(values)
    ordered = np.asarray(values, dtype=float)[order]
    cumulative = np.cumsum(np.asarray(weights, dtype=float)[order])
    return float(np.interp(quantile, cumulative, ordered))


def fit_tail_powerlaw(centres, density, min_points=5):
    """Loi de puissance en queue sur une densité déjà binée (demande
    utilisateur 2026-09-17).

    La borne inférieure est le DÉBUT DU COUDE : on ajuste une droite en
    log-log sur tous les points au-delà de chaque borne candidate, et on
    retient la borne la plus BASSE dont le R² reste à moins de 0,01 du
    meilleur R² atteignable. Autrement dit : la plage la plus large qui
    reste aussi droite que la meilleure. α est l'exposant de densité
    (p ∝ x^-α), donc l'opposé de la pente ajustée."""
    centres = np.asarray(centres, dtype=float); density = np.asarray(density, dtype=float)
    keep = np.isfinite(centres) & np.isfinite(density) & (centres > 0) & (density > 0)
    x, y = np.log10(centres[keep]), np.log10(density[keep])
    if len(x) < min_points + 2:
        return None
    peak = int(np.argmax(y))
    candidates = []
    for start in range(peak + 1, len(x) - min_points + 1):
        result = stats.linregress(x[start:], y[start:])
        if not np.isfinite(result.slope) or result.slope >= 0:
            continue
        candidates.append((start, result))
    if not candidates:
        return None
    best = max(r.rvalue ** 2 for _, r in candidates)
    start, result = next((s, r) for s, r in candidates if r.rvalue ** 2 >= best - .01)
    return {"alpha": float(-result.slope), "stderr": float(result.stderr), "r2": float(result.rvalue ** 2),
            "x_min": float(centres[keep][start]), "x_max": float(centres[keep][-1]),
            "n_points": int(len(x) - start), "intercept": float(result.intercept)}


def _plot_tail_powerlaw(axis, centres, density, color):
    """Trace la régression de queue en arrière-plan, peu marquée."""
    fit = fit_tail_powerlaw(centres, density)
    if not fit:
        return None
    grid = np.logspace(np.log10(fit["x_min"]), np.log10(fit["x_max"]), 120)
    model = 10 ** (fit["intercept"] - fit["alpha"] * np.log10(grid))
    # Droite fine, dans une couleur franchement distincte de celle des points
    # (demande utilisateur 2026-09-17) : la bande large se confondait avec eux.
    axis.plot(grid, model, "-", color="#111111", lw=1.2, alpha=.9, zorder=4,
              label=LABELS["fit_tail"].format(**fit))
    return fit


def temporal_distribution(folder, out, key, label, stem, color, title, fit_tail=True):
    """`fit_tail=False` retire la régression de queue (demande utilisateur
    2026-09-17 : pas de régression sur les données temporelles du capital ni de
    l'extraction). Les autres grandeurs la gardent ; `tail_fit` vaut alors
    `None` dans les métadonnées, ce qui est le compte rendu honnête."""
    prepared = temporal_density(snapshots(folder), key)
    if prepared is None: return
    steps, centres, densities, counts, edges = prepared
    weights = _time_weights(steps); mean = np.average(densities, axis=0, weights=weights)
    # Enveloppe D1-D9 : dispersion temporelle (inter-instantanés) de la densité
    # à chaque bin, pas une incertitude d'échantillonnage — remise en place à
    # l'identique de la convention M4 (cf. individual_figures.py, M4).
    q10 = np.asarray([_weighted_quantile(densities[:, j], weights, .1) for j in range(densities.shape[1])])
    q90 = np.asarray([_weighted_quantile(densities[:, j], weights, .9) for j in range(densities.shape[1])])
    positive = densities[densities > 0]
    if not len(positive): return
    ymin, ymax = max(1e-14, positive.min() / 2), max(positive.max(), mean.max()) * 2
    # Points non reliés, même représentation que soc_revenue_fits.png
    # (demande utilisateur 2026-09-15) : barre horizontale = étendue du bin
    # adaptatif, barre verticale = enveloppe temporelle D1–D9 (dispersion
    # entre instantanés, pas une incertitude d'échantillonnage).
    fig, axis = plt.subplots(figsize=(9.5, 5.8))
    valid = mean > 0
    # Fenêtre d'affichage : les 95 % de POINTS TRACÉS les plus grands (demande
    # utilisateur 2026-09-17 — 95 % des points, et non des observations : les
    # deux ne coïncident pas, mesuré sur int_out où le 5e percentile des
    # valeurs donne 7,8 et la règle sur les points 10,0). Motif : le bin le
    # plus bas est rare et très étalé en log — sur int_out il part de 0,04
    # J/pas et occupe à lui seul la moitié des 3,5 décades de l'axe. On coupe
    # toujours par le BAS : par le haut se trouve la queue en loi de puissance,
    # dont la plage ajustée dépasse largement le 97,5e percentile des valeurs.
    points = centres[valid]
    dropped = int(np.ceil(.05 * len(points))) if len(points) >= 8 else 0
    if len(points) > dropped + 1:
        window = (float(points[dropped]) / 1.15, float(points[-1]) * 1.15)
    else:
        window = (float(edges[0]), float(edges[-1]) * 1.05)
    lower = np.clip(mean - np.maximum(q10, ymin), 0, None); upper = np.clip(q90 - mean, 0, None)
    axis.errorbar(centres[valid], mean[valid],
                  xerr=np.vstack((centres - edges[:-1], edges[1:] - centres))[:, valid],
                  yerr=np.vstack((lower, upper))[:, valid],
                  fmt="o", ms=3.1, capsize=2, elinewidth=.7, alpha=.8, color=color, zorder=3,
                  label=LABELS["temporal_mean"].format(snapshots=len(steps)))
    tail = _plot_tail_powerlaw(axis, centres[valid], mean[valid], color) if fit_tail else None
    axis.set(xscale="log", yscale="log", xlim=window, ylim=(ymin, ymax), xlabel=label, ylabel=LABELS["density"])
    axis.grid(True, which="both", alpha=.22); axis.legend()
    fig.tight_layout()
    save(fig, out / f"{stem}_temporal_mean.png",
         sources=["snapshots/entities_t*.npz"],
         note=f"Densité de « {label} », moyenne pondérée par le temps sur les instantanés ; barres horizontales = étendue du bin adaptatif, barres verticales = enveloppe D1–D9 entre instantanés ; bande claire = régression de queue en loi de puissance.",
         quantity=key, quantity_label=label, snapshots_used=int(len(steps)), tail_fit=tail,
         display_window=[window[0], window[1]], display_points_dropped=int(dropped),
         display_points_total=int(len(points)), data_range=[float(edges[0]), float(edges[-1])])
    if len(steps) < 2:
        return
    frame_ids = np.unique(np.linspace(0, len(steps) - 1, min(48, len(steps)), dtype=int))
    fig, axis = plt.subplots(figsize=(9.5, 5.8)); line, = axis.plot([], [], "o-", ms=3, color=color)
    axis.plot(centres[valid], mean[valid], color="black", lw=1.7, label="moyenne temporelle")
    # Même fenêtre que la figure fixe : l'animation et la moyenne temporelle
    # doivent se lire sur les mêmes abscisses.
    axis.set(xscale="log", yscale="log", xlim=window, ylim=(ymin, ymax), xlabel=label, ylabel="Densité")
    axis.grid(True, which="both", alpha=.22); axis.legend()
    def update(frame):
        index = frame_ids[frame]; density = densities[index]; keep = density > 0
        line.set_data(centres[keep], density[keep]); axis.set_title(f"{title} — t={steps[index]}, n={counts[index]}")
        return line,
    FuncAnimation(fig, update, frames=len(frame_ids), interval=170).save(out / f"{stem}_evolution.gif", writer=PillowWriter(fps=6), dpi=90)
    plt.close(fig)


def temporal_selected(folder: Path, out: Path, title: str):
    # Capital et extraction (prod) : pas de régression de queue (demande
    # utilisateur 2026-09-17). La valeur nette NW la garde — la consigne nomme
    # le capital et l'extraction, pas elle.
    temporal_distribution(folder, out, "K", "Capital K (J)", "entity_size_histo", "#1f77b4", title, fit_tail=False)
    temporal_distribution(folder, out, "nw", "Valeur nette NW (J)", "entity_networth_histo", "#663399", title)
    for key, label, stem, color in REVENUES:
        temporal_distribution(folder, out, key, f"{label} (J/pas)", stem, color, title, fit_tail=(key != "prod"))


def series_figures(members, out: Path, title: str):
    fig, axis = plt.subplots(figsize=(12, 5))
    for index, (seed, folder) in enumerate(members):
        snaps=snapshots(folder); steps=sorted(snaps); color=COLORS[index%10]
        if not steps: continue
        med=[]; q10=[]; q90=[]
        for step in steps:
            values=np.asarray(snaps[step]["prod"],dtype=float); values=values[np.isfinite(values)&(values>=0)]
            med.append(np.median(values) if len(values) else 0); q10.append(np.quantile(values,.1) if len(values) else 0); q90.append(np.quantile(values,.9) if len(values) else 0)
        axis.fill_between(steps,q10,q90,color=color,alpha=.14); axis.plot(steps,med,color=color,label=f"médiane — {LABELS['seed']} {seed}")
    axis.set(xlabel=LABELS["step"], ylabel="Production Π (J/pas)"); axis.grid(True, alpha=.22); axis.legend()
    fig.tight_layout(); save(fig, out / "extraction_power.png", sources=["snapshots/entities_t*.npz"],
         note="Production individuelle aux instantanés : médiane et bande interdécile D1–D9.")

    fig, axis = plt.subplots(figsize=(12, 5))
    for index, (seed, folder) in enumerate(members):
        rows = read_csv(folder / "series.csv"); t = [row["t"] for row in rows]
        if not rows: continue
        window = max(5, min(100, len(rows) // 10)); color = COLORS[index % 10]
        axis.plot(t, rolling([row["prod_tot"] for row in rows], window), color=color, alpha=.55, label=f"production — {LABELS['seed']} {seed}")
        axis.plot(t, rolling([row["destroyed"] + row["claim_losses"] for row in rows], window), color=color, ls="--", label=f"destruction — {LABELS['seed']} {seed}")
    axis.set(xlabel=LABELS["step"], ylabel="J/pas"); axis.grid(True, alpha=.22); axis.legend()
    fig.tight_layout(); save(fig, out / "destruction_moving_avg.png", sources=["series.csv"],
         note="Production totale et destruction (joules détruits + pertes de créances), en moyennes glissantes.")

    fig, axis = plt.subplots(figsize=(12, 5))
    for index, (seed, folder) in enumerate(members):
        cfg = config(folder)
        gamma = float(cfg.get("gamma", 0.5)); scale_A = float(cfg.get("A", 1.0))
        snaps = snapshots(folder); steps=[]; values=[]
        for step, snap in snaps.items():
            k = np.asarray(snap["K"]); k = k[k > 0]
            if len(k): steps.append(step); values.append(float(np.median(scale_A * gamma * np.power(k, gamma - 1.0))))
        if steps: axis.plot(steps, values, "o-", ms=3, color=COLORS[index % 10], label=f"{LABELS['seed']} {seed}")
    axis.set(xlabel=LABELS["step"], ylabel="r* = A·γ·K^(γ−1)"); axis.grid(True, alpha=.22); axis.legend()
    fig.tight_layout(); save(fig, out / "internal_rate_evolution.png", sources=["snapshots/entities_t*.npz", "config.json"],
         note="Taux marginal interne médian r* = A·γ·K^(γ−1), aux instantanés.")


def inequality_figures(members, out: Path, title: str):
    # Panneau NW ajouté (demande utilisateur 2026-09-15). Le Gini n'est pas
    # défini pour des valeurs négatives : comme pour int_in, les valeurs
    # nettes négatives sont ramenées à 0 (entités insolvables comptées comme
    # ne détenant rien) ; la part concernée est indiquée en légende.
    # Deux figures séparées (demande utilisateur 2026-09-17) : le capital seul,
    # puis valeur nette et intérêts reçus ensemble — ces deux-là partagent une
    # échelle d'inégalité comparable, le capital non.
    fig_k, ax_k = plt.subplots(figsize=(10, 5.4))
    fig_nw, ax_nw = plt.subplots(figsize=(10, 5.4))
    negative_share = 0.0
    for index, (seed, folder) in enumerate(members):
        snaps = snapshots(folder); steps = sorted(snaps)
        color = COLORS[index % 10]
        if not steps: continue
        ax_k.plot(steps, [gini(snaps[t]["K"]) for t in steps], color=color, label=f"K — {LABELS['seed']} {seed}")
        ax_nw.plot(steps, [gini(np.maximum(snaps[t]["nw"], 0)) for t in steps], color=color, label=f"NW — {LABELS['seed']} {seed}")
        ax_nw.plot(steps, [gini(np.maximum(snaps[t]["int_in"], 0)) for t in steps], color=color, ls="--", label=f"Intérêts reçus — {LABELS['seed']} {seed}")
        negative_share = max(negative_share, max(float(np.mean(np.asarray(snaps[t]["nw"]) < 0)) for t in steps))
    for axis in (ax_k, ax_nw):
        axis.set(ylim=(0, 1), xlabel=LABELS["step"], ylabel=LABELS["gini"]); axis.grid(True, alpha=.22); axis.legend()
    fig_k.tight_layout(); save(fig_k, out / "gini_capital.png", sources=["snapshots/entities_t*.npz"],
        note="Coefficient de Gini du capital K aux instantanés.")
    fig_nw.tight_layout(); save(fig_nw, out / "gini_networth_interest.png", sources=["snapshots/entities_t*.npz"],
        note="Coefficient de Gini de la valeur nette NW et des intérêts reçus aux instantanés. Les valeurs négatives sont ramenées à 0, le Gini n'étant pas défini sinon.",
        negative_networth_max_share=round(negative_share, 5))

    # Trois figures de Lorenz (2026-09-17), une par grandeur. Les instantanés
    # intermédiaires forment un dégradé de densité de couleur du plus ancien au
    # plus récent ; l'état final est seul en couleur pleine et trait normal.
    for key, label, stem in (("K", "Taille K", "lorenz_capital"),
                             ("int_in", "Intérêts reçus", "lorenz_interest_received"),
                             ("nw", "Valeur nette NW (valeurs négatives ramenées à 0)", "lorenz_networth")):
        fig, axis = plt.subplots(figsize=(7.2, 6.6))
        axis.plot([0, 1], [0, 1], "--", color="gray", lw=1, label=LABELS["lorenz_equality"])
        finals = {}; shown = 0; intermediate_steps = {}; final_steps = {}
        for index, (seed, folder) in enumerate(members):
            snaps = snapshots(folder); steps = sorted(snaps)
            if not steps: continue
            color = COLORS[index % 10]; last = steps[-1]
            # Couleur sœur pour l'état final : même teinte, nettement plus
            # sombre — la courbe finale se distingue sans changer de famille.
            sister = tuple(.55 * channel for channel in mcolors.to_rgb(color))
            # Au plus douze instantanés intermédiaires, régulièrement espacés :
            # au-delà, les traits se superposent sans rien montrer de plus.
            intermediate = [steps[i] for i in np.unique(np.linspace(0, len(steps) - 2, min(12, max(1, len(steps) - 1)), dtype=int))]
            shown = len(intermediate)
            intermediate_steps[seed] = [int(step) for step in intermediate]
            final_steps[seed] = int(last)
            for position, step in enumerate(intermediate):
                result = lorenz(np.maximum(snaps[step][key], 0))
                if not result: continue
                x, y, _ = result
                fade = .16 + .5 * position / max(1, len(intermediate) - 1)
                axis.plot(x, y, color=color, lw=.7, alpha=fade, zorder=1,
                          label=LABELS["lorenz_intermediate"].format(count=len(intermediate), first=intermediate[0], last=intermediate[-1]) if position == 0 else None)
            result = lorenz(np.maximum(snaps[last][key], 0))
            if result:
                x, y, value = result; finals[seed] = value
                axis.plot(x, y, color=sister, lw=2.0, alpha=.97, zorder=3,
                          label=LABELS["lorenz_final"].format(seed_label=LABELS["seed"], seed=seed, step=last, gini=value))
        axis.set(xlabel=LABELS["cumulative_entities"], ylabel=LABELS["cumulative_share"], xlim=(0, 1), ylim=(0, 1))
        axis.grid(True, alpha=.2); axis.legend(loc="upper left")
        fig.tight_layout()
        save(fig, out / f"{stem}.png", sources=["snapshots/entities_t*.npz"],
             note=f"Courbes de Lorenz de « {label} » à chaque instantané ; trait fin et pâle pour les instantanés intermédiaires, la couleur étant d'autant plus dense que le pas est grand, trait plein et couleur sœur pour l'état final. Les pas représentés sont donnés par `intermediate_steps` et `final_step`.",
             quantity=key, quantity_label=label, final_gini=finals, intermediate_snapshots_shown=shown,
             intermediate_steps=intermediate_steps, final_step=final_steps)


def network_figure(folder: Path, out: Path, title: str):
    rows = read_csv(folder / "final_loans.csv")
    if not rows: return
    # Vue structurelle matricielle : lisible même pour des milliers de nœuds.
    lenders = np.asarray([row["lender"] for row in rows]); borrowers = np.asarray([row["borrower"] for row in rows]); q = np.asarray([row["q"] for row in rows])
    payments = q * np.asarray([row["r"] for row in rows], dtype=float)
    entities = np.unique(np.r_[lenders, borrowers])
    lend_count = {entity: int(np.sum(lenders == entity)) for entity in entities}
    borrow_count = {entity: int(np.sum(borrowers == entity)) for entity in entities}
    lend_power = {entity: float(np.sum(payments[lenders == entity])) for entity in entities}
    borrow_power = {entity: float(np.sum(payments[borrowers == entity])) for entity in entities}
    # Seuls les deux panneaux de rôles sont conservés (demande utilisateur
    # 2026-09-15 : matrice rangée par degré et histogramme des degrés retirés).
    fig_roles, roles = plt.subplots(figsize=(8, 6.8))
    fig_power, power = plt.subplots(figsize=(8, 6.8))
    fig = fig_roles

    # Distribution jointe : nombre de contrats actifs par entité, séparément en
    # tant que prêteuse et en tant qu'emprunteuse (un même contrat ne compte
    # que d'un côté ; un binôme prêteur-emprunteur récurrent compte plusieurs fois).
    lend_vals = np.asarray([lend_count[e] for e in entities]); borrow_vals = np.asarray([borrow_count[e] for e in entities])
    edges_l = np.arange(-0.5, int(lend_vals.max()) + 1.5); edges_b = np.arange(-0.5, int(borrow_vals.max()) + 1.5)
    counts2d, _, _ = np.histogram2d(borrow_vals, lend_vals, bins=(edges_b, edges_l))
    masked = np.ma.masked_where(counts2d.T == 0, counts2d.T)
    image2 = roles.pcolormesh(edges_b, edges_l, masked, cmap="magma", norm=LogNorm(vmin=1, vmax=max(1, counts2d.max())))
    fig_roles.colorbar(image2, ax=roles, label=LABELS["entities_log"])
    ols = None  # valeurs de la régression : légende simplifiée, chiffres en métadonnées
    if len(entities) >= 3 and borrow_vals.std() > 0:
        # Régression linéaire (moindres carrés ordinaires) y = a x + b.
        slope, intercept, r_value, _, stderr = stats.linregress(borrow_vals, lend_vals)
        x_line = np.array([edges_b[0], edges_b[-1]]); y_line = slope * x_line + intercept
        sign = "+" if intercept >= 0 else "−"
        ols = {"slope": float(slope), "intercept": float(intercept), "r2": float(r_value ** 2),
               "stderr": float(stderr), "n": int(len(entities))}
        roles.plot(x_line, y_line, "--", color="tab:blue", lw=1.5,
                   label=LABELS["fit_ols"].format(slope=slope, sign=sign, intercept=abs(intercept), r2=r_value ** 2))
        roles.legend(loc="upper left")
    roles.set(xlabel="Contrats en tant qu'emprunteuse", ylabel="Contrats en tant que prêteuse")
    roles.grid(True, alpha=.2)
    fig_roles.tight_layout()
    save(fig_roles, out / "loan_roles_contracts.png", sources=["final_loans.csv"],
         note="Distribution jointe du nombre de contrats actifs détenus par une entité comme prêteuse et comme emprunteuse, en fin de run, avec régression par moindres carrés ordinaires. Les coefficients de cette régression sont dans le champ `ols` (pente, ordonnée à l'origine, R², erreur-type).",
         ols=ols,
         entities=int(len(entities)), loans=int(len(rows)))

    # Même distribution jointe, mais en puissance (J/pas) plutôt qu'en nombre de
    # contrats : paiement d'intérêt courant par prêt = q x r (cf. model.py,
    # payment = ratio * principal * rate). Échelle log-log au centre, donc
    # limitée aux entités à la fois prêteuses et emprunteuses actives ; les
    # rôles purs (puissance nulle sur un axe, non représentable en log) sont
    # reportés sur deux bandes marginales contiguës aux axes, avec un
    # découpage plus grossier (moins de classes, seule une dimension est peuplée).
    lend_p = np.asarray([lend_power[e] for e in entities]); borrow_p = np.asarray([borrow_power[e] for e in entities])
    dual = (lend_p > 0) & (borrow_p > 0)
    pure_lender = (lend_p > 0) & (borrow_p == 0)
    pure_borrower = (borrow_p > 0) & (lend_p == 0)
    inactive = int(((lend_p == 0) & (borrow_p == 0)).sum())
    if dual.sum() >= 5:
        divider = make_axes_locatable(power)
        ax_left = divider.append_axes("left", size="20%", pad=0.06, sharey=power)
        ax_bottom = divider.append_axes("bottom", size="20%", pad=0.06, sharex=power)
        cax = divider.append_axes("right", size="4%", pad=0.12)

        image3 = power.hexbin(borrow_p[dual], lend_p[dual], gridsize=40, mincnt=1, bins="log", xscale="log", yscale="log", cmap="magma")
        fig_power.colorbar(image3, cax=cax, label=LABELS["entities_log"])
        # Diagonale y = x (demande utilisateur 2026-09-17) : repère discret de
        # l'entité qui reverse en intérêts exactement ce qu'elle en reçoit.
        # Au-dessus, une entité est prêteuse nette ; au-dessous, emprunteuse nette.
        # Les ÉCHELLES RESTENT LIBRES (2026-09-17) : la droite est découpée sur
        # les limites déjà fixées par les données, puis celles-ci sont
        # restaurées. Tracer le segment de bout en bout des deux séries, comme
        # auparavant, étirait les deux axes sur une plage commune et faisait de
        # y=x une bissectrice parfaite du cadre — un artefact de cadrage.
        x_limits, y_limits = power.get_xlim(), power.get_ylim()
        low, high = max(x_limits[0], y_limits[0]), min(x_limits[1], y_limits[1])
        if high > low:
            power.plot((low, high), (low, high), "--", color="#888888", lw=1.0, alpha=.65,
                       zorder=1, label=LABELS["diagonal_equal_power"])
            power.legend(loc="upper left", framealpha=.6)
        power.set_xlim(*x_limits); power.set_ylim(*y_limits)

        # Bornes aux quantiles (même famille que _quantile_edges/adaptive_hist,
        # plafonnées à 10 bins pour ces panneaux étroits) au lieu d'un
        # np.logspace uniforme — remplace l'ancien _coarse_log_edges, qui
        # avait le même défaut que temporal_density() (cf. docstring de ce
        # module, corrigé le 2026-08-09).
        # Bandes marginales : bins de largeur UNIFORME en log (sqrt(n), 3 à
        # 10 bins) et non plus aux quantiles. Des bins équipeuplés donnent
        # par construction des effectifs identiques, donc un histogramme plat
        # qui n'affiche plus que le nombre de bins (constaté 2026-09-15 sur
        # rho_0.25/seed1 : 190 emprunteuses pures → un seul bloc uniforme).
        def _log_edges(values):
            values = values[values > 0]
            if len(values) == 0: return None
            low, high = values.min(), values.max()
            if low == high: low, high = low / 1.5, high * 1.5
            return np.logspace(np.log10(low), np.log10(high) + 1e-9, max(3, min(10, int(np.sqrt(len(values))))) + 1)

        edges = _log_edges(lend_p[pure_lender])
        if edges is not None:
            counts, _ = np.histogram(lend_p[pure_lender], bins=edges)
            ax_left.barh(edges[:-1], counts, height=np.diff(edges), align="edge", color="#7f2aa3", alpha=.75)
        ax_left.set_yscale("log"); ax_left.invert_xaxis()
        ax_left.set_ylabel("Puissance prêtée Σq·r (J/pas)")
        ax_left.set_title(f"Prêteuses\npures n={int(pure_lender.sum())}")
        ax_left.xaxis.set_major_locator(plt.MaxNLocator(2, integer=True))
        # Effectifs des entités pures lisibles sur les bandes marginales, et
        # grille en transparence (demande utilisateur 2026-09-15).
        ax_left.tick_params(labelbottom=True)

        edges = _log_edges(borrow_p[pure_borrower])
        if edges is not None:
            counts, _ = np.histogram(borrow_p[pure_borrower], bins=edges)
            ax_bottom.bar(edges[:-1], counts, width=np.diff(edges), align="edge", color="#2ca02c", alpha=.75)
        ax_bottom.set_xscale("log"); ax_bottom.invert_yaxis()
        ax_bottom.set_xlabel("Puissance empruntée Σq·r (J/pas)"); ax_bottom.set_ylabel("Entités")
        ax_bottom.text(.01, .08, f"Emprunteuses pures n={int(pure_borrower.sum())}", transform=ax_bottom.transAxes)
        ax_bottom.yaxis.set_major_locator(plt.MaxNLocator(3, integer=True))
        ax_bottom.tick_params(labelleft=True)
        for panel in (ax_left, ax_bottom, power): panel.grid(True, which="both", alpha=.2)

        power.tick_params(labelleft=False, labelbottom=False)
        fig_power.tight_layout()
        save(fig_power, out / "loan_roles_power.png", sources=["final_loans.csv"],
             note="Puissance d'intérêt agrégée (Σq·r, J/pas) d'une entité comme prêteuse et comme emprunteuse, en fin de run. Le centre en log-log ne peut montrer que les entités des deux rôles à la fois ; les rôles purs sont reportés sur les deux bandes marginales.",
             dual_role=int(dual.sum()), pure_lenders=int(pure_lender.sum()), pure_borrowers=int(pure_borrower.sum()),
             inactive=int(inactive), entities=int(len(entities)))
    else:
        plt.close(fig_power)


def individual_summary(folder: Path):
    """Premier passage en flux : par entité, nombre de pas observés et capital
    maximal. Ne retient que des nombres — jamais les lignes — donc quelques
    dizaines de milliers d'entrées au lieu de plusieurs gigaoctets."""
    steps = defaultdict(int); peak = defaultdict(float)
    for row in iter_csv(folder / "individual_series.csv.gz"):
        entity = int(row["id"]); steps[entity] += 1
        value = float(row["K"] or 0.0)
        if value > peak[entity]: peak[entity] = value
    return steps, peak


def individual_history(folder: Path, keep=None):
    """Second passage en flux : ne conserve les lignes QUE des entités
    demandées (`keep`). Charger tout le fichier, comme avant le 2026-09-17,
    tuait la figure des vies individuelles sur les runs à individual_every=1."""
    history = defaultdict(list)
    for row in iter_csv(folder / "individual_series.csv.gz"):
        entity = int(row["id"])
        if keep is not None and entity not in keep: continue
        history[entity].append(row)
    for rows in history.values(): rows.sort(key=lambda row: row["t"])
    return history


def _life_legend(balance, flow):
    """Légende unique, SORTIE du cadre (2026-09-17). À taille doublée, les deux
    légendes posées dans le premier panneau recouvraient ses courbes et son
    étiquette d'entité. Les dix panneaux partageant exactement le même codage,
    une seule légende suffit — et ne masque plus rien, ce qui vaut mieux que de
    rendre les données translucides sous elle.
    EN COLONNE, SUR LE CÔTÉ (demande utilisateur 2026-09-17) : en une seule
    ligne au-dessus, les six entrées étiraient la figure en largeur et
    écrasaient les panneaux ; en colonne à droite, chaque entrée se lit sur une
    ligne et la hauteur disponible est celle de la figure entière.
    Exige une mise en page contrainte (`constrained_layout`), seule compatible
    avec les positions « outside » de matplotlib."""
    handles, labels = [], []
    for axis in (balance, flow):
        axis_handles, axis_labels = axis.get_legend_handles_labels()
        handles += axis_handles; labels += axis_labels
    balance.figure.legend(handles, labels, loc="outside right upper",
                          ncol=1, framealpha=.6)


def _life_block(balance, flow, rows, delta=0.0, legend=True):
    """Bilan et flux d'une entité. L'érosion du capital et le flux net ont été
    ajoutés le 2026-09-17. L'érosion n'est PAS une colonne enregistrée : elle
    est reconstruite comme δ·K(t) à partir du δ de config.json (règle du
    moteur, `model.py` : `depreciated += config.delta * capital`). Le choc
    log-normal de moyenne 1 n'y est pas compté : ce n'est pas une érosion."""
    t = np.asarray([row["t"] for row in rows]); k = np.asarray([row["K"] for row in rows]); claims = np.asarray([row["claims"] for row in rows]); debts = np.asarray([row["debts"] for row in rows]); nw = np.asarray([row["nw"] for row in rows])
    prod = np.asarray([row["prod"] for row in rows]); received = np.asarray([row["int_in"] for row in rows]); paid = np.asarray([row["int_out"] for row in rows])
    erosion = delta * k
    balance.stackplot(t, k, claims, labels=("Capital K", "Créances"), colors=("#4c78a8", "#f2cf5b"), alpha=.72)
    balance.fill_between(t, 0, -debts, color="#e45756", alpha=.58, label="Dettes (−)")
    balance.plot(t, nw, color="black", lw=1.25, label="Valeur nette"); balance.axhline(0, color="black", lw=.7); balance.set_ylabel("Bilan (J)")
    flow.fill_between(t, 0, prod, color="#54a24b", alpha=.65, label=LABELS["life_production"])
    flow.fill_between(t, prod, prod + received, color="#4c78a8", alpha=.65, label=LABELS["life_interest_in"])
    flow.fill_between(t, 0, -paid, color="#e45756", alpha=.65, label=LABELS["life_interest_out"])
    flow.fill_between(t, -paid, -paid - erosion, color="#8a6d3b", alpha=.6, label=LABELS["life_erosion"].format(delta=delta))
    flow.plot(t, prod + received - paid - erosion, color="black", lw=1.1, label=LABELS["life_net_flow"])
    flow.axhline(0, color="black", lw=.7); flow.set_ylabel("Flux (J/pas)"); flow.set_xlabel(LABELS["step"])
    for axis in (balance, flow): axis.set_xlim(t.min(), t.max()); axis.grid(True, alpha=.18)
    if legend: _life_legend(balance, flow)


def entity_lives(folder: Path, out: Path, title: str):
    # Deux passages en flux (2026-09-17) : le premier ne calcule que des
    # nombres pour choisir les dix entités, le second ne relit que leurs
    # lignes. Sélection strictement identique à l'ancienne version, qui
    # gardait tout le fichier en mémoire.
    steps_seen, peak_k = individual_summary(folder)
    eligible = [entity for entity, count in steps_seen.items() if count >= 3]
    if not eligible: return
    births = {int(row["id"]): row["birth_t"] for row in read_csv(folder / "entities.csv")}
    early = sorted(eligible, key=lambda entity: births.get(entity, 0))[:4]
    largest = sorted(eligible, key=lambda entity: peak_k[entity], reverse=True)[:4]
    longest = sorted(eligible, key=lambda entity: steps_seen[entity], reverse=True)[:4]
    selected = list(dict.fromkeys(early + largest + longest))[:10]
    history = individual_history(folder, keep=set(selected))
    delta = float(config(folder).get("delta", 0.0))
    selection = {"premieres_nees": early, "plus_grosses": largest, "plus_longues_vies": longest, "retenues": selected}
    fig = plt.figure(figsize=(22, 9), constrained_layout=True); grid = fig.add_gridspec(2, 5)
    for index, entity in enumerate(selected):
        inner = grid[index // 5, index % 5].subgridspec(2, 1, hspace=.05)
        balance = fig.add_subplot(inner[0]); flow = fig.add_subplot(inner[1], sharex=balance)
        _life_block(balance, flow, history[entity], delta=delta, legend=index == 0)
        # Le numéro d'entité reste dessiné : sans lui, un panneau d'une grille
        # de dix n'est plus identifiable. Ce n'est pas un titre de figure.
        balance.annotate(f"Entité {entity}", (.02, .95), xycoords="axes fraction", va="top")
        balance.tick_params(labelbottom=False)
    save(fig, out / "entity_lives_overview.png", sources=["individual_series.csv.gz", "entities.csv", "config.json"],
         note="Bilan et flux de dix entités suivies pas à pas : quatre parmi les premières nées, quatre parmi les plus grosses, quatre parmi les plus longues vies, doublons retirés. L'érosion δ·K est reconstruite depuis δ ; le flux net vaut production + intérêts reçus − intérêts payés − érosion.",
         delta=delta, selection=selection)
    detail = out / "detail_vie_entites"
    if detail.exists(): shutil.rmtree(detail)
    detail.mkdir(parents=True)
    for entity in selected:
        # Mise en page contrainte (et non `tight_layout`) : la légende unique
        # est placée hors du cadre, ce que seules les positions « outside »
        # permettent, elles-mêmes réservées à `constrained_layout`.
        fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True, constrained_layout=True)
        _life_block(*axes, history[entity], delta=delta)
        save(fig, detail / f"entity_{entity}.png", sources=["individual_series.csv.gz", "config.json"],
             note="Bilan et flux d'une entité sur la fenêtre exacte de sa vie observée.",
             entity_id=int(entity), delta=delta, steps_observed=int(len(history[entity])))


def _adaptive_horizon(prepared, quantile=0.999, floor=15, cap_fraction=0.4):
    """Fenêtre de vie restante calée sur l'échelle de vie réelle du run,
    jamais une constante fixe : 99,9e percentile des âges au décès observés
    après burn-in (toutes graines confondues), plafonné pour laisser assez
    de pas de recul aux landmarks (final_t - horizon doit rester net du burn-in).
    Un quantile aussi extrême exige plus de décès pour ne pas n'être qu'un
    maximum bruité — seuil minimal proportionnel à 1/(1-quantile)."""
    pooled_ages = [age for *_, ages in prepared for age in ages]
    caps = [max(floor, int(cap_fraction * max(final_t - burn, 0))) for _, _, burn, final_t, _, _ in prepared]
    cap = min(caps) if caps else 100
    min_samples = max(30, int(math.ceil(5.0 / max(1e-6, 1 - quantile))))
    if len(pooled_ages) >= min_samples:
        horizon = int(round(min(float(np.quantile(pooled_ages, quantile)), cap)))
    else:
        # Pas assez de décès pour estimer l'échelle à ce quantile : on ne
        # retombe jamais sur une constante arbitraire, on garde la fraction
        # du run disponible.
        horizon = cap
    return max(floor, horizon)


def landmark_records(members, horizon=None):
    prepared = []
    for seed, folder in members:
        cfg = config(folder); burn = int(cfg.get("T", 0)) // 4
        summary_path = folder / "summary.json"
        final_t = int(json.loads(summary_path.read_text()).get("t_final", cfg.get("T", 0))) if summary_path.exists() else int(cfg.get("T", 0))
        deaths_rows = read_csv(folder / "deaths.csv")
        deaths = {int(row["id"]): int(row["t"]) for row in deaths_rows}
        ages = [row["age"] for row in deaths_rows if row.get("age", 0) > 0 and row.get("t", 0) >= burn]
        prepared.append((seed, folder, burn, final_t, deaths, ages))

    if horizon is None:
        horizon = _adaptive_horizon(prepared)

    records = []
    for seed, folder, burn, final_t, deaths, _ in prepared:
        for step, snap in snapshots(folder).items():
            if step < burn or step > final_t - horizon: continue
            weight = 1 / max(1, len(snap["id"]))
            for index, raw_id in enumerate(snap["id"]):
                entity = int(raw_id); assets = float(snap["K"][index] + snap["claims"][index]); leverage = float(snap["debts"][index] / assets) if assets > 0 else 0
                death = deaths.get(entity); remaining = death - step if death is not None and death > step else horizon
                records.append((float(snap["K"][index]), leverage, float(np.clip(remaining, 0, horizon)), bool(death and 0 < remaining <= horizon), seed, weight))
    return records, horizon


def instantaneous_life(members, out: Path, title: str, horizon=None):
    records, horizon = landmark_records(members, horizon)
    if len(records) < 100: return
    for column, log_x, xlabel, filename in (
        (0, True, "Taille instantanée K(t) (J)", "instantaneous_life_expectancy_by_size.png"),
        (1, False, "Ratio instantané dettes/actifs", "instantaneous_life_expectancy_by_leverage.png"),
    ):
        x = np.asarray([row[column] for row in records]); y = np.asarray([row[2] for row in records]); weights = np.asarray([row[5] for row in records])
        valid = np.isfinite(x) & (x > 0 if log_x else x >= 0); x=x[valid]; y=y[valid]; weights=weights[valid]
        if len(x) < 100: continue
        # Résolution adaptative (règle sqrt(n), comme adaptive_hist) plutôt qu'un
        # nombre de classes fixe : le plancher de 20 observations/classe reste le
        # garde-fou de fiabilité, indépendant de la finesse de découpage.
        n_bins = max(8, min(50, int(round(math.sqrt(len(x))))))
        transformed = np.log10(x) if log_x else x; edges = np.unique(np.quantile(transformed, np.linspace(0, 1, n_bins + 1)))
        centres=[]; means=[]; q10=[]; q90=[]
        for index in range(len(edges)-1):
            inside=(transformed >= edges[index]) & (transformed <= edges[index+1] if index == len(edges)-2 else transformed < edges[index+1])
            if inside.sum() < 20: continue
            values=y[inside]; w=weights[inside]; order=np.argsort(values); values=values[order]; w=w[order]/w.sum(); cumulative=np.cumsum(w)
            centres.append(np.median(x[inside])); means.append(np.average(values, weights=w)); q10.append(np.interp(.1, cumulative, values)); q90.append(np.interp(.9, cumulative, values))
        if not centres: continue
        fig, (heat, mean_axis) = plt.subplots(1, 2, figsize=(14, 5.6))
        density = heat.hexbin(x, y, gridsize=60, mincnt=1, bins="log", xscale="log" if log_x else "linear", cmap="YlOrRd")
        fig.colorbar(density, ax=heat, label="Effectif (log)"); positions=np.unique(np.linspace(0, len(x)-1, min(25000, len(x)), dtype=int)); heat.scatter(x[positions], y[positions], s=.35, alpha=.06, color="#3f0000")
        heat.set(xlabel=xlabel, ylabel=f"Vie restante, tronquée à {horizon} pas", title=f"Tous les landmarks (n={len(x):,})")
        centres=np.asarray(centres); means=np.asarray(means); q10=np.asarray(q10); q90=np.asarray(q90)
        mean_axis.fill_between(centres, q10, q90, alpha=.2); mean_axis.plot(centres, means, "o-", color="black", ms=4, label="Espérance restreinte")
        if log_x: mean_axis.set_xscale("log")
        mean_axis.set(xlabel=xlabel, ylabel="Vie restante moyenne (pas)", ylim=(0, horizon*1.03), title="Moyenne conditionnelle par classes équipopulées"); mean_axis.legend(); mean_axis.grid(True, alpha=.2)
        heat.set_title(""); mean_axis.set_title("")
        fig.tight_layout()
        save(fig, out / filename, sources=["snapshots/entities_t*.npz", "deaths.csv", "summary.json"],
             note="Vie restante d'une entité, tronquée à un horizon H adaptatif (≈99,9e percentile des âges au décès après burn-in, plafonné par la marge de recul disponible). À gauche : tous les landmarks. À droite : moyenne conditionnelle par classes équipeuplées, avec bande interdécile.",
             horizon_steps=int(horizon), variable=xlabel, landmarks=int(len(x)))


def lifespan(members, out: Path, title: str):
    rows=[]
    for seed, folder in members:
        dead_ids=set()
        for row in read_csv(folder / "deaths.csv"):
            dead_ids.add(int(row["id"])); assets=row["K"]+row["claims"]; rows.append((row["K"], row["debts"]/assets if assets>0 else 0, row["age"], False, seed))
        snaps=snapshots(folder)
        if not snaps: continue
        final_t=max(snaps); snap=snaps[final_t]
        births={int(row["id"]): row for row in read_csv(folder / "entities.csv")}
        for index, raw_id in enumerate(snap["id"]):
            entity=int(raw_id); data=births.get(entity)
            if not data or entity in dead_ids or not data["alive_final"]: continue
            assets=float(snap["K"][index]+snap["claims"][index]); rows.append((float(snap["K"][index]), float(snap["debts"][index]/assets) if assets>0 else 0, final_t-data["birth_t"], True, seed))
    if len(rows)<5: return
    fig, axes=plt.subplots(1,2,figsize=(13,5.5))
    for axis, (column, xlabel, logx) in zip(axes, ((0,"Taille terminale K (J)",True),(1,"Ratio dettes/actifs terminal",False))):
        values=np.asarray([(row[column],row[2]) for row in rows if row[column]>0 or not logx])
        image=axis.hexbin(values[:,0],values[:,1],gridsize=65,mincnt=1,bins="log",xscale="log" if logx else "linear",cmap="YlOrRd")
        fig.colorbar(image,ax=axis,label="Effectif (log)")
        dead=np.asarray([(row[column],row[2]) for row in rows if not row[3] and (row[column]>0 or not logx)])
        alive=np.asarray([(row[column],row[2]) for row in rows if row[3] and (row[column]>0 or not logx)])
        if len(dead): axis.scatter(dead[:25000,0],dead[:25000,1],s=.35,alpha=.06,color="#4a0000",label="décès")
        if len(alive): axis.scatter(alive[:25000,0],alive[:25000,1],s=.8,alpha=.15,color="#006d2c",marker="^",label="censurées")
        axis.set(xlabel=xlabel,ylabel="Durée de vie (pas)"); axis.legend(); axis.grid(True,alpha=.16)
    fig.tight_layout(); save(fig, out / "lifespan_analysis.png", sources=["deaths.csv", "entities.csv", "snapshots/entities_t*.npz"],
         note="Durée de vie selon l'état terminal : décès observés et entités censurées (encore vivantes en fin de run).", n_records=int(len(rows)))


def soc_figures(folder: Path, out: Path, title: str):
    avalanches=read_csv(folder/"avalanches.csv")
    if avalanches:
        size=np.asarray([row["size"] for row in avalanches]); roots=np.asarray([row["n_roots"] for row in avalanches]); depth=np.asarray([row["depth"] for row in avalanches])
        fig,axes=plt.subplots(1,2,figsize=(12,5))
        # Deux figures séparées (2026-09-17). Isocourbes y = k/x tracées en
        # ARRIÈRE-PLAN et très peu marquées : elles servent de repère, pas de
        # message. Une avalanche à k racines tombe sur la k-ième courbe.
        fig_roots,ax_roots=plt.subplots(figsize=(8.5,5.8))
        x_grid=np.logspace(0,np.log10(max(2,size.max())),200); k_max=int(min(max(1,roots.max()),30))
        for k in range(1,k_max+1):
            keep=x_grid>=k
            ax_roots.plot(x_grid[keep],k/x_grid[keep],color="black",lw=.7,alpha=.13,zorder=0)
            if k<=5 or k%5==0:
                ax_roots.annotate(f"{k}/x",(k,1),xytext=(0,4),textcoords="offset points",fontsize=6,alpha=.35,ha="center",va="bottom",zorder=0)
        image=ax_roots.hexbin(size,roots/size,gridsize=45,mincnt=1,bins="log",xscale="log",cmap="viridis",zorder=2)
        fig_roots.colorbar(image,ax=ax_roots,label=LABELS["count_log"])
        ax_roots.set(xlabel="Taille d'avalanche",ylabel="Racines / taille")
        fig_roots.tight_layout()
        save(fig_roots,out/"avalanche_roots_share.png",sources=["avalanches.csv"],
             note="Part des faillites racines dans une avalanche, selon sa taille. Les courbes grises en arrière-plan sont les isocourbes y = k/x : une avalanche à k racines exactement tombe sur la k-ième.",
             isocurves_k_max=k_max, avalanches=int(len(avalanches)))
        fig_depth,ax_depth=plt.subplots(figsize=(8.5,5.8))
        image=ax_depth.hexbin(size,depth,gridsize=45,mincnt=1,bins="log",xscale="log",cmap="magma")
        fig_depth.colorbar(image,ax=ax_depth,label=LABELS["count_log"])
        ax_depth.set(xlabel="Taille d'avalanche",ylabel="Profondeur causale")
        fig_depth.tight_layout()
        save(fig_depth,out/"avalanche_depth.png",sources=["avalanches.csv"],
             note="Profondeur causale d'une avalanche selon sa taille.", avalanches=int(len(avalanches)))
        plt.close(fig)
    snaps=snapshots(folder)
    if snaps:
        incomes=np.concatenate([np.asarray(snap["income"])[np.asarray(snap["income"])>0] for snap in snaps.values()])
        if len(incomes)>2:
            fig,axis=plt.subplots(figsize=(9,5.5)); _plot_adaptive(axis,incomes,"#ff7f0e","empirique"); axis.set(xscale="log",yscale="log",xlabel="Revenu brut (J/pas)",ylabel=LABELS["density"]); axis.legend(); axis.grid(True,which="both",alpha=.2); fig.tight_layout(); save(fig,out/"soc_revenue_fits.png",sources=["snapshots/entities_t*.npz"],note="Densité empirique du revenu brut, tous instantanés confondus. Aucun ajustement.",n_values=int(len(incomes)))
    deaths=read_csv(folder/"deaths.csv")
    ages=np.asarray([row["age"] for row in deaths if row["age"]>0])
    if len(ages)>5:
        # Fit unique log-normal (retenu sur la campagne de sensibilité) : pas
        # de Weibull ni d'exponentielle, qui n'apportent rien de plus ici.
        # Axe des abscisses restreint aux 99 % centraux (quantiles 0,5 % et
        # 99,5 %, demande utilisateur 2026-09-15). Le fit et la normalisation
        # de la densité portent toujours sur TOUS les âges : les poids 1/n
        # rendent la hauteur des barres identique à celle d'un histogramme
        # complet ; seules les classes hors fenêtre ne sont pas dessinées.
        lo_q,hi_q=np.quantile(ages,[.005,.995])
        window=(ages>=lo_q)&(ages<=hi_q)
        # Âges entiers : bornes aux demi-entiers et largeur entière, sinon des
        # classes vides alternent avec des pleines (dents de peigne).
        width=max(1,int(round(np.diff(np.histogram_bin_edges(ages[window],bins="auto"))[0])))
        bin_edges=np.arange(math.floor(lo_q)-.5,hi_q+width,width)
        fig,axis=plt.subplots(figsize=(9,5.5))
        counts,edges,_=axis.hist(ages[window],bins=bin_edges,weights=np.full(int(window.sum()),1/(len(ages)*np.diff(bin_edges)[0])),alpha=.35,label="empirique")
        axis.set_xlim(lo_q,hi_q)
        grid=np.linspace(max(.01,lo_q),hi_q,250)
        shape,loc,scale=stats.lognorm.fit(ages,floc=0)
        # R² du fit : accord densité empirique / densité log-normale, bin à bin
        # (mêmes classes que l'histogramme), pas un R² de régression linéaire.
        # R² calculé sur l'histogramme COMPLET (classes "auto" sur tous les
        # âges, comme avant la restriction d'affichage) : la restriction de
        # l'axe ne doit pas faire bouger le nombre annoncé.
        counts,edges=np.histogram(ages,bins="auto",density=True)
        centres=(edges[:-1]+edges[1:])/2; fitted=stats.lognorm.pdf(centres,shape,loc,scale)
        ss_res=float(np.sum((counts-fitted)**2)); ss_tot=float(np.sum((counts-counts.mean())**2))
        r2=1-ss_res/ss_tot if ss_tot>0 else float("nan")
        axis.plot(grid,stats.lognorm.pdf(grid,shape,loc,scale),color="#d62728",lw=1.6,label=LABELS["fit_lognormal"].format(mu=math.log(scale), sigma=shape, r2=r2))
        axis.set(xlabel="Âge au décès (pas)",ylabel=LABELS["density"]); axis.legend(); axis.grid(True,alpha=.2); fig.tight_layout(); save(fig,out/"soc_age_at_death_fits.png",sources=["deaths.csv"],note="Distribution des âges au décès et ajustement log-normal sur tous les âges ; l'axe montre les 99 % centraux.",lognormal={"mu":float(math.log(scale)),"sigma":float(shape),"r2":float(r2)},n_deaths=int(len(ages)),display_quantiles=[0.005,0.995])
    if len(snaps)>=2:
        steps=sorted(snaps); first=snaps[steps[0]]; base=set(first["id"][np.asarray(first["nw"])>=np.quantile(first["nw"],.9)].astype(int)); x=[]; persistence=[]
        for step in steps:
            snap=snaps[step]; top=set(snap["id"][np.asarray(snap["nw"])>=np.quantile(snap["nw"],.9)].astype(int)); x.append(step-steps[0]); persistence.append(len(base&top)/max(1,len(base)))
        # Régression y = A·exp(-t/τ)+B (forme retenue le 2026-09-17). C'est la
        # même courbe que le A(1-exp(-t/τ))+B du 2026-09-15, simplement
        # reparamétrée — A' = -A, B' = A+B — donc τ, son erreur-type et le R²
        # sont inchangés (vérifié sur rho_0.25/seed1 : τ=664,4 et R²=0,99151
        # dans les deux écritures) ; seule l'écriture est plus directe.
        # τ est le temps caractéristique de perte de mémoire de l'état initial.
        # A+B = y(0) et B = plancher asymptotique (A>0 pour une persistance
        # décroissante). Moindres carrés non linéaires, sans pondération, sur
        # les données au-delà des 200 premiers pas (le tout début est un régime
        # transitoire qui tirait le fit). Repères 3τ/5τ et burn-in retirés :
        # le burn-in peut changer, il n'a pas sa place dans la figure.
        x=np.asarray(x,dtype=float); persistence=np.asarray(persistence,dtype=float)
        # `fit_from` écarte le transitoire initial. C'était 200 pas EN DUR —
        # constante calibrée sur les runs M4.3 de 8 000 pas, où elle vaut 2,5 %
        # de l'étendue des instantanés. Sur un run dont les instantanés couvrent
        # 240 pas, elle en excluait 83 % et ne laissait que trois points, tous
        # nuls : τ se retrouvait épinglé sur sa borne et R² valait nan, le tout
        # présenté avec une légende d'ajustement. 80 des 125 ajustements de la
        # campagne du 2026-09-17 étaient dans ce cas.
        #
        # On descend donc une échelle et on retient le PLUS GRAND seuil qui
        # laisse encore de quoi ajuster : au moins quatre points ET une variance
        # non nulle. Les runs qui allaient bien gardent 200 et ne bougent pas.
        #
        # Une fraction de l'étendue (2,5 %) avait été essayée d'abord. Elle
        # réparait autant, mais DÉPLAÇAIT 33 ajustements déjà sains — 28 % en
        # médiane, jusqu'à +259 %, avec un R² qui baissait (0,993 → 0,836) :
        # sur ces runs-là, le seuil de 200 faisait un vrai travail d'exclusion
        # du transitoire. L'échelle laisse les 44 sains rigoureusement
        # inchangés et n'en répare que 45 autres. Vérifié run par run.
        fit_from=None
        for seuil in (200.0,100.0,50.0,25.0,10.0,5.0):
            fenetre=x>=seuil
            if int(fenetre.sum())>=4 and float(np.ptp(persistence[fenetre]))>0:
                fit_from=seuil; break
        ajustable=fit_from is not None
        if not ajustable: fit_from=200.0
        used=(x>=fit_from) if ajustable else np.zeros(len(x),dtype=bool)
        fig,axis=plt.subplots(figsize=(10,5.8))
        axis.plot(x[~used],persistence[~used],"o",ms=3.2,mfc="none",color="#4c78a8",alpha=.55,label=LABELS["renewal_excluded"].format(fit_from=fit_from))
        axis.plot(x[used],persistence[used],"o",ms=3.5,color="#1f77b4",label=LABELS["renewal_measured"].format(fit_from=fit_from))
        def relaxation(t,A,tau,B): return A*np.exp(-t/tau)+B
        span=max(float(x.max()),1.0); tau=None; meta={}
        try:
            if not ajustable:
                raise ValueError("aucun seuil ne laisse de fenêtre ajustable : τ n'est pas dérivable ici")
            (A,tau,B),cov=curve_fit(relaxation,x[used],persistence[used],p0=(float(persistence[used][0]-persistence[-1]),span/10,float(persistence[-1])),bounds=((-2,1e-3,-1),(2,50*span,2)),maxfev=20000)
            fitted=relaxation(x[used],A,tau,B); values=persistence[used]
            ss_tot=float(np.sum((values-values.mean())**2)); r2=1-float(np.sum((values-fitted)**2))/ss_tot if ss_tot>0 else float("nan")
            tau_err=float(np.sqrt(cov[1,1])) if np.isfinite(cov[1,1]) else float("nan")
            # Trois refus portant sur le RÉSULTAT et non sur la fenêtre
            # (2026-09-19). Un ajustement peut converger, afficher un R²
            # flatteur, et ne rien mesurer. Trois pannes distinctes :
            #   - erreur-type ≥ τ : τ n'est pas contraint. Vu ±15 261 pour
            #     τ=1 381, avec R²=0,887 ;
            #   - τ > étendue observée : l'exponentielle n'a pas décru dans la
            #     fenêtre ; τ est extrapolé hors de ce que les données disent.
            #     Vu τ=6 613 sur 1 900 pas observés ;
            #   - R² < 0,5 : l'ajustement ne décrit pas les points (vu 0,241).
            # Sur les 90 ajustements de la campagne du 2026-09-19, ces règles en
            # refusent 3 et laissent les 87 autres rigoureusement intacts, dont
            # tous les τ de référence M4.3 (501 à 1 457, erreurs-types de 11 à
            # 36). Mieux vaut pas de τ qu'un τ que la mesure ne soutient pas.
            if not np.isfinite(tau_err) or tau_err>=tau:
                raise ValueError(f"τ non contraint : erreur-type {tau_err:.1f} pour τ={tau:.1f}")
            if tau>span:
                raise ValueError(f"τ={tau:.1f} dépasse l'étendue observée ({span:.0f} pas) : extrapolation")
            if r2<0.5:
                raise ValueError(f"ajustement trop mauvais : R²={r2:.3f}")
            grid=np.linspace(fit_from,span,400)
            meta={"tau":float(tau),"tau_stderr":float(tau_err),"A":float(A),"B":float(B),"r2":float(r2)}
            axis.plot(grid,relaxation(grid,A,tau,B),"-",color="#d62728",lw=1.6,label=LABELS["fit_relaxation"].format(**meta))
            # Prolongement sous le seuil, en pointillés : l'ajustement n'y a
            # pas été calculé, mais l'écart avec les points y est visible.
            early=np.linspace(0,fit_from,120)
            axis.plot(early,relaxation(early,A,tau,B),":",color="#d62728",lw=1.4,alpha=.85,label=LABELS["fit_relaxation_extrapolated"])
            axis.axvline(tau,color="#7f2aa3",ls=":",lw=1.0,alpha=.8,label=LABELS["renewal_tau"].format(tau=tau))
        except (RuntimeError,ValueError) as exc:
            meta={"error":str(exc)}
        axis.set(xlabel="Décalage depuis le premier instantané (pas)",ylabel="Part du top décile initial (NW) encore présente",ylim=(0,1.03)); axis.grid(True,alpha=.2); axis.legend(); fig.tight_layout()
        save(fig,out/"soc_top_decile_renewal.png",sources=["snapshots/entities_t*.npz"],
             note="Part des entités du décile supérieur de valeur nette du premier instantané encore présentes dans ce décile au fil du temps, et ajustement exponentiel dont τ est le temps caractéristique de perte de mémoire de l'état initial.",
             fit_from_step=fit_from, first_snapshot=int(steps[0]), fit=meta)


def empirical_revenue(members, out: Path, title: str, filename="revenue_fits.png"):
    fig,axis=plt.subplots(figsize=(9.5,6)); plotted=False
    for index,(seed,folder) in enumerate(members):
        snaps=snapshots(folder)
        values=np.concatenate([np.asarray(snap["income"])[np.asarray(snap["income"])>0] for snap in snaps.values()]) if snaps else np.asarray([])
        if len(values)>2:
            _plot_adaptive(axis,values,COLORS[index%10],f"{LABELS['seed']} {seed}"); plotted=True
    if plotted:
        axis.set(xscale="log",yscale="log",xlabel="Revenu brut (J/pas)",ylabel=LABELS["density"]); axis.legend(); axis.grid(True,which="both",alpha=.2); fig.tight_layout(); save(fig,out/filename,sources=["snapshots/entities_t*.npz"],note="Densité empirique du revenu brut, plusieurs graines superposées. Aucun ajustement.")
    else: plt.close(fig)


def volume_pareto(members, out: Path, title: str):
    """Volumes d'avalanches, plusieurs graines superposées, ajustement de
    Pareto sur la branche descendante — même convention que la figure de run
    `avalanche_volume_density.png` (2026-09-17 : la dPlN de la branche
    descendante est remplacée par une Pareto, cf. `fit_pareto_tail`)."""
    fig,axis=plt.subplots(figsize=(10,6)); plotted=False; fits={}
    for index,(seed,folder) in enumerate(members):
        _,_,volumes=avalanche_samples(folder)
        if len(volumes)<2: continue
        histogram=_plot_adaptive(axis,volumes,COLORS[index%10],f"{LABELS['seed']} {seed}")
        if histogram:
            fit=_plot_pareto_tail(axis,volumes,histogram,COLORS[index%10],prefix=f"{LABELS['seed']} {seed} — ")
            if fit: fits[f"seed_{seed}"]=fit
        plotted=True
    if plotted:
        axis.set(xscale="log",yscale="log",xlabel="Volume (pertes de créances, J)",ylabel=LABELS["density"]); axis.legend(); axis.grid(True,which="both",alpha=.2); fig.tight_layout()
        save(fig,out/"volume_pareto.png",sources=["avalanches.csv"],
             note="Densité des volumes d'avalanches (s≥2), graines superposées ; Pareto ajustée sur la branche descendante (méthode Clauset, α exposant de densité).",
             pareto_fits=fits)
    else: plt.close(fig)


def generate_run(folder: Path, title: str, out: Path | None = None) -> list[str]:
    # `out` permet d'écrire ailleurs que dans folder/figures (aperçu sans
    # écraser les figures en place). `describe_run` renseigne les métadonnées
    # communes à toutes les figures du run : depuis 2026-09-17, les figures
    # n'ont plus de titre dessiné, c'est là que leur identité est écrite.
    folder=Path(folder); out=Path(out) if out is not None else folder/"figures"; out.mkdir(parents=True,exist_ok=True)
    describe_run(folder, title)
    for filename in OBSOLETE_OUTPUTS:
        path=out/filename
        if path.exists(): path.unlink()
    recipes=(
        lambda: macro([(config(folder).get("seed",0),folder)],out,title),
        lambda: avalanche_figures([(config(folder).get("seed",0),folder)],out,title),
        lambda: temporal_selected(folder,out,title),
        lambda: series_figures([(config(folder).get("seed",0),folder)],out,title),
        lambda: inequality_figures([(config(folder).get("seed",0),folder)],out,title),
        lambda: network_figure(folder,out,title),
        lambda: instantaneous_life([(config(folder).get("seed",0),folder)],out,title),
        lambda: entity_lives(folder,out,title),
        lambda: soc_figures(folder,out,title),
    )
    errors=[]
    for recipe in recipes:
        try: recipe()
        except Exception as exc: errors.append(f"{getattr(recipe,'__name__','figure')}: {exc}")
    return errors


def generate_batch(members, out: Path, title: str) -> list[str]:
    out.mkdir(parents=True,exist_ok=True); errors=[]
    recipes=(
        lambda: avalanche_figures(members,out,title,volume_ccdf_output=False),
        lambda: volume_pareto(members,out,title),
        lambda: empirical_revenue(members,out,title),
        lambda: lifespan(members,out,title),
        lambda: instantaneous_life(members,out,title),
    )
    for recipe in recipes:
        try: recipe()
        except Exception as exc: errors.append(str(exc))
    return errors


def generate_synthesis(lots, out: Path, title: str) -> bool:
    """Y03 : invariants par run, puis position du lot selon sa taille."""
    points=[]
    for lot_label,members in lots:
        for seed,folder in members:
            rows=read_csv(folder/"series.csv"); avalanches=read_csv(folder/"avalanches.csv")
            if not rows or not avalanches: continue
            burn=int(config(folder).get("T",0))//4
            late_rows=[row for row in rows if row["t"]>=burn]; late=[row for row in avalanches if row["t"]>=burn]
            if not late_rows or not late: continue
            mean_population=float(np.mean([row["pop"] for row in late_rows])); total_size=sum(row["size"] for row in late); total_roots=sum(row["n_roots"] for row in late)
            branching=1-total_roots/total_size if total_size else 0; depth=float(np.mean([row["depth"] for row in late])); rate=len(late)/max(1,len(late_rows))
            points.append((mean_population,branching,depth,rate,lot_label,seed))
    if len({point[4] for point in points})<2: return False
    out.mkdir(parents=True,exist_ok=True); fig,axes=plt.subplots(1,3,figsize=(16,5.2))
    lot_names=list(dict.fromkeys(point[4] for point in points))
    for index,lot in enumerate(lot_names):
        subset=[point for point in points if point[4]==lot]; x=[p[0] for p in subset]; color=COLORS[index%10]
        for axis,column,label in zip(axes,(1,2,3),("Rapport de branchement","Profondeur moyenne","Avalanches / pas")):
            axis.scatter(x,[p[column] for p in subset],s=28,alpha=.75,color=color,label=lot if column==1 else None); axis.set(xscale="log",xlabel="Population moyenne post burn-in",ylabel=label); axis.grid(True,which="both",alpha=.2)
    axes[0].legend(); fig.suptitle(f"Invariants SOC selon la taille du système — {title}"); fig.tight_layout(); save(fig,out/"invariants_soc.png"); return True
