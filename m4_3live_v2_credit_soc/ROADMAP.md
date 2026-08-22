# M4.3Live-v2 — feuille de route

**Origine** : 28 notes manuscrites portées sur
`m4_3live_credit_soc/report/rapport_final.pdf` le 18 août 2026 entre 14 h 23
et 15 h 40. Chaque ligne de cette feuille de route cite la ou les notes dont
elle procède, entre crochets : `[n]` renvoie à la n-ième note dans l'ordre de
lecture du document (extraction complète dans `notes/notes_rapport_final.md`).

**État des notes de conception** : `conception_m4_3live.pdf` ne porte
**aucune annotation sur le disque** — 0 objet `/Subtype/Text`, vérifié par
`pdftk dump_data_annots` et par `mutool show … grep` ; l'horodatage du
fichier est celui de la compilation (13 h 43), antérieur à la première note
du rapport final (14 h 23). Les annotations n'ont vraisemblablement pas été
enregistrées depuis la visionneuse. Cette feuille de route est donc
**incomplète d'un jeu de notes** ; la section §9 lui est réservée et peut
être remplie sans rien réorganiser.

---

## 0. Ce que v2 hérite et ne doit pas refaire

Acquis de M4.3Live, à reprendre tels quels :

| Acquis | Où | Pourquoi le garder |
|---|---|---|
| Parité bit à bit avec M4.3 sur 8000 pas × 26 colonnes | `tests/test_parity_m4_3.py --full` | seule preuve que le fork n'a rien cassé ; **c'est le premier test à repasser après chaque changement de §1** |
| Noyau d'institution (δ\* = h(C) − K, table de Hermite, ordre 4) | `m4_3live/kernel.py` | validé, coût 1,3 % du pas |
| Appariement par graine avec bras `null` | `scripts/campaign.py` | plancher de bruit mesuré, note [12] le valide explicitement |
| Session pilotable + rejeu depuis journal | `m4_3live/live.py` | testé, non remis en cause |
| Import dans `simulation_lab` par lien symbolique | `scripts/import_to_simulation_lab.py` | 203 runs consultables, annexe de traçabilité à 207 lignes |
| Loi d'échelle ε = 1/(1−γ) et rôle de K0 | rapport §5–6 | résultat, pas outil |
| Covariance d'échelle (capital) et covariance de pas de temps | rapport §7.1 et §7.3 | deux groupes qui réduisent le nombre de paramètres libres — à énoncer ensemble en v2, voir §3.4 |

---

## 1. Changements de modèle

Ce sont les seuls chantiers qui justifient un fork. Chacun casse
potentiellement la parité : l'ordre donné plus bas est celui des lots (§7).

### 1.1 Le sens du prêt cesse d'être imposé — `[4] [6] [7]`

**État v1.** Dans chaque paire, la plus riche est prêteuse, la plus pauvre
emprunteuse. Quand l'optimum voudrait faire circuler le capital du pauvre
vers le riche (δ\* ≤ 0), la paire est refusée et comptée dans
`mkt_blocked_dir`.

**Note [4]** : « *C'est dommage. Si l'optimisation convexe donne un sens,
alors c'est celui-ci qui devrait être utilisé. Cette règle n'a pas de sens.* »
**Note [6]** : « *On va derechef faire une autre version où cette loi est
annulée. Abandon de la nomenclature K_ℓ K_b pour lender/borrower, passage à
K_a, K_b.* »

**Changement.** La paire devient non ordonnée `(a, b)`, de capitaux
`K_a, K_b`, `C = K_a + K_b`. Le noyau retourne l'allocation optimale
`K_a* = h(C)` ; le transfert est `δ = K_a* − K_a`, **de signe libre**. Le
prêt va de qui cède vers qui reçoit ; le receveur est le débiteur.

**Conséquences à instrumenter, pas à supposer.**

- `mkt_blocked_dir` tombe à zéro par construction. Le compteur et sa figure
  deviennent vestigiaux — note [24] : « *figure qui sera à terme archaïque.
  On la garde pour le moment.* » Garder le compteur, l'alimenter avec ce
  qu'il aurait valu sous l'ancienne règle (compteur *contrefactuel*), ce qui
  mesure directement combien d'échanges la v1 s'interdisait.
- Le volume de prêt augmente mécaniquement. Toute comparaison v1/v2 sur
  `loan_volume` est donc à faire à protocole appariéo, pas en absolu.
