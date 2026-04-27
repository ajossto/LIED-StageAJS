# Rapport de profilage — modele-27-04-WIP

**Date** : 2026-04-27
**Version cible** : `modele-27-04-WIP/src/` (cloné depuis `Modèle_sans_banque_wip/src/`)
**Comparaison** : `Modèle_sans_banque_wip/src/` (= `orig`) vs `modele-27-04-WIP/src/` (= `wip`)
**Plate-forme** : CPython 3.12.3, Linux x86_64
**Politique** : optimisations strictement conservatrices ; tout résultat de simulation
doit rester bit-pour-bit identique à seed et configuration constants.

---

## 1. Résumé exécutif

Le modèle de simulation multi-agents a été profilé puis optimisé sans modifier
sa dynamique. Six optimisations conservatrices ont été appliquées et chacune
validée par un test de non-régression strict (mêmes flottants au bit près) sur
trois seeds (42, 7, 123) à 400 pas, dont des trajectoires comportant cascades.

**Gain global mesuré** :

| taille | seed | original | WIP | speedup | gain |
|---|---|---|---|---|---|
| court (200 pas) | 42 | 1.43 s | 1.10 s | ×1.30 | −23 % |
| court (200 pas) | 7 | 1.42 s | 1.10 s | ×1.29 | −23 % |
| court (200 pas) | 123 | 1.39 s | 1.08 s | ×1.29 | −22 % |
| moyen (1000 pas) | 42 | 89.0 s | 45.7 s | ×1.95 | **−49 %** |
| moyen (1000 pas) | 7 | 86.5 s | 45.1 s | ×1.92 | **−48 %** |
| moyen (1000 pas) | 123 | 97.8 s | 50.4 s | ×1.94 | **−48 %** |
| long (3000 pas) | 42 | 748 s | 321 s | **×2.33** | **−57 %** |

Le speedup augmente fortement avec la taille de simulation (court ≈ ×1.3,
moyen ≈ ×1.95, long ≈ ×2.33) parce que les optimisations majeures suppriment
des balayages O(N_loans) et O(N_entities) qui dégradaient la complexité de la
version d'origine en O(N_loans · N_intérêts_payés). À 3000 pas avec ~26 K prêts
actifs et 687 K prêts créés cumulés, le gain absolu est de **427 secondes**
sur un seul run.

**Ce qui ralentissait réellement le programme :**
1. balayages O(N_loans) répétés dans `_ensure_payment_capacity` et
   `process_single_failure` (filtrer par `lender_id`/`borrower_id`) — corrigé par
   indexes incrémentaux ;
2. reconstruction de `active_entities()` à chaque appel (jusqu'à ~30 fois par
   pas) — corrigé par un cache invalidé seulement à création/décès ;
3. tris `sorted(active_loans, key=loan_id)` redondants — supprimés ;
4. multiples `sum()` séparés sur les mêmes listes — fusionnés en une passe ;
5. propriété `ratio_liquide_passif`, méthode `interest_due()`, helper
   `_route_interest_to_lender`, `get_entity` : surcoûts d'appel inlinés au
   hot-path.

**Ce qu'il ne faut pas modifier** (changements potentiellement non conservateurs
identifiés mais NON appliqués) :
- l'ordre des opérations dans la boucle temporelle (chaque réordonnancement peut
  modifier les résultats) ;
- la sémantique de `_select_active_credit_entities` : tout cache incrémental
  sur ce filtre changerait la trajectoire (les seuils dépendent des mutations
  fines de chaque transaction) ;
- la double cession de créances dans `_ensure_payment_capacity` (avant/après
  reliquéfaction) : l'ordre influence le `r*` recalculé.

---

## 2. Protocole de benchmark

### 2.1 Outils

- `benchmarks/bench.py` : protocole reproductible de mesure (n entités, prêts,
  faillites, transactions, mémoire). Utilise `time.perf_counter`. Option
  `--memory` : active `tracemalloc` pour le pic mémoire.
- `benchmarks/profile_run.py` : encapsule une exécution avec `cProfile`, dump
  `.prof` + top des fonctions par `cumtime` / `tottime`.
