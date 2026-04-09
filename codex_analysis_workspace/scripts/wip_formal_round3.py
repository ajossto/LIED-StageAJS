import csv
import json
import math
import sys
from dataclasses import asdict
from pathlib import Path


ROOT = Path("/home/anatole/jupyter/codex_analysis_workspace/data/round3")
FIG_DIR = ROOT / "figures"
SRC = Path("/home/anatole/jupyter/Modèle_sans_banque_wip/src")
ROOT.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(SRC))

from config import SimulationConfig  # noqa: E402
from simulation import Simulation  # noqa: E402


def mean(values):
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def sd(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    m = mean(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / len(vals))


def slope(xs, ys):
    if not xs or len(xs) != len(ys):
        return 0.0
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den


def rolling_mean(values, window):
    out = []
    acc = 0.0
    for i, v in enumerate(values):
        acc += v
        if i >= window:
            acc -= values[i - window]
        out.append(acc / min(i + 1, window))
    return out


def km_rmst(durations, events, horizon):
    pairs = sorted(zip(durations, events), key=lambda x: x[0])
    event_times = sorted({d for d, e in pairs if e and d <= horizon})
    s = 1.0
    prev = 0.0
    area = 0.0
    for t in event_times:
        area += s * (t - prev)
        at_risk = sum(1 for d, _ in pairs if d >= t)
        deaths = sum(1 for d, e in pairs if d == t and e)
        if at_risk > 0:
            s *= (1.0 - deaths / at_risk)
        prev = t
    area += s * max(0.0, horizon - prev)
    return s, area


def cohort_survival(entities, horizon, creation_predicate):
    durations = []
    events = []
    for entity in entities:
        if not creation_predicate(entity.creation_step):
            continue
        if entity.death_step is None:
            durations.append(horizon - entity.creation_step)
            events.append(False)
        else:
            durations.append(entity.death_step - entity.creation_step)
            events.append(True)
    if not durations:
        return {"n": 0, "S_horizon": None, "RMST": None}
    s_h, rmst = km_rmst(durations, events, horizon)
    return {"n": len(durations), "S_horizon": s_h, "RMST": rmst}


def late_cascade_metrics(cascades, start_step):
    sub = [ev for ev in cascades if ev.step >= start_step]
    total_fail = sum(ev.nb_entites_faillie for ev in sub)
    total_cont = sum(ev.nb_contamines for ev in sub)
    total_frag = sum(ev.nb_deja_fragiles for ev in sub)
    return {
        "late_cascades": len(sub),
        "late_secondary_share": (total_cont / total_fail) if total_fail else 0.0,
        "late_secondary_per_fragile": (total_cont / total_frag) if total_frag else 0.0,
        "late_mean_cascade_size": (total_fail / len(sub)) if sub else 0.0,
        "late_max_cascade_size": max((ev.nb_entites_faillie for ev in sub), default=0),
    }


def analyze_sim(sim, late_window):
    steps = sim.current_step
    stats = sim.stats
    late = stats[-late_window:]
    start_late = max(0, steps - late_window)
    xs = [row["step"] for row in late]
    hidden = sim.compute_hidden_fragility()
    hidden_total = sum(hidden.values())
    active_loans = sim.active_loans()
    active_nominal = sum(loan.principal for loan in active_loans)
    entities = list(sim.entities.values())
    failed_lifetimes = [
        entity.death_step - entity.creation_step
        for entity in entities
        if entity.death_step is not None
    ]
    full = cohort_survival(entities, steps, lambda c: True)
    initial = cohort_survival(entities, steps, lambda c: c == 0)
    born_later = cohort_survival(entities, steps, lambda c: c > 0)
    out = {
        "steps": steps,
        "entities_total": len(entities),
        "alive_final": stats[-1]["n_entities_alive"],
        "failures_total": sum(row["n_failures"] for row in stats),
        "mean_extraction_all": mean([row["extraction_total"] for row in stats]),
        "late_credit_tx": mean([row["credit_transactions"] for row in late]),
        "late_active_loans": mean([row["n_prets_actifs"] for row in late]),
        "late_loans_per_alive": mean([
            row["n_prets_actifs"] / row["n_entities_alive"] if row["n_entities_alive"] else 0.0
            for row in late
        ]),
        "late_financial_density": mean([
            row["volume_prets_actifs"] / row["actif_total_systeme"] if row["actif_total_systeme"] else 0.0
            for row in late
        ]),
        "late_failures_per_step": mean([row["n_failures"] for row in late]),
        "late_alive_mean": mean([row["n_entities_alive"] for row in late]),
        "late_credit_slope": slope(xs, [row["credit_transactions"] for row in late]),
        "late_loans_slope": slope(xs, [row["n_prets_actifs"] for row in late]),
        "late_failures_slope": slope(xs, [row["n_failures"] for row in late]),
        "late_alive_slope": slope(xs, [row["n_entities_alive"] for row in late]),
        "hidden_fragility_total_final": hidden_total,
        "hidden_fragility_ratio_final": (hidden_total / active_nominal) if active_nominal else 0.0,
        "mean_lifetime_failed": mean(failed_lifetimes),
        "median_lifetime_failed": sorted(failed_lifetimes)[len(failed_lifetimes) // 2] if failed_lifetimes else None,
        "watched_count": len(sim.collector.watched_entity_ids),
        "rmst_full": full["RMST"],
        "survival_full": full["S_horizon"],
        "rmst_initial": initial["RMST"],
        "survival_initial": initial["S_horizon"],
        "rmst_born_later": born_later["RMST"],
        "survival_born_later": born_later["S_horizon"],
        "n_initial": initial["n"],
        "n_born_later": born_later["n"],
    }
    out.update(late_cascade_metrics(sim.collector.cascades, start_late))
    return out


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def run_case(cfg_kwargs, steps, late_window, seed):
    cfg = SimulationConfig(duree_simulation=steps, seed=seed, **cfg_kwargs)
    sim = Simulation(cfg)
    sim.run(n_steps=steps, verbose=False)
    metrics = analyze_sim(sim, late_window=late_window)
    metrics.update({
        "seed": seed,
        "theta": cfg.theta,
        "lambda_creation": cfg.lambda_creation,
        "n_candidats_pool": cfg.n_candidats_pool,
        "alpha_sigma_brownien": cfg.alpha_sigma_brownien,
        "taux_amortissement": cfg.taux_amortissement,
    })
    return sim, metrics


def aggregate(rows, keys, group_keys):
    grouped = {}
    for row in rows:
        group = tuple(row[key] for key in group_keys)
        grouped.setdefault(group, []).append(row)
    out = []
    for group, members in grouped.items():
        record = {key: value for key, value in zip(group_keys, group)}
        for key in keys:
            vals = [member[key] for member in members]
            record[f"{key}_mean"] = mean(vals)
            record[f"{key}_sd"] = sd(vals)
        out.append(record)
    return out


def build_reference_windows(stats, cascades):
    windows = [(0, 200), (200, 400), (400, 600), (600, 800), (800, 1000), (0, 500), (500, 1000)]
    rows = []
    for start, end in windows:
        sub = stats[start:end]
        sub_c = [ev for ev in cascades if start <= ev.step < end]
        total_fail = sum(ev.nb_entites_faillie for ev in sub_c)
        total_cont = sum(ev.nb_contamines for ev in sub_c)
        total_frag = sum(ev.nb_deja_fragiles for ev in sub_c)
        rows.append({
            "window": f"{start}-{end}",
            "credit_tx_mean": mean([row["credit_transactions"] for row in sub]),
            "active_loans_mean": mean([row["n_prets_actifs"] for row in sub]),
            "failures_mean": mean([row["n_failures"] for row in sub]),
            "alive_mean": mean([row["n_entities_alive"] for row in sub]),
            "n_cascades": len(sub_c),
            "secondary_share": (total_cont / total_fail) if total_fail else 0.0,
            "secondary_per_fragile": (total_cont / total_frag) if total_frag else 0.0,
        })
    return rows


def build_reference_slopes(stats):
    windows = [(0, 500), (500, 1000), (600, 1000), (700, 1000)]
    rows = []
    for start, end in windows:
        sub = stats[start:end]
        xs = [row["step"] for row in sub]
        row = {"window": f"{start}-{end}"}
        for key in ("credit_transactions", "n_prets_actifs", "n_failures", "n_entities_alive"):
            ys = [item[key] for item in sub]
            sl = slope(xs, ys)
            m = mean(ys)
            row[f"{key}_slope"] = sl
            row[f"{key}_slope_over_mean"] = (sl / m) if m else 0.0
        rows.append(row)
    return rows


def make_reference_figure(stats):
    import matplotlib.pyplot as plt

    steps = [row["step"] for row in stats]
    tx = rolling_mean([row["credit_transactions"] for row in stats], 50)
    loans = rolling_mean([row["n_prets_actifs"] for row in stats], 50)
    fails = rolling_mean([row["n_failures"] for row in stats], 50)

    fig, axes = plt.subplots(3, 1, figsize=(9, 9), sharex=True)
    axes[0].plot(steps, tx, color="#005f73")
    axes[0].axvline(500, color="black", linestyle="--", linewidth=1)
    axes[0].set_ylabel("Tx crédit (MA50)")
    axes[0].set_title("WIP référence — flux et stock agrégés")

    axes[1].plot(steps, loans, color="#9b2226")
    axes[1].axvline(500, color="black", linestyle="--", linewidth=1)
    axes[1].set_ylabel("Prêts actifs (MA50)")

    axes[2].plot(steps, fails, color="#ca6702")
    axes[2].axvline(500, color="black", linestyle="--", linewidth=1)
    axes[2].set_ylabel("Faillites/pas (MA50)")
    axes[2].set_xlabel("Pas")

    fig.tight_layout()
    fig.savefig(FIG_DIR / "reference_timeseries.png", dpi=160)
    plt.close(fig)


def heatmap(rows, x_vals, y_vals, x_key, y_key, value_key, title, filename):
    import matplotlib.pyplot as plt

    matrix = []
    for y in y_vals:
        line = []
        for x in x_vals:
            found = next((row for row in rows if row[x_key] == x and row[y_key] == y), None)
            line.append(found.get(value_key, float("nan")) if found else float("nan"))
        matrix.append(line)

    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    im = ax.imshow(matrix, origin="lower", aspect="auto", cmap="YlOrRd")
    ax.set_xticks(range(len(x_vals)))
    ax.set_xticklabels([str(x) for x in x_vals])
    ax.set_yticks(range(len(y_vals)))
    ax.set_yticklabels([str(y) for y in y_vals])
    ax.set_xlabel(x_key)
    ax.set_ylabel(y_key)
    ax.set_title(title)
    for iy, y in enumerate(y_vals):
        for ix, x in enumerate(x_vals):
            val = matrix[iy][ix]
            if math.isfinite(val):
                ax.text(ix, iy, f"{val:.2f}", ha="center", va="center", fontsize=8, color="black")
    fig.colorbar(im, ax=ax, shrink=0.9)
    fig.tight_layout()
    fig.savefig(FIG_DIR / filename, dpi=160)
    plt.close(fig)


def make_k_figure(rows):
    import matplotlib.pyplot as plt

    rows = sorted(rows, key=lambda row: row["n_candidats_pool"])
    ks = [row["n_candidats_pool"] for row in rows]
    dense = [row["late_loans_per_alive_mean"] for row in rows]
    avalanche = [row["late_secondary_per_fragile_mean"] for row in rows]
    failures = [row["late_failures_per_step_mean"] for row in rows]

    fig, ax1 = plt.subplots(figsize=(8, 4.8))
    ax1.plot(ks, dense, marker="o", color="#005f73", label="prêts actifs / entité")
    ax1.set_xlabel("k = n_candidats_pool")
    ax1.set_ylabel("Densité de réseau", color="#005f73")
    ax1.tick_params(axis="y", labelcolor="#005f73")

    ax2 = ax1.twinx()
    ax2.plot(ks, avalanche, marker="s", color="#9b2226", label="secondaires / fragiles")
    ax2.plot(ks, failures, marker="^", color="#ca6702", label="faillites / pas")
    ax2.set_ylabel("Intensité d'avalanche", color="#9b2226")
    ax2.tick_params(axis="y", labelcolor="#9b2226")

    fig.tight_layout()
    fig.savefig(FIG_DIR / "k_sweep_summary.png", dpi=160)
    plt.close(fig)


def main():
    study_manifest = {
        "reference": {"steps": 1000, "seeds": [42, 43, 44, 45], "late_window": 500},
        "k_sweep": {"steps": 400, "seeds": [31, 32], "late_window": 200, "k_values": [1, 2, 3, 4, 5]},
        "theta_lambda": {
            "steps": 400,
            "seeds": [41, 42],
            "late_window": 200,
            "theta_values": [0.2, 0.35, 0.5, 0.7],
            "lambda_values": [1, 2, 3, 4],
            "k": 3,
        },
    }
    (ROOT / "study_manifest.json").write_text(json.dumps(study_manifest, indent=2), encoding="utf-8")

    # Long default study for regime timing and full-pop survival.
    long_rows = []
    reference_seed42_stats = None
    reference_seed42_cascades = None
    for seed in study_manifest["reference"]["seeds"]:
        sim, metrics = run_case({}, steps=study_manifest["reference"]["steps"], late_window=study_manifest["reference"]["late_window"], seed=seed)
        long_rows.append(metrics)
        if seed == 42:
            reference_seed42_stats = list(sim.stats)
            reference_seed42_cascades = list(sim.collector.cascades)
    write_csv(ROOT / "wip_long_default_1000.csv", long_rows)
    write_csv(
        ROOT / "wip_long_default_1000_aggregate.csv",
        aggregate(
            long_rows,
            keys=[
                "alive_final", "late_credit_tx", "late_active_loans", "late_loans_per_alive",
                "late_failures_per_step", "late_secondary_share", "late_secondary_per_fragile",
                "hidden_fragility_ratio_final", "rmst_full", "survival_full",
            ],
            group_keys=["theta", "lambda_creation", "n_candidats_pool"],
        ),
    )

    # k sweep at default theta/lambda
    k_rows = []
    for k in study_manifest["k_sweep"]["k_values"]:
        for seed in study_manifest["k_sweep"]["seeds"]:
            _, metrics = run_case(
                {"n_candidats_pool": k, "theta": 0.35, "lambda_creation": 2},
                steps=study_manifest["k_sweep"]["steps"],
                late_window=study_manifest["k_sweep"]["late_window"],
                seed=seed,
            )
            k_rows.append(metrics)
    write_csv(ROOT / "wip_k_sweep.csv", k_rows)
    k_agg = aggregate(
        k_rows,
        keys=["late_loans_per_alive", "late_failures_per_step", "late_secondary_share", "late_secondary_per_fragile", "alive_final"],
        group_keys=["n_candidats_pool"],
    )
    write_csv(ROOT / "wip_k_sweep_aggregate.csv", k_agg)

    # theta-lambda sweep at k=3
    tl_rows = []
    theta_values = study_manifest["theta_lambda"]["theta_values"]
    lambda_values = study_manifest["theta_lambda"]["lambda_values"]
    for lam in lambda_values:
        for theta in theta_values:
            for seed in study_manifest["theta_lambda"]["seeds"]:
                _, metrics = run_case(
                    {"n_candidats_pool": study_manifest["theta_lambda"]["k"], "theta": theta, "lambda_creation": lam},
                    steps=study_manifest["theta_lambda"]["steps"],
                    late_window=study_manifest["theta_lambda"]["late_window"],
                    seed=seed,
                )
                tl_rows.append(metrics)
    write_csv(ROOT / "wip_theta_lambda_sweep.csv", tl_rows)
    tl_agg = aggregate(
        tl_rows,
        keys=[
            "late_loans_per_alive", "late_financial_density", "late_failures_per_step",
            "late_secondary_share", "late_secondary_per_fragile", "alive_final"
        ],
        group_keys=["lambda_creation", "theta"],
    )
    write_csv(ROOT / "wip_theta_lambda_sweep_aggregate.csv", tl_agg)

    # Reference diagnostics and figures
    if reference_seed42_stats is not None:
        write_csv(ROOT / "reference_windows.csv", build_reference_windows(reference_seed42_stats, reference_seed42_cascades))
        write_csv(ROOT / "reference_slopes.csv", build_reference_slopes(reference_seed42_stats))
        make_reference_figure(reference_seed42_stats)

    heatmap(
        tl_agg,
        x_vals=theta_values,
        y_vals=lambda_values,
        x_key="theta",
        y_key="lambda_creation",
        value_key="late_loans_per_alive_mean",
        title="k=3 — densité de réseau tardive",
        filename="theta_lambda_density_k3.png",
    )
    heatmap(
        tl_agg,
        x_vals=theta_values,
        y_vals=lambda_values,
        x_key="theta",
        y_key="lambda_creation",
        value_key="late_secondary_per_fragile_mean",
        title="k=3 — propagation secondaire tardive",
        filename="theta_lambda_secondary_k3.png",
    )
    heatmap(
        tl_agg,
        x_vals=theta_values,
        y_vals=lambda_values,
        x_key="theta",
        y_key="lambda_creation",
        value_key="late_failures_per_step_mean",
        title="k=3 — faillites tardives par pas",
        filename="theta_lambda_failures_k3.png",
    )
    make_k_figure(k_agg)

    best_dense = sorted(
        [row for row in tl_agg if row["late_secondary_per_fragile_mean"] > 0.05],
        key=lambda row: (row["late_loans_per_alive_mean"], row["late_secondary_per_fragile_mean"]),
        reverse=True,
    )[:10]
    summary = {
        "reference_long_default": long_rows,
        "best_dense_avalanche_k3": best_dense,
        "notes": {
            "secondary_share": "part des faillites d'un pas qui etaient solvables avant la resolution",
            "secondary_per_fragile": "faillites secondaires par faillite deja fragile au debut de la resolution",
        },
    }
    (ROOT / "round3_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
