# Traitement des commentaires et report différé

Révision commencée le 15 septembre, finalisée le 17 septembre 2026. Périmètre : **proto-article uniquement**. Le carnet original reste intact ; la version commentée est archivée dans `reference/`. Toutes les décisions ci-dessous sont datées du 17 septembre 2026. **Tous les reports vers le rapport restent non appliqués.** Une rubrique vide du carnet n'est pas considérée comme une approbation.

## Lecture rapide

Le [PDF courant](../latex/note.pdf) suit désormais : question physique → modèle → démarche expérimentale → émergence → pilotage → réponse technologique → partage → limites → conclusion. Les annexes donnent les contrôles et estimateurs.

Trois décisions appellent particulièrement l'attention de l'auteur :

1. L'ajustement de puissance tronquée est présent, mais les écarts visibles empêchent de conclure que cette famille décrit adéquatement les avalanches. Un R² élevé ne suffit pas.
2. La charge a été recalculée avec production + intérêts reçus au dénominateur. L'ancienne « réfutation de la convexité » est retirée : ce diagnostic ne permet pas de la soutenir.
3. Les instantanés supplémentaires utilisent les dates disponibles (2010, 3000, 4000). Les dates demandées 1000, 2000, 8000 et l'éventuelle recherche d'une réponse négative restent ouvertes.

Les anciennes figures citées ci-dessous renvoient à l'impression commentée, pas à la nouvelle numérotation. Les cibles du rapport sont indiquées par thème, pas par pagination, pour ne pas présumer de sa future restructuration.

## Décisions

### COR-001 — Question du stage et progression

- Origine : commentaires globaux et introduction.
- Appliqué : titre, résumé, introduction et conclusion recentrés sur l'effet rebond physique et l'hypothèse d'organisation endogène. Les objectifs distinguent réponse non proportionnelle et distributions plausibles. Le début apprécié de l'introduction est conservé dans son idée.
- Vérification : confrontation de M4B, du recalage Live-v1 et de M4.4, sans fusionner leurs configurations ni leurs échantillons.
- Cible article : `corps_article.tex`, sections 1, 3–6, 8–9.
- Rapport : à reporter dans introduction et bilan, avec une narration adaptée au stage.

### COR-002 — Informations liminaires et résumé

- Origine : titre et résumé, mentions « campagnes / vérifications / rédaction ».
- Appliqué : suppression de la date affichée et des mentions de suivi ; résumé réécrit sans catalogue interne.
- Cible : `note.tex`, début de `corps_article.tex`.
- Rapport : article seulement pour le titre et la mise en page ; clarification du résumé à adapter, pas à copier.

### COR-003 — Exemple introductif à quatre entités

- Origine : lecture linéaire, exemple de `presentation_2_le_retour`.
- Appliqué : schéma fictif de stocks, prêt réel de 6, créances, dettes et valeur nette ; service défini avant son usage analytique.
- Vérification : présentation consultée ; identités avant/après testées. Valeurs nettes 16 et 4 inchangées alors que le prêt conduit aux stocks 10 et 10.
- Cible : `exemple_article.tex`, section 2.
- Rapport : à reporter dans l'introduction du modèle en adaptant la longueur.

### COR-004 — Dotation et échelles

- Origine : K₀ à remplacer par K° ; expliquer K_eq et κ°.
- Appliqué : `K^\circ`, `\kappa^\circ` dans le texte compilé ; distinction entre équilibre isolé, repère d'échelle et dotation. Les identifiants informatiques historiques des bras sont conservés.
- Vérification : points fixes et covariance d'échelle testés ; distinction ordre des opérations / équilibre continu conservée.
- Cible : `physique_echelles.tex` et article entier.
- Rapport : à reporter dans les notations, sans renommer les colonnes ou sources historiques.

### COR-005 — États individuels et paramètres globaux

