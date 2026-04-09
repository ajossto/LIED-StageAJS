# Note De Réponse Aux Critiques — Round 2

Date: 2026-04-03

Cette note accompagne le nouveau rapport:
- `papers/report_round3_formal_regimes.tex`

et les nouveaux jeux de données:
- `data/round3/wip_long_default_1000.csv`
- `data/round3/wip_k_sweep_aggregate.csv`
- `data/round3/wip_theta_lambda_sweep_aggregate.csv`
- `data/round3/reference_windows.csv`
- `data/round3/reference_slopes.csv`

Ainsi que les nouvelles figures:
- `data/round3/figures/reference_timeseries.png`
- `data/round3/figures/k_sweep_summary.png`
- `data/round3/figures/theta_lambda_density_k3.png`
- `data/round3/figures/theta_lambda_secondary_k3.png`
- `data/round3/figures/theta_lambda_failures_k3.png`

L'esprit de cette revision est le suivant:
- ne plus rafistoler localement les deux anciens papiers;
- consolider les corrections dans un rapport plus predictif;
- separer ce qui est exact au niveau du code, ce qui est mesure, et ce qui reste une fermeture ou une hypothese.

## Reponse Au Relecteur v3/WIP

`1. Contradiction interne sur ΔNW`

Statut: corrige.

Action:
- le nouveau rapport rappelle explicitement que l'auto-investissement impose `ΔNW_i^{endo} = -x_i` instantanement;
- l'effet du pret au deblocage est traite a part, comme mecanisme distinct potentiellement neutre en richesse nette si les postes miroirs se compensent.

`2. Proxy de contagion mal relie au rayon spectral`

Statut: corrige.

Action:
- abandon du vocabulaire ambigu de type ``proxy spectral'';
- introduction de deux metriques distinctes:
  - `s_t^{sec} = C_t / F_t`, part secondaire d'une cascade;
  - `R_t^{sec} = C_t / G_t`, secondaires par faillite deja fragile.

Position explicite:
- ces quantites ne sont pas un rayon spectral;
- `R_t^{sec}` est seulement un proxy branching de premier ordre, plus fidele que l'ancien ratio global.

`3. Incoherence de regime entre 500 et 1000 pas`

Statut: corrige.

Action:
- ajout d'une figure temporelle de la run de reference;
- ajout des tableaux `reference_windows.csv` et `reference_slopes.csv`;
- reformulation de la conclusion:
  - les flux atteignent un quasi-regime apres environ `t = 500`;
  - les stocks continuent de deriver parce que `tau = 0`.

Resultat clef:
- la contradiction apparente entre les batches `500` et `1000` vient d'un melange entre
  observables de flux quasi-stationnaires et observables de stock encore derivants.

`4. Approximation trop forte pour H`

Statut: corrige.

Action:
- la nouvelle derivation conserve le facteur d'age
  `delta_exo * sum q_e (1-delta_exo)^{a_e}`;
- la fermeture `delta_exo * M_t * q_bar` n'est plus presentee comme generique;
- condition d'applicabilite explicite:
  `delta_exo * a_bar << 1`.

`5. Retournement de signe du ratio Jensen`

Statut: corrige par reinterpretation.

Action:
- le nouveau rapport ne cache plus ce retournement;
- il l'interprete comme un changement de regime:
  - phase precoce: covariance `Cov(alpha, sqrt(P))` positive et forte;
  - phase plus tardive: dispersion de `P` et concavite dominent.

Position:
- le signe du biais n'est pas invariant;
- il depend du regime transitoire/tardif.

`6. Incoherence entre deux formules de Gamma`

Statut: corrige par suppression de la source d'ambiguite.

Action:
- le nouveau rapport n'utilise plus deux quantites synthetiques de meme nom;
- il revient a une decomposition discrete directe des flux liquides et productifs;
- le terme `+ iota m` n'est plus promu comme terme principal, mais remplace par un residu net `epsilon_t^ell`.

`7. Cohorte des 162 entites suivies`

Statut: corrige.

Action:
- la regle de suivi est maintenant explicite:
  - toutes les entites initiales;
  - environ `3%` des naissances ulterieures;
- la survie principale est desormais calculee sur la population complete de la simulation.

Resultat clef:
- cohorte initiale et cohortes nees apres `t=0` ont des RMST tres differents;
- la critique de representativite etait donc justifiee.

