# M4.4Rebond — plan d'attaque

**Effet rebond, résolu dans la distribution : qui capte la hausse de
production, dans quelle classe de loi, et peut-on piloter la queue et le
rapport de branchement ?**

Version : 23 août 2026, révision 1. Lignée : succède à **M4.3Live-v2**
(`m4_3live_v2_credit_soc/`), programme terminé — 2 rapports PDF, 153 runs
enregistrés, parité bit à bit reconduite trois fois. Convention de dossier :
`m4_4_rebond_credit_soc/`.

Ce document joue le rôle de spécification complète : il donne le *quoi*, le
*pourquoi* et l'*ordre*. Il est écrit avec les règles de discipline du prompt
M4.3Live-v2 et s'y substitue pour cette lignée.

---

## 0. Lectures préalables, et ce qui est acquis

### À lire avant d'écrire une ligne de code

| document | ce qu'on y prend |
|---|---|
| `m4_3live_v2_credit_soc/report/rapport_final.pdf` (28 p.) | le verdict rebond sous sens libre, la rotation = ρ·Ḡ, les deux fenêtres, le contrôle de stationnarité recalibré |
| `m4_3live_v2_credit_soc/report/conception_m4_3live_v2.pdf` (23 p.) | l'architecture du moteur, les trois sémantiques de parité, les décisions tranchées |
| `m4_3live_v2_credit_soc/m4_3live_v2/model.py` (~1560 l.) | le moteur de référence ; **ce plan cite ses numéros de ligne**, à revérifier s'il a bougé |
| `m4_3live_v2_credit_soc/JOURNAL.md` (471 l.) | les inférences retirées en cours de route, et pourquoi |
| **`m4_2b_credit_soc/report/rapport_final.pdf`** | **la queue de Pareto des revenus d'intérêt : programme entier, verdict de non-décidabilité, épistémologie de remplacement** — §2 ci-dessous |
| `recherche/sensibilite_m4b/report/rapport_final.pdf` | valeur nette, cycle débiteur→créancier, avalanches tronquées, rôles de σ/k/K0/δ/λ |
| `m4_credit_soc_fable/reports/01_soc_final/main.pdf` | régime SOC atteint, classes de lois ajustées, levier du branchement |
| `recherche/sensibilite_m4b/scripts/lib_metrics.py` | estimateurs discrets, Vuong, susceptibilité — **réutilisables tels quels** |

### Règle de confiance à 95 %

Si tu n'es pas certain à 95 % d'un fait, le signaler, en distinguant **fait
observé** (lu dans le code ou les données), **inférence**, **hypothèse** et
**incertitude**. Citer `fichier.py:ligne`. Ne jamais inventer un comportement
non vérifié. Traduction typographique obligatoire dans les rapports :
`\fait{}`, `\inference{}`, `\hyp{}`, `\incertitude{}`.

### La règle du fork

`m4_3live_v2_credit_soc/m4_3live_v2/` est **gelé** : 153 runs enregistrés et
deux rapports publiés en dépendent. M4.4 **forke** ce paquet par copie dans
`m4_4_rebond_credit_soc/m4_4/`, jamais par import — sauf en lecture, pour les
tests d'équivalence. C'est la troisième application de cette règle dans la
lignée ; elle n'est pas négociable.

Renommages obligatoires, chacun évitant une collision réelle déjà rencontrée :
paquet `m4_3live_v2` → `m4_4` ; routes `/live2` → `/live3` ; identifiants de
run `m4_3live_v2__` → `m4_4__` ; module d'aiguillage
`simulation_lab/live_v2/` → `simulation_lab/live_v3/`.

---

## 1. Le mandat, en une phrase

> **L'effet rebond est un énoncé sur des agrégats. Ce programme demande où il
> vit dans la distribution — et si la queue et le rapport de branchement se
> pilotent.**

Trois questions, hiérarchisées. Si le budget se resserre, livrer la première
proprement plutôt que trois moitiés.

1. **Décomposition distributionnelle du rebond.** Quand `A` monte, la
   production par entité monte de ×1,80 et la population se contracte de
   25 % : où va le surcroît ? Corps ou queue ? Producteurs ou rentiers ?
2. **Caractérisation coordonnée** des classes de lois du **revenu d'intérêt**
   et de la **valeur nette**, par groupe d'entités et au cours du temps.
3. **Tentative de contrôle** de l'exposant de queue α et du rapport de
   branchement b, par intervention en direct — pas par balayage entre runs.

---

## 2. Ce qui est acquis, et qu'il est **interdit** de refaire

Ces résultats sont publiés. Les citer, pas les reproduire.

### 2.1 Le rebond, mesuré

