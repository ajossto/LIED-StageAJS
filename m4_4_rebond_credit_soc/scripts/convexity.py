"""Lot I — pourquoi une institution équitable EN MOYENNE agit en asservissement.

Le lot T avait mesuré qu'un partage implicite moyen de p ≈ 0,53 (la règle
`marginal`) produit l'état d'un partage p = 1. Le rapport final posait le
mécanisme en hypothèse et le déclarait « à faire » (§ « ce que ce programme
n'établit pas », point 2) : *il faudrait montrer que la mortalité d'une
débitrice est convexe dans le service qu'elle porte.* Ce script fait le
calcul. Il rend TROIS verdicts, et le troisième réfute l'hypothèse en la
remplaçant par mieux.

**1. La convexité, telle qu'elle était posée, est fausse.** Le risque `h(s)`
de succomber à l'insolvabilité dans les dix pas qui suivent n'est pas convexe
dans le fardeau `s = debts/prod` : il est fortement NON MONOTONE — une bosse
à fardeau faible, puis une décroissance. Et la courbure ajustée sur le corps
ne survit pas au conditionnement par le capital, qui est le vrai facteur
dominant. Le test conditionnel est celui qui décide, et il tranche contre.

**2. Ce qui survit de la forme de l'argument.** L'écart de Jensen, lui, est
massif et se comporte comme il faut : la mortalité observée vaut cinq fois
celle qu'on lirait au fardeau MOYEN, et cet écart croît de façon monotone
avec `p`. Ce n'est donc pas la convexité qui manquait, c'est la variable.

**3. Le mécanisme, et il est exact.** `record_rate_split` permet de lire le
partage de deux façons — par contrat, ou pondéré par le surplus en jeu — et
leur écart est une IDENTITÉ :

    p_pondéré − p_par_contrat = Cov(p, Δ) / E[Δ]

Sur le bras historique, p par contrat = 0,53 mais **p pondéré = 0,94**. La
règle en vigueur n'applique pas le même partage aux gros et aux petits
contrats : elle asservit sur les gros et se montre altruiste sur les petits.
Les bras à `p` fixe donnent le témoin — chez eux l'écart est nul au
dix-millième —, ce qui vérifie l'estimateur avant qu'on le lise. Le « 0,53 »
du lot T n'était pas faux : il comptait des contrats là où le système compte
des joules.

Aucune campagne nouvelle : tout vient des panneaux (`panels.npz`), de la
table des décès (`deaths.csv`) et des séries (`series.csv`) déjà écrits par
les 72 runs du lot T.

    python3 scripts/convexity.py [--campaign results/campaign/bargain]
                                 [--burden dette|verse] [--cause insolvency|cascade|all]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from m4_4.live import read_panels  # noqa: E402

#: Student à onze degrés de liberté, seuil bilatéral à 5 % — la convention
#: de toute la lignée (douze graines appariées).
T_CRITICAL = 2.201

#: Nombre de classes de service. Vingt classes de quantile donnent ≈ 5 % de
#: la population par classe : assez fin pour voir une courbure, assez épais
#: pour que le taux de décès par classe ait un sens (≈ 10^4 entités-pas par
#: classe et par run).
N_BINS = 20

#: Le service est à queue lourde (une entité peut payer plusieurs fois sa
#: production d'un pas). La courbure est ajustée sur le corps : au-delà, les
#: classes sont trop peu peuplées et `h` sature à 1, ce qui CONCAVIFIE la
#: courbe pour une raison qui n'a rien à voir avec le mécanisme.
FIT_QUANTILE = 0.99

#: Nombre de classes de capital pour le test conditionnel. Cinq, et non dix :
#: à dix, les classes de service à l'intérieur d'une classe de capital
#: descendent sous le millier d'observations.
N_CAPITAL_BINS = 5


#: Le fardeau, et pourquoi ce n'est PAS le service versé.
#:
#: `int_out` est ce que l'entité a effectivement VERSÉ. Or `_service_interest`
#: fait payer au prorata quand le capital ne suffit pas : une entité en
#: détresse verse peu, voire rien. Sur le bras historique, 2,67 % des
#: endettées versent exactement zéro à un pas donné. Prendre `int_out` pour
#: mesure du fardeau met donc les plus étranglées dans la classe des fardeaux
#: LÉGERS, et retourne la question.
#:
#: `debts` — la somme des principaux dus — n'a pas ce défaut : il ne dépend
#: pas de la capacité à payer. C'est la spécification principale. Le service
#: versé reste mesuré, en robustesse, avec sa contamination déclarée.
BURDENS = {
    "dette": ("debts", "fardeau de principal — Σq rapportée à la production"),
    "verse": ("int_out", "service effectivement versé (contaminé par le prorata)"),
}


def read_deaths(path: Path) -> tuple[dict[int, int], dict[int, str]]:
    """`id -> t` de décès et `id -> cause`. Les identifiants ne sont JAMAIS
    recyclés (`Population.born` prend `len(self.K)`, `kill` ne retire rien de
    la liste), donc cette table est une bijection et la jointure par `id` est
    sûre. L'assertion le vérifie plutôt que de le supposer."""
    when: dict[int, int] = {}
    cause: dict[int, str] = {}
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            entity = int(row["id"])
            assert entity not in when, f"identifiant recyclé : {entity}"
            when[entity] = int(row["t"])
            cause[entity] = row["cause"]
    return when, cause


