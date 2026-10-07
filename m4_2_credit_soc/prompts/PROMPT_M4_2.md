# Prompt de recherche M4.2 — comment piloter la pente des avalanches ?

## Mission

Conçois, implémente, vérifie et étudie **M4.2**, successeur direct de M4B, à
partir de la question ouverte suivante :

> **Comment construire une famille de sociétés de crédit M4.2 dans laquelle la
> pente de la distribution des avalanches de faillites devient une propriété
> modulable, causalement intelligible et statistiquement robuste, sans détruire
> le mécanisme endogène d’accumulation-relaxation ?**

L’intuition de départ est que l’exposant de concavité productive $\gamma$ peut
fournir ce degré de liberté en modifiant simultanément la production, les
rendements marginaux et le service des intérêts. C’est une hypothèse de
recherche forte, pas la réponse contenue dans la question. Détermine ce qu’elle
explique, ce qu’elle n’explique pas et, si elle est insuffisante, quelle
modification structurelle simple et défendable permet d’aller plus loin.

Dans tous les cas, ne confonds pas :

- un changement de l’exposant de queue ;
- un déplacement de la coupure de taille finie ;
- une variation du taux de mortalité ou du rapport de branchement ;
- un changement d’échelle du capital ;
- une extinction, une croissance non stationnaire ou une censure numérique.

Ne présume ni que l’effet recherché existe, ni qu’il est monotone, ni que
$\gamma$ est l’unique levier pertinent. Un résultat négatif correctement établi
est un résultat scientifique valide. En revanche, ne t’arrête pas au premier
échec local : si les mesures révèlent une piste causale solide, formule-la,
teste-la et accepte une refonte audacieuse lorsqu’elle apporte une réponse plus
simple ou plus profonde à la question.

Le modèle et le programme s’appellent exclusivement **M4.2**. Les mentions de
« M5 » dans certains documents antérieurs sont une ancienne nomenclature et ne
doivent pas être reprises.

## Résultat attendu

Livre un moteur M4.2 autonome, testé et reproductible, ainsi qu’une étude
scientifique permettant de répondre clairement aux questions suivantes :

1. Dans la réduction minimale de départ, la pente des avalanches dépend-elle de
   $\gamma$ ?
2. Cette dépendance survit-elle aux graines, aux fenêtres temporelles, aux
   horizons et aux tailles de système ?
3. Relève-t-elle de la concavité elle-même, du changement d’échelle productive,
   des intérêts, de la démographie ou de la structure du réseau de crédit ?
4. Quelle plage de pentes est accessible sans quitter un régime stationnaire et
   sans effondrement systémique ?
5. Si $\gamma$ seul ne suffit pas, quel mécanisme supplémentaire minimal rend
   la pente pilotable sans calibration statistique ad hoc ?
6. Quelles prédictions analytiques simples rendent les résultats intelligibles ?

Commence par inspecter les sources, formalise le protocole avant les runs de
production, puis exécute le travail de bout en bout. Quand tu as assez
d’informations pour agir, agis.

## Sources de vérité et statut des connaissances

Lis intégralement les sources pertinentes avant de modifier quoi que ce soit :

- `README.md` et `CODEX.md` à la racine du dépôt ;
- `m4_credit_soc_fable/reports/01_soc_final/main.pdf` et sa source LaTeX ;
- `m4_credit_soc_fable/PROMPT_M4_SOC.md`, pour comprendre l’ouverture de la
  recherche qui a permis la refonte réussie de M4 ;
- `m4b_credit_soc_mini/README.md` ;
- `m4b_credit_soc_mini/report/mecanique_m4b.pdf` et sa source LaTeX ;
- `m4b_credit_soc_mini/m4b/`, qui fait foi sur la mécanique exécutée ;
- `recherche/sensibilite_m4b/report/rapport_final.pdf` et sa source LaTeX ;
- le protocole, le journal, les scripts et les résultats de
  `recherche/sensibilite_m4b/` lorsqu’ils sont utiles ;
- l’adaptateur actif de M4B et la documentation de `simulation_lab/` avant toute
  intégration à l’interface.

Traite M4 et M4B comme des références en lecture. Ne les modifie pas. M4B est
une réduction fidèle de la mécanique M4 retenue : ce ne sont pas deux preuves
scientifiques indépendantes.

À chaque étape, distingue explicitement :

