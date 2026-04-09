# Note Au Relecteur

Date: 2026-04-03

Ce document accompagne la version actuelle des deux papiers:
- `paper_v2_baseline.tex`
- `paper_v3_wip_criticality.tex`

Il repond aux remarques formulees dans:
- `review_critique_paper_v2_baseline.txt`
- `review_critique_paper_v3_wip_criticality.txt`

L'objectif de cette revision n'a pas ete de durcir artificiellement les conclusions, mais au contraire de separer plus proprement:
- ce qui est directement implemente par le code;
- ce qui est mesure empiriquement sur simulations;
- ce qui reste une hypothese analytique ou une fermeture de champ moyen.

## Synthese Generale

Les principales corrections apportees sont les suivantes:
- correction des formules de richesse nette sous auto-investissement dans `v2` et `v3/WIP`;
- distinction explicite entre regles exactes du code et approximations continues ou stochastiques;
- traitement explicite du biais de Jensen dans les fermetures de production;
- clarification de la derive moyenne implicite du brownien geometrique sur `alpha`;
- abaissement des formulations trop fortes sur la SOC et le seuil spectral;
- ajout de statistiques de survie censuree;
- ajout d'un batch multi-seeds plus long pour le WIP;
- ajout d'un appendice qui derive le champ moyen a partir des increments discrets.

En pratique, la revision deforme moins le contenu qu'elle ne le recadre. Les papiers sont maintenant plus prudents sur le plan epistemique et plus explicites sur le plan mathematique.

## Reponse Sur Le Papier v2

`1. Auto-investissement et valeur nette`

Statut: accepte et corrige.

Correction:
- la formule erronee `\Delta NW_i^{endo}=0` a ete remplacee par `\Delta NW_i^{endo}=-x_i`;
- le texte dit maintenant explicitement que l'auto-investissement conserve l'actif brut mais augmente la taille engagee.

`2. Matching deterministe et non stochastique`

Statut: accepte et corrige.

Correction:
- la topologie de `v2` est desormais decrite d'abord comme procedure deterministe conditionnelle a l'etat;
- le noyau stochastique n'apparait plus que comme approximation analytique lissée.

`3. Condition d'acceptation du credit insuffisamment analysee`

Statut: accepte et corrige partiellement.

Correction:
- ajout d'un developpement de Taylor de premier ordre;
- reinterpretation de la contrainte comme borne sur l'ecart admissible entre rendement marginal local et taux propose.

Limite restante:
- pas encore de fermeture complete en fonction des tailles relatives preteur/emprunteur.

`4. Terme agregé de liquidite mal justifie`

Statut: accepte et corrige.

Correction:
- suppression du terme `+\iota m` dans l'equation de liquidite de `v2`;
- meilleur decouplage entre production moyenne et redistribution financiere.

`5. Jensen`

Statut: accepte et corrige.

Correction:
- la production moyenne est maintenant ecrite via `\mathbb E[\alpha \sqrt{P_i}]`;
- le papier rappelle explicitement que `\sqrt{\mathbb E[P]}` est une fermeture optimiste.

Ajout quantitatif:
- sur `10` seeds et `300` pas, `E[\sqrt P]/\sqrt{E[P]} \approx 0.9907 \pm 0.0064`.

`6. Approximation de duree de vie trop forte`

Statut: accepte et reformule.

Correction:
- l'approximation de type premier passage n'est plus presentee comme loi validee, mais comme developpement heuristique de premier ordre.

`7. Censure a droite`

Statut: accepte et corrige.

Correction:
- les durees de vie reportees sont maintenant explicites comme durees de defuntes non censurees;
- le texte mentionne qu'une analyse de survie complete requerrait Kaplan-Meier.

`8. Rayon spectral non mesure`

Statut: accepte et reformule.

Correction:
- la section spectrale est desormais presentee comme cadre theorique de localisation de cascade, non comme resultat empirique etabli.

## Reponse Sur Le Papier v3/WIP

`1. Jensen mal applique`

Statut: accepte et corrige.

Correction:
- remplacement de `\bar\alpha \sqrt p` par `\Pi_{\mathrm{eff}}(p,t)=\mathbb E[\alpha_i\sqrt{P_i}]`;
- ajout de la decomposition covariance plus concavite.

Ajout quantitatif:
- sur `5` seeds et `200` pas, `E[\sqrt P]/\sqrt{E[P]} \approx 0.99827 \pm 0.00014`;
- sur le meme batch, `E[\alpha\sqrt P]/(\bar\alpha\sqrt{E[P]}) \approx 1.00079 \pm 0.00060`.

`2. Esperance du brownien geometrique`

Statut: accepte et corrige.

Correction:
- ajout de la derive implicite `e^{\sigma^2 t/2}` dans le texte;
- distinction claire entre le code tel quel et une version martingale corrigee qui n'est pas implemente.

Ajout quantitatif:
- avec `\sigma=0.005`, le multiplicateur theorique vaut `1.0025` a `t=200`, `1.0038` a `t=300`, `1.0126` a `t=1000`;
- sur le batch court WIP, `\bar\alpha_final \approx 1.0018 \pm 0.0046`.

`3. Pretention de criticite auto-organisee`

Statut: accepte et corrige.

