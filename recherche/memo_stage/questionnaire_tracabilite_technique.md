# Questionnaire de traçabilité scientifique et technique du stage

**Auteur interrogé :** Anatole Joseph-Stouls  
**Préparé le :** 24 août 2026  
**Statut :** quarante réponses reçues le 24 août 2026 — consolidation sourcée en cours, non encore intégrée au mémo maître  
**Objet :** reconstituer les raisons des choix, les méthodes d'arbitrage, les techniques mises en œuvre et le traitement des données au cours du stage

## 1. Comment utiliser ce questionnaire

Ce questionnaire n'est pas une liste de détails à justifier après coup. Une
question est conservée seulement si sa réponse peut éclairer au moins un des
points suivants :

- la formulation d'une hypothèse ;
- le choix ou l'abandon d'une règle du modèle ;
- la méthode employée pour départager deux explications ;
- le statut d'un résultat positif, négatif ou incertain ;
- la raison scientifique ou pratique pour laquelle certaines données n'ont
  pas été utilisées ;
- une compétence technique ou méthodologique réellement mobilisée pendant le
  stage ;
- la décision qui conduit à l'étape suivante.

Chaque entrée contient une **réponse inférée depuis le corpus**. Anatole peut :

- écrire `VALIDÉ` si elle est fidèle ;
- la corriger directement ;
- écrire `RÉFUTÉ` et donner la bonne explication ;
- ajouter un souvenir, une date approximative, une discussion d'encadrement ou
  une source manquante.

Pour une réponse incertaine, il est utile de préciser si elle correspond à un
souvenir contemporain du stage ou à une reconstruction actuelle. Les faits
techniques récupérables dans les fichiers seront vérifiés dans le corpus par
l'assistant ; Anatole n'a pas à recopier les chiffres ni à refaire les calculs.

### Niveaux d'enquête

- **Témoignage nécessaire** : le code ne peut pas révéler l'intention ou le
  contexte de décision.
- **Mixte** : les archives établissent les faits, mais pas complètement la
  manière dont Anatole les a interprétés.
- **Archive d'abord** : l'assistant doit établir la réponse par les pièces ;
  Anatole ne valide ensuite que l'interprétation ou l'importance historique.

### Gabarit de réponse

```text
Réponse d'Anatole :
Degré de certitude : certain / probable / souvenir flou
Date ou période approximative :
Discussion ou personne éventuellement impliquée :
Source supplémentaire à consulter :
```

## 2. Lot prioritaire — questions à forte valeur historiographique

### QT-01 — Où se termine exactement le travail de stage ?

**Nature :** témoignage nécessaire.

**Question.** Les dossiers `m4_3live_v2_credit_soc/` et
`m4_4_rebond_credit_soc/` montrent une implémentation et des campagnes datées
des 22–24 août, alors que le témoignage antérieur indiquait que la poursuite
numérique et les ablations avaient été arrêtées parce que le stage touchait à
sa fin. Ces deux lignées font-elles encore partie du stage, constituent-elles
une prolongation personnelle immédiate, ou faut-il distinguer leur statut dans
le récit ? Quel événement a fait reprendre le développement ?

**Réponse inférée.** La décision du 21 août portait probablement sur l'arrêt du
programme M4.3 alors ouvert, et non sur l'interdiction de toute nouvelle
question. La relecture de M4.3Live aurait produit une feuille de route plus
ciblée : libérer le sens du prêt, expliquer la rotation du crédit, puis chercher
où se distribue le rebond. V2 et M4.4 seraient donc des prolongements directs,
mais leur appartenance administrative au stage reste indécidable dans les
archives. OUI, partie du stage. Je continue sur le côté de caractériser mon modèle. 

**Pièces du corpus.**

- `m4_3live_credit_soc/JOURNAL.md`, sections « Prompt de la v2 » et
  « Deux rectifications de l'utilisateur » ;
- `m4_3live_v2_credit_soc/JOURNAL.md`, entrées des 21–22 août ;
- `m4_3live_v2_credit_soc/report/README.md` ;
- `m4_4_rebond_credit_soc/JOURNAL.md`, entrées des 23–24 août ;
- `m4_4_rebond_credit_soc/README.md`.

**Réponse d'Anatole :OUI, partie du stage. Je continue sur le côté de caractériser mon modèle.**

### QT-02 — Comment le tout premier moteur a-t-il réellement été conçu ?

**Nature :** mixte.

**Question.** Au moment des 12–13 mars, quelles règles as-tu écrites ou
demandées en premier : extraction concave, séparation actif/passif, prêt,
intérêt, érosion, illiquidité, faillite, naissance ? Étaient-elles déduites
d'une représentation conceptuelle préalable, ajoutées au fur et à mesure pour
obtenir un régime borné, ou traduites d'un schéma que tu avais déjà dessiné ?

**Réponse inférée.** Le modèle semble être né comme un moteur comptable riche,
conçu pour donner au système plusieurs voies d'accumulation, de dissipation et
de propagation avant tout élagage. L'extraction `alpha*sqrt(P)` et la
dépréciation matérialisaient d'emblée l'intuition énergétique ; actif/passif,
prêts et intérêts devaient rendre les entités interdépendantes. Les nombreux
postes n'étaient pas encore tenus pour indispensables : ils formaient un espace
exploratoire dans lequel chercher la convergence et les cascades.

**Pièces du corpus.**

- `recherche/note_de_travail/latex/note.tex` et ses schémas ;
- `anciens_modeles/claude/README.md` ;
- `anciens_modeles/claude/simulation.py` ;
- `anciens_modeles/Modèle_sans_banque/description_modele_actuel.txt` ;
- `anciens_modeles/Modèle_sans_banque/NOTE_INTERPRETATION_ABSTRAITE.md`.

**Réponse d'Anatole :** Ma première hypothèse était que le système comptable moderne, avec une déclaration de faillite comptable, était un élément fort dans la mise en route d'un SOC. Il y a beaucoup de compléxité dans le premier modèle, des seuils pour les crédits, un pool de marché, des mécanismes de reventes de dette, etc. Le modèle pouvait converger ou ne pas converger en fonction des paramètres de simulation, et aussi dépendait du seed. Beaucoup de rapports, d'études de sensibilité de paramètre, couplé sont sortis de ce modèle. 

### QT-03 — Pourquoi avoir choisi une comptabilité nominale/réelle asymétrique ?

**Nature :** témoignage nécessaire.

**Question.** Pourquoi le capital productif ou les actifs financés s'érodent-ils
alors que le principal nominal des prêts reste dû ? Cette asymétrie était-elle
dès le départ la traduction de l'analogie de la machine qui s'use, une
représentation du système financier réel, ou un mécanisme choisi parce qu'il
créait de la fragilité et des faillites ? Pourquoi les prêts sont-ils restés
perpétuels et non amortis dans les modèles de référence ?

**Réponse inférée.** L'asymétrie paraît avoir une double fonction. Elle traduit
l'idée qu'un investissement réel perd sa capacité productive tandis que la
créance comptable persiste ; elle produit aussi le décalage nécessaire à la
fragilité du bilan. L'amortissement nul simplifie le toy-model et concentre
l'analyse sur les intérêts, l'érosion et la liquidation, mais cette justification
doit être attribuée à Anatole plutôt qu'inférée d'un paramètre par défaut.

**Pièces du corpus.**

- `anciens_modeles/Modèle_sans_banque/description_modele_actuel.txt` ;
- `anciens_modeles/modele-27-04-WIP/RAPPORT_ELAGAGE_MODELE.md` ;
- `m4b_credit_soc_mini/report/mecanique_m4b.tex` ;
- `m4b_credit_soc_mini/m4b/model.py`.

**Réponse d'Anatole :** C'est ça. L'asymétrie de la vision est une perte d'information que subit la préteuse. Elle ne sait pas que son capital est déprécié, et, dans les premiers modèles, elle continue de prendre des décisions avec ces données éronnées. Je voulais que le risque réel de faire faillite soit d'autant sous-estimé que l'entité était grosse. Dans les modèles récent, cette asymétrie peut étre remise en question. 