- Un riche à mauvaise technologie peut désormais céder son capital à un
  pauvre à bonne technologie et vivre de l'intérêt. C'est un régime que la
  v1 n'a jamais pu produire : **c'est le résultat attendu du chantier**,
  et il faut lui donner ses propres diagnostics (part du capital détenue par
  les créancières nettes, corrélation technologie/position nette).
- Le plafond de transfert (`transfer_cap`) mordait dans un seul sens ; sa
  sémantique doit être réexaminée pour un δ signé.

**Parité — hypothèse à retester, pas acquise.** En régime homogène,
l'optimum est le partage égal, donc `δ = (K_b − K_a)/2` : la magnitude et
le sens coïncident avec la règle « la plus riche prête ». La parité
bit à bit *devrait* survivre. C'est une **hypothèse** : l'ordre de sommation
et l'ordre d'insertion dans le carnet dépendent de l'ordre du couple, et
c'est exactement le genre de détail qui décale un flottant.
`test_parity_m4_3.py --full` est le premier test à repasser.

### 1.2 Service des intérêts après dépréciation — `[3]`

**État v1.** Ordre des phases : naissances → choc → production → **service
des intérêts** → **dépréciation** → marché → faillites.

**Note [3]** : « *Test à faire, échanger 5 et 6, ça devrait faire augmenter
le taux de défaut.* »

**Changement.** Un champ de configuration `phase_order ∈ {"v1", "deprec_first"}`,
valeur par défaut `"v1"` — la parité doit rester atteignable sans détour.
Sous `"deprec_first"` : dépréciation puis service.

**Prédiction à falsifier.** Le capital disponible au moment de payer est
réduit de (1−δ), donc toute emprunteuse dont le capital était compris entre
`dû` et `dû/(1−δ)` bascule en défaut de liquidité. À δ = 0,03 c'est une
fenêtre étroite : l'effet attendu est **petit et calculable a priori** à
partir de la distribution du ratio capital/dû, qu'il faut donc enregistrer.
Mesurer avant de commenter : c'est un test A/B apparié par graine, coût d'un
seul bras de campagne.

### 1.3 ~~Une portée qui maintient l'intensité de traitement~~ — **ABANDONNÉ**

> **Décision du 21 août 2026, à la demande de l'utilisateur** :
> « *Pour la v2, on se souvient, je ne veux aucun traitement du cas
> partiel.* »

**Ce que cela retire du périmètre v2** :

- la portée `fraction_persistante` proposée ici (elle est annulée, pas
  reportée) ;
- toute campagne à portée `fraction` — plus de bras `frac_*`, donc plus de
  bras `null` apparié, plus d'inversion part ex post → part ex ante, plus de
  correction de cohorte qui s'éteint ;
- la question « le long horizon est-il tranchable ? » posée en portée
  partielle. **Elle ne se pose plus** : v2 mesure en portée globale, où
  l'intensité de traitement vaut 1 par construction et ne dérive pas.

**Ce que cela ne retire pas.** Les résultats v1 obtenus en portée partielle
restent acquis et publiés (§0) ; ils ne sont simplement pas prolongés. Et la
leçon de méthode reste valable si une portée partielle réapparaissait un
jour : un tirage qui consomme le générateur exige un bras `null` qui consomme
exactement les mêmes tirages (note [12]).

**Conséquence pratique** : le lot **G** du séquencement (§7) disparaît, et la
question ouverte n°5 (§10) est tranchée — par la négative.

### 1.4 Une seule borne de transfert : `optimum`

> **Décision du 21 août 2026, à la demande de l'utilisateur** :
> « *Je ne veux plus que `transfer_cap="optimum"`.* »

**Ce qui disparaît.** Le paramètre `transfer_cap` n'a jamais eu que deux
valeurs : `optimum` (l'énoncé littéral de l'institution, δ\* = h(C) − K_b) et
`equalization` (plafond à (K_ℓ − K_b)/2, conservé « en ablation » après le
pilote du 16 août). En v2, `equalization` est retiré :

