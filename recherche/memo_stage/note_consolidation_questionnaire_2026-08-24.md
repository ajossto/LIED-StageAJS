# Note de consolidation des réponses au questionnaire

**Date de consolidation :** 24 août 2026  
**Témoin principal :** Anatole Joseph-Stouls  
**Corpus interrogé :** `questionnaire_tracabilite_technique.md`, codes,
prompts, journaux, rapports et sorties de simulation cités ci-dessous  
**Statut :** note de relecture — **non encore intégrée au mémo maître**

## 1. Règle de lecture

Cette note ne transforme pas automatiquement une réponse en fait historique.
Elle distingue quatre niveaux :

1. **intention ou interprétation d'Anatole** : le témoignage du 24 août est la
   source primaire ;
2. **fait d'archive** : le code, les données ou plusieurs pièces concordantes
   permettent de l'établir ;
3. **affirmation d'un agent corroborée** : un rapport d'agent est soutenu par
   des scripts, tests ou sorties persistées, sans que toute la campagne ait été
   rejouée pendant la présente enquête ;
4. **question ouverte** : l'archive et le témoignage ne suffisent pas encore à
   fixer une formulation unique.

Les quarante réponses ont été lues. La plupart valident les inférences du
questionnaire, mais plusieurs ajoutent des motivations que le code ne pouvait
pas révéler et quatre corrigent matériellement le récit courant : QT-04,
QT-24, QT-28 et QT-32. QT-08 demandait d'abord de préciser le modèle concerné ;
la réponse archivistique est apportée en section 4.

## 2. Acquis historiographiques à intégrer

### 2.1 Le premier programme n'était pas seulement une recherche de formes

La première hypothèse mécaniste était que la comptabilité moderne et la
faillite comptable pouvaient contribuer à mettre le système en régime
auto-critique. Le premier moteur superposait donc volontairement plusieurs
mécanismes : seuils de crédit, bassin de marché, revente de créances,
comptabilité actif-passif, dépréciation, paiements d'intérêts et faillites.
Les régimes dépendaient à la fois des paramètres et de la graine. Les études de
sensibilité simples et couplées n'étaient pas des annexes : elles servaient à
cartographier la frontière entre divergence et population bornée. Source
d'intention : réponse QT-02. Sources d'archive :
`anciens_modeles/claude/`, `anciens_modeles/claude3-v2/`,
`anciens_modeles/Modèle_sans_banque/` et campagnes du WIP du 27 avril.

### 2.2 L'asymétrie nominal/réel est une hypothèse d'information

La créance reste connue de la prêteuse à sa valeur comptable tandis que le
capital productif placé chez l'emprunteuse s'érode. Cette dissociation avait
pour fonction de faire accumuler une fragilité que la prêteuse ne perçoit pas
dans ses décisions. Anatole cherchait en particulier un risque réel de
faillite d'autant plus sous-estimé que l'entité était grosse. Ce mécanisme est
scientifiquement assumé pour les premiers moteurs, mais sa conservation dans
les modèles récents redevient discutable. Source d'intention : QT-03. Source
formelle : `recherche/note_de_travail/latex/note.tex`, passage sur la double
fragilité et la non-réévaluation continue des créances.

### 2.3 Le retrait de la banque spéciale avait deux objectifs liés

Le questionnaire opposait trop fortement simplification et expérience
d'émergence. La séquence la plus fidèle est désormais :

- les agents n'ont jamais reçu de type déclaré « banque » ou « travailleur » ;
- retirer le mécanisme bancaire spécial devait d'abord éviter que le modèle ne
  repose sur des entités immortelles et réduire une complexité qui aurait rendu
  l'étude analytique beaucoup plus difficile ;
- une fois les agents replacés sous des règles communes, la réapparition ou non
  de rôles durables devenait bien une expérience d'émergence fonctionnelle ;
- les premières analyses ont pourtant retrouvé des entités très longues à
  vivre et une lecture « banques / travailleurs » ;
- l'analyse ultérieure du WIP du 27 avril a attribué la séparation principale
  aux cohortes d'âge et au protocole d'amorçage, ce qui a retiré sa portée
  économique générale.

