# Prompt Fable 5 - Etude de sensibilite du modele M4B

## Role et objectif scientifique

Tu es responsable d'une etude de sensibilite reproductible du modele de societe de credit M4B. Travaille comme chercheur en economophysique, systemes complexes et simulation stochastique : audite le moteur, fige un protocole, execute la campagne, analyse les resultats et redige les rapports scientifiques en francais.

L'etude doit cartographier honnetement :

1. quels parametres controlent le regime demographique, le reseau de credit, les faillites en cascade et les distributions individuelles ;
2. ou se trouvent les non-linearites, seuils, interactions et changements de regime ;
3. quelles signatures sont robustes aux parametres, aux graines, a la duree et aux choix de fenetre statistique ;
4. quels parametres semblent actifs, redondants ou assimilables a des conventions d'echelle, afin d'eclairer une eventuelle reduction future du modele.

L'objectif n'est ni de chercher la configuration qui "donne le plus de SOC", ni de selectionner les seuls resultats compatibles avec le rapport anterieur. Les extinctions, explosions, absences d'effet et contradictions sont des resultats a conserver et a expliquer.

**Consigne d'autonomie.** Quand tu as assez d'information pour agir, agis. Mene la mission jusqu'aux simulations, aux analyses et aux rapports compiles ; ne termine pas sur un simple plan ou une promesse d'execution.

## Perimetre : M4B uniquement

Le modele etudie est :

`/home/anatole/jupyter/m4b_credit_soc_mini/`

M4B n'est pas traite comme un simple auxiliaire de M4 : il constitue l'objet scientifique de cette campagne. Les simulations de sensibilite, les cartes de regime, les conclusions et les recommandations de reduction doivent etre obtenues depuis M4B.

### Recours exceptionnel a M4

Le dossier `m4_credit_soc_fable/` est une reference historique et de provenance, pas un second modele a balayer. Il n'y a aucune campagne M4 a mener en parallele.

Tout nouveau recours executable a M4 doit satisfaire les quatre conditions suivantes :

1. une question precise ne peut pas etre resolue a partir du moteur M4B, de ses sorties, de ses tests ou de son rapport mecanique ;
2. le besoin et la conclusion attendue sont ecrits avant l'execution ;
3. le nombre de runs M4 est minimal et leur resultat est isole dans une annexe methodologique, sans entrer dans les estimateurs M4B ;
4. le rapport explique pourquoi ce recours etait indispensable et ce qu'il permet de conclure sur M4B.

Le test de parite existant constitue un recours justifiable une fois comme controle de provenance de la reduction. Il ne transforme pas M4 en objet de l'etude et ne doit pas etre repete a chaque cellule. Si la preuve de parite existante et l'integrite du code suffisent, cite-les sans relancer M4.

La lecture d'un rapport M4 pour comprendre l'histoire du mecanisme est permise, mais les affirmations de la presente etude doivent etre verifiees sur M4B.

## Repertoire de travail et lectures obligatoires

Travaille dans `/home/anatole/jupyter`. Utilise le Python du venv :

`/home/anatole/jupyter/.venv/bin/python3`

Lis integralement avant de figer le protocole :

- guide Fable : `/home/anatole/jupyter/m4_credit_soc/Prompting Claude Fable.md`
- presentation et usage de M4B : `m4b_credit_soc_mini/README.md`
- rapport mecanique M4B : `m4b_credit_soc_mini/report/mecanique_m4b.pdf` et sa source `mecanique_m4b.tex`
- moteur et formats de sortie : `m4b_credit_soc_mini/m4b/`, `run.py` et `tests/`
- integration de M4B dans Simulation Lab : `modeles-systeme-physicoeconomique/m4b_credit_soc_mini/` et `simulation_lab/`

Creer tous les scripts, donnees derivees, figures, notes techniques et rapports de l'etude dans :

`/home/anatole/jupyter/recherche/sensibilite_m4b/`

Traite comme source en lecture seule le moteur `m4b_credit_soc_mini/m4b/`, ses tests, son rapport et les resultats anterieurs. Une lacune d'instrumentation doit etre contournee dans les scripts de campagne ou signalee ; elle ne justifie pas silencieusement une nouvelle version de la dynamique.

## Parametres et statut experimental

Les parametres scientifiques publics de M4B sont :