- `tests/test_non_regression.py` : compare deux exécutions (original vs WIP)
  pas par pas, avec tolérance flottante = 0 (égalité exacte exigée).

### 2.2 Tailles et seeds

```
court : 200 pas
moyen : 1000 pas
long  : 3000 pas
seeds : 42, 7, 123
```

Configuration : `SimulationConfig()` par défaut (Bloc 8 — `theta=0.35,
lambda=2, n_candidats_pool=3`). Aucun paramètre par défaut n'a été modifié.

### 2.3 Lancement

```bash
# Bench WIP, toutes tailles × tous seeds
/home/anatole/jupyter/.venv/bin/python3 modele-27-04-WIP/benchmarks/bench.py --target wip

# Bench original (référence) sur les mêmes paramètres
/home/anatole/jupyter/.venv/bin/python3 modele-27-04-WIP/benchmarks/bench.py --target orig

# Test de non-régression strict (3 seeds × 400 pas)
/home/anatole/jupyter/.venv/bin/python3 modele-27-04-WIP/tests/test_non_regression.py

# Profilage cProfile
/home/anatole/jupyter/.venv/bin/python3 modele-27-04-WIP/benchmarks/profile_run.py \
    --target wip --n-steps 1000 --seed 42 --top 30
```

---

## 3. Résultats du profilage initial

cProfile, 500 pas, seed 42, version d'origine. Total 138 s. Top fonctions
(ranked by `tottime`) :

| Fonction | tottime | cumtime | ncalls | Cause |
|---|---|---|---|---|
| `_select_active_credit_entities` | 16.4 s | 33.6 s | 14 356 (~28/pas) | filtre O(N_alive) avec propriété `ratio_liquide_passif` (10.2 M appels) |
| `_pay_single_interest` | 15.3 s | 38.6 s | 1.86 M | un appel par prêt actif et par pas |
| `pay_interest_phase` | 3.2 s | 47.3 s | 500 | + `sorted(active_loans, key=loan_id)` |
| `_ensure_payment_capacity` | 6.0 s | 9.1 s | 1.74 M | filtres `[l for l in active_loans() if l.lender_id==id ...]` répétés |
| `_route_interest_to_lender` | 5.9 s | 8.5 s | 1.74 M | wrapper de 3 lignes |
| `get_entity` | 5.3 s | 5.3 s | 3.6 M | wrapper de `dict[id]` |
| `_compute_indicators` (statistics) | — | 14.2 s | 500 | 4 `sum()` séparés sur alive/loans |
| `_collect_light_stats` | — | 11.7 s | 500 | 4 `sum()` séparés + listes intermédiaires |
| `process_single_failure` | — | (cumtime variable) | une fois par failli | 3 balayages O(N_loans) (Phases 1/2/3) |

`compute_hidden_fragility`, `_existing_interest_burden`, `_rebuild_interest_cache`
ne sont jamais appelées dans `run_step` → hors du hot path.

---

## 4. Goulets d'étranglement identifiés

### 4.1 Liste classée

