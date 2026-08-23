# JOURNAL — M4.4Rebond

Tenu au fil de l'eau (plan §10). Une entrée par séance, les chiffres clés
dedans, les inférences retirées dedans aussi.

Convention de marquage, reprise du plan §0 : `\fait{}` = lu dans le code ou
les données ; `\inference{}` = déduit ; `\hyp{}` = posé ; `\incertitude{}` =
non tranché.

---

## 23 août 2026 — Lot A, ouverture

### Le fork

`m4_4_rebond_credit_soc/m4_4/` est une COPIE de
`m4_3live_v2_credit_soc/m4_3live_v2/`, jamais un import (plan §0, règle du
fork). Copiés aussi : `driver/`, `web/`, `tests/`.

Renommages mécaniques appliqués par `sed` sur les `.py`, `.html`, `.js`,
`.css` :

| avant | après | pourquoi |
|---|---|---|
| `m4_3live_v2_credit_soc` | `m4_4_rebond_credit_soc` | dossier |
| `m4_3live_v2` | `m4_4` | paquet, imports, préfixe d'identifiant de run |
| `/live2`, `/api/live2` | `/live3`, `/api/live3` | routes de l'IHM |

\fait{} Les références aux AUTRES lignées sont laissées intactes, et c'est
voulu : `m4_3live_credit_soc` (v1, lu par `tests/test_v1_equivalence.py` et
`scripts/cost_profile.py`), `m4_3_credit_soc` (identifiant de modèle vérifié
par `web/router.py`), et le run de référence `m4_3__d1__baseline__seed0` de
`simulation_lab` (parité et reprise). Aucun de ces trois ne contient
`_v2` : le `sed` ne pouvait pas les atteindre.

\fait{} `web/router.py:225` comparait une LISTE de segments
(`parts[:3] != ["api", "live2", "sessions"]`) : le motif `/api/live2` ne
pouvait pas y correspondre. Corrigé à la main. C'est le seul endroit du fork
où la route est écrite autrement qu'en chemin.

### Le lot des scripts, et une erreur immédiatement payée

Décision : ne pas copier les scripts d'ANALYSE de v2 (`analyse.py`,
`rotation.py`, `survivors.py`, `make_numbers.py`, `make_traceability.py`),
qui lisent des résultats v2 et seront réécrits lot par lot. Copiés :
`campaign.py`, `cost_profile.py`, `import_to_simulation_lab.py`.

\fait{} Cette sélection a cassé le pilote sans tête : `driver/headless.py:84`
charge `scripts/tension_figures.py` par chemin, échoue proprement et
**imprime l'échec sur la sortie standard**, ce qui casse
`json.loads(buffer.getvalue())` dans
`tests/test_resume_divergence.py:122` — le seul test qui lit la sortie du
pilote. `tension_figures.py` copié ; test vert. Leçon pour les lots
suivants : dans ce dépôt, `scripts/` n'est pas que de l'analyse, le moteur
en dépend par chemin.

### État de la suite AVANT instrumentation

Sur le fork renommé, sans une ligne de code changée :

| test | verdict |
|---|---|
| `test_amplitude` | vert |
| `test_institution` | vert |
| `test_loan_direction` | vert |
| `test_parity_m4_3` (500 pas) | **écart maximal NUL**, 631 607 appels au noyau |
| `test_replay` | vert |
| `test_resume_divergence` | vert après la copie de `tension_figures.py` |

\fait{} Le fork est donc bit à bit le moteur v2 : la parité courte passe
avant toute addition, ce qui sépare proprement « le fork est fidèle » de
« l'instrumentation est neutre ».

### Un point du plan corrigé avant de l'implémenter

Le plan §0 dit de renommer `simulation_lab/live_v2/` en
`simulation_lab/live_v3/`. \fait{} Ce module est l'aiguillage HTTP que
`simulation_lab/web/app.py:13,55-58,109-110` importe pour servir l'IHM de
v2, laquelle est **gelée** avec ses 153 runs et ses deux rapports. Le
renommer casserait v2 au lieu d'éviter une collision.

Décision : `live_v3/` est AJOUTÉ à côté de `live_v2/`, avec une troisième
branche d'aiguillage dans `app.py`. Le renommage du plan se lit comme
« M4.4 prend un nom à elle », pas comme « v2 change de nom ». Même lecture
pour le paquet et pour le préfixe d'identifiant de run.

\fait{} Les trois IHM répondent maintenant sur le même serveur — `/live`
(v1), `/live2` (v2), `/live3` (M4.4) — et `tests/test_web_live.py` le
vérifie route par route, y compris que les pages de v1 et de v2 servent
toujours leurs propres fichiers statiques. La page de M4.4 est rebaptisée
pour qu'on ne confonde pas deux onglets ouverts côte à côte.

### L'instrumentation (§4), et ce qu'elle a appris

Quatre additions, toutes éteintes par défaut, aucune relue par la
trajectoire :

| § | addition | où |
|---|---|---|
| 4.1 | `write_series` écrit enfin les tables d'événements | `m4_4/live.py`, `EVENT_TABLES` |
| 4.2 | panneaux par entité échantillonnés DANS `step()` | `m4_4/model.py`, `panel_every` |
| 4.3 | checkpoint de fin de run | `m4_4/live.py`, `save_snapshot(records=False)` |
| 4.4 | arbre causal persisté | `m4_4/model.py`, `record_loss_edges` |