Correction:
- toutes les formulations fortes ont ete baissees;
- le papier parle maintenant de regime proche d'un seuil critique plausible, pas de SOC demontree.

Ajout quantitatif:
- ajout d'un proxy de contagion `\approx 0.272`;
- ajout d'un estimateur de Hill brut `\approx 4.56` sur le top `20%` des volumes de cascades, avec mention explicite que cela ne constitue pas un test de loi de puissance.

`4. Champ moyen sous-specifie`

Statut: accepte et corrige.

Correction:
- le papier indique explicitement que les coefficients de fermeture ne sont pas calibres;
- les EDO sont presentees comme outils qualitatifs d'intelligibilite dynamique.

`5. Approximation diffusionnelle de la duree de vie`

Statut: accepte et reformule.

Correction:
- le papier indique maintenant qu'une diffusion continue est peu fidele pendant les cascades et qu'un modele a sauts serait plus proche du discret.

Ajout quantitatif:
- ajout de `\hat S(1000)\approx 0.198` et `\mathrm{RMST}_{1000}\approx 495.9` sur les entites suivies.

`6. Matrice de reproduction non calculee`

Statut: accepte et reformule.

Correction:
- le seuil spectral est maintenu comme cadre theorique, sans pretendre avoir estime `\rho(\mathcal B_t)`.

Ajout quantitatif:
- ajout d'un proxy empirique simple de contagion, avec mention explicite qu'il ne remplace pas une mesure spectrale.

`7. Equation de H`

Statut: traite partiellement mais substantiellement ameliore.

Correction:
- ajout d'un appendice de derivation discret-vers-continu partant de `\Delta \mathcal H_t`;
- clarification de `\omega` comme taux effectif de fermeture, et non comme parametre litteral du code.

Point encore ouvert:
- une derivation plus structurelle de `\omega` directement a partir des regles discretes de vieillissement et de disparition des creances serait preferable.

`8. Clarification sur NW et les postes miroirs`

Statut: accepte et clarifie.

Correction:
- le texte maintient l'ecriture de `NW_i` en expliquant plus clairement la compensation de certains postes miroirs.

`9. Une seule trajectoire`

Statut: accepte et corrige.

Correction:
- le papier distingue desormais explicitement la trajectoire de reference et les resultats inter-runs.

Ajout quantitatif:
- batch `8` seeds / `500` pas:
- `alive_final \approx 716.5 \pm 90.3`;
- `failures_total \approx 385.0 \pm 79.7`;
- `mean_extraction \approx 9629.9 \pm 743.9`;
- `mean_credit_tx \approx 22.70 \pm 2.72`;
- `mean_active_loans \approx 1926.7 \pm 136.6`;
- `mean_failures_per_step \approx 0.770 \pm 0.159`;
- `mean_lifespan_failed \approx 259.8 \pm 30.0`.

`10. Ambiguite de q_max`

Statut: accepte et corrige.

Correction:
- ajout de la derivation explicite de `q_max` comme optimum statique du programme de l'emprunteur, avant troncature et application du facteur comportemental `\theta`.

`11. Derivation discret-vers-continu insuffisamment explicite`

Statut: accepte et corrige.

Correction:
- ajout d'un appendice qui derive successivement `\dot N`, `\dot \ell`, `\dot p`, `\dot m` et `\dot H` a partir des increments moyens des etapes discretes;
- clarification du statut des termes de fermeture `\eta`, `\iota`, `\kappa_\bullet`, `\omega`.

## Ce Qui Est Maintenant Etabli, Mesure Ou Ouvert

`Etabli au niveau du code`
- les regles discretes de creation, extraction, interets, depreciation, credit, faillite et auto-investissement;
- la concavite de la production individuelle;
- l'existence d'une contrainte de service de dette dans le WIP;
- l'existence d'une topologie de credit plus dense et plus multi-etage dans le WIP que dans `v2`.

`Mesure empiriquement`
- les ordres de grandeur de production, densite du graphe de credit, faillites et survie;
- la faiblesse empirique du biais de Jensen dans les regimes testes;
- le caractere non trivial de la contagion par cascade.

`Reste ouvert`
- calibration rigoureuse du champ moyen;
- estimation effective d'une matrice de reproduction et de son rayon spectral;
- test statistique formel de criticite;
- modelisation plus structurelle de la fragilite cachee `H`;
- analyse de survie plus complete, au-dela des statistiques actuellement ajoutees.

## Conclusion Au Relecteur

La revision actuelle a principalement corrige des sur-enonces et comble des trous de derivation. Le coeur du message est maintenant plus resserre:
- `v2` est un systeme de credit a topologie fortement contrainte, mathematiquement lisible via concavite, derive de valeur nette et contagion linearisée;
- `v3/WIP` est un systeme de graphe stochastique dirige sous contrainte de bilan, avec heterogeneite de productivite, fragilite cachee et dynamique de cascade;
- les EDO et les conditions spectrales sont presentees comme instruments d'analyse theorique, pas comme verites deja calibrees;
- la criticite reste une hypothese raisonnable de lecture, non un resultat statistiquement clos.

Autrement dit, les papiers sont maintenant plus proches d'une note mathematique honnete sur un systeme complexe discret: plus explicites sur les mecanismes, plus prudents sur les conclusions, et mieux relies au code effectif.