### QT-04 — Pourquoi retirer la banque explicite, et qu'attendais-tu de ce test ?

**Nature :** mixte.

**Question.** Le retrait de la banque spéciale devait-il uniquement simplifier
le code, ou constituer une expérience : vérifier si des rôles de prêteuses et
d'emprunteuses durables émergent entre entités soumises aux mêmes règles ? Quel
résultat aurait réfuté cette piste à l'époque ?

**Réponse inférée.** Il s'agissait consciemment de tester une émergence
fonctionnelle sous règles communes. Une différenciation persistante dans les
bilans et les revenus d'intérêt aurait soutenu l'analogie « banques /
travailleurs ». Sa disparition avec la règle spéciale, ou son explication par
l'âge et la cohorte fondatrice, devait retirer sa portée économique. C'est cette
seconde issue qui a finalement eu lieu.

**Pièces du corpus.**

- `anciens_modeles/Modèle_sans_banque/README.md` ;
- `anciens_modeles/Modèle_sans_banque/NOTE_INTERPRETATION_ABSTRAITE.md` ;
- `recherche/note_de_travail/latex/note.tex` ;
- `recherche/analyse_distributions_taille_revenu/latex/rapport.tex`.

**Réponse d'Anatole :** ?? Le modèle dit "sans banque" était une tentative de faire disparaitre les "banques", car je voulais un système sans entité immortelle. Je suis ok avec des disparités d'espérence de vie très grandes, mais la présence d'entités immortelles est un signal que le toy-model s'éloigne d'une interprétation dans le monde réel. Néanmoins, certaines structures réelles peuvent sembler immortelle (par exemple une ville), et on pourrait les tolerer. Cependant, l'objectif à terme était aussi de mener une étude analytique du comportement du modèle, ce que la présence de banque intimait de compléxifier enormément. 

### QT-05 — Quand et comment le problème de l'ancien paramètre `k` a-t-il été compris ?

**Nature :** mixte.

**Question.** À quel moment as-tu compris que `k` mêlait deux choses : la
taille de la rencontre locale et un nombre total de tentatives de marché fixe,
indépendant de la population ? Quelles observations ont convaincu que `k=3`
n'était pas un seuil structurel, et pourquoi le couple « paires aléatoires
`k=2` + activité proportionnelle à `N` » a-t-il été jugé plus juste pour un
toy-model ?

**Réponse inférée.** Les premières cartes faisaient apparaître un seuil
`k=3→4`, mais les couplages avec `mu`, les variations de population et les
contrôles à volume comparable ont montré que `k` pilotait aussi l'intensité
agrégée du marché. M4 identifie ensuite explicitement les rounds par tête comme
le levier du branching. M4B normalise l'activité par `N`, puis M4.2 fixe les
rencontres à des paires afin de séparer complexité locale et volume de marché.

**Pièces du corpus.**

- `anciens_modeles/modele-27-04-WIP/RAPPORT_ELAGAGE_MODELE.md` ;
- résultats de `anciens_modeles/modele-27-04-WIP/studies/sensitivity/` ;
- `m4_credit_soc_fable/NOTES.md`, passages sur `k`, le volume contrôlé et
  `rounds_div` ;
- `m4b_credit_soc_mini/m4b/model.py` ;
- `m4_2_credit_soc/prompts/PROMPT_M4_2.md`.

**Réponse d'Anatole :** Oui et non. L'ablation du k sort de deux observation: il compléxifie inutilement le modèle (le modèle désormais converge pour k minimal), et le nombre de round fixe indépendant de la population était analogiquement non pertinent : le nombre de nouveau contrat doit être proportionnel au nombre d'acteurs dans le marché, ou à minima dépendre de lui. 

### QT-06 — Pourquoi la première expérience de rebond n'a-t-elle pas suffi ?

**Nature :** mixte.

**Question.** La variante `alpha_plus_10pct` annonce +5,1 % d'extraction
post-transitoire et +25,2 % de prêts finaux. Qu'avais-tu conclu sur le moment ?
Pourquoi cette expérience a-t-elle été jugée insuffisante ensuite : définition
du rebond trop indirecte, seulement deux jeux de données archivés contre trois
annoncés, absence de ressource bornée, ou décrédibilisation générale du moteur
par l'artefact de cohortes ?

**Réponse inférée.** Le résultat a été pris comme une première signature
crédible : le gain de productivité élargissait le réseau financier et ne
réduisait pas l'extraction. Il n'a pas été conservé comme résultat final parce
que le moteur portait des artefacts démographiques, que la provenance
multi-graines est incomplète et que le protocole ne séparait pas amplitude,
échelle de naissance et dynamique de population. Il a nourri la suite sans la
valider.

**Pièces du corpus.**

- `anciens_modeles/4-05-dynamique/RAPPORT_ELAGAGE_MODELE.md` ;
- `anciens_modeles/4-05-dynamique/experiments/results/` ;
- `anciens_modeles/4-05-dynamique/DYNAMIC_RUNTIME_NOTES.md` ;
- `anciens_modeles/4-05-dynamique/examples/`.

**Réponse d'Anatole :** Exactement la réponse inférée. 

### QT-07 — À quoi devait servir le moteur interactif de début mai ?

**Nature :** témoignage nécessaire.

**Question.** Pourquoi avoir développé dès la branche `4-05-dynamique` une
API d'observation, des modifications atomiques de paramètres, des portées
`global_config` / `future_entities` / `existing_entities`, un journal
rejouable et un serveur web local ? L'as-tu effectivement utilisé pour former
des hypothèses, ou était-ce surtout une preuve de concept technique qui
préfigure M4.3Live ?

**Réponse inférée.** Cette branche paraît être la première tentative de
transformer le modèle en expérience pilotable : intervenir à un temps donné,
observer immédiatement la réponse, puis convertir la session en scénario
reproductible. Elle préfigure nettement l'architecture de M4.3Live, mais les
archives ne disent pas combien de décisions scientifiques ont réellement été
prises depuis l'interface.

**Pièces du corpus.**

- `anciens_modeles/4-05-dynamique/DYNAMIC_RUNTIME_NOTES.md` ;
- `anciens_modeles/4-05-dynamique/scripts/dynamic_control_server.py` ;
- `anciens_modeles/4-05-dynamique/scripts/dynamic_control_server_v2.py` ;
- `anciens_modeles/4-05-dynamique/examples/`.

**Réponse d'Anatole :** Effectivement, c'était une méthode pour moi pour expérimenter en live la réponse du modèle. J'espérais voir clairement et simplement un effet rebond. J'ai eu des resultats prométeurs mais insufisants. Je suis ensuite reparti dans la conception et l'élaboration du modèle.  

### QT-08 — Quel test a réellement renversé l'interprétation « banques / travailleurs » ?

**Nature :** mixte.

**Question.** Parmi la corrélation âge–log(taille), le trou dans la
distribution des âges, l'ajustement par deux lognormales et la dérive de
l'exposant avec l'horizon, quel élément a été décisif pour toi ? Pourquoi 642
des 805 simulations n'ont-elles pas été retenues comme stationnaires, et le
critère de stationnarité avait-il été défini avant l'analyse des distributions ?

**Réponse inférée.** Le faisceau est plus important qu'un test isolé : le
mélange ajustait deux cohortes d'âge, l'âge expliquait fortement la taille et
l'exposant de queue variait avec l'horizon. Les 163 runs stationnaires ont été
analysés séparément afin de ne pas confondre transitoire et distribution de
régime. Le corpus n'établit toutefois pas encore si les critères qui ont exclu
les 642 autres runs étaient tous fixés en amont ou hérités du harnais de
sensibilité.

**Pièces du corpus.**

- `recherche/analyse_distributions_taille_revenu/latex/rapport.tex` ;
- `recherche/analyse_distributions_taille_revenu/scripts/` ;
- `recherche/analyse_distributions_taille_revenu/results/` ;
- `recherche/note_de_travail/latex/note.tex`.

**Réponse d'Anatole :** De quel modèle parlons nous ? Effectivement, pour faire des études empiriques, il a fallut que je tente de déterminer un critère qui spécifie les simulations qui convergeaient vers un mode stationnaire (population bornée dans le temps)