\fait{} Le §4.2 dit de câbler les panneaux « dans la boucle de campagne, pas
seulement derrière un drapeau », parce que ni `driver/headless.py` ni
`scripts/campaign.py` ne passent par `Simulation.run()`. L'échantillonnage a
été placé dans `step()` plutôt que dans chaque boucle : tout appelant en
bénéficie, et surtout l'INSTANT de mesure est le même pour tous — une
boucle qui prendrait son panneau avant d'écrire sa ligne de série ne
mesurerait pas la même chose que sa voisine.

\fait{} **Une addition qui n'était dans aucune liste : les flux des
mortes.** Le panneau est pris sur `population.living()`, donc après les
faillites du pas ; `prod_tot` et `interest_paid`, eux, sont cumulés AVANT.
À ≈ 30 morts par pas, le panneau seul manque **7,60 %** de `prod_tot`
(mesuré, `tests/test_panels.py`). `dead_info` enregistre donc maintenant
`prod`, `int_in` et `int_out` de chaque morte, et la fermeture devient
exacte à **1,8·10⁻¹⁴** près — l'écart résiduel n'est que l'ordre de
sommation. Les stocks (`pop`, `K_tot`, `nw_tot`), eux, se referment **bit à
bit** : même instant, même ordre.

### Le second estimateur du rapport de branchement : l'écart n'est pas nul

\fait{} Deux runs courts, deux graines, régime par défaut :

| grandeur | graine 3, 300 pas | graine 7, 150 pas |
|---|---|---|
| b₁ = 1 − racines/morts | **0,7429** | **0,7228** |
| b₂ = descendance moyenne par mort | **0,8142** | **0,8036** |
| écart b₂ − b₁ | **0,0713** | **0,0808** |
| degré entrant moyen des morts non racines | 1,096 | — |
| part des morts non racines à ≥ 2 parents | 8,9 % | — |

\fait{} Les deux estimateurs coïncident si et seulement si chaque mort non
racine a exactement un parent. Ils ne coïncident pas : dans la graine 3,
**8,9 % des morts de cascade ont plusieurs parents** à la génération
précédente. L'écart est donc une mesure de la SUR-DÉTERMINATION, et non une
divergence d'estimateur.

\hyp{} « Plusieurs parents » n'est pas « chacun suffisant ». L'estimateur
compte les arêtes causales ; il ne teste pas si l'une d'elles aurait suffi à
elle seule à faire passer la valeur nette sous zéro. Le vérifier demande de
confronter chaque principal à la valeur nette de la victime AVANT la
cascade — mesure possible avec l'arbre persisté, à faire au lot D si la
question est jugée utile.

\fait{} b₂ > b₁ strictement, par construction : toute mort non racine a au
moins un parent, donc le nombre de couples est au moins le nombre de morts
non racines.

\incertitude{} L'AMPLEUR de l'écart, en revanche, n'est pas établie : les
deux graines donnent 0,071 et 0,081, soit 14 % d'écart entre elles, sur des
horizons différents. Le lot D la mesurera sur la fenêtre de campagne et ses
12 graines. Ce qui est acquis dès maintenant, c'est qu'elle n'est pas nulle.

\inference{} La conséquence pour le §3.2 du plan est directe : le b ≈ 0,79
qu'il rapporte, et le b = 0,297 de M4B auquel il le compare, sont **tous
deux** des b₁ — la comparaison inter-lignées reste valide, et c'est ce qui
compte. Mais b₁ n'est pas la descendance moyenne, et les deux chiffres
iront ensemble dans le rapport.

\fait{} L'énoncé structurel dont dépend b₁ est vérifié sur le moteur :
**génération 1 ⟺ racine**, sur 2053 racines et 5932 morts de cascade
(`tests/test_branching.py`). Aucune racine en génération ≥ 2, aucune mort de
cascade en génération 1.

### Le checkpoint : « bit à bit » n'est pas atteignable, et on mesure pourquoi

\fait{} Un run de 240 pas coupé en deux à t=120 par un checkpoint reproduit
le run mené d'un trait sur **les 14 colonnes entières et 8 des 10 colonnes
flottantes**, bit à bit. Les deux qui bougent sont `claim_losses`
(6,7·10⁻¹⁶) et `interest_paid` (2,9·10⁻¹⁶), écart relatif.

\fait{} La cause est connue et documentée depuis v2
(`tests/test_replay.py:57-65`) : ces deux colonnes sont des sommes accumulées
en parcourant un `set` du carnet, et l'ordre d'itération d'un `set` change
après un aller-retour `pickle`. L'ordre d'addition change, donc les derniers
bits changent. \incertitude{} Le §7 du plan demande une trajectoire
« bit-identique » : littéralement, elle n'est pas atteignable, et prétendre
le contraire demanderait de remplacer les `set` du carnet — ce qui casserait
la parité avec M4.3. Le test MESURE l'écart au lieu de le promettre, et
exige l'identité stricte sur tout ce qu'un arrondi ne peut pas bouger : les
14 colonnes de comptage.

\fait{} Le checkpoint emporte aussi l'instrumentation quand on le lui
demande — 6230 décès, 994 avalanches, 188 277 arêtes de perte et 12 panneaux
relus identiques après l'aller-retour. Le mode `records=False` ne laisse
tomber QUE ces listes, et sert au checkpoint de fin de run : l'histoire
vient d'être écrite en CSV à côté, la garder aussi dans le pickle la
stockerait deux fois. \fait{} Mesuré sur une cellule de campagne : 11,6 Mio
en mode léger, contre 101 à 379 Mio en mode complet selon l'instrumentation.

