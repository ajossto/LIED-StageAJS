# Révision V2 — décisions et transfert différé

Source intégrale, conservée sans réécriture : [carnet rempli figé](reference/COMMENTAIRES_PROTO_ARTICLE_V2.md). Le [PDF commenté](reference/note.pdf) et les [sources avant intervention](reference/latex_avant_v2/note.tex) sont archivés. Les cases vides ne sont pas des validations.

Périmètre : proto-article uniquement. Ni moteurs, ni générateurs Simulation Lab, ni rapport de stage modifiés. Aucune nouvelle simulation. Les calculs d'âge et de déciles lisent les panneaux existants. Après le signalement de l'auteur, les corrections des figures 2, 7 et 13 sont effectivement appliquées : leur report initial était trop large. Seule l'intégration des nouvelles sorties Simulation Lab attend leur disponibilité.

Pour **toutes** les entrées ci-dessous, statut du transfert : **non appliqué au rapport de stage**. Les destinations du rapport sont fonctionnelles (modèle, méthodes, résultats, annexes) ; les sections exactes seront identifiées au transfert, sans supposer une correspondance automatique de numérotation. Les décisions COR-001 à COR-025 de la première passe restent conservées dans leur propre registre.

## V2-001 — Diffusion académique, traduction et mise en page

- Original, remarques générales : « prévoir l'eventualité d'une traduction en anglais, allemand » ; « sans pour autant changer pour le moment l'article ».
- Décision : préparation consignée, traduction et refonte graphique différées. La présente passe corrige le contenu selon les annotations, sans changer la classe, la police ni les marges.
- Suite : stabiliser les termes dans le glossaire, séparer données/étiquettes/légendes, garder des sources éditables ; vérifier ensuite les exigences du support de diffusion. Ne pas traduire automatiquement les notations ni les identifiants des campagnes.
- Rapport : vocabulaire commun et sources graphiques réutilisables ; la mise en page de revue est propre à l'article. Cible : glossaire et figures.

## V2-002 — Fixation de k à deux

- Original, remarques générales : « le paramètre k [...] a toujours été déclaré à 2 » après une phase précoce ; « officieusement supprimé ».
- Vérification : `sensibilite_m4b/results/summary/nw_confirm.csv` et les exports M4B contiennent effectivement un centre à k=3 et des variations de k. La configuration principale M4.4 est à k=2.
- Décision appliquée : distinguer l'exploration historique du choix ultérieur des rencontres par paires, dans le protocole et le pilotage. Aucun ancien paramètre n'est réécrit. La date exacte de fixation n'est pas inventée.
- Rapport : conserver la chronologie et les essais historiques ; cibles : développement du modèle et sensibilité. Complète COR-013.

## V2-003 — Rétrocompatibilité et tests de régression

- Original, remarques générales : « le travail de retro-compatibilité n'est pas assez précisé » ; les M4 seraient passés par des tests « sauf erreur de ma part ».
- Vérifications : `m4_2_credit_soc/tests/test_parity_m4b.py` et `report/spec_m4_2.tex` (§ parité) ; `m4_4_rebond_credit_soc/tests/test_parity_m4_3.py`, `test_v1_equivalence.py` ; archive `results/analysis/parity_deviations_8000.csv` (8000 lignes, écart maximal nul). Le journal Live de non-régression porte aussi sur les routes/CLI : cela ne prouve pas la parité dynamique.
- Décision appliquée : annexe `complements_v2.tex`, distinction entre parité bit à bit, tolérance numérique et maintien des fonctionnalités. Les résultats historiques sont présentés comme tels ; aucun test moteur n'a été relancé, puisqu'il exécuterait des simulations.
- Réserve : présence d'un test ≠ attestation d'exécution réussie pour chaque version. Pas d'affirmation globale de validation de toutes les M4.
- Rapport : développer les cas, horizons et tolérances dans la partie validation numérique. Complète COR-008.

## V2-004 — Désignation M5