### QT-09 — Pourquoi demander deux implémentations concurrentes de M2 ?

**Nature :** témoignage nécessaire.

**Question.** Qu'espérais-tu apprendre en donnant le même prompt à Codex et à
Fable ? Cherchais-tu surtout une réplication du verdict, une confrontation des
conventions sous-spécifiées, une vérification indépendante du code, ou une
division du coût de travail ? Comment as-tu arbitré lorsque leurs formulations
différaient, par exemple sur le bornage asymptotique ou le statut de la queue ?

**Réponse inférée.** Les deux branches étaient des réplications adversariales
apparentées : partir de la même conception, expliciter séparément les
ambiguïtés, implémenter, tester, puis comparer. Leur accord sur la neutralité
distributionnelle du crédit, le corps Fisk, la faiblesse des cascades et le
renouvellement était plus important que leurs formulations différentes. Elles
n'étaient pas considérées comme deux preuves statistiquement indépendantes.

**Pièces du corpus.**

- `anciens_modeles/m2_codex/reports/research_log.md` ;
- `anciens_modeles/m2_fable/reports/research_log.md` ;
- rapports `01_critical_reading` à `05_negative_results` des deux branches ;
- codes et tests sous `anciens_modeles/m2_codex/` et
  `anciens_modeles/m2_fable/`.

**Réponse d'Anatole :** Exact. C'était aussi un test des capacités de mes agents. 

### QT-10 — Pourquoi accepter la fusion des contrats par paire ?

**Nature :** mixte.

**Question.** La règle de transfert prorata faisait croître le carnet jusqu'à
des millions d'objets et provoquait des arrêts mémoire. Pourquoi as-tu jugé
acceptable de fusionner les contrats d'une même paire au taux moyen pondéré,
malgré la perte de généalogie des fragments ? Quelles propriétés devvaient être
préservées pour que cette optimisation reste scientifiquement neutre ?

**Réponse inférée.** Le nombre d'objets représentait une fragmentation
informatique sans volume économique nouveau. La fusion conservait principal,
flux d'intérêt, valeur nette et résultats macro, puis a été vérifiée par tests
et comparaison de trajectoires. La généalogie fine a été sacrifiée parce
qu'elle n'était pas encore nécessaire à la question posée ; un compteur de
composantes en gardait une trace minimale. Ce choix deviendra lui-même un
enseignement : la représentation du carnet peut créer un artefact de coût sans
créer un mécanisme économique.

**Pièces du corpus.**

- `anciens_modeles/m2_codex/reports/research_log.md`, « explosion des
  fractions » ;
- `anciens_modeles/m2_fable/reports/research_log.md`, correctif
  `merge_pairs` et cas tué à 7,8 Go ;
- tests de contrats des deux branches ;
- `anciens_modeles/m3_credit_soc/NOTES.md`, liste des pièges hérités de M2.

**Réponse d'Anatole :** Exact. 

### QT-11 — Comment as-tu décidé que le crédit était « causal » ou « neutre » ?

**Nature :** mixte.

**Question.** Quelle hiérarchie faisais-tu entre ressemblance de distributions,
différence de population, durée de vie, mortalité, Gini, intérêts du top et
avalanches ? Pourquoi l'ablation sans crédit de M2 suffit-elle à conclure à une
neutralité distributionnelle, alors que M3 conduit à dire que le crédit est
causal démographiquement mais toujours neutre sur les formes ?

**Réponse inférée.** « Causal » ne signifiait pas « produit tous les faits
stylisés ». Une ablation appariée devait modifier la grandeur considérée. Dans
M2, retirer le crédit conservait corps, queue et renouvellement : le crédit
n'expliquait pas ces distributions. Dans M3, la même ablation doublait
population et durée de vie sans changer les familles : le crédit accélèrait
l'horloge démographique, mais ne causait toujours pas les formes. La règle de
revenu X1 montrera ensuite que cette neutralité dépend du comportement local.

**Pièces du corpus.**

- synthèses finales M2 Codex et Fable ;
- `anciens_modeles/m3_credit_soc/NOTES.md`, entrées A/B, C–J et X1 ;
- `anciens_modeles/m3_credit_soc/reports/04_validation_report/main.tex` ;
- `anciens_modeles/m3_credit_soc/reports/07_income_rule/main.tex`.

**Réponse d'Anatole :** Exact. C'est notamment pourquoi on est passé de M2 à M3. 

### QT-12 — Le passage M3-H + X1 vers M4 était-il conscient à l'époque ?

**Nature :** témoignage nécessaire.

**Question.** As-tu explicitement décidé de combiner le résultat H (`d0=0`,
absorption par dette contractuelle) avec X1 (objectif de revenu, levier élevé),
ou cette filiation est-elle surtout devenue claire à la relecture des journaux ?
Pourquoi fusionner ensuite `L` et `K` en un seul stock ?

**Réponse inférée.** Le journal M3 formule explicitement la piste « règle de
revenu × plancher endogène » et propose de remplacer la dette abstraite par un
réseau de créances réelles. M4 commence précisément par ces acquis. La fusion
`L/K` cherche ensuite le noyau minimal : si le service des intérêts peut agir
directement sur le stock productif, la séparation de liquidité n'est plus
nécessaire à la propagation recherchée. Il reste à confirmer que cette
combinaison était ta décision consciente, et non seulement une suggestion
d'agent retenue après coup.

**Pièces du corpus.**

- `anciens_modeles/m3_credit_soc/NOTES.md`, entrées H et X1 ;
- `m4_credit_soc_fable/NOTES.md`, « Cadrage », sweep B et prototype fusionné ;
- `m4_credit_soc_fable/reports/01_soc_final/main.tex`.

**Réponse d'Anatole :** Exact. 

### QT-13 — Quel critère t'a convaincu qu'une avalanche était causale ?

**Nature :** mixte.

**Question.** Pourquoi la pente log-log et le scaling du maximum ont-ils été
jugés insuffisants ? Est-ce l'inspection des arbres de pertes, le rapport
racines/taille, la profondeur, ou leur combinaison qui a réfuté les chocs
sectoriels et le candidat `k=3` ? Pourquoi la fenêtre inter-pas `tau=1`, qui
agrandissait fortement les cascades, a-t-elle été écartée des conclusions
principales ?

**Réponse inférée.** Les chocs sectoriels produisaient des morts simultanées :
racines/taille égal à 1 et profondeur très faible, même lorsque la régression
semblait excellente. Le candidat `k=3` se transformait en bosse avec la taille
du système. `tau=1` avait une justification mécanique, mais sur-liait les morts
par coïncidence dans les régimes denses et pouvait construire des composantes
plus grandes que la population moyenne. La définition stricte au même pas a
donc été retenue comme mesure principale, avec arbres, racines et profondeur
comme diagnostics de causalité.

**Pièces du corpus.**

- `m4_credit_soc_fable/NOTES.md`, 13–14 juillet ;
- `m4_credit_soc_fable/experiments/m4/soc_stats.py` ;
- `m4_credit_soc_fable/experiments/m4/causal_window.py` ;
- `m4_credit_soc_fable/reports/01_soc_final/main.tex` ;
- `m4_credit_soc_sol/reports/m4_research/REPORT.md`.

**Réponse d'Anatole :** Exact. Un bon système auto-critique doit avoir un mécanisme de contagion. 

### QT-14 — Pourquoi poursuivre M4 Fable et non M4 Sol ?

**Nature :** mixte.

**Question.** Quels résultats as-tu personnellement regardés pour choisir la
branche Fable : arbres causaux, ablations annulation/destruction, scaling de
taille, branching, figures Simulation Lab ? La branche Sol a-t-elle été
abandonnée parce que son meilleur régime dépendait encore de chocs sectoriels,
ou pour une raison de code, de calendrier ou de confiance dans les analyses ?

**Réponse inférée.** Le facteur décisif paraît scientifique : Sol obtenait un
candidat précritique dont le cutoff reposait encore sur la sectorialité et dont
les tests de loi de puissance étaient mixtes. Fable avait trouvé
`cancel+destroy`, une propagation profonde sous chocs i.i.d., puis établi que
la combinaison était nécessaire par ablation. Les figures causales et les
statistiques cohérentes ont justifié la promotion vers M4B.

