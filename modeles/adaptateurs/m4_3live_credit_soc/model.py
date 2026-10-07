"""Adaptateur Simulation Lab du moteur M4.3Live.

Créé le 2026-09-24. Ces 203 runs existaient dans le laboratoire sans qu'aucun
adaptateur ne permette d'en lancer de nouveaux : ils avaient été produits par
les scripts de campagne et importés après coup.

CE MODÈLE N'EST PAS UNE SIMULATION ORDINAIRE. C'est un protocole à
interventions : on chauffe la population jusqu'au pas `t0`, puis on « arme » un
plan — un ou plusieurs changements de paramètre appliqués à un pas donné — et on
poursuit jusqu'à `T`. Un run n'est donc pas défini par ses paramètres et sa
graine seuls : **le plan en fait partie**. C'est ce que fait `driver/headless.py`
avec ses commandes `burn` puis `arm`, et c'est ce que cet adaptateur reproduit
en un seul processus, sans passer par le fichier d'instantané intermédiaire qui
n'est qu'un artefact d'enchaînement en ligne de commande.

POURQUOI LE PLAN EST UNE CHAÎNE JSON. `ParameterSpec` n'admet que bool, int,
float et str (cf. `_coerce_value` dans simulation_lab/contracts.py) : une liste
de dictionnaires n'est pas représentable. On aurait pu piloter par le nom du
bras (`arm`), puisque chaque nom correspond en général à un plan canonique —
mais **pas ici** : dans cette lignée, `control` désigne deux plans distincts,
l'un vide et l'autre non. Un adaptateur piloté par le nom produirait donc un run
sur deux faux. `arm` est conservé comme libellé enregistré ; `plan_json` fait
foi.
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
ENGINE_ROOT = PROJECT_ROOT / "m4_3live_credit_soc"
ENGINE_PKG = "m4_3live"


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
    """Charge `driver/headless.py` PAR CHEMIN, et non par son nom.

    `driver` est un nom de premier niveau générique que les trois lignées
    (live, live_v2, m4_4) portent toutes : un import par nom résoudrait vers
    l'une ou l'autre selon l'ordre de `sys.path`. Le moteur lui-même prend cette
    précaution pour `scripts.tension_figures`, pour la même raison.
    """
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


class M43LiveCreditSocModel(BaseSimulationModel):
    model_id = "m4_3live_credit_soc"
    display_name = "M4.3Live crédit-société (institution de production jointe)"
    description = (
        "Protocole à interventions : la population est chauffée jusqu'au pas t0, "
        "puis un plan est armé — un ou plusieurs paramètres changent de valeur à "
        "un pas donné, sur tout ou partie des entités — et la trajectoire se "
        "poursuit jusqu'à T. Sert à mesurer le rebond d'une économie soumise à "
        "un choc de paramètre, par comparaison avec un bras de contrôle sans "
        "intervention. Le plan fait partie de la définition du run."
    )
    tags = ["m4_3live", "credit", "soc", "interventions", "active"]

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
            # Les listes ci-dessous sont celles des constantes du moteur —
            # `m4_3live.model.TRANSFER_CAPS`, `RATE_RULES` et `KERNEL_POLICIES`,
            # contre lesquelles Config valide en levant une ValueError. Elles
            # ont été RELEVÉES, pas devinées : ma première rédaction les avait
            # inventées et se trompait dans les deux sens à la fois — elle
            # rejetait des valeurs légales (`surplus_share`, `equalization`,
            # `hybrid`) et en proposait d'inexistantes (`average`, `none`,
            # `exact`, `lut`). À revérifier à la source si le moteur bouge.
            #
            # `target_rule` n'a PAS de choices : aucune constante ne le valide
            # dans ce moteur. Inventer une liste ici rejetterait peut-être une
            # valeur parfaitement légale ; mieux vaut laisser passer et laisser
            # le moteur trancher.
            ParameterSpec("target_rule", "str", "arithmetic", "Institution de principal"),
            ParameterSpec("transfer_cap", "str", "optimum", "Plafond de transfert",
                          choices=["equalization", "optimum"]),
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
        if isinstance(plan, dict):          # forme {"interventions": [...]}
            plan = plan.get("interventions", [])
        if not isinstance(plan, list):
            raise ValueError("plan_json doit décrire une LISTE d'interventions")

        total = int(parameters["T"])
        t0 = min(int(parameters["t0"]), total)
        steps = max(0, total - t0)

        champs = {f.name for f in dataclasses.fields(modele.Config)}
        base = {nom: valeur for nom, valeur in parameters.items() if nom in champs}
        base["seed"] = seed

        # Phase 1 — la chauffe, sans aucune intervention.
        config = driver.build_config(**{**base, "T": t0})
        simulation = modele.Simulation(config)
        depart = time.monotonic()
        ensure_not_cancelled()
        emit_progress({
            "progress": 5.0,
            "message": f"Chauffe M4.3Live jusqu'au pas {t0}",
            "telemetry": {"phase": "chauffe", "t": 0, "t_total": total,
                          "elapsed_seconds": 0.0},
            "alerts": [],
        })
        driver.run_plan(simulation, [], t0)

        # Phase 2 — le bras : le plan est soumis, puis on poursuit jusqu'à T.
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

        # `write_outputs` écrit lui-même series, tension, kernel.json ET
        # summary.json : on ne duplique rien, on complète seulement les
        # métadonnées que la ligne de commande y mettrait.
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
            message=(f"M4.3Live terminé à t={simulation.t} "
                     f"({len(plan)} intervention(s) au plan)"),
            extra={"seed": seed, "model_status": simulation.status,
                   "interventions": len(getattr(simulation, "intervention_log", []))},
        )


MODEL = M43LiveCreditSocModel()
