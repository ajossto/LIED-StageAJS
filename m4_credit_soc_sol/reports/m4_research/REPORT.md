# M4 — avalanches auto-organisées : rapport de recherche

Date : 13 juillet 2026. Workspace : `m4_credit_soc_sol`.

## Verdict

Le meilleur régime testé est le moteur contractuel sans dette abstraite `d0`,
avec objectif de revenu myope et chocs sectoriels (`rho=0,8`, 5 secteurs). Il
améliore nettement la baseline et présente un **scaling en taille finie positif** :
quand la population moyenne passe d'environ 160 à 318 puis 639, la médiane
inter-seeds du maximum d'avalanche passe de 7 à 18 puis 24, et le p99 des
avalanches multi-entités de 6 à 9,8 puis 13. Le ratio max/pop reste autour de
4–6 %, très loin d'un effondrement quasi total.

Ce résultat n'établit cependant **pas une loi de puissance robuste**. À λ=10,
les cinq seeds passent la régression descriptive hors taille 1
(R²=0,908–0,974), mais le LR discret correctement renormalisé rejette la loi de
puissance au profit de la lognormale tronquée sur 2/5 seeds (p=0,035 et 0,007).
À λ=20, les trois LR sont non conclusifs (p=0,319–0,883), mais une seed manque
de peu le seuil R² (0,898). Verdict honnête : **candidat proche d'un régime
critique, cutoff extensif établi, SOC robuste non établie**.

## Mécanisme causal candidat

En une phrase : **le crédit productif accumule lentement des chaînes de dettes
nominales ; un choc sectoriel fait tomber des emprunteuses, la perte de leurs
créances peut rendre les prêteuses insolvables, et la cascade annule/transfère
les contrats, relaxant le levier avant sa reconstruction**.

La propagation est endogène au réseau, mais l'ablation iid montre que la
sectorialité reste nécessaire pour étendre le cutoff : à λ=10 et T=4000, les
trois seeds iid donnent max=6/9/7 contre 16–21 avec secteurs. Il ne faut donc pas
présenter le résultat comme indépendant de la corrélation externe.

## Méthode

- RNG du moteur : instance locale de `random.Random(seed)` ; jamais le RNG global.
- Burn-in : `max(400, T/4)` ; aucun fit sur le transitoire.
- Aucun pooling inter-seeds pour les ajustements. Chaque `validation.json` est
  calculé depuis `config.json`, `summary.json`, `series.csv`, `avalanches.csv` et
  les snapshots `.npz` du run.
- Double régression fréquence–taille exacte, avec et sans taille 1.
- Queue : loi de puissance **discrète** normalisée par la zêta de Hurwitz ;
  alternative lognormale discrétisée et **renormalisée sur s>=xmin** ; LR de
  Vuong. Le test de queue porte sur les tailles >1, conformément au marqueur M4.
- Distributions NW/K/revenu : réutilisation directe de l'échelle existante de
  13 familles (`recherche/analyse_distributions_taille_revenu/scripts/families.py`),
  plus les fits tronqués du moteur M4.
- Renouvellement : survie/persistance du top décile entre deux snapshots séparés,
  jamais mortalité instantanée.

## Résultats factuels

### Baseline et candidat λ=10

| régime | seeds | population post burn-in | max | R² hors 1 | LR puissance non rejetée |
|---|---:|---:|---:|---:|---:|
| baseline M4 existante (`d0=28`) | 1 | 155,7 | 7 | 0,977 | non (p=0,040) |
| sans `d0`, iid | 3 | 312,9–322,2 | 6–9 | 0,945–0,992 | 2/3 |
| sans `d0`, sectoriel | 5 | 313,8–321,4 | 16–21 | 0,908–0,974 | 3/5 |

Les pentes de population post burn-in sont comprises entre -0,0056 et
+0,0025 entité/pas à λ=10. Aucun run n'est une extinction ou une explosion.

### Scaling en taille finie

| λ | seeds | population médiane | max par seed | médiane max | médiane p99 multi | max/pop |
|---:|---:|---:|---|---:|---:|---:|
| 5 | 3 | 160 | 7 / 9 / 7 | 7 | 6,0 | 4,4–5,6 % |
| 10 | 5 | 318 | 18 / 18 / 17 / 21 / 16 | 18 | 9,8 | 5,1–6,7 % |
| 20 | 3 | 636 | 37 / 23 / 24 | 24 | 13,0 | 3,6–5,8 % |