- **fait observé** : vérifié dans le code, les données ou un résultat produit ;
- **inférence** : interprétation appuyée sur ces faits ;
- **hypothèse** : proposition encore à tester ;
- **incertitude** : point que les données disponibles ne permettent pas de
  trancher.

En cas de conflit entre un rapport, un commentaire et l’implémentation, le code
exécuté fait foi. Documente le conflit au lieu de le masquer.

## Liberté de recherche et refonte audacieuse

Les résultats de M4 et M4B sont des points de départ empiriques, pas des lois à
respecter. M4 lui-même a réussi parce qu’il a été autorisé à supprimer des
variables d’état, renverser des conclusions antérieures et remplacer des règles
de faillite qui amortissaient les cascades. Adopte le même degré d’exigence et
de liberté.

Commence par construire la réduction minimale définie ci-dessous : elle fournit
une baseline interprétable et le premier test de $\gamma$. Mais si cette
baseline ne rend pas la pente pilotable, tu peux remettre en cause toute règle
qui n’est pas explicitement sanctuarisée, notamment :

- la forme ultérieure de $\eta$ et donc la façon dont l’activité de marché
  croît avec la population ;
- la règle de négociation du taux, à condition qu’elle reste dérivée d’une
  stratégie économique explicite et qu’elle soit comparée à la moyenne
  géométrique ;
- la durée, la fusion ou la structure des contrats ;
- la règle de faillite et le traitement des pertes ;
- l’ordre d’une phase candidate, si son rôle causal est formulé et si elle est
  comparée à la baseline ;
- les variables d’état et les mesures du réseau ;
- toute autre institution dont l’analyse montre qu’elle bloque artificiellement
  la question posée.

Les contraintes réellement sanctuarisées sont :

1. $\gamma$ apparaît dans une fonction productive concave et ses conséquences
   sur les contrats sont dérivées, pas calibrées directement sur les
   avalanches ;
2. le choix des parties d’un contrat se fait dans un pool fixé à deux,
   $k\equiv2$ ;
3. $\eta$ est la fonction explicitement nommée qui régit le nombre de tentatives
   d’appariement à partir de la population admissible ; sa baseline est
   l’identité ;
4. les notations $\eta$, $\xi$, $\gamma$, $\lambda$ et $\tau$ restent
   distinctes ;
5. toute grande avalanche revendiquée doit provenir d’une propagation endogène
   mesurée, pas d’une synchronisation exogène ou d’un effondrement total ;
6. invariants comptables, reproductibilité, traçabilité et honnêteté des tests
   statistiques.

Une refonte radicale n’est pas un permis d’ajouter des mécanismes arbitraires.
Chaque changement doit répondre à une hypothèse, avoir une ablation, être
comparé à la baseline et simplifier ou éclairer l’histoire causale. Ose changer
le modèle lorsque les preuves le demandent ; n’accumule pas des options.

## Héritage scientifique de M4B

M4B possède un capital réel productif $K$, un réseau de créances et de dettes
nominales perpétuelles, des chocs multiplicatifs individuels, une production
concave, un service d’intérêts, une dépréciation réelle et des faillites en
cascade par perte intégrale des créances et destruction du capital résiduel.

La valeur nette de l’entité $i$ reste

$$
\mathrm{NW}_i=K_i+C_i-D_i,
$$

où $C_i$ est le principal total de ses créances et $D_i$ le principal total
de ses dettes. Il n’existe ni dette abstraite d’amorçage, ni récupération, ni
transfert de créances lors d’une faillite.

La configuration centrale héritée est :

$$
\lambda=30,\qquad
\delta=0{,}05,\qquad
\sigma=0{,}25,\qquad
K_0=25.
$$

Dans M4.2, le pool d’appariement est fixé à deux et n’est plus un paramètre :

$$
k\equiv2.
$$

La fonction d’intensité du marché commence à l’identité :

$$
\eta(N)=N.
$$

Commence l’étude de $\gamma$ avec $k=2$ et $\eta(N)=N$ afin d’obtenir une
lecture causale propre. $k=2$ reste fixé. Si $\gamma$ ne suffit pas, ou si les
résultats révèlent un couplage essentiel entre concavité et densité du réseau,
tu peux ensuite proposer et tester des formes non triviales de $\eta$. Sépare
alors strictement l’effet de $\gamma$ à $\eta=\mathrm{Id}$ de l’effet propre et
de l’interaction de $\eta$.

## Définition complète de M4.2

### État et chronologie

Conserve l’ordre constitutif de M4B :

