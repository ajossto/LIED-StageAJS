# Proto-article — carnet de commentaires, deuxième passe

## Version de référence

Document : *Effet rebond, émergence et pilotage dans un modèle physique de société de crédit*.

Référence : version du 17 septembre 2026, PDF compilé à 11 h 24 (heure de Paris), 20 pages. Une [copie figée du PDF](revision_2026-09-17/reference/note.pdf) est conservée pour que les repères restent utilisables après les prochaines modifications. Le [PDF de travail](latex/note.pdf) pourra, lui, évoluer.

Les pages ci-dessous indiquent le début des rubriques dans cette version. Si ton impression diffère, donne simplement sa page et les premiers mots du passage ; les titres et citations permettront de retrouver la note.

Empreinte SHA-256 du PDF de référence :

```text
01bd4a19ea0a347372dedff210f6821a564065e8b72ac1fbfb4767a4158b7f02
```

Le [premier carnet rempli](COMMENTAIRES_PROTO_ARTICLE.md) et le [registre des corrections de la première passe](revision_2026-09-15/REGISTRE_CORRECTIONS.md) sont conservés sans remplacement. Ce nouveau carnet ne les annule pas.

## Mode d’emploi et périmètre

Écris librement dans les espaces ci-dessous. Une case vide n’est ni un accord ni une validation. Tu peux ajouter plusieurs remarques dans une rubrique, dupliquer un bloc de passage ou déposer des notes non classées en fin de carnet.

Pour un paragraphe précis, sa page et ses premiers mots suffisent : inutile de compter les paragraphes. Pour un graphique, précise son numéro et, si utile, son panneau ou sa légende. Pour une photographie, indique par exemple « photo 03, marge gauche, flèche du bas ». Les transcriptions incertaines doivent rester signalées.

- Révision à venir exclusivement sur le proto-article, après réception de tes notes.
- Aucune modification du proto-rapport de stage dans cette passe.
- Toutes les remarques sont à examiner aussi pour le futur rapport : pas besoin de les recopier ni de cocher leur pertinence une par une.
- Le champ facultatif « Précision propre au rapport » sert uniquement si tu souhaites une adaptation différente ou plus développée dans le rapport.
- Les notes originales seront conservées ; leur interprétation, les vérifications et les décisions seront consignées séparément. Une correction appliquée à l’article ne sera jamais marquée comme déjà appliquée au rapport.

## Commentaires sur l’ensemble du document

Fil directeur, question physique, articulation avec le travail de stage :

> Un objectif futur est d'adapter ce proto-article à la diffusion académique. Ainsi, il faut prévoir l'eventualité d'une traduction en anglais, allemand. Un travail à faire sur la mise en page et les figures doit commencé à être réfléchi, sans pour autant changer pour le moment l'article. 

Ordre des parties, progression pédagogique et équilibre entre modèle et résultats :

> 

Rigueur scientifique, interprétations, affirmations à nuancer ou à renforcer :

> Attention, à partir d'un tôt moment dans le stage, le paramètre k du bassin de l'apariement de marché a toujours été déclaré à 2. Même si le paramètre n'avait pas disparu du code, il a été officieusement supprimé. Aussi, le travail de retro-compatibilité n'est pas assez précisé. Mis à part la toute dernière version, dont la rêgle de marché à été modifié (cette version devrait s'appeler M5, d'ailleurs) , les M4 sont (sauf erreur de ma part) passé par des test de regression.

Longueur, style, vocabulaire, notations et lisibilité des figures :

> Je vais bientôt avoir fini de retravailler les figures natives de simulation_lab, dont nous pourrons en tirer certaines. Les figures que tu as faites sont bien, mais il serait bon d'en prévoir des versions vectorielles, pour une meilleure intégration et pour une meilleure traductabilité. 
> 
> De plus, la longueur est de 15-20 pages sans les annexes ! On peut penser rajouter des figures là où c'est le plus pertinent. 

Ajouts, suppressions ou déplacements souhaités :

> Rajouter un glossaire par ordre d'apparition des termes techniques et des notations. Rajout de l'étude sur le temps caractéristique du système, CF figures simulation_lab sur le renouvellement du premier décile. Cela sert à s'assurer que les figures finales sont assez éloignée / donc indépendante de la configuration initiale. Cela peut nuancer certains resultats. Attendre la fin de la mise à jour des graphiques et de leur génération dans simulation_lab avant de relancer éventuellement de manière autonome certaines simulations pour compléter les propos et les resultats. 

