# Analyse — distributions en taille et en revenu (modele-27-04-WIP)

Recherche de la meilleure famille de lois (1 à 5 paramètres) pour la
distribution transversale de la taille des entités (`actif_total` /
`passif_total`) et de leurs revenus (`revenu_total`) dans les simulations
du modèle `modele-27-04-WIP`, en remplacement d'un mélange de 2
log-normales jugé insatisfaisant.

- `latex/rapport.tex`, `latex/rapport.pdf` — le rapport.
- `figures/` — figures utilisées dans le rapport.
- `scripts/` — code d'ajustement, réutilisable (voir docstrings) :
  - `lib.py` : chargement des runs stationnaires depuis `simulation_lab_data/`
  - `families.py` : échelle de 13 familles de lois (MLE, AIC/BIC)
  - `tail_test.py` : test de queue Clauset–Shalizi–Newman
  - `batch_run.py` : exécution parallèle sur toutes les simulations stationnaires
  - `aggregate.py` : agrégation des résultats par groupe de paramètres
- `results/` — sorties brutes par simulation (JSON), une par run stationnaire.

Pour reproduire : `python3 scripts/batch_run.py` (nécessite le venv du
dépôt, `numpy`/`scipy`), puis `python3 scripts/aggregate.py`.

Les CSV bruts de simulation (`simulation_lab_data/`) ne sont pas inclus
ici : ils sont régénérables et déjà exclus du dépôt par `.gitignore`.
