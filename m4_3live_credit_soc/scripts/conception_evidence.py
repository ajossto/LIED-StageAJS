"""Preuves chiffrées et figures du rapport de CONCEPTION.

Consigne du dépôt : toute donnée qui a informé une décision doit être
sauvegardée dans un fichier accessible, et toute figure doit être
reproductible par un script. Ce module produit donc, pour chacun des faits
avancés dans `report/conception_m4_3live.tex`, à la fois le fichier de
données et la figure :

  1. l'institution elle-même — δ*(part de l'emprunteuse) dans les trois
     régimes, y compris la zone δ* ≤ 0 où le marché refuse de traiter ;
  2. la table 1D — erreur contre Newton exact en fonction du nombre de
     nœuds, avec la pente d'ordre 4 attendue ;
  3. le front coût/précision des cinq chemins du noyau ;
  4. le pilote du plafond institutionnel, PAS À PAS (le fichier agrégé
     `results/campaign/pilot_cap.json` ne gardait que des totaux) ;
  5. la règle de taux candidate : r = pΔ/q comparé au taux marginal ;
  6. l'aller-retour snapshot : dynamique identique, `interest_paid` au
     dernier bit.

    python3 scripts/conception_evidence.py
"""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, "/home/anatole/jupyter")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from simulation_lab.plot_utils import apply_style  # noqa: E402

from m4_3live.kernel import (  # noqa: E402
    PrincipalKernel,
    TechRegistry,
    joint_production_gain,
)
from m4_3live.live import load_snapshot, save_snapshot  # noqa: E402
from m4_3live.model import Config, Intervention, Simulation, pair_rate, surplus_rate  # noqa: E402

OUT = ROOT / "results" / "conception"
FIGDIR = ROOT / "report" / "figures"
BURN = ROOT / "results" / "campaign" / "burn"
T0 = 2000

# Domaine réel de M4.3 (rapport d'architecture §7) : quantiles de C = x + y.
C_MEDIAN = 1589.6
TECH_BASE = (1.0, 0.5)
TECH_A = (1.5, 0.5)  # levier sur A seul  -> régime (b)
TECH_G = (1.0, 0.6)  # levier sur γ        -> régime (c)


def write_csv(name: str, header: list[str], rows) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def write_json(name: str, payload) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# 1. L'institution : δ* selon la part de l'emprunteuse, trois régimes
# --------------------------------------------------------------------------
def institution_curves(capital_sum: float = C_MEDIAN) -> dict:
    registry = TechRegistry()
    kernel = PrincipalKernel(registry, threshold=10**9)
    base = registry.intern(*TECH_BASE)
    boosted_a = registry.intern(*TECH_A)
    boosted_g = registry.intern(*TECH_G)
    kernel.sync_matrix()

    fractions = np.linspace(0.02, 0.98, 193)
    cases = {
        "identite": (base, base, "(a) même technologie — δ* = (K_ℓ−K_b)/2"),
        "b_emprunteuse_dopee": (boosted_a, base, "(b) emprunteuse dopée A×1,5"),
        "b_preteuse_dopee": (base, boosted_a, "(b) prêteuse dopée A×1,5"),
        "c_emprunteuse_dopee": (boosted_g, base, "(c) emprunteuse dopée γ 0,5→0,6"),
        "c_preteuse_dopee": (base, boosted_g, "(c) prêteuse dopée γ 0,5→0,6"),
    }
    curves: dict[str, dict] = {}
    rows = []
    for key, (tech_b, tech_l, label) in cases.items():
        deltas, arithmetics = [], []
        for fraction in fractions:
            x = fraction * capital_sum
            y = capital_sum - x
            delta = kernel.solve_exact(tech_b, tech_l, x, y)
            deltas.append(delta)
            arithmetics.append(0.5 * (y - x))
            rows.append([key, f"{x:.6g}", f"{y:.6g}", f"{delta:.10g}", f"{0.5 * (y - x):.10g}"])
        curves[key] = {"label": label, "delta": deltas, "arithmetic": arithmetics}
    write_csv(
        "institution_curves.csv",
        ["cas", "K_emprunteuse", "K_preteuse", "delta_optimal", "delta_arithmetique"],
        rows,
    )
    return {"C": capital_sum, "fractions": fractions.tolist(), "curves": curves}


