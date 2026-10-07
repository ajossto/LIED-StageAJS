"""Pilote (pas un script de campagne figé) : contrôle géométrique (§12) et
balayage sigma (§13) demandés après l'analyse du run baseline T=3000. Lance
1 run de contrôle (target_rule=geometric, sinon baseline) + 8 runs
(sigma in {0.01,0.03,0.05,0.10} x seed in {0,1}), tous T=1000
(burn-in 375, cf. stationarité observée sur le run baseline), rho=1,
gamma=0.5, delta=0.01, K0=25, arithmetic sauf le contrôle. Parallélisé
(<=6 processus, cf. feedback_parallel_batch_jobs). Rapporte, par run :
Gini(K)/log_std(K) final, part de variance du log-revenu venant de deg_out
(fenêtre stationnaire), alpha_density (moyenne/écart-type inter-snapshots
+ à x_min/2), tau_hat des avalanches (vuong_trunc_vs_ln), branching_ratio,
size_max, statut de population.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

RESULTS = ROOT / "results" / "pilot_sigma_control"


def _run_one(spec: dict) -> dict:
    from m4_2b import Config, run_and_save
    import lib_metrics
    import interest_income

    label = spec["label"]
    directory = RESULTS / label
    cfg = Config(
        gamma=0.5, delta=0.01, sigma=spec["sigma"], lam=spec.get("lam", 30.0), K0=25.0,
        seed=spec["seed"], T=spec["T"], target_rule=spec["target_rule"], rho=1.0,
    )
    t0 = time.perf_counter()
    sim, summary = run_and_save(cfg, directory, snapshot_every=25, individual_every=0)
    elapsed = time.perf_counter() - t0

    T = spec["T"]
    lo, hi = 375, T  # burn-in fixe, cf. stationarité T/8~375 observée sur le run baseline T=3000
    series = lib_metrics.read_series(directory)
    avalanches = lib_metrics.read_avalanches(directory)
    mask = (avalanches["t"] >= lo) & (avalanches["t"] <= hi)
    sizes = avalanches["size"][mask]

    out = {"label": label, "elapsed_s": elapsed, "status": summary["status"],
           "population_final": summary["population_final"], "loans_final": summary["loans_final"]}
    out.update({k: spec[k] for k in ("sigma", "seed", "target_rule")})

    if len(sizes[sizes >= 2]) >= 100:
        vuong = lib_metrics.vuong_trunc_vs_ln(sizes, s_min=2)
        cutoff = lib_metrics.fit_powerlaw_cutoff(sizes[sizes >= 2], s_min=2)
        out["avalanche_n_tail"] = int(len(sizes[sizes >= 2]))
        out["avalanche_tau_hat"] = cutoff["alpha"] if cutoff else None
        out["avalanche_cutoff"] = cutoff["cutoff"] if cutoff else None
        out["avalanche_size_max"] = int(sizes.max())
        out["vuong_trunc_vs_ln_z"] = vuong["z"] if vuong else None
    else:
        out["avalanche_n_tail"] = int(len(sizes[sizes >= 2]))
        out["avalanche_tau_hat"] = None

    if series:
        pop_mask = (series["t"] >= lo) & (series["t"] <= hi)
        pop_mean = float(series["pop"][pop_mask].mean()) if pop_mask.sum() else float("nan")
        av_metrics = lib_metrics.window_avalanche_metrics(avalanches, lo, hi, pop_mean, s_min=2)
        out["branching_ratio"] = av_metrics.get("branching_ratio")
        wsm = lib_metrics.window_series_metrics(series, lo, hi)
        out["merge_share"] = wsm.get("market", {}).get("merge_share")
        out["pop_mean"] = pop_mean

    snaps = interest_income.load_all_entity_snapshots(directory, t_min=lo, t_max=hi)
    net_snaps = interest_income.load_all_network_snapshots(directory, t_min=lo, t_max=hi)
    if snaps:
        last_t, last_snap = snaps[-1]
        K = last_snap["K"]
        out["K_gini_final"] = float(lib_metrics._gini(K))
        positive_K = K[K > 0]
        out["K_log_std_final"] = float(np.log(positive_K).std()) if len(positive_K) > 10 else float("nan")

        alphas, alphas_half, shares_deg = [], [], []
        for t, snap in snaps:
            fit = interest_income.fit_income_distribution(snap["int_in"], min_n=80)
            if fit["identifiable"] and fit["tail_powerlaw"] is not None:
                alphas.append(fit["tail_powerlaw"]["alpha_density"])
                half = fit["tail_threshold_stability"].get("x_min_times_0.5")
                if half:
                    alphas_half.append(half["alpha_density"])
        for t, net in net_snaps:
            decomp = interest_income.decompose_tail_sources(net)
            lv = decomp.get("log_variance_decomposition")
            if lv:
                shares_deg.append(lv["share_from_deg_out"])

        out["n_snapshots_window"] = len(snaps)
        out["alpha_density_mean"] = float(np.mean(alphas)) if alphas else None
        out["alpha_density_std"] = float(np.std(alphas)) if len(alphas) > 1 else None
        out["alpha_density_half_threshold_mean"] = float(np.mean(alphas_half)) if alphas_half else None
        out["share_from_deg_out_mean"] = float(np.mean(shares_deg)) if shares_deg else None

    (directory / "pilot_summary.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out


def main() -> None:
    specs = [
        {"label": "control_geometric", "sigma": 0.01, "seed": 0, "target_rule": "geometric", "T": 1000},
    ]
    for sigma in (0.01, 0.03, 0.05, 0.10):
        for seed in (0, 1):
            specs.append({
                "label": f"sigma{sigma}_seed{seed}", "sigma": sigma, "seed": seed,
                "target_rule": "arithmetic", "T": 1000,
            })

    RESULTS.mkdir(parents=True, exist_ok=True)
    with mp.Pool(processes=min(6, len(specs))) as pool:
        results = pool.map(_run_one, specs)

    (RESULTS / "all_results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False))
    print(f"{'label':22s} {'elapsed':>8s} {'pop':>6s} {'K_gini':>7s} {'K_logstd':>9s} "
          f"{'sh_deg':>7s} {'alpha':>7s} {'alpha/2':>8s} {'tau_hat':>8s} {'branch':>7s} {'merge%':>7s}")
    for r in results:
        print(
            f"{r['label']:22s} {r['elapsed_s']:8.1f} {r.get('population_final', 0):6d} "
            f"{r.get('K_gini_final', float('nan')):7.3f} {r.get('K_log_std_final', float('nan')):9.3f} "
            f"{r.get('share_from_deg_out_mean') if r.get('share_from_deg_out_mean') is not None else float('nan'):7.3f} "
            f"{r.get('alpha_density_mean') if r.get('alpha_density_mean') is not None else float('nan'):7.3f} "
            f"{r.get('alpha_density_half_threshold_mean') if r.get('alpha_density_half_threshold_mean') is not None else float('nan'):8.3f} "
            f"{r.get('avalanche_tau_hat') if r.get('avalanche_tau_hat') is not None else float('nan'):8.3f} "
            f"{r.get('branching_ratio') if r.get('branching_ratio') is not None else float('nan'):7.3f} "
            f"{100*r.get('merge_share', 0) if r.get('merge_share') is not None else float('nan'):7.2f}"
        )


if __name__ == "__main__":
    main()
