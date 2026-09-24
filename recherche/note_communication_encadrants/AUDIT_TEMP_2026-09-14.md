# Audit provisoire de la note de transmission — 14 septembre 2026

## Objet et portée

Document principal retenu : `latex/note_encadrants.tex`, état annoncé au 25 août 2026, PDF de 71 pages. Ce choix est une inférence : son objet et son contenu correspondent à la demande. `../note_resultats/` constitue une synthèse des résultats actuels ; `../memo_stage/` conserve le récit et les réponses antérieures ; `../note_de_travail/` contient une autre note, plus ancienne. Le choix du document cible est proposé en Q01 du [questionnaire temporaire](QUESTIONS_TEMP_2026-09-14.md).

Audit documentaire et contrôles ciblés du code dans `/home/anatole/jupyter/`, au-delà du seul dossier `recherche/`. Lecture de la note principale, de ses définitions et références, confrontation aux questionnaires/consolidation du 24 août, aux rapports de campagne et aux fonctions pertinentes des moteurs. Les numéros de ligne ci-dessous désignent les sources LaTeX actuelles, non les pages du PDF.

Limites : les campagnes n'ont pas été relancées ; les sept parités annoncées n'ont pas été rejouées ; les articles n'ont pas fait l'objet d'une nouvelle revue bibliographique ; le rendu des 71 pages n'a pas été inspecté visuellement page par page. Il ne s'agit donc ni d'une certification complète des résultats ni d'un audit exhaustif de chaque fichier du dépôt.

## Diagnostic

La note dispose d'une matière scientifique riche et d'une bonne infrastructure de traçabilité. Elle restitue plusieurs résultats négatifs et intègre des corrections importantes apportées par Anatole. Son défaut principal est une portée des affirmations parfois supérieure à celle des preuves citées, aggravée par des mélanges entre régimes, observables et conventions statistiques. La transmission pratique du projet reste moins développée que le récit scientifique.

Avant de compléter le texte, il faut stabiliser le modèle décrit, la définition du résultat central, les niveaux de preuve et les correspondances entre grandeurs. Certaines corrections sont factuelles ; elles ne doivent pas être présentées comme des questions d'opinion.

## Ce qui a été vérifié et peut être conservé

- 47 inclusions de figures, 47 sources présentes, 47 copies identiques aux sources par comparaison SHA-256 complète. Aucune figure manquante parmi celles du catalogue.
- 268 définitions de macros numériques identiques entre `latex/numbers_m4_4.tex` et `/home/anatole/jupyter/m4_4_rebond_credit_soc/report/numbers.tex`.
- Live-v2 : 156 lignes de données dans `traceability.csv`, 153 dans `simulation_lab_index.csv`. La consolidation explique les trois références M4.3 supplémentaires.
- M4.4 : 372 lignes de données dans chacune de ces deux tables.
- Le PDF existant compte effectivement 71 pages. Son journal comporte quelques débordements de lignes et avertissements de signets ; le contrôle effectué n'est pas une recompilation.
- Le bilan de 19/19 tests en 2204 secondes existe dans `m4_4_rebond_credit_soc/results/analysis/suite.log`. Le fichier nommé `suite_final.log` correspond, lui, à un état 18/18 en 2194 secondes : le nom « final » ne suffit pas à identifier le dernier périmètre.
- Tes réponses QT-01, QT-04, QT-19, QT-24, QT-25, QT-28, QT-32 et QT-37–40 apportent déjà les éléments de périmètre et de méthode essentiels. Elles restent les sources de ton intention ; les nouvelles inférences ne les remplacent pas.

## A — Corrections factuelles prioritaires

### A01 — Le point fixe ne correspond pas à l'ordre des phases

**Constat.** `note_encadrants.tex:962` donne `K* = (A/δ)^(1/(1−γ))`. Or le moteur produit puis déprécie : `K' = (K + A K^γ)(1−δ)` en autarcie déterministe. Le point fixe de cette récurrence est donc :

`K_aut = [A(1−δ)/δ]^(1/(1−γ))`.

**Preuve.** `m4_4_rebond_credit_soc/m4_4/tension.py:77`, fonction `autarkic_scale`, implémente exactement cette formule. Le facteur manquant peut seulement être négligé sous une approximation explicitée. En outre, la condition de concavité utilisée dans le code est `0 < γ < 1`, et non le seul `γ < 1` écrit dans la note.

**Correction proposée.** Donner la récurrence, le point de mesure du stock et le domaine des paramètres. Réserver la formule simplifiée à une approximation identifiée. Ne pas présenter ce point fixe sans bruit comme la moyenne stationnaire du modèle stochastique. Validée.

### A02 — La description du marché est celle d'une restriction du moteur

