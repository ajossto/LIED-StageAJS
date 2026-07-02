#!/usr/bin/env python3
"""Recodage Python du modèle CSA de Wright (2009).

Le code suit l'appendice Mathematica de l'article: agents avec monnaie,
employeur, salaire reçu, attente salariale, règles de hiring/effective demand/
firm income/wage payment and firing. Les figures reproduisent les diagnostics
numériques de l'article.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
from scipy.special import erf


def ensure_dirs(root: Path) -> tuple[Path, Path]:
    figures = root / "figures"
    results = root / "results"
    figures.mkdir(exist_ok=True)
    results.mkdir(exist_ok=True)
    return figures, results


@dataclass
class CSAEconomy:
    n: int = 1000
    initial_money: float = 10.0
    initial_expectation: float = 10.0
    seed: int = 1
    rng: np.random.Generator = field(init=False)
    money: np.ndarray = field(init=False)
    employer: np.ndarray = field(init=False)
    wage: np.ndarray = field(init=False)
    demand: np.ndarray = field(init=False)
    employees: list[set[int]] = field(init=False)
    effective_demand: float = 0.0
    firm_birth_month: np.ndarray = field(init=False)
    month_index: int = 0
    revenue_year: np.ndarray = field(init=False)
    wages_year: np.ndarray = field(init=False)
    income_year: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
        self.rng = np.random.default_rng(self.seed)
        self.money = np.full(self.n, self.initial_money, dtype=float)
        self.employer = np.full(self.n, -1, dtype=int)
        self.wage = np.full(self.n, self.initial_expectation, dtype=float)
        self.demand = np.full(self.n, self.initial_expectation, dtype=float)
        self.employees = [set() for _ in range(self.n)]
        self.firm_birth_month = np.full(self.n, -1, dtype=int)
        self.revenue_year = np.zeros(self.n)
        self.wages_year = np.zeros(self.n)
        self.income_year = np.zeros(self.n)

    def is_employer(self, i: int) -> bool:
        return bool(self.employees[i])

    def is_employee(self, i: int) -> bool:
        return self.employer[i] >= 0

    def class_counts(self) -> tuple[int, int, int]:
        capitalists = sum(1 for e in self.employees if e)
        workers = int(np.sum(self.employer >= 0))
        unemployed = self.n - capitalists - workers
        return workers, capitalists, unemployed

    def firm_sizes(self) -> list[int]:
        return [len(e) for e in self.employees if e]

    def select_employer(self, agent: int) -> int:
        mask = (self.employer < 0) & (self.money > 0)
        mask[agent] = False
        idx = np.flatnonzero(mask)
        if idx.size == 0:
            return -1
        weights = self.money[idx]
        total = float(weights.sum())
        if total <= 0:
            return -1
        position = int(np.searchsorted(np.cumsum(weights), self.rng.random() * total, side="right"))
        return int(idx[min(position, idx.size - 1)])

    def join_firm(self, agent: int, employer: int, demises: list[int]) -> None:
        if self.employer[agent] >= 0:
            old = int(self.employer[agent])
            self.leave_firm(agent, old, demises)
        was_empty = not self.employees[employer]
        self.employer[agent] = employer
        self.employees[employer].add(agent)
        if was_empty:
            self.firm_birth_month[employer] = self.month_index

    def leave_firm(self, agent: int, employer: int, demises: list[int]) -> None:
        self.employer[agent] = -1
        self.employees[employer].discard(agent)
        if not self.employees[employer] and self.firm_birth_month[employer] >= 0:
            demises.append(self.month_index - int(self.firm_birth_month[employer]) + 1)
            self.firm_birth_month[employer] = -1

    def hiring_rule(self, agent: int, demises: list[int]) -> None:
        if self.is_employer(agent):
            return
        h = self.select_employer(agent)
        if h < 0:
            return
        wage_demand = self.demand[agent]
        offer = min(self.rng.uniform(wage_demand, 2.0 * wage_demand), self.money[h])
        if offer > wage_demand:
            self.join_firm(agent, h, demises)
            self.demand[agent] = offer
        if not self.is_employee(agent):
            self.demand[agent] = self.rng.random() * self.demand[agent]

    def effective_demand_rule(self, agent: int) -> None:
        expenditure = self.rng.random() * self.money[agent]
        self.money[agent] -= expenditure
        self.effective_demand += expenditure

    def firm_income_rule(self, agent: int) -> None:
        if not (self.is_employee(agent) or self.is_employer(agent)):
            return
        income = self.rng.random() * self.effective_demand
        self.effective_demand -= income
        recipient = int(self.employer[agent]) if self.is_employee(agent) else agent
        self.money[recipient] += income
        self.revenue_year[recipient] += income
        self.income_year[recipient] += income

    def wage_payment_and_firing_rule(self, agent: int, demises: list[int]) -> None:
        if not self.is_employer(agent):
            return
        for emp in list(self.employees[agent]):
            payment = self.demand[emp]
            if payment <= self.money[agent]:
                self.money[agent] -= payment
                self.money[emp] += payment
                self.wage[emp] = payment
                self.wages_year[agent] += payment
                self.income_year[emp] += payment
            else:
                self.leave_firm(emp, agent, demises)
                self.demand[emp] = self.wage[emp]

    def process_agent(self, agent: int, demises: list[int]) -> None:
        self.hiring_rule(agent, demises)
        self.effective_demand_rule(agent)
        self.firm_income_rule(agent)
        self.wage_payment_and_firing_rule(agent, demises)

    def one_month(self) -> list[int]:
        self.month_index += 1
        demises: list[int] = []
        for agent in self.rng.integers(0, self.n, size=self.n):
            self.process_agent(int(agent), demises)
        return demises

    def reset_year_accounts(self) -> None:
        self.revenue_year[:] = 0.0
        self.wages_year[:] = 0.0
        self.income_year[:] = 0.0


def ccdf(data: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = np.sort(data[data > 0])
    if len(x) == 0:
        return x, x
    y = 1.0 - np.arange(len(x)) / len(x)
    return x, y


def fit_power_alpha_discrete(values: np.ndarray, xmin: float = 1.0) -> float:
    x = values[values >= xmin]
    if len(x) < 5:
        return float("nan")
    return float(len(x) / np.sum(np.log(x / (xmin - 0.5))))


def run_simulation(args: argparse.Namespace) -> dict:
    econ = CSAEconomy(args.n, args.initial_money, args.initial_expectation, args.seed)
    stats_out: dict[str, list] = {
        "class_counts": [],
        "firm_sizes_monthly": [],
        "demises_monthly": [],
        "lifespans": [],
        "firm_growth_emp": [],
        "firm_growth_sales": [],
        "profit_rates": [],
        "gdp": [],
        "income": [],
        "wealth": [],
        "wage_share": [],
    }
    prev_sizes: dict[int, int] = {}
    prev_sales: dict[int, float] = {}

    for year in range(args.years):
        econ.reset_year_accounts()
        month_demises = []
        for _ in range(12):
            demises = econ.one_month()
            month_demises.append(len(demises))
            stats_out["lifespans"].extend(demises)
            if year >= args.burn_years:
                stats_out["firm_sizes_monthly"].extend(econ.firm_sizes())
        if year >= args.burn_years:
            stats_out["class_counts"].append(econ.class_counts())
            stats_out["demises_monthly"].extend(month_demises)
            current_sizes = {i: len(e) for i, e in enumerate(econ.employees) if e}
            current_sales = {i: float(econ.revenue_year[i]) for i in current_sizes}
            for i, s in current_sizes.items():
                if i in prev_sizes and prev_sizes[i] > 0:
                    stats_out["firm_growth_emp"].append(float(np.log(s / prev_sizes[i])))
                if i in prev_sales and prev_sales[i] > 0 and current_sales[i] > 0:
                    stats_out["firm_growth_sales"].append(float(np.log(current_sales[i] / prev_sales[i])))
            prev_sizes = current_sizes
            prev_sales = current_sales
            firms = np.flatnonzero(np.array([bool(e) for e in econ.employees]))
            valid = firms[econ.wages_year[firms] > 0]
            stats_out["profit_rates"].extend((100.0 * (econ.revenue_year[valid] / econ.wages_year[valid] - 1.0)).tolist())
            gdp = float(econ.revenue_year.sum())
            stats_out["gdp"].append(gdp)
            if gdp > 0:
                stats_out["wage_share"].append(float(econ.wages_year.sum() / gdp))
            stats_out["income"].extend(econ.income_year[econ.income_year > 0].tolist())
            stats_out["wealth"].extend(econ.money[econ.money > 0].tolist())
        else:
            prev_sizes = {i: len(e) for i, e in enumerate(econ.employees) if e}
            prev_sales = {i: float(econ.revenue_year[i]) for i in prev_sizes}

    return stats_out


def plot_all(stats_out: dict, figures: Path) -> dict:
    summary: dict[str, float | int | list] = {}
    class_counts = np.asarray(stats_out["class_counts"], dtype=float)
    labels = ["workers", "capitalists", "unemployed"]
    fig, axes = plt.subplots(1, 3, figsize=(10, 3))
    for j, ax in enumerate(axes):
        data = class_counts[:, j]
        ax.hist(data, bins=20, alpha=0.75)
        mu, sd = float(np.mean(data)), float(np.std(data))
        xs = np.linspace(data.min(), data.max(), 200)
        if sd > 0:
            ax.plot(xs, stats.norm.pdf(xs, mu, sd) * len(data) * (xs[1] - xs[0]), color="k")
        ax.set_title(f"{labels[j]}\nmu={mu:.1f}, sd={sd:.1f}")
        summary[f"class_{labels[j]}_mean"] = mu
    fig.tight_layout()
    fig.savefig(figures / "figure1_class_sizes.pdf")
    plt.close(fig)

    firm_sizes = np.asarray(stats_out["firm_sizes_monthly"], dtype=float)
    alpha = fit_power_alpha_discrete(firm_sizes, xmin=1)
    summary["firm_size_alpha"] = alpha
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.5))
    bins = np.arange(0.5, max(2, int(firm_sizes.max()) + 1.5), 1)
    axes[0].hist(firm_sizes, bins=bins)
    axes[0].set_title(fr"Firm sizes, $\hat\alpha={alpha:.2f}$")
    counts, edges = np.histogram(firm_sizes, bins=bins)
    centers = (edges[:-1] + edges[1:]) / 2
    mask = counts > 0
    axes[1].loglog(centers[mask], counts[mask], "o", ms=3)
    axes[1].set_xlabel("firm size")
    axes[1].set_ylabel("frequency")
    fig.tight_layout()
    fig.savefig(figures / "figure2_firm_sizes.pdf")
    plt.close(fig)

    def simple_hist(name: str, data: np.ndarray, bins: int | np.ndarray, title: str, logy: bool = False) -> None:
        fig, ax = plt.subplots(figsize=(5.5, 3.5))
        ax.hist(data, bins=bins, alpha=0.8)
        ax.set_title(title)
        if logy:
            ax.set_yscale("log")
        ax.grid(alpha=0.2)
        fig.tight_layout()
        fig.savefig(figures / name)
        plt.close(fig)

    demises = np.asarray(stats_out["demises_monthly"], dtype=float)
    simple_hist("figure3_demises.pdf", demises, np.arange(demises.min() - 0.5, demises.max() + 1.5, 1), "Firm demises per month")
    summary["demises_per_month_mean"] = float(demises.mean())

    lifespans = np.asarray(stats_out["lifespans"], dtype=float)
    if len(lifespans):
        simple_hist("figure4_lifespans.pdf", lifespans, np.arange(0.5, lifespans.max() + 2.5, 2), "Firm lifespans", logy=True)
        summary["lifespan_mean_months"] = float(lifespans.mean())

    growth_emp = np.asarray(stats_out["firm_growth_emp"], dtype=float)
    simple_hist("figure5_growth_employees.pdf", growth_emp[np.isfinite(growth_emp)], 50, "Firm growth, employees", logy=True)
    growth_sales = np.asarray(stats_out["firm_growth_sales"], dtype=float)
    simple_hist("figure6_growth_sales.pdf", growth_sales[np.isfinite(growth_sales)], 50, "Firm growth, sales", logy=True)

    profits = np.asarray(stats_out["profit_rates"], dtype=float)
    profits = profits[np.isfinite(profits)]
    profits_clip = profits[(profits > -100) & (profits < np.percentile(profits, 99.5))]
    simple_hist("figure7_profit_rates.pdf", profits_clip, 60, "Profit rates")
    summary["profit_rate_median"] = float(np.median(profits_clip))

    gdp = np.asarray(stats_out["gdp"], dtype=float)
    log_gdp = np.log(gdp[gdp > 0])
    simple_hist("figure8_log_gdp.pdf", log_gdp, 25, "log GDP")
    summary["log_gdp_mean"] = float(log_gdp.mean())
    growth_gdp = np.diff(np.log(gdp[gdp > 0]))
    simple_hist("figure9_gdp_growth.pdf", growth_gdp, 25, "GDP log growth")
    summary["gdp_growth_mean"] = float(growth_gdp.mean()) if len(growth_gdp) else float("nan")

    recessions = []
    k = 0
    for g in growth_gdp:
        if g < 0:
            k += 1
        elif k:
            recessions.append(k)
            k = 0
    if k:
        recessions.append(k)
    if recessions:
        simple_hist("figure10_recessions.pdf", np.asarray(recessions), np.arange(0.5, max(recessions) + 1.5, 1), "Recession durations", logy=True)
    summary["recessions"] = recessions

    income = np.asarray(stats_out["income"], dtype=float)
    wealth = np.asarray(stats_out["wealth"], dtype=float)
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.5))
    for ax, data, title in [(axes[0], income, "Income ccdf"), (axes[1], wealth, "Wealth ccdf")]:
        x, y = ccdf(data)
        ax.loglog(x, y)
        ax.set_title(title)
        ax.set_xlabel("money")
        ax.set_ylabel("P(X>=x)")
        ax.grid(alpha=0.2, which="both")
    fig.tight_layout()
    fig.savefig(figures / "figure11_12_income_wealth.pdf")
    plt.close(fig)

    wage_share = np.asarray(stats_out["wage_share"], dtype=float)
    simple_hist("figure13_wage_share.pdf", wage_share, 20, "Wage share")
    summary["wage_share_mean"] = float(wage_share.mean())
    summary["wage_share_std"] = float(wage_share.std())
    return summary


def wage_seed_sensitivity(args: argparse.Namespace, figures: Path) -> list[dict]:
    rows = []
    seeds = np.arange(0.5, 20.5, 1.5)
    for expectation in seeds:
        local = argparse.Namespace(
            n=100,
            initial_money=10.0,
            initial_expectation=float(expectation),
            seed=args.seed + int(expectation * 10),
            years=max(35, args.sensitivity_years),
            burn_years=max(10, args.sensitivity_burn),
        )
        out = run_simulation(local)
        ws = np.asarray(out["wage_share"], dtype=float)
        rows.append({"initial_expectation": float(expectation), "mean": float(ws.mean()), "std": float(ws.std())})
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.errorbar([r["initial_expectation"] for r in rows], [r["mean"] for r in rows], yerr=[r["std"] for r in rows], fmt="o")
    ax.set_xlabel("initial wage expectation")
    ax.set_ylabel("mean wage share")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(figures / "figure14_wage_seed_sensitivity.pdf")
    plt.close(fig)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260701)
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--initial-money", type=float, default=10.0)
    parser.add_argument("--initial-expectation", type=float, default=10.0)
    parser.add_argument("--years", type=int, default=130)
    parser.add_argument("--burn-years", type=int, default=30)
    parser.add_argument("--sensitivity-years", type=int, default=35)
    parser.add_argument("--sensitivity-burn", type=int, default=10)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    figures, results = ensure_dirs(root)
    stats_out = run_simulation(args)
    summary = plot_all(stats_out, figures)
    summary["seed_sensitivity"] = wage_seed_sensitivity(args, figures)
    summary["seed"] = args.seed
    summary["n"] = args.n
    summary["years"] = args.years
    summary["burn_years"] = args.burn_years
    summary["notes"] = [
        "Recodage basé sur l'appendice Mathematica.",
        "Les ajustements sont graphiques/descriptifs, comme dans l'article.",
        "La sélection pondérée d'un employeur exclut l'agent actif pour respecter e_i != i, point implicite dans le texte.",
    ]
    (results / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
