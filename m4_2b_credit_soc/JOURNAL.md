# JOURNAL — M4.2B (démarré 2026-07-30)

Cahier des charges d'autorité : `prompts/PROMPT_M4_2B.md`. Ce journal
consigne la chronologie réelle, y compris les hypothèses de départ
corrigées en cours de route (§18 du prompt : ne pas effacer les erreurs
intermédiaires).

## 1. Audit et implémentation (2026-07-30, matin)

Lecture complète de M4.2 (`m4_2_credit_soc/m4_2/model.py`, `io.py`, tests,
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