**Constat.** La chronologie décrit un tour par entité et un prêt de la plus riche vers la plus pauvre (`note_encadrants.tex`, section « La chronologie d'un pas »). M4.4 utilise par défaut `loan_direction="free"` ; les rencontres se font par paires et leur nombre dépend de l'intensité de marché.

**Preuve.** `m4_4/model.py:234,543,808,817` : nombre de tours `floor(eta(n, rho, eta_beta, eta_n_ref))`, sens déterminé par l'optimum du noyau. En régime homogène, le sens libre rejoint la règle historique ; ce n'est plus garanti avec des technologies différentes. Les interventions sont appliquées avant les naissances (`model.py:1411`).

**Correction proposée.** Distinguer noyau M4B, généralisation technologique et moteur M4.4. Indiquer les valeurs par défaut et la restriction homogène. Ne pas écrire une règle historique comme définition universelle du moteur actuel. Validée

### A03 — La conclusion conserve un plafond de branchement contredit par M4.4

**Constat.** La conclusion générale (`note_encadrants.tex:2141`) retient un branchement plafonnant à 0,30. La même note publie `b₁ = 0,7863 ± 0,0013` pour le contrôle M4.4 et un balayage de `ρ`.

**Correction proposée.** Rattacher le plateau 0,30 au régime M4B concerné. Réexaminer aussi la phrase de la section avalanches qui le dit stable pour toutes les variations de `σ` et `δ`, puisque l'ablation M4.4 attribue précisément une grande partie de l'écart à ces paramètres. Conserver « SOC non établie », mais ne pas la justifier par un plafond universel fictif. Validée. Le branchement devient à ce point un paramètre endogène observé. 

### A04 — La réconciliation de deux élasticités comporte une erreur arithmétique

**Constat.** La note sous le tableau du rebond affirme que l'écart entre 0,7473 et `0,765 ± 0,008` est « bien inférieur à l'incertitude de la plus petite » campagne. L'écart vaut 0,0177, supérieur à 0,008.

**Correction proposée.** Retirer cette justification. Identifier exactement les bras, fenêtres et définitions de l'incertitude avant toute conclusion de compatibilité. Une différence d'effectif de graines ne suffit pas à expliquer l'écart. Le choix d'une valeur principale peut être éditorial ; la compatibilité statistique ne l'est pas. Validée

### A05 — La légende de Lorenz rapproche deux observables différentes

**Constat.** La légende de `p01_lorenz` met en regard `(0,215 ; 0,595)` pour capital/intérêts et `(0,074 ; 0,435)` pour le centre de campagne. Le second 0,435 est le Gini de **valeur nette**, comme le précise le texte immédiatement précédent ; il ne s'agit pas du Gini des intérêts.

**Correction proposée.** Nommer chaque observable à côté de sa valeur. La différence de `σ` entre spécimen et centre ne suffit pas à lever cette confusion. Plusieurs autres légendes du spécimen ne rappellent pas ses paramètres, contrairement à la promesse de marquage systématique du questionnaire initial. Validée. 

### A06 — Des nombres sont encore saisis à la main

**Constat.** La promesse « aucun nombre de M4.4 recopié à la main » est trop forte : le tableau des quantiles et plusieurs paragraphes de la partie VI comportent des valeurs littérales (`1,748`, `1,755`, `0,295`, `0,533`, etc.). Le collecteur copie les macros et vérifie les inclusions ; il ne valide pas toutes les valeurs du texte.

**Correction proposée.** Relier ces tableaux à leurs fichiers de données ou limiter explicitement la garantie à ce qui est automatisé. Mettre à jour les compteurs du préambule : 42 figures annoncées contre 47 présentes ; neuf questions annoncées contre onze dans `QUESTIONS.md`. Validée 

### A07 — Deux définitions de sur-détermination sont fusionnées

**Constat.** `definitions.tex` définit `b₂−b₁` comme une « part des morts » à plusieurs parents. Pourtant, si `d_v` est le nombre de parents d'une morte non racine et `N` le nombre total de mortes :

`b₂−b₁ = Σ_v(d_v−1)/N`.

C'est un nombre d'arêtes supplémentaires par morte, pas en général une proportion de victimes. Une victime à trois parents contribue deux fois à ce numérateur. Le code calcule séparément `multi_parent_share` (`m4_4/cascades.py`).

**Correction proposée.** Distinguer excès d'arêtes, proportion de victimes à plusieurs parents et plancher de suffisance. Le commentaire introductif de `cascades.py` confond encore multiplicité et suffisance, alors que le lot J les sépare : ne pas hériter de ce commentaire comme d'une preuve. Validée

### A08 — L'appariement n'assure pas les mêmes chocs individuels après divergence

**Constat.** La définition du contraste apparié et le volet rebond promettent les « mêmes tirages aléatoires ». Les bras repartent effectivement du même snapshot (`scripts/campaign.py:263`). Mais le moteur tire un vecteur de chocs de taille `len(alive)` et réalise un nombre de rencontres dépendant de la population (`model.py:808,1438`).

**Inférence technique forte.** Lorsque les effectifs divergent, le nombre et l'affectation des tirages peuvent diverger. Un état initial du générateur partagé ne garantit donc pas des chocs identiques pour chaque entité et chaque pas futur.

**Correction proposée.** Écrire « même état initial, même état du générateur à la bifurcation, comparaisons appariées par graine ». Réserver la promesse de bruit individuellement commun à un protocole qui l'assure explicitement. Ce constat ne rend pas les contrastes par graine inutilisables. Validée

## B — Conclusions à reformuler ou à mieux justifier

### B01 — Rebond, amplification de production et signe de la réponse

La note distingue utilement sa définition interne du rebond énergétique, mais le titre, le résumé et la conclusion redeviennent parfois catégoriques. Les élasticités 0,7473 et environ 2 sont toutes deux positives : ce qui change de signe est l'écart à la proportionnalité, pas nécessairement la réponse elle-même. Proposer « réponse sous- ou super-proportionnelle » et préciser chaque fois l'observable et le contrefactuel.

Le code de `scripts/decomposition.py` emploie un contraste logarithmique fini rapporté à `log(1,5)`. Ce n'est pas automatiquement une dérivée locale. La note doit définir l'estimateur publié, l'amplitude du choc, la fenêtre et le sens de `±`. Elle utilise aussi `p` pour le partage et pour la fraction traitée ; employer deux symboles distincts. Validée. Ne pas hésiter à refaire tourner des calculs pour compléter les données. Valable pour tout le travail que nous allons faire ensemble. 

### B02 — La covariance d'échelle n'est pas une preuve sans restrictions sur le logiciel

`tests/test_scale_covariance.py` documente des seuils absolus `MIN_LOAN`, `ZERO_TOL` non rééchelonnés, ainsi qu'une ambiguïté numérique du nombre de créancières. La loi analytique homogène, sa vérification numérique dans un domaine et la relaxation après intervention sont trois énoncés à séparer. La parité entre versions prouve une non-régression sur les scénarios testés ; elle ne valide ni toutes les configurations ni l'interprétation empirique. Véridique. Nous faisons des interprétations. 

### B03 — Une difficulté de sélection des lois devient une impossibilité universelle

La formule « aucune quantité de données ne les séparera » apparaît à plusieurs reprises. Les sorties décrites établissent une difficulté de discrimination, avec des ajustements proches d'une limite dégénérée, dans le protocole étudié. Elles ne constituent pas à elles seules une démonstration d'impossibilité pour tous les paramètres, volumes et protocoles. Une inclusion à la limite ne signifie pas l'égalité de toutes les distributions à paramètres finis.

Proposition : « Les données et les tests employés ne départagent pas ces familles dans les régimes étudiés ; les exposants restent conditionnels à l'hypothèse de queue. » Une prétention plus forte demanderait un énoncé mathématique précis et une justification dédiée. Tes réponses QT-21 et QT-28 maintiennent d'ailleurs cette enquête ouverte.

La note dit aussi à la fois que M4.4 a repris les comparaisons de familles (lot C, Vuong) et que « les tests de Pareto […] n'ont pas été repris ». Il faut nommer les tests effectivement menés et ceux restés hors périmètre, sans amalgamer sélection de familles, adéquation absolue, autosimilarité et coupure. Acceptée. La présence ou non des queues de pareto n'est pas démontrée mais est inférée par beaucoup de visualisation de graphique : la preuve peut être un manque de temps. 

### B04 — Identité de pondération et causalité démographique

L'identité `E[pΔ]/E[Δ] − E[p] = Cov(p,Δ)/E[Δ]` explique exactement la différence entre deux moyennes. Elle ne démontre pas, seule, que toute la différence de population entre institutions est causée par cette moyenne pondérée. Le texte « le vrai mécanisme, et c'est une identité » risque de confondre ces deux niveaux. Présenter séparément identité, mesures sur les bras, explication proposée et éventuelle intervention discriminante. Validée. 

### B05 — Stationnarité et invariance : ne pas convertir une absence de détection en preuve

Le contrôle par comparaison des premiers et derniers quarts de fenêtre est utile mais partiel. L'absence de différence significative de la moyenne entre graines ne garantit pas la stationnarité de chaque trajectoire. De même, une faible variation de Gini ne démontre pas l'invariance de toute une distribution. Préférer des formulations bornées : grandeur, bras, horizon, amplitude et précision explorés. Validée 

### B06 — Quantiles et « captation du surcroît »

Les rapports de quantiles comparent des distributions de populations dont les identités et les effectifs changent. Ils ne suivent pas nécessairement les mêmes entités. Une hausse moindre du quantile extrême est un résultat distributionnel ; elle ne mesure pas directement la fraction du surplus total captée par un groupe fixe. Les parts par décile complètent l'analyse, à condition de préciser leur classement et leur dénominateur. « La petite rente disparaît » est également plus fort qu'une baisse du premier décile non nul. Validée. 

### B07 — Fragilité, mortalité et propagation ne sont pas interchangeables

La partie VI indique que monter `A` abaisse `b₁`, puis discute « un marché plus productif […] plus fragile ». La mortalité par entité peut augmenter pendant que la part des morts propagées diminue. Il faut associer chaque affirmation à sa métrique : décès, risque individuel, branchement, taille des cascades ou pertes de créances. Validée. 

### B08 — Plusieurs réserves sont reléguées trop loin de l'affirmation

Le dictionnaire final distingue correctement `K`, `NW`, production, intérêts et stock total, mais le lecteur rencontre auparavant des expressions comme « revenu », « énergie », « captation » ou « phénomènes réels retrouvés ». Introduire ces distinctions au premier emploi. « Aucun comparable identifié dans le corpus consulté » est plus précis que conclure à une absence générale de données. L'absence de calibration doit rester visible dans le registre des phénomènes.

Les affirmations sur l'absence de mobilité doivent distinguer mobilité des rangs parmi les survivantes, renouvellement par décès et mobilité intergénérationnelle : seule cette dernière exige par définition une articulation entre générations.

## C — Compléments nécessaires pour une transmission

1. **Un état opératoire daté du dépôt.** Le `README.md` racine et `CODEX.md` décrivent encore M4.2 comme futur et M4B comme seule lignée active, alors que M4.4 et les interfaces Live existent. Ce sont des index historiques devenus trompeurs pour une reprise. Modifier les index historiques.
2. **Une carte des documents.** Préciser lequel fait autorité pour le récit, les résultats numériques, les intentions validées et les instructions de reprise. La note de résultats courte existe déjà : inutile d'en proposer une seconde sans examiner son rôle. Note_resultats et note_communication_encadrants sont deux documents frères mais distincts. note_resultats ne s'interesse qu'aux conclusions de mon travail, c'est un proto-article scientifique. note_communication_encadrants est un proto-rapport de stage qui suit l'intégralité de mon raisonnement, de mes hypothèses, et des mes resultats négatifs. 
3. **Une fiche de reprise.** Environnement, commandes, modèles, campagnes, emplacement des données, sorties indispensables, tests pertinents, limites de reproductibilité et priorités de travail. L'autonomie de compilation du PDF n'est pas l'autonomie de reproduction des résultats. Le collecteur contient aussi un chemin absolu vers ce poste. A gérer. 
4. **Un tableau des configurations de référence.** M4B central, spécimen illustratif, Live-v1, Live-v2 et M4.4 : paramètres, bras, graines, fenêtres, estimateurs, source des nombres. Ne pas forcer la comparaison de régimes différents. Ok.
5. **Les illustrations des contractions de stock total.** La discordance avec les figures de production est reconnue depuis juillet. Le complément doit utiliser les runs existants et fixer l'observable avant de dessiner. Exact. 
6. **La méthode du stage.** Relier la question initiale sur la faillite comptable, les impasses, les décisions humaines et l'outillage. Les ressources de calcul, le stockage et les choix d'instrumentation peuvent figurer dans la transmission technique sans envahir le récit scientifique. Validé. 
7. **Une bibliographie normalisée.** Compléter au minimum les entrées incomplètes signalées par la note ; transformer les références génériques ou groupées en références identifiables. Aucun nouveau constat externe n'est certifié par le présent audit. Ok. 

## Ordre de reprise proposé

1. Valider les choix de sens et de destination dans le questionnaire temporaire.
2. Corriger A01–A08 et harmoniser définitions, unités, estimateurs et configurations.
3. Revoir résumé, titres de résultats et conclusion à la lumière de B01–B08.
4. Compléter la transmission, les illustrations et les références.
5. Recompiler, contrôler le rendu et vérifier les valeurs effectivement citées contre leurs sources.

Aucune modification de la note, des moteurs ou des anciens questionnaires n'a été effectuée pendant cet audit. Les deux nouveaux fichiers temporaires sont des supports de relecture, pas des conclusions validées par Anatole.
