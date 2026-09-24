# Questions de reprise — réponses inférées à valider

Date : 14 septembre 2026. Document temporaire, préparé après l'[audit de la note et du projet](AUDIT_TEMP_2026-09-14.md).

Chaque réponse ci-dessous est une proposition, pas une réponse qui t'est attribuée. Tu peux écrire **« validé »**, compléter la proposition ou la remplacer entièrement dans l'espace prévu. Une absence de réponse reste une absence de validation.

Les questions Q01–Q08 fixent le sens du futur document ; tu peux commencer par elles. Les suivantes précisent la présentation et la transmission. Les erreurs arithmétiques, formules incorrectes et confusions de variables sont consignées dans l'audit : leur correction ne dépend pas d'un vote.

Les sources désignées par `QT-xx` sont tes réponses du 24 août dans `../memo_stage/questionnaire_tracabilite_technique.md`. `Consolidation` désigne `../memo_stage/note_consolidation_questionnaire_2026-08-24.md`. Les chemins des moteurs partent de `/home/anatole/jupyter/`.

## Q01 — Quel document continuons-nous, et pour quelle fonction ?

**Question.** La note de 71 pages est-elle le document principal à perfectionner, et doit-elle surtout rendre compte du stage ou permettre à quelqu'un de reprendre le projet ?

**Réponse inférée — confiance moyenne.** « Nous poursuivons `note_communication_encadrants/latex/note_encadrants.tex` comme document principal. Il doit expliquer la démarche et les résultats du stage, et servir de transmission scientifique. Une annexe pratique permettra la reprise du projet. `note_resultats/` restera la synthèse courte des résultats actuels. »

**Fondement.** Ton expression « note de transmission / rapport de stage » ; fonctions annoncées dans les README des deux notes. La synthèse courte existe déjà.

**Ce que cela change.** Document cible, organisation des annexes et articulation avec le mémo maître.

**Ta réponse :**

> …deux documents pour deux utilisations distinctes. Le plus long comme rapprot de stage complet, avec impasses et resultats négatifs inutiles, l'autres avec état final de la recherche, avec resultats positifs, négatifs significatifs, et questions principales laissées en suspent. 

## Q02 — À qui le document doit-il être autonome ?

**Question.** Quel lecteur doit pouvoir comprendre le raisonnement et reprendre les résultats sans avoir suivi les échanges du stage ?

**Réponse inférée — confiance moyenne.** « Mes encadrants sont le premier public, mais je veux aussi qu'un scientifique connaissant la physique et la modélisation, sans connaître mes moteurs ni toutes les méthodes statistiques employées, puisse suivre le document. Il faut définir les objets et expliquer le rôle des tests au premier emploi. »

**Fondement.** Destinataires de la note ; exigence d'autonomie ; l'ancien Q2 reste ouvert. La liste des encadrants ne suffit pas à déduire leur familiarité avec chaque méthode.

**Ce que cela change.** Degré d'explication, place des détails statistiques, glossaire et longueur du corps.

**Ta réponse :**

> …Tout à fait. Il faut impérativement qu'une première lecture se fasse de manière fluide. On peut faire des rappels en notes de bas de pages. D'une manière générale, les notes de bas de page sont nos meilleures amies pour une pedagogie adaptée à la decouverte du document et du travail. 

## Q03 — Quelle date et quel périmètre de travail revendiques-tu maintenant ?

**Question.** Souhaites-tu conserver l'état scientifique arrêté au 25 août, ou intégrer des travaux ultérieurs à cette date dans cette version ?

**Réponse inférée — confiance moyenne.** « M4.3Live-v2 et M4.4 appartiennent au stage, comme je l'ai déjà confirmé. Pour l'instant, la note rapporte l'état du 25 août ; sa révision éditoriale est datée séparément. Les prolongements personnels restent identifiés comme tels, sauf résultats ultérieurs que je souhaite ajouter. »

**Fondement.** QT-01, QT-24, consolidation §3.1. L'appartenance de Live-v2 et M4.4 au stage est déjà acquise ; l'existence et le statut de travaux postérieurs ne sont pas établis par cet audit.

