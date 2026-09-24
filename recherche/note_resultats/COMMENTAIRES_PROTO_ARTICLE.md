# Proto-article — sommaire et carnet de commentaires

## Version de référence et périmètre

Document : *Réponse collective à une amélioration technologique et partage du surplus de coopération dans un modèle multi-agents de crédit*.

Référence : [PDF actuel, 20 pages](latex/note.pdf), révision du 14 septembre 2026, PDF compilé à 13 h 56 (heure de Paris). Les pages indiquées ci-dessous sont celles de ce PDF ; elles indiquent le début des rubriques, pas leur étendue. Si ton impression est antérieure, le titre de rubrique et les premiers mots du passage permettront de retrouver tes annotations malgré une pagination différente.

Ce carnet reprend les titres actuels sans les corriger ni les approuver. Les intertitres non numérotés sont également repris. Le titre, le résumé, les références et la mention finale de reproductibilité ont des espaces dédiés, bien qu'ils ne constituent pas des sections numérotées.

Périmètre convenu :

- Travail exclusivement sur le proto-article.
- Aucune modification de l'article avant réception de tes annotations manuscrites.
- Aucune modification du proto-rapport de stage à ce stade.
- Conserver les annotations originales, les décisions prises et les corrections pertinentes pour le rapport, pour une application ultérieure distincte.

Empreinte SHA-256 du PDF de référence :

```text
385a20e88cd92d95ebb1457b1413d5d7a321c7b8ead3797a862c21220d6105b5
```

## Comment utiliser ce carnet

Tu peux écrire directement sous « Commentaire général » ou « Commentaire sur un passage ». Rien n'est obligatoire : une rubrique vide signifie seulement « pas de commentaire renseigné », jamais une validation tacite.

Pour un paragraphe précis, indique la page de ton impression et ses premiers mots, ou recopie la phrase concernée. Cela suffit ; inutile de compter les paragraphes. Pour une figure, une équation ou un tableau, son numéro ou son intitulé peut remplacer les premiers mots. Tu peux dupliquer le bloc de passage autant que nécessaire.

Si tu transmets des photos ou un scan, tu peux ajouter un repère de la forme « photo 03, marge gauche, flèche du bas ». Toute transcription incertaine restera signalée, sans être transformée en correction acquise.

Les rubriques « Décisions et report différé » en fin de carnet sont destinées au suivi ultérieur ; tu n'as pas à les remplir.

## Commentaires sur l'ensemble de l'article

Fil directeur, place des résultats, ordre des parties, longueur, niveau technique, ton ou lectorat :

