# Note De Reponse Aux Critiques — Round 4

Date: 2026-04-09

Cette note accompagne les nouveaux livrables round 4:
- `papers/report_round4_predictive_bridge.tex`
- `data/round4/k_sweep_multiseed.csv`
- `data/round4/k_sweep_multiseed_aggregate.csv`
- `data/round4/reference_spectral_timeseries.csv`
- `data/round4/reference_spectral_summary.csv`
- `data/round4/population_fixed_point_validation.csv`
- `data/round4/population_fixed_point_validation_informative.csv`
- `data/round4/hidden_fragility_validation.csv`
- `data/round4/default_horizon_comparison.csv`
- `data/round4/default_horizon_comparison_aggregate.csv`

Et les nouvelles figures:
- `data/round4/figures/k_sweep_multiseed_summary.png`
- `data/round4/figures/reference_spectral_timeseries.png`
- `data/round4/figures/population_fixed_point_validation.png`
- `data/round4/figures/hidden_fragility_validation.png`

Le but du round 4 n'est pas de pretendre avoir ferme tout le modele. Le but est plus modeste et plus utile:
- transformer trois critiques formelles en objets quantifies;
- corriger une fermeture incorrecte de la fragilite cachee;
- clarifier ce que le WIP predit deja, et ce qu'il ne predit pas encore.

## Synthese

Le round 4 apporte quatre resultats nouveaux.

1. `beta_k` est maintenant mesure proprement sur un `k`-sweep a `10` seeds avec intervalles de confiance `t` de Student.
2. Le point fixe de population
   `N* = lambda / h*`
   est valide dans les regimes ou le hazard tardif est effectivement positif.
3. La bonne fermeture de la fragilite cachee n'utilise pas `delta_exo` comme hazard de sortie des prets; elle utilise
   `gamma_loan = beta / m`,
   ce qui reproduit bien le ratio observe.
4. `rho(B_t)` est desormais estime numeriquement sur la run de reference, avec sa structure topologique associee (taille de SCC).

## Reponse Point Par Point

### A1. Aucune prediction analytique derivee

Statut: partiellement corrige.

Ce qui est maintenant derive et teste:
- `N* = lambda / h*` a partir de `N_{t+1} - N_t = Xi_t - F_t` et `F_t ~= h* N_t`;
- `H/Q = 1 - gamma_loan / (1 - (1-gamma_loan)(1-delta_exo))` avec `gamma_loan = beta / m`;
- une mesure effective de `rho(B_t)` sur la trajectoire de reference.

Ce qui n'est pas encore ferme:
- une expression fermee de `beta_k(k, F_r)` sans calibration;
- une prediction complete de `m*` a partir de `(k, theta, lambda)` sans simulation.

Conclusion:
- le WIP n'est toujours pas un modele predictif complet;
- mais il n'est plus seulement une carte empirique brute.
  Il existe maintenant un pont predictif minimal sur `N*`, `H/Q` et la structure spectrale.

### A2. `beta_k` derivable mais jamais derive

Statut: partiellement corrige.

Action:
- definition operationnelle explicite
  `beta_k = credit_transactions / N`
  en fenetre tardive;
- nouveau `k`-sweep a `10` seeds, `400` pas, `theta = 0.35`, `lambda = 2`.

Resultats:
- `k = 1`: `beta ~= 3.70e-4`
- `k = 2`: `beta ~= 3.35e-3`
- `k = 3`: `beta ~= 5.13e-2`
- `k = 4`: `beta ~= 1.06e-1`
- `k = 5`: `beta ~= 1.36e-1`

Le saut central est bien entre `k = 2` et `k = 3`:
- `beta_3 / beta_2 ~= 15.3`
- `m_3 / m_2 ~= 5.2`

Position:
- le seuil topologique est maintenant quantifie proprement;
- mais il reste semi-empirique.
  Le round 4 mesure le bon objet et confirme le saut critique, sans encore donner une formule fermee pure en `k`.

### A3. Fragilite cachee non fermee

Statut: corrige, mais pas avec la fermeture proposee par le relecteur.

Point cle:
- dans le code, `delta_exo` deprecie la valeur economique des creances;
- mais avec `tau = 0`, il ne supprime pas les prets actifs.

Donc:
- `delta_exo` n'est pas le hazard de sortie du portefeuille;
- le bon hazard de portefeuille est `gamma_loan = beta / m`.

Sous hypothese geometrique sur l'age des prets actifs:
- `P(A = a) ~= gamma_loan (1-gamma_loan)^a`
- `H/Q = 1 - E[(1-delta_exo)^A]`
- d'ou
  `H/Q = 1 - gamma_loan / (1 - (1-gamma_loan)(1-delta_exo))`