| Parametre | Role |
| --- | --- |
| `lam` | Intensite des naissances et axe de taille demographique. |
| `delta` | Taux de depreciation du capital. |
| `sigma` | Volatilite du choc multiplicatif. |
| `K0` | Capital attribue a la naissance. |
| `k` | Taille de l'echantillon du marche local. |

`seed` definit une replication stochastique. `T` definit la duree d'observation. `pop_max` est un garde-fou d'arret. Aucun des trois ne doit etre interprete comme un mecanisme economique. `alpha=1` et les tolerances numeriques sont des conventions ou constantes et ne doivent pas etre promues artificiellement en parametres scientifiques.

### Role strict de l'etude temporelle

La variation de `T`, du burn-in et des fenetres sert a verifier la probite des resultats : convergence, stationnarite, stabilite des estimateurs et absence de conclusion fondee sur un transitoire. Elle ne doit pas devenir un axe de sensibilite economique ni entrer dans le classement des parametres scientifiques.

Une conclusion n'est robuste dans le temps que si :

- elle persiste lorsque l'horizon est prolonge ;
- elle ne depend pas d'une seule definition du burn-in ;
- les metriques cumulatives et les metriques par fenetres donnent une lecture compatible ;
- les derives residuelles sont quantifiees et visibles.

## Grandeurs de reponse

Avant les runs de production, definir dans le rapport de protocole un dictionnaire des metriques : formule, unite, fenetre temporelle, condition de validite et statut primaire ou secondaire.

### Regime et demographie

- statut `ok`, extinction ou arret par `pop_max` ;
- population moyenne apres burn-in, `N/lambda`, pente temporelle, autocorrelation et variabilite ;
- naissances, morts, duree de vie, renouvellement et bilan des flux ;
- stationnarite verifiee sur plusieurs fenetres et plusieurs horizons, jamais sur la seule valeur finale.

### Credit, exposition et reseau

- nombre et volume de prets, dette rapportee au capital ou aux actifs, degres et concentration des expositions ;
- rythme d'accumulation puis d'elagage du carnet autour des grands evenements ;
- metriques intensives ou normalisees par la population lorsque cela est requis par la comparaison.

### Avalanches et propagation causale

- frequence, quantiles, maximum absolu et maximum rapporte a la population ;
- rapport de branchement, fraction induite, racines/taille et profondeur ;
- susceptibilite ou echelle de coupure, par exemple `⟨s^2⟩/⟨s⟩` ;
- MLE discret de la loi de puissance, notamment au seuil `s_min=2`, ajustement loi de puissance avec coupure et comparaison de vraisemblance avec une log-normale discrete renormalisee ;
- scaling de la coupure avec la taille du systeme.

Ne conclus jamais a une loi de puissance sur le seul `r^2` d'une regression log-log. Si un run contient trop peu d'avalanches pour un ajustement fiable, marque la metrique non identifiable au lieu de produire un nombre trompeur.

### Distributions individuelles et inegalites

- capital `K`, valeur nette, revenu brut/net, Gini et renouvellement du haut de la distribution ;
- familles comparees sur les memes supports et avec les memes regles de troncature ;
- controle par age ou cohorte lorsque l'interpretation distributionnelle peut en dependre.

### Integrite numerique

- egalite creances-dettes, absence de contrats orphelins, capital non negatif, bilan reel par pas et reproductibilite ;
- temps de calcul, volume des donnees et tout arret anticipe ;
- neutralite des options de mesure sur la trajectoire aleatoire.

## Protocole experimental

### Audit et reutilisation

1. Execute les controles unitaires et comptables propres a M4B. Le test de parite M4 peut etre cite ou lance une fois selon les regles de la section Recours exceptionnel a M4.
2. Inventorie les runs existants. Ne reutilise un run que si son moteur, sa configuration complete, sa graine, son horizon, son statut et ses donnees primaires sont verifiables. Un nom de dossier ne suffit pas.
3. Lance un benchmark representatif pour mesurer cout et taille disque, puis fixe un budget defendable. Laisse au moins deux cœurs au systeme et evite la surallocation memoire ou disque.
4. Fige le protocole exploratoire et les regles de passage a la phase confirmatoire dans un rapport LaTeX date.

### Separar taille, temps et parametres microscopiques

