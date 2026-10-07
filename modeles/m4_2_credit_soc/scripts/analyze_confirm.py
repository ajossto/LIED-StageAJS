"""Verdict confirmatoire des contrastes γ (volet 4, protocole v1.1 §critères).

Pour chaque cellule confirmatoire hors centre, calcule le contraste apparié
par graine (cellule − centre γ=1/2) de la métrique primaire tau_hat, son IC
de Student à 95 %, puis évalue une à une les 8 conditions pré-enregistrées
de confirmation, le critère d'infirmation (IC ∋ 0 et demi-largeur ≤ 0,15)
et la clause de complétude. Les runs confirmatoires DOIVENT avoir été
extraits avec --bootstrap (condition 7) ; sinon le script s'arrête.

Sorties : results/tables/confirm_contrasts.csv (une ligne par contraste ×
condition évaluée) + verdict imprimé. Les conditions 2 (λ=100), 3 (horizon
doublé) et 8 (ablation) s'appuient sur les volets correspondants lorsque
leurs manifestes existent ; sinon elles sont marquées N/A avec motif.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lib_lab
import lib_metrics

ROOT = Path(__file__).resolve().parents[1]
METRICS = ROOT / "results" / "metrics"
TABLES = ROOT / "results" / "tables"

CENTER_GAMMA = 0.5
INFIRM_HALF_WIDTH = 0.15
WINDOWS = ("burn0.125", "burn0.25", "burn0.5")

DRIFT_MAX = 0.04
HALF_POP_MAX = 0.05
HALF_POP_SD_MAX = 2.0
HALF_K_MAX = 0.10


def load_plan_runs(plan: str) -> dict[str, dict[int, dict]]:
    """cellule -> graine -> {metrics, run_dir}. Vide si le plan n'existe pas."""
    if not lib_lab.manifest_path(plan).exists():
        return {}
    out: dict[str, dict[int, dict]] = {}
    for entry in lib_lab.load_manifest(plan)["cells"]:
        cell_runs = {}
        for seed, run_dir in lib_lab.run_dirs(entry):
            path = METRICS / f"{run_dir.name}.json"
            if path.exists():
                cell_runs[seed] = {"metrics": json.loads(path.read_text()),
                                   "run_dir": run_dir}
        out[entry["cell"]] = cell_runs
    return out


def tau_hat(metrics: dict, window: str = "burn0.25") -> float | None:
    avalanches = metrics["windows"].get(window, {}).get("avalanches", {})
    return avalanches.get("tau_hat")


def avalanche_block(metrics: dict, window: str = "burn0.25") -> dict:
    return metrics["windows"].get(window, {}).get("avalanches", {})


def is_stationary(metrics: dict) -> bool:
    pop = metrics["windows"].get("burn0.25", {}).get("series", {}).get("pop", {})
    stat = metrics.get("stationarity", {})
    checks = (
        (pop.get("rel_drift_window"), DRIFT_MAX),
        (stat.get("rel_diff"), HALF_POP_MAX),
        (stat.get("diff_in_sd"), HALF_POP_SD_MAX),
        (stat.get("K_rel_diff"), HALF_K_MAX),
    )
    return all(v is not None and abs(v) <= bound for v, bound in checks)


def paired_contrast(cell_runs: dict[int, dict], center_runs: dict[int, dict],
                    value=tau_hat) -> tuple[list[int], np.ndarray] | None:
    seeds = sorted(set(cell_runs) & set(center_runs))
    diffs = []
    kept = []
    for seed in seeds:
        a = value(cell_runs[seed]["metrics"])
        b = value(center_runs[seed]["metrics"])
        if a is None or b is None:
            continue
        kept.append(seed)
        diffs.append(a - b)
    if len(kept) < 3:
        return None
    return kept, np.asarray(diffs, dtype=float)


def student_ci(diffs: np.ndarray) -> dict:
    n = len(diffs)
    mean = float(diffs.mean())
    sd = float(diffs.std(ddof=1))
    half = float(stats.t.ppf(0.975, n - 1) * sd / math.sqrt(n)) if sd > 0 else 0.0
    return {"n": n, "mean": mean, "sd": sd, "lo": mean - half, "hi": mean + half,
            "half_width": half, "excludes_zero": not (mean - half <= 0 <= mean + half)}


def window_sizes(run_dir: Path, metrics: dict) -> np.ndarray:
    avalanches = lib_metrics.read_avalanches(run_dir)
    T = metrics["parameters"]["T"]
    lo = int(0.25 * T)
    mask = (avalanches["t"] >= lo) & (avalanches["t"] <= metrics["t_final"])
    return avalanches["size"][mask]


