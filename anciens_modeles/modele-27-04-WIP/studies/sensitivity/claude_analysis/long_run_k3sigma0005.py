"""
Simulation longue de k3_sigma0005_late_entry.
Lance d'abord 5000 pas avec mesure du temps réel par pas, puis 10000 si raisonnable.
Seuil : si > 300 ms/pas en moyenne sur les 200 derniers pas → arrêt à 5000, signaler.
"""
from __future__ import annotations
import json, sys, time, math
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
ROOT = Path(__file__).resolve().parents[4]
SRC  = ROOT / "modele-27-04-WIP" / "src"
sys.path.insert(0, str(SRC))

OUT = HERE / "results" / "claude_long_run_k3sigma0005.json"

PARAMS = {
    "alpha_min": 1.0, "alpha_max": 1.0,
    "alpha_sigma_brownien": 0.005,
    "n_candidats_pool": 3,
    "epsilon": 1e-3,
    "lambda_creation": 2.0,
    "taux_amortissement": 0.0,
    "log_events": False,
    "freq_snapshot": 100,
}
SEEDS     = [42, 7, 123, 0, 1]
N_SHORT   = 5000
N_LONG    = 10000
SLOW_THRESHOLD_MS = 300  # ms/pas


def run_timed(seed: int, n_steps: int, slow_threshold_ms: float) -> dict:
    import importlib
    for mod in ("config", "models", "statistics", "simulation"):
        sys.modules.pop(mod, None)
    config_mod = importlib.import_module("config")
    sim_mod    = importlib.import_module("simulation")
    SimulationConfig = config_mod.SimulationConfig
    Simulation = sim_mod.Simulation

    params = {**PARAMS, "seed": seed, "duree_simulation": n_steps}
    cfg = SimulationConfig(**params)
    sim = Simulation(cfg)

    step_times = []
    ts_alive   = []
    ts_loans   = []
    PROBE_INTERVAL = 200
    t_wall_start = time.perf_counter()
    stopped_early = False

    for step in range(n_steps):
        t0 = time.perf_counter()
        sim.run_step()
        dt_ms = (time.perf_counter() - t0) * 1000
        step_times.append(dt_ms)

        if step % PROBE_INTERVAL == 0 or step == n_steps - 1:
            s = sim.stats[-1]
            alive = s["n_entities_alive"]
            loans = s["n_prets_actifs"]
            ts_alive.append({"step": step, "alive": alive, "loans": loans, "ms_per_step": dt_ms})
            avg_recent = sum(step_times[-PROBE_INTERVAL:]) / min(PROBE_INTERVAL, len(step_times))
            remaining = n_steps - step
            eta_s = avg_recent * remaining / 1000
            print(f"  seed={seed} step={step:5d}/{n_steps} alive={alive:5d} loans={loans:6d} "
                  f"{dt_ms:6.1f}ms/step avg={avg_recent:.0f}ms eta={eta_s:.0f}s")

            if avg_recent > slow_threshold_ms and step > 500:
                print(f"  ARRÊT PRÉCOCE: {avg_recent:.0f} ms/pas > seuil {slow_threshold_ms} ms")
                stopped_early = True
                break

    total_s = time.perf_counter() - t_wall_start
    s_final = sim.stats[-1]
    diag = {}
    try:
        from run_simulation import detect_regime_diagnostics
        ts = sim.stats
        diag = detect_regime_diagnostics(
            [s["n_entities_alive"] for s in ts],
            [s["actif_total_systeme"] for s in ts],
            [s["n_prets_actifs"] for s in ts],
            [s["n_failures"] for s in ts],
            [ind.densite_financiere for ind in sim.collector.indicators],
        )
    except Exception as e:
        diag = {"error": str(e)}

    return {
        "seed": seed, "n_steps_requested": n_steps,
        "n_steps_done": sim.current_step,
        "stopped_early": stopped_early,
        "total_wall_s": total_s,
        "avg_ms_per_step": sum(step_times) / len(step_times),
        "max_ms_per_step": max(step_times),
        "final_alive": s_final["n_entities_alive"],
        "final_loans": s_final["n_prets_actifs"],
        "final_densite_fin": sim.collector.indicators[-1].densite_financiere,
        "final_gini": sim.collector.indicators[-1].gini_actif_total,
        "bounded_tail": diag.get("bounded_tail"),
        "alive_tail_slope_rel": diag.get("alive_tail_slope_rel"),
        "probe": ts_alive,
        "params": PARAMS,
    }


def main():
    existing = json.loads(OUT.read_text()) if OUT.exists() else []
    done_seeds = {e["seed"] for e in existing}
    results = list(existing)

    for seed in SEEDS:
        if seed in done_seeds:
            print(f"seed={seed} déjà fait, skip.")
            continue
        print(f"\n=== seed={seed}, {N_SHORT} pas (probe) ===")
        r = run_timed(seed, N_SHORT, SLOW_THRESHOLD_MS)
        results.append(r)
        OUT.write_text(json.dumps(results, indent=2))

        avg_ms = r["avg_ms_per_step"]
        print(f"  -> avg={avg_ms:.1f}ms/pas, total={r['total_wall_s']:.0f}s")
        slope = r["alive_tail_slope_rel"]
        slope_str = f"{slope:.3f}" if slope is not None else "N/A"
        print(f"  -> alive={r['final_alive']}, loans={r['final_loans']}, "
              f"bounded={r['bounded_tail']}, slope_alive={slope_str}")

        if not r["stopped_early"] and avg_ms < SLOW_THRESHOLD_MS:
            eta_10k = avg_ms * (N_LONG - N_SHORT) / 1000
            print(f"  -> OK pour 10000 pas, ETA {N_LONG} pas : +{eta_10k:.0f}s")
        else:
            print(f"  -> Trop lent ou arrêt précoce, pas d'extension à {N_LONG} pas pour ce seed.")

    print(f"\nRésultats: {OUT}")
    print("\nRésumé :")
    for r in results:
        slope = r["alive_tail_slope_rel"]
        slope_str = f"{slope:.3f}" if slope is not None else "N/A"
        print(f"  seed={r['seed']}: bounded={r['bounded_tail']} slope={slope_str} "
              f"alive={r['final_alive']} avg={r['avg_ms_per_step']:.0f}ms/pas "
              f"t={r['total_wall_s']:.0f}s {'[STOP]' if r['stopped_early'] else ''}")


if __name__ == "__main__":
    main()