Cette formulation réconcilie le témoignage antérieur sur l'émergence sous
règles communes et la réponse QT-04 sur l'immortalité et la simplification
analytique. Sources : QT-04 ; `recherche/note_de_travail/latex/note.tex`,
section « Premiers résultats » ;
`recherche/analyse_distributions_taille_revenu/latex/rapport.tex:166-212`.

### 2.4 L'ablation de l'ancien `k` vient de deux critiques distinctes

Le choix de paires `k=2` n'est pas seulement la conséquence d'une carte de
phase. Anatole retient :

- une taille de rencontre supérieure compliquait inutilement le toy-model,
  puisque la convergence finissait par être obtenue avec la rencontre locale
  minimale ;
- un nombre total de rounds fixe indépendamment du nombre d'entités n'avait
  pas d'interprétation économique acceptable : l'activité de création de
  contrats devait au minimum dépendre de la population du marché.

La solution ultérieure sépare donc la complexité locale — une paire — et
l'intensité agrégée — un nombre de rencontres proportionnel à `N`. Sources :
QT-05 ; code WIP ; `m4b_credit_soc_mini/m4b/model.py` ; prompt M4.2.

### 2.5 Simulation Lab est une méthode de recherche, pas seulement une IHM

Anatole décrit Simulation Lab comme son principal outil de supervision. La
génération systématique de graphiques pour chaque run lui permettait :

- de contrôler le travail des agents et les comportements des moteurs ;
- de naviguer entre les graines et les cellules de campagne ;
- de repérer des phénomènes non anticipés ;
- de reformuler les questions et de produire de nouvelles hypothèses.

La visualisation systématique est donc à présenter comme une composante de la
méthode exploratoire-régressive et comme la « moelle épinière » pratique du
stage. Les animations dynamiques sont la continuation prévue de ce principe.
Sources d'intention : QT-19 et QT-23. Sources techniques :
`simulation_lab/`, `simulation_lab_data/`, scripts d'import des différentes
lignées et tests des interfaces Live.

### 2.6 La reproductibilité exacte sert la continuité entre versions

Le passage de `random.Random` à `numpy.random.default_rng` n'avait pas, selon
Anatole, de motivation scientifique particulière. En revanche, la conservation
de la séquence de tirages et la parité bit à bit sont devenues cruciales pour
attribuer une divergence de trajectoire à la seule modification étudiée et
pour soutenir la continuité M4.2B → M4.3 → Live → Live-v2 → M4.4. Une
conservation des statistiques dans la variabilité inter-graines aurait parfois
suffi, mais la parité exacte constitue la preuve la plus forte disponible.
Sources : QT-32 et QT-33 ;
`m4_3live_v2_credit_soc/prompts/PROMPT_M4_3LIVE_V2.md:59-62,224-230` ;
tests de parité et de replay des lignées récentes.

### 2.7 Le recours aux agents fait partie de la technicité du stage

Les agents ont servi à implémenter, balayer, visualiser, critiquer et rédiger,
mais pas à décider seuls du programme scientifique. Anatole formule les
questions et n'accepte que du code qu'il estime pouvoir écrire lui-même avec
un temps suffisant ; il contrôle les propositions par le code, les tests, les
figures, les simulations et les comparaisons concurrentes. La délégation a
surtout augmenté le débit expérimental : demander directement une
caractérisation de sensibilité sans devoir écrire tout le harnais et toutes
les figures. Source d'intention : QT-09 et QT-37 à QT-40. Sources d'archive :
prompts, journaux de correction et branches concurrentes M2/M4.

## 3. Corrections factuelles urgentes du mémo maître

### 3.1 Live-v2 et M4.4 font partie du stage

La ligne actuelle du registre décrivant M4.3Live-v2 comme « conception
seulement, non implémentée » est fausse à l'état du 24 août.

- **M4.3Live-v2** a été conçu les 21–22 août, forké et testé le 22 août. Il
  libère le sens du prêt, supprime `equalization`, purge les clefs mortes,
  rend l'instrumentation native et mène ses campagnes A/B et de rotation.
  Le fichier de traçabilité contient 156 runs plus l'en-tête, dont trois runs
  M4.3 de référence : cela laisse **153 runs v2** ; l'index Simulation Lab
  contient également 153 entrées. Le rapport et le journal sont datés du
  22 août.
