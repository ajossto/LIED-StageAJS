"""
statistics.py — Module de collecte et d'organisation des données statistiques.

Ce module est indépendant du moteur de simulation. Il collecte :

  1. Snapshots périodiques des distributions (taille des entités, liquidité, levier…)
  2. Données brutes des cascades de faillite (volume en joules, contagion)
  3. Indicateurs systémiques dynamiques (levier agrégé, concentration, liquidité)

Interface principale :
    collector = Collector(freq_snapshot=10)
    # dans chaque pas de simulation :
    collector.record_step(sim, cascade_event_optionnel)

Aucune dépendance circulaire : le collecteur lit uniquement les
attributs/méthodes publics de la simulation.
"""

import math
import os
from typing import Dict, List, Optional


# ============================================================
#  STRUCTURES DE DONNÉES
# ============================================================

class SnapshotDistribution:
    """
    Capture la distribution d'une grandeur sur toutes les entités vivantes
    à un instant donné. Stocke les valeurs brutes (pas d'agrégation précoce).
    """

    def __init__(self, step: int, name: str, values: List[float]):
        self.step = step
        self.name = name          # ex : "passif_total", "ratio_L_P"
        self.values = sorted(values)

    def quantiles(self, probs=(0.1, 0.25, 0.5, 0.75, 0.9, 0.99)):
        if not self.values:
            return {p: 0.0 for p in probs}
        n = len(self.values)
        result = {}
        for p in probs:
            idx = p * (n - 1)
            lo, hi = int(idx), min(int(idx) + 1, n - 1)
            result[p] = self.values[lo] + (idx - lo) * (self.values[hi] - self.values[lo])
        return result

    def mean(self) -> float:
        if not self.values:
            return 0.0
        return sum(self.values) / len(self.values)

    def std(self) -> float:
        if len(self.values) < 2:
            return 0.0
        m = self.mean()
        return math.sqrt(sum((v - m) ** 2 for v in self.values) / len(self.values))

    def to_dict(self) -> dict:
        q = self.quantiles()
        return {
            "step": self.step,
            "name": self.name,
            "n": len(self.values),
            "mean": round(self.mean(), 4),
            "std": round(self.std(), 4),
            "min": round(self.values[0], 4) if self.values else 0.0,
            "q10": round(q[0.1], 4),
            "q25": round(q[0.25], 4),
            "median": round(q[0.5], 4),
            "q75": round(q[0.75], 4),
            "q90": round(q[0.9], 4),
            "q99": round(q[0.99], 4),
            "max": round(self.values[-1], 4) if self.values else 0.0,
        }


