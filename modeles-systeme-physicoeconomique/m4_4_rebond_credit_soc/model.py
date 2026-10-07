"""Adaptateur Simulation Lab du moteur M4.4Rebond.

Créé le 2026-09-24, en même temps que ceux de M4.3Live et M4.3Live-v2 : ces 372
runs existaient dans le laboratoire sans qu'aucun adaptateur ne permette d'en
lancer de nouveaux — ils venaient de `scripts/campaign.py` et de
`scripts/import_to_simulation_lab.py`.

Même protocole à interventions que les deux lignées précédentes : chauffe
jusqu'au pas `t0`, armement d'un plan, poursuite jusqu'à `T`. Voir la docstring
de l'adaptateur M4.3Live pour le raisonnement complet sur `plan_json`.

CE QUE CETTE LIGNÉE AJOUTE :

  - `bargain_p` (partage de la rente de négociation) et `record_rate_split` ;
  - `record_loss_edges` et `panel_every`, qui produisent `loss_edges.npz` et
    `panels.npz` ;
  - `Config` compte 28 champs, contre 22 et 24 pour les deux autres.

UNE RÉSERVE IMPORTANTE SUR LA REPRODUCTION DES RUNS ARCHIVÉS. Les 348 runs
archivés qui déclarent un `checkpoint` reprennent une chauffe enregistrée sur
disque (`snapshot_t*.pkl`, tous présents). Cet adaptateur, lui, **refait la
chauffe depuis la graine** au lieu de recharger l'instantané. C'est équivalent
si et seulement si le moteur est resté déterministe et inchangé depuis
l'écriture de ces instantanés — ce qui N'A PAS ÉTÉ VÉRIFIÉ pour cette lignée.
Tant que ça ne l'est pas, cet adaptateur sert à lancer des runs NEUFS ; il ne
doit pas être branché sur une resimulation destructrice des runs existants.
"""

from __future__ import annotations

import dataclasses
import importlib
import importlib.util
import json
import sys
import time
from contextlib import contextmanager
from pathlib import Path

from simulation_lab.contracts import (
    BaseSimulationModel,
    ParameterSpec,
    SimulationResult,
    collect_artifacts,
)
from simulation_lab.progress import emit_progress, ensure_not_cancelled

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = PROJECT_ROOT / "m4_4_rebond_credit_soc"
ENGINE_PKG = "m4_4"


@contextmanager
def _engine_on_path():
    path = str(ENGINE_ROOT)
    sys.path.insert(0, path)
    try:
        yield
    finally:
        if path in sys.path:
            sys.path.remove(path)


