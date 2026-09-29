# Inventaire des sources, données et preuves du stage

**Auteur du travail scientifique :** Anatole Joseph-Stouls  
**Cadre :** ENS Rennes, département mécatronique, parcours *Recherche aux
interfaces* — stage de recherche au LIED  
**Statut :** inventaire évolutif, version 0.2  
**Document narratif associé :** memo_recherche_complet.md

## 1. Fonction de cet inventaire

Ce fichier constitue la couche de provenance du dossier de recherche. Il sert à
préparer, sans les rédiger encore :

- un rapport de stage ;
- une fiche d'avancement ;
- une note de communication ;
- une présentation orale ;
- une discussion scientifique centrée sur un résultat particulier.

Il répond à quatre questions pour chaque pièce du dépôt :

1. Quel rôle joue-t-elle dans la trajectoire de recherche ?
2. Quelles affirmations permet-elle de soutenir ?
3. Quel est son niveau de preuve et son statut de lecture ?
4. Est-elle indépendante, dérivée, dupliquée ou historique ?

Les choix futurs de longueur, de lectorat et de mise en forme ne sont pas
traités ici.

## 2. Légende

### Statut scientifique

- **Source primaire interne** : code, données brutes, manifeste ou journal
  permettant un recalcul.
- **Analyse interne** : traitement reproductible de sources primaires.
- **Synthèse interne** : texte qui assemble des analyses mais ne constitue pas
  une confirmation supplémentaire.
- **Source académique** : article, thèse ou ouvrage de la bibliothèque.
- **Matériau de récit** : note, présentation ou échange utile pour reconstruire
  le raisonnement.
- **Archive** : état historique conservé pour la chronologie, non canonique.

### Statut d'exploitation

- **Intégré** : information principale déjà versée au mémo maître.
- **Partiellement intégré** : conclusions centrales reprises, détails à
  dépouiller.
- **À dépouiller** : pièce repérée mais pas encore exploitée systématiquement.
- **Navigation seulement** : index ou copie utile pour localiser une source.

## 3. Points d'entrée canoniques

| Pièce | Statut | Rôle | Exploitation |
|---|---|---|---|
| README.md | synthèse interne | point d'entrée du dépôt et statut des lignées | intégré |
| recherche/memo_stage/memo_recherche_complet.md | synthèse interne | dossier narratif exhaustif, niveaux de preuve et questions | intégré, actif |
| recherche/memo_stage/inventaire_sources_preuves.md | inventaire | provenance et carte des preuves | actif |
| m4b_credit_soc_mini/ | source primaire interne | moteur minimal M4B actif | intégré |
| recherche/sensibilite_m4b/ | sources primaires + analyses | campagne quantitative principale | intégré |
| m4_2_credit_soc/ | conception | prochaine version et tests de pilotage de l'exposant | partiellement intégré |
| Zotero local | sources académiques | corpus bibliographique principal, 43 références | partiellement intégré |

## 4. Lignée scientifique et pièces associées

| Étape | Question ou bascule | Sources principales | Statut |
|---|---|---|---|
| Premiers modèles | construire un système physico-économique riche | anciens_modeles/claude/, anciens_modeles/claude3-v2/, notes d'avril | historique, à dépouiller pour le récit |
| Modèle du 27 avril | distributions de taille et de revenu ; premières interprétations en classes | recherche/note_de_travail/latex/note.tex, anciens_modeles/modele-27-04-WIP/ | partiellement intégré |
| Diagnostic des cohortes | montrer que la bimodalité et la queue initiales sont dominées par l'âge et l'horizon | recherche/analyse_distributions_taille_revenu/latex/rapport.tex | intégré |
| M2 | tester si le crédit modifie les formes distributionnelles | anciens_modeles/m2_codex/, anciens_modeles/m2_fable/ | intégré dans ses conclusions ; détails disponibles |
| M3 | rendre le crédit causal sur la démographie et séparer liquidité/capital | anciens_modeles/m3_credit_soc/NOTES.md, rapports 01–07 | intégré dans ses conclusions |
| M4 | obtenir une propagation causale par annulation–destruction | m4_credit_soc_fable/NOTES.md, reports/01_soc_final/main.tex | intégré |
| M4 parallèle | branche expérimentale de contrôle, non preuve indépendante de M4B | m4_credit_soc_sol/NOTES.md, reports/m4_research/REPORT.md | partiellement intégré |
| M4B | réduire M4 au mécanisme minimal auditable | m4b_credit_soc_mini/report/mecanique_m4b.tex, code et tests | intégré |
| Sensibilité M4B | établir robustesse, hiérarchie des paramètres, effets de taille, NW et cycles | recherche/sensibilite_m4b/ | intégré, référence quantitative |
| Boltzmann–Pareto | explorer l'arbitrage mécanisme minimal / similarité distributionnelle | recherche/conception_boltzmann_pareto_soc/ | intégré comme branche secondaire |
| M4.2 | manipuler l'exposant et tester la concavité | m4_2_credit_soc/prompts/PROMPT_M4_2.md, protocole et journal | chantier courant, partiellement intégré |

