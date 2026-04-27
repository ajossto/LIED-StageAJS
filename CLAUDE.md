# CLAUDE.md — Index de travail

## Project

Simulation multi-agents d'entités économiques abstraites échangeant une ressource unique : le **joule**.
Modélise une société industrielle simplifiée avec prêts, faillites en cascade, indicateurs systémiques.
Projet de recherche académique — pas d'application web, pas d'API, pas de déploiement.

**Lire avant d'agir** :
- `modeles-systeme-physicoeconomique/modele_sans_banque_wip/model.py` — modèle WIP actuellement branché
- `simulation_lab/` — couche active d'orchestration locale
- `docs/ORGANISATION_ACTIVE_27_MARS.md` — note historique du 27 mars

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
├── simulation_lab/           ← interface locale + CLI + stockage
├── modeles-systeme-physicoeconomique/
│   ├── modele_sans_banque_wip/  ← modèle le plus abouti actuellement branché
│   └── claude3_v2/              ← second modèle intégré
├── archives/
│   └── modeles/
│       └── claude3-v3-27-mars/  ← archive complète de l'ancienne lignée 27 mars
├── claude/                   ← v1 monolithique (archive, ne pas modifier)
├── claude3-v2/               ← v2 modulaire stable (archive, ne pas modifier)
├── docs/                     ← documentation de travail et audits
├── recherche/                ← notes, visuels et analyses hors flux actif
├── arborescence_modeles/     ← symlinks organisateurs (ne pas modifier)
├── banque_versions_zip/      ← archives ZIP de versions supprimées
├── hooks/                    ← git hooks (pre-commit, commit-msg)
└── .venv/                    ← environnement Python
```

---

## Commands

```bash
# Lancement interface locale
cd /home/anatole/jupyter
/home/anatole/jupyter/.venv/bin/python3 -m simulation_lab.cli gui --open-browser

# Lister les modèles branchés
/home/anatole/jupyter/.venv/bin/python3 -m simulation_lab.cli list-models

# Validation historique ciblée si nécessaire
cd /home/anatole/jupyter/claude3-v2
/home/anatole/jupyter/.venv/bin/python3 tests/test_basic.py

# Activer les git hooks
git config core.hooksPath hooks

# Vérifier la syntaxe d'un fichier
/home/anatole/jupyter/.venv/bin/python3 -m py_compile simulation_lab/<fichier>.py
```

Résultats générés dans : `simulation_lab_data/` et, pour les modèles historiques, dans leurs dossiers `resultats/`

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

- Lire d'abord l'adaptateur WIP et `simulation_lab` avant toute modification
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

- **Modèle WIP branché** → `modeles-systeme-physicoeconomique/modele_sans_banque_wip/model.py`
- **Orchestration actuelle** → `simulation_lab/`
- **Note historique 27 mars** → `docs/ORGANISATION_ACTIVE_27_MARS.md`
- **Versions archivées** → `arborescence_modeles/INDEX_ARBORESCENCE.md`
- **Archives ZIP** → `banque_versions_zip/INDEX_ZIP.md`
- **Théorie du modèle WIP** → `Modèle_sans_banque_wip/description_theorisation_modele.pdf`
- En cas de contradiction entre mémoire et code : **le code fait foi**
