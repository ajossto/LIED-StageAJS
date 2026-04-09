import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path("/home/anatole/jupyter/codex_analysis_workspace/data/round3")
FIG_DIR = ROOT / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

REFERENCE_STATS = Path(
    "/home/anatole/jupyter/Modèle_sans_banque_wip/src/resultats/"
    "simu_20260402_142017_scenario_base_d6a1d52/csv/stats_legeres.csv"
)


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def to_float_rows(rows):
    out = []
    for row in rows:
        casted = {}
        for key, value in row.items():
            if value is None or value == "":
                casted[key] = None
            else:
                try:
                    if "." in value or "e" in value.lower():
                        casted[key] = float(value)
                    else:
                        casted[key] = int(value)
                except Exception:
                    casted[key] = value
        out.append(casted)
    return out


def rolling_mean(values, window):
    out = []
    acc = 0.0
    for i, value in enumerate(values):
        acc += value
        if i >= window:
            acc -= values[i - window]
        out.append(acc / min(i + 1, window))
    return out


def make_reference_timeseries():
    rows = to_float_rows(read_csv(REFERENCE_STATS))
    steps = [row["step"] for row in rows]
    tx = rolling_mean([row["credit_transactions"] for row in rows], 50)
    loans = rolling_mean([row["n_prets_actifs"] for row in rows], 50)
    fails = rolling_mean([row["n_failures"] for row in rows], 50)

    fig, axes = plt.subplots(3, 1, figsize=(9.5, 8.5), sharex=True)
    series = [
        (tx, "#005f73", "Transactions de crédit / pas (MA50)"),
        (loans, "#9b2226", "Prêts actifs (MA50)"),
        (fails, "#ca6702", "Faillites / pas (MA50)"),
    ]
    for ax, (values, color, ylabel) in zip(axes, series):
        ax.plot(steps, values, color=color, linewidth=2)
        ax.axvline(500, color="black", linestyle="--", linewidth=1)
        ax.set_ylabel(ylabel)
        ax.grid(alpha=0.25)
    axes[0].set_title("WIP référence — flux et stocks, avec rupture nette avant/après t = 500")
    axes[-1].set_xlabel("Pas")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "reference_timeseries.png", dpi=180)
    plt.close(fig)


def make_heatmap(csv_name, value_key, title, filename):
    rows = to_float_rows(read_csv(ROOT / csv_name))
    theta_values = sorted({row["theta"] for row in rows})
    lambda_values = sorted({row["lambda_creation"] for row in rows})
    matrix = []
    for lam in lambda_values:
        line = []
        for theta in theta_values:
            row = next(r for r in rows if r["theta"] == theta and r["lambda_creation"] == lam)
            line.append(row[value_key])
        matrix.append(line)

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    im = ax.imshow(matrix, origin="lower", aspect="auto", cmap="YlOrRd")
    ax.set_xticks(range(len(theta_values)))
    ax.set_xticklabels([str(theta) for theta in theta_values])
    ax.set_yticks(range(len(lambda_values)))
    ax.set_yticklabels([str(lam) for lam in lambda_values])
    ax.set_xlabel(r"$\theta$")
    ax.set_ylabel(r"$\lambda$")
    ax.set_title(title)
    for iy, lam in enumerate(lambda_values):
        for ix, theta in enumerate(theta_values):
            ax.text(ix, iy, f"{matrix[iy][ix]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, shrink=0.92)
    fig.tight_layout()
    fig.savefig(FIG_DIR / filename, dpi=180)
    plt.close(fig)


def make_k_figure():
    rows = to_float_rows(read_csv(ROOT / "wip_k_sweep_aggregate.csv"))
    rows.sort(key=lambda row: row["n_candidats_pool"])
    ks = [row["n_candidats_pool"] for row in rows]
    dense = [row["late_loans_per_alive_mean"] for row in rows]
    sec = [row["late_secondary_per_fragile_mean"] for row in rows]
    fail = [row["late_failures_per_step_mean"] for row in rows]

    fig, axes = plt.subplots(2, 1, figsize=(8.5, 7.0), sharex=True)
    axes[0].plot(ks, dense, marker="o", color="#005f73", linewidth=2)
    axes[0].set_ylabel("Prêts actifs / entité")
    axes[0].set_title("Sweep en k à θ = 0.35, λ = 2")
    axes[0].grid(alpha=0.25)

    axes[1].plot(ks, sec, marker="s", color="#9b2226", linewidth=2, label="secondaires / fragiles")
    axes[1].plot(ks, fail, marker="^", color="#ca6702", linewidth=2, label="faillites / pas")
    axes[1].set_xlabel("k = n_candidats_pool")
    axes[1].set_ylabel("Intensité d'avalanche")
    axes[1].legend(frameon=False)
    axes[1].grid(alpha=0.25)

    fig.tight_layout()
    fig.savefig(FIG_DIR / "k_sweep_summary.png", dpi=180)
    plt.close(fig)


def build_summary():
    rows = to_float_rows(read_csv(ROOT / "wip_theta_lambda_sweep_aggregate.csv"))
    candidates = [
        row for row in rows
        if row["late_loans_per_alive_mean"] >= 3.0 and row["late_secondary_per_fragile_mean"] >= 0.08
    ]
    candidates.sort(
        key=lambda row: (row["late_loans_per_alive_mean"], row["late_secondary_per_fragile_mean"]),
        reverse=True,
    )
    summary = {
        "top_dense_avalanche_regimes": candidates[:10],
        "metric_definitions": {
            "late_secondary_share_mean": "part des faillites tardives d'un pas qui etaient solvables avant la resolution",
            "late_secondary_per_fragile_mean": "faillites secondaires tardives par faillite deja fragile au debut de la resolution",
        },
    }
    (ROOT / "round3_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main():
    make_reference_timeseries()
    make_heatmap(
        "wip_theta_lambda_sweep_aggregate.csv",
        "late_loans_per_alive_mean",
        "k = 3 — densité tardive du réseau",
        "theta_lambda_density_k3.png",
    )
    make_heatmap(
        "wip_theta_lambda_sweep_aggregate.csv",
        "late_secondary_per_fragile_mean",
        "k = 3 — propagation secondaire tardive",
        "theta_lambda_secondary_k3.png",
    )
    make_heatmap(
        "wip_theta_lambda_sweep_aggregate.csv",
        "late_failures_per_step_mean",
        "k = 3 — faillites tardives par pas",
        "theta_lambda_failures_k3.png",
    )
    make_k_figure()
    build_summary()


if __name__ == "__main__":
    main()
