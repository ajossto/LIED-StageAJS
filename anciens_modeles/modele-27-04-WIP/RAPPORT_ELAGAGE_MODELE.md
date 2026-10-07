# Rapport exploratoire - elagage du modele 27-04-WIP

Date: 2026-04-27

Ce rapport porte sur `modele-27-04-WIP`. Une sauvegarde zip du dossier existe avant la suite de l'exploration dans `banque_versions_zip/modele-27-04-WIP_sauvegarde_20260427_131601.zip`.

## 1. Compréhension du projet général

Le projet ne vise pas seulement une simulation multi-agents plausible. Il cherche un noyau minimal pour une classe de systèmes complexes où des entités transforment un stock/bilan en flux, accumulent, dissipent, et deviennent interdépendantes par une règle artificielle de crédit. Le modèle intéressant doit donc rester proche de contraintes robustes:

- flux d'extraction;
- accumulation de capacité;
- depreciation/irreversibilite;
- bilans actif/passif;
- redistribution ou destruction lors des faillites;
- reseau de dependances par credit.

La question structurante est: quelles règles suffisent pour produire un régime collectif non trivial, et quelles règles ne sont que des raffinements numériques ou narratifs?

## 2. Compréhension du modèle actuel

Le modèle courant combine trois couches.

La couche thermodynamique minimale est la relation `Pi_i = alpha_i * sqrt(P_i)`, avec rendements décroissants du passif/capital `P_i`. Les entités extraient un flux depuis leur base productive, accumulent en capital endogène, et subissent une depreciation.

La couche crédit ajoute un taux interne marginal:

```text
r*_i = alpha_i / (2 * sqrt(P_i))
```

Les grandes entités ont généralement un `r*` faible et deviennent prêteuses; les petites ou plus productives ont un `r*` élevé et deviennent emprunteuses. Les prêts sont perpétuels par défaut (`taux_amortissement = 0`), paient des intérêts, et créent du capital exogène chez l'emprunteur.

La couche réseau/faillite vient de trois règles: appariement local aléatoire du crédit (`n_candidats_pool`), cession/fractionnement de créances en cas d'illiquidité ou faillite, et résolution itérative des insolvabilités. Elle donne un réseau de dépendances où une perte locale peut se propager.

## 3. Mécanismes soupçonnés centraux

- La loi d'extraction concave `sqrt(P)` est centrale: elle crée un rendement marginal décroissant, donc une base naturelle pour le prêt entre entités hétérogènes.
- L'hétérogénéité individuelle de `alpha` est centrale: elle suffit à créer une dispersion de `r*`. Le Brownien temporel semble secondaire, mais pas l'hétérogénéité initiale.
- L'auto-investissement est central: sans conversion du surplus liquide en capital endogène, le système devient riche en liquide mais pauvre en réseau de crédit.
- Le crédit avec intérêts perpétuels est central pour les phénomènes recherchés: réseau, classes financières, faillites, cascades.
- Le matching local avec `k >= 3` est central pour les intermédiaires: `k=1` et `k=2` produisent peu ou pas de cascades en régime observé.
- La depreciation exogène et la réévaluation des créances semblent centrales pour maintenir une fragilité financière; sans elle, le système croît fortement et ne produit plus de faillites dans les tests.
- Les naissances ne sont pas le mécanisme du crédit, mais elles sont importantes pour le régime quasi-stationnaire: sans entrées, la population se vide ou se contracte fortement.

## 4. Mécanismes soupçonnés accessoires

- Le Brownien sur `alpha` n'est pas indispensable: le régime post-500 reste proche avec `alpha_sigma_brownien = 0` si les `alpha` individuels restent hétérogènes.
- La contrainte d'endettement, dans les valeurs testées, change peu le régime court. Elle peut rester utile comme garde-fou, mais elle n'a pas encore le statut de mécanisme générateur.
- La reliquéfaction endogène forcée et la cession de créances en paiement n'ont pas changé les métriques du panel court. Cela indique surtout qu'elles sont peu sollicitées dans ce protocole, pas qu'elles sont conceptuellement inutiles en cas de stress.
- Le seuil `epsilon = 1e-3` conserve le régime qualitatif du baseline sur 300 pas. Les micro-flux peuvent probablement être traités par seuil explicite plutôt que par passage global aux entiers.
- Le détail comptable entre certaines composantes d'actif/passif pourrait être simplifiable, mais il faut conserver au moins une distinction fonctionnelle entre capital endogène productif, capital exogène financé par prêt, et créances financières si l'on veut étudier les cascades.

