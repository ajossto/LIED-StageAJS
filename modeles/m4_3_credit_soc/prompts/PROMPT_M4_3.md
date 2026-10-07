# Prompt de recherche M4.3 (nom provisoire) — l'anti-corrélation entre queue des revenus d'intérêt et criticité des avalanches est-elle structurelle, et quel mécanisme la brise ?

Successeur direct de M4.2B (`m4_2b_credit_soc/`), dont le prompt
(`prompts/PROMPT_M4_2B.md`) et le rapport final
(`report/rapport_final.md`) sont des lectures préalables obligatoires
— ce document ne répète pas ce qui y est déjà établi.

Version : 2026-08-06, remplace `PROMPT_M4_3.tex`/`.pdf` comme document
de travail (voir §11 — provenance et statut).

> **Point bloquant à trancher avant tout lancement de run, pas encore résolu par ce document** : le disque `/home` est à 93 % d'occupation (16 Gio libres, mesuré 2026-08-06). §3 et §7 imposent un checkpoint complet par run et un préflight qui refusera de démarrer si la marge est insuffisante — avec l'espace actuel, une seule cellule lourde (type K0 élevé) suffit probablement à consommer la marge restante. Ce n'est pas un problème que ce prompt peut résoudre seul : décider avec l'utilisateur (libérer de l'espace, monter un volume, ou réduire la rétention) avant la phase pilote.

## 0. Ce que M4.2B a établi, et pourquoi ce prompt existe

M4.2B a testé si la queue supérieure de la distribution des intérêts
perçus pouvait être de type Pareto, de façon contrôlable, sans détruire
la structure en loi de puissance des avalanches de faillites. Le
programme n'a tranché ni oui ni non sur l'existence de la queue (limite
de puissance statistique à l'échelle testée, pas une réfutation) mais a
établi trois faits solides, confirmés sur graines disjointes :

1. **Épaisseur de queue et criticité des avalanches s'anti-corrèlent
   dans tout ce qui a été exploré.** η aux deux extrêmes du sweep
   (ρ=0,125 et ρ=4) donne un α̂ *plus élevé* qu'à baseline (queue plus
   fine) alors que le rapport de branchement varie dans des sens
   opposés (0,478 vs 0,891) ; le sweep δ=σ conjoint donne la queue la
   plus épaisse de toute la campagne (α̂=3,05) exactement là où le
   rapport de branchement s'effondre (0,786→0,386). Aucune cellule des
   37 testées ne combine queue plus épaisse ET criticité préservée ou
   accrue.
2. **La cible de principal arithmétique est structurellement
   anti-multiplicative** : elle homogénéise le capital
   (Gini(K)≈0,05) et la dispersion du revenu d'intérêt est dominée à
   77 % par le nombre de contrats accumulés avec l'âge (`deg_out`, un
   compteur), 23 % seulement par la taille/taux des contrats. Aucune
   ablation de mécanisme n'a été tentée dans M4.2B (question 16 du
   prompt original) — c'est le plus gros degré de liberté resté
   inexploité.
3. **λ (naissances, `Config.lam`) contrôle déjà la taille de
   population indépendamment de K0** — vérifié directement dans
   `m4_2b/model.py`. La campagne de confirmation a fixé λ=30 partout
   et utilisé K0 comme proxy de taille, ce que le rapport lui-même
   signale comme confondu (Gini ×8, plancher de renouvellement 0→0,8,
   part `deg_out` jusqu'à 0,24 d'écart en même temps que K0 varie).
   C'est un défaut de plan de campagne, pas une limite du moteur.

Ce prompt ne redemande pas « existe-t-il une queue Pareto contrôlable ».
Il pose une question plus étroite et décidable : **l'anti-corrélation
observée entre l'épaisseur apparente de la queue des intérêts et la
criticité des avalanches est-elle une propriété structurelle de cette
classe de modèle (marché à pool k≡2, faillite cancel+destroy, service
d'intérêt perpétuel), ou existe-t-il un paramètre ou un mécanisme qui
la brise — qui déplace les deux quantités indépendamment, ou dans un
sens conjointement favorable ?**

## 1. Trois sous-questions, individuellement tranchables

- **D1 — cartographie.** Sur l'espace déjà couvert par M4.2B (η, γ,
  K0, δ, σ, `target_rule`) et sur ce que ce prompt ajoute (§4),
  l'anti-corrélation (α̂, b) tient-elle partout, ou existe-t-il des
  poches où elle s'inverse ou disparaît ?
