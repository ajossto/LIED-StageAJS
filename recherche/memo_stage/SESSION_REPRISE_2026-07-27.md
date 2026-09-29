# État de reprise de la discussion — 27 juillet 2026

Ce fichier conserve le contexte nécessaire pour reprendre le travail après
extinction de l'ordinateur. Il ne remplace pas le mémo maître : il indique où
en est la collaboration, quelles décisions sont confirmées et quelle doit être
la prochaine étape.

## 1. Demande initiale

Construire progressivement un dossier académique complet à partir de tout le
travail de stage présent dans le dépôt et dans Zotero. Ce dossier doit retracer
le raisonnement, les hypothèses, les résultats positifs et négatifs, les
artefacts, les bifurcations méthodologiques et les sources. Il servira ensuite
de source unique pour produire, selon le besoin, une fiche d'avancement, une
note de communication, un pré-rapport ou un rapport de stage complet.

Le rôle demandé à l'assistant est celui d'un journaliste-chercheur ayant accès
aux données : lire les pièces, reconstruire la trajectoire sans la lisser,
contrôler la provenance des affirmations et poser à Anatole des questions de
fond. La priorité actuelle est l'assemblage exhaustif des données nécessaires,
pas le choix du lectorat, de la longueur ou de la mise en forme finale.

## 2. Fichiers de travail canoniques

- `recherche/memo_stage/memo_recherche_complet.md` : mémo maître, version 1.0,
  environ 15 500 mots ; récit scientifique et registre des affirmations.
- `recherche/memo_stage/inventaire_sources_preuves.md` : inventaire version
  0.2 ; provenance, indépendance des preuves, lacunes et ordre de dépouillement.
- `recherche/memo_stage/README.md` : point d'entrée du dossier.
- le présent fichier : état de reprise de la collaboration.

Une analyse complémentaire des récessions mesurées sur l'énergie totale a été
ajoutée à `recherche/sensibilite_m4b/scripts/analyze_cycles.py`, aux tableaux
de `recherche/sensibilite_m4b/results/summary/` et au journal
`recherche/sensibilite_m4b/JOURNAL.md`.

## 3. Informations institutionnelles confirmées

- Stage de recherche, printemps et été 2026.
- ENS Rennes, département mécatronique, parcours *Recherche aux interfaces*.
- Stage au LIED.
- Titre : *Étude et modélisation de l'effet de rebond par approche
  énergétique. Métabolisme des sociétés industrielles*.
- Encadrement : Éric Herbert, Petros Chatzimpiros, Christophe Goupil et
  Jean-Philippe Brunetton.
- Les idées scientifiques sont attribuées à Anatole. Les encadrants ont joué un
  rôle de garde-fou, d'aide méthodologique, d'orientation et d'inspiration par
  les discussions. La généalogie d'une idée ne doit pas être racontée comme une
  propriété individuelle simple lorsqu'elle est née par réflexion avec eux.

## 4. Hypothèse et ambition scientifiques

Hypothèse de programme : l'effet rebond peut être un mécanisme endogène à
l'organisation de la société économique ; cette organisation pourrait avoir
une architecture similaire à un régime auto-critique.

Objectif intermédiaire actuel : construire un toy-model minimal, inspiré de la
physique statistique et de mécanismes proches des systèmes auto-critiques, qui
engendre endogènement des distributions plausibles. Une fois ce système
construit et compris, introduire une modification dynamique d'efficacité et
chercher un phénomène assimilable à un effet rebond.

Le statut correct de la SOC est : **hypothèse non actuellement réfutée, mais
non démontrée**. Même en cas de réfutation de l'application aux sociétés
capitalistes, le modèle conserverait une valeur théorique comme système
stochastique en réseau, avec une portée économique et physique réduite.

La démarche est décrite comme un accordéon : élargir les hypothèses et le
modèle pour faire apparaître des comportements, puis élaguer pour isoler le
mécanisme minimal.

## 5. Interprétation des objets du modèle

- Une entité est volontairement générique : personne, entreprise, objet
  technique, etc. Toutes les entités d'un run suivent les mêmes règles.
- Personnes et entreprises correspondent au même moteur avec des paramètres
  différents, pas à deux populations coexistantes.
- `K` est seulement la taille abstraite de l'entité.
- `NW` est une taille nette / position nette interne distincte de `K`, sans
  identification économique plus précise exigée dans le périmètre du stage.