def figure_institution(data: dict) -> None:
    fractions = np.array(data["fractions"])
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    colors = {
        "identite": "#66757f",
        "b_emprunteuse_dopee": "#c1440e",
        "b_preteuse_dopee": "#294c60",
        "c_emprunteuse_dopee": "#e08a3c",
        "c_preteuse_dopee": "#2e7d5b",
    }
    for key, entry in data["curves"].items():
        style = "-" if "emprunteuse" in key or key == "identite" else "--"
        axes[0].plot(fractions, entry["delta"], style, color=colors[key], lw=1.6,
                     label=entry["label"])
    axes[0].axhline(0.0, color="black", lw=0.8)
    axes[0].fill_between(fractions, -1000, 0, color="#a73d3d", alpha=0.07)
    axes[0].text(0.52, -180, "δ* ≤ 0 : le marché refuse\n(sens du prêt : riche → pauvre)",
                 fontsize=7, color="#a73d3d")
    axes[0].set_xlabel("part du capital de la paire détenue par l'emprunteuse, $K_b/C$")
    axes[0].set_ylabel("transfert δ* (unités de capital)")
    axes[0].set_title(f"Transfert optimal, C = {data['C']:.0f} (médiane du domaine réel M4.3)")
    axes[0].set_xlim(0, 1)
    axes[0].grid(True, alpha=0.25)
    axes[0].legend(fontsize=7, loc="upper right")

    for key, entry in data["curves"].items():
        if key == "identite":
            continue
        ratio = np.array(entry["delta"]) / np.maximum(1e-9, np.array(entry["arithmetic"]))
        axes[1].plot(fractions[fractions < 0.5], ratio[fractions < 0.5], color=colors[key], lw=1.6,
                     label=entry["label"])
    axes[1].axhline(1.0, color="black", ls="--", lw=1.0, label="règle arithmétique de M4.3")
    axes[1].set_xlabel("part du capital détenue par l'emprunteuse, $K_b/C$")
    axes[1].set_ylabel("δ* / δ arithmétique")
    axes[1].set_title("Écart à la règle historique (paires où l'emprunteuse est la plus pauvre)")
    axes[1].set_ylim(-1.5, 3.0)
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(fontsize=7)
    figure.tight_layout()
    figure.savefig(FIGDIR / "institution_regimes.png", dpi=150, bbox_inches="tight")
    plt.close(figure)


# --------------------------------------------------------------------------
# 2. Ordre de convergence de la table, et erreur du chemin tiède
# --------------------------------------------------------------------------
def lut_convergence() -> dict:
    registry = TechRegistry()
    exact_kernel = PrincipalKernel(registry)
    tech_b = registry.intern(*TECH_BASE)
    tech_l = registry.intern(1.25, 0.6)
    exact_kernel.sync_matrix()
    # L'échantillon doit BALAYER C : garder C constant ne sonderait qu'un seul
    # point de la table, et le maximum d'erreur y dépendrait de la position
    # fortuite de ce point dans son intervalle d'interpolation. On couvre donc
    # les quantiles 0,1 % à 99,9 % du domaine réel (192 → 2214), avec une part
    # d'emprunteuse variable.
    sums = np.linspace(192.0, 2213.6, 400)
    shares = 0.05 + 0.40 * ((np.arange(400) * 0.618) % 1.0)
    sample = [(share * total, (1.0 - share) * total) for total, share in zip(sums, shares)]

    node_counts = (9, 17, 33, 65, 129)
    errors = []
    for points in node_counts:
        registry_l = TechRegistry()
        kernel = PrincipalKernel(registry_l, threshold=5, points=points)
        b = registry_l.intern(*TECH_BASE)
        l = registry_l.intern(1.25, 0.6)
        kernel.sync_matrix()
        for x, y in sample:
            kernel.solve(b, l, x, y)
        errors.append(
            max(abs(kernel.solve(b, l, x, y) - exact_kernel.solve_exact(tech_b, tech_l, x, y))
                for x, y in sample)
        )

    warm_registry = TechRegistry()
    warm_kernel = PrincipalKernel(warm_registry, policy="hybrid", threshold=10**9)
    wb = warm_registry.intern(*TECH_BASE)
    wl = warm_registry.intern(1.25, 0.6)
    warm_kernel.sync_matrix()
    warm_error = 0.0
    for x, y in sample:
        warm_kernel.solve(wb, wl, x, y)
        warm_error = max(
            warm_error,
            abs(warm_kernel.solve(wb, wl, x, y) - exact_kernel.solve_exact(tech_b, tech_l, x, y)),
        )

    payload = {
        "noeuds": list(node_counts),
        "erreur_max_capital": errors,
        "rapports": [errors[i] / errors[i + 1] for i in range(len(errors) - 1)],
        "erreur_chemin_tiede": warm_error,
        "domaine": "C balayé de 192 à 2214 (quantiles 0,1 %–99,9 % de M4.3), 400 paires",
    }
    write_json("lut_convergence.json", payload)
    return payload


