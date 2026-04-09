import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path("/home/anatole/jupyter/codex_analysis_workspace/data/round4")
FIG_DIR = ROOT / "figures"
ROUND3_ROOT = Path("/home/anatole/jupyter/codex_analysis_workspace/data/round3")
SRC = Path("/home/anatole/jupyter/Modèle_sans_banque_wip/src")

ROOT.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(SRC))

from config import SimulationConfig  # noqa: E402
from simulation import Simulation  # noqa: E402


def mean(values):
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def pop_sd(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    m = mean(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / len(vals))


def sample_sd(values):
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return 0.0
    m = mean(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))


def slope(xs, ys):
    if not xs or len(xs) != len(ys):
        return 0.0
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den


def read_csv(path):
    with open(path, encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def t_critical_975(df):
    table = {
        1: 12.706,
        2: 4.303,
        3: 3.182,
        4: 2.776,
        5: 2.571,
        6: 2.447,
        7: 2.365,
        8: 2.306,
        9: 2.262,
        10: 2.228,
        11: 2.201,
        12: 2.179,
        13: 2.160,
        14: 2.145,
        15: 2.131,
        16: 2.120,
        17: 2.110,
        18: 2.101,
        19: 2.093,
        20: 2.086,
        21: 2.080,
        22: 2.074,
        23: 2.069,
        24: 2.064,
        25: 2.060,
        26: 2.056,
        27: 2.052,
        28: 2.048,
        29: 2.045,
        30: 2.042,
    }
    if df <= 0:
        return None
    if df in table:
        return table[df]
    return 1.96


def ci95_halfwidth(values):
    vals = [v for v in values if v is not None]
    n = len(vals)
    if n < 2:
        return 0.0
    tcrit = t_critical_975(n - 1)
    return tcrit * sample_sd(vals) / math.sqrt(n)


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


def hidden_fragility_geometric_prediction(delta_exo, gamma_loan):
    if gamma_loan is None:
        return None
    gamma_loan = max(0.0, min(1.0, gamma_loan))
    denom = 1.0 - (1.0 - gamma_loan) * (1.0 - delta_exo)
    if denom <= 0:
        return None
    return 1.0 - gamma_loan / denom


def augment_metrics(metrics, delta_exo=0.1):
    alive = metrics["late_alive_mean"]
    beta = (metrics["late_credit_tx"] / alive) if alive else 0.0
    hazard = (metrics["late_failures_per_step"] / alive) if alive else 0.0
    n_star = (metrics["lambda_creation"] / hazard) if hazard else None
    gamma_loan = (beta / metrics["late_loans_per_alive"]) if metrics["late_loans_per_alive"] else None
    metrics["beta_late"] = beta
    metrics["hazard_late"] = hazard
    metrics["n_star_pred"] = n_star
    metrics["n_star_gap"] = (metrics["alive_final"] - n_star) if n_star is not None else None
    metrics["loan_exit_late"] = gamma_loan
    metrics["hidden_fragility_ratio_geometric_pred"] = hidden_fragility_geometric_prediction(delta_exo, gamma_loan)
    pred_h = metrics["hidden_fragility_ratio_geometric_pred"]
    metrics["hidden_fragility_ratio_gap"] = (
        metrics["hidden_fragility_ratio_final"] - pred_h if pred_h is not None else None
    )
    return metrics


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
    augment_metrics(metrics, delta_exo=cfg.taux_depreciation_exo)
    return sim, metrics


def aggregate_with_ci(rows, keys, group_keys):
    grouped = {}
    for row in rows:
        group = tuple(row[key] for key in group_keys)
        grouped.setdefault(group, []).append(row)
    out = []
    for group, members in grouped.items():
        record = {key: value for key, value in zip(group_keys, group)}
        record["n_runs"] = len(members)
        for key in keys:
            vals = [member[key] for member in members]
            record[f"{key}_mean"] = mean(vals)
            record[f"{key}_sd"] = pop_sd(vals)
            record[f"{key}_ci95_halfwidth"] = ci95_halfwidth(vals)
        out.append(record)
    return out


def borrower_to_lender_graph(sim):
    exposures = defaultdict(float)
    active = [e for e in sim.active_entities()]
    equities = {e.entity_id: max(e.actif_total - e.passif_bilan, 0.0) for e in active}
    for loan in sim.active_loans():
        lender = sim.get_entity(loan.lender_id)
        borrower = sim.get_entity(loan.borrower_id)
        if not lender.alive or not borrower.alive:
            continue
        exposures[(borrower.entity_id, lender.entity_id)] += loan.principal
    adjacency = defaultdict(list)
    weights = defaultdict(list)
    eps = sim.config.epsilon
    for (src, dst), exposure in exposures.items():
        equity = equities.get(dst, 0.0)
        weight = 1.0 if equity <= eps else min(1.0, exposure / equity)
        adjacency[src].append(dst)
        weights[src].append((dst, weight))
    return adjacency, weights


def largest_scc_size(adjacency):
    index = 0
    stack = []
    on_stack = set()
    indices = {}
    lowlinks = {}
    largest = 0
    nodes = set(adjacency)
    for dsts in adjacency.values():
        nodes.update(dsts)

    def strongconnect(node):
        nonlocal index, largest
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for nxt in adjacency.get(node, []):
            if nxt not in indices:
                strongconnect(nxt)
                lowlinks[node] = min(lowlinks[node], lowlinks[nxt])
            elif nxt in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[nxt])

        if lowlinks[node] == indices[node]:
            size = 0
            while True:
                current = stack.pop()
                on_stack.remove(current)
                size += 1
                if current == node:
                    break
            largest = max(largest, size)

    for node in nodes:
        if node not in indices:
            strongconnect(node)
    return largest