**Pièces du corpus.**

- `m4_credit_soc_sol/NOTES.md` et
  `m4_credit_soc_sol/reports/m4_research/REPORT.md` ;
- `m4_credit_soc_fable/NOTES.md` ;
- `m4_credit_soc_fable/reports/01_soc_final/main.tex` ;
- runs M4 importés dans `simulation_lab_data/runs/`.

**Réponse d'Anatole :** Exact. 

### QT-15 — Pourquoi annulation + destruction a-t-il été retenu comme noyau minimal ?

**Nature :** mixte.

**Question.** Cette règle a-t-elle été choisie parce qu'elle était
économiquement défendable, parce qu'elle simplifiait la liquidation, ou parce
qu'elle était la première à produire une propagation ? Comment as-tu évité de
sélectionner après coup le mécanisme qui donnait la loi souhaitée ?

**Réponse inférée.** La règle a d'abord été découverte exploratoirement, puis
soumise à des contrôles qui cherchaient à la réfuter : destruction seule,
annulation seule, graines, tailles, `k`, volume de marché, profondeur et absence
d'effondrement. Elle supprimait deux amortisseurs du vieux système — récupération
du résidu et fragmentation des expositions — et rendait ainsi la contagion
compréhensible. Sa simplicité et son mécanisme causal ont compté autant que la
forme de la distribution ; elle reste néanmoins une institution forte et non
une description universelle des faillites réelles.

**Pièces du corpus.**

- `m4_credit_soc_fable/NOTES.md`, découverte et validations du 14 juillet ;
- `m4_credit_soc_fable/reports/01_soc_final/main.tex` ;
- options et ablations archivées sous `m4_credit_soc_fable/experiments/` ;
- moteur réduit `m4b_credit_soc_mini/m4b/model.py`.

**Réponse d'Anatole :** Excellente question et réponse. La réponse inférée est excellente car elle résume aussi très bien ma réfléxion. C'est une donnée cruciale pour la future redaciond du rapport de stage. 

### QT-16 — Pourquoi M4B a-t-il nécessité une campagne aussi structurée ?

**Nature :** mixte.

**Question.** Pourquoi combiner pilotes, OAT, hypercube latin, coupes 2D et
confirmation appariée, plutôt qu'un seul grand balayage ? Pourquoi ne pas
faire une analyse de Sobol ? Pourquoi le centre `lambda=30` et les graines
`1–3` puis `11–15` ont-ils été choisis ?

**Réponse inférée.** Les pilotes validaient les plages et le coût ; l'OAT
rendait les effets lisibles ; le LHS dépistait les contributions globales et
interactions à coût contenu ; les coupes vérifiaient les interactions
scientifiquement importantes ; la confirmation sur graines disjointes
protégeait des choix exploratoires. `lambda=30` offrait davantage de données
de queue qu'à 10 pour un coût encore raisonnable face à 100. Le plan n'était
pas un Saltelli, donc des indices de Sobol auraient donné une précision et une
interprétation injustifiées.

**Pièces du corpus.**

- `recherche/sensibilite_m4b/report/protocole.tex` ;
- `recherche/sensibilite_m4b/JOURNAL.md` ;
- manifestes sous `recherche/sensibilite_m4b/manifests/` ;
- scripts `lib_screening.py`, `analyze_pilotes.py`, `analyze_confirm.py` et
  `analyze_confirm_dist.py`.

**Réponse d'Anatole :** Exact. 

### QT-17 — Pourquoi certains runs ou certaines métriques n'ont-ils pas été utilisés ?

**Nature :** mixte.

**Question.** Peux-tu confirmer la doctrine suivante : anciens runs trop
courts ou sans manifeste exclus de la campagne ; transitoires exclus par
burn-in ; extinctions à `t=1` traitées comme artefacts d'amorçage ; coupures
non identifiables lorsque très au-delà du maximum observé ; profondeur maximale
écartée des surfaces de réponse quand la variance inter-graines domine ;
cellules interrompues pour mémoire conservées comme diagnostics mais non comme
résultats complets ? Y a-t-il d'autres catégories de données volontairement
ignorées, et pourquoi ?

**Réponse inférée.** Les données n'ont pas été écartées parce qu'elles
contredisaient une hypothèse, mais lorsqu'elles ne répondaient pas proprement à
la question : provenance insuffisante, régime non établi, censure, estimateur
hors domaine, métrique trop bruitée ou protocole confondu. Les exclusions
doivent être racontées avec leur raison et, lorsque possible, leur nombre.

**Pièces du corpus.**

- `recherche/sensibilite_m4b/JOURNAL.md` ;
- `m4_2b_credit_soc/JOURNAL.md`, incidents mémoire et couverture de queue ;
- `m4_3_credit_soc/JOURNAL.md`, nettoyage, garde-fous et sélection de graine ;
- manifestes et `summary.json` des campagnes.

**Réponse d'Anatole :** Exact.

### QT-18 — Pourquoi les analyses de valeur nette et de cycles ont-elles été ajoutées après l'audit ?

**Nature :** témoignage nécessaire.

**Question.** Les extensions `NW`, cycles de production puis récessions de
l'énergie totale ont été calculées sans nouveaux runs, après la campagne
principale. Quelles questions de ta part les ont déclenchées ? Pourquoi les
données existantes étaient-elles suffisantes, et pourquoi ces analyses ont-elles
été étiquetées post-hoc plutôt qu'intégrées rétroactivement au protocole
principal ?

**Réponse inférée.** Tu as constaté que la campagne disait peu de choses sur
`NW`, pourtant meilleur analogue du patrimoine, puis tu as demandé une mesure
des périodes de croissance/récession. Les sorties individuelles et les séries
de `K` avaient été conservées assez finement pour permettre ces analyses sans
relancer. Elles ont été confirmées sur les graines disjointes disponibles,
mais leur question n'était pas pré-enregistrée : leur statut post-hoc devait
donc rester visible.

**Pièces du corpus.**

- `recherche/sensibilite_m4b/JOURNAL.md`, extensions NW et cycles ;
- `recherche/sensibilite_m4b/scripts/analyze_nw.py` ;
- `recherche/sensibilite_m4b/scripts/analyze_cycles.py` ;
- tables `results/summary/nw_*` et `cycles_*`.

**Réponse d'Anatole :** Exact. 

### QT-19 — Quel rôle Simulation Lab a-t-il réellement joué dans la recherche ?

**Nature :** mixte.

**Question.** Pourquoi développer une interface web locale et un CLI commun,
plutôt que conserver des scripts propres à chaque modèle ? Quels usages ont
effectivement influencé tes décisions : lancement de lots, comparaison de
graines, inspection de figures, annotation des runs, reprise, marquage des runs
à conserver ? L'outil était-il principalement utilisé par toi, par les agents,
ou par les deux ?

**Réponse inférée.** Simulation Lab devait rendre les expériences consultables
et reproductibles indépendamment du moteur : paramètres typés, graines,
manifestes `run.json`, artefacts, lots parallèles et interface de navigation.
Le web local en bibliothèque standard évitait une dépendance GUI et servait
l'humain ; le CLI et les adaptateurs servaient les scripts et les agents. Les
figures de cascades et de sensibilité ont réellement pesé sur la poursuite des
hypothèses, mais l'intensité de ton utilisation personnelle doit être précisée.

**Pièces du corpus.**

- `docs/README_simulation_lab.md` ;
- `simulation_lab/contracts.py` ;
- `simulation_lab/runs/executor.py` et `storage.py` ;
- `simulation_lab/models/discovery.py` ;
- `simulation_lab_data/runs/*/run.json` ;
- journaux M4, M4B, M4.3, Live-v1, Live-v2 et M4.4.

