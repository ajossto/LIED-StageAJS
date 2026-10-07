# CODEX.md — Index de travail

## Project

Simulation multi-agents d'entités économiques abstraites échangeant une ressource unique : le **joule**.
Le projet modélise une société industrielle simplifiée avec prêts, faillites en cascade et indicateurs systémiques.
Contexte de recherche académique : pas d'application web, pas d'API, pas de déploiement.

**Lire avant d'agir** :
- `README.md` — navigation et statut courant des lignées
- `modeles/m4_4_rebond_credit_soc/README.md` — dernière lignée scientifique auditée (août 2026)
- `recherche/note_communication_encadrants/README.md` — proto-rapport de stage
- `recherche/note_resultats/` — proto-article des conclusions, document frère distinct
- `simulation_lab/` — orchestration locale, stockage et UI
- `docs/ORGANISATION_ACTIVE_27_MARS.md` — note historique du 27 mars à ne pas confondre avec l'état courant

---

## Tech Stack

- **Langage** : Python 3
- **Dépendances** : selon la lignée ; consulter ses imports et son environnement (notamment NumPy/SciPy pour les analyses récentes)
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
# Lancer l'interface locale
cd /home/anatole/jupyter
/home/anatole/jupyter/.venv/bin/python3 -m simulation_lab.cli gui --open-browser

# Lister les modèles branchés
/home/anatole/jupyter/.venv/bin/python3 -m simulation_lab.cli list-models

# Lancer une validation historique ciblée si nécessaire
cd /home/anatole/jupyter/modeles/anciens_modeles/claude3-v2
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
- Générateur pseudo-aléatoire isolé ; API et garanties de parité propres à chaque lignée
- Un rôle clair par module
- Commenter seulement les invariants ou choix non évidents
- Ne pas ajouter de dépendances sans nécessité démontrée
- Respecter les invariants de cache d'intérêts dans `simulation.py`

---

## Working Rules for Codex

- Lire d'abord le moteur concerné et, pour une intégration, son adaptateur et la couche `simulation_lab` avant toute modification fonctionnelle
- Travailler dans la lignée explicitement concernée ; les versions historiques servent de références en lecture
- Ne pas modifier les moteurs de `modeles/anciens_modeles/` sans demande explicite
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

- **Navigation courante** : `README.md`
- **Dernier moteur audité (index du 14 septembre 2026)** : `modeles/m4_4_rebond_credit_soc/m4_4/`
- **Résultats numériques M4.4** : `modeles/m4_4_rebond_credit_soc/results/analysis/` et `report/`
- **Proto-rapport du raisonnement** : `recherche/note_communication_encadrants/`
- **Proto-article des conclusions** : `recherche/note_resultats/`
- **Intentions de l'auteur** : réponses explicites aux questionnaires et à l'audit ; les inférences non validées restent provisoires
- **Rapport de sensibilité historique** : `recherche/sensibilite_m4b/report/rapport_final.pdf`
- **M4.2 implémenté** : `modeles/m4_2_credit_soc/`
- **Orchestration actuelle** : `simulation_lab/`
- **Note historique 27 mars** : `docs/ORGANISATION_ACTIVE_27_MARS.md`
- **Archives et index** : `archives/arborescence_modeles/INDEX_ARBORESCENCE.md`
- **Archives ZIP** : `archives/banque_versions_zip/INDEX_ZIP.md`
- **Description théorique d'une légacy WIP** : `modeles/anciens_modeles/Modèle_sans_banque/description_theorisation_modele.pdf`