- Original : « la toute dernière version, dont la rêgle de marché à été modifié (cette version devrait s'appeler M5, d'ailleurs) ».
- Constat : le README M4.4 décrit une extension d'instrumentation de Live-v2 ; le changement de sens de prêt est déjà présent dans la lignée Live-v2. La version exactement visée ne peut pas être identifiée sans ambiguïté à partir de cette phrase.
- Précision ultérieure de l'auteur, le 17 septembre : « On changera officiellement les noms après. Ce n'est pas très important, mais le passage de la rêgle du taux d'emprunt est un changement conséquent. »
- Interprétation corrigée : le changement substantiel signalé concerne la **règle de fixation du taux d'emprunt**, et ne doit pas être confondu avec le changement de sens du prêt évoqué dans le constat initial ci-dessus. Il modifie le modèle, pas seulement son instrumentation. Cette précision n'identifie pas à elle seule les deux formules ou les versions techniques concernées : aucune correspondance supplémentaire n'est inventée.
- Décision actualisée : renommage officiel expressément différé, non bloquant pour la révision. Aucune archive, classe ou campagne renommée. Dans les comparaisons, identifier la règle de taux effectivement utilisée et distinguer ce changement institutionnel des extensions de mesure ; un test de non-régression dans un mode de compatibilité ne rend pas identiques deux règles de taux différentes.
- Rapport : conserver cette précision dans l'historique des règles de crédit et la discussion des comparaisons. La table de correspondance noms scientifiques / chemins techniques / règles sera établie lors du renommage officiel. **Non appliqué au rapport de stage.**

## V2-005 — Figures natives et versions vectorielles

- Original : « bientôt [...] retravailler les figures natives de simulation_lab » ; « prévoir des versions vectorielles [...] traductabilité ».
- Vérification : `revision_article.py` exporte déjà les figures de l'article en PDF via Matplotlib et en PNG pour prévisualisation ; les schémas pédagogiques sont en TikZ. Les PDF sont les fichiers inclus dans l'article. `pdfimages -list` ne trouve aucune image matricielle incorporée dans les treize PDF de figures utilisés : les tracés actuels sont donc déjà vectoriels.
- Décision actualisée : ne pas lancer les générateurs partagés ; corriger les figures propres à l'article avec `scripts/figures_v2.py`, également appelé lors d'une régénération complète. Les figures 2, 7 et 13 sont exportées en PDF et SVG avec textes éditables. Un PDF vectoriel n'est pas à lui seul un dispositif de traduction.
- Rapport : mêmes données et sources graphiques, dimensions et légendes à adapter. Cible : toutes les figures.

## V2-006 — Longueur et figures supplémentaires

- Original : « la longueur est de 15-20 pages sans les annexes ! » ; « rajouter des figures là où c'est le plus pertinent ».
- Interprétation : cible de longueur du corps, non limite totale incluant les annexes. La version commentée ouvrait ses annexes page 14.
- Décision partielle : ajouts scientifiques et glossaire effectués sans allonger artificiellement ; conformité à la cible à réévaluer après réception des nouvelles figures. Pas d'ajout de graphiques redondants pour remplir des pages.
- Rapport : conserver les développements scientifiques ; la cible 15–20 pages est propre à l'article.

## V2-007 — Glossaire

- Original : « Rajouter un glossaire par ordre d'apparition des termes techniques et des notations ».
- Décision appliquée : `latex/glossaire_article.tex`, annexe de lecture suivant l'introduction des notions dans le corps après le résumé ; symboles introduits ensemble regroupés. Définitions du modèle, statistiques, ambiguïtés T (tension/horizon) et D (dette/durée), distinction âge/durée de vie dans le texte.
- Rapport : reprendre et étendre le glossaire selon son propre ordre d'exposition, non recopier aveuglément l'ordre de l'article.

## V2-008 — Temps caractéristique, décile et oubli de l'initialisation