def profiled_contrast(cell_runs, center_runs, seeds) -> np.ndarray | None:
    """Contraste des exposants profilés à coupure commune (condition 4b)."""
    def mean_sc(runs):
        values = [avalanche_block(runs[s]["metrics"]).get("powerlaw_cutoff", {})
                  .get("cutoff") for s in seeds]
        values = [v for v in values if v]
        return float(np.exp(np.mean(np.log(values)))) if values else None

    sc_cell, sc_center = mean_sc(cell_runs), mean_sc(center_runs)
    if not sc_cell or not sc_center:
        return None
    common = math.sqrt(sc_cell * sc_center)
    diffs = []
    for seed in seeds:
        fits = []
        for runs in (cell_runs, center_runs):
            sizes = window_sizes(runs[seed]["run_dir"], runs[seed]["metrics"])
            fit = lib_metrics.fit_powerlaw_cutoff_fixed_sc(
                sizes.astype(float), cutoff=common)
            fits.append(fit["alpha"] if fit else None)
        if None not in fits:
            diffs.append(fits[0] - fits[1])
    return np.asarray(diffs) if len(diffs) >= 3 else None


def family_defensible(runs: dict[int, dict]) -> tuple[bool, str]:
    """Condition 5, AU SENS LITTÉRAL du protocole v1.1 : LRT tronquée/pure
    p<0,05 (ou hors-portée + Vuong pure/log-normale > 2), ET la log-normale
    jamais strictement préférée à la loi de puissance (Vuong pure/LN < -2).

    AVERTISSEMENT (découvert en confirmation, cf. JOURNAL 27/07) : le seul
    Vuong disponible compare la loi PURE au log-normal, alors que le modèle
    primaire est la TRONQUÉE. Sur cette campagne, la pure est rejetée par
    LRT partout (p<1e-33) — Vuong(pure, LN) est donc structurellement non
    informatif (échoue de façon identique en cellule ET en centre) et ne
    doit pas être lu comme discriminant contre le contraste. Voir
    tail_vs_lognormal_loglik_gap ci-dessous pour le diagnostic correct.
    """
    for seed, run in sorted(runs.items()):
        block = avalanche_block(run["metrics"])
        lrt = (block.get("lrt_cutoff_vs_pure") or {}).get("p_value")
        vuong = (block.get("vuong_pl_vs_ln") or {}).get("z")
        out = block.get("s_c_out_of_range")
        if vuong is not None and vuong < -2:
            return False, f"graine {seed}: log-normale préférée (z={vuong:.1f})"
        ok = (lrt is not None and lrt < 0.05) or (
            out and vuong is not None and vuong > 2)
        if not ok:
            return False, (f"graine {seed}: ni LRT<0,05 (p={lrt}) ni "
                           f"hors-portée+Vuong>2 (z={vuong})")
    return True, "toutes graines"


def tail_vs_lognormal_vuong(runs: dict[int, dict]) -> float | None:
    """Diagnostic correctif à la condition 5 : test de Vuong PROPREMENT dit
    (tronquée vs log-normale, normalisé par la variance de la différence
    point par point — pas une simple comparaison brute de vraisemblances).
    z > 0 : la tronquée (modèle primaire) est favorisée. Recalculé
    directement sur les tailles brutes de chaque run (fenêtre par défaut)."""
    zs = []
    for run in runs.values():
        sizes = window_sizes(run["run_dir"], run["metrics"])
        result = lib_metrics.vuong_trunc_vs_ln(sizes)
        if result:
            zs.append(result["z"])
    return float(np.mean(zs)) if zs else None