| acquis | source | valeur |
|---|---|---|
| Portée globale, régime établi | v1 §4.3, **reconfirmé v2** | **ε = 0,7473 ± 0,0048** (12 graines appariées, fenêtre ]t₀+1000, t₀+2000]) |
| Décomposition du même | v2, calcul direct | production/entité **×1,8014 ± 0,0015**, population **×0,7516 ± 0,0013** |
| Le signe du verdict tient à K0 | v1 §5 | compenser `K0 → K0·A^{1/(1−γ)}` annule la contraction (pop ×1,005) et donne ε = 2,02 |
| Loi d'échelle | v1 §7 | ε = 1/(1−γ), démontrée par covariance d'échelle, exacte à 3·10⁻¹⁴ |
| Portée partielle, court horizon | v1 §4.1 | rebond ε ≈ 2,3–2,9 |
| Portée partielle, long horizon | v1 §4.2 | **non tranchable** : la cohorte s'éteint, le dénominateur disparaît |

\fait{} **Le sens libre ne peut pas changer le rebond à portée globale**, et
ce n'est pas un résultat mais une conséquence : `scope="all"` change aussi la
technologie de naissance (`m4_3live_v2/model.py`, `_apply`), donc la
population reste homogène, donc les deux règles de sens coïncident bit à bit.
Le programme distributionnel ne peut donc pas porter là-dessus.

### 2.2 La queue de Pareto — l'acquis le plus contraignant

**M4.2B a consacré un programme entier à la queue de Pareto des revenus
d'intérêt et a conclu qu'elle n'est pas décidable**, après trois critères
successifs (seuil/2, seuil×2, facteur d'admissibilité continu avec bootstrap
KS re-scanné). Le blocage n'est pas une courbure : c'est la **couverture** —
le volume de données dans la queue extrême, médiane 0,22.

> **Cette question est close. Le présent programme ne la rouvre pas.**

L'épistémologie de remplacement, à reprendre telle quelle :

- l'existence de la queue est posée en **hypothèse de travail**, marquée
  `\hyp{}` à chaque emploi ;
- ce qui est livré est la **caractérisation de α̂**, jamais sa validation ;
- **trois échelles d'incertitude, jamais fusionnées** : intra-instantané
  (bootstrap, seuil re-scanné à chaque tirage), inter-instantanés,
  inter-graines. M4.2B mesure un écart-type bootstrap intra-instantané
  ≈ 3,7× l'écart-type inter-graines : lire α̂ sur un seul instantané est bien
  moins précis que la reproductibilité de la moyenne de cellule ne le
  suggère ;
- **fenêtres par run**, pas de burn-in fixe : temps de convergence mesuré
  (M4.2B : régression FOPDT sur le renouvellement du décile supérieur ;
  27 cellules sur 37 avaient un burn-in insuffisant sous la règle T/4).

Plage d'α̂ mesurée par M4.2B : **2,97 à 4,84**. Leviers : η le plus
systématique, γ monotone après compensation de K0, K0 fort et non monotone,
δ et σ conjoints monotones, β sans effet mesurable.

### 2.3 Les classes de lois déjà ajustées — mais sur d'autres moteurs

\incertitude{} **Ces verdicts viennent de M4 fable et de M4B, dont
l'institution de principal est arithmétique.** M4.3Live-v2 maximise la
production jointe et laisse le sens du prêt libre. Les classes doivent être
**réétablies**, pas héritées. Elles servent de familles candidates et de
prédictions à falsifier, rien de plus.

| grandeur | classe retenue ailleurs | source |
|---|---|---|
| revenu d'intérêt > 10 J | **corps exponentiel × queue Pareto**, composite à 3 paramètres, bat la lognormale par AIC 5/5 ; T ≈ 22–25 J/pas, raccord x_b ≈ 25 J, α ≈ 8,5–10 | M4 fable |
| revenu d'intérêt, queue seule | α̂ ∈ [2,97 ; 4,84] | M4.2B |
| valeur nette | **gamma généralisée** | M4 fable |
| capital | Burr XII (5/5) ; mélange de lognormales écarté | M4 fable |
| âge au décès | lognormale (pas sans mémoire) | M4 fable |
| taille d'avalanche | loi de puissance **tronquée partout** ; α∞ ≈ 2,31 | M4B |

**Consigne de figures héritée, toujours en vigueur** : sur les tailles
d'avalanches, n'ajuster **que** des lois de puissance, aucune analyse de
coupure.

### 2.4 L'inégalité est dans les bilans, pas dans le capital

M4B, extension demandée par l'utilisateur : Gini NW 0,44 contre Gini K 0,07
au centre ; réponses **opposées** à σ ; cycle de vie débiteur→créancier
(x/K de −0,85 à +2,5 ; 62 % nets débiteurs) ; trou d'insolvabilité au décès
invariant le long de δ/K0/k/λ, fonction de σ seul. **NW doit être un
observable primaire.** v2 l'a partiellement entendu — `K_share_creditors`,
`corr_marg_net`, `corr_K_net` — mais au niveau agrégé seulement.

---

## 3. Ce que ce programme mesure de neuf

### 3.1 La décomposition, et le seul endroit où elle contient de la nouveauté

Par **définition** du capital équivalent (v2 §1), et en prenant l'effectif
producteur `n_prod` — celui d'avant les morts du pas, que v2 enregistre
nativement :