class CascadeEvent:
    """
    Capture les données complètes d'une cascade de faillites.
    L'unité de mesure principale est le joule (volume), pas le nombre d'entités.
    """

    def __init__(self, step: int):
        self.step = step

        # Volume en joules
        self.volume_actifs_detruits: float = 0.0    # actifs totaux des faillis
        self.volume_creances_annulees: float = 0.0  # nominal des prêts annulés
        self.volume_passif_efface: float = 0.0      # passif total des faillis

        # Structure
        self.nb_entites_faillie: int = 0
        self.taille_entites_faillie: List[float] = []  # passif_total de chaque failli

        # Contexte système avant la cascade
        self.actif_systeme_avant: float = 0.0
        self.passif_systeme_avant: float = 0.0
        self.liquidite_systeme_avant: float = 0.0
        self.nb_entites_avant: int = 0

        # Contagion
        self.nb_contamines: int = 0       # faillis qui étaient solvables avant la cascade
        self.nb_deja_fragiles: int = 0    # faillis déjà insolvables avant la cascade

    @property
    def ratio_destruction(self) -> float:
        """Volume détruit / actif total système avant cascade."""
        if self.actif_systeme_avant <= 0:
            return 0.0
        return self.volume_actifs_detruits / self.actif_systeme_avant

    @property
    def ratio_contagion(self) -> float:
        """Part des faillis qui étaient solvables avant la cascade."""
        if self.nb_entites_faillie == 0:
            return 0.0
        return self.nb_contamines / self.nb_entites_faillie

    def to_dict(self) -> dict:
        median_size = 0.0
        if self.taille_entites_faillie:
            s = sorted(self.taille_entites_faillie)
            median_size = s[len(s) // 2]
        return {
            "step": self.step,
            "nb_entites_faillie": self.nb_entites_faillie,
            "volume_actifs_detruits": round(self.volume_actifs_detruits, 4),
            "volume_creances_annulees": round(self.volume_creances_annulees, 4),
            "volume_passif_efface": round(self.volume_passif_efface, 4),
            "actif_systeme_avant": round(self.actif_systeme_avant, 4),
            "passif_systeme_avant": round(self.passif_systeme_avant, 4),
            "liquidite_systeme_avant": round(self.liquidite_systeme_avant, 4),
            "nb_entites_avant": self.nb_entites_avant,
            "ratio_destruction": round(self.ratio_destruction, 6),
            "ratio_contagion": round(self.ratio_contagion, 4),
            "nb_contamines": self.nb_contamines,
            "nb_deja_fragiles": self.nb_deja_fragiles,
            "passif_median_failli": round(median_size, 4),
        }


class SystemicIndicator:
    """
    Indicateurs agrégés du système à un instant donné.
    Permettent de suivre l'évolution macroscopique et de détecter les précurseurs.
    """

    def __init__(self, step: int):
        self.step = step

        # Stocks
        self.actif_total: float = 0.0
        self.passif_total: float = 0.0
        self.liquidite_totale: float = 0.0
        self.volume_prets: float = 0.0
        self.nb_entites: int = 0
        self.nb_prets: int = 0
        self.nb_masses_faillite: int = 0

        # Dérivés
        self.levier_systeme: float = 0.0       # P_total / A_total
        self.ratio_liquidite: float = 0.0      # L_total / P_total
        self.densite_financiere: float = 0.0   # volume_prets / actif_total
        self.concentration_prets: float = 0.0  # Herfindahl sur nominaux (0=dispersé, 1=monopole)

        # Faillites de ce pas
        self.nb_faillites: int = 0
        self.volume_faillites: float = 0.0

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "nb_entites": self.nb_entites,
            "nb_prets": self.nb_prets,
            "nb_masses_faillite": self.nb_masses_faillite,
            "actif_total": round(self.actif_total, 4),
            "passif_total": round(self.passif_total, 4),
            "liquidite_totale": round(self.liquidite_totale, 4),
            "volume_prets": round(self.volume_prets, 4),
            "levier_systeme": round(self.levier_systeme, 6),
            "ratio_liquidite": round(self.ratio_liquidite, 6),
            "densite_financiere": round(self.densite_financiere, 6),
            "concentration_prets": round(self.concentration_prets, 6),
            "nb_faillites": self.nb_faillites,
            "volume_faillites": round(self.volume_faillites, 4),
        }


# ============================================================
#  COLLECTEUR PRINCIPAL
# ============================================================

