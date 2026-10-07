# JOURNAL — M4.2B (démarré 2026-07-30)

Cahier des charges d'autorité : `prompts/PROMPT_M4_2B.md`. Ce journal
consigne la chronologie réelle, y compris les hypothèses de départ
corrigées en cours de route (§18 du prompt : ne pas effacer les erreurs
intermédiaires).

## 1. Audit et implémentation (2026-07-30, matin)

Lecture complète de M4.2 (`modeles/m4_2_credit_soc/m4_2/model.py`, `io.py`, tests,
`scripts/lib_metrics.py`, `scripts/lib_screening.py`), de l'adaptateur
Simulation Lab M4.2 et de sa batterie de 28 figures (`reporting.py`,
générique, ne connaît pas le moteur). Découverte d'un outillage déjà
existant et directement réutilisable pour l'objectif A, hors de la lignée
M4 : `recherche/analyse_distributions_taille_revenu/scripts/families.py`
(échelle de 13 familles continues, MLE+AIC/BIC, dont GB2, DPLN via mélange
lognormale+Pareto) et `tail_test.py` (test de queue continu façon
Clauset–Shalizi–Newman, MLE+scan de seuil par KS).

Moteur M4.2B construit par fork de `m4_2/model.py` :
- séparation stricte `_pair_rate` (taux, INCHANGÉ) / `_pair_principal`
  (cible arithmétique `(K_ℓ-K_b)/2` directe, ou géométrique = formule M4.2
  intacte, sélectionnée par `Config.target_rule`) ;
- `eta_rho_beta` : famille η_{ρ,β}(N)=ρ·N_ref·(N/N_ref)^β, β=1 court-circuite
  la reparamétrisation pour reproduire η(N)=N bit-à-bit ;
- table `loan_events` (nouvelle) : r, q, rq, rq/K_b', rq/F_γ(K_b') par
  transaction réussie du marché — mesure demandée au §3, sans effet sur la
  dynamique.

**Parité avec M4.2 vérifiée à 0,000e+00 d'écart flottant** (pas seulement en
tolérance 1e-9) sur deux régimes M4.2 et un régime baseline M4.2B, avec
`target_rule="geometric", rho=1, eta_beta=1` : le refactor n'a introduit
aucune dérive. 31 tests unitaires (engine, arithmétique/géométrique sur
grille, parité, outils statistiques) tous verts.

Outils statistiques copiés dans `scripts/` avec provenance : `lib_metrics.py`,
`lib_screening.py` (M4.2, inchangés), `families.py` (bug de chemin
`_REPO_ROOT` corrigé — 3 `dirname` pas 4, un niveau de moins que l'original),
`tail_test.py`. **Piège de convention détecté et corrigé** (`scripts/
pareto_convention.py`, nouveau) : `families.fit_pareto_1p` renvoie
l'exposant CCDF κ (convention scipy `pareto.b`), `tail_test.fit_powerlaw_xmin`
renvoie l'exposant de densité α=κ+1 — même nom de champ `"alpha"` pour deux
grandeurs différentes. Auto-test sur Pareto synthétique : les deux outils,
une fois convertis, s'accordent à mieux que 0,02 près sur α réel.

Nouveau module `scripts/interest_income.py` : masse en zéro explicite,
seuil d'effectif minimal explicite (jamais hérité silencieusement),
décomposition Var(log I) = Var(log deg_out) + Var(log mean_rq) +
2·Cov(...) (identité exacte, §9), ajustement multi-familles + queue + test
de Vuong exponentielle-vs-Pareto (famille explicitement demandée §10 et
absente des outils copiés), ajustement PAR SNAPSHOT (§10 : l'unité de
réplication est le snapshot).

## 2. Trois calculs analytiques avant tout run (conseillés par relecture)

1. **Temps de relaxation autarcique à δ=0,01** : K*_aut(γ=0,5)=9801 (vs 361 à
   δ=0,05 pour M4.2). 584 pas pour atteindre 90 % de K*_aut, 1048 pas pour
   99 %. **Hypothèse de départ, infirmée empiriquement en §3** : ce n'était
   pas la bonne horloge pour fixer T/burn-in.
2. Grille (K_ℓ,K_b) : confirmé analytiquement et numériquement
   q_A/q_geo = (1+√(K_ℓ/K_b))/2, **sans borne** quand K_ℓ/K_b croît (10,4×
   pour un couple K_ℓ=9801/K_b=25).
3. **Pathologie prédite** (§3) : un newborn K0=25 face à une prêteuse proche
   de K*_aut donne un service c=rq tel que c/F_γ(K_b')≈1,57 — supérieur à la
   production de l'emprunteuse sur CE pas. Vérifié dans les tests
   (`test_loan_events_diagnostics_are_self_consistent`).

## 3. Pilote baseline T=3000 (γ=0,5, δ=0,01, σ=0,01, K0=25, η(N)=N,
   arithmétique, seed=0) — et une hypothèse corrigée en cours de route

Coût mesuré : ~0,12-0,2 s/pas selon densité du réseau (dominé par la boucle
de paiement des intérêts, O(n_loans)) ; T=3000 complet en 575 s.

**Erreur méthodologique n°1 (corrigée)** : l'hypothèse initiale (issue du
calcul autarcique §2.1) était qu'il fallait T≈8000-10000 pour atteindre la
stationnarité, par analogie avec le temps de relaxation individuel. **Faux** :
la mortalité par cascade régule la population bien avant qu'aucune entité
n'approche K*_aut. Diagnostic empirique (`lib_metrics.window_series_metrics`,
comparaison demi-fenêtres) : population stationnaire dès t≈375-750
(pop moyenne 1134-1140, cv=0,034, dérive relative <1 % entre les deux
moitiés de fenêtre). T=1000 (burn-in 375) suffit pour l'exploration ;
T=3000 réservé aux cellules de confirmation.

Faits observés sur ce run :
- **0 défaut de liquidité sur tout le run** (`defaults=0`, `roots_liquidity=0`
  cumulés sur T=400 puis confirmé structurellement) : 100 % des faillites
  sont des racines d'insolvabilité (valeur nette négative), jamais une
  incapacité de service. Réponse nette à la question de pathologie du §3 :
  le service (rq) reste petit devant le STOCK de capital (K), donc jamais
  bloquant ; la fragilité vient du levier (K_debt/NW extrême pour un
  newborn) érodé par les chocs, pas de l'incapacité à payer un flux.
- Réseau très dense : n_loans≈34500-39000 pour pop≈1100-1200 (degré moyen
  ≈31-34), `merge_share`≈2,8 % (quasi aucune fusion — la quasi-totalité des
  transactions sont de nouvelles arêtes).
