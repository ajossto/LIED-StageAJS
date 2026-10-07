# JOURNAL — M4.3Live

Journal de bord du programme. Faits datés, décisions et incidents ; le
raisonnement complet est dans `report/conception_m4_3live.pdf`.

## 2026-08-17 — spécification

Prompt `prompts/PROMPT_M4_3LIVE.md` (révision 2, 17 août) reçu, avec le rapport
d'architecture `prompts/rapport_architecture_offline_online.pdf` en lecture
obligatoire. Deux passages de `CLAUDE.md` / `docs/README_simulation_lab.md`
signalés comme obsolètes par le prompt : vérifiés, ils le sont bien (moteur de
référence = `m4_3_credit_soc`, RNG `numpy.random.default_rng`, gabarits
`launch.html`/`results.html`).

## 2026-08-17 — noyau d'institution et parité

- `m4_3live/kernel.py` : trois régimes routés sur des **identifiants entiers**
  de technologie. Le régime (a) est déclenché par `s_b == s_l`, pas par un test
  `λ* == 0.5` — c'est ce qui rend la parité « par construction » et non par
  coïncidence numérique.
- Équations du rapport revérifiées à la main avant codage : éq. 14 (forme
  fermée), éq. 17 (formulation en `(t,u,z)`), éq. 21 (une étape de Newton),
  éq. 12 (`h'(C) = q h / S`). Toutes correctes.
