"""
simulation.py — Simulation multi-agents d'un système autocritique de prêts, investissements et faillites.

Architecture :
  - Entite       : bilan comptable d'un agent
  - Pret         : contrat de prêt entre deux agents
  - MasseFaillite: portefeuille redistribué après faillite
  - Simulation   : moteur principal, un pas de temps, statistiques

Toutes les règles sont documentées en ligne et référencent la note de modélisation.
"""

import random
import math
import csv
import copy
from typing import List, Dict, Optional, Tuple

from statistiques import Collecteur, EvenementCascade


# ============================================================
#  PARAMÈTRES GLOBAUX
#  (centraliser ici pour modification facile)
# ============================================================

PARAMS = {
    # Productivité (formule extraction : alpha * sqrt(P))
    "alpha": 1.0,

    # Seuil de liquidité relative pour agir sur le marché (L/P > s)
    "seuil_ratio_liquide_passif": 0.05,

    # Fraction de la demande maximale effectivement demandée
    "theta": 0.5,

    # Marge minimale relative pour accepter un emprunt vs auto-investissement
    "mu": 0.05,

    # Taux de Poisson pour l'arrivée de nouvelles entités par pas
    "lambda_creation": 0.5,

    # Dotation initiale de chaque nouvelle entité
    "actif_liquide_initial": 10.0,
    "passif_inne_initial": 5.0,

    # Taux de dépréciation
    "taux_depreciation_liquide": 0.02,
    "taux_depreciation_endo": 0.03,
    "taux_depreciation_exo": 0.03,

    # Rendement de reliquéfaction (fraction récupérée lors de la destruction endo)
    "coefficient_reliquefaction": 0.5,

    # Taux d'intérêt proposé par le prêteur (basé sur son taux interne)
    "spread_taux_preteur": 0.0,  # le prêteur propose son propre r* (sans marge par défaut)

    # Fraction de l'actif liquide auto-investie en fin de tour
    "fraction_auto_investissement": 0.3,

    # Durée de la simulation
    "nb_pas": 200,

    # Graine aléatoire (None = aléatoire)
    "graine": 42,
}


# ============================================================
#  ENTITÉ
# ============================================================

class Entite:
    """
    Bilan comptable d'un agent.

    Actifs  : liquide, prêté, endo-investi, exo-investi
    Passifs : inné, endo-investi, exo-investi
    """

    _compteur = 0  # compteur global d'identifiants

    def __init__(self, actif_liquide: float, passif_inne: float, pas_creation: int = 0):
        Entite._compteur += 1
        self.id = Entite._compteur
        self.vivante = True
        self.pas_creation = pas_creation

        # --- Actifs ---
        self.actif_liquide: float = actif_liquide
        self.actif_prete: float = 0.0          # nominal des créances détenues
        self.actif_endoinvesti: float = 0.0
        self.actif_exoinvesti: float = 0.0

        # --- Passifs ---
        self.passif_inne: float = passif_inne
        self.passif_endoinvesti: float = 0.0
        self.passif_exoinvesti: float = 0.0

    # --- Grandeurs dérivées ---

    @property
    def actif_total(self) -> float:
        return self.actif_liquide + self.actif_prete + self.actif_endoinvesti + self.actif_exoinvesti

    @property
    def passif_total(self) -> float:
        return self.passif_inne + self.passif_endoinvesti + self.passif_exoinvesti

    def taux_interne(self, alpha: float) -> float:
        """r* = alpha / (2 * sqrt(P))  — note §11"""
        P = self.passif_total
        if P <= 0:
            return float('inf')
        return alpha / (2.0 * math.sqrt(P))

    def est_active(self, seuil: float) -> bool:
        """L/P > seuil — note §9"""
        P = self.passif_total
        if P <= 0:
            return False
        return (self.actif_liquide / P) > seuil

    def est_insolvable(self) -> bool:
        """A < P — note §10"""
        return self.actif_total < self.passif_total

    def __repr__(self):
        return (f"Entite#{self.id}(L={self.actif_liquide:.2f}, "
                f"P={self.passif_total:.2f}, "
                f"solvable={'oui' if not self.est_insolvable() else 'NON'})")


