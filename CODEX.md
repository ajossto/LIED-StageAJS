# CODEX.md — Index de travail

## Project

Simulation multi-agents d'entités économiques abstraites échangeant une ressource unique : le **joule**.
Le projet modélise une société industrielle simplifiée avec prêts, faillites en cascade et indicateurs systémiques.
Contexte de recherche académique : pas d'application web, pas d'API, pas de déploiement.

**Lire avant d'agir** :
- `modeles-systeme-physicoeconomique/modele_sans_banque_wip/model.py` — adaptateur du modèle WIP actuellement branché
- `simulation_lab/` — orchestration locale, stockage et UI
- `docs/ORGANISATION_ACTIVE_27_MARS.md` — note historique du 27 mars à ne pas confondre avec l'état courant

---

## Tech Stack

- **Langage** : Python 3
- **Dépendances** : stdlib + matplotlib
- **Frameworks** : aucun
- **Venv** : `/home/anatole/jupyter/.venv`
- **Python à utiliser** : `/home/anatole/jupyter/.venv/bin/python3`
- **Tests** : tests simples dans les versions historiques + validations locales via `simulation_lab`
- **Formatage** : `black` disponible dans le venv
- **Git hooks** : `hooks/` (activation via `git config core.hooksPath hooks`)

---

## Repo Map

```text
jupyter/
├── simulation_lab/           ← orchestration actuelle (CLI + UI locale)
├── modeles-systeme-physicoeconomique/
│   ├── modele_sans_banque_wip/  ← modèle le plus abouti actuellement branché
│   └── claude3_v2/              ← autre modèle intégré au lab
├── archives/
│   └── modeles/
│       └── claude3-v3-27-mars/  ← archive complète de l'ancienne lignée 27 mars
├── claude/                   ← archive v1, ne pas modifier
├── claude3-v2/               ← archive v2, ne pas modifier
├── docs/                     ← documentation de cadrage et notes de session
├── recherche/                ← matériaux de recherche, notes et visuels hors flux actif
├── arborescence_modeles/     ← index et symlinks d'archives
├── banque_versions_zip/      ← archives ZIP
├── hooks/                    ← hooks git
└── .venv/                    ← environnement Python
```

---

## Commands

```bash
# Lancer l'interface locale
cd /home/anatole/jupyter
/home/anatole/jupyter/.venv/bin/python3 -m simulation_lab.cli gui --open-browser

# Lister les modèles branchés
/home/anatole/jupyter/.venv/bin/python3 -m simulation_lab.cli list-models

# Lancer une validation historique ciblée si nécessaire
cd /home/anatole/jupyter/claude3-v2
/home/anatole/jupyter/.venv/bin/python3 tests/test_basic.py

# Vérifier la syntaxe d'un fichier
/home/anatole/jupyter/.venv/bin/python3 -m py_compile simulation_lab/<fichier>.py

# Activer les hooks
git config core.hooksPath hooks
```

Sorties générées dans `simulation_lab_data/` et, pour les anciens modèles, dans leurs dossiers `resultats/`.

---

## Coding Conventions

- Style Python idiomatique, formaté avec `black`
- `snake_case` pour variables, fonctions et fichiers
- Modèles métier en `@dataclass` typées
- Références inter-entités par ID entier, pas par pointeurs d'objets
- Générateur pseudo-aléatoire isolé via `random.Random(seed)`
- Un rôle clair par module
- Commenter seulement les invariants ou choix non évidents
- Ne pas ajouter de dépendances sans nécessité démontrée
- Respecter les invariants de cache d'intérêts dans `simulation.py`

---

## Working Rules for Codex

- Lire d'abord l'adaptateur WIP et la couche `simulation_lab` avant toute modification fonctionnelle
- Travailler par défaut sur `simulation_lab/` et `modeles-systeme-physicoeconomique/`
- Ne pas modifier `claude/` ou `claude3-v2/` sans demande explicite
- Mettre à jour ce fichier si la structure du dossier, la version active, les commandes utiles ou les conventions changent
- Faire des changements minimaux, ciblés et justifiables
- Vérifier dans le code avant d'affirmer un comportement
- Signaler explicitement les hypothèses et les inférences
- Citer les fichiers touchés avec chemin et ligne dans les comptes rendus
- Préférer des validations locales simples après modification
- Ne pas restructurer l'architecture sans raison claire

---

## Maintenance

`CODEX.md` est un document vivant.
Il doit être mis à jour lorsque l'un de ces éléments change :
- dossier de travail actif
- arborescence importante du dépôt
- commandes de test, d'exécution ou de formatage
- conventions de code ou invariants métier
- source de vérité du projet

Si une modification rend une section de ce fichier inexacte, la correction fait partie du travail à faire.

---

## Confidence Rule

Si Codex n'est pas suffisamment certain d'un fait, il doit l'indiquer explicitement et relire les sources du dépôt.

Distinguer clairement :
- **Fait observé** : vérifié directement dans le code ou un fichier
- **Inférence** : déduction fondée sur le contexte
- **Incertitude** : point non confirmé qui doit être vérifié avant décision

En cas de conflit entre souvenir, commentaire et implémentation : **le code fait foi**.

---

## Source of Truth

- **Modèle WIP branché** : `modeles-systeme-physicoeconomique/modele_sans_banque_wip/model.py`
- **Orchestration actuelle** : `simulation_lab/`
- **Note historique 27 mars** : `docs/ORGANISATION_ACTIVE_27_MARS.md`
- **Archives et index** : `arborescence_modeles/INDEX_ARBORESCENCE.md`
- **Archives ZIP** : `banque_versions_zip/INDEX_ZIP.md`
- **Description théorique WIP** : `Modèle_sans_banque_wip/description_theorisation_modele.pdf`