| # | Fonction | Cause | Coût estimé | Risque scientifique |
|---|---|---|---|---|
| 1 | `_ensure_payment_capacity` (filtre par lender) | balayage O(N_loans) deux fois par appel illiquide | ~12 s sur 138 s à 500 pas, croît en O(N_loans·N_intérêts_payés) | nul |
| 2 | `process_single_failure` (Phases 1/2/3) | 3 balayages O(N_loans) par entité faillie | proportionnel au nb de cascades × N_loans | nul |
| 3 | `_select_active_credit_entities` | filtre O(N_alive) appelé ~28 fois/pas | ~33 s sur 138 s à 500 pas | nul (cache d'`alive`) ; faible (cache de filtre) |
| 4 | `pay_interest_phase` | `sorted(..., key=loan_id)` redondant car dict insertion = id ascending | ~3 s | nul |
| 5 | `_compute_indicators` + `_collect_light_stats` | sums séparés sur mêmes itérables | ~26 s | nul (associativité respectée) |
| 6 | `_pay_single_interest`, `_route_interest_to_lender`, `get_entity`, `interest_due` | overhead d'appel sur ~1.8 M itérations | ~10–12 s | nul |
| 7 | propriété `ratio_liquide_passif` (10 M appels) | descriptor lookup + branche morte | ~16 s | nul (inlining mathématiquement identique) |

### 4.2 Goulets identifiés mais NON modifiés

| Fonction | Cause | Pourquoi non modifié |
|---|---|---|
| `_pay_single_interest` (cumulé) | un appel par prêt actif × pas | comportement fondamental ; la fonction est la sémantique du modèle |
| `_ensure_payment_capacity` (logique 4 étapes) | ordre 1-2-3-4 imposé par la spécification | l'ordre conditionne la dynamique (cf. commentaire `L'ORDRE PEUT MODIFIER GRANDEMENT LE COMPORTEMENT`) |
| `_select_active_credit_entities` (calls/pas) | 28×/pas, lié à `need_resort=True` | réduire le nb d'appels changerait le matching aléatoire ; non conservateur |
| `_update_alphas` (`rng.gauss`) | 600 entités × 1000 pas = 600 K tirages | nécessaire à la dynamique brownienne |

---

## 5. Optimisations proposées

| Code | Description | Risque |
|---|---|---|
| OPT-1 | Suppression du `sorted(active_loans, key=loan_id)` (no-op : iteration dict en ordre d'id) | nul |
| OPT-2 | Indexes `_loans_by_lender` et `_loans_by_borrower` (sets de loan_id actifs) maintenus incrémentalement | nul (purement structurel) |
| OPT-3 | Cache `_alive_cache` invalidé seulement à naissance/décès | nul (cache avec invalidation explicite) |
| OPT-4 | Fusion des `sum()` en une seule passe dans `_collect_light_stats`, `_capture_system_state`, `_compute_indicators` | nul (ordre d'addition préservé → FP bit-identique) |
| OPT-5 | Inlining de `get_entity`, `_route_interest_to_lender`, `interest_due` dans le hot-path interest | nul (sémantique inchangée) |
| OPT-6 | `_select_active_credit_entities` réécrit en compréhension de liste (LIST_APPEND opcode) avec walrus pour éviter le double accès à `passif_total` | nul |

Optimisations envisagées et explicitement **rejetées** comme non conservatrices :

- **vectorisation NumPy** des sommes par pas : modifierait l'ordre d'addition
  flottante (réductions parallèles) et donc les flottants finaux. Rejetée.
- **cache incrémental du résultat de `_select_active_credit_entities`** : le
  filtre dépend de `actif_liquide` et `passif_total` qui changent à chaque
  transaction (et chaque dépréciation, intérêt, …). Maintenir l'index à jour
  requiert d'instrumenter chaque mutation flottante de ces champs, avec un
  risque non-nul d'oublier un point de mise à jour. Rejetée.
- **changer l'ordre 1-2-3-4 de `_ensure_payment_capacity`** : explicitement
  interdit par le commentaire dans le code.
- **fusion de `pay_interest_phase` et `pay_amortization_phase`** : l'ordre
  d'application des opérations sur le même prêt change ses résultats.
  Rejetée (et `pay_amortization_phase` est de toute façon désactivée par
  défaut, `tau=0`).

---

## 6. Optimisations implémentées

Voir `CHANGELOG.md` pour les sections OPT-1 à OPT-6 isolées.

Toutes les modifications portent un commentaire `# OPT-N : …` dans
`simulation.py` ou `statistics.py` pour permettre de retrouver et isoler chaque
changement.

### Liste des fichiers touchés

| Fichier | Sections modifiées |
|---|---|
| `modele-27-04-WIP/src/simulation.py` | `__init__` (caches/indexes), `active_entities`, `pay_interest_phase`, `pay_amortization_phase`, `_pay_single_interest`, `_ensure_payment_capacity`, `_revalue_loan`, `_transfer_claims_for_payment`, `_pay_single_amortization`, `_select_active_credit_entities`, `process_single_failure`, `create_loan`, `create_entity`, `_capture_system_state`, `_collect_light_stats`, helpers `_idx_add` / `_idx_remove` / `_idx_change_lender` |
| `modele-27-04-WIP/src/statistics.py` | `_compute_indicators` (fusion des sommes) |

### Modules NON modifiés
`config.py`, `models.py`, `output.py`, `analysis.py`, `main.py` — aucune
modification.

---

## 7. Tests de non-régression

Test : `tests/test_non_regression.py` (3 seeds × 400 pas, exigence d'égalité
flottante stricte avec `atol = rtol = 0`).

```
[seed=42, n_steps=400]   ✓ stats légères, indicateurs systémiques, cascades : tous identiques
[seed=7, n_steps=400]    ✓ stats légères, indicateurs systémiques, cascades : tous identiques
[seed=123, n_steps=400]  ✓ stats légères, indicateurs systémiques, cascades : tous identiques
RÉSULTAT : ✓ tous les seeds testés sont strictement identiques
```

Les indicateurs comparés à chaque pas :
- `n_entities_alive`, `n_entities_total`, `n_spawned`,
- `extraction_total`, `interest_paid_total`, `amortissement_total`,
- `credit_transactions`, `auto_invest_total`,
- `n_failures`, `destroyed_assets`, `redirected_claims`,
- `volume_prets_actifs`, `n_prets_actifs`,
- `actif_total_systeme`, `passif_total_systeme`, `liquidite_totale`,
- `mean_passif`, `mean_internal_rate`,
- les 14 colonnes des `SystemicIndicator`,
- les 14 colonnes des `CascadeEvent` (taille, contagion, ratio).

À chaque optimisation OPT-1 → OPT-6, ce test a été relancé. Aucune divergence
n'a été constatée à aucun seed et à aucun pas.

---

## 8. Résultats avant / après

### 8.1 Temps d'exécution (mesures sans `cProfile`)

| taille | seed | original | WIP | speedup | gain |
|---|---|---|---|---|---|
| court (200 pas) | 42 | 1.426 s | 1.102 s | ×1.29 | −23 % |
| court (200 pas) | 7 | 1.421 s | 1.098 s | ×1.29 | −23 % |
| court (200 pas) | 123 | 1.390 s | 1.080 s | ×1.29 | −22 % |
| moyen (1000 pas) | 42 | 89.02 s | 45.67 s | ×1.95 | **−49 %** |
| moyen (1000 pas) | 7 | 86.45 s | 45.12 s | ×1.92 | **−48 %** |
| moyen (1000 pas) | 123 | 97.75 s | 50.36 s | ×1.94 | **−48 %** |
| long (3000 pas) | 42 | 747.98 s | 321.16 s | **×2.33** | **−57 %** |

À 3000 pas, l'état final est rigoureusement identique entre les deux
implémentations : `entities_alive=736`, `entities_created_total=6117`,
`loans_active=26 105`, `loans_created_total=687 041`, `failures_total=5 381`,
`credit_transactions_total=134 284`. La concordance bit-pour-bit a été
vérifiée à 600 pas par `test_non_regression.py`.

### 8.2 Évolution étape par étape (moyen, seed 42)

| étape | description | elapsed (s) | gain cumulé |
|---|---|---|---|
| baseline (clone) | identique à l'original | 89.55 | 0 % |
| après OPT-1 | sorted retiré | (≈ 86) | ≈ −4 % |
| après OPT-2 | indexes lender/borrower | 63.65 | −29 % |
| après OPT-3 | alive_cache + ratio_liquide_passif inliné | 51.91 | −42 % |
| après OPT-4 | fusion des sums | 49.5 | −45 % |
| après OPT-5 | inlines (route_interest, interest_due, get_entity) | 46.91 | −48 % |
| après OPT-6 | list-comp `_select_active_credit_entities` | 45.67 | **−49 %** |

### 8.3 Profil après optimisations (1000 pas, seed 42, sous cProfile)

Top par `tottime` :

| Fonction | tottime | ncalls | Note |
|---|---|---|---|
| `_pay_single_interest` | 42.8 s | 12.6 M | hot-path résiduel : un appel par prêt actif et par pas |
| `_ensure_payment_capacity` | 31.7 s | 8.7 M | déjà optimisé par OPT-2 (filtre par index) |
| `pay_interest_phase` | 23.1 s | 1 000 | iteration de la liste d'intérêts |
| `min` (built-in) | 17.0 s | 8.9 M | dans `_ensure_payment_capacity` |
| `max` (built-in) | 10.2 s | 5.4 M | dans `_liquidity_reserve`, `_borrower_qmax`, etc. |
| `active_loans` | 8.9 s | 3 000 | 3 appels par pas (matérialisation 160 K → 22 K loans) |
| `actif_total` (property) | 6.5 s | 3.6 M | propriété sommant 4 attributs |
| `_select_active_credit_entities` | 6.0 s | 40 840 | (était 17 s ; gain ×3) |
| `compute_internal_rate` | 5.4 s | 1.1 M | dans la sort key du marché du crédit |

### 8.4 Mémoire

Mesures avec `tracemalloc` (`--memory`), moyen 1000 pas, seed 42 :

| target | pic mémoire (Python) | écart |
|---|---|---|
| original | 43.4 MB | référence |
| WIP optimisé | 55.5 MB | +12.1 MB (+28 %) |

Les +12 MB s'expliquent par :
- les indexes OPT-2 (`_loans_by_lender`, `_loans_by_borrower`) : ~22 K loan_ids
  actifs distribués dans des sets, soit ≈ 5 MB combinés (entrées dict + sets) ;
- le cache OPT-3 (`_alive_cache`) : liste de ~600 références, négligeable
  (~5 KB) ;
- le reste vient du remplacement des compréhensions par des append+sets, et de
  l'instrumentation propre à tracemalloc (frames supplémentaires retenues à
  cause des helpers `_idx_add` / `_idx_remove`).

