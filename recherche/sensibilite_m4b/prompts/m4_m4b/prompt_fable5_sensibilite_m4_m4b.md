# Prompt Fable 5 — Campagne de sensibilité des modèles M4 et M4B

> À exécuter de préférence avec l'effort `xhigh`. La mission est une campagne
> de recherche numérique de bout en bout, pas seulement la rédaction d'un plan.

## Rôle et objectif scientifique

Tu es responsable d'une étude de sensibilité reproductible sur les modèles de
société de crédit M4 et M4B. Travaille comme chercheur en économophysique,
systèmes complexes et simulation stochastique : conçois le protocole, audite
les moteurs, exécute les simulations, analyse les résultats et rédige le
rapport final en français.

L'objectif n'est ni de chercher la configuration qui « donne le plus de SOC »,
ni de reconfirmer sélectivement le rapport M4. Il faut cartographier honnêtement :

1. quels paramètres contrôlent le régime démographique, le réseau de crédit,
   les faillites en cascade et les distributions individuelles ;
2. où se trouvent les non-linéarités, seuils, interactions et changements de
   régime ;
3. quelles conclusions de M4 sont robustes dans une plage de paramètres et
   lesquelles dépendent d'un choix institutionnel ;
4. si M4B reproduit bien M4 sur le sous-espace commun, sans traiter ces deux
   implémentations d'une même mécanique comme deux preuves indépendantes.

Quand tu as assez d'information pour agir, agis. Mène la mission jusqu'aux
résultats et au rapport vérifié ; ne termine pas sur un simple plan ou une
promesse d'exécution.

## Répertoire de travail et sources obligatoires

Travaille dans `/home/anatole/jupyter`. Utilise le Python du venv :
`/home/anatole/jupyter/.venv/bin/python3`.

Lis intégralement avant de figer le protocole :

- guide Fable :
  `/home/anatole/jupyter/modeles/m4_credit_soc/Prompting Claude Fable.md` ;
- rapport scientifique M4 :
  `/home/anatole/jupyter/modeles/m4_credit_soc_fable/reports/01_soc_final/main.pdf`
  et sa source `main.tex` ;
- journal, configuration, moteur, statistiques et campagnes M4 :
  `modeles/m4_credit_soc_fable/NOTES.md`, `src/m4/`, `experiments/m4/` et `tests/` ;
- spécification M4B : `modeles/m4b_credit_soc_mini/README.md` et
  `modeles/m4b_credit_soc_mini/report/mecanique_m4b.pdf` (source `.tex` disponible) ;
- moteur et sorties M4B : `modeles/m4b_credit_soc_mini/m4b/`, `run.py` et `tests/` ;
- intégration actuelle de M4B dans Simulation Lab :
  `modeles/adaptateurs/m4b_credit_soc_mini/` et
  `simulation_lab/`.

Crée tous les scripts, résultats, figures, notes et rapports propres à cette
étude dans :

`/home/anatole/jupyter/recherche/sensibilite_m4_m4b/`

Traite comme **sources en lecture seule** les moteurs `modeles/m4_credit_soc_fable/src/`
et `modeles/m4b_credit_soc_mini/m4b/`, leurs tests, leurs rapports existants et tous
les résultats antérieurs. Ne modifie pas la dynamique pour faciliter l'étude.
Une lacune d'instrumentation doit être contournée dans les scripts de campagne
ou signalée ; elle ne justifie pas silencieusement une nouvelle version du
modèle.

## Relation exacte entre M4 et M4B

Ne pars pas de l'hypothèse erronée qu'il s'agit de deux modèles concurrents.
M4B est une réduction indépendante qui reproduit la configuration finale de
M4. Sur leur sous-espace commun, la trajectoire doit être identique à graine
et configuration identiques.

Paramètres scientifiques communs à étudier dans M4B :

- `lam` : intensité des naissances et axe de taille du système ;
- `delta` : dépréciation du capital ;
- `sigma` : volatilité du choc multiplicatif ;
- `K0` : capital de naissance ;
- `k` : taille de l'échantillon du marché local.

`seed` et `T` définissent la réplication et l'horizon expérimental.
`pop_max` est un garde-fou d'arrêt, pas un mécanisme de bornage. `alpha=1` et
les tolérances numériques sont des conventions/constantes et ne doivent pas
être promues artificiellement en paramètres scientifiques.

