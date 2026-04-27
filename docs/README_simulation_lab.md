# Simulation Lab

Simulation Lab est un outil Python local pour piloter plusieurs modèles de simulation
depuis une interface unique, sans passer par la console pour les usages courants, tout en
conservant un CLI exploitable par scripts, Codex ou Claude Code.

Les deux modèles intégrés en priorité sont :

- `modele_sans_banque_wip`
- `claude3_v2`

## Pourquoi une interface web locale plutôt qu’une GUI desktop

Le choix retenu est une interface web locale en Python standard library :

- pas de dépendance GUI native à installer ;
- plus robuste dans un environnement de recherche hétérogène ;
- interface utilisable aussi bien par un humain dans un navigateur que par un agent via le CLI ;
- architecture simple : un serveur HTTP local léger, sans framework web externe.

## Arborescence recommandée

```text
~/jupyter/
├── modeles-systeme-physicoeconomique/
│   ├── exemple_modele_lineaire/
│   │   └── model.py
│   ├── exemple_modele_marche/
│   │   └── model.py
│   ├── modele_sans_banque_wip/
│   │   └── model.py
│   ├── claude3_v2/
│   │   └── model.py
│   └── README.md
├── simulation_lab/
│   ├── cli.py
│   ├── contracts.py
│   ├── settings.py
│   ├── models/
│   │   ├── discovery.py
│   │   └── legacy.py
│   ├── runs/
│   │   ├── executor.py
│   │   └── storage.py
│   ├── stats/
│   │   └── base.py
│   └── web/
│       ├── app.py
│       ├── static/
│       │   ├── app.css
│       │   └── app.js
│       └── templates/
│           └── index.html
├── simulation_lab_data/
│   ├── runs/
│   └── batches/
├── docs/
│   ├── README_simulation_lab.md
│   └── note_de_travail_codex.txt
└── ...
```

## Lancement

Avec le venv existant :

```bash
cd ~/jupyter
./.venv/bin/python -m simulation_lab.cli gui --open-browser
```

Par défaut l’interface est servie sur `http://127.0.0.1:8765`.

L’interface est maintenant séparée en deux pages :

- `/launch` pour lancer une simulation unique ou un batch
- `/results` pour naviguer dans les simulations passées et la corbeille

Les paramètres sont regroupés par thèmes quand cela est déductible automatiquement
du nom des variables.

## Commandes CLI

Lister les modèles :

```bash
./.venv/bin/python -m simulation_lab.cli list-models
```

Lancer une simulation unique :

```bash
./.venv/bin/python -m simulation_lab.cli run \
  --model linear_growth \
  --params '{"steps": 80, "growth_rate": 1.1, "noise_scale": 0.5}' \
  --seed 1234 \
  --label test_local
```

Lancer un batch parallèle :

```bash
./.venv/bin/python -m simulation_lab.cli batch \
  --model market_toy \
  --params '{"steps": 120, "initial_price": 40}' \
  --runs 8 \
  --workers 4 \
  --base-seed 2000 \
  --label batch_marche
```

Lister les runs :

```bash
./.venv/bin/python -m simulation_lab.cli list-runs
```

Marquer une simulation à garder :

```bash
./.venv/bin/python -m simulation_lab.cli keep --run-id <RUN_ID> --value true
```

Supprimer une simulation :

```bash
./.venv/bin/python -m simulation_lab.cli delete --run-id <RUN_ID>
```

## Stockage des résultats

Chaque simulation est stockée dans `simulation_lab_data/runs/<run_id>/` avec :

- `run.json` : métadonnées standardisées ;
- CSV, PNG, JSON ou autres artefacts produits par le modèle ;
- éventuels sous-dossiers spécifiques au modèle.

`run.json` contient au minimum :

- `model_id`
- `parameters`
- `seed`
- `created_at`
- `status`
- `keep`
- `batch_id`
- `summary`
- `artifacts`

Les batchs sont indexés séparément dans `simulation_lab_data/batches/<batch_id>.json`.

Les simulations supprimées par l’interface ne sont pas effacées immédiatement :

- elles sont déplacées dans `simulation_lab_data/trash/`
- elles peuvent être restaurées
- la corbeille peut être vidée explicitement

En plus des runs lancés via l’outil, l’interface détecte aussi les anciens dossiers
de résultats déjà présents dans :

- `Modèle_sans_banque_wip/resultats/`
- `Modèle_sans_banque_wip/src/resultats/`
- `claude3-v2/src/resultats/`

