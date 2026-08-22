# M4.3Live-v2 — journal de travail

Tenu au fil de l'eau. Chaque session y consigne ses chiffres clés, ses
décisions, et les inférences qu'elle a dû retirer.

---

## 21 août 2026 — décisions de périmètre (retours oraux de l'utilisateur)

- **Aucun traitement du cas partiel.** `fraction_persistante` annulée, lot G
  retiré du séquencement, question ouverte n°5 de la feuille de route
  tranchée par la négative. v2 mesure en portée globale, où l'intensité de
  traitement vaut 1 par construction. Les résultats v1 en portée partielle
  restent publiés.
- **Une seule borne de transfert : `optimum`.** `equalization` retiré de v2.
  Vérification faite avant de l'écrire : `mkt_capped` cumulé vaut
  **exactement 0 sur les 164 runs du dépôt** — la branche n'a jamais mordu.
  C'est donc une amputation de code mort : elle ne peut changer aucun nombre
  publié, la parité doit être reconduite telle quelle, et elle a sa place
  dans le lot A, avant tout changement de comportement. Rend sans objet la
  question ouverte n°1 (plafond sous δ signé) ; le *sens* du transfert reste
  entier. Le pilote de plafond du 16 août reste publié dans le rapport de
  conception : il documente *pourquoi* le plafond est sans objet.

---

## 22 août 2026 — lot A : fork, purge des clefs mortes, suppression de `equalization`

### Ce qui a été fait

Fork par COPIE de `m4_3live_credit_soc/` vers `m4_3live_v2_credit_soc/` :
paquet moteur `m4_3live/` → `m4_3live_v2/`, plus `driver/`, `web/`, `tests/`
et la partie de `scripts/` que v2 réutilise. Aucun import de v1 dans le code
de v2. Le paquet v1 n'a pas été touché — vérifié par `git status` : les seuls
fichiers modifiés hors de `m4_3live_v2_credit_soc/` sont
`simulation_lab/web/app.py` (deux aiguillages additifs) et le nouveau
`simulation_lab/live_v2/`.

**Scripts non repris**, et pourquoi : `ablation_k0.py`, `scaling_gamma.py`,
`scaling_theory.py`, `tension_sweep.py`, `tension_vs_A.py`,
`time_rescaling.py`, `bench_kernel.py`, `exact_amplitude.py`,
`tension_analysis.py`, `protocol_figures.py`, `verification_figures.py`,
`conception_evidence.py`, `analyse.py`, `make_report_tables.py`. Ils ont
produit des résultats v1 **publiés et acquis** (§2 du prompt) que v2 cite
sans les refaire ; les garder aurait laissé du code que rien n'appelle.
`scripts/tension.py` disparaît pour une autre raison : son calcul devient
natif (§4.1) et vit désormais dans `m4_3live_v2/tension.py`.

**§3.5 — `equalization` supprimé.** `TRANSFER_CAPS`, le champ
`Config.transfer_cap`, la branche de plafonnement de `_run_market`, le
compteur `mkt_capped` et sa colonne, l'option `--transfer-cap`, le champ
exposé par l'IHM et la liste de l'IHM.

**§3.4 — purge des clefs mortes.** `LoanBook.forget(entity)`, appelé dans
`_fail_one` juste après `population.kill`, retire l'entité de
`by_borrower`, `by_lender`, `due`, `claims` et `debts`. La méthode lève si
l'entité porte encore un contrat : l'invariant est vérifié à l'exécution,
pas seulement commenté. Colonne `book_keys` ajoutée à la série pour rendre le
mécanisme lisible.

### Porte de sortie — franchie

**Parité bit à bit, 8000 pas × 26 colonnes** contre
`m4_3__d1__baseline__seed0` : **écart maximal NUL**. 9 366 225 appels au
noyau, tous sur le chemin identité — *exactement le nombre publié par v1*, ce
qui confirme que la suppression et la purge ne déplacent aucun appel.
**739 s** contre 1077 s pour v1 sur le même test, soit **−31 %**.
Trace : `results/analysis/parity_lotA_full.log`,
`results/analysis/parity_deviations_8000_lotA.csv`.

