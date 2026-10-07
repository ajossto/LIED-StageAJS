"""
simulation.py — Moteur de simulation multi-agents.

Ce module implémente la dynamique complète du modèle économique multi-agents.
Un pas de simulation (run_step) exécute les 9 étapes suivantes dans l'ordre :

  1. Mouvement brownien des α   — choc de productivité géométrique
  2. Création d'entités         — arrivée Poisson(λ) de nouveaux agents
  3. Extraction                 — Π_i = α_i √P_i ajouté au liquide
  4. Paiement des intérêts      — r·q de chaque emprunteur vers son prêteur,
                                   avec mobilisation de capacité si illiquidité
  5. Amortissement              — remboursement géométrique τ·q du principal (τ=0 par défaut)
  6. Dépréciation               — décroissance géométrique de tous les actifs
  7. Marché du crédit           — appariement aléatoire k-pool, prêts nouveaux
  8. Cascades de faillites      — résolution itérative des insolvabilités
  9. Auto-investissement        — conversion φ·surplus en capital endogène

Architecture technique :
  - Références par ID entier : Entity et Loan ne se pointent pas mutuellement.
    Les conteneurs sim.entities et sim.loans sont des Dict[int, ...].
  - RNG isolé : random.Random(seed) utilisé exclusivement, jamais le module
    random global. Garantit la reproductibilité indépendamment du contexte.
  - Caches d'intérêts (Bloc 8) : charges_interets et revenus_interets sont
    des attributs maintenus en temps réel sur chaque Entity. Ils sont mis à jour
    de façon incrémentale dans toute opération qui crée, modifie ou détruit un prêt.
    Suppression du _rebuild_interest_cache() O(N_prêts) à chaque pas.
  - Redistribution directe lors des faillites (pas de « masses de faillite ») :
    les créances de l'entité faillie sont fractionnées entre ses créanciers au
    prorata de leurs encours, évitant une entité intermédiaire temporaire.

Statistiques : le Collector (statistics.py) est instancié dans Simulation
               et appelé à la fin de chaque pas via record_step().
"""

from __future__ import annotations

import csv
import json
import math
import random
from dataclasses import asdict, fields
from typing import Any, Callable, Dict, List, Optional, Tuple

from config import SimulationConfig
from models import Entity, Loan
from statistics import CascadeEvent, Collector

# Probabilité qu'une entité nouvellement créée (après t=0) soit enregistrée
# pour le suivi détaillé (entity_histories.csv). 3 % ≈ 3 entités surveillées
# pour une cohorte de 100 nouveaux agents.
_P_WATCH_NEW = 0.03


PARAMETER_RISK_CATEGORIES = {
    # Catégorie A : modifiables entre deux pas avec faible risque structurel.
    "theta": "A",
    "mu": "A",
    "seuil_ratio_endettement": "A",
    "fraction_taux_emprunteur": "A",
    "lambda_creation": "A",
    "max_credit_iterations": "A",
    "n_candidats_pool": "A",
    "fraction_auto_investissement": "A",
    "coefficient_reliquefaction": "A",
    "taux_depreciation_liquide": "A",
    "taux_depreciation_endo": "A",
    "log_events": "A",
    "duree_simulation": "A",
    # Catégorie B : modifiables avec précautions explicites.
    "alpha_min": "B",
    "alpha_max": "B",
    "actif_liquide_initial": "B",
    "passif_inne_initial": "B",
    "alpha_sigma_brownien": "B",
    "seuil_ratio_liquide_passif": "B",
    "taux_amortissement": "B",
    "epsilon": "B",
    "freq_snapshot": "B",
    # Catégorie C : refusés en cours de simulation.
    "seed": "C",
    "n_entites_initiales": "C",
    "taux_depreciation_exo": "C",
    "alpha": "C",
}

PARAMETER_SCOPE_RULES = {
    "theta": {"global_config"},
    "mu": {"global_config"},
    "seuil_ratio_endettement": {"global_config"},
    "fraction_taux_emprunteur": {"global_config"},
    "lambda_creation": {"global_config", "future_entities"},
    "max_credit_iterations": {"global_config"},
    "n_candidats_pool": {"global_config"},
    "fraction_auto_investissement": {"global_config"},
    "coefficient_reliquefaction": {"global_config"},
    "taux_depreciation_liquide": {"global_config"},
    "taux_depreciation_endo": {"global_config"},
    "log_events": {"global_config"},
    "duree_simulation": {"global_config"},
    "alpha_min": {"global_config", "future_entities"},
    "alpha_max": {"global_config", "future_entities"},
    "actif_liquide_initial": {"global_config", "future_entities"},
    "passif_inne_initial": {"global_config", "future_entities"},
    "alpha_sigma_brownien": {"global_config"},
    "seuil_ratio_liquide_passif": {"global_config"},
    "taux_amortissement": {"global_config"},
    "epsilon": {"global_config"},
    "freq_snapshot": {"global_config"},
}

SCOPES = {"global_config", "future_entities", "existing_entities", "all_entities", "forbidden"}

ENTITY_UPDATE_NAMES = {"alpha_multiplier", "alpha_set", "alpha_add", "alpha_min", "alpha_max"}