**Ce que cela change.** Date de couverture, chronologie, emploi du futur et séparation résultats/perspectives.

**Ta réponse :**

> …Tout resultat doit rentrer dans le rapport de stage ainsi que le proto-article. Il est même possible, que lors de la redaction actuelle de ces documents, nous soyons menés à relancer des simulations pour valider, étayer, compléter, ou même créer ex-nihilo des chiffres, tables, graphiques... 

## Q04 — Quel résultat doit porter la conclusion ?

**Question.** Est-ce bien la modification collective de la réponse à une amélioration technologique qui doit conclure le stage, le résultat sur le partage du surplus venant ensuite ?

**Réponse inférée — confiance forte.** « Oui. Le résultat central est que la réponse agrégée à un changement technologique n'est pas mécaniquement proportionnelle à ce changement, et que nous avons caractérisé plusieurs conditions et canaux de cette réponse. Le résultat sur le partage du surplus est une contribution supplémentaire importante, qui prolonge naturellement l'enquête. »

**Fondement.** QT-24 désigne explicitement le résultat qui conclut le stage ; QT-27 situe le partage de la plus-value dans son prolongement. La note actuelle désigne plusieurs résultats différents comme “le plus important”.

**Ce que cela change.** Résumé, ordre des résultats et dernier paragraphe du rapport.

**Ta réponse :**

> …Validé. 

## Q05 — Quelle formulation du « rebond » correspond à ta revendication ?

**Question.** Souhaites-tu présenter les résultats comme un mécanisme candidat de rebond, défini par une amplification interne de production, avec la correspondance au rebond énergétique laissée ouverte ?

**Réponse inférée — confiance moyenne à forte.** « Oui. Je ne revendique pas une mesure calibrée du rebond énergétique réel. Je montre une réponse endogène sous- ou super-proportionnelle de la production, selon le protocole et la convention de naissance. Le lien avec le rebond motive le travail et reste une question d'interprétation à expliciter. »

**Fondement.** QT-24 ; définition interne `E > 1` ; absence de consommation finale et de service utile séparés dans le moteur. Audit B01.

**Ce que cela change.** Titre, résumé et remplacement de l'expression ambiguë « le signe du rebond bascule » par la grandeur dont le signe change effectivement.

**Ta réponse :**

> …Validée. 

## Q06 — Comment veux-tu formuler le statut physique du joule et de la production ?

**Question.** Le postulat monnaie–exergie est-il une hypothèse d'interprétation du modèle, ou souhaites-tu soutenir une correspondance physique plus précise ?

**Réponse inférée — confiance moyenne.** « Le modèle compte une ressource abstraite en joules. `K` représente une taille ou capacité productive, la production représente un accroissement physique par pas, et les intérêts sont des transferts internes pouvant représenter des revenus monétaires. Le postulat d'accès à l'exergie motive cette lecture sans démontrer l'identité de ces quantités avec les grandeurs observées dans une économie. »

**Fondement.** Mémo §1.2, dictionnaire final de la note, consolidation des choix d'ontologie. Audit B08.

**Ce que cela change.** Définitions introduites dans le corps, distinction stock/flux/puissance et vocabulaire des comparaisons empiriques.

**Ta réponse :**

> … Le parallèlisme entre stock, flux, J, W, physique, économie est au CENTRE de ma recherche. 

## Q07 — Que désignais-tu par « tension » dans l'explication finale ?

**Question.** Dans QT-24, parles-tu du rapport précis `T = K_aut/K_eq`, ou d'une fragilité plus générale de l'organisation du crédit ?

**Réponse inférée — confiance moyenne.** « Je fais référence à la tension d'échelle `K_aut/K_eq` comme outil pour comprendre le déplacement relatif des échelles, surtout à `δ` fixé. Je ne veux pas la présenter comme un paramètre d'état universel ni comme un synonyme exact de toute la chaîne Gini → rotation → mortalité → population. »

**Fondement.** QT-24 ; consolidation §5 ; ancien Q1. Les archives laissent précisément cette ambiguïté ouverte.