def spectral_radius_power(weights, iterations=30):
    nodes = set(weights)
    for outs in weights.values():
        for dst, _ in outs:
            nodes.add(dst)
    if not nodes:
        return 0.0
    vec = {node: 1.0 for node in nodes}
    lam = 0.0
    for _ in range(iterations):
        new = {node: 0.0 for node in nodes}
        for src, outs in weights.items():
            src_val = vec.get(src, 0.0)
            if src_val == 0.0:
                continue
            for dst, weight in outs:
                new[dst] += weight * src_val
        lam = max(new.values()) if new else 0.0
        if lam <= 1e-12:
            return 0.0
        vec = {node: value / lam for node, value in new.items()}
    return lam


def run_step_with_reference_capture(sim, sample_every, records):
    sim._reset_step_flows()
    sim._update_alphas()
    spawn_count = sim.spawn_new_entities()
    extraction_total = sim.extract_from_nature()
    interest_paid = sim.pay_interest_phase()
    amortissement_total = sim.pay_amortization_phase()
    sim.apply_depreciation()
    credit_transactions = sim.credit_market_iteration()

    if sim.current_step % sample_every == 0:
        adjacency, weights = borrower_to_lender_graph(sim)
        largest_scc = largest_scc_size(adjacency)
        rho = 0.0 if largest_scc <= 1 else spectral_radius_power(weights)
        alive = sim.active_entities()
        records.append({
            "step": sim.current_step,
            "alive_pre_cascade": len(alive),
            "active_loans_pre_cascade": len(sim.active_loans()),
            "rho_B_pre_cascade": rho,
            "largest_scc_pre_cascade": largest_scc,
            "mean_internal_rate_pre_cascade": mean([sim.compute_internal_rate(e) for e in alive if e.passif_total > sim.config.epsilon]) or 0.0,
        })

    cascade_totals, cascade_event = sim.resolve_cascades()
    auto_invest_total = sim.auto_invest_end_of_turn()
    light_stats = sim._collect_light_stats(
        spawn_count,
        extraction_total,
        interest_paid,
        amortissement_total,
        credit_transactions,
        auto_invest_total,
        cascade_totals,
    )
    sim.collector.record_step(sim, cascade_event, sim._step_flows)
    sim.current_step += 1

    if records and records[-1]["step"] == sim.current_step - 1:
        record = records[-1]
        record["credit_transactions"] = credit_transactions
        record["failures_this_step"] = light_stats["n_failures"]
        if cascade_event is None:
            record["secondary_share_step"] = 0.0
            record["secondary_per_fragile_step"] = 0.0
        else:
            total_fail = cascade_event.nb_entites_faillie
            frag = cascade_event.nb_deja_fragiles
            record["secondary_share_step"] = (cascade_event.nb_contamines / total_fail) if total_fail else 0.0
            record["secondary_per_fragile_step"] = (cascade_event.nb_contamines / frag) if frag else 0.0
    return light_stats