M4 seul expose les choix structurels retirés de M4B, notamment `credit`,
`objective`, `rounds_div`, les variantes de naissance, la corrélation des
chocs et les règles de faillite. Utilise M4 uniquement pour cette étude de
robustesse institutionnelle et pour quelques contrôles de parité. Utilise M4B
pour la campagne quantitative sur les paramètres communs. Ne double pas tous
les runs.

## Questions et grandeurs de réponse

Définis avant les runs un dictionnaire des métriques, leur formule, leur unité,
leur fenêtre temporelle, leurs conditions de validité et leur statut primaire
ou secondaire. Au minimum, couvre les familles suivantes.

### Régime et démographie

- statut `ok`, extinction ou arrêt par `pop_max` ;
- population moyenne après burn-in, `N/lam`, pente temporelle et variabilité ;
- naissances, morts, durée de vie et renouvellement ;
- stationnarité vérifiée sur plusieurs fenêtres, pas seulement sur la valeur
  finale.

### Crédit, exposition et réseau

- nombre et volume de prêts, dette rapportée au capital/aux actifs, degrés et
  concentration des expositions ;
- rythme d'accumulation puis d'élagage du carnet autour des grands événements ;
- métriques normalisées par la population lorsque nécessaire.

### Avalanches et propagation causale

- fréquence, quantiles, maximum absolu et maximum rapporté à la population ;
- rapport de branchement, fraction induite, racines/taille et profondeur ;
- susceptibilité ou échelle de coupure, par exemple `<s²>/<s>` ;
- MLE **discret** de la loi de puissance, en présentant notamment le seuil
  `s_min=2`, ajustement loi de puissance avec coupure et comparaison de
  vraisemblance avec une log-normale discrète renormalisée ;
- scaling de la coupure avec la taille du système.

Ne conclus jamais à une loi de puissance sur le seul `r²` d'une régression
log-log. Si un run contient trop peu d'avalanches pour un ajustement fiable,
marque la métrique non identifiable au lieu de produire un nombre trompeur.

### Distributions individuelles et inégalités

- capital `K`, valeur nette, revenu brut/net, Gini et renouvellement du haut de
  la distribution ;
- familles de distribution comparées avec les mêmes supports et les mêmes
  règles de troncature ;
- contrôle par âge/cohorte lorsque l'interprétation distributionnelle peut en
  dépendre.

### Intégrité numérique

- égalité créances-dettes, absence de contrats orphelins, capital non négatif,
  bilan réel par pas et reproductibilité ;
- temps de calcul, volume des données et tout arrêt anticipé.

## Protocole expérimental

### 1. Audit, parité et réutilisation

1. Exécute les suites de tests M4 et M4B.
2. Vérifie au moins deux trajectoires M4/M4B sur des configurations communes
   non triviales. Compare les séries par pas, états, contrats et avalanches,
   pas seulement les moyennes finales.
3. Inventorie les runs existants. Ne réutilise un run que si son moteur, sa
   configuration complète, sa graine, son horizon, son statut et ses fichiers
   primaires sont vérifiables. Un nom de dossier ne suffit pas.
4. Lance un petit benchmark représentatif pour mesurer coût et taille disque,
   puis fixe un budget expérimental défendable. Laisse au moins deux cœurs au
   système et évite la surallocation mémoire/disque.

### 2. Séparer les axes qui n'ont pas le même sens

Traite `lam` d'abord comme axe de taille finie/démographique, et `T` comme axe
de convergence temporelle. Ne les mélange pas sans précaution dans un unique
classement d'importance avec `delta`, `sigma`, `K0` et `k`.

La référence est : `lam=10`, `delta=0.05`, `sigma=0.25`, `K0=25`, `k=3`,
`T=2000`. Pour obtenir des queues mieux identifiées, le centre de la campagne
peut être `lam=30`; justifie ce choix et conserve le lien avec la baseline.

Construis successivement :

1. un contrôle de taille et d'horizon autour de `lam ∈ {10, 30, 100}` et
   `T ∈ {2000, 4000}`, en réutilisant les runs M4 valides déjà présents ;
2. des courbes OAT autour du centre pour rendre visibles monotonies, seuils et
   formes non linéaires ;
