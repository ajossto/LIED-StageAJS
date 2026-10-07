# Prompt de recherche M4.2B — émergence et contrôle des queues de revenus d’intérêt sous contrainte de cascades critiques

## Mission

Conçois, implémente, vérifie et étudie **M4.2B**, successeur expérimental direct de M4.2.

M4.2B poursuit deux objectifs scientifiques **simultanés**.

### Objectif A — distribution des revenus d’intérêt

Étudier la distribution cross-sectionnelle instantanée des **intérêts effectivement perçus** par les entités et construire un régime dans lequel sa **queue supérieure puisse être de type Pareto**, de manière endogène, robuste et statistiquement défendable.

Le **corps** de la distribution n’est pas imposé. Il peut être, selon les mécanismes et les données :

- lognormal ;
- exponentiel ;
- mélange de lognormales ;
- double-Pareto lognormal (DPLN) ;
- lognormal avec raccord Pareto ;
- exponentiel avec raccord Pareto ;
- double-lognormal avec raccord Pareto ;
- ou toute autre famille motivée par les résultats.

En revanche, l’objectif structurel est plus précis pour la partie haute :

> **il doit exister, si le modèle le permet, une région non dégénérée de l’espace des paramètres ou des mécanismes dans laquelle la queue des intérêts perçus soit compatible avec une loi de Pareto sur une plage statistiquement crédible.**

Ne fabrique pas cette queue par construction directe, par tirage exogène d’une loi de Pareto ou par calibration ad hoc sur l’exposant observé. Elle doit émerger de la dynamique économique du modèle.

Si une configuration particulière ne présente pas de queue Pareto, établis-le honnêtement. Le travail consiste alors à déterminer **où**, **quand** et **pourquoi** une queue Pareto apparaît ou disparaît, d’abord en explorant les paramètres du modèle, puis, seulement si nécessaire, en interrogeant explicitement ses mécanismes.

L’objectif n’est pas d’atteindre un exposant numérique fixé à l’avance. L’objectif est de déterminer si l’on peut obtenir un **contrôle de la queue** : une ou plusieurs variables du modèle doivent permettre de déplacer de manière reproductible l’exposant, la plage de scaling ou la transition vers la queue Pareto.

Une relation du type

\[
\theta
\longmapsto
\widehat{\alpha}_{I}
\]

est intéressante si \(\theta\) est un paramètre ou mécanisme économiquement interprétable et si \(\widehat{\alpha}_{I}\) représente réellement une queue Pareto, et non un artefact de coupure, de seuil, de mélange temporel ou de taille finie.

La fonction \(\eta\) est **un objet d’intérêt particulier**, parce qu’elle contrôle l’intensité des tentatives d’appariement et donc potentiellement la densification du réseau de crédit. Mais le travail de M4.2B **n’est pas limité à \(\eta\)**.

### Objectif B — préserver les cascades de faillites en loi de puissance

M4.2B ne doit pas obtenir la distribution recherchée des revenus d’intérêt au prix de la disparition du mécanisme critique hérité de M4/M4B/M4.2.

La **structure en loi de puissance des avalanches de faillites doit rester active** dans le régime final revendiqué.

Il faut donc suivre en parallèle :

- la distribution des tailles d’avalanches ;
- son éventuelle queue en loi de puissance ;
- l’exposant estimé et son incertitude ;
- la coupure de taille finie ;
- le nombre de racines ;
- la profondeur ;
- le rapport de branchement ou diagnostics équivalents déjà employés dans M4.2 ;
- la mortalité et la stationnarité de la population.

Une configuration qui produit une belle queue Pareto des intérêts mais détruit la structure de loi de puissance des cascades n’est **pas** un succès final de M4.2B. Elle peut être un résultat intermédiaire utile, à condition d’être identifiée comme telle et d’expliquer le compromis observé.

Réciproquement, conserver les avalanches critiques sans obtenir de régime à queue Pareto pour les revenus d’intérêt ne répond pas entièrement à la nouvelle question.

### Question générale

La question de recherche devient donc :

> **Quels paramètres et, si nécessaire, quels mécanismes institutionnels de cette société de crédit permettent de faire émerger et de contrôler une queue Pareto des revenus d’intérêt, tout en conservant une dynamique endogène d’accumulation-relaxation et des avalanches de faillites à structure de loi de puissance ? Quel rôle spécifique joue la fonction \(\eta\) dans cette organisation ?**

Les résultats doivent rester :

- reproductibles entre graines ;
- persistants entre snapshots et fenêtres temporelles ;
- robustes à la taille du système ;
- distincts d’un simple changement d’échelle ;
- distincts d’un déplacement de coupure de taille finie ;
- distincts d’une variation de la masse en zéro ;
- distincts d’un transitoire de croissance ;
- compatibles avec une population et une comptabilité non pathologiques ;
- causalement intelligibles.

Un résultat négatif local est valide. Un échec d’une valeur de \(\eta\), de \(\gamma\), de \(K_0\), de \(\sigma\) ou d’un autre paramètre n’est pas une raison pour arrêter la recherche. Cartographie d’abord l’espace pertinent ; si les paramètres ne suffisent pas, formule ensuite des hypothèses sur les mécanismes et teste-les avec des ablations propres.

---

# 1. Sources de vérité

Avant toute modification, lis intégralement les sources pertinentes du dépôt, notamment :

- `README.md` et `CODEX.md` à la racine ;
- les sources de M4 et M4B nécessaires à la compréhension historique ;
- `modeles/m4b_credit_soc_mini/` ;
- le moteur M4.2 actuellement exécuté ;
- la spécification mathématique de M4.2 ;
- le rapport scientifique et les expériences de M4.2 ;
- l’étude analytique du prêt unique comparant cible arithmétique et cible géométrique ;
- les scripts existants produisant les snapshots et distributions instantanées des variables individuelles ;
- les outils existants d’analyse des distributions et des queues ;
- les tests existants ;
- l’adaptateur Simulation Lab si M4.2 y est intégré.

M4, M4B et M4.2 sont des références **en lecture seule**.