**Courbe de coût par pas, 4000 pas, graine 0, les deux moteurs en parallèle
sur un cœur chacun** (`scripts/cost_profile.py`,
`results/analysis/cost_profile.csv`) :

| moteur | ms/pas, t ∈ ]10, 210] | ms/pas, 200 derniers pas | rapport | clefs du carnet à t=4000 | vivantes | total |
|---|---|---|---|---|---|---|
| v1 | 112,7 | 121,3 | **×1,076** | **120 153** | 1031 | 444 s |
| v2 | 115,2 | 92,3 | **×0,801** | **1 023** | 1031 | 378 s |

Le carnet de v1 porte 120 153 clefs pour 1031 entités vivantes : **99,1 %
sont vides**. Celui de v2 en porte 1023, soit la population vivante à une
unité près. Le coût par pas de v1 croît de 7,6 % sur l'horizon, celui de v2
décroît de 20 % — la décroissance vient d'ailleurs (le carnet actif se
contracte après le transitoire), et c'est justement le point : une fois la
purge faite, la taille du carnet mort ne pilote plus rien.

**Mesure faite sur le moteur du lot A seul** (la purge et la suppression, pas
les changements de comportement des lots suivants), puisque les deux
processus ont importé le module avant les modifications suivantes.

---

## 22 août 2026 — lot B : le sens du prêt cesse d'être imposé

### Ce qui a été fait

`_run_market` réécrit. La paire est **non ordonnée** : `a` et `b`, de
capitaux `K_a` et `K_b`. Le noyau retourne δ* = h(C) − K_a de **signe
libre** ; celle qui cède détient la créance, celle qui reçoit porte la dette.
Nomenclature : plus de `lender`/`borrower` dans la boucle de marché, mais
`a`/`b` pour la paire et `donor`/`receiver` pour les rôles que l'optimum fait
émerger. `LoanBook` garde `by_lender`/`by_borrower` : ce sont les rôles du
CONTRAT (qui détient la créance, qui porte la dette), pas ceux de la paire,
et ils ne portent aucune hypothèse de richesse — c'est la lecture de la note
[6], qui vise `K_ℓ, K_b` et non le carnet.

**Ordre de calcul canonique** : `a` est l'entité de plus petit capital.
Ce n'est plus un rôle, c'est l'ordre de présentation au noyau. Deux raisons,
écrites dans le code : (i) `solve(s_a, s_b, K_a, K_b)` et
`solve(s_b, s_a, K_b, K_a)` sont deux entrées différentes de la matrice de
noyaux, dont les tables sont compilées séparément — h_ab(C) + h_ba(C) = C est
vrai en mathématiques, pas au dernier bit ; (ii) il rend la requête au noyau
identique à celle de v1, donc `richest_lends` rejoue v1 exactement.

**Drapeau `loan_direction ∈ {"free", "richest_lends"}`**, défaut `free`.

**`mkt_blocked_dir` devient contrefactuel** sous `free` : il compte les
paires que la règle v1 aurait refusées **dans l'état où v2 se trouve**. Ce
n'est pas le compteur d'une trajectoire v1 — les deux divergent dès le
premier prêt inversé. Le garde `K_b > K_a` reproduit l'arbre de décision
exact de v1, qui écartait les capitaux égaux avant de compter un refus.
Deux compteurs nouveaux : `mkt_reversed` et `mkt_volume_rev`, les prêts
conclus dans le sens que v1 interdisait, et leur volume.

**Diagnostics du régime nouveau (§4.4)** : `n_creditors`,
`K_share_creditors` (part du capital total détenue par les créancières
nettes), `corr_marg_net` (corrélation de Pearson entre rendement marginal et
position nette) et `corr_K_net`.

**Question ouverte §12.2 tranchée — le taux d'intérêt.** `pair_rate` est
**symétrique bit à bit** : √(m₁·m₂) ne contient ni rôle, ni comparaison de
capitaux, et la seule opération qui mêle les deux côtés est un produit, dont
la version flottante est commutative. Libérer le sens ne change donc rien à
la règle de taux, et il n'y avait rien à y changer. Vérifié par assertion
d'égalité stricte sur trois paires (`tests/test_loan_direction.py`).
L'alternative — prendre le rendement marginal commun d'APRÈS l'échange, que
l'optimum égalise par construction — est **documentée et écartée** : elle
change l'institution au-delà du mandat du §3.1 et détruirait la parité (en
régime homogène elle donne Aγ(C/2)^{γ−1} au lieu de Aγ(K_a K_b)^{(γ−1)/2},
soit la moyenne arithmétique des capitaux au lieu de la géométrique).

