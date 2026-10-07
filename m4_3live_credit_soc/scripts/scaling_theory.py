"""Pourquoi ε = 1/(1-γ) : covariance d'échelle, énoncée puis vérifiée (note [28]).

L'ARGUMENT. Le rapport mesurait $\\varepsilon = 1/(1-\\gamma)$ sans le
justifier. La justification tient en une ligne : **le modèle est covariant
d'échelle**.

Posons $c = (A'/A)^{1/(1-\\gamma)}$ et remplaçons simultanément

    A -> A'        et        K0 -> c K0.

Alors toute trajectoire de capital est multipliée par $c$, à l'identique.
Vérification phase par phase, sur un capital $K \\mapsto cK$ :

* **production** : $A'(cK)^{\\gamma} = A' c^{\\gamma} K^{\\gamma}$, et par
  définition de $c$ on a $c^{1-\\gamma} = A'/A$, donc
  $A' c^{\\gamma} = c A$ : la production est bien multipliée par $c$ ;
* **taux d'intérêt** : la règle marginale évalue $\\gamma A K^{\\gamma-1}$,
  qui devient $\\gamma A' c^{\\gamma-1} K^{\\gamma-1}
  = \\gamma (A' c^{\\gamma}/c) K^{\\gamma-1} = \\gamma A K^{\\gamma-1}$ :
  le taux est **invariant**, c'est un nombre sans dimension ;
* **service** : principal $\\times$ taux, donc $\\times c$ ;
* **dépréciation, choc, injection à la naissance** : linéaires ou
  multiplicatifs, donc $\\times c$ ;
* **institution** : $\\delta^{*} = h(C) - K$ avec $h$ homogène de degré 1
  (à technologies fixées $h(C) = \\lambda^{*} C$), donc $\\times c$ ;
* **faillites** : ce sont des comparaisons entre grandeurs toutes en $c$,
  donc les mêmes entités meurent, aux mêmes pas.

Aucune phase ne consomme le générateur différemment : naissances, chocs et
appariements du marché tirent le même nombre de valeurs. Les deux
simulations sont donc la MÊME simulation à un facteur $c$ près, et

    prod_tot(A') = c * prod_tot(A)   =>   epsilon = dln(prod)/dln(A) = 1/(1-gamma).

CE QUI CASSE L'EXACTITUDE. Trois constantes du moteur sont dimensionnées et
ne sont pas rééchelonnées : `MIN_LOAN = 1e-9` (transfert jugé négligeable),
`ZERO_TOL` (capital jugé nul) et le plafond de transfert. Une paire dont le
transfert optimal tombe entre `MIN_LOAN` et `c·MIN_LOAN` est refusée d'un
côté et acceptée de l'autre : la covariance est exacte JUSQU'À ces seuils.
C'est la seule origine attendue d'un écart, et le script la teste.

CE QUE MESURE LE SCRIPT. Pour trois valeurs de γ, il lance depuis t=0 :

  ref        A = 1,0   K0 = 25
  covariant  A = 1,5   K0 = 25 c        avec c = 1,5^{1/(1-γ)}
  naif       A = 1,5   K0 = 25          (aucune compensation)
  lineaire   A = 1,5   K0 = 25 × 1,5    (compensation avec le mauvais exposant)

et rapporte, pour chaque bras, l'écart maximal à la proportionnalité exacte.
La prédiction est : `covariant` à la précision machine, les deux autres non.

    python3 scripts/scaling_theory.py
"""

from __future__ import annotations

import csv
import json
import math
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, "/home/anatole/jupyter")

from m4_3live.live import write_series  # noqa: E402
from m4_3live.model import Config, Simulation  # noqa: E402

from scripts.campaign import BASE  # noqa: E402

OUT = ROOT / "results" / "scaling_theory"
ANALYSIS = ROOT / "results" / "analysis"
FIGURES = ROOT / "report" / "figures"

STEPS = 800
GAMMAS = (0.4, 0.5, 0.6)
SEEDS = {0.4: (0,), 0.5: (0, 1, 2), 0.6: (0,)}
A_NEW = 1.5
WORKERS = 6

COLUMNS = ("prod_tot", "K_tot", "pop", "n_loans", "interest_paid", "loan_volume")


def factor(gamma: float) -> float:
    """c = (A'/A)^{1/(1-γ)} : le seul facteur qui laisse le système invariant."""
    return A_NEW ** (1.0 / (1.0 - gamma))


def variants(gamma: float) -> dict[str, dict]:
    c = factor(gamma)
    base_K0 = BASE["K0"]
    return {
        "ref": {"A": 1.0, "K0": base_K0, "scale": 1.0},
        "covariant": {"A": A_NEW, "K0": base_K0 * c, "scale": c},
        "naif": {"A": A_NEW, "K0": base_K0, "scale": c},
        "lineaire": {"A": A_NEW, "K0": base_K0 * A_NEW, "scale": c},
    }


