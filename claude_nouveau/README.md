# Simulation multi-agents — claude_nouveau

Simulation dynamique d'entités économiques abstraites échangeant une ressource unique (le **joule**).
Version hybride combinant l'architecture de ChatGPT et le système statistique de Claude.

---

## Structure

```
claude_nouveau/
├── src/
│   ├── models.py       — Dataclasses Entity, Loan, BankruptcyEstate (références par ID)
│   ├── config.py       — SimulationConfig (dataclass typée)
│   ├── statistics.py   — Collector, SnapshotDistribution, CascadeEvent, SystemicIndicator
│   ├── simulation.py   — Moteur de simulation
│   ├── output.py       — Gestion des dossiers de sortie auto-labellisés
│   ├── analysis.py     — Graphiques et résumés (log-binning pour cascades)
│   └── main.py         — Point d'entrée
└── tests/
    └── test_basic.py   — 11 tests de validation
```

---

## Choix d'architecture

| Aspect | Choix | Source |
|--------|-------|--------|
| Modèles | Dataclasses | ChatGPT |
| Références | Par ID entier | ChatGPT |
| Conteneurs | `Dict[int, Entity/Loan/Estate]` | ChatGPT |
| RNG | `random.Random(seed)` isolé | ChatGPT |
| Taux de crédit | Configurable (prêteur ou moyenne) | ChatGPT |
| Auto-investissement | Fraction du surplus `L - seuil*P` | ChatGPT |
| Paramètres | Valeurs du modèle Claude | Claude |
| Durée | 3000 pas | — |
| Statistiques | Collecteur riche (distributions, cascades, indicateurs) | Claude |
| Log-log cascades | **Bins log-espacés** (densité normalisée par largeur) | Nouveau |

---

## Paramètres

| Paramètre | Valeur | Rôle |
|-----------|--------|------|
| `alpha` | 1.0 | Productivité (extraction = α√P) |
| `seuil_ratio_liquide_passif` | 0.05 | Seuil L/P pour participer au marché |
| `theta` | 0.5 | Fraction de la demande maximale empruntée |
| `mu` | 0.05 | Marge minimale emprunt vs auto-investissement |
| `lambda_creation` | 0.5 | Taux d'arrivée Poisson de nouvelles entités |
| `actif_liquide_initial` | 10.0 | Dotation initiale en liquide |
| `passif_inne_initial` | 5.0 | Passif inné à la naissance |
| `taux_depreciation_liquide` | 0.02 | Dépréciation du liquide par pas |
| `taux_depreciation_endo` | 0.03 | Dépréciation de l'endo-investi |
| `taux_depreciation_exo` | 0.03 | Dépréciation de l'exo-investi |
| `coefficient_reliquefaction` | 0.5 | Rendement de destruction endo → liquide |
| `fraction_auto_investissement` | 0.3 | Fraction du **surplus** liquide auto-investie |
| `duree_simulation` | 3000 | Durée en pas |
| `seed` | 42 | Graine aléatoire |
| `use_lender_rate_as_offer_rate` | True | Taux proposé = taux prêteur (vs moyenne) |
| `freq_snapshot` | 10 | Fréquence des snapshots de distribution |

---

## Utilisation

```bash
cd claude_nouveau/src
python main.py
```

Ou depuis Python :

```python
import sys
sys.path.insert(0, "claude_nouveau/src")

from config import SimulationConfig
from output import run_and_save

config = SimulationConfig(duree_simulation=3000)
sim, folder = run_and_save(config, label="mon_scenario")
```

Analyser un dossier existant :

```python
from analysis import analyze_folder
analyze_folder("resultats/20260323_...")
```

---

## Tests

```bash
cd claude_nouveau
python tests/test_basic.py
```

11 tests couvrent : extraction, dépréciation, auto-investissement (surplus),
prêts, scission, taux interne, faillite, masse de faillite,
simulation complète, collecteur statistique.

---

## Ordre d'un pas de simulation

1. Création de nouvelles entités (Poisson)
2. Extraction depuis la nature (Π = α√P)
3. Paiement des intérêts + redistribution des masses de faillite
   *(en cas d'illiquidité : liquide → cession de créances → reliquéfaction endo)*
4. Dépréciation des stocks
5. Marché du crédit (itératif, max 100 000 itérations)
6. Auto-investissement du surplus de fin de tour
7. Test de faillite comptable + résolution des cascades
8. Enregistrement des statistiques (légères + collecteur riche)

---

## Sorties produites

```
resultats/YYYYMMDD_HHMMSS_<label>_<hash7>/
├── meta.json                       — config + résumé (JSON)
├── stats_legeres.csv               — 1 ligne/pas, agrégats simples
├── indicateurs_systemiques.csv     — levier, liquidité, volume prêts…
├── snapshots_distributions.csv     — quantiles des distributions
├── cascades_faillites.csv          — données détaillées de chaque cascade
├── tailles_cascades_brutes.csv     — volumes bruts pour loi de puissance
├── distrib_brute_passif_total.csv  — valeurs individuelles par entité
├── distrib_brute_actif_liquide.csv
├── distrib_brute_ratio_L_P.csv
├── distrib_brute_levier_entite.csv
├── distrib_brute_taux_interne.csv
├── distrib_brute_actif_total.csv
├── hist_evolutif_*.png             — distributions évolutives (log-log)
├── cascades_log_log.png            — PDF log-binnée + CCDF + distribution entités
├── indicateurs_systemiques.png     — 6 panneaux temporels
└── precurseurs_cascades.png        — état système avant chaque cascade
```

---

## Graphique log-log des cascades

Le graphique `cascades_log_log.png` utilise des **bins log-espacés** pour estimer
la densité de probabilité des tailles de cascade.

**Pourquoi ?** Pour une loi de puissance `p(x) ~ x^{-α}`, les bins linéaires
sous-représentent la queue. Les bins log-espacés donnent une densité constante
par décade, révélant la pente directement sur un axe log-log.

Méthode :
- Bins de largeur égale en espace log
- Densité = `count / (N * largeur_linéaire)`
- Centre géométrique : `√(bord_gauche × bord_droit)`
- Régression linéaire sur log(densité) vs log(taille) → pente = -α

---

## Dépendances

Python standard uniquement : `math`, `random`, `csv`, `json`, `os`, `dataclasses`.
`matplotlib` optionnel pour les graphiques (dégradé élégant si absent).