def collect(path: Path, t_min: float, t_max: float, horizon: int,
            burden: str, cause_filter: str) -> dict:
    """Table entité-pas d'un run : fardeau porté, capital, et décès à venir.

    `horizon` est la portée du pari : l'entité meurt-elle dans les `horizon`
    pas qui suivent l'instantané ? On le prend égal au pas d'échantillonnage
    des panneaux, de sorte que les fenêtres PAVENT le temps sans se
    recouvrir — sinon un même décès serait compté plusieurs fois et le taux
    n'aurait plus de sens de probabilité.

    `cause_filter` sépare les deux canaux de mort. Le mécanisme en cause est
    celui de la débitrice qui succombe à son propre fardeau : c'est le canal
    `insolvency`. Être fauchée par la faillite d'une consœur (`cascade`) est
    un autre canal, qui ne dépend pas du fardeau de la victime de la même
    façon. Les mélanger brouille la forme.
    """
    panels = read_panels(path / "panels.npz")
    death_t_map, cause_map = read_deaths(path / "deaths.csv")

    times = np.unique(panels["t"])
    times = times[(times > t_min) & (times <= t_max)]
    keep = np.isin(panels["t"], times)

    ident = panels["id"][keep]
    when = panels["t"][keep]
    prod = panels["prod"][keep]
    capital = panels["K"][keep]
    raw = panels[BURDENS[burden][0]][keep]

    # Seules les PRODUCTRICES ont un fardeau relatif défini : `s` est une part
    # de production, et une entité qui ne produit pas n'en porte pas un
    # « léger », elle en porte un qui n'est pas défini. Les écarter est une
    # décision de mesure, comptabilisée et rapportée.
    producing = prod > 0.0
    n_total = int(ident.size)
    ident, when = ident[producing], when[producing]
    service = raw[producing] / prod[producing]
    capital = capital[producing]

    death_t = np.array([death_t_map.get(int(entity), -1) for entity in ident], dtype=np.int64)
    dies = (death_t > when) & (death_t <= when + horizon)
    if cause_filter != "all":
        matches = np.array([cause_map.get(int(entity), "") == cause_filter for entity in ident])
        dies = dies & matches

    # Taux effectif porté, `int_out / debts`. Le prorata le tire vers le bas
    # chez les étranglées — d'où l'atome en zéro —, mais il laisse les
    # quantiles HAUTS intacts, et ce sont eux qui portent la comparaison
    # entre bras : c'est la queue du taux, pas sa moyenne, que le lot T met
    # en cause.
    debts = panels["debts"][keep][producing]
    indebted = debts > 1e-9
    rate = panels["int_out"][keep][producing][indebted] / debts[indebted]

    return {
        "service": service,
        "capital": capital,
        "dies": dies.astype(np.float64),
        "rate": rate,
        "n_total": n_total,
        "n_producing": int(ident.size),
    }