```
prod_tot = n_prod · A · K_eq^γ        (définition de K_eq)
```

d'où, en élasticités par rapport à `A` :

```
ε = dln(n_prod)/dlnA  +  1  +  γ·dlnK_eq/dlnA
```

\fait{} Les trois termes sont mesurés sur les bras `control` et `all_A150`,
12 graines appariées, fenêtre résiduelle :

| terme | valeur | source |
|---|---|---|
| `dln(n_prod)/dlnA` | **−0,6834 ± 0,0041** | colonne `n_prod` de `tension_agg.csv` |
| `1` | 1 | exact |
| `γ·dlnK_eq/dlnA` | **+0,4308 ± 0,0022** | colonne `K_eq` de `tension_agg.csv` |
| **somme** | **+0,7474 ± 0,0048** | l'identité |
| ε mesuré | **+0,7473 ± 0,0048** | `prod_tot` de `series.csv` |

Données : `results/analysis/decomposition_epsilon.csv`, 12 graines.

\fait{} L'identité se referme à **5,3·10⁻⁴** au pire, et non à la précision
machine. L'écart n'est pas une erreur : `K_eq` est moyenné sur les 1000 pas
de la fenêtre, et la moyenne d'une fonction non linéaire n'est pas la fonction
de la moyenne. 0,07 % sur ε — à rapporter, pas à masquer, et à ne surtout pas
présenter comme une vérification de l'identité.

\inference{} **Cette décomposition ne contient qu'une seule mesure, pas
deux.** L'identité étant la définition de `K_eq`, les deux termes non triviaux
sont la même mesure — la production — coupée en deux. C'est la leçon §14.4
appliquée à ce plan : une identité qui ne peut pas être fausse ne confirme
rien, et l'écrire en trois termes n'en fait pas trois résultats. Le seul
intérêt de la découpe est de séparer ce qui relève de l'effectif de ce qui
relève de l'échelle par entité.

\fait{} **Un piège d'instant, qu'il faut noter parce qu'il a déjà mordu.**
L'élasticité de la population de **fin de pas** vaut −0,7043, pas −0,6835 :
l'écart de 0,021 est la mortalité intra-pas (≈ 30 morts pour ≈ 1030
vivantes). L'identité ne se referme qu'avec `n_prod`. Employer `pop` la fait
manquer de 9 erreurs-types — c'est exactement la correction d'instant que v2
a portée dans le moteur, et elle se venge ici si on l'oublie.

**Le contenu empirique, et le test.** Il est ailleurs : dans le fait que le
terme d'effectif soit *prévisible* à partir de la distribution. Par la loi de
Little (M4B, vérifiée à mieux de 1 %), l'effectif stationnaire vaut
λ / (morts par entité et par pas) ; v2 relie cette mortalité à la rotation du
crédit, et la rotation au coefficient de Gini :

```
rotation = ρ · Ḡ        (v2 : exact en régime homogène)
mortalité ∝ rotation^a  (v2 : a = 1,260 ± 0,009 ; v1 : a = 1,337)
```

Les deux intervalles sur `a` **ne se recouvrent pas** ; ils décrivent des
corpus différents (322 runs des deux lignées contre 109 runs d'un balayage
contrôlé). D'où la prédiction, écrite ici **avant** toute mesure :

```
dln(Ḡ)/dln(A)  =  0,7043 / a  ∈  [0,527 ; 0,559]
```

la borne basse pour `a = 1,337`, la haute pour `a = 1,260`.

> **C'est le test, et il a trois issues, toutes informatives.** Si la mesure
> de `dlnḠ/dlnA` tombe dans la bande, elle **discrimine entre les deux
> exposants** — ce qu'aucun des deux programmes précédents ne pouvait faire.
> Si elle tombe hors de la bande, c'est la chaîne
> Gini → rotation → mortalité → population qui est en défaut, et le rebond
> n'est pas gouverné par l'inégalité. Si Ḡ ne répond pas du tout à `A`, la
> contraction de population vient d'ailleurs — et le candidat est l'échelle
> `K0`, que le bras compensé du §6 est là pour détecter.

Ḡ doit être **mesuré indépendamment**, par la sonde `record_market_stats` du
moteur v2, et non déduit de la rotation : le déduire referait une identité.

### 3.2 Le rapport de branchement se lit sur les runs déjà faits

\fait{} L'estimateur `b = 1 − racines/morts` — le rapport de branchement de
population, inverse de la descendance totale moyenne par racine — est
calculable sur toute série v2 existante, sans un calcul neuf : les colonnes
`deaths`, `roots_insolvency`, `roots_liquidity`, `roots_both` suffisent
(`m4_3live_v2/model.py:1458-1460`). Les « racines » sont, par construction,
la file initiale de `_resolve_bankruptcies` (`model.py:945-965`), donc la
génération 1 — c'est ce qui rend l'estimateur bien défini ici.

\fait{} **C'est exactement l'estimateur de M4B** :
`recherche/sensibilite_m4b/scripts/lib_metrics.py:333`,
`branching_ratio = 1 − roots.sum()/total_size`. La comparaison inter-lignées
est donc valide et n'est pas un artefact d'estimateur.