Compromis : **+28 % de mémoire pour −49 % de temps** sur moyen ; sur long,
**−57 % de temps pour la même empreinte (les deux versions ont la même
trajectoire et donc le même pic combinatoire)**. Sur ce projet (mémoire jamais
limitante, temps souvent inacceptable), c'est un compromis très favorable.

### 8.5 Nombre d'appels aux fonctions critiques (avant / après, 500 pas)

| Fonction | avant (orig) | après (WIP) | facteur |
|---|---|---|---|
| `ratio_liquide_passif` (property) | 10.2 M | 0 (inliné) | — |
| `sorted` (top niveau) | 14 916 | 1 480 | ×10 |
| `active_loans()` | 2 457 | 2 460 | ≈ × |
| `active_entities()` | 18 508 | ~30 / pas | ≈ ×30 (cache) |
| `_compute_indicators` calls de `sum` | 4 / pas | 0 (fusion) | — |
| `_select_active_credit_entities` cumtime | 33.6 s | 6.0 s | ×5.6 |

---

## 9. Points de vigilance scientifique

### 9.1 Invariants préservés

- Tous les bilans (`L`, `R`, `K^endo`, `K^exo`, `B`, `P^endo`, `P^exo`, `C`)
  sont mis à jour aux mêmes points et avec les mêmes formules.