## 5. Paquets de preuves internes

### 5.1 Artefact de cohorte et dérive temporelle

**Affirmations soutenues**

- La première séparation en classes était principalement une séparation de
  cohortes.
- La corrélation âge–log(taille) était très forte.
- L'exposant de queue dérivait avec l'horizon.
- Une loi visuellement plausible peut être un artefact de simulation.

**Pièces**

- recherche/analyse_distributions_taille_revenu/latex/rapport.tex
- figures du même dossier ;
- données et scripts associés ;
- recherche/note_de_travail/latex/note.tex pour l'interprétation antérieure.

**Indépendance**

Le rapport distributionnel critique la note initiale ; les deux textes ne sont
pas deux confirmations d'un même résultat.

### 5.2 Ablations M2 et M3

**Affirmations soutenues**

- Dans M2, le crédit ne transforme pas les familles principales.
- Dans M2, le corps est généralement Fisk et la queue effective, malgré un
  exposant assez stable, n'est pas identifiée comme Pareto face à la
  log-normale tronquée après correction des outils statistiques.
- Dans M3, le crédit modifie la population et la durée de vie mais pas les
  distributions de la baseline ; cette neutralité est conditionnelle à la
  règle comportementale.
- L'ablation H de M3 montre que la dette contractuelle peut remplacer le
  plancher exogène d'absorption et suggère le passage vers M4.
- La règle de revenu X1 rend le crédit distributionnellement actif et allume
  l'illiquidité, sans produire de SOC.
- La liquidité de M3 n'est pas Boltzmann--Gibbs dans le régime étudié.
- Les résultats négatifs ont conduit à reformuler la causalité recherchée.

**Pièces**

- anciens_modeles/m2_codex/reports/04_validation_report/main.tex
- anciens_modeles/m2_codex/reports/05_negative_results/main.tex
- anciens_modeles/m2_fable/reports/04_validation_report/main.tex
- anciens_modeles/m2_fable/reports/05_negative_results/main.tex
- anciens_modeles/m3_credit_soc/reports/04_validation_report/main.tex
- anciens_modeles/m3_credit_soc/reports/05_negative_results/main.tex
- anciens_modeles/m3_credit_soc/reports/06_final_synthesis/main.tex
- anciens_modeles/m3_credit_soc/reports/07_income_rule/main.tex

**Indépendance**

Les branches Codex et Fable de M2 sont des réplications critiques apparentées.
Leur degré d'indépendance doit être évalué à partir de leurs prompts, codes et
graines avant toute formulation forte.

**Réserves de protocole M3**

- L'ablation F ne teste pas proprement la topologie : la randomisation réduit
  le volume de crédit d'un facteur d'environ 6,5 et éteint presque le marché.
- G1 confond chocs corrélés et réduction de la dispersion idiosyncratique ; G2
  porte seul le verdict utile sur la synchronisation sectorielle.
- Un bug d'observation non neutre et un cas dégénéré de l'estimateur CSN ont été
  détectés puis corrigés et couverts par des tests.