## 5. Stratégie expérimentale proposée

J'ai utilisé une stratégie d'ablations ciblées plutôt qu'un plan exhaustif. Le but était de tester les mécanismes dominants:

- supprimer ou homogénéiser `alpha`;
- supprimer les naissances;
- supprimer le crédit;
- varier la taille locale du marché (`k=1`, `k=2`, `k=5`);
- supprimer l'auto-investissement;
- supprimer la depreciation exogène;
- tester un seuil numérique plus grossier;
- tester un arrondi centime et un arrondi entier;
- augmenter `alpha` de 10% pour sonder l'effet rebond.

Deux niveaux de lecture ont été distingués:

- panel 300 pas, 3 seeds, burn-in 150: criblage rapide des mécanismes;
- contrôle 1000 pas, burn-in 500: lecture plus pertinente du régime permanent ou quasi-permanent.

Le panel 300 pas ne doit pas être surinterprété, car le régime transitoire dure environ 500 pas.

## 6. Variantes testées

Les variantes sont implémentées dans `experiments/elagage_experiments.py`.

| Variante | Question testée |
| --- | --- |
| `baseline` | Référence WIP |
| `no_brownian_alpha` | Le Brownien temporel est-il nécessaire? |
| `common_static_alpha` | Une productivité commune suffit-elle? |
| `no_births` | Le renouvellement démographique est-il nécessaire? |
| `no_credit` | Que reste-t-il sans règle artificielle de crédit? |
| `k1_pure_arbitrage` | Matching pur sans intermédiaires naturels |
| `k2_pool` | Marché local sous le seuil critique supposé |
| `k5_pool` | Marché local plus dense et plus contagieux |
| `no_debt_constraint` | La contrainte d'endettement est-elle structurante? |
| `no_reliquefaction` | La vente forcée du capital endogène est-elle utilisée? |
| `no_claim_transfer` | La cession de créances en paiement est-elle utilisée? |
| `no_auto_invest` | L'accumulation endogène est-elle nécessaire? |
| `exo_no_depreciation` | La depreciation exogène est-elle nécessaire à la fragilité? |
| `epsilon_1e_3` | Les micro-flux sont-ils structurants? |
| `round_cent` | Arrondi type fixed-point centime |
| `round_integer` | Arrondi entier brutal |
| `alpha_plus_10pct` | Test simple d'effet rebond |

## 7. Métriques retenues

J'ai défini un phénotype minimal du modèle:

- extraction moyenne après burn-in;
- nombre moyen de transactions de crédit après burn-in;
- nombre moyen de prêts actifs après burn-in;
- population moyenne après burn-in;
- nombre total de faillites;
- nombre d'événements de cascade et taille maximale;
- densité finale du réseau de prêts;
- degré moyen entrant/sortant;
- part d'intermédiaires, définis comme entités à la fois prêteuses et emprunteuses;
- Gini du passif;
- Gini de liquidité;
- ratio `P90/P10` du passif comme proxy de séparation en classes;
- temps par pas.

Ces métriques ne cherchent pas l'égalité trajectoire par trajectoire. Elles caractérisent le régime collectif.

## 8. Résultats obtenus

### Criblage 300 pas, 3 seeds

Le panel court sert uniquement à repérer les directions fortes. Les résultats complets sont dans `experiments/results/elagage_aggregate.csv`.

