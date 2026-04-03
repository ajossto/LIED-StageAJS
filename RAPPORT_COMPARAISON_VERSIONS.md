# Rapport d'audit des versions du modèle (03 avril 2026)

## 1) Versions analysées

- `claude/`
- `claude3-v2/`
- `claude3-v3-25-mars-sans-banque/`
- `claude3-v3-27-mars/`
- `claude3 - Premier modèle fonctionnel/`
- `claude_nouveau/`
- `claude3 (Copie)/`
- `claude_nouveau (Copie)/`

## 2) Diagnostic rapide (exécution des tests)

| Version | Commande test | Résultat | Lecture rapide |
|---|---|---:|---|
| `claude/` | `python3 claude/tests.py` | ✅ 10/10 | Ancienne base monolithique, stable sur sa suite de tests. |
| `claude3-v2/` | `python3 'claude3-v2/tests/test_basic.py'` | ✅ 11/11 | Version modulaire hybride la plus stable côté exécution. |
| `claude3-v3-27-mars/` | `python3 'claude3-v3-27-mars/tests/test_basic.py'` | ❌ ImportError | Incohérence API entre `tests/` et `src/models.py` (classe attendue absente/renommée). |
| `claude3 - Premier modèle fonctionnel/` | `python3 'claude3 - Premier modèle fonctionnel/tests/test_basic.py'` | ❌ 9/11 | Régression: méthode `_borrow_is_acceptable` manquante. |
| `claude_nouveau/` | `python3 'claude_nouveau/tests/test_basic.py'` | ❌ 1/11 | Régression importante: `Collector.register_entity` manquante. |

## 3) Différences structurelles majeures

### A. Lignée « monolithique »
- `claude/` : architecture unique fichier central (`simulation.py`) + scripts d'analyse séparés.
- Points forts : simplicité, cohérence interne, tests verts.
- Limites : extensibilité et maintenance plus difficiles.

### B. Lignée « modulaire hybride »
- `claude3-v2/`, `claude_nouveau/`, `claude3 - Premier modèle fonctionnel/`, `claude3-v3-27-mars/` : séparation en `src/{models,config,simulation,statistics,analysis,output}.py`.
- Points forts : meilleure modularité et instrumentation statistique.
- Risques observés : dérives d'interface entre versions (tests non alignés avec le code).

### C. Statut de `claude3-v3-27-mars`
- C'est bien la version la plus riche en artefacts de conception (PDF/txt d'analyse, changelog, etc.).
- Mais l'état exécutable n'est pas aligné avec la suite de tests incluse.
- Donc: **candidate "source intellectuelle" principale**, mais pas encore **candidate "main exécutable"** sans consolidation.

## 4) Renommage recommandé (canonique)

Objectif : rendre l'historique lisible et éviter les ambiguïtés (`Copie`, `nouveau`, etc.).

- `claude/` → `archive_v1_monolithique_stable/`
- `claude3-v2/` → `baseline_v2_modulaire_stable/`
- `claude3-v3-25-mars-sans-banque/` → `archive_v3_25mars_sans_code/`
- `claude3-v3-27-mars/` → `candidate_v3_27mars_reference/`
- `claude3 - Premier modèle fonctionnel/` → `archive_v3_premier_modele_regression/`
- `claude_nouveau/` → `archive_v3_nouveau_regression/`
- `claude3 (Copie)/` → `archive_duplicate_claude3/`
- `claude_nouveau (Copie)/` → `archive_duplicate_nouveau/`

> Remarque : ce renommage est proposé pour l'organisation. Il peut être effectué en une passe dédiée quand tu valides la nomenclature.

## 5) Proposition pour construire la future `main`

### Étape 1 — Base de travail immédiate
Prendre `claude3-v2/` comme base exécutable (11/11 tests) pour sécuriser le flux de développement.

### Étape 2 — Intégration sélective de `27-mars`
Importer depuis `claude3-v3-27-mars/` uniquement les éléments validés (théorie, analyses, éventuellement fonctions de simulation), avec tests de non-régression à chaque migration.

### Étape 3 — Contrat d'API unique
Figer une API de référence pour :
- `models.py` (noms de classes exportées),
- `statistics.py` (méthodes attendues, ex. `register_entity`),
- `simulation.py` (méthodes appelées par tests, ex. `_borrow_is_acceptable` ou son remplaçant).

### Étape 4 — Validation continue
À chaque merge:
1. tests unitaires,
2. simulation courte smoke test,
3. contrôle des sorties CSV,
4. vérification des graphes (si matplotlib présent).

## 6) Décision recommandée aujourd'hui

- **Ne pas basculer immédiatement `main` sur `claude3-v3-27-mars` sans patch de compatibilité**.
- Utiliser `claude3-v2` comme socle technique provisoire.
- Ouvrir ensuite une branche d'intégration `v3-27mars-hardening` pour converger vers la version finale.