- **D2 — contrôle indépendant.** Existe-t-il un paramètre ou un
  mécanisme qui déplace α̂ (ou la forme de la queue, voir §2) sans
  déplacer b/τ̂ dans le sens opposé — ou qui déplace les deux dans un
  sens conjointement favorable (queue plus épaisse, criticité égale ou
  supérieure) ?
- **D3 — robustesse.** Si une telle région existe (D2), résiste-t-elle
  au changement de graine, de fenêtre temporelle, et à la taille du
  système testée proprement (§5, via λ, pas via K0) ?

Un résultat négatif sur D2 (l'anti-corrélation est structurelle, aucun
levier trouvé ne la brise) est un résultat scientifique valide et
publiable — ce n'est pas un échec de ce programme. C'est même le
résultat le plus probable au vu de M4.2B ; ne pas s'obstiner à le nier.

## 2. Existence de la queue de Pareto : hypothèse de travail dès le départ, pas un critère bloquant

M4.2B a dépensé une part importante de son budget (trois révisions
successives d'un test d'existence, §4 de son rapport final) à essayer
de *prouver* que la queue est une vraie loi de puissance, avant de
finalement traiter l'existence comme hypothèse. **Ce prompt saute
directement à ce point de départ.**

- L'existence d'une loi de puissance pure sur la queue des intérêts
  n'est **pas** le critère de succès. Le critère est la réponse aux
  sous-questions D1–D3 sur le plan (paramètre de queue, criticité).
- Caractériser la queue avec la famille qui s'ajuste le mieux et de
  façon reproductible — loi de puissance pure, tronquée, avec coude —
  sans chercher à trancher laquelle est « la vraie » au-delà de ce que
  les données permettent. Si un exposant de loi de puissance tronquée
  (ou un paramètre de coude/coupure) caractérise mieux et plus
  stablement la réponse aux paramètres que α̂ seul, l'utiliser et le
  dire.
- Ne pas répéter le test d'auto-similarité à seuil ×2 de M4.2B tel
  quel (déjà démontré non calculable à cette échelle, §4 du rapport
  final) — si un test d'existence est utile quelque part dans ce
  programme, le motiver spécifiquement et vérifier d'abord qu'il est
  calculable avec le volume de données attendu (n_tail estimé avant de
  lancer, pas après coup).
- **La statistique de queue utilisée pour D1/D2/D3 (§1) doit être
  choisie et gelée pendant la phase pilote, avant le début de la
  cartographie D1** — pas ajustée en cours de campagne selon ce qui
  « a l'air le mieux ». Choix justifié sur la reproductibilité
  inter-graines (écart-type le plus faible à paramètres fixés), pas
  sur la valeur elle-même. Une fois gelée (α̂ pur, exposant tronqué, ou
  paramètre de coupure), le plan (§1) est défini sur cette statistique
  jusqu'à la fin du programme — changer de statistique en cours de
  route a coûté trois révisions de protocole à M4.2B (§4 de son
  rapport final), ne pas répéter.

## 3. Durée et taille de run : adaptatives, pas un budget fixé à l'avance

Pas de T ou de N cible fixé dans ce prompt. Chaque configuration doit
tourner jusqu'à ce que son propre temps caractéristique soit mesuré et
la fenêtre d'analyse positionnée en conséquence — en généralisant dès
le départ ce que M4.2B a dû faire en rattrapage (régression FOPDT sur
le renouvellement du décile supérieur,
`scripts/renewal_relaxation_all_runs.py`) :

- Étendre l'estimation du temps de relaxation à la variable d'intérêt
  central (queue des intérêts, pas seulement le renouvellement du
  décile supérieur utilisé comme proxy en M4.2B — vérifier si son
  temps d'autocorrélation propre diffère, cf. limite notée au §8 du
  rapport final de M4.2B).
