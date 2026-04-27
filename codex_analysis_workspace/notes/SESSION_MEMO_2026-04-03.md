# Session Memo — 2026-04-03

But de la session:
- construire une formalisation mathematique predictive des modeles numeriques du depot;
- identifier les reperes de modele;
- produire des papiers/notes;
- repondre aux critiques successives;
- calibrer le WIP pour obtenir un reseau dense avec avalanches de faillites.

## Reperes du depot

- premier modele stable a documenter: `arborescence_modeles/stable/v2_modulaire_stable_A_documenter_DONE -> claude3-v2`
- dernier modele commite: `HEAD:claude3-v3-27-mars`
- WIP courant: `Modèle_sans_banque_wip`
- verification faite: les fichiers centraux du WIP et de `claude3-v3-27-mars` coincident pour l'analyse pratique.

## Livrables principaux

Anciens papiers:
- `papers/paper_v2_baseline.tex`
- `papers/paper_v2_baseline.pdf`
- `papers/paper_v3_wip_criticality.tex`
- `papers/paper_v3_wip_criticality.pdf`

Livrables canoniques de fin de session:
- `papers/report_round3_formal_regimes.tex`
- `papers/report_round3_formal_regimes.pdf`
- `reviews/note_reponse_round2.md`

Jeux de donnees et figures utiles:
- `data/round3/wip_long_default_1000.csv`
- `data/round3/wip_long_default_1000_aggregate.csv`
- `data/round3/wip_k_sweep_aggregate.csv`
- `data/round3/wip_theta_lambda_sweep_aggregate.csv`
- `data/round3/reference_windows.csv`
- `data/round3/reference_slopes.csv`
- `data/round3/round3_summary.json`
- `data/round3/figures/reference_timeseries.png`
- `data/round3/figures/k_sweep_summary.png`
- `data/round3/figures/theta_lambda_density_k3.png`
- `data/round3/figures/theta_lambda_secondary_k3.png`
- `data/round3/figures/theta_lambda_failures_k3.png`

Critiques lues:
- `reviews/review_critique_paper_v2_baseline.txt`
- `reviews/review_critique_paper_v3_wip_criticality.txt`
- `reviews/review_v2_round2.txt`
- `reviews/review_v3_round2.txt`
- `Modèle_sans_banque_wip/critique_exhaustive_modele.txt`

## Conclusions techniques actuelles

### v2
- l'auto-investissement reduit bien la richesse nette instantanee;
- les fermetures de production doivent distinguer `E[alpha sqrt(P)]` et `alpha sqrt(E[P])`;
- le hazard reste non ferme analytiquement;
- v2 sert surtout de baseline topologiquement contrainte.

### WIP
- la bonne lecture n'est pas un attracteur pleinement stationnaire, mais:
  - quasi-regime des flux apres environ `t = 500`;
  - derive persistante des stocks, surtout du nombre de prets actifs, tant que `tau = 0`.
- l'ancien pseudo-proxy spectral a ete abandonne;
- on utilise maintenant:
  - part secondaire d'une cascade;
  - secondaires par faillite deja fragile;
- la cohorte des entites suivies n'est pas representative de la population complete;
- la survie principale est maintenant lue sur la population complete.

## Carte de parametres du WIP

Effets principaux:
- `k = n_candidats_pool` controle la connectivite et l'intermediation;
- `theta` controle le levier et l'intensite des avalanches;
- `lambda_creation` controle le renouvellement de population.

Resultats clefs:
- `k <= 2`: reseau trop mince, pas d'avalanches;
- `k >= 3`: seuil topologique franchi, propagation possible.

Regimes recommandes:
- compromis dense + avalanches soutenues:
  - `k = 3`
  - `theta in [0.35, 0.5]`
  - `lambda ≈ 2`
- regime plus agressif type "feu de foret":
  - `k = 3`
  - `theta ≈ 0.7`
  - `lambda ≈ 2`

## Notes d'environnement

- les figures round3 ont ete rendues avec le venv:
  - `/home/anatole/jupyter/.venv`
- `matplotlib` y est disponible.

## Si je reprends plus tard

Ordre de lecture recommande:
1. `papers/report_round3_formal_regimes.tex`
2. `reviews/note_reponse_round2.md`
3. `data/round3/round3_summary.json`
4. `data/round3/reference_windows.csv`
5. `data/round3/wip_theta_lambda_sweep_aggregate.csv`
6. les figures dans `data/round3/figures/`

Question directrice a garder:
- construire un modele formel suffisamment fidele pour predire les observables finaux du WIP et choisir des parametres produisant un reseau dense avec avalanches.