- Original : « Rajout de l'étude sur le temps caractéristique [...] renouvellement du premier décile » ; « assez éloignée / donc indépendante de la configuration initiale ».
- Décision partielle : réserve méthodologique ajoutée à l'annexe de stationnarité, distinguant rétention dans un décile, survie des membres, autocorrélation et oubli de l'état initial.
- Mesure et figure différées : attendre les sorties finales de Simulation Lab. Vérifier l'observable de classement, le sens du « premier décile », les identifiants suivis, la date d'ancrage, les horizons, les graines et la censure. Ne pas transformer l'âge médian en temps de décorrélation.
- Réserve : un renouvellement rapide ne prouve pas l'absence de mémoire du réseau ni l'indépendance de deux instantanés. Si le temps observé est comparable à l'amorçage ou à la fenêtre, revoir les interprétations et incertitudes.
- Rapport : commun aux deux documents, à développer dans méthodes/établissement du régime. Complète COR-016 et les contrôles de stationnarité de la première passe.

## V2-009 — Attente avant de nouvelles simulations

- Original : « Attendre la fin de la mise à jour des graphiques et de leur génération dans simulation_lab avant de relancer éventuellement [...] certaines simulations ».
- Décision respectée : aucune simulation ou test moteur lançant une trajectoire ; aucune exécution des générateurs Simulation Lab. Lecture des campagnes et recalcul descriptif des âges seulement.
- Suite : après signal de fin, examiner les sorties, identifier les lacunes, puis définir les compléments nécessaires. L'éventualité de relancer n'est pas présentée comme une expérience déjà réalisée.
- Rapport : conserver le même gel des campagnes et leur provenance.

## V2-010 — Introduction

- Original, `V2-ART-1` : « enlever \"la séparation des stocks et des flux\" ».
- Appliqué : expression retirée de l'énumération des enjeux du stage. Les définitions physiques stock/flux restent dans le modèle, où elles sont nécessaires.
- Rapport : simplification éventuelle de l'introduction, sans supprimer les définitions. Cible : introduction.

## V2-011 — Dotation et exposant de naissance

- Original, `V2-ART-2.1` : « même dotation K^° et gamma^° » ; supprimer « le cercle désigne ... à zéro ».
- Appliqué : suppression de l'explication typographique ; ajout de l'exposant de naissance γ°=1/2 au régime homogène de référence. γ° n'est pas qualifié de dotation et n'est pas imposé aux traitements hétérogènes.
- Rapport : commun ; modèle pédagogique et notations.

## V2-012 — Renvoi aux paramètres

- Original, `V2-ART-2.2` : ajouter une note « Ces paramètres sont explicités en [ref paragraphe] ».
- Appliqué : renvois LaTeX vers le pas de temps, le crédit et le glossaire. Pas de numéros de section figés.
- Rapport : renvois équivalents à adapter à sa structure.

## V2-013 — Étude de non-invariance temporelle

- Original, `V2-ART-2.5` : « mettre l'étude faite pour ce [...] fait dans l'article, eventuellement en annexe ».
- Appliqué : renvoi depuis l'adimensionnement vers l'étude existante et nouvelle annexe `complements_v2.tex` : calcul explicite de F∘F ≠ G, exemple numérique contrôlé, résultats des essais Live-v1 déjà exportés.
- Sources : `data_article/temps_graines.csv`, `temps_points.csv`, phase production puis dépréciation du modèle. Pas de nouvel essai.
- Réserve : regroupement fini ≠ étude de convergence vers une limite continue.
- Rapport : transférer démonstration, observations et limite ensemble. Complète COR-013.

## V2-014 — Technologies qui se croisent

- Original, `V2-ART-2.6` : « deux technologie avec K ET gamma différents, dont leurs valeurs se croise ».
- Décision corrigée et appliquée : deux technologies f₁(K)=2K^(1/4) et f₂(K)=K^(1/2), et deux stocks initiaux distincts K₁=20, K₂=4. Les productions se croisent à K=16, valeur 4 ; le second panneau calcule le gain/perte pour cette même paire jusqu'à l'égalisation marginale, q*≈13,31. Les deux exposants ET les deux états K diffèrent donc explicitement.
- Vérifications : égalité au croisement, égalité des dérivées au prêt optimal, surplus non négatif sur le domaine tracé. Unité de stock fixée ; croisement des productions distinct de l'égalisation des rendements marginaux. Légende et tableau des sources actualisés ; courbes et points exportés dans `data_article/technologie_courbes_v2.csv` et `technologie_points.csv`.
- Rapport : même exemple pédagogique, explication plus développée possible. Complète COR-006.