- Le joule est actuellement une unité comptable abstraite.
- L'intuition selon laquelle l'argent serait un droit d'accès à l'énergie,
  motivée notamment par la corrélation exergie–PIB, sous-tend la réflexion mais
  n'est pas structurante pour le moteur actuel.

## 6. Résultats et moments importants rapportés par Anatole

- Premier moment marquant : obtention, dès les premiers runs, d'une taille
  totale du système bornée malgré la possibilité de divergence.
- Second moment : apparition des premières lois de puissance dans M4, avec des
  distributions plausibles.
- Résultat partiel actuellement formulé : naissances + prêts avec intérêts +
  érosion produisent un système potentiellement auto-critique.
- Critère de validation supplémentaire : durée, fréquence et amplitude des
  récessions, définies par les variations de l'énergie totale
  `E_t = somme_i K_i(t)` en fin de pas.
- Critère falsificateur : si l'exposant des cascades ne peut pas être manipulé
  et reste fortement incompatible avec la cible empirique des entreprises, il
  faut restructurer les hypothèses.

## 7. Cibles économiques et difficulté de validation

- Personnes : revenu brut annuel avant impôts, revenus du travail et du capital
  inclus. Proxy actuel : production cumulée + intérêts reçus, sans déduction
  des intérêts payés.
- Entreprises : chiffre d'affaires. Proxy actuel : production cumulée, hors
  intérêts, avec l'hypothèse comptable implicite que toute production est
  vendue à prix unitaire puisqu'il n'existe ni prix ni marché de biens.
- Patrimoine / taille nette : comparer au minimum les classes de distribution,
  sans imposer pour l'instant une correspondance précise à `K` ou `NW`.
- Mobilité sociale : critère futur fort, non encore intégré ; piste d'un
  mécanisme de filiation.
- Récessions : durée, fréquence et amplitude de `E_t`.
- Boltzmann–Pareto est une branche secondaire explorant l'arbitrage entre
  complexité du toy-model et similitude des phénomènes observés.

Conclusion épistémique centrale : l'absence de données académiques solides,
unifiées et directement compatibles pour identifier les distributions réelles
est une information importante du stage. Elle ne valide pas le modèle, mais
elle empêche de le rejeter contre une cible arbitraire ou mal définie. Le
verdict externe doit être suspendu jusqu'à construction d'une comparaison
compatible. Cela concerne les revenus, le chiffre d'affaires, la consommation
d'exergie, les cascades causales de faillites, les récessions et la mobilité.

## 8. Trajectoire scientifique reconstruite

### Premiers modèles et correction des artefacts

Le premier modèle était trop compliqué. Une bimodalité initialement interprétée
comme deux classes économiques était surtout un artefact de cohortes ; la queue
lourde dérivait avec l'horizon. Cela a conduit à supprimer la cohorte
fondatrice, contrôler l'âge et les fenêtres temporelles, multiplier les graines
et distinguer formes visuelles et identification statistique.

### M2

M2 est mieux décrit comme un modèle nul démographique de type Reed : naissance,
croissance multiplicative et absorption produisent l'essentiel des formes. Le
crédit est distributionnellement neutre. Le corps est généralement Fisk ; une
queue effective stable ne suffit pas à identifier Pareto contre une lognormale
tronquée. Des erreurs de comparaison de vraisemblance et de normalisation de
l'AIC ont été corrigées.

### M3

M3 sépare liquidité `L` et capital `K`. Le crédit devient causal sur la
démographie, divisant approximativement par deux population et espérance de
vie, mais reste neutre sur les distributions dans la baseline. La liquidité
n'est pas Boltzmann–Gibbs. Les cascades restent petites et sous-dispersées.

L'ablation H (`d0=0`) montre sur trois graines que la dette contractuelle peut
remplacer le plancher exogène et borner le système. La variante X1, où les
entités maximisent myopement leur revenu plutôt que la richesse soutenable,
rend le crédit distributionnellement actif, augmente le levier et les défauts
de liquidité, sans produire de SOC.

Deux protocoles M3 sont non concluants : F confond topologie et extinction du
volume de crédit ; G1 confond corrélation des chocs et réduction de la
dispersion idiosyncratique. Un bug d'observation non neutre et un estimateur CSN
dégénéré ont été détectés puis corrigés.

### M4

Le journal M4 date les bifurcations :