**Ce que cela change.** Formulation du mécanisme revendiqué, équations explicatives et articulation avec les limites du maillon rotation–mortalité.

**Ta réponse :**

> … Validée. 

## Q08 — Quel statut donner aux deux conventions de dotation des entrantes ?

**Question.** Faut-il les présenter comme deux scénarios scientifiques ouverts, ou as-tu une préférence d'interprétation pour l'un d'eux ?

**Réponse inférée — confiance forte.** « Ce sont deux scénarios qui isolent l'effet d'échelle. Je n'ai pas encore choisi lequel représente le mieux un système réel. La compensation de `K0` sert d'abord d'expérience de contrôle ; elle ne doit pas être présentée comme la correction évidente du modèle. »

**Fondement.** QT-24 : choix, interprétation et pertinence de `K0` explicitement ouverts ; tests de covariance et bras compensés.

**Ce que cela change.** Lecture du rebond de long terme, statut de la démographie et présentation des limites.

**Ta réponse :**

> … Validée. C'est très important ces effets d'échelles. On a un nombre de paramètres initiaux, et un nombre d'équations contraintes sur ces paramètres, qui determinent le système. On a donc moins de "paramètres réels", et c'est absolument crucial d'avoir un minimum de paramètres pour un toy-model. 

## Q09 — Que reste-t-il de l'hypothèse SOC dans ton bilan ?

**Question.** La criticité auto-organisée est-elle encore une hypothèse structurante à tester, ou surtout le moteur historique d'une recherche désormais centrée sur coopération et réponse technologique ?

**Réponse inférée — confiance moyenne.** « Elle reste une hypothèse de départ importante et une piste ouverte. Le résultat acquis est la propagation de faillites et sa caractérisation, pas la démonstration d'une SOC. Le rapport doit montrer comment cette recherche a conduit au noyau actuel, sans faire dépendre la valeur de tous les résultats d'un verdict positif de criticité. »

**Fondement.** QT-02, QT-13 et QT-15 ; distinction racines/descendance ; résultats de M4.4 sur `b₁` et `b₂`. Audit A03.

**Ce que cela change.** Récit de la commande initiale, vocabulaire « critique/précritique » et conclusion sur les cascades.

**Ta réponse :**

> … Vrai. Néanmoins, la définition de la criticité s'étend à un seul pas : notre système a des liens de causalité sur plusieurs pas. 

## Q10 — Quelle place donner à la recherche de Pareto et du corps exponentiel ?

**Question.** Veux-tu que ce soit présenté comme un objectif initial non atteint ou non tranché, et toujours ouvert faute d'une étude suffisante ?

**Réponse inférée — confiance forte.** « Oui. Le corps exponentiel recherché n'a pas été obtenu dans les analyses présentées. Pareto n'est pas établi ; certains tests ne départagent pas les alternatives. Je n'ai pas décidé de clore théoriquement ces questions. La note doit distinguer les tests réellement faits des études non réalisées, et expliquer pourquoi les statistiques de queue ont néanmoins servi à caractériser le modèle. »

**Fondement.** QT-21, QT-22, QT-28 ; consolidation §3.2–3.3 ; lot C de M4.4. Audit B03.

**Ce que cela change.** Retrait de l'impossibilité universelle non démontrée ; statut de `Dagum c`, des exposants et des perspectives statistiques.

**Ta réponse :**

> … Pareto n'est pas établi faute de temps, et effectivement il manque aussi du travail. Mais beaucoup de courbes laissent entrevoir l'arrivée d'une pareto. Néanmoins sur la forme exacte des répartitions, je me suis rendu compte que yakovenko ne faisait pas l'unanimité : j'ai donc abandonné l'idée d'avoir le corps exponentiel. Cf articles sur les distributions des exposants, sur les formes des revenus dans le monde, etc... Aussi, gros soucis du nombre de paramètres pour le fit. une classe à 3 paramètres à peu de chance de fit mieux qu'une à 4 paramètres. 