- X1 est un protocole descriptif post-M3, défini avant son exécution mais non
  pré-enregistré avec les critères du rapport de spécification M3.

### 5.3 Passage de synchronisation à propagation

**Affirmations soutenues**

- Les chocs corrélés de M3 synchronisent les décès sans créer une cascade
  causale.
- Les premières lois de puissance apparentes de M4 sous chocs sectoriels
  portent encore sur des grappes de racines synchronisées.
- Le candidat (k=3) antérieur à annulation--destruction est un effet de taille
  finie qui se déforme en bosse à grand système.
- M4 rend la perte de créance causalement propagative.
- La règle d'annulation–destruction est le mécanisme minimal retenu.
- La naissance par emprunt, pourtant directement inspirée de la dette de
  subsistance de M3-H, n'est pas nécessaire à cette propagation.

**Pièces**

- anciens_modeles/m3_credit_soc/NOTES.md
- m4_credit_soc_fable/NOTES.md
- m4_credit_soc_fable/reports/01_soc_final/main.tex
- journaux de cascades et graphes parent–enfant de M4.

**Chronologie contrôlée**

- 13 juillet 2026 : restauration des tests M3, construction d'estimateurs
  discrets, confirmation puis réfutation de la piste sectorielle comme
  contagion ; prototype à un seul (K) ; test de la naissance par emprunt.
- 14 juillet : réfutation du pseudo-critique (k=3) par scaling ; découverte de
  la combinaison annulation--destruction ; ablations, scaling, étude du volume
  de marché et promotion du moteur fusionné.
- 16 juillet : campagne confirmatoire via Simulation Lab, 15 runs
  ​(​3 tailles × 5 graines, (T=4000)​).
- 17 juillet : analyses distributionnelles complémentaires, révisions des fits
  et passage de M4 en référence historique au profit de M4B.

**Précautions**

- L'en-tête du journal M4 annonce « objectif atteint » au sens de la campagne
  de branche. Cette formulation est un état historique, non le verdict final du
  stage sur la SOC.
- Plusieurs ajustements distributionnels du 16--17 juillet se renversent quand
  une famille composite supplémentaire est introduite. Ils illustrent la
  dépendance du verdict au jeu de modèles candidats et motivent la doctrine de
  validation du mémo.
- Les résultats M4 sont les ancêtres de M4B ; ils ne s'ajoutent pas comme
  confirmation indépendante à la campagne de sensibilité M4B.

### 5.4 Mécanique minimale M4B

**Affirmations soutenues**

- M4B reproduit la mécanique utile de M4 avec un seul stock interne, du crédit
  nominal, des chocs, une production concave et la faillite
  annulation–destruction.
- Les invariants comptables sont testables.
- M4B est une réduction de M4, non une confirmation indépendante.

**Pièces**

- m4b_credit_soc_mini/m4b/
- m4b_credit_soc_mini/tests/
- m4b_credit_soc_mini/report/mecanique_m4b.tex
- m4b_credit_soc_mini/README.md

### 5.5 Campagne de sensibilité M4B

**Affirmations soutenues**

- Régime stationnaire sur l'espace exploré.
- Hiérarchie de \(\sigma\), \(k\), \(K_0\), \(\delta\), \(\lambda\).
- Loi de puissance tronquée, effets de taille finie et exposant de grand système.
- Inégalité portée par \(NW\), cycle débiteur–créancier, canal de liquidité
  silencieux.
- Baselines de production et d'énergie totale pour les contractions.

**Sources primaires**

- simulation_lab_data/runs/ : séries, avalanches, décès, entités et bilans ;
- recherche/sensibilite_m4b/manifests/ : plans OAT, LHS, coupes et
  confirmation ;
- recherche/sensibilite_m4b/JOURNAL.md : décisions et corrections ;
- recherche/sensibilite_m4b/scripts/ : extraction et analyses ;
- recherche/sensibilite_m4b/results/ : métriques dérivées.

**Synthèses**

- recherche/sensibilite_m4b/report/rapport_final.tex
- recherche/sensibilite_m4b/report/protocole.tex
- annexes de traçabilité.

**Précautions**

