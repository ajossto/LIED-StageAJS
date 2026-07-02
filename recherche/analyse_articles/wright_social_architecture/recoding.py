#!/usr/bin/env python3
"""Recodage Python du modèle SR de Wright, The Social Architecture of Capitalism.

Cette variante suit les règles SR1/S1/H1/E1/M1/F1/W1 de l'article de 2004:
N=1000, M=100000, salaires uniformes dans [10,90] par défaut.
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
class SREconomy:
    n: int = 1000
    total_money: float = 100000.0
    wage_min: int = 10
    wage_max: int = 90
    seed: int = 1
    rng: np.random.Generator = field(init=False)
    money: np.ndarray = field(init=False)
    employer: np.ndarray = field(init=False)
    employees: list[set[int]] = field(init=False)
    market_value: float = 0.0
    month_index: int = 0
    firm_birth_month: np.ndarray = field(init=False)
    revenue_year: np.ndarray = field(init=False)
    wages_year: np.ndarray = field(init=False)
    income_year: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
        self.rng = np.random.default_rng(self.seed)
        self.money = np.full(self.n, self.total_money / self.n, dtype=float)
        self.employer = np.full(self.n, -1, dtype=int)
        self.employees = [set() for _ in range(self.n)]
        self.firm_birth_month = np.full(self.n, -1, dtype=int)
        self.revenue_year = np.zeros(self.n)
        self.wages_year = np.zeros(self.n)
        self.income_year = np.zeros(self.n)

    @property
    def avg_wage(self) -> float:
        return 0.5 * (self.wage_min + self.wage_max)

    def is_employer(self, i: int) -> bool:
        return bool(self.employees[i])

    def is_employee(self, i: int) -> bool:
        return self.employer[i] >= 0

    def is_unemployed(self, i: int) -> bool:
        return (not self.is_employer(i)) and self.employer[i] < 0

    def class_counts(self) -> tuple[int, int, int]:
        capitalists = sum(1 for e in self.employees if e)
        workers = int(np.sum(self.employer >= 0))
        unemployed = self.n - capitalists - workers
        return workers, capitalists, unemployed

    def firm_sizes(self) -> list[int]:
        return [len(e) for e in self.employees if e]

    def select_potential_employer(self, active: int) -> int:
        # H=C∪U: tous les non-travailleurs. On exclut l'acteur actif pour éviter e_i=i.
        mask = self.employer < 0
        mask[active] = False
        idx = np.flatnonzero(mask & (self.money > 0))
        if idx.size == 0:
            return -1
        weights = self.money[idx]
        total = float(weights.sum())
        if total <= 0:
            return -1
        position = int(np.searchsorted(np.cumsum(weights), self.rng.random() * total, side="right"))
        return int(idx[min(position, idx.size - 1)])

    def join(self, worker: int, capitalist: int) -> None:
        was_empty = not self.employees[capitalist]
        self.employer[worker] = capitalist
        self.employees[capitalist].add(worker)
        if was_empty:
            self.firm_birth_month[capitalist] = self.month_index

    def fire(self, worker: int, capitalist: int, demises: list[int]) -> None:
        self.employer[worker] = -1
        self.employees[capitalist].discard(worker)
        if not self.employees[capitalist] and self.firm_birth_month[capitalist] >= 0:
            demises.append(self.month_index - int(self.firm_birth_month[capitalist]) + 1)
            self.firm_birth_month[capitalist] = -1

    def hiring_rule(self, active: int) -> None:
        if not self.is_unemployed(active):
            return
        c = self.select_potential_employer(active)
        if c >= 0 and self.money[c] > self.avg_wage:
            self.join(active, c)

    def expenditure_rule(self, active: int) -> None:
        b = int(self.rng.integers(0, self.n - 1))
        if b >= active:
            b += 1
        m = self.rng.random() * self.money[b]
        self.money[b] -= m
        self.market_value += m

    def market_sample_rule(self, active: int) -> None:
        if self.is_unemployed(active):
            return
        m = self.rng.random() * self.market_value
        self.market_value -= m
        recipient = int(self.employer[active]) if self.is_employee(active) else active
        self.money[recipient] += m
        self.revenue_year[recipient] += m
        self.income_year[recipient] += m

    def firing_rule(self, active: int, demises: list[int]) -> None:
        if not self.is_employer(active):
            return
        workers = list(self.employees[active])
        u = max(len(workers) - int(np.floor(self.money[active] / self.avg_wage)), 0)
        if u <= 0:
            return
        chosen = self.rng.choice(np.array(workers, dtype=int), size=min(u, len(workers)), replace=False)
        for worker in chosen:
            self.fire(int(worker), active, demises)

    def wage_payment_rule(self, active: int) -> None:
        if not self.is_employer(active):
            return
        for worker in list(self.employees[active]):
            if self.money[active] <= 0:
                wage = 0.0
            elif self.money[active] < self.wage_min:
                wage = self.rng.uniform(0.0, self.money[active])
            else:
                wage = float(self.rng.integers(self.wage_min, self.wage_max + 1))
                wage = min(wage, self.money[active])
            self.money[active] -= wage
            self.money[worker] += wage
            self.wages_year[active] += wage
            self.income_year[worker] += wage

    def step(self, demises: list[int]) -> None:
        active = int(self.rng.integers(0, self.n))
        self.hiring_rule(active)
        self.expenditure_rule(active)
        self.market_sample_rule(active)
        self.firing_rule(active, demises)
        self.wage_payment_rule(active)

    def one_month(self) -> list[int]:
        self.month_index += 1
        demises: list[int] = []
        for _ in range(self.n):
            self.step(demises)
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


def fit_power_alpha(values: np.ndarray, xmin: float = 1.0) -> float:
    x = values[values >= xmin]
    if len(x) < 5:
        return float("nan")
    return float(len(x) / np.sum(np.log(x / (xmin - 0.5))))


def run_simulation(args: argparse.Namespace) -> dict:
    econ = SREconomy(args.n, args.total_money, args.wage_min, args.wage_max, args.seed)
    out: dict[str, list] = {
        "class_counts": [],
        "firm_sizes_monthly": [],
        "demises_monthly": [],
        "lifespans": [],
        "firm_growth_emp": [],
        "gdp": [],
        "gdp_growth": [],
        "income": [],
        "wealth": [],
        "wage_share": [],
        "profit_rates": [],
        "profit_capital_weights": [],
    }
    prev_sizes: dict[int, int] = {}
    prev_gdp: float | None = None
    for year in range(args.years):
        econ.reset_year_accounts()
        month_demises = []
        for _ in range(12):
            demises = econ.one_month()
            month_demises.append(len(demises))
            out["lifespans"].extend(demises)
            if year >= args.burn_years:
                out["firm_sizes_monthly"].extend(econ.firm_sizes())
        gdp = float(econ.revenue_year.sum())
        if year >= args.burn_years:
            out["class_counts"].append(econ.class_counts())
            out["demises_monthly"].extend(month_demises)
            current_sizes = {i: len(e) for i, e in enumerate(econ.employees) if e}
            for i, s in current_sizes.items():
                if i in prev_sizes and prev_sizes[i] > 0:
                    out["firm_growth_emp"].append(float(np.log(s / prev_sizes[i])))
            prev_sizes = current_sizes
            out["gdp"].append(gdp)
            if prev_gdp is not None and prev_gdp > 0 and gdp > 0:
                out["gdp_growth"].append(float(np.log(gdp / prev_gdp)))
            if gdp > 0:
                out["wage_share"].append(float(econ.wages_year.sum() / gdp))
            out["income"].extend(econ.income_year[econ.income_year > 0].tolist())
            out["wealth"].extend(econ.money[econ.money > 0].tolist())
            firms = np.flatnonzero(np.array([bool(e) for e in econ.employees]))
            valid = firms[econ.wages_year[firms] > 0]
            pr = 100.0 * (econ.revenue_year[valid] / econ.wages_year[valid] - 1.0)
            out["profit_rates"].extend(pr.tolist())
            out["profit_capital_weights"].extend(econ.wages_year[valid].tolist())
        else:
            prev_sizes = {i: len(e) for i, e in enumerate(econ.employees) if e}
        if gdp > 0:
            prev_gdp = gdp
    return out


def profit_pdf_mixture(x: np.ndarray, mu1: float, var1: float, mu2: float, var2: float, alpha: float, n: int) -> np.ndarray:
    # Approximation numérique discrète de l'intégrale Eq. (11), suffisante pour superposer
    # la forme théorique sans dépendre d'intégrateurs lourds.
    s_values = np.arange(2, n + 1, dtype=float)
    weights = alpha * s_values ** (-(1.0 + alpha)) / (1.0 - n ** (-alpha))
    y = 1.0 + x[:, None] / 100.0
    s = s_values[None, :]
    mu_r = 12.0 * s * mu1
    var_r = 12.0 * s * var1
    mu_w = 12.0 * (s - 1.0) * mu2
    var_w = 12.0 * (s - 1.0) * var2
    # Approximation delta-method du ratio de normales, plus stable que la formule imprimée.
    mean_ratio = mu_r / mu_w
    var_ratio = var_r / (mu_w**2) + (mu_r**2) * var_w / (mu_w**4)
    dens = stats.norm.pdf(y, mean_ratio, np.sqrt(var_ratio)) / 100.0
    return np.sum(dens * weights[None, :], axis=1)


def plot_all(out: dict, args: argparse.Namespace, figures: Path) -> dict:
    summary: dict[str, float | int | list] = {}
    class_counts = np.asarray(out["class_counts"], dtype=float)
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
    fig.savefig(figures / "figure1_class_distribution.pdf")
    plt.close(fig)

    firm_sizes = np.asarray(out["firm_sizes_monthly"], dtype=float)
    alpha = fit_power_alpha(firm_sizes, xmin=1)
    summary["firm_size_alpha"] = alpha
    fig, ax = plt.subplots(figsize=(5.5, 4))
    counts, edges = np.histogram(firm_sizes, bins=np.arange(0.5, firm_sizes.max() + 1.5, 1))
    centers = (edges[:-1] + edges[1:]) / 2
    mask = counts > 0
    ax.loglog(centers[mask], counts[mask], "o", ms=3)
    ax.set_title(fr"Firm size, $\hat\alpha={alpha:.2f}$")
    ax.set_xlabel("firm size")
    ax.set_ylabel("frequency")
    ax.grid(alpha=0.2, which="both")
    fig.tight_layout()
    fig.savefig(figures / "figure2_firm_size.pdf")
    plt.close(fig)

    def hist(name: str, data: np.ndarray, bins, title: str, logy: bool = False, weights=None) -> None:
        fig, ax = plt.subplots(figsize=(5.5, 3.5))
        ax.hist(data, bins=bins, weights=weights, alpha=0.8)
        ax.set_title(title)
        if logy:
            ax.set_yscale("log")
        ax.grid(alpha=0.2)
        fig.tight_layout()
        fig.savefig(figures / name)
        plt.close(fig)

    growth = np.asarray(out["firm_growth_emp"], dtype=float)
    hist("figure3_firm_growth.pdf", growth[np.isfinite(growth)], 50, "Firm size growth", logy=True)
    demises = np.asarray(out["demises_monthly"], dtype=float)
    hist("figure4_firm_demises.pdf", demises, np.arange(demises.min() - 0.5, demises.max() + 1.5, 1), "Firm demises/month", logy=True)
    gdp_growth = np.asarray(out["gdp_growth"], dtype=float)
    hist("figure5_gdp_growth.pdf", gdp_growth, 30, "GDP growth", logy=True)

    recessions = []
    k = 0
    for g in gdp_growth:
        if g < 0:
            k += 1
        elif k:
            recessions.append(k)
            k = 0
    if k:
        recessions.append(k)
    if recessions:
        hist("figure6_recessions.pdf", np.asarray(recessions), np.arange(0.5, max(recessions) + 1.5, 1), "Recession durations", logy=True)
    summary["recessions"] = recessions

    wage_share = np.asarray(out["wage_share"], dtype=float)
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.plot(wage_share, label="wage share")
    ax.plot(1 - wage_share, label="profit share")
    ax.set_ylim(0, 1)
    ax.legend()
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(figures / "figure7_income_shares.pdf")
    plt.close(fig)
    summary["wage_share_mean"] = float(wage_share.mean())

    income = np.asarray(out["income"], dtype=float)
    wealth = np.asarray(out["wealth"], dtype=float)
    for name, data, title in [("figure8_income_distribution.pdf", income, "Income ccdf"), ("figure9_money_distribution.pdf", wealth, "Money ccdf")]:
        fig, axes = plt.subplots(1, 2, figsize=(9, 3.5))
        x, y = ccdf(data)
        axes[0].loglog(x, y)
        axes[0].set_title(title)
        axes[0].grid(alpha=0.2, which="both")
        axes[1].semilogy(x, y)
        axes[1].set_title(title + " semi-log")
        axes[1].grid(alpha=0.2)
        fig.tight_layout()
        fig.savefig(figures / name)
        plt.close(fig)

    profits = np.asarray(out["profit_rates"], dtype=float)
    weights = np.asarray(out["profit_capital_weights"], dtype=float)
    mask = np.isfinite(profits) & (profits > -100) & (profits < 10000)
    profits = profits[mask]
    weights = weights[mask]
    hist("figure10_profit_capital_weighted.pdf", profits, np.arange(-100, min(1000, profits.max() + 10), 10), "Profit rates, capital weighted", weights=weights)
    hist("figure11_profit_firm_weighted.pdf", profits, np.arange(-100, min(1000, profits.max() + 10), 10), "Profit rates, firm weighted")
    summary["profit_rate_mean"] = float(np.mean(profits))
    summary["profit_rate_median"] = float(np.median(profits))

    xgrid = np.linspace(-90, 700, 250)
    pdf = profit_pdf_mixture(xgrid, 75.0, 55000.0, 50.0, (args.wage_max - args.wage_min) ** 2 / 12.0, max(alpha, 0.2), args.n)
    fig, ax = plt.subplots(figsize=(6, 3.5))
    counts, edges, _ = ax.hist(profits[(profits > -100) & (profits < 700)], bins=60, density=True, alpha=0.55)
    ax.plot(xgrid, pdf, color="k", lw=1.5, label="approx. mélange ratio-normal")
    ax.set_title("Theoretical fit to profit rates")
    ax.legend()
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(figures / "figure12_profit_theory.pdf")
    plt.close(fig)

    summary["class_workers_pct"] = float(summary["class_workers_mean"] / args.n)
    summary["class_capitalists_pct"] = float(summary["class_capitalists_mean"] / args.n)
    summary["class_unemployed_pct"] = float(summary["class_unemployed_mean"] / args.n)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260701)
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--total-money", type=float, default=100000.0)
    parser.add_argument("--wage-min", type=int, default=10)
    parser.add_argument("--wage-max", type=int, default=90)
    parser.add_argument("--years", type=int, default=100)
    parser.add_argument("--burn-years", type=int, default=0)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    figures, results = ensure_dirs(root)
    out = run_simulation(args)
    summary = plot_all(out, args, figures)
    summary["seed"] = args.seed
    summary["n"] = args.n
    summary["years"] = args.years
    summary["notes"] = [
        "Règles SR codées d'après le texte de l'article.",
        "Le texte ne dit pas explicitement si l'acteur actif peut se sélectionner lui-même comme employeur; ce recodage l'exclut pour respecter e_i != i.",
        "La courbe théorique de la figure 12 utilise une approximation delta-method du ratio de normales pour stabilité numérique; les paramètres sont ceux mesurés/indiqués dans le texte.",
    ]
    (results / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