## Q11 — Jusqu'où porter l'interprétation du partage du surplus ?

**Question.** Veux-tu conserver les termes « altruisme » et « asservissement » comme noms techniques des extrêmes du partage, ou privilégier une description de la part revenant à chaque partie ?

**Réponse inférée — confiance moyenne.** « Le partage du surplus est une question théorique importante. Les termes historiques peuvent être conservés après définition, mais le résultat doit d'abord être exprimé quantitativement : part de la prêteuse, pondération par contrat ou par surplus, et comportement démographique mesuré. La covariance explique l'écart des moyennes ; sa portée causale sur toute la dynamique doit être présentée avec son niveau de preuve. »

**Fondement.** QT-27 ; lots T et I ; audit B04. Ta réponse antérieure confirme l'intérêt de la question, pas nécessairement chaque expression employée dans la note.

**Ce que cela change.** Titres et légendes, portée de la généralisation économique, distinction identité/mécanisme.

**Ta réponse :**

> … Oui, aussi il manque une question intéréssante, que se passe t'il en cas de sur-altruisme ? Ie la préteuse fait une opération négative à temps 0, mais avec la dissipation devient positive ensuite. 

## Q12 — Quel sens concret donner à l'entité dans ce rapport ?

**Question.** Veux-tu garder l'entité volontairement générique, ou choisir une application principale pour organiser les comparaisons au réel ?

**Réponse inférée — confiance moyenne.** « Je souhaite conserver une entité générique dans l'exposé du modèle. Les analogies avec personnes, entreprises ou autres organisations doivent être annoncées comme des lectures distinctes, avec leurs limites. Il ne faut pas que le même paragraphe passe implicitement de l'une à l'autre. »

**Fondement.** Absence de types d'agents distincts ; dictionnaire de correspondance et mémo sur l'analogie de la machine.

**Ce que cela change.** Usage de « revenu », « patrimoine », « rentier », « mobilité » et sélection des cibles empiriques.

**Ta réponse :**

> … Oui. C'est une étude très fondamentale. Néanmoins, si on considère qu'un système fait intervenir des mécanismes similaire à nos simulations, l'étude de notre modèle fondamental peut être intéréssante. 

## Q13 — Quelle comparaison empirique aurait le plus de valeur pour toi ?

**Question.** Parmi les comparaisons encore ouvertes, laquelle veux-tu mettre au premier plan dans les suites du rapport ?

**Réponse inférée — confiance faible à moyenne.** « Je privilégierais une observable de distribution liée au bilan ou aux intérêts, avec une unité statistique et une fenêtre définies. Les cascades causales restent centrales, mais leur confrontation demande des données permettant de reconstruire les liens. Je préfère identifier un test réellement discriminant avant de multiplier les rapprochements qualitatifs. »

**Fondement.** Importance des distributions dans QT-21 et des cascades dans QT-15 ; inventaire des cibles empiriques. Le corpus ne fixe pas un ordre de priorité unique.

**Ce que cela change.** Hiérarchie des perspectives et critère concret de mise à l'épreuve du modèle. Aucune nouvelle campagne ni recherche externe n'est engagée par cette proposition seule.

**Ta réponse :**

> …Validée

## Q14 — Comment présenter les figures et les chiffres de référence ?

**Question.** Veux-tu conserver le spécimen M4B existant comme illustration, en séparant clairement ses chiffres de ceux des campagnes et de M4.4 ?

**Réponse inférée — confiance moyenne.** « Oui, s'il rend le mécanisme lisible. Chaque figure doit dire quel moteur, quelle configuration et quelle observable elle montre. Les valeurs principales du bilan actuel viennent de M4.4 ; les valeurs historiques restent dans leur contexte. Les deux figures de contractions sur le stock total doivent compléter les séries de production déjà présentes. »

**Fondement.** Anciennes Q8, Q10, Q11 ; note de résultats courte ; audit A04–A06 et C4–C5. Le spécimen existant a `σ = 0,5` et ne représente pas toutes les configurations.

**Ce que cela change.** Tableau des configurations, légendes, sélection d'une valeur principale et complément des figures sur données existantes.