### Le prix de l'instrumentation, mesuré avant d'être choisi

`scripts/cost_panels.py`, cinq cellules branchées sur le MÊME amorçage à
t₀ = 2000, fenêtre de 2000 pas, 1031 entités —
`results/analysis/lotA_cost.{csv,json}`.

| cellule | temps de mur | empreinte |
|---|---|---|
| `nu` (aucun drapeau) | 220 s | 2,7 Mio |
| `events` (décès + avalanches + arêtes) | 228 s (**+3,7 %**) | 24,6 Mio |
| `panels_k1` | 235 s | 107 Mio |
| `panels_k10` | 228 s | 31,8 Mio |
| `market` (k=10 + sonde de Gini) | 232 s (**+1,8 %**) | 32,0 Mio |

\fait{} **Un panneau coûte 3,98 ms et 43,9 Kio**, à 1031 entités.

\fait{} **Le terme dominant n'était pas les panneaux, mais l'arbre causal.**
À ≈ 690 arêtes par pas, une fenêtre de 2000 pas en produit 1 380 113 :
**53,9 Mio de CSV par run**, contre 9,9 Mio de panneaux à k = 10. Les mêmes
colonnes en binaire compressé (`loss_edges.npz`, types étroits) tiennent en
**12,6 Mio** — un facteur 4,3. La campagne passe de 8,1 à 3,35 Gio. La
décision a été prise pendant le lot A plutôt que reportée : les lecteurs
(`scripts/branching.py`, `tests/test_persistence.py`) auraient dû être
touchés deux fois.

**Le pas d'échantillonnage k, et le critère qui le fixe.** Le critère est
écrit ici parce que le lot C pourra revoir k pour une raison entièrement
différente (la couverture de queue), et que deux valeurs choisies par deux
critères est acceptable là où deux valeurs sans critère ne l'est pas.

1. Le TEMPS n'est pas la contrainte : même à k = 1, les panneaux ajoutent
   8 s à un run de 220 s.
2. Le DISQUE l'est : k = 1 met la campagne de 108 runs à 11,3 Gio, k = 10 à
   3,35 Gio, k = 50 à 2,65 Gio (les 2,65 Gio incompressibles étant les
   événements).
3. Le pas doit rester petit devant le temps d'autocorrélation intégré de
   `prod_tot`, **52 pas** selon la lignée (cité dans le protocole de
   `scripts/campaign.py`), pour que l'échantillonnage ne replie pas la
   dynamique.

**k = 10** est le plus grand pas rond qui satisfasse k ≤ τ/5 = 10,4 :
200 panneaux par run, 1,0 Gio de panneaux pour la campagne entière, +0,3 %
de temps.

\fait{} La sonde de Gini (`record_market_stats`) coûte **+1,8 %** de temps
et 230 Kio par run. Elle est donc armée dans la campagne : le plan §3.1
exige que Ḡ soit mesuré par elle, et non déduit de `rotation = ρ·Ḡ`, qui
referait une identité.

### Les deux portes du lot A

\fait{} **Porte (i) — parité.** 8000 pas × 26 colonnes contre
`m4_3__d1__baseline__seed0` : **écart maximal NUL**, égalité bit à bit, en
762 s. 9 369 224 appels au noyau, tous sur le chemin identité — le MÊME
compte, à l'unité près, que la parité finale de v2
(`m4_3live_v2_credit_soc/results/analysis/parity_final_full.log`). Le fork
instrumenté est donc bit à bit le moteur v2, et le moteur v2 est bit à bit
M4.3 dans le régime homogène.

\fait{} Le diff de `m4_4/model.py` contre le moteur v2, modulo renommages,
ne contient **aucune ligne supprimée ni modifiée** : uniquement des ajouts.
`live.py` en compte dix, toutes dans l'écriture de fichiers et la
sérialisation — aucune dans un pas de simulation.

\fait{} **Porte (ii) — fermeture des panneaux.** `tests/test_panels.py`,
200 panneaux : effectif, `K_tot` et `nw_tot` bit à bit ; flux refermés à
1,8·10⁻¹⁴ près une fois les mortes ajoutées ; et 7,60 % d'écart sur
`prod_tot` si on les oublie. La parité ne voit rien de tout cela, ce qui est
précisément la raison d'être de cette seconde porte.

### Les deux estimateurs de b dans le régime de la campagne

\fait{} Sur la cellule `events` (graine 0, bras inerte, fenêtre
]2000, 4000], 60 151 morts) — `results/analysis/lotA_branching.json` :

| grandeur | valeur |
|---|---|
| b₁ = 1 − racines/morts | **0,7861** |
| b₂ = descendance moyenne par mort | **0,8485** |
| écart | **0,0624** |
| degré entrant moyen | 1,0793 |
| part des morts non racines à ≥ 2 parents | 7,35 % |
| arêtes de perte | 1 380 113, dont 67 664 mortelles et 51 037 causales |

\fait{} **Seules 4,9 % des arêtes de perte sont mortelles.** Les 95 autres
pour cent sont des créances perdues qu'une survivante absorbe sans tomber :
elles portent la propagation de la perte, pas la structure de la cascade.
Qui lira `loss_edges.npz` au lot D doit le savoir avant d'y chercher un
arbre — l'arbre est dans un vingtième du fichier.