- Origine : modèle ; sigma global, choc individuel ; delta et granularité.
- Appliqué : distinction explicite entre états individuels et paramètres communs ; dépréciation comme érosion par pas ; sigma n'est pas un choc commun.
- Vérification : règles du moteur et recalages temporels existants.
- Cible : `modele_article.tex`, section 5 du corps.
- Rapport : à reporter dans les définitions et la discussion du temps physique.

### COR-006 — Technologie et gain concave

- Origine : deux technologies, gain du prêt, analogie A / collaboration.
- Appliqué : figure analytique comparant √K et 1,5√K, puis gain et perte associés au prêt. A fixe le niveau de production ; gamma règle la concavité et les possibilités de gain coopératif.
- Réserve : ne pas identifier littéralement A à une puissance physique ni gamma à une préférence comportementale pour la coopération.
- Cible : `art_technologie`, section 2 ; `technologie_points.csv`.
- Rapport : à reporter dans crédit et fonctions de production.

### COR-007 — Cascade orientée et branchement

- Origine : arbre orienté simple.
- Appliqué : cinq entités, quatre faillites en trois générations et une survivante ; sens débiteur mort → créancier perdant. Avalanche définie sur les morts du même pas ; b₁ et b₂ distingués.
- Vérification : annulation des contrats et bilans recalculés par test ; les couples causals de b₂ relient les générations successives.
- Cible : `cascade_article.tex`, fin de `modele_article.tex`.
- Rapport : à reporter dans contagion et causalité ; une arête n'est pas une cause individuellement suffisante.

### COR-008 — Protocole motivé et précision numérique

- Origine : protocole à reprendre, précision excessive, changements technologiques mal introduits.
- Appliqué : trois étapes expérimentales et rôle de chacune ; portée globale / nouvelles entrantes, dotation fixe / compensée ; effectifs arrondis dans la prose.
- Vérification : fenêtres, graines et configurations dans `sources_article.tex` ; les campagnes ne sont pas des répétitions interchangeables.
- Rapport : à reporter dans méthodes et chronologie expérimentale.

### COR-009 — Histogrammes et puissance tronquée

- Origine : anciennes figures 1–2, log-log, IC, pente, R² ; suggestion de critère bootstrap.
- Appliqué : histogrammes à classes logarithmiques, masse divisée par largeur, ajustement discret p(s) ∝ s^(−α) exp(−s/Sc), repère de pente et R² descriptif. Les deux premiers panneaux montrent les distributions moyennes par bras ; le troisième montre les exposants de chacune des douze graines. Anciennes figures fusionnées.
- Méthode : vraisemblance par graine sur s ≥ 1, douze graines par bras ; normalisation sur 1…20000 et contrôle de masse terminale ; bootstrap de runs entiers pour les courbes. Le R² porte sur les logarithmes des classes non vides et n'est pas le critère ajusté.
- Non retenu : minimiser variance bootstrap × R² pour choisir le support. Ce critère pourrait favoriser un faible R² et sélectionner le support sans contrôle d'adéquation. Le support est annoncé et les limites exposées.
- Résultat : contrôle α ≈ 1,6235, Sc ≈ 206,3, R² moyen ≈ 0,938 ; intervention globale α ≈ 1,6674, Sc ≈ 185,3, R² ≈ 0,928. Des écarts systématiques subsistent : **ni famille validée, ni criticité démontrée**.
- Cible : `art_avalanches`, annexe B, exports `avalanches_*`.
- Rapport : à reporter en remplacement des anciennes lectures de pente ; ne pas mélanger masse et survie.

### COR-010 — Contractions et Wright

- Origine : commentaire global et ancienne figure 19 demandant explicitement une exponentielle.
- Appliqué : exponentielle discrète normalisée, coefficients et R², comparaison prudente avec Wright. La demande spécifique « exponential, not power law » guide ce passage.
- Résultat : beta ≈ 0,731 pour le stock, 0,696 pour la production ; R² descriptifs ≈ 0,981 et 0,983 sur les survies aux durées 1…11.
- Réserves : cinq graines M4B, épisodes potentiellement dépendants et tronqués aux frontières ; pas du modèle non assimilable à une année. Aucune validation empirique d'universalité.
- Sources : texte auteur de Wright lié dans la bibliographie ; `data_revision/rev_cycles_episodes.csv` et exports `cycles_*`.
- Rapport : à reporter dans contractions et comparaison empirique.

