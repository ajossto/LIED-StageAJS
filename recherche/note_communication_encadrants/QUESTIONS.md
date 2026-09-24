# Questions ouvertes sur la note de communication

**Objet :** questions rencontrées en rédigeant `latex/note_encadrants.tex`.
**Règle :** aucune n'a bloqué la rédaction. Chacune indique **l'hypothèse
provisoire retenue**, de sorte que la note soit complète sans la réponse ; la
réponse changera un passage identifié, pas la structure.

Date d'ouverture : 25 août 2026.

---

## Q1 — Le mot « tension » : lequel des deux sens ?

**Question.** La note de consolidation du 24 août laisse ce point explicitement
ouvert (§5, question résiduelle 1). Deux objets portent le même nom :

1. la tension formelle `T = K_aut/K_eq`, qui résume bien les effets d'échelle
   **à `delta` fixé** mais échoue comme paramètre d'état quand `delta` varie ;
2. la chaîne finale de M4.4 : `Gini du bassin → rotation du crédit →
   mortalité par entité → population`.

**Pourquoi cela change la note.** La partie 5 explique *pourquoi* la population
se contracte quand la productivité monte. Selon le sens retenu, cette partie
s'écrit soit comme « la tension d'échelle gouverne », soit comme « une chaîne
en quatre maillons gouverne, et la tension d'échelle n'en est pas un ».

**Hypothèse provisoire retenue, et appliquée.** La section « Définitions » de
la note réserve « tension d'échelle » **au sens 1 uniquement**, avec sa réserve
`delta` fixé en note de bas de page, et nomme le sens 2 « la chaîne ». Motif :
le sens 1 désigne un objet précis avec un échec documenté ; le sens 2 est une
chaîne causale à quatre maillons qui mérite son propre nom.

---

## Q2 — Quel public exactement, et faut-il tout le détail statistique ?

**Question.** « Note de communication à destination de mes encadrants » : les
quatre encadrants sont physiciens (Herbert, Chatzimpiros, Goupil, Brunetton).
Faut-il que la note porte les intervalles de confiance, les tests de Vuong, les
degrés de liberté — ou faut-il les reléguer en annexe ?

**Pourquoi cela change la note.** Cela déplace peut-être un tiers du texte entre
corps et annexe. La structure en parties le permet sans réécriture.

**Hypothèse provisoire retenue.** Je garde **les chiffres dans le corps**, avec
leur incertitude, parce que l'exigence exprimée est l'exhaustivité et parce que
c'est la matière que des physiciens jugeront. Les définitions de notations et de
termes sont regroupées en fin de partie II ; les provenances, la traçabilité par
`run_id` et les références sont en annexe.

---

## Q3 — Faut-il nommer les agents et le mode de travail ?

**Question.** Le mémo de stage traite explicitement le recours aux agents comme
une composante technique du travail (QT-09, QT-37 à QT-40), avec sa chaîne de
contrôle. Cette note en parle-t-elle, et à quel niveau de détail ?

**Pourquoi cela change la note.** C'est une question de présentation du travail
autant que de méthode. Ne pas en parler donnerait une image fausse du volume
produit ; en parler trop déplacerait le sujet.

**Hypothèse provisoire retenue.** J'en parle **en une sous-section de la partie
sur la méthode**, factuelle : ce qui a été délégué, ce qui ne l'a jamais été, et
la chaîne de contrôle par le code, les tests et les figures. Pas d'anecdote.

---

## Q4 — La campagne à technologies hétérogènes : dans le périmètre ou hors ?

**Question.** La note de consolidation pose la question (§9, résiduelle 3) :
la future campagne à `(A_i, gamma_i)` hétérogènes doit-elle apparaître comme
prolongement personnel hors du temps principal du stage ?

**Pourquoi cela change la note.** La partie « suites » se termine soit par un
programme annoncé, soit par une simple liste de possibilités.

**Hypothèse provisoire retenue.** Je la présente comme **la suite naturelle
identifiée, sans statut de calendrier**. C'est vrai indépendamment de la
réponse, et cela n'engage pas.

---

## Q5 — L'anomalie documentaire 153 / 203 runs v2 : la mentionner ?

**Question.** `m4_3live_v2_credit_soc/README.md` annonce 203 runs v2, l'annexe
207, alors que les tables persistées et l'index Simulation Lab en soutiennent
153. La note de consolidation demande de ne pas reprendre 203 sans
qualification.

**Pourquoi cela change la note.** Un encadrant qui ouvrirait le dépôt verrait
les deux nombres.