1. naissances de Poisson ;
2. choc multiplicatif individuel ;
3. production ;
4. service des intérêts ;
5. dépréciation ;
6. marché du crédit ;
7. faillites en cascade ;
8. mesures.

Une permutation de ces phases constitue un autre modèle. Ne la fais pas dans
la réduction minimale ; elle reste une refonte candidate si une hypothèse
causale précise la justifie ensuite.

### Production et paramètre $\gamma$

La fonction de production devient

$$
F_\gamma(K)=A K^\gamma,
\qquad 0<\gamma<1,
$$

avec $A=1$ dans la spécification principale. La production est entièrement
retenue dans le capital :

$$
K_i\leftarrow K_i+A K_i^\gamma.
$$

Le cas $\gamma=1/2$ doit retrouver la production de M4B.

Le rendement marginal productif est

$$
m_\gamma(K)=F_\gamma'(K)=A\gamma K^{\gamma-1}.
$$

Utilise une implémentation numériquement sûre à $K=0$, sans introduire une
nouvelle règle économique. Toute tolérance numérique doit être documentée et
testée.

Attention à l’ordre discret : sans choc ni crédit, la production précède la
dépréciation. Le point fixe exact de la mise à jour exécutée satisfait

$$
K=(1-\delta)\bigl(K+A K^\gamma\bigr),
$$

donc

$$
K_{\mathrm{aut}}^*(\gamma)
=
\left(\frac{(1-\delta)A}{\delta}\right)^{\!1/(1-\gamma)}.
$$

Ne remplace pas silencieusement cette relation discrète par son approximation
continue.

### Formation d’une paire

Au début de la phase de marché, définis le pool admissible comme l’ensemble des
entités vivantes n’ayant pas fait défaut pendant le service des intérêts du pas
courant. Ce pool est figé pendant toute la phase.

Chaque round tire uniformément deux identifiants distincts, sans remise à
l’intérieur de la paire. Les rounds sont indépendants entre eux et une même
entité peut participer à plusieurs rounds. Si les deux capitaux diffèrent, la
plus riche devient prêteuse $\ell$ et la plus pauvre emprunteuse $b$. Si le
pool contient moins de deux entités, aucun round n’est exécuté.

### Taux d’intérêt issu de la concavité

Le montant du prêt et le calcul des intérêts doivent rester dérivés de la
stratégie de maximisation du revenu associée à la fonction concave. N’ajoute ni
taux arbitraire, ni prime ad hoc, ni calibration directe sur les avalanches.

Pour une paire $(\ell,b)$, calcule les deux rendements marginaux :

$$
m_\ell=A\gamma K_\ell^{\gamma-1},
\qquad
m_b=A\gamma K_b^{\gamma-1}.
$$

Comme $K_\ell>K_b$ et $0<\gamma<1$, on a $m_\ell<m_b$. La concavité
définit l’intervalle des taux mutuellement avantageux, mais ne sélectionne pas
à elle seule un taux unique.

La réduction minimale de M4.2 conserve comme institution de négociation la
moyenne géométrique :

$$
r_{\ell b}=\sqrt{m_\ell m_b}
=A\gamma(K_\ell K_b)^{(\gamma-1)/2}.
$$

Cette moyenne géométrique est un **choix institutionnel explicite**, et non une
conséquence unique de la concavité. Elle est retenue parce qu’elle est
symétrique, multiplicativement invariante et égalise les distances relatives :

$$
\frac{r_{\ell b}}{m_\ell}
=
\frac{m_b}{r_{\ell b}}.
$$

Elle correspond au milieu de l’intervalle dans l’espace logarithmique des
rendements marginaux. Ne la remplace pas silencieusement. Si tu identifies une
règle de négociation plus pertinente pour $\gamma\ne1/2$, dérive-la à partir
des gains des deux parties, démontre ses propriétés, compare-la à la baseline
géométrique et traite-la comme une hypothèse institutionnelle distincte. La
concavité seule ne suffit jamais à faire passer une convention de négociation
pour un théorème.

### Cible productive et principal du prêt

Au taux $r_{\ell b}$, le capital cible qui égalise rendement marginal et taux
contractuel est

$$
K^*(r_{\ell b})
=
\left(\frac{A\gamma}{r_{\ell b}}\right)^{1/(1-\gamma)}.
$$

Avec la moyenne géométrique précédente, démontre et teste l’identité

$$
K^*(r_{\ell b})=\sqrt{K_\ell K_b}
$$

pour tout $0<\gamma<1$. Le principal transféré reste

