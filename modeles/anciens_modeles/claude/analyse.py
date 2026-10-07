"""
analyse.py — Analyse statistique et visualisation des résultats de simulation.

Lit les CSV produits par le collecteur et génère :
  1. Histogrammes évolutifs des tailles des entités (passif, actif liquide)
  2. Distribution des cascades en joules (log-log pour détecter les lois de puissance)
  3. Évolution temporelle des indicateurs systémiques
  4. Analyse des précurseurs (état du système avant les grandes cascades)
  5. Comparaison multi-scénarios

Usage :
    python analyse.py <dossier_resultats>
    python analyse.py <dossier1> <dossier2>   # comparaison
"""

import os
import csv
import json
import sys
import math
from collections import defaultdict
from typing import List, Dict, Optional

try:
    import matplotlib
    matplotlib.use('Agg')  # pas de fenêtre interactive, on sauvegarde en PNG
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    MATPLOTLIB_OK = True
except ImportError:
    MATPLOTLIB_OK = False
    print("matplotlib non disponible — seuls les résumés texte seront produits.")


# ============================================================
#  LECTURE DES DONNÉES
# ============================================================

def lire_csv(chemin: str, ignorer_commentaires: bool = True) -> List[dict]:
    """Lit un CSV et retourne une liste de dicts. Ignore les lignes #."""
    if not os.path.exists(chemin):
        return []
    rows = []
    with open(chemin, "r", encoding="utf-8") as f:
        for line in f:
            if ignorer_commentaires and line.startswith("#"):
                continue
            rows.append(line)
    if not rows:
        return []
    reader = csv.DictReader(rows)
    result = []
    for row in reader:
        # Convertir les nombres
        converted = {}
        for k, v in row.items():
            try:
                converted[k] = float(v) if '.' in v else int(v)
            except (ValueError, TypeError):
                converted[k] = v
        result.append(converted)
    return result


def lire_distrib_brute(dossier: str, grandeur: str) -> Dict[int, List[float]]:
    """
    Lit le fichier distrib_brute_<grandeur>.csv
    Retourne un dict {pas: [valeurs]}
    """
    chemin = os.path.join(dossier, f"distrib_brute_{grandeur}.csv")
    rows = lire_csv(chemin)
    data = defaultdict(list)
    for r in rows:
        data[int(r["pas"])].append(float(r["valeur"]))
    return dict(data)