3. un plan global espace-remplissant sur les paramètres microscopiques communs ;
4. des coupes 2D ciblées seulement après le screening ;
5. une phase confirmatoire indépendante sur les régimes et interactions les
   plus importants.

Plages initiales à auditer par des pilotes, puis à corriger si elles produisent
uniquement des cas triviaux ou des arrêts :

- `delta` : environ `0.02–0.10` ;
- `sigma` : environ `0.10–0.50`, avec un contrôle `sigma=0` séparé ;
- `K0` : environ `5–100`, de préférence sur une échelle logarithmique ;
- `k` : valeurs discrètes `{2, 3, 4, 6, 10}` ;
- `lam` : `{10, 30, 100}` pour le scaling principal.

Ces bornes sont des points de départ, pas des vérités. Relie les plages aux
équations, au rapport, aux pilotes et aux régimes observés. Ne fais pas varier
`pop_max` comme s'il bornait la population ; augmente-le seulement pour
diagnostiquer un arrêt, sans masquer un régime explosif.

Pour le plan global, utilise un plan reproductible adapté au mélange continu /
discret (par exemple Latin hypercube stratifié pour les continus et équilibrage
de `k`). Un ordre de grandeur de 48 à 80 points avec 3 graines par point est
raisonnable après benchmark ; réduis ou augmente ce nombre selon le coût et la
précision effectivement observés, en documentant la décision. Ne revendique
pas des indices de Sobol si le plan de Saltelli et le nombre de réplications ne
les rendent pas valides.

Utilise le même panel de graines pour chaque cellule d'une comparaison. Cela
permet des contrastes appariés, mais ne l'appelle pas abusivement « common
random numbers » si les trajectoires consomment ensuite des tirages différents.
Ne fusionne jamais les événements de plusieurs graines avant d'ajuster une loi :
ajuste chaque graine, puis agrège les estimateurs et leur incertitude.

Après screening, confirme les cellules retenues avec `T=4000` et au moins
5 graines. Près d'une frontière de régime ou lorsque la variance inter-graines
domine l'effet, augmente les répétitions plutôt que d'affirmer une sensibilité
instable. Utilise par défaut un burn-in de `T/4` et vérifie la robustesse à la
fenêtre.

### 3. Robustesse institutionnelle dans M4

Sépare clairement cette partie de la sensibilité paramétrique M4B. Étudie de
façon parcimonieuse et causale :

- la dose-réponse de `rounds_div` dans les valeurs réellement supportées par le
  moteur, notamment `{6, 3, 2, 1}` ;
- `objective="income"` contre `"wealth"` ;
- la combinaison factorielle des règles de faillite
  `cancel/transfer × destroy/prorata` ;
- crédit actif/inactif, naissance par emprunt et chocs corrélés comme contrôles
  structurels, si les rapports/runs existants ne suffisent pas déjà ;
- `k` aux mêmes points dans M4 et M4B sur un petit sous-échantillon de parité.

Réutilise en priorité les ablations M4 existantes dont la provenance est
complète. Distingue résultats obtenus autour de `rounds_div=3` et de la
configuration finale `rounds_div=1`; ne transpose pas quantitativement une
ablation d'un centre à l'autre sans contrôle.

### 4. Analyse de sensibilité

Produis plusieurs lectures complémentaires :

- courbes OAT avec incertitude inter-graines et contrastes appariés ;
- corrélations de rang partielles ou régressions standardisées avec intervalles
  bootstrap pour le screening global ;
- modèle de réponse non linéaire validé hors échantillon pour détecter seuils
  et interactions, avec importance par permutation si elle est pertinente ;
- cartes de régime extinction / stationnaire / explosion et diagrammes 2D des
  interactions confirmées ;
- décomposition explicite de la variabilité due aux paramètres et de la
  variabilité stochastique inter-graines.

Ne donne pas un classement unique sans préciser la métrique : un paramètre peut
être peu important pour `b` mais dominant pour la population ou les inégalités.
Rapporte tailles d'effet, incertitudes, non-monotonies et conditions de
validité. Toute analyse exploratoire utilisée pour choisir des cellules doit
être étiquetée comme telle ; les conclusions fortes doivent venir de la phase
confirmatoire.