$$
q=
\min\!\left(
K_\ell-K^*,
\max(0,K^*-K_b)
\right).
$$

Le transfert

$$
K_\ell\leftarrow K_\ell-q,
\qquad
K_b\leftarrow K_b+q
$$

crée ou augmente le contrat nominal perpétuel $(\ell,b,q,r_{\ell b})$.
Les intérêts dus à chaque pas sont $r_{\ell b}q$. Si une paire orientée
existe déjà, conserve la fusion des principaux et le taux moyen pondéré qui
préserve exactement le flux d’intérêts total.

Conséquence à rendre explicite dans l’analyse : lorsque cette négociation est
conservée, $\gamma$ modifie directement la production et les taux d’intérêt,
mais pas la cible instantanée $\sqrt{K_\ell K_b}$ à capitaux donnés. Les
capitaux, les volumes de crédit et le réseau peuvent néanmoins changer
endogènement au cours du temps.

### Fonction d’intensité du marché $\eta$

Le symbole $\eta$ est réservé exclusivement à la fonction qui transforme la
taille du pool admissible en nombre de tentatives d’appariement.

Définis

$$
N_t^{\mathrm{mkt}}
=
\#\{\text{entités vivantes et sans défaut admises au marché au pas }t\},
$$

puis

$$
R_t
=
\left\lfloor\eta\!\left(N_t^{\mathrm{mkt}}\right)\right\rfloor.
$$

Pour la baseline M4.2 :

$$
\boxed{\eta(N)=N.}
$$

Il y a donc exactement un round par membre du pool admissible. Implémente
$\eta$ comme une fonction clairement identifiée. Ne préjuge pas dès
l’implémentation d’une famille paramétrique compliquée : commence par
l’identité. Une extension ultérieure doit naître d’un résultat scientifique,
pas d’une abstraction anticipée.

$R_t$ est le nombre de **tentatives d’appariement**, non le nombre garanti de
nouveaux contrats distincts. Une tentative peut :

- ne produire aucun prêt ;
- produire une nouvelle arête contractuelle ;
- augmenter et fusionner un contrat déjà présent pour la même paire orientée.

Enregistre séparément : le nombre de rounds, le nombre de transactions
réussies, le nombre de nouvelles arêtes, le nombre de fusions et le volume de
principal échangé.

### Nomenclature sans collision

Dans M4B, le symbole $\eta_i$ a parfois été employé pour le choc aléatoire.
Cette notation est interdite dans M4.2 afin d’éviter toute collision avec la
fonction d’intensité du marché.

Note le choc multiplicatif individuel

$$
\xi_{i,t}\sim
\mathcal N\!\left(-\frac{\sigma^2}{2},\sigma^2\right),
\qquad
K_i\leftarrow K_i e^{\xi_{i,t}},
$$

de sorte que $\mathbb E[e^{\xi_{i,t}}]=1$. Réserve les symboles ainsi :

- $\gamma$ : exposant de concavité productive ;
- $\eta$ : fonction d’intensité du marché ;
- $\xi_{i,t}$ : choc multiplicatif individuel ;
- $\lambda$ : intensité des naissances ;
- $\tau$ : exposant statistique de la distribution des avalanches ;
- $A$ : échelle productive, fixée à un dans le modèle principal.

N’emploie pas $\alpha$ pour désigner simultanément l’échelle productive et
l’exposant d’avalanche.

### Faillites et avalanches

Conserve sans modification de principe la règle M4B : faillite racine en cas
de défaut de service ou de valeur nette négative ; perte intégrale du principal
pour les prêteuses de la morte ; annulation des créances portées par la morte ;
destruction de son capital résiduel ; résolution itérative jusqu’au point fixe.

Une avalanche causale est une composante faiblement connexe du graphe des
arêtes de perte entre entités mortes pendant la même résolution. Conserve les
mesures de taille, volume, nombre de racines, profondeur et génération de
décès.

Ne change pas la définition d’une avalanche pendant l’étude.

## Paramètres scientifiques de M4.2

La configuration publique principale contient :

- $\gamma$, nouveau levier scientifique ;
- $\lambda$, taille du système par le flux de naissances ;
- $\delta$, dépréciation ;
- $\sigma$, volatilité ;
- $K_0$, capital de naissance ;
- la graine et l’horizon d’exécution.

La réduction minimale utilise les règles institutionnelles suivantes :

