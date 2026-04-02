# Simulation multi-agents — Système autocritique de joules

Simulation dynamique d'entités économiques abstraites échangeant une ressource unique (le **joule**).  
Le modèle représente extraction, investissement, crédit, illiquidité, faillites et cascades de défaut.

---

## Structure des fichiers

```
simulation/
├── simulation.py    — Code principal (classes Entite, Pret, MasseFaillite, Simulation)
├── parametres.py    — Paramètres centralisés, facilement modifiables
├── tests.py         — 10 tests de validation unitaires
├── exemple.py       — 3 scénarios commentés + analyse des cascades
└── README.md        — Ce fichier
```

---

## Utilisation rapide

```python
from simulation import Simulation
from parametres import PARAMS
import copy

params = copy.deepcopy(PARAMS)
params["nb_pas"] = 200

sim = Simulation(params)
stats = sim.run(verbose=True)
sim.exporter_csv("resultats.csv")
print(sim.resume())
```

---

## Paramètres principaux

| Paramètre | Défaut | Rôle |
|-----------|--------|------|
| `alpha` | 1.0 | Productivité (extraction = α√P) |
| `seuil_ratio_liquide_passif` | 0.05 | Seuil L/P pour agir sur le marché |
| `theta` | 0.5 | Fraction de la demande maximale empruntée |
| `mu` | 0.05 | Marge minimale emprunt vs auto-investissement |
| `lambda_creation` | 0.5 | Taux d'arrivée (Poisson) de nouvelles entités |
| `actif_liquide_initial` | 10.0 | Dotation initiale en liquide |
| `passif_inne_initial` | 5.0 | Passif inné de naissance |
| `taux_depreciation_liquide` | 0.02 | Dépréciation du liquide par pas |
| `taux_depreciation_endo` | 0.03 | Dépréciation de l'endo-investi |
| `taux_depreciation_exo` | 0.03 | Dépréciation de l'exo-investi |
| `coefficient_reliquefaction` | 0.5 | Rendement de destruction endo → liquide |
| `fraction_auto_investissement` | 0.3 | Fraction du liquide auto-investie par pas |
| `nb_pas` | 200 | Durée de la simulation |
| `graine` | 42 | Graine aléatoire (None = aléatoire) |

---

## Lancer les tests

```bash
python tests.py
```

10 tests couvrent : extraction, dépréciation, auto-investissement, prêts, scission, faillite, masses de faillite, taux interne, simulation complète, critère d'activation.

---

## Lancer les scénarios d'exemple

```bash
python exemple.py
```

Trois scénarios sont comparés :
- **Standard** : paramètres par défaut
- **Fragile** : fort levier, critère d'acceptation lâche
- **Robuste** : emprunteurs prudents, marché restrictif

---

## Ordre d'un pas de simulation

1. Création de nouvelles entités (Poisson)
2. Extraction depuis la nature (Π = α√P)
3. Paiement des intérêts
4. Gestion de l'illiquidité (liquide → cession de créances → reliquéfaction endo)
5. Dépréciation des stocks
6. Sélection des entités actives + marché du crédit (itératif)
7. Auto-investissement de fin de tour
8. Test de faillite comptable + résolution des cascades
9. Enregistrement des statistiques

---

## Statistiques produites par pas

| Champ | Description |
|-------|-------------|
| `pas` | Numéro du pas |
| `nb_entites_vivantes` | Entités actives |
| `nb_faillites` | Faillites dans ce pas (taille de la cascade) |
| `actifs_detruits` | Valeur totale des actifs détruits |
| `creances_annulees` | Nominal total des créances annulées |
| `volume_prets_actifs` | Somme des principals des prêts actifs |
| `nb_prets_actifs` | Nombre de prêts en cours |
| `actif_total_systeme` | Somme des actifs de toutes les entités vivantes |
| `passif_total_systeme` | Somme des passifs |
| `liquidite_totale` | Somme des actifs liquides |

---

## Dépendances

Python standard uniquement : `math`, `random`, `csv`, `copy`, `collections`.  
Aucune bibliothèque externe requise.

---

## Notes de modélisation

Le modèle est décrit en détail dans la *Note de modélisation* (PDF joint).  
Chaque règle est référencée dans le code par son numéro de section (§4, §13, etc.).

---

## Nouveaux modules statistiques (v2)

```
simulation/
├── statistiques.py  — Collecteur de données (distributions, cascades, indicateurs)
├── sortie.py        — Gestion des dossiers de sortie auto-labellisés
├── analyse.py       — Graphiques et résumés texte
```

### Lancement avec collecte statistique complète

```python
from sortie import lancer_et_sauvegarder
from parametres import PARAMS
import copy

params = copy.deepcopy(PARAMS)
sim, dossier = lancer_et_sauvegarder(
    params,
    label="mon_scenario",
    notes="Description libre",
    freq_snapshot=5,       # snapshot toutes les 5 étapes
    dossier_racine="resultats"
)
```

### Structure d'un dossier de sortie

```
resultats/YYYYMMDD_HHMMSS_<label>_<hash7>/
├── meta.json                        — paramètres + résumé (JSON)
├── indicateurs_systemiques.csv      — 1 ligne/pas : levier, liquidité, volume prêts...
├── snapshots_distributions.csv      — statistiques résumées des distributions (quantiles)
├── cascades_faillites.csv           — 1 ligne/cascade : volume joules, contagion, précurseurs
├── tailles_cascades_brutes.csv      — volumes bruts pour analyse loi de puissance
├── distrib_brute_passif_total.csv   — valeurs individuelles par entité et par instant
├── distrib_brute_actif_liquide.csv
├── distrib_brute_ratio_L_P.csv
├── distrib_brute_levier_entite.csv
├── distrib_brute_taux_interne.csv
├── distrib_brute_actif_total.csv
├── stats_legeres.csv                — statistiques agrégées (rétrocompatibilité)
├── hist_evolutif_passif_total.png   — histogrammes évolutifs (si entités vivantes)
├── hist_evolutif_actif_liquide.png
├── hist_evolutif_ratio_L_P.png
├── hist_evolutif_levier_entite.png
├── cascades_log_log.png             — CCDF log-log (si cascades)
├── indicateurs_systemiques.png      — 6 panneaux temporels
└── precurseurs_cascades.png         — état système avant chaque cascade
```

### Analyse d'un dossier existant

```python
from analyse import analyser_dossier
analyser_dossier("resultats/mon_dossier")
```

### Comparaison multi-scénarios

```python
from analyse import graphique_comparaison
graphique_comparaison(["dossier1", "dossier2"], ["label1", "label2"], dossier_sortie=".")
```

### Grandeurs collectées dans les distributions brutes

| Fichier | Description | Intérêt |
|---------|-------------|---------|
| `passif_total` | Taille productive de chaque entité | Distribution de puissance ? |
| `actif_liquide` | Réserves disponibles | Fragilité individuelle |
| `ratio_L_P` | Liquidité relative | Précurseur systémique |
| `levier_entite` | P/A individuel | Détection des entités fragiles |
| `taux_interne` | r* = α/2√P | Structure du marché de crédit |

### Grandeurs dans cascades_faillites.csv

| Colonne | Description |
|---------|-------------|
| `volume_actifs_detruits` | Joules détruits — **métrique principale** |
| `ratio_destruction` | Volume / actif total système avant cascade |
| `volume_creances_annulees` | Propagation via réseau de crédit |
| `nb_contamines` | Entités solvables avant la cascade qui ont failli |
| `ratio_contagion` | nb_contamines / nb_total_faillis |
