# Runtime dynamique controle

Ce travail est fait uniquement dans `/home/anatole/jupyter/modeles/anciens_modeles/4-05-dynamique`.
Le dossier original `/home/anatole/jupyter/modeles/anciens_modeles/modele-27-04-WIP` n'a pas ete modifie.

## Lancer le demonstrateur

```bash
cd /home/anatole/jupyter/modeles/anciens_modeles/4-05-dynamique
python examples/dynamic_demo.py --steps 80 --observe-every 10
```

Le demonstrateur lance une simulation courte, affiche quelques metriques
dynamiques et applique une modification de `lambda_creation` et `theta` au
milieu de la simulation. Le journal des modifications est affiche a la fin.

## Lancer le petit logiciel local

```bash
cd /home/anatole/jupyter/modeles/anciens_modeles/4-05-dynamique
/home/anatole/jupyter/.venv/bin/python3 scripts/dynamic_control_server.py --port 8765
```

Puis ouvrir :

```text
http://127.0.0.1:8765/
```

Raccourci equivalent :

```bash
cd /home/anatole/jupyter/modeles/anciens_modeles/4-05-dynamique
./run_dynamic_app.sh 8766
```

Fonctions disponibles :
- play, pause, stop ;
- avancement pas a pas, +10, +50 ;
- observation immediate des metriques legeres ;
- modification controlee de parametres via `apply_parameter_updates()` ;
- execution d'un scenario JSON reproductible ;
- export du journal interactif sous forme de scenario rejouable.
- modification controlee de `alpha` pour les entites vivantes existantes.

Endpoints JSON utiles :
- `GET /api/observation` ;
- `POST /api/step` avec `{"n_steps": 10}` ;
- `POST /api/play` avec `{"max_steps": 100, "delay_seconds": 0.02}` ;
- `POST /api/pause` ;
- `POST /api/update` avec `{"updates": {"theta": 0.4}, "scope": "global_config"}` ;
- `POST /api/entity_update` avec `{"updates": {"alpha_multiplier": 1.05}, "scope": "existing_entities", "allow_risky": true}` ;
- `POST /api/run_scenario` avec `{"scenario": ...}` ;
- `GET /api/export_journal`.

## Observation dynamique

```python
from config import SimulationConfig
from simulation import Simulation

sim = Simulation(SimulationConfig(duree_simulation=100, seed=42))
sim.run_step()
obs = sim.current_observation()
```

`current_observation()` retourne un dictionnaire JSON-serialisable sans exposer
`self.entities`, `self.loans`, `self.stats` ou `self.collector` par reference.
Apres au moins un `run_step()`, les grandeurs principales viennent de la derniere
ligne de statistiques legeres et du dernier indicateur du collector.

Complexite :
- O(1) pour les compteurs, flux du dernier pas, derniere statistique legere,
  dernier indicateur systemique et configuration courante.
- O(1) amorti pour le nombre d'entites vivantes grace au cache existant.
- O(N entites) et O(N prets) seulement avant le premier pas, pour construire un
  snapshot initial si aucune statistique n'existe encore.
- Les snapshots de distribution restent echantillonnes via `freq_snapshot`.

## Modifier des parametres entre deux pas

```python
result = sim.apply_parameter_updates({"theta": 0.4})
```

La methode est atomique : si une demande est refusee, aucun parametre du lot
n'est applique. Les modifications ne sont acceptees que hors `run_step()`. Elles
ne touchent jamais directement les entites ni les prets.

Chaque modification acceptee ajoute une entree dans `sim.parameter_update_log`
avec `step`, `parameter`, ancienne valeur, nouvelle valeur, categorie de risque,
scope, source et avertissement eventuel.

## Categories de parametres

Categorie A, acceptee par defaut entre deux pas :
`theta`, `mu`, `seuil_ratio_endettement`, `fraction_taux_emprunteur`,
`lambda_creation`, `max_credit_iterations`, `n_candidats_pool`,
`fraction_auto_investissement`, `coefficient_reliquefaction`,
`taux_depreciation_liquide`, `taux_depreciation_endo`, `log_events`,
`duree_simulation`.

