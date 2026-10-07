# Prompt Codex - Suite de l'etude de sensibilite

Tu es Codex. Tu reprends l'etude dans :

`/home/anatole/jupyter/anciens_modeles/modele-27-04-WIP/studies/sensitivity`

Lis d'abord :

1. `notes.txt`
2. `rapport/rapport_preliminaire_sensibilite.tex`
3. `prompt_adaptation_simulation_lab.md`
4. les scripts existants : `run_simulation.py`, `alpha_sigma_sweep.py`, `k_sweep.py`, `epsilon_runtime_probe.py`, `export_to_simulation_lab.py`, `populate_lab_full_graphs.py`, `build_important_case_figures.py`

## Mission principale

Tu es responsable de l'execution numerique, de l'infrastructure, de la production des donnees et de l'integration Simulation Lab.

Claude travaille en parallele sur l'interpretation theorique/statistique et le rapport. Ne modifie pas ses fichiers de rapport final sauf coordination explicite.

## Perimetre d'ecriture Codex

Tu peux modifier ou creer :

- `studies/sensitivity/run_simulation.py`
- `studies/sensitivity/*sweep*.py`
- `studies/sensitivity/oat_*.py`
- `studies/sensitivity/coupling_*.py`
- `studies/sensitivity/export_to_simulation_lab.py`
- `studies/sensitivity/populate_lab_full_graphs.py`
- `studies/sensitivity/build_important_case_figures.py`
- `studies/sensitivity/results/codex_*`
- `studies/sensitivity/report/figures/codex_*`
- `studies/sensitivity/notes.txt`
- `simulation_lab_data/runs/sensitivity_*`

Evite d'ecrire dans :

- `studies/sensitivity/claude_analysis/`
- `studies/sensitivity/report/rapport_final_sensibilite.tex`
- `studies/sensitivity/report/figures/claude_*`
- tout fichier explicitement marque comme produit par Claude

## Regles scientifiques

- Cas principal : alpha homogene, donc `alpha_min = alpha_max = 1`.
- Faire varier `alpha_sigma_brownien`.
- `taux_amortissement` est exclu de l'etude.
- Le regime permanent ne se reduit pas a une chute de 25 %. Utiliser des criteres plus souples :
  - chute de 5 % possible ;
  - queue bornee apres un temps fini ;
  - pente de `n_alive`, `actif_total`, `densite_fin` ;
  - pente ou derive des faillites ;
  - correlations de queue entre `n_alive`, `actif`, `n_loans`, faillites.
- `epsilon=1e-3` est le compromis de production, mais verifier certains points sensibles a `1e-6`.
- `epsilon` controle fortement le nombre de contrats via les microcredits ; ne pas confondre nombre de prets et volume financier.
- `k` a un comportement de seuil et un plateau grand k.
- Le nombre de workers autorise est 6.

## Regle Simulation Lab obligatoire

Dorenavant, chaque simulation utile doit etre observable dans Simulation Lab avec les figures completes du modele.

Workflow obligatoire pour chaque run conserve :

1. executer la simulation ;
2. produire les graphiques complets via `analysis.analyze_folder` ;
3. extraire `compact_timeseries.json` ;
4. supprimer les CSV bruts ;
5. rafraichir `run.json` pour que les artefacts PNG/PDF soient visibles dans Simulation Lab.

Utilise ou adapte `populate_lab_full_graphs.py`.

Ne conserve les CSV que si l'utilisateur le demande explicitement.

## Suite de travail conseillee

1. Construire une vraie etude OAT autour de deux centres :
   - centre sous-critique : `k=3`, alpha homogene, `epsilon=1e-3`, pour voir quels parametres font apparaitre un regime ;
   - centre en regime : `k=4`, alpha homogene, `epsilon=1e-3`, pour mesurer les sensibilites une fois le regime installe.
2. Parametres candidats OAT, sauf `taux_amortissement` :
   - `theta`
   - `mu`
   - `lambda_creation`
   - `n_candidats_pool`
   - `fraction_taux_emprunteur`
   - `seuil_ratio_endettement`
   - `seuil_ratio_liquide_passif`
   - `taux_depreciation_endo`
   - `taux_depreciation_exo`
   - `fraction_auto_investissement`
   - `coefficient_reliquefaction`
   - `actif_liquide_initial` et `passif_inne_initial`, en gardant la richesse nette initiale coherente si possible
   - `n_entites_initiales`
   - `alpha_sigma_brownien`
   - `epsilon`, seulement comme parametre numerique de robustesse
3. Apres OAT, choisir les couples/triples les plus informatifs :
   - `k x alpha_sigma_brownien`
   - `epsilon x k`
   - `theta x seuil_ratio_endettement`
   - `lambda_creation x taux_depreciation_exo`
   - `fraction_taux_emprunteur x mu`
4. Produire des fichiers de resultats compacts, des figures comparatives et des runs Simulation Lab lisibles.
5. Noter explicitement ce qui est robuste et ce qui depend de la resolution numerique.

## Communication avec Claude

Tu fournis a Claude :

- les resultats JSON agreges ;
- les planches comparatives ;
- les chemins des runs lab importants ;
- une synthese des anomalies ou cas ambigus.

Tu lui demandes de ne pas relancer de simulations et de ne pas modifier les scripts d'execution.

## Definition de "termine" pour une phase

Une phase est terminee seulement si :

- les simulations ont tourne sans echec ;
- les figures completes sont visibles dans Simulation Lab ;
- les CSV bruts ont ete supprimes apres extraction compacte ;
- les resultats agreges sont ecrits dans `results/` ;
- une note de reprise est ajoutee dans `notes.txt`.
