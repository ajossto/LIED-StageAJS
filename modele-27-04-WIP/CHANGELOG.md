# Changelog — modele-27-04-WIP

Optimisations conservatrices (sans modification de la dynamique du modèle).
Chaque entrée donne :
- ce qui change (et POURQUOI ce n'est pas une modification scientifique),
- résultat des tests de non-régression (`tests/test_non_regression.py`),
- mesures benchmark (`benchmarks/bench.py`).

Référence : tous les nombres sont mesurés sur la même machine. CPython 3.12.3,
`random.Random(seed)` isolé. Tests de non-régression à atol = rtol = 0
(égalité flottante stricte exigée).

---

## OPT-0 — Clone fidèle (baseline)

- Copie strictement identique de `Modèle_sans_banque_wip/src/` → `modele-27-04-WIP/src/`.
- Test de non-régression : ✓ (3 seeds × 400 pas).

| size  | seed | n_steps | elapsed_s | ms/step |
|-------|------|---------|-----------|---------|
| court | 42   | 200     | 1.440     | 7.20    |
| moyen | 42   | 1000    | 89.55     | 89.55   |

---

## OPT-1 — Suppression du `sorted` redondant

**Fichiers** : `simulation.py:pay_interest_phase`, `pay_amortization_phase`.

**Changement** : `for loan in sorted(self.active_loans(), key=lambda x: x.loan_id)`
→ `for loan in self.active_loans()`.

**Justification de neutralité** :
- `self.next_loan_id` est strictement monotone croissant (incrémenté de 1 à
  chaque allocation).
- CPython 3.7+ garantit l'ordre d'insertion pour `dict`.
- Donc `self.loans.values()` itère en ordre `loan_id` croissant.
- `active_loans()` matérialise déjà la liste filtrée → le tri par loan_id était
  un no-op coûteux O(N log N).

**Risque scientifique** : nul.

**Test de non-régression** : ✓ (3 seeds × 400 pas).

---

## OPT-2 — Indexes `_loans_by_lender` et `_loans_by_borrower`

**Fichiers** : `simulation.py:__init__`, `_idx_add`, `_idx_remove`,
`_idx_change_lender` (nouveaux), `create_loan`, `_revalue_loan`,
`_transfer_claims_for_payment`, `_pay_single_amortization`,
`_ensure_payment_capacity`, `process_single_failure`.

**Changement** : ajout de deux dicts `Dict[int, set[int]]` qui mappent
`entity_id → {loan_id actifs}`. Maintenus incrémentalement à chaque création /
désactivation / changement de prêteur.

**Effet** :
- `_ensure_payment_capacity` : `[l for l in self.active_loans() if l.lender_id == X ...]`
  (O(N_loans)) → `[self.loans[lid] for lid in self._loans_by_lender[X] ...]`
  (O(loans-de-X)).
- `process_single_failure` Phases 1/2/3 : balayage de `self.active_loans()`
  filtré → itération directe de l'index.

**Justification de neutralité** : les indexes contiennent exactement les mêmes
prêts que le filtre (par invariant). L'ordre d'itération est restauré par tri
explicite (`sorted(..._by_borrower[id])`) là où il influence l'ordre des
sommes flottantes (Phase 1, 3 de `process_single_failure`).

**Risque scientifique** : nul.

**Test de non-régression** : ✓ (3 seeds × 400 pas, dont cascades).

| size  | seed | elapsed_s | gain vs baseline |
|-------|------|-----------|------------------|
| court | 42   | 1.434     | −0 % (pas de faillites donc index inactif) |
| moyen | 42   | 63.65     | **−29 %** |
| moyen | 7    | 61.61     | **−29 %** |

---

## OPT-3 — Cache `_alive_cache` + inline de `ratio_liquide_passif`

**Fichiers** : `simulation.py:__init__`, `active_entities`, `create_entity`,
`process_single_failure`, `_select_active_credit_entities`.

**Changement** :
- Cache `self._alive_cache: List[Entity]` avec drapeau `_alive_cache_dirty`.
  Reconstruit lazily au prochain appel à `active_entities()` après un
  événement de naissance ou décès.
- `_select_active_credit_entities` : la propriété `e.ratio_liquide_passif`
  est inlinée (`e.actif_liquide / p`). La branche morte
  `passif_total <= 0 → +inf` est éliminée puisque le filtre en amont impose
  déjà `p > eps`.

**Justification de neutralité** :
- Le cache se base uniquement sur la liste des entités vivantes — la
  composition `alive` ne change que dans `create_entity` (naissance) et
  `process_single_failure` (mort), ces deux points marquent le cache dirty.
  Les autres phases (extract, depreciation, market…) n'altèrent pas
  `e.alive`.
- L'expression inlinée `e.actif_liquide / p > s` est strictement identique à
  `e.ratio_liquide_passif > s` quand `p > eps > 0` — même division, mêmes
  flottants.

**Risque scientifique** : nul.

**Test de non-régression** : ✓ (3 seeds × 400 pas).

| size  | seed | elapsed_s | gain vs baseline |
|-------|------|-----------|------------------|
| court | 42   | 1.172     | −19 % |
| moyen | 42   | 51.91     | **−42 %** |
| moyen | 7    | 51.88     | **−40 %** |

---

## OPT-4 — Fusion des sommes en passe unique

**Fichiers** : `simulation.py:_collect_light_stats`, `_capture_system_state` ;
`statistics.py:_compute_indicators`.

**Changement** : remplacement des 4-6 `sum(... for ... in alive)` /
`sum(... for ... in active_loans)` par une seule boucle `for` qui accumule
les agrégats (`actif_total`, `passif_total`, `liquidite`, `volume_prets`,
concentration de Herfindahl…).

**Justification de neutralité** : l'ordre d'addition est strictement
préservé. `sum(g)` accumule dans l'ordre du générateur ; ma boucle accumule
dans l'ordre de la liste. Comme `alive` et `active_loans` sont les mêmes
listes itérées dans le même ordre, le résultat flottant est bit-pour-bit
identique.

**Risque scientifique** : nul.

**Test de non-régression** : ✓.

---

## OPT-5 — Inlines hot-path interest

**Fichiers** : `simulation.py:_pay_single_interest`.

**Changement** : `self.get_entity(...)` → `self.entities[...]` ;
`loan.interest_due()` → `loan.principal * loan.rate` (le `if loan.active` est
déjà testé en début de fonction) ; `self._route_interest_to_lender(loan, payment)`
inliné en 3 lignes locales.

**Justification de neutralité** : aucune logique modifiée, juste suppression
des appels de méthode wrapper.

**Risque scientifique** : nul.

**Test de non-régression** : ✓.

| size  | seed | elapsed_s | gain vs baseline |
|-------|------|-----------|------------------|
| court | 42   | 1.109     | −23 % |
| moyen | 42   | 46.91     | **−48 %** |
| moyen | 7    | 45.47     | **−48 %** |

---

## OPT-6 — `_select_active_credit_entities` réécrit en compréhension

**Fichiers** : `simulation.py:_select_active_credit_entities`.

**Changement** : remplacement de la boucle `for + append` par une
compréhension de liste avec walrus (`:=`) pour ne lire `e.passif_total`
qu'une seule fois.

**Justification de neutralité** : sémantique strictement identique. CPython
optimise les compréhensions de liste avec un opcode dédié `LIST_APPEND`,
plus rapide que l'append explicite.

**Risque scientifique** : nul.

**Test de non-régression** : ✓.

| size  | seed | elapsed_s | gain vs baseline |
|-------|------|-----------|------------------|
| court | 42   | 1.102     | −23 % |
| court | 7    | 1.098     | −23 % |
| court | 123  | 1.080     | −22 % |
| moyen | 42   | 45.67     | **−49 %** |
| moyen | 7    | 45.12     | **−48 %** |
| moyen | 123  | 50.36     | **−48 %** |

---

## Récapitulatif final

| Étape | court 42 (s) | moyen 42 (s) | gain moyen 42 |
|---|---|---|---|
| baseline (OPT-0) | 1.440 | 89.55 | 0 % |
| OPT-1 | ≈ 1.43 | ≈ 86 | −4 % |
| + OPT-2 | 1.434 | 63.65 | −29 % |
| + OPT-3 | 1.172 | 51.91 | −42 % |
| + OPT-4 | (mineur) | (≈ 49) | −45 % |
| + OPT-5 | 1.109 | 46.91 | −48 % |
| + OPT-6 | 1.102 | 45.67 | **−49 %** |

Speedup global mesuré (seed 42) :

| taille | n_steps | original | WIP | speedup | gain |
|---|---|---|---|---|---|
| court | 200 | 1.43 s | 1.10 s | ×1.30 | −23 % |
| moyen | 1000 | 89.0 s | 45.7 s | ×1.95 | −49 % |
| long | 3000 | **748 s** | **321 s** | **×2.33** | **−57 %** |

Le speedup croît avec la taille : optimisations qui suppriment des O(N²) implicites.
Résultats analogues sur seeds 7 et 123 (testés sur court+moyen).

Mémoire (moyen, tracemalloc) : 43.4 MB orig → 55.5 MB WIP (+28 %), dû aux
indexes incrémentaux OPT-2.

Toutes les modifications sont marquées `# OPT-N : …` dans le code source
pour permettre de les retrouver et les isoler.