**Réponse d'Anatole :** Outil principal de supervision de la recherche, il m'a permi de naviguer aisément entre les simulations, vérifier les comportements, et si les agents avaient bien fait leur travail, et aussi m'ont permi de d'obeserver des nouveaux phénomènes, me poser de meilleures questions et de formuler des nouvelles hypothèses. La génération systématique, pour toute simulation, de graphiques décrivant son déroulé, sur des statistiques pertinentes a été la moelle épinaire de mon travail. 

### QT-20 — Comment s'est construite ta doctrine statistique sur les distributions ?

**Nature :** mixte.

**Question.** À quels moments as-tu cessé de considérer une droite log-log ou
un bon `R²` comme suffisants ? Pourquoi imposer ensuite MLE discret, scan de
`xmin` par KS, supports communs, renormalisation des lois tronquées, tests de
Vuong, AIC/BIC, bootstrap, absence de pooling inter-graines et séparation
corps/queue ? Parmi ces outils, lesquels comprenais-tu et choisissais-tu
directement, et lesquels ont d'abord été proposés par les agents puis adoptés
après vérification ?

**Réponse inférée.** La doctrine s'est construite par corrections successives :
artefact de cohorte, dérive temporelle, AIC calculé sur un corps tronqué avec
des lois non tronquées, LR historiquement biaisé en faveur de Pareto, CSN
continu dégénéré sur des avalanches discrètes, puis contrôle `seuil/2` mal
orienté. Chaque erreur a ajouté une règle. La progression va d'une lecture
visuelle exploratoire vers des comparaisons de familles sur support commun,
sans supprimer la valeur de l'observation graphique.

**Pièces du corpus.**

- `recherche/analyse_distributions_taille_revenu/scripts/` et rapport ;
- journaux M2 Codex/Fable ;
- `anciens_modeles/m3_credit_soc/NOTES.md` ;
- `m4_credit_soc_fable/experiments/m4/soc_stats.py` ;
- `recherche/sensibilite_m4b/scripts/lib_metrics.py` ;
- scripts statistiques de M4.2B, M4.3 et M4.4.

**Réponse d'Anatole :** Exact. Certaines métriques étaient aussi simplement des aides à la compréhension grossière.

### QT-21 — Que signifie exactement « Pareto comme hypothèse de travail » dans M4.2B ?

**Nature :** mixte.

**Question.** Tu voyais une queue de Pareto sur les figures, mais trois
tentatives de caractérisation ne concluaient pas. Pourquoi as-tu conservé la
queue comme hypothèse plutôt que la déclarer réfutée ? Comment as-tu découvert
que le contrôle `seuil/2` était dirigé vers le corps, et pourquoi le contrôle
`seuil×2` n'a-t-il pas suffi malgré son sens correct ?

**Réponse inférée.** La forme visuelle et la stabilité de l'exposant
justifiaient de continuer à caractériser la queue. `seuil/2` changeait l'objet
en incorporant le corps et dégradait mécaniquement le fit ; `seuil×2` testait
bien l'autosimilarité vers l'extrême, mais réduisait l'échantillon à une médiane
d'environ 17 observations. L'échec du test venait donc d'un manque de puissance,
pas d'une disparition de la queue observée. La bonne formulation est une
hypothèse explicite, non une loi démontrée.

**Pièces du corpus.**

- `m4_2b_credit_soc/JOURNAL.md`, sections 18, 20 et 21 ;
- `m4_2b_credit_soc/scripts/probe_criterion1_2x.py` ;
- `m4_2b_credit_soc/scripts/make_threshold_worked_example.py` ;
- `m4_2b_credit_soc/report/rapport_final.md` ;
- figures et résultats de caractérisation de `alpha`.