## V2-015 — Titre du protocole

- Original, `V2-ART-3` : « DES démarcheS expérimentaleS en PLUSIEURS ETAPES ».
- Appliqué : titre « Des démarches expérimentales en plusieurs étapes ». Les trois familles effectivement mobilisées restent décrites séparément.
- Rapport : chronologie plurielle à conserver, titre à adapter.

## V2-016 — Figure 6, NW et place des distributions

- Original, `V2-ART-4.4` : supprimer « Les panneaux disponibles ... 2000 » ; préciser « valeur nette (Networth, NW en anglais) » ; « coeur battant de l'article ».
- Appliqué : retrait du commentaire de fabrication de la légende ; dates réelles 2010, 3000, 4000 conservées. Définition explicite « valeur nette (net worth, NW) ». La section demeure dans le corps principal, pas reléguée aux annexes.
- À poursuivre : enrichissement visuel après réception des nouvelles figures. Les limites de comparabilité avec patrimoine/revenu empiriques sont maintenues.
- Rapport : conserver centralité, définitions et réserves ; les limites d'enregistrement restent dans la traçabilité. Complète COR-011 et COR-012.

## V2-017 — Étude de k réservée à l'historique

- Original, `V2-ART-5` : « l'étude sur la volatilité du gini en fonction de k n'est pas ultimement pertinent, mais [...] pour le rapport ».
- Décision corrigée et appliquée : panneau k retiré de la figure 7 ; seul le balayage en σ est conservé, avec son centre historique k=3 explicitement indiqué. La figure initiale à deux panneaux et ses données restent archivées pour le rapport. Aucun résultat ancien n'est rebaptisé comme issu de k=2.
- Vérification : la figure montre un Gini final et sa variabilité entre graines ; elle ne mesure pas une volatilité temporelle du Gini.
- Rapport : conserver le balayage historique de k avec cette définition exacte. Complète COR-013.

## V2-018 — Légende de la figure 8

- Original, placé sous `V2-ART-5.4` : « figure 8 [...] supprimer \"le dernier panneau... rencontre\" ».
- Appliqué au bon objet : figure `art_rho`, pas `art_temps` ; retrait de la phrase, définition Gini NW maintenue dans la légende et le texte.
- Rapport : alléger la légende si besoin, sans confondre population et bassin.

## V2-019 — Sens de la compensation

- Original, `V2-ART-6.2` : « préciser ce que fait la compensation (compenser quoi) de K^°. User Kappa à escient ».
- Appliqué : K_aut=9801 puis 22052,25 ; κ°≈0,00255 puis 0,00113 à K° fixe ; K°=56,25 conserve le rapport sous A×1,5. La compensation augmente l'apport réel des naissances sans transformer les stocks/contrats des présentes. Elle ne compense pas une perte de revenu.
- Rapport : reprendre la distinction apport constant/position réduite constante, avec la réserve sur l'interprétation énergétique. Complète COR-004 et COR-014.

## V2-020 — Amplitude et exploration future

- Original, `V2-ART-6.4` : préciser « A vers A*1.5 » et « plages [...] plus larges de A et gamma [...] à mener ».
- Appliqué : portée vivantes + futures entrantes, pas 2001, K° fixe explicités localement ; exploration distributionnelle plus large annoncée comme nécessaire.
- Réserve : des explorations historiques de γ existent déjà ailleurs dans le projet. Ne pas dire qu'aucune variation de γ n'a jamais été étudiée.
- Rapport : délimiter les résultats acquis et le programme de robustesse. Complète COR-016.

