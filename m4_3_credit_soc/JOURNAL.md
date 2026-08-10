# JOURNAL — M4.3

## 1. Démarrage (2026-08-06 soir) : lecture, vérification, garde-fous §7

Prompt de référence : `prompts/PROMPT_M4_3_FINAL.md`. Avant tout travail
substantiel, vérification indépendante (pas de confiance aveugle dans les
affirmations du prompt, règle de confiance à 95 % du CLAUDE.md racine) des
faits cités comme déjà vérifiés :

- **`m4_2b/model.py:269-291` (`_pair_principal`)** — confirmé lu
  directement : `target_rule` est bien un branchement discret
  (`if target_rule == "arithmetic": return 0.5 * (lender_capital -
  borrower_capital)` vs. cible géométrique `K*(r)=(Aγ/r)^(1/(1−γ))`), pas un
  exposant continu. La note manuscrite sur une famille de moyennes de
  puissance (§4 du prompt) exigerait donc bien du code de mécanisme
  nouveau, pas un paramètre de balayage à coût nul — confirmé.
- **`JOURNAL.md` de M4.2B, §9** (deuxième arrêt, 04/08) — confirmé : uptime
  continue, aucun boot supplémentaire (`journalctl --list-boots`), aucune
  trace d'OOM-kill (accès `sudo` aux logs kernel indisponible dans cette
  session).