**Réponse d'Anatole :** Exact. Par ailleurs, il vient une question similaire sur les données réelles : au vue de la difficulté réelle à estimer une loi de puissance (cf un des articles dans zotero), quelle est la robustesse des lois de puissances documentées dans la litérature ainsi que leurs exposants ? Cette question a aussi mené à une autre question académique, est ce que  la lecture de yakovenko boltzmann pareto a été reprise par d'autres économistes ? Point très important, le nombre de paramètres qui permettent le fit : "Donnez moi 4 paramètres et je vous fais un éléphant, 5 et je lui fait remuer la queue" Certains chercheurs ont avancé des fits avec des lois à 4, 5 paramètres pour expliquer la forme des distributions de revenus et de capital. Ce n'est pas pertinent pour mon travail. Reed propose un modèle à 4 paramètres, lognormal double pareto, mais le justifie comme étant la loi d'un processus markovien (pour citer ce que je viens d'écrire, il faut retrouver les articles dont je parle. Ils sont surement dans zotero, sinon ailleurs) la lNdP est la plus convaiquante selon moi, mais je reste sur ma faim quant aux données utilisées pour fit, aux incertitudes, etc qui ne font pas partie de l'article de reed. 

### QT-22 — Pourquoi geler `Dagum c` dans M4.3 ?

**Nature :** mixte.

**Question.** Pourquoi choisir un indice de queue de type `Dagum c`, après la
correction du produit erroné `c*d`, plutôt que continuer les tests de familles
de M4.2B ? Quel résultat permettait de dire que `gamma_comp` brisait réellement
l'anti-corrélation queue/branching ? Pourquoi l'ablation institutionnelle a-t-elle
été laissée ouverte malgré ce résultat ?

**Réponse inférée.** M4.3 pose Pareto comme hypothèse de travail afin de ne pas
bloquer une nouvelle question sur une validation sous-alimentée. Une statistique
de queue unique est mesurée, corrigée puis gelée avant la carte principale.
`gamma_comp(2/3)` déplace simultanément `Dagum c` vers une queue plus épaisse et
le branching vers le haut, avec écarts presque constants pour plusieurs
`lambda` et dans deux demi-fenêtres. L'ablation aurait demandé de modifier le
mécanisme et restait une décision réservée à Anatole ; le temps disponible a
clos le programme avant arbitrage.

**Pièces du corpus.**

- `m4_3_credit_soc/prompts/PROMPT_M4_3_FINAL.md` ;
- `m4_3_credit_soc/JOURNAL.md`, sections 11, 16, 21–23 et 35bis ;
- `m4_3_credit_soc/scripts/freeze_tail_statistic.py` ;
- `m4_3_credit_soc/scripts/d1_verdict.py` ;
- `m4_3_credit_soc/report/rapport_final.md`.

**Réponse d'Anatole :** vrai. De plus, le choix Dagum c a été fait de manière automatique. 

### QT-23 — Pourquoi rendre M4.3 « pilotable en direct » ?

**Nature :** mixte.

**Question.** Quel problème scientifique l'architecture session/pause/pas à
pas/intervention/rejeu devait-elle résoudre que des batches statiques ne
résolvaient pas ? Pourquoi porter `A` et `gamma` au niveau de l'entité, offrir
les portées `all`, `new`, `fraction`, permettre reprise et bifurcation d'état,
et exiger un journal d'interventions ?

**Réponse inférée.** Le rebond est une réponse dynamique à une modification
d'efficacité ; comparer seulement deux régimes lancés depuis zéro mélange
technologie, graine et transitoire. Le fork Live permet de partir du même état,
appliquer une intervention datée, comparer des bras appariés et distinguer choc
global, vintage technologique et sous-population. Le journal transforme une
exploration interactive en scénario rejouable. Le choix répond à la question
scientifique, pas seulement au confort de visualisation.

**Pièces du corpus.**

- `m4_3live_credit_soc/prompts/PROMPT_M4_3LIVE.md` ;
- `m4_3live_credit_soc/m4_3live/live.py` ;
- `m4_3live_credit_soc/driver/headless.py` ;
- `m4_3live_credit_soc/JOURNAL.md` ;
- tests de replay, reprise, portées et parité.

**Réponse d'Anatole :** Vrai, plus je vais avoir besoin de pouvoir illustrer mes découvertes par des animations dynamiques. 

### QT-24 — Pourquoi l'ablation de `K0` a-t-elle renversé le verdict de rebond ?

**Nature :** mixte.

**Question.** Quatre contrôles ont réfuté l'explication initiale par le service
d'intérêts, puis `K0` compensé a supprimé la contraction de population. Pourquoi
as-tu demandé ces contrôles, et comment as-tu compris que `K0=25` devenait une
dotation relativement plus petite lorsque l'échelle technologique augmentait ?
Dans le rapport final, le bras compensé doit-il être présenté comme le bon
contre-factuel ou comme un second choix de convention tout aussi légitime ?

**Réponse inférée.** L'explication par les intérêts ne résistait pas aux
ratios service/production. La covariance d'échelle montrait qu'une hausse de
`A` change l'échelle naturelle du capital de facteur
`A^(1/(1-gamma))`. Garder `K0` fixe modifiait donc simultanément la technologie
et la position relative des nouvelles entités. La compensation isole le choc
technologique à géométrie constante ; le bras fixe reste toutefois un scénario
institutionnel possible. Le résultat important est précisément que le signe
agrégé dépend de ce choix.

**Pièces du corpus.**

- `m4_3live_credit_soc/JOURNAL.md`, 18 août ;
- `m4_3live_credit_soc/scripts/ablation_k0.py` ;
- `m4_3live_credit_soc/scripts/scaling_theory.py` ;
- `m4_3live_credit_soc/report/rapport_final.tex`.

**Réponse d'Anatole :** Le choix, l'interprétation et la pertinence de K0 restent des questions ouvertes. Le resultat principal, et celui qui vient conclure ce stage, c'est que le mécanisme de collaboration par une sorte de marché vient effectivement modifier les réponses à des stimulis. Une modification de 1.5 sur A ne crée pas une réponse globale de 1.5. Néanmoins, bouger A modifie aussi K_aut*. La question pour expliquer l'elasticité de la reponse a été : est ce que la chaine d'expliquation de l'elasticité passe par la tension ? La réponse a été oui, et de manière intéréssante. La formulation des technologies comme (A,gamma) qui peut être considéré comme (puissance d'une technologie, avantage à colaborrer avec cette technologie), est primordial. Une autre campagne va être menée: si les (Ai,gamma_i) des entités sont tous différents (mais Kaut constant, ou K0 modifié tel que Kaut/K0 constant, que sais-je), comment se comporte le modèle ? Mais c'est plus pour la curiosité qu'autre chose. 

### QT-25 — Pourquoi V2 a-t-il libéré le sens du prêt ?

**Nature :** mixte.

**Question.** Quelle critique de V1 a conduit à ne plus imposer « la plus riche
prête » et à laisser le signe de l'optimum de production jointe déterminer
donneuse et receveuse ? Pourquoi conserver le taux géométrique, supprimer
`equalization`, purger les clefs mortes et ne pas reprendre les scripts qui
avaient produit les acquis V1 ?

**Réponse inférée.** V1 pouvait refuser des échanges productivement optimaux
pour la seule raison que l'entité qui devait céder du capital était la plus
petite. V2 isole cette hypothèse par un drapeau appariable
`free/richest_lends`. Le taux est resté inchangé car sa formule est symétrique
et indépendante du rôle contractuel. `equalization` était du code mort
(`mkt_capped=0` sur les runs vérifiés) ; la purge supprimait une accumulation
de clefs vides qui faisait croître le coût sans modifier la dynamique. Les
scripts V1 non repris correspondaient à des résultats acquis, cités plutôt que
recalculés.

**Pièces du corpus.**

- `m4_3live_v2_credit_soc/prompts/PROMPT_M4_3LIVE_V2.md` ;
- `m4_3live_v2_credit_soc/JOURNAL.md`, lots A et B ;
- `m4_3live_v2_credit_soc/report/README.md` ;
- tests `test_loan_direction.py`, `test_v1_equivalence.py` et
  `test_parity_m4_3.py`.

**Réponse d'Anatole :** compléxification injustifiée du code et entrave à la logique d'optimisation concave. 

### QT-26 — Pourquoi modifier le critère de stationnarité en V2 ?

**Nature :** mixte.

**Question.** La bande fixe `[0,99;1,01]` rejetait 11 graines sur 12 du
contrôle. Pourquoi passer à un test de Student sur la moyenne du rapport entre
quarts, et que représente l'étendue par run rapportée comme plancher de bruit ?
Cette correction remet-elle en cause des verdicts V1 ou seulement la lecture du
nouveau protocole à 12 graines ?

**Réponse inférée.** La bande fixe confondait fluctuation d'une fenêtre courte
et dérive systématique. Avec 12 graines appariées, le test sur la moyenne
demande si le rapport diffère collectivement de 1, tandis que l'étendue par run
montre la variabilité irréductible des trajectoires. Le changement corrige le
critère pour V2/M4.4 ; il ne réfute pas automatiquement V1, dont les horizons et
questions différaient, mais invite à auditer toute conclusion fondée uniquement
sur la bande de 1 %.

**Pièces du corpus.**

- `m4_3live_v2_credit_soc/JOURNAL.md`, lot D ;
- `m4_3live_v2_credit_soc/scripts/analyse.py` ;
- `m4_4_rebond_credit_soc/report/rapport_final.tex`, protocole ;
- tables appariées des lots D et M4.4.

**Réponse d'Anatole :** Exact. 

### QT-27 — Pourquoi lancer M4.4, et quelle était sa question propre ?

**Nature :** témoignage nécessaire.

**Question.** Après l'établissement d'un rebond agrégé et l'étude du sens du
prêt, pourquoi demander où se dépose le surcroît dans la distribution ? Les
questions sur corps/queue, producteurs/rentiers, taux comme partage du surplus,
deux estimateurs de branching et contrôle conjoint de `alpha` et `b` venaient-elles
d'une même intuition ou ont-elles été assemblées au fil des résultats ?

**Réponse inférée.** M4.4 déplace l'objet de l'agrégat vers la distribution :
une production totale supérieure ne dit pas qui en bénéficie ni si la queue se
renforce. Le chantier du taux a été ajouté le 24 août pendant la campagne,
après avoir constaté que le taux historique impliquait un partage moyen proche
de 1/2. L'analyse de `rho` réunit ensuite les deux fils anciens du stage :
piloter les exposants de queue et piloter les cascades par une même institution.

**Pièces du corpus.**

- `m4_4_rebond_credit_soc/PLAN_M4_4_REBOND.md` ;
- `m4_4_rebond_credit_soc/JOURNAL.md` ;
- `m4_4_rebond_credit_soc/report/rapport_final.tex` ;
- `m4_4_rebond_credit_soc/README.md`.

**Réponse d'Anatole :** Exact. Spécification et compréhension du mécanisme de rebond, et vérification que les paramètres implicites ou arbitraires ne sont pas cruciaux au fonctionnement.  le partage de la plus value est aussi une très très grande question théorique économique. C'est donc une suite naturelle aux questionnements qui suivent l'étude du modèle. 

### QT-28 — Pourquoi ne pas rouvrir la validation de Pareto ni analyser la coupure dans M4.4 ?

**Nature :** mixte.

**Question.** Le plan interdit de refaire la validation de la queue et demande
de n'ajuster que des lois de puissance sur les avalanches, sans analyse de
coupure. Était-ce une décision de ta part pour éviter une dérive de périmètre,
ou une contrainte héritée des agents ? Pourquoi accepter alors de caractériser
des exposants `alpha` tout en laissant la famille exacte ouverte ?

**Réponse inférée.** M4.2B avait déjà montré que Pareto contre lognormale
tronquée était non décidable avec la méthode et le support disponibles. M4.4
pose donc la queue comme hypothèse de travail et cherche uniquement si son
indice varie sous intervention. L'analyse de coupure des avalanches est écartée
pour préserver la comparabilité avec le mandat et éviter de transformer une
question de réponse des exposants en nouvelle campagne de sélection de modèles.
Il faut confirmer que cette limitation reflète bien ton arbitrage scientifique.

**Pièces du corpus.**

- `m4_4_rebond_credit_soc/PLAN_M4_4_REBOND.md`, section des acquis ;
- `m4_4_rebond_credit_soc/scripts/laws.py` et `tails.py` ;
- `m4_4_rebond_credit_soc/JOURNAL.md`, lots C et E ;
- `m4_2b_credit_soc/JOURNAL.md`.

**Réponse d'Anatole :** Ce n'est juste pas encore fait. Manque de temps pour une étude propre aussi. 

### QT-29 — Comment décidais-tu qu'une quantité était un résultat, une identité ou un simple corrélat ?

**Nature :** mixte.

**Question.** Les journaux récents corrigent plusieurs surinterprétations :
`E=1` pour l'amplitude est une réécriture des définitions ; la décomposition de
l'élasticité par `K_eq` n'est pas plusieurs preuves ; mortalité × population à
l'état stationnaire relève de la loi de Little ; `rotation = rho*Gini` est une
identité ou une approximation selon le régime ; une forte régression n'établit
pas le canal. Cette vigilance était-elle déjà une règle consciente du stage ou
s'est-elle formée surtout pendant les relectures de Live-v1/V2/M4.4 ?

**Réponse inférée.** La distinction s'est renforcée progressivement. Les
premiers travaux cherchaient surtout des signatures. Les erreurs de tests et
les relations trop belles ont ensuite imposé de demander si une égalité pouvait
être fausse, si ses deux côtés étaient mesurés indépendamment et si une ablation
pouvait couper le canal. V2 et M4.4 formalisent cette doctrine en balisant
`fait`, `inférence`, `hypothèse` et `incertitude`.

**Pièces du corpus.**

- journaux M2–M4.4 ;
- `m4_3live_credit_soc/JOURNAL.md`, relecture annotée ;
- `m4_3live_v2_credit_soc/report/JOURNAL.md` ;
- `m4_4_rebond_credit_soc/report/rapport_final.tex`.

**Réponse d'Anatole :** Exact. Point crucial de la méthodologie. 

### QT-30 — Quelle place les contraintes de calcul ont-elles prise dans les décisions scientifiques ?

**Nature :** témoignage nécessaire.

**Question.** Dans quels cas le temps CPU, la mémoire ou le stockage ont-ils
réellement modifié le plan expérimental : arrêt à 7,8 Go, budget M3 de 48 h,
choix de `lambda=30`, seuils de garde mémoire M4.2B/M4.3, suppression de données
brutes, nombre de graines fixé après pilote, symlinks vers Simulation Lab ?
Quels résultats n'ont pas été poursuivis pour raison de ressources plutôt que
pour raison scientifique ?

**Réponse inférée.** Les contraintes ont été traitées comme une partie du
protocole : profiler avant d'allouer, mesurer le coût d'une cellule, paralléliser
avec une réserve de cœurs, interrompre les carnets combinatoires, conserver les
agrégats et supprimer seulement des bruts régénérables ou non nécessaires. Elles
ont déterminé la couverture et parfois le nombre de graines, mais les journaux
cherchent à distinguer « non testé faute de ressources » de « hypothèse
réfutée ».

**Pièces du corpus.**

- rapports de profilage du modèle du 27 avril ;
- `anciens_modeles/m2_fable/reports/research_log.md` ;
- `anciens_modeles/m3_credit_soc/NOTES.md`, budget ;
- journaux M4.2B et M4.3, incidents mémoire ;
- journaux Live-v2 et M4.4, coûts des pilotes et campagnes.

**Réponse d'Anatole :** Exact. D'une manière général, le lancement de campagne par ssh sur mon temps libre ainsi que la puissance de calcul de mon poste m'ont permis de traiter mes questions correctement. Une question reste (timidement) en attente. On a trouvé une pseudo conservation temporelle d'échelle, qui permettrait de réduire énormément les temps de calculs. Une échelle très petite permettrait une sorte d'étude qui se rapproche du continue : converge t'elle ? mes simulations sont elles représentatives du fonctionnement "en continu" ? Cette étude reste à faire. C'est un point que je souhaite noter et faire savoir. 

## 3. Questions techniques transversales — à traiter dans un second lot

### QT-31 — Architecture des entités et des contrats

**Question.** Pourquoi passer du premier moteur monolithique à des dataclasses,
des identifiants entiers et des dictionnaires de contrats, puis à des index
`by_lender/by_borrower` ? Était-ce d'abord une recherche de lisibilité, de
sécurité des références lors des faillites, de performance, ou de capacité à
mesurer les réseaux ?

**Réponse inférée.** Les identifiants évitent les références d'objets devenues
invalides après liquidation ; les dataclasses et la modularisation rendent les
règles testables ; les index suppriment les balayages répétés du carnet. Les
trois motivations se succèdent plutôt qu'elles ne s'excluent.

**Sources.** `anciens_modeles/claude3-v2/README.md`, codes `models.py` et
`simulation.py`, rapports de profilage du 27 avril, codes M2–M4.

**Réponse d'Anatole :** Exact. 

### QT-32 — Reproductibilité aléatoire

**Question.** Pourquoi isoler très tôt le générateur `random.Random(seed)`, puis
passer dans les moteurs réduits à `numpy.random.default_rng(seed)` ? Quelles
garanties exigeais-tu : répétabilité macro, ordre exact des tirages, absence de
consommation par les mesures, parité bit à bit ?

**Réponse inférée.** La graine seule ne suffit pas si le RNG global ou une
fonction d'observation consomme des tirages. Le programme a progressivement
exigé une séquence locale, des mesures neutres et, pour les forks, la même
trajectoire au dernier bit. Le passage à NumPy accompagne les moteurs vectorisés
et les sorties `.npz`, mais la raison exacte du changement reste à documenter.

**Sources.** README des premières versions, test I8 de M3, tests de parité M4B,
M4.2, M4.3 et Live.

**Réponse d'Anatole :** pas de raison particulière. Néanmoins la reproductibilité au bit près m'a permis d'étendre mes découvertes sur le modèle d'une version à l'autre. C'est crucial pour prétendre avoir une continuité dans l'étude. 

### QT-33 — Pourquoi l'égalité bit à bit est-elle devenue un critère ?

**Question.** Pourquoi une simple proximité statistique ne suffisait-elle pas
pour valider une optimisation ou un fork ? Dans quels cas as-tu accepté un
écart borné — par exemple après sérialisation d'un `set` — et dans quels cas
zéro écart était obligatoire ?

**Réponse inférée.** Pour une optimisation annoncée neutre ou une réduction de
moteur, tout écart de trajectoire pouvait masquer une modification scientifique ;
l'identité bit à bit était donc le test le plus simple. Pour une sauvegarde qui
ne garantit pas l'ordre interne d'un ensemble, le dernier bit d'une somme pouvait
changer sans déplacer les verdicts : l'écart devait alors être mesuré et
documenté, non présenté comme nul.

**Sources.** `anciens_modeles/modele-27-04-WIP/CHANGELOG.md`, tests M4B,
M4.2/M4.3, `m4_3live_credit_soc/tests/test_replay.py` et journaux Live-v2.

**Réponse d'Anatole :** Exact, mais j'aurais pu me satisfaire d'une conservations des statistiques générales (la simulation tombe dans la variabilité inter-seed)

### QT-34 — Profilage et optimisation conservatrice

**Question.** Pourquoi investir du temps dans `cProfile`, `tracemalloc`, les
indexes incrémentaux, le cache des vivantes et l'inlining ? Le gain de temps
était-il nécessaire pour rendre possibles les campagnes, ou constituait-il
aussi un apprentissage technique autonome ? Pourquoi refuser NumPy à ce stade
afin de préserver l'ordre des additions flottantes ?

**Réponse inférée.** Les longs runs devenaient dominés par des balayages de
prêts et d'entités ; le speedup croissant avec l'horizon rendait les campagnes
envisageables. Les optimisations étaient acceptées uniquement avec non-régression
stricte. La vectorisation des réductions aurait changé l'ordre flottant et donc
la trajectoire, ce qui brouillait la distinction entre amélioration technique
et nouveau modèle.

**Sources.** `anciens_modeles/modele-27-04-WIP/RAPPORT_PROFILAGE_MODELE_27_04_WIP.md`,
`anciens_modeles/modele-27-04-WIP/CHANGELOG.md`, profils `.prof` et
`anciens_modeles/modele-27-04-WIP/tests/test_non_regression.py`.

**Réponse d'Anatole :** Exact. On cherche à optimiser notre capacité d'étude du modèle. 

### QT-35 — Choix des formats de données

**Question.** Pourquoi combiner CSV, JSON, CSV gzip, snapshots NPZ, pickle de
reprise et JSONL d'interventions ? Quelles données devaient rester lisibles à
l'œil, lesquelles étaient optimisées pour le volume, lesquelles servaient à
rejouer ou bifurquer une trajectoire ?

**Réponse inférée.** JSON porte configurations, manifestes et résumés ; CSV
porte les séries auditables ; gzip rend possibles les trajectoires
individuelles ; NPZ stocke efficacement les états et réseaux numériques ;
pickle conserve l'état interne exact pour la reprise ; JSONL journalise une
suite d'interventions append-only. Le choix s'est diversifié avec les besoins
de traçabilité et de reprise.

**Sources.** modules `io.py` de M4B à M4.3, `live.py` des lignées Live,
`simulation_lab/runs/storage.py`, README des moteurs.

**Réponse d'Anatole :** Exact. Simulation Lab m'a permis d'avoir toutes les visualisations que je souhaitais. 

### QT-36 — Pourquoi séparer données primaires, analyses et figures ?

**Question.** À quel moment cette séparation est-elle devenue une exigence ?
Était-elle motivée par les erreurs d'agents, le besoin de régénérer les rapports,
la taille des campagnes, ou la volonté de ne jamais recopier un chiffre à la
main ?

**Réponse inférée.** Les premières sorties mêlaient davantage exécution et
interprétation. À partir de M4B, chaque run conserve les bruts, des scripts
produisent les métriques, d'autres les figures et des macros alimentent les
rapports. Les corrections répétées ont montré qu'une figure ou un paragraphe
ne devait pas devenir une source indépendante des données dont il dérive.

**Sources.** architecture M4B, `recherche/sensibilite_m4b/`, scripts
`make_numbers.py` et `make_traceability.py` de Live-v2/M4.4.

**Réponse d'Anatole :** Exact, et le dossier pesait 70Go. Je dois garder de la place sur mon disque dur !

### QT-37 — Choix du burn-in et des fenêtres

**Question.** Comment choisissais-tu le burn-in à chaque époque : valeur fixe
500, fraction `T/4`, comparaison `T/8–T/2`, relaxation mesurée par blocs,
FOPDT du renouvellement, ou fenêtre adaptative par run ? Pourquoi les intérêts
ont-ils nécessité une relaxation distincte de la population ?

**Réponse inférée.** Le burn-in a d'abord été estimé visuellement autour de
500, puis contrôlé par fenêtres. M4B utilise `T/4` et teste sa robustesse.
M4.2B constate ensuite que différentes observables, notamment le revenu
d'intérêt, relaxent à des vitesses différentes et passe à une fenêtre mesurée
par run. Le choix devient donc observable-dépendant plutôt qu'une convention
universelle.

**Sources.** rapport d'élagage du 27 avril, analyse des cohortes, protocole
M4B, journaux M4.2B et M4.3.

**Réponse d'Anatole :** Exact. 

### QT-38 — Pourquoi ne jamais pooler les graines ?

**Question.** Cette règle visait-elle surtout à conserver l'unité de
réplication, à ne pas gonfler artificiellement la puissance statistique ou à
voir les instabilités de seuil entre trajectoires ? Comment distingues-tu
pooling interdit des individus et agrégation légitime des estimations par
graine ?

**Réponse inférée.** Les individus d'une même trajectoire ne sont pas des
réplications indépendantes, et fusionner plusieurs graines peut masquer un
changement de régime ou de `xmin`. Les fits sont donc faits par snapshot ou
par graine ; les paramètres obtenus sont ensuite résumés entre graines. Les
comparaisons appariées exploitent la même graine pour réduire le bruit sans
fusionner les populations.

**Sources.** rapports d'analyse distributionnelle, M2, M4, M4B, M4.2B et
M4.4.

**Réponse d'Anatole :** Exact. 

### QT-39 — Pourquoi séparer exploration et confirmation ?

**Question.** Quel incident ou risque a rendu nécessaire l'emploi de graines
disjointes et de critères figés ? Pourquoi certaines analyses post-hoc ont-elles
encore été considérées informatives lorsqu'elles réutilisaient les mêmes runs ?

**Réponse inférée.** L'exploration servait à trouver les plages, métriques et
candidats ; conclure sur les mêmes fluctuations aurait favorisé les faux
positifs. Des graines séparées testaient donc la reproductibilité des signes.
Une analyse post-hoc pouvait rester informative si elle était explicitement
étiquetée, calculée à partir de données conservées et vérifiée sur les graines
confirmatoires, sans être présentée comme pré-enregistrée.

**Sources.** protocole M4B, journaux M4B/M4.3, extensions NW/cycles, campagnes
appariées Live-v2/M4.4.

**Réponse d'Anatole :** Exact

### QT-40 — Quel rôle les agents ont-ils joué dans la technicité du stage ?

**Question.** Quelles tâches leur déléguais-tu réellement : implémentation,
profilage, plans d'expérience, calcul statistique, interprétation, rédaction,
audit ? Comment vérifiais-tu une proposition avant de l'adopter ? Quels types
d'erreurs d'agents ont le plus influencé ta méthode de travail ?

**Réponse inférée.** Codex et Fable ont servi d'instruments de calcul, de
codage, de critique et de rédaction sous prompts détaillés. Tu choisissais les
questions, axes et décisions scientifiques, puis contrôlais par comparaison du
code, tests, figures, runs et demandes de vérification. Les erreurs les plus
formatrices concernent les tests statistiques mal normalisés, le seuil
`/2`, les explications causales trop rapides, la sélection de graines après
coup et les critères de stationnarité trop rigides.

**Sources.** prompts de sensibilité et de conception, journaux M2–M4.4,
rapports de correction, tests et annotations de relecture.

**Réponse d'Anatole :** Exact. Je n'accepte que du code que j'aurais été capable de coder en temps asymptotique, et je contrôle chaque élément que me donne un LLM. Néanmoins, il est jouissif de demander "Caractérise la sensibilité de tel paramètre à tel autre paramètre" sans avoir à coder le code, la visualisation, etc. 

## 4. Questions de clôture à poser après les réponses précédentes

Ces questions ne doivent être posées qu'après consolidation des lots 2 et 3.
Elles synthétisent la trajectoire et risqueraient sinon de produire une
reconstruction trop propre.

1. Quelles sont les trois décisions techniques qui ont le plus changé le
   contenu scientifique du stage ?
2. Quelle expérience t'a le plus convaincu de poursuivre l'hypothèse SOC, et
   quelle expérience t'a le plus rapproché de l'abandonner ?
3. Quel résultat as-tu accepté malgré sa contrariété avec ton intuition, et par
   quelle méthode a-t-il fini par s'imposer ?
4. Quelle donnée aurais-tu voulu exploiter mais as-tu laissée de côté faute de
   temps, de puissance ou de définition empirique compatible ?
5. Quelle règle du modèle considères-tu aujourd'hui comme une hypothèse
   scientifique, laquelle comme une institution exploratoire, et laquelle
   comme une simple convention numérique ?
6. Quel est le niveau de preuve maximal atteint pour chacun des trois objets :
   queue lourde, propagation causale, auto-organisation critique ?
7. Parmi M4.3Live-v1, Live-v2 et M4.4, quels résultats doivent figurer dans le
   corps du rapport, en annexe, ou seulement dans l'historique de recherche ?
8. Si le stage devait être résumé par une seule chaîne
   « question → méthode → résultat → décision », laquelle choisirais-tu ?

## 5. Règle d'intégration future au mémo maître

Une réponse ne sera pas copiée telle quelle dans le mémo. Elle sera :

1. datée comme témoignage ;
2. confrontée aux codes, rapports, prompts, journaux et sorties cités ;
3. séparée des affirmations d'agents ;
4. reliée à la décision ou à la modification de modèle correspondante ;
5. accompagnée des contradictions ou limites encore visibles ;
6. soumise à une note de relecture avant intégration lorsqu'elle modifie
   substantiellement la chronologie ou le statut d'un résultat.