- $A=1$ dans le modèle principal ;
- $k=2$ ;
- $\eta(N)=N$ ;
- moyenne géométrique des rendements marginaux ;
- prêts nominaux perpétuels ;
- un contrat orienté fusionné par paire ;
- annulation et destruction sans récupération ;
- ordre des phases.

Parmi elles, $k=2$ et la dérivation économique des contrats sont fixés par le
cahier des charges. Les autres forment la baseline à battre ou à expliquer,
pas une grande grille de paramètres à balayer sans hypothèse. Toute institution
remise en cause doit l’être par une expérience ciblée.

## Contrôle indispensable du changement d’échelle

Faire varier $\gamma$ avec $A=1$ modifie simultanément la courbure et
l’échelle du point fixe autarcique. C’est la définition principale demandée,
mais cette confusion doit être mesurée plutôt qu’ignorée.

Après la campagne principale, réalise sur les contrastes de $\gamma$ les plus
informatifs un contrôle d’échelle apparié. Choisis un capital de référence
explicite $K_{\mathrm{ref}}$, puis utilise uniquement dans cette ablation

$$
A_{\mathrm{norm}}(\gamma)
=
\frac{\delta}{1-\delta}
K_{\mathrm{ref}}^{1-\gamma},
$$

afin de conserver le même point fixe discret autarcique. Ce contrôle ne doit
pas devenir un second modèle silencieux ni un paramètre libre. Rapporte
séparément :

- l’effet total de $\gamma$ à $A=1$ ;
- l’effet résiduel de la concavité à échelle autarcique comparable.

Si ce contrôle révèle qu’une conclusion initialement attribuée à la concavité
vient surtout du changement d’échelle, révise la conclusion.

## Implémentation

Crée le moteur et tous les nouveaux matériaux scientifiques dans
`m4_2_credit_soc/`. Une intégration à Simulation Lab peut ajouter le seul
adaptateur minimal nécessaire dans le dossier de découverte des modèles, mais
elle ne doit pas modifier M4B.

Privilégie une implémentation minimale et lisible issue de la mécanique M4B.
N’importe pas le moteur M4B comme dépendance dynamique. Ne transporte pas les
anciennes branches d’ablation. Ne refactorise pas les autres modèles.

Le moteur doit au minimum fournir :

- une configuration sérialisable ;
- un générateur pseudo-aléatoire local et reproductible ;
- les séries macroéconomiques par pas ;
- les trajectoires individuelles nécessaires ;
- les contrats finaux et des instantanés de réseau ;
- la composition détaillée des avalanches ;
- les nouvelles mesures de fonctionnement de $\eta$ ;
- un résumé et des contrôles d’intégrité par run.

Les options d’enregistrement ne doivent pas modifier les trajectoires.

## Vérifications avant toute campagne

Écris et exécute des tests couvrant au minimum :

1. la dérivée $F_\gamma'(K)$ sur plusieurs $\gamma$ ;
2. l’identité $K^*=\sqrt{K_\ell K_b}$ sur une grille de capitaux et de
   $\gamma$ ;
3. l’encadrement $m_\ell<r_{\ell b}<m_b$ lorsque $K_\ell>K_b$ ;
4. la conservation du capital réel pendant un prêt ;
5. la conservation de la valeur nette individuelle au moment du prêt ;
6. la fusion des contrats et la conservation du flux d’intérêts ;
7. $k=2$ et l’absence de ce paramètre dans la configuration scientifique ;
8. $\eta(N)=N$, y compris $N=0$ et $N=1$ ;
9. la distinction entre rounds, transactions, nouvelles arêtes et fusions ;
10. les invariants créances égales aux dettes et absence de contrats orphelins ;
11. la résolution des cascades jusqu’au point fixe ;
12. la reproductibilité par graine ;
13. la neutralité des options de mesure ;
14. la validité des estimateurs statistiques sur données synthétiques.

À $\gamma=1/2$, $A=1$, $k=2$ et $\eta(N)=N$, compare M4.2 à M4B
configuré avec $k=2$, mêmes paramètres et mêmes graines. Vérifie les états,
contrats, intérêts et avalanches pas à pas sur des runs courts. Exige l’égalité
logique et numérique dans les tolérances justifiées. N’ajoute pas de branche de
compatibilité uniquement pour fabriquer une égalité bit à bit si l’ordre
arithmétique générique produit un écart flottant sans conséquence ; documente
et borne cet écart.

Ne lance pas la campagne de production tant que ces contrôles ne sont pas
verts ou que leurs éventuelles exceptions ne sont pas expliquées et jugées
sans incidence scientifique.