- **Checkpointing obligatoire dès le premier run** (pas de rattrapage
  possible sans lui, leçon déjà actée en mémoire de session après
  M4.2B) : sauvegarder l'état complet picklable de `Simulation` à
  intervalle régulier et en fin de run, pour permettre l'extension
  d'un run existant plutôt que sa relance complète si son temps de
  relaxation s'avère plus long que prévu.
- **Rétention d'un seul checkpoint par run** : ne conserver que le
  dernier checkpoint complet (écraser le précédent à chaque nouvelle
  sauvegarde), jamais un historique — voir §7 pour le rationale
  disque, mesuré et chiffré, pas seulement une précaution abstraite.
- **Préflight disque avant chaque lancement de run, budgété sur la
  cellule entière, pas sur le seul run qui démarre** : estimer le
  volume attendu d'un run (poids observé en M4.2B, K0=2000 ≈ 600 Mo
  hors checkpoint, à majorer pour le checkpoint complet ajouté ici),
  multiplier par le nombre de runs **restants** dans la cellule en
  cours (les graines non encore lancées, typiquement 5 en confirmation),
  et refuser de démarrer si l'espace libre ne couvre pas au moins 3×
  cette estimation totale — voir §7. Un préflight qui ne regarde que le
  run sur le point de démarrer passe cinq fois de suite avant que le
  disque ne se remplisse au milieu de la cellule.
- Une cellule dont le temps de relaxation ne peut pas être atteint dans
  un budget de calcul raisonnable est documentée comme telle (sévère,
  non stationnaire confirmée) plutôt que forcée à un T arbitraire —
  convention déjà en place en M4.2B, à garder.
- Profiler le coût réel (s/pas, en fonction de λ au minimum) avant tout
  engagement de campagne à plusieurs cellules — pas après.

## 4. Où chercher un levier (D2) : ce qui est déjà disponible sans nouveau code

Pas de liste de mécanismes pré-autorisée ni interdite — la liberté de
diagnostic de M4.2B (§17 de son prompt) est reconduite. Trois
précisions cependant :

- **Le contrôle géométrique (`target_rule="geometric"`) est déjà
  implémenté, testé et parité-vérifiée avec M4.2 — c'est un point de
  départ à coût quasi nul pour tester si le canal multiplicatif (que
  la cible arithmétique supprime, §0.2) fait une différence sur le
  plan (α̂, b), avant d'écrire une seule ligne de mécanisme nouveau. Ce
  doit être le tout premier run de la phase pilote.** Le rapport
  M4.2B donne déjà un indice (α̂=3,318 en géométrique contre 3,890 en
  arithmétique à baseline autrement identique, mais cellule sévère, un
  seul instantané) — à re-mesurer proprement avec la méthode de
  fenêtrage adaptative (§3) avant d'en tirer une conclusion.
- **Note issue d'une relecture manuscrite du brouillon (annotation
  conservée verbatim)** : « Que ce soit la moyenne géométrique ou
  arithmétique, on peut aussi imaginer des moyennes harmoniques etc...
  Il existe une continuité de moyen de determiner le taux du prêt.
  Peut être que ça n'a pas beaucoup d'importance. » Vérifié dans le
  code avant d'agir sur cette note (`m4_2b/model.py:275-291`) :
  `target_rule` n'est **pas** un exposant continu, c'est un branchement
  discret entre deux formules structurellement différentes —
  « arithmetic » cible directement K_target=(Kℓ+Kb)/2, « geometric »
  cible K*(r)=(Aγ/r)^(1/(1−γ))=√(KℓKb), une cible dérivée du taux de
  rendement marginal, pas une moyenne de puissance appliquée aux deux
  capitaux. Une famille de moyennes de puissance (harmonique,
  géométrique, arithmétique, quadratique…) pour la règle de taux est
  donc **du code de mécanisme nouveau à écrire**, pas un paramètre
  supplémentaire à balayer à coût nul. **Ce n'est pas un mandat de
  campagne** : n'envisager cette famille que si le run géométrique du
  point précédent montre une différence réelle sur (α̂, b), et alors la
  traiter comme une extension de mécanisme soumise à la même règle de
  décision d'ablation que le point suivant — pas comme un balayage de
  paramètre bon marché.