def build_reference_spectral(seed=42, steps=1000, late_window=500, sample_every=10):
    cfg = SimulationConfig(duree_simulation=steps, seed=seed)
    sim = Simulation(cfg)
    records = []
    for _ in range(steps):
        run_step_with_reference_capture(sim, sample_every=sample_every, records=records)

    metrics = analyze_sim(sim, late_window=late_window)
    metrics.update({
        "seed": seed,
        "theta": cfg.theta,
        "lambda_creation": cfg.lambda_creation,
        "n_candidats_pool": cfg.n_candidats_pool,
        "alpha_sigma_brownien": cfg.alpha_sigma_brownien,
        "taux_amortissement": cfg.taux_amortissement,
    })
    augment_metrics(metrics, delta_exo=cfg.taux_depreciation_exo)
    write_csv(ROOT / "reference_spectral_timeseries.csv", records)

    summary_rows = []
    for start, end in ((0, 500), (500, 1000)):
        sub = [row for row in records if start <= row["step"] < end]
        summary_rows.append({
            "window": f"{start}-{end}",
            "rho_B_mean": mean([row["rho_B_pre_cascade"] for row in sub]),
            "largest_scc_mean": mean([row["largest_scc_pre_cascade"] for row in sub]),
            "largest_scc_max": max((row["largest_scc_pre_cascade"] for row in sub), default=0),
            "secondary_per_fragile_mean": mean([row["secondary_per_fragile_step"] for row in sub]),
            "failures_mean": mean([row["failures_this_step"] for row in sub]),
        })
    write_csv(ROOT / "reference_spectral_summary.csv", summary_rows)
    return metrics, records, summary_rows


def load_round3_rows():
    rows = []
    for name in ("wip_k_sweep.csv", "wip_theta_lambda_sweep.csv", "wip_long_default_1000.csv"):
        for row in read_csv(ROUND3_ROOT / name):
            numeric = {}
            for key, value in row.items():
                if value in ("", "None"):
                    numeric[key] = None
                else:
                    try:
                        numeric[key] = float(value)
                    except ValueError:
                        numeric[key] = value
            numeric["source_file"] = name
            augment_metrics(numeric)
            rows.append(numeric)
    return rows


def build_population_fixed_point_validation(round3_rows):
    rows = []
    for row in round3_rows:
        if row["n_star_pred"] is None:
            continue
        rows.append({
            "source_file": row["source_file"],
            "seed": row.get("seed"),
            "steps": row["steps"],
            "n_candidats_pool": row["n_candidats_pool"],
            "theta": row["theta"],
            "lambda_creation": row["lambda_creation"],
            "alive_final": row["alive_final"],
            "late_alive_mean": row["late_alive_mean"],
            "hazard_late": row["hazard_late"],
            "n_star_pred": row["n_star_pred"],
            "prediction_error_alive_final": row["alive_final"] - row["n_star_pred"],
        })
    write_csv(ROOT / "population_fixed_point_validation.csv", rows)
    informative = [row for row in rows if row["hazard_late"] is not None and row["hazard_late"] >= 0.002]
    write_csv(ROOT / "population_fixed_point_validation_informative.csv", informative)
    abs_errors = [abs(row["prediction_error_alive_final"]) for row in informative]
    return {
        "n_rows_total": len(rows),
        "n_rows_informative": len(informative),
        "hazard_threshold_informative": 0.002,
        "mae_alive_final": mean(abs_errors),
        "mean_abs_pct_error_alive_final": mean([
            abs(row["prediction_error_alive_final"]) / row["alive_final"]
            for row in informative if row["alive_final"]
        ]),
    }