| À supprimer | Où (référence v1) |
|---|---|
| tuple `TRANSFER_CAPS` et sa validation | `m4_3live/model.py:69, 167-168` |
| champ `transfer_cap` de `Config` | `m4_3live/model.py:144` |
| `cap_at_equalization` et la branche de plafonnement | `m4_3live/model.py:506, 531-536` |
| compteur `mkt_capped` (devient mort) | `_run_market`, colonne de `series.csv` |
| option `--transfer-cap` du CLI | `driver/headless.py:214` |
| champ exposé par l'API locale | `web/router.py:55` |
| pilote de plafond et sa figure `cap_pilot.png` | `scripts/campaign.py:166`, `scripts/conception_evidence.py:309, 348, 723` |
| contrôle d'intégrité « transfer_cap inattendu » | `scripts/analyse.py:249-256` |

**C'est une suppression sans risque, et on peut le prouver.** Sous
`optimum`, la branche n'est simplement jamais exécutée. Vérifié directement :
sur les **164 runs** du dépôt, `mkt_capped` cumulé vaut **exactement 0** —
aucune transaction n'a jamais été plafonnée. La suppression ne peut donc
changer aucun nombre publié, et **la parité bit à bit avec M4.3 doit être
reconduite telle quelle**. C'est la différence avec le §1.1, qui change
réellement le comportement : celui-ci est une amputation de code mort.

**À faire dans le lot A**, avant tout changement de comportement — c'est
précisément le genre de nettoyage qui doit précéder les modifications
mesurables, pour que la parité qui suit porte sur un moteur déjà simplifié.

**Ce que la v1 garde.** Le pilote de plafond et son analyse restent publiés
dans le rapport de conception (§\ref{sec:plafond}) : ils documentent
*pourquoi* le plafond est sans objet — les entités dopées deviennent en
quelques dizaines de pas le côté riche de leurs paires, l'optimum voudrait
alors leur envoyer du capital, et le sens du prêt l'interdit. Le résultat
justifie la suppression, il ne disparaît pas avec elle.

**Question qui devient sans objet** : la n°1 du §10 (« plafonner la valeur
absolue, ou seulement le sens riche → pauvre ? ») ne portait que sur le
comportement du plafond sous δ signé. Sans plafond, elle tombe — mais le
**sens** du transfert reste la question du §1.1, qui elle demeure entière.

---

## 2. Instrumentation et mesure

### 2.1 Métrique de « tension » K_aut / K_eq — `[17] [22]` — **la demande la plus explicite**

**Note [17]** : « *TRÈS IMPORTANT : une nouvelle métrique que j'aimerais
observer est ce que j'appelle la « tension », c'est-à-dire le rapport
K_aut/K_eq […]. J'aimerais que le calcul de ce rapport, ainsi que les graphes
associés de son évolution, soient ajoutés au code Python pour qu'ils soient
générés à chaque nouvelle simulation.* »

Cette demande est **satisfaite dans la v1 sans toucher au moteur** (§8
ci-dessous) : `scripts/tension.py` dérive la tension de `tech_series.csv` et
`series.csv`, donc tout run déjà terminé la produit sans être relancé.

**Ce que v2 doit corriger à la source.** `tech_series.csv` donne
l'effectif de *fin* de pas, alors que la production a été calculée sur
l'effectif d'*avant* les morts. La v1 reconstitue l'effectif producteur par
`n_alive + deaths`, ce qui est **exact tant qu'une seule technologie est
vivante** — donc pour tous les runs de contrôle, d'amorçage, d'ablation et
de loi d'échelle — mais impossible à répartir entre groupes dès qu'il y en a
plusieurs : les bras `fraction` retombent alors sur l'effectif de fin de pas,
ce qui surestime `K_eq` d'environ 5 %. La colonne `basis` de `tension.csv`
dit laquelle des trois bases a servi, run par run et pas par pas.

**Correction v2, deux lignes dans la phase de production** : enregistrer
`n_prod` (effectif producteur) et `K_prod` (leur capital à l'instant de
produire) par technologie dans `tech_series`. `scripts/tension.py` les
consomme déjà si elles existent (`basis = "prod"`) : rien d'autre à écrire.
Cela rend aussi l'écart de Jensen exact, alors qu'il mélange aujourd'hui deux
instants du pas.

Le reste de ce que v2 en hérite :

- `tension` et `K_eq` calculées **en cours de run** et non a posteriori,
  avec la valeur exacte par entité plutôt que reconstituée depuis les
  agrégats ;
