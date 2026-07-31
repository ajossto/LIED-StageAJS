# Protocole de campagne M4.2B (figé le 30 juillet 2026, soir)

Rédigé APRÈS la phase pilote (JOURNAL.md §1-8) mais AVANT de lancer la
campagne d'exploration/confirmation ci-dessous — conformément à §18 du
prompt ("le protocole de production... figé avant... les résultats
négatifs [sont] conservés"). Autorisation utilisateur (30/07/2026) : budget
de calcul illimité, 8 processus (au lieu de la convention ≤6), T=10000
praticable pour la baseline lente.

## Correction méthodologique préalable (avant la campagne)

Un piège a été trouvé et corrigé dans le pilote λ (JOURNAL.md §7) : mon
propre script de pilote appelait `fit_powerlaw_cutoff` directement sans
vérifier `s_c_out_of_range`. **La correction n'est PAS dans
`lib_metrics.py`** (qui implémente déjà correctement le repli vers
l'exposant pur via `compare_laws`) **mais dans le runner de campagne**, qui
utilise désormais systématiquement `compare_laws` (+ `vuong_trunc_vs_ln`
pour le test de modèle primaire correct) au lieu d'appeler
`fit_powerlaw_cutoff` isolément.

## Diagnostic de renouvellement (demandé par l'utilisateur, corrigé)

Le premier diagnostic (cohorte du premier décile *d'âge*) était mal posé :
il montrait une extinction en ~300 pas, mais mesurait la mortalité des
jeunes/pauvres (fragiles par construction), pas le renouvellement du
système. Le bon diagnostic — déjà implémenté et généré comme figure
standard M4B/M4.2/M4.2B (`reporting.py::soc_figures`,
`soc_top_decile_renewal.png`) — suit la PERSISTANCE DANS LE TOP DÉCILE (par
valeur nette) : identifie qui est dans le top décile au premier snapshot,
puis mesure à chaque snapshot ultérieur quelle fraction de ce groupe initial
est ENCORE dans le top décile courant (recalculé à chaque instant).

Résultat sur le run baseline (T=3000, seed 0) : décroissance rapide dans les
100 premiers pas (0,98→0,79), puis décroissance plus lente jusqu'à ~t=2000
(0,79→~0,09), puis un **plancher non nul (~0,07-0,09) qui persiste jusqu'à
t=3000 sans redescendre**. Vérification (`scipy.stats.linregress`) : Gini(K)
lui-même ne montre AUCUNE tendance dans la fenêtre [750,3000]
(p=0,73, r²=0,003) — les statistiques transversales déjà rapportées (Gini,
exposant de queue) NE SONT PAS contaminées par cette lente dynamique
d'identité, qui concerne la PERSISTANCE DES INDIVIDUS dans l'élite, pas la
FORME de la distribution instantanée. Le plancher non-décroissant à
t=3000 justifie néanmoins de vérifier à T=10000 s'il continue de décroître
ou s'il s'agit d'un second régime stationnaire — c'est l'objet de la
validation d'horizon étendu ci-dessous.

## Grille de campagne

Baseline commune sauf indication contraire : γ=0,5, δ=0,01, σ=0,01, K0=25,
λ=30, ρ=1, β=1, target_rule=arithmetic, T=3000, burn-in=750 (T/4, conforme
à la stationnarité agrégée établie en phase pilote). 3 graines par cellule
d'exploration (seeds 0,1,2) ; les cellules dédupliquées avec la baseline
(mêmes paramètres) réutilisent son cell_id — pas de recalcul.

| Branche | Variable | Valeurs | Justification |
|---|---|---|---|
| 0. Validation d'horizon | T | 10000 (baseline sinon) | Demande utilisateur ; vérifie si le plancher de renouvellement continue d'évoluer |
| A. K0 | K0 | {1, 5, 25, 100, 500, 2000} | Branche prioritaire (mécanisme deg_out/rq pointe directement vers K0/K*_aut) |
| B. γ (non compensé) | γ | {1/3, 0,4, 0,5, 0,6, 2/3} | Cartographie de la concavité |
| B'. γ (K0 compensé) | γ, K0 | idem, K0=K0/K*_aut(0,5)·K*_aut(γ) | Sépare échelle et courbure (méthode M4.2) |
| C. η non linéaire | β (eta_n_ref=1140) | {0,5, 0,75, 1, 1,25, 1,5} | Déliverable §7 manquant |
| D. δ,σ joints | (δ,σ) | {(0,01;0,01),(0,02;0,02),(0,05;0,05),(0,10;0,10),(0,05;0,25)} | Dernier couple = baseline M4.2 (comparaison institutionnelle complète) |
| E. ρ (η linéaire) | ρ | {0,125, 0,25, 0,5, 1, 2, 4} | Reprise rigoureuse du contraste pilote (1 graine → 3 graines, T plus long) |
| F. Contrôle géométrique | target_rule | geometric | Ré-exécuté à T=3000, 3 graines (vs 1 graine T=1000 en pilote) |

## Diagnostics enregistrés par run (script `scripts/campaign.py`)

- `compare_laws` (avalanches, fenêtre de burn-in) : τ̂, `tau_hat_source`
  (pure vs cutoff), `s_c_out_of_range`, LRT cutoff-vs-pure ;
  `vuong_trunc_vs_ln` séparément (modèle primaire correct) ; branching_ratio,
  size_max, n_tail.
- `interest_income.fit_across_snapshots` : lignes PAR SNAPSHOT persistées
  (pas seulement la moyenne), + résumé (α̂ moyen/écart-type, stabilité au
  seuil ×0,5/×2).
- `decompose_tail_sources` (réseau, moyenné sur les snapshots de la
  fenêtre) : parts deg_out / mean_rq / covariance.
- Gini(K), log-std(K), trajectoire complète (pas seulement la valeur
  finale) — pour détecter toute dérive résiduelle.
- Renouvellement du top décile (net worth ET revenu d'intérêt séparément) :
  courbe complète + demi-vie (premier pas où la part retombe sous 50 %).
- Coût (temps CPU), statut de population (ok/extinction/explosion).

## Critères de confirmation, pré-enregistrés AVANT tout résultat de campagne

**Une queue Pareto des intérêts sera qualifiée de robuste pour une cellule
si, sur AU MOINS 3 graines disjointes de confirmation (seeds 10-14, jamais
utilisées en exploration) :**

1. α̂_density (seuil KS) et α̂_density(seuil/2) diffèrent de moins de 20 %
   relatif (contre >30-40% observé en phase pilote partout) ;
2. n_tail ≥ 100 par snapshot en moyenne sur la fenêtre de confirmation ;
3. le signe et l'ordre de grandeur de l'effet du paramètre testé sont
   cohérents entre les ≥3 graines (pas seulement en moyenne) ;
4. `tail_vs_lognormal`/`tail_vs_exponential` (Vuong) favorise la loi de
   puissance dans une majorité des graines ;
5. Gini(K) et `share_from_deg_out` ne suffisent pas seuls à expliquer le
   changement observé (i.e. l'effet ne se réduit pas à un simple
   changement d'échelle du corps).

**Un exposant d'avalanche τ̂ sera qualifié d'indépendant de la taille si :**

1. `tau_hat_source="powerlaw_cutoff"` (pas de repli sur la loi pure) pour
   TOUTES les tailles de population testées dans la cellule ;
2. τ̂ varie de moins de 15 % relatif entre les tailles de population les
   plus petites et les plus grandes observées à paramètres autrement
   identiques ;
3. le rapport de branchement reste stable (±0,05) sur la même plage.

**Ce qui compte comme un échec honnête, pas un problème à corriger** :
toute cellule qui ne satisfait pas ces critères est rapportée comme telle,
avec le detail des critères ratés — aucune sélection a posteriori de
graines, de fenêtres ou de seuils pour obtenir un résultat positif.

## Ordre d'exécution

1. Exploration complète (grille ci-dessus, seeds 0-2, T=3000 sauf branche 0).
2. Analyse d'exploration → sélection de ≤6 cellules candidates à la
   confirmation (celles montrant l'effet le plus net sur `share_from_mean_rq`,
   la stabilité de seuil, ou le comportement d'avalanche le plus
   intéressant).
3. Confirmation (5 graines disjointes 10-14, T=3000, cellules choisies).
4. Application des critères ci-dessus, rapport final.