- **Ordre de convergence de la LUT mesuré** : erreurs 3,69·10⁻⁷ / 2,38·10⁻⁸ /
  1,51·10⁻⁹ pour 17 / 33 / 65 nœuds, rapports 15,5 et 15,8 ≈ 16. L'ordre 4
  confirme que la dérivée analytique alimentant l'interpolation de Hermite est
  juste (une dérivée fausse donnerait de l'ordre 2). Nœuds portés de 33 à 65
  par défaut.
- **Chemin tiède mesuré** : erreur max 9,8·10⁻² unité de capital sur le domaine
  réel de M4.3 — sept ordres de grandeur au-dessus de la LUT. D'où le défaut
  `kernel_policy="exact_lut"` (le chemin tiède reste implémenté et testé sous
  `"hybrid"`), justifié dans le rapport de conception.
- **Parité bit à bit avec M4.3** : run homogène graine 0, paramètres baseline,
  8000 pas, 26 colonnes comparées au run stocké `m4_3__d1__baseline__seed0` —
  **aucun écart**, pas même au dernier bit. 9 366 225 appels au noyau, tous sur
  le chemin identité. Contrôle croisé amusant : le rapport d'architecture
  compte 9 366 177 événements de prêt sur ce même run, soit exactement 48 paires
  de moins — les paires dont le principal tombe sous `MIN_LOAN`.

## 2026-08-17 — session en direct

- Un thread, pas un sous-processus (partage d'état sans copie ; jusqu'à 30 000
  entités).
- Compilation des tables du noyau **synchrone**, au point de déclenchement
  déterministe. Le rapport d'architecture suggère de la déporter sur un thread
  (§7.2) : refusé, un build asynchrone ferait basculer la table à un indice
  d'appel dépendant de l'ordonnancement et casserait le rejeu identique.
- **Réserve trouvée et bornée sur les snapshots** : après un aller-retour
  `pickle`, l'ordre d'itération de ~la moitié des `set` de `by_borrower` change
  (mesuré : 225 sur 467). Conséquence exacte, vérifiée sur 90 pas : la
  dynamique est **bit-identique** (K_tot à 0 près), seuls `interest_paid` et
  `int_out` — deux agrégats de diagnostic — varient au dernier bit (2,1·10⁻¹⁶
  relatif). Cause : la phase d'intérêts somme les versements dans l'ordre du
  `set`, hérité de M4.3 ; chaque versement va à une prêteuse différente, donc
  aucun capital n'est affecté. Documenté plutôt que corrigé : le corriger
  demanderait de changer la structure de données et de perdre la parité M4.3.

## 2026-08-17 — protocole de la campagne

- **t₀ = 2000, fenêtre W = 2000**, justifiés sur des résultats DÉJÀ sur disque
  (le prompt interdit de remesurer la relaxation) : `t_converge_int_in` =
  1016 / 948 / 841 sur les trois graines baseline de M4.3, et `prod_tot`
  stationnaire par blocs de 500 dès t ≈ 500. Temps d'autocorrélation intégré de
  `prod_tot` mesuré à ≈ 52 pas sur la queue des mêmes séries.
- **Bras `null`** ajouté au plan : il tire la fraction φ et n'applique rien. Il
  fixe le plancher de bruit dû au décalage de flux aléatoire, et il sert de
  référence appariée EXACTE aux bras `fraction` (même état du générateur, même
  cohorte tirée). Sans lui, « effet rebond » et « les flux ont divergé » sont le
  même nombre.
- **Compteurs de refus séparés** (`mkt_blocked_dir` / `mkt_blocked_tiny` /
  `mkt_blocked_rate`) ajoutés à la série : sans eux, l'effondrement du volume de
  prêt d'un bras traité serait ininterprétable.

## 2026-08-17 — pilote du plafond institutionnel (§11)

Pilote mené sur un bras **traité** (φ=0,2, A×1,5), jamais sur le contrôle : en
régime homogène λ*=1/2 et les deux plafonds coïncident exactement, le contrôle
ne peut donc rien départager.

Fait observé, et c'est le mécanisme le plus intéressant trouvé jusqu'ici : le
plafond d'égalisation mord 149 fois au pas h=1, 24 fois à h=5, 1 fois à h=25,
**jamais** au-delà de h=50. Raison : les entités dopées accumulent du capital et
deviennent en quelques dizaines de pas le côté RICHE de presque toutes leurs
paires ; l'optimum de production jointe voudrait alors leur envoyer du capital,
et le sens du prêt (riche → pauvre) l'interdit. La paire ne traite plus du tout
— `mkt_blocked_dir` se stabilise autour de 25 % des rounds. Le plafond devient
sans objet. Décision : `transfer_cap = "optimum"`, l'énoncé littéral de
l'institution, le plafond restant implémenté en ablation.

## 2026-08-17 — chantier taux/p (§3.4)

Abouti, mais **désactivé par défaut**. L'hypothèse manquante retenue : dans ce
modèle la production est un flux par pas, donc Δ aussi ; on le gèle au contrat
comme l'est déjà le rendement marginal, et `r = p·Δ/q`. Mesuré : `r` vaut au
plus 0,227 fois le taux marginal sur un échantillon de paires représentatif —
le service est donc plus LÉGER, pas plus lourd, et aucun pic de défauts n'est
observé (0 défaut sur 120 pas dans les deux règles, intérêts versés divisés
par 10). `rate_rule="marginal"` reste le défaut : la question du rebond est
mesurable avec le mécanisme existant, et aucune cellule de campagne n'utilise
la règle candidate.

## 2026-08-17 (soir) — campagne §7 et verdict

**Amorçages** : 5 graines × 2000 pas en 220 s (5 procs). **Bras** : 9 × 5
graines × 2000 pas en 1865 s (6 procs). 45/45 terminés `ok`, aucun carnet
incohérent, aucune transaction plafonnée — vérifié automatiquement par
`scripts/analyse.py`, qui refuse d'analyser une campagne incomplète plutôt
que de moyenner silencieusement des séries tronquées.

**Validation de la chaîne de mesure.** À l'horizon 1, les capitaux du bras
traité sont encore exactement ceux de sa référence appariée. L'amplitude
reconstruite à partir des seules mesures agrégées vaut 1,5000 / 1,2500 /
1,5000 / 1,5000 / 1,5000 pour les cinq bras à levier sur A — les valeurs
imposées, à quatre décimales — et `all_A150` donne +50,0000 % pour une part
ex ante de 1,0000. Le bras γ donne 1,9462 : le passage γ 0,5→0,6 n'est PAS
un choc de même taille que A×1,5, il est presque deux fois plus fort.

**Deux corrections de dénominateur** trouvées en route, toutes deux
matérielles : (1) `tech_series` mesure la part de production APRÈS
application du levier, il faut l'inverser en part ex ante sous peine de
sous-estimer l'élasticité de 10 % ; (2) l'amplitude d'un levier sur γ vaut
K^Δγ, elle dépend du capital et doit être mesurée, pas imposée.

**Verdict** (détail et figures dans `report/rapport_final.pdf`) :
- portée partielle + court horizon → **rebond observé**, élasticité 2,3 à
  2,9, de 3 à 48 σ, stable sur deux amplitudes, trois intensités et deux
  leviers ;
- portée globale + régime établi → **effet inverse**, élasticité 0,72
  (88 σ) : +36,1 % de production pour +50 % de A, avec production par
  entité ×1,80 mais population ×0,754 ;
- portée partielle + long horizon → **non tranchable** : la cohorte traitée
  s'éteint (part de production 0,198 → 0,022) et le dénominateur disparaît.

**Prémisse du prompt contredite par les données** (§2) : `fraction` ne
« fixe » pas l'intensité de traitement dans ce modèle — elle la fait
dériver vers zéro en ~300 pas, pendant que `new` la fait monter de 0 à 1 en
~600 pas. Les deux portées dérivent. Ce sont `all`/`new` qui portent la
version à intensité fixe de la question. Le protocole a été conservé tel
quel (il donne les deux réponses) mais la lecture en tient compte.

## 2026-08-17 (soir) — banc du noyau, seuils recalibrés (§11)

Débits mesurés sur cette machine, 300 000 appels, meilleur de 5 :
identité 3,23 Mreq/s, γ égaux 2,04, table Hermite 65 nœuds 0,83, tiède
0,42, Newton exact 0,13. Compilation d'une ligne : 0,45 ms.

- **Seuil d'amortissement mesuré : 71 usages** par ligne d'exposant, contre
  ~1800 sur le banc synthétique du rapport (notre Newton exact est plus
  coûteux, la compilation reste très bon marché).
- **Le noyau ne pèse que 1,3 % du temps d'un pas** (1268 appels par pas,
  114 ms par pas) : le pas est dominé par la phase d'intérêts, qui parcourt
  ~32 000 contrats. La valeur exacte du seuil est donc sans portée
  pratique ; `lut_threshold` est laissé à 1800 (la valeur avec laquelle
  toute la campagne a tourné), l'abaisser déplacerait les trajectoires au
  niveau 1e-9 pour un gain non mesurable.

