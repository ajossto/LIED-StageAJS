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