- Les extensions \(NW\) et cycles sont post-audit, sur les mêmes runs, avec
  graines confirmatoires séparées mais sans nouvelles simulations.
- Les figures et rapports dérivent des mêmes données et ne constituent pas des
  preuves indépendantes.
- Les colonnes energy des tables de cycles ont été ajoutées le 27 juillet 2026
  pour \(E_t=\sum_iK_i(t)\).

### 5.6 Branche Boltzmann–Pareto

**Affirmations soutenues**

- Une queue stable peut être produite sans obtenir un corps exponentiel strict.
- Gamma, lognormale ou Fisk peuvent mieux décrire le corps.
- Le nombre de paramètres d'un fit ne suffit pas à juger la plausibilité d'un
  mécanisme.

**Pièces**

- recherche/conception_boltzmann_pareto_soc/conception_modele_M2.md
- recherche/conception_boltzmann_pareto_soc/latex/rapport.tex
- dossier exploration/.

**Statut**

Branche théorique secondaire ; résultats provisoires à ne pas mélanger avec la
baseline M4B.

## 6. Corpus académique déjà exploité

| Thème | Références Zotero principales | Apport | Limite révélée |
|---|---|---|---|
| Monnaie, richesse, revenu | Yakovenko & Rosser | corps exponentiel, queue de Pareto, distinction des objets | revenus fiscaux personnels, exposants variables |
| Architecture sociale | Ian Wright, deux modèles | distributions multiples issues de règles minimales ; revenus, firmes, récessions | conventions d'implémentation et objets mélangés |
| Ajustement des revenus | Fisk | hétérogénéité des groupes, trois contre quatre paramètres | pas de loi globale évidente |
| Richesse en réseau | Bouchaud & Mézard | condensation et queue de Pareto | objet richesse abstrait et mécanisme spécifique |
| Cascades | Watts | exposant théorique \(3/2\), formes puissance ou bimodale | absence déclarée de données empiriques de taille de cascade |
| SOC | Bak, Dhar, Dickman–Vespignani–Zapperi | accumulation–relaxation, criticité, processus absorbants | une loi de puissance seule ne prouve pas la SOC |
| Récessions | Wright et références citées | durées courtes, lois exponentielle ou puissance selon corpus | conventions et résultats non unifiés |
| Firmes | Wright, Dessertaine, Arvidsson et al. | croissance des ventes Laplace/Subbotin ; tailles lourdes ; hétérogénéité urbaine | niveau du chiffre d'affaires encore insuffisamment caractérisé |
| Rebond | Sorrell & Dimitropoulos | définitions, service, ressource et contrefactuel | M4B ne sépare pas encore ressource et service |
| Métabolisme et échelle | West–Brown–Enquist, Herbert et al., Hendrick et al. | lois d'échelle, contraintes énergétiques, structure | passage micro–macro et cible distributive non directs |

## 7. Lacunes empiriques comme résultats de recherche

| Objet recherché | Ce qui existe | Ce qui manque pour tester M4B | Conséquence actuelle |
|---|---|---|---|
| Revenu personnel brut | données fiscales et enquêtes ; corps exponentiel/lognormal + queue Pareto | convention parfaitement alignée sur le proxy M4B | comparaison qualitative seulement |
| Chiffre d'affaires des firmes | lois de croissance des ventes ; lois de « taille » | distribution du niveau, périmètre, seuils et source primaire explicites | chantier bibliographique |
| Patrimoine / taille nette | quelques distributions de richesse nette | correspondance avec \(NW\) non recherchée dans l'ambition actuelle | diagnostic de forme, pas calibration |
| Cascades de faillites | modèles théoriques ; tailles ou fréquences de faillites | graphe causal racine–descendants et taille des cascades | exposant empirique non fixé |
| Consommation d'exergie | résultats sectoriels et définitions multiples | unité, population et échelle communes | pas de cible unifiée |
| Mobilité sociale | matrices et mesures dépendant du corpus | trajectoires comparables et filiation | hors moteur actuel |
| Récessions énergétiques | datations PIB et lois de durée variables | agrégat comparable à \(E_t\), seuil et temps | baseline interne seulement |