def hazard_curve(service: np.ndarray, dies: np.ndarray, n_bins: int) -> dict:
    """Taux de décès par classe de quantile de service.

    Retourne les centres de classe, le taux, son erreur binomiale et
    l'effectif. Les classes sont des QUANTILES et non des intervalles
    réguliers : à queue lourde, des intervalles réguliers mettraient 99 % de
    la population dans la première classe.
    """
    if service.size < n_bins * 20:
        return {}
    edges = np.quantile(service, np.linspace(0.0, 1.0, n_bins + 1))
    # Les quantiles peuvent coïncider (masse atomique en zéro) : on
    # déduplique, sinon des classes vides produisent des NaN silencieux.
    edges = np.unique(edges)
    if edges.size < 4:
        return {}
    index = np.clip(np.digitize(service, edges[1:-1], right=True), 0, edges.size - 2)

    centre, rate, se, count = [], [], [], []
    for bucket in range(edges.size - 1):
        mask = index == bucket
        n = int(mask.sum())
        if n < 50:
            continue
        p = float(dies[mask].mean())
        centre.append(float(service[mask].mean()))
        rate.append(p)
        se.append(math.sqrt(max(p * (1.0 - p), 0.0) / n))
        count.append(n)
    return {
        "centre": np.array(centre),
        "rate": np.array(rate),
        "se": np.array(se),
        "count": np.array(count, dtype=float),
    }


def curvature(curve: dict, cut: float) -> dict:
    """Ajustement quadratique pondéré `h = c0 + c1 s + c2 s²` sur le corps.

    Le coefficient `c2` EST la convexité : positif, la mortalité accélère
    avec le service. Son erreur vient de la matrice de covariance pondérée,
    et l'écart de Jensen d'une distribution de service de variance `V` vaut
    alors exactement `c2 · V` — c'est la propriété qui rend le quadratique
    intéressant ici, bien plus que sa qualité d'ajustement.
    """
    if not curve:
        return {}
    mask = curve["centre"] <= cut
    if mask.sum() < 5:
        return {}
    x = curve["centre"][mask]
    y = curve["rate"][mask]
    n = curve["count"][mask]
    sigma = curve["se"][mask]
    # Poids inverse-variance ; une classe à taux nul aurait une erreur nulle
    # et un poids infini, d'où le plancher sur l'effectif.
    weight = np.where(sigma > 0, 1.0 / np.maximum(sigma, 1e-12) ** 2, n)

    design = np.vstack([np.ones_like(x), x, x * x]).T
    scaled = design * weight[:, None]
    normal = design.T @ scaled
    try:
        inverse = np.linalg.inv(normal)
    except np.linalg.LinAlgError:
        return {}
    beta = inverse @ (scaled.T @ y)
    residual = y - design @ beta
    dof = max(int(mask.sum()) - 3, 1)
    chi2 = float((weight * residual**2).sum() / dof)
    errors = np.sqrt(np.diag(inverse) * max(chi2, 1.0))
    return {
        "c0": float(beta[0]), "c1": float(beta[1]), "c2": float(beta[2]),
        "c2_se": float(errors[2]), "chi2_reduit": chi2, "n_classes": int(mask.sum()),
        "cut": float(cut),
    }


def second_differences(curve: dict, cut: float) -> dict:
    """Test NON PARAMÉTRIQUE de convexité : signe des différences secondes.

    Il ne suppose aucune forme. Sur des classes de quantile les abscisses ne
    sont pas également espacées, donc la différence seconde est la pente
    aval moins la pente amont — la définition de la convexité discrète.
    """
    if not curve:
        return {}
    mask = curve["centre"] <= cut
    x, y = curve["centre"][mask], curve["rate"][mask]
    if x.size < 4:
        return {}
    slope = np.diff(y) / np.diff(x)
    delta = np.diff(slope)
    return {
        "n": int(delta.size),
        "part_positive": float((delta > 0).mean()),
        "mediane": float(np.median(delta)),
    }


def jensen(curve: dict, service: np.ndarray, dies: np.ndarray) -> dict:
    """Écart de Jensen, sans forme fonctionnelle.

    `E[h(s)]` est le taux de décès du groupe entier ; `h(E[s])` est la courbe
    interpolée au service MOYEN. Leur différence est la part de mortalité
    imputable à la dispersion du service plutôt qu'à son niveau.
    """
    if not curve:
        return {}
    mean_service = float(service.mean())
    observed = float(dies.mean())
    at_mean = float(np.interp(mean_service, curve["centre"], curve["rate"]))
    return {
        "service_moyen": mean_service,
        "service_variance": float(service.var(ddof=1)),
        "service_cv": float(service.std(ddof=1) / mean_service) if mean_service > 0 else float("nan"),
        "mortalite_observee": observed,
        "mortalite_au_service_moyen": at_mean,
        "ecart_jensen": observed - at_mean,
        "ecart_relatif": (observed - at_mean) / at_mean if at_mean > 0 else float("nan"),
    }