> L'article actuel se concentre sur les dernières expériences faites sur le dernier modèle, or, il s'agit de faire un compte rendu sur le travail donné au stage. La question était d'analyser l'effet rebond sous un angle physique, et mon hypothèse est que l'effet rebond peut être expliqué comme un effet endogène de l'organisation de la société, qui s'apparente à un système présentant des tendances auto-critiques. Pour étayer mon hypothèse, j'ai construit un toy modèle. Ses objectifs sont : reproduire une non linéarité dans la réponse macro à une modification micro, et reproduire des classes de distribution plausiblement interprétable comme cohérente dans le monde réel. La question de l'émergence, du pilotage des paramètres endogènes, des analyses de sensibilité en ce sens, de la reconnaissance des classes de distribution, ainsi que les symptômes d'un SOC (essentiellement l'apparition de loi de puissance tronquée dans la taille des avalanches, à mettre explicitement en exemple avec une regression + r^2, mais aussi la loi de puissance dans la durée des récéssions, etc) sont à mettre en avant. Aussi, transformations des paramètres ne changeant pas proportionnellement le comportement du système, travail sur la granularité du pas de temps.  

Éléments à ajouter, supprimer, déplacer ou développer :

> L'article doit pouvoir se lire de manière linéaire. Ainsi, je recommande l'ajout d'une introduction avec le shéma d'un système fictif à 4 ou 5 entitées, comme présent dans '/home/anatole/jupyter/presentation_2_le_retour' pour bien définir les termes et construire l'intuition et la compréhension du modèle. 

Autres remarques :

> Détail mais assez important K_0 devrait être renommé K^°. kappa^°. Pour ne pas confondre avec K_i, capitale de l'entité indice i.  

## Sommaire de la version actuelle

- Titre et informations liminaires — p. 1
- Résumé — p. 1
- 1 — Introduction — p. 1
- 2 — Le modèle — p. 2
  - 2.1 — État, comptabilité, invariants — p. 2
  - 2.2 — Un pas de temps — p. 2
  - 2.3 — Stocks, flux et correspondance physique–économie — p. 2
  - 2.4 — Échelles : quels paramètres sont réellement indépendants ? — p. 3
  - 2.5 — Le crédit comme coopération, et le taux comme partage — p. 3
  - 2.6 — Faillite et cascade — p. 4
- 3 — Protocole — p. 4
- 4 — Ce que le modèle produit de lui-même — p. 4
  - Un régime stationnaire borné. — p. 4
  - Des cascades causales de toutes tailles. — p. 4
  - Et une propagation qu'il faut deux nombres pour décrire. — p. 4
  - Une inégalité qui se loge dans les bilans. — p. 6
- 5 — La réponse à une amélioration technologique — p. 6
  - À portée partielle, l'effet est transitoire. — p. 7
  - À portée globale, l'effet est établi et sous-proportionnel. — p. 7
  - L'écart à la proportionnalité tient à une convention. — p. 7
  - La chaîne, et le statut de chacun de ses maillons. — p. 8
  - La même convention affecte le branchement. — p. 9
- 6 — Les déplacements distributionnels — p. 9
- 7 — Le taux est un partage, et sa moyenne est trompeuse — p. 9
  - 7.1 — Une anomalie — p. 9
  - 7.2 — Une explication réfutée et une identité de pondération — p. 11
  - 7.3 — Ce n'est pas une propriété de la campagne — p. 12
- 8 — Plusieurs causes, rarement chacune suffisante — p. 13
- 9 — Ce qui ne bouge pas — p. 13
- 10 — Limites — p. 14
  - Les queues lourdes ne vivent que dans les bilans, et leur famille n'est pas tranchée. — p. 14
  - Autres réserves. — p. 14
- 11 — Questions ouvertes et expériences discriminantes — p. 16
  - Hétérogénéité du trio $(K_0,A,\gamma )$. — p. 16
  - Causalité entre pas et hypothèse de criticité. — p. 16
  - Sur-altruisme et temporalité du contrat. — p. 16
  - Distributions et comparaison empirique. — p. 16
- 12 — Conclusion — p. 16
- A — Stock et flux : un contrôle illustratif historique — p. 17
- B — Configurations, figures et données de reprise — p. 18
  - B.1 — Configurations de lecture — p. 18
  - B.2 — Chaque figure, sa source et son protocole — p. 18
  - B.3 — Runs M4B des nouveaux graphiques de stock — p. 19
  - B.4 — Répertoire des configurations M4.4 — p. 19
  - B.5 — Reproduire et interpréter les incertitudes — p. 20
- Références — p. 20
- Mention finale « Reproductibilité » — p. 20

## Annotations par rubrique

Les blocs ci-dessous suivent l'ordre du texte. Les commentaires d'une section peuvent concerner toute la section ; ceux d'une sous-section ou d'un intertitre peuvent rester strictement locaux.

### Titre et informations liminaires

Repère : `LIM-TITRE` · début p. 1.

Commentaire général :

> Enlever "campagnes ... vérifications... rédaction... ""

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

### Résumé

Repère : `LIM-RESUME` · début p. 1.

Commentaire général :

> Le résumé est à retravailler. Il n'est absolument pas compréhensible tel quel. 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

### 1 — Introduction

Repère : `ART-1` · début p. 1.

Commentaire général :

> Le début du paragraphe est excellent, jusqu'à émerger. 
> 
> Néanmoins on parle trop vite de "position de bilan", "technologie" sans avoir défini ces termes en amont. L'exemple introductif permettra de modifier cela. 
> 
> --le système "subit"-- c'est à dire "subir" ? 
> 
> Une fois l'axe de l'article retravaillé (voir notes globales), parler du travail de pilotage. 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

### 2 — Le modèle

Repère : `ART-2` · début p. 2.

Commentaire général :

> Pas mal du tout. préciser les variables qui sont rattachées aux entités de celles qui sont globales pour toutes les entitées. sigma est un paramètre global, mais le choc est individuel. Préciser que la dépréciation delta symbolise l'errosion temporelle et ainsi marque la granularité de la discrétisation de la simulation. 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

#### 2.1 — État, comptabilité, invariants

Repère : `ART-2.1` · début p. 2.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

#### 2.2 — Un pas de temps

Repère : `ART-2.2` · début p. 2.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

#### 2.3 — Stocks, flux et correspondance physique–économie

Repère : `ART-2.3` · début p. 2.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

#### 2.4 — Échelles : quels paramètres sont réellement indépendants ?

Repère : `ART-2.4` · début p. 3.

Commentaire général :

> Il faut expliquer avec des mots le sens de K_eq et kappa_0. 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

#### 2.5 — Le crédit comme coopération, et le taux comme partage

Repère : `ART-2.5` · début p. 3.

Commentaire général :

> Faire un figure avec deux fonctions d'extraction selon deux technologies différentes, Illustrer par un shéma le gain concave à un prêt. Expliquer la technologie, analogie "A est la puissance de la technologie, gamma est sa proportion a la colaboration"

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

#### 2.6 — Faillite et cascade

Repère : `ART-2.6` · début p. 4.

Commentaire général :

> Faire un shéma illustratif avec un arbre ORIENTE d'un exemple simple avec un système simple. 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

### 3 — Protocole

Repère : `ART-3` · début p. 4.

Commentaire général :

> 1132.5112 --> \apprxeq 1132. Le protocole n'est pas assez introduit. Qu'est ce qu'on cherche ? Pourquoi ? Après le retravail du fond de l'article, changer ce paragraphe entièrement. 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

### 4 — Ce que le modèle produit de lui-même

Repère : `ART-4` · début p. 4.

Commentaire général :

> Mieux expliquer la nature des changements dans les technologies 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation : figure 1 : Mettre un histogramme log log pour mieux voir les données (points avec barres d'incertitude, faire apparaitre les regressions loi de puissance tronquées avec droite + indice pente, et r^2 de regression. Test : la coupure se situe au niveau qui minimise la variance bootstrap de l'exposant en produit avec son r^2. Ce  n'est qu'une suggestion, tu peux faire autrement.)

figure 2: idem que figure 1 pour la partie gauche, expliquer que gauche est un cas particulier de la figure de droite

- Commentaire / modification souhaitée :

#### Un régime stationnaire borné.

Repère : `ART-4-INT-1` · début p. 4.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

#### Des cascades causales de toutes tailles.

Repère : `ART-4-INT-2` · début p. 4.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

#### Et une propagation qu'il faut deux nombres pour décrire.

Repère : `ART-4-INT-3` · début p. 4.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

#### Une inégalité qui se loge dans les bilans.

Repère : `ART-4-INT-4` · début p. 6.

Commentaire général :

> La comparaison entre des ginis est impértinente. Comparer les ginis NW et intérêts reçus avec des données réelles capital (ici NW) et revenus (ici intérêts reçus), citer article. 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation : figure 4 : rajouter des instantané à 1000,2000,8000 si possible. 
- Commentaire / modification souhaitée :

### 5 — La réponse à une amélioration technologique

Repère : `ART-5` · début p. 6.

Commentaire général :

> Expliquer le détail des calculs et ce qu'ils représentent. Utiliser les notes de bas de pages si besoin. 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

#### À portée partielle, l'effet est transitoire.

Repère : `ART-5-INT-1` · début p. 7.

Commentaire général :

> La portée partielle n'est pas un resultat primaire. C'est un coup d'épée dans l'eau. 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

#### À portée globale, l'effet est établi et sous-proportionnel.

Repère : `ART-5-INT-2` · début p. 7.

Commentaire général :

> Pas de références aux "macro historiques" l'article se considère de manière autonome. explication d'où vient le ln(1.5). Marquer en gras que la réponse n'est pas proportionnelle. Eventuellement rechercher une combinaison où la réponse est négative. (Nouvelles simulations exploratoires)

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

#### L'écart à la proportionnalité tient à une convention.

Repère : `ART-5-INT-3` · début p. 7.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

#### La chaîne, et le statut de chacun de ses maillons.

Repère : `ART-5-INT-4` · début p. 8.

Commentaire général :

> Mieux expliquer la chaine de causalité, la représenter. Le contrôle de stationnarité doit être developpé en annexe. On ne peut pas se permettre de donner des vérités sans justification. 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

#### La même convention affecte le branchement.

Repère : `ART-5-INT-5` · début p. 9.

Commentaire général :

> Mal amené : quel resultat ? On perd le fil de l'article. A voir après la revue du fond de l'article (voir notes globales). Reprendre kappa comme repère. 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

### 6 — Les déplacements distributionnels

Repère : `ART-6` · début p. 9.

Commentaire général :

> Une figure est toujours mieux qu'un tableau (mais le tableau doit être présent en annexe pour avoir les données claires) dévelloper ce paragraphe si besoin pour le rendre plus intélligible. 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

### 7 — Le taux est un partage, et sa moyenne est trompeuse

Repère : `ART-7` · début p. 9.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation : figure 9 : les premiers centiles sont occupés par des entitées jeunes qui sont en train de grossir, elles ne sont pas en "régime permanent" en quelques sortes. L'axe des abscisse n'est pas cohérent et induit en erreur marquer une rupture si il y a une rupture de linéarité ou changer d'échelle. figure 10 : idem 9 pur les naissances, donner en légendes une lecture des données. 

- Commentaire / modification souhaitée :

#### 7.1 — Une anomalie

Repère : `ART-7.1` · début p. 9.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation : figure 11: donner la valeur brute de référence si c'est un rapport (Gini (p=0)=?) L'axe des ordonnées du graphique "capital total" peut démarrer à 0. Tracer les regressions et leurs equations, r^2. Dans ce cas, les catégories peuvent être reliées (par leur régression) car c'est un phénomène continu. 
- Commentaire / modification souhaitée :

#### 7.2 — Une explication réfutée et une identité de pondération

Repère : `ART-7.2` · début p. 11.

Commentaire général :

> Pb de méthodologie, le taux de charge doit, non pas prendre la production mais la production + les intérêts reçus. La pertinence de la section 7.2 est remise en cause. 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation : figure 12: "classe" de capital --> kesako ? Equation 6: prouver l'égalité, potentiellement en annexe. 
- Commentaire / modification souhaitée :

#### 7.3 — Ce n'est pas une propriété de la campagne

Repère : `ART-7.3` · début p. 12.

Commentaire général :

> Introduire la signification du terme service. L'exemple introductif peut y servir. 
> 
> La quasi totalité des contrats se déroulent proche de 0. L'analyse est superflue. 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

### 8 — Plusieurs causes, rarement chacune suffisante

Repère : `ART-8` · début p. 13.

Commentaire général :

> paragraphe "sur ces victimes sur-determinées ..." incompréhensible tel quel. Mieux l'intégrer dans l'article. La partie 8 entière souffre du même commentaire. Potentiellement aussi surperflue. 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

### 9 — Ce qui ne bouge pas

Repère : `ART-9` · début p. 13.

Commentaire général :

> Arbitrage log normale, deux paramètres contre pareto-tronquée aussi deux paramètres. Néanmoins la pareto semble avoir "moins de paramètres" car le paramètre de coupure varie en fonction de la taille du système, donc tend à l'infini vers la même valeur (+ inf). 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation : figure 16 : très bien.  Comparaisson des ginis sur (K) inintéréssant sur (NW) bien plus pertinent. figure 17:  présence évidente de deux population . Annexe : Test de Vuong expliqué, détaillé. La figure peut être superflue.  
- Commentaire / modification souhaitée :

### 10 — Limites

Repère : `ART-10` · début p. 14.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

#### Les queues lourdes ne vivent que dans les bilans, et leur famille n'est pas tranchée.

Repère : `ART-10-INT-1` · début p. 14.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

#### Autres réserves.

Repère : `ART-10-INT-2` · début p. 14.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

### 11 — Questions ouvertes et expériences discriminantes

Repère : `ART-11` · début p. 16.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

#### Hétérogénéité du trio $(K_0,A,\gamma )$.

Repère : `ART-11-INT-1` · début p. 16.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

#### Causalité entre pas et hypothèse de criticité.

Repère : `ART-11-INT-2` · début p. 16.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

#### Sur-altruisme et temporalité du contrat.

Repère : `ART-11-INT-3` · début p. 16.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

#### Distributions et comparaison empirique.

Repère : `ART-11-INT-4` · début p. 16.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

### 12 — Conclusion

Repère : `ART-12` · début p. 16.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

### A — Stock et flux : un contrôle illustratif historique

Repère : `ART-A` · début p. 17.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation : Figure 19 :  régression exponentielle evidente sur le graphique durée de contraction, la formaliser, afficher ses coefficients et r^2. Lien avec article de Wright à souligner.  (regressions are exponential, not power law)
- Commentaire / modification souhaitée :

### B — Configurations, figures et données de reprise

Repère : `ART-B` · début p. 18.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

#### B.1 — Configurations de lecture

Repère : `ART-B.1` · début p. 18.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

#### B.2 — Chaque figure, sa source et son protocole

Repère : `ART-B.2` · début p. 18.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

#### B.3 — Runs M4B des nouveaux graphiques de stock

Repère : `ART-B.3` · début p. 19.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

#### B.4 — Répertoire des configurations M4.4

Repère : `ART-B.4` · début p. 19.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

#### B.5 — Reproduire et interpréter les incertitudes

Repère : `ART-B.5` · début p. 20.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

### Références

Repère : `FIN-REF` · début p. 20.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

### Mention finale « Reproductibilité »

Repère : `FIN-REPRO` · début p. 20.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer au besoin) :