- **M4.4Rebond** est ouvert le 23 août et développé/testé jusqu'au 24 août.
  Sa traçabilité contient **372 runs** plus l'en-tête ; l'index Simulation Lab
  contient les mêmes 372 entrées. La sortie
  `results/analysis/suite_final.log` consigne 18/18 tests verts et le journal
  rapporte 29,9 heures de calcul cumulées. Le rapport final est daté du
  24 août.
- Anatole confirme explicitement en QT-01 que les deux lignées appartiennent
  au stage, même s'il poursuit désormais la caractérisation du modèle par
  curiosité personnelle.

Sources : `m4_3live_v2_credit_soc/JOURNAL.md`,
`m4_3live_v2_credit_soc/report/README.md:25-31`, fichiers
`results/analysis/{traceability,simulation_lab_index}.csv` ;
`m4_4_rebond_credit_soc/JOURNAL.md`, `README.md:98-108,177-179`,
`results/analysis/{traceability,simulation_lab_index,suite_final.log}`.

**Anomalie documentaire à conserver :**
`m4_3live_v2_credit_soc/README.md:99-103,272-273` annonce 203 runs v2 et 207
dans l'annexe. Cette liste reprend en réalité plusieurs campagnes v1 que le
journal dit ne pas avoir copiées. Les tables persistées et le README du
rapport soutiennent 153 runs v2. Le nombre 203 ne doit donc pas être repris
sans qualification.

Les assertions A79 et la liste des sources du mémo maître doivent être
corrigées, et M4.4 doit être ajoutée au registre.

### 3.2 M4.4 n'a pas clos les tests Pareto et coupure par décision théorique

Le plan M4.4 qualifiait les résultats antérieurs d'« acquis qu'il est interdit
de refaire » et excluait l'analyse de coupure (`PLAN_M4_4_REBOND.md:75-144`).
QT-28 corrige l'interprétation de cet impératif : Anatole n'a pas décidé que
ces questions étaient définitivement sans intérêt ; elles n'ont simplement
pas été reprises, faute de temps pour une étude propre. Le mémo doit donc
parler d'un **périmètre de campagne imposé par le temps**, non d'une clôture
épistémologique voulue.

### 3.3 `Dagum c` a été choisi automatiquement, sous un critère étroit

Le choix n'a pas été effectué parce que la courbe paraissait mieux convenir.
Le script `m4_3_credit_soc/scripts/freeze_tail_statistic.py` compare deux
candidats sur des fenêtres post-convergence propres à chaque run et sélectionne
automatiquement celui dont le coefficient de variation inter-graines est le
plus faible. `Dagum c` gagne avec un CV de 0,69–0,70 %, contre 1,35–1,59 %
pour l'estimateur de Hill/Pareto pur. L'erreur initiale `c·d` — indice de
queue inférieure pris pour l'indice supérieur — a été corrigée avant la
cartographie D1 ; le gagnant n'a pas changé. Sources : QT-22 ; script cité ;
`m4_3_credit_soc/JOURNAL.md:482-535` ; rapport M4.3, §2.4.

Il faudra écrire « sélection automatique entre deux statistiques candidates
selon la reproductibilité inter-graines », et non « sélection automatique de
la meilleure famille de loi ».

### 3.4 Le recalage temporel est un acquis partiel et une question ouverte

Le test du 21 août a établi qu'un changement de pas exige de transformer
ensemble `delta`, `sigma`, `lambda`, mais aussi les flux par pas `A` et `rho`.
Le recalage reste imparfait : un résidu de 6 à 17 % persiste parce que deux
phases de marché successives ne se composent pas comme une seule phase deux
fois plus intense. QT-30 ouvre une étude qui n'a pas été menée : faire tendre
le pas vers une petite échelle, tester la convergence vers une dynamique
continue et vérifier si les simulations actuelles représentent ce régime.
Sources : `m4_3live_credit_soc/scripts/time_rescaling.py:1-70` ;
`m4_3live_v2_credit_soc/ROADMAP.md:366-394` ; QT-30.

## 4. Réponse archivistique apportée à QT-08

