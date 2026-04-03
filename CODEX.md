# CODEX.md — Index de travail

## Project

Simulation multi-agents d'entités économiques abstraites échangeant une ressource unique : le **joule**.
Le projet modélise une société industrielle simplifiée avec prêts, faillites en cascade et indicateurs systémiques.
Contexte de recherche académique : pas d'application web, pas d'API, pas de déploiement.

**Lire avant d'agir** :
- `claude3-v3-27-mars/src/config.py` — paramètres du modèle
- `claude3-v3-27-mars/src/simulation.py` — moteur principal
- `ORGANISATION_ACTIVE_27_MARS.md` — version active et périmètre de travail

---

## Tech Stack

- **Langage** : Python 3
- **Dépendances** : stdlib + matplotlib
- **Frameworks** : aucun
- **Venv** : `/home/anatole/jupyter/.venv`
- **Python à utiliser** : `/home/anatole/jupyter/.venv/bin/python3`
- **Tests** : assertions Python simples dans `claude3-v3-27-mars/tests/test_basic.py`
- **Formatage** : `black` disponible dans le venv
- **Git hooks** : `hooks/` (activation via `git config core.hooksPath hooks`)

---

## Repo Map

```text
jupyter/
├── claude3-v3-27-mars/       ← VERSION ACTIVE, cible par défaut
│   ├── src/
│   │   ├── config.py         ← paramètres
│   │   ├── models.py         ← structures métier
│   │   ├── simulation.py     ← logique principale
│   │   ├── statistics.py     ← collecte et métriques
│   │   ├── output.py         ← sorties horodatées
│   │   ├── analysis.py       ← graphiques et analyses
│   │   └── main.py           ← point d'entrée
│   └── tests/
│       └── test_basic.py     ← validation de base
├── claude/                   ← archive v1, ne pas modifier
├── claude3-v2/               ← archive v2, ne pas modifier
├── arborescence_modeles/     ← index et symlinks d'archives
├── banque_versions_zip/      ← archives ZIP
├── hooks/                    ← hooks git
└── .venv/                    ← environnement Python
```

---

## Commands

```bash
# Lancer une simulation
cd /home/anatole/jupyter/claude3-v3-27-mars/src
/home/anatole/jupyter/.venv/bin/python3 main.py

# Lancer les tests
cd /home/anatole/jupyter/claude3-v3-27-mars
/home/anatole/jupyter/.venv/bin/python3 tests/test_basic.py

# Formater
/home/anatole/jupyter/.venv/bin/black claude3-v3-27-mars/src/

# Vérifier la syntaxe d'un fichier
/home/anatole/jupyter/.venv/bin/python3 -m py_compile claude3-v3-27-mars/src/<fichier>.py

# Activer les hooks
git config core.hooksPath hooks
```

Sorties générées dans `claude3-v3-27-mars/src/resultats/`.

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

- Lire `config.py` et `simulation.py` avant toute modification fonctionnelle
- Travailler par défaut uniquement dans `claude3-v3-27-mars/`
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

- **Paramètres du modèle** : `claude3-v3-27-mars/src/config.py`
- **Logique de simulation** : `claude3-v3-27-mars/src/simulation.py`
- **Version active** : `ORGANISATION_ACTIVE_27_MARS.md`
- **Archives et index** : `arborescence_modeles/INDEX_ARBORESCENCE.md`
- **Archives ZIP** : `banque_versions_zip/INDEX_ZIP.md`
- **Description théorique** : `claude3-v3-27-mars/description_theorisation_modele.pdf`