Mesure faite sur les 96 bras de v2, 12 graines, fenêtre résiduelle :

| bras | règle | b | racines/morts |
|---|---|---|---|
| `control` | sens libre | **0,7863 ± 0,0006** | 0,2137 |
| `all_A150` | sens libre | **0,7541 ± 0,0011** | 0,2459 |
| `new_A150` | sens libre | 0,7560 ± 0,0010 | 0,2440 |
| `new_A150` | règle v1 | 0,7559 ± 0,0012 | 0,2441 |
| `new_g060` | sens libre | 0,7212 ± 0,0012 | 0,2788 |

et sur la fenêtre de transition, où le sens du prêt agit :

| bras | sens libre | règle v1 | écart |
|---|---|---|---|
| `new_A150` | **0,7873 ± 0,0020** | **0,7550 ± 0,0023** | **+0,032** |
| `new_g060` | 0,7569 ± 0,0016 | 0,7157 ± 0,0026 | +0,041 |

\fait{} Trois faits en tombent, tous nouveaux :

1. **b ≈ 0,72–0,79**, très au-dessus des 0,297 de M4B (σ = 0,25) et des 0,30
   de M4 fable, et au-dessus même des 0,647 de M4B à σ = 0.
2. **Monter A abaisse b** : contrôle 0,786 → `all_A150` 0,754.
3. **Le sens libre élève b pendant la transition** (+0,032 et +0,041,
   appariés) et l'écart se referme dans le régime résiduel. C'est la mesure
   directe de « un marché plus complet est ici un marché plus fragile », que
   v2 avait établi par une chaîne de colonnes sans jamais nommer b.

\hyp{} L'écart à M4B tient au régime : v2 tourne à **σ = 0,01** contre 0,25
au centre M4B, et M4B mesure b = 0,647 à σ = 0 contre 0,297 à σ = 0,25. La
direction est la bonne, l'ampleur ne l'est pas — v2 dépasse la valeur σ = 0
de M4B.

\incertitude{} **Mais la cellule σ = 0 de M4B n'est pas comparable terme à
terme**, et il faut le dire avant de bâtir un lot dessus : elle tourne à
δ = 0,05 (v2 : 0,01), avec un pool d'appariement k ∈ [2 ; 10] (v2 : k ≡ 2),
et sous l'institution de principal **arithmétique** (v2 : production jointe
maximale). Quatre différences, pas une. Le lot F ne peut donc pas « isoler
σ » ; il peut au mieux ordonner les quatre candidats par une ablation à un
facteur à la fois, en partant du régime v2 et en marchant vers celui de M4B.
Le dire ainsi, et non « séparer σ de l'institution ».

**Garde-fou obligatoire (porte du lot A), et il coûte plus cher qu'il n'y
paraît.** Un second estimateur — la descendance moyenne par mort, lue sur
l'arbre causal — n'est **pas** la même fonctionnelle, et les deux doivent être
recalculés sur les **mêmes** runs avant qu'un seul chiffre ne soit publié.

\fait{} Mais `avalanche_members.generation` (`model.py:1398`) **ne permet pas
de le calculer** : ce champ vaut `death_iteration`, c'est-à-dire le numéro de
**passe du point fixe** de `_resolve_bankruptcies` (`model.py:945-985`).
Toutes les entités devenues insolvables à la même passe partagent la même
« génération », indépendamment de qui a causé la perte de qui. Ce n'est pas
un compte de descendance.

\fait{} La structure causale réelle est dans `ledger["loss_edges"]` —
les triplets (source, victime, principal) — que `_build_avalanches` consomme
pour son union-find puis **jette** (`model.py:900-935`) : rien ne la persiste,
nulle part. **Persister `loss_edges` est donc une condition d'existence de la
porte du lot A**, et non un raffinement. C'est le cinquième manque
d'instrumentation, et il n'était pas dans la liste du §4 avant cette
vérification.

### 3.3 Ce que « contrôler » veut dire, et ce que ça exclut

M4.2B ne pouvait que **balayer** des paramètres entre runs. v2 sait
**intervenir en cours de trajectoire** et mesurer la réponse sur la même
trajectoire, appariée par graine. C'est la seule capacité réellement neuve, et
« tentative de contrôle » ne désigne rien d'autre.

> Un levier **contrôle** α (ou b) si, et seulement si :
> 1. la réponse appariée a un **signe constant** sur toutes les graines ;
> 2. elle est **monotone** sur une étendue mesurée d'au moins **×3** du
>    levier ;
> 3. son exposant intra-famille **survit au contrôle §14.2** — c'est-à-dire
>    qu'il ne coïncide pas avec la droite qui joint les lignes de base.
>
> Tout ce qui est plus faible est une corrélation, et doit être appelé ainsi.

\hyp{} **Chaîne à écrire avant de mesurer.** M4.2B désigne η (ici ρ) comme le
levier le plus systématique sur α̂ *et* sur b. v2 établit `rotation = ρ·Ḡ`.
D'où la chaîne candidate :

