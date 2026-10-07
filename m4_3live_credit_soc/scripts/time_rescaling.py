"""Covariance de pas de temps : « deux pas d'avant se déroulent en un pas ».

L'HYPOTHÈSE (relecteur). δ, σ et λ sont des paramètres *structurants du pas
de temps*, pas des paramètres de forme. Si l'on double λ, alors en posant

    δ' = 2δ - δ²        σ' = √2 · σ        λ' = 2λ

un pas neuf doit valoir deux pas anciens : la population resterait la même,
la production serait « grossièrement multipliée par deux », etc.

CE QUI COMPOSE EXACTEMENT. Trois des phases du pas se composent sans reste,
et le relecteur a écrit les trois formules justes :

* **dépréciation** — deux pas font K(1-δ)², un pas neuf fait K(1-δ'), et
  1 - (2δ - δ²) = (1-δ)². Exact, sans approximation ;
* **choc** — le moteur tire ξ ~ N(-σ²/2, σ) puis fait K ← K·e^ξ
  (`model.py:880-884`). Deux pas composent e^{ξ₁+ξ₂} avec
  ξ₁+ξ₂ ~ N(-σ², σ√2) ; un pas neuf avec σ' = √2σ tire
  N(-σ'²/2, σ') = N(-σ², √2σ). Exact — y compris la correction de dérive,
  qui est la partie qu'on rate d'habitude ;
* **naissances** — le moteur tire Poisson(λ) (`model.py:864`). Deux pas
  donnent Poisson(λ)+Poisson(λ) = Poisson(2λ), un pas neuf Poisson(2λ).
  Exact en loi.

CE QUI NE COMPOSE PAS TOUT SEUL. Deux phases sont des *flux par pas* et ne
sont pas dans la liste :

* **production** — deux pas anciens produisent ≈ 2AK^γ, un pas neuf n'en
  produit que AK^γ. Il manque un facteur 2 sur A ;
* **marché** — le moteur fait R = floor(ρN) rondes d'appariement par pas
  (`model.py:497`). Deux pas font 2ρN rondes, un pas neuf ρN. Il manque un
  facteur 2 sur ρ.

Et A porte les deux : le taux d'intérêt est γAK^{γ-1} (`pair_rate`), donc
doubler A double aussi le service par pas, ce qu'exige la composition.

CONSÉQUENCE PRÉVISIBLE, CORRIGÉE. Sans A → 2A, le point fixe autarcique
passe de [A(1-δ)/δ]^{1/(1-γ)} à [A(1-δ)²/(2δ-δ²)]^{1/(1-γ)}, soit un facteur
[(1-δ)/(2-δ)]^{1/(1-γ)} ≈ 0,25 à γ = 0,5 : le système s'effondre d'un facteur
4 en capital. Avec A → 2A le même calcul donne ≈ 0,990. ATTENTION : ce 1 % ne
mesure PAS le résidu total. Le résidu observé vaut 6 à 17 %, un ordre de
grandeur au-dessus — la discrétisation en δ n'en explique qu'un huitième.

CE QUE MESURE LE SCRIPT. Sept bras lancés depuis t = 0, comparés à *temps
ancien égal* (le pas t d'un bras de pas s répond au pas s·t de sa référence) :

  ref            λ=30  δ=0,01     σ=0,01      A=1  ρ=1   T=2000
  litteral       λ=60  δ=0,0199   σ=0,01√2    A=1  ρ=1   T=1000  (énoncé brut)
  sans_marche    λ=60  δ=0,0199   σ=0,01√2    A=2  ρ=1   T=1000  (isole ρ)
  complet        λ=60  δ=0,0199   σ=0,01√2    A=2  ρ=2   T=1000  (+ les flux)
  complet_s4     λ=120 δ=0,0394   σ=0,02      A=4  ρ=4   T=500   (s = 4)
  ref_dfin       λ=30  δ=0,002    σ=0,01      A=1  ρ=1   T=2000
  complet_dfin   λ=60  δ=0,003996 σ=0,01√2    A=2  ρ=2   T=1000  (δ divisé par 5)

Les flux (production, morts, volume de prêt, service) sont divisés par s dans
les bras rapides avant comparaison : ils sont rapportés au pas ANCIEN. Les
stocks (population, capital, nombre de prêts) sont comparés tels quels.

D'OÙ VIENT LE RÉSIDU : DEUX TESTS, UN SEUL QUI TRANCHE.

* `complet_s4` NE tranche PAS. Le résidu triple de s=2 à s=4, mais le
  déplacement de Kaut triple aussi (1,0 % → 3,0 %) : les deux termes croissent
  en (s-1), un pas neuf recouvrant s-1 compositions manquées. Compatible avec
  les deux explications. Il montre seulement que le rapport reste stable.
* `complet_dfin` tranche. À δ divisé par 5, Kaut ne se déplace plus que de
  0,20 % au lieu de 1,00 % — mais le résidu NE DÉCROÎT PAS (production
  +11,8 % → +15,0 %, capital +15,8 % → +22,1 %). La discrétisation en δ est
  donc écartée : le résidu vient de la PHASE DE MARCHÉ, qui ne se compose pas
  (deux rondes de ρN appariements ≠ une ronde de 2ρN, la seconde voyant
  l'état laissé par la première).

    python3 scripts/time_rescaling.py
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
from scripts.tension import write_tension  # noqa: E402

OUT = ROOT / "results" / "time_rescaling"
ANALYSIS = ROOT / "results" / "analysis"
FIGURES = ROOT / "report" / "figures"

#: Facteur de recalage : combien de pas anciens tiennent dans un pas neuf.
STRIDE = 2
#: Second pas de recalage, qui sert de discriminant entre les deux sources du
#: résidu (voir la docstring et le §7.3 du rapport).
STRIDE_LONG = 4
#: δ du bras discriminant : cinq fois plus petit que la base. Le terme de
#: discrétisation lui est proportionnel, le terme de marché l'ignore.
DELTA_THIN = 0.002
STEPS_REF = 2000
SEEDS = (0, 1, 2)
WORKERS = 6

#: Fenêtre stationnaire, en temps ANCIEN : les 800 derniers pas anciens.
WINDOW_OLD = 800

#: Flux par pas — à diviser par STRIDE dans les bras rapides.
FLOWS = ("prod_tot", "deaths", "loan_volume", "interest_paid", "births",
         "new_loans", "depreciated", "mkt_rounds")
#: Stocks — à comparer tels quels.
STOCKS = ("pop", "K_tot", "n_loans")


def coarsened(base: dict, stride: int = STRIDE) -> dict:
    """Les trois substitutions qui composent exactement (δ, σ, λ), pour un
    pas de recalage `stride` quelconque."""
    delta = base["delta"]
    return {
        "lam": base["lam"] * stride,
        # 1 - δ' = (1-δ)^stride  ⇔  δ' = 1 - (1-δ)^stride ; pour stride = 2
        # c'est exactement 2δ - δ², la formule du relecteur.
        "delta": 1.0 - (1.0 - delta) ** stride,
        # Var(Σ ξ) = stride·σ², et la dérive -σ²/2 suit automatiquement.
        "sigma": base["sigma"] * math.sqrt(stride),
    }


def variants() -> dict[str, dict]:
    fast = coarsened(BASE, STRIDE)
    long = coarsened(BASE, STRIDE_LONG)
    # Le discriminant : δ cinq fois plus petit, à pas de recalage inchangé.
    # Le terme de discrétisation suit δ, le terme de marché ne le voit pas.
    thin_base = {**BASE, "delta": DELTA_THIN}
    thin = coarsened(thin_base, STRIDE)
    return {
        "ref": {"params": {}, "steps": STEPS_REF, "stride": 1, "reference": None},
        "litteral": {"params": fast, "steps": STEPS_REF // STRIDE, "stride": STRIDE,
                     "reference": "ref"},
        "complet": {"params": {**fast, "A": BASE["A"] * STRIDE, "rho": float(STRIDE)},
                    "steps": STEPS_REF // STRIDE, "stride": STRIDE,
                    "reference": "ref"},
        "sans_marche": {"params": {**fast, "A": BASE["A"] * STRIDE},
                        "steps": STEPS_REF // STRIDE, "stride": STRIDE,
                        "reference": "ref"},
        # Même transformation, deux fois plus grossière.
        "complet_s4": {"params": {**long, "A": BASE["A"] * STRIDE_LONG,
                                  "rho": float(STRIDE_LONG)},
                       "steps": STEPS_REF // STRIDE_LONG, "stride": STRIDE_LONG,
                       "reference": "ref"},
        # Même transformation, même pas de recalage, mais δ divisé par 5.
        "ref_dfin": {"params": {"delta": DELTA_THIN}, "steps": STEPS_REF,
                     "stride": 1, "reference": None},
        "complet_dfin": {"params": {**thin, "A": BASE["A"] * STRIDE,
                                    "rho": float(STRIDE)},
                         "steps": STEPS_REF // STRIDE, "stride": STRIDE,
                         "reference": "ref_dfin"},
    }


def autarkic(A: float, gamma: float, delta: float) -> float:
    return (A * (1.0 - delta) / delta) ** (1.0 / (1.0 - gamma))


def run_one(job: tuple[str, int]) -> dict:
    name, seed = job
    directory = OUT / name / f"seed{seed}"
    if (directory / "series.csv").exists():
        return {"variant": name, "seed": seed, "skipped": True}
    started = time.time()
    spec = variants()[name]
    parameters = {**BASE, **spec["params"]}
    simulation = Simulation(Config(**parameters, seed=seed, T=spec["steps"]))
    simulation.run()
    write_series(simulation, directory)
    write_tension(directory, simulation.config.delta)
    (directory / "summary.json").write_text(
        json.dumps({"variant": name, "seed": seed,
                    "parameters": simulation.config.to_dict(),
                    "stride": spec["stride"],
                    "status": simulation.status,
                    "wall_seconds": time.time() - started}, indent=2),
        encoding="utf-8",
    )
    return {"variant": name, "seed": seed, "status": simulation.status,
            "wall_seconds": round(time.time() - started, 1)}


def series(name: str, seed: int) -> dict[str, np.ndarray]:
    path = OUT / name / f"seed{seed}" / "series.csv"
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {key: np.array([float(row[key]) for row in rows]) for key in rows[0]}


def tension_of(name: str, seed: int) -> float:
    """Tension moyenne sur la fenêtre stationnaire, lue dans `tension_agg.csv`.

    Elle est déjà sans dimension ET sans unité de temps : elle se compare
    directement, sans division par le pas.
    """
    path = OUT / name / f"seed{seed}" / "tension_agg.csv"
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    stride = variants()[name]["stride"]
    last = float(rows[-1]["t"])
    keep = [float(row["tension"]) for row in rows
            if float(row["t"]) > last - WINDOW_OLD / stride]
    return float(np.mean(keep))


def window(data: dict[str, np.ndarray], stride: int, key: str) -> float:
    """Moyenne d'une colonne sur la fenêtre stationnaire, ramenée au PAS ANCIEN.

    Un bras de stride s couvre le même temps ancien en s fois moins de pas ;
    ses flux par pas valent donc s doses. On divise pour comparer.
    """
    steps = data["t"]
    keep = steps > steps[-1] - WINDOW_OLD / stride
    value = float(data[key][keep].mean())
    return value / stride if key in FLOWS else value


def compare() -> list[dict]:
    specs = variants()
    rows = []
    for seed in SEEDS:
        for name, spec in specs.items():
            if spec["reference"] is None:
                continue
            reference = series(spec["reference"], seed)
            candidate = series(name, seed)
            entry = {"variant": name, "seed": seed, "stride": spec["stride"],
                     "reference": spec["reference"]}
            for key in STOCKS + FLOWS:
                if key not in candidate or key not in reference:
                    continue
                base = window(reference, 1, key)
                got = window(candidate, spec["stride"], key)
                entry[key] = got
                entry[f"{key}_ref"] = base
                entry[f"{key}_ratio"] = got / base if base else float("nan")
            # durée de vie : en pas anciens des deux côtés
            entry["lifetime"] = (window(candidate, spec["stride"], "pop")
                                 / window(candidate, spec["stride"], "deaths"))
            entry["lifetime_ref"] = (window(reference, 1, "pop")
                                     / window(reference, 1, "deaths"))
            entry["lifetime_ratio"] = entry["lifetime"] / entry["lifetime_ref"]
            parameters = json.loads(
                (OUT / name / f"seed{seed}" / "summary.json").read_text(encoding="utf-8")
            )["parameters"]
            reference_parameters = json.loads(
                (OUT / spec["reference"] / f"seed{seed}" / "summary.json")
                .read_text(encoding="utf-8")
            )["parameters"]
            entry["K_aut"] = autarkic(parameters["A"], parameters["gamma"],
                                      parameters["delta"])
            entry["K_aut_ref"] = autarkic(reference_parameters["A"],
                                          reference_parameters["gamma"],
                                          reference_parameters["delta"])
            entry["K_aut_ratio"] = entry["K_aut"] / entry["K_aut_ref"]
            # La tension est sans dimension et sans unité de temps : c'est le
            # résumé le plus direct de « le système tourne-t-il pareil ? ».
            entry["tension"] = tension_of(name, seed)
            entry["tension_ref"] = tension_of(spec["reference"], seed)
            entry["tension_ratio"] = entry["tension"] / entry["tension_ref"]
            rows.append(entry)
    return rows


def aggregate(rows: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for name in sorted({row["variant"] for row in rows}):
        subset = [row for row in rows if row["variant"] == name]
        entry: dict = {"n": len(subset)}
        for key in list(subset[0]):
            if not key.endswith("_ratio"):
                continue
            values = np.array([row[key] for row in subset])
            entry[key] = float(values.mean())
            entry[f"{key}_sd"] = float(values.std(ddof=1)) if len(values) > 1 else 0.0
        out[name] = entry
    return out


LABELS = {
    "pop_ratio": "population",
    "K_tot_ratio": "capital total",
    "prod_tot_ratio": "production / pas ancien",
    "deaths_ratio": "morts / pas ancien",
    "lifetime_ratio": "durée de vie (pas anciens)",
    "loan_volume_ratio": "volume prêté / pas ancien",
    "interest_paid_ratio": "service / pas ancien",
    "n_loans_ratio": "prêts actifs",
    "tension_ratio": "tension $T$ (sans dimension)",
}
VARIANT_LABELS = {
    "litteral": "énoncé brut",
    "sans_marche": "+ A×2",
    "complet": "+ A×2 et ρ×2",
    "complet_s4": "recalage complet, s = 4",
    "complet_dfin": "recalage complet, δ = 0,002",
}
#: Mêmes étiquettes, en LaTeX : la figure prend les unes, le tableau les autres.
TEX_LABELS = {
    "litteral": r"énoncé brut",
    "sans_marche": r"$+\,A\times 2$",
    "complet": r"$+\,A\times 2$ et $\rho\times 2$",
    "complet_s4": r"recalage complet, $s = 4$",
    "complet_dfin": r"recalage complet, $\delta = 0{,}002$",
}
ORDER = ("litteral", "sans_marche", "complet")
#: Bras du test de pas de recalage : même transformation, deux grossièretés.
STRIDE_ORDER = ("complet", "complet_s4", "complet_dfin")


def decimal(value: float, digits: int = 4) -> str:
    """Nombre en virgule française, protégé pour le mode mathématique."""
    return f"{value:.{digits}f}".replace(".", "{,}")


def write_table(summary: dict[str, dict], path: Path) -> None:
    lines = [r"\begin{center}", r"\begin{tabular}{@{}lrrr@{}}", r"\toprule",
             r"\textbf{Observable (rapport au bras \code{ref})} & "
             + " & ".join(rf"\textbf{{{TEX_LABELS[name]}}}" for name in ORDER)
             + r" \\", r"\midrule"]
    for key, label in LABELS.items():
        if key not in summary[ORDER[0]]:
            continue
        cells = []
        for name in ORDER:
            value = decimal(summary[name][key])
            deviation = decimal(summary[name][f"{key}_sd"])
            cells.append(f"${value} \\pm {deviation}$")
        lines.append(f"{label} & " + " & ".join(cells) + r" \\")
    lines += [r"\midrule",
              r"\emph{$\Kaut$ --- prédiction analytique} & "
              + " & ".join(f"$\\mathit{{{decimal(summary[name]['K_aut_ratio'])}}}$"
                           for name in ORDER)
              + r" \\",
              r"\bottomrule", r"\end{tabular}", r"\end{center}"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_stride_table(summary: dict[str, dict], path: Path) -> None:
    """Le même recalage à deux grossièretés : s = 2 et s = 4.

    Si le résidu était dominé par la discrétisation en δ, il suivrait le
    déplacement de Kaut (1,0 % puis 3,0 %). S'il est dominé par la
    recomposition du marché, il croît avec s bien plus vite que ça.
    """
    present = [name for name in STRIDE_ORDER if name in summary]
    if len(present) < 2:
        return
    # En-têtes propres à ce tableau : ce qui compte ici est le couple (s, δ),
    # pas le nom interne du bras.
    heads = {"complet": r"$s = 2$, $\delta = 0{,}01$",
             "complet_s4": r"$s = 4$, $\delta = 0{,}01$",
             "complet_dfin": r"$s = 2$, $\delta = 0{,}002$"}
    spec = "@{}l" + "r" * len(present) + "@{}"
    lines = [r"\begin{center}", rf"\begin{{tabular}}{{{spec}}}", r"\toprule",
             r"\textbf{Observable} & "
             + " & ".join(rf"\textbf{{{heads.get(name, TEX_LABELS[name])}}}"
                          for name in present)
             + r" \\", r"\midrule"]
    for key, label in LABELS.items():
        if any(key not in summary[name] for name in present):
            continue
        lines.append(
            f"{label} & "
            + " & ".join(f"${decimal(summary[name][key])} \\pm "
                         f"{decimal(summary[name][f'{key}_sd'])}$" for name in present)
            + r" \\")
    lines.append(r"\midrule")
    lines.append(
        r"\emph{$\Kaut$ --- prédiction analytique} & "
        + " & ".join(f"$\\mathit{{{decimal(summary[name]['K_aut_ratio'])}}}$"
                     for name in present) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{center}"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def figure(path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from simulation_lab.plot_utils import apply_style

    apply_style()
    specs = variants()
    colours = {"ref": "#000000", "litteral": "#c1121f",
               "sans_marche": "#d99b1c", "complet": "#3f7d20",
               "complet_s4": "#7a4e9f", "complet_dfin": "#1b7a8c"}
    panels = (("pop", "population", 1),
              ("prod_tot", "production par pas ancien", 0))
    figure_, axes = plt.subplots(1, 3, figsize=(13.5, 4.4))
    for axis, (key, title, is_stock) in zip(axes, panels):
        for name, spec in specs.items():
            if name != "ref" and spec["reference"] != "ref":
                continue
            data = series(name, SEEDS[0])
            stride = spec["stride"]
            values = data[key] if is_stock else data[key] / stride
            label = "référence (pas ancien)" if name == "ref" else VARIANT_LABELS[name]
            axis.plot(data["t"] * stride, values, color=colours[name], lw=1.0,
                      alpha=0.9, label=label)
        axis.set_xlabel("temps ancien (pas de la référence)")
        axis.set_title(title, fontsize=9)
        axis.grid(True, alpha=0.2)
    axes[0].legend(fontsize=7)
    axes[1].set_yscale("log")

    # Troisième panneau : le rapport à la référence, à temps ancien égal. Les
    # deux premiers montrent les niveaux, celui-ci montre le résidu — sans
    # lui, un écart de 6 % est invisible sur une échelle log.
    axis = axes[2]
    reference = series("ref", SEEDS[0])
    window_size = 101
    kernel = np.ones(window_size) / window_size
    for name, spec in specs.items():
        if spec["reference"] != "ref":
            continue
        data = series(name, SEEDS[0])
        stride = spec["stride"]
        old_time = (data["t"] * stride).astype(int)
        index = np.searchsorted(reference["t"].astype(int), old_time)
        index = np.clip(index, 0, len(reference["t"]) - 1)
        for key, style in (("pop", "-"), ("prod_tot", "--")):
            factor = 1.0 if key in STOCKS else stride
            ratio = (data[key] / factor) / reference[key][index]
            smooth = np.convolve(ratio, kernel, mode="valid")
            axis.plot(old_time[window_size - 1:], smooth, style,
                      color=colours[name], lw=1.1, alpha=0.9,
                      label=f"{VARIANT_LABELS[name]} — "
                            f"{'population' if key == 'pop' else 'production'}")
    axis.axhline(1.0, color="black", lw=1.0, ls=":")
    axis.set_ylim(0.5, 2.2)
    axis.set_xlabel("temps ancien (pas de la référence)")
    axis.set_title("rapport à la référence (moyenne glissante, 101 pas)", fontsize=9)
    axis.legend(fontsize=6.2)
    axis.grid(True, alpha=0.2)

    figure_.suptitle(
        "Recalage temporel : λ×2, δ → 2δ−δ², σ → √2σ. Ces trois substitutions "
        "composent exactement, mais ne suffisent pas :\nl'énoncé brut porte la "
        "population à ×1,85 et la production par pas ancien à ×0,70. Il faut y "
        "ajouter les deux flux par pas (A×2, ρ×2).",
        fontsize=9.5)
    figure_.tight_layout()
    figure_.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figure_)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    jobs = [(name, seed) for name in variants() for seed in SEEDS]
    started = time.time()
    with mp.Pool(WORKERS) as pool:
        for result in pool.imap_unordered(run_one, jobs):
            if result.get("skipped"):
                print(f"  {result['variant']:<12} seed{result['seed']} déjà là")
            else:
                print(f"  {result['variant']:<12} seed{result['seed']} "
                      f"{result['status']} {result['wall_seconds']} s", flush=True)
    print(f"{len(jobs)} runs en {time.time() - started:.0f} s\n")

    rows = compare()
    with open(ANALYSIS / "time_rescaling.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = aggregate(rows)
    json.dump(summary, open(ANALYSIS / "time_rescaling.json", "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    write_table(summary, ROOT / "report" / "tables" / "time_rescaling.tex")
    write_stride_table(summary,
                       ROOT / "report" / "tables" / "time_rescaling_stride.tex")
    figure(FIGURES / "time_rescaling.png")

    for name in ORDER + tuple(n for n in STRIDE_ORDER if n not in ORDER):
        print(f"{name} ({VARIANT_LABELS[name]}) :")
        for key, label in LABELS.items():
            if key not in summary[name]:
                continue
            print(f"    {label:<28} {summary[name][key]:8.4f} "
                  f"± {summary[name][f'{key}_sd']:.4f}")
        print(f"    {'K_aut (théorie)':<28} {summary[name]['K_aut_ratio']:8.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