def figure_lut(payload: dict) -> None:
    nodes = np.array(payload["noeuds"], dtype=float)
    errors = np.array(payload["erreur_max_capital"])
    figure, axis = plt.subplots(figsize=(6.4, 4.4))
    axis.loglog(nodes, errors, "o-", color="#294c60", lw=1.6, label="table de Hermite (mesuré)")
    reference = errors[0] * (nodes[0] / nodes) ** 4
    axis.loglog(nodes, reference, "--", color="#66757f", lw=1.2,
                label="pente d'ordre 4 attendue")
    order_two = errors[0] * (nodes[0] / nodes) ** 2
    axis.loglog(nodes, order_two, ":", color="#a73d3d", lw=1.2,
                label="ordre 2 (ce qu'une dérivée fausse donnerait)")
    axis.axhline(payload["erreur_chemin_tiede"], color="#c1440e", lw=1.4,
                 label=f"chemin tiède ({payload['erreur_chemin_tiede']:.2e})")
    axis.set_xlabel("nœuds par octave de la table")
    axis.set_ylabel("erreur maximale sur δ (unités de capital)")
    axis.set_title(f"Table 1D : ordre de convergence mesuré\n(n=400 paires, {payload['domaine']})")
    axis.grid(True, which="both", alpha=0.25)
    axis.legend(fontsize=7)
    figure.tight_layout()
    figure.savefig(FIGDIR / "kernel_convergence.png", dpi=150, bbox_inches="tight")
    plt.close(figure)


# --------------------------------------------------------------------------
# 3. Front coût / précision (relit le banc déjà mesuré)
# --------------------------------------------------------------------------
def figure_bench() -> bool:
    source = ROOT / "results" / "analysis" / "bench_kernel.json"
    if not source.exists():
        return False
    data = json.loads(source.read_text(encoding="utf-8"))
    labels = {
        "identite": "(a) même techno",
        "gamma_egaux": "(b) γ égaux",
        "newton_exact": "(c) Newton exact",
        "tiede_newton_1": "(c) tiède",
        "lut_hermite_33": "(c) table, 33 nœuds",
        "lut_hermite_65": "(c) table, 65 nœuds",
    }
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    names, throughput = [], []
    for key, label in labels.items():
        entry = data["chemins"].get(key)
        if entry is None:
            continue
        names.append(label)
        throughput.append(entry["mreq_s"])
    axes[0].barh(names, throughput, color="#294c60", alpha=0.9)
    for index, value in enumerate(throughput):
        axes[0].text(value, index, f" {value:.2f}", va="center", fontsize=8)
    axes[0].set_xlabel("débit (millions de résolutions/s)")
    axes[0].set_title(f"Débit par chemin ({data['machine']['appels']:,} appels)".replace(",", " "))
    axes[0].grid(True, axis="x", alpha=0.25)

    for key, label in labels.items():
        entry = data["chemins"].get(key)
        if entry is None or "erreur_max_capital" not in entry:
            continue
        axes[1].scatter(entry["mreq_s"], entry["erreur_max_capital"], s=60,
                        color="#c1440e" if "tiède" in label else "#294c60")
        axes[1].annotate(label, (entry["mreq_s"], entry["erreur_max_capital"]),
                         textcoords="offset points", xytext=(6, 4), fontsize=7)
    axes[1].set_yscale("log")
    axes[1].set_xlabel("débit (millions de résolutions/s)")
    axes[1].set_ylabel("erreur maximale sur δ (unités de capital)")
    axes[1].set_title("Front coût / précision — le chemin tiède paie 10⁷ en précision")
    axes[1].grid(True, which="both", alpha=0.25)
    share = data.get("part_du_pas", {}).get("fraction_du_pas_estimee")
    if share is not None:
        axes[1].text(0.02, 0.04, f"part du noyau dans le coût d'un pas : {share:.1%}",
                     transform=axes[1].transAxes, fontsize=8)
    figure.tight_layout()
    figure.savefig(FIGDIR / "kernel_cost_precision.png", dpi=150, bbox_inches="tight")
    plt.close(figure)
    return True