`8. Denominateur de la contrainte d'endettement`

Statut: clarifie.

Action:
- le nouveau rapport explicite que `rho_b` n'est pas une simple normalisation;
- il fait partie du mecanisme actif d'intermediation:
  une entite deja creanciere peut accroître sa capacite d'emprunt.

Conclusion:
- ce couplage contribue directement a l'emergence d'intermediaires endogenes.

`9. Terme + iota m`

Statut: corrige.

Action:
- le rapport round 3 retire ce terme du coeur de l'equation de liquidite;
- il est remplace par un residu de fermeture `epsilon_t^ell`, explicitement non calibre.

## Reponse Au Relecteur v2

`1. Contradiction sur ΔNW sous auto-investissement`

Statut: corrige conceptuellement.

Action:
- le rapport round 3 rappelle explicitement que l'auto-investissement reduit immediatement la richesse nette;
- la formulation ancienne n'est plus retenue dans la synthese actuelle.

`2. Quantite diagnostique utilisant alpha * sqrt(p)`

Statut: corrige conceptuellement.

Action:
- le nouveau rapport distingue toujours le terme exact `Pi_eff` des fermetures optimistes;
- il n'emploie plus `alpha * sqrt(p)` comme identite non discutee.

`3. Condition d'acceptation du credit incomplete`

Statut: accepte comme point encore ouvert.

Action:
- pas de fausse fermeture ajoutee;
- la limitation est maintenant assumee comme ouverture analytique.

`4. Non-comparabilite 300 vs 1000 pas`

Statut: corrige.

Action:
- le rapport round 3 fait un usage explicite des fenetres tardives et des horizons fixes;
- il ne compare plus directement des moyennes `300` et `1000` comme si elles etaient de meme nature.

`5. Hazard h(t) circulaire`

Statut: accepte comme limitation de fermeture.

Action:
- le nouveau rapport evite de sur-vendre un point fixe ferme;
- la dynamique est discutee au niveau discret et empirique plutot qu'au niveau d'une EDO fermee par hazard postule.

`6. Difference structurelle de q_max entre v2 et v3`

Statut: clarifie.

Action:
- le rapport round 3 explicite que `v3/WIP` retranche le surplus deja mobilisable `S_b`, alors que `v2` ne le fait pas;
- cette difference est maintenant interpretee comme difference structurelle de probleme de choix, pas comme detail de notation.

## Reponse Aux Critiques Conceptuelles Plus Larges

Plusieurs critiques du document exhaustif sont acceptees comme limites de portee du modele:
- absence de marche des biens;
- numeraire abstrait;
- absence de calibration economique realiste;
- usage prudent du terme SOC.

Action:
- le nouveau rapport adopte une position explicite de systeme abstrait dirige et non de modele macroeconomique calibre;
- la conclusion parle de regime dense a avalanches, pas de SOC statistiquement etablie;
- la carte de parametres est presentee comme outil d'exploration des regimes numeriques, pas comme calibration d'une economie reelle.

## Ce Qui Est Maintenant Resolu

- la contradiction sur `ΔNW` est corrigee;
- la confusion proxy de contagion / rayon spectral est levee;
- la non-stationnarite est documentee au lieu d'etre ignoree;
- la cohorte suivie est definie et de-priorisee au profit de la population complete;
- l'accumulation de fragilite cachee est rederivee avec son facteur d'age;
- une carte de parametres exploitable pour viser un regime dense avec avalanches est fournie.

## Ce Qui Reste Ouvert

- une vraie estimation de matrice de reproduction et de `rho(B_t)`;
- un test statistique formel de criticite;
- une fermeture structurelle de `H_t`;
- une fermeture analytique du hazard dans `v2`;
- une stationnarisation plus propre des stocks si l'on veut parler d'attracteur complet plutot que de quasi-regime de flux.

## Conclusion

La revision round 3 change la nature de l'analyse. On ne cherche plus a soutenir trop vite une these forte de criticite auto-organisee. On construit a la place un modele formel plus modeste mais plus utile:
- il explique pourquoi `k`, `theta` et `lambda` sont les trois commandes principales du regime;
- il permet de regler un compromis entre densite du reseau, propagation secondaire et survie de population;
- il fournit enfin une lecture compatible avec les critiques de stationnarite, de definition des observables et de fermeture theorique.
