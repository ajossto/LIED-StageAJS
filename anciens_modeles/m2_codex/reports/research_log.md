# Journal de recherche M2

## 2026-07-03 — Inventaire et cadrage initial

- **Fichiers ajoutés** : `reports/00_inventory.md`, `reports/research_log.md`.
- **Travail effectué** : inventaire de l'arborescence, identification du rapport
  M2, de sa version LaTeX, du prototype M1, des sondes anti-cohorte, des logs,
  des lignées WIP et du laboratoire de simulation.
- **Expériences lancées** : aucune ; l'implémentation et les simulations sont
  volontairement différées jusqu'à la lecture critique et la spécification.
- **Résultat** : le rapport source et ses annexes sont présents. Il n'existe pas
  encore d'implémentation M2 isolée ni de validation multi-seed automatisée.
- **Risque rencontré** : arbre Git déjà très sale, incluant des modifications et
  fichiers non suivis hors périmètre. Décision de ne toucher qu'aux nouveaux
  chemins M2 et `reports/`.
- **Hypothèse à tester** : les verdicts E0--E7 sont des résultats exploratoires,
  non une démonstration de Boltzmann--Pareto ni de SOC.
- **Prochaine étape** : lecture intégrale du rapport et reconstruction critique
  des règles, ambiguïtés et prédictions réfutables.

## 2026-07-03 — Lecture critique, spécification et noyau testé

- **Fichiers ajoutés** : rapports `01_critical_reading` et
  `02_technical_spec`, paquet `src/m2/`, quatre scripts sous `experiments/m2/`,
  tests sous `tests/`, `README.md`.
- **Décision d'isolation** : tous les livrables ont été déplacés sous
  `anciens_modeles/m2_codex/` à la demande de l'utilisateur, afin d'éviter les collisions avec
  un autre agent.
- **Résultats conceptuels** : le point fixe 400 du rapport est celui de l'ODE ;
  avec l'ordre extraction puis dépréciation, la carte discrète a pour point fixe
  exact `((1-delta) alpha/delta)^2`. La dette `d0` est un seuil sans créancier,
  et plusieurs règles de liquidation étaient sous-spécifiées.
- **Choix implémentés** : intérêts simultanés prorata par emprunteur ; exclusion
  du marché des défaillantes ; liquidation par identifiant ; créances
  fractionnées et traçables ; résiduel détruit sans créancier admissible.
- **Tests** : 26 tests passent avec `unittest`, couvrant bilans, principal,
  intérêts complets/partiels, faillites, cascade, orphelins, seeds et cas limites,
  ainsi que données exponentielles/Pareto synthétiques.
- **Expériences** : smoke-test baseline 50 pas, seed 0. Population finale 224,
  241 faillites cumulées, 2 contrats actifs. Le pipeline d'artefacts et de
  validation fonctionne. À cet horizon, Fisk gagne l'AIC du corps de NW ; aucune
  conclusion de régime n'est permise.
- **Erreur/limite rencontrée** : SciPy émet des warnings d'overflow lors des
  explorations numériques extrêmes du fit Fisk ; ils sont diagnostiques de
  l'optimiseur, pas des données de simulation, et seront confinés.
- **Hypothèse infirmée à ce stade** : aucune sur le régime long ; le smoke-test
  confirme seulement que l'exponentielle ne doit pas être supposée.
- **Prochaine étape** : baseline 2000 pas multi-seed, validation par fenêtres,
  puis grille/ablations dans la limite du coût calculatoire.

## 2026-07-03 — Résultat négatif numérique : explosion des fractions

- **Expérience** : baseline seed 0 visée à 2000 pas, d'abord avec audits complets,
  puis sonde sans audits jusqu'au seuil de 100000 contrats.
- **Résultat** : 3482 contrats à `t=1200`, 25243 à `t=1300`, 74807 à `t=1400`,
  142766 à `t=1414`. Le premier run a été interrompu après 178 s et un pic RSS
  de 588 Mo.
- **Interprétation** : le transfert prorata fractionne récursivement les
  créances. L'encours économique ne justifie pas cette croissance du nombre
  d'objets ; c'est un artefact de représentation susceptible d'empêcher toute
  validation longue.
- **Décision** : fusion exacte par paire prêteur--emprunteur, principal sommé et
  taux moyen pondéré. Cette opération préserve tous les flux et bilans du modèle
  nominal perpétuel. Elle ne fixe aucune taille minimale et ne supprime aucun
  montant.
- **Limite** : la lignée complète de chaque fraction n'est plus stockée ; un
  compteur de composantes est conservé. Le rapport technique reçoit un
  amendement explicite, sans réécriture rétroactive de la décision initiale.

## 2026-07-03 — Baselines, grille, ablations et verdict final

- **Fichiers produits** : trois runs `outputs/baseline_seed_{0,1,2}`, analyses
  JSON, tableaux et figures ; grille `outputs/grid_screen` (36 cas) ; ablations
  courtes ; ablation longue `no_credit` ; rapports 03, 04, 05 et synthèse finale.
- **Tests** : 27 tests passent. Les cinq rapports LaTeX compilent avec
  `latexmk -pdf`.
- **Baselines** : populations finales 1672/1680/1677 ; faillites cumulées
  18242/18379/18281. Pentes de population encore positives sur `[1000,2000]`.
- **Corps** : Fisk gagne pour `NW` dans les trois seeds ; ΔAIC exponentielle
  61,2/61,7/80,4. Sur 36 cas de grille : 35 Fisk, 1 log-normal, 0 exponentiel.
- **Queue** : exposants `NW` globalement autour de 2,8, mais seed 2 varie de 2,54
  à 3,05 avec saut de `xmin`. Les LR Pareto moins log-normale tronquée sont tous
  négatifs ; une comparaison du prototype était biaisée par l'absence de
  renormalisation de la log-normale sur la queue.
- **Cohortes** : corrélation âge–log(NW) 0,064--0,155 ; mortalité du top
  86--91 % ; top presque entièrement renouvelé. Hypothèse anti-cohorte soutenue.
- **SOC** : tailles de lots de faillites similaires pour `k=2,3,4,6`, aucun lien
  positif entre HHI précédent et faillites. L'ablation sans crédit à 2000 pas
  conserve corps Fisk, queue apparente et renouvellement. L'explication SOC du
  crédit n'est pas soutenue.
- **Robustesse** : à `sigma=0.15`, plusieurs configurations ont presque aucune
  mortalité et une croissance quasi linéaire. Le régime dépend fortement de la
  fenêtre de naissance ; absence de réglage fin infirmée partiellement.
- **Hypothèses infirmées** : corps exponentiel, exposant commun revenu/NW,
  nécessité du crédit, robustesse globale.
- **Hypothèses soutenues** : classes dynamiques, mortalité endogène sur la
  baseline, reproductibilité inter-seed du niveau de population.
- **Décision finale** : rapporter une réfutation partielle substantielle, sans
  tenter d'améliorer le corps par changement de règles après inspection.
- **Prochaines étapes** : horizons 4000--10000, réplications des frontières de
  grille, invariance de temps, avalanches causales et prédiction hors échantillon.