- **La décision d'ablation ne doit pas disparaître par défaut de
  temps.** M4.2B avait explicitement autorisé une refonte de mécanisme
  « en second recours » (§17 de son prompt) et n'en a tenté aucune —
  pas par choix motivé, mais parce que le temps a manqué. Ce prompt
  impose donc une règle de processus, pas une liste de mécanismes : **à
  un jalon fixé à l'avance (par exemple, la fin de la cartographie D1),
  une décision explicite et écrite doit être prise — ablation
  nécessaire ou non, avec la justification — avant de passer à la
  suite.** Si la réponse est « non nécessaire », elle doit être aussi
  défendable et documentée qu'un « oui ». Cette décision fait partie
  des jalons qui attendent la supervision quotidienne — voir §9, elle
  n'est pas prise seul.

## 5. Objectif B rigoureux : réutiliser la méthodologie déjà validée sur M4B, avec une réserve vérifiée

M4.2B n'a jamais testé l'indépendance de taille de l'exposant
d'avalanche correctement (λ=30 fixe, K0 confondu comme proxy de
taille, §8 de son rapport final). `recherche/sensibilite_m4b/`
(campagne M4B, 594 runs, outils `lib_metrics.py`/`lib_screening.py`
déjà copiés sans changement dans `m4_2b_credit_soc/scripts/`) a résolu
cette question **pour k=3** (`rapport_final.tex` §« Avalanches : loi
tronquée… » et table `tab:lois`, vérifié directement dans le source
LaTeX, pas de mémoire) :

- loi de puissance **tronquée** partout (LRT p<10⁻⁶, pas de loi pure) ;
- coupure ŝc ∝ λ^1,5 (mesuré λ=10→30 : 10,0→51,6 ; à λ=100 la coupure
  sort de la fenêtre observable, Vuong tronquée-vs-pure bascule
  franchement en faveur de la pure, z=+21,0±0,9, 5/5 graines) ;
- exposant tronqué monotone avec λ (1,584 / 2,041 / 2,313), extrapolant
  à α∞≈2,31–2,32 — la non-monotonie du fit en loi *pure* est un
  artefact de coupure ;
- λ confirmé comme **pure taille finie** (intensivité ±2 % sur les
  observables normalisés).

**Réserve importante, à ne pas ignorer** : cette échelle en λ n'a été
mesurée qu'à k=3. Le même rapport signale explicitement, dans sa
section « non observé/non confirmé », que **la coupure ŝc à k=2 (le
`pool_size` de M4.2B) n'est pas confirmée en amplitude** (contraste
exploratoire −3,2 vs confirmé +6,0±2,8, métrique la plus bruitée du
programme, variance inter-graines 17 %) et recommande explicitement de
ne piloter aucune conclusion sur la coupure ajustée seule — de
préférer b et α̂ (déclaré avec la taille de système) et la
susceptibilité, plus stables. Le lien entre M4B (k=3) et M4.2B/ce
prompt (k≡2) est donc une **hypothèse à vérifier**, pas un fait
transférable tel quel : la pente λ^1,5 peut différer à k=2, même si le
mécanisme d'avalanche est hérité sans changement.

**Confirmé (relecture manuscrite du brouillon) : k≡2 est gardé fixe,
hérité de M4.2B sans changement. Pas de balayage sur `pool_size` dans
ce programme** — la réserve ci-dessus reste une hypothèse à vérifier
*à k=2 fixé*, pas une invitation à comparer k=2 et k=3 dans ce prompt.

**Ce que ce prompt exige concrètement** :

- Réutiliser la méthodologie (loi tronquée par MLE, Vuong
  tronquée-vs-pure, échelle de λ incluant au moins {10, 30, 100} et un
  point au-delà si le budget le permet) — pas les nombres de M4B.