def build_hidden_fragility_validation(round3_rows):
    rows = []
    for row in round3_rows:
        pred = row["hidden_fragility_ratio_geometric_pred"]
        obs = row["hidden_fragility_ratio_final"]
        if pred is None or obs is None:
            continue
        rows.append({
            "source_file": row["source_file"],
            "seed": row.get("seed"),
            "steps": row["steps"],
            "n_candidats_pool": row["n_candidats_pool"],
            "theta": row["theta"],
            "lambda_creation": row["lambda_creation"],
            "beta_late": row["beta_late"],
            "loan_exit_late": row["loan_exit_late"],
            "hidden_fragility_ratio_observed": obs,
            "hidden_fragility_ratio_predicted": pred,
            "prediction_gap": obs - pred,
        })
    write_csv(ROOT / "hidden_fragility_validation.csv", rows)
    abs_errors = [abs(row["prediction_gap"]) for row in rows]
    return {
        "n_rows": len(rows),
        "mae_hidden_fragility_ratio": mean(abs_errors),
    }


def build_horizon_comparison():
    short_rows = []
    for seed in (42, 43, 44, 45):
        _, metrics = run_case(
            {"n_candidats_pool": 3, "theta": 0.35, "lambda_creation": 2},
            steps=400,
            late_window=200,
            seed=seed,
        )
        short_rows.append(metrics)

    long_rows = []
    for row in read_csv(ROUND3_ROOT / "wip_long_default_1000.csv"):
        if int(float(row["seed"])) not in (42, 43, 44, 45):
            continue
        numeric = {}
        for key, value in row.items():
            if value in ("", "None"):
                numeric[key] = None
            else:
                try:
                    numeric[key] = float(value)
                except ValueError:
                    numeric[key] = value
        augment_metrics(numeric)
        long_rows.append(numeric)

    rows = []
    for label, members in (("400", short_rows), ("1000", long_rows)):
        for member in members:
            rows.append({
                "horizon": label,
                "seed": member["seed"],
                "alive_final": member["alive_final"],
                "late_alive_mean": member["late_alive_mean"],
                "late_active_loans": member["late_active_loans"],
                "late_loans_per_alive": member["late_loans_per_alive"],
                "beta_late": member["beta_late"],
                "hazard_late": member["hazard_late"],
                "hidden_fragility_ratio_final": member["hidden_fragility_ratio_final"],
            })
    write_csv(ROOT / "default_horizon_comparison.csv", rows)
    agg = aggregate_with_ci(
        rows,
        keys=[
            "alive_final",
            "late_alive_mean",
            "late_active_loans",
            "late_loans_per_alive",
            "beta_late",
            "hazard_late",
            "hidden_fragility_ratio_final",
        ],
        group_keys=["horizon"],
    )
    write_csv(ROOT / "default_horizon_comparison_aggregate.csv", agg)
    return agg