# --------------------------------------------------------------------------
# 4. Pilote du plafond institutionnel, pas à pas
# --------------------------------------------------------------------------
def cap_pilot(seed: int = 0, steps: int = 600) -> dict:
    from scripts.campaign import BASE

    snapshot = BURN / f"seed{seed}" / f"snapshot_t{T0}.pkl"
    if not snapshot.exists():
        return {}
    payload = {}
    rows = []
    for cap in ("optimum", "equalization"):
        config = Config(**{**BASE, "transfer_cap": cap}, seed=seed, T=T0 + steps)
        simulation = load_snapshot(snapshot, config=config)
        simulation.submit(Intervention(param="A", value=1.5, scope="fraction", phi=0.2))
        while simulation.t < config.T and simulation.status == "ok":
            simulation.step()
        window = simulation.series[T0:]
        tech = {}
        for entry in simulation.tech_series:
            if entry["t"] > T0:
                tech.setdefault(entry["t"], {})[entry["tech"]] = entry
        for index, row in enumerate(window, start=1):
            treated = tech.get(T0 + index, {})
            share = sum(v["n_alive"] for k, v in treated.items() if k != 0)
            total = sum(v["n_alive"] for v in treated.values()) or 1
            rows.append([cap, index, row["mkt_capped"], row["mkt_blocked_dir"],
                         row["mkt_rounds"], row["pop"], f"{share / total:.6f}"])
        payload[cap] = {
            "status": simulation.status,
            "capped_total": sum(r["mkt_capped"] for r in window),
            "capped_h1": window[0]["mkt_capped"],
            "capped_after_h50": sum(r["mkt_capped"] for r in window[50:]),
            "blocked_dir_share": sum(r["mkt_blocked_dir"] for r in window)
            / max(1, sum(r["mkt_rounds"] for r in window)),
            "roots_liquidity": sum(r["roots_liquidity"] for r in window),
            "deaths": sum(r["deaths"] for r in window),
            "prod_mean": sum(r["prod_tot"] for r in window) / len(window),
        }
    write_csv("cap_pilot_steps.csv",
              ["plafond", "h", "capped", "blocked_dir", "rounds", "pop", "part_traitee"], rows)
    write_json("cap_pilot.json", payload)
    return payload


def figure_cap(payload: dict) -> None:
    if not payload:
        return
    rows = list(csv.DictReader(open(OUT / "cap_pilot_steps.csv", encoding="utf-8")))
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    for cap, color in (("equalization", "#c1440e"), ("optimum", "#294c60")):
        subset = [r for r in rows if r["plafond"] == cap]
        h = [int(r["h"]) for r in subset]
        axes[0].plot(h, [int(r["capped"]) for r in subset], color=color, lw=1.3,
                     label=f"plafond « {cap} »")
        axes[1].plot(h, [int(r["blocked_dir"]) / max(1, int(r["rounds"])) for r in subset],
                     color=color, lw=1.3, label=f"plafond « {cap} »")
    axes[0].set_xlabel("horizon h après l'intervention (pas)")
    axes[0].set_ylabel("transactions plafonnées par pas")
    axes[0].set_title("Le plafond d'égalisation ne mord que le transitoire")
    axes[0].set_xlim(0, 200)
    axes[0].grid(True, alpha=0.25)
    axes[0].legend(fontsize=8)
    subset = [r for r in rows if r["plafond"] == "optimum"]
    axes[1].plot([int(r["h"]) for r in subset], [float(r["part_traitee"]) for r in subset],
                 color="#2e7d5b", lw=1.3, ls="--", label="part traitée de la population")
    axes[1].set_xlabel("horizon h après l'intervention (pas)")
    axes[1].set_ylabel("part des rounds refusés / part traitée")
    axes[1].set_title("Les paires mixtes basculent vers le refus par le sens du prêt")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(fontsize=8)
    figure.suptitle("Pilote du plafond institutionnel — bras traité φ=0,2, A×1,5, graine 0")
    figure.tight_layout()
    figure.savefig(FIGDIR / "cap_pilot.png", dpi=150, bbox_inches="tight")
    plt.close(figure)