\fait{} Le b₁ mesuré ici, **0,7861**, tombe sur le 0,7863 ± 0,0006 que le
plan §3.2 rapporte pour le bras `control` de v2 sur 12 graines. Le fork
reproduit donc la mesure de la lignée précédente sur une graine, ce qui est
un contrôle de plus que la parité ne donnait pas (elle porte sur le régime
homogène de M4.3, pas sur ce bras).

\fait{} **Les deux estimateurs restent sous-critiques** : 0,79 et 0,85 sont
tous deux < 1. Le verdict qualitatif de v2 ne dépend donc pas du choix
d'estimateur — seule l'amplitude en dépend.

\fait{} Le contrôle d'intégrité fonctionne : la même mesure sur la fenêtre
0..4000 rend `closes = false` et un b₂ absurde de 0,428, parce que la série
hérite des 2000 pas de l'amorçage alors que l'arbre causal ne commence qu'à
t₀. C'est exactement le piège que le champ `closes` est là pour rendre
impossible à commettre en silence.

### Décisions du §8 tranchées, et celles qui restent ouvertes

| # | question | tranchée ? |
|---|---|---|
| 1 | nom du dossier et du paquet | oui : `m4_4_rebond_credit_soc/`, paquet `m4_4`, routes `/live3` — avec la nuance additive ci-dessus |
| 4 | pas d'échantillonnage k | oui : **k = 10**, par le critère écrit plus haut, sur mesure et non sur goût |
| 2 | portée partielle | **non**, et aucun lot n'en dépend : à l'utilisateur de rouvrir s'il le veut |
| 3 | σ comme axe balayé | **non** dans les lots A–E, par le plan ; le lot F l'aborde par ablation |
| 5 | horizon des runs de queue | **non** : à mesurer au pilote C0, avant d'engager la campagne du lot C |

### La suite, reconduite sur le code final

\fait{} **16/16 verts en 1786 s**
(`results/analysis/suite_lotA_final.log`), dont les quatre nouveaux fichiers
— `test_branching`, `test_panels`, `test_checkpoint`, `test_persistence` —
et la parité complète relancée APRÈS le passage des arêtes en `.npz` et les
options ajoutées au pilote : 8000 pas × 26 colonnes, **écart maximal nul**,
723 s.

\fait{} La boucle shell habituelle du dépôt

    for t in tests/test_*.py; do python3 "$t" | tail -8; echo "rc=$?"; done

est un piège : `$?` y est le code de `tail`, jamais celui du test. C'est
ainsi que l'échec de `test_resume_divergence` du matin est passé pour un
`rc=0`. `scripts/run_tests.py` garde le vrai code de sortie de chaque
fichier et sort en erreur si un seul a échoué.

### Ce que le lot A n'a PAS fait, volontairement (revu le 24 août)

- `m4_4/tails.py` (estimateurs de queue, bootstrap) et son test sur
  échantillon synthétique de Pareto : ils appartiennent au lot C, qui les
  dimensionne à partir du pilote C0.
- Les quatre partitions d'entités du §4.5 : elles servent au lot C, et le
  plan ne les met pas dans la porte du lot A. Les panneaux portent déjà tous
  les champs dont elles ont besoin (`tech`, `age`, `K`, `claims`, `debts`).
- Les scripts d'analyse et de rapport de v2 (`analyse.py`, `rotation.py`,
  `survivors.py`, `make_numbers.py`, `make_traceability.py`) : non copiés,
  parce qu'ils lisent des résultats v2 et seront réécrits lot par lot. Ils
  restent lisibles dans le dossier gelé.
- Le bras `all_A150_K0comp` est DÉCLARÉ dans `scripts/campaign.py`
  (K0 = 25 · 1,5^(1/(1−γ)) = 56,25, par la formule et non par le nombre)
  mais n'est pas lancé : c'est le lot B qui l'exécutera.

---

## 24 août 2026 — Lot B lancé, et un chantier ajouté par l'utilisateur

### La campagne

12 amorçages en 411 s, puis 108 cellules (6 bras × règles de sens × 12
graines), instrumentées : décès, avalanches, arbre causal, panneaux à k = 10,
sonde de Gini. Le bras compensé `all_A150_K0comp` est vérifié avant
lancement : A → 1,5 sur les 1176 vivantes ET K0 → 56,25, deux interventions
au même pas, journalisées séparément.

### LE TAUX COMME VARIABLE DE PARTAGE — chantier ajouté le 24 août

Demande de l'utilisateur, explicitement rattachée à la caractérisation du
rebond et non traitée comme un travail séparé. Le taux cessait d'être une
grandeur économique pour n'être qu'une formule — la moyenne géométrique des
rendements marginaux. Il devient un **paramètre de partage** entre les deux
seules bornes que l'économie d'une paire admet.

**La formulation retenue.** Pour un contrat de principal `q` où la donneuse
`(A_d, γ_d, K_d)` cède à la receveuse `(A_r, γ_r, K_r)` :

```
L = A_d·K_d^γ_d − A_d·(K_d − q)^γ_d      perte de puissance extractrice
Δ = surplus coopératif de la paire        (déjà calculé par le noyau)
r · q = L + p · Δ,      p ∈ [0, 1]
```

- `p = 0`, **altruisme** : le service couvre exactement L. La donneuse fait
  une OPÉRATION BLANCHE — production d'après contrat plus intérêt reçu égale
  production d'avant — et la receveuse garde tout le surplus.