# ============================================================
#  PRÊT
# ============================================================

class Pret:
    """
    Contrat de prêt entre prêteur et emprunteur.
    Peut être scindé (divisibilité — note §16.3).
    """

    _compteur = 0

    def __init__(self, preteur: Entite, emprunteur: Entite, principal: float, taux: float):
        Pret._compteur += 1
        self.id = Pret._compteur
        self.preteur: Entite = preteur          # peut être None si entité faillie (masse)
        self.emprunteur: Entite = emprunteur
        self.principal: float = principal
        self.taux: float = taux
        self.actif: bool = True

    def interet_du(self) -> float:
        """Montant d'intérêt dû à ce pas (I = r * q)"""
        return self.taux * self.principal

    def scinder(self, montant_cede: float) -> "Pret":
        """
        Scinde ce prêt en deux.
        Ce prêt conserve (principal - montant_cede).
        Renvoie le nouveau prêt de montant montant_cede (même taux, même emprunteur).
        Le prêteur du nouveau prêt est fixé par l'appelant.
        """
        assert 0 < montant_cede < self.principal, "montant_cede hors bornes"
        nouveau = Pret(self.preteur, self.emprunteur, montant_cede, self.taux)
        self.principal -= montant_cede
        return nouveau

    def __repr__(self):
        pid = self.preteur.id if self.preteur else "MASSE"
        return (f"Pret#{self.id}(preteur={pid}, "
                f"emprunteur={self.emprunteur.id}, "
                f"q={self.principal:.2f}, r={self.taux:.4f})")


# ============================================================
#  MASSE DE FAILLITE
# ============================================================

class MasseFaillite:
    """
    Après la faillite d'une entité, ses prêts sont hérités par cette masse.
    Les flux entrants futurs sont redistribués aux créanciers au prorata — note §17.
    """

    def __init__(self, entite_faillie: Entite, prets_detenus: List[Pret],
                 creanciers: List[Entite], montants_creances: List[float]):
        self.entite_id = entite_faillie.id

        # Prêts dont les flux reviendront à la masse
        self.prets: List[Pret] = prets_detenus

        # Poids de redistribution (figés à la date de faillite)
        total = sum(montants_creances)
        if total > 0:
            self.poids: Dict[int, float] = {
                c.id: m / total
                for c, m in zip(creanciers, montants_creances)
            }
        else:
            self.poids = {}

        self.creanciers: Dict[int, Entite] = {c.id: c for c in creanciers}

    def redistribuer(self, flux: float):
        """Distribue un flux entrant aux créanciers au prorata."""
        for cid, poids in self.poids.items():
            if cid in self.creanciers:
                beneficiaire = self.creanciers[cid]
                if beneficiaire.vivante:
                    beneficiaire.actif_liquide += poids * flux

    def __repr__(self):
        return f"MasseFaillite(entite_faillie={self.entite_id}, nb_prets={len(self.prets)})"


# ============================================================
#  SIMULATION
# ============================================================