def run_one(job: tuple[float, int, str]) -> dict:
    gamma, seed, name = job
    directory = OUT / f"g{gamma}" / name / f"seed{seed}"
    if (directory / "series.csv").exists():
        return {"gamma": gamma, "seed": seed, "variant": name, "skipped": True}
    started = time.time()
    spec = variants(gamma)[name]
    parameters = {**BASE, "gamma": gamma, "A": spec["A"], "K0": spec["K0"]}
    simulation = Simulation(Config(**parameters, seed=seed, T=STEPS))
    simulation.run()
    write_series(simulation, directory)
    (directory / "summary.json").write_text(
        json.dumps({"gamma": gamma, "seed": seed, "variant": name,
                    "parameters": simulation.config.to_dict(),
                    "status": simulation.status,
                    "wall_seconds": time.time() - started}, indent=2),
        encoding="utf-8",
    )
    return {"gamma": gamma, "seed": seed, "variant": name,
            "status": simulation.status, "wall_seconds": round(time.time() - started, 1)}


def series(gamma: float, name: str, seed: int) -> dict[str, np.ndarray]:
    path = OUT / f"g{gamma}" / name / f"seed{seed}" / "series.csv"
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {key: np.array([float(row[key]) for row in rows]) for key in rows[0]}


def compare(gamma: float, seed: int) -> list[dict]:
    reference = series(gamma, "ref", seed)
    c = factor(gamma)
    out = []
    for name in ("covariant", "naif", "lineaire"):
        candidate = series(gamma, name, seed)
        entry = {"gamma": gamma, "seed": seed, "variant": name, "c": c}
        for column in COLUMNS:
            base = reference[column]
            # `pop` et `n_loans` sont des effectifs : ils doivent être
            # IDENTIQUES, pas proportionnels.
            scale = 1.0 if column in ("pop", "n_loans") else c
            keep = base != 0
            deviation = np.abs(candidate[column][keep] / (scale * base[keep]) - 1.0)
            entry[f"{column}_ecart_max"] = float(deviation.max())
            entry[f"{column}_ecart_final"] = float(deviation[-1])
        entry["blocked_tiny_ref"] = float(reference["mkt_blocked_tiny"].sum())
        entry["blocked_tiny_var"] = float(candidate["mkt_blocked_tiny"].sum())
        entry["epsilon"] = float(
            np.log(candidate["prod_tot"][-200:].mean() / reference["prod_tot"][-200:].mean())
            / np.log(A_NEW)
        )
        out.append(entry)
    return out


def figure(rows: list[dict], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from simulation_lab.plot_utils import apply_style

    apply_style()
    figure_, axes = plt.subplots(1, 2, figsize=(12, 4.6))

    axis = axes[0]
    gamma = 0.5
    reference = series(gamma, "ref", 0)
    c = factor(gamma)
    axis.plot(reference["t"], reference["prod_tot"] * c, color="black", lw=1.6,
              label=f"référence × c   (c = {c:.3f})")
    for name, colour in (("covariant", "#c1440e"), ("naif", "#294c60"),
                         ("lineaire", "#3f7d20")):
        candidate = series(gamma, name, 0)
        axis.plot(candidate["t"], candidate["prod_tot"], color=colour, lw=0.9,
                  label={"covariant": "A×1,5 et K₀×c  (covariant)",
                         "naif": "A×1,5, K₀ inchangé",
                         "lineaire": "A×1,5 et K₀×1,5  (mauvais exposant)"}[name])
    axis.set_xlabel("t (pas)")
    axis.set_ylabel("production agrégée")
    axis.set_title(f"γ = {gamma} : une seule compensation superpose les courbes",
                   fontsize=9)
    axis.legend(fontsize=7)
    axis.grid(True, alpha=0.25)

    axis = axes[1]
    labels = {"covariant": "K₀ × c", "naif": "K₀ inchangé", "lineaire": "K₀ × 1,5"}
    colours = {"covariant": "#c1440e", "naif": "#294c60", "lineaire": "#3f7d20"}
    for name in ("covariant", "naif", "lineaire"):
        subset = [row for row in rows if row["variant"] == name]
        axis.scatter([row["gamma"] for row in subset],
                     [max(row["prod_tot_ecart_max"], 1e-17) for row in subset],
                     s=34, color=colours[name], label=labels[name])
    axis.axhline(1e-15, color="black", ls="--", lw=0.9)
    axis.text(0.4, 1.4e-15, "précision machine", fontsize=7, va="bottom")
    axis.set_yscale("log")
    axis.set_xlabel("γ")
    axis.set_ylabel("écart maximal à la proportionnalité exacte")
    axis.set_title("la covariance est exacte, les autres compensations non",
                   fontsize=9)
    axis.legend(fontsize=7)
    axis.grid(True, alpha=0.25, which="both")

    figure_.suptitle(
        "Justification de ε = 1/(1−γ) : en remplaçant A par A′ ET K₀ par cK₀, "
        "avec c = (A′/A) élevé à la puissance 1/(1−γ),\n"
        "on obtient la MÊME simulation à l'échelle c près — "
        "aucune autre compensation ne le fait", fontsize=10)
    figure_.tight_layout()
    figure_.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figure_)