- **le résultat du test, à connaître avant de continuer** : la tension a été
  mise à l'épreuve dans la v1 par un balayage à quatre leviers indépendants
  (`K0` seul, `δ` seul, `A` seul, `A`+`K0`), 39 runs, tous appliqués au même
  état. Verdict : **la tension est un excellent paramètre d'état tant que la
  dépréciation ne bouge pas** (109 runs, plage de tension ×15,
  `morts/pop ∝ T^0,668`, R² = 0,9885, écart médian 1,4 %, les trois leviers
  d'échelle d'accord à mieux que 4 %), et **elle échoue sur `δ`** : faire
  varier `δ` d'un facteur 8 déplace la tension d'un facteur 13 et la
  mortalité de 14 % seulement. Deux bras à tension quasi identique
  (`δ=0,04` → T=2,78 et `K0=400` → T=3,12) ont des mortalités dans un
  rapport 3,3.
- **et ce qui, lui, aligne les quatre leviers** : l'intensité de rotation du
  crédit, `loan_volume / K_tot`, avec `morts/pop ∝ (rotation)^1,337`,
  R² = 0,9982, écart médian 0,41 %. C'est une variable **endogène**, donc une
  régularité descriptive et non une loi de contrôle — mais elle désigne le
  canal.

### 2.2 Amplitude exacte, enregistrée et non reconstruite — `[16]`

**Note [16]** : « *“amplitude reconstruite depuis les agrégats” → on peut
parfaitement calculer l'exacte amplitude en conservant les bonnes données
lors de la simulation… Il faut le faire !* »

**Changement.** Au moment où une intervention est appliquée, enregistrer
dans le journal : la liste des identifiants touchés, leur capital, leur
`(A, γ)` avant et après. L'amplitude exacte est alors

    m_exact = Σ_{i ∈ traitées} A'_i K_i^{γ'_i}  /  Σ_{i ∈ traitées} A_i K_i^{γ_i}

évaluée sur l'état exact au moment de l'application. Deux lignes dans
`_apply()`. Cela supprime toute reconstruction depuis `tech_series`.

**Corollaire de conception, plus important que la mesure elle-même** : que
le bras `null` crée une **technologie distincte de paramètres identiques**.
Aujourd'hui, assigner la valeur courante ne crée aucune ligne dans
`tech_series`, donc la cohorte témoin n'est pas traçable. Avec un
identifiant distinct, la cohorte est suivie dans les deux bras, et
l'amplitude comme la part traitée se lisent par différence directe, sans
inversion de dénominateur. **Vérifier que cela ne consomme pas de RNG et ne
change pas la trajectoire** — la technologie n'entre dans la dynamique que
par `(A, γ)`, mais elle entre dans le routage du noyau (`receiver == donor`)
et donc dans le chemin de calcul : deux identifiants distincts de paramètres
identiques passeraient par la branche « même γ » au lieu de la branche
« identité ». Résultat numériquement égal, mais **pas bit à bit**. À traiter
comme une modification qui casse la parité, ou à router explicitement sur
l'égalité des paramètres et non des identifiants.

### 2.3 Prédiction naïve du levier γ — `[17]`

**Note [17]** : « *Pour γ_avant, γ_après, on a Π_tot = Pop·A·K_eq^{γ_avant},
Π_prédit = Pop·A·K_eq^{γ_après} à comparer avec le Π réel final.* »

Fait dans la v1 (§8). En v2, à produire automatiquement pour tout bras dont
l'intervention porte sur γ, à côté de l'amplitude exacte de §2.2 : les deux
chiffres encadrent la réponse, l'un sans effet de marché, l'autre à capital
figé.

### 2.4 Statistique : ce que « x σ » veut dire — `[19]`

**Note [19]** : « *Il faut, quand cette histoire de mesure à x σ arrive dans
le rapport, une note de bas de page expliquant mathématiquement ce que cela
veut dire.* »

Corrigé dans la v1 (§8), avec une conséquence à porter en v2 : avec 5
graines, `moyenne / erreur-type` suit une **Student à 4 degrés de liberté**,
pas une normale. Le seuil de significativité à 5 % est 2,78 et non 1,96 ;
à 1 %, 4,60 et non 2,58. **v2 doit lever cette limite à la source** : le
nombre de graines, pas la présentation. Recommandation : **12 graines**
minimum pour les bras de verdict (t₁₁ : seuil 5 % à 2,20), 5 restant
acceptable pour l'exploration. Coût mesuré en v1 : 1865 s pour 9 bras × 5
graines × 2000 pas sur 6 processus, donc ≈ 4500 s pour 12 graines — une
heure et quart, acceptable.