## Protocole scientifique

### Pré-enregistrement

Avant les runs de production, écris un protocole daté contenant :

- hypothèses principales et hypothèses nulles ;
- paramètres fixes et variables ;
- grille initiale de $\gamma$ ;
- stratégie adaptative autorisée après les pilotes ;
- graines d’exploration et graines confirmatoires disjointes ;
- horizons, burn-in et tailles de système ;
- métriques primaires et secondaires ;
- méthodes d’ajustement et de comparaison des lois ;
- critères de stationnarité, censure et arrêt ;
- critères de confirmation, d’infirmation et d’indétermination.

Ne modifie pas rétroactivement les critères après avoir vu les résultats. Toute
extension doit être identifiée comme exploratoire ou confirmatoire.

### Campagne pilote

Une grille initiale raisonnable pourrait être

$$
\gamma\in\left\{
\frac13,\ 0{,}4,\ \frac12,\ 0{,}6,\ \frac23
\right\},
$$

à la configuration centrale, avec plusieurs graines et un horizon suffisant
pour détecter rapidement : non-stationnarité, échelles numériques extrêmes,
extinction, saturation, changement massif de durée de vie ou disparition du
crédit.

Cette grille est une suggestion, pas une prescription. Choisis le plan pilote
qui maximise l’information scientifique par unité de calcul. Tu peux resserrer,
étendre ou remplacer la plage après une analyse dimensionnelle et des pilotes,
à condition de documenter la raison avant les runs supplémentaires. Ne choisis
pas les seules valeurs qui donnent le résultat souhaité.

### Campagne de taille finie

Pour les valeurs de $\gamma$ retenues, utilise au moins trois tailles de
système, par exemple

$$
\lambda\in\{10,30,100\},
$$

avec des graines indépendantes, un burn-in explicite et des horizons assez
longs pour stabiliser la démographie et accumuler une statistique suffisante
d’avalanches. Utilise au moins trois graines en exploration et cinq graines
disjointes en confirmation pour les contrastes principaux, sauf impossibilité
de coût précisément documentée.

Ne pool pas les graines pour créer artificiellement une précision élevée. Les
ajustements primaires sont effectués par run ; les effets sont ensuite agrégés
avec leur variabilité inter-graines.

Vérifie la robustesse aux fenêtres $T/8$, $T/4$ et $T/2$, puis double
l’horizon sur les cellules lentes ou centrales retenues.

### Distribution des avalanches

Les singletons sont décrits séparément par leur fréquence. Pour la queue
$s\ge2$, ajuste au minimum :

1. une loi de puissance discrète pure ;
2. une loi de puissance discrète avec coupure exponentielle ;
3. une log-normale discrète correctement renormalisée sur le même support.

La forme principale de taille finie est

$$
p(s\mid\tau,s_c)
\propto
s^{-\tau}e^{-s/s_c},
\qquad s\ge s_{\min}.
$$

Estime conjointement $\tau$, $s_c$ et, lorsque la méthode le permet,
$s_{\min}$. Utilise des vraisemblances discrètes correctement normalisées,
des diagnostics de qualité d’ajustement, des comparaisons à des alternatives et
des incertitudes par bootstrap ou méthode équivalente justifiée. Ne conclus pas
à partir d’une seule régression log-log ni du seul $R^2$.

Rapporte aussi :

- le rapport de branchement $b$ ;
- la fraction racines/taille ;
- la profondeur et le volume des cascades ;
- la susceptibilité $\langle s^2\rangle/\langle s\rangle$ ;
- le maximum et les quantiles élevés ;
- le taux de singletons ;
- le scaling de la coupure et du maximum avec $\lambda$.

### Effet causal de $\gamma$ et ouverture de la recherche

Estime une relation $\tau(\gamma)$ sans supposer qu’elle soit linéaire ou
monotone. Une variation apparente de pente n’est considérée comme robuste que
si :

- le signe et l’ordre de grandeur sont reproduits sur des graines
  confirmatoires disjointes ;
- l’effet ne disparaît pas lorsque la taille du système augmente ;
- il est stable aux fenêtres et horizons raisonnables ;
- il ne vient pas uniquement d’un déplacement de $s_{\min}$ ou de $s_c$ ;
- la famille ajustée reste statistiquement défendable ;
- le système reste stationnaire et non censuré ;
- la différence excède l’incertitude inter-graines et d’ajustement ;
- le contrôle d’échelle permet de dire quelle part vient de la concavité.

