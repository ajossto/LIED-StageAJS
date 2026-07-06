"""Catalogue des runs M3 : groupes du protocole, verdicts, découverte des runs.

Chaque groupe correspond à une étape du protocole pré-enregistré (rapport 02)
et porte : la question posée, le verdict (rapports 04/05/06), et la liste des
runs archivés qui y répondent. L'ordre des groupes suit le déroulé de la
recherche — c'est la structure de présentation de l'explorateur web.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # m3_credit_soc/
RESULTS = ROOT / "experiments" / "m3" / "results"
REPORTS = ROOT / "reports"

# ---------------------------------------------------------------- groupes

GROUPS = [
    dict(
        id="calibration",
        title="0. Calibration pré-enregistrée de (s, c)",
        question="Dans quelles plages (s, c) l'ablation B conserve-t-elle le "
                 "régime démographique de M2 (population quasi stationnaire, "
                 "mortalité endogène) ?",
        verdict="Seule la colonne c = 0,10 est viable : à c ≤ 0,05 le stock de "
                "liquidité L* ≈ (1−s)√K*/c amortit le plancher d0 et éteint la "
                "mortalité (population divergente). Baseline figée à "
                "(s = 0,75 ; c = 0,10) par la règle pré-enregistrée.",
        report="03 §4",
        pattern=r"^calib_B_",
    ),
    dict(
        id="baseline",
        title="A. Baseline M3 (10 seeds, T = 4000)",
        question="Quel est le régime de référence du modèle complet : "
                 "distributions de L, K, NW, revenu ; démographie ; crédit ; "
                 "avalanches ?",
        verdict="Régime quasi stationnaire reproductible (pop 1103–1183). "
                "NW : corps Fisk, queue α ≈ 2,69, jamais identifiée Pareto. "
                "Revenu : double Pareto-lognormale 10/10 (signature Reed). "
                "L : Fisk — l'hypothèse Boltzmann-Gibbs échoue (ΔAIC ≈ 700). "
                "K : lognormal mécanistique. Zéro défaut de liquidité ; "
                "avalanches sous-Poisson (max 7).",
        report="04 §2",
        pattern=r"^baseline_s\d+$",
    ),
    dict(
        id="ablation_B",
        title="B. Sans crédit — le modèle nul (10 seeds, T = 4000)",
        question="Question causale centrale : le crédit change-t-il au moins "
                 "deux signatures majeures (critère pré-enregistré) ?",
        verdict="Critère formellement atteint, mais par des signatures "
                "démographiques redondantes : population et espérance de vie "
                "×0,5, renouvellement accéléré. Les DISTRIBUTIONS sont "
                "indiscernables de A (mêmes familles, α = 2,69 des deux côtés, "
                "CCDF superposées) : le verdict M2 « crédit distributionnellement "
                "neutre » se répète.",
        report="04 §3 ; 06 §2.6",
        pattern=r"^abl_B_s\d+$",
    ),
    dict(
        id="mecanismes",
        title="C · D · E. Décomposition du canal létal du crédit",
        question="D'où vient l'effet démographique : de la conversion "
                 "productive L→K (C), des pertes de créances (D), ou de la "
                 "perte du flux d'intérêts (E) ?",
        verdict="C (crédit non productif) reproduit tout l'effet → le canal "
                "létal est NOMINAL, pas productif. D (pertes indemnisées) = A "
                "→ les pertes de stock n'y sont pour rien. E (flux maintenu) "
                "récupère ~40 % de l'écart → la perte de flux futur domine la "
                "perte de stock. Hiérarchie : nominal ≫ flux > stock ≈ 0.",
        report="04 §4",
        pattern=r"^abl_[CDE]_s\d+$",
    ),
    dict(
        id="reseau",
        title="F (+ F'' exploratoire). La topologie du réseau compte-t-elle ?",
        question="À bilans agrégés comparables, la structure du réseau de "
                 "crédit change-t-elle les signatures ?",
        verdict="F (appariement aléatoire) est CONFONDUE : elle éteint le "
                "marché (volume ÷6,5) au lieu d'en randomiser la topologie — "
                "échec de conception documenté. F'' (prêteuse aléatoire, "
                "exploratoire) : la population suit le VOLUME de crédit de "
                "façon monotone à travers les trois règles d'appariement — "
                "aucune évidence d'effet topologique au-delà du volume.",
        report="05 §2.1 ; 04 §9",
        pattern=r"^abl_F2?_s\d+$",
    ),
    dict(
        id="chocs",
        title="G. Chocs corrélés (macro, sectoriels ; + G2b/G2c exploratoires)",
        question="Les chocs i.i.d. étouffent-ils les cascades ? La corrélation "
                 "réveille-t-elle le canal de fragilité ?",
        verdict="G1 macro : confondue (à σ² constant, la corrélation raréfie "
                "le crédit lui-même) ; variance inter-seed massive. G2 "
                "sectoriel : premières avalanches non triviales (max 36–72), "
                "mais la sur-dispersion suit la corrélation imposée "
                "CONTINÛMENT (var/mean 0,07→0,38→0,84, jamais > 1) : le "
                "système amplifie, il ne s'auto-organise pas. Zéro défaut de "
                "liquidité même sous chocs corrélés.",
        report="04 §5 ; 05 §2.2",
        pattern=r"^abl_G",
    ),
    dict(
        id="plancher",
        title="H. Sans plancher d0 — la découverte du programme",
        question="Le plancher d'absorption exogène d0 est-il nécessaire au "
                 "bornage endogène de la population ?",
        verdict="NON — découverte positive : sans d0, seules les endettées "
                "peuvent mourir (D > actifs) et le système se borne quand même "
                "(pop 5574/5566/5649 sur 3 seeds, d/b = 0,98). Le plancher "
                "devient ENDOGÈNE via la dette contractuelle ; seul régime du "
                "programme avec des défauts de liquidité en nombre (67–79). "
                "Base du M4 recommandé (dette de subsistance contractée).",
        report="04 §10 ; 06 §2.11",
        pattern=r"^abl_H_s\d+$",
    ),
    dict(
        id="renouvellement",
        title="I. Sans renouvellement démographique",
        question="Que subsiste-t-il sans le mécanisme Reed (λ = 0, cohorte "
                 "initiale de 1000) ?",
        verdict="RIEN : extinction totale à t ≈ 1760 (2 seeds ; le 3e à N = 1). "
                "Le renouvellement n'est pas un ingrédient de la distribution, "
                "c'est la condition d'existence du régime stationnaire.",
        report="04 §6 ; 06 §2.2",
        pattern=r"^abl_I_s\d+$",
    ),
    dict(
        id="echelle",
        title="J. Extensivité en λ",
        question="Le régime dépend-il de l'échelle (λ = 3, 30 vs 10) ?",
        verdict="Extensivité propre : N*/λ = 114–115 pour λ ∈ {3, 10, 30}. "
                "Aucune dépendance d'échelle des formes.",
        report="04 §6",
        pattern=r"^abl_J[ab]_s\d+$",
    ),
    dict(
        id="grille",
        title="Grille de robustesse (σ, s, c, k, d0 — 45 cellules)",
        question="Les formes tiennent-elles sans réglage fin ? Existe-t-il une "
                 "zone critique (SOC) ou un régime à défauts de liquidité ?",
        verdict="Formes universelles : Fisk 36/37, dPlN 37/37. α(NW) insensible "
                "à k, s, c, d0 ; réponse monotone lisse à σ (3,71→2,19), sans "
                "transition ni plateau — pas de zone SOC. Défauts de liquidité : "
                "4 événements en tout (à s = 0,9), zéro ailleurs. Fenêtre "
                "d'existence étroite : σ ≥ 0,25 et c ≈ 0,10 requis ; c = 0,02 "
                "diverge ET fait exploser le carnet (2,6 M de contrats).",
        report="04 §8",
        pattern=r"^grid_",
    ),
    dict(
        id="longs",
        title="Runs longs (T = 20 000, A et B)",
        question="La queue est-elle stable à long horizon ? Dérive-t-elle "
                 "différemment avec ou sans crédit ?",
        verdict="Exposant de queue stationnaire autour de 2,5–2,8 sur 20 000 "
                "pas, sans dérive, A et B indiscernables : la stabilité "
                "long-horizon ne doit rien au crédit.",
        report="04 §7",
        pattern=r"^long_",
    ),
]

# Champs de config qui diffèrent de la baseline → affichés comme « variante »
_BASELINE_KEYS = dict(credit=True, loan_target="K", claim_loss="on",
                      flow_loss="on", market_selection="assortative",
                      shock_rho_macro=0.0, shock_rho_sector=0.0, n_init=0,
                      lam=10.0, d0=28.0, s=0.75, c=0.10, sigma=0.25, k=6,
                      T=2000)


def _variant_of(cfg: dict) -> str:
    diffs = []
    for key, base in _BASELINE_KEYS.items():
        val = cfg.get(key, base)
        if val != base and not (key == "T"):
            diffs.append(f"{key}={val}")
    return ", ".join(diffs) if diffs else "baseline"


def list_runs() -> dict:
    """Index complet : groupes du protocole avec leurs runs et méta-données."""
    runs_by_group: dict[str, list] = {g["id"]: [] for g in GROUPS}
    ungrouped = []
    for run_dir in sorted(RESULTS.iterdir()):
        summary_p = run_dir / "summary.json"
        config_p = run_dir / "config.json"
        if not (summary_p.exists() and config_p.exists()):
            continue
        summary = json.loads(summary_p.read_text())
        cfg = json.loads(config_p.read_text())
        entry = dict(
            id=run_dir.name,
            seed=cfg.get("seed"),
            T=cfg.get("T"),
            status=summary.get("status"),
            pop_final=summary.get("pop_final"),
            loans_final=summary.get("n_loans_final"),
            wall_seconds=summary.get("wall_seconds"),
            variant=_variant_of(cfg),
            has_validation=(run_dir / "validation.json").exists(),
        )
        for g in GROUPS:
            if re.match(g["pattern"], run_dir.name):
                runs_by_group[g["id"]].append(entry)
                break
        else:
            ungrouped.append(entry)
    out = []
    for g in GROUPS:
        out.append(dict(
            id=g["id"], title=g["title"], question=g["question"],
            verdict=g["verdict"], report=g["report"],
            runs=runs_by_group[g["id"]],
        ))
    return dict(groups=out, ungrouped=ungrouped)


def run_paths(run_id: str) -> Path:
    """Chemin du dossier d'un run, avec garde anti-traversée."""
    if not re.fullmatch(r"[A-Za-z0-9._-]+", run_id):
        raise ValueError(f"run_id invalide : {run_id!r}")
    p = RESULTS / run_id
    if not p.is_dir():
        raise FileNotFoundError(run_id)
    return p