### Porte de sortie — franchie, et sans écart à expliquer

**Parité bit à bit reconduite**, 8000 pas × 26 colonnes, **écart maximal
NUL**, sur le moteur v2 complet avec `loan_direction="free"` par défaut
(`results/analysis/parity_lotBCE_full.log`, 741 s).

Une seule différence, et elle ne porte sur aucun nombre : **9 369 224 appels
au noyau contre 9 366 225**, soit **+2 999**. Explication ligne à ligne : v1
écartait les paires de capitaux égaux AVANT d'appeler le noyau
(`K[lender] <= K[borrower]: continue`) ; v2 sous `free` les lui soumet,
parce qu'entre technologies différentes une paire de capitaux égaux a un
optimum non trivial. En régime homogène ces 2999 paires (des entités à
capital nul, mises à zéro par la dépréciation) reçoivent δ* = 0, sont
comptées `blocked_tiny` et ne traitent pas. Aucune opération flottante n'est
ajoutée à la trajectoire, aucune table du noyau n'est compilée
différemment — le chemin identité ne tient pas de compteur d'usage.

**La v1 est rejouable dans le moteur v2** (`tests/test_v1_equivalence.py`) :
300 pas × **34 colonnes**, intervention A×1,5 sur 20 % à t=100, **deux
technologies vivantes**, **61 166 paires refusées pour cause de sens** —
écart maximal NUL entre le moteur v1 et v2/`richest_lends`. C'est cette
égalité, et non la parité avec M4.3, qui rend la campagne A/B appariée.
Contrôle négatif : sous `free`, première divergence au pas de l'intervention
lui-même (t=100) et **30 768 prêts conclus dans le sens interdit**.

---

## 22 août 2026 — lot C : instrumentation native

- **§4.1 tension native.** `n_prod` et `K_prod` — effectif et capital **à
  l'instant de produire**, par technologie — sont enregistrés dans la phase
  de production. `m4_3live_v2/tension.py` (module du MOTEUR, plus un script)
  en dérive `K_eq`, `K_aut`, `T` et l'écart de Jensen ; `write_series` écrit
  `tension.csv` et `tension_agg.csv` pour **tout** run, sans intervention
  manuelle. La colonne `basis` de v1 disparaît : il n'y a plus de
  reconstruction à documenter. Deux gains de justesse, pas seulement de
  commodité : l'écart de Jensen est désormais exact (numérateur et
  dénominateur pris au même instant du pas), et le δ employé est celui du
  pas courant — un dérivé a posteriori lit un δ de fichier et ne verrait pas
  une intervention sur δ.
- **§4.2 amplitude exacte.** Une sonde `{identifiant → (A, γ) d'avant}` est
  posée par `_apply` et consommée par la phase de production du même pas.
  Elle couvre aussi les entités **nées** au pas de l'intervention lorsque la
  technologie de naissance a changé : sans elles, la part traitée d'une
  portée `toutes` ne vaudrait pas 1 mais 0,9914 — mesuré avant correction.
- **§4.3 prédiction naïve du levier γ**, enregistrée à côté de l'amplitude
  mesurée, sous deux formes : « K = 1 » (qui donne m = 1) et « K = K_eq »
  (qui donne K_eq^{Δγ}).

Mesures de contrôle (`tests/test_amplitude.py`, graine 1, t = 200) :

| levier | m mesurée | naïve « K = 1 » | naïve « K = K_eq » | p ex ante | E |
|---|---|---|---|---|---|
| A×1,5, portée toutes | 1,500000000000001 | 1,5 | 1,5 | 1,0 exactement | 1,000000000000000 |
| A×1,25, portée fraction φ=0,2 | 1,250000000000 | 1,25 | 1,25 | 0,1978 | 1 à 1e−9 près |
| γ : 0,5 → 0,6, portée toutes | **1,960149** | **1,000000** | 1,952475 (−0,39 %) | 1,0 | 1 à 1e−9 près |
| A×1,5, portée nouvelles | 1,500000000000 | 1,5 | 1,5 | 0,005769 | 1 à 1e−9 près |