## 2026-08-17 (soir) — IHM et non-régression

IHM `/live` vérifiée dans un vrai navigateur (chromium sans tête) sur une
session pilotée en direct avec deux interventions asynchrones : quatre
graphiques avec repères d'intervention, tableau de dispersion des
technologies, journal, compteurs du noyau. Deux défauts trouvés et
corrigés à cette occasion : le tableau des technologies restait vide (l'état
comparait à `simulation.t`, que le thread de boucle peut avoir déjà
incrémenté avant d'écrire les lignes du pas), et les axes descendaient sous
zéro pour des grandeurs positives.

Non-régression de `simulation_lab` **exécutée**, pas relue :
`list-models` (11 modèles), `list-runs` (447 runs), `run` et `batch`
réels sur `m4b_credit_soc_mini`, et 14 routes HTTP dont les anciennes
(`/`, `/launch`, `/results`, `/static/*`, `/api/*`) toutes à 200, `/live*`
à 200, `/inexistant` à 404. Trace complète dans
`results/analysis/nonregression.txt`.

## 2026-08-18 — corrections de dernière relecture

- **Base de calcul des faillites corrigée dans le rapport de résultats.** Le
  nombre absolu de morts par pas est fixé par le flux de naissances (λ=30 à
  l'état stationnaire) : le rapporter tel quel (×1,001) faisait lire comme
  « stable » un taux qui, ramené à une population 25 % plus petite, monte de
  33 % par entité ; les racines d'insolvabilité passent de ×1,155 en absolu à
  ×1,532 par entité. Les deux bases sont désormais données côte à côte.
- **Le test de parité existe maintenant dans le dépôt**
  (`tests/test_parity_m4_3.py`, 500 pas par défaut, `--full` pour les 8000).
  La vérification la plus forte du programme ne vivait que dans un script
  temporaire, donc citée partout mais non reproductible.
- **`mkt_blocked_dir` nul sur `all_A150` : vérifié exhaustivement** — somme
  rigoureusement nulle sur les 5 × 2000 = 10 000 lignes de série, et non
  seulement sur quelques horizons échantillonnés. Le mot « exactement » est
  donc justifié.
- **Constance de l'élasticité d'impact nuancée.** E varie de 2,32 à 2,86 sans
  tendance monotone, et la cellule φ=0,05 n'est mesurée qu'à 3,2 σ : c'est le
  signe et l'ordre de grandeur (facteur ≈2,5) qui sont solides, pas le
  classement des cellules entre elles.

## 2026-08-18 — vérifications demandées, et une inférence réfutée

Quatre vérifications demandées par l'utilisateur : simulations consultables
dans `simulation_lab`, norme de raisonnement scientifique, faits illustrés,
rapports autonomes. Elles ont fait apparaître une erreur de fond et deux
lacunes de forme.

### L'inférence sur le service d'intérêts était fausse

Le rapport attribuait la contraction de population du bras global à un
service d'intérêts alourdi. **Réfuté par les données** : le service rapporté
à la PRODUCTION — le dénominateur qui décide si une entité peut payer —
passe de 1,128 à 1,093, il s'ALLÈGE. Seul le service rapporté au capital
monte (+21 %), mais la production par unité de capital monte davantage
(+25 %). L'inférence a été retirée du rapport et remplacée par une ablation.

### Ablation K0 : la contraction est un artefact d'échelle, et elle inverse le verdict

Hypothèse restante : `K0 = 25` est fixe alors que le capital moyen par
entité monte de 773 à 1118, donc une entité naît relativement plus pauvre
(3,23 % → 2,24 % du capital moyen). Cinq bras, 5 graines, mêmes snapshots à
t₀ (`scripts/ablation_k0.py`, 25 runs, 1287 s).

Contrôle de méthode d'abord : `abl_control` reproduit `control` **bit à
bit** sur 6 colonnes × 5 graines, ce qui vérifie que le drapeau
`record_deaths` (ajouté pour obtenir les âges au décès) est bien inerte.

| bras | population | production | K0/(K par entité) | vie moyenne | ε_prod,A |
|---|---|---|---|---|---|
| contrôle | ×1,000 | ×1,000 | 0,0323 | 37,7 | — |
| A×1,5 | ×0,754 | ×1,359 | 0,0224 | 28,4 | 0,756 |
| A×1,5 + K0×2,25 | **×1,005** | **×2,267** | 0,0322 | 37,9 | **2,018** |
| A×1,5 + K0×1,45 | ×0,856 | ×1,708 | 0,0265 | 32,3 | 1,320 |
| K0×2,25 seul | ×1,358 | ×1,694 | 0,0468 | 51,2 | — |

Compenser K0 à l'échelle autarcique (×A^{1/(1-γ)} = ×2,25) **annule
entièrement** la contraction, et ramène à leur valeur de contrôle TOUS les
diagnostics : capital de naissance relatif, durée de vie, part des morts
avant 10 pas (0,416 contre 0,413), racines d'insolvabilité (×1,018 contre
×1,155). La distribution des âges au décès montre que le surcroît de
mortalité du bras non compensé est concentré sur les tout premiers pas de
vie.

Conséquence sur le verdict : ε = 0,756 à K0 fixe (sous-proportionnel) mais
ε = 2,018 à K0 compensé — et 1/(1-γ) = 2 exactement, l'exposant de l'échelle
autarcique. **Le signe du résultat global dépend donc d'une convention**,
celle que le prompt laissait ouverte au §11 et que j'avais tranchée en
découplant K0. Le caveat que j'avais documenté était le facteur dominant.
Les deux chiffres sont conservés dans le rapport : ils répondent à deux
questions différentes.

### Consultabilité et traçabilité

- `scripts/import_to_simulation_lab.py` : **75 runs** (5 amorçages, 45 bras
  de campagne, 25 d'ablation) enregistrés par symlink + `run.json`, chacun
  avec une figure de synthèse `figures/macro_overview.png` générée pour
  l'occasion. `m4_3live_credit_soc` ajouté à `ACTIVE_MODEL_IDS`
  (`simulation_lab/settings.py`) — sans quoi la lignée serait classée
  archivée et non supprimable.
- `scripts/make_traceability.py` : annexe de traçabilité (79 runs, y compris
  les runs M4.3 cités), insérée dans les deux rapports, plus
  `results/analysis/traceability.csv`.
- `scripts/conception_evidence.py` : les six faits du rapport de conception
  qui n'avaient qu'un chiffre dans le texte ont maintenant chacun leur
  fichier de données ET leur figure.
- `report/model_summary.tex` : section partagée définissant le modèle, le
  pas de temps, toutes les notations et les trois portées — les deux
  rapports se lisent désormais sans accès au code ni aux lignées antérieures.

### Deux mesures rectifiées au passage

- **Ordre de convergence de la table** : le premier échantillon gardait C
  constant, donc ne sondait qu'un point de table ; les rapports mesurés
  étaient erratiques (48,7 puis 6,3). Sur un balayage complet du domaine
  (400 paires, C de 192 à 2214) : 14,6 / 15,4 / 16,2 / 15,3 ≈ 16, ordre 4
  confirmé. L'erreur à 65 nœuds sur tout le domaine est 1,05·10⁻⁸ (et non
  1,51·10⁻⁹, qui valait pour une plage de C étroite).
- **Plafond d'égalisation** : « ne mord jamais au-delà de h=50 » était faux.
  Il mord encore 23 fois en 550 pas, soit environ une transaction sur
  29 000. La décision ne change pas, la formulation si.

## 2026-08-18 (suite) — la loi d'échelle ε = 1/(1−γ), testée

L'ablation K0 laissait une incertitude explicite : ε = 2,018 n'était mesuré
qu'en γ = 0,5, où 1/(1−γ) vaut 2. Une égalité en un point n'est pas une loi.
`scripts/scaling_gamma.py` rejoue le même protocole en γ = 0,4 et γ = 0,6,
où la loi prédit des valeurs franchement différentes. Chaque γ reçoit son
propre amorçage de 2000 pas et son propre contrôle apparié.

| γ | compensation K0 | production | population | ε mesuré | 1/(1−γ) | écart |
|---|---|---|---|---|---|---|
| 0,4 | ×1,966 | ×1,949 ± 0,002 | ×0,993 | **1,646** | 1,667 | −1,2 % |
| 0,5 | ×2,250 | ×2,267 ± 0,011 | ×1,005 | **2,018** | 2,000 | +0,9 % |
| 0,6 | ×2,756 | ×2,753 ± 0,013 | ×0,999 | **2,497** | 2,500 | −0,1 % |

La loi est vérifiée à mieux que 1,3 % sur une plage où ε varie lui-même de
52 %. Et la compensation neutralise l'effet de population à chaque γ, pas
seulement en γ = 0,5. Contrôle préalable : les amorçages sont stationnaires
à t₀ pour les deux nouveaux γ (rapport dernier quart / quart précédent :
1,0014 et 0,9993), donc le t₀ calibré sur γ = 0,5 y est valide.

Énoncé retenu : **quand le capital de naissance suit l'échelle
technologique, la production agrégée se comporte comme l'échelle autarcique
A^{1/(1−γ)}** — une loi de puissance dont l'exposant ne dépend que du
rendement d'échelle de la production, pas des paramètres du marché du crédit.

Coût : 6 amorçages (γ=0,4 : 530 s chacun ; γ=0,6 : 104 s) puis 12 bras
(γ=0,4 : ~1200 s ; γ=0,6 : ~136 s). γ=0,4 est cher parce que le carnet y
compte ~125 000 contrats actifs contre ~33 000 à γ=0,5.

## 2026-08-18 (suite) — ce qui domine vraiment le coût d'un pas

Trouvé en cherchant pourquoi les bras γ=0,4 dépassaient l'estimation. **Le
coût d'un pas croît de 20 % entre t=210 et t=1810** à prêts actifs
(31–37 k) et population (~1100) constants. La seule quantité qui croît est
le nombre de clefs de `by_borrower`, que la phase d'intérêts parcourt
entièrement à chaque pas : 6389 → 54 527, dont **98 % pointent sur un
ensemble vide** — les entités mortes, dont `LoanBook.remove` retire le
contrat sans jamais supprimer la clef (hérité tel quel de M4.3).

Assumé et documenté plutôt que corrigé, pour la même raison que l'ordre des
`set` : purger ces clefs changerait l'ordre de sommation de `interest_paid`
et ferait perdre la parité bit à bit. Conséquence pratique pour dimensionner
une campagne : **le coût d'un run croît avec λ × T**, c'est-à-dire avec le
nombre d'entités jamais nées, et pas seulement avec la taille instantanée du
système. Mesures dans `results/analysis/step_cost_growth.json`.

**93 runs** sont désormais consultables dans `simulation_lab` (5 amorçages,
45 bras de campagne, 25 d'ablation, 18 de loi d'échelle), et l'annexe de
traçabilité en recense 97 avec les runs M4.3 cités.

## 2026-08-18 (soir) — relecture annotée du rapport final

28 notes manuscrites sur `report/rapport_final.pdf`, extraites par
`mutool show … grep` et archivées dans
`../m4_3live_v2_credit_soc/notes/notes_rapport_final.md`. Le PDF de
conception ne porte **aucune** annotation sur le disque (0 objet
`/Subtype/Text`, vérifié deux fois) : les notes n'y ont pas été
enregistrées depuis la visionneuse.

Feuille de route v2 écrite dans `../m4_3live_v2_credit_soc/ROADMAP.md`,
chaque ligne citant sa note d'origine. **Le moteur n'a pas été touché** :
tout ce qui suit est soit un dérivé des séries déjà écrites, soit un
nouveau run avec le moteur inchangé.

### Note [16] — l'amplitude est maintenant mesurée, plus reconstruite

`scripts/exact_amplitude.py`. Le tour : après le pas de l'intervention,
`population.prod[i] = A' K_i^{γ'}` est en mémoire, donc le capital au moment
de produire se retrouve **exactement** par `K_i = (prod_i/A')^{1/γ'}`. On
écrit alors la production contrefactuelle `A K_i^γ` de chaque entité traitée
et l'on obtient m et p sans aucune inversion.

Résultat : m = 1,500000 / 1,250000 / 1,946184 ; part ex ante de `all_A150`
= 1,000000 exactement (les nées du pas reçoivent aussi la nouvelle
technologie). L'ancienne reconstruction agrégée est **validée** à
1,5·10⁻⁵ près. Et **E(h=1) = 1 à 1,0·10⁻¹⁵** sur les six bras à levier.

### Note [14] — le relecteur avait tort, et la mesure le montre

Le choc frappe bien entre l'intervention et la production, mais il est
**commun aux deux bras appariés** : mêmes vivantes, même ordre, même état du
générateur. Il ne s'annule pas terme à terme, il est simplement identique
des deux côtés. L'égalité `écart observé = (m−1)p` est donc exacte, pas
approchée — et elle l'est à la précision machine (ci-dessus).

### Note [28] — ε = 1/(1−γ) est démontré, plus seulement mesuré

`scripts/scaling_theory.py`. **Le modèle est covariant d'échelle** : avec
`A → A'` et `K0 → cK0`, `c = (A'/A)^{1/(1−γ)}`, chaque phase du pas est
homogène de degré 1 en capital et le taux d'intérêt marginal est invariant
(c'est un nombre sans dimension). Les deux simulations sont la même à
l'échelle c près. Vérifié depuis t=0 : écart max **5,2·10⁻¹⁵** sur
`prod_tot`, **population rigoureusement identique**, ε = 2,0000 et 1,6667
exactement. Sans compensation : 58 % d'écart, ε = 0,71 ; au mauvais exposant
(K0×1,5) : 39 %, ε = 1,34.

Corollaire qui corrige une inférence que j'allais écrire : les ±1,3 %
résiduels de la loi empirique **ne viennent pas** des constantes
dimensionnées (`MIN_LOAN` pèse 10⁻¹⁵) mais de la relaxation incomplète du
protocole à snapshot, qui part d'un état non rééchelonné.

### Note [17] et [22] — la tension, et le test qu'elle ne passe pas

`scripts/tension.py` (définition), `tension_figures.py` (par run),
`tension_analysis.py` (lecture croisée). T = K_aut/K_eq avec
K_eq = (prod/(n·A))^{1/γ}. Calculée sur les 93 runs existants sans en
relancer un seul ; chaque run porte désormais `tension.csv`,
`tension_agg.csv` et `figures/tension.png`.

Le système observé tourne à **T ≈ 13,3**, un treizième de son échelle
autarcique. Compenser K0 conserve T à 0,5 % près (13,26 contre 13,32) là où
le même choc sans compensation le porte à 21,12.

**Le test des quatre leviers** (`scripts/tension_sweep.py`, 39 runs,
2390 s) : K0 seul (3 → 400), δ seul (0,005 → 0,04), A seul (0,75 → 2),
appliqués au même état à t0.

- À **δ fixé** : `morts/pop ∝ T^0,668`, R² = 0,9885 sur 100 runs et une
  plage de tension ×15, écart médian 1,4 %, les trois leviers d'accord à
  mieux que 4,3 %. Le cas le plus net : `K0/4` et `A×2` — sans rapport —
  amènent à T = 29,46 et 29,61 et donnent 0,04282 et 0,04304 morts/pop.
- **δ casse tout** : facteur 8 sur δ → facteur 13,4 sur T mais 14 % sur la
  mortalité. `δ=0,04` (T=2,78) et `K0=400` (T=3,12) ont la même tension et
  des mortalités dans un rapport 3,3. R² tombe à 0,58.

**Donc la tension n'est pas un paramètre d'état** : c'est un diagnostic
d'échelle valide à δ fixé. Ce qui aligne les quatre leviers est
`loan_volume/K_tot` — la rotation du crédit — avec
`morts/pop ∝ rotation^1,337`, R² = **0,9982**, écart médian 0,41 %, biais
par levier entre −1,7 % et +0,7 %. Variable **endogène** : régularité
descriptive, pas loi de contrôle. Elle désigne le canal.

### Notes de rédaction traitées

[2] E|ξ| = σ√(2/π) ≈ 8·10⁻³ et contribution nette du choc mesurée (−0,41 %
de K_tot sur 2000 pas) · [5] le cas K<1 retiré, remplacé par l'énoncé correct
en rendement marginal · [7] « meilleure technologie » retiré des deux
rapports (l'ordre des rendements marginaux dépend du capital) · [9]
définitions de h, m, p, E réécrites avec exemple chiffré · [15] tableau de
calibration → figure à trois panneaux, un par colonne · [19] note de bas de
page Student à 4 ddl, seuils recalculés (2,78 à 5 %, 4,60 à 1 %), aucun
verdict ne bascule · [20] paragraphe du creux réécrit avec son tableau ·
[21] calcul du ×1,80 déroulé · [23] surplus coopératif défini avant emploi ·
[24] figure des canaux : panneau des morts retiré, K_tot coupé à +0,7 avec
encart · [25] réponse cumulée réécrite · [26] ablation resserrée sur le fait.

---

## 21 août 2026 — figure 12 reprise, deux covariances, l'exposant dlnT/dlnA

### Figure 12 refaite (retour de relecture)

*« On doit avoir un graph différent pour des gammas différents. Pas de
régression linéaire, on ne voit pas que les runs se font en fonction d'écarts
à la base-line différents. »*

La figure superposait trois γ dans un plan et y traçait quatre ajustements.
Vérification faite, **les trois ajustements par γ portaient sur du bruit** :
à γ = 0,4 les neuf runs couvrent une plage de tension de 0,6 %, à γ = 0,6 de
1,0 % — ce sont des runs à échelle compensée, faits pour *ne pas* déplacer la
tension. Le garde-fou de `tension_analysis.py` testait le nombre de valeurs
distinctes et non l'étendue ; il laissait donc passer un ajustement de pente
1,02 (R² = 0,371) sur neuf points identiques au troisième chiffre. Corrigé en
test d'étendue (facteur 1,5 minimum).

Le quatrième ajustement, « tous γ confondus » (R² = 0,72), méritait mieux
qu'un rejet à vue. La droite passant par les **trois seules lignes de base**
a pour exposant 0,410, contre 0,396 pour l'ajustement sur les 127 runs : les
deux coïncident à 3,5 %. **L'ajustement global ne mesurait aucune réponse à
la tension, il mesurait le déplacement de la base avec γ.**

Nouvelle figure : un panneau par γ, axes absolus partagés, base du panneau en
étoile pleine et bases des deux autres γ en étoiles creuses (la droite retirée
joignait exactement ces trois étoiles), encart en écart à *sa* base, durée de
vie en second axe puisqu'elle est l'inverse exact du taux. Aucun ajustement.

### Covariance de pas de temps (§7.3, `scripts/time_rescaling.py`)

Hypothèse du relecteur : λ→2λ, δ→2δ−δ², σ→√2σ ⇒ « deux pas d'avant se
déroulent en un pas ». **Les trois substitutions sont exactes**, chacune pour
une raison différente : identité algébrique pour δ ; somme de deux
log-normales, dérive comprise, pour σ ; somme de deux Poisson pour λ.

**Elles ne suffisent pas.** Deux phases sont des débits par pas et manquent à
l'appel : la production (`A→2A`, qui porte aussi le taux d'intérêt
γAK^{γ−1}) et le marché (`ρ→2ρ`, R = floor(ρN) rondes par pas). Mesuré sur
12 runs, 4 bras × 3 graines, comparés à temps ancien égal :

| | énoncé brut | + A×2 | + A×2 et ρ×2 |
|---|---|---|---|
| population | ×1,853 | ×1,145 | **×1,067** |
| production / pas ancien | ×0,701 | ×1,246 | **×1,118** |
| morts / pas ancien | ×0,997 | ×1,000 | **×1,003** |
| tension T | ×0,434 | ×0,867 | **×0,943** |
| prêts actifs | ×1,570 | ×0,690 | **×1,167** |

Les trois prédictions du relecteur tiennent **dans leur substance** avec les
cinq substitutions (population inchangée à 7 %, production par pas neuf
×2,24) et **pas du tout** avec trois seulement.

Deux points à retenir. **Piège de lecture** : sous l'énoncé brut `K_tot` ne
bouge que de 1 % — pas parce que le système est conservé, mais parce que
chaque entité est deux fois plus petite et qu'il y en a presque deux fois
plus. C'est l'observable la moins informative sur cette transformation.
**Résidu irréductible** : la phase de marché ne se compose pas — deux rondes
de ρN appariements ne valent pas une ronde de 2ρN, parce que la seconde voit
l'état laissé par la première. C'est ce qui distingue ce modèle d'une
équation différentielle.

Classement induit : δ, σ, λ, A, ρ sont des grandeurs **par pas** ; γ, K0 et
les règles sont des grandeurs **de forme**.

### « A×x implique-t-il T×x ? » (§6.5, `scripts/tension_vs_A.py`)

Lecture de la figure 14 par le relecteur. **Presque vrai, et systématiquement
faux** : à γ = 0,5 et K0 fixé, `all_A150` porte la tension de 13,32 à 21,12,
soit ×1,586 pour A×1,5. Sur quatre valeurs de A, la relation est une loi de
puissance nette d'exposant 1,145 (R² = 0,9999).

L'exposant n'est pas libre. En dérivant `ln T = ln K_aut − ln K_eq` :

    dlnT/dlnA = 1/(1−γ) − (1/γ)(ε_prod − η_pop − 1)

C'est une **réécriture des définitions**, pas une hypothèse — le résidu de
10⁻³ mesure la propreté de l'aller-retour `prod = n·A·K_eq^γ`, pas la
validité de l'identité. Ce qui est non trivial, c'est que ε_prod (0,64 /
0,71 / 0,75) et η_pop (−0,72 / −0,72 / −0,75) sont presque insensibles à γ :
toute la dépendance en γ de l'exposant est **géométrique**.

Balayage à trois γ (30 runs neufs, branchés sur les amorçages existants) :

| γ | exposant mesuré | R² |
|---|---|---|
| 0,4 | 0,776 | 0,9999 |
| 0,5 | 1,145 | 0,9999 |
| 0,6 | 1,673 | 1,0000 |

L'exposant ne passe par 1 qu'au voisinage de **γ ≈ 0,46**. Et sous
compensation de K0 il vaut exactement 0 (mesuré −0,012) : le phénomène est
entièrement un effet du décalage entre l'échelle du système et un capital de
naissance laissé derrière.

*Prédiction écrite avant de lancer* : 0,59 et 1,78, en supposant
ε_prod − η_pop ≈ 1,43 constant. Le sens est confirmé, les valeurs ratées de
0,19 et 0,11 — la différence vaut 1,356 / 1,433 / 1,501, elle dérive
lentement. Non expliqué : c'est la seule chose que ce test laisse ouverte.

### D'où vient le résidu du recalage temporel

Le §7.3 affirmait d'abord un résidu « d'ordre δ ». **Faux** : le déplacement
de K_aut vaut 1,0 % quand le résidu vaut 11,8 à 16,7 %. Deux tests :

- **`s = 4` ne tranche pas.** Le résidu triple, mais le déplacement de K_aut
  triple aussi — les deux termes croissent en (s−1), un pas neuf recouvrant
  s−1 compositions manquées. Compatible avec les deux explications.
- **`δ = 0,002` tranche.** Le terme de K_aut tombe à 0,20 % (cinq fois
  moins), et le résidu ne décroît pas : production +11,8 % → +15,0 %,
  capital +15,8 % → +22,1 %. La discrétisation est écartée. Le résidu vient
  de la **phase de marché**, qui ne se compose pas.

Ce n'est donc plus une explication par élimination. Un recalage exact
demanderait de composer les appariements eux-mêmes — question ouverte, et
probablement le vrai contenu de la limite en temps continu du modèle.

### État

**203 runs** dans `simulation_lab`, annexe de traçabilité à 207 lignes, 0
sans rôle. Les numéros de figure de `make_traceability.py` dataient d'une
version antérieure du rapport (16 figures, 18 aujourd'hui) : remplacés par
des renvois de section, vérifiés sur le PDF construit.

### Prompt de la v2

Écrit à la demande de l'utilisateur, dans
`modeles/m4_3live_v2_credit_soc/prompts/PROMPT_M4_3LIVE_V2.{md,tex,pdf}` (14 pages).

**Choix de structure** : le prompt de v1 était organisé par *sous-système*
(institution, architecture en direct, IHM, intégration, protocole), parce
qu'il construisait un système à partir de rien. v2 modifie un système qui
marche : son épine dorsale est donc le **séquencement en lots** (A→H, chacun
avec sa porte de sortie et son coût). La feuille de route garde le *pourquoi*
et cite ses notes ; le prompt donne le *quoi* et l'*ordre*.

**Ce que le prompt porte au-delà de la feuille de route** :

- les trois **sémantiques de parité**, distinguées lot par lot — obligatoire
  et bit-exacte au lot A (code mort), hypothèse à retester au lot B (l'ordre
  du couple change l'ordre de sommation), conditionnelle au lot E ;
- les **conventions de rédaction en clair**, puisqu'un agent frais n'a pas
  accès à la mémoire : autonomie du document, variable définie à sa première
  apparition, méthode réimplémentable, chiffre sourcé, annexe de traçabilité
  par `run_id`, marquage `\fait{}`/`\inference{}`/`\incertitude{}` ;
- les **pièges de mesure**, en séparant ceux qui restent actifs de ceux qui
  deviennent dormants avec le retrait du cas partiel — sinon l'agent outille
  des bras qui n'existeront pas ;
- **quatre leçons d'analyse générales** : un garde-fou d'ajustement doit
  tester l'étendue et non le nombre de valeurs distinctes ; un ajustement
  groupé peut n'être que la droite des lignes de base ; un observable peut
  être ininformatif parce que deux effets se compensent ; une identité qui
  est une réécriture des définitions n'est pas une confirmation empirique ;
- la consigne d'**écrire la prédiction avant de lancer les runs**.

**Renvois** : par section, jamais par numéro de figure — les numéros ont
bougé aujourd'hui même. Le tableau des sections du rapport v1 a été vérifié
sur le PDF construit.

Conversion markdown → LaTeX par `prompts/md_to_tex.py` plutôt qu'à la main :
le PDF est le support de la boucle d'annotation, il sera donc révisé, et une
transcription manuelle diverge dès la première révision. Le markdown reste la
source unique.

### Deux rectifications de l'utilisateur sur le prompt v2 (21 août, soir)

**1. La purge des clefs mortes passe de décision ouverte à exigence.** «*Il
est essentiel de purger les clefs mortes. Le run est en λT² en ce moment.*»
Correct, et mon énoncé antérieur était trop faible : je disais « le coût croît
en λ×T », ce qui est le coût **par pas** en fin de run. Le nombre de clefs
croît en λ·t, donc le coût par pas est en λ·t et le coût **total** en
**λT²/2** — quadratique.

**Et j'ai vérifié la note v1 qui disait que purger ferait perdre la parité :
elle est fausse.** Trois raisons lues dans le code :

- le corps de boucle est un **no-op** sur un ensemble vide — le `continue`
  (`model.py:903-904`) précède la lecture de `book.due[borrower]`, donc
  aucune opération flottante n'a lieu ;
- supprimer une clef d'un `dict` CPython **ne réordonne pas** les restantes ;
- une entité morte est tuée (`_fail_one`, `model.py:608-617`) et **ne peut
  plus jamais emprunter**, donc sa clef ne sera pas réinsérée.

La note v1 n'est juste que pour un cas qu'elle ne distinguait pas : purger
les clefs vides des entités **vivantes** casserait bien la parité, parce
qu'un `defaultdict` réinsère la clef en **fin** d'ordre au prochain emprunt.
D'où la consigne exacte portée au prompt : **ne purger qu'à la mort**.

**2. Sept cœurs au lieu de six.** Consigne « droit à 7 cœurs ». Mémoire
`feedback_parallel_batch_jobs.md` mise à jour ; l'ancienne règle (8 cœurs,
en laisser 2 libres) est périmée. Les coûts mesurés jusqu'ici l'ont été à
6 processus — à rapporter à 7 en le disant.

Prompt reconstruit : 15 pages.