Attentes particulières pour le futur rapport de stage :

> 

## Sommaire de la version commentée

- Titre et informations liminaires — p. 1
- Résumé — p. 1
- 1 — Introduction : la question physique du stage — p. 1
- 2 — Un modèle physique et comptable minimal — p. 1
  - 2.1 — Construire l'intuition avec quatre entités — p. 1
  - 2.2 — État, comptabilité, invariants — p. 2
  - 2.3 — Un pas de temps — p. 2
  - 2.4 — Stocks, flux et correspondance physique–économie — p. 3
  - 2.5 — Échelles : quels paramètres sont réellement indépendants ? — p. 3
  - 2.6 — Le crédit comme coopération, et le taux comme partage — p. 4
  - 2.7 — Faillite et cascade — p. 5
- 3 — Une démarche expérimentale en trois étapes — p. 5
- 4 — Ce qui émerge sans être imposé — p. 6
  - 4.1 — Une population renouvelée et un réseau de crédit — p. 6
  - 4.2 — Des cascades orientées et une gamme étendue de tailles — p. 6
  - 4.3 — Des contractions courtes, distinctes des avalanches — p. 6
  - 4.4 — Distributions de bilan et d'intérêts : quelle plausibilité ? — p. 8
- 5 — Pilotage : quels leviers changent quelles propriétés ? — p. 8
  - 5.1 — Une hiérarchie de sensibilités, pas un unique bouton de contrôle — p. 8
  - 5.2 — L'intensité des rencontres comme levier expérimental — p. 9
  - 5.3 — Changer une échelle n'est pas toujours changer le système — p. 9
  - 5.4 — La granularité du pas de temps — p. 9
- 6 — Réponse collective à une amélioration technologique — p. 11
  - 6.1 — Ce qui change et ce que mesure l'élasticité — p. 11
  - 6.2 — Une réponse positive mais non proportionnelle — p. 11
  - 6.3 — Une chaîne explicative à tester maillon par maillon — p. 11
  - 6.4 — Les distributions changent avec les cohortes — p. 12
- 7 — L'institution de crédit : un levier complémentaire — p. 13
- 8 — Portée, limites et expériences suivantes — p. 14
- 9 — Conclusion — p. 14
- A — Vérifier le régime étudié et les calculs de réponse — p. 14
- B — Ajustements de distributions : définitions et limites — p. 15
  - B.1 — Masse, densité par classe et fonction de survie — p. 15
  - B.2 — Durées : exponentielle discrète et choix de fenêtre — p. 15
  - B.3 — Le test de Vuong et ce qu'il compare réellement — p. 15
- C — Charge du crédit et pondération du surplus — p. 16
  - C.1 — Définition et mesure du taux de charge — p. 16
  - C.2 — Preuve de l'identité de pondération — p. 17
- D — Compléments de mesure et valeurs tabulées — p. 17
  - D.1 — Rapports de quantiles — p. 17
  - D.2 — Portée temporaire d'une intervention — p. 17
  - D.3 — Plusieurs pertes et causes suffisantes — p. 17
  - D.4 — Stock et production sur une même réalisation — p. 17
- E — Sources locales, configurations et reproductibilité — p. 18
  - E.1 — Trois protocoles, sans fusion des échantillons — p. 18
  - E.2 — Chaque figure et ses fichiers de points — p. 18
- Références — p. 20
- Mention finale « Reproductibilité » — p. 20

## Annotations par rubrique

Les espaces d’une section portent sur toute la partie ; ceux des sous-sections permettent de préciser une remarque locale. Les figures disposent aussi d’espaces dédiés plus bas, sans obligation de répéter les notes.

### Titre et informations liminaires

Repère : `V2-LIM-TITRE` · début p. 1.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

### Résumé

Repère : `V2-LIM-RESUME` · début p. 1.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

### 1 — Introduction : la question physique du stage

Repère : `V2-ART-1` · début p. 1.

Commentaire général :

> enlever "la séparation des stocks et des flux"

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

### 2 — Un modèle physique et comptable minimal

Repère : `V2-ART-2` · début p. 1.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### 2.1 — Construire l'intuition avec quatre entités

Repère : `V2-ART-2.1` · début p. 1.

Commentaire général :

> "même dotation K^° et gamma^°." supprimer "le cercle désigne ... à zéro"

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### 2.2 — État, comptabilité, invariants

Repère : `V2-ART-2.2` · début p. 2.

Commentaire général :