class Simulation:
    """
    Moteur principal de la simulation multi-agents.

    Attributs publics utiles en lecture :
        entities    — Dict[int, Entity] : toutes les entités (vivantes et mortes)
        loans       — Dict[int, Loan]   : tous les prêts (actifs et inactifs)
        stats       — List[Dict]        : statistiques légères par pas
        collector   — Collector         : données statistiques riches
        current_step — int              : pas courant (incrémenté en fin de run_step)
    """

    def __init__(self, config: Optional[SimulationConfig] = None) -> None:
        self.config = config or SimulationConfig()
        self.initial_config_snapshot: Dict[str, Any] = asdict(self.config)

        # RNG isolé : toute la stochasticité passe par ce générateur.
        # Garantit la reproductibilité : même seed → même trajectoire.
        self.rng = random.Random(self.config.seed)

        # Conteneurs principaux (croissent au fil de la simulation, jamais purgés).
        self.entities: Dict[int, Entity] = {}
        self.loans: Dict[int, Loan] = {}

        # OPT-2 : indexes de prêts ACTIFS par prêteur / emprunteur, maintenus
        # incrémentalement. Permet aux fonctions hot-path
        # (_ensure_payment_capacity, process_single_failure phases 1-3)
        # de ne plus balayer self.loans en O(N_loans) à chaque appel.
        # Invariant : un loan_id apparaît dans _loans_by_lender[lender]
        # ET dans _loans_by_borrower[borrower] si et seulement si loan.active=True.
        self._loans_by_lender: Dict[int, set] = {}
        self._loans_by_borrower: Dict[int, set] = {}
        self._active_loan_ids: Dict[int, None] = {}

        # OPT-3 : cache de la liste des entités vivantes, invalidé seulement
        # lors d'un événement de naissance ou de mort. La majorité des phases
        # d'un pas (extract, depreciation, credit_market, auto_invest, stats…)
        # n'altère pas la composition `alive` ; le cache reste valide entre
        # spawn_new_entities() et resolve_cascades().
        self._alive_cache: List[Entity] = []
        self._alive_cache_dirty: bool = True

        self.current_step: int = 0
        self.next_entity_id: int = 1   # compteur d'IDs entités (monotone croissant) Attention à l'overflow en cas de simulation longue. 
        self.next_loan_id: int = 1     # compteur d'IDs prêts   (monotone croissant)
        self._in_run_step: bool = False
        self._stop_requested: bool = False
        self._paused: bool = False

        # Statistiques légères : une ligne par pas, exportée dans stats_legeres.csv.
        self.stats: List[Dict] = []
        self.dynamic_observation_buffer: List[Dict] = []
        self.dynamic_observation_buffer_size: int = 500

        # Journal d'événements (prêts, faillites) — rempli seulement si log_events=True.
        self.event_log: List[str] = []
        self.parameter_update_log: List[Dict] = []
        self.planned_interventions: List[Dict] = []
        self.scenario_name: Optional[str] = None

        # Collecteur statistique riche (distributions, cascades, indicateurs systémiques).
        self.collector = Collector(freq_snapshot=self.config.freq_snapshot)

        # Flux de chaque entité surveillée sur le pas courant (extraction, intérêts...).
        # Réinitialisé en début de pas par _reset_step_flows().
        self._step_flows: dict = {}  # eid -> {'extraction': 0, 'interest_received': 0, ...}

        # Population initiale : toutes les entités initiales sont enregistrées pour suivi.
        self._create_initial_population(self.config.n_entites_initiales)
        for eid in list(self.entities.keys()):
            self.collector.register_entity(eid)
            self._step_flows[eid] = {'extraction': 0.0, 'interest_received': 0.0,
                                      'interest_paid': 0.0, 'depreciation': 0.0}

    # ------------------------------------------------------------------
    #  UTILITAIRES GÉNÉRAUX
    # ------------------------------------------------------------------

    def log(self, message: str) -> None:
        """Ajoute un message horodaté dans event_log si log_events=True."""
        if self.config.log_events:
            self.event_log.append(f"[t={self.current_step}] {message}")

    def _reset_step_flows(self) -> None:
        """Réinitialise les compteurs de flux des entités surveillées en début de pas."""
        for eid in self.collector.watched_entity_ids:
            self._step_flows[eid] = {'extraction': 0.0, 'interest_received': 0.0,
                                      'interest_paid': 0.0, 'depreciation': 0.0}

    def active_entities(self) -> List[Entity]:
        """
        Retourne la liste des entités vivantes (alive=True).

        OPT-3 : la liste est cachée et reconstruite uniquement quand
        _alive_cache_dirty est vrai (i.e. après une naissance ou un décès).
        Les phases qui n'affectent pas la composition `alive` (extraction,
        dépréciation, marché du crédit, auto-investissement, stats…)
        bénéficient d'un coût O(1) au lieu de O(|self.entities|).
        """
        if self._alive_cache_dirty:
            self._alive_cache = [e for e in self.entities.values() if e.alive]
            self._alive_cache_dirty = False
        return self._alive_cache

    def active_loans(self) -> List[Loan]:
        """Retourne la liste des prêts actifs (active=True)."""
        return [self.loans[lid] for lid in self._active_loan_ids]

    def get_entity(self, entity_id: int) -> Entity:
        """Accès direct à une entité par son ID (KeyError si inexistant)."""
        return self.entities[entity_id]

    @staticmethod
    def parameter_scope_matrix() -> Dict[str, Dict[str, bool]]:
        """Retourne la matrice de cohérence paramètre/scope sans état mutable."""
        matrix: Dict[str, Dict[str, bool]] = {}
        for name, category in PARAMETER_RISK_CATEGORIES.items():
            allowed = PARAMETER_SCOPE_RULES.get(name, set())
            if name in {"alpha_min", "alpha_max"}:
                allowed = set(allowed) | {"existing_entities", "future_entities"}
            matrix[name] = {
                "risk_category": category,
                "global_config": "global_config" in allowed,
                "future_entities": "future_entities" in allowed,
                "existing_entities": "existing_entities" in allowed,
                "all_entities": "all_entities" in allowed,
            }
        for name in sorted(ENTITY_UPDATE_NAMES - set(matrix)):
            matrix[name] = {
                "risk_category": "B-entity",
                "global_config": False,
                "future_entities": False,
                "existing_entities": True,
                "all_entities": False,
            }
        return matrix

    def _config_field_names(self) -> set:
        return {f.name for f in fields(SimulationConfig)}

    @staticmethod
    def _json_safe(value: Any) -> Any:
        """Convertit récursivement en types simples JSON sans références mutables."""
        if value is None or isinstance(value, (str, int, float, bool)):
            if isinstance(value, float) and not math.isfinite(value):
                return None
            return value
        if isinstance(value, dict):
            return {str(k): Simulation._json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [Simulation._json_safe(v) for v in value]
        if hasattr(value, "to_dict"):
            return Simulation._json_safe(value.to_dict())
        return str(value)

    def _copy_config_subset(self) -> Dict[str, Any]:
        names = sorted(PARAMETER_RISK_CATEGORIES.keys())
        return {name: self._json_safe(getattr(self.config, name)) for name in names}

    def _latest_stats_or_initial_snapshot(self) -> Dict[str, Any]:
        if self.stats:
            return dict(self.stats[-1])

        alive = self.active_entities()
        active_loans = self.active_loans()
        actif_total = sum(e.actif_total for e in alive)
        passif_total = sum(e.passif_total for e in alive)
        liquidite_totale = sum(e.actif_liquide for e in alive)
        volume_prets = sum(l.principal for l in active_loans)
        n_alive = len(alive)
        return {
            "step": self.current_step,
            "n_entities_alive": n_alive,
            "n_entities_total": len(self.entities),
            "extraction_total": 0.0,
            "interest_paid_total": 0.0,
            "amortissement_total": 0.0,
            "n_failures": 0,
            "destroyed_assets": 0.0,
            "volume_prets_actifs": round(volume_prets, 4),
            "n_prets_actifs": len(active_loans),
            "actif_total_systeme": round(actif_total, 4),
            "passif_total_systeme": round(passif_total, 4),
            "liquidite_totale": round(liquidite_totale, 4),
            "network_density": 0.0 if n_alive <= 1 else round(len(active_loans) / (n_alive * (n_alive - 1)), 8),
            "mean_credit_in_degree": round(len(active_loans) / n_alive, 6) if n_alive else 0.0,
            "mean_credit_out_degree": round(len(active_loans) / n_alive, 6) if n_alive else 0.0,
            "mean_credit_total_degree": round((2 * len(active_loans)) / n_alive, 6) if n_alive else 0.0,
            "extraction_power_total": round(sum(e.alpha * math.sqrt(max(e.passif_total, 0.0)) for e in alive), 4),
        }

    def current_observation(self) -> Dict[str, Any]:
        """
        Retourne une observation dynamique JSON-sérialisable, sans mutation d'état.

        Complexité après au moins un run_step :
          - O(1) pour les compteurs, les flux du dernier pas, les stats légères,
            le dernier indicateur systémique, le journal et la configuration.
          - O(1) amorti pour le nombre d'entités vivantes via active_entities().
          - O(1) pour les métriques réseau ajoutées, car elles sont collectées
            dans _collect_light_stats().

        Complexité avant le premier run_step :
          - O(N entités) pour actif/passif/liquidité/extraction_power_total.
          - O(N prêts) pour compter et sommer les prêts actifs.

        La méthode ne retourne jamais self.entities, self.loans, self.stats ou
        self.collector directement : uniquement des copies en types simples.
        """
        latest = self._latest_stats_or_initial_snapshot()
        last_indicator = None
        if getattr(self.collector, "indicators", None):
            last_indicator = self.collector.indicators[-1].to_dict()

        observation = {
            "current_step": int(self.current_step),
            "n_entities_alive": int(latest.get("n_entities_alive", 0)),
            "n_entities_total": int(latest.get("n_entities_total", len(self.entities))),
            "n_active_loans": int(latest.get("n_prets_actifs", 0)),
            "active_loans_total_volume": latest.get("volume_prets_actifs", 0.0),
            "system_total_assets": latest.get("actif_total_systeme", 0.0),
            "system_total_liabilities": latest.get("passif_total_systeme", 0.0),
            "total_liquidity": latest.get("liquidite_totale", 0.0),
            "last_step_extraction_total": latest.get("extraction_total", 0.0),
            "last_step_interest_paid": latest.get("interest_paid_total", 0.0),
            "last_step_amortization_total": latest.get("amortissement_total", 0.0),
            "last_step_failures": latest.get("n_failures", 0),
            "last_step_destroyed_assets": latest.get("destroyed_assets", 0.0),
            "last_systemic_indicator": last_indicator,
            "last_light_stats": latest,
            "current_config": self._copy_config_subset(),
            "parameter_update_log_size": len(self.parameter_update_log),
            "last_parameter_update": self.parameter_update_log[-1] if self.parameter_update_log else None,
            "dynamic_metrics": {
                "network_density": latest.get("network_density"),
                "financial_density": latest.get("financial_density"),
                "mean_credit_in_degree": latest.get("mean_credit_in_degree"),
                "mean_credit_out_degree": latest.get("mean_credit_out_degree"),
                "mean_credit_total_degree": latest.get("mean_credit_total_degree"),
                "extraction_power_total": latest.get("extraction_power_total"),
                "asset_distribution_snapshot": latest.get("asset_distribution_snapshot"),
                "entity_age_distribution": latest.get("entity_age_distribution"),
                "failed_entity_lifespans": latest.get("failed_entity_lifespans"),
                "alive_entity_lifespans": latest.get("alive_entity_lifespans"),
                "gini_actif_total": (
                    last_indicator.get("gini_actif_total") if isinstance(last_indicator, dict) else None
                ),
            },
        }
        return self._json_safe(observation)

    def _append_observation_to_buffer(self) -> None:
        obs = self.current_observation()
        self.dynamic_observation_buffer.append(obs)
        overflow = len(self.dynamic_observation_buffer) - self.dynamic_observation_buffer_size
        if overflow > 0:
            del self.dynamic_observation_buffer[:overflow]

    @staticmethod
    def _distribution_summary(values: List[float]) -> Optional[Dict[str, Any]]:
        xs = sorted(v for v in values if math.isfinite(v))
        if not xs:
            return None
        n = len(xs)

        def q(prob: float) -> float:
            idx = prob * (n - 1)
            lo = int(idx)
            hi = min(lo + 1, n - 1)
            return xs[lo] + (idx - lo) * (xs[hi] - xs[lo])

        return {
            "n": n,
            "min": round(xs[0], 4),
            "q10": round(q(0.10), 4),
            "q25": round(q(0.25), 4),
            "median": round(q(0.50), 4),
            "q75": round(q(0.75), 4),
            "q90": round(q(0.90), 4),
            "max": round(xs[-1], 4),
            "mean": round(sum(xs) / n, 4),
        }

    def _coerce_config_value(self, parameter: str, value: Any) -> Tuple[bool, Any, str]:
        field_types = {f.name: f.type for f in fields(SimulationConfig)}
        expected_type = field_types.get(parameter)
        if expected_type is bool:
            if isinstance(value, bool):
                return True, value, ""
            return False, value, "type invalide: bool attendu"
        if expected_type is int:
            if isinstance(value, bool) or not isinstance(value, int):
                return False, value, "type invalide: int attendu"
            return True, value, ""
        if expected_type is float:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return False, value, "type invalide: float attendu"
            if not math.isfinite(float(value)):
                return False, value, "valeur numérique non finie"
            return True, float(value), ""
        return True, value, ""

    def _validate_parameter_update(
        self,
        parameter: str,
        new_value: Any,
        allow_risky: bool,
        scope: str,
        old_value_expected: Any = None,
    ) -> Tuple[bool, Any, Dict[str, Any]]:
        config_fields = self._config_field_names()
        if parameter not in config_fields:
            return False, new_value, {
                "parameter": parameter,
                "new_value": self._json_safe(new_value),
                "scope": scope,
                "reason": "paramètre absent de SimulationConfig",
            }

        if scope not in SCOPES:
            return False, new_value, {
                "parameter": parameter,
                "new_value": self._json_safe(new_value),
                "scope": scope,
                "reason": f"scope inconnu: {scope}",
            }

        category = PARAMETER_RISK_CATEGORIES.get(parameter)
        if category is None:
            return False, new_value, {
                "parameter": parameter,
                "new_value": self._json_safe(new_value),
                "scope": scope,
                "reason": "paramètre non classé, refus conservateur",
            }

        if category == "C" or scope == "forbidden":
            return False, new_value, {
                "parameter": parameter,
                "new_value": self._json_safe(new_value),
                "scope": scope,
                "risk_category": category,
                "reason": "paramètre interdit en cours de simulation",
            }

        allowed_scopes = PARAMETER_SCOPE_RULES.get(parameter, set())
        if scope not in allowed_scopes:
            return False, new_value, {
                "parameter": parameter,
                "new_value": self._json_safe(new_value),
                "scope": scope,
                "risk_category": category,
                "reason": "scope incohérent pour ce paramètre dans cette version",
                "allowed_scopes": sorted(allowed_scopes),
            }

        if category == "B" and not allow_risky:
            return False, new_value, {
                "parameter": parameter,
                "new_value": self._json_safe(new_value),
                "scope": scope,
                "risk_category": category,
                "reason": "paramètre de catégorie B refusé sans allow_risky=True",
            }

        ok, coerced_value, reason = self._coerce_config_value(parameter, new_value)
        if not ok:
            return False, new_value, {
                "parameter": parameter,
                "new_value": self._json_safe(new_value),
                "scope": scope,
                "risk_category": category,
                "reason": reason,
            }

        old_value = getattr(self.config, parameter)
        if old_value_expected is not None and old_value != old_value_expected:
            return False, coerced_value, {
                "parameter": parameter,
                "old_value": self._json_safe(old_value),
                "old_value_expected": self._json_safe(old_value_expected),
                "new_value": self._json_safe(coerced_value),
                "scope": scope,
                "risk_category": category,
                "reason": "ancienne valeur différente de old_value_expected",
            }

        warning = ""
        if category == "B":
            warning = "Catégorie B: modification acceptée avec précautions; comparer les trajectoires avec prudence."
        if scope == "future_entities":
            warning = (warning + " " if warning else "") + "Scope future_entities: effet limité aux règles de création futures."
        if parameter == "freq_snapshot":
            warning = (warning + " " if warning else "") + "collector.freq_snapshot est synchronisé avec config.freq_snapshot."

        return True, coerced_value, {
            "parameter": parameter,
            "old_value": self._json_safe(old_value),
            "new_value": self._json_safe(coerced_value),
            "scope": scope,
            "risk_category": category,
            "warning": warning or None,
        }

    def apply_parameter_updates(
        self,
        updates: Dict[str, Any],
        allow_risky: bool = False,
        scope: str = "global_config",
        source: str = "interactive",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Applique atomiquement des changements de SimulationConfig entre deux pas.

        La méthode ne modifie jamais les entités ni les prêts. Elle refuse les
        paramètres inconnus, les paramètres de catégorie C et les scopes incohérents.
        Si une seule demande est refusée, aucune modification n'est appliquée.
        """
        if self._in_run_step:
            return {
                "step": self.current_step,
                "applied": [],
                "refused": [{"reason": "modification refusée pendant run_step()"}],
            }
        if not isinstance(updates, dict) or not updates:
            return {"step": self.current_step, "applied": [], "refused": []}

        metadata = dict(metadata or {})
        validations = []
        refused = []
        expected_values = metadata.get("old_value_expected_by_parameter", {})
        for parameter, new_value in updates.items():
            expected = expected_values.get(parameter)
            ok, coerced_value, info = self._validate_parameter_update(
                parameter, new_value, allow_risky=allow_risky, scope=scope, old_value_expected=expected
            )
            if ok:
                validations.append((parameter, coerced_value, info))
            else:
                refused.append(info)

        if refused:
            result = {"step": self.current_step, "applied": [], "refused": refused}
            return self._json_safe(result)

        applied = []
        for parameter, coerced_value, info in validations:
            setattr(self.config, parameter, coerced_value)
            if parameter == "freq_snapshot":
                self.collector.freq_snapshot = coerced_value
            entry = {
                "step": self.current_step,
                "parameter": parameter,
                "old_value": info["old_value"],
                "new_value": info["new_value"],
                "risk_category": info["risk_category"],
                "scope": scope,
                "source": source,
                "warning": info.get("warning"),
            }
            entry.update({k: self._json_safe(v) for k, v in metadata.items() if k != "old_value_expected_by_parameter"})
            self.parameter_update_log.append(entry)
            applied.append(dict(entry))

        return self._json_safe({"step": self.current_step, "applied": applied, "refused": []})

    def _entity_alpha_summary(self, entities: List[Entity]) -> Dict[str, Any]:
        if not entities:
            return {"count": 0, "min": None, "mean": None, "max": None}
        values = [e.alpha for e in entities]
        return {
            "count": len(values),
            "min": round(min(values), 8),
            "mean": round(sum(values) / len(values), 8),
            "max": round(max(values), 8),
        }

    def _validate_entity_updates(
        self,
        updates: Dict[str, Any],
        scope: str,
        allow_risky: bool,
    ) -> Tuple[bool, Dict[str, float], List[Dict[str, Any]]]:
        refused = []
        if scope not in {"existing_entities", "future_entities"}:
            return False, {}, [{
                "scope": scope,
                "reason": "les modifications d'alpha exigent scope existing_entities ou future_entities",
            }]
        if not allow_risky:
            return False, {}, [{
                "scope": scope,
                "risk_category": "B-entity",
                "reason": "modification d'entités refusée sans allow_risky=True",
            }]
        if not isinstance(updates, dict) or not updates:
            return True, {}, []

        coerced: Dict[str, float] = {}
        for name, value in updates.items():
            if name not in ENTITY_UPDATE_NAMES:
                refused.append({
                    "parameter": name,
                    "scope": scope,
                    "reason": "opération d'entité inconnue ou non autorisée",
                    "allowed": sorted(ENTITY_UPDATE_NAMES),
                })
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                refused.append({
                    "parameter": name,
                    "new_value": self._json_safe(value),
                    "scope": scope,
                    "reason": "valeur numérique finie attendue",
                })
                continue
            coerced[name] = float(value)

        if "alpha_multiplier" in coerced and coerced["alpha_multiplier"] <= 0:
            refused.append({"parameter": "alpha_multiplier", "reason": "alpha_multiplier doit etre > 0"})
        if "alpha_set" in coerced and coerced["alpha_set"] < 0:
            refused.append({"parameter": "alpha_set", "reason": "alpha_set doit etre >= 0"})
        if "alpha_min" in coerced and coerced["alpha_min"] < 0:
            refused.append({"parameter": "alpha_min", "reason": "alpha_min doit etre >= 0"})
        if "alpha_max" in coerced and coerced["alpha_max"] < 0:
            refused.append({"parameter": "alpha_max", "reason": "alpha_max doit etre >= 0"})
        if "alpha_min" in coerced and "alpha_max" in coerced and coerced["alpha_min"] > coerced["alpha_max"]:
            refused.append({"parameter": "alpha_min/alpha_max", "reason": "alpha_min doit etre <= alpha_max"})

        return not refused, coerced, refused

    def apply_entity_updates(
        self,
        updates: Dict[str, Any],
        scope: str = "existing_entities",
        allow_risky: bool = False,
        source: str = "interactive",
        selector: str = "alive",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Modifie explicitement les productivités alpha entre deux pas.

        Version volontairement bornée : scope="existing_entities" transforme
        uniquement les entités vivantes déjà présentes. scope="future_entities"
        transforme uniquement la plage de tirage alpha_min/alpha_max utilisée
        par les entités qui naîtront ensuite. Les bilans et les prêts ne sont
        jamais modifiés. Opérations supportées :
          - alpha_multiplier : multiplie alpha par un facteur > 0 ;
          - alpha_set        : fixe alpha à une valeur >= 0 ;
          - alpha_add        : ajoute un delta, sans autoriser alpha final < 0 ;
          - alpha_min/max    : borne les alpha.
        """
        if self._in_run_step:
            return {
                "step": self.current_step,
                "applied": [],
                "refused": [{"reason": "modification d'entités refusée pendant run_step()"}],
            }
        if selector != "alive":
            return {
                "step": self.current_step,
                "applied": [],
                "refused": [{"selector": selector, "reason": "seul selector='alive' est supporté"}],
            }

        metadata = dict(metadata or {})
        ok, coerced, refused = self._validate_entity_updates(updates, scope=scope, allow_risky=allow_risky)
        if not ok:
            return self._json_safe({"step": self.current_step, "applied": [], "refused": refused})
        if not coerced:
            return {"step": self.current_step, "applied": [], "refused": []}

        if scope == "future_entities":
            before = {
                "alpha_min": self._json_safe(self.config.alpha_min),
                "alpha_max": self._json_safe(self.config.alpha_max),
            }
            alpha_min = float(self.config.alpha_min)
            alpha_max = float(self.config.alpha_max)
            if "alpha_set" in coerced:
                alpha_min = coerced["alpha_set"]
                alpha_max = coerced["alpha_set"]
            if "alpha_multiplier" in coerced:
                alpha_min *= coerced["alpha_multiplier"]
                alpha_max *= coerced["alpha_multiplier"]
            if "alpha_add" in coerced:
                alpha_min += coerced["alpha_add"]
                alpha_max += coerced["alpha_add"]
            if "alpha_min" in coerced:
                alpha_min = max(alpha_min, coerced["alpha_min"])
            if "alpha_max" in coerced:
                alpha_max = min(alpha_max, coerced["alpha_max"])
            if alpha_min < 0 or alpha_max < 0 or alpha_min > alpha_max:
                return self._json_safe({
                    "step": self.current_step,
                    "applied": [],
                    "refused": [{
                        "reason": "l'opération produirait une plage alpha future invalide",
                        "computed_alpha_min": alpha_min,
                        "computed_alpha_max": alpha_max,
                    }],
                })
            self.config.alpha_min = alpha_min
            self.config.alpha_max = alpha_max
            after = {"alpha_min": self._json_safe(alpha_min), "alpha_max": self._json_safe(alpha_max)}
            entry = {
                "step": self.current_step,
                "parameter": "future_entity_alpha",
                "operation": dict(coerced),
                "old_value": before,
                "new_value": after,
                "risk_category": "B-entity",
                "scope": scope,
                "selector": "future_births",
                "source": source,
                "affected_entities": 0,
                "config_changes": {
                    "alpha_min": {"old_value": before["alpha_min"], "new_value": after["alpha_min"]},
                    "alpha_max": {"old_value": before["alpha_max"], "new_value": after["alpha_max"]},
                },
                "warning": "Modification de la plage de productivite alpha pour les entites qui naitront ensuite.",
            }
            entry.update({k: self._json_safe(v) for k, v in metadata.items()})
            self.parameter_update_log.append(entry)
            return self._json_safe({"step": self.current_step, "applied": [entry], "refused": []})

        affected = list(self.active_entities())
        before = self._entity_alpha_summary(affected)
        planned_values: Dict[int, float] = {}
        for entity in affected:
            alpha = entity.alpha
            if "alpha_set" in coerced:
                alpha = coerced["alpha_set"]
            if "alpha_multiplier" in coerced:
                alpha *= coerced["alpha_multiplier"]
            if "alpha_add" in coerced:
                alpha += coerced["alpha_add"]
            if "alpha_min" in coerced:
                alpha = max(alpha, coerced["alpha_min"])
            if "alpha_max" in coerced:
                alpha = min(alpha, coerced["alpha_max"])
            if alpha < 0 or not math.isfinite(alpha):
                return self._json_safe({
                    "step": self.current_step,
                    "applied": [],
                    "refused": [{
                        "reason": "l'opération produirait un alpha négatif ou non fini",
                        "entity_id": entity.entity_id,
                        "computed_alpha": alpha,
                    }],
                })
            planned_values[entity.entity_id] = alpha

        for entity in affected:
            entity.alpha = planned_values[entity.entity_id]

        after = self._entity_alpha_summary(affected)
        entry = {
            "step": self.current_step,
            "parameter": "entity_alpha",
            "operation": dict(coerced),
            "old_value": before,
            "new_value": after,
            "risk_category": "B-entity",
            "scope": scope,
            "selector": selector,
            "source": source,
            "affected_entities": len(affected),
            "config_changes": {},
            "warning": "Modification directe de productivite alpha des entités vivantes; trajectoire dépendante de l'intervention.",
        }
        entry.update({k: self._json_safe(v) for k, v in metadata.items()})
        self.parameter_update_log.append(entry)
        return self._json_safe({"step": self.current_step, "applied": [entry], "refused": []})

    # ------------------------------------------------------------------
    #  OPT-2 — Maintenance des indexes de prêts actifs
    # ------------------------------------------------------------------

    def _idx_add(self, loan: Loan) -> None:
        """Inscrit un prêt actif dans les indexes (à appeler à la création / réactivation)."""
        self._active_loan_ids[loan.loan_id] = None
        s = self._loans_by_lender.get(loan.lender_id)
        if s is None:
            self._loans_by_lender[loan.lender_id] = {loan.loan_id}
        else:
            s.add(loan.loan_id)
        s = self._loans_by_borrower.get(loan.borrower_id)
        if s is None:
            self._loans_by_borrower[loan.borrower_id] = {loan.loan_id}
        else:
            s.add(loan.loan_id)

    def _idx_remove(self, loan: Loan) -> None:
        """Retire un prêt des indexes (à appeler avant ou après loan.active = False)."""
        self._active_loan_ids.pop(loan.loan_id, None)
        s = self._loans_by_lender.get(loan.lender_id)
        if s is not None:
            s.discard(loan.loan_id)
        s = self._loans_by_borrower.get(loan.borrower_id)
        if s is not None:
            s.discard(loan.loan_id)

    def _idx_change_lender(self, loan: Loan, new_lender_id: int) -> None:
        """Met à jour les indexes lors d'un changement de prêteur (cession totale)."""
        s = self._loans_by_lender.get(loan.lender_id)
        if s is not None:
            s.discard(loan.loan_id)
        s = self._loans_by_lender.get(new_lender_id)
        if s is None:
            self._loans_by_lender[new_lender_id] = {loan.loan_id}
        else:
            s.add(loan.loan_id)

    def compute_internal_rate(self, entity: Entity) -> float:
        """
        Taux de rendement marginal interne de l'entité :
            r* = α / (2√P)
        C'est la dérivée de l'extraction Π = α√P par rapport à P.
        r* décroît avec la taille (P) : les grandes entités ont un r* faible
        → naturellement prêteuses ; les petites ont un r* élevé → naturellement
        emprunteuses. C'est le seul signal de prix du marché du crédit.
        Le max avec ε évite la division par zéro si P ≈ 0.
        """
        p = max(entity.passif_total, self.config.epsilon)#Impossible que P soit nul car le passif inné n'est jamais touché. 
        return entity.alpha / (2.0 * math.sqrt(p))

    # ------------------------------------------------------------------
    #  CRÉATION D'ENTITÉS
    # ------------------------------------------------------------------

    def create_entity(
        self,
        actif_liquide: Optional[float] = None,
        passif_inne: Optional[float] = None,
    ) -> Entity:
        p_inne = self.config.passif_inne_initial if passif_inne is None else passif_inne
        entity = Entity(
            entity_id=self.next_entity_id,
            actif_liquide=self.config.actif_liquide_initial if actif_liquide is None else actif_liquide,
            passif_inne=p_inne,
            alpha=self.rng.uniform(self.config.alpha_min, self.config.alpha_max),
            creation_step=self.current_step,
            passif_total=p_inne,  # passif_endoinvesti=0, passif_exoinvesti=0 à la création
        )
        self.entities[entity.entity_id] = entity
        self._alive_cache_dirty = True  # OPT-3 : naissance
        # Watch newly born entities with probability _P_WATCH_NEW (but not initial ones, watched separately)
        if self.current_step > 0 and self.rng.random() < _P_WATCH_NEW:
            self.collector.register_entity(entity.entity_id)
            self._step_flows[entity.entity_id] = {'extraction': 0.0, 'interest_received': 0.0,
                                                    'interest_paid': 0.0, 'depreciation': 0.0}
        self.next_entity_id += 1
        self.log(f"Création entité {entity.entity_id}")
        return entity

    def _create_initial_population(self, n: int) -> None:
        """Peuple la simulation avec n entités identiques (sauf alpha) à t=0."""
        for _ in range(n):
            self.create_entity()

    # ------------------------------------------------------------------
    #  CRÉATION DE PRÊTS (primitive bas-niveau)
    # ------------------------------------------------------------------

    def create_loan(
        self,
        lender_id: int,
        borrower_id: int,
        principal: float,
        rate: float,
        parent_loan_id: Optional[int] = None,
    ) -> Loan:
        """
        Primitive bas-niveau : crée un prêt et l'enregistre dans sim.loans.
        NE met PAS à jour les bilans ni les caches d'intérêts.

        Utiliser execute_loan() pour un nouveau prêt de marché (met à jour bilans et caches).
        Utiliser directement create_loan() uniquement lors des redistributions de faillite
        ou des réévaluations, où les mises à jour de bilan sont gérées manuellement.
        """
        if principal <= self.config.epsilon:
            raise ValueError("Le principal doit être strictement positif.")
        loan = Loan(
            loan_id=self.next_loan_id,
            lender_id=lender_id,
            borrower_id=borrower_id,
            principal=principal,
            rate=rate,
            active=True,
            parent_loan_id=parent_loan_id,
            creation_step=self.current_step,
        )
        self.loans[loan.loan_id] = loan
        self._idx_add(loan)  # OPT-2
        self.next_loan_id += 1
        return loan

    # ------------------------------------------------------------------
    #  TIRAGE DE POISSON
    # ------------------------------------------------------------------

    def poisson(self, lam: float) -> int:
        """
        Algorithme de Knuth pour un tirage Poisson(λ) à partir du RNG isolé.

        Principe : la somme de k variables U[0,1] est > e^{-λ} en attendant la première
        qui fait passer le produit cumulé en dessous de e^{-λ}. Retourne 0 si λ ≤ 0.
        Complexité : O(λ) en moyenne.
        """
        if lam <= 0:
            return 0
        l_val = math.exp(-lam)
        k = 0
        p = 1.0
        while p > l_val:
            k += 1
            p *= self.rng.random()
        return k - 1

    # ------------------------------------------------------------------
    #  ÉTAPE 1 — Création de nouvelles entités
    # ------------------------------------------------------------------

    def spawn_new_entities(self) -> int:
        """
        Tire n ~ Poisson(λ_création) nouvelles entités et les crée avec la dotation par défaut.
        Retourne le nombre d'entités créées ce pas.
        """
        n = self.poisson(self.config.lambda_creation)
        for _ in range(n):
            self.create_entity()
        return n

    # ------------------------------------------------------------------
    #  ÉTAPE 2 — Extraction depuis la nature
    # ------------------------------------------------------------------

    def extract_from_nature(self) -> float:
        """
        Chaque entité vivante extrait Π_i = α_i √P_i et l'ajoute à son liquide.

        La fonction √P est concave : rendements décroissants à l'échelle.
        α_i est hétérogène entre entités et varie lentement (mouvement brownien).
        C'est la seule source exogène de ressources dans le système.
        Retourne le flux total extrait ce pas.
        """
        total = 0.0
        for e in self.active_entities():
            extracted = e.alpha * math.sqrt(max(e.passif_total, 0.0))
            e.actif_liquide += extracted
            total += extracted
            if e.entity_id in self.collector.watched_entity_ids:
                self._step_flows[e.entity_id]['extraction'] += extracted
        return total

    # ------------------------------------------------------------------
    #  ÉTAPE 3 — Paiement des intérêts
    # ------------------------------------------------------------------

    def pay_interest_phase(self) -> float:
        """
        Traite le paiement des intérêts pour l'ensemble des prêts actifs.

        Les prêts sont traités dans l'ordre croissant de loan_id (ordre de création)
        pour garantir un ordre déterministe quel que soit l'état du dict.
        Si un emprunteur est illiquide, _ensure_payment_capacity() est appelé.
        Retourne le flux total d'intérêts versé ce pas.

        OPT-1 (conservatrice) : suppression du sorted() redondant.
        Les loan_id sont alloués strictement monotonement (next_loan_id += 1)
        et CPython garantit que dict.values() itère en ordre d'insertion.
        active_loans() matérialise déjà la liste en snapshot ; trier par loan_id
        sur cette liste était un no-op et coûtait O(N log N) inutilement.
        """
        total_paid = 0.0
        for loan in self.active_loans():
            total_paid += self._pay_single_interest(loan)
        return total_paid

    def _pay_single_interest(self, loan: Loan) -> float:
        """
        Traite le paiement des intérêts d'un seul prêt. Retourne le montant
        effectivement payé.

        OPT-5 : appels inlinés (get_entity → self.entities[id], interest_due →
        principal*rate, _route_interest_to_lender → 3 lignes locales). La
        fonction est appelée ~3700×/pas dans le hot path : économies
        cumulées non négligeables, sans changer la sémantique.
        """
        if not loan.active:
            return 0.0
        entities = self.entities
        eps = self.config.epsilon
        borrower = entities[loan.borrower_id]
        due = loan.principal * loan.rate
        if due <= eps:
            return 0.0
        watched = self.collector.watched_entity_ids
        flows = self._step_flows
        if borrower.actif_liquide >= due:
            borrower.actif_liquide -= due
            if borrower.entity_id in watched:
                flows[borrower.entity_id]['interest_paid'] += due
            lender = entities[loan.lender_id]
            lender.actif_liquide += due
            if lender.entity_id in watched:
                flows[lender.entity_id]['interest_received'] += due
            return due
        payment = self._ensure_payment_capacity(borrower, due, loan.lender_id)
        if borrower.entity_id in watched:
            flows[borrower.entity_id]['interest_paid'] += payment
        # Inline _route_interest_to_lender(loan, payment)
        lender = entities[loan.lender_id]
        lender.actif_liquide += payment
        if lender.entity_id in watched:
            flows[lender.entity_id]['interest_received'] += payment
        return payment

    def _ensure_payment_capacity(self, payer: Entity, amount_due: float, creditor_id: int) -> float:
        """
        Mobilise la capacité de paiement de payer via un arbitrage en quatre étapes :
          1) Actif liquide disponible. Question: Pourquoi pas l'inverser 1et2
          2) Cession des créances dont le taux < r* (moins rentables que la capacité
             extractive marginale — vendre en priorité).
          3) Reliquéfaction de l'endo-investi (décote c, perte de capacité extractive). Question: Rajouter un paramètre qui permet de désactiver la reliquéfaction de l'endo-investi, au même titre que l'exo-investi. 
          4) Cession des créances dont le taux ≥ r* (plus rentables — dernier recours).
        Chaque cession réévalue le prêt à sa valeur réelle avant transfert.
        Retourne le montant effectivement payé.

        L'ORDRE PEUT MODIFIER GRANDEMENT LE COMPORTEMENT
        """
        if amount_due <= self.config.epsilon:
            return 0.0

        amount_remaining = amount_due
        paid = 0.0

        # 1) Liquide
        liquid_payment = min(payer.actif_liquide, amount_remaining)
        payer.actif_liquide -= liquid_payment
        amount_remaining -= liquid_payment
        paid += liquid_payment

        if amount_remaining <= self.config.epsilon:
            return paid

        # Taux interne marginal courant du payeur
        r_star = self.compute_internal_rate(payer)

        # 2) Cession des créances sous r* (faible rendement relatif)
        # OPT-2 : on lit l'index _loans_by_lender (prêts actifs uniquement) au
        # lieu de balayer self.loans en O(N_loans). L'ordre final reste
        # déterminé par le tri explicite (rate, loan_id), donc identique.
        payer_loan_ids = self._loans_by_lender.get(payer.entity_id, ())
        below_rstar = sorted(
            [self.loans[lid] for lid in payer_loan_ids
             if self.loans[lid].rate < r_star - self.config.epsilon],
            key=lambda x: (x.rate, x.loan_id),
        )
        if amount_remaining > self.config.epsilon and below_rstar:
            transferred = self._transfer_claims_for_payment(
                payer.entity_id, creditor_id, amount_remaining, below_rstar
            )
            paid += transferred
            amount_remaining = amount_due - paid

        # 3) Reliquéfaction endo
        if amount_remaining > self.config.epsilon:
            c = max(self.config.coefficient_reliquefaction, self.config.epsilon)
            y_needed = amount_remaining / c #Quand la reliquefaction sera désactivée, attention !! 
            y = min(payer.actif_endoinvesti, payer.passif_endoinvesti, y_needed) #Passif = Actif non ? Protection contre passif négatif ?
            if y > self.config.epsilon:
                payer.actif_endoinvesti -= y
                payer.passif_endoinvesti -= y
                liquid_generated = c * y
                payer.actif_liquide += liquid_generated
                final_payment = min(payer.actif_liquide, amount_due - paid)
                payer.actif_liquide -= final_payment
                paid += final_payment
                amount_remaining = amount_due - paid

        # 4) Cession des créances au-dessus de r* (haut rendement — dernier recours)
        if amount_remaining > self.config.epsilon:
            # r* a pu changer après reliquéfaction (P^endo a diminué) : recalcul
            r_star = self.compute_internal_rate(payer)
            # OPT-2 : on relit l'index (les transferts précédents ont pu en sortir
            # certains prêts ; les nouveaux fragments y sont déjà inscrits).
            payer_loan_ids = self._loans_by_lender.get(payer.entity_id, ())
            above_rstar = sorted(
                [self.loans[lid] for lid in payer_loan_ids
                 if self.loans[lid].rate >= r_star - self.config.epsilon],
                key=lambda x: (x.rate, x.loan_id),
            )
            if above_rstar:
                transferred = self._transfer_claims_for_payment(
                    payer.entity_id, creditor_id, amount_remaining, above_rstar
                )
                paid += transferred

        return paid

    def _revalue_loan(self, loan: Loan) -> Optional[Loan]:
        """
        Calcule la valeur économique réelle d'un prêt : principal × (1−δ_exo)^âge.
        Si la valeur réelle diffère du nominal courant (> ε) :
          - écrit le delta (négatif) dans actif_prete et passif_credit_detenu du prêteur ;
          - désactive le prêt original, crée un nouveau prêt à valeur réelle.
        Le bilan de l'emprunteur n'est PAS modifié : K^exo et P^exo ont déjà
        décru via apply_depreciation() et restent alignés sur la valeur réelle.
        Retourne le prêt actif à valeur réelle (nouveau ou inchangé), ou None si nul.
        """
        factor = max(0.0, 1.0 - self.config.taux_depreciation_exo)
        age = self.current_step - loan.creation_step
        real_value = loan.principal * (factor ** age)

        if real_value <= self.config.epsilon:
            lender = self.get_entity(loan.lender_id)
            lender.actif_prete -= loan.principal
            lender.passif_credit_detenu -= loan.principal
            lender.revenus_interets -= loan.rate * loan.principal
            borrower = self.entities.get(loan.borrower_id)
            if borrower and borrower.alive:
                borrower.charges_interets -= loan.rate * loan.principal
            self._idx_remove(loan)  # OPT-2
            loan.active = False
            return None

        delta = real_value - loan.principal
        if abs(delta) <= self.config.epsilon:
            return loan  # valeur nominale déjà alignée, pas de correction

        # Write-down chez le prêteur (delta < 0 : réduction)
        lender = self.get_entity(loan.lender_id)
        lender.actif_prete += delta
        lender.passif_credit_detenu += delta
        delta_flow = loan.rate * delta
        lender.revenus_interets += delta_flow
        borrower = self.entities.get(loan.borrower_id)
        if borrower and borrower.alive:
            borrower.charges_interets += delta_flow
        self._idx_remove(loan)  # OPT-2
        loan.active = False
        new_loan = self.create_loan(
            lender_id=loan.lender_id,
            borrower_id=loan.borrower_id,
            principal=real_value,
            rate=loan.rate,
            parent_loan_id=loan.loan_id,
        )
        return new_loan

    def _transfer_claims_for_payment(
        self,
        from_entity_id: int,
        to_entity_id: int,
        amount_needed: float,
        sorted_loans: Optional[List[Loan]] = None,
    ) -> float:
        """
        Cède des créances de from_entity vers to_entity pour couvrir amount_needed.
        Chaque créance est réévaluée à sa valeur réelle avant cession (write-down
        chez le prêteur si la valeur a décru depuis l'émission).
        Si sorted_loans est fourni (liste pré-triée/filtrée), l'utilise directement.
        Sinon, trie toutes les créances actives par taux croissant.
        Retourne le montant effectivement transféré (en valeur réelle).
        """
        payer = self.get_entity(from_entity_id)
        if sorted_loans is None:
            sorted_loans = sorted(
                [loan for loan in self.active_loans() if loan.lender_id == from_entity_id],
                key=lambda x: (x.rate, x.loan_id),
            )
        transferred_total = 0.0

        for loan in sorted_loans:
            if transferred_total >= amount_needed - self.config.epsilon:
                break
            if not loan.active:
                continue

            # Réévaluation à la valeur réelle avant cession
            revalued = self._revalue_loan(loan)
            if revalued is None:
                continue  # prêt sans valeur résiduelle

            remain = amount_needed - transferred_total
            transfer_amount = min(revalued.principal, remain)
            if transfer_amount <= self.config.epsilon:
                continue

            payer.actif_prete -= transfer_amount
            payer.passif_credit_detenu -= transfer_amount
            receiver = self.get_entity(to_entity_id)
            receiver.actif_prete += transfer_amount
            receiver.passif_credit_detenu += transfer_amount
            # Cache : le prêteur change, l'emprunteur reste identique → seuls les revenus bougent.
            flow = revalued.rate * transfer_amount
            payer.revenus_interets -= flow
            receiver.revenus_interets += flow

            if abs(transfer_amount - revalued.principal) <= self.config.epsilon:
                # Cession totale : changement de prêteur
                self._idx_change_lender(revalued, to_entity_id)  # OPT-2
                revalued.lender_id = to_entity_id
            else:
                # Cession partielle : scission du prêt réévalué.
                # split() désactive `revalued` et retourne deux fragments actifs.
                t_id = self.next_loan_id
                r_id = self.next_loan_id + 1
                self._idx_remove(revalued)  # OPT-2 : retire le prêt parent désactivé par split()
                transferred_frag, remaining_frag = revalued.split(t_id, r_id, transfer_amount, to_entity_id)
                self.loans[transferred_frag.loan_id] = transferred_frag
                self.loans[remaining_frag.loan_id] = remaining_frag
                self._idx_add(transferred_frag)  # OPT-2
                self._idx_add(remaining_frag)    # OPT-2
                self.next_loan_id += 2

            transferred_total += transfer_amount

        return transferred_total

    def _route_interest_to_lender(self, loan: Loan, amount: float) -> None:
        """Crédite le prêteur du montant d'intérêt reçu."""
        lender = self.get_entity(loan.lender_id)
        lender.actif_liquide += amount
        if lender.entity_id in self.collector.watched_entity_ids:
            self._step_flows[lender.entity_id]['interest_received'] += amount


    # ------------------------------------------------------------------
    #  ÉTAPE 4 — Dépréciation
    # ------------------------------------------------------------------

    def apply_depreciation(self) -> None:
        """
        Applique une dépréciation géométrique à tous les actifs de chaque entité vivante.

        Actif liquide       : L  ← L  × (1 − δ_L)       δ_L    = 0.01
        Capital endo (K,P)  : K^endo ← K^endo × (1 − δ_endo),
                              P^endo ← P^endo × (1 − δ_endo)    δ_endo = 0.10
        Capital exo  (K,P)  : K^exo  ← K^exo  × (1 − δ_exo),
                              P^exo  ← P^exo  × (1 − δ_exo)     δ_exo  = 0.10

        L'invariant K^endo = P^endo et K^exo = P^exo est préservé car les deux
        côtés du bilan dépécient au même taux.

        passif_total est recalculé depuis zéro après dépréciation car les trois
        composantes (B, P^endo, P^exo) changent simultanément — un calcul direct
        est plus sûr qu'une mise à jour incrémentale.

        Note : la dépréciation des créances (actif_prete/passif_credit_detenu) n'est
        PAS effectuée ici. Elle est traitée paresseusement, à la demande, via
        _revalue_loan() lors d'une cession ou d'une faillite. Cela crée une fragilité
        cachée (valeur nominale > valeur réelle) qui est capturée par
        compute_hidden_fragility() à des fins statistiques.
        """
        for e in self.active_entities():
            if e.entity_id in self.collector.watched_entity_ids:
                dep = (e.actif_liquide * self.config.taux_depreciation_liquide +
                       e.actif_endoinvesti * self.config.taux_depreciation_endo)
                self._step_flows[e.entity_id]['depreciation'] += dep

            e.actif_liquide *= max(0.0, 1.0 - self.config.taux_depreciation_liquide)

            factor_endo = max(0.0, 1.0 - self.config.taux_depreciation_endo)
            e.actif_endoinvesti *= factor_endo
            e.passif_endoinvesti *= factor_endo

            factor_exo = max(0.0, 1.0 - self.config.taux_depreciation_exo)
            e.actif_exoinvesti *= factor_exo
            e.passif_exoinvesti *= factor_exo

            # Recalcul complet du cache passif_total après les dépréciations :
            # plus fiable qu'une mise à jour incrémentale car les trois termes changent.
            e.passif_total = e.passif_inne + e.passif_endoinvesti + e.passif_exoinvesti

    # ------------------------------------------------------------------
    #  ÉTAPE 5 — Marché du crédit
    # ------------------------------------------------------------------

    def _rebuild_interest_cache(self) -> None:
        """
        Reconstruction complète des caches charges_interets / revenus_interets.

        USAGE : outil de débogage ou de vérification de cohérence uniquement.
        En fonctionnement normal, ces caches sont maintenus de façon INCRÉMENTALE
        dans toutes les opérations qui créent, modifient ou détruisent un prêt :
          execute_loan, _revalue_loan, _transfer_claims_for_payment,
          _pay_single_amortization, process_single_failure (phases 2 et 3).
        Appeler cette méthode à chaque pas (comportement antérieur au Bloc 9)
        est redondant et coûte O(N_prêts) inutilement.
        """
        for e in self.active_entities():
            e.charges_interets = 0.0
            e.revenus_interets = 0.0
        for loan in self.active_loans():
            borrower = self.entities.get(loan.borrower_id)
            lender = self.entities.get(loan.lender_id)
            flow = loan.rate * loan.principal
            if borrower and borrower.alive:
                borrower.charges_interets += flow
            if lender and lender.alive:
                lender.revenus_interets += flow

    def _select_active_credit_entities(self) -> List[Entity]:
        """
        Retourne les entités éligibles au marché du crédit :
          P_i > 0  ET  L_i / P_i > s  (seuil de liquidité relative).
        Filtre les entités sans passif productif (division par zéro) et celles
        trop illiquides pour offrir ou demander du crédit utilement.

        OPT-3 : ratio_liquide_passif inliné (descriptor lookup + branche morte
        évités). OPT-6 : compréhension de liste (LIST_APPEND opcode spécialisé,
        plus rapide que append explicite). Expression mathématiquement
        identique → résultat bit-pour-bit identique à la propriété quand p > 0.
        """
        s = self.config.seuil_ratio_liquide_passif
        eps = self.config.epsilon
        return [
            e for e in self.active_entities()
            if (p := e.passif_total) > eps and e.actif_liquide / p > s
        ]

    def _lender_offer(self, lender: Entity) -> float:
        """
        Liquidité que le prêteur peut offrir : L − réserve.
        La réserve = max(s·P, B_innée) garantit L ≥ B après le prêt,
        ce qui protège contre un passage sous le seuil de faillite.
        Sans cette contrainte, une entité avec P < B/s prêterait sous son propre
        seuil d'insolvabilité.
        """
        return max(0.0, lender.actif_liquide - self._liquidity_reserve(lender))

    def _liquidity_reserve(self, entity: Entity) -> float:
        """
        Réserve de liquidité minimale imposée à toute entité :
            réserve = max(s·P, B_innée)

        Utilisée de façon cohérente dans _lender_offer() (offre de crédit)
        et auto_invest_end_of_turn() (surplus auto-investi) pour éviter des
        incohérences de comportement entre les deux phases.
        """
        return max(
            self.config.seuil_ratio_liquide_passif * entity.passif_total,
            entity.passif_inne,
        )

    def _borrower_qmax(self, borrower: Entity, rate: float) -> float:
        """
        Volume optimal d'emprunt pour un emprunteur au taux r.

        Dérivation : l'emprunteur va auto-investir son surplus s de toute façon.
        La question est combien emprunter en PLUS. Le gain marginal d'une unité
        supplémentaire de passif à (P + s + q) est r*(P+s+q) = α / (2√(P+s+q)).
        Optimal quand ce gain marginal = coût r :
            α / (2√(P + s + q_max)) = r  ⟹  q_max = (α/2r)² − P − s

        Retourne 0 si q_max ≤ 0 (l'entité a déjà atteint ou dépassé l'optimum).

        """
        if rate <= self.config.epsilon:
            return 0.0
        surplus = max(0.0, borrower.actif_liquide - self._liquidity_reserve(borrower))
        qmax = (borrower.alpha / (2.0 * rate)) ** 2 - borrower.passif_total - surplus
        return max(0.0, qmax)

    def _gain_auto_invest(self, borrower: Entity, amount: float) -> float:
        """Gain brut d'auto-investissement de `amount` : α(√(P+amount) − √P)."""
        if amount <= self.config.epsilon:
            return 0.0
        p = borrower.passif_total
        return borrower.alpha * (math.sqrt(p + amount) - math.sqrt(p))

    def _gain_borrow(self, borrower: Entity, amount: float, rate: float) -> float:
        """
        Gain net d'emprunt de `amount` au taux r :
            gain_brut − coût = α(√(P+amount) − √P) − r·amount
        Ne tient pas compte du surplus déjà planifié (utilisé pour calculs marginaux).
        """
        if amount <= self.config.epsilon:
            return 0.0
        p = borrower.passif_total
        gross = borrower.alpha * (math.sqrt(p + amount) - math.sqrt(p))
        return gross - rate * amount

    def _gain_lend(self, lender: Entity, amount: float, rate: float) -> float:
        """Gain du prêteur pour un prêt de `amount` au taux r : r·amount."""#Vraiment utile de calculer ça en extérieur ? 
        if amount <= self.config.epsilon:
            return 0.0
        return rate * amount

    def _borrowing_is_acceptable(self, borrower: Entity, amount: float, rate: float) -> bool:
        """
        Comparaison marginale : l'emprunteur auto-investira son surplus de toute façon.
        La question est : vaut-il la peine d'emprunter amount EN PLUS de ce surplus ?

        gain_sans_emprunt = α*(√(P + surplus) − √P)
        gain_avec_emprunt = α*(√(P + surplus + amount) − √P) − rate*amount

        On accepte si gain_avec >= (1 + mu) * gain_sans.
        """
        if amount <= self.config.epsilon:
            return False
        p = borrower.passif_total
        surplus = max(0.0, borrower.actif_liquide - self._liquidity_reserve(borrower))
        gain_b = borrower.alpha * (math.sqrt(p + surplus + amount) - math.sqrt(p)) \
                 - rate * amount
        gain_a = borrower.alpha * (math.sqrt(p + surplus) - math.sqrt(p)) \
                 if surplus > self.config.epsilon else 0.0
        if gain_a <= self.config.epsilon:
            return gain_b > self.config.epsilon
        return gain_b / gain_a >= 1.0 + self.config.mu

    def _lending_is_acceptable(self, lender: Entity, amount: float, rate: float) -> bool:
        """
        Le prêteur prête son excédent de liquidité à son propre taux r*.
        Prêter à r* est neutre avec l'auto-invest à la marge ; on accepte si
        rate >= r*_prêteur (toujours vérifié quand use_lender_rate_as_offer_rate=True).
        """#Rajouter une limite de gain minimal. Réfléchir sur le choix d'auto-invest. 
        if amount <= self.config.epsilon:
            return False
        return rate >= self.compute_internal_rate(lender) - self.config.epsilon

    def _existing_interest_burden(self, borrower: Entity) -> float:
        """
        Charge d'intérêts existante de l'emprunteur : Σ r·q sur ses prêts actifs.
        Lit directement le cache borrower.charges_interets (O(1)).
        Ce cache est maintenu incrémentalement par toutes les opérations de prêt.#
        """ #Utile cette fonction? 
        return borrower.charges_interets

    def _debt_ratio_ok(self, borrower: Entity, principal: float, rate: float) -> bool:
        """
        Vérifie la contrainte d'endettement avant d'accorder un nouveau prêt :
            (charges_existantes + r_new · q_new) / revenus_totaux ≤ seuil_d

        Revenus totaux = extraction α√P + intérêts financiers reçus.
        Cette contrainte empêche un emprunteur de s'endetter au-delà de sa
        capacité à rembourser les intérêts (seuil = 1 : charges ≤ revenus).

        Utilise les caches O(1) charges_interets et revenus_interets.
        Retourne True si le prêt est admissible (ou si seuil ≤ 0 = contrainte désactivée).
        """ #Revenus totaux après ou avant emprunt ? 
        seuil = self.config.seuil_ratio_endettement
        if seuil <= 0:
            return True
        p = max(borrower.passif_total, self.config.epsilon)
        revenus = borrower.alpha * math.sqrt(p) + borrower.revenus_interets
        if revenus <= self.config.epsilon:
            return False
        return (borrower.charges_interets + rate * principal) / revenus <= seuil

    def execute_loan(self, lender: Entity, borrower: Entity, principal: float, rate: float) -> Loan:
        """
        Exécute un prêt de marché : met à jour les bilans des deux parties et les caches.

        Effets sur le bilan du prêteur :
            L_prêteur  -= q   (liquidité sortante)
            R_prêteur  += q   (nouvelle créance)
            C_prêteur  += q   (passif miroir de R)

        Effets sur le bilan de l'emprunteur :
            K^exo_empr += q   (capital exo-investi reçu)
            P^exo_empr += q   (passif exo-investi correspondant)
            P_empr     += q   (cache passif_total)

        Caches d'intérêts mis à jour immédiatement (O(1)) :
            lender.revenus_interets  += r·q
            borrower.charges_interets += r·q
        """
        lender.actif_liquide -= principal
        lender.actif_prete += principal
        lender.passif_credit_detenu += principal
        borrower.actif_exoinvesti += principal
        borrower.passif_exoinvesti += principal
        borrower.passif_total += principal             # cache passif_total
        lender.revenus_interets  += rate * principal   # cache intérêts
        borrower.charges_interets += rate * principal  # cache intérêts
        loan = self.create_loan(lender.entity_id, borrower.entity_id, principal, rate)
        self.log(
            f"Prêt {loan.loan_id}: {lender.entity_id} -> {borrower.entity_id}, "
            f"q={principal:.4f}, r={rate:.4f}"
        )
        return loan

    def credit_market_iteration(self) -> int:
        """
        Appariement itératif prêteur/emprunteur avec matching aléatoire (Bloc 8).

        Si n_candidats_pool == 1 : arbitrage pur (prêteur r* minimal, emprunteur r* maximal).
        Si n_candidats_pool > 1  : tirage aléatoire parmi les k meilleurs candidats de chaque
          côté. Cela permet à une entité médiane d'être prêteur d'une petite et emprunteur
          d'une grande → intermédiaires financiers naturels → contagion en cascade.

        Optimisation : le tri est refait uniquement après une transaction réussie
        (seules les transactions modifient les r*). Entre deux transactions, on re-tire
        aléatoirement dans les pools existants. L'arrêt intervient si MAX_IDLE tentatives
        consécutives échouent.
        """#Changement à faire: non pas les meilleurs/moins bien, mais juste tirer un nombre au hasard de candidats pour chaque round, avec potentiellement plusieurs round par pas !!
        transactions = 0
        k = max(1, self.config.n_candidats_pool)
        MAX_IDLE = max(20, k * k)  # tentatives max sans transaction avant arrêt # Le 20 doit être un paramètre modifiable. Pourquoi k*k ? 
        idle = 0
        need_resort = True
        active_sorted: List[Entity] = []
        pool_lenders: List[Entity] = []
        pool_borrowers: List[Entity] = []

        # Les caches charges_interets / revenus_interets sont maintenus en temps réel
        # (mises à jour incrémentales dans execute_loan, _revalue_loan, etc.).
        # Accès O(1) ici sans reconstruction préalable.
        seuil = self.config.seuil_ratio_endettement
        eps   = self.config.epsilon
        f     = self.config.fraction_taux_emprunteur

        for _ in range(self.config.max_credit_iterations):
            if need_resort:
                # Reconstruction du pool après chaque transaction réussie.
                # On tire un échantillon de 2k entités (O(k)) au lieu de trier N entités (O(N log N)).
                # Cela reflète un marché décentralisé à information locale : chaque agent
                # n'observe qu'un sous-ensemble de contreparties potentielles.
                active = self._select_active_credit_entities()
                if len(active) < 2:
                    break
                sample_size = min(len(active), 2 * k) 
                sample = self.rng.sample(active, sample_size)
                active_sorted = sorted(sample, key=self.compute_internal_rate)
                n = len(active_sorted)
                # Moitié basse → pool prêteurs (r* faible = excédent de capital)
                # Moitié haute → pool emprunteurs (r* élevé = besoin de capital)
                pool_lenders = active_sorted[:max(1, n // 2)]
                pool_borrowers = active_sorted[n // 2:] #Pourquoi séparer les deux pools ? Pourquoi ne pas les traiter comme une seule ? 
                if not pool_lenders or not pool_borrowers:
                    break
                need_resort = False

            # Tirage aléatoire dans les pools : c'est ici que k > 1 crée les intermédiaires.
            # Une entité médiane peut être tirée comme prêteur face à une petite entité dans
            # une itération, et comme emprunteur face à une grande dans une autre.
            lender = self.rng.choice(pool_lenders)
            pool_b = [e for e in pool_borrowers if e.entity_id != lender.entity_id]
            if not pool_b: #si pool_b est vide, ie lender n'a personne à qui donner dans la partie basse 
                idle += 1
                if idle >= MAX_IDLE:
                    break
                continue
            borrower = self.rng.choice(pool_b)

            lender_rate = self.compute_internal_rate(lender)
            borrower_rate = self.compute_internal_rate(borrower)
            if borrower_rate <= lender_rate + eps:
                idle += 1
                if idle >= MAX_IDLE:
                    break
                continue

            offer = self._lender_offer(lender)
            if offer <= eps:
                idle += 1
                if idle >= MAX_IDLE:
                    break
                continue

            # Taux de transaction : interpolation convexe entre r*_prêteur et r*_emprunteur.
            # f = 0 → taux = r*_prêteur (neutre pour lui, tout le surplus va à l'emprunteur).
            # f = 1 → taux = r*_emprunteur (neutre pour lui, tout le surplus va au prêteur).
            rate = (1.0 - f) * lender_rate + f * borrower_rate

            # Volume : fraction θ de la demande optimale, plafonnée par l'offre du prêteur.
            qmax = self._borrower_qmax(borrower, rate)
            demand = self.config.theta * qmax
            principal = min(offer, demand)

            if principal <= eps:
                idle += 1
                if idle >= MAX_IDLE:
                    break
                continue
            # Vérification de la prime de rendement μ : gain_avec ≥ (1+μ)·gain_sans
            if not self._borrowing_is_acceptable(borrower, principal, rate):
                idle += 1
                if idle >= MAX_IDLE:
                    break
                continue

            # Contrainte d'endettement : (charges + r·q) / revenus ≤ seuil_d
            # Inlinée ici pour éviter un appel de méthode (hot path de la boucle).
            if seuil > 0:
                p = max(borrower.passif_total, eps)
                revenus = borrower.alpha * math.sqrt(p) + borrower.revenus_interets
                if revenus <= eps or (borrower.charges_interets + rate * principal) / revenus > seuil:
                    idle += 1
                    if idle >= MAX_IDLE:
                        break
                    continue

            # Transaction validée : mise à jour bilans + caches intérêts.
            self.execute_loan(lender, borrower, principal, rate)
            transactions += 1
            idle = 0
            # Les r* et les offres ont changé → ré-échantillonner les pools au prochain tour.
            need_resort = True

        return transactions

    # ------------------------------------------------------------------
    #  ÉTAPE 6 — Auto-investissement
    # ------------------------------------------------------------------

    def auto_invest_end_of_turn(self) -> float:
        """
        Auto-investissement en fin de pas : convertit une fraction φ du surplus liquide
        en capital endogène.

        Pour chaque entité :
            surplus  = max(0, L − réserve)   avec réserve = max(s·P, B_innée)
            x        = φ · surplus           (φ = fraction_auto_investissement = 0.5)
            L       -= x
            K^endo  += x,   P^endo += x      (invariant K^endo = P^endo maintenu)
            P       += x                      (cache passif_total mis à jour)

        La réserve max(s·P, B_innée) garantit L ≥ B après conversion,
        cohérente avec _lender_offer() qui applique la même contrainte.
        Retourne le volume total auto-investi ce pas.
        """
        total = 0.0
        for e in self.active_entities():
            surplus = max(0.0, e.actif_liquide - self._liquidity_reserve(e))
            x = self.config.fraction_auto_investissement * surplus
            if x > self.config.epsilon:
                e.actif_liquide -= x
                e.actif_endoinvesti += x
                e.passif_endoinvesti += x
                e.passif_total += x   # cache passif_total
                total += x
        return total

    # ------------------------------------------------------------------
    #  ÉTAPE 7 — Faillites et cascades
    # ------------------------------------------------------------------

    def is_bankrupt(self, entity: Entity) -> bool:
        return entity.alive and entity.actif_total + self.config.epsilon < entity.passif_bilan

    def _capture_system_state(self) -> dict:
        """
        Snapshot agrégé du système juste avant la résolution des faillites.
        Utilisé par resolve_cascades() pour construire le CascadeEvent (comparaison avant/après).

        OPT-4 : trois sommes fusionnées en une seule passe (ordre d'addition
        identique → résultat FP bit-pour-bit identique).
        """
        alive = self.active_entities()
        a = p = l = 0.0
        for e in alive:
            a += e.actif_total
            p += e.passif_total
            l += e.actif_liquide
        return {
            "actif_total": a,
            "passif_total": p,
            "liquidite": l,
            "nb_entites": len(alive),
        }

    def compute_hidden_fragility(self) -> Dict[int, float]:
        """
        Calcule la fragilité cachée de chaque prêteur vivant :
            perte_cachée = Σ [q_nominal − q_nominal×(1−δ_exo)^âge]
                         = Σ q_nominal × [1 − (1−δ_exo)^âge]

        Cette quantité représente l'écart entre la valeur comptable nominale des
        créances (actif_prete) et leur valeur économique réelle (dépréciée). Elle
        mesure le risque de write-down latent si les prêts étaient réévalués aujourd'hui.

        NE modifie aucun bilan. Purement analytique.
        Retourne {entity_id: perte_cachée_totale}.
        """
        factor = max(0.0, 1.0 - self.config.taux_depreciation_exo)
        fragility: Dict[int, float] = {}
        for loan in self.active_loans():
            lender = self.get_entity(loan.lender_id)
            if not lender.alive:
                continue
            age = self.current_step - loan.creation_step
            real_value = loan.principal * (factor ** age)
            hidden_loss = loan.principal - real_value
            if hidden_loss > self.config.epsilon:
                fragility[loan.lender_id] = fragility.get(loan.lender_id, 0.0) + hidden_loss
        return fragility

    def process_single_failure(self, failed_entity: Entity) -> Dict[str, float]:
        """
        Traite la faillite d'une entité en trois phases :
          1) Identification des créanciers (poids proportionnels aux encours).
          2) Redistribution directe des créances où l'entité était prêteuse :
             chaque prêt est réévalué à sa valeur réelle (principal×(1−δ)^âge) puis
             fractionné entre les créanciers au prorata de leurs poids.
             Le bilan de l'emprunteur n'est pas modifié : K^exo et P^exo ont déjà
             décru via apply_depreciation(). Si pas de créanciers éligibles, la
             créance est annulée symétriquement (K^exo et P^exo réduits).
          3) Annulation des prêts dont l'entité était emprunteuse (perte pour prêteurs).
        Retourne {destroyed_assets, redirected_claims}.
        """
        destroyed_assets = 0.0
        redirected_claims = 0.0

        # Phase 1 : calcul des poids créanciers (avant annulation des emprunts)
        # OPT-2 : index _loans_by_borrower → on n'itère que sur les prêts dont
        # l'entité faillie est emprunteuse. Tri par loan_id pour préserver
        # exactement l'ordre d'addition flottante de l'implémentation d'origine
        # (qui itérait active_loans() en ordre d'insertion = ordre loan_id).
        creditors: Dict[int, float] = {}
        borrower_loan_ids = sorted(self._loans_by_borrower.get(failed_entity.entity_id, ()))
        for lid in borrower_loan_ids:
            loan = self.loans[lid]
            creditors[loan.lender_id] = creditors.get(loan.lender_id, 0.0) + loan.principal
        total_claims = sum(creditors.values())
        weights: Dict[int, float] = {}
        if total_claims > self.config.epsilon:
            weights = {cid: amt / total_claims for cid, amt in creditors.items()}

        # Phase 2 : redistribution des prêts où l'entité faillie était prêteuse
        # OPT-2 : index _loans_by_lender + tri par loan_id pour préserver l'ordre
        # de traitement (et donc l'ordre des create_loan → next_loan_id).
        factor = max(0.0, 1.0 - self.config.taux_depreciation_exo)
        lender_loan_ids = sorted(self._loans_by_lender.get(failed_entity.entity_id, ()))
        for lid in lender_loan_ids:
            loan = self.loans[lid]
            if not loan.active:
                continue  # défensif (ne devrait pas survenir : index ⇒ actif)
            age = self.current_step - loan.creation_step
            real_value = loan.principal * (factor ** age)

            # Créanciers éligibles : exclure les auto-prêts (cid == borrower)
            eligible = {cid: w for cid, w in weights.items() if cid != loan.borrower_id}
            total_eligible = sum(eligible.values())

            if real_value <= self.config.epsilon or total_eligible <= self.config.epsilon:
                # Annulation symétrique : l'emprunteur perd la contrepartie exo
                borrower = self.get_entity(loan.borrower_id)
                cancel = min(real_value, borrower.actif_exoinvesti)
                borrower.actif_exoinvesti -= cancel
                exo_cancel = min(real_value, borrower.passif_exoinvesti)
                borrower.passif_exoinvesti -= exo_cancel
                borrower.passif_total -= exo_cancel  # Bloc 8 : cache passif_total
                # Cache : le prêt disparaît → l'emprunteur ne doit plus ces charges.
                if borrower.alive:
                    borrower.charges_interets -= loan.rate * loan.principal
                # Le prêteur est l'entité faillie (morte) → son cache n'importe pas.
                self._idx_remove(loan)  # OPT-2
                loan.active = False
                continue

            # Redistribution fractionnée à valeur réelle
            self._idx_remove(loan)  # OPT-2
            loan.active = False
            borrower = self.get_entity(loan.borrower_id)
            # Cache : supprime la contribution du prêt original (prêteur = entité faillie).
            # La somme redistribuée = real_value ; la différence avec loan.principal
            # (dépreciation non réévaluée) est absorbée par l'emprunteur.
            if borrower.alive:
                borrower.charges_interets += loan.rate * (real_value - loan.principal)
            for cid, w in eligible.items():
                share = (w / total_eligible) * real_value
                if share <= self.config.epsilon:
                    continue
                creditor = self.get_entity(cid)
                if not creditor.alive:
                    continue
                self.create_loan(
                    lender_id=cid,
                    borrower_id=loan.borrower_id,
                    principal=share,
                    rate=loan.rate,
                    parent_loan_id=loan.loan_id,
                )
                creditor.actif_prete += share
                creditor.passif_credit_detenu += share
                creditor.revenus_interets += loan.rate * share
                redirected_claims += share

        # Phase 3 : annulation des prêts dont l'entité faillie était emprunteuse
        # OPT-2 : index _loans_by_borrower + tri par loan_id pour ordre déterministe.
        borrower_loan_ids = sorted(self._loans_by_borrower.get(failed_entity.entity_id, ()))
        for lid in borrower_loan_ids:
            loan = self.loans[lid]
            if not loan.active:
                continue  # défensif (Phase 2 a pu désactiver des auto-prêts éventuels)
            lender = self.get_entity(loan.lender_id)
            lender.actif_prete -= loan.principal
            lender.passif_credit_detenu -= loan.principal
            # Cache : le prêteur perd ses revenus sur ce prêt.
            lender.revenus_interets -= loan.rate * loan.principal
            # L'emprunteur (entité faillie) perd ses charges ; inutile de mettre à
            # jour son cache car elle sera marquée morte juste après.
            destroyed_assets += loan.principal
            self._idx_remove(loan)  # OPT-2
            loan.active = False

        failed_entity.alive = False
        failed_entity.death_step = self.current_step
        self._alive_cache_dirty = True  # OPT-3 : décès
        self.log(f"Faillite entité {failed_entity.entity_id}")
        return {"destroyed_assets": destroyed_assets, "redirected_claims": redirected_claims}

    def resolve_cascades(self) -> Tuple[Dict[str, float], Optional[CascadeEvent]]:
        """
        Détecte et résout les faillites en cascade.
        Retourne (totals_dict, cascade_event_ou_None).
        """
        state_before = self._capture_system_state()
        # Entités solvables avant la cascade (pour détecter la contagion)
        # Remarque : cette étiquette statistique n'utilise volontairement ici que
        # passif_total, alors que le critère effectif de faillite passe par
        # passif_bilan = passif_total + passif_credit_detenu (voir is_bankrupt()).
        # Il n'y a donc pas de contradiction dans la dynamique de faillite elle-même,
        # mais une légère divergence possible dans la classification analytique
        # "faillite initiale" vs "faillite de contagion".
        solvent_before = {
            eid for eid, e in self.entities.items()
            if e.alive and e.actif_total >= e.passif_total - self.config.epsilon
        }

        totals = {
            "destroyed_assets": 0.0,
            "redirected_claims": 0.0,
            "failures": 0.0,
            "failed_entity_lifespans": [],
        }
        faillis_info = []

        changed = True
        while changed:
            changed = False
            bankrupts = [e for e in self.active_entities() if self.is_bankrupt(e)]
            if not bankrupts:
                break
            for entity in bankrupts:
                if not entity.alive:
                    continue
                faillis_info.append({
                    "actif_total": entity.actif_total,
                    "passif_total": entity.passif_total,
                    "etait_solvable": entity.entity_id in solvent_before,
                })
                result = self.process_single_failure(entity)
                totals["destroyed_assets"] += result["destroyed_assets"]
                totals["redirected_claims"] += result["redirected_claims"]
                totals["failures"] += 1.0
                totals["failed_entity_lifespans"].append(self.current_step - entity.creation_step)
                changed = True

        cascade_event = None
        if faillis_info:
            cascade_event = Collector.build_cascade(
                self.current_step,
                state_before,
                faillis_info,
                totals["destroyed_assets"],
            )

        return totals, cascade_event

    # ------------------------------------------------------------------
    #  ÉTAPE 4b — Amortissement du principal JE N'EN VEUX PAS 
    # ------------------------------------------------------------------

    def pay_amortization_phase(self) -> float:
        """
        Remboursement géométrique du principal pour tous les prêts actifs :
          amort = taux_amortissement × principal_restant
        Le borrower verse ce montant au lender ; principal et passif_exoinvesti
        diminuent en conséquence. actif_exoinvesti reste inchangé : l'investissement
        subsiste, la dette seule décroît, ce qui crée de l'équité graduellement.
        Les prêts avec un prêteur mort (cas résiduel défensif) sont ignorés.
        """
        tau = self.config.taux_amortissement
        if tau <= self.config.epsilon:
            return 0.0
        total = 0.0
        # OPT-1 : sorted() redondant supprimé (cf. pay_interest_phase).
        for loan in self.active_loans():
            total += self._pay_single_amortization(loan, tau)
        return total

    def _pay_single_amortization(self, loan: Loan, tau: float) -> float:
        """
        Traite l'amortissement d'un seul prêt.

        Le remboursement est géométrique : dû = τ × principal_restant.
        L'emprunteur verse le montant via _ensure_payment_capacity() (mobilisation
        de liquidité ou cession de créances si illiquidité).

        Effets bilans :
            loan.principal     -= reduction   (réduction proportionnelle au paiement)
            P^exo_empr         -= reduction   (la dette fond)
            P_empr             -= reduction   (cache passif_total)
            R_prêteur          -= reduction   (créance réduite d'autant)
            C_prêteur          -= reduction   (passif miroir réduit)
            L_prêteur          += payment     (cash reçu)

        Caches d'intérêts :
            borrower.charges_interets -= r × reduction
            lender.revenus_interets   -= r × reduction

        Note : actif_exoinvesti de l'emprunteur n'est PAS réduit. Le capital reste
        déployé ; seule la dette correspondante diminue, créant de l'équité graduelle.
        """
        if not loan.active:
            return 0.0
        lender = self.get_entity(loan.lender_id)
        if not lender.alive:
            return 0.0   # garde défensif (ne devrait pas survenir après redistribution)
        due = tau * loan.principal
        if due <= self.config.epsilon:
            return 0.0
        borrower = self.get_entity(loan.borrower_id)
        payment = self._ensure_payment_capacity(borrower, due, loan.lender_id)

        # Réduction du principal proportionnelle au paiement effectif.
        # Si payment < due (illiquidité partielle), réduction proportionnelle seulement.
        reduction = min(payment, loan.principal)
        loan.principal -= reduction
        borrower.passif_exoinvesti -= reduction   # la dette fond
        borrower.passif_total -= reduction         # cache passif_total
        lender.actif_prete -= reduction            # créance réduite d'autant
        lender.passif_credit_detenu -= reduction   # passif miroir réduit
        lender.actif_liquide += payment            # cash reçu par le prêteur
        # Cache intérêts : la réduction du principal diminue les flux futurs r·q.
        delta_flow = loan.rate * reduction
        borrower.charges_interets -= delta_flow
        lender.revenus_interets -= delta_flow

        if loan.principal <= self.config.epsilon:
            self._idx_remove(loan)  # OPT-2
            loan.active = False

        return payment

    # ------------------------------------------------------------------
    #  MOUVEMENT BROWNIEN DES ALPHAS
    # ------------------------------------------------------------------

    def _update_alphas(self) -> None: #Problème conceptuel avec ce calcul là.  Pourquoi il y a t'il un drift positif ?  
        """
        Choc de productivité géométrique sur chaque entité vivante :
            α(t+1) = α(t) × exp(σ · N(0,1))

        Modélise une hétérogénéité temporelle des productivités. Le processus
        est géométrique (pas de signe négatif possible sur α) et log-normal.
        σ = 0 désactive le processus (α statique).
        """
        sigma = self.config.alpha_sigma_brownien
        if sigma <= 0:
            return
        for e in self.active_entities():
            e.alpha *= math.exp(self.rng.gauss(0.0, sigma)) #GROS PROBLEME !!! DRIFT POSITIF

    # ------------------------------------------------------------------
    #  STATISTIQUES LÉGÈRES
    # ------------------------------------------------------------------

    def _collect_light_stats(
        self,
        spawn_count: int,
        extraction_total: float,
        interest_paid: float,
        amortissement_total: float,
        credit_transactions: int,
        auto_invest_total: float,
        cascade_totals: Dict,
    ) -> Dict:
        """
        Collecte les statistiques légères (une ligne par pas) et les ajoute à self.stats.

        Ces statistiques sont exportées dans stats_legeres.csv et permettent un suivi
        macroscopique rapide sans charger les données du Collector.

        Champs exportés : step, population (vivante/totale), flux d'extraction,
        intérêts, transactions de crédit, faillites, volume de prêts, actif/passif/liquidité
        systémique, passif moyen, taux interne moyen.
        """
        # OPT-4 : agrégats fusionnés en une seule passe sur alive (et une sur loans).
        # L'ordre des additions est strictement préservé (alive[0] + alive[1] + …),
        # donc le résultat flottant est identique au bit près à l'implémentation
        # précédente qui appelait sum() séparément sur chaque grandeur.
        alive = self.active_entities()
        active_loans = self.active_loans()
        eps = self.config.epsilon

        actif_total_sys = 0.0
        passif_total_sys = 0.0
        liquidite_totale = 0.0
        passifs_sum = 0.0
        n_passifs = 0          # = len(alive)
        rates_sum = 0.0
        n_rates = 0
        extraction_power_total = 0.0
        asset_values = []
        alive_lifespans = []
        for e in alive:
            actif_total_sys += e.actif_total
            p = e.passif_total
            passif_total_sys += p
            liquidite_totale += e.actif_liquide
            extraction_power_total += e.alpha * math.sqrt(max(p, 0.0))
            asset_values.append(e.actif_total)
            alive_lifespans.append(self.current_step - e.creation_step)
            passifs_sum += p
            n_passifs += 1
            if p > eps:
                rates_sum += self.compute_internal_rate(e)
                n_rates += 1

        volume_prets = 0.0
        for l in active_loans:
            volume_prets += l.principal
        network_density = 0.0
        if n_passifs > 1:
            network_density = len(active_loans) / (n_passifs * (n_passifs - 1))
        financial_density = volume_prets / actif_total_sys if actif_total_sys > eps else 0.0
        mean_credit_in_degree = len(active_loans) / n_passifs if n_passifs else 0.0
        mean_credit_out_degree = mean_credit_in_degree
        mean_credit_total_degree = (2 * len(active_loans)) / n_passifs if n_passifs else 0.0

        snapshot_due = self.config.freq_snapshot > 0 and self.current_step % self.config.freq_snapshot == 0
        asset_distribution_snapshot = self._distribution_summary(asset_values) if snapshot_due else None
        alive_entity_lifespans = self._distribution_summary(alive_lifespans) if snapshot_due else None
        failed_entity_lifespans = cascade_totals.get("failed_entity_lifespans", [])

        data = {
            "step": self.current_step,
            "n_entities_alive": n_passifs,
            "n_entities_total": len(self.entities),
            "n_spawned": spawn_count,
            "extraction_total": round(extraction_total, 4),
            "interest_paid_total": round(interest_paid, 4),
            "amortissement_total": round(amortissement_total, 4),
            "credit_transactions": credit_transactions,
            "auto_invest_total": round(auto_invest_total, 4),
            "n_failures": int(cascade_totals["failures"]),
            "destroyed_assets": round(cascade_totals["destroyed_assets"], 4),
            "redirected_claims": round(cascade_totals["redirected_claims"], 4),
            "volume_prets_actifs": round(volume_prets, 4),
            "n_prets_actifs": len(active_loans),
            "actif_total_systeme": round(actif_total_sys, 4),
            "passif_total_systeme": round(passif_total_sys, 4),
            "liquidite_totale": round(liquidite_totale, 4),
            "mean_passif": round(passifs_sum / n_passifs, 4) if n_passifs else 0.0,
            "mean_internal_rate": round(rates_sum / n_rates, 6) if n_rates else 0.0,
            "network_density": round(network_density, 8),
            "financial_density": round(financial_density, 8),
            "mean_credit_in_degree": round(mean_credit_in_degree, 6),
            "mean_credit_out_degree": round(mean_credit_out_degree, 6),
            "mean_credit_total_degree": round(mean_credit_total_degree, 6),
            "extraction_power_total": round(extraction_power_total, 4),
            "asset_distribution_snapshot": asset_distribution_snapshot,
            "entity_age_distribution": alive_entity_lifespans,
            "failed_entity_lifespans": failed_entity_lifespans,
            "alive_entity_lifespans": alive_entity_lifespans,
        }
        self.stats.append(data)
        return data

    # ------------------------------------------------------------------
    #  PAS DE SIMULATION
    # ------------------------------------------------------------------

    def run_step(self) -> Dict:
        """
        Exécute un pas complet de simulation et retourne les statistiques légères.

        Séquence des 9 étapes :
          0. Réinitialisation des flux de suivi
          1. Chocs browniens sur les α
          2. Création d'entités Poisson(λ)
          3. Extraction Π = α√P
          4. Paiement des intérêts r·q (avec mobilisation de capacité)
          5. Amortissement τ·q (désactivé par défaut)
          6. Dépréciation géométrique des actifs
          7. Marché du crédit (matching aléatoire k-pool)
          8. Résolution des cascades de faillite
          9. Auto-investissement φ·surplus

        current_step est incrémenté en fin de méthode.
        """
        if self._in_run_step:
            raise RuntimeError("run_step() est déjà en cours.")
        self._in_run_step = True
        try:
            self._reset_step_flows()
            self._update_alphas()
            spawn_count = self.spawn_new_entities()
            extraction_total = self.extract_from_nature()

            interest_paid = self.pay_interest_phase()

            amortissement_total = self.pay_amortization_phase()

            self.apply_depreciation()
            credit_transactions = self.credit_market_iteration()
            cascade_totals, cascade_event = self.resolve_cascades()
            auto_invest_total = self.auto_invest_end_of_turn()

            light_stats = self._collect_light_stats(
                spawn_count, extraction_total, interest_paid,
                amortissement_total, credit_transactions, auto_invest_total, cascade_totals,
            )

            # Collecteur statistique riche
            self.collector.record_step(self, cascade_event, self._step_flows)

            self.current_step += 1
            self._append_observation_to_buffer()
            return light_stats
        finally:
            self._in_run_step = False

    # ------------------------------------------------------------------
    #  EXÉCUTION COMPLÈTE
    # ------------------------------------------------------------------

    def request_stop(self) -> None:
        """Demande l'arrêt propre d'une boucle run_dynamic()/run_with_interventions()."""
        self._stop_requested = True

    def pause(self) -> None:
        """Marque la simulation comme en pause pour les contrôleurs interactifs."""
        self._paused = True

    def resume(self) -> None:
        """Relance une simulation mise en pause par un contrôleur interactif."""
        self._paused = False
        self._stop_requested = False

    def step_once(self) -> Dict:
        """Avance d'un pas complet, point d'entrée pratique pour une interface pas-à-pas."""
        if self._stop_requested:
            raise RuntimeError("Simulation arrêtée: appeler resume()/nouvelle instance avant de continuer.")
        return self.run_step()

    def run_dynamic(
        self,
        n_steps: Optional[int] = None,
        observe_every: int = 10,
        observer: Optional[Callable[[Dict[str, Any]], None]] = None,
        update_provider: Optional[Callable[[], Optional[Dict[str, Any]]]] = None,
        allow_risky: bool = False,
    ) -> List[Dict]:
        """
        Boucle dynamique optionnelle par blocs.

        Les updates sont demandées et appliquées uniquement avant un run_step()
        complet. observer(observation) est appelé après un pas complet, donc après
        _collect_light_stats(), collector.record_step() et current_step += 1.
        """
        n = self.config.duree_simulation - self.current_step if n_steps is None else n_steps
        if observe_every <= 0:
            observe_every = 1
        self._stop_requested = False

        for _ in range(n):
            if self._stop_requested or self._paused:
                break
            if update_provider is not None:
                updates = update_provider()
                if updates:
                    self.apply_parameter_updates(
                        updates,
                        allow_risky=allow_risky,
                        scope="global_config",
                        source="interactive",
                    )
            self.run_step()
            if observer is not None and self.current_step % observe_every == 0:
                observer(self.current_observation())
        return self.stats

    @staticmethod
    def _normalize_intervention(raw: Dict[str, Any], index: int) -> Dict[str, Any]:
        intervention_type = "parameter_updates"
        if "entity_updates" in raw:
            updates = dict(raw["entity_updates"])
            intervention_type = "entity_updates"
        elif "updates" in raw:
            updates = dict(raw["updates"])
        elif (
            "parameter" in raw
            and "new_value" in raw
            and raw.get("scope") in {"existing_entities", "future_entities"}
            and raw["parameter"] in ENTITY_UPDATE_NAMES
        ):
            updates = {raw["parameter"]: raw["new_value"]}
            intervention_type = "entity_updates"
        elif "parameter" in raw and "new_value" in raw:
            updates = {raw["parameter"]: raw["new_value"]}
        else:
            raise ValueError(
                f"Intervention #{index}: fournir 'updates', 'entity_updates' ou 'parameter' + 'new_value'."
            )
        expected_by_parameter = {}
        if "old_value_expected" in raw and "parameter" in raw:
            expected_by_parameter[raw["parameter"]] = raw["old_value_expected"]
        if "old_value_expected_by_parameter" in raw:
            expected_by_parameter.update(raw["old_value_expected_by_parameter"])
        step = raw.get("step")
        if not isinstance(step, int) or step < 0:
            raise ValueError(f"Intervention #{index}: step doit être un entier >= 0.")
        scope = raw.get("scope", "global_config")
        if scope not in SCOPES:
            raise ValueError(f"Intervention #{index}: scope inconnu {scope!r}.")
        return {
            "index": index,
            "type": intervention_type,
            "step": step,
            "updates": updates,
            "scope": scope,
            "selector": raw.get("selector", "alive"),
            "comment": raw.get("comment", ""),
            "old_value_expected_by_parameter": expected_by_parameter,
        }

    def _prevalidate_interventions(self, interventions: List[Dict[str, Any]], allow_risky: bool, n_steps: int) -> None:
        last_executable_step = n_steps - 1
        for intervention in interventions:
            if intervention["step"] > last_executable_step:
                raise ValueError(
                    f"Intervention #{intervention['index']}: step {intervention['step']} hors de la fenetre executee."
                )
            if intervention["type"] == "entity_updates":
                ok, _, refused = self._validate_entity_updates(
                    intervention["updates"],
                    scope=intervention["scope"],
                    allow_risky=allow_risky,
                )
                if not ok:
                    raise ValueError(f"Intervention #{intervention['index']} invalide: {refused}")
                continue
            for parameter, new_value in intervention["updates"].items():
                ok, _, info = self._validate_parameter_update(
                    parameter,
                    new_value,
                    allow_risky=allow_risky,
                    scope=intervention["scope"],
                )
                if not ok and info.get("reason") != "ancienne valeur différente de old_value_expected":
                    raise ValueError(f"Intervention #{intervention['index']} invalide: {info}")

    def run_with_interventions(
        self,
        interventions: List[Dict[str, Any]],
        n_steps: Optional[int] = None,
        observe_every: int = 10,
        observer: Optional[Callable[[Dict[str, Any]], None]] = None,
        allow_risky: bool = False,
        validate_before_start: bool = True,
    ) -> List[Dict]:
        """
        Exécute un scénario d'interventions reproductible.

        Les interventions sont triées par step et appliquées avant le pas portant
        ce numéro, jamais pendant credit_market_iteration() ni resolve_cascades().
        Chaque changement est journalisé dans parameter_update_log.
        """
        n = self.config.duree_simulation - self.current_step if n_steps is None else n_steps
        if observe_every <= 0:
            observe_every = 1
        normalized = [self._normalize_intervention(raw, i) for i, raw in enumerate(interventions)]
        normalized.sort(key=lambda item: (item["step"], item["index"]))
        if validate_before_start:
            self._prevalidate_interventions(normalized, allow_risky=allow_risky, n_steps=self.current_step + n)
        self.planned_interventions = self._json_safe(normalized)

        cursor = 0
        self._stop_requested = False
        for _ in range(n):
            if self._stop_requested or self._paused:
                break
            while cursor < len(normalized) and normalized[cursor]["step"] == self.current_step:
                intervention = normalized[cursor]
                metadata = {
                    "intervention_index": intervention["index"],
                    "comment": intervention["comment"],
                    "old_value_expected_by_parameter": intervention["old_value_expected_by_parameter"],
                }
                if intervention["type"] == "entity_updates":
                    result = self.apply_entity_updates(
                        intervention["updates"],
                        allow_risky=allow_risky,
                        scope=intervention["scope"],
                        selector=intervention["selector"],
                        source="scenario",
                        metadata={k: v for k, v in metadata.items() if k != "old_value_expected_by_parameter"},
                    )
                else:
                    result = self.apply_parameter_updates(
                        intervention["updates"],
                        allow_risky=allow_risky,
                        scope=intervention["scope"],
                        source="scenario",
                        metadata=metadata,
                    )
                if result["refused"]:
                    raise ValueError(f"Intervention #{intervention['index']} refusée: {result['refused']}")
                cursor += 1
            self.run_step()
            if observer is not None and self.current_step % observe_every == 0:
                observer(self.current_observation())
        return self.stats

    def intervention_journal(self) -> Dict[str, Any]:
        """Journal complet suffisant pour rejouer la configuration et les interventions."""
        return self._json_safe({
            "scenario_name": self.scenario_name,
            "initial_config": self.initial_config_snapshot,
            "seed": self.initial_config_snapshot.get("seed"),
            "planned_interventions": self.planned_interventions,
            "applied_updates": self.parameter_update_log,
        })

    def export_intervention_journal(self, filepath: str) -> None:
        """Exporte le journal d'interventions en JSON reproductible."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.intervention_journal(), f, indent=2, ensure_ascii=False)

    def run(self, n_steps: Optional[int] = None, verbose: bool = True) -> List[Dict]:
        """
        Lance la simulation pour n_steps pas (par défaut config.duree_simulation).
        Affiche une progression toutes les 10 % si verbose=True.
        Retourne self.stats (liste de dicts, une entrée par pas).
        """
        n = self.config.duree_simulation if n_steps is None else n_steps
        report_interval = max(1, n // 10)

        if verbose:
            print(f"Démarrage : {n} pas, {len(self.entities)} entités initiales")

        for k in range(n):
            self.run_step()
            if verbose and (k + 1) % report_interval == 0:
                s = self.stats[-1]
                print(
                    f"  Pas {k+1:5d} | Entités: {s['n_entities_alive']:4d} | "
                    f"Faillites: {s['n_failures']:3d} | "
                    f"Prêts actifs: {s['n_prets_actifs']:5d} | "
                    f"Vol. prêts: {s['volume_prets_actifs']:10.1f}"
                )

        if verbose:
            print("Simulation terminée.")
        return self.stats

    # ------------------------------------------------------------------
    #  EXPORTS
    # ------------------------------------------------------------------

    def export_stats_csv(self, filepath: str) -> None:
        """Exporte self.stats (statistiques légères par pas) dans un fichier CSV."""
        if not self.stats:
            return
        fieldnames = list(self.stats[0].keys())
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.stats)

    def export_event_log(self, filepath: str) -> None:
        """Exporte le journal d'événements (log_events=True) dans un fichier texte."""
        with open(filepath, "w", encoding="utf-8") as f:
            for line in self.event_log:
                f.write(line + "\n")

    def summary(self) -> dict:
        """
        Retourne un résumé statistique de la simulation terminée.
        Utilisé pour meta.json et l'affichage final.
        cascade_max_size est la taille maximale d'une cascade sur un seul pas
        (nombre de faillites), pas la taille maximale enregistrée par le Collector.
        """
        if not self.stats:
            return {}
        total_failures = sum(s["n_failures"] for s in self.stats)
        max_cascade = max(s["n_failures"] for s in self.stats)
        return {
            "steps_simulated": self.current_step,
            "entities_created_total": len(self.entities),
            "entities_alive_final": self.stats[-1]["n_entities_alive"],
            "failures_total": total_failures,
            "cascade_max_size": max_cascade,
            "loans_created_total": len(self.loans),
            "loans_active_final": self.stats[-1]["n_prets_actifs"],
            "cascades_recorded": len(self.collector.cascades),
        }


def run_scenario(
    scenario: Dict[str, Any],
    observe_every: int = 10,
    observer: Optional[Callable[[Dict[str, Any]], None]] = None,
    allow_risky: bool = False,
) -> Simulation:
    """
    Crée et exécute une Simulation depuis un scénario reproductible en dict.

    Format minimal :
        {
          "name": "...",
          "seed": 42,
          "initial_config": {"duree_simulation": 3000, "theta": 0.2},
          "interventions": [...]
        }
    """
    if not isinstance(scenario, dict):
        raise ValueError("scenario doit être un dictionnaire.")
    initial_config = dict(scenario.get("initial_config", {}))
    if "seed" in scenario:
        initial_config["seed"] = scenario["seed"]
    config = SimulationConfig(**initial_config)
    sim = Simulation(config)
    sim.scenario_name = scenario.get("name")
    sim.run_with_interventions(
        scenario.get("interventions", []),
        n_steps=config.duree_simulation,
        observe_every=observe_every,
        observer=observer,
        allow_risky=allow_risky,
    )
    return sim