### COR-011 — Lorenz, Gini et données réelles

- Origine : comparaison de Gini d'observables différentes, références demandées.
- Appliqué : distinction NW / intérêts ; repères SCF 2019–Federal Reserve pour patrimoine net (0,852) et CBO 2019 pour revenu avant transferts sous condition de ressources et impôts fédéraux (0,516).
- Réserve : unités statistiques, revenu et population ne coïncident pas avec le modèle. Les intérêts reçus ne sont pas le revenu total ; ces chiffres ne constituent pas une calibration.
- Cible : section 4, bibliographie, `art_lorenz`.
- Rapport : à reporter avec les définitions complètes, pas seulement les chiffres.

### COR-012 — Dates des instantanés

- Origine : ancienne figure 4, dates 1000, 2000, 8000 « si possible ».
- Partiellement appliqué : Lorenz recalculées à 2010, 3000, 4000 pour douze graines de contrôle.
- Limite : panneaux disponibles entre 2010 et 4000. Le checkpoint 2000 contient un état dynamique, pas un panneau comparable de flux de fin de pas. Aucune observation inventée.
- Suite possible : rejouer/exporter les dates manquantes avec conventions identiques et étendre l'horizon ; non effectué ici.
- Rapport : reporter la figure disponible et cette limite ; demande initiale encore partiellement ouverte.

### COR-013 — Pilotage et granularité temporelle

- Origine : sensibilité, émergence et transformations des paramètres.
- Appliqué : section dédiée à sigma, k, rho et aux essais existants de changement de pas. Flux ramenés au même temps ancien et fenêtres comparables.
- Vérification : confirmations M4B (cinq graines) et sorties Live-v1 `time_rescaling.py` (trois graines). Rééchelonner quelques paramètres ne prouve pas l'invariance du processus entier.
- Cible : `art_sensibilite`, `art_rho`, `art_temps`, exports associés.
- Rapport : à reporter en distinguant les moteurs et les protocoles.

### COR-014 — Élasticité et portée de l'intervention

- Origine : détail du calcul, ln(1,5), non-proportionnalité en gras ; portée partielle secondaire.
- Appliqué : définition du contraste fini, appariement par graine, origine du dénominateur et interprétation. Portée partielle en annexe ; réponse globale mise en avant. Renvois de rédaction aux « macros historiques » supprimés.
- Vérification : recalcul des niveaux terminaux par graine. Epsilon global ≈ 0,7473 ± 0,0106 ; compensé ≈ 2,0029 ± 0,0148 (IC95 inter-graines).
- Réserve : compenser la dotation des futures entrantes ne rééchelonne pas les stocks existants ; proximité de 2, pas identité exacte du protocole.
- Cible : section 6, `art_reponse`, annexes A et D.
- Rapport : à reporter dans effets technologiques et conventions d'échelle.

### COR-015 — Recherche éventuelle d'une réponse négative

- Origine : « éventuellement rechercher une combinaison où la réponse est négative ».
- Statut : **non exécuté**, piste conservée dans les prolongements. Les expériences exploitées ne montrent pas une telle réponse.
- Motif : révision fondée sur les campagnes existantes ; une recherche sélective exige un protocole exploratoire puis des graines de confirmation pour ne pas ériger une fluctuation sélectionnée en résultat.
- Rapport : à examiner en perspectives, pas parmi les résultats acquis.

### COR-016 — Chaîne interprétative et stationnarité