> "les paramètres \lambda, ... " rajouter footnote "Ces paramètres sont explicités en [ref paragraphe]". 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### 2.3 — Un pas de temps

Repère : `V2-ART-2.3` · début p. 2.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### 2.4 — Stocks, flux et correspondance physique–économie

Repère : `V2-ART-2.4` · début p. 3.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### 2.5 — Échelles : quels paramètres sont réellement indépendants ?

Repère : `V2-ART-2.5` · début p. 3.

Commentaire général :

> "...n'est pas une symetrie exacte du marché discret" Il faut mettre l'étude faite pour ce ce fait dans l'article, eventuellement en annexe. 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### 2.6 — Le crédit comme coopération, et le taux comme partage

Repère : `V2-ART-2.6` · début p. 4.

Commentaire général :

> figure 2 : mettre deux technologie avec K ET gamma différents, dont leurs valeurs se croise à un moment donné. Corriger en conséquence la légende. 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### 2.7 — Faillite et cascade

Repère : `V2-ART-2.7` · début p. 5.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

### 3 — Une démarche expérimentale en trois étapes

Repère : `V2-ART-3` · début p. 5.

Commentaire général :

> "DES démarcheS expérimentaleS en PLUSIEURS ETAPES" 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

### 4 — Ce qui émerge sans être imposé

Repère : `V2-ART-4` · début p. 6.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### 4.1 — Une population renouvelée et un réseau de crédit

Repère : `V2-ART-4.1` · début p. 6.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### 4.2 — Des cascades orientées et une gamme étendue de tailles

Repère : `V2-ART-4.2` · début p. 6.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### 4.3 — Des contractions courtes, distinctes des avalanches

Repère : `V2-ART-4.3` · début p. 6.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### 4.4 — Distributions de bilan et d'intérêts : quelle plausibilité ?

Repère : `V2-ART-4.4` · début p. 8.

Commentaire général :

> figure 6: légende : supprimer "Les panneaux disponibles ... 2000" .
> 
> "patrimoine net" préciser valeur nette (Networth, NW en anglais)
> 
> Ce paragraphe fait partie du coeur battant de l'article. 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

### 5 — Pilotage : quels leviers changent quelles propriétés ?

Repère : `V2-ART-5` · début p. 8.

Commentaire général :

> k sera scéllé à 2 après un certain moment. l'étude sur la volatilité du gini en fonction de k n'est pas ultimement pertinent, mais il reste intéréssant pour le rapport de stage. 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### 5.1 — Une hiérarchie de sensibilités, pas un unique bouton de contrôle

Repère : `V2-ART-5.1` · début p. 8.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### 5.2 — L'intensité des rencontres comme levier expérimental

Repère : `V2-ART-5.2` · début p. 9.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### 5.3 — Changer une échelle n'est pas toujours changer le système

Repère : `V2-ART-5.3` · début p. 9.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### 5.4 — La granularité du pas de temps

Repère : `V2-ART-5.4` · début p. 9.

Commentaire général :

> figure 8: légende : supprimer "le dernier panneau... rencontre"

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

### 6 — Réponse collective à une amélioration technologique

Repère : `V2-ART-6` · début p. 11.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### 6.1 — Ce qui change et ce que mesure l'élasticité

Repère : `V2-ART-6.1` · début p. 11.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### 6.2 — Une réponse positive mais non proportionnelle

Repère : `V2-ART-6.2` · début p. 11.

Commentaire général :

> Ce paragraphe fait partie de l'interprétation en tant qu'effet rebond. Il faut mieux préciser ce que fait la compensation (compenser quoi) de K^°. User Kappa à escient. 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### 6.3 — Une chaîne explicative à tester maillon par maillon

Repère : `V2-ART-6.3` · début p. 11.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### 6.4 — Les distributions changent avec les cohortes

Repère : `V2-ART-6.4` · début p. 12.

Commentaire général :

> préciser mieux la transformation A vers A*1.5. Préciser qu'une étude sur des plages de variation plus larges de A et gamma restent à mener. Il faut préciser quelle jeu de paramètre donne 111 pas de moyenne, préciser aussi le médian. 
> 
> figure 13: on veut un pannel sur le NW, mais pas sur le capital. 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

### 7 — L'institution de crédit : un levier complémentaire

Repère : `V2-ART-7` · début p. 13.

Commentaire général :

> figure 14: préciser que le point vert correspond à la règle archaique, et ne sert que de référence illustratrice. 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

### 8 — Portée, limites et expériences suivantes