```
ρ  →  rotation  →  mortalité  →  cascades  →  b
                              ↘  renouvellement  →  queue de α
```

Elle prédit que ρ agit sur α et sur b **par le même canal**, donc que les deux
réponses sont liées et non indépendantes. C'est falsifiable : si un levier
déplace b sans déplacer α, ou l'inverse, la chaîne est fausse.

---

## 4. Instrumentation : cinq manques, et leur ordre

L'ordre n'est pas indifférent — les quatre derniers manques sont sans objet
tant que le premier tient.

### 4.1 La persistance — bloquant

\fait{} `deaths`, `avalanches`, `avalanche_members` et `loan_events` sont
enregistrés **en mémoire** quand les drapeaux sont armés
(`model.py:200-203`), mais `write_series` ne les écrit **jamais** sur disque
(`m4_3live_v2/live.py:88-115` : seuls `series.csv`, `tech_series.csv`,
`tension.csv`, `tension_agg.csv` et `kernel.json` sortent). Aucune campagne
v2 n'arme d'ailleurs ces drapeaux.

**Conséquence** : aucune donnée d'avalanche, de décès ni de contrat n'existe
dans les 153 runs v2. Tout le programme d'avalanches part de zéro côté
données, même si le moteur sait déjà les produire.

### 4.2 Les panneaux par entité — bloquant pour les distributions

`entity_snapshot()` (`model.py:1543`) rend exactement les 18 champs dont ce
programme a besoin : `K`, `claims`, `debts`, `nw`, `prod`, `int_in`,
`int_out`, `income`, `income_net`, `A`, `gamma`, `tech`, `age`, `deg_out`,
`deg_in`. Mais il n'est appelé que par `Simulation.run(snapshot_times=…)`
(`model.py:1532-1539`), et **ni `driver/headless.py:run_plan` ni
`scripts/campaign.py:_run_cell` (ligne 151) ne passent par `run()`** : les
deux ont leur propre boucle `while`. Le câblage est donc à faire dans la
boucle de campagne, pas seulement derrière un drapeau.

**Le pas d'échantillonnage k est à mesurer, pas à choisir.** Coût par
instantané et empreinte disque à mesurer sur **une** cellule avant de fixer k,
et le chiffre mesuré va dans le plan de campagne. Ordre de grandeur à
vérifier : ~1000 entités × 18 champs × 200 instantanés × 96 runs.

### 4.3 Le checkpoint de fin de run — dette héritée, jamais payée

M4.2B a inscrit une décision d'ingénierie explicite « pour tous les modèles
postérieurs » : sauvegarder le `Simulation` complet à la fin de chaque run.
\fait{} v2 ne le fait que pour les amorçages (`scripts/campaign.py`,
`burn_one`) ; aucun bras ne laisse de checkpoint. M4.2B avait payé cela au
prix fort : impossible d'étendre les cellules sévères sans tout rejouer, à
~90 min par graine.

Ce programme a besoin d'horizons longs pour la statistique de queue. **La
dette se paie ici, dans le lot A.**

### 4.4 L'arbre causal des cascades — découvert en écrivant ce plan

\fait{} `ledger["loss_edges"]` porte les arêtes (source, victime, principal)
de chaque cascade ; `_build_avalanches` s'en sert pour son union-find puis les
jette (`model.py:900-935`). Sans elles, **aucun** estimateur de descendance
n'est calculable, et le garde-fou du §3.2 est inexécutable. À persister avec
le reste (§4.1), en notant que le volume est celui des arêtes de perte, pas
celui des contrats.

### 4.5 Les groupes d'entités — à définir une fois

Quatre partitions, et une seule règle : elles doivent être calculées sur le
**même instantané** que les distributions, sinon la coordination annoncée
n'existe pas. Les groupes sont référencés `§4.5` dans la suite.

| groupe | définition | pourquoi |
|---|---|---|
| position nette | `claims − debts` > 0 / < 0 / ≈ 0 | M4B : l'inégalité est dans les bilans ; cycle débiteur→créancier |
| technologie | `tech` | seul groupe où A et γ sont définis ; existe dès qu'une portée `new` agit |
| cohorte d'âge | déciles de `age` | M4B : l'horloge des fluctuations est démographique |
| décile de capital | déciles de `K` | raccord avec le Gini, qui pilote la rotation |

---

## 5. Séquencement en lots

Chaque lot a une **porte de sortie**. Tant qu'elle n'est pas franchie, le
suivant ne commence pas. Les coûts sont dérivés des coûts **mesurés** de la
campagne v2 (144 s, 154 s, 220 s, 260 s par cellule de 2000 pas selon le bras ;
96 runs en 2495 s sur 7 processus) ; **toute cellule dont la forme n'a pas de
précédent mesuré est signalée comme telle**.

