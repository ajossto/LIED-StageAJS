# CLAUDE.md — Index de travail

## Project

Simulation multi-agents d'entités économiques abstraites échangeant une ressource unique : le **joule**.
Modélise une société industrielle simplifiée avec prêts, faillites en cascade, indicateurs systémiques.
Projet de recherche académique — pas d'application web, pas d'API, pas de déploiement.

**Lire avant d'agir** :
- `README.md` — navigation et statut courant des lignées
- `modeles/m4b_credit_soc_mini/README.md` — moteur scientifique actif
- `modeles/adaptateurs/m4b_credit_soc_mini/model.py` — adaptateur actif
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

```text
jupyter/
├── modeles/                    ← tout ce qui est modèle (moteurs, anciens moteurs, adaptateurs)
│   ├── m4_4_rebond_credit_soc/    ← dernière lignée auditée, campagnes et tests
│   ├── m4_3live_v2_credit_soc/    ← sens libre du prêt, campagnes Live-v2
│   ├── m4_3live_credit_soc/       ← interventions et technologies individuelles
│   ├── m4_3_credit_soc/           ← institutions de crédit
│   ├── m4_2b_credit_soc/, m4_2_credit_soc/  ← moteurs implémentés, étude d'échelle
│   ├── m4b_credit_soc_mini/       ← référence historique autonome
│   ├── m4_credit_soc/, m4_credit_soc_fable/, m4_credit_soc_sol/  ← lignée M4 initiale
│   ├── anciens_modeles/           ← tous les moteurs et travaux jusqu'à M3 inclus
│   └── adaptateurs/               ← adaptateurs découverts par Simulation Lab (list-models)
├── simulation_lab/             ← orchestration (CLI + UI locale)
├── simulation_lab_data/        ← données générées (non versionnées)
├── recherche/                  ← notes, articles et campagnes (dossiers scellés par empreinte)
│   └── bibliographie/             ← articles de référence (PDF) et leurs analyses
├── docs/                       ← documentation de cadrage et notes de session
├── presentations/              ← sources et artefacts des présentations
├── archives/                   ← versions historiques, ZIP, espaces de travail clos
├── outils/                     ← scripts utilitaires transverses
├── hooks/                      ← hooks git
└── .venv/                      ← environnement Python (non versionné)
```
Liens de compatibilité à la racine : `m4_4_rebond_credit_soc` et `m4_3live_credit_soc`
(→ `modeles/…`), requis par les manifestes d'empreintes des articles dans `recherche/`.

---

## Commands

```bash
# Lancement interface locale
cd /home/anatole/jupyter
/home/anatole/jupyter/.venv/bin/python3 -m simulation_lab.cli gui --open-browser

# Lister les modèles branchés
/home/anatole/jupyter/.venv/bin/python3 -m simulation_lab.cli list-models

# Validation historique ciblée si nécessaire
cd /home/anatole/jupyter/modeles/anciens_modeles/claude3-v2
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
- **Dépendances** : stdlib + matplotlib + numpy + scipy autorisés — pas d'autres dépendances sans accord explicite
- **Cache incrémental** : tout `loan.active = False` dans `simulation.py` doit être accompagné de mises à jour de `revenus_interets` / `charges_interets` (enforced par pre-commit)
- **Invariant critique** : `_rebuild_interest_cache()` interdit dans `run_step` (enforced par pre-commit)

---

## Working Rules for Claude

- Lire d'abord le moteur M4B, son adaptateur et `simulation_lab` avant toute modification fonctionnelle
- Pour M4.2, travailler dans `modeles/m4_2_credit_soc/` et traiter les moteurs antérieurs comme des sources en lecture tant que le prompt n'a pas fixé le périmètre
- Ne pas modifier les moteurs de `modeles/anciens_modeles/` sans demande explicite
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

- **Navigation courante** → `README.md`
- **Moteur actif** → `modeles/m4b_credit_soc_mini/m4b/`
- **Adaptateur actif** → `modeles/adaptateurs/m4b_credit_soc_mini/model.py`
- **Dernier rapport de sensibilité** → `recherche/sensibilite_m4b/report/rapport_final.pdf`
- **Chantier M4.2** → `modeles/m4_2_credit_soc/`
- **Orchestration actuelle** → `simulation_lab/`
- **Note historique 27 mars** → `docs/ORGANISATION_ACTIVE_27_MARS.md`
- **Versions archivées** → `archives/arborescence_modeles/INDEX_ARBORESCENCE.md`
- **Archives ZIP** → `archives/banque_versions_zip/INDEX_ZIP.md`
- **Théorie d'une légacy WIP** → `modeles/anciens_modeles/Modèle_sans_banque/description_theorisation_modele.pdf`
- En cas de contradiction entre mémoire et code : **le code fait foi**