| Variante | Extraction tail | Tx crédit | Prêts actifs tail | Faillites | Intermédiaires | Temps ms/pas |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `baseline` | 14222 | 20.3 | 2280 | 14.3 | 0.563 | 8.72 |
| `no_brownian_alpha` | 13811 | 21.5 | 2369 | 16.3 | 0.583 | 8.51 |
| `common_static_alpha` | 14306 | 2.46 | 558 | 0.0 | 0.153 | 4.56 |
| `no_credit` | 13634 | 0.0 | 0 | 0.0 | 0.000 | 3.34 |
| `k1_pure_arbitrage` | 14426 | 0.41 | 106 | 0.0 | 0.014 | 4.00 |
| `k2_pool` | 13745 | 3.73 | 736 | 0.0 | 0.249 | 5.14 |
| `k5_pool` | 11579 | 61.4 | 7640 | 244 | 0.717 | 18.53 |
| `no_auto_invest` | 7586 | 0.01 | 12 | 0.0 | 0.000 | 3.57 |
| `exo_no_depreciation` | 15563 | 5.61 | 1088 | 0.0 | 0.424 | 5.99 |
| `round_integer` | 13937 | 1.15 | 367 | 0.0 | 0.160 | 6.71 |

Lecture principale du criblage:

- `no_brownian_alpha` est proche du baseline: le Brownien n'est pas nécessaire au régime court.
- `common_static_alpha` garde l'extraction mais détruit largement le réseau financier et les faillites: l'hétérogénéité initiale compte.
- `no_credit`, `k1`, `k2`, `round_integer` détruisent les cascades.
- `k5` crée un réseau très dense, coûteux, et très destructeur.
- `no_auto_invest` détruit le mécanisme d'accumulation productive et presque tout crédit.
- `exo_no_depreciation` supprime les faillites et ouvre une croissance plus forte.

### Contrôle 1000 pas, burn-in 500

Ce contrôle est plus pertinent pour le régime permanent. Les résultats complets sont dans `experiments/results/targeted_1000_aggregate.csv`; un complément rebond est dans `experiments/results/rebound_1000_runs.csv`.

| Variante | Extraction post-500 | Tx crédit | Prêts actifs | Faillites | Cascades | Intermédiaires | Temps ms/pas |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `baseline` | 16472 | 52.0 | 21428 | 1478 | 600 | 0.746 | 45.8 |
| `no_brownian_alpha` | 15697 | 48.5 | 19567 | 1458 | 604 | 0.708 | 40.4 |
| `common_static_alpha` | 42350 | 1.35 | 1497 | 5 | 5 | 0.100 | 11.5 |
| `no_credit` | 42013 | 0.0 | 0 | 0 | 0 | 0.000 | 8.8 |
| `k2_pool` | 43038 | 3.45 | 2526 | 7 | 7 | 0.228 | 14.4 |
| `k5_pool` | 8531 | 59.7 | 51827 | 1751 | 725 | 0.711 | 111.7 |
| `no_auto_invest` | 21936 | 0.00 | 12 | 0 | 0 | 0.000 | 9.1 |
| `exo_no_depreciation` | 50856 | 8.34 | 4760 | 0 | 0 | 0.504 | 18.2 |
| `round_integer` | 43405 | 0.32 | 674 | 0 | 0 | 0.104 | 16.5 |
| `alpha_plus_10pct` | 16776 | 52.9 | 27371 | 1577 | 602 | 0.739 | 52.2 |

Le contrôle post-500 renforce les conclusions: plusieurs variantes qui semblaient seulement "moins financières" sur 300 pas deviennent des régimes alternatifs très différents sur 1000 pas. `no_credit`, `k2_pool`, `common_static_alpha` et `round_integer` produisent une forte extraction moyenne, mais sans le régime de réseau dense, d'intermédiation et de faillites qui caractérise le modèle courant.

## 9. Comparaison modèle actuel / variantes simplifiées

Le modèle actuel n'est pas minimal, mais son régime intéressant dépend de peu de leviers:

- `baseline` et `no_brownian_alpha` sont proches: on peut retirer le Brownien pour simplifier sans perdre le régime collectif principal.
- `baseline` et `alpha_plus_10pct` restent proches en structure, mais le réseau devient plus volumineux: l'amélioration de productivité est absorbée par une extension financière.
- `common_static_alpha` n'est pas une bonne simplification si l'on veut conserver les classes financières: homogénéiser `alpha` détruit la différenciation de rôle.
- `k2_pool` et `k1` ne sont pas de bonnes simplifications si l'on veut les cascades: elles stabilisent trop le crédit.
- `k5_pool` n'est pas une bonne direction de travail: il amplifie le réseau et le coût de calcul, avec un régime plus destructeur.
- `no_auto_invest` et `no_credit` ne sont pas des modèles sociaux/economiques comparables: ils servent de témoins négatifs.
- `exo_no_depreciation` est informatif: la depreciation des actifs financés et des créances semble être un mécanisme de fermeture/régulation, pas un simple détail comptable.