Categorie B, refusee sauf `allow_risky=True` :
`alpha_min`, `alpha_max`, `actif_liquide_initial`, `passif_inne_initial`,
`alpha_sigma_brownien`, `seuil_ratio_liquide_passif`, `taux_amortissement`,
`epsilon`, `freq_snapshot`.

Categorie C, toujours refusee en cours de simulation :
`seed`, `n_entites_initiales`, `taux_depreciation_exo`, `alpha`.

## Scopes coherents dans cette version

`global_config` est coherent pour les parametres A et B autorises : il modifie
les regles futures du moteur.

`future_entities` est coherent pour `lambda_creation`, `alpha_min`, `alpha_max`,
`actif_liquide_initial`, `passif_inne_initial`. Pour `lambda_creation`, cela
modifie le flux futur d'entrees. Pour les bornes/dotations initiales, cela
concerne uniquement les entites creees apres l'intervention.

`existing_entities` et `all_entities` sont acceptes uniquement par la fonction dediee
`apply_entity_updates()` pour modifier `Entity.alpha` des entites vivantes.
Les bilans et les prets restent intouchables.

Operations d'entites supportees :
- `alpha_multiplier` : multiplie alpha par un facteur strictement positif ;
- `alpha_set` : fixe alpha a une valeur positive ou nulle ;
- `alpha_add` : ajoute un delta, refuse si un alpha final deviendrait negatif ;
- `alpha_min` : borne inferieurement les alpha existants ;
- `alpha_max` : borne superieurement les alpha existants.

Avec `scope="existing_entities"`, seules les entites vivantes deja presentes
sont touchees. Avec `scope="all_entities"`, `alpha_min` et `alpha_max` mettent
aussi a jour la configuration globale pour les futures entites.

`forbidden` refuse explicitement l'intervention.

## Scenario reproductible

Un scenario peut etre charge depuis un dict JSON-compatible :

```python
import json
from simulation import run_scenario

with open("examples/scenario_theta_lambda.json", "r", encoding="utf-8") as f:
    scenario = json.load(f)

sim = run_scenario(scenario)
journal = sim.intervention_journal()
```

Pour un scenario qui modifie les entites existantes, utiliser
`allow_risky=True` :

```python
with open("examples/scenario_existing_entities.json", "r", encoding="utf-8") as f:
    scenario = json.load(f)

sim = run_scenario(scenario, allow_risky=True)
```

Les interventions sont triees par `step` et appliquees avant le pas portant ce
numero. Le journal contient la configuration initiale, la seed, le calendrier
planifie et les modifications effectivement appliquees avec anciennes et
nouvelles valeurs.

## Separation proposee

- Moteur de simulation : `Simulation.run_step()`, `Simulation.run()`,
  statistiques legeres, collector et invariants comptables.
- Mode scenario reproductible : `run_scenario()` et
  `Simulation.run_with_interventions()`, avec calendrier discret, validation et
  journal exportable.
- Mode interactif exploratoire : `run_dynamic()`, `pause()`, `resume()`,
  `request_stop()`, `step_once()` et `apply_parameter_updates()`. Les changements
  restent appliques entre deux pas.
- Couche de visualisation : notebook, Matplotlib dynamique ou interface locale
  legere consommant uniquement `current_observation()` et le rolling buffer.

## Limites ouvertes

- Pas encore de vraie interface graphique.
- Pas encore de sauvegarde/reprise complete d'un etat micro.
- Pas encore de visualisation reseau temps reel.
- Pas de modification pendant les cascades ni pendant le marche du credit.
- Pas de transformation directe des entites existantes.
- Les historiques lourds restent optionnels via les snapshots du collector et la
  frequence `freq_snapshot`.

## Transformer une session interactive en scenario

1. Lancer une session avec `run_dynamic()` et appliquer les modifications via
   `apply_parameter_updates()`.
2. Exporter `sim.intervention_journal()` ou `sim.export_intervention_journal()`.
3. Extraire `applied_updates` en interventions planifiees `{step, parameter,
   old_value_expected, new_value, scope, comment}`.
4. Rejouer avec `run_scenario()` en fixant la meme seed et la meme
   `initial_config`.
5. Comparer les trajectoires obtenues pour verifier qu'aucune source externe de
   non-determinisme n'a ete introduite.