Le levier γ est le cas qui justifie la mesure : la prédiction naïve à K = 1
se trompe d'un facteur 1,96. **E = 1 n'est pas une mesure** : c'est une
réécriture des définitions de m et p, et son écart à 1 ne dit rien d'autre
que la propreté de l'aller-retour flottant. C'est écrit dans la docstring de
`_close_amplitude` et ce sera écrit dans le rapport.

---

## 22 août 2026 — lot E (partie moteur) : ordre des phases

`phase_order ∈ {"v1", "deprec_first"}`, défaut `"v1"`. Les deux phases sont
extraites en fonctions (`_service_interest`, `_depreciate`) et appelées dans
l'ordre voulu ; l'extraction ne change aucun calcul, la parité le confirme.

**Prédiction a priori, écrite avant de lancer le bras.** Le capital
disponible au moment de payer est réduit d'un facteur (1 − δ) : bascule en
défaut de liquidité toute débitrice dont le capital K vérifie
(1 − δ)·K < dû ≤ K. C'est un ensemble que le moteur peut compter **dans le
bras de référence lui-même** : la colonne `defaults_window` le fait, sans
division (dû ≤ K/(1−δ) est écrit dû·(1−δ) ≤ K). Le nombre est donc mesuré
sous l'ordre v1 avant que le bras `deprec_first` n'existe.

---

## Décisions ouvertes du prompt (§12), tranchées

| # | Question | Décision | Où c'est justifié |
|---|---|---|---|
| 1 | nom du paquet forké | `m4_3live_v2` — inchangé | — |
| 2 | taux quand la créancière est la plus fragile | **règle inchangée** : `pair_rate` est symétrique bit à bit, elle ne contient aucun rôle | lot B ci-dessus, `tests/test_loan_direction.py` |
| 3 | nombre de graines de verdict | **12**, contre coût mesuré et non extrapolé | lot D ci-dessous |
| 4 | rééchelonner `MIN_LOAN` / `ZERO_TOL` | **non** : cela casserait la comparabilité avec toutes les campagnes antérieures, pour un gain qui ne se voit qu'au 14ᵉ chiffre | `tests/test_scale_covariance.py` |
| 5 | covariance de pas de temps en non-régression | **non** — son résidu mesuré est de 6 à 17 %, un seuil y serait arbitraire. En revanche la **covariance d'échelle**, elle, est exacte : elle DEVIENT un test de non-régression | `tests/test_scale_covariance.py` |

---

## 22 août 2026 — lot D : campagne appariée du sens du prêt

### Protocole effectivement exécuté

12 graines, amorçage partagé à t₀ = 2000 (404 s pour les 12), 96 bras de
2000 pas (2495 s sur 7 processus). Cellule pilote mesurée avant de s'engager :
144,5 s sous le sens libre, 140,8 s sous la règle v1 — c'est ce chiffre, et
non une extrapolation depuis v1, qui a confirmé les 12 graines.

`control` et `all_A150` restent homogènes après intervention : ils ne sont
lancés que sous le sens libre, parce que les relancer sous l'autre règle
produirait des fichiers identiques bit à bit (vérifié par
`test_v1_equivalence.py`).

### Une correction de protocole faite en cours de route

**Inférence retirée.** J'avais prévu de lire un seul niveau sur les 1000
derniers pas. C'est faux, et le pilote l'a montré : la portée `new` ne
renouvelle pas la cohorte d'origine, dont la durée de vie moyenne est
pop/λ ≈ 34 pas. La part des rondes à contre-sens passe de **23,7 %** sur
]t₀, t₀+200] à **1,4 %** sur le plateau. Lire un seul niveau moyenné aurait
donné « pas d'effet » là où il fallait lire « plus de paires mixtes ».
Deux fenêtres sont donc rapportées, et la fenêtre de transition est
explicitement présentée comme un transitoire.