## Infrastructure, traçabilité et Simulation Lab

Organise le dossier de campagne au minimum ainsi :

```text
recherche/sensibilite_m4_m4b/
  README.md
  design.md
  notes.md
  scripts/
  manifests/
  results/
  figures/
  report/
```

Exigences :

- scripts relançables et reprise après interruption ;
- identifiant de run déterministe ou table de correspondance non ambiguë ;
- manifeste comportant modèle, version/provenance, tous les paramètres, graine,
  horizon, burn-in, statut, durée, chemin des données et contrôles d'intégrité ;
- résultats agrégés en CSV/JSON lisibles sans relancer les simulations ;
- journal des décisions, résultats négatifs et anomalies dans `notes.md` ;
- aucune cellule silencieusement exclue parce qu'elle s'éteint, explose ou
  contredit l'hypothèse.

M4B est le modèle actif de Simulation Lab. Les runs M4B confirmatoires retenus
doivent y être consultables, avec leurs figures et métadonnées, et être marqués
à conserver. Pour le screening massif, limite l'écriture individuelle
(`individual_every=0` ou fréquence espacée) et les instantanés lorsque ces
données ne sont pas requises ; cela ne doit pas changer la trajectoire. Pour
les cellules confirmatoires et distributionnelles, conserve les mesures
nécessaires. Vérifie toujours cette neutralité de mesure sur un contrôle.

N'essaie pas de réactiver M4 dans Simulation Lab : les ablations M4 peuvent
être exécutées par les outils propres à `m4_credit_soc_fable` et référencées
dans le manifeste commun.

## Vérification et conduite autonome

Délègue les sous-tâches réellement indépendantes à des sous-agents, par exemple
l'audit de parité, l'inventaire des résultats existants et la vérification
statistique. Garde la conception expérimentale et la synthèse scientifique sous
ta responsabilité. À la fin de chaque phase majeure, fais vérifier par un
sous-agent à contexte frais : conformité au protocole, fuites entre exploration
et confirmation, calcul des métriques, provenance des figures et adéquation des
conclusions aux données.

Avant chaque compte rendu de progression, vérifie chaque affirmation dans un
résultat d'outil de cette session. Si un test échoue, si un run est incomplet ou
si une étape est omise, dis-le explicitement. Ne présente jamais une intention
comme un travail accompli.

Travaille de façon autonome pour toutes les actions réversibles dans ce
périmètre. Ne demande l'utilisateur que si une action destructive/irréversible,
un vrai changement de modèle, une extension de périmètre ou une information que
lui seul possède devient indispensable. Ne supprime aucun résultat existant et
ne modifie pas les moteurs de référence.

## Livrables finaux

1. `design.md` : protocole figé avant la campagne confirmatoire, domaines,
   métriques, graines, critères d'arrêt et plan d'analyse.
2. Manifeste complet des runs et table longue des métriques par run/graine.
3. Tables d'effets OAT, résultats du screening global, interactions et
   incertitudes.
4. Figures lisibles : courbes de réponse, diagrammes de régime, interactions,
   sensibilité par famille de métriques, scaling de taille finie et contrôles de
   parité.
5. Rapport scientifique final en français, en `.tex` et `.pdf`, qui contient :
   méthode, résultats, résultats négatifs, comparaison M4/M4B, limites et
   conclusions robustes. Chaque figure doit être traçable jusqu'aux runs.
6. `README.md` avec les commandes exactes pour reproduire l'étude et régénérer
   les figures/rapport sans relancer inutilement les simulations.
7. Une synthèse courte répondant explicitement :
   - quels paramètres influencent quelles sorties ;
   - où sont les frontières de régime et interactions ;
   - quelles signatures SOC sont robustes ;
   - ce qui relève d'un effet de taille, d'un choix institutionnel ou du bruit
     stochastique ;
   - ce que la parité M4/M4B permet — et ne permet pas — de conclure.

La mission est terminée seulement lorsque les runs retenus sont exécutés ou
explicitement comptabilisés comme échecs, les contrôles sont passés, les
résultats sont reproductibles, les figures sont sourcées et le PDF final est
compilé. Dans ton message final, commence par le résultat scientifique le plus
important, puis donne les chemins des livrables et les éventuelles limites.