## 10. Discussion float / int / fixed-point

Le passage naïf aux entiers n'est pas recommandé.

Dans les tests, `round_integer` n'est pas seulement une optimisation numérique: il transforme le régime. Sur 1000 pas post-500, il donne une extraction élevée, presque aucune transaction de crédit, peu de prêts actifs, aucune faillite et une très faible séparation en classes. Il agit donc comme un élagage brutal des micro-flux financiers, pas comme une représentation équivalente.

`round_cent` conserve mieux le régime court, mais ralentit l'exécution dans ce prototype, car l'arrondi de tous les champs à chaque pas ajoute du coût Python. Ce test ne prouve pas qu'un vrai fixed-point optimisé serait lent, mais il montre que l'arrondi explicite global n'est pas une optimisation gratuite.

Si l'on change d'échelle, il faut transformer `alpha`. Si les stocks sont codés en unités multipliées par `F`, il faut préserver:

```text
Pi' = F * Pi
Pi' = alpha' * sqrt(P')
P' = F * P
donc alpha' = sqrt(F) * alpha
```

Sans cette transformation, le changement d'unité modifie la dynamique.

Recommandation numérique:

- garder `float` pour le modèle de recherche courant;
- introduire plutôt des seuils explicites sur les micro-prêts, micro-intérêts ou micro-cessions;
- tester un fixed-point seulement si l'on définit d'abord la sémantique des arrondis;
- ne pas vendre le passage aux entiers comme optimisation tant qu'un benchmark Python réel ne le montre pas.

## 11. Discussion sur l'effet rebond endogène

Le test simple `alpha_plus_10pct` augmente `alpha_min` et `alpha_max` de 10%.

Sur 1000 pas, burn-in 500, avec 3 seeds combinés pour `baseline` et `alpha_plus_10pct`:

| Métrique | Baseline | Alpha +10% | Ratio |
| --- | ---: | ---: | ---: |
| Extraction post-500 | 16115 | 16942 | 1.051 |
| Transactions de crédit | 51.0 | 49.6 | 0.972 |
| Prêts actifs post-500 | 22355 | 24992 | 1.118 |
| Prêts actifs finaux | 22068 | 27623 | 1.252 |
| Faillites totales | 1474 | 1529 | 1.037 |
| Cascades | 599 | 616 | 1.028 |
| Gini passif | 0.187 | 0.195 | 1.041 |
| Gap P90/P10 passif | 2.265 | 2.406 | 1.063 |

Interprétation prudente: il existe déjà une forme crédible d'effet rebond endogène. L'amélioration locale de productivité ne réduit pas la pression extractive; elle augmente l'extraction moyenne et élargit surtout le stock de prêts actifs. Une partie du gain semble absorbée par l'expansion financière et la différenciation plutôt que par une baisse de pression sur la ressource.

Ce n'est pas encore une théorie complète de l'effet rebond. Il manque une expérience où l'amélioration porte sur l'efficacité d'usage d'une ressource bornée, avec ressource totale suivie explicitement. Mais le mécanisme minimal "gain local -> plus grande capacité d'endettement/investissement -> réseau plus volumineux -> extraction non réduite" est déjà présent.

## 12. Proposition de modèle minimal candidat

Le candidat minimal pour continuer n'est pas `baseline` inchangé, mais:

```text
Noyau thermodynamique:
  P_i >= 0
  Pi_i = alpha_i * sqrt(P_i)
  depreciation endogene et exogene
  auto-investissement d'une fraction du surplus
  naissances simples pour fermer la démographie

Noyau hétérogénéité:
  alpha_i tire une fois a la naissance
  pas de Brownien temporel dans la première version analytique

Noyau crédit:
  r*_i = alpha_i / (2 sqrt(P_i))
  prêts perpétuels avec intérêts
  matching local k=3
  taux entre r*_preteur et r*_emprunteur
  volume plafonné par offre/demande

Noyau fragilité:
  depreciation exogene des actifs financés
  réévaluation des créances
  faillite si actif_total < passif_bilan
  redistribution ou annulation des créances en faillite
```