**Seconde correction, méthodologique.** Le contrôle de stationnarité hérité de
v1 (bande fixe [0,99 ; 1,01]) **rejetait 11 des 12 graines du contrôle** sur
une fenêtre de 1000 pas : les quarts font 250 pas et le rapport a un écart-type
de graine à graine de ~3 %. La bande ne mesurait que la longueur de la
fenêtre. Le critère est désormais un test de Student sur la moyenne du rapport
(12 graines), l'étendue par run étant rapportée comme plancher de bruit.

### Résultats

Bras `new_A150`, fenêtre de transition, écarts appariés sens libre / règle v1 :

| grandeur | écart | t (11 ddl) |
|---|---|---|
| production agrégée | **−5,20 %** | −11,2 |
| capital total | **−10,11 %** | −19,8 |
| contrats vivants | **+24,34 %** | +26,5 |
| rotation du crédit | **+15,81 %** | +57,5 |
| intérêts versés | +2,96 % | +5,5 |
| mortalité par entité | +2,13 % | +7,0 |
| population | −2,10 % | −4,6 |
| cohorte d'origine vivante | +22,0 % | +11,2 |

**Le régime nouveau existe et il est durable.** À t₀+2000, il reste **7,0**
entités de l'ancienne technologie sous le sens libre et **0,0** sous la règle
v1, moyenne sur 12 graines. C'est le résultat attendu du chantier : une entité
de faible rendement marginal cède son capital et vit de l'intérêt.

**Un résultat qui n'était pas attendu.** Chaque échange augmente la production
jointe de sa paire par construction, et pourtant la production agrégée baisse.
La chaîne est mesurée : plus de contrats → plus de service perpétuel → plus de
faillites → et une faillite *détruit* le capital dans ce modèle. Un marché plus
complet y est un marché plus fragile. Cette lecture est cohérente avec toutes
les colonnes ; elle n'est pas démontrée, il faudrait une ablation qui coupe un
maillon.

**Une régularité de v1 mise en défaut.** `morts/pop ∝ rotation^1,337`
sur-prédit la mortalité d'un facteur 3 à 10 sur ce cinquième levier
(+21,7 % prédit contre +2,1 % mesuré pour `new_A150`). **Ce n'est pas encore
une réfutation** : la loi est une relation d'état stationnaire et la fenêtre de
transition n'en est pas un ; dans le régime résiduel, où la comparaison serait
légitime, le levier n'agit presque plus. Le seul régime où ce levier agit
fortement est un régime où la loi n'a pas à s'appliquer.

**Asymétrie à noter.** L'effet de survie n'apparaît que quand la technologie
d'origine est celle de plus faible A. Dans `new_A075` — où les entités en place
ont le A le plus élevé — la cohorte d'origine survit sous les deux règles
(9,2 contre 10,8), et l'écart n'est pas significatif.

---

## 22 août 2026 — lot E : ordre des phases, une prédiction réfutée

**La prédiction, écrite avant le bras traité.** Bascule en défaut toute
débitrice dont le capital vérifie (1−δ)K < dû ≤ K. La distribution du rapport
capital/dû est lue sur les 12 snapshots d'amorçage, soit **13 447 observations
de débitrices** :

| minimum | 1ᵉʳ centile | 5ᵉ centile | médiane | maximum | seuil de bascule |
|---|---|---|---|---|---|
| 3,27 | 11,14 | 13,83 | 26,76 | 1314,1 | 1,0101 |

**La fenêtre est vide.** Zéro observation. La débitrice la plus tendue du
corpus détient 3,27 fois ce qu'elle doit, soit 3,23 fois le seuil. La
prédiction est donc : *aucun défaut de liquidité supplémentaire*. Mesuré :
0 défaut par pas dans les deux bras.

**L'attente d'origine — « ça devrait faire augmenter le taux de défaut » — est
donc réfutée, et pour une raison chiffrable** : il faudrait δ > 0,69 pour que
le levier morde par ce canal.

**Le canal réel, exact.** Sous l'ordre v1 une débitrice finit à
(1−δ)(K − dû) ; sous l'ordre inverse à (1−δ)K − dû. L'écart est −δ·dû. Une
créancière gagne symétriquement +δ·versement. Les deux se compensent : le
capital total du pas est rigoureusement le même, et l'échange des phases est
une **pure redistribution** des débitrices vers les créancières, de
δ × (intérêts servis) par pas — soit 356 joules par pas, 0,041 % du capital
total à chaque pas.