**Hypothèse provisoire retenue.** Je cite **153**, et je signale l'anomalie en
note de bas de page avec son explication (la liste reprend des campagnes v1).
Motif : c'est exactement le genre de zone d'ombre que la consigne demande de ne
pas cacher.

---

## Q6 — Le nombre de figures dans le corps

**Question.** Quarante-sept figures sont rassemblées. Toutes dans le corps, ou
une sélection dans le corps et le reste en planches d'annexe ?

**Pourquoi cela change la note.** Longueur et rythme de lecture.

**Hypothèse provisoire retenue.** **Toutes dans le corps**, placées au point du
raisonnement qu'elles servent, parce que la consigne est explicite sur ce
point (« je veux absolument que tout soit imagé »). La table de provenance en
annexe permet de retirer une figure sans casser le texte.

---

## Q7 — Faut-il une version anglaise ?

**Question.** Non posée, mais elle se posera si la note circule au-delà du LIED.

**Hypothèse provisoire retenue.** Français. La structure en parties rend une
traduction partielle possible.

---

## Q8 — Le run spécimen de Simulation Lab

**Question.** Les figures individuelles viennent du run `20260718_033746_8b0c5acb`
(M4B au point central, σ = 0,5, k = 2, graine 14). Ce point a σ élevé par
rapport au centre de campagne usuel. Est-ce le spécimen que tu veux montrer,
ou préfères-tu un run à σ plus faible ?

**Pourquoi cela change la note.** Les valeurs annotées sur ces figures
(G = 0,215 pour la taille, G = 0,595 pour les intérêts) sont celles de **ce
run**, et non les valeurs de campagne du point de référence (0,074 et 0,435
pour NW). Les deux jeux coexistent dans la note et je le signale à chaque fois,
mais un lecteur pressé pourrait les confondre.

**Hypothèse provisoire retenue.** Je garde ce run — c'est celui dont la
batterie complète d'analyses existe — et **je marque systématiquement** en
légende qu'il s'agit d'un spécimen à σ = 0,5, distinct du point de référence de
campagne.

---

## Q9 — Le statut de la note vis-à-vis du mémo

**Question.** Le mémo maître (`memo_stage/memo_recherche_complet.md`, v1.7)
s'arrête à M4.3Live-v1 et ne contient ni Live-v2 ni M4.4. Cette note est le
premier document qui les intègre au récit. Faut-il qu'elle soit ensuite
rétro-versée dans le mémo, ou les deux vivent-ils séparément ?

**Hypothèse provisoire retenue.** Je le **signale en préambule** de la note pour
que les encadrants sachent ce qu'ils lisent, et je ne touche pas au mémo.

---

## Q10 — Une figure énergétique des récessions manque

**Question.** Le critère principal de validation des récessions est passé, en
juillet, de la production totale à l'**énergie totale** `E_t = Σ K_i`. Les
métriques ont suivi ; les **figures non**. Le journal de la campagne M4B le
note explicitement : « une figure énergétique dédiée reste à produire ».

**Pourquoi cela change la note.** Les figures `p09` et `p10` de la partie IV
sont tracées sur la production, tandis que les chiffres du même paragraphe
(252,4 récessions par millier de pas, durée 1,930 pas) portent sur l'énergie.
Les deux observables donnent la même image qualitative et des chiffres
différents.

**Hypothèse provisoire retenue.** Je **signale la discordance dans les deux
légendes**, et je donne aussi le chiffre de production (487 épisodes par millier
de pas) pour que la figure ait ses propres nombres. Produire la figure
énergétique est une tâche d'une demi-journée sur les runs existants — dis-moi si
tu la veux, je la fais.

---

## Q11 — Deux mesures de la même élasticité

**Question.** L'élasticité de la production à la productivité, à portée globale
et dotation fixe, vaut **0,7473** dans la lignée v2 (12 graines) et **0,76**
dans M4.3Live-v1 (5 graines, où le bras `new_A150` donne 0,765 ± 0,008).

**Pourquoi cela change la note.** Les deux valeurs y figurent — le résumé donne
la première, le tableau du volet rebond la seconde. Sans explication, cela se
lit comme une contradiction.

**Hypothèse provisoire retenue.** Note de bas de page sous le tableau : deux
campagnes, deux effectifs de graines, écart inférieur à l'incertitude de la plus
petite. Si tu préfères n'en publier qu'une, dis laquelle — je penche pour la v2,
qui a plus de graines et qui est celle que M4.4 prolonge.