def conditional(data: dict, cut_quantile: float) -> list[dict]:
    """Le test qui DÉCIDE : la convexité survit-elle à capital donné ?

    Si `c2` s'effondre une fois le capital tenu fixe, alors « service élevé »
    ne disait que « petite », et le mécanisme n'est pas établi. S'il survit
    dans chaque classe, la convexité est bien dans le service.
    """
    capital = data["capital"]
    edges = np.quantile(capital, np.linspace(0.0, 1.0, N_CAPITAL_BINS + 1))
    edges = np.unique(edges)
    out = []
    for bucket in range(edges.size - 1):
        low, high = edges[bucket], edges[bucket + 1]
        mask = (capital >= low) & (capital <= high) if bucket == edges.size - 2 else \
               (capital >= low) & (capital < high)
        service, dies = data["service"][mask], data["dies"][mask]
        if service.size < N_BINS * 20:
            continue
        curve = hazard_curve(service, dies, N_BINS)
        cut = float(np.quantile(service, cut_quantile)) if service.size else 0.0
        fit = curvature(curve, cut)
        if not fit:
            continue
        out.append({
            "classe_capital": bucket,
            "K_min": float(low), "K_max": float(high),
            "n": int(service.size),
            "service_moyen": float(service.mean()),
            "mortalite": float(dies.mean()),
            **fit,
        })
    return out


#: Quantiles rapportés pour la comparaison entre bras. La médiane ne
#: suffit pas : c'est la QUEUE du taux qui tue, et c'est elle que la règle
#: historique est soupçonnée de peupler.
RATE_QUANTILES = (0.5, 0.75, 0.9, 0.95, 0.99)


def quantile_profile(rate: np.ndarray, service: np.ndarray) -> dict:
    """Profil de queue du taux effectif et du fardeau, pour un bras."""
    finite = rate[np.isfinite(rate)]
    return {
        "n": int(finite.size),
        "taux": {f"q{q}": float(np.quantile(finite, q)) for q in RATE_QUANTILES},
        "taux_moyen": float(finite.mean()),
        "taux_cv": float(finite.std(ddof=1) / finite.mean()) if finite.mean() > 0 else float("nan"),
        "fardeau": {f"q{q}": float(np.quantile(service, q)) for q in RATE_QUANTILES},
        "fardeau_moyen": float(service.mean()),
    }


def neighbourhood(rates: dict[str, dict]) -> dict:
    """De quel bras à partage FIXE la règle historique est-elle voisine ?

    C'est la question du lot T posée directement sur la donnée, sans passer
    par un modèle de risque : si `marginal` — dont le partage moyen vaut
    0,53 — a un profil de taux qui ressemble à celui de `p = 1` et non à
    celui de `p = 0,5`, alors le résultat « une institution équitable en
    moyenne se comporte comme un asservissement » se lit dans la
    DISTRIBUTION, avant toute mortalité.

    La distance est prise sur les quantiles hauts, en écart relatif, parce
    que c'est là que les bras se séparent — leurs médianes sont proches par
    construction.
    """
    if "marginal" not in rates:
        return {}
    reference = rates["marginal"]["taux"]
    out = {}
    for arm, profile in rates.items():
        if arm == "marginal":
            continue
        gaps = [abs(profile["taux"][key] - reference[key]) / reference[key]
                for key in reference if reference[key] > 0]
        out[arm] = {
            "distance_relative_moyenne": float(np.mean(gaps)) if gaps else float("nan"),
            "distance_q099": (abs(profile["taux"]["q0.99"] - reference["q0.99"])
                              / reference["q0.99"]) if reference["q0.99"] > 0 else float("nan"),
        }
    if out:
        closest = min(out, key=lambda name: out[name]["distance_relative_moyenne"])
        out["plus_proche"] = closest
    return out


