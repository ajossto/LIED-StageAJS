"""
Analyse predictive globale de l'etude de sensibilite.

Objectif: estimer dans quelle mesure l'issue d'une simulation peut etre predite
depuis ses parametres d'execution. Les modeles sont volontairement simples et
diagnostiques: forets aleatoires avec validation croisee par petits echantillons.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, balanced_accuracy_score, r2_score
from sklearn.model_selection import KFold, StratifiedKFold, cross_val_predict


HERE = Path(__file__).resolve().parent
RESULTS_DIR = HERE / "results"
FIGURES_DIR = HERE / "report" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

DATASETS = [
    "pilot_results.json",
    "k_sweep_steps1500_eps0.001.json",
    "alpha_sigma_sweep_steps1500_eps0.001.json",
    "epsilon_runtime_probe.json",
    "lab_guided_probe.json",
    "codex_oat_screen_steps1500_seeds42.json",
]

FEATURES = [
    "theta",
    "mu",
    "lambda_creation",
    "n_candidats_pool",
    "fraction_taux_emprunteur",
    "seuil_ratio_endettement",
    "seuil_ratio_liquide_passif",
    "taux_depreciation_endo",
    "taux_depreciation_exo",
    "fraction_auto_investissement",
    "coefficient_reliquefaction",
    "actif_liquide_initial",
    "passif_inne_initial",
    "n_entites_initiales",
    "alpha_sigma_brownien",
    "epsilon",
    "alpha_span",
]


def main() -> None:
    rows = load_rows()
    X, feature_names = feature_matrix(rows)
    y_bounded = np.array([1 if row.get("bounded_tail") else 0 for row in rows], dtype=int)
    y_density = np.array([metric(row, "measure_densite_fin_mean", "densite_fin_mean") for row in rows], dtype=float)
    y_alive = np.array([metric(row, "measure_n_alive_mean", "n_alive_mean") for row in rows], dtype=float)

    clf_result = fit_classifier(X, y_bounded, feature_names)
    density_result = fit_regressor(X, y_density, feature_names, target_name="densite_fin")
    alive_result = fit_regressor(X, np.log1p(y_alive), feature_names, target_name="log_n_alive")

    phase = phase_summary(rows)
    summary = {
        "n_rows": len(rows),
        "features": feature_names,
        "bounded_tail_rate": float(np.mean(y_bounded)),
        "classifier": clf_result["metrics"],
        "density_regressor": density_result["metrics"],
        "alive_regressor": alive_result["metrics"],
        "phase_summary": phase,
    }
    (RESULTS_DIR / "codex_predictive_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    plot_importances(clf_result, density_result, alive_result, path=FIGURES_DIR / "codex_predictive_importance.pdf")
    plot_importances(clf_result, density_result, alive_result, path=FIGURES_DIR / "codex_predictive_importance.png")
    plot_phase(rows, FIGURES_DIR / "codex_phase_maps.pdf")
    plot_phase(rows, FIGURES_DIR / "codex_phase_maps.png")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def load_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for filename in DATASETS:
        path = RESULTS_DIR / filename
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            continue
        for row in data:
            if not isinstance(row, dict):
                continue
            rec = dict(row)
            rec["source_file"] = filename
            normalize_flags(rec)
            rows.append(rec)
    return rows


def normalize_flags(row: dict[str, Any]) -> None:
    diag = row.get("regime_diagnostics")
    if isinstance(diag, dict):
        row.setdefault("bounded_tail", bool(diag.get("bounded_tail", False)))
        row.setdefault("drop_5_detected", bool(diag.get("drop_5_detected", False)))
    if "bounded_tail" not in row:
        row["bounded_tail"] = bool(row.get("converged") or row.get("joint_drop"))


def feature_matrix(rows: list[dict[str, Any]]) -> tuple[np.ndarray, list[str]]:
    X = []
    for row in rows:
        params = row.get("params") if isinstance(row.get("params"), dict) else {}
        rec = []
        for name in FEATURES:
            if name == "alpha_span":
                amin = value(row, params, "alpha_min", default=1.0)
                amax = value(row, params, "alpha_max", default=1.0)
                rec.append(float(amax - amin))
            else:
                rec.append(float(value(row, params, name, default=default_for(name))))
        X.append(rec)
    return np.array(X, dtype=float), list(FEATURES)


def value(row: dict[str, Any], params: dict[str, Any], name: str, *, default: float) -> float:
    val = row.get(name)
    if val is None:
        val = params.get(name)
    if val is None:
        val = default
    try:
        f = float(val)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError):
        return default


def default_for(name: str) -> float:
    defaults = {
        "theta": 0.35,
        "mu": 0.05,
        "lambda_creation": 2.0,
        "n_candidats_pool": 3.0,
        "fraction_taux_emprunteur": 0.2,
        "seuil_ratio_endettement": 1.0,
        "seuil_ratio_liquide_passif": 0.05,
        "taux_depreciation_endo": 0.05,
        "taux_depreciation_exo": 0.05,
        "fraction_auto_investissement": 0.5,
        "coefficient_reliquefaction": 0.5,
        "actif_liquide_initial": 200.0,
        "passif_inne_initial": 190.0,
        "n_entites_initiales": 100.0,
        "alpha_sigma_brownien": 0.0,
        "epsilon": 1e-3,
        "alpha_span": 0.0,
    }
    return defaults[name]


def metric(row: dict[str, Any], preferred: str, fallback: str) -> float:
    val = row.get(preferred)
    if val is None:
        val = row.get(fallback)
    try:
        f = float(val)
        return f if math.isfinite(f) else 0.0
    except (TypeError, ValueError):
        return 0.0


def fit_classifier(X: np.ndarray, y: np.ndarray, feature_names: list[str]) -> dict[str, Any]:
    clf = RandomForestClassifier(n_estimators=400, min_samples_leaf=3, random_state=42, class_weight="balanced")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    pred = cross_val_predict(clf, X, y, cv=cv)
    clf.fit(X, y)
    perm = permutation_importance(clf, X, y, n_repeats=30, random_state=42, scoring="balanced_accuracy")
    return {
        "model": clf,
        "importance": dict(zip(feature_names, clf.feature_importances_)),
        "permutation": dict(zip(feature_names, perm.importances_mean)),
        "metrics": {
            "accuracy_cv": float(accuracy_score(y, pred)),
            "balanced_accuracy_cv": float(balanced_accuracy_score(y, pred)),
        },
    }


def fit_regressor(X: np.ndarray, y: np.ndarray, feature_names: list[str], *, target_name: str) -> dict[str, Any]:
    reg = RandomForestRegressor(n_estimators=400, min_samples_leaf=3, random_state=42)
    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    pred = cross_val_predict(reg, X, y, cv=cv)
    reg.fit(X, y)
    perm = permutation_importance(reg, X, y, n_repeats=30, random_state=42, scoring="r2")
    return {
        "model": reg,
        "importance": dict(zip(feature_names, reg.feature_importances_)),
        "permutation": dict(zip(feature_names, perm.importances_mean)),
        "metrics": {
            "target": target_name,
            "r2_cv": float(r2_score(y, pred)),
            "rmse_cv": float(np.sqrt(np.mean((pred - y) ** 2))),
        },
    }


def top_items(values: dict[str, float], n: int = 12) -> list[tuple[str, float]]:
    return sorted(values.items(), key=lambda item: abs(item[1]), reverse=True)[:n]


def plot_importances(*results: dict[str, Any], path: Path) -> None:
    titles = [
        "Prediction queue bornee",
        "Prediction densite financiere",
        "Prediction log(n_alive)",
    ]
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.4), constrained_layout=True)
    for ax, result, title in zip(axes, results, titles):
        items = top_items(result["permutation"], n=12)
        names = [name for name, _ in items][::-1]
        vals = [val for _, val in items][::-1]
        ax.barh(range(len(vals)), vals, color="#376795")
        ax.set_yticks(range(len(vals)), names, fontsize=8)
        ax.set_title(title)
        ax.set_xlabel("importance par permutation")
        ax.grid(axis="x", alpha=0.25)
    fig.suptitle("Parametres les plus predictifs sur les campagnes disponibles")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_phase(rows: list[dict[str, Any]], path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    scatter_panel(axes[0, 0], rows, "n_candidats_pool", "alpha_sigma_brownien", "k", "sigma alpha")
    scatter_panel(axes[0, 1], rows, "theta", "mu", "theta", "mu")
    scatter_panel(axes[1, 0], rows, "lambda_creation", "taux_depreciation_exo", "lambda", "depreciation exo")
    scatter_panel(axes[1, 1], rows, "fraction_taux_emprunteur", "taux_depreciation_endo", "fraction taux empr.", "depreciation endo")
    fig.suptitle("Cartes de phase empiriques: couleur=densite, marqueur=queue bornee")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def scatter_panel(ax: plt.Axes, rows: list[dict[str, Any]], xkey: str, ykey: str, xlabel: str, ylabel: str) -> None:
    xs, ys, cs, markers = [], [], [], []
    for row in rows:
        params = row.get("params") if isinstance(row.get("params"), dict) else {}
        xs.append(value(row, params, xkey, default=default_for(xkey)))
        ys.append(value(row, params, ykey, default=default_for(ykey)))
        cs.append(metric(row, "measure_densite_fin_mean", "densite_fin_mean"))
        markers.append(bool(row.get("bounded_tail")))
    xs = np.array(xs)
    ys = np.array(ys)
    cs = np.array(cs)
    bounded = np.array(markers, dtype=bool)
    sc = ax.scatter(xs[~bounded], ys[~bounded], c=cs[~bounded], cmap="viridis", marker="x", alpha=0.75)
    ax.scatter(xs[bounded], ys[bounded], c=cs[bounded], cmap="viridis", marker="o", edgecolor="black", linewidth=0.4)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.25)
    if xkey == "epsilon":
        ax.set_xscale("log")
    if ykey == "epsilon":
        ax.set_yscale("log")
    plt.colorbar(sc, ax=ax, label="densite fin.")


def phase_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for key in ["n_candidats_pool", "alpha_sigma_brownien", "theta", "mu", "lambda_creation"]:
        buckets: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            params = row.get("params") if isinstance(row.get("params"), dict) else {}
            v = value(row, params, key, default=default_for(key))
            buckets.setdefault(f"{v:g}", []).append(row)
        summary[key] = {
            name: {
                "n": len(vals),
                "bounded_share": sum(1 for r in vals if r.get("bounded_tail")) / len(vals),
                "densite_fin_mean": float(np.mean([metric(r, "measure_densite_fin_mean", "densite_fin_mean") for r in vals])),
                "n_alive_mean": float(np.mean([metric(r, "measure_n_alive_mean", "n_alive_mean") for r in vals])),
            }
            for name, vals in sorted(buckets.items(), key=lambda item: float(item[0]))
        }
    return summary


if __name__ == "__main__":
    main()
