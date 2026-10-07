"""Exemple travaillé (une seule simulation) : régression "réponse
exponentielle délayée" sur les courbes de renouvellement du décile
supérieur (net worth / capital / revenu), pour extraire un temps
caractéristique tau, un temps de délai t_delay, et la qualité de
l'ajustement (R²) — demande utilisateur du 2026-08-06 (voir JOURNAL.md).

Reproduit exactement la logique de persistence(t) de
scripts/campaign.py::_renewal_summary (même définition du décile
supérieur, même recalcul du décile courant à chaque instantané), mais
conserve la courbe complète (campaign.py ne garde que half_life_steps et
floor_last5_mean) et sur TOUTE la plage de temps disponible (pas
seulement la fenêtre de confirmation ]T/4, T]) : le but ici est
justement de voir le régime transitoire, pas de le couper d'avance.

Modèle ajusté (FOPDT, "premier ordre + délai", classique en réponse
indicielle) :

    persistence(t) = 1                                        si t-t0 <= t_delay
    persistence(t) = floor + (1-floor)*exp(-(t-t0-t_delay)/tau) sinon

y0=1 n'est PAS un paramètre libre : par construction, persistence(t0)=1
(le décile supérieur est identique à lui-même au premier instantané).
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import interest_income  # noqa: E402

RUN_DIR = ROOT / "results" / "campaign" / "baseline" / "seed0"
T_TOTAL = 3000
BURN_IN = int(0.25 * T_TOTAL)  # scripts/campaign.py:54, BURN_FRACTION
OUT = ROOT / "report" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

FIELDS = (("nw", "net worth"), ("K", "capital"), ("income", "revenu (intérêts)"))

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 130, "font.size": 10.5,
    "axes.grid": True, "grid.alpha": 0.25,
})


def persistence_curve(snaps, field: str) -> tuple[np.ndarray, np.ndarray]:
    """Copie exacte de la logique de campaign.py::_renewal_summary pour un
    seul champ, mais renvoie la courbe complète (t, persistence)."""
    t0, snap0 = snaps[0]
    key0 = snap0[field]
    threshold0 = np.quantile(key0, 0.90)
    base_ids = set(snap0["id"][key0 >= threshold0].tolist())
    n0 = len(base_ids)
    ts, ys = [], []
    for t, snap in snaps:
        current_key = snap[field]
        current_threshold = np.quantile(current_key, 0.90)
        current_top = set(snap["id"][current_key >= current_threshold].tolist())
        persistence = len(base_ids & current_top) / max(1, n0)
        ts.append(t)
        ys.append(persistence)
    return np.array(ts, dtype=float), np.array(ys, dtype=float)


def fopdt(t, floor, tau, t_delay, t0):
    dt = t - t0
    return np.where(dt <= t_delay, 1.0, floor + (1.0 - floor) * np.exp(-(dt - t_delay) / tau))


def fit_fopdt(t: np.ndarray, y: np.ndarray, t0: float) -> dict:
    def model(tt, floor, tau, t_delay):
        return fopdt(tt, floor, tau, t_delay, t0)

    span = t.max() - t0
    p0 = [max(y[-1], 1e-3), span / 5, span / 20]
    bounds = ([0.0, 1.0, 0.0], [1.0, span * 5, span])
    try:
        popt, pcov = curve_fit(model, t, y, p0=p0, bounds=bounds, maxfev=20000)
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
    floor, tau, t_delay = popt
    y_pred = model(t, *popt)
    ss_res = float(np.sum((y - y_pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return {
        "ok": True, "floor": float(floor), "tau": float(tau), "t_delay": float(t_delay),
        "t0": float(t0), "r2": r2, "y_pred": y_pred,
    }


def main():
    snaps = interest_income.load_all_entity_snapshots(RUN_DIR)
    print(f"{len(snaps)} instantanés charges, t de {snaps[0][0]} a {snaps[-1][0]}")

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), sharey=True)
    results = {}
    for ax, (field, name) in zip(axes, FIELDS):
        t, y = persistence_curve(snaps, field)
        t0 = t[0]
        fit = fit_fopdt(t, y, t0)
        results[field] = fit

        ax.plot(t, y, "o", ms=4, color="#444444", label="donnees (persistance decile sup.)")
        if fit["ok"]:
            t_smooth = np.linspace(t.min(), t.max(), 400)
            y_smooth = fopdt(t_smooth, fit["floor"], fit["tau"], fit["t_delay"], t0)
            ax.plot(t_smooth, y_smooth, "-", color="crimson", lw=2,
                     label=(f"ajustement FOPDT : floor={fit['floor']:.3f}, "
                            f"tau={fit['tau']:.0f}, t_delay={fit['t_delay']:.0f}, "
                            f"R2={fit['r2']:.3f}"))
            t_converge = t0 + fit["t_delay"] + 3 * fit["tau"]
            ax.axvline(t_converge, color="crimson", ls=":", lw=1.2, alpha=0.7,
                        label=f"~convergence (t_delay+3.tau) = {t_converge:.0f}")
        ax.axvline(BURN_IN, color="#1f77b4", ls="--", lw=1.4,
                    label=f"burn-in pipeline (T/4) = {BURN_IN}")
        ax.set_title(name)
        ax.set_xlabel("t (pas de temps)")
        ax.legend(fontsize=7, loc="upper right")
    axes[0].set_ylabel("persistance du décile supérieur au temps t0")
    fig.suptitle("Baseline, seed 0 (T=3000) — régression exponentielle délayée sur "
                  "le renouvellement du décile supérieur, toute la plage temporelle",
                  fontsize=10.5, y=1.03)
    fig.tight_layout()
    out_path = OUT / "fig8_renouvellement_fopdt_exemple.png"
    fig.savefig(out_path, bbox_inches="tight")
    print(f"ecrit : {out_path}")

    for field, name in FIELDS:
        fit = results[field]
        if fit["ok"]:
            t_converge = fit["t0"] + fit["t_delay"] + 3 * fit["tau"]
            print(f"{name:20s} floor={fit['floor']:.4f} tau={fit['tau']:.1f} "
                  f"t_delay={fit['t_delay']:.1f} R2={fit['r2']:.4f} "
                  f"convergence~t={t_converge:.0f} (burn-in pipeline={BURN_IN})")
        else:
            print(f"{name:20s} echec ajustement : {fit.get('error')}")


if __name__ == "__main__":
    main()