def lire_meta(dossier: str) -> dict:
    chemin = os.path.join(dossier, "meta.json")
    if not os.path.exists(chemin):
        return {}
    with open(chemin, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
#  GRAPHIQUES
# ============================================================

def _sauvegarder(fig, chemin: str):
    fig.savefig(chemin, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  → {chemin}")


def graphique_histogrammes_evolutifs(dossier: str, grandeur: str = "passif_total",
                                      titre_extra: str = ""):
    """
    Histogrammes évolutifs : une courbe de densité par instant snapshot.
    Montre l'évolution de la distribution de taille des entités.
    """
    if not MATPLOTLIB_OK:
        return
    data = lire_distrib_brute(dossier, grandeur)
    if not data:
        print(f"  Pas de données pour {grandeur}")
        return

    pas_list = sorted(data.keys())
    n_snapshots = len(pas_list)
    if n_snapshots == 0:
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    # Palette de couleurs : bleu froid → rouge chaud selon le temps
    cmap = plt.cm.plasma
    couleurs = [cmap(i / max(n_snapshots - 1, 1)) for i in range(n_snapshots)]

    for i, pas in enumerate(pas_list):
        valeurs = data[pas]
        if len(valeurs) < 2:
            continue
        # Histogramme normalisé comme densité
        counts, bins = _histogramme_log(valeurs, n_bins=20)
        if counts is None:
            continue
        centres = [(bins[j] + bins[j+1]) / 2 for j in range(len(counts))]
        ax.plot(centres, counts, color=couleurs[i], alpha=0.6, linewidth=1.0)

    # Colorbar pour le temps
    sm = plt.cm.ScalarMappable(cmap=cmap,
                                norm=mcolors.Normalize(vmin=pas_list[0], vmax=pas_list[-1]))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax)
    cbar.set_label("Pas de simulation", fontsize=10)

    noms_lisibles = {
        "passif_total": "Passif total P (joules)",
        "actif_liquide": "Actif liquide L (joules)",
        "actif_total": "Actif total A (joules)",
        "ratio_L_P": "Ratio de liquidité L/P",
        "taux_interne": "Taux interne marginal r*",
        "levier_entite": "Levier individuel P/A",
    }
    xlabel = noms_lisibles.get(grandeur, grandeur)

    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel("Densité", fontsize=11)
    titre = f"Histogrammes évolutifs — {xlabel}"
    if titre_extra:
        titre += f"\n{titre_extra}"
    ax.set_title(titre, fontsize=12)
    ax.set_xscale('log')
    ax.grid(True, alpha=0.3)

    chemin = os.path.join(dossier, f"hist_evolutif_{grandeur}.png")
    _sauvegarder(fig, chemin)


def _histogramme_log(valeurs: List[float], n_bins: int = 20):
    """Calcule un histogramme en échelle log. Retourne (counts_norm, bins)."""
    positifs = [v for v in valeurs if v > 0]
    if len(positifs) < 2:
        return None, None
    vmin, vmax = min(positifs), max(positifs)
    if vmin <= 0 or vmax <= vmin:
        return None, None
    log_min, log_max = math.log10(vmin), math.log10(vmax)
    if log_max == log_min:
        return None, None
    step = (log_max - log_min) / n_bins
    bins = [10 ** (log_min + i * step) for i in range(n_bins + 1)]
    counts = [0] * n_bins
    for v in positifs:
        idx = int((math.log10(v) - log_min) / step)
        idx = min(max(idx, 0), n_bins - 1)
        counts[idx] += 1
    total = sum(counts)
    if total == 0:
        return None, None
    # Normaliser par largeur de bin (densité)
    densites = []
    for i, c in enumerate(counts):
        largeur = bins[i+1] - bins[i]
        densites.append(c / total / largeur if largeur > 0 else 0)
    return densites, bins


def graphique_cascades_log_log(dossier: str, titre_extra: str = ""):
    """
    Distribution complémentaire cumulée (CCDF) des tailles de cascade en joules.
    Tracé en log-log pour détecter une loi de puissance.
    P(X > x) ~ x^(-alpha) → droite en log-log.
    """
    if not MATPLOTLIB_OK:
        return
    chemin = os.path.join(dossier, "tailles_cascades_brutes.csv")
    rows = lire_csv(chemin)
    if not rows:
        print("  Pas de données de cascade")
        return

    volumes = sorted([r["volume_joules"] for r in rows if r["volume_joules"] > 0])
    if len(volumes) < 3:
        print("  Trop peu de cascades pour un graphique log-log")
        return

    # CCDF : P(X > x)
    n = len(volumes)
    ccdf_x = []
    ccdf_y = []
    for i, v in enumerate(volumes):
        ccdf_x.append(v)
        ccdf_y.append((n - i) / n)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Gauche : CCDF log-log
    ax = axes[0]
    ax.scatter(ccdf_x, ccdf_y, s=15, alpha=0.7, color='#d62728', zorder=3)
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel("Volume de la cascade (joules)", fontsize=11)
    ax.set_ylabel("P(X > x)", fontsize=11)
    titre = "CCDF des tailles de cascade"
    if titre_extra:
        titre += f"\n{titre_extra}"
    ax.set_title(titre, fontsize=11)
    ax.grid(True, which='both', alpha=0.3)

    # Ajustement de pente (régression log-log sur la queue)
    if len(volumes) >= 10:
        # Utiliser le quart supérieur
        tail_start = volumes[3 * len(volumes) // 4]
        tail_x = [v for v in volumes if v >= tail_start]
        tail_y = [(n - volumes.index(v)) / n for v in tail_x]
        if len(tail_x) >= 3:
            try:
                log_x = [math.log10(v) for v in tail_x]
                log_y = [math.log10(y) for y in tail_y if y > 0]
                log_x = log_x[:len(log_y)]
                if len(log_x) >= 2:
                    slope, intercept = _regression_lineaire(log_x, log_y)
                    ax.text(0.05, 0.15, f"Pente queue ≈ {slope:.2f}",
                            transform=ax.transAxes, fontsize=10,
                            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))
            except Exception:
                pass

    # Droite : histogramme simple des tailles
    ax2 = axes[1]
    nb_entites = [r["nb_entites"] for r in rows]
    max_nb = int(max(nb_entites)) if nb_entites else 1
    bins_e = list(range(0, max_nb + 2))
    counts_e = [0] * (max_nb + 1)
    for nb in nb_entites:
        counts_e[int(nb)] += 1
    ax2.bar(range(max_nb + 1), counts_e, color='#1f77b4', alpha=0.8, edgecolor='white')
    ax2.set_xlabel("Taille cascade (nb entités)", fontsize=11)
    ax2.set_ylabel("Fréquence", fontsize=11)
    ax2.set_title("Distribution en nombre d'entités faillie", fontsize=11)
    ax2.grid(True, axis='y', alpha=0.3)

    chemin_out = os.path.join(dossier, "cascades_log_log.png")
    _sauvegarder(fig, chemin_out)


def _regression_lineaire(xs, ys):
    """Régression linéaire simple (moindres carrés)."""
    n = len(xs)
    sx = sum(xs); sy = sum(ys)
    sxx = sum(x*x for x in xs); sxy = sum(x*y for x, y in zip(xs, ys))
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-12:
        return 0.0, 0.0
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    return slope, intercept


def graphique_indicateurs_systemiques(dossier: str, titre_extra: str = ""):
    """
    Évolution temporelle des indicateurs systémiques clés.
    4 panneaux : entités vivantes, levier, liquidité, volume prêts.
    """
    if not MATPLOTLIB_OK:
        return
    rows = lire_csv(os.path.join(dossier, "indicateurs_systemiques.csv"))
    if not rows:
        return

    pas      = [r["pas"] for r in rows]
    entites  = [r["nb_entites"] for r in rows]
    levier   = [r["levier_systeme"] for r in rows]
    liquidite = [r["ratio_liquidite"] for r in rows]
    vol_prets = [r["volume_prets"] for r in rows]
    faillites = [r["nb_faillites"] for r in rows]
    vol_faillites = [r["volume_faillites"] for r in rows]

    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    axes = axes.flatten()

    def tracer(ax, y, ylabel, color, titre, marquer_cascades=False):
        ax.plot(pas, y, color=color, linewidth=1.2)
        if marquer_cascades:
            cascade_pas = [p for p, f in zip(pas, faillites) if f > 0]
            cascade_y   = [yi for yi, f in zip(y, faillites) if f > 0]
            ax.scatter(cascade_pas, cascade_y, color='red', s=20, zorder=5, alpha=0.7)
        ax.set_xlabel("Pas", fontsize=9)
        ax.set_ylabel(ylabel, fontsize=9)
        ax.set_title(titre, fontsize=10)
        ax.grid(True, alpha=0.25)

    tracer(axes[0], entites, "Nb entités", "#2196F3", "Entités vivantes", marquer_cascades=True)
    tracer(axes[1], levier, "P_total / A_total", "#FF5722", "Levier système", marquer_cascades=True)
    tracer(axes[2], liquidite, "L_total / P_total", "#4CAF50", "Ratio liquidité", marquer_cascades=True)
    tracer(axes[3], vol_prets, "Joules", "#9C27B0", "Volume prêts actifs")

    # Tailles des cascades
    axes[4].bar(pas, vol_faillites, color='#F44336', alpha=0.8, width=0.8)
    axes[4].set_xlabel("Pas", fontsize=9)
    axes[4].set_ylabel("Joules détruits", fontsize=9)
    axes[4].set_title("Volume des cascades (joules)", fontsize=10)
    axes[4].grid(True, axis='y', alpha=0.25)

    # Concentration des prêts
    concentration = [r["concentration_prets"] for r in rows]
    tracer(axes[5], concentration, "Herfindahl", "#795548", "Concentration réseau de crédit")

    titre_global = "Indicateurs systémiques"
    if titre_extra:
        titre_global += f" — {titre_extra}"
    fig.suptitle(titre_global, fontsize=13, fontweight='bold')
    plt.tight_layout()

    chemin_out = os.path.join(dossier, "indicateurs_systemiques.png")
    _sauvegarder(fig, chemin_out)


def graphique_precurseurs(dossier: str, titre_extra: str = ""):
    """
    Analyse des précurseurs : état du système AVANT chaque cascade.
    Nuage de points : (ratio_liquidite_avant, levier_avant) coloré par volume de cascade.
    """
    if not MATPLOTLIB_OK:
        return
    rows = lire_csv(os.path.join(dossier, "cascades_faillites.csv"))
    if len(rows) < 3:
        return

    # Extraire les indicateurs systémiques juste avant chaque cascade
    ind_rows = lire_csv(os.path.join(dossier, "indicateurs_systemiques.csv"))
    ind_par_pas = {r["pas"]: r for r in ind_rows}

    cascade_data = []
    for c in rows:
        pas = c["pas"]
        # Prendre l'indicateur du pas précédent
        ind_avant = ind_par_pas.get(pas - 1, {})
        if ind_avant:
            cascade_data.append({
                "levier": ind_avant.get("levier_systeme", 0),
                "liquidite": ind_avant.get("ratio_liquidite", 0),
                "volume": c["volume_actifs_detruits"],
                "ratio": c["ratio_destruction"],
            })

    if len(cascade_data) < 3:
        return

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    volumes = [d["volume"] for d in cascade_data]
    leviers = [d["levier"] for d in cascade_data]
    liquidites = [d["liquidite"] for d in cascade_data]
    ratios = [d["ratio"] for d in cascade_data]

    # Gauche : levier avant vs volume cascade
    sc = axes[0].scatter(leviers, volumes, c=ratios, cmap='hot_r',
                          s=40, alpha=0.8, edgecolors='k', linewidths=0.3)
    axes[0].set_xlabel("Levier système avant cascade (P/A)", fontsize=10)
    axes[0].set_ylabel("Volume cascade (joules)", fontsize=10)
    axes[0].set_title("Précurseur : levier", fontsize=11)
    axes[0].grid(True, alpha=0.3)
    plt.colorbar(sc, ax=axes[0], label="Ratio destruction (cascade/actif total)")

    # Droite : liquidité avant vs volume cascade
    sc2 = axes[1].scatter(liquidites, volumes, c=ratios, cmap='hot_r',
                           s=40, alpha=0.8, edgecolors='k', linewidths=0.3)
    axes[1].set_xlabel("Ratio liquidité système avant cascade (L/P)", fontsize=10)
    axes[1].set_ylabel("Volume cascade (joules)", fontsize=10)
    axes[1].set_title("Précurseur : liquidité", fontsize=11)
    axes[1].grid(True, alpha=0.3)
    plt.colorbar(sc2, ax=axes[1], label="Ratio destruction")

    titre = "Analyse des précurseurs de cascade"
    if titre_extra:
        titre += f" — {titre_extra}"
    fig.suptitle(titre, fontsize=12, fontweight='bold')
    plt.tight_layout()

    chemin_out = os.path.join(dossier, "precurseurs_cascades.png")
    _sauvegarder(fig, chemin_out)


def graphique_comparaison(dossiers: List[str], labels: List[str],
                           dossier_sortie: str = "."):
    """
    Compare plusieurs scénarios sur les indicateurs clés.
    """
    if not MATPLOTLIB_OK or len(dossiers) < 2:
        return

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    axes = axes.flatten()
    couleurs = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

    for idx, (dossier, label) in enumerate(zip(dossiers, labels)):
        rows = lire_csv(os.path.join(dossier, "indicateurs_systemiques.csv"))
        if not rows:
            continue
        color = couleurs[idx % len(couleurs)]
        pas = [r["pas"] for r in rows]

        axes[0].plot(pas, [r["nb_entites"] for r in rows], label=label, color=color, linewidth=1.3)
        axes[1].plot(pas, [r["levier_systeme"] for r in rows], label=label, color=color, linewidth=1.3)
        axes[2].plot(pas, [r["ratio_liquidite"] for r in rows], label=label, color=color, linewidth=1.3)
        axes[3].plot(pas, [r["volume_faillites"] for r in rows], label=label, color=color, linewidth=1.3, alpha=0.8)

    titres = ["Entités vivantes", "Levier système (P/A)",
              "Ratio liquidité (L/P)", "Volume faillites (joules)"]
    ylabels = ["Nb entités", "P_total/A_total", "L_total/P_total", "Joules"]

    for ax, titre, yl in zip(axes, titres, ylabels):
        ax.set_title(titre, fontsize=11)
        ax.set_ylabel(yl, fontsize=9)
        ax.set_xlabel("Pas", fontsize=9)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.25)

    fig.suptitle("Comparaison multi-scénarios", fontsize=13, fontweight='bold')
    plt.tight_layout()

    chemin_out = os.path.join(dossier_sortie, "comparaison_scenarios.png")
    _sauvegarder(fig, chemin_out)
    print(f"Comparaison sauvegardée : {chemin_out}")