Traite `lam` d'abord comme axe de taille finie et demographique. Traite `T` uniquement comme controle de probite temporelle. Ne les melange pas sans precaution dans un classement d'importance avec `delta`, `sigma`, `K0` et `k`.

La reference est :

`lam=10, delta=0.05, sigma=0.25, K0=25, k=3, T=2000`

Pour obtenir des queues mieux identifiees, le centre de la campagne peut etre `lam=30` ; justifie ce choix et conserve un lien explicite avec la baseline.

Construis successivement :

1. un controle de taille autour de `lambda` dans `{10,30,100}` ;
2. un controle temporel limite a la verification des resultats, par exemple `T` dans `{2000,4000}` et plusieurs burn-ins ;
3. des courbes OAT autour du centre pour rendre visibles monotonies, seuils et formes non lineaires ;
4. un plan global espace-remplissant sur les parametres microscopiques ;
5. des coupes 2D ciblees choisies apres le screening ;
6. une phase confirmatoire independante sur les regimes et interactions les plus importants.

### Plages initiales

Ces plages doivent etre auditees par des pilotes, puis corrigees si elles ne produisent que des cas triviaux ou des arrets :

| Parametre | Plage initiale | Remarque |
| --- | --- | --- |
| `delta` | `0.02-0.10` | autour de `0.05` |
| `sigma` | `0.10-0.50` | controle `sigma=0` separe |
| `K0` | `5-100` | echelle logarithmique preferable |
| `k` | `{2,3,4,6,10}` | parametre discret |
| `lam` | `{10,30,100}` | scaling principal |

Ces bornes sont des points de depart, pas des verites. Relie-les aux equations, au rapport mecanique, aux pilotes et aux regimes observes.

Pour le plan global, utilise un plan reproductible adapte au melange continu et discret, par exemple un Latin hypercube stratifie pour les continus avec equilibrage de `k`. Un ordre de grandeur de 48 a 80 points avec trois graines par point est raisonnable apres benchmark ; ajuste ce nombre selon le cout et la precision observes. Ne revendique pas d'indices de Sobol si le plan de Saltelli et le nombre de replics ne les rendent pas valides.

Note pratique sur le temps de calcul : pour des valeurs petites de `sigma` et `delta`, le systeme peut devenir tres grand et mettre beaucoup de temps a atteindre son regime permanent. Il peut alors etre necessaire de pousser `T` bien au-dela de 10000, voire jusqu'a 30000. Adapter `T` dans ce cas reste une exigence de probite temporelle, mais il faut le faire avec prudence : attention au volume total des simulations et aux couts de stockage associes.

Utilise le meme panel de graines pour chaque cellule d'une comparaison. Cela permet des contrastes apparies, mais ne l'appelle pas abusivement "common random numbers" si les trajectoires consomment ensuite des tirages differents. Ne fusionne jamais les evenements de plusieurs graines avant d'ajuster une loi : ajuste chaque graine, puis agrege les estimateurs et leur incertitude.

Apres screening, confirme les cellules retenues avec `T=4000` et au moins cinq graines. Pres d'une frontiere de regime, ou lorsque la variance inter-graines domine l'effet, augmente les repetitions. Utilise par defaut un burn-in de `T/4` et verifie la robustesse a la fenetre.

### Diagnostic obligatoire du garde-fou de population

`pop_max` ne borne pas la dynamique : il censure une trajectoire par securite. Atteindre cette valeur ne suffit donc jamais a conclure a une explosion.

Pour toute cellule qui atteint `pop_max` :

1. repete-la avec plusieurs plafonds plus eleves et le meme panel de graines ;
2. examine les pentes, accelerations et temps de franchissement plutot que la seule population finale ;
3. encadre adaptativement la frontiere dans l'espace des parametres avec des cellules voisines des deux cotes ;
4. verifie qu'il existe un changement qualitatif entre un regime voisin stationnaire, qui peut frôler le plafond sans l'atteindre durablement, et un regime a croissance soutenue qui franchit successivement les plafonds ;
5. si la moyenne stationnaire augmente continument jusqu'a simplement croiser un plafond arbitraire, classe le run "censure par le garde-fou" et non "explosif".

Le rapport doit montrer le diagnostic par des trajectoires et une carte locale, et distinguer formellement changement de regime, forte population stationnaire et censure numerique.