Le modèle visé par QT-08 est explicitement le **WIP du 27 avril**.
`recherche/analyse_distributions_taille_revenu/latex/rapport.tex` indique :

- 805 simulations du même moteur, dont 13 lancées directement et 792 issues
  de l'étude de sensibilité ;
- 163 retenues comme stationnaires ;
- un critère déjà calculé par le harnais
  `run_simulation.py:detect_regime_diagnostics` : queue bornée
  (`bounded_tail`) **et** flux de faillites équilibré avec les créations
  (`flow_balanced`) ;
- un ajustement MLE sur un seul instantané stationnaire par run, puis une
  agrégation des verdicts, afin de ne pas fabriquer une multimodalité par
  mélange de temps ou de paramètres.

Le filtre de stationnarité n'est pas ce qui réfute à lui seul la lecture en
classes. Sur les 163 runs retenus, le faisceau décisif est : corrélation
âge–log(taille) de 0,88 à 0,95, distribution des âges bimodale avec un trou
intermédiaire, association des deux composantes ajustées aux fondateurs et
aux entrants, et alourdissement de la queue avec l'horizon. Le rapport conclut
donc à un artefact de cohorte et d'amorçage plutôt qu'à deux types économiques
stables (`rapport.tex:166-212`).

Ce point est un **résultat de rapport d'agent fortement étayé par les sorties
et scripts**, puis adopté par Anatole dans la suite du travail. Il ne faut pas
le présenter comme une propriété universelle de toute ancienne simulation :
il porte sur cette lignée et sur ce protocole d'initialisation.

## 5. Point encore ambigu : le mot « tension » dans QT-24

Les archives distinguent deux objets qu'il ne faut pas fusionner :

1. la tension formelle `T = K_aut/K_eq`, qui résume très bien les effets
   d'échelle **à `delta` fixé**, mais échoue comme paramètre d'état universel
   lorsque `delta` varie ;
2. la chaîne finale de M4.4 expliquant la contraction :
   `Gini du bassin → rotation du crédit → mortalité par entité → population`.
   Le premier maillon est vérifié sur deux fichiers indépendants, le dernier
   est une identité de stationnarité, et l'exposant rotation–mortalité est
   mesuré mais non universel : il dépend du levier.

QT-24 affirme que « la chaîne d'explication de l'élasticité passe par la
tension ». Cette phrase peut être vraie dans le premier sens, sous la réserve
`delta` fixé, ou employer « tension » comme nom général de la fragilité
financière décrite par la seconde chaîne. Avant intégration, il faut fixer
lequel de ces deux sens Anatole souhaite donner au mot. Sources :
`m4_3live_credit_soc/JOURNAL.md:378-407` ; rapport Live-v1, résumé ;
`m4_4_rebond_credit_soc/report/rapport_final.tex`, section « Ce qui gouverne
la contraction de population ».

## 6. Pistes bibliographiques identifiées depuis QT-21

### 6.1 Difficulté d'identifier une loi de puissance

Deux sources présentes ou déjà citées localement correspondent au souvenir :

