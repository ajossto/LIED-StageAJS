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

### Ce que le lot A n'a PAS fait, volontairement

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