## V2-021 — Paramètres et médiane des âges

- Original, `V2-ART-6.4` : « quelle jeu de paramètre donne 111 pas [...] préciser aussi le médian ».
- Appliqué : configuration complète du contrôle et définition de la moyenne sur 100 instantanés puis 12 graines ; âge moyen 110,9733 et moyenne des médianes instantanées 40,0533. Traité : 94,9362 et 32,0300. IC95 inter-graines ajoutés.
- Sources et méthode : `scripts/ages_v2.py`, `ages_v2_graines.csv`, `ages_v2.json` avec empreintes des 24 panneaux. Aucune génération de figures et aucune simulation.
- Réserve : âge des survivantes ≠ durée de vie ; moyenne des médianes ≠ médiane d'un échantillon concaténé. Ne pas en déduire un temps d'oubli.
- Rapport : commun, avec méthode et réserves. Complète COR-018.

## V2-022 — Figure 13 classée par valeur nette

- Original, `V2-ART-6.4` : « un pannel sur le NW, mais pas sur le capital ».
- Décision corrigée et appliquée : le panneau « Capital » est remplacé par les **parts de valeur nette NW=K+C−D**, calculées depuis les microdonnées. Lecture retenue de « un panneau sur le NW » : remplacer la grandeur du troisième panneau, sans changer implicitement le classement commun par capital. L'inférence initiale d'un changement de classement est donc abandonnée et cette convention est annoncée explicitement à l'auteur et dans la légende.
- Méthode : 100 instantanés 3010–4000, classement K stable, dix groupes `array_split` égaux à une entité près, parts par instantané puis moyenne temporelle par graine ; Student sur 12 graines. Les trois panneaux sont recalculés avec cette convention unique (et non assemblés depuis des exports aux arrondis de déciles possiblement différents). Somme des dix parts égale à 1 pour chaque observable/bras/graine.
- Livrables : `art_deciles.pdf` et `.svg`, `deciles_v2_graines.csv`, `deciles_v2_points.csv`, manifeste des sources complété. L'ancienne figure `rev_deciles` n'est pas détruite, mais n'est plus incluse dans le PDF.
- Rapport : reprendre le panneau NW avec sa définition et conserver l'ancien panneau K si utile ; ne pas confondre grandeur mesurée et critère de classement. Complète COR-018.

## V2-023 — Point vert de la figure 14

- Original, `V2-ART-7` : « règle archaique [...] référence illustratrice ».
- Appliqué : règle marginale historique dite archaïque, point illustratif exclu de la régression des partages imposés ; incertitudes conservées.
- Réserve : ce qualificatif n'en fait pas un bras issu d'une autre campagne ; le point représente la règle marginale effectivement mesurée dans M4.4.
- Rapport : même distinction règle de référence / partage imposé. Complète COR-019.

## V2-024 — Suppression d'un commentaire de révision en annexe C

- Original, `V2-ART-C` : supprimer « l'ancienne section... corrigée ».
- Vérification : cette phrase n'est pas présente dans les sources incluses ni dans la copie de référence V2. Le passage correspondant est donc introuvable sous cette formulation.
- Décision : pas de suppression conjecturale d'un argument scientifique. Retrait du mot éditorial « corrigé » dans « Le dénominateur corrigé inclut... ». Les définitions payé/dû/dette sont maintenues.
- Rapport : supprimer les commentaires de fabrication s'ils y figurent, conserver la correction scientifique. Réserve de localisation ouverte si l'auteur désigne un autre passage. Complète COR-020.

## Prochaine intégration graphique

Les figures 2, 7 et 13 sont corrigées, indépendamment des générateurs de l'auteur. Attendre son signal de fin pour inventorier les nouvelles sorties Simulation Lab ; établir leur correspondance avec les données/configurations ; vérifier les temps de renouvellement et la fenêtre finale ; revoir la longueur du corps. Toute simulation complémentaire devra être justifiée par une lacune identifiée. Conserver ce registre et les notes originales pour le rapport.