**Lecture épistémique.** Ces lacunes ne valident pas le modèle. Elles empêchent
cependant de le rejeter contre une cible arbitraire ou mal définie. Le verdict
externe est suspendu jusqu'à construction d'une comparaison compatible.

## 8. Matériaux de récit et de communication à dépouiller

| Zone | Contenu attendu | Exploitation actuelle |
|---|---|---|
| presentation/ | première présentation, figures et frise chronologique | partiellement intégré |
| presentation_2_le_retour/ | révision de la même présentation, non indépendante | partiellement intégré |
| codex_analysis_workspace/notes/ | mémos des 3 avril et analyses formelles | intégré pour les conclusions centrales |
| codex_analysis_workspace/papers/ | rapports sur régimes formels et pont prédictif | partiellement intégré |
| docs/note_de_travail_codex.txt | note historique transversale | à dépouiller |
| docs/RAPPORT_COMPARAISON_VERSIONS.md | audit technique des premières versions | partiellement intégré |
| échanges avec l'auteur | motivations, moments de bascule, rôle de l'encadrement, échecs | intégration continue |
| presentation/informations/Texte candidature.txt | rapport personnel à la recherche et constat bibliographique contemporain | intégré pour les thèmes centraux |

Ces pièces sont importantes pour reconstruire ce que l'auteur savait et croyait
à chaque étape. Elles ne doivent pas servir à antidater une interprétation
apparue plus tard.

**Constats du premier dépouillement**

- Début avril, la revendication de SOC est explicitement retirée après critique.
- Le WIP historique présente des flux quasi-stationnaires mais des stocks
  dérivants ; il ne constitue pas un attracteur SOC complet.
- Le suivi partiel des entités surreprésentait la cohorte initiale.
- Le seuil topologique entre \(k=2\) et \(k=3\) est quantifié sur dix graines
  dans le round 4 historique.
- Les présentations de mai réintroduisent la SOC comme hypothèse de programme,
  non comme conclusion démontrée.
- Elles présentent encore les « deux populations » comme un résultat
  économique ; l'analyse distributionnelle ultérieure l'identifiera comme un
  artefact de cohortes.
- presentation_2_le_retour est une révision éditoriale de presentation, avec
  notamment une définition SOC ajoutée et une annexe sur les corrélations ;
  elle ne constitue pas une source scientifique indépendante.
- Le texte de candidature formule déjà le paradoxe d'une littérature abondante
  et pertinente qui ne répond jamais directement à la question posée. Il
  atteste que la lacune de comparabilité empirique a été vécue pendant la
  recherche, et non ajoutée après coup pour protéger le modèle.

### Chronologie de formation disponible pour de futures communications

La frise de présentation documente les éléments suivants, à conserver comme
matériau biographique et non comme résultat scientifique :

- 2018–2020 : CPGE MPSI au lycée Lakanal puis PSI au lycée Michelet ;
- 2020–2021 : ENSAM ParisTech, campus de Lille, avec préparation parallèle des
  concours ENS en candidat libre ;
- à partir de 2021 : ENS Rennes, département mécatronique ;
- L3 électronique, génie électrique et automatique, et L3 sciences pour
  l'ingénieur / ingénierie des systèmes complexes ;
- L3 mathématiques puis M1 mathématiques fondamentales en parallèle ;
- année pluridisciplinaire ENS : M2 mathématiques et applications,
  mathématiques avancées pour l'enseignement secondaire et supérieur,
  préparation de l'agrégation ;
- formation ENSAM en énergie électrique pour le développement durable.

La narration de candidature relie cette trajectoire à une préférence pour les
« mathématiques du réel », la physique statistique, la probabilité et
l'interdisciplinarité. Ces éléments pourront servir à une note de communication
personnelle ou à l'introduction institutionnelle d'un rapport, mais leur place
sera décidée ultérieurement.

## 9. Archives, liens et doublons

- arborescence_modeles/ contient des liens symboliques historiques, pas des
  réplications.