# ============================================================
#  RÉSUMÉS TEXTE
# ============================================================

def resumer_cascades(dossier: str) -> str:
    """Produit un résumé textuel des statistiques de cascade."""
    rows = lire_csv(os.path.join(dossier, "tailles_cascades_brutes.csv"))
    if not rows:
        return "  Aucune cascade enregistrée."

    volumes = sorted([r["volume_joules"] for r in rows])
    n = len(volumes)
    total = sum(volumes)
    moyenne = total / n
    mediane = volumes[n // 2]
    max_v = volumes[-1]

    lines = [
        f"  Nombre de cascades       : {n}",
        f"  Volume total détruit     : {total:.1f} joules",
        f"  Volume moyen             : {moyenne:.2f} joules",
        f"  Volume médian            : {mediane:.2f} joules",
        f"  Volume maximal           : {max_v:.2f} joules",
        f"  Q90                      : {volumes[int(0.9*n)]:.2f} joules",
        f"  Q99                      : {volumes[min(int(0.99*n), n-1)]:.2f} joules",
    ]

    # Distribution des tailles
    seuils = [1, 5, 10, 50, 100, 500]
    lines.append("  Distribution (volume > seuil) :")
    for s in seuils:
        nb = sum(1 for v in volumes if v > s)
        if nb > 0:
            lines.append(f"    > {s:6.0f} joules : {nb:5d} cascades ({100*nb/n:.1f}%)")

    return "\n".join(lines)


# ============================================================
#  POINT D'ENTRÉE
# ============================================================

def analyser_dossier(dossier: str, verbose: bool = True):
    """Lance l'analyse complète d'un dossier de simulation."""
    if not os.path.exists(dossier):
        print(f"Dossier introuvable : {dossier}")
        return

    meta = lire_meta(dossier)
    label = meta.get("label", os.path.basename(dossier))
    titre_extra = label

    if verbose:
        print(f"\nAnalyse : {dossier}")
        print(f"Label    : {label}")
        if meta.get("resume"):
            for k, v in meta["resume"].items():
                print(f"  {k}: {v}")

    print("\nStatistiques des cascades :")
    print(resumer_cascades(dossier))

    if MATPLOTLIB_OK:
        print("\nGénération des graphiques :")
        for grandeur in ["passif_total", "actif_liquide", "ratio_L_P", "levier_entite"]:
            graphique_histogrammes_evolutifs(dossier, grandeur, titre_extra=titre_extra)
        graphique_cascades_log_log(dossier, titre_extra=titre_extra)
        graphique_indicateurs_systemiques(dossier, titre_extra=titre_extra)
        graphique_precurseurs(dossier, titre_extra=titre_extra)
        print("Graphiques générés.")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("Usage : python analyse.py <dossier> [dossier2 ...]")
        sys.exit(1)

    if len(args) == 1:
        analyser_dossier(args[0])
    else:
        # Mode comparaison
        labels = []
        for d in args:
            m = lire_meta(d)
            labels.append(m.get("label", os.path.basename(d)))

        for d in args:
            analyser_dossier(d)

        print("\nComparaison multi-scénarios :")
        graphique_comparaison(args, labels, dossier_sortie=".")