- `p = 1`, **asservissement** : le service vaut L + Δ = G, tout le gain de la
  receveuse. C'est elle qui fait l'opération blanche.

\fait{} Les deux égalités sont vérifiées à 10⁻⁹ relatif sur quatre paires
construites à la main (`tests/test_bargain_rate.py`), et la linéarité en p
est exacte à 10⁻¹⁵.

\fait{} **Les deux opérations blanches ne valent qu'AU MOMENT DU CONTRAT.**
Le taux est gelé là, comme celui de `pair_rate`, alors que les capitaux des
deux côtés continuent d'évoluer. « Opération blanche » ne veut pas dire
« sans conséquence » : la donneuse a définitivement moins de capital, donc
une trajectoire différente.

**Précision de l'utilisateur, et ce qu'elle imposait de vérifier** : le
paramètre gouverne les NOUVEAUX contrats et seulement eux ; les anciens
gardent leur taux. \fait{} C'est bien le cas, y compris quand une paire
re-traite : `LoanBook.add` fusionne les deux prêts et n'en garde qu'un taux,
la moyenne pondérée — mais le montant dû devient exactement
`q_ancien·r_ancien + q_nouveau·r_nouveau`. Le taux moyen n'est qu'une façon
de ranger deux taux dans un nombre ; **l'intérêt de l'ancien contrat est
préservé au joule près**. Vérifié explicitement, parce que c'est la condition
de la persistance demandée.

### Premier résultat : la lignée entière tournait à un partage équitable

\fait{} La règle historique `marginal` n'avait jamais été présentée comme un
partage. On peut désormais mesurer celui qu'elle opère :
`p_impliqué = (r·q − L)/Δ`. Sur 150 pas de moteur, la moyenne vaut **0,5210**
(`tests/test_bargain_rate.py`). Sur quatre paires isolées elle vaut +0,687,
+0,706, +0,126, +0,394 — donc dispersée, mais centrée près de la moitié.

\inference{} La moyenne géométrique des rendements marginaux réalise donc,
en moyenne, un partage presque exactement ÉQUITABLE du surplus coopératif.
Ce n'était ni voulu ni su : c'est une propriété de la formule, mise au jour
par le fait de disposer de l'échelle. Toute la lignée M4.3 → M4.4 se lit donc
comme le point p ≈ 0,52 d'un continuum.

\incertitude{} La dispersion paire à paire est large (0,13 à 0,71 sur quatre
paires) : la règle `marginal` n'est PAS un partage constant, seulement un
partage de moyenne proche de 0,5. La campagne dira ce qu'il en est sur des
centaines de milliers de contrats.

### Direction confirmée dès le moteur

\fait{} 250 pas depuis zéro, même graine : population **1935** sous
`p = 0` contre **1115** sous `p = 1`, intérêts versés 76 638 contre 33 595.
La prédiction de l'utilisateur — population beaucoup plus grande dans le cas
altruiste — est du bon signe dès le régime transitoire.

\incertitude{} Ce n'est pas encore l'état stationnaire, et le sens de
l'effet sur les intérêts VERSÉS est contre-intuitif (le cas altruiste en
verse plus au total) : c'est un effet d'effectif, pas de taux. À trancher sur
la campagne, en séparant taux moyen et masse de contrats.

\fait{} Aucun refus de paire faute de taux sous `bargain` : L > 0 dès que le
transfert l'est, contrairement à `surplus_share` qui pouvait rendre r ≤ 0.

\fait{} `bargain_p` est intervenable en direct (portées `all`/`new`, alias) :
le partage impliqué passe de 0,000 à 1,000 après une intervention à t = 101,
et les contrats antérieurs gardent leur taux.

\fait{} **La parité est conservée** après ces ajouts : 500 pas × 26 colonnes,
écart maximal nul. La règle par défaut n'a pas bougé, et le drapeau de mesure
`record_rate_split` ne change aucune colonne de trajectoire (vérifié sur
6 colonnes et 150 pas).

### Lot B — la porte, et une tension de la lignée qui se dénoue

Campagne : 5 bras × 12 graines sous le sens libre, fenêtre résiduelle
]3000, 4000]. Sorties : `results/analysis/lotB_{windows,paired,elasticities}.csv`
et `lotB_gate.json`.

**D'abord, la lignée est reproduite au chiffre près.** Le moteur est un fork,
la campagne est neuve, les amorçages sont neufs :

| élasticité | M4.4 (12 graines) | v2 (12 graines) |
|---|---|---|
| ε = dln(prod_tot)/dlnA | **+0,7473 ± 0,0106** | +0,7473 ± 0,0048 |
| dln(pop)/dlnA | **−0,7043 ± 0,0091** | −0,7043 |
| dln(n_prod)/dlnA | **−0,6834 ± 0,0091** | −0,6834 ± 0,0041 |
| γ·dln(K_eq)/dlnA | **+0,4308** | +0,4308 ± 0,0022 |

\fait{} L'identité du §3.1 se referme à **1,25·10⁻⁴**, mieux que les
5,3·10⁻⁴ de v2. Elle reste une IDENTITÉ : elle ne confirme rien, elle sépare
l'effectif de l'échelle.

**LA PORTE.** `dln(Ḡ)/dlnA = +0,5263 ± 0,0069`, contre la bande prédite
[0,5268 ; 0,5590] écrite avant mesure.