Ce candidat supprime le Brownien sur `alpha` et garde `k=3`, l'auto-investissement, le crédit, les naissances et la depreciation exogène. Il est plus simple sans perdre le régime collectif principal observé.

## 13. Incertitudes restantes

- Les tests 1000 pas n'ont qu'un panel ciblé; seules `baseline` et `alpha_plus_10pct` ont 3 seeds post-500.
- La stationnarité doit être testée par fenêtres temporelles multiples, par exemple 500-1000, 1000-1500, 1500-2000.
- Les métriques de cascade doivent être enrichies par distributions de tailles, pas seulement moyennes et maxima.
- La reliquéfaction et la cession de créances n'ont pas été stressées; elles peuvent être inutiles en régime normal mais importantes lors de chocs.
- L'effet rebond doit être testé avec une ressource explicitement bornée ou un indicateur de pression écologique plus direct.
- La distinction endo/exo peut être simplifiable, mais la suppression complète de la depreciation exogène montre qu'il faut conserver une source de fragilité sur les créances.
- Les performances sont dominées par la taille du réseau de prêts; toute variante qui augmente les prêts actifs dégrade fortement le coût.

## 14. Prochaines expériences

1. Lancer un protocole régime permanent: 2000 pas, burn-in 500, métriques par fenêtres de 500 pas, sur 3 à 5 seeds.
2. Restreindre ce protocole à 6 variantes: `baseline`, `no_brownian_alpha`, `common_static_alpha`, `k2_pool`, `k5_pool`, `exo_no_depreciation`.
3. Ajouter une variante `k3_no_brownian` comme candidat minimal principal.
4. Tester des seuils explicites: montant minimal de prêt, intérêt minimal, cession minimale, plutôt qu'un arrondi global.
5. Tester un choc local: augmenter `alpha` d'une sous-population ou d'une classe et mesurer propagation, dette, faillites et extraction.
6. Ajouter une métrique de distribution des cascades: histogramme ou quantiles des tailles.
7. Formaliser un modèle moyen-champ à partir du candidat minimal: dynamique de `P`, distribution de `alpha`, taux marginal `r*`, densité de prêts, condition de solvabilité.

## Conclusion

Des simplifications semblent possibles. La plus nette est de supprimer le Brownien temporel de `alpha` et de conserver seulement une hétérogénéité individuelle fixe à la naissance. Les seuils numériques explicites sont aussi préférables à une représentation entière globale.

Certaines simplifications détruisent la dynamique recherchée. Homogénéiser complètement `alpha`, supprimer le crédit, supprimer l'auto-investissement, passer à `k <= 2`, supprimer la depreciation exogène, ou arrondir brutalement aux entiers changent le régime au lieu de l'élaguer.

Les mécanismes probablement indispensables sont: extraction concave, hétérogénéité productive, auto-investissement, crédit à intérêts perpétuels, matching local autour de `k=3`, depreciation/réévaluation des actifs financés, et faillites avec propagation par créances. Les mécanismes probablement dispensables dans un premier modèle minimal sont: Brownien sur `alpha`, amortissement du principal, raffinement fin de certains paiements par reliquéfaction/cession hors scénarios stressés, et représentation entière.

La version recommandée pour continuer est donc un `baseline` simplifié sans Brownien d'`alpha`, avec `k=3`, floats, seuils explicites sur micro-flux, et instrumentation stationnaire plus forte. Le noyau minimal qui semble porter l'émergence est:

```text
flux concave + hétérogénéité fixe + auto-investissement + crédit perpétuel local + depreciation des actifs financés + faillites en réseau
```

Le modèle contient déjà une forme crédible d'effet rebond endogène: une hausse de productivité augmente l'extraction post-transitoire et étend le réseau de prêts plutôt que de réduire la pression globale. Pour en faire un objet mathématique plus formel, il faut maintenant réduire ce noyau en équations de bilan, isoler une loi d'appariement simplifiée, puis comparer les prédictions moyen-champ aux distributions simulées.