# --------------------------------------------------------------------------
# 5. Règle de taux candidate
# --------------------------------------------------------------------------
def rate_comparison() -> dict:
    registry = TechRegistry()
    kernel = PrincipalKernel(registry, threshold=10**9)
    pairs = {
        "homogène": (registry.intern(*TECH_BASE), registry.intern(*TECH_BASE), TECH_BASE, TECH_BASE),
        "emprunteuse A×1,5": (registry.intern(*TECH_A), registry.intern(*TECH_BASE), TECH_A, TECH_BASE),
        "emprunteuse γ=0,6": (registry.intern(*TECH_G), registry.intern(*TECH_BASE), TECH_G, TECH_BASE),
    }
    kernel.sync_matrix()
    fractions = np.linspace(0.05, 0.48, 80)
    rows, curves = [], {}
    for name, (tech_b, tech_l, tb, tl) in pairs.items():
        marginal, surplus_based = [], []
        for fraction in fractions:
            x = fraction * C_MEDIAN
            y = C_MEDIAN - x
            delta = kernel.solve_exact(tech_b, tech_l, x, y)
            if delta <= 0:
                marginal.append(np.nan)
                surplus_based.append(np.nan)
                continue
            gain = joint_production_gain(tb[0], tb[1], tl[0], tl[1], x, y, delta)
            r_marginal = pair_rate(y, x, tl[1], tl[0], tb[1], tb[0])
            r_surplus = surplus_rate(delta, gain, 0.5)
            marginal.append(r_marginal)
            surplus_based.append(r_surplus)
            rows.append([name, f"{x:.6g}", f"{y:.6g}", f"{delta:.6g}", f"{gain:.6g}",
                         f"{r_marginal:.8g}", f"{r_surplus:.8g}", f"{r_surplus / r_marginal:.6g}"])
        curves[name] = {"marginal": marginal, "surplus": surplus_based}
    write_csv("rate_rules.csv",
              ["cas", "K_emprunteuse", "K_preteuse", "delta", "surplus",
               "taux_marginal", "taux_surplus_p0.5", "rapport"], rows)
    ratios = [float(r[7]) for r in rows]
    payload = {"rapport_max": max(ratios), "rapport_median": float(np.median(ratios)),
               "n_paires": len(rows), "p": 0.5}
    write_json("rate_rules.json", payload)
    return {"fractions": fractions.tolist(), "curves": curves, **payload}


def figure_rate(data: dict) -> None:
    fractions = np.array(data["fractions"])
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    colors = {"homogène": "#66757f", "emprunteuse A×1,5": "#c1440e", "emprunteuse γ=0,6": "#2e7d5b"}
    for name, entry in data["curves"].items():
        axes[0].plot(fractions, entry["marginal"], "-", color=colors[name], lw=1.5,
                     label=f"{name} — taux marginal")
        axes[0].plot(fractions, entry["surplus"], "--", color=colors[name], lw=1.5,
                     label=f"{name} — r = pΔ/q, p=0,5")
        ratio = np.array(entry["surplus"]) / np.array(entry["marginal"])
        axes[1].plot(fractions, ratio, color=colors[name], lw=1.5, label=name)
    axes[0].set_yscale("log")
    axes[0].set_xlabel("part du capital détenue par l'emprunteuse, $K_b/C$")
    axes[0].set_ylabel("taux par pas")
    axes[0].set_title(f"Deux règles de taux, C = {C_MEDIAN:.0f}")
    axes[0].grid(True, which="both", alpha=0.25)
    axes[0].legend(fontsize=6)
    axes[1].axhline(1.0, color="black", ls="--", lw=1.0, label="parité des deux règles")
    axes[1].set_xlabel("part du capital détenue par l'emprunteuse, $K_b/C$")
    axes[1].set_ylabel("taux au surplus / taux marginal")
    axes[1].set_title(
        f"La règle candidate allège toujours le service (max mesuré {data['rapport_max']:.3f})"
    )
    axes[1].set_ylim(0, 1.1)
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(fontsize=7)
    figure.tight_layout()
    figure.savefig(FIGDIR / "rate_rules.png", dpi=150, bbox_inches="tight")
    plt.close(figure)