Ne modifie pas M4.2 pour fabriquer M4.2B.

Crée un moteur autonome M4.2B, en réutilisant seulement ce qui doit l’être par copie/refactorisation locale raisonnable.

En cas de divergence entre :

1. rapport ;
2. documentation ;
3. commentaire ;
4. code exécuté ;

**le code exécuté fait foi**.

Documente toute divergence scientifiquement pertinente.

À chaque étape, distingue explicitement :

- **fait observé** : vérifié dans le code, les données ou un résultat produit ;
- **inférence** : interprétation appuyée sur ces faits ;
- **hypothèse** : proposition encore à tester ;
- **incertitude** : point que les données disponibles ne permettent pas de trancher.

---

# 2. Modification constitutive de M4.2B : le principal devient arithmétique

M4.2 utilisait une cible de capital géométrique issue de sa règle institutionnelle de prêt.

M4.2B change explicitement cette institution.

Pour deux entités de capitaux avant transaction

\[
K_\ell>K_b>0,
\]

la plus riche est prêteuse \(\ell\) et la plus pauvre emprunteuse \(b\).

Le transfert doit désormais **égaliser leurs capitaux** :

\[
K_{\mathrm{target}}
=
\frac{K_\ell+K_b}{2}.
\]

Le principal est donc exactement

\[
\boxed{
q_A=\frac{K_\ell-K_b}{2}
}
\]

et après transfert :

\[
K_\ell'
=
K_b'
=
\frac{K_\ell+K_b}{2}.
\]

Cette règle n'est pas une approximation et ne doit pas être reformulée comme une utilisation de \(K^*(r)\).

Elle constitue précisément la nouvelle institution M4.2B.

Elle possède une justification économique importante : pour une production strictement concave

\[
F_\gamma(K)=AK^\gamma,
\qquad 0<\gamma<1,
\]

elle maximise

\[
F_\gamma(K_\ell-q)+F_\gamma(K_b+q)
\]

sous conservation du capital des deux parties.

Formalise cette propriété dans la documentation et teste-la.

## Tests indispensables

Vérifie numériquement et analytiquement :

\[
K_\ell'+K_b'=K_\ell+K_b,
\]

\[
K_\ell'=K_b',
\]

\[
q_A=(K_\ell-K_b)/2,
\]

ainsi que la conservation des valeurs nettes immédiatement au transfert compte tenu de la création simultanée de la créance et de la dette nominales.

Compare également automatiquement, sur une grille de couples \((K_\ell,K_b)\), le principal arithmétique au principal géométrique de M4.2.

---

# 3. Le taux d’intérêt est conservé en baseline, mais placé sous surveillance explicite

Pour obtenir une attribution causale propre, conserve initialement **exactement la règle de taux de M4.2**.

Pour

\[
m_\ell=A\gamma K_\ell^{\gamma-1},
\qquad
m_b=A\gamma K_b^{\gamma-1},
\]

le taux reste :

\[
\boxed{
r_{\ell b}=\sqrt{m_\ell m_b}
}
\]

soit

\[
r_{\ell b}
=
A\gamma(K_\ell K_b)^{(\gamma-1)/2}.
\]

Important :

- cette formule détermine **le taux** ;
- elle ne détermine plus **le principal** dans M4.2B ;
- la cible \(K^*(r)=\sqrt{K_\ell K_b}\) de M4.2 n'est donc plus la cible du transfert.

Cette séparation doit être très explicite dans le code, les tests et le rapport.

Le contrat reste nominal et perpétuel.

Le service nominal reste :

\[
c=rq_A.
\]

Conserve initialement la règle existante de fusion des contrats d'une même paire orientée, avec moyenne de taux pondérée par les principaux préservant exactement le service total.

Ne modifie cette règle que dans une ablation ultérieure si des données démontrent qu'elle constitue elle-même un mécanisme déterminant de concentration des intérêts.

## Le taux n’est pas supposé neutre

Le passage de la cible géométrique au principal arithmétique augmente structurellement le principal et peut donc augmenter fortement le service contractuel \(rq\), même si le taux \(r\) est inchangé.

Le taux, le principal et leur produit doivent donc être considérés comme un triplet de diagnostics de premier rang :

\[
r,\qquad q,\qquad rq.
\]

Pour chaque configuration, mesure au minimum les distributions de :

\[
r_{\ell b},
\qquad
q_{\ell b},
\qquad
r_{\ell b}q_{\ell b}.
\]

Au moment de la création ou fusion d’un contrat, mesure également :