\fait{} La valeur tombe à **0,06 demi-intervalle** de la borne `a = 1,337`
et à **4,70 demi-intervalles** de la borne `a = 1,260`. Lire « hors de la
bande » serait un artefact de binarisation : la mesure est
indiscernable de la borne basse et exclut la borne haute.

\incertitude{} **Mais cette lecture vaut moins qu'il n'y paraît, et il faut
le dire.** La bande a été construite à partir du `dln(pop)/dlnA = −0,7043`
de v2, et c'est exactement ce que ce bras mesure : la prédiction et la mesure
partagent une entrée. Confronter l'une à l'autre teste donc surtout que le
bras reproduit v2 — ce qu'il fait — et non que l'exposant vaille 1,337.

**LE VRAI RÉSULTAT est ailleurs, et il dénoue la tension du §3.1.** Le plan
notait que les deux intervalles sur `a` ne se recouvrent pas, sans pouvoir
trancher. Mesuré ici bras par bras, en contraste apparié (jamais en
régression groupée — piège §14.2), sans passer par aucune bande :

| bras | a |
|---|---|
| `all_A150` | **1,334 ± 0,013** |
| `new_A075` | 1,325 ± 0,019 |
| `new_A150` | 1,310 ± 0,009 |
| `new_g060` | **1,268 ± 0,005** |

\fait{} `a` n'est PAS un exposant universel : il varie de 1,268 à 1,334
selon le levier, soit 5 %, et les intervalles ne se recouvrent pas entre
`all_A150` et `new_g060`.

\fait{} Les deux valeurs publiées antérieurement tombent chacune sur un
bras de cette campagne : **1,334 ± 0,013 sur `all_A150` contre les 1,337 de
v1**, et **1,268 ± 0,005 sur `new_g060` contre les 1,260 ± 0,009 de v2 —
intervalles qui se RECOUVRENT**. C'est la pièce la plus nette du dossier.

\inference{} Les deux estimations antérieures étaient donc toutes deux
justes, **chacune pour son corpus** : v1 mesurait un mélange dominé par le
levier A à portée globale, v2 un mélange où les leviers γ pèsent davantage.
Le désaccord n'était pas une erreur de mesure mais une différence de
mélange — et il ne pouvait pas se voir tant que `a` était supposé universel.
Aucune des deux lignées n'avait de quoi le découvrir : il fallait plusieurs
leviers mesurés séparément sur le MÊME corpus.

**Les deux autres maillons, et ce qu'ils valent.**

\fait{} `rotation = ρ·Ḡ` : l'élasticité de la rotation vaut +0,5265 et celle
de Ḡ +0,5263, soit un écart de 1,3·10⁻⁴. Les deux sont lues dans des
FICHIERS DIFFÉRENTS — `series.csv` pour le volume et le capital,
`market_stats.csv` pour le Gini du bassin — donc leur accord mesure quelque
chose. C'est le seul maillon de la chaîne qui soit à la fois non trivial et
vérifié.

\fait{} La loi de Little, elle, est une IDENTITÉ à l'état stationnaire :
naissances = morts = λ, donc mortalité = λ/pop et dln(mortalité) = −dln(pop)
par construction. Mesuré : +0,7021 contre +0,7043, écart 2,2·10⁻³. Ce n'est
pas une confirmation de la loi ; c'est un contrôle de stationnarité déguisé,
et il passe.

\fait{} Le contrôle de stationnarité du §6.2 passe sur les cinq bras :
rapport du dernier au premier quart de la fenêtre, |t| ≤ 1,83 < 2,201.
L'étendue par run va de 0,952 à 1,047 — c'est le plancher de bruit, et il
explique pourquoi la bande fixe [0,99 ; 1,01] de v2 rejetait 11 graines
sur 12.

### Lot C0 — la couverture, et une surprise structurelle

`scripts/laws.py --pilot`, sur `control/seed0`, 100 instantanés de la fenêtre
résiduelle. Cible dérivée et non choisie : `n_tail ≥ 400`, pour une
erreur-type de Hill ≤ 0,10 à α̂ ≈ 3.

| grandeur | n_tail médian | α̂ médian | SE |
|---|---|---|---|
| revenu d'intérêt | **247** | 3,90 | 0,184 |
| valeur nette | 282 | 2,76 | 0,105 |
| capital | 429 | **27,0** | 1,25 |
| production | 408 | **52,8** | 2,56 |

\fait{} La couverture est **2,2 fois meilleure que celle qui a bloqué
M4.2B** (n_tail médian 113). Le facteur manquant pour atteindre 400 est
1,62, soit λ ≈ 49 — une campagne à λ = 50 est lancée.

\fait{} **Le capital et la production n'ont pas de queue lourde.** Un α̂ de
27 ou 53 n'est pas une loi de puissance : c'est une décroissance quasi
bornée, et l'ajustement ne fait que suivre le bord de la distribution. Les
queues lourdes de ce modèle vivent dans le **revenu d'intérêt** et la
**valeur nette**, c'est-à-dire dans les BILANS. C'est exactement ce que M4B
avait établi par les Gini (NW 0,44 contre K 0,07), retrouvé ici par un
chemin entièrement différent.

\inference{} Conséquence pour le lot C : ajuster des classes de lois sur le
capital serait ajuster du bruit. Les familles candidates ne seront testées
que sur le revenu d'intérêt et la valeur nette.