- `branching_ratio`(fenêtre stationnaire)=0,786 — bien au-dessus du 0,30
  épinglé institutionnellement par M4.2 à sa propre baseline.

**Erreur méthodologique n°2 (corrigée par un run de contrôle, voir §5)** :
première interprétation (fausse) — attribuer ce branching élevé et le
Gini(K) très bas (0,054) à l'institution arithmétique elle-même
(« l'égalisation crée un réseau dense et fragile »). **Infirmée** par le
contrôle géométrique (§5) : les deux grandeurs sont quasiment identiques
sous `target_rule="geometric"` à la même baseline lente (δ=0,01,σ=0,01).
La cause réelle est la baseline δ/σ (relaxation lente + chocs faibles +
η(N)=N), pas la règle de principal.

## 4. Objectif A à la baseline : négatif, avec mécanisme identifié

Ajustement `interest_income.fit_income_distribution` sur 46 snapshots de la
fenêtre stationnaire (t∈[750,3000]) :
- p0 = 0,089±0,008 (masse en zéro stable, faible) ;
- α̂_density (seuil optimal KS) = 3,80±0,18 (serré entre snapshots) ;
- **instabilité de seuil systématique** : à seuil moitié, α̂ retombe à
  2,52±0,12 sur les 46 snapshots — écart bien supérieur à ce qu'une vraie
  loi de Pareto stable tolérerait (§11 critère 6 : échoue) ;
- test de Vuong tronquée-Pareto-vs-exponentielle dans la queue : **46/46
  snapshots favorisent la loi de puissance sur l'exponentielle** (z=3,15
  ±0,87) — la queue haute N'EST PAS un simple prolongement exponentiel ;
- comparaison de familles sur tout le support (AIC) : **GB2 (4 paramètres)
  gagne systématiquement**, devant lognorm_mix_5p, gengamma_3p ; le
  raccord explicite lognormale+Pareto (`lognorm_pareto_mix_5p`) est
  SYSTÉMATIQUEMENT moins bon malgré le même nombre de paramètres ; Pareto
  pure (sur tout le support) est très largement rejetée (ΔAIC>2900).
- décomposition Var(log I) = Var(log deg_out) + Var(log mean_rq) +
  2·Cov : **77 % de la variance vient du nombre de prêts (deg_out), 23 %
  du rq moyen par prêt**, covariance négligeable.
- mécanisme causal : spearman(revenu, âge)≈0,89 stable, R²(revenu~âge
  linéaire)≈0,72 : le revenu croît avec l'âge via l'accumulation du nombre
  de contrats émis. L'âge lui-même rejette (KS, p≈0 partout) une loi
  exactement exponentielle mais reste très dispersé (std/mean≈2,1),
  cohérent avec une mortalité par cascades épisodiques plutôt qu'à taux
  constant.
- Gini(K) final = 0,054 : **le capital est presque parfaitement homogénéisé**
  à la baseline — peu de matière première pour un rq hétérogène.

**Verdict honnête (§11)** : pas de régime Pareto robuste pour les intérêts
reçus à la baseline. Le corps est mieux décrit par GB2 ; la queue haute est
plus lourde qu'une exponentielle mais son exposant n'est pas stable au
seuil — c'est un artefact de coupure/courbure, pas un contrôle de queue.

## 5. Contrôle géométrique (2026-07-30, après-midi)