- Page de l'impression / repère manuscrit :
- Début du paragraphe, citation, figure, tableau ou équation :
- Commentaire / modification souhaitée :

## Repères des figures

Ce tableau sert uniquement à retrouver les figures dans l'impression ; leurs pages peuvent différer de celles du texte qui les commente. Les remarques peuvent être inscrites dans la rubrique correspondante ou dans l'espace libre ci-dessous.

| Figure | Page | Début de légende                                                    |
| ------ | ---- | ------------------------------------------------------------------- |
| 1      | 5    | La distribution historique des tailles de cascade.                  |
| 2      | 5    | Voir la pente, puis en mesurer la variabilité.                      |
| 3      | 6    | Il faut deux estimateurs de propagation.                            |
| 4      | 6    | Comparer les observables au même instant.                           |
| 5      | 7    | La réponse dépend de la portée de l'intervention.                   |
| 6      | 8    | Même estimateur, bras distincts ; deux conventions d'échelle.       |
| 7      | 8    | La chaîne de la contraction, maillon par maillon.                   |
| 8      | 9    | Le branchement répond à la convention d'échelle.                    |
| 9      | 10   | Production, bilan et intérêts ne se déplacent pas uniformément.     |
| 10     | 10   | Parts de flux et de stock par décile.                               |
| 11     | 11   | La moyenne contractuelle ne prédit pas à elle seule la démographie. |
| 12     | 11   | L'explication par la convexité ne tient pas.                        |
| 13     | 12   | Compter des contrats ou compter des joules.                         |
| 14     | 13   | La covariance dérivée des fonctions du modèle.                      |
| 15     | 14   | Sur-détermination et suffisance ne se confondent pas.               |
| 16     | 15   | L'intensité de marché déplace ce qu'aucun autre levier ne déplace.  |
| 17     | 15   | Une discrimination non concluante dans ces données.                 |
| 18     | 17   | Une réalisation, deux observables.                                  |
| 19     | 17   | Durées et fréquence des contractions.                               |