- Origine : représenter la chaîne, justifier la stationnarité, amener le branchement via kappa.
- Appliqué : schéma séparant identités, observations et mécanismes proposés ; repère κ° réintroduit. Tableau des rapports entre premiers et derniers 250 pas de la fenêtre terminale, six bras et trois observables.
- Vérification : 3000 < t ≤ 4000, douze graines ; IC de Student sur les rapports. Aucun contraste au-delà du seuil usuel, sans preuve de stationnarité complète. Population à la production distinguée de celle en fin de pas.
- Cible : section 6, annexe A, `diagnostic_chaine.json`, `stationnarite_*`.
- Rapport : à reporter avec le statut des flèches et les conventions de comptage.

### COR-017 — Quantiles et axe horizontal

- Origine : ancienne section 6 et figure 9 ; graphique préférable, abscisse trompeuse.
- Appliqué : figure de rapports dans le corps, tableau en annexe ; axe logit(q) annoncé, graduations en centiles. Les points ne suivent pas une cohorte fixe.
- Vérification : rapports par graine existants, sans interpolation d'entités.
- Cible : `art_quantiles`, `table_quantiles.tex`.
- Rapport : à reporter avec échelle et conventions de quantile.

### COR-018 — Jeunes entités et déciles

- Origine : figures 9–10 ; jeunes entités dans les petits centiles, légende à expliciter.
- Appliqué : contrôle d'âge des 10 % les plus bas par capital, NW et intérêts à chaque instantané ; lecture des parts de flux/stock développée, naissances rappelées.
- Résultat contrôle : environ 99,9 % du bas des intérêts a dix pas ou moins, contre 24 % de l'ensemble ; environ 49 % pour le bas du capital. Intuition étayée pour les intérêts, non généralisable à tous les classements.
- Réserve : moyennes par instantané puis graine, ex æquo départagés par ordre stable ; pas de suivi longitudinal de maturation.
- Cible : section 6, `ages_graines.csv`, figure conservée `rev_deciles`.
- Rapport : à reporter sans transformer l'association d'âge en causalité identifiée.

### COR-019 — Partage, référence brute et régressions

- Origine : ancienne figure 11 ; Gini(p=0), axe stock depuis zéro, équations et R².
- Appliqué : références brutes, rapports appariés à p=0, stock depuis zéro, régressions linéaires descriptives par graine avec équations et R² ; faible qualité de certaines tendances signalée.
- Vérification : cinq valeurs de p, douze graines. Référence Gini NW ≈ 0,61549, population ≈ 1904, capital ≈ 2,874 millions ; population p=1 ≈ 1138.
- Cible : section 7, `art_institutions`, `institutions_*`.
- Rapport : à reporter sans assimiler une droite descriptive à une loi causale.

### COR-020 — Charge et ancienne « réfutation »

- Origine : ancienne section 7.2 et figure 12 ; mauvais dénominateur, classes indéfinies.
- Appliqué : intérêts versés / (production + intérêts reçus), distinct de dette / revenu. Classes fixes et effectifs explicités ; décès à dix pas uniquement sur les horizons entièrement observés.
- Vérification : bras marginal, douze graines, instantanés 3010…3990 ; toutes causes distinguées des racines d'insolvabilité. Cinq classes non vides sous 1, aucune observation dans les classes supérieures prévues.
- Retrait scientifique : conclusion « la convexité ne tient pas » abandonnée. Le service dû n'est pas enregistré dans les panneaux ; les intérêts payés peuvent différer du dû. Sélection des survivantes, âge et état initial limitent aussi l'interprétation.
- Cible : annexe C, `art_charge`, `charge_*` ; ancienne figure retirée du texte courant.
- Rapport : **à reporter prioritairement** dans définitions et conclusions du risque ; remplacer le raisonnement, pas seulement la légende.

### COR-021 — Identité de pondération

- Origine : preuve de l'ancienne équation 6, ancienne section 7.3 superflue.
- Appliqué : preuve de moyenne pondérée − moyenne simple = covariance(p, surplus) / moyenne(surplus). Grille analytique étendue et graphiques de contrats rares retirés du fil principal.
- Vérification : identité testée ; portée comptable séparée d'une explication démographique.
- Cible : section 7, annexe C.
- Rapport : preuve et limites à reporter ; ampleur du développement à adapter.