Repère : `V2-ART-8` · début p. 14.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

### 9 — Conclusion

Repère : `V2-ART-9` · début p. 14.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

### A — Vérifier le régime étudié et les calculs de réponse

Repère : `V2-ART-A` · début p. 14.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

### B — Ajustements de distributions : définitions et limites

Repère : `V2-ART-B` · début p. 15.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### B.1 — Masse, densité par classe et fonction de survie

Repère : `V2-ART-B.1` · début p. 15.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### B.2 — Durées : exponentielle discrète et choix de fenêtre

Repère : `V2-ART-B.2` · début p. 15.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### B.3 — Le test de Vuong et ce qu'il compare réellement

Repère : `V2-ART-B.3` · début p. 15.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

### C — Charge du crédit et pondération du surplus

Repère : `V2-ART-C` · début p. 16.

Commentaire général :

> Supprimer "l'ancienne section... corrigée"

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### C.1 — Définition et mesure du taux de charge

Repère : `V2-ART-C.1` · début p. 16.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### C.2 — Preuve de l'identité de pondération

Repère : `V2-ART-C.2` · début p. 17.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

### D — Compléments de mesure et valeurs tabulées

Repère : `V2-ART-D` · début p. 17.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### D.1 — Rapports de quantiles

Repère : `V2-ART-D.1` · début p. 17.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### D.2 — Portée temporaire d'une intervention

Repère : `V2-ART-D.2` · début p. 17.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### D.3 — Plusieurs pertes et causes suffisantes

Repère : `V2-ART-D.3` · début p. 17.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### D.4 — Stock et production sur une même réalisation

Repère : `V2-ART-D.4` · début p. 17.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

### E — Sources locales, configurations et reproductibilité

Repère : `V2-ART-E` · début p. 18.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### E.1 — Trois protocoles, sans fusion des échantillons

Repère : `V2-ART-E.1` · début p. 18.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

#### E.2 — Chaque figure et ses fichiers de points

Repère : `V2-ART-E.2` · début p. 18.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

### Références

Repère : `V2-REFERENCES` · début p. 20.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

### Mention finale « Reproductibilité »

Repère : `V2-REPRODUCTIBILITE` · début p. 20.

Commentaire général :

> 

Commentaire sur un passage (bloc à dupliquer autant que nécessaire) :

- Page de l’impression / repère sur la photo :
- Premiers mots du paragraphe, citation ou numéro d’équation :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

## Annotations des figures

Les intitulés reprennent la première phrase de chaque légende. Les pages sont celles où les figures apparaissent, pas nécessairement celles où commence leur sous-section.

### Figure 1 — Stock réel et engagement comptable ne sont pas la même chose.

Repère : `V2-FIG-01` · p. 2 · source : `exemple`.

- Panneau / courbe / axe / légende / repère manuscrit :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

> 

### Figure 2 — Technologie et gain de coopération.

Repère : `V2-FIG-02` · p. 4 · source : `art_technologie`.

- Panneau / courbe / axe / légende / repère manuscrit :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

> 

### Figure 3 — Un arbre orienté de propagation, pas le sens du prêt.

Repère : `V2-FIG-03` · p. 5 · source : `cascade`.

- Panneau / courbe / axe / légende / repère manuscrit :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

> 

### Figure 4 — Histogrammes, ajustements et répétitions.

Repère : `V2-FIG-04` · p. 7 · source : `art_avalanches`.

- Panneau / courbe / axe / légende / repère manuscrit :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

> 

### Figure 5 — Durées de contraction : une exponentielle, pas une puissance imposée.

Repère : `V2-FIG-05` · p. 7 · source : `art_cycles`.

- Panneau / courbe / axe / légende / repère manuscrit :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

> 

### Figure 6 — La distribution collective persiste malgré le renouvellement individuel.

Repère : `V2-FIG-06` · p. 8 · source : `art_lorenz`.

- Panneau / courbe / axe / légende / repère manuscrit :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

> 

### Figure 7 — Revenir aux leviers étudiés pendant la construction du modèle.

Repère : `V2-FIG-07` · p. 9 · source : `art_sensibilite`.

- Panneau / courbe / axe / légende / repère manuscrit :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

> 

### Figure 8 — Mesurer le pilotage sur des observables définies.

Repère : `V2-FIG-08` · p. 10 · source : `art_rho`.

- Panneau / courbe / axe / légende / repère manuscrit :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

> 

### Figure 9 — Le changement de pas ne s'arrête pas à trois substitutions.