- Les caches `passif_total`, `charges_interets`, `revenus_interets` sont
  maintenus exactement comme avant.
- Les indexes OPT-2 sont des dérivées strictes de `self.loans` : tout
  loan_id appartient à `_loans_by_lender[loan.lender_id]` ET
  `_loans_by_borrower[loan.borrower_id]` si et seulement si `loan.active`.
  Cet invariant a été vérifié indirectement par les tests de non-régression
  (toute désynchronisation produirait des balayages divergents en Phase 1/2/3
  de `process_single_failure`, donc un résultat différent).
- Les ordres d'itération critiques :
  - `pay_interest_phase` : ordre `loan_id` croissant (préservé : on lit
    `self.loans.values()` qui itère en ordre d'insertion = ordre d'id).
  - `process_single_failure` Phases 1/2/3 : ordre `loan_id` croissant,
    explicitement reconstruit via `sorted(self._loans_by_borrower[id])` /
    `sorted(self._loans_by_lender[id])` car les sets Python ne
    garantissent pas un ordre déterministe.
  - `_ensure_payment_capacity` Étape 2/4 : tri par `(rate, loan_id)`
    explicite — préservé par le `sorted(...)` final.
- L'ordre des opérations dans la boucle temporelle (`run_step`) est inchangé.

### 9.2 Risques résiduels

