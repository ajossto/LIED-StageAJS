# Sélection des cellules de confirmation (2026-08-05)

Étape 2 du protocole (`protocole.md`) : « sélection de ≤6 cellules
candidates à la confirmation (celles montrant l'effet le plus net sur
`share_from_mean_rq`, la stabilité de seuil, ou le comportement
d'avalanche le plus intéressant) ». Calculé sur
`results/campaign/exploration_summary.csv` (87/87 runs, moyenne sur les
3 graines d'exploration par cellule), comparé à la baseline
(`share_from_mean_rq`=0,2294, `tau_hat`=1,41, `branching_ratio`=0,786,
`alpha_density_mean`=3,78).

## Classement complet (|Δ share_from_mean_rq| vs baseline, décroissant)

| label | rq | Δrq | seuil<20% (frac) | τ̂ | Δτ̂ | branching | Δbranching | α | pop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rho_0.125 | 0,388 | +0,159 | 0,00 | 1,84 | +0,43 | 0,480 | -0,306 | 4,20 | 1616 |
| K0_2000 | 0,106 | -0,124 | 0,01 | 1,39 | -0,02 | 0,655 | -0,130 | 2,79 | 7247 |
| K0_1 | 0,346 | +0,117 | 0,00 | 1,79 | +0,38 | 0,588 | -0,198 | 3,59 | 387 |
| rho_0.25 | 0,341 | +0,112 | 0,00 | 1,88 | +0,47 | 0,584 | -0,201 | 4,09 | 1352 |
| rho_4 | 0,137 | -0,093 | 0,00 | 0,99 | -0,42 | 0,891 | +0,105 | 4,05 | 988 |
| gamma_0.6667 | 0,317 | +0,088 | 0,00 | 1,66 | +0,25 | 0,640 | -0,145 | 3,35 | 401 |
| K0_500 | 0,145 | -0,085 | 0,00 | 1,42 | +0,00 | 0,746 | -0,039 | 3,10 | 3852 |
| control_geometric | 0,156 | -0,073 | 0,00 | 1,46 | +0,05 | 0,757 | -0,029 | 3,17 | 1617 |
| gamma_0.3333 | 0,161 | -0,069 | 0,00 | 1,49 | +0,08 | 0,765 | -0,021 | 3,80 | 3302 |
| … | | | | | | | | | |

(table complète reproductible via le script de ranking utilisé pour
cette sélection, non conservé séparément — recalcul direct sur
`exploration_summary.csv`, colonnes `share_from_mean_rq_mean`, `tau_hat`,
`branching_ratio`, `threshold_reldiff_frac_under_20pct`,
`alpha_density_mean`, `population_final`, moyenne par `label`)

**Observation transversale** : `threshold_reldiff_frac_under_20pct` ≈ 0
sur la quasi-totalité des 28 branches (seule `deltasigma_0.1_0.1`
atteint 0,09). Le critère 1 de robustesse de queue (stabilité au
seuil KS vs seuil/2, <20 % relatif) est donc structurellement rarement
satisfait dans le grid d'exploration — attendu à confirmer/documenter
comme tel en confirmation plutôt que corrigé a posteriori (protocole,
« ce qui compte comme un échec honnête »).

## Cellules retenues (6, ≤6 autorisé par le protocole)

| Cellule | Motif |
|---|---|
| `rho_0.125` | Effet le plus net sur `share_from_mean_rq` (+0,159) parmi toutes les branches ; branche E = η linéaire, « levier privilégié » du prompt complet (§7-8, `PROMPT_M4_2B_COMPLET.md`) |
| `rho_4` | Extrême opposé de la même branche E : `share_from_mean_rq` -0,093, mais surtout `branching_ratio` +0,105 (0,786→0,891, proche de la criticalité) — complète le tableau objectif A/objectif B sur le même levier |
| `K0_1` | Extrême bas de la branche A (K0), « branche prioritaire » du protocole (mécanisme deg_out/rq identifié en phase pilote) ; `share_from_mean_rq` +0,117, population finale 387 |
| `K0_2000` | Extrême haut de la même branche : `share_from_mean_rq` -0,124, population 7247 (×19 vs K0_1), `alpha_density_mean` le plus bas observé sur tout le grid (2,79) — cellule la plus coûteuse (≈95 min/graine en exploration) mais la plus informative pour la branche prioritaire |
| `gamma_0.6667` | Effet le plus net de la branche B (γ non compensé, +0,088) ; le prompt complet interdit explicitement de traiter γ comme secondaire (§13) |
| `control_geometric` | Non retenue par la taille de l'effet (-0,073, milieu du classement) mais nécessaire : seule cellule répondant à la question 1 du rapport final (§21, comparaison institutionnelle cible arithmétique vs géométrique) |

Non retenues malgré un effet notable : `rho_0.25` (même direction que
`rho_0.125`, effet plus faible, redondant pour la confirmation — la
robustesse inter-graines se teste par cellule, pas par re-balayage du
domaine) ; `K0_500` (entre les deux extrêmes déjà couverts par `K0_1`/
`K0_2000`).

## Protocole d'exécution

5 graines disjointes (10-14, jamais utilisées en exploration), T=3000,
même moteur/adaptateur, mêmes diagnostics que l'exploration
(`scripts/confirmation.py`, résultats sous `results/confirmation/`,
indépendants de `results/campaign/`). Critères d'application post-hoc :
`protocole.md`, section « Critères de confirmation ».

## Extension (2026-08-05, après coup)

`report/rapport_interim.md` §6 a signalé que la sélection ci-dessus
n'exploitait qu'un des trois motifs autorisés par le protocole (effet
sur `share_from_mean_rq`). Deux motifs non exploités ressortaient
nettement dans l'exploration : `deltasigma_0.1_0.1` (seule cellule à
sortir du bruit sur la stabilité de seuil elle-même, critère 1) et la
branche `gamma_comp_*` (effet γ le plus net une fois l'échelle
K0/K*_aut contrôlée). Ajoutées via `scripts/confirmation_extra.py`
(mêmes 5 graines 10-14, mêmes résultats sous `results/confirmation/`,
pool réduit à 3 workers pour tourner en parallèle des 8 workers déjà
engagés sur les 6 cellules initiales). **À traiter comme une
extension, pas une modification a posteriori** : décidée avant tout
résultat de confirmation, sur la seule base de l'exploration — mais à
rapporter séparément dans le rapport final pour ne pas brouiller la
sélection pré-enregistrée initiale.