# --------------------------------------------------------------------------
# 6. Aller-retour snapshot
# --------------------------------------------------------------------------
def snapshot_round_trip(steps: int = 120, cut: int = 60) -> dict:
    base = dict(seed=11, lam=12.0, delta=0.01, sigma=0.01, K0=25.0, gamma=0.5, A=1.0)
    straight = Simulation(Config(**base, T=steps))
    straight.run()
    branched = Simulation(Config(**base, T=cut))
    branched.run()
    OUT.mkdir(parents=True, exist_ok=True)
    path = save_snapshot(branched, OUT / "round_trip.pkl")
    restored = load_snapshot(path, config=Config(**base, T=steps))
    restored.run()

    changed = sum(
        1
        for key in branched.book.by_borrower
        if list(branched.book.by_borrower[key]) != list(restored.book.by_borrower[key])
    )
    rows = []
    for a, b in zip(straight.series, restored.series):
        rows.append([
            a["t"],
            f"{abs(a['K_tot'] - b['K_tot']):.17g}",
            f"{abs(a['prod_tot'] - b['prod_tot']):.17g}",
            f"{abs(a['pop'] - b['pop']):.17g}",
            f"{abs(a['interest_paid'] - b['interest_paid']) / max(1.0, abs(a['interest_paid'])):.17g}",
        ])
    write_csv("snapshot_round_trip.csv",
              ["t", "ecart_K_tot", "ecart_prod_tot", "ecart_pop", "ecart_relatif_interest_paid"],
              rows)
    payload = {
        "pas": steps,
        "coupure": cut,
        "ensembles_reordonnes": changed,
        "ensembles_total": len(branched.book.by_borrower),
        "ecart_max_K_tot": max(float(r[1]) for r in rows),
        "ecart_max_prod_tot": max(float(r[2]) for r in rows),
        "ecart_relatif_max_interest_paid": max(float(r[4]) for r in rows),
    }
    write_json("snapshot_round_trip.json", payload)
    return payload


def figure_snapshot(payload: dict) -> None:
    rows = list(csv.DictReader(open(OUT / "snapshot_round_trip.csv", encoding="utf-8")))
    time_axis = [int(r["t"]) for r in rows]
    figure, axis = plt.subplots(figsize=(7.5, 4.2))
    axis.plot(time_axis, [max(float(r["ecart_relatif_interest_paid"]), 1e-20) for r in rows],
              color="#c1440e", lw=1.2, label="interest_paid (agrégat de diagnostic)")
    axis.plot(time_axis, [max(float(r["ecart_K_tot"]), 1e-20) for r in rows],
              color="#294c60", lw=1.6, label="K_tot (dynamique)")
    axis.plot(time_axis, [max(float(r["ecart_prod_tot"]), 1e-20) for r in rows],
              color="#2e7d5b", lw=1.6, ls="--", label="prod_tot (dynamique)")
    axis.axvline(payload["coupure"], color="black", ls=":", lw=1.0)
    axis.text(payload["coupure"], 1e-6, " snapshot", fontsize=8)
    axis.axhline(2.2e-16, color="#66757f", ls=":", lw=1.0)
    axis.text(2, 3e-16, "epsilon machine", fontsize=7, color="#66757f")
    axis.set_yscale("log")
    axis.set_ylim(1e-20, 1e-10)
    axis.set_xlabel("t (pas)")
    axis.set_ylabel("écart à une simulation menée d'un trait")
    axis.set_title(
        "Aller-retour snapshot : la dynamique est exactement nulle "
        f"({payload['ensembles_reordonnes']}/{payload['ensembles_total']} ensembles réordonnés)"
    )
    axis.grid(True, which="both", alpha=0.25)
    axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(FIGDIR / "snapshot_round_trip.png", dpi=150, bbox_inches="tight")
    plt.close(figure)