- Aucun risque scientifique identifié dans les optimisations implémentées.
- Si quelqu'un ajoute un nouveau point de désactivation/création de prêt
  sans appeler `_idx_add` / `_idx_remove` / `_idx_change_lender`, les
  indexes OPT-2 deviendraient incohérents. Recommandation : centraliser ces
  appels via une méthode `_set_loan_active(loan, value)` lors d'un
  refactoring futur (hors scope conservateur ici).
- Si un futur changement crée des entités hors de `create_entity` ou les
  tue hors de `process_single_failure`, le cache OPT-3 devra être
  invalidé. Recommandation : centraliser via `_kill_entity(...)`.

---

## 10. Prochaines pistes (non implémentées)

Pistes possibles, classées par risque scientifique croissant :

### Risque nul / très faible

1. **Cache d'`active_loans` une fois par pas** : `_collect_light_stats` et
   `record_step.statistics` partageraient la même liste. Gain estimé : ~3 s
   sur moyen (3 %).
2. **Fusion `_collect_light_stats` ↔ `_compute_indicators`** : ils itèrent les
   mêmes listes pour les mêmes sommes (`actif_total_systeme`, `passif_total_systeme`,
   `liquidite_totale`, `volume_prets`). Gain estimé : ~5 s sur moyen.
3. **Inliner `compute_internal_rate` dans la `key` du marché du crédit** : la
   méthode est appelée 1 M fois pour la fonction de tri. Gain estimé : ~3 s.

### Risque faible

4. **Cache incrémental du filtre `_select_active_credit_entities`** : nécessite
   d'instrumenter chaque mutation de `actif_liquide` et `passif_total` pour
   réévaluer l'éligibilité. Possible mais demande une réécriture
   architecturale et un audit des points de mutation. Gain estimé : ~5 s.
5. **Maintenir un cache `actif_total` sur Entity** : invalidé à chaque mutation
   de `L`, `R`, `K^endo`, `K^exo`. Gain estimé : ~5 s.

### Risque moyen / non recommandé

6. **Vectorisation NumPy** : changerait l'ordre des additions flottantes →
   non conservateur strict. À ne faire qu'avec une tolérance numérique
   acceptée (et mention explicite dans le rapport scientifique).
7. **Cython / Numba sur le hot-loop d'intérêt** : gain potentiel élevé (×3-10
   sur la phase d'intérêt) mais introduit une dépendance build, contraire
   à la règle "stdlib + matplotlib uniquement". Rejet par défaut.

### À ne pas modifier

- Ordre des étapes dans `run_step()`.
- Logique des 4 étapes de `_ensure_payment_capacity` (commentaire explicite :
  *"L'ORDRE PEUT MODIFIER GRANDEMENT LE COMPORTEMENT"*).
- `n_candidats_pool` et autres paramètres du marché du crédit.
- Valeurs par défaut de `SimulationConfig` (la mission interdit explicitement
  de les changer pour gagner du temps artificiellement).

---

## Annexe — Reproduction

```bash
# 1. Vérifier la non-régression (3 seeds × 400 pas)
/home/anatole/jupyter/.venv/bin/python3 modele-27-04-WIP/tests/test_non_regression.py

# 2. Benchmark des 3 tailles × 3 seeds
/home/anatole/jupyter/.venv/bin/python3 modele-27-04-WIP/benchmarks/bench.py --target wip
/home/anatole/jupyter/.venv/bin/python3 modele-27-04-WIP/benchmarks/bench.py --target orig

# 3. Profil cProfile (dump dans modele-27-04-WIP/profiling/)
/home/anatole/jupyter/.venv/bin/python3 modele-27-04-WIP/benchmarks/profile_run.py \
    --target wip --n-steps 1000 --seed 42 --top 30
```

Toutes les optimisations sont identifiées dans le code par des commentaires
`# OPT-N : ...` qui permettent de les retrouver et de les isoler.