Un seul run, mêmes paramètres que la baseline sauf `target_rule="geometric"`,
T=1000 : branching=0,756 (vs 0,787 en arithmétique — quasi identique),
Gini(K)=0,053 (vs 0,053 — identique), mais **α̂(seuil KS)=2,94 (contre 3,86
en arithmétique) : le géométrique donne une queue plus lourde**, avec un
`share_from_deg_out` encore plus élevé (0,872 contre ~0,79). Réponse
directe et contre-intuitive à la question §21-Q1 : le changement
constitutif de M4.2B (cible arithmétique) rend l'objectif A **plus
difficile**, pas plus facile — l'égalisation exacte assèche l'hétérogénéité
plus efficacement que la cible géométrique (qui ne bouge que le bras de
l'emprunteuse).

## 6. Balayage σ ∈ {0,01; 0,03; 0,05; 0,10} (2 graines, T=1000, arithmétique)

σ agit dans le sens prédit sur les variables intermédiaires : Gini(K)
0,053→0,09 (2 graines à σ=0,10 : 0,080 et 0,103), `share_from_deg_out`
0,79→0,73 — mais **α̂(seuil KS) augmente (s'alourdit) avec σ : 3,86→5,03**,
tandis que α̂(seuil/2) reste quasi constant (≈2,6-2,8) sur toute la plage.
Interprétation : σ réduit la population stationnaire (1072→630) et
raccourcit l'espérance de vie, ce qui TRONQUE l'accumulation de degré — le
mécanisme même qui produit la dispersion du revenu. Les deux effets
s'opposent ; la troncature l'emporte. **Ce n'est pas un contrôle raté, c'est
une identification de mécanisme** : σ ne fait que déplacer une coupure, pas
la forme du corps (invariante). Côté avalanches : τ̂ augmente avec σ
(1,42→2,00), branching diminue (0,79→0,46) — σ éloigne le système d'un
régime critique plutôt que de l'en rapprocher.

## 7. Balayage λ ∈ {10, 100} (2 graines, T=1000) — limite de la méthode
   d'ajustement des avalanches identifiée

τ̂ dérive avec λ : 1,19-1,27 (λ=10) → 1,42-1,45 (λ=30) → 1,75 (λ=100), avec
size_max 75→155→280. **Vérification de l'artefact avant toute conclusion**
(cf. mémoire M4.2 : ne jamais confondre coupure et exposant) : la coupure
ajustée par `fit_powerlaw_cutoff` vaut 35-107 (bien en-deçà de size_max) à
λ=10 et λ=30, mais **≈4,85×10⁸ à λ=100 — exactement e²⁰, la borne
supérieure numérique du paramètre `log_cutoff` dans `lib_metrics.py`**.
L'optimiseur a buté sur sa borne : à λ=100, AUCUNE coupure finie n'est
détectée dans la plage observée — le "τ̂=1,75" rapporté est en réalité
l'exposant de la loi PURE (mêmes symptômes que la note méthodologique de
M4.2 : « à λ=100, τ̂ est en réalité l'exposant de la loi pure, coupure hors
portée »). Les trois τ̂ ne sont donc **pas directement comparables** (deux
sont des ajustements tronqués authentiques, un est un ajustement pur
dégénéré). **Verdict honnête** : aucun exposant indépendant de la taille
n'est établi sur 10≤λ≤100 avec cette méthode ; noter aussi que λ déplace
simultanément la taille du système ET l'intensité de marché (η(N)=N), donc
la dérive observée ne peut pas être attribuée à la taille seule.

Invariants robustes malgré tout : branching_ratio = 0,78-0,79 sur tout
λ∈{10,30,100} ET sous les deux target_rule — pinning institutionnel réel,
analogue à celui trouvé par M4.2 (0,30) mais à un niveau différent, fixé
par la baseline lente δ=0,01/σ=0,01. Gini(K) = 0,052-0,064 sur toute cette
plage — l'homogénéisation du capital est un fait structurel robuste de
M4.2B, quasi indépendant de λ et du target_rule, et c'est ce qui prive
l'objectif A de matière première.

## 9. Reprise (30/07/2026, soir) : budget illimité, diagnostic de
   renouvellement corrigé, optimisation mesurée, campagne complète lancée

Autorisation utilisateur : budget de calcul illimité, 8 processus (au lieu
de la convention ≤6), exécution de l'intégralité de la tâche du prompt.

**Diagnostic de renouvellement — deux erreurs de ma part, corrigées par
l'utilisateur** :
1. Premier essai : cohorte du premier décile *d'âge* au premier snapshot →
   extinction totale en ~300 pas. L'utilisateur a signalé que la figure de
   référence existe déjà dans la batterie M4B/M4.2/M4.2B
   (`reporting.py::soc_figures`, `soc_top_decile_renewal.png`) et que le
   découpage pertinent est par **taille/revenu**, pas par âge.
2. Reproduit avec la convention exacte de cette figure (top décile par
   VALEUR NETTE, persistance de l'appartenance recalculée à chaque
   snapshot, pas simple survie) sur le run baseline T=3000 : décroissance
   rapide sur ~100 pas (0,98→0,79), décroissance plus lente jusqu'à
   t≈2000 (→~0,09), puis **un plancher non nul (~0,07-0,09) qui ne
   redescend plus jusqu'à t=3000**. Vérifié séparément (`scipy.stats.
   linregress`) que Gini(K) lui-même ne dérive pas dans cette fenêtre
   (p=0,73 sur [750,3000]) : les statistiques déjà rapportées ne sont pas
   contaminées, mais le plancher persistant justifie une validation à
   T=10000 (demandée par l'utilisateur), incluse dans la campagne
   ci-dessous.

**Optimisation du moteur** : profilage (cProfile, T=600) montre que
`_run_market` domine (59 % du temps), lui-même dominé par le coût
d'appel numpy de `_sample` (~750 000 appels/run à taille quasi-nulle).
Un batching des tirages RNG a été envisagé mais **écarté** : la
correction par rejet (paire non-distincte) consomme un nombre VARIABLE de
tirages selon les collisions, donc un pré-tirage en bloc désynchroniserait
la suite RNG dès la première collision (probabilité faible par tirage mais
certaine sur un run complet) — non conforme à l'exigence de parité stricte.
Optimisations sûres appliquées à la place (aucun appel RNG modifié, alias
locaux + suppression de `tolist()/set()` pour k=2 constant, remplacement de
`max`/`min` par comparaison directe reproduisant EXACTEMENT le
comportement en cas d'égalité) : **parité re-vérifiée à 0,000e+00** après
coup. Gain réel mesuré en comparaison équitable (non profilée avant/après,
piège méthodologique évité : la première comparaison, contaminée par le
surcoût de cProfile lui-même, indiquait à tort ×2,7) : **~9 % plus rapide**
(51,9 s → 47,6 s à T=400, même config). Le gain de débit attendu pour la
nuit vient donc essentiellement du parallélisme (8 processus), pas de
l'accélération par cœur.

**Campagne complète lancée** (protocole figé : `report/protocole.md`) : 29
cellules uniques × 3 graines = 87 runs (T=3000, sauf validation d'horizon
à T=10000), branches K0 (prioritaire), γ (non compensé + compensé), η non
linéaire (β), δ/σ joints (incluant la baseline M4.2 (0,05;0,25) en
comparaison institutionnelle directe), ρ (repris rigoureusement), contrôle
géométrique. Bug corrigé avant lancement : le pilote λ appelait
`fit_powerlaw_cutoff` directement sans vérifier `s_c_out_of_range` — la
campagne utilise désormais `lib_metrics.compare_laws` (qui gère déjà
correctement ce repli) partout.

## 8. Ce qui n'a pas été testé (à faire figurer explicitement, §18)

γ≠0,5, K0≠25, formes non linéaires de η (β≠1), ablations de mécanisme
(règle de taux, fusion/mémoire des contrats), campagne multi-graines
complète par cellule, collapse de taille finie en bonne et due forme pour
les avalanches (λ>100, ou N contrôlé indépendamment de l'intensité de
marché). Le budget de calcul de cette session a été alloué aux pilotes
ci-dessus plutôt qu'à une grille étendue, sur la base du diagnostic qu'ils
apportaient l'information marginale la plus grande avant de figer quoi que
ce soit.

## 9. Exécution de la campagne — incidents machine et lecture partielle (04/08)

**Incidents** : le poste a crashé et redémarré une première fois pendant
l'exécution (uptime repartie à ~0, aucune session tmux/processus survivant
après un lancement initial hors tmux). Campagne relancée dans une session
tmux détachée (`m42b_campaign`) pour être indépendante du cycle de vie du
process qui la lance. Un second arrêt s'est produit ~40 min plus tard
**sans redémarrage machine cette fois** (uptime continue, `journalctl
--list-boots` ne montre qu'un seul boot ; aucune trace d'OOM-kill dans le
journal utilisateur, accès `sudo` aux logs kernel non disponible dans cette
session) — cause non élucidée, investigation déléguée par l'utilisateur à
une autre instance. À chaque arrêt : les répertoires de run partiels
(`analysis.json` absent) ont été supprimés avant relance pour forcer un
recalcul propre ; la reprise automatique de `scripts/campaign.py` (skip si
`analysis.json` avec `status="ok"`) a été vérifiée fonctionnelle à chaque
relance (aucun run déjà complet recalculé).

**État à 13h20** : 14/87 runs complets (`baseline`, `K0_1`, `K0_5`,
`K0_100` — 3 graines chacun ; `t10000_baseline` 2/3 graines). Campagne de
nouveau en cours (tmux `m42b_campaign`, 8 workers).

**Outil créé** : `scripts/aggregate_exploration.py` — agrège tous les
`analysis.json` de `results/campaign/` en une table plate,
`results/campaign/exploration_summary.csv` (stdlib seul, pas de nouvelle
dépendance). Relire ce fichier au fur et à mesure, ne rien recalculer à la
main.

**Lecture PARTIELLE et PRÉLIMINAIRE, branche A (K0) — 4/6 valeurs
disponibles (K0∈{1,5,25(baseline),100}, seeds 0-2 d'exploration
uniquement, PAS les graines de confirmation)** : moyennes sur 3 graines,
depuis `exploration_summary.csv` :

| K0 | α̂_density moyen | share_mean_rq | share_deg_out | τ̂ | branching_ratio | Gini(K) |
|---|---|---|---|---|---|---|
| 1 | 3,59 | 0,346 | 0,660 | 1,79 | 0,588 | 0,117 |
| 5 | 4,08 | 0,282 | 0,732 | 1,56 | 0,709 | 0,083 |
| 25 (baseline) | 3,78 | 0,229 | 0,777 | 1,41 | 0,786 | 0,057 |
| 100 | 3,51 | 0,189 | 0,791 | 1,39 | 0,795 | 0,039 |

Motif monotone sur les 4 points disponibles : `share_from_mean_rq_mean`
DÉCROÎT quand K0 croît (0,346→0,189) — c'est le sens INVERSE de ce qui
rapprocherait de l'objectif A (dominance du mécanisme deg_out encore plus
forte à K0 élevé, pas moins). En parallèle, branching_ratio croît
(0,588→0,795) et τ̂ décroît (1,79→1,39) avec K0 — avalanches plus
critiques/plus lourdes à K0 élevé. **Hypothèse, non établie** : si ce motif
se confirme sur K0∈{500,2000} (en cours) et sur les graines de
confirmation, la direction prometteuse pour l'objectif A serait K0 FAIBLE
(<1), pas élevé — à l'inverse de ce qu'indiquait la seule intuition
K0/K*_aut de départ (protocole, branche A). Ne pas sélectionner de cellule
de confirmation sur cette seule lecture partielle : attendre l'exploration
complète (§ordre d'exécution, `report/protocole.md`).

## 10. Garde-fous mémoire (troisième arrêt, 04/08 14h12 — cause identifiée)

**Troisième arrêt** : ni redémarrage machine (`uptime`/`journalctl
--list-boots` : même boot que le second arrêt) ni trace d'OOM-kill
accessible sans `sudo` — cause précise toujours non confirmée par le
journal système, mais l'hypothèse de l'utilisateur (une simulation devient
trop grosse en mémoire) est fondée sur un fait observé indépendant :

**Fait observé** : le poids sur disque d'un run complet croît fortement
avec K0 (échantillon seed0, `du -sh`) : K0=1 → 107 Mo, K0=5 → 176 Mo,
K0=25 (baseline) → 324 Mo, K0=100 → 600 Mo — porté essentiellement par
`loan_events.csv.gz` (77→127→220→369 Mo) et `snapshots/` (15→34→88→213 Mo).
**Fait observé (code)** : `simulation.loan_events` (`m4_2b/model.py:534,602`)
était une liste Python accumulée sur tout le run (3 548 978 événements pour
la seule baseline seed0) et écrite en un seul bloc à la toute fin
(`io.py::_write_loan_events`, ancien code) — contrairement à
`individual_series.csv.gz` qui était déjà streamé pas-à-pas sans
accumulation. Avec 8 workers en parallèle sur des cellules K0 élevé
(K0_500, K0_2000, jamais terminées), c'est le candidat le plus probable
pour une saturation mémoire brutale et quasi simultanée sur plusieurs
workers.

**Correctifs appliqués** :
1. `m4_2b/io.py` — `loan_events` est maintenant streamé pas-à-pas et vidé
   de la mémoire à chaque pas (`RunRecorder.record_loan_events`, même
   patron que `record_individuals`), au lieu d'être accumulé puis écrit une
   fois à la fin. `loan_events_total` compté par un compteur incrémental
   plutôt que `len(simulation.loan_events)`. Aucun changement de RNG, de
   logique de pas, ni des invariants du cache d'intérêts (changement
   strictement côté I/O). `tests/test_engine.py::test_loan_events_written_and_readable`
   mis à jour pour refléter que la liste en mémoire est vide en fin de run
   (elle ne l'était pas avant). **31/31 tests verts après coup**
   (`test_engine.py`, `test_parity_m4_2.py`, `test_arithmetic_institution.py`,
   `test_interest_income_tools.py`).
2. `scripts/campaign.py` — garde-fou dur : chaque worker du pool reçoit une
   limite de mémoire virtuelle (`resource.RLIMIT_AS`, stdlib), calculée
   dynamiquement comme 75 % de la RAM totale de la machine divisée par le
   nombre de workers (3,15 GB/worker sur cette machine à 8 workers/31 Go
   RAM). Un run qui dérape malgré tout lève un `MemoryError` propre, capté
   par `_run_and_analyze` et écrit en `status="error"` — au lieu de
   saturer la machine entière.
3. `scripts/mem_watch.py` (nouveau) — observateur indépendant (sa propre
   session tmux `m42b_memwatch`, découplée du pool de la campagne) : logge
   toutes les 15 s la mémoire système (`/proc/meminfo`) et la RSS cumulée
   des processus `campaign.py` dans `results/campaign/mem_watch.csv`.
   Objectif : disposer d'un historique exploitable en cas de nouvel arrêt,
   sans dépendre de `sudo`/logs kernel inaccessibles dans cette session.

**Ce que ceci NE prouve PAS** : que le troisième arrêt était bien un
OOM — c'est une hypothèse cohérente avec un fait observé (croissance de
`loan_events` avec K0), pas une cause confirmée par un log système. Si un
nouvel arrêt survient malgré les garde-fous ci-dessus, `mem_watch.csv`
donnera la première preuve directe (ou l'infirmera, orientant vers une
autre cause).

**État à 14h22** : campagne relancée (tmux `m42b_campaign`, garde-fou
mémoire actif) + observateur mémoire lancé en parallèle (tmux
`m42b_memwatch`). 14/87 runs déjà complets conservés (reprise
automatique).

## 11. Campagne d'exploration terminée (04/08 22h15) — garde-fou confirmé, hypothèse utilisateur validée

**84/87 runs terminés avec succès, 0 nouveau crash machine** depuis le
relancement du §10 (`uptime` continue, 9h54 sans interruption). Les
garde-fous ont tenu sur l'intégralité de la campagne, y compris sur les
cellules K0 élevé qui faisaient planter la machine avant correctif.

**3 échecs, tous identiques et localisés à `K0_2000` (les 3 graines)** :
`MemoryError` propre, capté par `_run_and_analyze`, `status="error"` avec
traceback complet conservé dans `analysis.json`. Point de rupture exact :
`m4_2b/model.py:182`, `Book.add()` — `self.loans[loan_id] = [...]`, PAS
`loan_events` (déjà corrigé). **Ceci confirme directement l'hypothèse de
l'utilisateur** (certaines simulations deviennent trop grosses en mémoire)
ET révèle un second point d'accumulation non borné, différent du premier :
le carnet de prêts ACTIFS (`Book.loans`) lui-même grossit sans limite
apparente à K0=2000, dans le budget de 3,15 Go/worker — indépendamment de
`pop_max` (30 000, jamais atteint : aucun `status="explosion"` observé).

**Ce que ceci NE dit PAS encore** : si le carnet de prêts croît simplement
plus lentement vers un plateau (et qu'un budget mémoire plus large
suffirait) ou s'il diverge réellement sans borne à K0=2000 (auquel cas
aucun budget mémoire fini ne suffirait) — pas d'investigation plus
poussée à ce stade, décision à prendre avec l'utilisateur avant de
relancer K0_2000 avec plus de ressources.

**Import simulation_lab** : script parallélisé (8 workers, cf.
`scripts/import_to_simulation_lab.py`) pour rattraper les 61 runs restants
maintenant que la campagne a libéré les cœurs (23 déjà importés en solo
pendant la campagne). `results/campaign/simlab_import_map.json` retient le
mapping run campagne -> run_id simulation_lab (idempotent).

## 12. K0_2000 : quatre causes distinctes, résolues une à une (04-05/08)

Sur demande explicite de l'utilisateur ("investiguer d'abord"), quatre
tentatives successives, chacune corrigeant une cause réelle mais
insuffisante à elle seule — décrites dans l'ordre où elles ont été
découvertes (chaque nouvel échec déplaçait le point de rupture plus loin
dans le run, ce qui a servi de fil conducteur) :

1. **`_write_final_loans` dupliquait le carnet en mémoire** (`m4_2b/io.py`) :
   construisait une liste `rows` complète (~700-750k lignes en régime
   stationnaire à K0=2000) EN PLUS du carnet déjà résident, au moment du
   bilan final. Corrigé : écriture directe ligne à ligne. **Insuffisant
   seul** — échec suivant toujours au même endroit (`Book.add`, pendant la
   boucle), prouvant que ce n'était pas la cause principale.
2. **`deaths`/`avalanches`/`avalanche_members` jamais streamés** (même
   anti-motif que `loan_events`, jamais corrigé) : accumulés sur tout le
   run, écrits en un seul bloc à la fin. Corrigé dans `m4_2b/io.py`
   (streaming pas-à-pas + compteurs incrémentaux pour `deaths_total`,
   `avalanches_total`, `branching_ratio`) ; a nécessité un changement dans
   `m4_2b/model.py` : `avalanche_id` était dérivé de `len(self.avalanches)`,
   ce qui se serait cassé (IDs qui se réinitialisent) une fois la liste
   vidée à chaque pas — remplacé par un compteur monotone dédié
   (`_avalanche_id_counter`). Parité stricte re-vérifiée (0,000e+00,
   `test_parity_m4_2.py`) car ce changement touche le moteur. **Insuffisant
   seul** — mais a fait progresser le point de rupture : les 3 graines
   terminent maintenant la simulation complète (t=3000) ; l'échec se
   déplace vers la phase d'ANALYSE (`interest_income.load_all_network_snapshots`
   dans `numpy.load`/`zipfile`, `MemoryError: Unable to allocate output
   buffer`).
3. **`load_all_network_snapshots` matérialisait toute la fenêtre en
   mémoire** (`scripts/interest_income.py`) : jusqu'à ~90 instantanés
   réseau chargés simultanément pour la décomposition, chacun jusqu'à
   ~700k lignes × 4 tableaux à K0=2000 (≈ 2 Go rien que pour cette liste).
   Converti en générateur (un instantané à la fois) ; seul consommateur
   dans `campaign.py` (boucle de décomposition), déjà en simple itération
   — aucun changement d'appelant nécessaire. **Insuffisant seul** — échec
   toujours au même endroit (lecture d'un instantané réseau), ce qui a
   orienté vers la cause suivante.
4. **`sim` (l'objet `Simulation` complet, avec `sim.book`) restait vivant
   pendant toute la phase d'analyse** (`scripts/campaign.py::_run_and_analyze`) :
   `_analyze_run` ne lit que des fichiers sur disque (jamais l'objet live),
   mais `sim` était conservé comme variable locale pendant tout l'appel —
   avec son carnet de prêts actifs (~700-900 Mo à K0=2000, carnet +
   `by_lender`/`by_borrower`/`by_pair`/`claims`/`debts`/`due`) toujours
   résident au moment même où l'analyse a le plus besoin de marge. Corrigé :
   `del sim; gc.collect()` immédiatement après `run_and_save`, avant
   `_analyze_run`. **Cause déterminante** : les 3 graines K0_2000 ont
   terminé avec succès juste après (elapsed 5524-5850 s, ~92-98 min
   chacune ; RSS max observée 1,94 Go, sous le plafond de 3,15 Go).

**Résultat** : exploration complète, **87/87 runs, 0 échec**. Les quatre
correctifs partagent le même principe (ne jamais garder en mémoire ce qui
peut être streamé ou libéré), déjà appliqué une première fois à
`loan_events` (§10) — cette section documente pourquoi il a fallu
l'appliquer de façon systématique plutôt qu'au cas par cas : à K0 élevé,
plusieurs structures indépendantes (carnet de prêts, décès, avalanches,
instantanés réseau, objet Simulation complet) approchent simultanément le
budget mémoire, et corriger une seule ne suffit pas tant que les autres
restent au même ordre de grandeur.

Tests : 31/31 verts après chaque étape (`test_engine.py`,
`test_parity_m4_2.py`, `test_arithmetic_institution.py`,
`test_interest_income_tools.py`).

## 13. Résolution du doute sur la version du prompt (2026-08-05)

Doute soulevé : `prompts/PROMPT_M4_2B.md` (version condensée déjà dans le
dépôt) semblait diverger d'un fichier `PROMPT_M4_2B_SONNET5.md` trouvé
dans `~/Téléchargements` (objectif unique centré sur η, K0 absent du
grid, γ secondaire, 14 questions finales) — à l'opposé du double objectif
A/B, de K0 comme paramètre libre et de γ non hiérarchisé qui ont
effectivement gouverné la conception de la campagne d'exploration.

L'utilisateur a alors signalé un second fichier,
`PROMPT_M4_2B_SONNET5(2).md`, dans le même dossier. Horodatage : 16h33 le
30/07, contre 16h00 pour le fichier sans suffixe — postérieur de 33 min,
donc probablement une révision. Contenu vérifié section par section :
double Objectif A/B (§9, §46), *« K0 n'est pas sanctuarisé »* (§5,
quasi verbatim identique à la version condensée), *« Ne traite pas γ
comme un simple contrôle secondaire ni η comme l'unique levier »* (§13),
*« η : levier privilégié, mais non exclusif »* (§7), avalanches *« pas un
simple diagnostic secondaire »* (§15), 17 questions finales (§21) — tout
concorde avec `prompts/PROMPT_M4_2B.md` déjà dans le dépôt.

**Conclusion** : `PROMPT_M4_2B_SONNET5.md` (sans suffixe) était un
brouillon antérieur incomplet, pas la version qui fait foi.
`PROMPT_M4_2B_SONNET5(2).md` est la version intégrale de référence ;
copiée dans le dépôt sous `prompts/PROMPT_M4_2B_COMPLET.md`. La campagne
d'exploration (87/87 runs) est donc correctement dimensionnée par
rapport au prompt complet — aucune reprise ni étude séparée nécessaire
pour ce motif. Décision utilisateur : abandon de l'idée d'une étude
« M4.2C » distincte envisagée un temps sur la base du brouillon
incomplet ; reprise directe des tâches #12 (campagne de confirmation) et
#13 (rapport final sur les 17 questions du §21).

## 14. Lancement de la campagne de confirmation (2026-08-05)

6 cellules sélectionnées à partir de `exploration_summary.csv` (effet le
plus net sur `share_from_mean_rq`, plus `control_geometric` requise pour
la question 1 du rapport) : `rho_0.125`, `rho_4`, `K0_1`, `K0_2000`,
`gamma_0.6667`, `control_geometric`. Rationale complet et tableau de
classement : `report/selection_confirmation.md`. 5 graines disjointes
(10-14), T=3000, `scripts/confirmation.py` (nouveau script, réutilise
`build_cells`/`_run_and_analyze` de `campaign.py` — seul changement dans
`campaign.py` : `_run_and_analyze`/`_reanalyze` acceptent maintenant un
`results_root` optionnel dans `spec`, pour écrire sous
`results/confirmation/` sans toucher `results/campaign/`). Lancé dans
tmux (`m42b_confirmation`), 30 runs, même garde-fou mémoire (3,15 Go/
worker, 8 workers) que l'exploration.

## 15. Incident du 05/08 (confirmation) : deux pools concurrents, garde-fou mémoire non coordonné + pool entier tué par une seule MemoryError

À 15h20, une extension à 3 cellules supplémentaires
(`scripts/confirmation_extra.py`, 3 workers `nice -n 19`) a été lancée
**en même temps** que la confirmation principale (`scripts/
confirmation.py`, 8 workers), pour ne pas perdre de temps pendant que
les cellules lourdes (K0_2000) tournaient. Vers 16h45, le pool principal
est mort entièrement (`MemoryError: Unable to allocate output buffer`,
dans `np.savez_compressed` pendant l'écriture d'un instantané réseau,
`m4_2b/io.py:141`), après 23/30 runs réussis.

**Deux causes, l'une root-cause, l'autre aggravante :**

1. **Garde-fou mémoire non coordonné entre deux pools indépendants**
   (root cause). `_worker_memory_cap_bytes(n_workers)` calcule 75 % de
   la RAM totale divisée par `n_workers` du pool *courant* — hypothèse
   implicite qu'un seul pool tourne à la fois. Avec les deux pools
   simultanés (8 workers à 3,15 Go de plafond chacun + 3 workers à
   8,41 Go chacun, calculés indépendamment), la réservation combinée
   dépassait largement les 31 Go de la machine (jusqu'à ~50 Go dans le
   pire cas) — chaque pool respectait SON plafond individuel sans savoir
   que l'autre existait.
2. **`_run_and_analyze` ne capturait pas les erreurs de la phase de
   simulation** (aggravant) : seule `_analyze_run` (post-traitement)
   avait un `try/except` ; un run dont `run_and_save` levait une
   exception (ici `MemoryError`) la propageait telle quelle à travers
   `pool.imap_unordered`, qui la re-lève dans le process principal et
   **termine tout le pool** — y compris les autres workers encore en
   vol (3 runs K0_2000 ont été surpris en fin de simulation, juste avant
   l'écriture de `analysis.json`, cf. `summary.json` présent mais pas
   `analysis.json`).

**Corrigé** :
- `_run_and_analyze` (`scripts/campaign.py`) : la phase `run_and_save`
  est maintenant dans un `try/except Exception`, qui écrit un
  `analysis.json` de statut `"error"` (comme le fait déjà
  `_analyze_run`) au lieu de propager. Une erreur sur UN run ne tue plus
  le pool entier.
- `_reanalyze` : tolère maintenant l'absence de `analysis.json` (cas des
  3 runs K0_2000 dont la simulation avait fini mais dont l'analyse a été
  interrompue par la mort du pool) — `elapsed_s` mis à NaN dans ce cas
  (perdu, jamais persisté ailleurs) plutôt que de lever une exception.
  Ces 3 runs ont été ré-analysés depuis le disque (`summary.json`
  déjà présent), sans re-simuler (~95 min/run économisées).
- **Pas de correctif sur la coordination mémoire entre pools** : décision
  de ne plus jamais lancer deux pools de simulation en même temps sur
  cette machine, plutôt que de complexifier le calcul du plafond. La
  confirmation principale a été relancée seule (reprend à 23/30, reprise
  automatique) ; l'extension (`confirmation_extra.py`) sera relancée
  seule après, séquentiellement.

Runs perdus (à re-simuler, pas de résultat partiel utilisable) : `rho_4`
seed 13-14, `K0_2000` seed 13-14 (4 runs). Aucune perte sur les 26 runs
déjà correctement terminés (23 + les 3 K0_2000 ré-analysés).

**Suite (même soirée)** : confirmation principale relancée seule (reprise
automatique, a bien sauté les 26 runs déjà valides) — terminée **30/30,
0 erreur**. Extension relancée ensuite, seule (plus de pool concurrent),
workers remontés de 3 à 6 (convention du projet, plus besoin de réduire
pour un partage CPU/mémoire) — terminée **15/15, 0 erreur**. Total
confirmation : **45/45 runs, 0 erreur** (9 cellules × 5 graines
disjointes 10-14 : les 6 initiales + les 3 de l'extension §14/rapport
intérimaire §10). Tâche #12 du programme close.

## 16. Analyse finale et rapport (2026-08-06)

`scripts/aggregate_confirmation.py` (nouveau) applique les 5 critères
objectif A + le critère 5 (opérationnalisé, protocole muet dessus) aux
45 runs de confirmation. Verdict : les 9 cellules échouent, toutes
bloquées par le même critère (stabilité de seuil, 0/5 graines partout,
sans exception) — critères 2/3 à 5/5 partout (excellente reproductibilité
inter-graines, écart-type de alpha <= 0,09), critère 4 en échec net
uniquement sur K0_1 et rho_0.125 (0/5, l'exponentielle y domine meme
superficiellement). Detail et tables : results/confirmation/
confirmation_verdicts.csv, confirmation_runs.csv.

Objectif B : pas de verdict formel calculé - aucune des 9 cellules ne
fait varier la taille du systeme a parametres autrement identiques
(lambda=30 fixe partout ; K0_1 vs K0_2000 changeraient simultanement
Gini, mobilite et mecanisme de prix, donc non interpretable comme un
axe de taille). Conclusion du pilote (resume.md, balayage lambda)
reconduite sans changement : aucun exposant d'avalanche independant de
la taille etabli.

Rapport final redige (report/rapport_final.md + .tex + .pdf, autonome
comme rapport_interim.md, reponses aux 17 questions du §21), livre a
l'utilisateur. Tests 31/31 verts, parite 0,000e+00. Tache #13 close -
programme M4.2B (pilote + exploration + confirmation + rapport)
termine.

## 17. Illustration du rapport final (2026-08-06)

Demande utilisateur : rapport comprehensible "grossierement" par ses
seules figures, en combinant (a) les graphiques de simulation deja
generes dans simulation_lab (adaptateur M4.2B, figures.py/reporting.py)
et (b) de nouvelles figures de synthese derivees des tables agregees.

(a) 6 figures choisies parmi celles deja importees dans simulation_lab
(exploration, seed0, cellules deja dans les 9 de confirmation) :
distribution des interets recus (baseline, K0_1, K0_2000), renouvellement
du top decile (K0_1, K0_2000), CCDF des avalanches (rho_0.125, rho_4).
Copiees dans report/figures/.

(b) scripts/make_report_figures.py (nouveau) : 6 figures generees a
partir de exploration_summary.csv/confirmation_runs.csv/
confirmation_verdicts.csv (aucun run brut relu) -- matrice de verdict
9 cellules x 5 criteres, stabilite de seuil sur les 29 cellules
d'exploration, alpha vs K0/gamma(brut+compense)/rho, panel eta a 3
diagnostics, scatter compromis objectif A/B. Chaque figure superpose
exploration (3 graines) et confirmation (5 graines) quand pertinent,
pour rendre visible la reproductibilite.

report/rapport_final.md et .tex retravailles pour integrer les 12
figures au fil du texte (pas en annexe), + audit d'autonomie : 4
renvois casses "§11" (numero inexistant, copie-colle d'un brouillon)
corriges vers §8 ; mention a rapport_interim.md retiree de l'intro.
LaTeX : \usepackage{float} + [H] sur toutes les figures (evite la derive
de flottants qui separait les figures de leur texte declencheur de 1-2
pages). PDF final 13 pages, compilation propre (0 warning), envoye a
l'utilisateur.

## 18. Verification du sens seuil/2 (critere 1) suite a question utilisateur (2026-08-06)

Question : la figure "stabilite de seuil" (fig1, "Figure 3" dans le PDF
compile) compare alpha(seuil) a alpha(seuil/2) — l'utilisateur soupconnait
une coquille (attendu : seuil*2). Verifie : ce n'est pas une coquille.

- `report/protocole.md:88` fixe explicitement "seuil/2" comme critere 1,
  ecrit avant tout resultat de confirmation.
- `scripts/interest_income.py:54` calcule les DEUX facteurs
  (`THRESHOLD_STABILITY_FACTORS = (0.5, 2.0)`), stockes par instantane ;
  seul 0,5 a ete retenu comme critere de robustesse.
- Raison empirique, deja etablie en phase pilote (§6, balayage sigma) :
  alpha au seuil KS variait fortement avec sigma (3,86->5,03) alors
  qu'alpha a seuil moitie restait quasi constant (~2,6-2,8) — signe que
  le selecteur automatique de seuil accroche parfois une fenetre etroite
  en haut de la distribution plutot qu'une vraie loi de puissance
  etendue. Elargir la fenetre vers le bas (seuil/2) est le test qui
  expose cet artefact ; la retrecir encore (seuil*2) ne l'aurait pas
  teste — c'est exactement le test qui avait demasque le probleme en
  pilote (§4 : "artefact de coupure/courbure, pas un controle de
  queue").

## 21. Refonte complete : hypothese Pareto + caracterisation d'alpha (2026-08-06)

Suite logique de §18-20 : l'utilisateur tranche definitivement
l'incertitude sur seuil/2 vs seuil*2 (§18-19) puis, apres avoir constate
que le facteur d'admissibilite continu (§20) donne A<0,5 partout sans
etre une preuve de courbure (couverture mediane 0,22 << platitude
mediane 0,56 -- limite de VOLUME de donnees, pas de forme), decide :
**l'existence de la queue de Pareto des interets est desormais posee
comme hypothese de travail**, le "coude" apres la cassure etant reconnu
mais pas teste. Le programme se recentre sur la CARACTERISATION de
alpha-hat et de son incertitude, plus sur son existence.

Detour intermediaire (renouvellement, demande utilisateur avant la
decision ci-dessus) : regression FOPDT (delai + decroissance
exponentielle) sur le renouvellement du decile superieur,
`scripts/renewal_worked_example.py` (baseline, R²=0,99 net worth/revenu)
puis `scripts/renewal_relaxation_all_runs.py` (132 runs x 3 champs,
6 workers, ~5 min) -> `results/renewal_relaxation_all_runs.csv`.
Trouvaille cle : le burn-in fixe T/4 est insuffisant pour 27/37 cellules
(revenu/net worth), le capital relaxant lui quasi instantanement
partout. `scripts/window_selection.py` classe chaque run "leger"
(fenetre repositionnee a t_conv=t0+t_delay+3.tau, instantanes espaces
de ~tau) ou "severe" (pas de marge avant T, dernier instantane seul,
flag explicite) -> `results/window_selection.csv`.

Rollout : `scripts/admissibility_rollout.py` etendu pour persister
`alpha_boot_sd` (deja calcule via le bootstrap KS-rescanne, juste pas
garde). Nouveau script `scripts/characterize_alpha.py` : agrege en
TROIS composantes de variance jamais fusionnees -- intra-instantane
(bootstrap), inter-instantanes (dispersion sur les instantanes selectionnes
d'un run), inter-graines (dispersion de la moyenne de run entre graines
d'une cellule) -> `results/alpha_characterization_{runs,cells}.csv`.
Constat cle (verifie avant de l'ecrire dans le rapport, cf. revue) :
intra-instantane (moyenne 0,338) ~3,7x plus grand que inter-graines
(moyenne 0,092) -- lire alpha sur un seul instantane est bien moins
precis que ne le suggere l'excellente reproductibilite de la moyenne de
cellule. K0_2000 (severe) reste tres reproductible malgre l'absence de
fenetre stationnaire confirmee (ecart-type inter-graines 0,007-0,053) --
distinction "reproductible" != "stationnaire etabli" gardee explicite
partout dans le rapport.

Nouvelles figures (`scripts/make_alpha_characterization_figures.py`) :
fig12 (alpha vs K0, marqueurs creux pour cellules severes), fig13 (alpha
vs gamma), fig14 (alpha vs eta/rho/beta), fig15 (alpha vs delta=sigma,
point delta=0,05/sigma=0,25 seul separe de la branche conjointe --
bug attrape et corrige avant publication, ce point n'a pas delta=sigma).

Rapport (`rapport_final.md`/`.tex`) integralement retravaille : §3
(glossaire alpha, incertitude bootstrap), §4 (ex-"criteres de
confirmation" -> "du test d'existence a la caracterisation", retrace les
3 tentatives et la decision), §5 (ex-"verdict" -> "resultat central :
alpha caracterise, pas teste"), §6 (ex-"ce qui bouge quand meme" ->
section principale, nouvelle sous-section FOPDT/fig8-9, tableaux et
figures mis a jour avec les nouvelles valeurs alpha + 3 composantes),
§7 (17 questions, Q1/Q3/Q5-Q9/Q11-Q15 reecrites), §8 (nouvelles entrees :
test abandonne pas resolu, hypotheses du bootstrap, cellules severes),
conclusion. fig1/2/3/4/6/7 (bases sur l'ancien critere pass/fail)
retirees ; fig10/11 (facteur d'admissibilite) et fig8/9 (FOPDT) et
fig12-15 (alpha vs parametres) integrees. Recompile 3x, 16 pages,
0 warning/erreur. PDF renvoye a l'utilisateur.

---

Rapport corrige (`rapport_final.md`/`.tex`, glossaire §3, paragraphe
alpha/stabilite de seuil) : ajout d'une explication explicite du sens
seuil/2 avec le chiffre pilote (3,86->5,03 vs 2,6-2,8 stable), pour que
ce point ne redemande plus de lire le journal. Recompile 3x, 13 pages,
0 warning, PDF renvoye a l'utilisateur.

Suite : l'utilisateur a demande de MONTRER le calcul du seuil et les
regressions (seuil et seuil/2) tracees sur les vraies donnees. Cree
`scripts/make_threshold_worked_example.py` : appelle directement
`tail_test.fit_powerlaw_xmin` et `interest_income._alpha_hill_at_threshold`
(aucune reimplementation) sur un instantane reel — baseline seed0,
t=2225 (fenetre confirmation [750,3000], choisi car alpha_density le
plus proche de la moyenne du run, 3,7798). Figure 2 panneaux :
A) distance KS vs seuil candidat (montre le balayage de quantiles et le
minimum qui selectionne x_min=48,2) ; B) CCDF log-log des 1059 valeurs
positives avec les deux droites de regression superposees — seuil
(alpha=3,78, n_tail=277, KS=0,041) et seuil/2 (alpha=2,46, n_tail=610,
KS=0,173). Ecart relatif sur ce seul instantane : 35% (> 20%, echoue
deja le critere isolement). Figure ecrite dans
`report/figures/fig7_seuil_exemple_travaille.png`, inseree dans
rapport_final.md et .tex juste avant §4 (Les criteres de confirmation).
Recompile 3x, 13 pages, 0 warning. PDF renvoye a l'utilisateur.

## 20. Revision du critere 1 : seuil x2, incertitude bootstrap, facteur
## d'admissibilite continu (2026-08-06)

L'utilisateur a reconsidere seuil/2 : c'est seuil*2 (auto-similarite
d'une vraie loi de puissance) qui a du sens comme test, pas seuil/2 (qui
teste juste la remontee vers le corps, deja modelise separement par
GB2 -- echoue quasi tautologiquement). Verification empirique
(`scripts/probe_criterion1_2x.py`) : a seuil*2, n_tail median tombe de
113 a 17 (1331 instantanes selectionnes) -- seuil*2 fixe n'est PAS
calculable de facon fiable (2% des refits atteignent n_tail>=80, le
plancher deja utilise ailleurs dans le pipeline). Correctif de
coherence applique : `interest_income._alpha_hill_at_threshold` prend
desormais `min_n` en parametre et l'herite de `fit_income_distribution`
(avant : 20 en dur, incoherent avec le scan KS primaire a 80).

Remplace par un facteur d'admissibilite CONTINU (pas pass/fail),
`scripts/admissibility_factor.py` : A = couverture(x_max) * platitude,
avec x_max = plus grand facteur x tel que n_tail(x*seuil)>=80 (donnee-
dependant), couverture = min(1, ln(x_max)/ln(2)), platitude = moyenne
(ponderee log) de exp(-z^2/2) sur la grille testable, z = |Δα| /
ecart-type BOOTSTRAP de Δα (300 tirages, KS RE-SCANNE a chaque tirage --
preference explicite utilisateur : capture aussi la variabilite du choix
de seuil, plus robuste a un "coude" structurel connu apres la cassure
que l'utilisateur a signale dans toutes ses simulations). Litterature
apparentee (memoire, non verifiee ligne a ligne) : Hill plot stability
(Drees-de Haan-Resnick 2000), seuil MSE-optimal par bootstrap
(Danielsson-de Haan-Peng-de Vries 2001), intervalle de stabilite
explicite (Voitalov et al. 2019, tres proche du contexte reseau ici).

Applique aux 132 runs (1457 instantanes selectionnes par
window_selection.csv, ~5 min avec 6 workers paralleles --
`scripts/admissibility_rollout.py` ->
`results/admissibility_all_runs.csv`). Resultat (fig11) :
**A<0,5 pour les 37 cellules sans exception**, la meilleure
(deltasigma_0.1_0.1) plafonne a ~0,47. Decomposition cle : coverage
mediane=0,22 (x_max median=1,17, tres loin de la cible x=2) contre
platitude mediane=0,56 (29% des instantanes ont une platitude>=0,75) --
**le facteur limitant est presque partout la couverture (donnees trop
rares pour tester loin), pas la platitude** (la ou on peut tester, ca ne
semble pas franchement s'ecarter du bruit). A rapporter comme tel : pas
"preuve de coupure partout", mais "le test pre-enregistre n'est
rigoureusement validable nulle part avec le volume de donnees
disponible".

Ce resultat correspond exactement au declencheur que l'utilisateur avait
lui-meme pose a l'avance : si rien de satisfaisant n'emerge a cette
iteration, abandonner le critere "existence robuste d'une queue de
Pareto" et basculer sur la caracterisation directe de la queue
(descriptive plutot que confirmatoire). Decision a prendre avec
l'utilisateur avant de reconstruire verdicts/rapport/§7 sur cette base.
