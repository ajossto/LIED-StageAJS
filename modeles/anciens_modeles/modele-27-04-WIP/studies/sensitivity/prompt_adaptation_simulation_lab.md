# Prompt pour adapter Simulation Lab a l'etude OAT/sensibilite

Tu reprends le travail dans `/home/anatole/jupyter`, principalement :

- code du lab : `/home/anatole/jupyter/simulation_lab`
- donnees du lab : `/home/anatole/jupyter/simulation_lab_data`
- etude WIP : `/home/anatole/jupyter/modeles/anciens_modeles/modele-27-04-WIP/studies/sensitivity`

Objectif : adapter Simulation Lab pour que toutes les simulations de l'etude de sensibilite/OAT soient observables comme les simulations classiques, mais sans conserver les CSV lourds une fois les figures generees.

Contraintes fonctionnelles importantes :

1. Chaque simulation OAT ou sensibilite doit apparaitre dans Simulation Lab comme un run standard.
2. Chaque run doit contenir les figures completes du modele, comme les runs lances via le lab :
   - `macro_overview.png`
   - `cascades_rank_size.png`
   - `entity_size_histos.png`
   - `extraction_power.png`
   - `destruction_moving_avg.png`
   - `internal_rate_evolution.png`
   - `gini_evolution.png`
   - `gini_lorenz_snapshots.png`
   - `revenue_distributions.png`
   - `entity_lives_overview.png`
   - figures d'entites individuelles
   - `loan_network_final.png`
   - `lifespan_analysis.png`
3. Les CSV complets doivent etre supprimes apres generation des figures, car ils sont trop volumineux.
4. Avant suppression des CSV, extraire une petite serie temporelle compacte par run, par exemple `compact_timeseries.json`, contenant au minimum :
   - `step`
   - `alive`
   - `actif`
   - `volume_prets`
   - `densite_fin`
   - `loan_density`
   - `failures`
   - `gini`
5. Cette serie compacte doit permettre de refaire des planches comparatives du type `simulation_lab_regime_examples`, sans avoir besoin des CSV.
6. Il faut une vue ou un mecanisme de navigation pratique pour l'OAT :
   - filtrer par campagne (`alpha_sigma`, `k_sweep`, `epsilon_runtime`, puis futurs OAT)
   - filtrer par parametre varie, seed, regime detecte, `bounded_tail`, `drop_5_detected`
   - ouvrir rapidement les figures clefs d'un run
   - ouvrir les planches comparatives agregees
7. Il faut garder le workflow resumable :
   - si un run a deja ses figures completes, ne pas le relancer sauf option `force`
   - si un run a ses figures mais pas `compact_timeseries.json`, extraire la serie compacte si les CSV existent encore
   - si les CSV ont deja ete supprimes, ne pas casser l'affichage
8. Les scripts deja ajoutes dans l'etude sont :
   - `export_to_simulation_lab.py` : exporte les metriques legeres en runs lab
   - `populate_lab_full_graphs.py` : relance les runs importants pour produire les figures completes, puis peut supprimer les CSV
   - `build_important_case_figures.py` : cree des planches comparatives visibles dans le lab

Travail demande :

1. Inspecter `simulation_lab/runs/storage.py`, `simulation_lab/web/static/app.js`, `simulation_lab/web/templates/results.html` et le systeme d'artefacts.
2. Ajouter une presentation claire des campagnes d'etude dans `/results`, sans casser les anciens runs.
3. Faire en sorte que `compact_timeseries.json` soit reconnu comme un artefact utile et, si possible, affiche sous forme de mini-graphes interactifs ou au moins lie aux planches comparatives.
4. Ajouter un bouton ou une action "regenerer les figures completes" pour un run d'etude si les figures manquent.
5. Ajouter un bouton ou une action "nettoyer CSV" qui supprime les CSV apres verification que les figures et `compact_timeseries.json` existent.
6. Ne pas supprimer les PNG, PDF, `run.json`, `record.json`, `compact_timeseries.json`, `resume_analyse.txt` ni le rapport.
7. Mettre a jour la documentation du lab ou une note dans `studies/sensitivity/notes.txt`.

Attention :

- Ne pas toucher aux changements hors scope dans le depot.
- Ne pas utiliser `taux_amortissement` comme axe d'etude.
- Le cas principal demande par l'utilisateur est alpha homogene : `alpha_min=alpha_max=1`, avec variation de `alpha_sigma_brownien`.
- Le serveur Simulation Lab tourne generalement sur `http://127.0.0.1:8765/results`.
- Le modele peut etre couteux ; utiliser des jobs resumables et ne jamais relancer toute la grille sans confirmation explicite.