---

## 3. Théorie

### 3.1 Justification analytique de ε = 1/(1−γ) — `[28]`

**Note [28]** : « *Est-ce qu'on a une idée d'une justification analytique de
cette loi ? Si oui, je ne l'ai pas bien vu/lu/comprise.* »

**Réponse : oui, et elle est courte.** Elle a été écrite et vérifiée
numériquement dans la v1 (§8) : le système est **covariant d'échelle**. Si
l'on remplace `A → A' ` et `K₀ → cK₀` avec `c = (A'/A)^{1/(1−γ)}`, alors
toutes les trajectoires de capital sont multipliées par `c` à l'identique,
donc la production aussi, d'où `ε = d ln Π / d ln A = 1/(1−γ)`. L'exposant
ne dépend que du rendement d'échelle de la production. Les écarts résiduels
mesurés (≤ 1,3 %) proviennent des **constantes dimensionnées non
rééchelonnées** (`MIN_LOAN`, `transfer_cap`, `ZERO_TOL`).

**Ce que v2 en fait.** Cette invariance n'est pas un résultat isolé, c'est
une **contrainte de conception** : tout mécanisme ajouté à v2 doit être
déclaré homogène de degré 1 en capital, ou explicitement dimensionné.
Recommandation : exprimer `MIN_LOAN` et `transfer_cap` en unités de `K_eq`
(ou de `K₀`) plutôt qu'en joules absolus, ce qui rend l'invariance exacte et
non approchée — et rend au passage la loi d'échelle vérifiable à la
précision machine.

### 3.2 Étude théorique de K0 — `[26] [27]`

**Note [27]** : « *Une étude théorique sur l'action de K0 sera menée.* »
**Note [26]** : « *On sait depuis un rapport précédent qu'on peut multiplier
K0, A et γ sans modifier le fonctionnement du système. Ce paragraphe n'est
pas intéressant en tant que tel, il ne fait que de la redite. Néanmoins, ce
fait reste intéressant.* »

**Programme.** K0 n'est pas un paramètre libre : c'est **l'échelle de
naissance rapportée à l'échelle du système**. Les trois objets de §2.1, §3.1
et cette note sont le même objet vu de trois côtés :

- `K₀/K_eq` — la petitesse relative d'une nouvelle-née ;
- `K_aut/K_eq` — la tension, l'écart entre l'échelle d'équilibre autarcique
  et l'échelle effectivement portée par le marché ;
- `c = (A'/A)^{1/(1−γ)}` — le facteur qui laisse le système invariant.

**Question centrale de v2** : la dynamique ne dépend-elle des paramètres
`(A, γ, δ, K₀, λ, σ, k)` **que par ces rapports sans dimension** ? Si oui,
la carte de phase du modèle est de dimension réduite, et l'essentiel des
campagnes passées se replie sur un petit nombre de courbes. C'est une
prédiction forte et **testable à coût faible** : deux jeux de paramètres de
mêmes rapports doivent donner des séries proportionnelles.

**La v1 a déjà tranché une moitié de cette question, et la réponse oriente
v2.** `K_aut/K_eq` ne suffit pas : `δ` s'en échappe (§2.1). Ce qui aligne les
quatre leviers est la rotation du crédit `loan_volume/K_tot` — une variable
endogène. Le programme théorique de v2 se reformule donc ainsi, et c'est un
énoncé plus précis que celui de la note [27] :

> **Quelle combinaison de `(A, γ, δ, K₀, λ, k)` détermine la rotation du
> crédit à l'état stationnaire ?**

Si l'on sait répondre à cela, on obtient la mortalité, donc la population,
donc la production agrégée — toute la chaîne de causalité que les campagnes
mesurent une par une. C'est le chantier théorique le plus rentable de v2, et
il ne demande pas une ligne de moteur : les 127 runs existants portent déjà
`loan_volume`, `K_tot` et tous les paramètres.

**Piste de départ, à vérifier et non à croire** : la rotation est le produit
du nombre de paires tirées par pas `η(N)`, de la probabilité qu'une paire
traite, et du transfert moyen rapporté au capital. Les deux premiers
facteurs sont combinatoires et se calculent ; le troisième est
$\mathbb{E}|\delta^{*}|/\overline{K}$, dont l'institution donne la forme
exacte. Une prédiction analytique de la rotation est donc plausible.

### 3.3 Le surplus coopératif, défini avant d'être invoqué — `[23]`

**Note [23]** : « *Le surplus coopératif est intéressant comme notion, mais
il faut le définir mathématiquement en amont.* »

Corrigé dans la v1 (§8). En v2, `mkt_surplus` doit être documenté dans le
`model_summary` partagé et non dans le corps d'un résultat.

### 3.4 Covariance de pas de temps — consigne du 21 août 2026

**Consigne de l'utilisateur** : « *δ, comme σ ou λ, est une variable
structurante de la modélisation physique du système. Si on double λ, changeons
δ par 2δ−δ², et multiplions σ par √2 σ, le système tournera comme si « deux
pas d'avant se déroulent en un pas désormais ». Bien sûr il y a des
changements marginaux de simulations, mais je pense que la population restera
la même, la production grossièrement multipliée par deux, etc. À vérifier et
ajouter au rapport.* »

**Vérifié en v1 le 21 août** — voir §8 et `scripts/time_rescaling.py`. Les
trois substitutions se composent **exactement** ; il faut leur ajouter les
deux flux par pas (`A`, `ρ`) que l'énoncé ne mentionne pas.

**Ce que v2 en retient.**

1. **Une classification des paramètres.** δ, σ, λ, A, ρ sont des grandeurs
   *par pas* — elles se recalent avec le pas de temps. γ, K0, `transfer_cap`,
   `rate_rule` sont des grandeurs *de forme* — elles n'en dépendent pas. Le
   `model_summary` de v2 doit porter cette colonne, elle évite de discuter un
   « effet de δ » qui n'est qu'un changement d'unité de temps.
2. **Un second groupe de covariance.** v1 a démontré la covariance d'échelle
   (`A → A'`, `K0 → cK0`). Le recalage temporel en est le pendant : à eux
   deux ils réduisent le nombre de paramètres réellement libres. À écrire
   comme tel dans la conception v2, pas comme deux résultats séparés.
3. **Un test de non-régression candidat** — voir la question ouverte n°6.
4. **Une limite documentée, et mesurée.** Le résidu du recalage (6 à 17 %)
   ne vient **pas** de la discrétisation en δ : c'était l'hypothèse de
   départ, elle a été réfutée. Le test à `s = 4` ne tranche pas (les deux
   termes croissent en s−1) ; celui à `δ = 0,002` tranche — le terme de K_aut
   est divisé par 5 et le résidu ne bouge pas. La source est la **phase de
   marché, qui ne se compose pas** : deux rondes de ρN appariements ne valent
   pas une ronde de 2ρN, la seconde voyant l'état laissé par la première.
   C'est ce qui distingue ce modèle d'une équation différentielle, et c'est
   la vraie question ouverte : *que font s rondes successives qu'une ronde s
   fois plus grosse ne fait pas ?*

---

## 4. Rapport et pédagogie

Les notes [2] [5] [9] [15] [20] [21] [24] [25] [26] portent sur la lisibilité
du rapport final v1 et **ont toutes été traitées dans la v1 elle-même**
(§8). Ce que v2 en retient comme **règles d'écriture**, à porter dans le
prompt :

1. **Tout tableau de plus de quatre colonnes est d'abord une figure.** La
   note [15] (« *ce tableau est illisible* ») porte sur un tableau de
   calibration qui tenait en cinq colonnes de nombres bruts.
2. **Aucune notation n'apparaît avant sa définition** — `h`, `p`, `m`, `E`,
   « surplus coopératif », « x σ » ont tous été signalés (notes [9] [19]
   [23]).
3. **Un calcul cité est un calcul déroulé.** Note [21] : « *On comprend
   quand on connaît les chiffres, mais la transmission du savoir n'est pas
   idéale pour un novice du projet.* »
4. **Un paragraphe de résultat qu'un lecteur ne peut pas paraphraser est à
   réécrire, pas à défendre.** Notes [20] et [25] : « *On ne comprend pas de
   quoi tu parles.* »
5. **Pas de superlatif sur les technologies** — note [7] : « *Il n'y a pas
   de “meilleure” technologie.* » Sous exposants inégaux, l'ordre dépend du
   capital : on dit « la technologie de plus grand rendement marginal à ce
   capital ».

---

## 5. Ce que l'utilisateur a explicitement dépriorisé

À ne pas traiter, ou à traiter en dernier — la consigne est dans les notes.

| Sujet | Note | Consigne littérale |
|---|---|---|
| Remesurer la relaxation a posteriori | [11] | « *Problème secondaire, à ne pas corriger absolument.* » |
| Horizon h = 1 | [13] | « *On ne continuera pas les recherches pour cet horizon, mais on garde les résultats déjà obtenus.* » |
| Portée partielle, en entier | [18] + consigne du 21 août | « *Problème de deuxième classe qu'on ne traitera pas tout de suite* » [18], puis « *Pour la v2, je ne veux **aucun** traitement du cas partiel* » — passé de déprioritisé à **hors périmètre** (voir §1.3) |
| Figure des paires refusées | [24] | « *Figure qui sera à terme archaïque. On la garde pour le moment.* » |
| Morts par pas comme diagnostic | [24] | « *Pas intéressant. On sait que les morts vont tourner autour de α.* » |

---

## 6. Un point où la note et le code divergent — `[14]`

**Note [14]** : « *Le choc se passe APRÈS l'action et AVANT la production.
L'effet mécanique doit donc être relativement proche (loi des grands
nombres), mais potentiellement inégal au seuil calculé.* »