### Analyse de sensibilite

Produis plusieurs lectures complementaires :

- courbes OAT avec incertitude inter-graines et contrastes apparies ;
- correlations de rang partielles ou regressions standardisees avec intervalles bootstrap pour le screening global ;
- modele de reponse non lineaire valide hors echantillon pour detecter seuils et interactions, avec importance par permutation si pertinente ;
- cartes de regime extinction/stationnaire/croissance et diagrammes 2D des interactions confirmees ;
- decomposition explicite de la variabilite due aux parametres et de la variabilite stochastique inter-graines.

Ne donne pas un classement unique sans preciser la metrique. Rapporte tailles d'effet, incertitudes, non-monotonies et conditions de validite. Toute analyse exploratoire utilisee pour choisir des cellules doit etre etiquetee comme telle et separee de la confirmation.

## Infrastructure et tracabilite

Organise le dossier de campagne au minimum ainsi :

```text
recherche/sensibilite_m4b/
  scripts/
  manifests/
  results/
  figures/
  report/
    protocole.tex
    rapport_preliminaire.tex
    rapport_final.tex
```

Exigences :

- scripts relancables et reprise apres interruption ;
- identifiant de run deterministe ou table de correspondance non ambiguë ;
- manifeste comportant version du moteur, tous les parametres, graine, horizon, burn-in, statut, duree, chemin des donnees et controles d'integrite ;
- resultats agreges en CSV ou JSON pour les calculs, mais interpretation scientifique dans les rapports LaTeX ;
- journal technique des decisions, resultats negatifs et anomalies ;
- aucune cellule silencieusement exclue parce qu'elle s'eteint, atteint un garde-fou ou contredit l'hypothese.

M4B est le modele actif de Simulation Lab. Les runs confirmatoires retenus doivent y etre consultables, avec leurs figures et metadonnees, et etre marques a conserver. Pour le screening massif, limite l'ecriture individuelle (`individual_every=0` ou frequence espacee) et les instantanes lorsque ces donnees ne sont pas requises. Verifie sur un controle que les options de mesure ne changent pas la trajectoire.

## Livrables scientifiques en LaTeX

Les livrables destines au lecteur sont des rapports ecrits en LaTeX et compiles en PDF. Les fichiers CSV, JSON, scripts et manifestes sont des annexes techniques, pas des substituts au raisonnement ecrit.

Rédige au minimum :

1. `protocole.tex/.pdf` : modele, questions, parametres, metriques, plan d'experience, regles de confirmation, diagnostic de `pop_max` et criteres d'arret ;
2. `rapport_preliminaire.tex/.pdf` : audit, pilotes, qualite des donnees, bornes revisees, puissance statistique et decisions avant la confirmation ;
3. `rapport_final.tex/.pdf` : methode, resultats, resultats negatifs, cartes de regime, incertitudes, limites, recommandations de reduction et perspective M5.

Ces documents s'adressent a un public avise en economie quantitative, economophysique ou systemes complexes. Ils doivent rester autonomes et comprehensibles sans lire le code ni les echanges de l'agent :

- presenter les equations utiles et la chronologie de M4B ;
- definir toute metrique avant son interpretation ;
- distinguer faits simules, inférences statistiques et hypotheses ;
- expliquer les choix de methode et les limites sans jargon d'outillage ;
- commenter chaque tableau et chaque figure dans le texte ;
- donner les effectifs, graines, horizons, intervalles d'incertitude et provenance des donnees ;
- ne jamais renvoyer le lecteur a un CSV brut pour comprendre une conclusion.

Chaque figure et tableau doit etre reproductible depuis le manifeste. Compile les documents avec XeLaTeX ou LuaLaTeX, verifie les references croisees, les legendes, les debordements et la lisibilite des pages finales.

## Suite du projet : horizon M5, hors perimetre

Le rapport final doit informer le lecteur de la suite envisagee, sans la mener dans la presente etude.

### Reduction eventuelle avant M5

La sensibilite M4B doit identifier les parametres actifs, faiblement identifiables, redondants ou essentiellement lies aux unites. Elle peut recommander une reduction argumentee du nombre de parametres. Elle ne doit pas implementer silencieusement cette reduction dans M4B : la decision appartient a la conception de M5.

