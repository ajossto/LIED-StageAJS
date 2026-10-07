# Réplication critique du modèle M2

Ce dossier est autonome afin de ne pas entrer en collision avec les autres
travaux du dépôt. Les anciennes lignées sont uniquement lues comme sources.

## Commandes

Depuis `modeles/anciens_modeles/m2_codex/` avec le venv du dépôt :

```bash
PYTHONPATH=src /home/anatole/jupyter/.venv/bin/python3 -m unittest discover -s tests -v
/home/anatole/jupyter/.venv/bin/python3 experiments/m2/run_baseline.py --seed 0
/home/anatole/jupyter/.venv/bin/python3 experiments/m2/run_validation.py outputs/baseline_seed_0
/home/anatole/jupyter/.venv/bin/python3 experiments/m2/run_grid.py
/home/anatole/jupyter/.venv/bin/python3 experiments/m2/run_ablation.py
```

Les rapports LaTeX se compilent depuis leur dossier avec :

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

## Conventions scientifiques importantes

- Les intérêts de plusieurs contrats sont servis simultanément au prorata de ce
  qui est dû, pour ne pas introduire une priorité par ordre de dictionnaire.
- Les entités déjà en défaut sont exclues du marché avant leur liquidation.
- Les créances d'une faillie sont fractionnées entre ses créanciers ; sans
  créancier admissible, elles sont annulées.
- La « taille de cascade » enregistrée par pas est un lot de faillites et non une
  avalanche causale isolée lorsque plusieurs chocs initiaux surviennent au même
  pas.
- Seeds et fenêtres temporelles ne sont jamais poolés dans les estimations.
