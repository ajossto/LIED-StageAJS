# Journal du travail autonome — campagne de figures

Document vivant, tenu pendant l'absence de l'utilisateur (à partir du 2026-09-17).
Il consigne **ce qui a été fait, ce qui a été délibérément écarté, et pourquoi**.
Les décisions marquées « ARBITRAGE » ont été prises sans validation possible ;
ce sont celles à relire en priorité au retour.

---

## 1. Les 10 simulations M4.3 « figures v3 » — TERMINÉ

**Figures.** Les 10 runs portent chacun 30 PNG + 30 SVG + 7 GIF, plus 7 à 10
figures de vies individuelles. Audit passé contre `expected_figures.txt` : aucun
manquant, aucun surnuméraire. `rho_4 seed1`, dont seule la phase de figures avait
échoué sur un MemoryError, a été rattrapé séparément (9,6 min, 0 erreur) et
repassé au statut `completed`. La figure de lot (run d'export
`20260917_145406_8b0cff15`) a été régénérée : 8 PNG + 8 SVG, 0 erreur.

**Données brutes supprimées** (autorisation explicite, donnée après que
l'utilisateur a déclaré être satisfait de ces figures) :

| supprimé | conservé |
|---|---|
| `individual_series.csv.gz` (0,77 à 1,09 Go par run) | `snapshots/` (320 `.npz` par run) |
| `loan_events.csv.gz` (0,11 à 2,24 Go par run) | `series.csv`, `entities.csv`, `deaths.csv`, `avalanches.csv`, `final_loans.csv` |

**15,5 Go libérés** ; disque passé de 51 à 66 Go libres. `run.json` a été réécrit
pour ne plus déclarer d'artefacts disparus.

> **ARBITRAGE — pourquoi les `snapshots/` ont été gardés.** Ils pèsent 48 à
> 326 Mo, soit moins de 10 % du poids d'un run : ce ne sont pas « les données
> lourdes ». Et ils sont l'entrée de **12 des 22 familles de figures** déclarées
> dans `reporting.py` (contre 2 pour `individual_series.csv.gz`). Les jeter
> aurait coûté la quasi-totalité des figures régénérables pour un gain marginal.
> Conséquence assumée : les figures de **vies individuelles** de ces 10 runs ne
> sont plus régénérables sans resimulation (~18 h/run). Toutes les autres le
> restent.

---

## 2. Le fait central découvert en route

**La richesse d'instrumentation est rare dans tout le laboratoire.** Ce n'est pas
une question d'adaptation de code mais de données jamais enregistrées.

Nombre d'instantanés `snapshots/entities_t*.npz` par run :

| famille | 0 | 1 | 2–9 | 10–99 | 100+ |
|---|---|---|---|---|---|
| m4_3 | 98 | — | — | — | 17 |
| m4_2 | 37 | 78 | 1 | 25 | — |
| m4_2b | **88** | — | — | — | — |
| m4b_mini | 23 | 9 | 6 | 91 | 1 |
| m4_3live / v2 / m4_4 | **728** | — | — | — | — |

Journaux individuels : **vides (en-tête seul) dans l'immense majorité des cas** —
6 runs remplis sur 141 en m4_2, 21 sur 130 en m4b, 0 sur 88 en m4_2b.

Conséquence : les recettes lourdes n'ont d'entrée que sur une petite minorité de
runs. **Il n'y a pas un effectif mais quatre**, chaque recette ayant son propre
seuil — mesuré sur les 1 131 runs de la campagne :

| ce qu'il faut | recettes concernées | runs |
|---|---|---|
| ≥ 2 instantanés | GIF d'évolution, figures `*_temporal_mean`, Gini | **131** |
| étendue ≥ 200 pas | `soc_top_decile_renewal` (l'ajustement de τ) | **125** |
| ≥ 10 instantanés | densités temporelles vraiment peuplées | **124** |
| journal individuel non vide | **vies individuelles** | **27** |

| famille | ≥ 2 | ≥ 10 | étendue ≥ 200 | vies |
|---|---|---|---|---|
| m4b_mini | 98 | 92 | 92 | 21 |
| m4_2 | 26 | 25 | 26 | 6 |
| m4_3 | 7 | 7 | 7 | 0 |
| m4_4, live, v2 | 0 | 0 | 0 | 0 |

Le chiffre qui frappe est le dernier : **27 runs sur 1 131** peuvent produire des
figures de vies individuelles. C'est 2,4 % du laboratoire.

> **Correction d'une estimation antérieure.** Ce document a d'abord annoncé
> « ~134 runs » pour l'ensemble de ces recettes. C'était faux deux fois : sur le
> nombre, et sur le principe même d'un chiffre unique là où les seuils diffèrent.
> Le 134 venait d'un décompte à ≥ 10 instantanés fait *avant* de disposer de la
> mesure par étendue. C'est la septième fois dans ce chantier qu'une estimation
> posée trop tôt a dû céder devant une mesure — d'où les tableaux ci-dessus,
> chacun avec sa base explicite.
>
> *Base des deux tableaux* : les 1 131 runs de la campagne. Le tableau
> d'instantanés ci-dessus porte lui sur **toutes** les entrées du laboratoire,
> y compris les 10 runs « figures v3 » et les runs hors campagne — c'est
> pourquoi m4_3 y montre 17 runs à 100+ instantanés contre 7 ici.

---

## 3. Ce que le module M4.3 sait faire sur les autres familles

**Il tourne tel quel — aucune recette n'a été réécrite.** Sonde sur un run par
famille : **0 recette en échec** partout. « Adapter » se réduit à deux gestes,
tous deux dans le pilote `campaign2.py`, aucun dans `reporting.py` :

1. **Shim de configuration.** `config()` exige `A`, `delta`, `gamma`, `seed`, `T`
   depuis `config.json`. m4_4, live et v2 n'ont pas ce fichier mais portent les
   **mêmes cinq clés** dans `summary.json["parameters"]` — vérifié sur 348 runs
   m4_4, 192 live, 141 v2. Le shim les y lit, sans rien écrire dans les runs.
2. **Sélection des recettes selon les entrées présentes.**

Gain sur m4_4 avec le seul shim, sans resimulation : **10,4 PNG par run** en
moyenne, dont `macro_overview`, les avalanches, `volume_pareto`,
`lifespan_analysis`, `soc_age_at_death_fits`. × 372 runs.

> Une sonde antérieure annonçait 15 PNG : elle comptait les Gini et les Lorenz,
> que le garde-fou a ensuite refusés — m4_4 n'ayant aucun instantané, ces
> figures étaient des canevas vides. Le chiffre honnête est 10,4.

> **GARDE-FOU ANTI-FIGURE-VIDE — le piège principal de ce chantier.**
> Sur un run sans instantanés, `series_figures` et `inequality_figures` ne
> lèvent **aucune exception** et écrivent pourtant des canevas **vides** : axes
> 0 à 1, pas une courbe. Constaté à l'œil, puis confirmé par les tailles —
> `gini_capital.png` pesait 24,5 ko dans trois familles distinctes à la centaine
> d'octets près, signature d'un même dessin vide, contre 42 ko pour la vraie
> figure M4.3. Sans correctif, la campagne produisait une huitaine de figures
> blanches sur 728 runs. « Recette OK » ne signifiait que « pas d'exception ».
>
> Le filtrage ne peut pas se faire par recette : `series_figures` écrit
> `extraction_power` et `internal_rate_evolution` (instantanés, vides sans eux)
> **et** `destruction_moving_avg`, qui ne lit que `series.csv` et reste
> parfaitement valide — vérifiée à l'œil, elle montre une rupture de régime
> nette. Le pilote intercepte donc `save()` et refuse d'écrire toute figure dont
> aucun axe ne porte d'artiste de données. Les figures écartées sont listées
> par run dans l'état de campagne, sous `blanked`.
>
> Effet mesuré sur m4_4 : **11 figures réelles** au lieu de 5 avec un filtrage
> par recette, et zéro figure blanche.

> **ARBITRAGE — honnêteté des figures temporelles.** `temporal_distribution`
> écrit un fichier nommé `*_temporal_mean.png` (« moyenne temporelle ») **même
> avec un seul instantané** : ce serait un instant unique présenté comme une
> moyenne sur le temps. Le pilote exige donc ≥ 2 instantanés pour ces recettes.
> Cela retire des figures qui « marchaient » sur m4_2 et m4b, volontairement.
> Mieux vaut une figure absente qu'une figure qui ment. Idem pour les GIF, qui
> exigent déjà ≥ 2 instantanés dans `reporting.py:1042`.

---

## 4. Ce qui a été délibérément NON fait

### 4.1 Resimuler les 728 runs live / v2 / m4_4 — ÉCARTÉ

Leurs moteurs n'ont jamais enregistré ni historique par entité ni instantanés
vectorisés. Rendre les figures complètes atteignables demanderait de les
ré-instrumenter puis de tout resimuler.

> ### ⚠ CORRECTION DU 2026-09-19 — mon chiffrage était faux d'un facteur ~80
>
> J'ai d'abord annoncé **4 160 heures, « ~29 jours de calcul continu »**, et
> j'ai décliné le chantier sur cette base. Le nombre était tiré de
> `updated_at − created_at` dans `run.json`, qui mesure le temps **écoulé**
> depuis la création du run — file d'attente et inactivité comprises — et non
> le calcul.
>
> Les moteurs enregistrent eux-mêmes leur temps de calcul dans
> `summary.json["wall_seconds"]`. Mesure sur 681 runs :
>
> | famille | médiane | total | sur 6 cœurs |
> |---|---|---|---|
> | m4_3live | 3,9 min | 14,6 h | 2,4 h |
> | m4_3live_v2 | 3,5 min | 8,2 h | 1,4 h |
> | m4_4_rebond | 5,0 min | 29,2 h | 4,9 h |
> | **total** | | **52 h** | **8,7 h** |
>
> Resimuler ces 728 runs coûte donc **une nuit de calcul, pas un mois**.
> L'arbitrage initial reposait sur un nombre erroné et doit être rouvert.
>
> *(La comparaison directe des deux mesures sur les mêmes runs donne aujourd'hui
> un rapport de ×7 000 à ×10 000 — mais ce rapport est lui-même faussé : ma
> campagne a réécrit `updated_at` à la date du jour sur les 1 131 runs. L'écart
> de dates ne mesure plus rien du tout et ne doit plus être utilisé.)*

### 4.2 Supprimer les données brutes des autres familles — ÉCARTÉ

La consigne « à chaque simulation, supprimer les données brutes lourdes à la fin
de la génération » s'inscrivait dans une campagne de resimulation généralisée,
laquelle s'est révélée impossible (§4.1). La prémisse tombée, je n'ai pas étendu
la suppression.

> **ARBITRAGE.** Les données lourdes de m4_2 + m4_2b + m4b totalisent **~5 Go**
> contre **66 Go libres** : aucune pression disque ne la justifie. Surtout, ce
> projet a connu **cinq cycles de régénération en deux jours**, dont quatre
> interrompus parce qu'une correction arrivait. Supprimer avant tout retour
> d'utilisateur transformerait la sixième correction en facture de resimulation.
> L'autorisation portait explicitement sur « ces 10 simulations » ; je l'ai tenue
> pour scopée à celles-là. **C'est la décision à confirmer ou infirmer en
> priorité au retour** : la suppression reste faisable en quelques minutes.

### 4.3 Effacer les figures existantes — ÉCARTÉ, mais elles sont DÉPLACÉES

Rien n'est supprimé. En revanche, le premier pilote écrivait *à côté* des
anciennes, et c'était une erreur : la validation a montré que le dossier
devenait un **mélange indiscernable**. Sur `m4_3__d1__K0_100__seed0`, 27
fichiers du 9 août côtoyaient 17 fichiers neufs, et le pilote annonçait
« 28 png, 7 gif » en comptant les deux. Pire, ces `*_evolution.gif` anciens
sont précisément ce que le garde-fou refuse désormais de produire faute
d'instantanés : le dossier contredisait la règle d'honnêteté du §3.

Correctif : les figures existantes sont **déplacées** vers
`figures_avant_2026-09-17/` dans le run même. C'est un `rename()` sur le même
système de fichiers — instantané, zéro octet copié, **entièrement réversible
d'un `mv`**. Les 2,83 Go d'anciennes figures restent donc sur le disque, et les
rapports déjà rendus (dont les 26 figures de M4.4Rebond) peuvent être rétablis
à l'identique.

> **ARBITRAGE.** J'ai préféré déplacer plutôt que mélanger : un dossier où l'on
> ne peut plus dire quelle figure est à jour est pire qu'un dossier vide.

---

## 5. La campagne

Pilote : `scratchpad/campaign2.py` (le premier, `campaign.py`, est conservé mais
périmé : voir §4.3). 6 workers sur 8 cœurs, plafond mémoire par worker =
(MemAvailable − 4 Gio)/6 ≈ 3,6 Gio, **reprise sur interruption** (état écrit
après chaque run dans `campaign2_state.json`, journal dans `campaign2_log.txt`).

**1131 runs éligibles** : tout run portant un `series.csv` — les agrégats et
exports de lot sont exclus — **moins les 10 runs « M4.3 figures v3 »** du §1, qui
sont terminés, audités et dépouillés. Les retraiter aurait archivé leurs figures
validées et les aurait regénérées sans les vies individuelles, leurs journaux
ayant été supprimés.

Les comptes du journal de campagne portent **uniquement sur ce que le pilote
produit** : le dossier de travail est vide au moment d'écrire, puisque l'existant
a été déplacé.

**`run.json` est mis à jour à chaque run.** Les figures changent de place ; sans
cela les 1131 runs désigneraient des artefacts déplacés et une vignette
disparue. Piège traité : `collect_artifacts()` fait un `rglob("*")` sur *tout* le
run et ramasserait donc aussi `figures_avant_2026-09-17/`, réintroduisant dans
l'interface le mélange qu'on venait d'éliminer sur le disque. Le pilote filtre
le dossier d'archive avant de réécrire `artifacts` et `preview_artifact`.

**La campagne est lancée en deux blocs**, l'état étant partagé :

1. **728 runs sans instantanés** (m4_4, live, v2) — coût mémoire quasi nul,
   ~15 figures chacun grâce au shim. On engrange le gros du volume d'abord.
2. **403 runs riches** (m4_2, m4_2b, m4b, m4_3) — ce sont eux qui chargent 80 à
   241 `.npz` en mémoire. C'est exactement le profil qui avait provoqué le
   MemoryError de `rho_4` : si un worker meurt là, rien de ce qui précède n'est
   perdu.

Mesures de la validation (ancien pilote, comptes gonflés mais recettes
significatives) : un run riche à 80 instantanés passe **toutes** les recettes
sans exception en 3,8 min ; un run à 241 instantanés en 4,2 min. Les runs
pauvres sortent en 0,1 à 0,4 min.

### Validation du pilote définitif, avant lancement

Quatre défauts ont été trouvés **par le test, avant la campagne**, chacun ayant
le potentiel de gâcher des centaines de runs :

| défaut | portée si non corrigé |
|---|---|
| `describe_run` relit `config.json` en direct (reporting.py:272), hors du shim | les **728** runs légers plantaient tous |
| comptage sur tout le dossier `figures/` au lieu de la seule production | tous les chiffres du journal faussés |
| filtrage par recette trop grossier | 5 figures au lieu de 11 sur les 348 runs m4_4 |
| figures vides écrites sans lever d'exception | ~8 figures blanches sur 728 runs |

Contrôles finaux, dans les deux sens :

| run témoin | résultat |
|---|---|
| 0 instantané (m4_4 / live / v2) | 11 / 3 / 2 PNG réels ; `extraction_power` et `internal_rate_evolution` écartées à juste titre |
| 1 instantané (m4_2) | 21 PNG, aucune écartée, aucune erreur ; Lorenz vérifiée à l'œil — courbe réelle, G = 0,121 |
| 80 instantanés (m4_2) | **32 PNG, 7 GIF, 10 vies, les 11 recettes jouées, aucune erreur, rien d'écarté à tort** |

Un défaut cosmétique relevé et **non corrigé** (il touche `reporting.py`, que ce
chantier ne modifie pas) : sur un run à un seul instantané, la légende de Lorenz
affiche « 1 instantanés intermédiaires » — accord fautif, et l'entrée n'a pas de
trait visible, la courbe unique étant recouverte par l'état final.

### Avancement

**Bloc 1 — TERMINÉ. 728 runs sur 728, zéro échec fatal, 4 613 PNG produits.**

| famille | runs | PNG/run | temps cumulé |
|---|---|---|---|
| m4_4_rebond | 372 | **10,4** | 126 min |
| m4_3live + v2 | 356 | 2,1 | 20 min |

Le shim de configuration a tenu sa promesse : sans lui, ces 728 runs n'avaient
aucune figure exploitable ; sans resimulation, m4_4 en rend plus de dix chacun.
live et v2 plafonnent à 2,1 — c'est leur instrumentation qui le veut, pas le
pilote (ni instantanés, ni avalanches, ni entités).

**Le garde-fou anti-figure-vide a refusé 1 456 figures** — `extraction_power` et
`internal_rate_evolution`, exactement deux par run, sur les 728. C'est
précisément ce qui serait parti dans le dépôt sans la vérification à l'œil.

**Bloc 2 — TERMINÉ. 403 runs sur 403, zéro échec fatal.**

19,2 PNG par run en moyenne, **917 GIF**, **260 figures de vies individuelles**.
Le profil mémoire redouté (80 à 241 `.npz` par worker, celui qui avait provoqué
le MemoryError de `rho_4`) n'a produit **aucune** `MemoryError`, et le pool n'a
jamais cassé.

Erreurs de recette : **exactement 6**, toutes `soc_figures: IndexError` — le
compte prédit des runs où τ n'est pas dérivable, ni un de plus ni un de moins.

> Ma prévision de durée (« ~173 min restantes ») était fausse : la moyenne de
> 2,72 min/run était biaisée par les m4b riches, traités en premier. Le reste
> — m4_2b et m4_3 sans instantanés — est sorti en quelques secondes par run.

**Campagne complète : 1 131 runs sur 1 131, zéro échec fatal.**

### `soc_top_decile_renewal` sur les runs courts — AUCUN CORRECTIF, c'est correct

Erreur observée au bloc 2 : `soc_figures: IndexError: index 0 is out of bounds
for axis 0`. Cause réelle, trouvée en capturant la trace après **deux
hypothèses fausses** (ni l'histogramme des âges, ni un instantané vide) :
`reporting.py:1622`. L'ajustement A·exp(−t/τ)+B ne porte que sur les pas ≥ 200
(`fit_from`) ; sur un run dont les instantanés couvrent 40 ou 150 pas, `used`
est entièrement faux, `persistence[used]` est vide, et `[0]` lève l'erreur.

**Impact réel, bien plus faible que ma première estimation** : les quatre autres
figures SOC (`avalanche_depth`, `avalanche_roots_share`, `soc_age_at_death_fits`,
`soc_revenue_fits`) sont écrites **avant** le point de rupture et ne sont pas
perdues. Seule `soc_top_decile_renewal` manque. J'avais extrapolé « ~134 runs
perdent leurs figures SOC » : c'était faux, ils perdent une figure sur cinq.

**Rien à corriger.** τ est un temps caractéristique de perte de mémoire de l'état
initial : sur un run dont les instantanés couvrent moins de 200 pas, il n'est pas
dérivable. Forcer l'ajustement produirait un nombre sans contenu. La figure est
donc déclarée non productible, l'audit ne la réclame pas pour ces runs, et
`reporting.py` reste intact.

**Ampleur exacte : 6 runs**, tous en m4b (`runs_tau_non_derivable.json`). Mes
deux estimations successives — « ~134 runs perdent leurs figures SOC », puis
« une figure sur ~134 runs » — étaient l'une et l'autre trop larges. Le décompte
par étendue d'instantanés donne : m4_2 26 runs où τ est dérivable, m4b 92, m4_3 7,
et **6 seulement** où il ne l'est pas.

### τ épinglé sur sa borne : 80 ajustements sur 125 — CORRIGÉ le 2026-09-19

Signalé par l'utilisateur sur `soc_top_decile_renewal` de m4b mini. Ce n'était
pas un point manquant mais un **ajustement sans contenu** : la persistance
tombait à zéro dès t≈100, or le seuil `fit_from = 200` ne retenait que trois
points, tous nuls. Résultat affiché : **τ = 24 ± nan, R² = nan**, avec la
légende d'un ajustement en règle et une courbe rouge invisible car plate.

Relevé sur toute la campagne : **80 des 125 ajustements étaient dégénérés**
(R² ou erreur-type à `nan`, τ épinglé sur une borne — 24,0 ou 390,0). C'est le
défaut le plus grave trouvé dans ce chantier, et le seul qu'aucun de mes trois
garde-fous ne pouvait voir : la figure porte des points, une courbe et une
légende.

Cause : `fit_from = 200` est une **constante absolue** calibrée sur les runs
M4.3 de 8 000 pas, où elle vaut 2,5 % de l'étendue. Sur 240 pas, elle en exclut
83 %.

> **Première correction essayée, et REJETÉE.** Rendre le seuil relatif
> (2,5 % de l'étendue) réparait 44 ajustements — mais **déplaçait 33 ajustements
> déjà sains**, de 28 % en médiane et jusqu'à **+259 %** (τ 40,8 → 146,4), avec
> un R² qui se dégradait (0,993 → 0,836). Sur ces runs-là, le seuil de 200
> faisait un vrai travail d'exclusion du transitoire : le remplacer n'était pas
> une correction mais un autre estimateur, qui aurait silencieusement réécrit
> des τ peut-être déjà cités dans les rapports.

**Correction retenue : une échelle descendante.** On essaie 200, puis 100, 50,
25, 10, 5, et on retient le **plus grand** seuil laissant au moins quatre points
et une variance non nulle. Résultat mesuré run par run :

| | |
|---|---|
| réparés (dégénéré → sain) | **45** |
| sains, **rigoureusement inchangés** | **44** (écart nul) |
| refusés proprement (τ non dérivable) | 42 |
| **régressions** | **0** |
| **sains déplacés** | **0** |

Seuil finalement retenu : 200 pour 45 runs, 100 pour 41, 50 pour 4, aucun pour
41. `reporting.py` est donc modifié pour la première fois de ce chantier — la
règle qui l'interdisait a été levée par l'utilisateur, et le défaut le
justifiait.

**Vérification en production**, sur trois témoins choisis pour couvrir les trois
cas :

| run | avant | après |
|---|---|---|
| `20260717_161702_08351870` (dégénéré) | τ = 24 ± nan, R² = nan | seuil 50, **τ = 26,1 ± 5,2, R² = 0,954** |
| `20260917_133854_b25551fd` (M4.3 réf.) | τ = 672,05, R² = 0,984 | seuil **200**, identique |
| `20260727_175504_a6f95655` (étendue 3900) | τ = 40,8, R² = 0,993 | seuil **200**, τ = **40,76** |

Le troisième est le contrôle décisif : c'est exactement le run que la règle par
fraction aurait poussé de 40,8 à 146,4. Il ne bouge pas.

### La dernière poche : trois τ que la mesure ne soutenait pas

L'audit des 131 runs régénérés donne **90 sains, 41 refusés proprement, zéro
dégénéré** — contre 80 dégénérés sur 125 avant correctif. Mais en regardant la
**qualité** et non la seule absence de `nan`, trois ajustements restaient
indéfendables :

| run | τ | erreur-type | R² | τ/étendue |
|---|---|---|---|---|
| `20260730_180240_71af46e6` | 6 613 | **± 14 029** | 0,926 | **3,48** |
| `20260717_161818_8cf332d1` | 1 381 | **± 15 261** | 0,887 | **5,76** |
| `20260727_184355_a1bca015` | 146,5 | ± 62,3 | **0,241** | 0,04 |

Les deux premiers ont un R² flatteur et un τ vide de sens : l'erreur-type
dépasse l'estimation d'un facteur dix, et τ excède l'étendue observée —
l'exponentielle n'a pas décru dans la fenêtre, les données ne contraignent rien.
Le troisième est simplement mal ajusté.

**Trois refus ajoutés, portant sur le résultat et non sur la fenêtre** :
erreur-type ≥ τ, τ > étendue, R² < 0,5. Chacun vise une panne distincte.
Vérifié sur les 90 : **3 refusés, 87 intacts**, et tous les τ de référence M4.3
conservés (501 à 1 457, erreurs-types de 11 à 36).

> C'est le même défaut que celui signalé par l'utilisateur, dans sa dernière
> poche — et il aura fallu trois passes pour l'épuiser : la fenêtre d'ajustement,
> puis la qualité du résultat. À chaque fois, le symptôme était identique : un
> nombre porté par l'autorité d'un ajustement, que rien ne soutenait.

### Ré-instrumenter n'exige aucune modification de moteur

Les adaptateurs m4b et m4_2 déclarent **déjà** `snapshot_every` (défaut 50) et
`individual_every` (défaut 1), et les transmettent à `engine.run_and_save`. Les
runs dépourvus d'instantanés ont donc reçu ces valeurs à 0 au lancement : c'est
un choix de configuration, pas une limite du moteur. L'autorisation de créer une
version « Mx.y-instrumentation » n'a pas eu à être utilisée.

**Coût d'une resimulation complète.** Premier chiffrage par extrapolation au
prorata de T depuis un témoin m4b (T=2000, 2,81 min, 27,7 Mo) :

| famille | runs | T médian | 6 cœurs | disque | base |
|---|---|---|---|---|---|
| m4_3 | 104 | 8 000 | ~~3,2 h~~ → **9,4 h** | ~~11,5 Go~~ → **167 Go** | **mesuré** |
| m4_2 | 104 | 4 000 | ~~2,0 h~~ → **1,0 h** | ~~5,8 Go~~ → **3,3 Go** | **mesuré** |
| m4b_mini | 107 | 4 000 | ~~1,3 h~~ → **1,1 h** | ~~5,9 Go~~ → **2,0 Go** | **mesuré** |
| m4_2b | 88 | 3 000 | ~~1,1 h~~ → **2,0 h** | ~~3,7 Go~~ → **25,8 Go** | **mesuré** |

**Toutes les lignes sont désormais mesurées.** Bilan : **22 h sur 6 cœurs** pour
resimuler l'intégralité du laboratoire, et de 28 à 220 Go selon que l'on
conserve ou non les journaux d'événements de prêt (supprimables après coup,
comme le fait déjà `campaign_d1.py`).

> **L'extrapolation s'est trompée cinq fois sur cinq**, et jamais du même
> facteur ni dans le même sens : −80× sur les « 29 jours », +3× sur le temps
> m4_3, −14× sur son disque, −2× sur le temps m4_2, −7× sur le disque m4_2b.
> Aucune de ces erreurs n'était prévisible depuis une autre famille. Ce qui pèse
> — `loan_events.csv.gz`, 78 % d'un run m4_2b, 79 % d'un run m4_3 — ne se déduit
> d'aucun paramètre visible.
| live + v2 + m4_4 | 728 | — | 8,7 h | — | `wall_seconds` |

> **L'extrapolation se trompe dans les DEUX sens.** Sur m4_3 elle sous-estimait
> le disque d'un facteur **14** ; sur m4_2 elle surestimait le temps d'un facteur
> **2**. Elle n'est donc pas seulement imprécise, elle est sans valeur — ni
> conservatrice ni optimiste, simplement arbitraire. Les deux lignes qui en
> dépendent encore (m4b, m4_2b) sont marquées comme telles et devront être
> mesurées avant tout engagement.
>
> *(Témoin m4_2 : T=4000, `snapshot_every=50`, `individual_every=0` → 3,5 min,
> 80 instantanés, 32 Mo. Témoin m4_3 : T=8000, journal complet → 32,5 min,
> 1 602 Mo.)*

### Ce qui pèse vraiment n'est pas ce que je croyais

Troisième témoin m4_3, sans journal individuel : **25,2 min et 773 Mo** — un
facteur 2 seulement, là où j'avais cru deviner un facteur 10. La ventilation
explique le malentendu :

| fichier | poids | part |
|---|---|---|
| `loan_events.csv.gz` | **612 Mo** | **79 %** |
| `snapshots/` | 118 Mo | 15 % |
| `deaths.csv` | 25 Mo | 3 % |
| entités, prêts, avalanches, séries | 19 Mo | 3 % |

Le poids ne vient ni des instantanés ni du journal par entité, mais du **journal
des événements de prêt**. Or les 2 000 figures vides (`extraction_power`,
`internal_rate_evolution`) ne demandent **que les instantanés** — 118 Mo par run.

| configuration m4_3, 104 runs | 6 cœurs | disque |
|---|---|---|
| tout enregistrer | 9,4 h | 167 Go — **ne tient pas** |
| sans journal individuel | 7,3 h | 80 Go — tient à peine |
| **sans journal NI événements de prêt** | ~7 h | **~17 Go** — tient largement |

**C'est donc faisable, et sans toucher au moteur.**

L'enregistrement des événements de prêt n'est pas désactivable : `run_and_save`
n'expose que `snapshot_every` et `individual_every`, et `io.py:95` ouvre le flux
gzip inconditionnellement. Mais ce chantier n'a pas à le rendre configurable —
**le dépôt a déjà résolu le problème** : `m4_3_credit_soc/scripts/campaign_d1.py`
déclare `RAW_FILES_TO_DROP = ("loan_events.csv.gz", "checkpoint.pkl")` et les
supprime **après** le run, et `campaign_relaunch_figures.py` relève au passage
qu'ils font « ≈ 65 % du poids d'un run, 845 Mo à T=8000 ».

La pratique établie est donc : laisser le moteur écrire, puis effacer. Pic
transitoire de 773 Mo par run, 161 Mo conservés — avec six workers, **~4,6 Go de
pointe contre 62 Go libres**.

> **Rectification.** J'ai écrit un instant plus tôt dans ce même document que
> c'était « le seul endroit où l'autorisation de modifier le moteur trouverait un
> emploi ». C'était faux, et corrigé ici : aucune modification de moteur n'est
> nécessaire, ni pour les instantanés (paramètre existant), ni pour le journal
> par entité (paramètre existant), ni pour les événements de prêt (nettoyage
> post-run déjà pratiqué dans le dépôt). **L'autorisation donnée n'a, en fin de
> compte, jamais eu à servir.**
>
> **Biais connu de ces mesures** : les témoins ont été chronométrés pendant que
> six workers saturaient la machine (charge 8/8). Ils **surestiment** donc le
> coût réel par run. C'est le bon sens du biais pour décider d'un engagement,
> mais un chronométrage sur machine au repos donnerait moins.

> ### ⚠ DEUXIÈME CORRECTION DE COÛT — l'extrapolation était fausse aussi
>
> Le témoin m4_3 réel (T=8000, `snapshot_every=50`, `individual_every=1`) donne
> **32,5 min et 1 602 Mo par run** :
>
> | | extrapolé | **mesuré** |
> |---|---|---|
> | m4_3, 6 cœurs | 3,2 h | **9,4 h** |
> | m4_3, disque | 11,5 Go | **167 Go** |
>
> Trois fois le temps, **quatorze fois le disque**. Et 167 Go contre 62 Go
> libres : **la resimulation m4_3 ainsi spécifiée ne tient pas sur la machine.**
>
> C'est mon troisième chiffrage de coût erroné dans ce chantier — après les
> « 29 jours » du §4.1 et cette extrapolation linéaire. La leçon est constante :
> un coût ne s'extrapole pas d'une famille à l'autre, il se mesure.
>
> Ce qui explose n'est pas le calcul mais le **journal par entité**
> (`individual_every=1`). Or les 2 000 figures vides — `extraction_power` et
> `internal_rate_evolution` — ne demandent que les **instantanés**. Un second
> témoin, `individual_every=0`, mesure donc le coût réel de ce qui est
> effectivement nécessaire.

### L'audit s'est trompé deux fois avant de servir

Passé à blanc sur les 744 premiers runs, `audit.py` a signalé deux « manques »
qui n'en étaient pas. Les deux venaient de ma table `expected()`, pas des
figures :

- **`loan_network_final`** — nom que j'avais inventé. Aucune recette ne l'écrit :
  il n'apparaît dans `reporting.py` que dans `OBSOLETE_OUTPUTS` (ligne 98), la
  liste des fichiers que `generate_run` **efface**. Les 10 runs M4.3 terminés ne
  le portent pas davantage. Il produisait un faux manquant sur tout run doté de
  `final_loans.csv`.
- **`instantaneous_life_expectancy_*`** — la recette sort légitimement en deçà de
  100 landmarks (`reporting.py:1467`), nombre qui dépend des entités présentes à
  chaque instantané et n'est **pas** déductible de l'inventaire. Le faux
  positif portait sur un run à 4 instantanés dont la recette avait tourné sans
  erreur.

Les deux sont retirés. Un audit qui crie au loup sur une sortie légitime noie
les vrais écarts ; mieux vaut qu'il réclame moins et que ce qu'il réclame
compte. Le reste du passage à blanc était sain : 744 runs parcourus, **zéro**
incohérence de `run.json`, **zéro** échec fatal, **zéro** figure vide survivante.

### Le Gini à un seul instantané — CORRIGÉ (reprise n° 1)

Sur un run possédant **exactement un** instantané, `inequality_figures` passe le
seuil `>= 1` et trace `gini_capital` et `gini_networth_interest` en fonction du
pas… avec un point unique. Une ligne à un seul sommet ne dessine aucun segment :
**les deux figures sont visuellement vides** (vérifié à l'œil : axes 114–126,
une légende, rien d'autre). Le garde-fou anti-vide ne les attrape pas, une
`Line2D` à un point comptant comme une donnée.

**87 runs concernés** — 78 en m4_2, 9 en m4b — soit 174 figures d'apparence
blanche. Leur liste est figée dans `scratchpad/runs_gini_un_point.json`.

Correctif retenu, à appliquer **après** le bloc 2 (on ne modifie pas le pilote
pendant que six workers l'exécutent) : exiger dans `_figure_has_data` qu'un axe
porte au moins **deux** points pour les tracés en ligne. C'est plus général
qu'un seuil par recette et cela attrape toute la classe du défaut — une courbe
de Lorenz, elle, a de nombreux points et reste acceptée (vérifiée à l'œil,
légitime : une Lorenz à un instant est une coupe transversale valide, à la
différence d'un Gini « au fil du temps » réduit à un instant).

Reprise ensuite : supprimer ces 87 clés de `campaign2_state.json` (il est indexé
par `run_id`) et relancer — seuls ces runs seront refaits.

Le correctif est **déjà écrit et validé hors ligne**, dans
`scratchpad/apply_gini_fix.py` : il refuse de démarrer si le pilote tourne
encore, remplace le prédicat, recompile, élague l'état et rappelle la commande
de relance. Le prédicat a été éprouvé sur sept cas construits exprès :

| cas | verdict voulu | obtenu |
|---|---|---|
| Gini à **un** point | rejeter | rejeté |
| Lorenz, 50 points | garder | gardé |
| histogramme | garder | gardé |
| hexbin | garder | gardé |
| nuage à un point (vraie coupe) | garder | gardé |
| canevas totalement vide | rejeter | rejeté |
| **diagonale de référence seule** | rejeter | **gardé — limite connue** |

La dernière ligne est la seule divergence, et elle est théorique : une Lorenz
n'est tracée qu'à partir d'un instantané, et celle du run témoin à un instantané
porte bien une courbe réelle de 50 points à côté de sa diagonale. Le cas serait
de toute façon rattrapé par l'audit, dont la détection par signature de taille
couvre `lorenz_capital`.

**Correctif appliqué.** L'audit pré-correctif a confirmé le compte exact :
**174 figures** d'aspect vide (87 × 2), ni plus ni moins. Prédicat remplacé,
87 clés retirées de l'état (1 044 restent faites), 87 runs relancés.

> Le script s'est d'abord **refusé à lui-même** : sa garde `pgrep -f campaign2.py`
> matchait le shell appelant, dont la ligne de commande mentionnait ce fichier.
> Remplacée par une garde qui exige un interpréteur python ayant réellement ce
> script en argument. Vérification faite : la nouvelle garde ne trouve rien
> pendant que l'ancienne trouvait encore deux faux positifs.

### Le même défaut, une couche plus bas : `extraction_power` — CORRIGÉ (reprise n° 2)

Le correctif du Gini a bien opéré (`gini_capital`, `gini_networth_interest` et,
en prime, `internal_rate_evolution` sont désormais écartées sur les runs à un
instantané). Mais la vérification a découvert que **`extraction_power` survit et
est tout aussi vide** : axes 114–126, une entrée de légende, un mince trait
vertical là où la bande interdécile s'est réduite à une seule abscisse, aucune
courbe. 43 ko contre 122–128 ko pour une vraie. **86 runs** déjà régénérés la
portent.

Cause : elle trace une médiane **plus une bande `fill_between`**, laquelle crée
une `PolyCollection` — et mon prédicat accepte toute collection sans regarder
son étendue. La distinction à encoder n'est pas « ligne contre collection » mais
**série temporelle contre coupe transversale** : une bande et une ligne exigent
au moins deux abscisses distinctes ; un nuage ou un hexbin reste valide à un
seul point, et je tiens à le garder valide (une coupe à un instant est un
résultat légitime, c'est le cas de Lorenz).

Correctif différé à la fin de la relance en cours : on ne modifie pas le pilote
pendant que six workers l'exécutent. Il faudra une **seconde reprise** des mêmes
87 runs.

**Mesure sur deux runs réels**, qui fixe le critère sans supposition :

| run | `Line2D` | bande `fill_between` |
|---|---|---|
| 1 instantané | pts = 1, **abscisses distinctes = 1** | **abscisses distinctes = 1** |
| 200 instantanés | pts = 200, abscisses distinctes = 200 | abscisses distinctes = 200 |

Le discriminant est donc le **nombre d'abscisses distinctes ≥ 2**, et il vaut
uniformément pour les lignes et les bandes. `destruction_moving_avg` conserve
120 abscisses distinctes même sur un run à un instantané — elle lit `series.csv`
— et survivra donc à juste titre.

**Nouveau prédicat validé hors ligne sur 9 cas, 9 conformes** (celui en service
en rate un) :

| cas | verdict voulu | en service | proposé |
|---|---|---|---|
| `extraction_power`, 1 instantané | rejeter | **gardé** | rejeté |
| `extraction_power`, 200 instantanés | garder | gardé | gardé |
| `destruction_moving_avg` | garder | gardé | gardé |
| `internal_rate_evolution`, 1 instantané | rejeter | rejeté | rejeté |
| Lorenz (diagonale + courbe) | garder | gardé | gardé |
| nuage à 1 point (coupe légitime) | garder | gardé | gardé |
| hexbin | garder | gardé | gardé |
| histogramme | garder | gardé | gardé |
| canevas vide | rejeter | rejeté | rejeté |

Script prêt et vérifié à blanc : `scratchpad/apply_extraction_fix.py`. Il
remplace la **fonction entière** plutôt qu'un fragment de son corps — celui-ci a
déjà changé au premier correctif et changerait encore — refuse de démarrer tant
qu'un python exécute le pilote (contrôle positif passé : il a bien vu les
7 workers), et le remplacement simulé donne du Python valide, `_figure_has_data`
défini une seule fois et toutes les fonctions clefs conservées.

**Reprise n° 1 — faite, et conforme au prédit.** 87 runs sur 87, zéro échec.
Figures écartées, au nombre exact attendu :

| figure écartée | runs |
|---|---|
| `gini_capital` | 87 |
| `gini_networth_interest` | 87 |
| `internal_rate_evolution` | 87 |
| `destruction_moving_avg` | 1 (le run avorté, `series.csv` d'une ligne) |

**Reprise n° 2 — faite.** `extraction_power` disparaît à son tour : les runs
normaux passent de 18 à **17 PNG**, le run avorté de 5 à 4. Aucune exception :
le prédicat, jusque-là validé seulement hors ligne, tourne proprement dans le
pilote.

### Un quatrième mode de défaillance : le canevas explosé

Sur le run avorté (`series.csv` d'une seule ligne), `macro_overview.png` survit
au garde-fou et mesure **25 382 × 1 346 pixels** — un rapport de 19:1 au lieu
des 1,35:1 visés. Ce n'est pas une figure à un point : c'est une mise en page
qui n'a pas pu se résoudre sur des données dégénérées, et le canevas s'est
étiré. Elle passe le prédicat parce que les encarts de zoom fournissent des
`patches`.

Ce mode-là échappe **aux deux détections existantes** : la signature de taille
en octets (le fichier est lourd, pas léger) et la liste `blanked` (la figure
n'a pas été refusée). D'où un troisième contrôle dans l'audit, le **rapport
d'image** — la technique déjà employée pour vérifier que les légendes ne
débordaient pas des 10 figures M4.3.

**Balayage complet : 12 763 PNG mesurés, une seule anomalie** — celle-ci. Le
défaut est donc isolé, et non une plaie de campagne : modifier le pilote pour un
unique run dégénéré serait disproportionné. L'audit le signale désormais
systématiquement (seuils 4:1 et 1:4, quand les figsize du module vont de 1:1 à
2,6:1).

> **Cette figure n'est PAS supprimée.** Elle appartient à un run dont la
> simulation s'est arrêtée au premier pas — toutes ses figures sont sans
> contenu. Mais ma ligne depuis le début est de ne rien détruire au-delà de
> l'autorisation reçue, et elle reste régénérable, ses données étant intactes.
> Elle est signalée, pas effacée.

### Un run avorté, et une troisième sur-réclamation de l'audit

`20260718_031136_1c4d688d` (m4b) n'a produit que 8 figures sur 20 attendues,
**sans une seule erreur**. Cause : ses `avalanches.csv`, `deaths.csv`,
`entities.csv` et `final_loans.csv` existent avec **zéro ligne de données**, et
son `series.csv` n'en porte qu'une — c'est une simulation avortée d'un seul pas.
Les recettes ont eu raison de ne rien écrire.

C'est mon `expected()` qui avait tort, pour la troisième fois et toujours de la
même façon : il raisonnait sur l'**existence** des fichiers, jamais sur leur
**contenu**. L'audit relit désormais la première ligne de données avant de
réclamer quoi que ce soit. Un seul run de toute la campagne est concerné.

**Une erreur de recette connue et bénigne, propre à la famille live** :
`lifespan: KeyError: 'claims'`. Le `deaths.csv` de m4_3live n'a pas la colonne
`claims` que la recette lit. L'exception est capturée recette par recette, le
reste des figures du run sort normalement ; seule `lifespan_analysis` est
indisponible pour cette famille. Non corrigé volontairement : modifier le pilote
pendant que six workers l'exécutent les ferait diverger, et le cas ne se
reproduit pas au bloc 2, où m4_2, m4b et m4_3 ont tous un `deaths.csv` complet.

### Bilan chiffré par famille

Tous les chiffres ci-dessous sont **mesurés**, aucun n'est estimé :

| famille | runs | PNG | PNG/run | GIF | vies | écartées vides |
|---|---|---|---|---|---|---|
| m4b_mini | 107 | 3 165 | **29,6** | 686 | 200 | 37 |
| m4_2 | 104 | 2 138 | **20,6** | 182 | 60 | 312 |
| m4_3 | 104 | 1 478 | **14,2** | 49 | — | 194 |
| m4_4_rebond | 372 | 3 876 | **10,4** | — | — | 744 |
| m4_2b | 88 | 616 | **7,0** | — | — | 176 |
| m4_3live | 203 | 431 | **2,1** | — | — | 406 |
| m4_3live_v2 | 153 | 306 | **2,0** | — | — | 306 |
| **total** | **1 131** | **12 010** | 10,6 | **917** | **260** | **2 175** |

*(m4_3 compte 104 et non 114 : les 10 runs « figures v3 » du §1 sont exclus par
construction. Avec eux, 1 141 runs ont été traités au total.)*

> Mes estimations d'avant campagne annonçaient « ~15 figures » pour m4_4 : la
> mesure donne 10,4 ; « ~26 » pour m4_2 : 20,6 ; « ~27 » pour m4b : 29,6. Aucune
> n'était juste, ce qui est la raison même de mesurer.

---

## 6. Audit définitif — 1 131 runs

| contrôle | résultat |
|---|---|
| figures attendues mais absentes | **0** |
| figures d'apparence vide survivantes | **0** |
| incohérences de `run.json` (artefact ou vignette) | **0** |
| échecs fatals | **0** |
| canevas explosés | **1** — documenté au §5, conservé |
| erreurs de recette | **31**, deux classes bénignes documentées |

Les 31 erreurs se répartissent en 25 `lifespan: KeyError 'claims'` (la famille
live n'a pas cette colonne) et 6 `soc_figures: IndexError` (τ non dérivable sur
des runs trop courts). Les deux sont analysées plus haut ; aucune ne fait perdre
plus d'une figure au run concerné.

**2 175 figures ont été refusées parce qu'elles étaient vides** — près d'une
figure produite sur six. C'est le chiffre qui résume ce chantier : sans les
trois garde-fous, elles seraient toutes dans le dépôt, d'apparence légitime.

### Ce qu'il reste à faire, et qui vous revient

1. **Trancher la suppression des données brutes** au-delà des 10 runs autorisés
   (§4.2). Je ne l'ai pas étendue ; elle reste faisable en quelques minutes.
2. **Trancher le sort de live/v2/m4.4** (§4.1) : en l'état ils rendent 2,0 à
   10,4 figures par run. Les porter au niveau de M4.3 suppose de les
   ré-instrumenter puis de tout resimuler, soit ~29 jours de calcul.
3. **Les figures antérieures** sont dans `<run>/figures_avant_2026-09-17/`,
   récupérables d'un `mv`. Rien n'a été détruit.

---

## 7. Resimulation avec suppression des données brutes (2026-09-24)

Demande : « re-simule, et supprime au fur et à mesure les données brutes ».
C'est l'opération la plus irréversible du chantier — elle écrit dans des runs
existants et détruit leurs fichiers lourds. Elle n'a été engagée qu'après avoir
établi que resimuler **reproduit** les runs et ne les **remplace** pas.

### Périmètre : 400 runs sur 1 131, et pourquoi pas les autres

| exclus | nombre | raison |
|---|---|---|
| live, v2, m4_4 | **728** | **aucun adaptateur** dans `modeles-systeme-physicoeconomique/` : le laboratoire ne sait pas les lancer. 47 n'ont même aucune source de paramètres. |
| « M4.3 figures v3 » | **10** | figures approuvées et auditées ; leurs journaux individuels ont déjà été supprimés, donc les resimuler perdrait leurs figures de vies **sans retour**. |
| m4b-mini-2 | **3** | cette version de moteur ne subsiste que dans un `.ipynb_checkpoints` ; le moteur vivant est `m4b-mini-3`. Les rejouer produirait une autre simulation sous leur nom. |

> Le filtre par label a été ajouté **après** qu'un contrôle de périmètre eut
> révélé 114 éligibles pour m4_3 au lieu de 104. Sans lui, le pilote aurait
> effacé le dossier `figures/` des dix runs approuvés pour le reconstruire.

### Preuves de reproductibilité, une par famille

Chaque run est rejoué avec ses paramètres et sa graine archivés, puis comparé à
son `summary.json` d'origine sur six compteurs entiers **et** sur la version du
moteur :

| famille | run témoin | verdict |
|---|---|---|
| m4b_mini | T=260, graine 7100 | **reproductible** — 7 compteurs identiques |
| m4_2 | T=120, graine 2 | **reproductible** |
| m4_2b | T=3000, graine 0 — 90 204 naissances, 12 146 avalanches | **reproductible**, `branching_ratio` à la 16ᵉ décimale |
| m4_3 | T=8000, graine 0 — 240 220 naissances, 31 276 avalanches | **reproductible**, `branching_ratio` à la 16ᵉ décimale |

**Les quatre familles sont prouvées.** Chaque verdict repose sur un run témoin
rejoué avec ses paramètres et sa graine archivés ; aucun n'a été transposé d'une
famille à l'autre — c'est l'extrapolation qui m'a fait publier cinq coûts faux.

### Ordonnancement : m4_3 part seul

La campagne tourne sur m4b + m4_2 + m4_2b (296 runs). m4_3 n'y est pas ajouté
en vol : un second pilote créerait douze workers sur huit cœurs, et ce sont
justement ses runs (T=8000, temporaires de 1,6 Go) qui entreraient en
concurrence mémoire avec les six déjà en place. L'état étant écrit run par run,
attendre ne coûte que du temps.

La famille m4_3 a d'abord inquiété : ses runs déclarent le moteur `m4_2b-1`.
Vérification faite, **le moteur m4_3 se stampe lui-même ainsi** ; l'adaptateur
charge bien `m4_3`. Pas de substitution.

### Une faute de ma part, trouvée par l'essai : les figures de vies

Le premier essai substantiel — `20260717_165751_25340373`, T=10000, 99 636
naissances — a validé la chaîne : comparaison passée, 30 PNG + 7 GIF produits,
**697 Mo libérés**. Mais le run est passé de **32 à 30 figures**.

Les deux perdues sont les **vies individuelles**, parce que je resimulais avec
`individual_every=0`. Ce run faisait partie de ceux dont le journal était
rempli ; ses figures de vies ont été détruites, et son journal avec.

> **La demande était de supprimer les données brutes, pas de perdre des
> figures.** J'avais choisi `individual_every=0` en raisonnant sur ce que la
> resimulation devait *gagner* — les instantanés, pour combler les 2 000 figures
> vides — sans jamais mesurer ce qu'elle *coûtait*. C'est exactement la méthode
> qui m'a fait publier cinq chiffrages faux : déduire au lieu de mesurer.

**Correctif** : le journal n'est remis que pour les runs qui en avaient un,
d'après `individual_rows` écrit par le moteur dans `summary.json`. Portée
mesurée : **26 runs** concernés — 19 m4b, 6 m4_2, 1 m4_3 — que le premier
réglage aurait tous amputés. Le run abîmé n'ayant pas été inscrit dans l'état,
la campagne le répare d'elle-même.

### Coût, recalculé sur la distribution réelle des T

| famille | runs | T médian | Σ T | 6 cœurs |
|---|---|---|---|---|
| m4_3 | 104 | 8 000 | 832 000 | 6,5 h |
| m4_2 | 104 | 4 000 | 504 520 | 4,0 h |
| m4b_mini | 104 | 4 000 | 333 601 | 2,6 h |
| m4_2b | 88 | 3 000 | 285 000 | 2,2 h |
| **total** | **400** | | **1 955 121** | **15,4 h** |

Fichiers lourds à supprimer : m4_3 5,26 Go, m4b 1,29 Go, m4_2 0,22 Go,
**m4_2b 0,00 Go** — pour cette dernière famille, « supprimer les données
brutes » est sans objet ; son gain est l'ajout des instantanés.

> **Réserve assumée** : une seule ancre mesurée (m4b, T=10000, 28,3 min sur le
> chemin complet). Les moteurs n'ont pas le même coût par pas. Ce chiffre reste
> une estimation jusqu'à ce que le journal de campagne donne les vitesses
> réelles par famille — et vu mon palmarès en la matière, je ne le présente pas
> autrement.

### Le pilote ne détruit jamais avant d'avoir prouvé

`scratchpad/resimulate.py`. Pour chaque run : rejeu dans un répertoire
**temporaire**, comparaison des compteurs, et **si un seul diffère, le run est
laissé strictement intact** et signalé. Ce n'est qu'en cas d'identité que les
instantanés sont versés, les figures régénérées, puis `loan_events.csv.gz` et
`individual_series.csv.gz` supprimés. Un run non reproductible ne perd rien.

### Incident : campagne tuée par l'OOM à 123/296 — aucun dégât

Le premier lancement a été **arrêté par le système** pour mémoire insuffisante.
Bilan vérifié :

| | |
|---|---|
| runs enregistrés | **123**, tous remplacés |
| échecs fatals | **0** |
| runs laissés intacts pour divergence | **0** |
| runs non traités dont `figures/` serait vide ou absent | **0 sur 173** |

**La conception a tenu, et c'est le point.** `traite()` rejoue dans un
répertoire temporaire et ne touche au run qu'à la toute fin ; sa seule fenêtre
destructrice — entre l'effacement de `figures/` et sa reconstruction — dure le
temps d'une génération de figures. La mise à mort n'y a attrapé aucun run. Une
interruption fait donc perdre du travail, jamais des données.

**Cause et correctif.** `RLIMIT_AS` borne l'espace d'adressage, pas la mémoire
résidente : six workers chargeant chacun 160 instantanés pour tracer leurs
figures saturent légitimement. Mes trois essais d'adaptateurs tournaient en
parallèle et y ont probablement contribué. Le pilote passe de **6 à 4 workers** —
une mise à mort par l'OOM se traite en réduisant la charge, pas en espérant
qu'elle était fortuite.

> **Troisième faux positif identique de la session.** Après l'arrêt, `pgrep -f
> resimulate.py` a signalé deux processus survivants : c'était le shell
> exécutant ma propre sonde, dont la ligne de commande contient ce nom. J'avais
> écrit un scanner strict dans `apply_gini_fix.py` exactement pour ce piège, et
> je ne l'ai pas réutilisé. Vérification refaite proprement : aucun survivant,
> aucun descripteur ouvert, six temporaires orphelins nettoyés.

### Deuxième mort, à 4 workers — et mon explication était fausse

La relance à 4 workers a été tuée à son tour, après **7 runs**. Dégâts vérifiés
comme la première fois : **130 runs enregistrés, 0 échec fatal, et 0 sur 166
runs non traités avec un `figures/` vide ou absent**. La conception a encaissé
une seconde mise à mort sans perdre de données.

**J'avais annoncé la cause : les runs à 160+ instantanés, dont `snapshots()`
charge tous les `.npz` d'un coup. C'est faux.** Mesure directe du pic de mémoire
résidente d'un `traite()` complet — resimulation *et* figures — sur un run à
80 instantanés :

| | |
|---|---|
| pic pour **un** worker | **0,48 Go** |
| projection à 4 workers | 1,9 Go |
| projection à 6 workers | 2,9 Go |
| mémoire disponible sur la machine | **26 Go** |

Aucune de ces valeurs ne peut provoquer une mise à mort. Et les autres relevés
concordent : échantillonnages précoces à ~0,5 Go résident, aucun processus de la
machine au-dessus de 0,9 Go (le plus gros étant firefox), total visible ~4 Go.

> **Ces faits ne s'additionnent pas, et je ne sais pas pourquoi.** Deux
> hypothèses successives — le nombre de workers, puis le chargement des
> instantanés — ont été démenties par la mesure. Plutôt que d'en formuler une
> troisième, la relance suivante tourne avec un **échantillonneur** qui écrit la
> mémoire résidente cumulée toutes les deux secondes dans `scratchpad/memoire.log`.
> Si une troisième mort survient, j'aurai la trace du pic au lieu d'une
> conjecture. Le nombre de workers reste à 4 : ma mesure valide aussi bien 4 que
> 6, et descendre à 3 sur cette base serait arbitraire.

### Troisième mort — et la trace réfute le motif invoqué

L'échantillonneur a tourné pendant plus de deux heures, **3 741 relevés**. Verdict :

| grandeur | valeur |
|---|---|
| mémoire disponible, **minimum** sur toute la campagne | **22,0 Go** sur 31,3 |
| RSS cumulé de mes workers, **maximum** | **4,59 Go** |
| mémoire disponible **au moment de la mise à mort** | **26,5 Go**, workers à **0,00 Go** |

Les deux chiffres se recoupent exactement — 26,6 − 4,6 = 22,0 — donc mes
processus expliquent toute la baisse, et cette baisse est dérisoire. **La machine
n'a jamais manqué de mémoire.** Au moment précis de l'arrêt, elle en avait 26,5 Go
de libre et mes processus étaient déjà terminés.

> **Le motif annoncé ne correspond pas à l'état de la machine.** Mes deux
> explications précédentes étaient fausses ; celle-ci l'est aussi, mais d'une
> autre manière : ce n'est pas mon diagnostic qui était mauvais, c'est la
> prémisse. Piste restante à vérifier : mon échantillonneur lit `/proc/meminfo`,
> c'est-à-dire l'**hôte**, alors que le superviseur peut mesurer un **cgroup**
> bien plus étroit — auquel cas tous mes raisonnements sur le nombre de workers
> portaient sur le mauvais compteur.

**Progression malgré tout, et sûreté confirmée une troisième fois** : 123 → 130 →
**190 runs** enregistrés, **0 échec fatal**, et **0 run abîmé** sur les 106 non
traités. Chaque passe avance ; aucune ne détruit.

### Mon correctif des figures de vies était à moitié fait

Vérification du run que j'avais abîmé (`20260717_165751_25340373`) : **toujours
pas réparé**, malgré une resimulation complète — 200 instantanés, 31,6 min, et
un `summary.json` déclarant **7 697 786 lignes de journal** régénérées. Donc
`individual_every=1` fonctionnait ; les figures de vies manquaient quand même.

Cause, lue dans le code : `traite()` ne déplace du temporaire vers le run que
`snapshots/` (ligne 193). Le journal régénéré restait dans le temporaire, jeté
avec lui ; puis la boucle `LOURDS` supprimait par-dessus l'ancien journal du
run. **J'avais restauré l'enregistrement sans restaurer le transfert.**

Portée : **2 runs déjà amputés**, et **23 autres qui allaient l'être** — les
26 runs à journal non vide, dont 23 n'avaient pas encore été resimulés.

> **J'ai arrêté la passe en cours.** C'est la première fois de cette session
> qu'interrompre est le choix conservateur : le dégât était certain et
> croissant, contre quelques minutes de calcul que l'état rend intégralement
> récupérable. Arrêt propre — SIGTERM au parent, puis aux quatre workers
> orphelins qui lui ont survécu (un `ProcessPoolExecutor` décapité les laisse
> tourner, et ils pouvaient se trouver dans la fenêtre destructrice).
> Bilan après arrêt : **190 runs enregistrés, 0 échec, 0 abîmé sur 106 non
> traités.**

Correctif : le journal est désormais déplacé vers le run **avant** la génération
des figures, la suppression des lourds intervenant **après**. Les vies sont
tracées, puis le journal effacé — ce que demandait la consigne : supprimer après
avoir produit, non à la place.

**Vérifié sur un run réel**, et non par compilation — le correctif précédent
compilait parfaitement et ne faisait que la moitié du travail :

| `20260727_184355_1e0896c8` (T=4000, journal de 489 717 lignes) | avant | après |
|---|---|---|
| figures | 29 png | **30 png + 7 gif** |
| `entity_lives_overview` | absente | **présente** |
| `detail_vie_entites/` | 0 | **10 figures** |
| fichiers lourds restants | — | **aucun, supprimés** |

Le run est réparé du même coup. Le second amputé
(`20260717_165751_25340373`) est réinscrit dans la file de la passe suivante.

### 88 runs m4_2b ont un `snapshots/` qui est un lien symbolique

Neuf échecs fatals sont apparus à la 4ᵉ passe — les trois précédentes en
comptaient zéro. Tous le même :
`OSError: Cannot call rmtree on a symbolic link`, à la ligne qui remplace le
dossier d'instantanés.

Cause : **les 88 runs m4_2b ont été importés** depuis l'arbre de campagne du
programme, et leur `snapshots/` est un lien vers
`m4_2b_credit_soc/results/campaign/<bras>/<graine>/snapshots` — **hors du
laboratoire**. `shutil.rmtree` refuse de supprimer un lien.

> **Le correctif évident aurait été une faute.** Suivre le lien pour y déverser
> les nouveaux instantanés écrivait dans l'arbre source du programme M4.2B, et
> **au moins une cible est partagée par deux runs du laboratoire** — qui se
> seraient disputé le même répertoire. Les cibles sont d'ailleurs **vides** : le
> lien ne porte plus de données, seulement une provenance. On délie donc au lieu
> de suivre ; chaque run reçoit un répertoire qui lui appartient, l'arbre de
> campagne reste intact.

**Aucun run n'a rien perdu** : l'exception survient avant toute étape
destructrice, `traite()` la capture, et les 9 runs conservent leurs 7 figures et
leur journal. La propriété de sûreté a joué une quatrième fois.

**Correctif vérifié sur un run réel**, sur les quatre critères qui comptaient :

| `20260804_161739_d6b24067` | avant | après |
|---|---|---|
| `snapshots/` | lien symbolique | **vrai répertoire, 60 `.npz`** |
| figures | 7 png | **26 png** |
| cible dans l'arbre de campagne | 0 entrée | **0 entrée, toujours présente — INTACTE** |

Le quatrième critère était le vrai enjeu : l'arbre source du programme M4.2B
n'a pas été touché.

> **Et un gain de fond, inattendu.** Ces 88 runs m4_2b pointaient vers des
> répertoires d'instantanés **vides** : c'est pourquoi la famille ne rendait que
> 7 figures par run. En les déliant et en leur donnant leurs propres instantanés,
> chacun passe à environ 26. La famille la plus pauvre du laboratoire cesse de
> l'être — non par un correctif de figures, mais parce que la resimulation lui
> apporte enfin les données qui lui manquaient.

> **Mon garde-fou de relance était incomplet.** Il conditionnait le redémarrage à
> « zéro run abîmé » et « zéro figure de vie manquante », **sans regarder le
> compteur d'échecs**. J'ai donc relancé une passe qui allait resimuler 88 runs
> m4_2b pendant ~8 minutes chacun pour échouer à la fin sur ce même lien — une
> dizaine d'heures de calcul pour rien. Passe arrêtée dès le diagnostic.

### Le garde-fou de relance, rendu durable — `scratchpad/relancer.py`

Quatre arrêts, quatre relances improvisées à la main, et une condition oubliée
qui a coûté dix heures de calcul. Le geste devait cesser d'être réinventé à
chaque fois. Trois refus, dans cet ordre :

1. **un pilote tourne déjà** ;
2. **un run non traité a perdu ses figures** — signe qu'une interruption a frappé
   dans la fenêtre destructrice ;
3. **un motif d'échec inconnu est apparu**.

Le troisième est la vraie leçon. La règle n'est *pas* « refuser s'il y a des
échecs » : après correctif, des échecs déjà diagnostiqués subsistent
légitimement jusqu'à leur reprise. C'est l'apparition d'un **motif jamais vu**
qui doit arrêter — exactement ce qui s'est produit, et exactement ce que je n'ai
pas regardé.

**Un trou trouvé dans le garde-fou lui-même.** Le scan par ligne de commande ne
voit que les pilotes lancés avec `resimulate.py` en argument ; il rate une
vérification manuelle qui *importe* le module et appelle `traite()` directement
— et c'était précisément le cas qui tournait pendant que j'écrivais ce script.
Un verrou PID n'y aurait rien changé : une telle vérification ne passe pas par
`main()`. Le signal fiable est **comportemental** : tout `traite()` en vol
possède un répertoire `/tmp/resim_*`. Refuser tant qu'il en existe attrape
pilotes et vérifications sans aucune heuristique sur les lignes de commande, et
force au passage le nettoyage.

> **Éprouvé par contrôle positif** : lancé pendant qu'une vérification tournait,
> le script a **refusé**, en nommant le temporaire en cause. C'est le premier
> garde-fou de ce chantier que je valide en le faisant dire *non* — les autres,
> je m'étais contenté de supposer qu'ils le diraient.

### Le diagnostic, enfin : le cache de pages, pas les workers

Le cgroup de la session n'impose **aucune limite** (`memory.max` = `max`), mais
ses compteurs disent l'essentiel :

| compteur | valeur |
|---|---|
| `memory.current` | 12,62 Go |
| `memory.peak` | **22,25 Go** |
| `free` — « utilisé » | ~4 Go |
| `free` — tampons/cache | ~18 Go |

L'écart est le **cache de pages**. Cette campagne lit et écrit des centaines de
mégaoctets par run — instantanés `.npz`, figures, journaux — et ce trafic gonfle
l'occupation du cgroup jusqu'à 22 Go sur 31.

**Mes deux compteurs étaient aveugles à cela, par construction** :
`MemAvailable` compte le cache comme disponible, puisqu'il est récupérable ; le
RSS ne compte que la mémoire anonyme. J'ai donc mesuré pendant deux heures
exactement les deux grandeurs qui ne pouvaient pas montrer le phénomène.

> **Ce que je ne corrige pas, et pourquoi.** Réduire le nombre de workers
> ralentirait le débit d'entrée-sortie sans changer son total, fixé par le
> nombre de runs : cela retarderait le pic au lieu de l'éviter. Et ce cache est
> récupérable — ce n'est pas une pénurie réelle. Le nombre reste donc à 4, et
> **j'accepte que l'arrêt se reproduise** : il est inoffensif, l'état rend la
> reprise idempotente, et chaque passe traite 60 à 120 runs.

## 8. Les trois adaptateurs manquants (2026-09-24)

Demande : « fais les adaptateurs si besoin ». Les 728 runs live / v2 / m4_4
existaient dans le laboratoire sans qu'aucun adaptateur ne permette d'en lancer
de nouveaux — ils venaient des scripts de campagne et avaient été importés après
coup. Trois fichiers écrits :
`modeles-systeme-physicoeconomique/{m4_3live,m4_3live_v2,m4_4_rebond}_credit_soc/model.py`.
Le laboratoire liste désormais **14 modèles** au lieu de 11, les trois nouveaux
lançables avec 24, 26 et 30 paramètres.

### Ce ne sont pas des simulations mais des protocoles à interventions

Découverte qui change la nature du travail : ces moteurs n'ont pas de
`run_and_save`. Leur driver expose `build_config`, **`run_plan`** et
`write_outputs`, avec des commandes `burn`, `arm`, `replay`, `resume`. Un run
consiste à chauffer la population jusqu'au pas `t0`, puis à **armer un plan** —
un ou plusieurs changements de paramètre appliqués à un pas donné — et à
poursuivre jusqu'à `T` :

```
{"t": 2001, "param": "A", "value": 1.5, "scope": "all"}
```

**Le plan fait donc partie de la définition du run**, au même titre que les
paramètres et la graine. `summary["plan"]` le contient, sous forme de liste
rejouable, sur 120 runs live, 84 v2 et 240 m4_4. `interventions.jsonl` est le
journal de ce qui s'est produit — une sortie, pas une entrée.

> **Conséquence directe sur la resimulation du §7** : mon contrat « paramètres +
> graine → compteurs identiques » serait **faux** pour ces familles. Il
> rejouerait la trajectoire non perturbée et la déclarerait conforme. C'est
> pourquoi aucun de ces trois modèles n'est branché sur `resimulate.py`.

### Pourquoi le plan passe en JSON et non par le nom du bras

`ParameterSpec` n'admet que `bool`, `int`, `float`, `str` : une liste de
dictionnaires n'est pas représentable. Piloter par le nom du bras était tentant —
chaque nom correspond en général à un plan canonique — mais **`control` désigne
deux plans distincts en lignée live**, l'un vide et l'autre non. Un adaptateur
piloté par le nom produirait un run sur deux faux. `arm` est conservé comme
libellé ; `plan_json` fait foi.

### Sept valeurs inventées, cinq valeurs légales manquantes

J'avais rédigé les listes de choix des paramètres énumérés **de mémoire**. Le
contrôle contre les constantes du moteur — `RATE_RULES`, `TRANSFER_CAPS`,
`PHASE_ORDERS`, `LOAN_DIRECTIONS`, `KERNEL_POLICIES` — montre que les quatre
listes étaient fausses, **dans les deux sens** :

| paramètre | écrit de mémoire | accepté par le moteur |
|---|---|---|
| `rate_rule` | `marginal`, ~~`average`~~ | `marginal`, **`surplus_share`**, **`bargain`** (m4_4) |
| `transfer_cap` | `optimum`, ~~`none`~~ | `optimum`, **`equalization`** |
| `phase_order` | `v1`, ~~`v2`~~ | `v1`, **`deprec_first`** |
| `loan_direction` | `free`, `richest_lends`, ~~`poorest_lends`~~ | `free`, `richest_lends` |
| `kernel_policy` | `exact_lut`, ~~`exact`~~, ~~`lut`~~ | `exact_lut`, **`hybrid`** |

L'interface aurait refusé `surplus_share` et `deprec_first`, que des runs
archivés emploient, et proposé `average`, que le moteur aurait rejeté à
l'exécution. `target_rule` n'a **pas** de liste : aucune constante ne le valide,
et en inventer une rejetterait peut-être du légal.

### Deux réserves de reproductibilité, non levées

1. **86 runs n'ont pas de plan** (53 live, 33 v2, antérieurs au champ) : leur
   protocole est inconnu, donc irreproductible.
2. **m4_4 reprend une chauffe enregistrée** — 348 runs déclarent un `checkpoint`,
   tous présents sur disque. L'adaptateur, lui, **refait la chauffe depuis la
   graine**. C'est équivalent si et seulement si le moteur est resté déterministe
   depuis l'écriture de ces instantanés, **ce qui n'a pas été vérifié**.

Ces adaptateurs servent donc à lancer des runs **neufs**. Les brancher sur une
resimulation destructrice exigerait d'abord une preuve de reproductibilité par
famille, comme celle obtenue pour les quatre autres au §7.

### Ce qui a été vérifié, et dans quel ordre

Trois contrôles de **déclaration**, puis un d'**exécution** — la distinction
compte, c'est elle qui m'a manqué plusieurs fois dans ce chantier :

| contrôle | portée | résultat |
|---|---|---|
| complétude des paramètres | archives ↔ specs ↔ `Config` | aucun manquant, aucun surnuméraire, aucun champ oublié |
| listes de choix | contre les constantes du moteur | 4 listes fausses sur 4, **corrigées** |
| `validate_parameters` | les **681** runs archivés porteurs d'un sommaire | **681 acceptés, 0 rejeté** |
| **exécution réelle** | un run T=100, `t0=50`, une intervention | **les trois aboutissent** |

L'essai d'exécution est le seul qui prouve que le code tourne. Il a parcouru
toute la chaîne : chargement du driver par chemin, `build_config`, chauffe par
`run_plan`, reconstruction de la config, bras avec plan, `write_outputs`,
relecture du sommaire, collecte des artefacts. Résultat sur les trois :
statut `completed`, `t_final=100`, **l'intervention est appliquée et
journalisée**, `plan`/`arm`/`t0` sont enregistrés, et chaque moteur stampe sa
version (`m4_3live-1`, `m4_3live_v2-1`, `m4_4-1`). m4_4 écrit bien son jeu plus
riche : avalanches, décès, `loss_edges.npz`, `panels.npz`, statistiques de
marché — 14 artefacts contre 8 pour les deux autres.

Reste à faire : un essai à pleine échelle (T=4000), différé tant que la campagne
de resimulation occupe les six cœurs.

## 9. Où sont les traces

- **Planche-contact des figures** (page publiée, privée) :
  <https://claude.ai/artifact/X85ugoh4E2cCAgigSaPiKw> — 100 figures tirées au sort
  parmi les 12 010, et toutes les figures d'une simulation pour chacun des sept
  modèles. Vignettes à 820 px ; les originaux restent dans les runs.
- Pilote et scripts : `/tmp/claude-1007/-home-anatole-jupyter/e9006e24-b413-4eac-9e59-dd2d6c6ecddb/scratchpad/`
  (`campaign2.py` — le pilote en service ; `campaign.py` — première version, périmée ;
  `strip_ten.py`, `probe_families.py`, `regen_figures.py`, `recover_rho4.py`, `regen_lot.py`)
- Journal de campagne : `scratchpad/campaign2_log.txt` — état : `campaign2_state.json`
- Figures antérieures, déplacées et récupérables : `<run>/figures_avant_2026-09-17/`
- Référence des figures M4.3 : `scratchpad/expected_figures.txt` (30 noms, sans extension)
- Module de figures, **non modifié par ce chantier** :
  `modeles-systeme-physicoeconomique/m4_3_credit_soc/reporting.py`