Effet apparié (12 graines, fenêtre résiduelle) : production **−1,84 %**
(t = −11,7), capital −2,52 %, population −1,16 %, mortalité +0,99 %.

**Ce que la prédiction a attrapé et manqué** : elle a attrapé exactement ce
sur quoi elle portait, le nombre de défauts, qu'elle annonçait nul et qui l'est.
Elle a manqué le canal réel parce qu'elle ne regardait que les défauts — la
note d'origine parlait de « taux de défaut », et cette focalisation a orienté
la prédiction vers la seule grandeur que le levier ne touche pas.

---

## 22 août 2026 — vérification finale, sur le moteur effectivement livré

**Parité, troisième passe.** 8000 pas × 26 colonnes contre
`m4_3__d1__baseline__seed0` : **écart maximal NUL**, **9 369 224** appels au
noyau — *le même nombre* que la passe du lot B, ce qui confirme qu'aucune des
additions ultérieures (sonde d'amplitude aux naissances, `n_probe`, sonde de
statistiques de marché) ne déplace un appel. 747 s.
Trace : `results/analysis/parity_final_full.log`.

**Coût, seconde mesure.** Sur le moteur livré : v1 passe de 111,6 à
119,8 ms/pas (×1,073) avec 120 153 clefs pour 1031 vivantes ; v2 de 115,6 à
93,1 ms/pas (×0,805) avec 1023 clefs. 445 s contre 383 s au total.
**L'instrumentation n'est pas mesurable** à ce niveau de bruit : l'écart entre
les deux mesures de v2 (378 s puis 383 s) est du même ordre que celui des deux
mesures de v1 (444 s puis 445 s), et v1 n'a pas changé d'une ligne.

**Suite complète, 12 fichiers, tous verts** :

| test | statut |
|---|---|
| `test_institution.py` | ✓ |
| `test_scopes.py` | ✓ |
| `test_surplus_rate.py` | ✓ |
| `test_loan_direction.py` | ✓ |
| `test_tension.py` | ✓ |
| `test_amplitude.py` | ✓ |
| `test_replay.py` | ✓ |
| `test_resume_divergence.py` | ✓ |
| `test_scale_covariance.py` | ✓ |
| `test_v1_equivalence.py` | ✓ |
| `test_parity_m4_3.py --full` | ✓ |
| `test_web_live.py` | ✓ |

Trace : `results/analysis/suite.log`.

**Rapports compilés** en trois passes après suppression des `.aux`/`.toc` :
aucun `!` dans le journal, aucune référence non définie, aucune commande
indéfinie. `conception_m4_3live_v2.pdf` (23 pages),
`rapport_final.pdf` (27 pages).

**Aucune macro sans source n'est citée** dans le corps des deux rapports :
`scripts/make_numbers.py` en engendre 484, dont 10 valent `---` faute de
source — et aucune de ces dix n'apparaît dans un `.tex` (vérifié par
expression régulière).

---

## Écarts au prompt, signalés

1. **Séquencement git.** Le prompt §8 demande que les lots qui changent le
   modèle soient séparés dans l'historique. L'historique comporte le fork,
   puis le lot A seul, puis **les lots B, C et E groupés** : ils ont été
   écrits dans une même passe sur un seul fichier. L'attribution des verdicts
   n'en dépend pas — elle est assurée par des drapeaux d'exécution
   (`loan_direction`, `phase_order`) mesurés en campagne appariée dans le même
   binaire, ce qui est plus fort qu'une séparation d'historique.
2. **Pilotage « dans un vrai navigateur ».** Le prompt §10 demande de piloter
   une session dans un navigateur et de vérifier visuellement les graphiques.
   Il n'y a pas de navigateur ici. Ce qui a été fait à la place, et qui est
   vérifiable : `tests/test_web_live.py` démarre le serveur, sert la page,
   contrôle la présence des huit éléments d'IHM dans le HTML, crée une
   session par HTTP, la fait tourner, lui soumet une intervention, relit
   l'état par la route qu'emploie le navigateur, vérifie que les douze
   colonnes tracées sont dans la charge utile, et écrit les fichiers de
   sortie. **Le rendu graphique lui-même n'est pas testé**, et c'est dit dans
   les deux rapports.