et, plus généralement, tout dossier de `~/jupyter` contenant un `meta.json` de simulation
reconnaissable.

Ces simulations historiques apparaissent en lecture seule avec leurs previews de graphiques.
Elles peuvent toutefois recevoir des annotations persistantes :

- label personnalisé
- commentaire
- drapeau `important`
- drapeau `étoile`

## Note développeurs / chercheurs

### Architecture générale

Le logiciel est organisé en quatre couches :

1. `contracts.py` définit l’API commune des modèles.
2. `models/` gère la découverte automatique et les adaptateurs legacy.
3. `runs/` gère l’exécution, le multicoeur et le stockage disque.
4. `web/` et `cli.py` exposent les usages humain et scriptable.

Le futur module statistique commun devra venir dans `simulation_lab/stats/` sous forme
de plugin compatible avec `StatisticsPlugin`.

### Interface minimale qu’un modèle doit respecter

Un modèle compatible expose une instance de `BaseSimulationModel`.

Méthodes minimales :

- `parameter_specs(self) -> list[ParameterSpec]`
- `run(self, parameters: dict, output_dir: Path, seed: int, run_label: str = "") -> SimulationResult`

Attributs minimaux :

- `model_id`
- `display_name`
- `description`

### Déclaration des paramètres

Chaque paramètre est décrit par `ParameterSpec` :

- `name`
- `param_type` parmi `int`, `float`, `str`, `bool`
- `default`
- `label`
- `description`
- optionnellement `minimum`, `maximum`, `choices`

Cette convention permet :

- l’affichage dynamique dans l’interface ;
- la validation côté CLI et côté serveur ;
- l’extensibilité sans recoder l’UI.

### Format standard de résultat

Le `run()` d’un modèle retourne un `SimulationResult` :

- `status`
- `summary`
- `artifacts`
- `message`
- `extra`

Les artefacts sont décrits par `Artifact(relative_path, kind, label, description)`.

### Déclaration des sorties

Le modèle écrit librement ses sorties dans `output_dir`, mais il est recommandé de produire :

- au moins un CSV de données brutes ;
- au moins un PNG de synthèse si une visualisation est pertinente ;
- un résumé compact dans `summary`.

`collect_artifacts(output_dir)` permet de recenser automatiquement les fichiers courants.

### Graphiques

Deux options sont prévues :

1. le modèle produit directement ses graphiques dans `output_dir` ;
2. un adaptateur appelle un module d’analyse existant après la simulation.

L’interface affiche automatiquement les images détectées comme preview.

### Progression d’exécution

Pour les modèles legacy déjà branchés, la sortie console est capturée dans `legacy_execution.log`
et utilisée pour :

- afficher un journal de progression dans la page de lancement
- alimenter une barre de progression approximative basée sur les messages `Pas X`

## Annotations persistantes

Les annotations utilisateur sont conservées dans :

```text
simulation_lab_data/catalog.json
```

Cela permet de persister d’une session à l’autre :

- labels personnalisés
- commentaires
- marquage `important`
- marquage `étoile`

sur les runs gérés par l’outil comme sur les historiques externes.

### Compatibilité avec des modèles existants

Le module `simulation_lab.models.legacy.LegacyModuleModel` permet de brancher un code
existant si celui-ci expose déjà :

- une dataclass de configuration ;
- une fonction `run_and_save(...)` ;
- idéalement un module d’analyse séparé.

Cela évite de casser l’existant et permet une migration progressive.

### Futur module statistique commun

Le point d’entrée prévu est `simulation_lab.stats.base.StatisticsPlugin`.

Principe attendu :

- un plugin reçoit un `StatisticsContext` ;
- il agrège plusieurs runs compatibles ;
- il écrit ses sorties dans un dossier dédié ;
- il retourne un dictionnaire de résumé.

Cela permettra plus tard d’ajouter :

- statistiques sur batchs ;
- comparaison inter-modèles ;
- tableaux de synthèse ;
- graphiques communs réutilisables.

### Conseils d’ajout d’un nouveau modèle

1. Créer un sous-dossier dans `modeles-systeme-physicoeconomique/`.
2. Ajouter un `model.py`.
3. Définir une classe héritant de `BaseSimulationModel`.
4. Déclarer proprement les paramètres avec `ParameterSpec`.
5. Écrire les résultats dans `output_dir`.
6. Retourner un `SimulationResult`.

Le modèle sera alors détecté automatiquement au prochain lancement.