Si $\tau$ ne varie pas de façon identifiable mais que $s_c$, $b$, la
démographie ou le réseau varient, établis d’abord que $\gamma$ contrôle ces
grandeurs et non la pente dans la plage étudiée. Demande-toi ensuite quel
verrou mécanique empêche la pente de suivre : invariance de la cible de
capital, plateau du branchement, densité imposée par $\eta=\mathrm{Id}$,
convention de taux, fragmentation des expositions ou autre mécanisme mesuré.
Formule alors un petit nombre de candidats audacieux et teste le plus explicatif.

Tu n’es pas obligé de conclure par « $\gamma$ marche » ou « $\gamma$ ne marche
pas ». Une conclusion plus profonde peut être que la pente dépend d’une
combinaison adimensionnelle, d’un couplage $\gamma$--$\eta$, d’une institution
de contrat, ou qu’elle reste universelle dans toute une classe de modèles. Le
rapport doit laisser les données décider de la forme de la réponse.

### Mécanisme

Relie les résultats aux chaînes causales mesurables :

$$
\begin{aligned}
\gamma
&\longrightarrow \text{production et rendements marginaux}\\
&\longrightarrow \text{taux et service des intérêts}\\
&\longrightarrow \text{durée de vie, exposition et réseau}\\
&\longrightarrow \text{propagation et avalanches}.
\end{aligned}
$$

Cette notation indique un programme de mesure, pas une causalité acquise.
Quantifie chaque maillon avec des observables enregistrées. Utilise des
ablations appariées seulement lorsqu’elles sont nécessaires pour départager
deux mécanismes concurrents ; ne transforme pas le projet en exploration
illimitée.

Vérifie notamment si la modification de $\tau$ éventuelle est mieux expliquée
par les taux d’intérêt, le levier, la concentration des expositions, le nombre
de contrats par tête, le rapport de branchement ou la distribution des pertes
unitaires.

## Résultats négatifs et garde-fous

Documente explicitement :

- cellules éteintes, divergentes, censurées ou numériquement instables ;
- absence de crédit ou marché presque toujours inactif ;
- changements non confirmés ;
- métriques dominées par la variance des graines ;
- lois rejetées ;
- effets dépendant d’une seule taille de système ;
- confusions entre pente et coupure ;
- hypothèses mécaniques infirmées.

Un franchissement du garde-fou de population n’est pas automatiquement une
explosion. Diagnostique la trajectoire avec plusieurs plafonds et ses pentes
avant de conclure. Inversement, ne qualifie pas de stationnaire une trajectoire
simplement arrêtée par le plafond.

## Livrables

Produis au minimum dans l’espace M4.2 :

1. le moteur autonome et son lanceur ;
2. les tests et contrôles de parité ;
3. une spécification mathématique de la mécanique, en LaTeX et PDF ;
4. le protocole pré-enregistré, en LaTeX et PDF ;
5. les scripts de campagne et des manifestes entièrement reproductibles ;
6. les résultats bruts ou leur index traçable ;
7. les scripts d’analyse statistique testés ;
8. des figures lisibles avec sources de données identifiées ;
9. un journal de recherche chronologique ;
10. un rapport préliminaire séparant exploration et confirmation ;
11. un rapport final en LaTeX et PDF ;
12. un résumé Markdown copiable et lisible sans le PDF ;
13. la documentation nécessaire à Simulation Lab si l’intégration est faite.

Chaque figure doit être régénérable. Chaque valeur citée dans le rapport doit
pouvoir être reliée à un manifeste, un run ou une table agrégée. Les unités,
graines, horizons, fenêtres et versions du moteur doivent apparaître dans les
artefacts.

## Organisation du travail avec Claude Fable 5

Travaille de façon autonome sur la durée. Utilise un niveau d’effort élevé si
l’environnement le permet.

Quand tu as assez d’informations pour agir, agis. Ne redérive pas les faits
déjà établis, ne remets pas en discussion une décision prise dans ce prompt et
ne présente pas des options que tu ne poursuivras pas. Si un choix reste
nécessaire, formule une recommandation appuyée sur les contraintes
scientifiques.

Délègue les sous-tâches indépendantes à des sous-agents et continue le travail
pendant leur exécution. Emploie des vérificateurs en contexte frais pour auditer
au minimum :

- la dérivation mathématique ;
- la fidélité de l’implémentation à la spécification ;
- les invariants comptables ;
- le protocole statistique ;
- la traçabilité des chiffres du rapport final.