def main() -> None:
    confirm = load_plan_runs("confirm")
    if not confirm:
        raise SystemExit("aucun manifeste confirm — lancer le volet 4")

    center_name = next((n for n in confirm if "g050" in n), None)
    if center_name is None:
        raise SystemExit("cellule centre g050 absente du plan confirm")
    center_runs = confirm[center_name]

    for name, runs in confirm.items():
        for seed, run in runs.items():
            if "bootstrap" not in run["metrics"]:
                raise SystemExit(
                    f"{name} graine {seed}: extrait sans --bootstrap "
                    "(obligatoire en confirmation, protocole §incertitudes)")

    ablation = load_plan_runs("ablation_A")
    horizon = load_plan_runs("horizon_double")
    exploration = load_plan_runs("pilotes")
    taille = load_plan_runs("taille_finie")

    rows = []
    print("=== Verdicts confirmatoires (protocole v1.1) ===\n")
    for name, cell_runs in sorted(confirm.items()):
        if name == center_name or "lam100" in name:
            continue
        gamma = next(iter(cell_runs.values()))["metrics"]["parameters"]["gamma"]
        pair = paired_contrast(cell_runs, center_runs)
        if pair is None:
            print(f"{name}: contraste incalculable (graines appariées < 3)")
            continue
        seeds, diffs = pair
        ci = student_ci(diffs)
        conditions: dict[str, tuple[str, str]] = {}

        # 1. IC apparié excluant zéro.
        conditions["1_ic_apparie"] = (
            "PASS" if ci["excludes_zero"] else "FAIL",
            f"Δτ̂={ci['mean']:+.3f} IC95=[{ci['lo']:+.3f},{ci['hi']:+.3f}] "
            f"(n={ci['n']})")

        # 2. Persistance en taille (λ=100) — confirm si présent, sinon
        # exploration taille_finie, sinon N/A.
        lam100_name = next((n for n in confirm if n.startswith(name.split("_")[0])
                            and "lam100" in n), None)
        source = None
        if lam100_name:
            source = (confirm[lam100_name],
                      confirm.get(f"g050_lam100_confirm", center_runs), "confirm")
        else:
            expl_cell = taille.get(f"{name.split('_')[0]}_lam100")
            expl_center = taille.get("g050_lam100")
            if expl_cell and expl_center:
                source = (expl_cell, expl_center, "exploration")
        if source:
            pair100 = paired_contrast(source[0], source[1])
            if pair100:
                _, diffs100 = pair100
                ci100 = student_ci(diffs100)
                same_sign = np.sign(ci100["mean"]) == np.sign(ci["mean"])
                strong = (abs(ci100["mean"]) >= 0.5 * abs(ci["mean"])
                          or ci100["excludes_zero"])
                conditions["2_taille"] = (
                    "PASS" if (same_sign and strong) else "FAIL",
                    f"λ=100 ({source[2]}): Δτ̂={ci100['mean']:+.3f} "
                    f"IC=[{ci100['lo']:+.3f},{ci100['hi']:+.3f}]")
            else:
                conditions["2_taille"] = ("N/A", "λ=100 : appariement impossible")
        else:
            conditions["2_taille"] = ("N/A", "pas de bras λ=100")

        # 3. Stabilité fenêtres + horizon doublé.
        window_means = {}
        for window in WINDOWS:
            pair_w = paired_contrast(
                cell_runs, center_runs,
                value=lambda m, w=window: tau_hat(m, w))
            if pair_w:
                window_means[window] = float(pair_w[1].mean())
        spread = (max(window_means.values()) - min(window_means.values())
                  if len(window_means) == 3 else None)
        window_ok = (spread is not None and abs(ci["mean"]) > 0
                     and spread < 0.5 * abs(ci["mean"]))
        h_cell = horizon.get(f"{name.split('_')[0]}_T8000")
        h_center = horizon.get("g050_T8000")
        horizon_note = "volet 3 absent"
        horizon_ok = None
        if h_cell and h_center:
            pair_h = paired_contrast(h_cell, h_center)
            if pair_h:
                mean_h = float(pair_h[1].mean())
                horizon_ok = (np.sign(mean_h) == np.sign(ci["mean"])
                              and abs(mean_h) >= 0.5 * abs(ci["mean"]))
                horizon_note = f"T=8000: Δτ̂={mean_h:+.3f}"
        status3 = "PASS" if (window_ok and horizon_ok) else (
            "FAIL" if (window_ok is False or horizon_ok is False) else "N/A")
        conditions["3_fenetres_horizon"] = (
            status3,
            f"étendue fenêtres={spread if spread is None else round(spread,3)} "
            f"(seuil {0.5*abs(ci['mean']):.3f}) ; {horizon_note}")

        # 4a. Signe du scan ; 4b. profil à coupure commune.
        pair_scan = paired_contrast(
            cell_runs, center_runs,
            value=lambda m: avalanche_block(m).get("tail_scan", {}).get("alpha")
            if avalanche_block(m).get("tail_scan") else None)
        scan_ok = (pair_scan is not None
                   and np.sign(pair_scan[1].mean()) == np.sign(ci["mean"]))
        prof = profiled_contrast(cell_runs, center_runs, seeds)
        prof_ok = (prof is not None
                   and np.sign(prof.mean()) == np.sign(ci["mean"])
                   and abs(prof.mean()) >= 0.5 * abs(ci["mean"]))
        scan_text = (f"scan Δα={pair_scan[1].mean():+.3f} ({'même' if scan_ok else 'signe opposé'})"
                    if pair_scan else "scan indisponible")
        prof_text = (f"profil s_c commun Δτ̂={prof.mean():+.3f} ({'même' if prof_ok else 'signe/amplitude insuffisants'})"
                    if prof is not None else "profil indisponible")
        conditions["4_seuil_coupure"] = (
            "PASS" if (scan_ok and prof_ok) else "FAIL",
            f"{scan_text} ; {prof_text}")

        # 5. Famille défendable dans les deux cellules (lecture littérale
        # du protocole — voir avertissement dans family_defensible) +
        # diagnostic correctif (tronquée vs log-normale, comparaison
        # directe à parité de paramètres).
        ok_cell, why_cell = family_defensible(cell_runs)
        ok_center, why_center = family_defensible(center_runs)
        vuong_cell = tail_vs_lognormal_vuong(cell_runs)
        vuong_center = tail_vs_lognormal_vuong(center_runs)
        gap_note = (f"[diagnostic correctif : Vuong(tronquée,LN) moyen "
                   f"cellule z={vuong_cell:+.1f}, centre z={vuong_center:+.1f} "
                   f"— tronquée favorisée si ≫0]")
        conditions["5_famille"] = (
            "PASS" if (ok_cell and ok_center) else "FAIL",
            f"cellule: {why_cell} ; centre: {why_center} {gap_note}")

        # 6. Stationnarité et statuts.
        bad = [f"{n}:{s}" for n, runs in ((name, cell_runs), (center_name, center_runs))
               for s, run in runs.items()
               if run["metrics"]["model_status"] != "ok"
               or not is_stationary(run["metrics"])]
        conditions["6_stationnarite"] = (
            "PASS" if not bad else "FAIL",
            "toutes cellules ok" if not bad else "problèmes: " + ",".join(bad))

        # 7. Incertitude combinée (quadrature inter-graines ⊕ bootstrap).
        boot_sds = [((run["metrics"].get("bootstrap") or {}).get("alpha_cutoff")
                     or {}).get("sd") for runs in (cell_runs, center_runs)
                    for run in runs.values()]
        boot_sds = [b for b in boot_sds if b]
        mean_boot = float(np.mean(boot_sds)) if boot_sds else 0.0
        combined = 2.0 * math.sqrt(ci["sd"] ** 2 / ci["n"] + mean_boot ** 2)
        conditions["7_quadrature"] = (
            "PASS" if abs(ci["mean"]) > combined else "FAIL",
            f"|Δτ̂|={abs(ci['mean']):.3f} vs 2√(s²/n+SE²boot)={combined:.3f}")

        # 8. Ablation A_norm : effet résiduel de même signe.
        abl_cell = ablation.get(f"{name.split('_')[0]}_Anorm")
        abl_center = exploration.get("g050") or taille.get("g050_lam30")
        if abl_cell and abl_center:
            pair_a = paired_contrast(abl_cell, abl_center)
            if pair_a:
                mean_a = float(pair_a[1].mean())
                conditions["8_ablation"] = (
                    "PASS" if np.sign(mean_a) == np.sign(ci["mean"]) else "FAIL",
                    f"résiduel à échelle égalisée: Δτ̂={mean_a:+.3f}")
            else:
                conditions["8_ablation"] = ("N/A", "appariement impossible")
        else:
            conditions["8_ablation"] = ("N/A", "volet 5 absent pour ce γ")

        statuses = [status for status, _ in conditions.values()]
        if all(s == "PASS" for s in statuses):
            verdict = "CONFIRMÉ"
        elif (not ci["excludes_zero"] and ci["half_width"] <= INFIRM_HALF_WIDTH):
            verdict = "INFIRMÉ (nul précis)"
        else:
            failing = [k for k, (s, _) in conditions.items() if s == "FAIL"]
            na = [k for k, (s, _) in conditions.items() if s == "N/A"]
            verdict = (f"PARTIEL/INDÉTERMINÉ (échec: {','.join(failing) or '—'}"
                       f" ; n/a: {','.join(na) or '—'})")

        print(f"--- {name} (γ={gamma:.3f}) vs {center_name} ---")
        for key, (status, detail) in conditions.items():
            print(f"  [{status:>4}] {key}: {detail}")
        print(f"  VERDICT : {verdict}\n")

        for key, (status, detail) in conditions.items():
            rows.append({"contrast": name, "gamma": gamma,
                         "delta_tau_mean": ci["mean"], "ci_lo": ci["lo"],
                         "ci_hi": ci["hi"], "n_seeds": ci["n"],
                         "condition": key, "status": status,
                         "detail": detail, "verdict": verdict})

    TABLES.mkdir(parents=True, exist_ok=True)
    if rows:
        with (TABLES / "confirm_contrasts.csv").open("w", newline="",
                                                     encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"table écrite : {TABLES / 'confirm_contrasts.csv'}")


if __name__ == "__main__":
    main()