**Le code dit autre chose.** `model.py:858–896` : `_apply_pending()` →
naissances → choc multiplicatif → production. À l'horizon 1, l'intervention
ne touche que `(A, γ)` : l'ensemble des vivantes, son ordre, et l'état du
générateur sont **identiques** dans le bras traité et dans sa référence
appariée. Le même vecteur `ξ` frappe donc les mêmes capitaux dans les deux
bras, et il se simplifie exactement dans le rapport. L'égalité `(m−1)p`
est **exacte, pas approchée** — et les amplitudes reconstruites
(1,5000 / 1,2500 / 1,5000, à cinq chiffres) en sont la preuve empirique.

Ce point est argumenté dans le rapport v1 corrigé (§8). Il figure ici parce
qu'il vaut comme **règle de conception v2** : tant qu'une intervention ne
touche pas au capital, tout ce qui est en amont de la production se
simplifie dans un rapport apparié. C'est ce qui rend l'appariement par
graine puissant, et c'est ce qu'il faut préserver dans tout nouveau
mécanisme.

---

## 7. Séquencement proposé

| Lot | Contenu | Porte de sortie | Coût estimé |
|---|---|---|---|
| **A** | Fork du dossier, **§1.4 suppression de `equalization`**, `test_parity_m4_3.py --full` vert sur le fork nu | parité bit à bit reconduite (la suppression est du code mort : `mkt_capped` = 0 sur 164 runs) | 1 h + 1000 s de calcul |
| **B** | §1.1 sens du prêt libre, `K_a/K_b`, compteur contrefactuel | parité reconduite **ou** écart expliqué ligne à ligne | 1 j |
| **C** | §2.1 tension et `K_eq` en colonnes natives, §2.2 amplitude exacte, §2.3 prédiction naïve | tests unitaires sur données synthétiques | 0,5 j |
| **D** | §1.2 `phase_order`, campagne A/B appariée | taux de défaut mesuré contre la prédiction a priori | 0,5 j + 2 h de calcul |
| **E** | §3.2 test des rapports sans dimension (deux jeux de paramètres homothétiques) | séries proportionnelles à la précision des constantes non rééchelonnées | 0,5 j + 1 h |
| **F** | Campagne de verdict 12 graines (§2.4) sur le modèle à sens libre | verdict rebond reconduit ou infirmé, à Student 11 ddl | 1,5 h de calcul |
| **H** | Rapport v2 selon les cinq règles du §4 | relecture annotée | 1 j |