def weighting(directory: Path, t_min: float, t_max: float) -> dict:
    """La décomposition qui REMPLACE l'hypothèse de convexité.

    `record_rate_split` écrit à chaque pas trois agrégats de marché : la
    perte totale des donneuses `Σ L`, le service total contracté `Σ r·q`, et
    le surplus coopératif total `Σ Δ`. Le partage implicite peut donc se
    lire de DEUX façons, et elles ne coïncident pas :

    - moyenne PAR CONTRAT, `mkt_p_implied` = moyenne des `p_i` ;
    - moyenne PONDÉRÉE PAR LA VALEUR, `(Σ r·q − Σ L) / Σ Δ` = `Σ p_i Δ_i / Σ Δ_i`.

    Leur écart est une IDENTITÉ, pas une estimation :

        p_pondéré − p_moyen = Cov(p, Δ) / E[Δ]

    Un écart non nul dit donc exactement une chose : la règle en vigueur
    n'applique pas le même partage aux gros et aux petits contrats. Les bras
    à `p` fixe fournissent le témoin — chez eux les deux moyennes coïncident
    au chiffre près, par construction, ce qui vérifie l'estimateur avant
    qu'on le lise sur le bras historique.
    """
    per_seed = []
    for run in sorted(directory.iterdir(), key=lambda p: p.name):
        series = run / "series.csv"
        if not run.is_dir() or not series.exists():
            continue
        rq = loss = surplus = 0.0
        unweighted: list[float] = []
        with open(series, newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                time = float(row["t"])
                if time <= t_min or time > t_max or not row.get("mkt_rq"):
                    continue
                rq += float(row["mkt_rq"])
                loss += float(row["mkt_loss"])
                surplus += float(row["mkt_surplus"])
                # Une cellule VIDE est légitime : `write_series` prend l'UNION
                # des colonnes entre versions du moteur (voir JOURNAL).
                raw = row.get("mkt_p_implied", "")
                if raw and raw != "nan":
                    value = float(raw)
                    if value == value:
                        unweighted.append(value)
        if surplus <= 0.0 or not unweighted:
            continue
        weighted = (rq - loss) / surplus
        mean = sum(unweighted) / len(unweighted)
        per_seed.append({
            "seed": int(run.name[4:]),
            "p_pondere": weighted,
            "p_moyen": mean,
            "covariance_normalisee": weighted - mean,
        })
    if not per_seed:
        return {}
    out = {"n_runs": len(per_seed)}
    for key in ("p_pondere", "p_moyen", "covariance_normalisee"):
        mean, ci, n = student([row[key] for row in per_seed])
        out[key] = {"mean": mean, "ci95": ci, "n": n}
    out["par_graine"] = per_seed
    return out


def student(values: list[float]) -> tuple[float, float, int]:
    clean = [value for value in values if value == value and math.isfinite(value)]
    n = len(clean)
    if n < 2:
        return (clean[0] if clean else float("nan")), float("nan"), n
    mean = sum(clean) / n
    variance = sum((value - mean) ** 2 for value in clean) / (n - 1)
    return mean, T_CRITICAL * math.sqrt(variance / n), n


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path,
                        default=ROOT / "results" / "campaign" / "bargain")
    parser.add_argument("--t-min", type=float, default=3000)
    parser.add_argument("--t-max", type=float, default=4000)
    parser.add_argument("--horizon", type=int, default=10)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "analysis")
    parser.add_argument("--arms", type=str, default="marginal,p=0,p=0.5,p=1")
    parser.add_argument("--burden", choices=sorted(BURDENS), default="dette")
    parser.add_argument("--cause", choices=("all", "insolvency", "cascade"),
                        default="insolvency")
    parser.add_argument("--tag", type=str, default="")
    args = parser.parse_args(argv[1:])
    tag = args.tag or ""

    arms = [name for name in args.arms.split(",") if name]
    per_run: list[dict] = []
    curves: dict[str, dict] = {}
    conditionals: dict[str, list[dict]] = {}
    rates: dict[str, dict] = {}
    weights: dict[str, dict] = {}

    for arm in arms:
        directory = args.campaign / arm
        if not directory.is_dir():
            print(f"bras absent : {directory}", file=sys.stderr)
            continue
        pooled_service, pooled_dies, pooled_capital, pooled_rate = [], [], [], []
        for run in sorted(directory.iterdir(), key=lambda p: p.name):
            if not run.is_dir() or not (run / "panels.npz").exists():
                continue
            data = collect(run, args.t_min, args.t_max, args.horizon,
                           args.burden, args.cause)
            if data["n_producing"] == 0:
                continue
            cut = float(np.quantile(data["service"], FIT_QUANTILE))
            curve = hazard_curve(data["service"], data["dies"], N_BINS)
            fit = curvature(curve, cut)
            gap = jensen(curve, data["service"], data["dies"])
            per_run.append({
                "arm": arm, "seed": int(run.name[4:]),
                "n_entite_pas": data["n_producing"],
                "part_productrices": data["n_producing"] / data["n_total"],
                **{key: fit.get(key, float("nan")) for key in ("c1", "c2", "c2_se", "chi2_reduit")},
                **{key: gap.get(key, float("nan")) for key in
                   ("service_moyen", "service_variance", "service_cv",
                    "mortalite_observee", "mortalite_au_service_moyen",
                    "ecart_jensen", "ecart_relatif")},
            })
            pooled_service.append(data["service"])
            pooled_dies.append(data["dies"])
            pooled_capital.append(data["capital"])
            pooled_rate.append(data["rate"])

        if not pooled_service:
            continue
        pooled = {
            "service": np.concatenate(pooled_service),
            "dies": np.concatenate(pooled_dies),
            "capital": np.concatenate(pooled_capital),
            "rate": np.concatenate(pooled_rate),
        }
        cut = float(np.quantile(pooled["service"], FIT_QUANTILE))
        curve = hazard_curve(pooled["service"], pooled["dies"], N_BINS)
        curves[arm] = {
            "centre": curve["centre"].tolist(), "rate": curve["rate"].tolist(),
            "se": curve["se"].tolist(), "count": curve["count"].tolist(),
            "cut": cut,
            "fit": curvature(curve, cut),
            "differences_secondes": second_differences(curve, cut),
            "jensen": jensen(curve, pooled["service"], pooled["dies"]),
        }
        conditionals[arm] = conditional(pooled, FIT_QUANTILE)
        rates[arm] = quantile_profile(pooled["rate"], pooled["service"])
        weights[arm] = weighting(directory, args.t_min, args.t_max)

    args.out.mkdir(parents=True, exist_ok=True)
    if per_run:
        with open(args.out / f"lotI_convexity_runs{tag}.csv", "w", newline="",
                  encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(per_run[0]))
            writer.writeheader()
            writer.writerows(per_run)

    # Agrégation appariée par graine, bras par bras.
    summary: dict[str, dict] = {}
    for arm in arms:
        rows = [row for row in per_run if row["arm"] == arm]
        if not rows:
            continue
        entry = {}
        for key in ("c2", "c1", "ecart_jensen", "ecart_relatif", "service_moyen",
                    "service_variance", "service_cv", "mortalite_observee",
                    "mortalite_au_service_moyen"):
            mean, ci, n = student([row[key] for row in rows])
            entry[key] = {"mean": mean, "ci95": ci, "n": n}
        entry["n_runs"] = len(rows)
        summary[arm] = entry

    # Le verdict conditionnel : la convexité tient-elle dans CHAQUE classe de
    # capital, sur le bras historique ?
    verdict = {}
    reference = conditionals.get("marginal") or next(iter(conditionals.values()), [])
    if reference:
        positives = [row for row in reference if row["c2"] > 2 * row["c2_se"]]
        verdict = {
            "bras": "marginal" if "marginal" in conditionals else "premier",
            "n_classes_capital": len(reference),
            "n_classes_convexes": len(positives),
            "c2_min": min(row["c2"] for row in reference),
            "c2_max": max(row["c2"] for row in reference),
            "convexite_conditionnelle": len(positives) == len(reference),
        }

    payload = {
        "fardeau": args.burden,
        "fardeau_definition": BURDENS[args.burden][1],
        "cause": args.cause,
        "fenetre": [args.t_min, args.t_max],
        "horizon": args.horizon,
        "n_classes": N_BINS,
        "quantile_ajustement": FIT_QUANTILE,
        "resume": summary,
        "courbes": curves,
        "conditionnel": conditionals,
        "taux": rates,
        "voisinage": neighbourhood(rates),
        "ponderation": weights,
        "verdict": verdict,
    }
    (args.out / f"lotI_convexity{tag}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    for arm, entry in summary.items():
        print(f"{arm:>10} : c2 = {entry['c2']['mean']:+.5f} ± {entry['c2']['ci95']:.5f}   "
              f"Jensen = {entry['ecart_jensen']['mean']:+.5f} "
              f"({100 * entry['ecart_relatif']['mean']:+.1f} %)   "
              f"CV(s) = {entry['service_cv']['mean']:.3f}")
    for arm, entry in weights.items():
        if entry:
            print(f"{arm:>10} : p pondéré = {entry['p_pondere']['mean']:.4f} "
                  f"± {entry['p_pondere']['ci95']:.4f}   "
                  f"p par contrat = {entry['p_moyen']['mean']:.4f}   "
                  f"Cov(p,Δ)/E[Δ] = {entry['covariance_normalisee']['mean']:+.4f}")
    if verdict:
        print(f"conditionnel ({verdict['bras']}) : "
              f"{verdict['n_classes_convexes']}/{verdict['n_classes_capital']} "
              f"classes de capital convexes, c2 ∈ "
              f"[{verdict['c2_min']:+.5f}, {verdict['c2_max']:+.5f}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