### Lot T — les deux extrêmes, et une non-linéarité

Pilote, graine 0, fenêtre résiduelle :

| | population | capital | production | intérêts versés |
|---|---|---|---|---|
| `marginal` (avant t₀) | 1140 | 883 929 | 31 784 | 35 539 |
| p = 1 (asservissement) | **1129** | 877 782 | 31 523 | 35 748 |
| p = 0 (altruisme) | **1917** | 2 897 693 | 74 517 | 80 565 |

\fait{} La prédiction de l'utilisateur est vérifiée, et largement :
**+68 % de population** sous le partage altruiste.

\fait{} Les morts par pas restent à 30,0 dans les deux cas, c'est-à-dire λ :
à l'état stationnaire, naissances = morts. Ce que le partage déplace n'est
donc pas le flux de morts mais la MORTALITÉ PAR ENTITÉ, 30/pop — et c'est
elle qui fixe la population.

\fait{} La transition est rapide : 1176 → 1897 en 200 pas, puis plateau. La
fenêtre résiduelle est donc largement convergée, et le contrôle de
stationnarité pourra le confirmer sur les 12 graines.

\fait{} **Le cas asservi est indiscernable du régime historique** (1129
contre 1140), alors que `marginal` se situe à p ≈ 0,52 sur l'échelle. La
réponse au partage n'est donc pas monotone-linéaire : elle est presque plate
au-dessus de p ≈ 0,5 et s'envole quand p → 0.

\hyp{} Deux explications concurrentes, que le balayage complet doit
départager : (i) la réponse est intrinsèquement convexe en p ; (ii) le
partage impliqué par `marginal` est DISPERSÉ paire à paire (0,13 à 0,71 sur
quatre paires isolées), et c'est la queue haute de cette dispersion qui
gouverne, pas sa moyenne.

\fait{} Coût mesuré : la cellule altruiste prend 569 s contre 262 s pour
l'asservie — le prix d'une population 1,7 fois plus grande.

### Contrôle de version de la campagne, avant de publier quoi que ce soit

\fait{} Les 108 cellules ont été lancées à 00:17, et le moteur a été modifié
entre 00:35 et 00:50 (règles de taux, colonnes `mkt_loss`/`mkt_rq`/
`mkt_p_implied`). `mp.Pool` ayant forké ses ouvriers au lancement, ils ont
tourné sur le code d'avant — mais cela ne se voit pas de l'extérieur, donc
c'est vérifié : la cellule `control/seed0` REJOUÉE avec le code du jour rend
**4000 lignes × 26 colonnes, 0 cellule différente, écart maximal nul**
(`results/analysis/verify_code_version.log`). Les chiffres du lot B tiennent.

### Lot B — LA question du mandat : où va le surcroît ?

100 instantanés par run, 12 graines, bras `all_A150` contre `control`.
Sorties : `lotB_distribution.csv`, `lotB_contrasts.csv`, `lotB_distribution.json`.

**Les niveaux d'abord, parce qu'ils cadrent tout le reste** (bras `control`) :

| grandeur | niveau |
|---|---|
| part du revenu venant de l'intérêt | **0,533** |
| part des entités rentières (int_in > prod) | 0,450 |
| Gini de la production | **0,052** |
| Gini du capital | **0,057** |
| Gini du revenu d'intérêt | **0,513** |
| part des intérêts captée par le décile supérieur | 0,323 |
| part créancière nette / débitrice nette | 0,297 / 0,698 |

\fait{} **L'inégalité de ce modèle est presque entièrement dans le canal
d'intérêt.** Gini 0,51 sur les intérêts reçus contre 0,05 sur la production
et 0,06 sur le capital — un facteur dix. Et la moitié du revenu (53 %) passe
par ce canal. C'est le résultat de M4B (Gini NW 0,44 contre Gini K 0,07)
retrouvé sur une autre institution de principal, et cette fois avec le canal
identifié.

**Et maintenant, où va le ×1,80 ?** Rapport des quantiles traité/contrôle —
1,80 partout signifierait un pur changement d'échelle :

| grandeur | q10 | q50 | q90 | q99 | q99,9 |
|---|---|---|---|---|---|
| production | 1,748 | 1,806 | 1,823 | **1,831** | 1,816 |
| revenu total | 1,755 | 1,776 | 1,798 | 1,738 | **1,472** |
| valeur nette | 1,103 | 1,486 | 1,507 | 1,445 | **1,165** |
| capital | 1,386 | 1,451 | 1,477 | 1,489 | 1,460 |
| revenu d'intérêt | **0,105** | 1,743 | 1,793 | 1,722 | 1,444 |

\fait{} **La production monte par pur changement d'échelle.** Le rapport va
de 1,748 au premier décile à 1,831 au 99ᵉ centile : une inclinaison de 4,7 %
d'un bout à l'autre de la distribution, sur un facteur 1,8. Le Gini de la
production ne bouge que de 0,0518 à 0,0664.

\fait{} **La queue extrême capte MOINS que le corps, pas plus.** Au 99,9ᵉ
centile, le revenu total monte de ×1,47 et la valeur nette de ×1,17, contre
×1,78 et ×1,49 dans le corps. Le sommet est comprimé par le rebond, il n'est
pas amplifié. C'est l'inverse de ce qu'une intuition « les gros captent
tout » aurait prédit, et c'est le résultat le plus net de ce lot.