### COR-022 — Surdétermination et suffisance

- Origine : ancienne section 8 incompréhensible ou superflue.
- Appliqué : développement quantitatif retiré du corps ; exemple simple en annexe distinguant pertes nécessaires ensemble et causes individuellement suffisantes. Les anciennes mesures ne sont plus présentées comme preuve dans l'article.
- Motif : pluralité d'arêtes et pluralité de causes suffisantes ne coïncident pas.
- Cible : annexe D.
- Rapport : distinction à reporter ; anciennes statistiques à réauditer avant toute reprise.

### COR-023 — Familles de lois et paramètres

- Origine : log-normale contre Pareto tronquée, coupure dépendant de la taille.
- Appliqué : distinction entre puissance discrète à coupure des avalanches et queues continues de bilan ; rappel des deux paramètres des familles envisagées.
- Réserve : une dépendance supposée à la taille ne supprime pas un paramètre libre sans loi de taille finie établie. Les données ne prouvent ni divergence de coupure ni universalité.
- Cible : section 8 et annexe B.
- Rapport : à reporter dans distributions, criticité et limites.

### COR-024 — Gini NW et Vuong

- Origine : anciennes figures 16–17 ; NW plus pertinent, deux populations apparentes, détailler Vuong.
- Appliqué : Gini NW recalculé sur les panneaux du balayage rho ; trois autres mesures conservées. L'ancien Gini de bassin concernait l'échantillon de rencontre, pas le capital de la population.
- Appliqué : figure Vuong retirée ; formule, échantillon commun, signe et conditions d'interprétation détaillés en annexe avec référence originale.
- Réserve : les points représentent des ajustements, pas des individus ; deux groupes de scores ne prouvent pas deux populations d'entités. Seuil sélectionné et dépendances empêchent une interprétation automatique des seuils gaussiens.
- Cible : `art_rho`, annexe B, `rho_nw_graines.csv`.
- Rapport : à reporter dans pilotage et discrimination des lois avec ces réserves.

### COR-025 — Autonomie et conservation

- Origine : article autonome et conservation pour report futur.
- Appliqué : assemblage local, table de correspondance des seize figures, exports, manifeste des sources, script article et neuf tests ciblés. Le collecteur historique s'arrête avant toute écriture pour le nouvel assemblage.
- Vérification : compilation autonome en trois passes ; références, figures, calculs ciblés, empreintes du carnet, du PDF archivé et des fichiers principaux du rapport. Ces contrôles ne garantissent pas l'absence de toute erreur scientifique.
- Archives : ancien PDF et sources dans `reference/latex/`, copie du carnet dans `reference/` ; original intact.
- Rapport : adaptation ultérieure seulement ; ne pas exécuter les générateurs partagés pour appliquer indistinctement ces changements.

## Ordre recommandé du futur report

1. Définitions et conclusions scientifiques : charge, causalité, Gini, lois, compensation et stationnarité (COR-014, COR-016, COR-020–024).
2. Notations et exemples pédagogiques (COR-003–007).
3. Résultats recalculés avec moteurs, fenêtres et graines correspondants (COR-009–013, COR-017–019).
4. Introduction et bilan propres au rapport (COR-001–002, COR-008).
5. Décision séparée sur les nouvelles simulations éventuelles (COR-012, COR-015).

## Vérifier la livraison

Depuis `/home/anatole/jupyter/recherche/` :

```bash
OPENBLAS_NUM_THREADS=1 ../.venv/bin/python note_resultats/scripts/verify_article.py --compile
```

Les neuf tests ne couvrent pas tous les nombres du projet, ne certifient pas la convergence statistique des simulations et ne remplacent pas les expériences ouvertes. Sources bibliographiques avec liens dans le PDF ; sources numériques et empreintes dans `latex/data_article/manifest.json`.
