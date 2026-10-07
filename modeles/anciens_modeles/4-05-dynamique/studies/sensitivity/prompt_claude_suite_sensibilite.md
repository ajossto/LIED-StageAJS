# Prompt Claude - Analyse et rapport de l'etude de sensibilite

Tu es Claude. Tu reprends l'etude dans :

`/home/anatole/jupyter/modeles/anciens_modeles/modele-27-04-WIP/studies/sensitivity`

Lis d'abord :

1. `notes.txt`
2. `rapport/rapport_preliminaire_sensibilite.tex`
3. `results/*.json`
4. les planches dans `report/figures/`
5. les runs visibles dans Simulation Lab sous le modele `etude_sensibilite_27_04_wip`
6. `prompt_adaptation_simulation_lab.md`

## Mission principale

Tu es responsable de l'analyse statistique, de l'interpretation theorique, de la critique des criteres de regime permanent et de la redaction du rapport final.

Codex travaille en parallele sur l'execution numerique, les scripts, les nouvelles simulations et l'integration Simulation Lab. Ne modifie pas ses scripts d'execution sauf demande explicite.

## Perimetre d'ecriture Claude

Tu peux modifier ou creer :

- `studies/sensitivity/claude_analysis/`
- `studies/sensitivity/report/rapport_final_sensibilite.tex`
- `studies/sensitivity/report/figures/claude_*`
- `studies/sensitivity/report/figures/interpretation_*`
- `studies/sensitivity/notes_claude.md`
- sections analytiques dans `studies/sensitivity/notes.txt`, en ajoutant clairement un bloc `[Claude]`

Evite d'ecrire dans :

- `studies/sensitivity/run_simulation.py`
- `studies/sensitivity/*sweep*.py`
- `studies/sensitivity/oat_*.py`
- `studies/sensitivity/coupling_*.py`
- `studies/sensitivity/export_to_simulation_lab.py`
- `studies/sensitivity/populate_lab_full_graphs.py`
- `studies/sensitivity/build_important_case_figures.py`
- `simulation_lab_data/runs/sensitivity_*`
- `studies/sensitivity/results/codex_*`

Tu peux lire tous ces fichiers, mais ne les modifie pas.

## Donnees et figures a exploiter

Les resultats deja produits incluent notamment :

- `alpha_sigma_sweep_steps1500_eps0.001.json`
- `alpha_sigma_sweep_steps1500_eps0.001_aggregate.json`
- `k_sweep_steps1500_eps0.001.json`
- `k_sweep_steps1500_eps0.001_aggregate.json`
- `epsilon_runtime_probe.json`
- `epsilon_runtime_probe_aggregate.json`
- `simulation_lab_regime_scan.json`
- les planches comparatives du run lab `sensitivity_important_cases_figures`

Les runs importants dans Simulation Lab contiennent les figures completes du modele et `compact_timeseries.json`. Les CSV bruts peuvent avoir ete supprimes volontairement.

## Regles scientifiques

- Cas principal : alpha homogene, donc `alpha_min = alpha_max = 1`.
- On fait varier `alpha_sigma_brownien`.
- `taux_amortissement` est exclu.
- Ne pas utiliser l'ancien critere unique de chute forte comme definition du regime permanent.
- Le regime permanent doit etre discute comme une question empirique :
  - trajectoires bornees ou non ;
  - existence d'une queue stationnaire ou quasi-stationnaire ;
  - pente de `n_alive`, `actif_total`, `densite_fin` ;
  - evolution des faillites ;
  - correlations de queue ;
  - decouplages entre population, actif et reseau de prets.
- Distinguer :
  - densite financiere en volume : `volume_prets / actif_total` ;
  - densite contractuelle : `n_prets / n_alive`.
- `epsilon` est un parametre numerique qui revele des microcredits ; il ne doit pas etre interprete comme un parametre economique sans prudence.
- `k` semble avoir un seuil d'apparition du reseau puis un plateau grand k.

## Questions d'analyse prioritaires

1. Quels parametres changent vraiment le critere principal :
   - densite et taille du reseau de pret relatives au nombre d'entites ;
   - densite financiere en volume ;
   - nombre de contrats par entite ?
2. Quels parametres changent la taille du systeme :
   - `n_alive`
   - `actif_total`
3. Quels parametres changent la volatilite :
   - CV de `n_alive`
   - CV de `actif_total`
   - amplitude ou pente de queue
4. Quelle est la distribution des tailles d'entites en regime ou quasi-regime ?
   - Gini
   - formes log-normales / queues lourdes si les donnees le permettent
   - attention : ne pas surinterpretrer sans test
5. Dans quels volumes de l'espace des parametres observe-t-on :
   - absence de reseau ;
   - reseau dense stable ;
   - microcredits nombreux mais faible volume ;
   - explosion ou non-bornitude ;
   - cascades significatives ?
6. Quelles correlations guident l'analyse ?
   - parametres -> statistiques ;
   - `n_alive` vs `actif_total` ;
   - `actif_total` vs volume de prets ;
   - nombre de prets vs volume de prets ;
   - faillites vs densite.

## Rapport attendu

Produire un rapport LaTeX final clair et critique :

`studies/sensitivity/report/rapport_final_sensibilite.tex`

Le rapport doit :

- expliquer la methode ;
- justifier les criteres de regime permanent ;
- presenter les resultats deja robustes ;
- expliciter les limites ;
- separer resultats economiques et artefacts numeriques ;
- inclure les figures comparatives pertinentes ;
- nommer les cas temoins du Simulation Lab ;
- proposer les prochaines experiences de couplage.

Ne pas transformer des heuristiques en verites. Quand un diagnostic est fragile, le dire.

## Coordination avec Codex

Si tu as besoin d'une nouvelle simulation, ne la lances pas directement. Ecris une demande concrete pour Codex avec :

- parametres exacts ;
- nombre de seeds ;
- duree ;
- raison scientifique ;
- figure ou statistique attendue ;
- priorite.

Ne modifie pas les scripts d'execution ni les donnees lab produites par Codex.

## Definition de "termine" pour ton travail

Ton travail est termine quand :

- le rapport final compile ou, si LaTeX manque, le `.tex` est coherent ;
- les figures que tu ajoutes sont dans `report/figures/` ;
- les demandes de simulations manquantes sont listees explicitement ;
- tes conclusions distinguent robuste / plausible / speculative ;
- tu as ajoute une note de reprise dans `notes_claude.md` ou dans un bloc `[Claude]` de `notes.txt`.
