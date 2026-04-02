"""
statistiques.py — Module de collecte et d'organisation des données statistiques.

Ce module est indépendant du moteur de simulation. Il collecte :

  1. Snapshots périodiques des distributions (taille des entités, liquidité, levier...)
  2. Données brutes des cascades de faillite (volume en joules, durée, contagion)
  3. Indicateurs systémiques dynamiques (levier agrégé, concentration, liquidité)
  4. Données fine par cascade pour l'analyse des précurseurs

Séparation des responsabilités :
  - La Simulation appelle collecteur.enregistrer_pas(sim, cascade_event)
  - Ce module stocke, structure, et sait exporter sans rien savoir du moteur.
"""

import math
import copy
from typing import List, Dict, Optional, Any


# ============================================================
#  STRUCTURES DE DONNÉES
# ============================================================

class SnapshotDistribution:
    """
    Capture la distribution d'une grandeur sur toutes les entités vivantes
    à un instant donné. Stocke les valeurs brutes (pas d'agrégation précoce).
    """
    def __init__(self, pas: int, nom: str, valeurs: List[float]):
        self.pas = pas
        self.nom = nom          # ex : "passif_total", "actif_liquide", "ratio_L_P"
        self.valeurs = sorted(valeurs)

    def quantiles(self, probs=(0.1, 0.25, 0.5, 0.75, 0.9, 0.99)):
        """Renvoie les quantiles demandés."""
        if not self.valeurs:
            return {p: 0.0 for p in probs}
        n = len(self.valeurs)
        result = {}
        for p in probs:
            idx = p * (n - 1)
            lo, hi = int(idx), min(int(idx) + 1, n - 1)
            result[p] = self.valeurs[lo] + (idx - lo) * (self.valeurs[hi] - self.valeurs[lo])
        return result

    def moyenne(self) -> float:
        if not self.valeurs:
            return 0.0
        return sum(self.valeurs) / len(self.valeurs)

    def ecart_type(self) -> float:
        if len(self.valeurs) < 2:
            return 0.0
        m = self.moyenne()
        return math.sqrt(sum((v - m) ** 2 for v in self.valeurs) / len(self.valeurs))

    def to_dict(self) -> dict:
        q = self.quantiles()
        return {
            "pas": self.pas,
            "nom": self.nom,
            "n": len(self.valeurs),
            "moyenne": round(self.moyenne(), 4),
            "ecart_type": round(self.ecart_type(), 4),
            "min": round(self.valeurs[0], 4) if self.valeurs else 0,
            "q10": round(q[0.1], 4),
            "q25": round(q[0.25], 4),
            "median": round(q[0.5], 4),
            "q75": round(q[0.75], 4),
            "q90": round(q[0.9], 4),
            "q99": round(q[0.99], 4),
            "max": round(self.valeurs[-1], 4) if self.valeurs else 0,
        }


