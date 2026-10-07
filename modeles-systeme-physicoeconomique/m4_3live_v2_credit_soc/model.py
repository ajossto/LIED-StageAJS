"""Adaptateur Simulation Lab du moteur M4.3Live-v2.

Créé le 2026-09-24, en même temps que celui de M4.3Live et de M4.4Rebond : ces
153 runs existaient dans le laboratoire sans qu'aucun adaptateur ne permette
d'en lancer de nouveaux.

Même protocole à interventions que M4.3Live — chauffe jusqu'à `t0`, puis un plan
est armé et la trajectoire se poursuit jusqu'à `T`. Voir la docstring de
l'adaptateur M4.3Live pour le raisonnement complet ; les différences de cette
lignée sont :

  - `loan_direction` et `phase_order` remplacent `transfer_cap` ;
  - `record_market_stats` s'ajoute ;
  - `Config` compte 24 champs au lieu de 22.

Une mise en garde propre à v2, relevée dans le moteur lui-même (m4_4/live.py,
§4.1) : sa version de `write_series` n'écrivait QUE cinq fichiers. Décès,
avalanches et événements de prêt étaient mesurés en mémoire quand les drapeaux
étaient armés, **puis perdus à la fin du processus** — d'où l'absence totale de
données d'avalanche dans les 153 runs archivés, alors même que le moteur savait
les produire. Armer `record_avalanches` ici ne garantit donc pas que les
fichiers correspondants soient écrits : cela dépend de la version de
`write_series` de CETTE lignée, et non des drapeaux.
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
ENGINE_ROOT = PROJECT_ROOT / "m4_3live_v2_credit_soc"
ENGINE_PKG = "m4_3live_v2"


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
    """Chargé PAR CHEMIN : `driver` est un nom de premier niveau que les trois
    lignées partagent, un import par nom résoudrait vers l'une ou l'autre selon
    l'ordre de `sys.path`."""
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


class M43LiveV2CreditSocModel(BaseSimulationModel):
    model_id = "m4_3live_v2_credit_soc"
    display_name = "M4.3Live-v2 crédit-société (rotation du crédit)"
    description = (
        "Deuxième lignée du protocole à interventions : chauffe jusqu'au pas t0, "
        "puis armement d'un plan et poursuite jusqu'à T. Se distingue de M4.3Live "
        "par la direction de prêt (`loan_direction`) et l'ordre des phases "
        "(`phase_order`), qui portent la question de la rotation du crédit. "
        "Le plan fait partie de la définition du run."
    )
    tags = ["m4_3live_v2", "credit", "soc", "interventions", "active"]

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
            ParameterSpec("T", "int", 4000, "Nombre de pas AU TOTAL, chauffe comprise",
                          minimum=0),
            ParameterSpec("t0", "int", 2000,
                          "Fin de la chauffe : le plan est armé après ce pas",
                          minimum=0),
            ParameterSpec("pop_max", "int", 30_000, "Limite de population", minimum=1),
            ParameterSpec("rho", "float", 1.0, "Intensité de marché ρ", minimum=1e-9),
            ParameterSpec("eta_beta", "float", 1.0, "Élasticité β à la population"),
            ParameterSpec("eta_n_ref", "float", 1.0, "Échelle de référence N_ref",
                          minimum=1e-9),
            # Listes relevées sur les constantes du moteur —
            # `m4_3live_v2.model.LOAN_DIRECTIONS`, `PHASE_ORDERS`, `RATE_RULES`,
            # `KERNEL_POLICIES` — contre lesquelles Config valide. Ma première
            # rédaction les avait devinées et se trompait dans les deux sens :
            # elle rejetait `deprec_first` et `surplus_share`, pourtant employés
            # par les runs archivés, et proposait `v2`, `poorest_lends`,
            # `average`, `exact`, `lut`, qui n'existent pas.
            #
            # `target_rule` reste sans choices : aucune constante ne le valide.
            ParameterSpec("target_rule", "str", "arithmetic", "Institution de principal"),
            ParameterSpec("loan_direction", "str", "free", "Direction du prêt",
                          choices=["free", "richest_lends"]),
            ParameterSpec("phase_order", "str", "v1", "Ordre des phases",
                          choices=["deprec_first", "v1"]),
            ParameterSpec("rate_rule", "str", "marginal", "Règle de taux",
                          choices=["marginal", "surplus_share"]),
            ParameterSpec("surplus_share_p", "float", 0.5, "Partage du surplus p",
                          minimum=0.0, maximum=1.0),
            ParameterSpec("kernel_policy", "str", "exact_lut", "Politique du noyau",
                          choices=["exact_lut", "hybrid"]),
            ParameterSpec("lut_threshold", "int", 1800, "Seuil de la table", minimum=0),
            ParameterSpec("lut_points", "int", 65, "Points de la table", minimum=2),
            ParameterSpec("record_deaths", "bool", True, "Enregistrer les décès"),
            ParameterSpec("record_avalanches", "bool", True, "Enregistrer les avalanches"),
            ParameterSpec("record_market_stats", "bool", True,
                          "Enregistrer les statistiques de marché"),
            ParameterSpec("record_loan_events", "bool", False,
                          "Enregistrer les événements de prêt (très volumineux)"),
            ParameterSpec(
                "plan_json", "str", "[]",
                "Plan d'interventions, en JSON — liste d'objets "
                "{\"t\": 2001, \"param\": \"A\", \"value\": 1.5, \"scope\": \"all\"}. "
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
            "message": f"Chauffe M4.3Live-v2 jusqu'au pas {t0}",
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
            message=(f"M4.3Live-v2 terminé à t={simulation.t} "
                     f"({len(plan)} intervention(s) au plan)"),
            extra={"seed": seed, "model_status": simulation.status,
                   "interventions": len(getattr(simulation, "intervention_log", []))},
        )


MODEL = M43LiveV2CreditSocModel()