- 13 juillet : reprise de M3, règle de revenu, retrait de `d0`, prototype à un
  seul `K`, estimateurs discrets, test de la naissance par emprunt ;
- les grands événements sectoriels sont réfutés comme contagion : ce sont des
  racines synchronisées ;
- un candidat à `k=3` est ensuite réfuté comme effet de taille finie ;
- 14 juillet : découverte de la combinaison annulation des contrats +
  destruction du résidu, qui crée la première propagation causale profonde ;
- la naissance par emprunt n'est pas nécessaire au régime ;
- 16 juillet : campagne confirmatoire dans Simulation Lab ;
- 17 juillet : analyses distributionnelles supplémentaires puis réduction vers
  M4B.

Une loi de puissance apparente, une propagation causale et une SOC sont trois
niveaux distincts. M4 établit la propagation dans son moteur. La SOC au sens
fort reste une hypothèse prudente ; la campagne de sensibilité M4B est la
référence quantitative ultérieure.

### M4B et sensibilité

M4B est la réduction minimale de M4, non une confirmation indépendante. La
campagne principale documente le régime stationnaire, les rôles distincts de
`sigma`, `k`, `K0`, `delta` et `lambda`, les cascades tronquées et leurs effets
de taille, ainsi que la structure de `NW`.

Une analyse post-audit des contractions de l'énergie totale donne, au centre et
sur cinq graines, environ 252 récessions par millier de pas, une durée moyenne
de 1,93 pas et une perte représentative moyenne d'environ 3,5 %. L'amplitude est
surtout pilotée par `sigma` et `K0`. C'est une baseline interne, pas une
validation externe.

## 9. Zotero déjà dépouillé

La bibliothèque locale contient 43 références principales. Les constats
provisoires déjà versés au mémo sont :

- Yakovenko–Rosser : structure en régimes pour les revenus, mais corps et queue
  dépendent des conventions et périodes ;
- Wright : corps inférieur lognormal et queue Pareto dans certains cadres ;
  croissance des ventes Laplace/Subbotin ;
- Fisk : difficulté d'une fonction mondiale unique du revenu et arbitrage entre
  ajustements à trois ou quatre paramètres ;
- Watts : exposant `3/2` théorique, pas mesure empirique de cascades de
  faillites ; l'article signale lui-même le manque de données détaillées ;
- Dessertaine et Arvidsson et al. : tailles de firmes lourdes, mais objet exact
  et niveau de chiffre d'affaires encore mal alignés sur le modèle ;
- aucune cible empirique causalement comparable pour l'exposant des cascades de
  faillites n'a encore été identifiée.

## 10. État documentaire au moment de l'arrêt

- Le mémo maître et l'inventaire ont été vérifiés par `git diff --check`.
- Le mémo compte environ 1 810 lignes et 15 561 mots.
- L'inventaire compte environ 420 lignes et 3 324 mots.
- Les dossiers apparaissent non suivis dans l'état Git observé ; aucun commit
  n'a été créé ni demandé.
- Le prochain dépouillement prévu porte sur les journaux M4B, les premiers
  modèles antérieurs à M2, puis les corpus empiriques sur chiffre d'affaires,
  cascades causales et exergie.

## 11. Questions à poser à Anatole à la reprise

1. Les présentations associent l'origine de l'intuition SOC notamment à la
   lecture de Hendrick et à l'analogie entre organismes, villes et réseaux
   économiques. Hendrick a-t-il été le déclencheur principal, ou cette intuition
   vient-elle d'un faisceau de lectures qu'il serait artificiel de hiérarchiser ?
2. Le passage M3-H + X1 vers M4 est-il une décision consciemment formulée à
   l'époque — combiner plancher contractuel endogène et règle de revenu — ou une
   reconstruction seulement visible après lecture des journaux ?
3. Dans le noyau actuel « naissances + prêts avec intérêts + érosion », quel
   statut faut-il donner à la production concave et à la règle
   annulation--destruction : mécanismes indispensables, choix provisoires à
   élaguer ou conventions techniques ?

## 12. Consigne de reprise pour l'assistant

Relire d'abord ce fichier, puis le README, le mémo maître et l'inventaire. Ne
pas recommencer l'enquête depuis zéro et ne pas demander de choix éditoriaux.
Reprendre par les réponses d'Anatole aux trois questions ci-dessus, les intégrer
avec leur statut épistémique, puis poursuivre le dépouillement des sources et la
carte affirmation–preuve.