class Simulation:
    """
    Moteur de simulation.
    Orchestre les entités, prêts, masses de faillite et statistiques.
    """

    def __init__(self, params: dict = None, freq_snapshot: int = 10):
        self.p = params or PARAMS
        if self.p.get("graine") is not None:
            random.seed(self.p["graine"])

        self.entites: List[Entite] = []
        self.prets: List[Pret] = []
        self.masses_faillite: List[MasseFaillite] = []
        self.pas_courant: int = 0

        # Statistiques légères par pas (rétrocompatibilité)
        self.stats: List[dict] = []

        # Collecteur statistique riche (distributions, cascades, indicateurs)
        self.collecteur = Collecteur(freq_snapshot=freq_snapshot)

        # Réinitialiser les compteurs de classes
        Entite._compteur = 0
        Pret._compteur = 0

        # Créer quelques entités initiales
        self._initialiser()

    def _initialiser(self):
        """Crée un groupe initial d'entités."""
        n_init = 10
        for _ in range(n_init):
            self._creer_entite()

    def _creer_entite(self) -> Entite:
        """Crée une nouvelle entité avec la dotation paramétrique."""
        e = Entite(
            actif_liquide=self.p["actif_liquide_initial"],
            passif_inne=self.p["passif_inne_initial"],
            pas_creation=self.pas_courant
        )
        self.entites.append(e)
        return e

    # --------------------------------------------------------
    #  PAS DE SIMULATION
    # --------------------------------------------------------

    def pas(self):
        """
        Exécute un pas de simulation.
        Ordre défini dans la note §19.
        """
        self.pas_courant += 1

        # 1. Création de nouvelles entités (Poisson)
        self._etape_creation()

        # 2. Extraction depuis la nature
        self._etape_extraction()

        # 3. Paiement des intérêts
        self._etape_interets()

        # 4. Gestion de l'illiquidité
        self._etape_illiquidite()

        # 5. Dépréciation des stocks
        self._etape_depreciation()

        # 6 & 7. Marché du crédit (sélection + itérations)
        self._etape_marche_credit()

        # 8. Auto-investissement de fin de tour
        self._etape_auto_investissement()

        # Capturer l'état système AVANT les faillites (pour les cascades)
        etat_avant = self._capturer_etat_systeme()

        # 9 & 10. Test de faillite + cascades
        cascade_ev, nb_faillites, actifs_detruits, creances_annulees = self._etape_faillites(etat_avant)

        # 11. Enregistrement des statistiques légères (rétrocompatibilité)
        self._enregistrer_stats(nb_faillites, actifs_detruits, creances_annulees)

        # 11b. Collecteur statistique riche
        self.collecteur.enregistrer_pas(self, cascade_ev)

    # --------------------------------------------------------
    #  ÉTAPE 1 — Création
    # --------------------------------------------------------

    def _etape_creation(self):
        """Crée des entités selon Poisson(lambda)."""
        n = _poisson(self.p["lambda_creation"])
        for _ in range(n):
            self._creer_entite()

    # --------------------------------------------------------
    #  ÉTAPE 2 — Extraction
    # --------------------------------------------------------

    def _etape_extraction(self):
        """Pi = alpha * sqrt(P) ajouté au liquide — note §4"""
        alpha = self.p["alpha"]
        for e in self.entites:
            if not e.vivante:
                continue
            P = e.passif_total
            if P > 0:
                extraction = alpha * math.sqrt(P)
                e.actif_liquide += extraction

    # --------------------------------------------------------
    #  ÉTAPE 3 — Paiement des intérêts
    # --------------------------------------------------------

    def _etape_interets(self):
        """
        Pour chaque prêt actif :
          emprunteur paie r*q au prêteur (ou à la masse).
        Enregistre les paiements en souffrance pour l'étape suivante.
        """
        for pret in self.prets:
            if not pret.actif:
                continue
            emprunteur = pret.emprunteur
            if not emprunteur.vivante:
                continue

            interet = pret.interet_du()
            paiement = min(interet, emprunteur.actif_liquide)
            emprunteur.actif_liquide -= paiement

            # Créditer le prêteur ou redistribuer via masse
            self._crediter_preteur(pret, paiement)

            # Marquer la dette résiduelle (utilisée à l'étape illiquidité)
            pret._dette_residuelle = interet - paiement

    def _crediter_preteur(self, pret: Pret, montant: float):
        """Crédite le prêteur ou redistribue via la masse de faillite."""
        if pret.preteur is None:
            # Trouver la masse de faillite correspondante
            for masse in self.masses_faillite:
                if pret in masse.prets:
                    masse.redistribuer(montant)
                    return
        elif pret.preteur.vivante:
            pret.preteur.actif_liquide += montant

    # --------------------------------------------------------
    #  ÉTAPE 4 — Gestion de l'illiquidité
    # --------------------------------------------------------

    def _etape_illiquidite(self):
        """
        Traite les dettes résiduelles après le paiement initial.
        Procédure : liquide → cession de créances → reliquéfaction endo — note §16.
        """
        for pret in self.prets:
            if not pret.actif:
                continue
            dette = getattr(pret, '_dette_residuelle', 0.0)
            if dette <= 1e-12:
                continue

            emprunteur = pret.emprunteur
            if not emprunteur.vivante:
                continue

            creancier = pret.preteur  # peut être None (masse)

            # 16.1 : utiliser le liquide restant
            paiement = min(dette, emprunteur.actif_liquide)
            emprunteur.actif_liquide -= paiement
            dette -= paiement
            if creancier and creancier.vivante:
                creancier.actif_liquide += paiement
            elif creancier is None:
                self._redistribuer_masse(pret, paiement)

            if dette <= 1e-12:
                pret._dette_residuelle = 0.0
                continue

            # 16.2 : cession de créances (les moins rémunératrices en premier)
            if creancier is not None and creancier.vivante:
                dette = self._ceder_creances(emprunteur, creancier, dette)

            if dette <= 1e-12:
                pret._dette_residuelle = 0.0
                continue

            # 16.3 : reliquéfaction de l'endo-investi
            dette = self._reliquefier_endo(emprunteur, creancier, dette)

            pret._dette_residuelle = max(0.0, dette)

    def _ceder_creances(self, emprunteur: Entite, creancier: Entite, dette: float) -> float:
        """
        Cède des créances d'emprunteur à creancier pour réduire la dette.
        Priorité : créances à plus faible taux.
        Retourne la dette résiduelle après cession.
        """
        # Prêts dont emprunteur est le prêteur, triés par taux croissant
        mes_prets = sorted(
            [p for p in self.prets if p.actif and p.preteur is emprunteur],
            key=lambda p: p.taux
        )

        for p in mes_prets:
            if dette <= 1e-12:
                break
            if p.principal <= dette:
                # Cession totale
                montant_cede = p.principal
                # Mise à jour des bilans
                emprunteur.actif_prete -= montant_cede
                creancier.actif_prete += montant_cede
                # Transfert du prêt
                p.preteur = creancier
                dette -= montant_cede
            else:
                # Cession partielle — scission du prêt
                nouveau_pret = p.scinder(dette)
                nouveau_pret.preteur = creancier
                # Mise à jour des bilans
                emprunteur.actif_prete -= dette
                creancier.actif_prete += dette
                self.prets.append(nouveau_pret)
                dette = 0.0

        return dette

    def _reliquefier_endo(self, emprunteur: Entite, creancier: Optional[Entite], dette: float) -> float:
        """
        Détruit du stock endo-investi pour générer du liquide.
        c = coefficient_reliquefaction — note §16.4.
        """
        c = self.p["coefficient_reliquefaction"]
        disponible = emprunteur.actif_endoinvesti

        # Montant à détruire pour couvrir la dette : c*y = dette → y = dette/c
        if c > 0:
            y_necessaire = dette / c
        else:
            return dette  # impossible

        y = min(y_necessaire, disponible)
        liquide_genere = c * y

        emprunteur.actif_endoinvesti -= y
        emprunteur.passif_endoinvesti -= y
        emprunteur.actif_liquide += liquide_genere  # temporaire, sera payé ci-dessous

        paiement = min(liquide_genere, dette)
        emprunteur.actif_liquide -= paiement

        if creancier and creancier.vivante:
            creancier.actif_liquide += paiement
        elif creancier is None:
            self._redistribuer_masse_par_preteur(emprunteur, paiement)

        return dette - paiement

    def _redistribuer_masse(self, pret: Pret, montant: float):
        for masse in self.masses_faillite:
            if pret in masse.prets:
                masse.redistribuer(montant)
                return

    def _redistribuer_masse_par_preteur(self, preteur_fantome: Entite, montant: float):
        """Redistribue quand on ne peut pas identifier le prêt précis."""
        # Simplification : redistribue à la première masse liée à cet emprunteur
        for masse in self.masses_faillite:
            if masse.entite_id == preteur_fantome.id:
                masse.redistribuer(montant)
                return

    # --------------------------------------------------------
    #  ÉTAPE 5 — Dépréciation
    # --------------------------------------------------------

    def _etape_depreciation(self):
        """Dépréciation des stocks — note §5"""
        dL = self.p["taux_depreciation_liquide"]
        de = self.p["taux_depreciation_endo"]
        dx = self.p["taux_depreciation_exo"]

        for e in self.entites:
            if not e.vivante:
                continue
            e.actif_liquide *= (1 - dL)
            delta_endo = de * e.actif_endoinvesti
            e.actif_endoinvesti -= delta_endo
            e.passif_endoinvesti -= delta_endo
            delta_exo = dx * e.actif_exoinvesti
            e.actif_exoinvesti -= delta_exo
            e.passif_exoinvesti -= delta_exo

        # Dépréciation des prêts : actif_prete reflète les nominaux des prêts détenus
        # On met à jour actif_prete à partir des prêts réels pour garder la cohérence.
        self._recalculer_actif_prete()

    def _recalculer_actif_prete(self):
        """Recalcule actif_prete de chaque entité vivante depuis la liste des prêts."""
        for e in self.entites:
            if e.vivante:
                e.actif_prete = 0.0
        for p in self.prets:
            if p.actif and p.preteur and p.preteur.vivante:
                p.preteur.actif_prete += p.principal

    # --------------------------------------------------------
    #  ÉTAPE 6 & 7 — Marché du crédit
    # --------------------------------------------------------

    def _etape_marche_credit(self):
        """
        Appariement itératif prêteur/emprunteur — note §15.
        Après chaque transaction, recalcul des taux.
        Arrêt si aucun emprunt accepté.
        """
        alpha = self.p["alpha"]
        seuil = self.p["seuil_ratio_liquide_passif"]

        iterations = 0
        max_iter = 1000  # garde-fou

        while iterations < max_iter:
            iterations += 1

            # Entités actives
            actives = [e for e in self.entites if e.vivante and e.est_active(seuil)]
            if len(actives) < 2:
                break

            # Trier par taux interne
            actives_triees = sorted(actives, key=lambda e: e.taux_interne(alpha))

            preteur = actives_triees[0]   # plus faible taux → prêteur
            emprunteur = actives_triees[-1]  # plus fort taux → emprunteur

            if preteur is emprunteur:
                break

            # Taux proposé par le prêteur (son taux interne + spread)
            taux_propose = preteur.taux_interne(alpha) + self.p["spread_taux_preteur"]

            # Offre du prêteur
            offre = max(0.0, preteur.actif_liquide - seuil * preteur.passif_total)
            if offre <= 1e-12:
                break

            # Demande de l'emprunteur
            demande = self._calculer_demande(emprunteur, taux_propose)
            if demande <= 1e-12:
                break

            montant = min(offre, demande)

            # Condition d'acceptation (emprunt vs auto-investissement) — note §14
            if not self._emprunt_acceptable(emprunteur, montant, taux_propose):
                break

            # Exécution de la transaction
            self._executer_pret(preteur, emprunteur, montant, taux_propose)

        # Si aucune itération productive n'a eu lieu, on sort simplement.

    def _calculer_demande(self, emprunteur: Entite, taux: float) -> float:
        """
        qmax = (alpha/(2r))^2 - P  — note §13
        qdem = theta * qmax
        """
        alpha = self.p["alpha"]
        theta = self.p["theta"]
        P = emprunteur.passif_total
        if taux <= 0:
            return 0.0
        qmax = (alpha / (2.0 * taux)) ** 2 - P
        if qmax <= 0:
            return 0.0
        return theta * qmax

    def _emprunt_acceptable(self, emprunteur: Entite, q: float, taux: float) -> bool:
        """
        Compare gain net sous emprunt vs gain sous auto-investissement — note §14.
        gain_emprunt / gain_auto >= 1 + mu
        """
        alpha = self.p["alpha"]
        mu = self.p["mu"]
        P = emprunteur.passif_total
        L = emprunteur.actif_liquide

        # Gain sous auto-investissement : extraction supplémentaire si on investit L
        gain_auto = alpha * math.sqrt(P + L) - alpha * math.sqrt(P)

        # Gain net sous emprunt : extraction supplémentaire - intérêts
        gain_emprunt_brut = alpha * math.sqrt(P + q) - alpha * math.sqrt(P)
        cout_interets = taux * q
        gain_emprunt_net = gain_emprunt_brut - cout_interets

        if gain_auto <= 1e-12:
            return gain_emprunt_net > 0

        return (gain_emprunt_net / gain_auto) >= (1.0 + mu)

    def _executer_pret(self, preteur: Entite, emprunteur: Entite, q: float, taux: float):
        """Réalise un prêt entre deux entités — note §7"""
        preteur.actif_liquide -= q
        preteur.actif_prete += q

        emprunteur.actif_exoinvesti += q
        emprunteur.passif_exoinvesti += q

        pret = Pret(preteur, emprunteur, q, taux)
        self.prets.append(pret)

    # --------------------------------------------------------
    #  ÉTAPE 8 — Auto-investissement
    # --------------------------------------------------------

    def _etape_auto_investissement(self):
        """
        Convertit une fraction de l'actif liquide en investissement endogène — note §6.
        """
        frac = self.p["fraction_auto_investissement"]
        for e in self.entites:
            if not e.vivante:
                continue
            x = frac * e.actif_liquide
            if x <= 0:
                continue
            e.actif_liquide -= x
            e.actif_endoinvesti += x
            e.passif_endoinvesti += x

    # --------------------------------------------------------
    #  ÉTAPE 9 & 10 — Faillites et cascades
    # --------------------------------------------------------

    def _capturer_etat_systeme(self) -> dict:
        """Capture un instantané de l'état du système pour les statistiques de cascade."""
        vivantes = [e for e in self.entites if e.vivante]
        return {
            "actif_total": sum(e.actif_total for e in vivantes),
            "passif_total": sum(e.passif_total for e in vivantes),
            "liquidite": sum(e.actif_liquide for e in vivantes),
            "nb_entites": len(vivantes),
        }

    def _etape_faillites(self, etat_avant: dict) -> Tuple[Optional[EvenementCascade], int, float, float]:
        """
        Détecte les faillites et résout les cascades.
        Retourne (cascade_event, nb_faillites, actifs_detruits, creances_annulees).
        etat_avant : snapshot système capturé avant cette étape.
        """
        nb_faillites = 0
        actifs_detruits = 0.0
        creances_annulees = 0.0
        faillis_info = []  # pour le collecteur

        # Marquer les entités solvables AVANT la cascade (pour détecter la contagion)
        solvables_avant = {e.id for e in self.entites if e.vivante and not e.est_insolvable()}

        # Résolution itérative des cascades
        changement = True
        while changement:
            changement = False
            for e in self.entites:
                if not e.vivante:
                    continue
                if e.est_insolvable():
                    # Enregistrer infos AVANT de tuer l'entité
                    faillis_info.append({
                        "actif_total": e.actif_total,
                        "passif_total": e.passif_total,
                        "etait_solvable": e.id in solvables_avant,
                    })
                    a, c = self._traiter_faillite(e)
                    nb_faillites += 1
                    actifs_detruits += a
                    creances_annulees += c
                    changement = True

        # Construire l'événement cascade si des faillites ont eu lieu
        cascade_ev = None
        if nb_faillites > 0:
            cascade_ev = Collecteur.construire_cascade(
                self.pas_courant, etat_avant, faillis_info, creances_annulees
            )

        return cascade_ev, nb_faillites, actifs_detruits, creances_annulees

    def _traiter_faillite(self, entite: Entite) -> Tuple[float, float]:
        """
        Traite la faillite d'une entité.
        - Annule les prêts dont elle est emprunteur (réduction actif des prêteurs)
        - Transfère ses prêts détenus à une masse de faillite
        - Retourne (actifs_detruits, creances_annulees)
        """
        actifs_detruits = entite.actif_total
        creances_annulees = 0.0

        # 1. Trouver les créanciers de l'entité faillie (elle est emprunteur)
        prets_emprunteur = [p for p in self.prets if p.actif and p.emprunteur is entite]
        creanciers = []
        montants_creances = []
        for p in prets_emprunteur:
            if p.preteur and p.preteur.vivante:
                creanciers.append(p.preteur)
                montants_creances.append(p.principal)
                # Réduire l'actif_prete du prêteur
                p.preteur.actif_prete -= p.principal
                creances_annulees += p.principal
            p.actif = False

        # Réduire actif_exoinvesti et passif_exoinvesti de l'entité
        # (déjà perdu dans la faillite, mais pour cohérence comptable)

        # 2. Prêts que l'entité détenait (elle est prêteuse)
        prets_preteur = [p for p in self.prets if p.actif and p.preteur is entite]

        if prets_preteur and creanciers:
            # Créer une masse de faillite
            masse = MasseFaillite(entite, prets_preteur, creanciers, montants_creances)
            self.masses_faillite.append(masse)
            # Détacher ces prêts de l'entité (preteur = None, géré via masse)
            for p in prets_preteur:
                p.preteur = None  # géré par la masse

        elif prets_preteur:
            # Pas de créancier : les prêts sont orphelins, on les désactive
            for p in prets_preteur:
                p.actif = False

        # 3. Marquer l'entité comme morte
        entite.vivante = False

        return actifs_detruits, creances_annulees

    # --------------------------------------------------------
    #  STATISTIQUES
    # --------------------------------------------------------

    def _enregistrer_stats(self, nb_faillites: int, actifs_detruits: float, creances_annulees: float):
        """Collecte les statistiques du pas courant."""
        vivantes = [e for e in self.entites if e.vivante]
        prets_actifs = [p for p in self.prets if p.actif]

        self.stats.append({
            "pas": self.pas_courant,
            "nb_entites_vivantes": len(vivantes),
            "nb_faillites": nb_faillites,
            "actifs_detruits": round(actifs_detruits, 4),
            "creances_annulees": round(creances_annulees, 4),
            "volume_prets_actifs": round(sum(p.principal for p in prets_actifs), 4),
            "nb_prets_actifs": len(prets_actifs),
            "actif_total_systeme": round(sum(e.actif_total for e in vivantes), 4),
            "passif_total_systeme": round(sum(e.passif_total for e in vivantes), 4),
            "liquidite_totale": round(sum(e.actif_liquide for e in vivantes), 4),
        })

    # --------------------------------------------------------
    #  EXÉCUTION COMPLÈTE
    # --------------------------------------------------------

    def run(self, verbose: bool = True) -> List[dict]:
        """Lance la simulation complète et retourne les statistiques."""
        nb_pas = self.p["nb_pas"]
        if verbose:
            print(f"Démarrage simulation : {nb_pas} pas, {len(self.entites)} entités initiales")

        for t in range(nb_pas):
            self.pas()
            if verbose and (t + 1) % 20 == 0:
                s = self.stats[-1]
                print(f"  Pas {t+1:4d} | Entités: {s['nb_entites_vivantes']:4d} | "
                      f"Faillites: {s['nb_faillites']:3d} | "
                      f"Prêts actifs: {s['nb_prets_actifs']:4d} | "
                      f"Vol. prêts: {s['volume_prets_actifs']:8.1f}")

        if verbose:
            print("Simulation terminée.")
        return self.stats

    def exporter_csv(self, chemin: str = "resultats.csv"):
        """Exporte les statistiques légères en CSV (rétrocompatibilité)."""
        if not self.stats:
            print("Aucune statistique à exporter.")
            return
        colonnes = list(self.stats[0].keys())
        with open(chemin, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=colonnes)
            writer.writeheader()
            writer.writerows(self.stats)
        print(f"Statistiques exportées : {chemin}")

    def exporter_stats_completes(self, dossier: str):
        """
        Exporte tous les jeux de données statistiques riches dans un dossier.
        Délègue au collecteur.
        """
        self.collecteur.exporter_tout(dossier)

    def resume(self) -> dict:
        """Retourne un résumé final de la simulation."""
        if not self.stats:
            return {}
        total_faillites = sum(s["nb_faillites"] for s in self.stats)
        max_cascade = max(s["nb_faillites"] for s in self.stats)
        return {
            "nb_pas_simules": self.pas_courant,
            "entites_creees_total": Entite._compteur,
            "entites_vivantes_final": self.stats[-1]["nb_entites_vivantes"],
            "faillites_total": total_faillites,
            "cascade_max": max_cascade,
            "prets_crees_total": Pret._compteur,
            "prets_actifs_final": self.stats[-1]["nb_prets_actifs"],
            "masses_faillite_creees": len(self.masses_faillite),
        }


# ============================================================
#  UTILITAIRES
# ============================================================

def _poisson(lam: float) -> int:
    """Génère un tirage selon une loi de Poisson(lam)."""
    if lam <= 0:
        return 0
    # Algorithme de Knuth
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p *= random.random()
    return k - 1