Commentaires supplémentaires sur les figures, tableaux ou équations :

- Numéro / intitulé / page :
- Commentaire :

## Notes manuscrites à rattacher

Espace libre pour transcrire une annotation dont l'emplacement ou le sens reste à préciser.

- Photo ou page :
- Transcription, en conservant les éventuelles hésitations :
- Passage probablement visé :
- Point à clarifier :

## Décisions et report différé vers le proto-rapport de stage

À remplir lors du traitement des annotations, sans modifier le rapport. Les commentaires ci-dessus resteront conservés ; une reformulation retenue ne les remplacera pas.

Chaque correction recevra un identifiant stable `COR-001`, `COR-002`, etc. Une correction scientifique, une définition, une convention statistique ou une figure commune sera examinée pour un report. Un changement purement éditorial propre à l'article pourra être marqué « article seulement », avec sa justification. Le report nécessitera une adaptation au contexte du rapport, pas une copie automatique.

Gabarit à dupliquer pour chaque décision :

### COR-___ — À renseigner

- Annotation d'origine : rubrique / citation / page ou photo.
- Demande de l'auteur :
- Interprétation retenue ou point restant à clarifier :
- Vérification nécessaire et sources consultées :
- Modification exacte retenue pour l'article (avant / après, ou résumé précis avec lien vers le passage) :
- Statut article : à clarifier / à vérifier / retenu / appliqué / non retenu.
- Motif de la décision :
- Pertinence pour le rapport : à examiner / à reporter / article seulement.
- Passage cible dans le rapport, lorsqu'il sera identifié :
- Adaptation et vérifications à prévoir pour le rapport :
- Statut du report : non appliqué.
- Date :

À la création de ce carnet, aucune nouvelle correction de l'article ni aucun report vers le rapport n'a été effectué.
