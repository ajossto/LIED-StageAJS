"""Ablation §D — d'où vient la contraction de population du bras global ?

QUESTION. Le bras `all_A150` de la campagne principale produit, en régime
établi, une population 25 % plus petite que son contrôle apparié. Le rapport
de résultats a d'abord attribué cette contraction à un service d'intérêts
plus lourd. **Cette attribution est fausse** : le service rapporté à la
production PASSE de 1,128 à 1,093, il s'allège. L'hypothèse restante, et la
seule que les données existantes désignent, est d'échelle : le capital de
naissance K0 = 25 est FIXE, alors que le capital moyen par entité monte de
773 à 1118. Une entité naissante vaut donc 3,23 % du capital moyen dans le
contrôle contre 2,24 % dans le bras traité — elle naît relativement plus
pauvre, dans un système plus grand.

PLAN. Cinq bras, mêmes graines, mêmes snapshots à t₀ que la campagne
principale, donc directement comparables à elle :

  abl_control          rien                       (contrôle apparié)
  abl_A150             A × 1,5 (portée `all`)     (réplique de all_A150)
  abl_A150_K0aut       A × 1,5  +  K0 × 2,25      (K0/K*_aut conservé)
  abl_A150_K0obs       A × 1,5  +  K0 × 1,45      (K0/(K par entité) conservé)
  abl_K0aut            K0 × 2,25 seul             (effet de K0 sans A)

2,25 = A^{1/(1-γ)} = 1,5² est le facteur qui laisse invariant le rapport
K0/K*_aut, où K*_aut = [A(1-δ)/δ]^{1/(1-γ)} est l'échelle autarcique (le
capital où production et dépréciation s'équilibrent sans marché). C'est la
convention de compensation déjà employée par M4.3 pour ses cellules
`gamma_comp`. 1,45 est le rapport OBSERVÉ des capitaux par entité — une
compensation a posteriori plutôt qu'a priori.

MESURE SUPPLÉMENTAIRE. Ces bras enregistrent les morts (`record_deaths`),
ce que la campagne principale ne faisait pas : on obtient l'âge au décès de
chaque entité, donc la réponse directe à « qui meurt en plus ? ». Le drapeau
n'écrit que dans une liste et ne consomme aucun tirage : `abl_control` doit
donc reproduire `control` BIT À BIT, ce que le script vérifie.

    python3 scripts/ablation_k0.py run
    python3 scripts/ablation_k0.py analyse
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

from m4_3live.live import load_snapshot, write_series  # noqa: E402
from m4_3live.model import Config, Intervention  # noqa: E402

from scripts.campaign import BASE, SEEDS, T0, WINDOW, WORKERS  # noqa: E402

OUT = ROOT / "results" / "ablation_k0"
BURN = ROOT / "results" / "campaign" / "burn"
ANALYSIS = ROOT / "results" / "analysis"
FIGDIR = ROOT / "report" / "figures"

K0_BASE = BASE["K0"]
K0_AUT = K0_BASE * 1.5 ** (1.0 / (1.0 - BASE["gamma"]))  # = 25 × 2,25 = 56,25
K0_OBS = K0_BASE * 1.45  # rapport observé des capitaux par entité


def step(**kwargs) -> dict:
    payload = {"t": T0 + 1, "note": ""}
    payload.update(kwargs)
    return payload


ARMS: dict[str, list[dict]] = {
    "abl_control": [],
    "abl_A150": [step(param="A", value=1.5, scope="all")],
    "abl_A150_K0aut": [
        step(param="A", value=1.5, scope="all"),
        step(param="K0", value=K0_AUT, scope="all"),
    ],
    "abl_A150_K0obs": [
        step(param="A", value=1.5, scope="all"),
        step(param="K0", value=K0_OBS, scope="all"),
    ],
    "abl_K0aut": [step(param="K0", value=K0_AUT, scope="all")],
}

LABELS = {
    "abl_control": "contrôle",
    "abl_A150": "A×1,5",
    "abl_A150_K0aut": "A×1,5 + K0×2,25 (échelle autarcique)",
    "abl_A150_K0obs": "A×1,5 + K0×1,45 (échelle observée)",
    "abl_K0aut": "K0×2,25 seul",
}
COLORS = {
    "abl_control": "#66757f",
    "abl_A150": "#294c60",
    "abl_A150_K0aut": "#c1440e",
    "abl_A150_K0obs": "#e08a3c",
    "abl_K0aut": "#2e7d5b",
}


def run_arm(job: tuple[int, str]) -> dict:
    seed, arm = job
    directory = OUT / arm / f"seed{seed}"
    if (directory / "summary.json").exists():
        return {"seed": seed, "arm": arm, "skipped": True}
    started = time.time()
    config = Config(**BASE, seed=seed, T=T0 + WINDOW, record_deaths=True)
    simulation = load_snapshot(BURN / f"seed{seed}" / f"snapshot_t{T0}.pkl", config=config)
    planned: dict[int, list[Intervention]] = {}
    for entry in ARMS[arm]:
        planned.setdefault(int(entry["t"]), []).append(Intervention.from_dict(entry))
    while simulation.t < config.T and simulation.status == "ok":
        for item in planned.get(simulation.t + 1, ()):
            simulation.submit(item)
        simulation.step()
    write_series(simulation, directory)
    deaths = [row for row in simulation.deaths if row["t"] > T0]
    with open(directory / "deaths.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["t", "id", "age", "cause", "K", "nw"])
        writer.writeheader()
        for row in deaths:
            writer.writerow({k: row[k] for k in ("t", "id", "age", "cause", "K", "nw")})
    (directory / "summary.json").write_text(
        json.dumps(
            {
                "seed": seed,
                "arm": arm,
                "t_final": simulation.t,
                "status": simulation.status,
                "wall_seconds": time.time() - started,
                "plan": ARMS[arm],
                "interventions": simulation.intervention_log,
                "n_deaths_window": len(deaths),
                "parameters": simulation.config.to_dict(),
                "book_errors": simulation.book.consistency_errors(simulation.population.alive),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return {"seed": seed, "arm": arm, "status": simulation.status,
            "wall_seconds": time.time() - started, "deaths": len(deaths)}


# --------------------------------------------------------------------------
def series(arm: str, seed: int, column: str, root: Path = OUT) -> np.ndarray:
    with open(root / arm / f"seed{seed}" / "series.csv", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return np.array([float(row[column]) for row in rows])[T0 : T0 + WINDOW]


def matrix(arm: str, column: str, root: Path = OUT) -> np.ndarray:
    return np.array([series(arm, seed, column, root) for seed in SEEDS])


def ages(arm: str) -> np.ndarray:
    out = []
    for seed in SEEDS:
        with open(OUT / arm / f"seed{seed}" / "deaths.csv", newline="", encoding="utf-8") as handle:
            out.extend(int(row["age"]) for row in csv.DictReader(handle) if int(row["t"]) > T0 + 1000)
    return np.array(out)


def check_flag_is_inert() -> dict:
    """`abl_control` doit reproduire `control` BIT À BIT : le drapeau
    d'enregistrement des morts n'écrit que dans une liste."""
    columns = ("pop", "K_tot", "prod_tot", "n_loans", "deaths", "interest_paid")
    worst = 0.0
    for seed in SEEDS:
        for column in columns:
            a = series("abl_control", seed, column)
            b = series("control", seed, column, root=ROOT / "results" / "campaign" / "arms")
            worst = max(worst, float(np.max(np.abs(a - b))))
    return {"colonnes": list(columns), "ecart_max": worst, "bit_identique": worst == 0.0}


def analyse() -> dict:
    sl = slice(1000, WINDOW)
    reference = "abl_control"
    result = {"t0": T0, "window": WINDOW, "seeds": list(SEEDS),
              "K0": {"base": K0_BASE, "autarcique": K0_AUT, "observe": K0_OBS},
              "drapeau_inerte": check_flag_is_inert(), "arms": {}}
    for arm in ARMS:
        entry = {"label": LABELS[arm]}
        for column in ("prod_tot", "pop", "K_tot", "deaths", "roots_insolvency", "interest_paid"):
            values = matrix(arm, column)[:, sl].mean(axis=1)
            base = matrix(reference, column)[:, sl].mean(axis=1)
            entry[column] = float(values.mean())
            entry[f"{column}_ratio"] = float((values / base).mean())
            entry[f"{column}_ratio_sem"] = float(
                (values / base).std(ddof=1) / math.sqrt(len(SEEDS))
            )
        pop = matrix(arm, "pop")[:, sl]
        entry["K_per_entity"] = float((matrix(arm, "K_tot")[:, sl] / pop).mean())
        entry["prod_per_entity"] = float((matrix(arm, "prod_tot")[:, sl] / pop).mean())
        entry["service_over_prod"] = float(
            (matrix(arm, "interest_paid")[:, sl] / matrix(arm, "prod_tot")[:, sl]).mean()
        )
        k0 = K0_AUT if "K0aut" in arm else (K0_OBS if "K0obs" in arm else K0_BASE)
        entry["K0"] = k0
        entry["K0_over_K_per_entity"] = k0 / entry["K_per_entity"]
        # Durée de vie moyenne = effectif / flux de morts, calculée sur les
        # MOYENNES (un pas sans aucune mort donnerait sinon une division par
        # zéro et une moyenne infinie).
        entry["mean_lifetime"] = float(pop.mean() / matrix(arm, "deaths")[:, sl].mean())
        age = ages(arm)
        entry["age_median"] = float(np.median(age))
        entry["age_mean"] = float(age.mean())
        entry["age_p90"] = float(np.percentile(age, 90))
        entry["n_deaths"] = int(age.size)
        entry["share_deaths_age_le_10"] = float((age <= 10).mean())
        result["arms"][arm] = entry
    return result


def figures(result: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from simulation_lab.plot_utils import apply_style

    apply_style()
    FIGDIR.mkdir(parents=True, exist_ok=True)
    horizon = np.arange(1, WINDOW + 1)
    order = list(ARMS)

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4))
    for arm in order:
        for axis, column, title in zip(
            axes, ("pop", "prod_tot", "K_tot"),
            ("population", "production agrégée prod_tot", "capital agrégé K_tot"),
        ):
            mean = matrix(arm, column).mean(axis=0)
            kernel = np.ones(101) / 101
            smoothed = np.convolve(np.pad(mean, 50, mode="edge"), kernel, mode="valid")[: mean.size]
            axis.plot(horizon, smoothed, color=COLORS[arm], lw=1.4, label=LABELS[arm])
            axis.set_title(title)
            axis.set_xlabel("horizon h après t₀ (pas)")
            axis.grid(True, alpha=0.25)
    axes[0].set_ylabel(f"niveau (moyenne de {len(SEEDS)} graines, lissée sur 101 pas)")
    axes[0].legend(fontsize=7)
    fig.suptitle(
        "Ablation K0 : la contraction de population disparaît-elle quand le capital "
        f"de naissance suit l'échelle ? (n={len(SEEDS)} graines)"
    )
    fig.tight_layout()
    fig.savefig(FIGDIR / "ablation_k0_levels.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # -- distribution des âges au décès -----------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    bins = np.logspace(0, np.log10(600), 40)
    for arm in order:
        age = ages(arm)
        counts, edges = np.histogram(age, bins=bins)
        widths = np.diff(edges)
        centres = np.sqrt(edges[:-1] * edges[1:])
        density = counts / (age.size * widths)
        error = np.sqrt(counts) / (age.size * widths)
        keep = counts > 0
        axes[0].errorbar(centres[keep], density[keep], yerr=error[keep], fmt="o-", ms=2.5,
                         lw=1.0, capsize=1.5, color=COLORS[arm],
                         label=f"{LABELS[arm]} (n={age.size})")
        survival = 1.0 - np.searchsorted(np.sort(age), np.sort(age), side="left") / age.size
        axes[1].step(np.sort(age), survival, color=COLORS[arm], lw=1.3, label=LABELS[arm])
    axes[0].set_xscale("log")
    axes[0].set_yscale("log")
    axes[0].set_xlabel("âge au décès (pas)")
    axes[0].set_ylabel("densité (barres = incertitude de Poisson)")
    axes[0].set_title("Distribution de l'âge au décès, h ∈ [1001, 2000]")
    axes[0].grid(True, which="both", alpha=0.25)
    axes[0].legend(fontsize=6)
    axes[1].set_xscale("log")
    axes[1].set_xlabel("âge (pas)")
    axes[1].set_ylabel("fraction survivant au-delà")
    axes[1].set_title("Fonction de survie empirique")
    axes[1].grid(True, which="both", alpha=0.25)
    axes[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGDIR / "ablation_k0_survival.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else "run"
    if command == "run":
        OUT.mkdir(parents=True, exist_ok=True)
        jobs = [(seed, arm) for arm in ARMS for seed in SEEDS]
        started = time.time()
        with mp.Pool(processes=WORKERS) as pool:
            done = 0
            for payload in pool.imap_unordered(run_arm, jobs):
                done += 1
                print(f"[{done}/{len(jobs)}] " + json.dumps(payload), flush=True)
        print(f"# ablation terminée en {time.time() - started:.0f} s", flush=True)
        return 0
    result = analyse()
    figures(result)
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    (ANALYSIS / "ablation_k0.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(result["drapeau_inerte"], indent=2, ensure_ascii=False))
    header = f"{'bras':34s} {'pop':>8s} {'prod':>8s} {'K/ent':>8s} {'K0/K_ent':>9s} {'vie moy':>8s} {'age med':>8s} {'serv/prod':>9s}"
    print(header)
    print("-" * len(header))
    for arm, entry in result["arms"].items():
        print(
            f"{LABELS[arm]:34s} {entry['pop_ratio']:8.3f} {entry['prod_tot_ratio']:8.3f} "
            f"{entry['K_per_entity']:8.1f} {entry['K0_over_K_per_entity']:9.4f} "
            f"{entry['mean_lifetime']:8.1f} {entry['age_median']:8.1f} {entry['service_over_prod']:9.4f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