# --------------------------------------------------------------------------
# 7. Les trois garanties de déterminisme, sur un même graphique
# --------------------------------------------------------------------------
def determinism(steps: int = 120, cut: int = 60) -> dict:
    """Rejeu d'un journal, invariant de pause, aller-retour snapshot.

    Les trois se mesurent de la même façon — écart pas à pas à une exécution
    de référence — donc une seule figure les compare. Le rejeu part d'un
    journal produit par une session pilotée, pas d'un plan écrit à la main.
    """
    import threading
    import shutil
    import tempfile

    from m4_3live.live import LiveSession, replay

    base = dict(seed=11, lam=12.0, delta=0.01, sigma=0.01, K0=25.0, gamma=0.5, A=1.0)
    reference = Simulation(Config(**base, T=steps))
    reference.submit(Intervention(param="A", value=1.4, scope="fraction", phi=0.25))
    for _ in range(40):
        reference.step()
    reference.submit(Intervention(param="gamma", value=0.6, scope="new"))
    reference.run()
    journal = list(reference.intervention_log)

    replayed = replay(Config(**base, T=steps), journal)

    directory = tempfile.mkdtemp(prefix="m4_3live_det_")
    try:
        session = LiveSession(Simulation(Config(**base, T=steps)), "evid", directory)
        plan = {int(entry["t"]): entry for entry in journal}
        session.set_speed(0.0)
        while session.simulation.t < steps:
            nxt = session.simulation.t + 1
            if nxt in plan:
                entry = plan[nxt]
                session.submit(param=entry["param"], value=entry["value"],
                               scope=entry["scope"], phi=entry.get("phi"))
            session.step_once(1)
            deadline = time.time() + 20.0
            while session.simulation.t < nxt and time.time() < deadline:
                time.sleep(0.002)
        paused = session.simulation
    finally:
        try:
            session.stop()
        except Exception:
            pass
        shutil.rmtree(directory, ignore_errors=True)

    # Branche par snapshot : on rejoue jusqu'à la coupure en appliquant TOUTES
    # les interventions dont le t y tombe, on sauvegarde, on restaure, puis on
    # poursuit avec celles qui restent.
    by_step = {int(entry["t"]): entry for entry in journal}
    branched = Simulation(Config(**base, T=cut))
    while branched.t < cut and branched.status == "ok":
        if branched.t + 1 in by_step:
            branched.submit(Intervention.from_dict(by_step[branched.t + 1]))
        branched.step()
    OUT.mkdir(parents=True, exist_ok=True)
    path = save_snapshot(branched, OUT / "determinism.pkl")
    restored = load_snapshot(path, config=Config(**base, T=steps))
    while restored.t < steps and restored.status == "ok":
        if restored.t + 1 in by_step and restored.t + 1 > cut:
            restored.submit(Intervention.from_dict(by_step[restored.t + 1]))
        restored.step()

    rows = []
    for index, row in enumerate(reference.series):
        entry = [row["t"]]
        for other in (replayed, paused, restored):
            gap = 0.0
            if index < len(other.series):
                for column in ("K_tot", "prod_tot", "pop", "n_loans"):
                    gap = max(gap, abs(float(row[column]) - float(other.series[index][column])))
            entry.append(gap)
        rows.append(entry)
    write_csv("determinism.csv",
              ["t", "ecart_rejeu", "ecart_pause", "ecart_snapshot"], rows)
    payload = {
        "pas": steps,
        "coupure_snapshot": cut,
        "interventions": len(journal),
        "ecart_max_rejeu": max(r[1] for r in rows),
        "ecart_max_pause": max(r[2] for r in rows),
        "ecart_max_snapshot": max(r[3] for r in rows),
    }
    write_json("determinism.json", payload)
    return payload


def figure_determinism(payload: dict) -> None:
    rows = list(csv.DictReader(open(OUT / "determinism.csv", encoding="utf-8")))
    time_axis = [int(r["t"]) for r in rows]
    figure, axis = plt.subplots(figsize=(8.4, 4.4))
    for key, label, color, style in (
        ("ecart_rejeu", "rejeu du journal sans tête", "#294c60", "-"),
        ("ecart_pause", "pas-à-pas via la session en direct", "#c1440e", "--"),
        ("ecart_snapshot", "aller-retour par snapshot", "#2e7d5b", ":"),
    ):
        # Écarts exactement nuls : rabattus sur un plancher visible, étiqueté.
        axis.plot(time_axis, [max(float(r[key]), 1e-19) for r in rows],
                  color=color, lw=1.6, ls=style, label=label)
    axis.axvline(payload["coupure_snapshot"], color="black", ls=":", lw=1.0)
    axis.text(payload["coupure_snapshot"], 3e-11, " snapshot", fontsize=8)
    axis.axhline(2.2e-16, color="#66757f", ls=":", lw=1.0)
    axis.text(2, 3e-16, "epsilon machine", fontsize=7, color="#66757f")
    axis.set_yscale("log")
    axis.set_ylim(3e-20, 1e-10)
    axis.set_xlabel("t (pas)")
    axis.set_ylabel("écart maximal à la trajectoire de référence\n(K_tot, prod_tot, pop, n_loans)")
    axis.set_title(
        "Trois garanties de déterminisme, une seule mesure : l'écart est "
        "exactement nul\n"
        f"({payload['interventions']} interventions, {payload['pas']} pas)"
    )
    axis.grid(True, which="both", alpha=0.25)
    axis.legend(fontsize=8, loc="upper right")
    figure.tight_layout()
    figure.savefig(FIGDIR / "determinism.png", dpi=150, bbox_inches="tight")
    plt.close(figure)