class Collector:
    """
    Agrège toutes les données statistiques pendant la simulation.

    Usage depuis la Simulation :
        collector = Collector(freq_snapshot=10)
        # dans chaque pas :
        collector.record_step(sim, cascade_event_optionnel)

    Aucune dépendance circulaire : le collecteur lit les attributs publics
    des objets Entity et Loan, sans rien modifier.
    """

    def __init__(self, freq_snapshot: int = 10):
        self.freq_snapshot = freq_snapshot

        # Snapshots de distributions
        self.snapshots: List[SnapshotDistribution] = []

        # Cascades (une entrée par pas avec au moins une faillite)
        self.cascades: List[CascadeEvent] = []

        # Indicateurs systémiques (un par pas)
        self.indicators: List[SystemicIndicator] = []

        # Distributions brutes par grandeur : {nom: [(step, [valeurs]), ...]}
        self.raw_distributions: Dict[str, List[tuple]] = {
            "passif_total": [],
            "actif_liquide": [],
            "actif_total": [],
            "ratio_L_P": [],
            "taux_interne": [],
            "levier_entite": [],
        }

        # Entity watching
        self.watched_entity_ids: set = set()
        self._accumulated_flows: dict = {}   # eid -> {extraction, interest_received, interest_paid, depreciation}
        self.entity_records: dict = {}       # eid -> list of record dicts

    def register_entity(self, entity_id: int):
        self.watched_entity_ids.add(entity_id)
        self.entity_records[entity_id] = []
        self._accumulated_flows[entity_id] = {
            'extraction': 0.0, 'interest_received': 0.0,
            'interest_paid': 0.0, 'depreciation': 0.0,
        }

    # --------------------------------------------------------
    #  POINT D'ENTRÉE PRINCIPAL
    # --------------------------------------------------------

    def record_step(self, sim, cascade_event: Optional[CascadeEvent] = None, entity_flows=None):
        """
        À appeler à la fin de chaque pas de simulation.
        sim : objet Simulation (attributs publics lus en lecture seule)
        cascade_event : CascadeEvent si des faillites ont eu lieu ce pas.
        """
        step = sim.current_step
        alive = sim.active_entities()
        active_loans = sim.active_loans()
        n_estates = sum(1 for e in sim.estates.values() if e.active)
        alpha = sim.config.alpha

        # 1. Indicateurs systémiques (chaque pas)
        ind = self._compute_indicators(step, alive, active_loans, n_estates)
        if cascade_event is not None:
            ind.nb_faillites = cascade_event.nb_entites_faillie
            ind.volume_faillites = cascade_event.volume_actifs_detruits
        self.indicators.append(ind)

        # Accumulate entity flows
        if entity_flows:
            for eid in self.watched_entity_ids:
                flows = entity_flows.get(eid, {})
                acc = self._accumulated_flows.setdefault(eid, {
                    'extraction': 0.0, 'interest_received': 0.0,
                    'interest_paid': 0.0, 'depreciation': 0.0,
                })
                for k in ('extraction', 'interest_received', 'interest_paid', 'depreciation'):
                    acc[k] += flows.get(k, 0.0)

        # 2. Snapshots de distributions (freq_snapshot)
        if step % self.freq_snapshot == 0:
            self._take_snapshot(step, alive, alpha)
            self._record_entity_snapshots(step, sim)

        # 3. Cascade
        if cascade_event is not None and cascade_event.nb_entites_faillie > 0:
            self.cascades.append(cascade_event)

    # --------------------------------------------------------
    #  INDICATEURS SYSTÉMIQUES
    # --------------------------------------------------------

    def _compute_indicators(self, step, alive, active_loans, n_estates) -> SystemicIndicator:
        ind = SystemicIndicator(step)
        ind.nb_entites = len(alive)
        ind.nb_prets = len(active_loans)
        ind.nb_masses_faillite = n_estates

        if alive:
            ind.actif_total = sum(e.actif_total for e in alive)
            ind.passif_total = sum(e.passif_total for e in alive)
            ind.liquidite_totale = sum(e.actif_liquide for e in alive)

        if active_loans:
            ind.volume_prets = sum(loan.principal for loan in active_loans)

        if ind.actif_total > 0:
            ind.levier_systeme = ind.passif_total / ind.actif_total
        if ind.passif_total > 0:
            ind.ratio_liquidite = ind.liquidite_totale / ind.passif_total
        if ind.actif_total > 0:
            ind.densite_financiere = ind.volume_prets / ind.actif_total
        if ind.volume_prets > 0:
            parts = [loan.principal / ind.volume_prets for loan in active_loans]
            ind.concentration_prets = sum(x * x for x in parts)

        return ind

    # --------------------------------------------------------
    #  SNAPSHOTS DE DISTRIBUTIONS
    # --------------------------------------------------------

    def _take_snapshot(self, step: int, alive, alpha: float):
        if not alive:
            return

        grandeurs = {
            "passif_total":  [e.passif_total for e in alive],
            "actif_liquide": [e.actif_liquide for e in alive],
            "actif_total":   [e.actif_total for e in alive],
            "ratio_L_P":     [
                e.actif_liquide / e.passif_total if e.passif_total > 0 else 0.0
                for e in alive
            ],
            "taux_interne":  [
                alpha / (2.0 * math.sqrt(e.passif_total))
                for e in alive if e.passif_total > 0
            ],
            "levier_entite": [
                e.passif_total / e.actif_total if e.actif_total > 0 else float("inf")
                for e in alive
            ],
        }

        for name, values in grandeurs.items():
            finite_values = [v for v in values if math.isfinite(v)]
            if finite_values:
                snap = SnapshotDistribution(step, name, finite_values)
                self.snapshots.append(snap)
                self.raw_distributions[name].append((step, finite_values))

    def _record_entity_snapshots(self, step: int, sim):
        for eid in self.watched_entity_ids:
            entity = sim.entities.get(eid)
            if entity is None:
                continue
            acc = self._accumulated_flows.get(eid, {})
            record = {
                'entity_id': eid,
                'step': step,
                'alive': int(entity.alive),
                'creation_step': entity.creation_step,
                'actif_liquide': round(entity.actif_liquide, 6),
                'actif_prete': round(entity.actif_prete, 6),
                'actif_endoinvesti': round(entity.actif_endoinvesti, 6),
                'actif_exoinvesti': round(entity.actif_exoinvesti, 6),
                'actif_total': round(entity.actif_total, 6),
                'passif_inne': round(entity.passif_inne, 6),
                'passif_endoinvesti': round(entity.passif_endoinvesti, 6),
                'passif_exoinvesti': round(entity.passif_exoinvesti, 6),
                'passif_total': round(entity.passif_total, 6),
                'extraction': round(acc.get('extraction', 0.0), 6),
                'interest_received': round(acc.get('interest_received', 0.0), 6),
                'interest_paid': round(acc.get('interest_paid', 0.0), 6),
                'depreciation': round(acc.get('depreciation', 0.0), 6),
            }
            self.entity_records[eid].append(record)
            # Reset accumulated flows
            self._accumulated_flows[eid] = {
                'extraction': 0.0, 'interest_received': 0.0,
                'interest_paid': 0.0, 'depreciation': 0.0,
            }

    # --------------------------------------------------------
    #  CONSTRUCTION D'UN ÉVÉNEMENT CASCADE
    # --------------------------------------------------------

    @staticmethod
    def build_cascade(
        step: int,
        state_before: dict,
        faillis_info: list,
        creances_annulees: float,
    ) -> CascadeEvent:
        """
        Construit un CascadeEvent à partir des informations collectées
        avant et pendant la résolution.

        state_before : dict {actif_total, passif_total, liquidite, nb_entites}
                       capturé AVANT la résolution des faillites.
        faillis_info : liste de dicts {actif_total, passif_total, etait_solvable}
                       pour chaque entité ayant fait faillite.
        creances_annulees : nominal total des prêts annulés lors de la cascade.
        """
        ev = CascadeEvent(step)
        ev.actif_systeme_avant = state_before["actif_total"]
        ev.passif_systeme_avant = state_before["passif_total"]
        ev.liquidite_systeme_avant = state_before["liquidite"]
        ev.nb_entites_avant = state_before["nb_entites"]
        ev.volume_creances_annulees = creances_annulees

        for info in faillis_info:
            ev.nb_entites_faillie += 1
            ev.volume_actifs_detruits += info["actif_total"]
            ev.volume_passif_efface += info["passif_total"]
            ev.taille_entites_faillie.append(info["passif_total"])
            if info["etait_solvable"]:
                ev.nb_contamines += 1
            else:
                ev.nb_deja_fragiles += 1

        return ev

    # --------------------------------------------------------
    #  EXPORT CSV
    # --------------------------------------------------------

    def export_all(self, folder: str, entities: dict = None):
        """Exporte tous les jeux de données dans le dossier indiqué."""
        import csv
        os.makedirs(folder, exist_ok=True)

        # 1. Indicateurs systémiques
        self._write_csv(
            os.path.join(folder, "indicateurs_systemiques.csv"),
            [i.to_dict() for i in self.indicators],
            "Indicateurs agrégés du système à chaque pas",
        )

        # 2. Snapshots de distributions (résumé statistique)
        self._write_csv(
            os.path.join(folder, "snapshots_distributions.csv"),
            [s.to_dict() for s in self.snapshots],
            "Statistiques résumées des distributions par grandeur et par pas",
        )

        # 3. Cascades de faillites
        if self.cascades:
            self._write_csv(
                os.path.join(folder, "cascades_faillites.csv"),
                [c.to_dict() for c in self.cascades],
                "Données détaillées de chaque cascade de faillites",
            )

        # 4. Distributions brutes
        for name, series in self.raw_distributions.items():
            if not series:
                continue
            path = os.path.join(folder, f"distrib_brute_{name}.csv")
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["step", "value"])
                for (step, values) in series:
                    for v in values:
                        w.writerow([step, round(v, 6)])

        # 5. Tailles brutes des cascades (pour analyse loi de puissance)
        if self.cascades:
            path = os.path.join(folder, "tailles_cascades_brutes.csv")
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["step", "volume_joules", "nb_entites", "ratio_destruction"])
                for c in self.cascades:
                    w.writerow([
                        c.step,
                        round(c.volume_actifs_detruits, 4),
                        c.nb_entites_faillie,
                        round(c.ratio_destruction, 6),
                    ])

        # 6. Entity histories
        if self.entity_records:
            all_records = []
            for eid in sorted(self.entity_records.keys()):
                all_records.extend(self.entity_records[eid])
            if all_records:
                self._write_csv(
                    os.path.join(folder, "entity_histories.csv"),
                    all_records,
                    "Historiques d'entités surveillées (snapshots toutes les freq_snapshot étapes)",
                )
                print(f"  → {len(all_records)} enregistrements d'historiques d'entités")

            # Entity meta
            if entities:
                meta_rows = []
                for eid in sorted(self.entity_records.keys()):
                    entity = entities.get(eid)
                    if entity:
                        meta_rows.append({
                            'entity_id': eid,
                            'creation_step': entity.creation_step,
                            'death_step': getattr(entity, 'death_step', None),
                            'still_alive': int(entity.alive),
                            'n_records': len(self.entity_records[eid]),
                        })
                if meta_rows:
                    self._write_csv(
                        os.path.join(folder, "entity_meta.csv"),
                        meta_rows,
                        "Métadonnées des entités surveillées",
                    )

        print(f"  → {len(self.indicators)} indicateurs systémiques")
        print(f"  → {len(self.snapshots)} snapshots de distribution")
        print(f"  → {len(self.cascades)} événements de cascade")

    @staticmethod
    def _write_csv(path: str, rows: list, comment: str = ""):
        import csv
        if not rows:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            if comment:
                f.write(f"# {comment}\n")
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