- Aaron Clauset, Cosma R. Shalizi et M. E. J. Newman (2009), « Power-Law
  Distributions in Empirical Data », *SIAM Review* 51(4), 661–703,
  DOI [10.1137/070710111](https://doi.org/10.1137/070710111). Le papier n'est
  pas archivé comme PDF autonome dans Zotero, mais il est cité dans
  `/home/anatole/Zotero/storage/268ISWKI/Systèmes auto-critiques et self-organized critical.pdf`
  et sa méthode MLE–KS inspire les scripts `tail_test.py` du corpus ;
- Rafael Wildauer et Ines Heck, « Was Pareto right? Do the US wealth and
  income distributions follow power laws? », présent en double dans Zotero
  (`AAY9U5ZD` et `RJAQ8VTC`). Il documente explicitement le soutien empirique
  mixte aux lois de puissance strictes et compare des alternatives par tests
  d'ajustement formels.

### 6.2 La double Pareto-lognormale de Reed

Les deux références exactes, absentes de Zotero sous forme de PDF autonome,
sont :

- William J. Reed (2003), « The Pareto law of incomes—an explanation and an
  extension », *Physica A* 319, 469–486,
  DOI [10.1016/S0378-4371(02)01507-8](https://doi.org/10.1016/S0378-4371(02)01507-8) ;
- William J. Reed et Murray Jorgensen (2004), « The Double
  Pareto-Lognormal Distribution—A New Parametric Model for Size
  Distributions », *Communications in Statistics—Theory and Methods* 33(8),
  1733–1753,
  DOI [10.1081/STA-120037438](https://doi.org/10.1081/STA-120037438).

La justification précise n'est pas seulement « une loi flexible à quatre
paramètres » : la dPlN est la loi de l'état d'un mouvement brownien géométrique
partant d'un état lognormal, observé après une durée exponentielle — ou tué à
taux constant. C'est cette dérivation générative qui lui donne un intérêt
supérieur à un simple ajustement à quatre paramètres. La réserve d'Anatole sur
les données, les incertitudes et l'évaluation empirique du fit reste à inscrire
comme jugement de lecture, pas comme conclusion démontrée par Reed.

### 6.3 Reprises de Yakovenko par des économistes

Une réponse existe déjà dans Zotero : Anwar Shaikh, Nikolaos Papanikolaou et
Noe Wiener (2014), « Race, gender and the econophysics of income distribution
in the USA », `/home/anatole/Zotero/storage/3DRCWXJF/…pdf`. Les auteurs se
réclament explicitement de l'hypothèse « two-class » de Yakovenko et la testent
sur les revenus salariaux américains par race et genre. Cela établit au moins
une reprise directe par des économistes ; cela ne suffit pas encore à dresser
la réception académique générale de la lecture Boltzmann–Pareto.

## 7. Matrice d'intégration des quarante réponses

| QT | Statut après confrontation | Action proposée |
|---:|---|---|
| 01 | correction majeure confirmée | inclure Live-v2 et M4.4 dans le stage et le registre |
| 02 | enrichissement d'intention | expliciter la faillite comptable comme première hypothèse SOC et le rôle des campagnes couplées |
| 03 | validation avec portée temporelle | écrire l'asymétrie comme perte d'information de la prêteuse ; signaler sa remise en question récente |
| 04 | réponse inférée trop étroite | remplacer par la séquence à double objectif : supprimer les immortelles/simplifier, puis observer l'émergence éventuelle |
| 05 | validation partielle | séparer inutilité de `k>2` et inadéquation d'un volume de marché fixe |
| 06 | validé | conserver l'échec de la première expérience de rebond comme insuffisance de protocole, non absence de signal |
| 07 | validé et enrichi | relier l'interface dynamique à l'expérimentation en direct et au retour ultérieur à la conception |
| 08 | modèle précisé par l'archive | intégrer la réponse de la section 4 ; laisser Anatole préciser seulement le déclic personnel s'il le souhaite |
| 09 | validé et enrichi | ajouter le test des capacités des agents à la réplication adversariale M2 |
| 10 | validé | conserver fusion des contrats et invariants requis |
| 11 | validé | relier explicitement la critique des cascades synchronisées au passage M2 → M3 |
| 12 | validé | conserver la séparation liquidité/capital et le déplacement du choc |
| 13 | validé | écrire la contagion comme condition nécessaire du candidat SOC |
| 14 | validé | conserver la promotion de Fable et la raison mécaniste |
| 15 | validation forte | utiliser cette réponse comme articulation centrale entre M3, M4 et la notion de propagation causale |
| 16 | validé | conserver la réduction M4 → M4B comme test de nécessité |
| 17 | validé | conserver la stationnarité comme préalable aux comparaisons distributionnelles |
| 18 | validé | conserver les extensions NW/cycles comme analyses postérieures sur runs existants |
| 19 | enrichissement majeur | faire de Simulation Lab une méthode de supervision, découverte et formulation d'hypothèses |
| 20 | validé avec réserve | distinguer métriques de décision et aides grossières à la compréhension |
| 21 | chantier bibliographique ouvert | intégrer les quatre sources de la section 6 et poursuivre la réception de Yakovenko |
| 22 | précision technique confirmée | documenter le choix algorithmique par CV et la correction `c·d → c` |
| 23 | validé et prolongé | mentionner le besoin d'animations pour communiquer les résultats |
| 24 | résultat final enrichi, vocabulaire à fixer | mettre au centre la réponse non proportionnelle à `A`, le couple technologique `(A,gamma)` et distinguer les deux sens de « tension » |
| 25 | correction d'intention | expliquer le sens libre par la complexité injustifiée et l'entrave à l'optimum concave |
| 26 | validé | conserver les tests de parité institutionnelle et de reprise |
| 27 | validé et enrichi | ajouter la vérification des paramètres implicites/arbitraires et le partage de la plus-value comme question théorique |
| 28 | correction majeure | remplacer la clôture théorique par « non réalisé faute de temps pour une étude propre » |
| 29 | validation forte | conserver la taxonomie résultat / identité / corrélat comme règle méthodologique explicite |
| 30 | enrichissement majeur | ajouter calcul SSH, puissance du poste et question ouverte du passage au temps continu |
| 31 | validé | conserver garde-fous mémoire et reprise des campagnes |
| 32 | correction de motivation | aucune raison particulière pour le changement de RNG ; importance acquise ensuite par la parité |
| 33 | validé avec nuance | bit-exact comme preuve maximale, statistiques inter-graines comme solution parfois acceptable |
| 34 | validé | présenter l'optimisation comme augmentation de la capacité d'étude |
| 35 | validé | rattacher les figures voulues à Simulation Lab |
| 36 | validé et chiffré | ajouter la contrainte de stockage d'environ 70 Go et le nettoyage conservateur |
| 37 | validé | conserver l'organisation des rôles humains/agents |
| 38 | validé | conserver les erreurs d'agents comme objets de contrôle et non comme faits |
| 39 | validé | conserver le caractère exploratoire-régressif des campagnes |
| 40 | validé et enrichi | décrire le critère personnel d'acceptation du code et le gain de débit expérimental |

## 8. Modifications proposées au mémo après validation de cette note

1. Corriger le registre des modèles : Live-v2, 21–22 août, implémentée et
   testée ; ajouter M4.4, 23–24 août, implémentée, testée et analysée.
2. Corriger A79 et les sources principales ; ajouter une assertion sur
   l'anomalie documentaire 153/203 runs v2.
3. Réécrire le retrait de la banque spéciale selon la séquence de la section
   2.3, sans effacer le test d'émergence ni le motif d'immortalité.
4. Ajouter la fonction scientifique de Simulation Lab et la méthode de
   contrôle du travail des agents.
5. Ajouter le caractère automatique et limité du gel `Dagum c`.
6. Requalifier l'absence de tests Pareto/coupure dans M4.4 comme travail non
   mené faute de temps.
7. Ajouter le recalage temporel partiel et la question non traitée de la
   limite continue.
8. Ajouter Reed, Clauset, Wildauer–Heck et Shaikh et al. au registre
   scientifique avec leur intérêt exact et leurs précautions.
9. Inscrire le résultat final revendiqué par Anatole : le mécanisme de
   collaboration marchande modifie la réponse agrégée à une amélioration
   technologique ; une multiplication de `A` par 1,5 n'entraîne pas une
   multiplication mécanique de la production totale par 1,5. La formulation
   causale détaillée dépend encore de la clarification de la section 5.

## 9. Questions résiduelles pour la relecture

1. Dans QT-24, le mot « tension » désigne-t-il exactement
   `T = K_aut/K_eq`, avec la réserve « à `delta` fixé », ou la chaîne
   `Gini → rotation → mortalité → population` mise en évidence par M4.4 ?
2. Pour QT-08, le faisceau âge/cohortes/dérive temporelle a-t-il constitué ton
   propre motif d'abandon de la lecture « banques / travailleurs », ou as-tu
   surtout adopté cette conclusion parce que le rapport la rendait beaucoup
   plus convaincante que l'interprétation économique initiale ?
3. Souhaites-tu que la future campagne à technologies hétérogènes
   `(A_i,gamma_i)` apparaisse dans le mémo comme prolongement personnel hors
   du temps principal du stage, bien que Live-v2 et M4.4 restent dans le
   périmètre du stage ?