- **§10** (troisième arrêt, 04/08 14h12) — confirmé : même lecture (uptime
  continue, pas de trace d'OOM-kill), corrigé à l'époque par streaming de
  `loan_events` + plafond `RLIMIT_AS` par worker + `mem_watch.py`
  (journalisation seule, sans autorité de blocage).
- **§12** (K0_2000, quatre causes) — confirmé : `_write_final_loans`,
  `deaths`/`avalanches` non streamés, `load_all_network_snapshots`
  matérialisant toute la fenêtre, puis `sim` gardé vivant pendant l'analyse
  — quatre corrections indépendantes, la dernière déterminante.
- **§15** (05/08, deux pools concurrents) — confirmé : plafond mémoire
  calculé indépendamment par deux pools simultanés (8 workers × 3,15 Go +
  3 workers × 8,41 Go), réservation combinée jusqu'à ~50 Go sur une machine
  à 31 Go ; aggravé par l'absence de `try/except` autour de la phase
  simulation dans `_run_and_analyze` (une seule `MemoryError` a tué tout le
  pool). Décision de l'époque : règle humaine ("ne plus jamais deux pools
  en même temps"), non appliquée par le code — exactement le défaut que
  §7 point 3 de ce prompt corrige.

Toutes les citations du prompt M4.3 vérifiées comme exactes. Aucune
divergence trouvée.

**`results/` de M4.2B n'est PAS suivi par git** (`git ls-files
m4_2b_credit_soc/results | wc -l` → 0) — pas de complication git pour le
nettoyage du point 6.

## 2. Interprétation de la consigne « attends une heure avant de considérer
le prochain prompt » (commande `/remote-control`)

Aucune définition de `/remote-control` trouvée dans le dépôt ni dans la
configuration Claude Code locale. Plutôt que de deviner sa mécanique et de
poser un `ScheduleWakeup` sur une sémantique non confirmée (outil prévu pour
`/loop`, non invoqué ici), lecture retenue : l'utilisateur est absent de la
machine, l'instruction signifie **ne pas lancer de calcul lourd immédiatement
depuis un prompt collé en cours de tour, sans supervision** — pas rester
inactif. Le prompt M4.3 lui-même impose de toute façon un blocage plus solide
que l'heure : `m4_3_credit_soc/` ne contenait que `prompts/` au démarrage,
aucun des six garde-fous §7 n'existait, donc aucun lancement n'était de toute
façon possible avant qu'ils soient écrits. §9 autorise explicitement, sans
attendre de supervision : « choix d'implémentation, correctifs de bug,
**paramétrage des garde-fous de §7** ». C'est le travail de cette session.

## 3. Garde-fous §7 implémentés et testés (2026-08-06 soir)

`scripts/safety/` :

- **`disk_preflight.py`** — `check_disk_preflight(remaining_runs,
  per_run_bytes, path, margin=3.0)` : lit `shutil.disk_usage` à chaque appel
  (aucun seuil codé en dur), exige `remaining_runs` (graines restantes de la
  cellule ENTIÈRE, pas le seul run qui démarre, §3/§7.4).
- **`mem_cap.py`** — plafond par worker calculé sur `MemAvailable` lu au
  moment de l'appel (pas la RAM totale), moins une réserve fixe (4 Gio par
  défaut), divisé par `n_workers` ; lève une erreur si le plafond résultant
  tombe sous un plancher (512 Mo) plutôt que de lancer un pool avec un
  budget dérisoire (§7.2).
- **`pool_lock.py`** — verrou `flock` exclusif non-bloquant sur un chemin
  fixe (`results/.pool.lock`, PAS dérivé de `sys.argv[0]`) : protège contre
  un second pool lancé par n'importe quel processus touchant ce dossier ;
  libéré automatiquement par le noyau si le titulaire meurt sans releaser
  (§7.3).
- **`checkpoint.py`** — écriture dans un fichier temporaire sur le MÊME
  répertoire puis `os.replace` (rename atomique) ; un échec de pickling ou
  une interruption ne laisse ni fichier temporaire ni checkpoint tronqué
  sous le nom final (§3, §7.4).
- **`halt.py` / `worker_registry.py`** — sentinelle de blocage
  (`results/HALT`) et registre des PID du pool courant, partagés entre le
  lanceur de pool (pas encore écrit) et le garde-fou mémoire.
- **`scripts/mem_guard.py`** — observateur INDÉPENDANT (process séparé, à
  lancer dans sa propre session tmux comme `mem_watch.py` en M4.2B) :
  surveille `MemAvailable` (`/proc/meminfo`) et le débit `pswpin`/`pswpout`
  (`/proc/vmstat`) toutes les 15 s. Contrairement à `mem_watch.py` de
  M4.2B (log seul — les arrêts §9/§10 n'ont laissé aucune trace d'OOM-kill,
  cohérent avec un thrashing swap qu'un plafond par worker ne voit pas), ce
  script a l'AUTORITÉ de poser `results/HALT` et de terminer
  (SIGTERM puis SIGKILL après 10 s de grâce) les PID enregistrés si le
  dépassement persiste sur 3 lectures consécutives (~45 s). Ne lève PAS le
  halt automatiquement à la résorption — reprise laissée au superviseur
  humain (§9 : ce qui engage un budget de calcul attend la supervision).

**Tests** (`tests/test_safety.py`, 8 tests, assertions simples comme le
reste du dépôt) : préflight refuse/passe selon le volume, croît linéairement
avec `remaining_runs`, plafond mémoire utilise bien la valeur injectée (pas
la RAM totale) et refuse sous le plancher, verrou bloque un second acquire
et se relibère correctement, checkpoint écrase proprement sans laisser de
fichier temporaire même en cas d'échec de pickling. **8/8 verts.**

Encore À FAIRE (pas fait cette session) : brancher ces modules dans un
lanceur de pool réel (équivalent `campaign.py`) — aucun run n'a encore été
lancé.

## 4. Arithmétique du préflight sur l'état réel du disque (2026-08-06 soir)

Mesuré : `/home` à 29-30 Gio libres (`df -h`, fluctuant légèrement avec
l'activité du système). Estimation par run : 600 Mo (poids observé K0=2000
en M4.2B, JOURNAL §10) + 2 Go de checkpoint complet majoré = 2,6 Go/run.

```
check_disk_preflight(remaining_runs=1, per_run_bytes=2.6e9) -> OK
  (7,8 Go requis, 30,3 Go libres)
check_disk_preflight(remaining_runs=5, per_run_bytes=2.6e9) -> REFUS
  (39,0 Go requis, 30,3 Go libres)
```

**Conclusion opérationnelle** : le premier run pilote (géométrique, §4)
reste lançable aujourd'hui sans nettoyage préalable. Une cellule de
confirmation à 5 graines ne l'est PAS avant que l'espace du point 6
(nettoyage M4.2B) soit effectivement libéré — le préflight refusera
correctement de la démarrer en l'état, comme prévu par construction. Le
prompt distingue explicitement "phase pilote" et "campagne" (§2, §3, §4) ;
cette contrainte est cohérente avec cette distinction, pas un obstacle
imprévu.

## 5. Nettoyage M4.2B — dry-run exécuté, AUCUNE suppression (2026-08-06 soir)

`scripts/cleanup_m4_2b_raw_logs.py` (dry-run uniquement) : portée limitée à
`results/{campaign,confirmation}/` (~75 Go sur ~76 Go mesurés — les
dossiers `pilot_*`, ~2 Go combinés, structurellement moins réguliers, sont
exclus de cette passe automatisée par choix conservateur, pas par oubli).

Pour chaque run : suppression proposée seulement si (label, seed) apparaît
dans le fichier agrégé de sa collection (`campaign/exploration_summary.csv`
ou `confirmation/confirmation_runs.csv`) ET `config.json` + (`analysis.json`
ou `summary.json`) présents. Liste blanche stricte des fichiers supprimables
(`loan_events.csv.gz`, `deaths.csv`, `final_loans.csv`, `entities.csv`,
`avalanche_members.csv`, `snapshots/*.npz`) — rien d'autre.

**Résultat** : 132/132 runs éligibles (87 campaign + 45 confirmation, 0
ignoré), **78,94 Go libérables**. Manifeste complet écrit dans
`m4_2b_credit_soc/results/CLEANUP_MANIFEST.md` (chemins, tailles, date).

**Exécuté le 2026-08-07**, après feu vert explicite de l'utilisateur
("sois autonome") au point d'étape ci-dessus, dry-run + manifeste déjà
montrés : `scripts/cleanup_m4_2b_raw_logs.py --execute` — recalcule un scan
FRAIS (pas le manifeste déjà écrit, pour éviter tout TOCTOU), chaque
suppression passe une assertion de défense en profondeur indépendante
(`_assert_safe_to_delete` : chemin sous `results/{campaign,confirmation}/`,
jamais sous `report/`, nom sur liste blanche stricte). **32 346 fichiers
supprimés, 78,94 Go libérés, 0 erreur.**

**Vérifié après coup** (pas supposé) :
- `report/` de M4.2B : 25 fichiers figures (`*.png/*.pdf/*.svg/*.jpg`),
  liste de chemins identique avant/après (hash MD5 de la liste), **aucune
  figure touchée**.
- Les 7 fichiers agrégés à la racine de `results/` (`*.csv`, `*.json`)
  toujours présents et intacts.
- `df -h /home` : **87 % → 51 %** d'occupation (179 Go → 105 Go utilisés,
  28 Go → 102 Go libres) — exactement la baisse annoncée par l'autorisation
  du prompt (§7.6).

## 6. Point d'étape (2026-08-06 soir → 2026-08-07)

**Fait** : vérification des faits cités par le prompt (§1, tous confirmés) ;
six garde-fous §7 écrits et testés (§3) ; arithmétique de préflight vérifiée
(§4) ; nettoyage M4.2B — dry-run PUIS exécution réelle, 78,94 Go libérés,
figures et fichiers agrégés vérifiés intacts après coup (§5). Aucun run de
simulation M4.3 lancé.

**Pas encore fait** : port du moteur `m4_2b/model.py` (inchangé, §8) dans
`m4_3_credit_soc/m4_3/` ; lanceur de pool (`campaign.py` équivalent)
branchant les six garde-fous ; premier run pilote géométrique (§4) ; mesure
du temps de relaxation sur la queue des intérêts (§3) ; choix et gel de la
statistique de queue (§2).

**2026-08-07 : consigne explicite de l'utilisateur — « sois autonome, ne
détruit aucun graphique »**, en réponse au point d'étape ci-dessus. Lue
comme : (a) feu vert pour exécuter le nettoyage déjà présenté au checkpoint
(fait, §5) et pour avancer sur les tâches déjà prescrites par le prompt
sans marquer une pause à chaque étape ; (b) contrainte dure, au-delà de la
protection déjà en place sur `report/` (§7.6) — ne jamais supprimer ou
écraser un fichier figure (`*.png`/`*.pdf`/`*.svg`/`*.jpg`) nulle part dans
le dépôt, y compris les figures que ce programme générera lui-même.
Décisions #1 et #2 ci-dessous sont closes par cette instruction ; seule #3
reste en attente (jalon non atteint).

**Décisions en attente de supervision (§9)** :
1. ~~Exécution réelle du nettoyage M4.2B~~ — close, exécutée 2026-08-07.
2. ~~Portée du nettoyage limitée à `campaign/`+`confirmation/`~~ — close,
   confirmée implicitement (pas d'objection, instruction d'autonomie).
3. Décision d'ablation de mécanisme (§4) — jalon non atteint (fin de
   cartographie D1), pas encore pertinente.

## 7. Deux corrections avant tout lancement réel (2026-08-06 soir, relecture)

- **`mem_guard.py`** : le chemin `HALT` re-déclenchait
  `_terminate_registered_workers()` à CHAQUE itération tant que
  `consecutive_breaches >= 3`, y compris sur des PID déjà tués — et le
  `sleep(GRACE_PERIOD_S)` de cette fonction gelait l'échantillonnage
  mémoire du garde-fou pendant 10 s à chaque tour. Corrigé : un verrou
  `workers_killed_this_episode` limite la terminaison à une fois par
  épisode de halt, réarmé seulement quand `results/HALT` est effacé (par un
  humain).
- **`worker_registry.register_workers`** : `path.with_suffix(".tmp")`
  remplace l'extension au lieu de l'ajouter (fonctionnait par coïncidence
  sur `.pool_workers.json` mais cassait le patron d'écriture atomique
  voulu). Corrigé pour suivre le même patron que `checkpoint.py`
  (`path.parent / (path.name + ".tmp")`).

8/8 tests toujours verts après les deux correctifs. Manifeste de nettoyage
régénéré avec une note de réconciliation GiB/GB expliquant l'écart apparent
entre 78,94 Go (ce script, `campaign/`+`confirmation/` seuls) et les
« ≈76 Go » de l'autorisation (`du -h`, portée légèrement différente).

## 8. Port du moteur, profilage, premier run pilote (2026-08-07)

**Port `m4_2b/model.py`+`io.py` → `m4_3/`** : copie octet pour octet
(`diff` vide) ; seul `__init__.py` a un docstring propre au nouveau
programme (aucune ligne de mécanique). Parité runtime testée
(`tests/test_parity_m4_2b.py`) : égalité EXACTE (pas de tolérance, même
code source) entre `m4_2b.Simulation` et `m4_3.Simulation`, mêmes
paramètres/graines, sur `target_rule ∈ {arithmetic, geometric}` × graines
{0,1,7} × T=200 — **6/6 passent**.

**Profilage de coût (§3, avant tout engagement)** — `scripts/profile_cost.py`,
300 pas, baseline (γ=0,5, δ=0,01, σ=0,01, K0=25) :

| λ | s/pas mesuré | pop @300 | n_loans @300 |
|---|---|---|---|
| 10 | 0,034 | 399 | 12 967 |
| 30 | 0,112 | 1195 | 38 646 |
| 100 | 0,444 | 3838 | 136 331 |

**Fait observé, pas anticipé par ce prompt ni par M4.2B tel que relu** : à
paramètres baseline (λ=30), le carnet de prêts actifs dépasse largement son
niveau ultérieur pendant la montée en charge — pic à ~96 000 prêts vers
t≈100 (population ~2400), puis CONTRACTE (41 800 prêts, population ~1075 à
t=180). Le coût par pas suit ce même profil (pic ~0,20 s/pas vers t=100,
descend à ~0,11 s/pas vers t=180) — mesuré directement, pas supposé. Consé-
quence pour l'extrapolation de coût : une fenêtre de profilage courte
(comme les 300 pas ci-dessus) surestime probablement le coût d'un run long
plutôt que de le sous-estimer, puisqu'elle capture le transitoire le plus
cher. Extrapolation linéaire (donc probablement pessimiste) : λ=30, T=3000
→ ~5,6 min ; λ=100, T=3000 → ~22 min.

**Premier run de la phase pilote (§4 : contrôle géométrique) lancé** —
`scripts/run_pilot.py --label control_geometric --seed 0 --steps 3000
--target-rule geometric`, baseline sinon identique. Câblé avec les six
garde-fous : préflight disque passé (7,8 Go requis pour ce run seul, 102 Go
libres après le nettoyage §7), verrou mono-pool acquis, PID enregistré
auprès du garde-fou mémoire, plafond RLIMIT_AS=26,9 Go (calculé sur
`MemAvailable` réel), checkpoint atomique tous les 200 pas. **Deux sessions
tmux détachées, indépendantes de ce process Claude** (convention M4.2B,
JOURNAL.md §9) :
- `m43_memguard` : `scripts/mem_guard.py`, log `results/mem_guard.csv`.
- `m43_pilot` : le run lui-même.

Le smoke test préalable (T=30 puis T=10, deux lancements successifs,
labels `smoke_test`/`smoke_test2`, supprimés après vérification) a confirmé
le cycle complet (préflight → verrou → registre → plafond → run → check-
point final → libération du verrou → registre nettoyé) avant le lancement
réel.

**Run terminé** : t=3000/3000, elapsed=1036,1 s (~17,3 min), status=ok,
0 dépassement mémoire sur toute la durée (`mem_guard.csv`, 0 ligne avec
`n_breaches_consecutive>0`), `book_errors=[]`. Poids sur disque mesuré :
941 Mo (dont individual_series.csv.gz 450 Mo — voir §9).

**Recoupement indépendant, gratuit** : `population_final=1624` (mon run
frais) == `population_final=1624` dans `campaign/exploration_summary.csv`
de M4.2B pour `control_geometric seed=0` (ligne écrite AVANT le port de ce
programme). Confirmation croisée du port + déterminisme RNG, pas juste le
`diff` de code déjà vérifié.

## 9. Temps de relaxation étendu à l'intérêt pur — écart notable trouvé, run refait (2026-08-07)

Copié tel quel dans `scripts/` (§5/§8, aucune modification) :
`lib_metrics.py`, `lib_screening.py`, `interest_income.py`, `renewal.py`,
`renewal_relaxation_all_runs.py`, et leurs dépendances transitives
(`families.py`, `pareto_convention.py`, `tail_test.py` — `families.py` lit
`anciens_modeles/modele-27-04-WIP/src/analysis.py` par un chemin relatif à
sa propre profondeur dans le dépôt, fonctionne à l'identique depuis
`m4_3_credit_soc/scripts/`, vérifié).

**`scripts/relaxation_pilot.py` (nouveau)** : étend la régression FOPDT de
persistance du décile supérieur (déjà validée en M4.2B) au champ `int_in`
(intérêt PUR reçu, `pop.int_in` — la variable centrale de tout ce
programme), à côté des trois champs déjà utilisés par M4.2B (`nw`, `K`,
`income`=production+intérêt, PAS l'intérêt seul). C'est exactement l'écart
que le §3 du prompt demande de vérifier.

**Résultat sur `control_geometric seed0` (premier run, T=3000)** :

| champ | tau | t_delay | t_converge (t0+t_delay+3·tau) |
|---|---|---|---|
| nw | 996,6 | 591,1 | 3606,0 |
| K | 35,6 | 0,0 | 131,9 |
| income | 1038,5 | 544,2 | 3684,7 |
| **int_in** | **1146,1** | **447,6** | **3910,8** |

**tau(int_in)=1146 vs tau moyen(nw,K,income)=690 → ratio=1,66 (>50%,
écart notable).** `t_converge(int_in)=3910,8 > T=3000` : le run à T=3000
(convention M4.2B, jamais validée pour `int_in` spécifiquement, §3 du
prompt le signale explicitement comme un angle mort) n'a probablement PAS
atteint la stationnarité pour la variable d'intérêt centrale du programme,
même si `nw`/`income` semblaient proches de la convergence.

**Décision (§9 : implémentation/correctif, décidable seule)** : refaire ce
run à T=8000 (marge ≈2× sur `t_converge(int_in)`) PLUTÔT QUE d'implémenter
une reprise depuis checkpoint sous pression de temps. Le mécanisme de
checkpoint (§7.4) fonctionne (sauvegarde atomique testée, exercée en
conditions réelles sur le run T=3000) mais n'a PAS encore de consommateur
de reprise (`RunRecorder` de `m4_3/io.py` ouvre toujours ses flux en mode
écriture, jamais en mode ajout — écrire ce consommateur correctement
[réamorcer les compteurs `avalanche_id`/`loan_events_total`/etc. depuis
l'état du checkpoint, rouvrir les flux gzip/csv en ajout SANS dupliquer
l'en-tête] est un travail non trivial que je préfère ne pas improviser
pour économiser 17 minutes de calcul sur un run qui coûte de toute façon
peu). À construire avant qu'un run coûte des heures, pas maintenant.

**Optimisation disque appliquée en même temps** : `individual_series.csv.gz`
(450 Mo sur les 941 du premier run, 48 %) n'est consommé QUE par
`reporting.py` (les 28 figures Simulation Lab), jamais par
`interest_income.py`/`renewal.py` (qui lisent les instantanés `.npz`) —
et M4.2B ne générait les 28 figures que pour confirmation/cellules
centrales, pas pour l'exploration (`m4_2_credit_soc/scripts/lib_lab.py`,
docstring). `run_pilot.py` prend maintenant `--individual-every` (défaut 0
pour les runs pilote/exploration), avec le paramètre disponible si un run
est promu au statut "confirmation". `PER_RUN_BYTES_ESTIMATE` remonté à
2,5 Go (mesuré 941 Mo à T=3000 AVEC individual_series ; T=8000 SANS, majoré
pour ne pas supposer une mise à l'échelle strictement linéaire avec T).

**Relancé** : `control_geometric seed0`, T=8000, `individual_every=0`,
mêmes garde-fous (préflight repassé avec la nouvelle estimation, verrou,
registre, plafond mémoire). Le run à T=3000 est remplacé (même label/seed,
son rôle était diagnostique — a servi à établir le besoin de T=8000, pas à
être conservé comme résultat).

**Terminé avec succès à 09:14 (lancé 08:34, ~40 min)** : `status="ok"`,
`t_final=8000`, `book_errors=[]`. `mem_guard.csv` : **0 dépassement sur
toute la durée** — première validation du garde-fou mémoire sur un run
substantiellement plus long que le premier (40 min contre 17), utile avant
de lui faire confiance sur des runs de plusieurs heures.

**Bug de supervision trouvé et documenté (pas un incident du run)** : le
script d'attente que j'avais lancé (`until tmux capture-pane ...; do sleep
10; done`) a continué à interroger la session tmux `m43_pilot` bien après
sa fermeture normale (fermeture attendue : `sleep 5` après l'affichage de
"run terminé", cf. `run_pilot.py`) sans jamais satisfaire sa condition
d'arrêt — `capture-pane` sur une session fermée renvoie une erreur, pas le
dernier contenu affiché, donc le motif recherché ("run terminé") n'a
jamais été revu. Résultat : aucune notification de complétion reçue, le
run terminé silencieusement à 09:14, découvert seulement à la question de
l'utilisateur ("on en est où ?") six heures plus tard. **Le run lui-même
n'a subi aucun impact** (fichiers complets, `summary.json` cohérent,
`series.csv` va jusqu'à t=8000) — c'est uniquement le mécanisme de
notification qui a échoué. À corriger avant de refaire confiance à ce
patron d'attente : vérifier la complétion via un fichier sur disque
(`summary.json` existe + `status="ok"`) plutôt que via le contenu d'un
pane tmux qui peut disparaître.

**Relaxation ré-mesurée sur le run complet (T=8000)** :

| champ | tau | t_delay | t_converge |
|---|---|---|---|
| nw | 1168,2 | 547,9 | 4077,6 |
| K | 42,7 | 0,0 | 153,1 |
| income | 1232,9 | 488,3 | 4212,0 |
| **int_in** | **1243,0** | **420,1** | **4174,1** |

`t_converge(int_in)=4174,1 < T=8000` : cette fois la stationnarité de
l'intérêt pur est atteinte AVANT la fin du run, avec marge (~48 % du run
reste post-convergence, exploitable pour l'analyse). **L'écart notable
international se reproduit** (ratio tau(int_in)/tau_moyen(nw,K,income)
=1,53 sur ce run contre 1,66 sur le run T=3000, même ordre de grandeur,
deux mesures indépendantes malgré une seule graine partagée) — pas un
artefact du premier run trop court.

**Statistique de queue (§2) — PAS ENCORE gelée** : nécessite plusieurs
graines à paramètres fixés pour comparer la reproductibilité inter-graines
de plusieurs candidats (α̂ pur, exposant tronqué, paramètre de coupure).
Un seul run ne suffit pas à cette décision. Prochaine étape.

## 10. Consigne utilisateur (2026-08-07, 15h29) : autonomie systématique + réveil périodique

**« Go. Enchaine systématiquement. Mets un réveil qui te demande de
poursuivre toutes les 5h30. Ne t'arrêtes que quand l'intégralité du prompt
initial est répondu. »**

**Mécanisme de réveil** : la compétence `schedule` invoquée d'abord crée
des agents CLOUD (sandbox isolé, son propre checkout git, AUCUN accès à
cette machine — ni aux fichiers, ni aux sessions tmux `m43_memguard`/runs
en cours, ni à `/proc/meminfo` de CETTE machine). Totalement inadapté :
un tel agent ne pourrait ni voir l'état réel du programme ni respecter les
garde-fous §7 (qui protègent CETTE machine spécifiquement). Abandonné
avant création. Utilisé à la place : `CronCreate` (outil de premier niveau,
distinct de la compétence `schedule`/`RemoteTrigger`) — enfile un prompt
dans CETTE session à intervalle cron, avec tout le contexte déjà accumulé.

**Limite technique acceptée et documentée** : cron (5 champs, calé sur
l'horloge murale) ne peut pas exprimer un intervalle de 5h30 exact (24h/5,5h
n'est pas entier, le motif dériverait entre jours). Approximé par
`17 */5 * * *` (toutes les 5h, à :17 — minute non ronde par convention de
l'outil) : plus fréquent que demandé, dans le sens le plus sûr pour une
tâche de calcul autonome. **Limites du mécanisme, à surveiller** : job
propre à CETTE session (disparaît si la session se termine — cohérent avec
ce qu'on a observé : la session a survécu à l'écart de 6h de ce
matin) ; expire automatiquement après 7 jours (à recréer si le programme
dépasse cette fenêtre). Job id `f2c7c648`.

**Règle de fonctionnement retenue pour la suite autonome** : continuer
systématiquement tout ce qui est prescrit par le prompt et ne PAS
s'arrêter pour demander confirmation sur les choix d'implémentation — MAIS
les décisions explicitement réservées à la supervision par le prompt
lui-même (§9 : décision d'ablation, changement de la statistique de queue
gelée après la phase pilote, tout engagement de budget de calcul hors
périmètre du prompt) restent documentées comme des décisions EN ATTENTE
dans ce journal, jamais tranchées seul, même sous cette consigne
d'autonomie — le prompt les a explicitement mises hors du champ des choses
décidables seul, et rien dans la consigne de l'utilisateur n'indique
vouloir lever spécifiquement CES garde-fous de gouvernance scientifique
(contrairement aux gardes-fous de calcul §7, sur lesquels l'autonomie a
déjà été donnée explicitement plus tôt).

**Lancé** : `scripts/run_pilot_batch.py` (nouveau, enchaîne des runs
`run_pilot.py` séquentiellement — le verrou mono-pool §7.3 empêcherait de
toute façon le parallélisme, c'est voulu). Phase 1 seulement, volontairement
limitée à 2 cellules avant d'aller plus loin :
- `control_geometric seed1`, T=8000 (déjà validé sur seed0, même régime,
  pari raisonnable).
- `baseline_arithmetic seed0`, T=8000 — PREMIÈRE sonde pour ce régime, sa
  relaxation n'a jamais été mesurée (institution arithmétique ≠
  géométrique, dynamiques de capital différentes en M4.2B, Gini(K) très
  contrasté) ; rien ne garantit T=8000 suffisant. À vérifier avec
  `relaxation_pilot.py` avant de lancer les graines 1 et 2 d'arithmetic
  (et avant de généraliser T=8000 comme valeur figée pour D1).

**Phase 1 terminée (16h38), les deux runs à `status="ok"`, 0 dépassement
mémoire sur toute la fenêtre.** Relaxation mesurée :

| run | tau(int_in) | t_converge(int_in) | ratio int_in/proxy |
|---|---|---|---|
| geometric seed0 (T=3000) | 1146,1 | 3910,8 | 1,66 |
| geometric seed1 (T=8000) | 979,9 | 3005,6 | 1,49 |
| geometric seed0 (T=8000) | 1243,0 | 4174,1 | 1,53 |
| arithmetic seed0 (T=8000) | 316,6 | 1015,7 | 1,35 |

**Deux enseignements** :
1. **T=8000 est confirmé largement suffisant pour les deux régimes** —
   arithmetic converge presque 4× plus vite que geometric (t_converge≈1016
   contre 3006-4174), aucune extension nécessaire.
2. **Le temps de relaxation lui-même varie sensiblement entre graines à
   paramètres FIXES** (control_geometric seed0 vs seed1 : t_converge
   3006-4174, ~28 % d'écart) — confirme que la fenêtre d'analyse doit être
   positionnée PAR RUN (sa propre mesure), pas par une valeur unique
   figée pour toute la cellule, conformément au principe du §3.
3. **La direction de l'écart int_in > proxy se reproduit sur 4/4 mesures
   indépendantes** (ratio 1,35 à 1,66, jamais inversé), mais son AMPLITUDE
   varie assez pour repasser sous le seuil de 50 % choisi arbitrairement
   dans `relaxation_pilot.py` (seed1 geometric : 1,49). Le seuil de 50 %
   était un critère d'alerte grossier pour ce script de diagnostic, pas un
   test statistique — la conclusion qualitative (le proxy M4.2B sous-
   estime systématiquement, l'écart n'est pas negligeable) tient sur les 4
   mesures ; l'ampleur exacte devra être caractérisée avec plus de graines
   avant d'entrer dans le rapport final comme un nombre précis.

**Lancé, phase 2** : `control_geometric seed2`, `baseline_arithmetic
seed1`, `baseline_arithmetic seed2`, tous T=8000 (reprise automatique,
phase 1 sautée car déjà `status="ok"`). Objectif : 3 graines par cellule,
pour (a) geler la statistique de queue (§2) via reproductibilité
inter-graines, (b) comparer geometric/arithmetic avec barres d'erreur (§4).

**Phase 2 terminée (18h12), 0 dépassement mémoire sur toute la fenêtre
(~1h33, 3 runs séquentiels).**

## 11. Statistique de queue GELÉE (§2) — Dagum c (indice de queue), pas c·d

**`scripts/freeze_tail_statistic.py`** (nouveau, assemble
`interest_income.fit_income_distribution` — donc `families.py`/
`tail_test.py`, RIEN de récrit, §5/§8) : sur chaque graine, fenêtre
positionnée sur son propre `t_converge(int_in)` (§3), valeurs `int_in`
poolées sur tout le run post-convergence, deux candidats comparés :

- **Candidat A** : `alpha_density`, l'estimateur de Hill/Pareto pur à
  seuil scanné — la statistique α̂ utilisée PARTOUT dans M4.2B.
- **Candidat B** : le paramètre de forme du meilleur ajustement à 3
  paramètres de la famille de corps (`dagum_3p`, Burr Type III, scipy
  `burr` — famille usuelle pour les distributions de revenu avec
  coude/coupure de queue), le paramètre `c`.

### Erreur trouvée et corrigée (2026-08-07, avant la clôture de la phase pilote — correctif de bug, décidable seul §9, pas un changement de statistique gelée puisque rien n'était encore gelé de façon fiable)

Première passe : j'avais annoncé le candidat B comme `c·d` avec la
justification « survie ~ x^-(c·d) à x grand ». **Faux.** Pour
`scipy.stats.burr` (Burr Type III/Dagum), pdf(x,c,d) =
c·d·x^(-c-1)·(1+x^-c)^(-d-1) ; à x grand le facteur (1+x^-c)^(-d-1)→1, donc
**la survie asymptotique va comme x^-c — l'indice de queue SUPÉRIEURE est
`c` seul**. `c·d` gouverne la queue INFÉRIEURE (x→0) — c'est la formule de
Burr Type XII (`scipy.stats.burr12`, utilisée par `singhmaddala_3p`, une
AUTRE famille du ladder) que j'ai appliquée par erreur à Burr III. Deux
signaux auraient dû m'alerter avant de geler : (1) `c·d≈0,92` comme indice
de queue implique une moyenne infinie — incompatible avec un revenu borné
par la production totale d'une économie finie, dont l'échantillon a
manifestement une moyenne finie ; (2) le code affichait `scale=0` pour
CHAQUE graine — `dist.fit(pos, floc=0)` renvoie 4 valeurs `(c, d, loc,
scale)`, pas 3, et mon dépaquetage `c, d, scale = params[:3]` étiquetait
`loc` (pinné à 0 par construction) comme `scale`. Trouvé en demandant un
second avis avant de bâtir D1 dessus — corrigé dans le script, section
réécrite ci-dessous avec les valeurs correctes (pas une nouvelle mesure :
mêmes ajustements, juste la bonne colonne des mêmes `params`).

**Résultat sur les 3 graines `control_geometric`** :

| candidat | seed0 | seed1 | seed2 | moyenne | std | CV |
|---|---|---|---|---|---|---|
| A — alpha_density (Pareto pur) | 3,3732 | 3,3652 | 3,2773 | 3,3386 | 0,0532 | 1,59 % |
| B — dagum c (indice de queue) | 3,3738 | 3,3754 | 3,3346 | 3,3613 | 0,0231 | **0,69 %** |

**Résultat sur les 3 graines `baseline_arithmetic`** :

| candidat | seed0 | seed1 | seed2 | moyenne | std | CV |
|---|---|---|---|---|---|---|
| A — alpha_density (Pareto pur) | 3,7647 | 3,8620 | 3,8441 | 3,8236 | 0,0518 | 1,35 % |
| B — dagum c (indice de queue) | 3,9486 | 4,0005 | 3,9569 | 3,9687 | 0,0279 | **0,70 %** |

**Décision (critère du §2, appliqué tel quel — écart-type inter-graines le
plus faible, pas la valeur) : GELÉ sur le candidat B, `dagum_3p` c.**
La conclusion de la décision NE CHANGE PAS avec la correction — B reste
~2× plus reproductible que A sur les deux régimes (0,69-0,70 % contre
1,35-1,59 %) — seule la valeur numérique et sa justification physique
changent. Fait notable, indépendant du bug : avec 2 graines seulement
(résultat intermédiaire, voir plus haut) le candidat A semblait déjà très
reproductible (CV 0,17 %) — c'est la 3ᵉ graine qui a révélé l'instabilité
réelle. **Leçon méthodologique enregistrée** : ne jamais geler sur 2
graines, le protocole (§2, "plusieurs graines") est vérifié a posteriori
comme nécessaire.

**Ce que cela signifie pour le fond** : le corps ENTIER de la distribution
d'intérêts (ladder AIC, k=1 à 5) favorise TRÈS largement une famille à
coude (`dagum_3p`/`gb2_4p`, ΔAIC~15 000-20 000 par rapport à l'exponentielle
1p) sur les 6 graines — cohérent avec l'hypothèse de travail du §0 du
prompt M4.3.2B (existence d'une coupure/coude, pas une loi de puissance
pure) et avec le fait que le Pareto pur (candidat A), qui IGNORE cette
courbure par construction, est empiriquement moins stable d'une graine à
l'autre.

**Statistique gelée pour la suite du programme (D1/D2/D3, jusqu'à
nouvel ordre — un changement ultérieur attend la supervision, §9)** :
`dagum_3p` (Burr Type III) ajusté sur `int_in` poolé, fenêtre = post-
`t_converge(int_in)` propre à chaque run, statistique reportée = `c`
(indice de queue supérieure, `survie ~ x^-c`).

**Re-vérification terminée** : script corrigé relancé sur les 6 graines.
Les 6 valeurs de `c` (et désormais `scale`, non nul — confirme aussi le
correctif du dépaquetage) reproduisent EXACTEMENT celles calculées à la
main ci-dessus (3,3738/3,3754/3,3346/3,9486/4,0005/3,9569). Fit confirmé
correct et reproductible.

**Piège méthodologique évité de justesse** : le résumé final de cette
invocation (les 6 runs passés en UNE seule commande) calcule un CV
combiné geometric+arithmetic — et y trouve A « plus reproductible » que B.
**Ce résumé combiné est invalide, pas utilisé pour la décision** : il
mélange la variance inter-GRAINES (le bruit à caractériser) avec l'écart
RÉEL entre régimes (geometric c≈3,36 vs arithmetic c≈3,97, un effet, pas
du bruit) — exactement la confusion d'échelle que le §6 du prompt interdit
explicitement (« ne jamais fusionner ces échelles »). La décision de gel
ci-dessus reste celle calculée SÉPARÉMENT par régime (3 graines à
paramètres FIXES à la fois), la seule comparaison valide pour ce critère.

## 12. Comparaison geometric/arithmetic (§4, objectif du tout premier run) — côté avalanches fait, côté intérêt en cours

**`scripts/compare_geo_arith.py`** (nouveau, assemble
`lib_metrics.window_avalanche_metrics`/`compare_laws` — méthodologie M4B
héritée sans changement, §5/§8) : fenêtre par run sur son propre
`t_converge(int_in)`, `s_min=2` (convention M4B/M4.2B).

**Côté avalanches (b, τ̂), 3 graines chacun** :

| régime | b (branching ratio) | τ̂ (avalanches, tronqué) |
|---|---|---|
| geometric | 0,7542 ± 0,0015 | 1,4763 ± 0,0069 |
| arithmetic | 0,7853 ± 0,0005 | 1,4242 ± 0,0060 |
| Δ (geo−arith) | −0,0311 ± 0,0009 (≈34σ) | +0,0521 ± 0,0053 (≈10σ) |

Séparation extrêmement nette sur les deux métriques, avec seulement 3
graines chacun — pas un effet marginal. **geometric = moins critique
(b plus bas) ET queue d'avalanches plus fine (τ̂ plus élevé)** que
arithmetic, cohérent avec la direction déjà connue de M4.2B
(`s_c_out_of_range=False` sur les 6 runs — coupure dans la fenêtre
observable, pas de repli sur la loi pure).

**Côté intérêt (statistique gelée, dagum c, corrigée §11)** :

| régime | dagum c (indice de queue supérieure) | dagum c invalide (c·d, corrigé) |
|---|---|---|
| geometric | 3,3613 ± 0,0231 | ~~0,9209 ± 0,0018~~ (formule fausse) |
| arithmetic | 3,9687 ± 0,0279 | ~~0,8080 ± 0,0072~~ (formule fausse) |

**c plus petit = queue plus épaisse (décroissance plus lente). geometric a
c PLUS PETIT que arithmetic (3,36 < 3,97) → geometric a la queue
d'intérêt PLUS ÉPAISSE.** Confirmé indépendamment par le candidat A
(alpha_density) : geometric 3,34 < arithmetic 3,82, MÊME SENS — et par la
mesure historique de M4.2B citée en §0 du prompt (α̂=3,318 géométrique
contre 3,890 arithmétique, même sens encore). Trois mesures indépendantes,
même direction. (La version erronée `c·d` avait inversé ce sens — c'est
CE renversement, contradictoire avec les deux autres mesures et avec
M4.2B, qui a déclenché la vérification du §11.)

### Verdict D2 pour ce levier (target_rule) : NÉGATIF — l'anti-corrélation tient

- **geometric** : queue d'intérêt plus ÉPAISSE (c=3,36) **et** avalanches
  MOINS critiques (b=0,754, τ̂=1,476 — queue d'avalanches plus fine).
- **arithmetic** : queue d'intérêt plus FINE (c=3,97) **et** avalanches
  PLUS critiques (b=0,785, τ̂=1,424 — queue d'avalanches plus épaisse).

Exactement le motif d'anti-corrélation déjà établi dans M4.2B sur les 37
cellules explorées (§0 du prompt) : aucune direction ne combine queue
d'intérêt plus épaisse ET criticité égale/accrue. `target_rule`
(géométrique vs arithmétique — le canal multiplicatif que la cible
arithmétique supprime) **ne casse pas l'anti-corrélation** ; c'est un
point de plus sur la même droite anti-corrélée. Séparation statistique
très nette (b : ≈34σ ; τ̂ : ≈10σ ; c : delta=0,607, SE combiné
√(0,0231²/3+0,0279²/3)≈0,021, soit ≈29σ) — pas un résultat marginal, pas
un artefact de faible puissance statistique.

**Ce verdict est négatif ET c'est un résultat scientifique valide (§1 du
prompt, cité explicitement : « Un résultat négatif sur D2... est un
résultat scientifique valide et publiable — ce n'est pas un échec »).**
Il répond à la question posée en tête de ce prompt pour CE levier
spécifique (le canal multiplicatif) ; il ne clôt pas D2 pour l'ensemble du
programme — D1 (cartographie sur l'espace déjà couvert par M4.2B + les
extensions propres à ce prompt) reste à faire pour chercher un autre
levier avant de conclure D2 dans son ensemble.

## 13. Cartographie D1 lancée (2026-08-07, 18h50)

**`scripts/campaign_d1.py`** (nouveau) : pool multiprocessing (patron
`m4_2b_credit_soc/scripts/campaign.py`, déjà validé sur 87+45 runs en
M4.2B, 0 crash après ses correctifs JOURNAL §10/§12/§15), 6 workers
(§7.5), avec les six garde-fous §7 câblés :
- `build_cells()` = copie exacte des paramètres de
  `m4_2b_credit_soc/scripts/campaign.py` (28 cellules : baseline, K0×5,
  gamma×4, gamma_comp×4, beta×4, deltasigma×4, rho×5,
  control_geometric — SANS `t10000_baseline`, T géré séparément ici) —
  c'est « l'espace déjà couvert par M4.2B » du §1, paramètres INCHANGÉS.
- **T=8000 uniforme** pour le premier passage (validé sur baseline
  arithmetic ET geometric, §9-§10 — pas re-calibré par cellule avant
  lancement, ce qui prendrait un temps déraisonnable sur 28 cellules ;
  **chaque run mesure son propre `t_converge(int_in)` a posteriori** et
  se marque `severe_nonstationary=True` si `t_converge > 0,9·T` ou non
  identifiable — repli explicite sur la convention M4.2B (§3 : documenter
  comme sévère plutôt que forcer une fenêtre invalide), pas une hypothèse
  silencieuse.
- **Analyse ALLÉGÉE** par run : un seul fit `dagum_3p` (la statistique
  gelée, §11) — PAS le ladder complet à 10 modèles de
  `freeze_tail_statistic.py` (qui a servi à choisir la statistique, pas à
  l'appliquer répétitivement — c'est le poste de temps dominant, inutile
  une fois le choix fait) — plus `lib_metrics.window_avalanche_metrics`
  (b, τ̂, méthodologie M4B/M4.2B inchangée).
- **Nettoyage post-analyse intégré dès le départ** (pas en rattrapage
  comme pour M4.2B, §7.6) : `loan_events.csv.gz`/`snapshots/`/
  `checkpoint.pkl` supprimés après écriture réussie d'`analysis.json` —
  nécessaire par arithmétique disque (87 runs bruts ~1,3 Go chacun
  ≈113 Go > 97 Go libres ; gardé/run ~44 Mo ≈3,8 Go pour 84 runs, largement
  soutenable).
- Verrou mono-pool tenu pour la durée de vie du pool entier ; PID des 6
  workers enregistrés auprès de `mem_guard.py` (`pool._pool[i].pid`,
  vérifié isolément avant le lancement réel) ; plafond mémoire par worker
  calculé sur `MemAvailable` réel pour 6 workers ; préflight disque avant
  le lancement du pool ET avant chaque run individuel.

**Smoke-testé avant lancement réel** (`_run_and_analyze` isolé, T=50,
label "smoke", supprimé après vérification) : cycle complet run → analyse
→ nettoyage → reprise (deuxième appel instantané, `analysis.json` déjà
`status="ok"`) confirmé correct. `pool._pool[i].pid` vérifié séparément
sur un pool à 2 workers jetable.

**Lancé** (tmux `m43_d1`, détaché) : 28 cellules, **84 runs**. Démarrage
confirmé sain : 6 workers enregistrés (PID
33751-33756), plafond 4,43 Go/worker (`MemAvailable`=30,89 Go, cohérent
avec le pic RSS de ~1,94 Go observé en M4.2B sur K0=2000 avec le même
moteur, §12 JOURNAL M4.2B — marge confortable), `mem_guard.csv` stable
(~31 Go disponible, 0 dépassement) sur les ~3 premières minutes, disque à
96 Go libres.

**Durée attendue** : de l'ordre de plusieurs heures (84 runs / 6 workers,
chaque run T=8000 de quelques minutes — arithmetic — à plusieurs dizaines
de minutes selon la cellule, K0_2000 notamment). Le réveil cron (§10,
toutes les 5h, job `f2c7c648`) reprendra le fil pour vérifier l'avancement
et, une fois `84/84` runs à `status∈{ok,error}`, calculer le verdict D1
(l'anti-corrélation tient-elle partout sur cet espace, ou existe-t-il des
poches où elle s'inverse ?) — pas encore fait à l'heure de cette entrée.

**Reste à faire après D1** : verdict D1 (tableau (dagum_c, b) par
cellule, graines agrégées, figure dédiée — livrable §10) ; si une poche
positive apparaît, vérifier sa robustesse (graine/fenêtre — D3, pas encore
la taille via λ qui est un sous-programme séparé §5) ; jalon de décision
d'ablation (§4, fin de cartographie D1 — décision EN ATTENTE de
supervision, §9) ; rapport final (§10).

## 14. Point d'étape (2026-08-07, 20h47, réveil cron)

**D1 en cours** : 12/84 runs (`status=ok`, 0 erreur), ~2h écoulées depuis
le lancement (18h50) — rythme ≈6 runs/h avec 6 workers, donc ≈14h pour les
84 runs si le rythme reste stable (cellules K0 élevé plus lentes,
attendre un ralentissement, pas une accélération). `mem_guard.csv` :
0 dépassement, `MemAvailable` stable autour de 20-31 Go. Disque : 88 Go
libres (nettoyage post-analyse confirmé actif — le disque NE croît PAS
avec le nombre de runs terminés).

**Observation PRÉLIMINAIRE sur la branche K0 (3-4 cellules sur 28, PAS un
verdict)** : K0_1 (c≈4,54, b≈0,586) → K0_5 (c≈4,18, b≈0,709) → K0_100
(c≈3,89, b≈0,793) → baseline/K0_25 (c≈3,97, b≈0,785) — sur ces points, la
queue s'épaissit (c décroît) EN MÊME TEMPS que la criticité augmente (b
croît), motif OPPOSÉ à l'anti-corrélation vue sur `target_rule` (§12).
**Ne PAS interpréter comme un D2 positif avant d'avoir appliqué la réserve
du §5** : K0 est exactement l'axe que M4.2B a confondu avec un proxy de
taille (mémoire de session, rapport final M4.2B §8) — population finale
K0_1≈?, K0_100≈? pas encore comparées ; un effet de taille finie peut
affecter b ET la statistique de queue simultanément sans qu'aucun
mécanisme économique ne les relie. Vérification différée à la fin de la
cartographie K0 complète (5 valeurs) et croisée avec les cellules dont le
`eta_n_ref`/population sont comparables.

**`scripts/d1_verdict.py` (nouveau, en cours d'écriture)** : agrège tous
les `analysis.json` sous `results/d1/`, calcule moyenne/std inter-graines
de `dagum_c` et `branching_ratio` par cellule (même une fois la campagne
partiellement terminée), signale les cellules `severe_nonstationary`.
Pas encore de verdict final (données insuffisantes, 12/84).

**Rien de nouveau en attente de supervision** — la seule décision encore
en liste (§4, jalon d'ablation) attend la fin de D1, pas encore atteinte.

## 15. Point d'étape (2026-08-08, 00h47, réveil cron) — K0_2000 échoue proprement, garde-fou validé en conditions réelles

**36/84 runs, 34 ok, 3 erreurs (K0_2000, les trois graines)** — TOUTES les
autres cellules déjà passées (K0_1/5/100/500, gamma×4, gamma_comp×2)
réussissent sans exception. `K0_500` a réussi (~118 min/run, la cellule la
plus lente jusqu'ici) — c'est bien SEULEMENT K0_2000 qui échoue, pas un
problème systémique. Cohérent avec l'historique M4.2B (JOURNAL M4.2B §11-
§12 : K0_2000 était déjà la SEULE cellule à nécessiter des correctifs
spécifiques sur 87 runs).

**Erreur** : `numpy._core._exceptions._ArrayMemoryError: Unable to
allocate 5.51-5.94 MiB` — dans `m4_3/model.py::network_snapshot`, pendant
la construction du tableau `r`/`q` du réseau de prêts (~720-780k prêts
actifs). **Capturée proprement par le `try/except` de
`_run_and_analyze`** (§7 point 3 de l'incident M4.2B §15, reproduit ici) :
`status="error"` écrit avec traceback complet, LE POOL A CONTINUÉ (28 runs
supplémentaires réussis juste après, aucune propagation). **C'est le
garde-fou qui fonctionne comme prévu, pas un échec du garde-fou** — la
différence avec M4.2B avant ses correctifs (JOURNAL M4.2B §15 : une seule
`MemoryError` non capturée tuait tout le pool) est exactement ce que le
`try/except` de `campaign_d1.py` (copié du correctif M4.2B) est censé
empêcher, et l'empêche bien.

**Piste de cause, pas encore confirmée** : l'allocation qui échoue est
PETITE (5,5 Mo) — signe que le worker était déjà proche de son plafond
`RLIMIT_AS` (4,43 Go) avant cette allocation précise, pas que cette
allocation seule soit énorme. Hypothèse : `RLIMIT_AS` borne la mémoire
VIRTUELLE, pas résidente (RSS) — M4.2B avait mesuré K0_2000 à 1,94 Go de
RSS MAX (JOURNAL M4.2B §12), sous son plafond de 3,15 Go, mais la mémoire
virtuelle réservée par l'allocateur Python/numpy (fragmentation,
arènes glibc, régions mmap) peut dépasser sensiblement le RSS — mon
plafond de 4,43 Go peut être plus serré en VIRTUEL qu'il n'y paraît en
comparant au RSS de M4.2B. Pas vérifié directement (nécessiterait de
relancer K0_2000 seul avec `/proc/<pid>/status` VmSize suivi en direct) —
noté comme piste, pas comme fait établi.

**`mem_guard.csv` : premier swap_in non nul de toute la session** (164,2
pps à 00h47, sous le seuil de 200 pps qui déclenche une action — donc pas
d'intervention du garde-fou) — cohérent avec une pression mémoire agrégée
au moment où plusieurs workers étaient proches de leur plafond
simultanément (K0_2000 + d'autres cellules lourdes en vol). `MemAvailable`
descendu à ~14 Go (contre 31 Go au lancement) — pas un défaut du calcul du
plafond (fait au lancement, conforme à §7.2), mais une limite du modèle
« plafond calculé une fois, jamais réévalué » sur un pool de plusieurs
heures — à garder en tête pour un futur pool encore plus long.

**Décision (correctif de bug/implémentation, décidable seule §9)** :
laisser le pool principal continuer (48 runs restants, aucune autre
cellule affectée) ; **retenter K0_2000 séparément, APRÈS la fin du pool
principal** (le verrou mono-pool §7.3 empêche de toute façon un second
pool concurrent — protection qui a évité de reproduire l'incident M4.2B
§15 si j'avais été tenté de lancer une reprise en parallèle), avec MOINS
de workers pour lui donner beaucoup plus de marge par worker (ex. 2
workers au lieu de 6 -> plafond ≈13 Go/worker au lieu de 4,43 Go).

## 16. D1 TERMINÉE (2026-08-08, 04h27) — un candidat D2 sérieux trouvé : `gamma_comp`

**84/84 runs traités, 81 ok, 3 erreurs (K0_2000, cause déjà diagnostiquée
§15).** `mem_guard.csv` : 11 lectures avec dépassement isolé sur toute la
campagne (jamais plus de 2 consécutives, le seuil d'action est 3) — **0
HALT posé, 0 kill, aucune intervention nécessaire**. `MemAvailable` revenu
à 31 Go dès la fin du pool. Disque stable à 82 Go libres tout du long (le
nettoyage post-analyse a tenu sa promesse). 0/81 runs `severe_
nonstationary` — T=8000 s'est avéré suffisant pour TOUTES les cellules
qui ont pu tourner.

`scripts/d1_verdict.py` exécuté sur les 84 runs : table complète dans
`results/d1/d1_verdict_cells.csv`, figure dans
`results/d1/d1_verdict_plan.png`.

### Verdict D1 : l'anti-corrélation tient sur 24/26 cellules identifiables, MAIS PAS SUR LA BRANCHE `gamma_comp` À γ ÉLEVÉ

Classification systématique (chaque cellule vs baseline : `dagum_c` plus
bas = queue plus épaisse ; `b` plus haut = plus critique) :

- **Anti-corrélée (motif M4.2B, majorité)** : `beta_*` (4/4), la plupart
  de `deltasigma_*`, `gamma_0.4000/0.6000/0.6667`, `rho_*` (5/5),
  `control_geometric` (§12, déjà établi), `K0_500`.
- **« Both down » (queue plus fine ET moins critique, pas informatif pour
  D2 — les deux baissent ensemble)** : `K0_1`, `gamma_0.3333`,
  `gamma_comp_0.3333/0.4000`, `deltasigma_0.05_0.25`.
- **CANDIDATS D2 (queue plus épaisse ET b plus élevé)** : `K0_100`
  (effet faible, c=3,894 vs 3,969 — MAIS c'est justement l'axe K0
  confondu avec la taille, réserve §5, à ignorer comme preuve autonome) ;
  **`gamma_comp_0.6000` (c=3,582±0,010, b=0,8015±0,0013) et
  `gamma_comp_0.6667` (c=3,387±0,026, b=0,8036±0,0011)**, tous deux très
  significatifs (~15σ sur les deux axes vs baseline).

**La branche `gamma_comp` complète montre une tendance MONOTONE et
cohérente**, pas juste deux points isolés :

| γ | K0 (compensé) | dagum_c | b |
|---|---|---|---|
| 1/3 | | 5,187±0,059 | 0,7598±0,0009 |
| 0,4 | | 4,562±0,034 | 0,7696±0,0005 |
| 0,6 | | 3,582±0,010 | 0,8015±0,0013 |
| 2/3 | | 3,387±0,026 | 0,8036±0,0011 |

En comparaison, la branche `gamma` NON compensée (même γ, K0 fixe à 25)
montre un `b` NON monotone (pic à γ=0,4 puis chute) — la compensation
K0/K*_aut(γ) change qualitativement la relation. C'est un résultat
scientifique intéressant en soi, indépendamment de D2.

**Réserve appliquée avant de crier victoire** : `gamma_comp` fait AUSSI
varier K0 (par construction, pour compenser γ) — vérifié directement
(`population_final`, 3 graines par cellule) : gamma_comp_0,3333→1220,
0,4→1098, 0,6→1224, 0,6667≈1395, baseline≈1163. Variation ≈±25 % autour de
la baseline — BIEN MOINDRE que la branche K0 brute (K0_1→K0_2000 fait
varier la population sur PLUSIEURS ORDRES DE GRANDEUR), mais PAS NULLE.
**Ce candidat n'est PAS confirmé tant que la robustesse de taille (§5,
via λ à γ fixé) n'a pas été vérifiée** — c'est exactement la question D3
que le prompt anticipe pour un D2 positif (§1, §10 : « Si D2 positif :
verdict D3 »).

### Prochaines étapes (décidables seules, prescrites par §1/§5/§10, PAS le jalon d'ablation)

1. Retenter K0_2000 (3 graines) séparément, moins de workers (déjà prévu
   §15).
2. **Vérification de taille sur `gamma_comp_0.6667`** (le candidat le
   plus net) : sweep λ∈{10,30,100} à γ=2/3 compensé, K0 fixe à la valeur
   compensée — si le motif (queue épaisse + b élevé) persiste
   indépendamment de λ, le candidat est robuste à la taille et D2 devient
   positif pour de bon ; si le motif disparaît/s'inverse avec λ, c'est un
   artefact de taille comme K0 brut, D2 reste négatif sur cet axe aussi.
3. Rapport intermédiaire de ce verdict D1 dans le rapport final (§10).

### Jalon d'ablation (§4) : ATTEINT — décision EN ATTENTE DE SUPERVISION (§9)

**La cartographie D1 est maintenant substantiellement terminée** (81/84,
K0_2000 en reprise séparée) — c'est le jalon que le prompt fixe pour
trancher, explicitement et par écrit, si une refonte de mécanisme (§4 :
famille de moyennes de puissance pour la règle de taux, ou autre) est
nécessaire. **Cette décision est explicitement hors du champ de ce que je
peux trancher seul (§9)** — je ne la prends pas, je documente les éléments
pour vous :
- **Pour** une ablation : le candidat `gamma_comp` (ci-dessus) montre
  qu'un changement de RÈGLE DE TAUX combiné à une COMPENSATION de capital
  peut casser l'anti-corrélation — si D3 (λ) confirme sa robustesse,
  cela suggère qu'une famille de moyennes de puissance plus riche (la
  note manuscrite du §4) pourrait révéler une région encore plus
  favorable, pas seulement les deux points déjà couverts (arithmétique,
  géométrique).
- **Contre** (ou "pas encore") : le candidat n'est PAS confirmé (réserve
  de taille ci-dessus) ; une ablation est un investissement de code
  nouveau (§4 : "n'envisager cette famille que si le run géométrique...
  montre une différence réelle" — condition remplie pour `target_rule`
  seul, mais `target_rule` seul était D2-négatif, §12 ; c'est `gamma_comp`
  qui est positif, un axe différent de celui que §4 anticipait comme
  déclencheur) ; la vérification D3 par λ (étape 2 ci-dessus, pas cher,
  déjà l'outillage existant) est un préalable moins coûteux et plus
  informatif avant d'engager du code de mécanisme nouveau.

**Je vais continuer sur l'étape 2 (D3 par λ) en attendant votre décision**
— c'est un prolongement direct de D1 déjà prescrit par le prompt, pas une
ablation.

**Lancé** : `scripts/retry_k0_2000.py` (2 workers, plafond 13,56 Go/worker
— 3× plus de marge que les 4,43 Go du pool principal) — tmux `m43_k0_2000`.
**Écrit et vérifié, PAS encore lancé** (verrou mono-pool tenu par la
reprise K0_2000) : `scripts/d3_size_check.py`, 4 cellules nouvelles
({baseline, gamma_comp_0.6667} × λ∈{10,100}, λ=30 déjà couvert par D1,
réutilisé sans relancer) — valeur de K0 compensé revérifiée identique
(2474,999999999995) à celle déjà mesurée en D1, pas de divergence
d'arrondi. Sera lancé dès la fin de la reprise K0_2000 (le verrou l'exige
de toute façon).

## 17. Point d'étape (2026-08-08, 05h47, réveil cron) — rapport démarré

**K0_2000 (reprise) toujours en cours** (~1h20 écoulées sur ~3h attendues,
2 workers × 3 graines, ~90-100 min/run en M4.2B). Rien de nouveau, aucune
erreur, mémoire stable (~27 Go disponible). Le verrou mono-pool empêche
toujours le lancement de D3.

**`report/rapport_final.md` démarré** (brouillon vivant, statut affiché en
tête, pas encore final) — sections stables déjà rédigées : contexte,
méthode complète (garde-fous, fenêtre adaptative, statistique gelée,
cartographie), repères terminologiques, verdict `target_rule` (§4 du
rapport, D2 négatif), cartographie D1 complète avec le candidat
`gamma_comp`, section K0_2000. Deux sections explicitement marquées EN
ATTENTE : verdict D3 (§7 du rapport) et décision d'ablation (§8, réservée
à la supervision — mêmes arguments pour/contre déjà écrits ici §16, repris
tels quels dans le rapport pour cohérence). Figure copiée dans
`report/figures/d1_plan_dagum_c_vs_b.png`.

**Rien de nouveau en attente de supervision au-delà de ce qui est déjà
noté** (décision d'ablation, §16).

## 18. Point d'étape (2026-08-08, 10h47, réveil cron) — K0_2000 : plus de mémoire a suffi, mais la cellule est intrinsèquement sévère

**Correction d'une lecture erronée faite en cours de vérification** (pas
une erreur du programme — trouvée en revérifiant avant d'écrire cette
entrée) : `results/d1/K0_2000/seed2/analysis.json` affichait encore
`status="error"` au moment du contrôle, horodaté 2026-08-07 23h21 —
**c'est le fichier de l'ÉCHEC ORIGINAL** (pool principal, avant la
reprise lancée à 04h31 le 08/08), pas une nouvelle tentative ratée. La
reprise (2 workers) n'avait simplement pas encore traité cette graine au
moment du contrôle (`imap_unordered`, seed0/seed1 traitées en premier).

**Résultat réel, confirmé** : seed0 (`elapsed_s`≈15274s≈4h14, ok) et
seed1 (`elapsed_s`≈15386s≈4h16, ok) **ont réussi avec le plafond élargi
(13,56 Go/worker)** — confirme l'hypothèse mémoire virtuelle du §15 (le
plafond de 4,43 Go du pool principal était trop serré, pas un problème
insoluble de la cellule elle-même). seed2 toujours en cours (CPU actif
confirmé, `ps aux`).

**Fait nouveau, important pour l'interprétation** : seed0 ET seed1 sont
`severe_nonstationary=True` À T=8000 (`t_converge_int_in` = 9087 et 7568
respectivement — le second dépasse tout juste le seuil 0,9×8000=7200,
le premier le dépasse largement). **K0_2000 est donc une cellule
intrinsèquement sévère pour la statistique de queue gelée**, même une
fois le problème mémoire résolu — cohérent avec le fait que c'est déjà,
de loin, la cellule la plus chère en temps de calcul (4h+/run contre
quelques minutes à ~2h pour le reste de D1).

**Décision (application de la convention déjà actée, §3/§9 — décidable
seule, pas un nouveau choix)** : **ne PAS étendre K0_2000 au-delà de
T=8000.** Coût d'une extension suffisante (T≈15-18000 vu `t_converge`
mesuré) estimé à 8-10h/run, pour UNE SEULE cellule extrême sur 28, déjà
hors de la portée informative du reste de la cartographie (K0=2000 est
80× la baseline). Le prompt prévoit explicitement cette issue : « Une
cellule dont le temps de relaxation ne peut pas être atteint dans un
budget de calcul raisonnable est documentée comme telle (sévère, non
stationnaire confirmée) plutôt que forcée à un T arbitraire — convention
déjà en place en M4.2B, à garder » (§3). K0_2000 sera documentée dans le
rapport comme cellule sévère (`dagum_c` non disponible), avec ses
métriques d'avalanches (`b`/`τ̂`, moins sensibles à la fenêtre) rapportées
quand identifiables (déjà le cas pour seed1 : b=0,680, τ̂=1,306).

**Rien de nouveau en attente de supervision.**

## 19. K0_2000 clos, D3 lancé (2026-08-08, 13h01)

**Reprise K0_2000 terminée** (session tmux `m43_k0_2000` fermée à 13h01) :
**3/3 `status=ok`**, les 3 `severe_nonstationary=True` (t_converge 9087,
7568, 7619 — confirme le diagnostic §18, pas un problème mémoire résiduel).
Côté avalanches (moins sensible à la fenêtre) : 2/3 graines identifiables,
`b`=0,6797±0,0011 (seed1=0,681, seed2=0,679 — cohérent ; seed0 non
identifiable, cause pas creusée, cellule déjà documentée comme sévère).
**Table D1 régénérée** (`scripts/d1_verdict.py`) : K0_2000 apparaît
maintenant avec `n_ok=3`, `dagum_c` absent (3/3 sévères, correctement
exclu), `b` disponible. `mem_guard.csv` : 0 dépassement sur toute la
reprise, `MemAvailable` revenu à 31,5 Go dès la fin.

**D3 lancé** dès la libération du verrou mono-pool (tmux `m43_d3`,
`scripts/d3_size_check.py`, 6 workers, plafond 4,52 Go/worker, 12 runs :
{baseline, gamma_comp_0.6667} × λ∈{10,100} × 3 graines — λ=30 déjà couvert
par D1). Objectif : vérifier si le motif `gamma_comp_0.6667` (queue plus
épaisse ET b plus élevé que baseline, §16) tient à taille FIXE (via λ,
pas K0) ou si c'est un artefact de la variation de population (~±25 %)
que la compensation K0/K*_aut(γ) n'élimine pas complètement.

## 20. D3 : résultat partiel très favorable au candidat, un échec mémoire du même type que K0_2000 (2026-08-08, 15h19)

**9/12 runs ok, 3 erreurs** (`gamma_comp_0.6667_lam100`, les 3 graines —
même motif que K0_2000, JOURNAL.md §15/§18 : cette combinaison compense
K0 à 2475 ET pousse λ=100, un des systèmes les plus gros du programme ;
`MemoryError` cette fois dans `pickle.dump` du checkpoint, pas dans
`network_snapshot`, mais même cause racine — plafond virtuel trop serré à
6 workers/4,52 Go). `mem_guard.csv` : 0 dépassement, disque stable à
84 Go. **Retenté séparément** (`scripts/retry_d3_lam100.py`, 2 workers,
13,56 Go/worker — même correctif que K0_2000) — tmux `m43_d3_retry`.

**Résultat sur les 9 runs disponibles** :

| cellule | λ | population finale | dagum_c | b |
|---|---|---|---|---|
| baseline | 10 | ~390 | 3,9932±0,0021 | 0,7825±0,0023 |
| baseline | 30 (D1) | ~1163 | 3,969±0,028 | 0,7853±0,0005 |
| baseline | 100 | ~3775 | 3,9864±0,0018 | 0,7864±0,0006 |
| gamma_comp_0.6667 | 10 | ~468 | 3,3997±0,0370 | 0,8009±0,0028 |
| gamma_comp_0.6667 | 30 (D1) | ~1395 | 3,387±0,026 | 0,8036±0,0011 |
| gamma_comp_0.6667 | 100 | — | en reprise | — |

**Deux faits, tous deux favorables au candidat** :

1. **La baseline est SIZE-INDEPENDENTE sur `dagum_c` ET `b`** (c :
   3,969-3,993, écart <1 % sur un facteur ~10× en population ; b :
   0,7825-0,7864, écart <0,5 %) — reproduit directement le résultat déjà
   établi par M4B (« intensivité ±2 % » sur les observables normalisés),
   validation indépendante que la méthode de test de taille par λ
   fonctionne comme prévu sur CE moteur.
2. **L'écart `gamma_comp_0.6667` vs baseline (queue plus épaisse, b plus
   élevé) est QUASI IDENTIQUE à λ=10 et λ=30**, malgré un facteur ~3× sur
   la population absolue (468 contre 1395) — **PAS le comportement attendu
   d'un artefact de taille** (qui devrait s'atténuer ou disparaître à
   population plus petite). C'est un signal fort, mais pas encore une
   confirmation complète (il manque λ=100, la reprise est en cours) —
   PAS de verdict D3 tranché avant ce dernier point.

**Rien de nouveau en attente de supervision.**

**`scripts/d1_verdict.py` terminé et testé** sur les 12 runs disponibles
(4 cellules complètes à 3 graines : K0_1, K0_5, K0_100, baseline) — table
CSV + figure (nuage de points (dagum_c, b), barres d'erreur inter-graines)
générées avec succès dans `results/d1/`. Réutilisable à tout moment pour
suivre l'avancement ou calculer le verdict final une fois la campagne
terminée. Toujours 12/84 à la fin de ce cycle (rien de nouveau depuis le
dernier point) — le goulot est le calcul lui-même, pas le manque d'outils.
Prochain réveil cron : revérifier l'avancement, calculer le verdict D1 dès
que suffisamment de cellules sont couvertes, en gardant la réserve K0/§5
active pour toute lecture de cet axe spécifique.

**Rien d'autre n'attend la supervision** : le port du moteur, le lanceur de
pool, et le premier run pilote géométrique sont prescrits explicitement par
le prompt (§4, §8) — pas des décisions nouvelles.

**Note de maintenance (2026-08-08, 19h11)** : une section §7 dupliquée par
erreur en fin de fichier lors d'une édition précédente a été déplacée à sa
place chronologique correcte (juste après cette section) — contenu
inchangé, juste l'ordre. Signalé pour traçabilité, pas un correctif de
fond.

## 21. VERDICT D3 : POSITIF, sans ambiguïté — premier levier D2 confirmé du programme (2026-08-08, 19h11)

**Reprise `gamma_comp_0.6667_lam100` terminée : 3/3 ok, AUCUNE sévère**
(T=8000 suffisant, contrairement à K0_2000 — cette cellule est grosse en
population mais pas en K0 individuel élevé, la dynamique de relaxation
diffère). `mem_guard.csv` : 0 dépassement sur toute la reprise.

**Table complète, les trois échelles de taille (λ=10, 30, 100)** :

| cellule | λ | pop moyenne | dagum_c | b |
|---|---|---|---|---|
| baseline | 10 | 393 | 3,9932±0,0021 | 0,7825±0,0023 |
| baseline | 30 | 1163 | 3,9687±0,0279 | 0,7853±0,0005 |
| baseline | 100 | 3775 | 3,9864±0,0018 | 0,7864±0,0006 |
| gamma_comp_0.6667 | 10 | 468 | 3,3997±0,0370 | 0,8009±0,0028 |
| gamma_comp_0.6667 | 30 | 1395 | 3,3867±0,0262 | 0,8036±0,0011 |
| gamma_comp_0.6667 | 100 | 4681 | 3,3921±0,0121 | 0,8049±0,0006 |

**Écart gamma_comp − baseline, aux trois échelles** :

| λ | Δc | Δb |
|---|---|---|
| 10 | −0,5935 (27,7σ) | +0,0184 (8,7σ) |
| 30 | −0,5819 (26,4σ) | +0,0184 (25,9σ) |
| 100 | −0,5944 (84,5σ) | +0,0185 (36,9σ) |

**Δb est identique à 4 chiffres significatifs sur les trois échelles
(0,0184 / 0,0184 / 0,0185) et Δc varie de moins de 2 % relatif** malgré
un facteur >10× sur la population absolue (393→4681 pour la cellule la
plus grosse). C'est la signature exacte d'un effet indépendant de la
taille — pas l'atténuation ou l'inversion qu'on attendrait d'un artefact
de population (le comportement observé sur la branche K0 brute, à
comparer : voir §16, où l'effet EST confondu avec la taille).

### Verdict D3 : POSITIF
Le candidat `gamma_comp_0.6667` (γ=2/3, K0 compensé K0/K*_aut(γ)
constant) casse l'anti-corrélation, ET cette rupture est ROBUSTE À LA
TAILLE du système (λ∈{10,30,100}, méthodologie M4B/§5, population variant
sur plus d'un ordre de grandeur).

### Ce que cela signifie pour D2 (§1 du prompt)

**Le levier existe.** Sur l'espace testé, `target_rule` seul (le canal
multiplicatif, premier run pilote §4) est D2-négatif, mais `gamma_comp`
(un changement de γ COMBINÉ à une compensation de capital, testé dans le
même espace déjà couvert par M4.2B, γ∈{1/3,0.4,0.6,2/3}) est D2-POSITIF
et D3-confirmé. C'est le premier résultat de tout le programme M4.2B→M4.3
(37+28=65 cellules testées au total) qui casse l'anti-corrélation avec
cette solidité statistique. **Ce n'est PAS un nouveau mécanisme à
construire** — γ et la compensation K0/K*_aut(γ) sont DÉJÀ dans le moteur
tel quel (aucune ablation nécessaire pour CE résultat spécifique), la
question qui reste est de savoir si la région favorable s'étend au-delà
des deux points déjà mesurés (γ=0,6 et 2/3) ou si γ=2/3 est déjà proche
d'un optimum/plateau.

### Décision d'ablation (§4/§9) — éléments mis à jour, TOUJOURS EN ATTENTE

Le candidat était encore incertain (réserve de taille) lors du premier
énoncé de cette décision en attente (§16). **Il ne l'est plus : D3 vient
de le confirmer robuste à la taille avec une marge statistique large.**
Ça renforce l'argument « pour » une exploration plus poussée de cet axe
(cartographier plus finement γ∈[0,6 ; 1] compensé — PAS une ablation au
sens du §4, un prolongement direct de D1 déjà prescrit) et rend la
question de l'ablation proprement dite (famille de moyennes de puissance
pour la règle de taux, note manuscrite du §4) plus intéressante si le
mécanisme actuel plafonne. **Toujours pas tranché ici** — c'est
explicitement votre décision (§9). Ajouté à la liste des décisions en
attente : un affinement du balayage γ_comp (ex. γ∈{0,7 ; 0,8 ; 0,9}
compensé, coût ~identique à D1 par cellule) serait un prolongement
naturel et peu coûteux, mais représente un nouvel engagement de calcul
non explicitement couvert par le plan D1 initial (§9 : « toute décision
qui engagerait un budget de calcul significatif sur une direction non
couverte par ce prompt » — le plan D1 listait γ∈{1/3,0.4,0.6,2/3},
pas au-delà) → **je ne le lance pas seul, je le signale comme option.**

## 22. Robustesse temporelle (§10 : « niveau de preuve exact... robustesse temporelle ») — vérifiée, tient

Distincte de la reproductibilité inter-graines déjà établie. Les
instantanés bruts nécessaires à `dagum_c` sont supprimés après analyse
(nettoyage disque) — seul `b` (avalanches.csv, conservé) est re-testable
sans re-simuler. `scripts/temporal_robustness_check.py` : découpe la
fenêtre post-convergence de chaque run (baseline et gamma_comp_0.6667,
λ=30, 3 graines chacun) en deux moitiés temporelles, recalcule `b` sur
chacune séparément.

| | 1ère moitié | 2ème moitié |
|---|---|---|
| baseline | 0,7860±0,0005 | 0,7846±0,0005 |
| gamma_comp_0.6667 | 0,8049±0,0010 | 0,8024±0,0025 |
| **écart** | **+0,0189** | **+0,0178** |

**Écart stable dans le bruit entre les deux moitiés** (+0,0189 vs
+0,0178, à comparer à l'écart inter-graines déjà mesuré ±0,0007-0,0028) —
pas un artefact d'une sous-période particulière de la fenêtre
post-convergence. Complète la preuve D3 (robustesse de taille) par une
robustesse temporelle indépendante, avec l'outillage déjà écrit, sans
calcul supplémentaire.

**État des livrables du §10 du prompt** : plan cartographié + figure
(fait), verdict D2 explicite avec niveau de preuve (fait — inter-graines
+ taille + temporel, tous convergents), verdict D3 (fait, positif),
rapport autonome (fait, `report/rapport_final.md`), journal chronologique
(ce fichier), points d'étape quotidiens (faits à chaque réveil cron).
**Seule pièce non close : la décision d'ablation — explicitement réservée
à la supervision (§9), documentée §21, pas tranchée.** C'est la seule
chose qui reste, à ma connaissance, entre ce programme et la clôture
complète du prompt de référence.

## 23. Point d'étape (2026-08-08, 20h47, réveil cron) — programme au point mort en attendant la décision

Aucune activité de calcul en cours (seul `mem_guard` tourne). Aucune
nouvelle donnée depuis le dernier cycle. Ajouté une figure dédiée au
verdict D3 (`report/figures/d3_size_robustness.png` — Δc et Δb contre λ,
échelle log, deux courbes visuellement plates) : travail de présentation
à coût nul (aucun nouveau calcul, données déjà en main), pas une
tentative de générer du travail artificiellement.

**Le programme est réellement au point mort** : tout ce qui pouvait être
avancé sans nouveau calcul ni décision de supervision a été fait. Les
seules directions qui restent (affiner le balayage γ_comp, tester une
famille de moyennes de puissance) engagent toutes un budget de calcul
significatif sur une direction non explicitement couverte par le plan
D1 initial — exactement ce que le §9 réserve à la supervision. Continuer
à « chercher du travail » au-delà de ce point risquerait de produire du
bruit (recalculs redondants, sur-interprétation de signaux faibles) plutôt
que du signal. Les prochains cycles de réveil resteront courts (vérifier
qu'aucune donnée nouvelle n'est apparue) tant qu'aucune décision n'est
prise, conformément à la consigne de l'utilisateur (« ne t'arrêtes que
quand l'intégralité du prompt initial est répondu »).


## 24. Rapport LaTeX + figures de vérification + gap simulation_lab découvert et corrigé (2026-08-09)

Demandes utilisateur successives, hors calcul D1/D2/D3 (déjà clos §22) :
(a) pousser le rapport sur Git avec tout le travail + la question
d'ablation + ce qu'il faut de l'utilisateur pour continuer — fait,
`report/rapport_final.md` étendu et poussé (commit `73bf03eb`) ; (b)
figures de vérification sur données réelles (régressions/tests, pas
seulement les paramètres finaux dans une table) + PDF LaTeX — en cours ;
(c) question explicite : toutes les simulations ont-elles leurs
graphiques générés, accessibles par `simulation_lab`, triés par cellule ?

**Réponse à (c) : non**, et le diagnostic a révélé un écart de processus
plus profond qu'un simple retard d'import. §8 du prompt demandait de
réutiliser `simulation_lab` et ses 28 figures validées telles quelles ;
au lieu de ça, `campaign_d1.py`/`d3_size_check.py` ont construit un
pipeline d'analyse maison (dagum_c + b uniquement) et leur nettoyage
post-analyse (`_cleanup_raw`) supprime `snapshots/` juste après l'analyse
légère — donc AVANT toute génération de figures possible. Aucun
adaptateur `m4_3_credit_soc` n'existait sous
`modeles-systeme-physicoeconomique/`, et `simulation_lab_data/` n'avait
aucune entrée M4.3.

Proposition initiale (périmètre réduit : adaptateur + seulement 3
cellules centrales relancées) **explicitement rejetée par l'utilisateur**
: « re-launch every simulations. these graphics are PARAMOUNT to the
research. » — instruction de relancer l'intégralité des simulations, pas
un sous-ensemble.

**Investigation avant relance (mesures réelles, pas d'hypothèse)** :
- `individual_series.csv.gz` n'est utilisé QUE par `entity_lives()` dans
  `reporting.py` (1 des 9 recettes de `generate_run`, protégée par
  try/except). Vérification décisive : **toute la campagne M4.2B**
  (`results/campaign/*/seed*/config.json`, ~90 runs) a
  `individual_every: 0` — la convention scientifique déjà établie et
  validée de ce projet ne peuple JAMAIS cette table pour les runs de
  campagne. `individual_every=0` n'est donc pas une simplification
  introduite par M4.3, c'est la norme du projet. Aucun changement requis
  sur ce point.
- `loan_events.csv.gz` (≈65 % du poids d'un run — 845 Mo/941 Mo à
  T=8000) **n'est référencé nulle part dans `reporting.py`** (grep, 0
  résultat) : aucune des 28 figures n'en a besoin. Reste supprimable
  après figures, comme avant.
- Seul `snapshots/` (327 Mo/run) est effectivement nécessaire à la
  majorité des recettes (macro, temporel, séries, inégalité, réseau,
  vie instantanée, soc — 7 des 9). `network_figure` n'a besoin que de
  `final_loans.csv` (déjà conservé), pas de `loan_events.csv.gz`.
- **Test d'import réel** (pas supposé) : `reporting.generate_run()`
  exécuté tel quel (aucune modification de code) sur
  `results/pilot/control_geometric/seed0` (run M4.3 réel, T=8000,
  toujours muni de ses instantanés) → 22 PNG + figures GIF, **0 erreur**,
  259 s. Confirme que le pipeline M4.2B est directement réutilisable sur
  la structure de dossier M4.3 sans adaptation de code (moteurs
  byte-identiques, cf. parité §engine).

**Conséquence sur l'arithmétique disque** : le changement nécessaire est
minimal — ne plus supprimer `snapshots/` avant d'avoir appelé
`generate_run()`, tout le reste du nettoyage (`loan_events.csv.gz`,
`checkpoint.pkl`) reste inchangé. Empreinte finale par run après figures
: ~40 Mo (déjà conservé) + ~30-50 Mo de figures ≈ 90 Mo, pas les 1,3-2 Go
initialement redoutés. Pic transitoire pendant le traitement (6 workers
× ~941 Mo avant nettoyage) ≈ 5,6 Go, trivial sur 91 Go libres.

**Correctifs appliqués** :
1. Adaptateur créé : `modeles-systeme-physicoeconomique/m4_3_credit_soc/{model.py,figures.py,reporting.py}`
   (copie de m4_2b, `reporting.py`/`figures.py` inchangés — confirmés
   agnostiques au moteur par le test d'import ci-dessus ; `model.py`
   adapté : `model_id="m4_3_credit_soc"`, `ENGINE_ROOT`, description).
   `simulation_lab/settings.py::ACTIVE_MODEL_IDS` mis à jour pour inclure
   `m4_3_credit_soc` (vérifié via `python3 -m simulation_lab.cli
   list-models` : apparaît, `archived=false`).
2. `scripts/campaign_relaunch_figures.py` (nouveau) : relance les 96
   runs D1(84)+D3(12) déjà mesurés, réutilise `campaign_d1._run_and_analyze`
   SANS duplication (monkey-patch de `campaign_d1._cleanup_raw` pour
   insérer `reporting.generate_run()` juste avant le nettoyage réel —
   même patron de bascule `cd.RESULTS` que `d3_size_check.py`). Logique
   de reprise : si `figures/macro_overview.png` absent, force un
   re-run complet même si `analysis.json` existe déjà en `status=ok`
   (le raw a été supprimé au premier passage, rien à réutiliser sans
   re-simuler).
3. `scripts/generate_figures_existing.py` (nouveau, pool séparé sans
   garde-fous mémoire — aucune simulation, seulement du calcul de
   figures CPU) : génère les figures pour les 6 runs pilotes qui ont
   encore leurs instantanés bruts (baseline_arithmetic ×3,
   control_geometric ×2 restants, gamma_comp_0.6667_verif ×1).

**Lancé sous les six garde-fous** (préflight disque, verrou mono-pool,
plafond mémoire réel, PID enregistrés, checkpoint) : `tmux` session
`m43_relaunch`, 96 runs, 6 workers, `results/relaunch_figures.log`. Coût
estimé : durée D1 initiale + ~5 min de génération de figures par run en
plus (mesuré : 259 s sur control_geometric) — plusieurs heures à ~1-2
jours de calcul mur, comparable à l'ampleur déjà engagée sur ce
programme. `mem_guard` (tmux `m43_memguard`) tourne sans interruption
depuis le 2026-08-07.

**gamma_comp_0.6667_verif** (run de vérification lancé plus tôt pour
récupérer les instantanés du candidat central) terminé avec succès
pendant cette investigation (status ok, T=8000). Figures FOPDT
(τ=436,6, R²=0,973) et queue dagum (c=3,417) générées vers
`report/figures/verification/` — débloque le placeholder du PDF LaTeX.

**Ce qui reste ouvert** : la décision d'ablation (§9, cf. §21-22) —
toujours non tranchée, toujours hors de ma décision. Le PDF LaTeX
(`report/rapport_final.tex`) doit encore être mis à jour avec les
figures gamma_comp_0.6667 et recompilé/poussé. Le rapport final devra
être mis à jour pour refléter que TOUTES les simulations D1/D3 ont
maintenant (une fois `m43_relaunch` terminé) leurs 28 figures
accessibles via `simulation_lab`, triées par cellule
(`results/{d1,d3_size}/<cellule>/seed<N>/figures/`).


## 25. Correctif bins adaptatifs (demande utilisateur explicite) + run de démonstration complet (2026-08-09)

Demande : « Every histogram MUST have bins of adaptative size (such as in
cascade_rank_size.pdf). To be fixed before generating : *_evolution And
*_temporal_mean. » — plus faire tourner une simulation, générer TOUTES les
figures d'un run M4.2B (y compris les vies individuelles) et nettoyer le
lourd ensuite.

**Bug confirmé et corrigé (2 occurrences), `modeles-systeme-physicoeconomique/m4_3_credit_soc/reporting.py`** :
1. `temporal_density()` (alimente `*_evolution.gif`/`*_temporal_mean.png`,
   7 champs × 2 sorties) : `np.logspace(min, max, bins=32)` — bins de
   LARGEUR fixe en log, pas adaptés à la densité réelle. Comparaison
   avant/après sur `control_geometric/seed0` : la version originale
   produit une courbe en dents de scie sur 2-3 ordres de grandeur (bins
   pauvres en effectif → bruit de comptage dominant) ; la version
   corrigée (bornes aux quantiles, factorisées dans `_quantile_edges()`,
   même famille que `adaptive_hist()`/`cascades_rank_size.png` cité en
   référence) donne une courbe lisse et unimodale.
2. `_coarse_log_edges()` dans `network_figure()` (histogrammes de
   puissance prêtée/empruntée en marge de `loan_network_final.png`) :
   même défaut (nombre de bins adaptatif mais bornes `np.logspace`
   uniformes). Remplacé par un appel direct à `_quantile_edges()`,
   fonction locale supprimée.

Audit complet des autres histogrammes du module (`grep` sur
`np.histogram`/`.hist(`/`bins=`) : `instantaneous_life()` était déjà
correcte (bornes aux quantiles) ; les `bins="auto"` (degré réseau, âge au
décès) et les `hexbin(..., bins="log")` (density plots 2D) ne sont pas
concernés par ce défaut (mécanismes différents, pas de bins uniformes sur
grande dynamique) — laissés inchangés.

**Ce fichier n'est donc plus une copie strictement identique de l'original
M4.2B** (cf. docstring mise à jour) — correctif non reporté sur
`m4_2b_credit_soc/reporting.py` (hors périmètre, CLAUDE.md : ne pas
modifier un autre modèle sans accord explicite).

**Conséquence sur la relance en cours (§24)** : le pool des 96 runs D1+D3
avait été lancé AVANT ce correctif et n'avait encore terminé aucun run
(vérifié : log ne montrait que les 3 lignes de démarrage) — arrêté
proprement (SIGTERM puis SIGKILL des workers orphelins, verrou et
registre de workers nettoyés, vérifiés libres) pour ne pas générer 96×7
figures buguées qu'il aurait fallu regénérer. Relancé après le correctif,
coût nul (rien n'était complété).

**Run de démonstration** : `results/pilot/baseline_showcase/seed0`
(cellule baseline, T=8000, `individual_every=1` — première fois dans ce
programme, cf. §24 où toute la convention était `individual_every=0`).
33 min de calcul, 1,5 Go brut (`individual_series.csv.gz` seul : 791 Mo,
conforme à l'estimation d'ordre de grandeur de l'analyse préalable).
`reporting.generate_run()` : 32 PNG, 0 erreur, ~7 min — y compris
`entity_lives_overview.png` + 10 figures détail par entité
(`detail_vie_entites/entity_*.png`), impossibles jusqu'ici faute
d'`individual_series` peuplé. Nettoyage post-figures : 1,6 Go → 53 Mo
(loan_events.csv.gz, checkpoint.pkl, snapshots/, individual_series.csv.gz
supprimés ; figures/ + CSV légers conservés).

## 26. Point d'étape (2026-08-09, cycle cron) — rapport LaTeX poussé, relance 96 runs en cours

`rapport_final.tex`/`.pdf` complétés (placeholder gamma_comp_0.6667 rempli
avec les figures de vérification déjà générées §24), section §13/9 sur le
complément simulation_lab/bins/run de démonstration ajoutée aux deux
rapports (`.md` et `.tex`). Commit `222f7fd2` poussé sur `main`
(pré-commit + pré-push OK). Périmètre Git inchangé : `report/`,
`JOURNAL.md`, `prompts/` uniquement — `simulation_lab/settings.py` a des
changements PRÉ-EXISTANTS non liés à ce travail (fonction
`model_is_archived()`, correctifs de chemin `LEGACY_RESULT_SOURCES`,
présents avant toute intervention de ce programme sur ce fichier) laissés
tels quels, non commités, pour ne pas embarquer du travail non revu dans
ce commit.

Relance des 96 runs D1+D3 (§24-25) en cours : 12/96 terminés au moment de
ce point d'étape, tous `status=ok`, aucun incident mémoire/disque,
`mem_guard` actif sans interruption, pas de HALT. Progression normale
(cellules plus grandes = plus lentes, cf. incidents K0_2000/λ=100 déjà
rencontrés et résolus en §17/§19 pour la même famille de cellules).

**Rien de nouveau côté verdict scientifique** (D2/D3 clos §21-22,
inchangés). **Décision d'ablation toujours en attente de supervision**
(§21-22, rappelée aussi dans les deux rapports) — pas d'action unilatérale
prise sur ce point, conformément à la consigne. Prochain cycle : vérifier
l'avancement de la relance 96 runs, et si elle est terminée, régénérer/
compléter les livrables qui en dépendent (aucun livrable §10 du prompt ne
dépend directement des figures simulation_lab — c'est un complément
d'outillage demandé séparément, pas un critère de clôture du prompt).

## 27. Signalement utilisateur : « impossible de voir/lancer des simulations M4.3 dans simulation_lab » — diagnostiqué et corrigé (2026-08-09)

Deux causes distinctes, diagnostiquées séparément (pas supposées) :

**(1) Runs invisibles.** Confirmé réel : `run_pilot.py`/
`campaign_relaunch_figures.py` écrivent directement dans
`m4_3_credit_soc/results/`, sans jamais passer par
`RunStorage.create_run()`/`finalize_run()` — `simulation_lab_data/runs/`
n'a donc aucune trace de ces runs. Le seul mécanisme de découverte
externe existant (`RunStorage.list_external_runs()`, cherche un fichier
`meta.json`) est conçu pour d'anciennes lignées (claude3-v2, Modèle sans
banque) avec un schéma différent — pas réutilisable sans toucher du code
partagé (`storage.py`, hors périmètre M4.3).

Correctif : `scripts/import_to_simulation_lab.py` (nouveau, idempotent) —
pour chaque run M4.3 terminé (figures déjà générées), crée un SYMLINK
`simulation_lab_data/runs/<id>` → dossier réel sous
`m4_3_credit_soc/results/`, et y écrit un `run.json` au format managé
standard. Vérifié avant d'adopter le lien symbolique (pas une copie,
zéro duplication disque) : `delete_run()`/`empty_trash()` opèrent par
`shutil.move`/suppression au niveau du lien top-level, jamais de descente
récursive destructive dans la cible — testé en pratique (déplacé vers la
corbeille puis vidé un run importé, données réelles
`results/d1/baseline/seed0/figures/macro_overview.png` intactes après).
38 runs déjà enregistrés (D1 en cours + phase pilote), visibles et
étiquetés par cellule (`D1/<cellule>/seed<N>`) via `list-runs`/le GUI.
Le script sera relancé (idempotent) au fur et à mesure que la relance des
96 runs (§24-26) avance.

**(2) Lancement refusé/impossible.** Testé directement (CLI + API HTTP du
GUI, un serveur GUI FRAIS, lancé après vérification qu'aucun processus
GUI ne tournait déjà) : un lancement M4.3 réel a fonctionné du premier
coup (`model_id`, paramètres, exécution, figures --- tout correct).
Cause la plus probable du signalement initial : un serveur GUI déjà en
cours d'exécution AVANT la création de l'adaptateur M4.3 (§24), dont le
`ModelRegistry` n'est chargé qu'une fois au démarrage (`reload()` dans
`__init__`) --- un serveur resté actif depuis avant n'aurait aucune
connaissance du modèle `m4_3_credit_soc`, expliquant « je ne peux pas en
lancer » alors que d'autres modèles (M4B, lancé par l'utilisateur le
2026-08-09 vers 16h20) continuaient de fonctionner dans cette même
session. Pas de preuve définitive (le serveur en question, s'il existait,
avait déjà cessé de tourner au moment du diagnostic), mais cohérent avec
toutes les observations.

**(3) Trou de sécurité trouvé PENDANT ce diagnostic, corrigé aussi :**
`model.py::run()` (le point d'entrée que le GUI/CLI utilise pour lancer
une simulation) n'avait AUCUN garde-fou --- ni préflight disque, ni verrou
mono-pool, ni plafond mémoire, ni enregistrement PID auprès de
`mem_guard`. Un lancement GUI pendant que le pool de 96 runs tourne (état
réel actuel) se serait exécuté sans AUCUNE coordination mémoire avec ce
pool --- exactement le scénario que le verrou mono-pool existe pour
empêcher (JOURNAL.md M4.2B §15, cité dans `pool_lock.py`). Corrigé :
`run()` renommé `_run_inner()`, nouveau `run()` fin enveloppant
`require_disk_preflight`/`PoolLock`/`register_workers`/plafond
`RLIMIT_AS` --- même patron que `run_pilot.py`, verrou PARTAGÉ (même
fichier `results/.pool.lock`) donc mutuellement exclusif avec les
lancements par script. Vérifié par un test réel : un lancement GUI
pendant que le pool des 96 runs tenait le verrou a échoué immédiatement
avec le message d'erreur attendu (`PoolAlreadyRunningError`), pas de
plantage silencieux ni de contention mémoire.

**Conséquence pour l'utilisateur, à communiquer clairement** : avec ce
correctif, lancer une NOUVELLE simulation M4.3 via le GUI/CLI est
désormais REFUSÉ tant que le pool de 96 runs tourne (comportement
intentionnel, pas un nouveau bug) --- c'est le prix du même garde-fou
mémoire que le reste du programme. Serveur GUI relancé proprement (tmux
`simlab_gui`, port 8777) pour que l'utilisateur reparte d'un état propre.

## 28. Point d'étape (2026-08-09, cycle cron) — relance à mi-parcours, importeur suivi

Relance 96 runs : 45/96 terminés, tous `status=ok`, disque 77 Go libres
(consommation stable, ~1,2 Go/run en moyenne sur les runs traités jusqu'ici,
cohérent avec l'estimation §24), `mem_guard` actif, pas de HALT.
`gamma_comp_0.6667` (cellule centrale du résultat D2/D3) a terminé ses 3
graines --- figure `entity_size_histo_temporal_mean.png` inspectée
visuellement : courbe lisse et unimodale, correctif bins (§25) confirmé
opérant sur cette cellule aussi.

`scripts/import_to_simulation_lab.py` relancé (idempotent) : 50 runs
maintenant enregistrés et visibles dans `simulation_lab` (était 38 au
cycle précédent), continuera d'être relancé à chaque cycle tant que la
relance progresse.

Rien de nouveau côté verdict scientifique (clos §21-22). Décision
d'ablation toujours en attente de supervision --- aucune action
unilatérale. Tous les livrables §10 du prompt sont répondus à l'exception
de cette décision, qui n'est pas de mon ressort. Prochain cycle :
vérifier l'avancement de la relance, continuer à synchroniser
l'importeur, sans autre action nécessaire tant que la décision d'ablation
n'arrive pas.

## 29. Point d'étape (2026-08-10, cycle cron) — K0_2000 réplique l'échec mémoire connu, retry préparé

Relance 96 runs : 90/96 traités (K0_2000 exclu, cf. ci-dessous), tous les
autres `status=ok`. Les 6 derniers (`baseline_lam100`,
`gamma_comp_0.6667_lam100`, les cellules λ=100 les plus lourdes de la
grille) sont en cours, lents mais sans incident (disque 67 Go libres,
`mem_guard` actif, pas de HALT) --- normal, déjà observé pour ces tailles.

`K0_2000` a échoué sur ses 3 graines avec le même `MemoryError` au
checkpoint déjà rencontré et résolu une première fois lors de la
campagne D1 initiale (JOURNAL.md §17/19) --- cellule intrinsèquement plus
lourde que le plafond mémoire calculé pour 6 workers. Pas une régression
du correctif bins/figures : root cause identique, déjà documentée.
`scripts/retry_k0_2000_with_figures.py` écrit (2 workers, même
monkey-patch génération-figures-avant-nettoyage que
`campaign_relaunch_figures.py` --- **pas** une réutilisation telle quelle
de l'ancien `retry_k0_2000.py`, qui daterait le nettoyage avant les
figures et reproduirait le problème initial de ce chantier). Prêt à
lancer dès que le pool principal libère le verrou mono-pool (les deux ne
peuvent pas tourner en même temps par construction, §7.3).

Rien de nouveau côté verdict scientifique ni côté décision d'ablation
(toujours en attente de supervision, aucune action unilatérale). Prochain
cycle : si le pool principal est terminé, lancer le retry K0_2000, puis
resynchroniser l'importeur simulation_lab (§27) une dernière fois.

## 30. Relance des 96 runs terminée (90/96 ok), retry combiné K0_2000 + gamma_comp_0.6667_lam100 lancé (2026-08-10)

`campaign_relaunch_figures.py` (§24-26) terminé : 96/96 runs traités, 90
`status=ok`, 6 échecs `MemoryError` au checkpoint --- `K0_2000` (D1, 3/3
graines) et `gamma_comp_0.6667_lam100` (D3, 3/3 graines), toutes deux DÉJÀ
rencontrées et résolues lors de la campagne D1/D3 initiale par la même
méthode (JOURNAL.md §17/19) --- pas une régression du correctif
bins/figures, root cause identique et déjà documentée (cellules
intrinsèquement plus lourdes que le plafond calculé pour 6 workers).

`scripts/retry_failed_cells.py` (nouveau, combine les deux cellules en un
seul passage 2 workers au lieu de deux retries séquentiels) lancé sous
les six garde-fous : préflight disque OK, verrou mono-pool tenu, plafond
13,52 Go/worker (cohérent avec les 13,56 Go/worker qui avaient déjà
résolu ce même problème). Réutilise `campaign_relaunch_figures` tel quel
(le monkey-patch génération-figures-avant-nettoyage s'applique à
l'import, pas dupliqué).

`scripts/import_to_simulation_lab.py` resynchronisé : 98/104 runs M4.3
maintenant visibles dans `simulation_lab` (96 relance + 7 pilote + 1
démonstration, moins les 6 en cours de reprise). Les 6 derniers seront
importés dès que le retry aboutit.

Rien de nouveau côté verdict scientifique ni décision d'ablation (toujours
en attente de supervision). Prochain cycle : vérifier l'issue du retry,
resynchroniser l'importeur une dernière fois (104/104 attendu), et à ce
stade tous les travaux d'outillage simulation_lab demandés seront clos ---
il ne restera que la décision d'ablation comme point ouvert de tout le
programme M4.3.

## 31. Point d'étape (2026-08-10, cycle cron) — retry en cours, 2/6 déjà ok

`retry_failed_cells.py` : K0_2000 seed0/seed1 terminés avec succès
(`status=ok`) sur le plafond élargi (13,52 Go/worker, 2 workers) --- confirme
que le retry fonctionne comme la première fois (§17/19). 4 runs restants
(K0_2000 seed2 + gamma_comp_0.6667_lam100 ×3), aucun incident, disque
82 Go libres, `mem_guard` actif, pas de HALT. Importeur resynchronisé :
100/104 runs M4.3 visibles dans `simulation_lab`.

Rien de nouveau côté science ni décision d'ablation (en attente). Prochain
cycle : vérifier la fin du retry, resynchroniser l'importeur (104/104
attendu) --- dernier point d'outillage avant que tout le travail demandé
sur `simulation_lab` soit clos.