def make_reference_spectral_figure(records):
    import matplotlib.pyplot as plt

    steps = [row["step"] for row in records]
    rho = [row["rho_B_pre_cascade"] for row in records]
    sec = [row["secondary_per_fragile_step"] for row in records]
    scc = [row["largest_scc_pre_cascade"] for row in records]

    fig, axes = plt.subplots(3, 1, figsize=(9.2, 8.6), sharex=True)
    axes[0].plot(steps, rho, color="#264653", linewidth=2)
    axes[0].set_ylabel(r"$\rho(B_t)$")
    axes[0].set_title("Run de reference seed=42 — diagnostic spectral et propagation")
    axes[0].axvline(500, color="black", linestyle="--", linewidth=1)

    axes[1].plot(steps, sec, color="#9b2226", linewidth=2)
    axes[1].set_ylabel("Second./fragiles")
    axes[1].axvline(500, color="black", linestyle="--", linewidth=1)

    axes[2].plot(steps, scc, color="#ca6702", linewidth=2)
    axes[2].set_ylabel("SCC max")
    axes[2].set_xlabel("Pas")
    axes[2].axvline(500, color="black", linestyle="--", linewidth=1)

    fig.tight_layout()
    fig.savefig(FIG_DIR / "reference_spectral_timeseries.png", dpi=180)
    plt.close(fig)


def make_k_multiseed_figure(rows):
    import matplotlib.pyplot as plt

    rows = sorted(rows, key=lambda row: row["n_candidats_pool"])
    ks = [row["n_candidats_pool"] for row in rows]

    beta = [row["beta_late_mean"] for row in rows]
    beta_ci = [row["beta_late_ci95_halfwidth"] for row in rows]
    hazard = [row["hazard_late_mean"] for row in rows]
    hazard_ci = [row["hazard_late_ci95_halfwidth"] for row in rows]
    loans = [row["late_loans_per_alive_mean"] for row in rows]
    loans_ci = [row["late_loans_per_alive_ci95_halfwidth"] for row in rows]

    fig, axes = plt.subplots(3, 1, figsize=(8.4, 9.0), sharex=True)
    axes[0].errorbar(ks, beta, yerr=beta_ci, marker="o", color="#005f73", linewidth=2, capsize=4)
    axes[0].set_ylabel(r"$\beta_k$")
    axes[0].set_title("k-sweep round 4 — 10 seeds, IC 95% t-Student")

    axes[1].errorbar(ks, hazard, yerr=hazard_ci, marker="s", color="#9b2226", linewidth=2, capsize=4)
    axes[1].set_ylabel(r"$h^*$")

    axes[2].errorbar(ks, loans, yerr=loans_ci, marker="^", color="#ca6702", linewidth=2, capsize=4)
    axes[2].set_ylabel("Prêts / entité")
    axes[2].set_xlabel("k = n_candidats_pool")

    fig.tight_layout()
    fig.savefig(FIG_DIR / "k_sweep_multiseed_summary.png", dpi=180)
    plt.close(fig)


def make_population_fixed_point_figure(rows):
    import matplotlib.pyplot as plt

    actual = [float(row["alive_final"]) for row in rows]
    pred = [float(row["n_star_pred"]) for row in rows]
    fig, ax = plt.subplots(figsize=(6.8, 5.6))
    ax.scatter(pred, actual, color="#005f73", alpha=0.75)
    if pred and actual:
        low = min(min(pred), min(actual))
        high = max(max(pred), max(actual))
        ax.plot([low, high], [low, high], linestyle="--", color="black", linewidth=1)
    ax.set_xlabel(r"Prediction $N^* = \lambda / h^*$")
    ax.set_ylabel("Entites vivantes finales")
    ax.set_title("Validation du point fixe de population sur les jeux round 3")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "population_fixed_point_validation.png", dpi=180)
    plt.close(fig)


def make_hidden_fragility_figure(rows):
    import matplotlib.pyplot as plt

    pred = [float(row["hidden_fragility_ratio_predicted"]) for row in rows]
    obs = [float(row["hidden_fragility_ratio_observed"]) for row in rows]
    fig, ax = plt.subplots(figsize=(6.8, 5.6))
    ax.scatter(pred, obs, color="#9b2226", alpha=0.75)
    if pred and obs:
        low = min(min(pred), min(obs))
        high = max(max(pred), max(obs))
        ax.plot([low, high], [low, high], linestyle="--", color="black", linewidth=1)
    ax.set_xlabel("Fragilite cachee predite")
    ax.set_ylabel("Fragilite cachee observee")
    ax.set_title("Fermeture geometrique de la fragilite cachee")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "hidden_fragility_validation.png", dpi=180)
    plt.close(fig)