*(Le lot G — portée `fraction_persistante` — a été retiré le 21 août : aucun traitement du cas partiel en v2, §1.3.)*

Les lots B et D changent le modèle : ils doivent être **séparés dans
l'historique git** et chacun accompagné de sa campagne appariée. Ne jamais
les empiler avant mesure — c'est la seule manière de garder un verdict
attribuable.

---

## 8. Traité dans la v1, sans attendre v2

Les notes ci-dessous ne demandaient pas de fork : elles ont été traitées
dans `m4_3live_credit_soc/` le 18 août 2026, et le rapport final a été
recompilé. Elles figurent ici pour que v2 hérite de l'état corrigé et non de
l'état annoté.

| Note | Objet | Où |
|---|---|---|
| [2] | ordre de grandeur de E\|ξ\| pour le σ utilisé | `model_summary.tex` |
| [5] | cas K < 1 retiré (il ne survient jamais) | rapport §2 |
| [7] | « meilleure technologie » retiré du vocabulaire | rapport, conception |
| [9] | définition de m, p, h, E réécrite avec exemple chiffré | rapport §2 |
| [14] | réponse par l'argument de simplification du choc | rapport §3.4 |
| [15] | tableau de calibration → figure légendée | rapport, figure |
| [17] | tension K_aut/K_eq : code, colonnes, figures, section | `scripts/`, rapport |
| [19] | note de bas de page Student, seuils recalculés | rapport §3.1 |
| [20] | paragraphe du creux réécrit | rapport §4.2 |
| [21] | calcul du capital par entité déroulé | rapport §4.4 |
| [22] | durée de vie et mortalité lues contre la tension | rapport §4.4 |
| [23] | surplus coopératif défini mathématiquement en amont | `model_summary.tex` |
| [24] | figure des canaux : encart sur K_tot, panneau des morts retiré | figure |
| [25] | réponse cumulée réécrite | rapport §4.5 |
| [26] | paragraphe de l'ablation resserré sur le fait | rapport §5 |