| lot | contenu | porte de sortie | coût |
|---|---|---|---|
| **A** | Fork ; persistance (§4.1) ; panneaux câblés dans la boucle de campagne (§4.2) ; checkpoint de fin de run (§4.3) ; arbre causal persisté (§4.4) ; **les deux estimateurs de b réconciliés** (§3.2) | **deux portes distinctes.** (i) Parité bit à bit 8000 pas × 26 colonnes, écart nul exigé : elle couvre le **moteur**, dont rien de l'addition n'est relu. (ii) **Test de fermeture des panneaux** (§7) : la parité ne verrait pas un instantané pris au mauvais instant, puisqu'il n'entre pas dans `step()`. Les deux sont nécessaires ; ni l'une ni l'autre ne suffit | 1 j + ~750 s |
| **B** | Décomposition distributionnelle du rebond : bras `control`, `all_A150`, **`all_A150_K0comp` (K0×2,25)**, panneaux à k mesuré, 12 graines | `dln(Ḡ)/dlnA` mesuré et confronté à la prédiction [0,527 ; 0,559] du §3.1 ; verdict sur lequel des deux exposants tient | 3 h de calcul |
| **C0** | **Pilote de couverture** : une cellule, mesurer `n_tail` au seuil optimal et l'empreinte disque des panneaux | `n_tail` médian mesuré, et le nombre d'instantanés indépendants qu'un run rend | 1 h + 1 cellule |
| **C** | Classes de lois, coordonnées : revenu d'intérêt et NW, par groupe (§4.5), sur les instantanés post-convergence ; familles candidates du §2.3 ; sélection par AIC + Vuong | **cible de couverture atteinte** (voir ci-dessous) ; **aucune** conclusion d'existence de queue ; α̂ rendu avec ses trois échelles d'incertitude non fusionnées | 1,5 j + calcul **fixé par C0** |
| **D** | Avalanches et branchement : les deux estimateurs, susceptibilité, profondeur, distribution des tailles (lois de puissance **seules**) ; réconciliation avec M4B et M4 fable | l'écart b ≈ 0,79 vs 0,30 expliqué, ou déclaré ouvert avec ce qui a été essayé | 0,5 j + 2 h |
| **E** | **Contrôle** : interventions en direct sur ρ (candidat n°1, §3.3), puis sur le second levier que le lot C ou D désigne ; réponse appariée de α et de b | les trois conditions du §3.3 tenues ou explicitement non tenues, levier par levier | 1 j + 4 h |
| **F** | La question ouverte du §3.2 : pourquoi b dépasse la valeur σ = 0 de M4B — σ, ou l'institution de production jointe ? | une ablation qui sépare les deux, ou un constat d'échec documenté | 0,5 j + 3 h |
| **G** | Rapports, journal, traçabilité, import `simulation_lab` | relecture annotée | 1,5 j |

### La couverture de queue est le budget du lot C, et rien d'autre

\fait{} Ce qui a bloqué M4.2B n'est pas la finesse du critère : c'est le
**nombre de points dans la queue extrême** — `n_tail` médian 113 au seuil
optimal, 17 au seuil doublé, 2 % seulement des instantanés restant
admissibles.

\inference{} **Aucun lot de ce plan ne change la couverture par défaut.**
12 graines × 1000 pas × ≈ 1000 entités à λ = 30 rendent la même profondeur de
queue par instantané que M4.2B. Reconduire ce protocole, c'est reproduire son
impasse avec un moteur plus récent. Il n'existe que deux leviers, et ils ont
un coût mesurable :

| levier | effet | coût |
|---|---|---|
| plus d'entités par instantané (λ ↑) | M4B : λ est de la **pure taille finie**, intensivité ±2 % — donc la physique ne change pas, seule la statistique s'améliore | ≈ ×4 à λ = 60 (population double, marché et service doublent) |
| plus d'instantanés indépendants (T ↑, espacés de τ) | ne change pas `n_tail` par instantané, réduit l'incertitude inter-instantanés | linéaire en T, **sans précédent mesuré** dans v2 au-delà de 4000 pas |

**Porte du lot C, à fixer chiffrée par C0** : une cible `n_tail ≥ X` par
instantané, X étant dérivé de la précision voulue sur α̂ et non choisi. Et le
calcul du lot C est dimensionné pour l'atteindre, ou le lot est déclaré
infaisable au budget — ce qui est un résultat, pas un échec.

**Les lots qui changent le moteur sont séparés dans l'historique git.**
Ici, un seul le fait (A), et il est neutre par construction : rien de ce qu'il
ajoute n'est relu par la trajectoire, ce que la parité vérifie.

---

## 6. Protocole

Reprendre le protocole v2 — amorçage partagé à t₀ = 2000, fenêtre de 2000 pas,
12 graines, appariement par graine, Student à 11 degrés de liberté (seuil 5 % :
2,201 ; 1 % : 3,106) — avec quatre modifications.

1. **Deux fenêtres**, comme en v2 : transition ]t₀, t₀+200] et régime
   résiduel ]t₀+1000, t₀+2000]. La première n'est pas stationnaire et n'est
   jamais lue comme un niveau.