def main():
    study_manifest = {
        "reference_spectral": {"seed": 42, "steps": 1000, "late_window": 500, "sample_every": 10},
        "k_sweep_multiseed": {
            "steps": 400,
            "late_window": 200,
            "theta": 0.35,
            "lambda_creation": 2,
            "k_values": [1, 2, 3, 4, 5],
            "seeds": [31, 32, 33, 34, 35, 36, 37, 38, 39, 40],
        },
        "default_horizon_compare": {"seeds": [42, 43, 44, 45], "horizons": [400, 1000]},
    }
    (ROOT / "study_manifest.json").write_text(json.dumps(study_manifest, indent=2), encoding="utf-8")

    k_rows = []
    for k in study_manifest["k_sweep_multiseed"]["k_values"]:
        for seed in study_manifest["k_sweep_multiseed"]["seeds"]:
            _, metrics = run_case(
                {
                    "n_candidats_pool": k,
                    "theta": study_manifest["k_sweep_multiseed"]["theta"],
                    "lambda_creation": study_manifest["k_sweep_multiseed"]["lambda_creation"],
                },
                steps=study_manifest["k_sweep_multiseed"]["steps"],
                late_window=study_manifest["k_sweep_multiseed"]["late_window"],
                seed=seed,
            )
            k_rows.append(metrics)
    write_csv(ROOT / "k_sweep_multiseed.csv", k_rows)

    k_agg = aggregate_with_ci(
        k_rows,
        keys=[
            "late_loans_per_alive",
            "late_failures_per_step",
            "late_secondary_share",
            "late_secondary_per_fragile",
            "alive_final",
            "beta_late",
            "hazard_late",
            "n_star_pred",
            "hidden_fragility_ratio_final",
        ],
        group_keys=["n_candidats_pool"],
    )
    write_csv(ROOT / "k_sweep_multiseed_aggregate.csv", k_agg)

    reference_metrics, reference_records, reference_summary = build_reference_spectral(
        seed=study_manifest["reference_spectral"]["seed"],
        steps=study_manifest["reference_spectral"]["steps"],
        late_window=study_manifest["reference_spectral"]["late_window"],
        sample_every=study_manifest["reference_spectral"]["sample_every"],
    )

    round3_rows = load_round3_rows()
    pop_summary = build_population_fixed_point_validation(round3_rows)
    hidden_summary = build_hidden_fragility_validation(round3_rows)
    horizon_summary = build_horizon_comparison()

    make_reference_spectral_figure(reference_records)
    make_k_multiseed_figure(k_agg)
    make_population_fixed_point_figure(read_csv(ROOT / "population_fixed_point_validation_informative.csv"))
    make_hidden_fragility_figure(read_csv(ROOT / "hidden_fragility_validation.csv"))

    summary = {
        "k_sweep_multiseed": k_agg,
        "reference_spectral": {
            "metrics": reference_metrics,
            "windows": reference_summary,
        },
        "population_fixed_point_validation": pop_summary,
        "hidden_fragility_validation": hidden_summary,
        "default_horizon_comparison": horizon_summary,
        "notes": {
            "beta_late": "taux de creation de prets tardif par entite vivante, approxime par credit_transactions / N",
            "hazard_late": "hazard tardif de faillite par entite, approxime par failures_per_step / N",
            "n_star_pred": "point fixe de population N* = lambda_creation / hazard_late",
            "loan_exit_late": "hazard tardif de sortie d'un pret, approxime par beta_late / (prets actifs par entite)",
            "hidden_fragility_ratio_geometric_pred": "fermeture geometrique H/Q = 1 - gamma_loan / (1 - (1-gamma_loan)(1-delta_exo))",
        },
    }
    (ROOT / "round4_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