Validation:
- run de reference `seed = 42`, `1000` pas:
  - observe: `0.9057`
  - predit: `0.9006`
- moyenne absolue de l'erreur sur les `46` runs round 3:
  - `0.0113`

Conclusion:
- la fermeture de `H` est maintenant correcte conceptuellement;
- elle explique le ratio tardif eleve sans utiliser une hypothese d'age incompatible avec le code.

### A4. Critere spectral vide

Statut: corrige.

Action:
- estimation numerique de `rho(B_t)` sur la run de reference `seed = 42`;
- mesure conjointe de la taille de la plus grande composante fortement connexe.

Resultats:
- fenetre `0-500`:
  - `rho_B` moyen `~= 0.107`
  - `SCC_max` moyen `~= 1.28`
  - `SCC_max` max `= 3`
- fenetre `500-1000`:
  - `rho_B` moyen `~= 0.422`
  - `SCC_max` moyen `~= 14.96`
  - `SCC_max` max `= 95`

Comparaison propagation:
- `secondary_per_fragile` passe de `0.037` a `0.377` entre les deux fenetres.

Conclusion:
- le critere spectral n'est pas vide dans le regime tardif;
- il devient informatif seulement quand de vraies boucles de credit apparaissent.

### B1. Seulement 2 seeds par configuration

Statut: partiellement corrige.

Action:
- `k`-sweep central rerun a `10` seeds;
- intervalles de confiance `95%` calcules avec `t` de Student.

Limite restante:
- la carte `(theta, lambda)` de round 3 reste exploratoire a `2` seeds;
- elle n'est pas promue ici au meme niveau de confiance que le `k`-sweep round 4.

### B2. La population decline dans le quasi-regime

Statut: accepte et clarifie.

Le round 4 confirme que la critique etait juste:
- sur la reference `1000` pas, la pente tardive de `N` reste negative;
- le bon langage n'est pas attracteur complet, mais quasi-regime de flux.

Action:
- le point fixe `N* = lambda / h*` est maintenant utilise comme diagnostic local;
- il faut lire ce point fixe comme fermeture de regime tardif, pas comme preuve de stationnarite stricte sur tous les stocks.

### B3. Incoherence batch long / sweep

Statut: corrige.

Action:
- comparaison explicite sur les memes seeds `42-45`, meme config, horizons `400` et `1000`.

Resultats:
- a `400` pas:
  - prets/entite `~= 4.18`
  - `beta ~= 0.0515`
  - `h ~= 0.00166`
- a `1000` pas:
  - prets/entite `~= 6.93`
  - `beta ~= 0.0734`
  - `h ~= 0.00353`

Conclusion:
- la divergence round 3 n'etait pas principalement un probleme de seeds;
- c'etait surtout un probleme d'horizon.
  A `k = 3`, `400` pas reste pre-asymptotique.

### C4. Errata v2 incomplets

Statut: corrige.

Action:
- correction de la phrase contradictoire dans
  `papers/paper_v2_baseline.tex`.

## Ce Qui Est Maintenant Resolu

- `beta_k` est quantifie proprement avec `10` seeds sur le sweep central en `k`;
- le seuil `k = 3` est confirme quantitativement;
- `N* = lambda / h*` est valide dans les regimes de cascades actives;
- la fermeture de `H/Q` est corrigee et testee;
- `rho(B_t)` est estime numeriquement;
- l'ecart `400` vs `1000` pas sur le scenario par defaut est explique;
- l'erratum `v2` restant est corrige.

## Ce Qui Reste Ouvert

1. une formule fermee de `beta_k` en fonction des statistiques d'ordre du marche du credit;
2. une prediction explicite de `m*` sans calibration intermediaire;
3. un rerun `10` seeds de la carte `(theta, lambda)`;
4. une theorie plus structurelle du passage de `rho(B_t) ~ 0.1` a `~ 0.4` avec apparition de cycles;
5. une stationnarisation des stocks si l'objectif devient un attracteur complet plutot qu'un quasi-regime de flux.

## Conclusion

Le round 4 ne boucle pas toute la theorie, mais il ferme enfin trois objets qui restaient rhetoriques:
- `beta_k` comme intensite de creation de credit;
- `N*` comme point fixe local de population;
- `H/Q` comme fermeture geometrique correcte du portefeuille.

Le rapport suivant peut donc viser une etape plus ambitieuse: une vraie fermeture semi-empirique de `beta_k(k, theta, lambda)` et une prediction explicite de `m*`, au lieu de seulement consolider des critiques.