2. **Contrôle de stationnarité calibré, pas postulé.** v2 a démontré qu'une
   bande fixe [0,99 ; 1,01] sur le rapport de quarts rejette **11 des 12
   graines du contrôle** sur une fenêtre de 1000 pas : elle ne mesure que la
   longueur de la fenêtre. Le critère est un test de Student sur la moyenne du
   rapport ; l'étendue par run est rapportée comme plancher de bruit.
3. **Fenêtres de queue par run**, pas de burn-in fixe (§2.2). Le temps de
   convergence est mesuré, et les runs qui n'y arrivent pas sont marqués
   « non-stationnaire-confirmé » et rendus sur un instantané unique.
4. **Portée globale et portée `new` seulement.** Voir §8, décision n°2.

**Bras du lot B**, et pourquoi ceux-là :

| bras | intervention à t₀+1 | ce qu'il sépare |
|---|---|---|
| `control` | aucune | référence appariée |
| `all_A150` | A = 1,5, portée toutes | le rebond à K0 fixe : ε = 0,747 attendu |
| `all_A150_K0comp` | A = 1,5 **et** `K0 → K0·(A'/A)^{1/(1−γ)}`, soit 56,25 à γ = 0,5 | **indispensable** : v1 montre que la contraction de population est un effet d'échelle de K0 que la compensation annule entièrement (pop ×1,005). Sans ce bras, une réponse de queue qui ne serait qu'un artefact d'échelle serait découverte à la fin plutôt que détectée. La formule, et non le nombre, pour que le bras survive à un changement de γ |
| `new_A150` | A = 1,5, portée nouvelles | deux technologies coexistantes ; le seul régime où le sens du prêt agit |

---

## 7. Tests exigés

Assertions Python simples, convention du dépôt — **pas de pytest**. Reprendre
la suite v2 (12 fichiers, tous verts) et l'étendre.

- **Parité, trois sémantiques**, inchangées : bit-exacte après le lot A ;
  `loan_direction="richest_lends"` reproduit v2 **et** v1 en régime
  hétérogène ; `phase_order="deprec_first"` ne la préserve pas, par
  construction.
- **Branchement** (nouveau) : sur une cascade construite à la main dont on
  connaît l'arbre, les **deux** estimateurs rendent la valeur attendue, et
  leur écart est celui qu'on calcule à la main.
- **Panneaux** (nouveau) : un instantané pris à `t` reproduit exactement les
  agrégats de la ligne `t` de `series.csv` — population, K_tot, somme des
  `int_in`, valeur nette totale. Un panneau qui ne se referme pas sur les
  agrégats ne mesure pas ce qu'on croit.
- **Checkpoint** (nouveau) : un run repris depuis son checkpoint et poursuivi
  produit une trajectoire bit-identique à un run mené d'un trait.
- **Estimateurs de queue** (nouveau) : sur un échantillon **synthétique** tiré
  d'une Pareto d'exposant connu, l'estimateur rend l'exposant et son bootstrap
  couvre la vraie valeur au taux nominal. Sans ce test, une dérive de
  l'estimateur serait lue comme un effet de modèle.
- **Covariance d'échelle**, conservée en non-régression (exacte à 3·10⁻¹⁴).

---

## 8. Décisions à trancher — et ce que je recommande

| # | question | recommandation | pourquoi elle est ouverte |
|---|---|---|---|
| 1 | nom du dossier et du paquet | `m4_4_rebond_credit_soc/`, paquet `m4_4` | convention de l'utilisateur ; trivialement changeable |
| 2 | **portée partielle** | **maintenir l'interdiction** | l'interdiction était formulée « pour la v2 » et ce programme n'est pas v2. Mais v1 a montré que le dénominateur de toute élasticité y disparaît, et §1 se traite entièrement en portée globale et `new`. **Aucun lot ne dépend de la réponse** — c'est à l'utilisateur de la rouvrir s'il le veut |
| 3 | **σ devient-il un axe balayé ?** | **pas dans les lots A–E** | c'est le plus grand écart de régime entre les lignées (0,01 ici, 0,25 au centre M4B) et le candidat n°1 pour l'écart de b. Mais un balayage en σ est un programme en soi : M4B en a fait un. Le lot F l'aborde par une **ablation**, pas par un balayage |
| 4 | pas d'échantillonnage k des panneaux | **à mesurer**, pas à choisir | porte du lot A |
| 5 | horizon des runs de queue | **sans précédent mesuré** | M4.2B a eu besoin de T = 3000 et ~90 min par graine sur ses cellules sévères. À mesurer sur une cellule avant d'engager la campagne du lot C |

---

## 9. Pièges de mesure, hérités et actifs

- **La couverture de queue, pas la courbure.** Ce qui a bloqué M4.2B est le
  nombre de points dans la queue extrême. Un protocole qui n'augmente pas la
  couverture ne fera pas mieux, quelle que soit la finesse du critère — c'est
  pourquoi le lot C a une **cible de couverture chiffrée** et un pilote C0 qui
  la dimensionne (§5), plutôt qu'un budget en jours.