**Ta réponse :**

> … Tout à fait. Chaque tableau, régression, valeur moyenne doit être illustrée par un ou plusieurs graphiques adaptés d'un ou de plusieurs cas particuliers, et la source de points utilisés doit être trouvable dans un tableau en annexe : "figure n, modèle XX, paramètres de simulation x,y,z... ref de la simulation. "

## Q15 — Quel équilibre entre exhaustivité et parcours de lecture ?

**Question.** L'exhaustivité doit-elle signifier que toute la matière reste disponible, tout en permettant de lire d'abord une argumentation resserrée ?

**Réponse inférée — confiance moyenne.** « Oui. Je veux préserver les résultats, les limites et les étapes importantes. Mais je peux avoir un parcours principal lisible et des annexes détaillées. Une figure doit rester au point du raisonnement quand elle est nécessaire pour le comprendre ; les diagnostics secondaires peuvent être regroupés. »

**Fondement.** Structure modulaire de la note ; ancien Q6 ; synthèse courte déjà disponible. Aucune nouvelle limite de pages n'a été établie.

**Ce que cela change.** Organisation des 47 figures, tableaux statistiques et répétitions entre parties IV, VI et conclusion.

**Ta réponse :**

> …Validée. Il n'y a pas de limite de taille sur la note_aux_encadrants, mais un chapitrage intélligent, joint de paragraphes introductifs et d'une introduction pertinente doit permettre au lecteur de savoir quels chapitres sauter selon sa convenance. (Par exemple, un chapitre qui traite d'un resultat négatif)

## Q16 — Quelle part du raisonnement personnel manque encore au récit ?

**Question.** Veux-tu expliciter davantage les décisions que tu as prises et leurs raisons, plutôt que laisser la succession des moteurs porter seule le récit ?

**Réponse inférée — confiance forte sur l'orientation, moyenne sur le déclic personnel.** « Oui. Il faut faire apparaître l'hypothèse initiale sur la faillite comptable, le retrait des entités immortelles, la distinction synchronisation/contagion, la simplification M4B et le retour au rebond. Pour l'artefact de cohortes du WIP du 27 avril, je retiens le faisceau documenté ; le rapport ne doit pas inventer un déclic personnel ou une chronologie de ma conviction. »

**Fondement.** QT-02, QT-04, QT-08, QT-15 ; consolidation §2 et §4. La conclusion archivistique sur les cohortes est documentée ; la manière précise dont tu l'as adoptée reste partiellement ouverte.

**Ce que cela change.** Passages à la première personne, récit des bifurcations et attribution des découvertes.

**Ta réponse :**

> … Validée. D'ailleurs, il y a encore un travail historiographique à faire là dessus, sur lequel je te soliciterai. 

## Q17 — Comment rendre visible ta contribution technique et le recours aux agents ?

**Question.** Le rapport doit-il développer la conception des expériences, la supervision par Simulation Lab et le contrôle des productions d'agents comme une contribution méthodologique du stage ?

**Réponse inférée — confiance forte.** « Oui. Ma contribution comprend les questions, les choix de modèle, l'organisation des expériences et la critique des résultats. Les agents ont augmenté la capacité d'implémentation et d'analyse. Je veux expliquer comment je vérifie leur travail et comment la visualisation systématique m'aide à découvrir et reformuler des problèmes. »

**Fondement.** QT-09, QT-19, QT-23 et QT-37–40 : ces choix sont déjà explicités. La question porte sur leur place dans cette note, pas sur la nécessité de les revalider.

**Ce que cela change.** Méthode du stage, exemples concrets de contrôle, présentation de Simulation Lab et de la contribution personnelle.

**Ta réponse :**

> …Validée, + mise en place des gardes fous, code que j'aurais été capable de coder en temps asymptotique, etc. 

## Q18 — Que doit pouvoir faire la personne qui reprend le projet ?

**Question.** Quel premier travail la note doit-elle rendre possible sans ton intervention ?

**Réponse inférée — confiance moyenne.** « Retrouver un résultat et sa configuration, ouvrir les données correspondantes, reconstruire une figure et comprendre quel test protège le comportement du moteur. Ensuite seulement, modifier un mécanisme ou lancer un prolongement. Une fiche de reprise doit indiquer les données indispensables, l'environnement et les limites de portabilité. »

**Fondement.** Objet de transmission ; fichiers de traçabilité ; snapshots ; documentation de Simulation Lab. Audit C1–C3.

**Ce que cela change.** Annexe de prise en main, mise à jour des index périmés et vérification de commandes concrètes. Le prochain utilisateur et sa machine ne sont pas connus.

**Ta réponse :**

> … Validée, et aussi savoir quelles questions sont toujours en suspent, quelles expériences j'aurais aimé mener si j'avais plus de temps, sur quelles interactions je pense intéréssant de s'attarder. Exemple : Le trio (K0,A,gamma) peut être unique à la naissance, parfaitement aléatoire sur une plage, ou dépendre de l'état de la simulation. Quels comportements émergent de tels choix, quels paramètres endogènes sont significatifs pour comprendre l'évolution micro et macro du système, etc.

## Q19 — Quel prolongement scientifique faut-il annoncer en premier ?

**Question.** La campagne à technologies hétérogènes reste-t-elle ta prochaine question personnelle, devant les autres pistes identifiées ?

**Réponse inférée — confiance moyenne à forte.** « Oui, c'est une piste qui m'intéresse : faire varier `(A_i, γ_i)` en contrôlant explicitement les échelles pertinentes, puis observer la réponse collective. Elle doit apparaître comme une question ouverte, sans protocole prétendument arrêté. Le temps continu, la robustesse des queues et les règles de crédit restent d'autres pistes. »

**Fondement.** QT-24 et QT-30 ; consolidation §9 ; ancien Q4. Le choix de garder `K_aut` ou `K_aut/K0` constant n'était pas tranché.

**Ce que cela change.** Ordre des perspectives, statut stage/prolongement personnel et distinction intention/protocole validé.

**Ta réponse :**

> …K0,A,gamma ! 

## Q20 — Comment éviter de nouvelles divergences entre les documents ?

**Question.** Veux-tu une répartition explicite des rôles entre la note longue, la synthèse courte, le mémo et les rapports de campagne ?

**Réponse inférée — confiance moyenne.** « Oui. La note longue porte le récit destiné à être lu ; la note courte porte les résultats actuels ; les campagnes et leurs données font autorité pour les chiffres ; le mémo et les questionnaires conservent les intentions et décisions. Les corrections validées doivent être reportées dans les passages concernés, avec un journal bref, pour éviter qu'une ancienne erreur réapparaisse. »

**Fondement.** Ancien Q9 ; consolidation non intégrée au mémo ; index racine périmés et écarts relevés dans l'audit.

**Ce que cela change.** Procédure de consolidation après tes réponses et carte des sources faisant autorité. Les documents existants restent conservés.

**Ta réponse :**

> … Les deux notes doivent être totalement indépendants et autonomes. Les questionnaires doivent être vus comme des documents de travail pour leur élaborations et seront à termes supprimés. 

## Remarques libres

Un point essentiel manque-t-il dans l'audit ou dans ces propositions ? Tu peux aussi indiquer ici les passages de la note qui te gênent le plus, ou une contrainte de rendu connue.

**Ta réponse :**

> … Il est absolument essentiel de choisir et intégrer des graphiques disponibles dans simulation_lab pour illustrer les mots. L'article, comme le rapport de stage, doivent être compréhensibles presque à l'unique vue des graphiques. Si nécéssaire, faire de nouveaux graphiques. Il manque par exemple des regressions sur la taille des avalanches ou on voit très bien la loi de puissance. Sur les graphiques à générer, il est impératif que les données représentées soient aussi accompagnées de leurs incertitudes. On ne doit pas relier des points si la droite produite ne représente rien. Eventuellement mettre en transparence une droite de tendance. Je ne peux pas le dire suffisament fort, le travail de communication visuelle est primordial et crucial.  