- **Ré-établir ŝc(λ) sur le moteur M4.2B (k≡2)** avant de supposer une
  pente ; si elle diverge de 1,5, le documenter, ne pas forcer
  l'accord.
- Suivre la recommandation de M4B sur les observables de pilotage :
  **b (rapport de branchement) et l'exposant tronqué α̂ déclaré avec sa
  taille de système sont les métriques primaires** du plan D1/D2/D3
  côté avalanches ; la coupure ajustée reste une analyse
  secondaire/de confirmation, jamais le critère qui tranche à elle
  seule.
- Toujours à paramètres par ailleurs identiques, jamais en faisant
  varier K0 comme proxy de taille.

C'est un gain d'ingénierie direct (l'outillage existe déjà) et
méthodologique (fini les τ̂ indépendants par taille qui avaient produit
une dérive non interprétable dans le pilote M4.2B) — sans hériter une
conclusion numérique qui n'a pas encore été vérifiée dans ce régime.

## 6. Discipline scientifique (reconduite de M4.2B, sans changement)

- Distinguer explicitement fait observé / inférence / hypothèse /
  incertitude à chaque affirmation quantitative.
- Ne jamais sélectionner après coup graines, snapshots ou seuils
  donnant le résultat attendu.
- Protocole figé après la phase pilote ; résultats négatifs conservés
  et rapportés comme tels (D1/D2 négatifs inclus, §1).
- Unité de réplication = snapshot pour la queue, run pour la moyenne de
  cellule, cellule pour l'effet de paramètre — ne jamais fusionner ces
  échelles (leçon déjà actée : écart-type intra-instantané ≈3,7× l'écart-type
  inter-graines dans M4.2B, ne pas répéter la confusion).

## 7. Sécurité de calcul : garde-fous obligatoires (impératif)

**Contexte du programme, tel qu'exprimé par l'utilisateur (2026-08-06,
verbatim)** : « c'est un travail long, itératif, et autonome […] trois
jours humains de calculs devant [Claude]. Je superviserai une fois par
jour. […] K2000 faisait planter le PC. Il faut mettre des gardes fous
IMPERATIVEMENT (un crash du PC serait catastrophique). » Sur un travail
de plusieurs jours sans supervision continue, un garde-fou qui n'est
qu'une convention documentée (JOURNAL.md, mémoire de session) n'est
**pas** suffisant — il doit être appliqué par le code lui-même, pas
seulement respecté par discipline. Les quatre points ci-dessous
comblent des lacunes concrètes, identifiées sur incidents réels de
M4.2B (`m4_2b_credit_soc/JOURNAL.md` §10, §12, §15), pas des précautions
génériques.

1. **Coupe-circuit sur la mémoire système, pas seulement par worker.**
   M4.2B a mis en place un plafond `resource.RLIMIT_AS` par worker
   (§10 du journal), mais les deuxième et troisième arrêts machine
   documentés (§9–§10) n'ont laissé **aucune** trace d'OOM-kill et
   l'uptime est restée continue — cohérent avec un thrashing swap
   plutôt qu'un OOM-kill propre. Un plafond par processus ne voit pas
   ce phénomène : avec 28 Gio de swap disponibles sur cette machine
   (mesuré 2026-08-06), un worker peut rester sous son propre plafond
   tout en faisant swapper le système entier jusqu'au gel. **Exiger**
   un observateur indépendant du pool (sur le modèle de
   `scripts/mem_watch.py` de M4.2B) qui surveille en continu
   `MemAvailable` (`/proc/meminfo`) et le taux de swap-in/out
   (`/proc/vmstat`, `pswpin`/`pswpout`), et qui a l'**autorité** de
   bloquer le lancement de nouveaux runs et, en dernier recours, de
   terminer proprement les workers en cours si `MemAvailable` descend
   sous un seuil fixe ou si le swap-in dépasse un débit soutenu sur
   plusieurs lectures consécutives — pas seulement logguer pour
   analyse a posteriori.
2. **Plafond par worker calculé sur la mémoire disponible au
   lancement, pas sur la RAM totale de la machine.** La formule M4.2B
   (75 % de RAM totale ÷ n_workers) réserve ≈23,3 Gio au total pour le
   pool (≈3,9 Gio/worker à 6 workers) sur cette machine à 31 Gio.
   Mesuré le 2026-08-06 (`free -h`) : `MemAvailable` ≈26 Gio (24 Gio de
   cache/tampon réclamable, 5,1 Gio réellement utilisés hors cache) —
   la réservation du pool (≈23,3 Gio) ne laisse donc qu'une marge
   résiduelle d'≈3 Gio pour le système et la phase d'analyse qui suit
   chaque run. Marge insuffisante pour un travail de plusieurs jours
   pendant lequel d'autres usages de la machine ne sont pas exclus.
   Calculer le plafond sur `MemAvailable` au moment du lancement, moins
   une réserve fixe pour le système (à définir, ordre de grandeur
   4 Gio), divisée par `n_workers`.
3. **Verrou mono-pool appliqué par le code, pas par convention.**
   JOURNAL §15 documente la cause racine d'un crash direct : deux
   pools de simulation indépendants lancés en même temps, chacun
   calculant son propre plafond sans connaissance de l'autre,
   réservation combinée jusqu'à ≈50 Gio sur une machine à 31 Gio. La
   décision prise à l'époque (« ne plus jamais lancer deux pools en
   même temps ») est une règle humaine, non appliquée par un
   mécanisme. Sur un travail autonome de plusieurs jours, avec
   compaction de contexte possible entre sessions de travail, cette
   règle sera oubliée tôt ou tard. **Exiger** un verrou exclusif
   (fichier pid + `flock`, ou équivalent stdlib) acquis au démarrage de
   tout pool de simulation, qui fait échouer bruyamment (pas
   silencieusement) une seconde tentative de lancement tant que le
   premier verrou est tenu.