Le maximum 37 est le plus grand obtenu dans cette session. Il n'est pas compté
comme succès isolé : la médiane et le p99 croissent aussi, et max/pop ne croît
pas vers 1. La seed 37 n'est donc pas un effondrement quasi total.

### Robustesse temporelle

Sur les cinq trajectoires λ=10/T=4000, le préfixe analysé comme T=2000
([500,2000]) donne max=16–20 et R²=0,878–0,970 ; la fenêtre tardive
([2000,4000]) donne max=9–21 et R²=0,902–0,974. Les niveaux de cutoff fluctuent
entre fenêtres, mais ne montrent ni dérive démographique ni apparition tardive
unique. Le LR devient plus discriminant avec plus d'observations : deux rejets
sur la fenêtre complète, contre aucun sur les préfixes T=2000. Cette sensibilité
est une raison supplémentaire de ne pas annoncer une loi de puissance robuste.

### Renouvellement et distributions d'entités

À λ=10 sectoriel, sur des fenêtres séparées d'environ 1500 pas : survie du top
décile 6,2–18,8 %, persistance dans le top 0–13,8 %, et 65–84 % du top final est
né dans les 1000 derniers pas. Le renouvellement demandé est donc présent.

L'échelle de 13 familles trouve, sur les cinq snapshots finaux λ=10 :

- NW : mélange de deux lognormales 4/5, gamma généralisée 1/5 ;
- K : exponentielle 2/5, Dagum 1/5, lognormale 1/5, mélange lognormal 1/5 ;
- revenu : mélange de deux lognormales 4/5, lognormale 3 paramètres 1/5.

Ces formes sont reconnaissables mais moins stables que les verdicts M3
(NW Fisk, K lognormal, revenu dPlN). Le mélange lognormal est à surveiller : le
rapport de référence montre qu'il peut proxyfier des cohortes. Ici le fort
renouvellement exclut une aristocratie fondatrice figée, sans prouver que le
mélange ait une interprétation économique structurelle. La contrainte de famille
est donc satisfaite au sens faible « famille identifiable », pas au sens d'une
loi empirique unique robuste sur toutes les seeds.

## Hypothèses infirmées dans cette session

Toutes les conditions de conclusion ont été écrites dans `NOTES.md` avant run.

- Zéro-recouvrement des actifs résiduels : max 15/20/15 ; 2/3 LR anti-puissance.
- Appétit de crédit adaptatif multipliant la cible K : A reste près du plafond,
  max 11–12 ; le capital supplémentaire stabilise plus qu'il ne fragilise.
- Portefeuilles limités à trois contreparties : population déjà 5604–5896 à
  t=1000 et carnet 153 k–440 k ; runs arrêtés comme divergents.
- Crédit vers L plutôt que K : marché actif mais max 6/6/8.
- Seuil de capital NW/dette à 10 %, puis test de principe à 30 % : racines
  prudentielles actives, mais max respectivement 9–18 puis 9–13.

## Modifications et invariants

- `d0` est entièrement absent de `src/m4` : configuration, valeur nette et
  snapshots. La mortalité vient uniquement des contrats et des chocs.
- `ModelRNG` encapsule `random.Random(seed)` et fournit normale, Poisson exact,
  échantillonnage et secteurs.
- Le carnet conserve `merge_pairs`, l'égalité créances=dettes, l'absence de
  contrats orphelins et le point fixe de cascade.
- Dix tests couvrent le bilan global par pas, reproductibilité, neutralité des
  snapshots, RNG global intact, marché, fusion/carnet, cascade, seuil expérimental
  et estimateurs synthétiques (dont lognormale tronquée non biaisée pro-Pareto).

## Artefacts principaux

- `validation_aggregate.json` : faits et inférences par run.
- `figures/finite_size_scaling.png` : scaling et garde anti-effondrement.
- `figures/baseline_candidate_cascades.png` : comparaison baseline/candidat.
- `figures/distribution_family_winners.png` : familles sur cinq seeds λ=10.
- Chaque run sélectionné contient son propre `validation.json` et ses figures
  `cascades_rank_size.png` avec les deux régressions.

## Conclusion

Le programme dépasse de façon robuste la baseline max=7 et établit un cutoff qui
croît avec N, sans extinction. Il ne satisfait toutefois pas simultanément les
trois critères forts : le R² est presque toujours bon et le scaling est positif,
mais le LR corrigé n'est pas robuste à λ=10. Le bon résultat scientifique est
donc un **régime pré-critique/extensif prometteur**, pas une SOC démontrée.