\fait{} **Le bas du canal d'intérêt s'effondre.** Le premier décile du revenu
d'intérêt passe de 0,295 à 0,033 joule par pas, soit ×0,11, pendant que la
médiane double (24,2 → 42,1). Les petits créanciers sont effacés ; les autres
suivent l'échelle. Le Gini des intérêts n'en bouge presque pas (+0,005)
précisément parce que ce bas de distribution ne pesait rien.

\inference{} La signature distributionnelle du rebond est donc : une
population plus petite (1132 → 852) et plus jeune (âge moyen 111 → 95 pas),
dont chaque membre produit 1,8 fois plus sur un bilan 1,45 fois plus gros, et
dans laquelle la petite rente a disparu. Le surcroît ne va ni à la queue ni
aux rentiers : il va au CORPS, presque proportionnellement, et il détruit le
bas du canal d'intérêt.

\fait{} Producteurs contre rentiers, la question du mandat, tranchée : la
part du revenu venant de l'intérêt passe de 0,5332 à 0,5265, soit
−0,0067 ± 0,0007. Le déplacement est significatif mais minuscule — **aucun
des deux canaux ne capte au détriment de l'autre**, les deux montent
ensemble, avec un très léger avantage à la production.

\fait{} Les autres bras confirment la lecture par leur contraste : à
`new_A075` (levier vers le BAS), tous les signes s'inversent — Gini de
production −0,0022, part rentière +0,0064, part créancière nette −0,0093. Le
mécanisme est donc bien attaché au sens du levier, et non à l'agitation.

### Lot D — avalanches et branchement, sur les 12 graines

`scripts/avalanches.py`, fenêtre résiduelle, bras sous sens libre.
Sorties : `lotD_avalanches.{csv,json}`.

| bras | b₁ | b₂ | α des tailles |
|---|---|---|---|
| `new_A075` | 0,7962 ± 0,0019 | 0,8573 ± 0,0022 | 1,697 ± 0,005 |
| `control` | **0,7863 ± 0,0013** | **0,8483 ± 0,0015** | 1,708 ± 0,006 |
| `all_A150_K0comp` | **0,7842 ± 0,0025** | 0,8450 ± 0,0027 | 1,716 ± 0,011 |
| `new_A150` | 0,7560 ± 0,0022 | 0,8171 ± 0,0023 | 1,751 ± 0,006 |
| `all_A150` | **0,7541 ± 0,0024** | 0,8154 ± 0,0030 | 1,750 ± 0,007 |
| `new_g060` | 0,7212 ± 0,0026 | 0,7876 ± 0,0023 | 1,779 ± 0,005 |

\fait{} Les b₁ reproduisent au millième les valeurs que le plan §3.2 avait
tirées de v2 : contrôle 0,7863 contre 0,7863 ± 0,0006 ; `all_A150` 0,7541
contre 0,7541 ± 0,0011 ; `new_A150` 0,7560 contre 0,7560 ± 0,0010 ;
`new_g060` 0,7212 contre 0,7212 ± 0,0012.

\fait{} **L'écart b₂ − b₁ est remarquablement constant** : 0,0609 à 0,0663
sur les six bras, alors que b₁ lui-même varie de 0,72 à 0,80. La
sur-détermination est donc une propriété du mécanisme de cascade, pas du
régime — 7,2 % à 8,5 % des morts non racines ont plusieurs parents, quel que
soit le levier.

\fait{} **LE RÉSULTAT DU LOT : la fragilité que le rebond fait apparaître
est un effet d'échelle de K0, à 93 % près.** Monter A abaisse b₁ de
−0,0322 ; compenser `K0 → K0·A^{1/(1−γ)}` en même temps ne laisse que
**−0,0021 ± 0,0025**, c'est-à-dire rien de significatif. **93,4 % de l'effet
est annulé.**

\inference{} C'est le même verdict que v1 avait obtenu sur la CONTRACTION DE
POPULATION (compenser K0 annule la contraction, pop ×1,005), obtenu ici sur
une grandeur entièrement différente et par une chaîne de mesure entièrement
différente. « Un marché plus productif est un marché plus fragile » est donc
un énoncé sur K0, pas sur A : ce qui rend le système fragile n'est pas que la
technologie s'améliore, c'est que la dotation de naissance reste une longueur
FIXE pendant que l'échelle du reste change. Le bras compensé était là pour
détecter exactement cela (plan §6) ; il l'a fait.

\fait{} **L'exposant des tailles d'avalanches vaut 1,708 ± 0,006 au
contrôle**, contre l'α∞ ≈ 2,31 de M4B. L'écart est massif et ne peut pas
venir de l'estimateur : `tests/test_tails.py` vérifie que l'implémentation
employée ici rend le même nombre que celle de M4B à 0,0·10⁰ près sur les
mêmes tailles.

\fait{} α < 2 signifie que la moyenne de la loi non tronquée diverge : dans
ce régime, c'est la troncature de taille finie qui fixe la taille moyenne des
avalanches. Consigne héritée respectée : aucune analyse de coupure n'est
faite, seule la loi de puissance est ajustée.

\fait{} Les avalanches maximales atteignent 108 à 160 entités selon le bras,
soit 10 à 15 % de la population vivante, et la susceptibilité ⟨s²⟩/⟨s⟩ va de
30 à 43. Le levier A la fait BAISSER (40,7 → 34,1), le levier γ aussi
(30,1) : les deux réduisent la taille caractéristique des cascades en même
temps qu'ils réduisent b.