def main(argv: list[str]) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [(gamma, seed, name)
            for gamma in GAMMAS for seed in SEEDS[gamma] for name in variants(gamma)]
    started = time.time()
    with mp.Pool(processes=WORKERS) as pool:
        done = 0
        for payload in pool.imap_unordered(run_one, jobs):
            done += 1
            print(f"[{done}/{len(jobs)}] " + json.dumps(payload), flush=True)
    print(f"# {time.time() - started:.0f} s\n", flush=True)

    rows = [entry for gamma in GAMMAS for seed in SEEDS[gamma]
            for entry in compare(gamma, seed)]
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    with open(ANALYSIS / "scaling_theory.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    FIGURES.mkdir(parents=True, exist_ok=True)
    figure(rows, FIGURES / "scaling_covariance.png")

    print(f"{'γ':>5s} {'graine':>7s} {'variante':>10s} {'c':>7s} "
          f"{'prod':>10s} {'K_tot':>10s} {'pop':>10s} {'ε mesuré':>9s}")
    print("-" * 78)
    for row in rows:
        print(f"{row['gamma']:5.1f} {row['seed']:7d} {row['variant']:>10s} "
              f"{row['c']:7.3f} {row['prod_tot_ecart_max']:10.2e} "
              f"{row['K_tot_ecart_max']:10.2e} {row['pop_ecart_max']:10.2e} "
              f"{row['epsilon']:9.4f}")
    (ANALYSIS / "scaling_theory.json").write_text(
        json.dumps({"steps": STEPS, "A_new": A_NEW, "rows": rows}, indent=2),
        encoding="utf-8",
    )
    write_table(rows)
    return 0


VARIANT_LABEL = {
    "covariant": "$K_0 \\times c$ \\quad\\emph{(covariant)}",
    "naif": "$K_0$ inchangé",
    "lineaire": "$K_0 \\times 1{,}5$ \\quad\\emph{(mauvais exposant)}",
}


def decimal(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}".replace(".", "{,}")


def sci(value: float) -> str:
    """Notation scientifique LaTeX, avec un plancher au zéro machine."""
    if value <= 0.0:
        return "$0$"
    exponent = int(math.floor(math.log10(value)))
    mantissa = value / 10.0**exponent
    return f"${mantissa:.1f}".replace(".", "{,}") + f"\\cdot 10^{{{exponent}}}$"


def write_table(rows: list[dict]) -> None:
    path = ROOT / "report" / "tables" / "scaling_theory.tex"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "\\begin{center}\\footnotesize",
        "\\begin{tabular}{@{}llrrrr@{}}",
        "\\toprule",
        "$\\gamma$ & compensation & $c$ & écart max & écart max & "
        "$\\varepsilon$ \\\\",
        " & & & \\code{prod\\_tot} & \\code{pop} & mesuré \\\\",
        "\\midrule",
    ]
    for gamma in GAMMAS:
        first = True
        for name in ("covariant", "naif", "lineaire"):
            group = [row for row in rows
                     if row["gamma"] == gamma and row["variant"] == name]
            if not group:
                continue
            entry = max(group, key=lambda row: row["prod_tot_ecart_max"])
            gamma_cell = decimal(gamma, 1) if first else ""
            first = False
            lines.append(
                f"{gamma_cell} & {VARIANT_LABEL[name]} & {decimal(entry['c'])}"
                f" & {sci(entry['prod_tot_ecart_max'])}"
                f" & {sci(entry['pop_ecart_max'])}"
                f" & {decimal(entry['epsilon'], 4)} \\\\"
            )
        lines.append("\\addlinespace")
    lines += [
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{center}",
        "",
        "\\noindent\\footnotesize Écart maximal, sur les "
        f"{STEPS} pas et toutes les graines, entre la trajectoire du bras et "
        "celle de la référence multipliée par $c$ (par 1 pour \\code{pop}, "
        "qui doit être identique et non proportionnelle). Seule la "
        "compensation covariante atteint la précision machine ; les deux "
        "autres s'en écartent de plusieurs ordres de grandeur. La colonne "
        "$\\varepsilon$ est l'élasticité mesurée sur les 200 derniers pas ; "
        "elle vaut $1/(1-\\gamma)$ pour la compensation covariante par "
        "construction du test.\\normalsize",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"tableau écrit : {path.relative_to(ROOT)}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