Interviens si un sous-agent s’écarte du périmètre ou manque de contexte. Les
agents de vérification ne doivent pas simplement reformuler les conclusions de
l’agent principal : ils doivent les confronter aux fichiers, tests et données.

Maintiens une mémoire de recherche compacte. Enregistre les corrections et les
méthodes confirmées avec leur raison, sans recopier ce que le code, les rapports
ou le journal établissent déjà. Mets à jour une note existante plutôt que de
créer un doublon et supprime une leçon devenue fausse.

Ne demande pas à reproduire, exposer ou transcrire un raisonnement interne.
Présente les preuves, calculs, résultats et justifications utiles, pas une
chaîne de pensée privée.

## Bornes d’action

Ne modifie pas M4, M4B, M3 ni leurs résultats. Ne réorganise pas le dépôt. Ne
crée pas de sauvegarde Git défensive, de branche ou de publication distante
sans demande explicite. Ne supprime pas de données existantes.

N’ajoute pas de fonctionnalité, de mécanisme économique, de paramètre, de
refactorisation ou d’abstraction sans rôle dans la question scientifique. Mais
ne confonds pas sobriété et timidité : une refonte radicale est dans le
périmètre lorsqu’une hypothèse articulée et une expérience comparative la
justifient. Ne conçois pas pour des besoins hypothétiques. Valide aux frontières
du système et fais confiance aux invariants internes une fois testés.

Lorsque l’utilisateur décrit un problème, pose une question ou réfléchit sans
demander de changement, fournis une évaluation et arrête-toi. N’applique une
modification que lorsqu’elle est demandée ou qu’elle découle directement de la
mission autonome définie ici.

Ne sollicite l’utilisateur que si le travail exige réellement :

- une action destructive ou irréversible ;
- un changement substantiel de périmètre ;
- une décision scientifique non déterminée par ce prompt ;
- une information que seul l’utilisateur peut fournir.

Dans ce cas, explique le blocage précisément et termine le tour sur la question
nécessaire. Pour les actions réversibles relevant clairement de la mission,
avance sans demander une permission supplémentaire.

## Communication et véracité

Avant chaque annonce de progrès, vérifie chaque affirmation contre un résultat
d’outil obtenu pendant la session. Ne déclare jamais un test, un run, une
figure ou un rapport terminé sans preuve. Si un test échoue, cite fidèlement le
résultat. Si une étape est omise, indique-le. Si un résultat est vérifié,
annonce-le sans hésitation artificielle.

Les messages intermédiaires doivent rester brefs et factuels. Le rapport final
à l’utilisateur doit commencer par le résultat scientifique principal, puis
expliquer les éléments nécessaires à son interprétation. Écris pour une
personne qui n’a pas suivi les appels d’outils : phrases complètes, vocabulaire
réintroduit, pas de raccourcis internes ni de chaînes de flèches non expliquées.

La concision consiste à écarter les détails qui ne changent pas la décision,
pas à comprimer le texte en fragments difficiles à lire.

## Critère d’achèvement

La mission est achevée uniquement lorsque :

- la spécification M4.2 est implémentée et testée ;
- la parité du cas $\gamma=1/2$ avec M4B à $k=2$ est établie ou précisément
  bornée ;
- le protocole a été figé avant la campagne de production ;
- les runs retenus sont exécutés ou comptabilisés comme échecs ou censures ;
- l’effet de $\gamma$ sur $\tau$, $s_c$, $b$, la démographie et le
  réseau est estimé avec incertitudes ;
- si $\gamma$ seul est insuffisant, au moins la meilleure hypothèse
  structurelle issue des mesures a été testée, plutôt que simplement évoquée ;
- le contrôle de changement d’échelle est effectué sur les contrastes
  principaux ;
- les résultats exploratoires sont séparés des confirmations ;
- les résultats négatifs et limites sont consignés ;
- les figures et valeurs du rapport sont traçables et reproductibles ;
- les rapports sont compilés et relus ;
- un vérificateur indépendant a audité les conclusions centrales ;
- le compte rendu final répond à la question ouverte : ce qui permet de
  contrôler la pente, ce qui reste invariant, et par quel mécanisme mesuré.

Avant de terminer, vérifie que ton dernier paragraphe ne soit ni une promesse,
ni un plan, ni une demande de permission pour une action déjà autorisée.
Termine seulement lorsque le travail est accompli ou réellement bloqué par une
information que seul l’utilisateur peut fournir.
