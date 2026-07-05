# M3 — crédit productif, liquidité et fragilité nominale

Workspace autonome (comme `m2_fable`/`m2_codex`) : les autres lignées du dépôt
sont lues comme sources, jamais modifiées.

## Question scientifique

M2 (répliqué deux fois) est un générateur démographique Reed-like où le crédit
n'a aucun effet distributionnel mesurable. M3 sépare liquidité `L` et capital
productif `K`, fait du crédit l'unique canal de recyclage `L -> K` entre
entités, et rend les intérêts exigibles en liquidité seulement (défaut de
liquidité possible avec NW > 0). Question : ce crédit productif, risqué et
topologique a-t-il enfin un effet causal — voire une dynamique
accumulation-relaxation (SOC) ?

Spécification pré-enregistrée : `reports/02_m3_specification/main.pdf`.

## Commandes

Depuis `m3_credit_soc/`, avec le venv du dépôt :

```bash
# Tests (assertions simples, pas de pytest)
/home/anatole/jupyter/.venv/bin/python3 tests/run_all.py

# Calibration pré-enregistrée de (s, c)
/home/anatole/jupyter/.venv/bin/python3 experiments/m3/run_calibration.py

# Baseline multi-seed, ablations, runs longs, grille
/home/anatole/jupyter/.venv/bin/python3 experiments/m3/run_baseline.py --seeds 0 1 2 3 4
/home/anatole/jupyter/.venv/bin/python3 experiments/m3/run_ablation.py --which B
/home/anatole/jupyter/.venv/bin/python3 experiments/m3/run_long.py --variant baseline
/home/anatole/jupyter/.venv/bin/python3 experiments/m3/run_grid.py --axis sigma

# Analyse statistique d'un run -> validation.json ; table comparative
/home/anatole/jupyter/.venv/bin/python3 experiments/m3/run_validation.py experiments/m3/results/baseline_s0
/home/anatole/jupyter/.venv/bin/python3 experiments/m3/aggregate_results.py experiments/m3/results/*/

# Suivi du budget de calcul (48 h)
/home/anatole/jupyter/.venv/bin/python3 experiments/m3/exp_common.py
```

Les rapports LaTeX se compilent depuis leur dossier :
`latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex`.

## Conventions scientifiques

- Ablation B (sans crédit) = modèle nul ; la propriété R1 (s=1, c=0, L0=0,
  crédit coupé == M2 exactement, bit à bit) est testée automatiquement.
- Service des intérêts simultané au prorata par emprunteuse (pas de priorité
  par ordre de création).
- « Avalanche » = composante causale du graphe de pertes, PAS un lot de
  faillites du même pas ; les racines indépendantes ne sont pas agrégées.
- Estimateurs : MLE tronqués, LR Pareto/lognormale renormalisé, x_min commun,
  jamais de pooling inter-seed ; chaque estimateur est validé sur données
  synthétiques avant usage réel.
- Ablations D et E injectent délibérément (non conservatif) ; l'injection est
  mesurée et rapportée.
- Journal de recherche et suivi du budget : `NOTES.md`.