4. **Préflight disque, chiffré, pas seulement mentionné, et budgété sur
   la cellule entière.** Fait observé le 2026-08-06 : `/home` est à
   93 % d'occupation, 16 Gio libres (`df -h`). Un run K0=2000 pesait
   déjà ≈600 Mo sur disque en M4.2B (avant l'ajout du checkpoint
   complet exigé par §3) ; un checkpoint complet d'une cellule lourde
   peut plausiblement ajouter 1 à 2 Gio de plus. Une écriture de
   checkpoint ou de `np.savez_compressed` interrompue par un disque
   plein est une **corruption**, pas un échec propre — aucun des
   garde-fous mémoire ci-dessus ne protège contre ce cas. Avant de
   lancer un run, vérifier l'espace disque libre contre une estimation
   du volume attendu pour **tous les runs restants de la cellule en
   cours**, pas pour le seul run qui démarre (marge ×3 minimum, §3), et
   refuser de démarrer si insuffisant — un préflight par run isolé
   passerait plusieurs fois de suite avant que le disque ne se remplisse
   au milieu d'une cellule à 5 graines. Ne garder qu'un seul checkpoint
   par run (§3) pour limiter l'empreinte cumulée d'une campagne de
   plusieurs jours.

Ces quatre points sont des exigences pour le code de campagne à écrire
au démarrage du programme (`m4_3_credit_soc/` ne contient pour l'instant
que ce dossier `prompts/`, pas encore de moteur ni de scripts) — pas
une implémentation à livrer avec ce document. Aucun des quatre n'est
optionnel compte tenu du contexte d'autonomie de §9.

## 8. Parité et réutilisation d'outils

- Moteur : partir de `m4_2b/model.py` tel quel (l'institution
  arithmétique reste la référence sauf si D2/§4 justifie explicitement
  un changement, avec ablation propre et comparaison à la baseline
  arithmétique).
- Figures et snapshots : réutiliser sans modification l'adaptateur
  `simulation_lab` et le code de génération de figures hérité de
  M4.2/M4.2B (28 figures déjà validées) ; ajouter uniquement les
  figures propres au plan (α̂, b) et à la loi d'échelle ŝc(λ).
- Statistiques d'avalanches : réutiliser
  `lib_metrics.py`/`lib_screening.py` (§5) sans les récrire.

