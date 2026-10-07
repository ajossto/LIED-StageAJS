"""
Figure de correlations parametres -> statistiques.

Cette figure est exploratoire : elle sert a reperer quels parametres de
simulation deplacent quelles statistiques, mais elle ne remplace pas les
balayages de seuils, car k et epsilon ont des effets fortement non lineaires.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
RESULTS_DIR = HERE / "results"
FIGURES_DIR = HERE / "report" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


SOURCES = [
    "k_sweep_steps1500_eps0.001.json",
    "epsilon_runtime_probe.json",
    "alpha_sigma_sweep_steps1500_eps0.001.json",
]

PARAM_KEYS = [
    ("k", "k"),
    ("epsilon", "epsilon"),
    ("alpha_sigma_brownien", "sigma_alpha"),
    ("steps", "duree"),
]

METRIC_KEYS = [
    ("bounded_tail", "queue bornee"),
    ("drop_5_detected", "chute 5%"),
    ("measure_densite_fin_mean", "vol. prets/actif"),
    ("densite_fin_mean", "vol. prets/actif"),
    ("measure_loan_density_mean", "prets/entite"),
    ("loan_density_mean", "prets/entite"),
    ("measure_n_alive_mean", "n_alive"),
    ("n_alive_mean", "n_alive"),
    ("measure_failure_rate_mean", "faillites/pas"),
    ("failure_rate_mean", "faillites/pas"),
    ("cascade_size_mean", "taille cascade"),
    ("cascade_event_rate", "freq. cascades"),
    ("corr_alive_actif_tail", "corr alive-actif"),
    ("corr_actif_loans_tail", "corr actif-prets"),
]


def load_rows() -> list[dict]:
    rows = []
    for filename in SOURCES:
        path = RESULTS_DIR / filename
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for row in data:
            rows.append(dict(row, source=filename))
    return rows


def get_numeric(row: dict, keys: list[tuple[str, str]]) -> dict[str, float]:
    out = {}
    for key, label in keys:
        if label in out:
            continue
        value = row.get(key)
        if value is None and key == "alpha_sigma_brownien":
            value = row.get("params", {}).get("alpha_sigma_brownien")
        if value is None and key == "epsilon":
            value = row.get("params", {}).get("epsilon")
        if value is None and key == "k":
            value = row.get("params", {}).get("n_candidats_pool")
        if isinstance(value, bool):
            out[label] = 1.0 if value else 0.0
        elif isinstance(value, (int, float)) and math.isfinite(float(value)):
            out[label] = float(value)
    return out


def pearson(x: list[float], y: list[float]) -> float:
    n = min(len(x), len(y))
    if n < 4:
        return float("nan")
    mx = sum(x) / n
    my = sum(y) / n
    dx = math.sqrt(sum((v - mx) ** 2 for v in x))
    dy = math.sqrt(sum((v - my) ** 2 for v in y))
    if dx <= 0 or dy <= 0:
        return float("nan")
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (dx * dy)


def build_matrix(rows: list[dict]) -> tuple[list[str], list[str], np.ndarray, np.ndarray]:
    param_labels = [label for _, label in PARAM_KEYS]
    metric_labels = []
    for _, label in METRIC_KEYS:
        if label not in metric_labels:
            metric_labels.append(label)

    mat = np.full((len(param_labels), len(metric_labels)), np.nan)
    counts = np.zeros_like(mat)

    normalized = []
    for row in rows:
        normalized.append({
            "params": get_numeric(row, PARAM_KEYS),
            "metrics": get_numeric(row, METRIC_KEYS),
        })

    for i, p_label in enumerate(param_labels):
        for j, m_label in enumerate(metric_labels):
            xs = []
            ys = []
            for row in normalized:
                if p_label in row["params"] and m_label in row["metrics"]:
                    xs.append(row["params"][p_label])
                    ys.append(row["metrics"][m_label])
            mat[i, j] = pearson(xs, ys)
            counts[i, j] = len(xs)
    return param_labels, metric_labels, mat, counts


def plot(param_labels: list[str], metric_labels: list[str], mat: np.ndarray, counts: np.ndarray) -> None:
    fig, ax = plt.subplots(figsize=(13, 4.8))
    im = ax.imshow(mat, vmin=-1, vmax=1, cmap="RdBu_r", aspect="auto")
    ax.set_xticks(range(len(metric_labels)))
    ax.set_xticklabels(metric_labels, rotation=35, ha="right")
    ax.set_yticks(range(len(param_labels)))
    ax.set_yticklabels(param_labels)
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            if math.isfinite(mat[i, j]):
                color = "white" if abs(mat[i, j]) > 0.65 else "black"
                ax.text(j, i, f"{mat[i, j]:.2f}\n(n={int(counts[i,j])})",
                        ha="center", va="center", fontsize=7, color=color)
    fig.colorbar(im, ax=ax, label="Correlation de Pearson")
    ax.set_title("Correlations exploratoires parametres -> statistiques")
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "parameter_metric_correlations.pdf", bbox_inches="tight", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    rows = load_rows()
    p, m, mat, counts = build_matrix(rows)
    plot(p, m, mat, counts)
    print(f"{len(rows)} lignes utilisees")
    print(FIGURES_DIR / "parameter_metric_correlations.pdf")