class EvenementCascade:
    """
    Capture les données complètes d'une cascade de faillites.
    L'unité de mesure principale est le joule (volume), pas le nombre d'entités.
    """
    def __init__(self, pas: int):
        self.pas = pas

        # --- Volume en joules ---
        self.volume_actifs_detruits: float = 0.0    # somme des actifs_total des entités faillie
        self.volume_creances_annulees: float = 0.0  # nominal des prêts annulés
        self.volume_passif_efface: float = 0.0      # passif total des entités faillie

        # --- Structure de la cascade ---
        self.nb_entites_faillie: int = 0
        self.ids_faillis: List[int] = []
        self.taille_entites_faillie: List[float] = []  # passif_total de chaque entité faillie

        # --- Contexte système avant la cascade ---
        self.actif_systeme_avant: float = 0.0
        self.passif_systeme_avant: float = 0.0
        self.liquidite_systeme_avant: float = 0.0
        self.nb_entites_avant: int = 0

        # --- Contagion ---
        # Entités dont le bilan était sain (A >= P) avant la cascade
        # mais qui ont failli à cause de la propagation
        self.nb_contamines: int = 0         # faillis "sains" au départ de la cascade
        self.nb_deja_fragiles: int = 0      # faillis déjà insolvables au départ

    @property
    def ratio_destruction(self) -> float:
        """Volume détruit / actif total système avant cascade."""
        if self.actif_systeme_avant <= 0:
            return 0.0
        return self.volume_actifs_detruits / self.actif_systeme_avant

    @property
    def ratio_contagion(self) -> float:
        """Part des faillis qui étaient sains avant la cascade."""
        if self.nb_entites_faillie == 0:
            return 0.0
        return self.nb_contamines / self.nb_entites_faillie

    def to_dict(self) -> dict:
        return {
            "pas": self.pas,
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
            "passif_median_faille": round(
                sorted(self.taille_entites_faillie)[len(self.taille_entites_faillie)//2], 4
            ) if self.taille_entites_faillie else 0.0,
        }


class IndicateurSystemique:
    """
    Indicateurs agrégés du système à un instant donné.
    Permettent de suivre l'évolution macroscopique et de détecter les précurseurs.
    """
    def __init__(self, pas: int):
        self.pas = pas

        # Stock
        self.actif_total: float = 0.0
        self.passif_total: float = 0.0
        self.liquidite_totale: float = 0.0
        self.volume_prets: float = 0.0
        self.nb_entites: int = 0
        self.nb_prets: int = 0
        self.nb_masses_faillite: int = 0

        # Dérivés
        self.levier_systeme: float = 0.0        # P_total / A_total
        self.ratio_liquidite: float = 0.0       # L_total / P_total
        self.densite_financiere: float = 0.0    # volume_prets / actif_total
        self.concentration_prets: float = 0.0   # Herfindahl sur nominaux prêts (0=dispersé, 1=monopole)

        # Faillites de ce pas
        self.nb_faillites: int = 0
        self.volume_faillites: float = 0.0

    def to_dict(self) -> dict:
        return {
            "pas": self.pas,
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

class Collecteur:
    """
    Agrège toutes les données statistiques pendant la simulation.

    Usage depuis la Simulation :
        collecteur = Collecteur(freq_snapshot=5)
        # ... dans chaque pas :
        collecteur.enregistrer_pas(sim, cascade_event_optionnel)

    Aucune dépendance circulaire : le collecteur lit les attributs publics
    des objets Entite et Pret, sans rien modifier.
    """

    def __init__(self, freq_snapshot: int = 10):
        """
        freq_snapshot : fréquence en pas entre deux snapshots de distribution.
                        1 = chaque pas, 10 = tous les 10 pas, etc.
        """
        self.freq_snapshot = freq_snapshot

        # Snapshots de distributions (liste de SnapshotDistribution)
        self.snapshots: List[SnapshotDistribution] = []

        # Cascades (une entrée par pas où au moins une faillite s'est produite)
        self.cascades: List[EvenementCascade] = []

        # Indicateurs systémiques (un par pas)
        self.indicateurs: List[IndicateurSystemique] = []

        # Données brutes des distributions pour histogrammes évolutifs
        # Format : {nom_grandeur: [(pas, [valeurs]), ...]}
        self.distributions_brutes: Dict[str, List[tuple]] = {
            "passif_total": [],
            "actif_liquide": [],
            "actif_total": [],
            "ratio_L_P": [],
            "taux_interne": [],
            "levier_entite": [],  # P/A par entité
        }

    # --------------------------------------------------------
    #  POINT D'ENTRÉE PRINCIPAL
    # --------------------------------------------------------

    def enregistrer_pas(self, sim, cascade_event: Optional[EvenementCascade] = None):
        """
        À appeler à la fin de chaque pas de simulation.
        sim : objet Simulation (on lit ses attributs publics)
        cascade_event : EvenementCascade si des faillites ont eu lieu ce pas.
        """
        pas = sim.pas_courant
        vivantes = [e for e in sim.entites if e.vivante]
        prets_actifs = [p for p in sim.prets if p.actif]

        # 1. Indicateurs systémiques (chaque pas)
        ind = self._calculer_indicateurs(pas, vivantes, prets_actifs, sim.masses_faillite)
        if cascade_event:
            ind.nb_faillites = cascade_event.nb_entites_faillie
            ind.volume_faillites = cascade_event.volume_actifs_detruits
        self.indicateurs.append(ind)

        # 2. Snapshot de distributions (freq_snapshot)
        if pas % self.freq_snapshot == 0:
            self._prendre_snapshot(pas, vivantes, sim.p["alpha"])

        # 3. Cascade
        if cascade_event and cascade_event.nb_entites_faillie > 0:
            self.cascades.append(cascade_event)

    # --------------------------------------------------------
    #  CALCUL DES INDICATEURS SYSTÉMIQUES
    # --------------------------------------------------------

    def _calculer_indicateurs(self, pas, vivantes, prets_actifs, masses_faillite) -> IndicateurSystemique:
        ind = IndicateurSystemique(pas)
        ind.nb_entites = len(vivantes)
        ind.nb_prets = len(prets_actifs)
        ind.nb_masses_faillite = len(masses_faillite)

        if vivantes:
            ind.actif_total = sum(e.actif_total for e in vivantes)
            ind.passif_total = sum(e.passif_total for e in vivantes)
            ind.liquidite_totale = sum(e.actif_liquide for e in vivantes)

        if prets_actifs:
            ind.volume_prets = sum(p.principal for p in prets_actifs)

        # Levier système
        if ind.actif_total > 0:
            ind.levier_systeme = ind.passif_total / ind.actif_total

        # Ratio de liquidité
        if ind.passif_total > 0:
            ind.ratio_liquidite = ind.liquidite_totale / ind.passif_total

        # Densité financière
        if ind.actif_total > 0:
            ind.densite_financiere = ind.volume_prets / ind.actif_total

        # Concentration des prêts (Herfindahl)
        if prets_actifs and ind.volume_prets > 0:
            parts = [p.principal / ind.volume_prets for p in prets_actifs]
            ind.concentration_prets = sum(x * x for x in parts)

        return ind

    # --------------------------------------------------------
    #  SNAPSHOT DES DISTRIBUTIONS
    # --------------------------------------------------------

    def _prendre_snapshot(self, pas: int, vivantes, alpha: float):
        """Capture les distributions brutes et leurs statistiques résumées."""
        if not vivantes:
            return

        # Grandeurs à capturer
        grandeurs = {
            "passif_total":    [e.passif_total for e in vivantes],
            "actif_liquide":   [e.actif_liquide for e in vivantes],
            "actif_total":     [e.actif_total for e in vivantes],
            "ratio_L_P":       [e.actif_liquide / e.passif_total
                                 if e.passif_total > 0 else 0.0
                                 for e in vivantes],
            "taux_interne":    [e.taux_interne(alpha) for e in vivantes
                                 if e.passif_total > 0],
            "levier_entite":   [e.passif_total / e.actif_total
                                 if e.actif_total > 0 else float('inf')
                                 for e in vivantes],
        }

        for nom, valeurs in grandeurs.items():
            valeurs_finies = [v for v in valeurs if math.isfinite(v)]
            if valeurs_finies:
                snap = SnapshotDistribution(pas, nom, valeurs_finies)
                self.snapshots.append(snap)
                # Stocker aussi les valeurs brutes pour histogrammes
                self.distributions_brutes[nom].append((pas, valeurs_finies))

    # --------------------------------------------------------
    #  CONSTRUCTION D'UN ÉVÉNEMENT CASCADE
    # --------------------------------------------------------

    @staticmethod
    def construire_cascade(pas: int, sim_avant: dict, faillis_info: list,
                           creances_annulees: float) -> EvenementCascade:
        """
        Construit un EvenementCascade à partir des informations collectées
        avant et pendant la résolution.

        sim_avant : dict avec actif_total, passif_total, liquidite, nb_entites
                    capturé AVANT la résolution des faillites de ce pas
        faillis_info : liste de dicts {actif_total, passif_total, etait_solvable}
                       pour chaque entité ayant fait faillite
        """
        ev = EvenementCascade(pas)
        ev.actif_systeme_avant = sim_avant["actif_total"]
        ev.passif_systeme_avant = sim_avant["passif_total"]
        ev.liquidite_systeme_avant = sim_avant["liquidite"]
        ev.nb_entites_avant = sim_avant["nb_entites"]
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

    def exporter_tout(self, dossier: str):
        """Exporte tous les jeux de données dans le dossier indiqué."""
        import csv, os
        os.makedirs(dossier, exist_ok=True)

        # 1. Indicateurs systémiques (un par pas)
        self._ecrire_csv(
            os.path.join(dossier, "indicateurs_systemiques.csv"),
            [i.to_dict() for i in self.indicateurs],
            "Indicateurs agrégés du système à chaque pas"
        )

        # 2. Snapshots de distributions (résumé statistique)
        self._ecrire_csv(
            os.path.join(dossier, "snapshots_distributions.csv"),
            [s.to_dict() for s in self.snapshots],
            "Statistiques résumées des distributions par grandeur et par pas"
        )

        # 3. Cascades de faillites
        if self.cascades:
            self._ecrire_csv(
                os.path.join(dossier, "cascades_faillites.csv"),
                [c.to_dict() for c in self.cascades],
                "Données détaillées de chaque cascade de faillites"
            )

        # 4. Distributions brutes (valeurs individuelles par entité)
        #    Une ligne = une entité à un instant donné
        for nom_grandeur, serie in self.distributions_brutes.items():
            if not serie:
                continue
            chemin = os.path.join(dossier, f"distrib_brute_{nom_grandeur}.csv")
            with open(chemin, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["pas", "valeur"])
                for (pas, valeurs) in serie:
                    for v in valeurs:
                        w.writerow([pas, round(v, 6)])

        # 5. Tailles brutes des cascades (pour analyse loi de puissance)
        if self.cascades:
            chemin = os.path.join(dossier, "tailles_cascades_brutes.csv")
            with open(chemin, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["pas", "volume_joules", "nb_entites", "ratio_destruction"])
                for c in self.cascades:
                    w.writerow([c.pas,
                                 round(c.volume_actifs_detruits, 4),
                                 c.nb_entites_faillie,
                                 round(c.ratio_destruction, 6)])

        print(f"  → {len(self.indicateurs)} indicateurs systémiques")
        print(f"  → {len(self.snapshots)} snapshots de distribution")
        print(f"  → {len(self.cascades)} événements de cascade")

    @staticmethod
    def _ecrire_csv(chemin: str, lignes: list, commentaire: str = ""):
        """Écrit une liste de dicts en CSV."""
        import csv
        if not lignes:
            return
        with open(chemin, "w", newline="", encoding="utf-8") as f:
            if commentaire:
                f.write(f"# {commentaire}\n")
            w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
            w.writeheader()
            w.writerows(lignes)