Repère : `V2-FIG-09` · p. 10 · source : `art_temps`.

- Panneau / courbe / axe / légende / repère manuscrit :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

> 

### Figure 10 — Une même amélioration, deux conventions de naissance.

Repère : `V2-FIG-10` · p. 11 · source : `art_reponse`.

- Panneau / courbe / axe / légende / repère manuscrit :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

> 

### Figure 11 — Définitions, covariations mesurées et mécanismes proposés.

Repère : `V2-FIG-11` · p. 12 · source : `chaine`.

- Panneau / courbe / axe / légende / repère manuscrit :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

> 

### Figure 12 — Lire des positions, pas des groupes fixes.

Repère : `V2-FIG-12` · p. 12 · source : `art_quantiles`.

- Panneau / courbe / axe / légende / repère manuscrit :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

> 

### Figure 13 — Parts par décile de stock productif.

Repère : `V2-FIG-13` · p. 13 · source : `rev_deciles`.

- Panneau / courbe / axe / légende / repère manuscrit :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

> 

### Figure 14 — Le partage agit sur les niveaux, moins sur le Gini de bilan.

Repère : `V2-FIG-14` · p. 13 · source : `art_institutions`.

- Panneau / courbe / axe / légende / repère manuscrit :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

> 

### Figure 15 — Un diagnostic de charge correctement nommé.

Repère : `V2-FIG-15` · p. 16 · source : `art_charge`.

- Panneau / courbe / axe / légende / repère manuscrit :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

> 

### Figure 16 — Observer la différence entre stock et flux.

Repère : `V2-FIG-16` · p. 18 · source : `rev_stock_trajectoire`.

- Panneau / courbe / axe / légende / repère manuscrit :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

> 

## Tableaux, équations et notes de bas de page

Le tableau 1 de stationnarité est p. 15 ; le tableau des rapports de quantiles est en D.1, p. 17 ; les tableaux de protocoles et de sources sont dans l’annexe E, p. 18–19. Pour les équations ou notes de bas de page, indique la page et le numéro ou les premiers mots.

Bloc à dupliquer :

- Repère : `V2-OBJ-01` (puis 02, 03…)
- Page / tableau / équation / note :
- Citation ou repère manuscrit :
- Note manuscrite / modification souhaitée :
- Précision propre au rapport de stage (facultatif) :

> 

## Notes non classées, ajouts et pièces jointes

Une remarque n’a pas besoin d’être rattachée immédiatement au sommaire pour être prise en compte.

Bloc à dupliquer :

- Repère : `V2-LIBRE-01` (puis 02, 03…)
- Page éventuelle / nom du fichier photo ou scan :
- Transcription de la note :
- Passage incertain ou contexte à préciser :
- Modification ou développement souhaité :

> 

## Suivi des décisions et transfert différé vers le rapport

Partie réservée au suivi de la prochaine révision : tu n’as pas à la remplir. À la création de ce carnet, aucune nouvelle annotation n’est encore reçue et aucune révision correspondante n’est appliquée.

Lors de la reprise, chaque remarque recevra un identifiant distinct, rattaché au repère de rubrique ci-dessus. Une copie du carnet rempli sera figée avant traitement. Les notes originales ne seront pas remplacées par mes interprétations.

Pour chaque remarque, le registre de cette deuxième passe consignera :

- La formulation originale et son emplacement, avec lien vers la photo ou le scan éventuel.
- L’interprétation retenue ; toute ambiguïté ou inférence à confirmer.
- Les vérifications effectuées et leurs sources dans le projet.
- La décision pour l’article : appliquée, partiellement appliquée, à vérifier, différée ou non retenue, avec justification.
- Les passages, figures ou calculs effectivement modifiés.
- La portée pour le rapport : à adapter, commune aux deux documents ou strictement propre à l’article, avec justification si elle n’est pas transférable.
- Le contenu à reprendre et l’emplacement cible du rapport, à identifier lors du travail sur celui-ci.
- Le statut de transfert : **non appliqué au rapport de stage**, jusqu’à une demande explicite de travailler sur ce document.
- Le lien éventuel avec les corrections COR-001 à COR-025 de la première passe, sans effacer leurs décisions antérieures.

Une réserve scientifique ou une vérification encore ouverte restera visible dans le suivi du rapport, même si la rédaction de l’article a déjà évolué. Le futur transfert adaptera les changements à la structure et au niveau de détail du rapport ; il ne sera pas un simple copier-coller.