- **Un instantané n'est pas une cellule.** L'écart-type bootstrap
  intra-instantané vaut ≈ 3,7× l'écart-type inter-graines : ne jamais publier
  un α̂ d'instantané avec l'incertitude d'une moyenne de cellule.
- **La mesure d'avalanche inter-pas percole** dès que la densité d'événements
  est haute (M4 fable) : à 30 morts par pas, vérifier que les avalanches
  restent séparables avant d'ajuster quoi que ce soit.
- **r² > 0,90 hors taille 1 ne suffit pas** (M4 fable) : contrôler
  racines/taille et profondeur, sinon des grappes synchronisées passent pour
  des cascades.
- **Le canal de liquidité est muet.** \fait{} Mesuré sur v2 :
  `roots_liquidity` = 0 et `defaults` = 0 sur toute la campagne ; la débitrice
  la plus tendue détient 3,27 fois ce qu'elle doit. La contagion y est
  **purement de bilan**, conforme à M4B en dessous de σ ≈ 0,85. Tout
  raisonnement sur la liquidité dans ce régime est hors sujet.
- **Le contrôle §14.2 s'applique à ce plan.** Un balayage à un levier à la
  fois autour d'un point unique produit un R² groupé qui n'est que la droite
  joignant les lignes de base — v2 s'y est fait prendre et l'a documenté.
  Ajuster **dans** chaque famille, et exiger une étendue d'au moins ×3.
- **L'instant de mesure décide du résultat.** L'identité du §3.1 ne se
  referme qu'avec l'effectif **producteur** ; avec l'effectif de fin de pas
  elle manque de 9 erreurs-types, pour une différence qui n'est que la
  mortalité intra-pas. v2 a porté cette correction dans le moteur ; toute
  grandeur nouvelle doit déclarer à quel instant du pas elle est prise.
- **Une identité n'est pas une confirmation.** Le §3.1 en est une ; le dire
  dans le rapport à chaque emploi.

---

## 10. Livrables

Les mêmes que v2, sans négociation :

- **code complet et fonctionnel** dans `m4_4_rebond_credit_soc/` — un système
  qui tourne, pas un squelette ;
- **rapport de conception** (`report/conception_m4_4.pdf`) : décisions
  d'architecture justifiées avec `fichier.py:ligne`, statut de la parité après
  chaque lot, décisions du §8 et comment elles ont été tranchées ;
- **rapport de résultats** (`report/rapport_final.pdf`) : protocole,
  résultats, figures, verdict, limites ;
- **compilation vérifiée** : trois passes après suppression des `.aux`/`.toc`,
  aucun `!`, aucune référence non définie, aucune macro sans source citée ;
- **`README.md`** et **`JOURNAL.md`** tenu **au fil de l'eau** ;
- **annexe de traçabilité** engendrée par script, refusant de produire une
  annexe dont une ligne serait sans rôle ;
- **tous les nombres cités dans le corps des rapports sont des macros
  engendrées** depuis `results/analysis/` — jamais recopiés à la main.

**Règles de rédaction**, inchangées : tout tableau de plus de quatre colonnes
est d'abord une figure ; aucune notation avant sa définition ; un calcul cité
est un calcul déroulé ; un paragraphe qu'on ne peut pas paraphraser est à
réécrire ; jamais de « meilleure technologie » ; renvoyer aux **sections**,
jamais aux numéros de figure.

---

## 11. Arborescence attendue

```
m4_4_rebond_credit_soc/
+-- PLAN_M4_4_REBOND.md          (ce document)
+-- m4_4/                        (paquet moteur FORKE de m4_3live_v2)
|   +-- model.py                 (+ persistance, panneaux, checkpoint)
|   +-- kernel.py                (repris tel quel)
|   +-- live.py                  (+ ecriture des morts/avalanches/panneaux)
|   +-- tension.py               (repris tel quel)
|   +-- tails.py                 (NOUVEAU : estimateurs de queue, bootstrap)
|   +-- cascades.py              (NOUVEAU : les deux estimateurs de b)
+-- driver/  web/  tests/  scripts/  results/  report/
+-- README.md  JOURNAL.md
```

---

## 12. Ce que ce plan ne promet pas

\incertitude{} Trois choses sont hors de portée, et il vaut mieux l'écrire
maintenant que le découvrir au lot G.

1. **Prouver que la queue de Pareto existe.** M4.2B a montré que la question
   n'est pas décidable avec ce volume de données. Ce programme la caractérise
   sous hypothèse.
2. **Un plan factoriel.** Les lots B à E balaient un levier à la fois. Le
   contrôle §14.2 dira jusqu'où cela porte ; il ne remplacera pas un plan
   factoriel, que le budget ne permet pas.
3. **Un verdict causal sur la fragilité.** Que le sens libre élève b est
   mesuré et apparié ; que ce soit *par* la chaîne du §3.3 reste une chaîne
   d'inférences cohérente avec les colonnes, et il faudrait une ablation par
   maillon pour la démontrer.