def _load_driver():
    """Chargé PAR CHEMIN — `driver` est un nom de premier niveau que les trois
    lignées portent toutes ; le moteur prend déjà cette précaution pour
    `scripts.tension_figures`, pour exactement la même raison."""
    name = f"simulation_lab_{ENGINE_PKG}_driver"
    if name in sys.modules:
        return sys.modules[name]
    with _engine_on_path():
        spec = importlib.util.spec_from_file_location(
            name, ENGINE_ROOT / "driver" / "headless.py"
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Impossible de charger {ENGINE_ROOT}/driver/headless.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return module


def _load_model():
    with _engine_on_path():
        return importlib.import_module(f"{ENGINE_PKG}.model")


class M44RebondCreditSocModel(BaseSimulationModel):
    model_id = "m4_4_rebond_credit_soc"
    display_name = "M4.4Rebond crédit-société (rebond après choc)"
    description = (
        "Troisième lignée du protocole à interventions : chauffe jusqu'au pas t0, "
        "armement d'un plan, poursuite jusqu'à T. Étudie le rebond de l'économie "
        "après un choc de paramètre, par comparaison à un bras de contrôle "
        "apparié partageant exactement les lignes de série de la chauffe. Ajoute "
        "la rente de négociation (`bargain_p`), les arêtes de perte "
        "(`record_loss_edges`) et les panneaux par entité (`panel_every`). "
        "Le plan fait partie de la définition du run."
    )
    tags = ["m4_4", "rebond", "credit", "soc", "interventions", "active"]

    def parameter_specs(self) -> list[ParameterSpec]:
        return [
            ParameterSpec("gamma", "float", 0.5, "Exposant de concavité γ",
                          minimum=0.05, maximum=0.95),
            ParameterSpec("A", "float", 1.0, "Échelle productive A", minimum=1e-9),
            ParameterSpec("lam", "float", 30.0, "Naissances λ", minimum=0.0),
            ParameterSpec("delta", "float", 0.01, "Dépréciation δ",
                          minimum=0.0, maximum=0.999999),
            ParameterSpec("sigma", "float", 0.01, "Volatilité σ", minimum=0.0),
            ParameterSpec("K0", "float", 25.0, "Capital de naissance K₀", minimum=1e-12),
            ParameterSpec("T", "int", 6000, "Nombre de pas AU TOTAL, chauffe comprise",
                          minimum=0),
            ParameterSpec("t0", "int", 2000,
                          "Fin de la chauffe : le plan est armé après ce pas",
                          minimum=0),
            ParameterSpec("pop_max", "int", 30_000, "Limite de population", minimum=1),
            ParameterSpec("rho", "float", 1.0, "Intensité de marché ρ", minimum=1e-9),
            ParameterSpec("eta_beta", "float", 1.0, "Élasticité β à la population"),
            ParameterSpec("eta_n_ref", "float", 1.0, "Échelle de référence N_ref",
                          minimum=1e-9),
            # Listes relevées sur les constantes du moteur — `m4_4.model`
            # expose `LOAN_DIRECTIONS`, `PHASE_ORDERS`, `RATE_RULES` et
            # `KERNEL_POLICIES`, contre lesquelles Config valide. Noter que
            # `rate_rule` compte ICI une troisième valeur, `bargain`, absente
            # des deux lignées précédentes : c'est elle qui porte la rente de
            # négociation (`bargain_p`), et des runs archivés l'emploient.
            # Ma première rédaction, devinée, la rejetait purement et
            # simplement.
            #
            # `target_rule` reste sans choices : aucune constante ne le valide.
            ParameterSpec("target_rule", "str", "arithmetic", "Institution de principal"),
            ParameterSpec("loan_direction", "str", "free", "Direction du prêt",
                          choices=["free", "richest_lends"]),
            ParameterSpec("phase_order", "str", "v1", "Ordre des phases",
                          choices=["deprec_first", "v1"]),
            ParameterSpec("rate_rule", "str", "marginal", "Règle de taux",
                          choices=["bargain", "marginal", "surplus_share"]),
            ParameterSpec("surplus_share_p", "float", 0.5, "Partage du surplus p",
                          minimum=0.0, maximum=1.0),
            ParameterSpec("bargain_p", "float", 0.5, "Partage de la rente de négociation",
                          minimum=0.0, maximum=1.0),
            ParameterSpec("kernel_policy", "str", "exact_lut", "Politique du noyau",
                          choices=["exact_lut", "hybrid"]),
            ParameterSpec("lut_threshold", "int", 1800, "Seuil de la table", minimum=0),
            ParameterSpec("lut_points", "int", 65, "Points de la table", minimum=2),
            ParameterSpec("record_deaths", "bool", True, "Enregistrer les décès"),
            ParameterSpec("record_avalanches", "bool", True, "Enregistrer les avalanches"),
            ParameterSpec("record_market_stats", "bool", True,
                          "Enregistrer les statistiques de marché"),
            ParameterSpec("record_loss_edges", "bool", True,
                          "Enregistrer les arêtes de perte (loss_edges.npz)"),
            ParameterSpec("record_rate_split", "bool", False,
                          "Enregistrer la décomposition du taux"),
            ParameterSpec("record_loan_events", "bool", False,
                          "Enregistrer les événements de prêt (très volumineux)"),
            ParameterSpec("panel_every", "int", 10,
                          "Fréquence des panneaux par entité (0 = aucun)", minimum=0),
            ParameterSpec(
                "plan_json", "str", "[]",
                "Plan d'interventions, en JSON — liste d'objets "
                "{\"t\": 2001, \"param\": \"delta\", \"value\": 0.05, \"scope\": \"all\"}. "
                "Liste vide = bras de contrôle.",
            ),
            ParameterSpec("arm", "str", "", "Nom du bras (libellé enregistré)"),
        ]

    def run(
        self,
        parameters: dict,
        output_dir: Path,
        seed: int,
        run_label: str = "",
    ) -> SimulationResult:
        driver = _load_driver()
        modele = _load_model()

        try:
            plan = json.loads(parameters.get("plan_json") or "[]")
        except ValueError as erreur:
            raise ValueError(f"plan_json n'est pas du JSON valide : {erreur}") from erreur
        if isinstance(plan, dict):
            plan = plan.get("interventions", [])
        if not isinstance(plan, list):
            raise ValueError("plan_json doit décrire une LISTE d'interventions")

        total = int(parameters["T"])
        t0 = min(int(parameters["t0"]), total)
        steps = max(0, total - t0)

        champs = {f.name for f in dataclasses.fields(modele.Config)}
        base = {nom: valeur for nom, valeur in parameters.items() if nom in champs}
        base["seed"] = seed

        config = driver.build_config(**{**base, "T": t0})
        simulation = modele.Simulation(config)
        depart = time.monotonic()
        ensure_not_cancelled()
        emit_progress({
            "progress": 5.0,
            "message": f"Chauffe M4.4Rebond jusqu'au pas {t0}",
            "telemetry": {"phase": "chauffe", "t": 0, "t_total": total,
                          "elapsed_seconds": 0.0},
            "alerts": [],
        })
        driver.run_plan(simulation, [], t0)

        if steps:
            ensure_not_cancelled()
            emit_progress({
                "progress": 50.0,
                "message": (f"Bras armé ({len(plan)} intervention(s)) "
                            f"jusqu'au pas {total}"),
                "telemetry": {"phase": "bras", "t": simulation.t, "t_total": total,
                              "interventions": len(plan),
                              "elapsed_seconds": time.monotonic() - depart},
                "alerts": [],
            })
            simulation.config = driver.build_config(
                **{**simulation.config.to_dict(), "T": total}
            )
            driver.run_plan(simulation, plan, steps)

        driver.write_outputs(simulation, Path(output_dir), {
            "wall_seconds": time.monotonic() - depart,
            "plan": plan,
            "arm": parameters.get("arm") or None,
            "t0": t0,
        })

        sommaire = {}
        chemin = Path(output_dir) / "summary.json"
        if chemin.exists():
            try:
                sommaire = json.loads(chemin.read_text(encoding="utf-8"))
            except ValueError:
                sommaire = {}
        return SimulationResult(
            status="completed",
            summary=sommaire,
            artifacts=collect_artifacts(Path(output_dir)),
            message=(f"M4.4Rebond terminé à t={simulation.t} "
                     f"({len(plan)} intervention(s) au plan)"),
            extra={"seed": seed, "model_status": simulation.status,
                   "interventions": len(getattr(simulation, "intervention_log", []))},
        )


MODEL = M44RebondCreditSocModel()