3. **Contradiction ROADMAP / prompt, signalée.** La feuille de route §1.2
   écrit δ = 0,03 là où le prompt et `model.py` disent δ = 0,01. C'est la
   valeur du code qui a été employée. Et la feuille de route §2.2 propose que
   le bras `null` crée une technologie distincte de paramètres identiques :
   cette proposition est **sans objet**, le prompt §3.3 supprimant le bras
   `null` — elle aurait de plus cassé la parité, en routant les paires sur la
   branche « même γ » plutôt que sur la branche « identité ».
4. **§9 de la feuille de route reste vide.** Les annotations de
   `conception_m4_3live.pdf` ne sont pas sur le disque (0 objet
   `/Subtype/Text`). Rien n'a été inventé pour combler ce trou.

---

## 22 août 2026 — cinq corrections de relecture, avant clôture

Une relecture critique a trouvé cinq points qui ne survivaient pas à la
vérification. Les cinq sont corrigés ; ils sont consignés ici parce que
retirer une affirmation fait partie du travail.

1. **`rotation = ρ·Ḡ` n'était vérifiée qu'en régime homogène.** Les 33 runs
   instrumentés du balayage n'ont aucune intervention : une seule technologie,
   donc λ* = 1/2 et l'égalité est une conséquence *algébrique* de la
   définition du Gini. En régime hétérogène — c'est-à-dire dans tout le sujet
   de ce rapport — le transfert est pondéré et rien ne la garantit. **Quatre
   rejeux instrumentés du bras `new_A150` (156 s)** l'ont mise à l'épreuve :
   écart médian **−4,04 %** sous le sens libre et **−1,19 %** sous la règle v1,
   mais avec une **queue lourde** (5ᵉ centile à −51,5 %) concentrée dans la
   fenêtre de transition. Ce n'est donc pas une loi du modèle : c'est une loi
   de son régime homogène, robuste en médiane hors de lui. Les quatre endroits
   qui l'énonçaient sans restriction sont corrigés.
2. **Le superlatif était sur la mauvaise affirmation** (§14.4 du prompt).
   « Le résultat le plus net » portait sur une identité dérivée. Il porte
   désormais sur ce qui est réellement mesuré : la taille de la correction
   intra-pas (−17,7 % de biais si on l'ignore, ramené à +0,5 % par la moyenne
   logarithmique).
3. **« Un facteur ∼17 en quatre cents pas » était faux.** Les blocs de 200 pas
   donnent 23,8 % / 7,8 % / 3,8 % : c'est un facteur ∼6 en quatre cents pas.
   Le 17 était le rapport entre la moyenne de la fenêtre de transition et
   celle du régime résiduel, qui couvre 1500 pas. Corrigé aux deux endroits.
4. **`rotation.py` filtrait encore avec la bande fixe ±1 %** que le §3.6 du
   même rapport démontre inutilisable. Le sous-ensemble est renommé « les runs
   les plus plats », et le texte dit explicitement que ce n'est pas le
   contrôle de stationnarité du protocole.
5. **« Compatible avec le 1,337 publié » n'était pas soutenu** : l'ajustement
   ne rendait aucune erreur-type. Elle est ajoutée
   (`se = √[(Syy − a·Sxy)/((n−2)·Sxx)]`), et le résultat est que l'intervalle
   à deux erreurs-types **n'atteint pas** 1,337 — sur un corpus qui n'est pas
   celui de l'ajustement publié. Le texte le dit maintenant ainsi, sans
   présenter cela comme une contradiction.

**Et deux règles de rédaction du §10 qui n'étaient pas tenues** : deux
tableaux de plus de quatre colonnes n'avaient pas de figure. Celui de la
distribution capital/dû en a une désormais (`figures/service_ratio.png`), et
c'est la plus parlante du chapitre — la fenêtre de bascule y est un cheveu à
gauche d'une distribution qui commence à 3,27. Celui des amplitudes est réduit
à quatre colonnes, les deux retirées tenant en une phrase.