- modeles-systeme-physicoeconomique/ contient surtout des adaptateurs de
  Simulation Lab ; seul M4B est lançable.
- archives/ et banque_versions_zip/ conservent des états historiques.
- anciens_modeles/4-05-dynamique/ et
  anciens_modeles/modele-27-04-WIP/studies/sensitivity/ contiennent des
  campagnes proches ou dupliquées ; leur provenance doit être comparée avant de
  compter des résultats séparément.
- Les PDF sont des rendus des sources Markdown ou LaTeX correspondantes, non des
  sources indépendantes.
- Les rapports M4 et M4B décrivent une lignée de réduction ; ils ne fournissent
  pas deux confirmations indépendantes.

## 10. Carte minimale affirmation–preuve

| ID | Affirmation | Source primaire ou analyse | Statut |
|---|---|---|---|
| P1 | Le premier modèle produisait un artefact de cohorte | analyse distributions taille/revenu | établi pour cette lignée |
| P2 | Le crédit est distributionnellement neutre dans M2 | ablations M2 | établi pour M2 |
| P3 | Le crédit modifie la démographie dans M3 | rapports M3 | établi pour M3 |
| P3a | Le crédit est neutre sur les distributions dans la baseline M3 | ablation A/B M3 | établi pour cette règle de comportement |
| P3b | La règle X1 rend le crédit distributionnellement actif | protocole X1, 18 runs | exploratoire robuste sur les cellules testées |
| P3c | La dette contractuelle remplace le plancher exogène dans H | ablation H, trois graines | établi dans M3 |
| P3d | La liquidité M3 n'est pas Boltzmann--Gibbs | ajustements de L | établi sur la campagne M3 |
| P4 | Les chocs sectoriels synchronisent sans propager | arbres de causalité M3 | établi pour la variante |
| P5 | Annulation–destruction rend la contagion causale | M4, ablations et graphes | établi dans M4 |
| P5a | La naissance par emprunt est nécessaire à la contagion | ablation M4 | faux dans M4 |
| P5b | Des régressions log-log élevées suffisent à distinguer synchronisation et contagion | arbres causaux M4 | faux |
| P6 | M4B est une réduction minimale de M4 | mécanique, code et tests M4B | établi |
| P7 | La campagne principale est comptablement valide | manifestes, journaux, invariants | établi sur l'espace testé |
| P8 | Les avalanches ont une queue tronquée et un scaling de taille | tables et scripts de sensibilité | établi numériquement |
| P9 | \(NW\) porte davantage d'inégalité que \(K\) | analyse NW post-audit | établi numériquement |
| P10 | Le canal de liquidité est silencieux sur la plage principale | événements de défaut | résultat négatif établi |
| P11 | Les contractions de \(E_t\) sont courtes et leur amplitude dépend de \(\sigma\) | colonnes energy | provisoire post-audit |
| P12 | M4B démontre un effet rebond | aucune | faux à ce stade |
| P13 | La société capitaliste est SOC | aucune preuve décisive | hypothèse non actuellement réfutée |
| P14 | Une cible empirique unique existe pour chaque distribution | recherche Zotero | faux ou non établi selon l'objet |
| P15 | L'absence de cible valide M4B | aucune | faux ; verdict suspendu |

## 11. Prochain dépouillement documentaire

Ordre proposé pour enrichir le dossier source, indépendamment de toute mise en
forme finale :

1. journaux M4/M4B, afin de dater précisément la découverte de la contagion et
   de vérifier comment les enseignements H et X1 de M3 y sont transférés ;
2. anciens premiers modèles et note transversale, afin de compléter les règles
   et impasses antérieures à M2 ;
3. sources primaires sur le niveau du chiffre d'affaires des firmes ;
4. corpus sur faillites causales et réseaux fournisseur–client ;
5. corpus sur exergie et distributions de consommation ;
6. construction d'un tableau chronologique des hypothèses, décisions,
   réfutations et mécanismes conservés.

Chaque dépouillement devra produire : faits nouveaux, corrections du mémo,
citations bibliographiques, figures réutilisables, questions à poser à l'auteur
et niveau de preuve.