## 9. Cadence de travail autonome et supervision

Contrainte explicite de l'utilisateur : travail long, itératif,
autonome, budget de l'ordre de trois jours humains de calcul,
supervision une fois par jour. Ce rythme impose des règles de
processus propres à ce prompt, en plus de la discipline scientifique
(§6) et des garde-fous de calcul (§7) :

- **Un point d'étape quotidien, lisible en une session.** À chaque
  cycle de supervision : état d'avancement (runs terminés/en
  cours/en échec), tout incident de garde-fou déclenché (§7) et sa
  cause, résultats décisionnels disponibles depuis le dernier point,
  et la liste des décisions en attente de supervision (voir
  ci-dessous). Pas un journal brut à relire intégralement — un résumé
  qui permet une décision rapide.
- **Ordonnancer le travail pour que les résultats décisionnels
  arrivent avant chaque point d'étape, pas après.** Prioriser dans
  l'ordre : (a) le premier run géométrique de §4, (b) la cartographie
  D1 sur l'espace déjà couvert par M4.2B, (c) toute extension D1
  propre à ce prompt, dans cet ordre — pour qu'il y ait toujours un
  résultat interprétable à présenter au point du jour suivant plutôt
  qu'un calcul en cours sans lecture possible.
- **Règle explicite de ce qui peut être décidé seul et de ce qui
  attend la supervision.** Peuvent être décidés sans attendre : choix
  d'implémentation, correctifs de bug, paramétrage des garde-fous de
  §7, extension mineure d'un run existant via checkpoint (§3). Doivent
  attendre le point de supervision suivant, explicitement listés comme
  décision en attente : la décision d'ablation de mécanisme (§4,
  jalon de fin de cartographie D1), tout changement de la statistique
  de queue gelée (§2) une fois la phase pilote close, et toute décision
  qui engagerait un budget de calcul significatif sur une direction non
  couverte par ce prompt.
- Le point disque signalé en tête de ce document (93 % d'occupation) et
  toute question laissée ouverte dans ce prompt sont, par construction,
  des décisions en attente de supervision — ne pas les trancher seul en
  cours de route.

## 10. Livrables

- Le plan (α̂ ou paramètre de queue équivalent, b/τ̂) cartographié sur
  l'espace testé (D1), avec figure dédiée (un point par cellule,
  graines agrégées, barres d'erreur inter-graines).
- Verdict D2 explicite : levier trouvé ou non, avec le niveau de preuve
  exact (reproductibilité inter-graines, robustesse temporelle).
- Si D2 positif : verdict D3 (robustesse de taille, méthodologie §5).
- Décision d'ablation (§4) documentée par écrit, prise ou non prise,
  avec justification, à la date du jalon fixé — et validée au point de
  supervision correspondant (§9).
- Rapport autonome (contexte, grandeurs et méthode rappelés avant
  usage, comme le rapport final de M4.2B) + journal chronologique +
  points d'étape quotidiens (§9).

## 11. Provenance et statut de ce document

Ce fichier remplace `PROMPT_M4_3.tex`/`PROMPT_M4_3.pdf` comme document
de travail de référence — les deux sont conservés tels quels dans ce
dossier comme trace de la version annotée à la main (ne pas les
supprimer). Deux annotations manuscrites portées sur le PDF
(2026-08-06, 19h47–19h51) ont été relues et intégrées ci-dessus :

- Sur la page relative à la règle de taux (§4 de ce document) : « Que
  ce soit la moyenne géométrique ou arithémetique, on peut aussi
  imaginer des moyennes harmoniques etc... Il existe une continuité de
  moyen de determiner le taux du prêt. Peut être que ça n'a pas
  beaucoup d'importance. »
- Sur la page relative à la coupure d'avalanche à k=2 (§5 de ce
  document) : « On garde k=2. »

La question ouverte du brouillon précédent (« nom et emplacement de
dossier ») est close : `m4_3_credit_soc/` est confirmé, en suivant la
convention M4→M4B→M4.2→M4.2B→M4.3 déjà en place.
