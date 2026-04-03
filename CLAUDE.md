# CLAUDE.md — Index de travail

## Project

Simulation multi-agents d'entités économiques abstraites échangeant une ressource unique : le **joule**.
Modélise une société industrielle simplifiée avec prêts, faillites en cascade, indicateurs systémiques.
Projet de recherche académique — pas d'application web, pas d'API, pas de déploiement.

**Lire avant d'agir** :
- `claude3-v3-27-mars/src/config.py` — tous les paramètres du modèle
- `claude3-v3-27-mars/src/simulation.py` — moteur principal
- `ORGANISATION_ACTIVE_27_MARS.md` — quelle version est active

---

## Tech Stack

- **Langage** : Python 3 (stdlib + matplotlib)
- **Frameworks** : aucun (dataclasses stdlib, `random.Random`)
- **Venv** : `/home/anatole/jupyter/.venv` — utiliser TOUJOURS ce Python
- **Python** : `/home/anatole/jupyter/.venv/bin/python3`
- **Build** : aucun
- **Tests** : assertions Python plain (`tests/test_basic.py`) — pas de pytest
- **Lint/format** : `black` disponible dans le venv
- **Git hooks** : `hooks/` (activer avec `git config core.hooksPath hooks`)

---

## Repo Map

```
jupyter/
├── claude3-v3-27-mars/       ← VERSION ACTIVE (seule cible de développement)
│   ├── src/
│   │   ├── config.py         ← paramètres (lire en premier)
│   │   ├── models.py         ← Entity, Loan, BankruptcyEstate
│   │   ├── simulation.py     ← moteur (run_step, marché du crédit)
│   │   ├── statistics.py     ← Collector, distributions, cascades
│   │   ├── output.py         ← dossiers de sortie auto-labellisés
│   │   ├── analysis.py       ← graphiques, log-binning
│   │   └── main.py           ← point d'entrée
│   └── tests/
│       └── test_basic.py     ← 11 tests de validation
├── claude/                   ← v1 monolithique (archive, ne pas modifier)
├── claude3-v2/               ← v2 modulaire stable (archive, ne pas modifier)
├── arborescence_modeles/     ← symlinks organisateurs (ne pas modifier)
├── banque_versions_zip/      ← archives ZIP de versions supprimées
├── hooks/                    ← git hooks (pre-commit, commit-msg)
└── .venv/                    ← environnement Python
```

---

## Commands

```bash
# Lancement simulation
cd claude3-v3-27-mars/src
/home/anatole/jupyter/.venv/bin/python3 main.py

# Tests
cd claude3-v3-27-mars
/home/anatole/jupyter/.venv/bin/python3 tests/test_basic.py

# Format
/home/anatole/jupyter/.venv/bin/black claude3-v3-27-mars/src/

# Activer les git hooks
git config core.hooksPath hooks

# Vérifier la syntaxe d'un fichier
/home/anatole/jupyter/.venv/bin/python3 -m py_compile claude3-v3-27-mars/src/<fichier>.py
```

Résultats générés dans : `claude3-v3-27-mars/src/resultats/`

---

## Coding Conventions

- **Style** : Python idiomatique, black pour le formatage
- **Nommage** : `snake_case` pour tout (variables, fonctions, fichiers)
- **Modèles** : dataclasses typées (`@dataclass`), jamais de dicts ad hoc pour les entités
- **Références** : par ID entier (`Dict[int, Entity]`), pas de références directes entre objets
- **RNG** : `random.Random(seed)` isolé — ne jamais utiliser `random` global
- **Modules** : un rôle par fichier (config / models / simulation / statistics / output / analysis)
- **Commentaires** : docstring de module en tête de fichier ; commenter les invariants non évidents
- **Dépendances** : stdlib uniquement + matplotlib — ne pas ajouter de dépendances sans nécessité absolue
- **Cache incrémental** : tout `loan.active = False` dans `simulation.py` doit être accompagné de mises à jour de `revenus_interets` / `charges_interets` (enforced par pre-commit)
- **Invariant critique** : `_rebuild_interest_cache()` interdit dans `run_step` (enforced par pre-commit)

---

## Working Rules for Claude

- Lire `config.py` et `simulation.py` avant toute modification
- Ne pas modifier les versions archivées (`claude/`, `claude3-v2/`) sauf demande explicite
- Proposer des changements petits et ciblés — un diff minimal par intention
- Citer systématiquement les fichiers touchés (`fichier.py:ligne`)
- Expliciter toute hypothèse sur le comportement du modèle
- Ne jamais inventer un comportement non vérifié dans le code
- Ne pas ajouter de dépendances externes sans accord explicite
- Ne pas restructurer l'architecture sans nécessité démontrée

---

## 95% Confidence Rule

Si Claude n'est pas à ≥ 95 % certain d'un fait sur ce projet, il doit le signaler explicitement.

Distinguer clairement :
- **Fait observé** : lu directement dans le code ou les fichiers
- **Inférence** : déduit du contexte — à signaler comme tel
- **Incertitude** : rechercher dans le repo avant de supposer

En cas de doute sur un paramètre, un comportement ou une convention : lire le fichier source, pas mémoriser.

---

## Source of Truth

- **Paramètres du modèle** → `claude3-v3-27-mars/src/config.py`
- **Comportement de simulation** → `claude3-v3-27-mars/src/simulation.py`
- **Version active** → `ORGANISATION_ACTIVE_27_MARS.md`
- **Versions archivées** → `arborescence_modeles/INDEX_ARBORESCENCE.md`
- **Archives ZIP** → `banque_versions_zip/INDEX_ZIP.md`
- **Théorie du modèle** → `claude3-v3-27-mars/description_theorisation_modele.pdf`
- En cas de contradiction entre mémoire et code : **le code fait foi**