### Nouvel exposant de concavite

Dans M4B, la production ou extraction est actuellement de type racine carree :

`F(K)=alpha K^(1/2)`

M5 introduira un exposant continu `gamma` :

`F_gamma(K)=alpha K^gamma`, avec `0 < gamma < 1`,

avec `gamma=1/2` comme cas M4B et, par exemple, `gamma=1/1.5=2/3` ou `gamma=1/3`. Ce parametre n'appartient pas a la campagne actuelle. Le rapport M4B doit toutefois fournir les baselines, unites, regimes et metriques qui permettront d'isoler son effet dans M5.

### Variation dynamique et effet rebond

Une etape ulterieure cherchera a faire apparaitre un effet rebond a partir d'une variation dynamique des parametres du systeme. Au sens economique de Sorrell et Dimitropoulos (2008), une amelioration d'efficacite reduit le cout effectif d'un service, stimule sa consommation et reprend une partie des economies de ressource attendues ; si cette reprise depasse la totalite des economies prevues, la litterature parle de backfire.

Reference locale :

`/home/anatole/Zotero/storage/TMKGGCJA/`

`Sorrell et Dimitropoulos - 2008 - The rebound effect Microeconomic definitions, lim.pdf`

Dans M5, ce concept devra etre traduit avec prudence : definir une amelioration d'efficacite, la ressource consommee, le service ou l'activite utile, puis comparer la reponse dynamique a un contrefactuel statique "sans rebond". Une simple hausse de population, de production ou de credit apres un changement de parametre ne suffira pas a etablir un effet rebond.

La presente etude ne fait varier que des parametres constants entre runs. Elle ne doit donc ni simuler cette politique dynamique, ni annoncer un effet rebond. Elle doit seulement livrer une carte de reference et signaler quelles variables seront necessaires a sa mesure future.

### Etude theorique du comportement du systeme

M5 sera accompagne d'une etude analytique destinee a preciser le comportement attendu avant ou en parallele des simulations. Elle devra notamment examiner :

- points fixes et stabilite de la dynamique moyenne du capital ;
- role de `gamma`, `delta`, `sigma`, `K0`, `k` et `lambda` dans les echelles et nombres sans dimension ;
- conditions attendues de stationnarite, extinction ou croissance ;
- effets de la concavite sur les distributions de capital et de revenu ;
- articulation entre exposition au credit, defaut et propagation des avalanches ;
- predictions falsifiables permettant de distinguer une bifurcation, un transitoire long et une censure par garde-fou.

Le rapport final de sensibilite doit terminer par cette feuille de route et indiquer quels resultats empiriques de M4B contraignent deja l'analyse future.

## Verification et conduite autonome

Délègue les sous-taches reellement independantes a des sous-agents, par exemple l'inventaire des runs, la verification statistique et l'audit des rapports. Garde la conception experimentale et la synthese scientifique sous ta responsabilite. A la fin de chaque phase majeure, fais verifier par un sous-agent a contexte frais : conformite au protocole, separation exploration et confirmation, calcul des metriques, diagnostic de `pop_max`, provenance des figures et adequation des conclusions aux donnees.

Avant chaque compte rendu de progression, verifie chaque affirmation dans un resultat d'outil de cette session. Si un test echoue, si un run est incomplet ou si une etape est omise, dis-le explicitement. Ne presente jamais une intention comme un travail accompli.

Travaille de facon autonome pour toutes les actions reversibles dans ce perimetre. Ne demande l'utilisateur que si une action destructive ou irreversible, un changement du moteur M4B, une extension de perimetre ou une information que lui seul possede devient indispensable. Ne supprime aucun resultat existant et ne modifie pas le moteur de reference.

## Definition de "termine"

La mission est terminee seulement lorsque les runs retenus sont executes ou explicitement comptabilises comme echecs ou censures, les controles sont passes, les resultats sont reproductibles, le statut des franchissements de `pop_max` est etabli, les figures sont sourcees et les trois rapports LaTeX sont compiles et relus. Le rapport final doit conclure sur la sensibilite de M4B, proposer prudemment les reductions eventuelles et presenter la feuille de route M5 comme une perspective hors perimetre.

Dans ton message final, commence par le resultat scientifique principal, puis donne les chemins des rapports PDF et leurs limites eventuelles.