\[
\frac{r_{\ell b}q_{\ell b}}{K_b'},
\qquad
\frac{r_{\ell b}q_{\ell b}}{F_\gamma(K_b')},
\]

où \(K_b'\) est le capital de l'emprunteuse immédiatement après transfert.

Mesure aussi, par entité :

- service total dû ;
- service dû / capital ;
- service dû / production du pas ;
- taux moyen pondéré des dettes ;
- taux maximum porté ;
- nombre de contrats ;
- fraction des défauts directement associés à une incapacité de service.

### Recherche d’anomalies

Recherche explicitement les régimes où la règle de taux produit des comportements économiquement ou dynamiquement pathologiques, notamment :

- taux extrêmement élevés pour les petits capitaux ;
- service d'un nouveau prêt comparable ou supérieur au capital de l'emprunteuse ;
- service très supérieur à sa production ;
- défaut presque immédiat après création du contrat ;
- concentration de la queue des intérêts dans quelques contrats à taux extrême ;
- dépendance excessive des résultats au plancher numérique utilisé pour calculer le rendement marginal.

Ne pose pas de plafond arbitraire sur \(r\) dans la baseline.

Si ces diagnostics révèlent une pathologie réelle, traite la règle de taux comme une **institution candidate à l'ablation**.

Formule alors une ou plusieurs règles alternatives économiquement dérivées, puis compare-les à la moyenne géométrique à principal arithmétique identique.

Toute alternative doit :

- rester économiquement interprétable ;
- être dérivée d'une règle de partage ou de négociation explicite ;
- ne pas être calibrée pour produire un exposant statistique particulier ;
- être testée avec une ablation propre.

Le but est de savoir si le contrôle éventuel de la queue vient de \(\eta\), de la règle de taux, du principal, ou de leur interaction.

---

# 4. Régime principal : dépréciation et chocs faibles

M4.2B doit fonctionner dans un régime où la dynamique exogène individuelle est beaucoup plus lente que dans M4.2.

## Dépréciation principale

Utilise :

\[
\boxed{\delta=0.01}
\]

soit **1 % de dépréciation par pas**.

## Chocs

Conserve la convention de M4.2 :

\[
\xi_{i,t}
\sim
\mathcal N
\left(
-\frac{\sigma^2}{2},
\sigma^2
\right),
\qquad
K_i\leftarrow K_i e^{\xi_{i,t}}.
\]

La baseline de M4.2B est :

\[
\boxed{\sigma=0.01}.
\]

Ce choix correspond à une volatilité logarithmique de 1 % par pas et produit des variations multiplicatives typiques de l'ordre de 1 %.

Ne recalibre jamais \(\sigma\) sur les distributions de queue obtenues.

Avant la campagne scientifique, vérifie sur un grand échantillon de chocs la distribution de

\[
e^\xi-1
\]

et rapporte :

- moyenne ;
- écart-type ;
- moyenne absolue ;
- médiane absolue ;
- quantiles 5 %, 50 %, 95 %.

Le but de cette vérification est descriptif uniquement.

---

# 5. Échelles, stationnarité et liberté sur \(K_0\)

La dynamique autarcique exécutée satisfait :

\[
K=(1-\delta)(K+AK^\gamma),
\]

donc :

\[
K_{\mathrm{aut}}^*
=
\left(
\frac{(1-\delta)A}{\delta}
\right)^{1/(1-\gamma)}.
\]

Avec

\[
\delta=0.01,\qquad A=1,\qquad \gamma=\frac12,
\]

on obtient :

\[
K_{\mathrm{aut}}^*=9801.
\]

Cette échelle est nettement supérieure au \(K_0=25\) historique. Elle doit être comprise avant toute interprétation statistique.

Cependant, **\(K_0\) n’est pas sanctuarisé dans M4.2B**. Il peut parfaitement varier et doit être considéré comme un paramètre scientifique potentiel, notamment parce qu’il contrôle :

- la distance initiale à l’échelle productive endogène ;
- la durée des transitoires ;
- l’échelle des premiers prêts ;
- l’exposition initiale au service des intérêts ;
- la démographie économique des jeunes entités.

Tu peux donc modifier \(K_0\), y compris de manière substantielle, à condition de distinguer :

1. un changement d’échelle ou de temps de relaxation ;
2. un véritable changement de forme des distributions ;
3. un effet durable en régime stationnaire ou quasi-stationnaire.

Ne confonds jamais :

- apparition d'une distribution large ;
- transitoire de croissance vers une nouvelle échelle ;
- régime stationnaire ou quasi-stationnaire ;
- queue Pareto authentique ;
- simple mélange de cohortes à différents âges.

Le cas \(K_0=25\) peut rester une référence de comparaison historique, mais **ne le traite pas comme une contrainte du nouveau modèle**.

De même, \(A=1\) reste une baseline utile. Une variation de \(A\) peut être utilisée pour des contrôles d’échelle explicitement motivés, mais elle ne doit pas masquer un phénomène dynamique.

---

# 6. Variable scientifique centrale : intérêts instantanément perçus

Les outils produisant les distributions individuelles instantanées existent déjà dans le dépôt.

Inspecte-les et **réutilise-les** plutôt que de recréer inutilement une nouvelle infrastructure.

La variable scientifique principale est :

\[
I_{i,t}^{\mathrm{recv}}
\]

= **montant effectivement perçu par l'entité \(i\) pendant le service des intérêts du pas \(t\)**.

Il s'agit du paiement réellement reçu, après éventuel paiement partiel de l'emprunteuse, et non simplement du flux contractuel théorique.

L'objet principal est la distribution cross-sectionnelle observée à des snapshots :

\[
\left\{
I_{i,t}^{\mathrm{recv}}
\right\}_{i\in\mathcal A_t}.
\]

Ne pool pas aveuglément tous les temps pour fabriquer artificiellement une queue.

Commence par les distributions **snapshot par snapshot**.

Les outils existants doivent normalement permettre cela ; adapte-les seulement si nécessaire.

## Masse en zéro

De nombreuses entités peuvent recevoir exactement zéro intérêt.

Cette masse est économiquement informative mais ne doit pas être mélangée à l'ajustement de la queue positive.

Mesure donc séparément :

\[
p_0(t)
=
P(I_{i,t}^{\mathrm{recv}}=0),
\]

et étudie la queue conditionnelle :

\[
I_{i,t}^{\mathrm{recv}}
\mid
I_{i,t}^{\mathrm{recv}}>0.
\]

Une diminution de \(p_0\) n'est pas en elle-même un « étalement de queue ».

---

# 7. \(\eta\) : levier privilégié, mais non exclusif

Dans M4.2,

\[
R_t
=
\lfloor
\eta(N_t^{\mathrm{mkt}})
\rfloor
\]

est le nombre de tentatives d'appariement.

La baseline historique est :

\[
\eta(N)=N.
\]

M4.2B doit porter une attention particulière à \(\eta\), parce qu’elle agit directement sur l’activité de marché et peut modifier :

- la fréquence des rencontres ;
- le nombre de transactions ;
- les fusions de contrats ;
- la densité et la force du réseau ;
- la concentration des créances ;
- l’accumulation des flux d’intérêts ;
- et potentiellement les deux queues qui nous intéressent : revenus d’intérêt et avalanches.

Mais **ne fais pas de \(\eta\) l’unique explication possible**.

La question spécifique est :

> Lorsque le principal égalise les capitaux, comment \(\eta\) transforme-t-elle le réseau de crédit, les principaux, les taux, les flux \(rq\), la distribution des intérêts reçus et la dynamique des cascades ?

Puis :

> Existe-t-il une famille simple de \(\eta\) permettant de déplacer de façon robuste l’exposant ou la plage Pareto de la queue des intérêts, sans faire disparaître la loi de puissance des avalanches ?

Si \(\eta\) a peu d’effet, ou si son effet dépend fortement de \(K_0\), \(\gamma\), \(\lambda\), \(\delta\), \(\sigma\) ou d’un autre paramètre, quantifie cette interaction au lieu de forcer une conclusion centrée sur \(\eta\).

---

# 8. Exploration paramétrique : \(\eta\) en priorité, mais pas seule

Commence par une exploration **interprétable** des paramètres plutôt que par une optimisation opaque ou une énorme grille cartésienne.

La configuration de départ recommandée est :

\[
\gamma=\frac12,\qquad
\delta=0.01,\qquad
\sigma=0.01,\qquad
\eta(N)=N,
\]

avec les autres paramètres hérités de M4.2 comme points de départ, notamment \(\lambda\) et \(K_0\). Cette configuration est une **baseline**, pas une frontière de recherche.

Les paramètres à explorer peuvent notamment inclure :

- \(\eta\) et ses paramètres ;
- \(\gamma\) ;
- \(\lambda\) ;
- \(\delta\) ;
- \(\sigma\) ;
- \(K_0\) ;
- éventuellement \(A\) dans des contrôles d’échelle clairement identifiés ;
- l’horizon et la taille effective du système pour les tests de robustesse.

L’objectif n’est pas de tout balayer uniformément. Utilise des pilotes, diagnostics analytiques, contrastes ciblés et plans adaptatifs pour identifier les régions intéressantes.

## Famille \(\eta\) linéaire à tester tôt

Une première famille naturelle est :

\[
\boxed{
\eta_\rho(N)=\rho N
}
\]

avec \(\rho>0\).

La baseline correspond à \(\rho=1\).

Une grille pilote logarithmique telle que

\[
\rho
\in
\{
0.125,\,
0.25,\,
0.5,\,
1,\,
2,\,
4,\,
8
\}
\]

est une suggestion raisonnable, pas une obligation. Adapte-la aux diagnostics du modèle.

## Familles non linéaires de \(\eta\)

Si les résultats le justifient, teste ensuite des formes où l’élasticité à la population varie, par exemple :

\[
\eta_{\rho,\beta}(N)
=
\rho N_{\mathrm{ref}}
\left(
\frac{N}{N_{\mathrm{ref}}}
\right)^\beta.
\]

Cette normalisation permet de distinguer le niveau d’activité au voisinage de \(N_{\mathrm{ref}}\) de son élasticité à la taille du système.

Mais ne te limite pas à cette famille si les faits suggèrent une autre forme plus simple ou plus pertinente.

## Interactions

Après identification de quelques contrastes solides, teste les interactions les plus plausibles, par exemple :

\[
\eta\times K_0,
\qquad
\eta\times\gamma,
\qquad
\eta\times\sigma,
\qquad
\eta\times\delta,
\qquad
\eta\times\lambda.
\]

Ne transforme pas automatiquement ces interactions en balayage cartésien exhaustif. Choisis les coupes à partir d’hypothèses causales et de résultats pilotes.

---

# 9. Mesurer les mécanismes reliant paramètres, réseau, intérêts et cascades

Pour chaque configuration, ne te contente jamais de tracer une distribution finale.

Mesure la chaîne causale reliant les paramètres à la microstructure puis aux deux phénomènes macroscopiques recherchés.

## Activité du marché

- `mkt_pool` ;
- `mkt_rounds` ;
- transactions réussies ;
- nouvelles arêtes ;
- fusions ;
- volume de principal échangé ;
- taux de succès par round.

## Réseau de crédit

- nombre d'arêtes actives ;
- degré entrant et sortant ;
- nombre de prêteuses/emprunteuses distinctes par entité ;
- force entrante/sortante en principal ;
- concentration des créances ;
- concentration des dettes ;
- âge des contrats si accessible ;
- multiplicité des fusions ;
- distribution des principaux ;
- distribution des taux ;
- distribution des flux contractuels \(rq\).

## Revenus d'intérêt

- fraction d'entités recevant un intérêt strictement positif ;
- moyenne ;
- médiane conditionnelle positive ;
- variance ou coefficient de variation ;
- quantiles élevés ;
- parts reçues par les top 10 %, 1 %, éventuellement 0,1 % si l'échantillon le permet ;
- Gini ou mesures apparentées comme diagnostics ;
- distribution complète ;
- CCDF de la partie positive ;
- seuil d’entrée dans la queue ;
- exposant Pareto lorsque défendable ;
- étendue en décades ou en ratio de la plage de scaling ;
- éventuelle coupure haute.

## Cascades de faillites

Conserve et analyse les mesures M4.2 pertinentes :

- taille des avalanches ;
- volume ;
- nombre de racines ;
- profondeur ;
- générations ;
- taux de mortalité ;
- rapport de branchement ou indicateur équivalent ;
- exposant de queue ;
- coupure ;
- diagnostics de stationnarité et de taille finie.

## Chaîne causale

Une histoire explicative peut prendre la forme :

\[
\begin{aligned}
\text{paramètres}
&\rightarrow \text{activité de marché}
\rightarrow \text{réseau}
\rightarrow (r,q,rq) \\
&\rightarrow \text{revenus d'intérêt}
\rightarrow \text{fragilité et cascades}.
\end{aligned}
\]

Pour \(\eta\), documente particulièrement :

\[
\begin{aligned}
\eta
&\rightarrow \text{fréquence d'interaction}
\rightarrow \text{topologie/forces du réseau} \\
&\rightarrow \text{concentration des créances} \\
&\rightarrow \text{queue des intérêts et propagation des pertes}.
\end{aligned}
\]

Ces chaînes sont des hypothèses de lecture, pas des conclusions à imposer.

---

# 10. Analyse statistique de la distribution des revenus d’intérêt

L’analyse doit séparer clairement :

1. la masse en zéro ;
2. le corps de la distribution positive ;
3. la queue supérieure.

Le **corps** peut appartenir à des familles très différentes. Le **but structurel de M4.2B est qu’une queue Pareto puisse émerger** dans une région robuste du modèle.

Ne décide donc pas de la famille globale à partir d’un simple histogramme log-log.

## Familles candidates

Au minimum, confronte lorsque les données le permettent :

- lognormale ;
- exponentielle ;
- Pareto pure ;
- Pareto tronquée ;
- lognormale + queue Pareto avec seuil/raccord estimé ;
- exponentielle + queue Pareto ;
- mélange de deux lognormales + queue Pareto ;
- double-Pareto lognormal (DPLN) ;
- autres mélanges ou distributions composites si les diagnostics les motivent.

Le terme « + queue Pareto » signifie une modélisation **spliced / composite** dans laquelle le corps et la queue peuvent obéir à des familles différentes, avec un seuil estimé et testé. N’impose pas un raccord arbitraire uniquement pour obtenir le résultat souhaité.

Une lognormale pure peut parfaitement décrire le corps tout en étant insuffisante pour la partie haute. Inversement, une apparence rectiligne sur quelques points en log-log ne suffit pas à établir une queue Pareto.

## Condition essentielle sur la queue

Pour le régime final revendiqué, recherche une zone où les intérêts positifs présentent une queue compatible avec :

\[
P(I>x)\propto x^{-\kappa}
\]

ou, en convention densité,

\[
p(I)\propto I^{-\alpha}.
\]

Sois parfaitement explicite sur la relation entre \(\kappa\) et \(\alpha\), et ne mélange jamais exposant de CCDF et exposant de densité.

La queue Pareto doit être :

- statistiquement soutenue ;
- suffisamment peuplée ;
- stable sur plusieurs snapshots ;
- stable entre graines ;
- robuste à une variation raisonnable du seuil ;
- observable sur une plage suffisamment large pour être scientifiquement intéressante ;
- meilleure ou au moins compétitive face aux alternatives de queue pertinentes ;
- non expliquée par un mélange de régimes non stationnaires.

Si aucune région de paramètres ne satisfait ces critères, dis-le. Mais avant de conclure à l’échec du modèle, explore les paramètres pertinents et les interactions identifiées par les diagnostics.

## Seuil de queue

Le seuil \(I_{\min}\) ne doit pas être choisi visuellement pour obtenir une pente désirée.

Utilise une procédure reproductible : maximum de vraisemblance, recherche de seuil, bootstrap, comparaison de vraisemblance ou méthodes déjà robustement implémentées dans le dépôt.

Vérifie la stabilité de l’exposant lorsque le seuil varie raisonnablement.

Rapporte au minimum :

- nombre d'observations dans la queue ;
- fraction totale représentée ;
- estimateur de l'exposant ;
- intervalle d'incertitude ;
- seuil ;
- étendue de la plage ajustée ;
- qualité d'ajustement ;
- comparaison aux distributions concurrentes ;
- éventuelle coupure.

## Robustesse temporelle

L'unité naturelle de réplication est le snapshot, pas chaque individu traité comme observation indépendante à travers toute l'histoire.

Étudie :

\[
\widehat{\alpha}_{I,t}
\]

sur une série de snapshots en régime comparable.

Puis compare ces estimations entre paramètres et graines.

Le pooling temporel peut être utilisé comme analyse secondaire seulement si la stationnarité est établie et si son effet sur la queue est explicitement contrôlé.

---

# 11. Définition opérationnelle d’un régime réussi et d’un contrôle de queue

Le mot **contrôle** ne signifie pas atteindre arbitrairement un exposant choisi.

Il signifie qu’un paramètre ou mécanisme économiquement défendable déplace de façon reproductible une propriété de la queue Pareto : exposant, seuil d’entrée, largeur de scaling ou coupure, sans simplement changer l’unité des intérêts.

Considère un contrôle de la queue des intérêts comme établi si plusieurs conditions convergent :

1. une queue Pareto est statistiquement défendable dans les configurations revendiquées ;
2. son exposant ou sa plage varie substantiellement avec le paramètre étudié ;
3. le sens de la variation est reproductible entre graines ;
4. l'effet persiste sur plusieurs fenêtres de snapshots ;
5. suffisamment d'observations appartiennent réellement à la queue ;
6. l'effet ne s'explique pas seulement par un changement de moyenne ou d’échelle ;
7. l'effet ne se réduit pas à une modification de la coupure haute ;
8. l'effet n’est pas seulement une variation de la masse en zéro ;
9. le système reste stationnaire ou quasi-stationnaire au sens pertinent ;
10. le mécanisme causal est compatible avec les diagnostics du réseau, des taux, des principaux et des flux \(rq\).

Mais le **régime final M4.2B** doit en plus satisfaire la contrainte sur les cascades :

11. la distribution des avalanches conserve une structure en loi de puissance robuste ;
12. cette structure n’est pas un artefact d’un effondrement total ou d’une synchronisation exogène ;
13. l’accumulation-relaxation endogène demeure active ;
14. la population et les bilans restent dans un régime scientifiquement exploitable.

Une relation monotone n'est pas obligatoire. Une transition, un optimum intermédiaire, une bifurcation ou une relation non monotone mais reproductible sont des résultats légitimes.

Cherche les **domaines conjointement admissibles** dans lesquels on peut écrire, de manière empirique :

\[
\alpha_I\in\mathcal A_I,
\qquad
\tau_{\mathrm{aval}}
\in
\mathcal A_{\mathrm{aval}},
\]

avec une queue Pareto des intérêts et une queue de loi de puissance des avalanches simultanément observables.

---

# 12. Comparaison indispensable M4.2 / M4.2B

Avant d'attribuer un effet à \(\eta\), compare à paramètres identiques autant que possible :

### M4.2

Principal vers cible géométrique.

### M4.2B

Principal vers moyenne arithmétique.

La règle arithmétique crée structurellement des principaux plus élevés et un levier initial plus important.

Quantifie donc ce qu'elle modifie :

- volume de prêt par transaction ;
- distribution des taux ;
- service \(rq\) créé ;
- durée de vie des contrats ;
- fréquence des défauts ;
- densité du réseau ;
- intérêts reçus ;
- concentration des intérêts ;
- distributions de queue.

Cette comparaison est essentielle pour comprendre pourquoi \(\eta\) pourrait devenir plus ou moins efficace dans M4.2B qu'il ne l'était dans M4.2.

---

# 13. Cartographie des paramètres du modèle

Ne traite pas \(\gamma\) comme un simple contrôle secondaire ni \(\eta\) comme l’unique levier.

L’objectif est d’identifier quels paramètres contrôlent quels aspects de la dynamique.

Parmi les variables à considérer :

- \(\gamma\) : concavité productive et niveau des rendements marginaux ;
- \(\eta\) : intensité et scaling du marché ;
- \(\lambda\) : démographie et taille du système ;
- \(\delta\) : temps de relaxation et échelle productive ;
- \(\sigma\) : intensité des fluctuations individuelles ;
- \(K_0\) : capital d’entrée et distance à l’échelle endogène ;
- \(A\) : surtout comme contrôle d’échelle ou levier si une hypothèse scientifique le justifie.

La baseline \(\delta=0.01,\sigma=0.01\) reste la référence principale demandée, mais tu peux faire varier ces paramètres lorsqu’une étude de sensibilité ou une hypothèse causale le justifie.

Pour chaque paramètre, demande séparément s’il agit principalement sur :

- le corps de la distribution des intérêts ;
- l’apparition de la queue Pareto ;
- l’exposant de cette queue ;
- la coupure ;
- la masse en zéro ;
- la distribution des taux ;
- la distribution des principaux ;
- la topologie du réseau ;
- la fréquence et la taille des cascades ;
- l’exposant des avalanches ;
- la stationnarité.

Utilise des contrôles appariés lorsque plusieurs paramètres changent simultanément l’échelle du capital.

---

# 14. Taille de système, démographie et \(K_0\)

Tout résultat central doit être testé contre des changements raisonnables de taille et de démographie.

Utilise notamment \(\lambda\), l’horizon et les tailles de population effectivement obtenues pour distinguer :

- un véritable exposant asymptotique ;
- une coupure de taille finie ;
- un réseau trop petit pour développer une queue ;
- une queue apparente créée par quelques entités dominantes.

\(K_0\) peut varier librement dans l’étude. Analyse son effet sur les cohortes, les temps de relaxation, les premiers contrats et la forme stationnaire des distributions.

Pour les familles de \(\eta\), teste si le comportement reste cohérent lorsque \(N\) change. Une règle qui ne fonctionne qu’à une taille de population arbitraire n’est pas encore un mécanisme robuste.

---

# 15. Les avalanches restent une contrainte scientifique centrale

Les avalanches ne sont plus l’unique variable cible, mais elles ne sont **pas** un simple diagnostic secondaire.

M4.2B doit préserver un régime dans lequel la distribution des faillites en cascade conserve une **structure en loi de puissance** comparable dans son principe à celle étudiée dans M4/M4B/M4.2.

Conserve la définition causale d’une avalanche et, dans la baseline, la mécanique de faillite de M4.2.

Pour chaque campagne importante, analyse simultanément :

- la distribution des tailles ;
- la CCDF ;
- l’exposant de loi de puissance ;
- le seuil d’ajustement ;
- la coupure éventuelle ;
- les comparaisons avec des distributions concurrentes ;
- la stabilité entre graines et fenêtres ;
- la dépendance à la taille du système ;
- la profondeur et les générations ;
- les racines ;
- le rapport de branchement ou diagnostics apparentés.

Une modification qui épaissit la queue des intérêts mais transforme les avalanches en distribution exponentielle, les éteint presque complètement ou les remplace par des effondrements systémiques synchronisés doit être identifiée comme un **échec au regard du double objectif**, même si elle reste instructive.

Inversement, si un compromis existe entre exposant des revenus d’intérêt et exposant des avalanches, cartographie ce compromis explicitement.

Si une modification des mécanismes de faillite devient scientifiquement nécessaire, elle est autorisée en second temps, mais doit être extrêmement explicite, motivée, comparée à la baseline et accompagnée d’une ablation démontrant ce qu’elle change.

---

# 16. Parcours expérimental suggéré — non contraignant

L’ordre suivant est **une stratégie de départ recommandée**, pas un protocole rigide.

Tu peux réordonner les étapes, revenir en arrière, ajouter une expérience, abandonner une branche ou approfondir immédiatement un mécanisme si les résultats le justifient. Explique simplement pourquoi.

Une trajectoire raisonnable est :

## A — audit et reproduction

Comprendre M4.2, ses tests, ses campagnes, ses snapshots et `simulation_lab`. Reproduire quelques résultats de référence avant de modifier le moteur.

## B — implémentation minimale de M4.2B

Introduire la cible arithmétique du principal, conserver initialement le reste de la mécanique et vérifier les invariants microscopiques.

## C — baseline demandée

Commencer notamment autour de :

\[
\gamma=1/2,
\qquad
\delta=0.01,
\qquad
\sigma=0.01,
\qquad
\eta(N)=N,
\]

avec un \(K_0\) de référence explicite.

Caractériser simultanément :

- capitaux ;
- réseau ;
- \(r,q,rq\) ;
- distribution des intérêts ;
- queue des intérêts ;
- avalanches et leur scaling.

## D — exploration des paramètres

Étudier les paramètres et interactions qui semblent réellement actifs : \(\eta\), \(K_0\), \(\gamma\), \(\lambda\), \(\delta\), \(\sigma\), etc.

Privilégier les contrastes causaux, les plans adaptatifs et les contrôles appariés plutôt qu’une grille exhaustive sans hypothèse.

## E — approfondissement de \(\eta\)

Comme \(\eta\) est un objet d’intérêt particulier, quantifier soigneusement son effet avec des familles simples puis, si nécessaire, non linéaires.

## F — recherche du domaine conjoint

Identifier les régions où coexistent :

1. une queue Pareto des intérêts suffisamment robuste ;
2. une structure de loi de puissance des avalanches ;
3. une dynamique stationnaire ou quasi-stationnaire non pathologique.

## G — mécanismes, seulement si nécessaire ou scientifiquement éclairants

Si les paramètres disponibles ne suffisent pas, ou si les résultats indiquent qu’une institution particulière bloque le phénomène, formuler une hypothèse de mécanisme puis la tester.

Cela peut concerner, par exemple :

- la règle de taux ;
- la fusion ou la mémoire des contrats ;
- la forme de \(\eta\) ;
- la durée des contrats ;
- certaines règles de faillite ;
- l’ordre d’une phase ;
- les règles de sélection ou d’appariement ;
- les variables d’état ou la structure du réseau.

Cette liste n’est pas exhaustive.

## H — robustesse et synthèse

Répéter les résultats importants sur plusieurs graines, horizons, tailles, snapshots et contrôles de paramètres ; produire les mêmes diagnostics graphiques que M4.2 et les nouveaux diagnostics propres à M4.2B.

Ce parcours est une **suggestion de recherche**, pas une interdiction de penser autrement.

---

# 17. Liberté de recherche et refonte justifiée

Tu n'es pas chargé de confirmer une hypothèse ni d’optimiser uniquement \(\eta\).

Tu es chargé de comprendre quels **paramètres** et, si nécessaire, quels **mécanismes** produisent conjointement les phénomènes recherchés.

## Première priorité : exploiter les degrés de liberté déjà présents

Avant une refonte lourde, utilise intelligemment les paramètres existants et leurs interactions. Un résultat où \(K_0\), \(\gamma\) ou \(\sigma\) jouent un rôle plus important que \(\eta\) est parfaitement recevable.

La fonction \(\eta\) reste toutefois un objet de recherche privilégié et doit faire l’objet d’une analyse spécifique, même si elle n’est pas le levier dominant.

## Deuxième temps : modifier les mécanismes si les preuves le demandent

Tu peux effectuer des modifications **importantes, voire lourdes**, du modèle si elles sont nécessaires pour répondre à la question et si elles sont parfaitement justifiées par les résultats précédents.

Une refonte lourde n’est pas un échec du projet. Elle est acceptable lorsqu’elle apporte une explication plus simple, plus robuste ou plus profonde.

Mais chaque modification institutionnelle doit :

1. répondre à une hypothèse scientifique explicite ;
2. être motivée par un diagnostic ou un résultat antérieur ;
3. être comparée à la baseline ;
4. disposer d’une ablation permettant d’isoler son effet ;
5. préserver les invariants comptables ou documenter précisément toute nouvelle comptabilité ;
6. ne pas coder directement une distribution Pareto ou un exposant souhaité ;
7. être évaluée sur **les deux objectifs** : queue des intérêts et cascades.

Tu peux remettre en cause, si nécessaire :

- la règle de taux ;
- la fusion et la durée des contrats ;
- certaines modalités de \(\eta\) ;
- l’appariement ;
- la mémoire ou l’hétérogénéité du réseau ;
- la règle de faillite ;
- l’ordre de certaines phases ;
- les variables d’état ;
- d’autres institutions dont l’analyse montre qu’elles sont causalement déterminantes.

N’accumule pas les modifications. Préfère une refonte motivée et intelligible à une succession d’options arbitraires.

Si un changement permet une queue Pareto des intérêts mais détruit les avalanches en loi de puissance, ou l’inverse, documente ce compromis et poursuis la recherche d’un régime conjoint si cela reste scientifiquement plausible.

---

# 18. Discipline scientifique

Pour chaque affirmation du rapport, distingue :

**Fait observé**  
directement vérifié dans le code ou les résultats.

**Inférence**  
interprétation appuyée par plusieurs faits.

**Hypothèse**  
mécanisme proposé mais pas encore établi.

**Incertitude**  
données insuffisantes pour conclure.

Ne sélectionne jamais après coup uniquement les graines, snapshots, seuils ou plages de \(\eta\) donnant le résultat attendu.

Les pilotes servent à construire le protocole.

Une fois le protocole de production défini, fige-le et conserve également les résultats négatifs.

---

# 19. Efficacité de calcul

La campagne peut devenir coûteuse avec une population élevée et \(\eta(N)>N\).

Avant les runs longs :

- profile le moteur ;
- estime le coût par pas ;
- vérifie la complexité de la phase de marché ;
- évite les copies ou parcours quadratiques inutiles ;
- exploite les scripts de campagne existants ;
- sauvegarde les résultats intermédiaires ;
- rends chaque run reproductible à partir de `config.json` et de la graine.

Les optimisations ne doivent jamais modifier la suite pseudo-aléatoire ou la mécanique sans validation de parité.

---


# 20. Parité graphique avec M4.2 et `simulation_lab`

M4.2B doit produire **les mêmes graphiques de référence que M4.2** pour toutes les observables comparables, en utilisant autant que possible **exactement le code de génération déjà présent dans `simulation_lab`**.

Ne recrée pas approximativement cette batterie de figures.

Commence par inspecter comment `simulation_lab` :

- découvre ou sélectionne un moteur ;
- charge les résultats ;
- construit les snapshots ;
- applique les transformations ;
- appelle les fonctions de tracé ;
- nomme et sauvegarde les figures ;
- expose les paramètres de configuration.

## Exigence de parité

Pour les variables communes à M4.2 et M4.2B, les graphiques doivent conserver autant que possible :

- les mêmes définitions d’observables ;
- les mêmes conventions de snapshots ;
- les mêmes transformations ;
- les mêmes normalisations ;
- les mêmes échelles linéaires ou logarithmiques ;
- les mêmes conventions de binning ;
- les mêmes conventions de CCDF ;
- les mêmes unités ;
- les mêmes diagnostics d’avalanches.

L’objectif est de pouvoir comparer visuellement et quantitativement M4.2 et M4.2B sans ambiguïté méthodologique.

## Réutilisation du code

Le code de génération des graphiques existe déjà. **Lis-le et réutilise-le.**

Si l’architecture de `simulation_lab` prévoit des adaptateurs de modèle, crée ou adapte proprement celui de M4.2B au lieu de dupliquer le moteur de visualisation.

Les résultats sauvegardés doivent permettre de régénérer les figures sans relancer inutilement les simulations.

## Figures supplémentaires propres à M4.2B

La parité M4.2 est un **minimum**. Ajoute les graphiques nécessaires pour la nouvelle question, notamment :

- distributions instantanées des intérêts reçus ;
- densités et CCDF de la partie positive ;
- diagnostics de corps : lognormal, exponentiel, mélanges ;
- diagnostics et fits de queue Pareto ;
- comparaison lognormale-Pareto, exponentielle-Pareto, mélange/DPLN et autres candidats pertinents ;
- estimation du seuil \(I_{\min}\) ;
- exposant Pareto au cours du temps ;
- largeur de la plage de scaling ;
- distributions de \(r\), \(q\) et \(rq\) ;
- relations entre \(\eta\), autres paramètres et exposant de queue ;
- diagnostics de réseau ;
- cartes ou coupes du domaine conjoint « queue Pareto des intérêts + loi de puissance des avalanches » ;
- comparaison des exposants des intérêts et des avalanches lorsque pertinente.

## Validation

Pour une configuration M4.2 de référence, vérifie que le pipeline graphique réutilisé reproduit les sorties attendues de `simulation_lab` avant de considérer l’intégration M4.2B comme fiable.

---

# 21. Livrables

Livre au minimum :

1. un moteur autonome `modeles/m4_2b_credit_soc/` ;
2. une configuration sérialisable complète ;
3. les tests unitaires et d'invariants ;
4. l’intégration ou l’adaptateur nécessaire à `simulation_lab` ;
5. les scripts de snapshots réutilisés ou adaptés ;
6. les scripts d'analyse de distribution et de queue ;
7. le protocole expérimental effectivement retenu et son journal de modifications ;
8. les résultats bruts nécessaires à la reproduction ;
9. toute la batterie de graphiques M4.2 applicable ;
10. les nouveaux graphiques M4.2B ;
11. un tableau synthétique des modèles de distribution comparés pour les intérêts ;
12. un tableau des estimations de queue Pareto par configuration ;
13. un tableau parallèle des statistiques de queue des avalanches ;
14. des diagnostics systématiques de \(r\), \(q\), \(rq\), réseau et stationnarité ;
15. un rapport scientifique complet en LaTeX + PDF ;
16. un README permettant de reproduire les expériences principales.

Le rapport final doit répondre explicitement :

1. Que change la cible arithmétique par rapport à la cible géométrique ?
2. Quelle est la forme du corps de la distribution instantanée des intérêts ?
3. Existe-t-il une queue Pareto robuste des intérêts ? Dans quelles régions du modèle ?
4. Quelle famille globale ou composite décrit le mieux la distribution : lognormale, exponentielle-Pareto, lognormale-Pareto, DPLN, mélange ou autre ?
5. Quel est le domaine accessible des exposants de queue des intérêts ?
6. Quels paramètres contrôlent principalement cette queue ?
7. Quel rôle spécifique joue \(\eta\) ?
8. Quel rôle jouent \(K_0\), \(\gamma\), \(\lambda\), \(\delta\) et \(\sigma\) ?
9. Quel rôle jouent respectivement \(r\), \(q\) et \(rq\) ?
10. La règle de taux géométrique produit-elle des effets pathologiques ?
11. Les avalanches conservent-elles une structure en loi de puissance dans les mêmes régimes ?
12. Existe-t-il un compromis entre la queue des revenus et la criticalité des cascades ?
13. Quel domaine de paramètres satisfait simultanément les deux objectifs ?
14. Les effets survivent-ils aux graines, au temps et à la taille du système ?
15. Quels changements observés relèvent d’un exposant, d’une coupure, d’une échelle, d’une masse en zéro ou d’un transitoire ?
16. Si une refonte du modèle a été nécessaire, quelle hypothèse la justifie et quelle ablation démontre son effet ?
17. Quels éléments restent incertains ?

---

# 22. Comportement agentique attendu

Ce travail est une mission de recherche et d'implémentation de bout en bout.

Inspecte le dépôt avant de coder, notamment M4.2 et `simulation_lab`.

Ne te contente pas de proposer un plan lorsque tu as assez d'informations pour agir.

Effectue les implémentations, tests, pilotes, analyses et runs raisonnablement réalisables dans l'environnement.

Utilise les résultats intermédiaires pour choisir les expériences suivantes. Le parcours expérimental de la section 16 est une **suggestion**, pas une obligation.

Lorsque tu rencontres un résultat surprenant, vérifie d'abord :

- le code ;
- les invariants ;
- l'échelle ;
- la stationnarité ;
- les cohortes et l’effet de \(K_0\) ;
- la distribution des taux ;
- la distribution des principaux ;
- la distribution du service \(rq\) ;
- le choix du modèle statistique pour le corps ;
- le seuil et la robustesse de la queue Pareto ;
- les diagnostics de loi de puissance des avalanches ;
- les effets de taille finie ;

avant de construire une explication économique.

Tu peux demander un document ou rapport supplémentaire uniquement si une information réellement nécessaire n'est ni dans le dépôt ni reconstructible à partir du code.

Sinon, avance de manière autonome.

L'objectif n'est pas de produire beaucoup de simulations ni de maximiser une métrique arbitraire.

L'objectif est de comprendre **comment une société de crédit peut faire émerger et éventuellement contrôler une queue Pareto des revenus d’intérêt tout en conservant des cascades de faillites en loi de puissance**, en exploitant d’abord les paramètres existants puis, si les preuves le demandent, en modifiant explicitement et rigoureusement les mécanismes du modèle.

La fonction \(\eta\) est un levier particulièrement important à étudier, mais elle n’est ni présumée dominante ni exclusive.