# --------------------------------------------------------------------------
# 8. Le rapport de divergence à la reprise, mis à l'épreuve
# --------------------------------------------------------------------------
def divergence_cases(upto: int = 200) -> dict:
    from m4_3live.live import divergence_report, read_series_csv, resume_from_series
    from simulation_lab.runs.storage import RunStorage

    storage = RunStorage()
    reference_run = "m4_3__d1__baseline__seed0"
    other_run = "m4_3__d1__rho_2__seed0"
    parameters = storage.read_metadata(reference_run)["parameters"]
    series_reference = Path(storage.run_dir(reference_run)) / "series.csv"
    series_other = Path(storage.run_dir(other_run)) / "series.csv"

    cases = {}
    simulation, report = resume_from_series(parameters, series_reference, upto)
    cases["reprise homogène"] = report

    _, report_other = resume_from_series(parameters, series_other, 60)
    cases["confrontée à un autre run"] = report_other

    known = set(Config.__dataclass_fields__)
    config = Config(**{**{k: v for k, v in parameters.items() if k in known}, "T": upto})
    treated = Simulation(config)
    for _ in range(upto // 2):
        treated.step()
    treated.submit(Intervention(param="A", value=1.4, scope="fraction", phi=0.3))
    treated.run()
    cases["après une intervention"] = divergence_report(
        treated, read_series_csv(series_reference), upto
    )
    write_json("divergence_cases.json", cases)
    return cases


def figure_divergence(cases: dict) -> None:
    figure, axis = plt.subplots(figsize=(8.4, 4.2))
    labels = list(cases)
    values = [max(cases[k]["max_relative"], 1e-18) for k in labels]
    colors = ["#2e7d5b", "#c1440e", "#294c60"]
    bars = axis.bar(labels, values, color=colors, alpha=0.9)
    for bar, key in zip(bars, labels):
        report = cases[key]
        note = ("identique bit à bit" if report["bit_identical"]
                else f"1er écart : t={report['first_difference']['t']}\n"
                     f"({report['first_difference']['column']})")
        axis.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.6, note,
                  ha="center", fontsize=8)
    axis.set_yscale("log")
    axis.set_ylim(1e-18, 1e3)
    axis.set_ylabel("écart relatif maximal rapporté")
    axis.set_title(
        "Le rapport de divergence n'est pas décoratif : il détecte,\n"
        "et il rapporte zéro quand c'est zéro"
    )
    axis.grid(True, axis="y", which="both", alpha=0.25)
    figure.tight_layout()
    figure.savefig(FIGDIR / "divergence_cases.png", dpi=150, bbox_inches="tight")
    plt.close(figure)


def main() -> int:
    apply_style()
    FIGDIR.mkdir(parents=True, exist_ok=True)
    started = time.time()

    print("1/8 institution — trois régimes")
    figure_institution(institution_curves())
    print("2/8 table 1D — ordre de convergence")
    lut = lut_convergence()
    figure_lut(lut)
    print(f"    rapports {['%.1f' % r for r in lut['rapports']]} (attendu ≈ 16)")
    print("3/8 front coût/précision")
    if not figure_bench():
        print("    (banc absent : lancer scripts/bench_kernel.py)")
    print("4/8 pilote du plafond institutionnel")
    cap = cap_pilot()
    figure_cap(cap)
    if cap:
        print(f"    plafonnées h=1 : {cap['equalization']['capped_h1']}, "
              f"après h=50 : {cap['equalization']['capped_after_h50']}")
    print("5/8 règles de taux")
    rate = rate_comparison()
    figure_rate(rate)
    print(f"    rapport max r_surplus/r_marginal = {rate['rapport_max']:.4f}")
    print("6/8 aller-retour snapshot")
    snapshot = snapshot_round_trip()
    figure_snapshot(snapshot)
    print(f"    ensembles réordonnés {snapshot['ensembles_reordonnes']}/"
          f"{snapshot['ensembles_total']}, écart K_tot {snapshot['ecart_max_K_tot']:.1e}")
    print("7/8 trois garanties de déterminisme")
    det = determinism()
    figure_determinism(det)
    print(f"    écarts max : rejeu {det['ecart_max_rejeu']:.1e}, "
          f"pause {det['ecart_max_pause']:.1e}, snapshot {det['ecart_max_snapshot']:.1e}")
    print("8/8 rapport de divergence à la reprise")
    cases = divergence_cases()
    figure_divergence(cases)
    for name, report in cases.items():
        print(f"    {name:28s} bit-identique={report['bit_identical']} "
              f"ecart_relatif_max={report['max_relative']:.3e}")
    print(f"\nDonnées dans {OUT.relative_to(ROOT)}, figures dans {FIGDIR.relative_to(ROOT)} "
          f"({time.time() - started:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