**Ajouts du 21 août 2026** (retours oraux, hors des 28 notes du PDF) :

| Retour | Objet | Où |
|---|---|---|
| « figure 12 à retravailler » | un panneau par γ, aucune régression, bases rendues visibles ; garde-fou d'ajustement corrigé (étendue et non nombre de valeurs distinctes) | `tension_analysis.py`, rapport §6.2 |
| « δ, σ, λ structurent le pas de temps » | covariance de pas de temps vérifiée : les trois substitutions composent exactement, mais il faut y ajouter A×2 et ρ×2 | `time_rescaling.py`, rapport §7.3 |
| « A×x semble impliquer T×x » | exposant dlnT/dlnA mesuré et décomposé exactement ; balayage en A à trois γ | `tension_vs_A.py`, rapport §6.2 |
| « je ne veux plus que `transfer_cap="optimum"` » | décision de périmètre v2, §1.4 ; vérifié que `mkt_capped` = 0 sur les 164 runs, donc suppression de code mort | feuille de route §1.4 |
| [28] | justification analytique de ε = 1/(1−γ) + vérification numérique | rapport §6 |

---

## 9. Notes de conception — à remplir

Réservé aux annotations de `conception_m4_3live.pdf`, absentes du fichier au
moment d'écrire (voir en-tête). Pour les récupérer : rouvrir le PDF dans la
visionneuse et **enregistrer** (les annotations ne sont pas persistées
automatiquement), ou déposer la copie annotée à côté du fichier d'origine.

---

## 10. Ce qui reste à trancher avant d'écrire le prompt v2

1. ~~**Le plafond de transfert sous δ signé** (§1.1)~~ — **sans objet depuis
   le 21 août** : il n'y a plus de plafond du tout (§1.4). Le *sens* du
   transfert reste en revanche la question entière du §1.1.
2. **Le taux d'intérêt quand la créancière est la plus pauvre** (§1.1) — la
   règle de taux actuelle a-t-elle encore un sens si la prêteuse est la plus
   fragile des deux ?
3. **Nombre de graines de verdict** (§2.4) — 12 recommandé, à confirmer
   contre le budget de calcul.
4. **Constantes dimensionnées** (§3.1) — rééchelonner `MIN_LOAN` et
   `transfer_cap` en unités de capital rendrait l'invariance exacte, mais
   casse la comparabilité directe avec toutes les campagnes antérieures.
5. ~~**Portée `fraction_persistante`** (§1.3)~~ — **tranché le 21 août, par
   la négative** : aucun traitement du cas partiel en v2. Voir §1.3.
6. **Recalage temporel** (§3.4, ajouté le 21 août) — la covariance de pas de
   temps doit-elle devenir un *test de non-régression* de v2 (au même titre
   que la parité M4.3), ou rester une vérification ponctuelle du rapport ?
