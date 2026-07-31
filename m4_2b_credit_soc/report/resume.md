# M4.2B — résumé (30 juillet 2026, phase pilote)

**Question posée** : une queue Pareto endogène des revenus d'intérêt reçus
peut-elle émerger et être contrôlée dans une société de crédit à cible de
principal arithmétique, sans détruire la structure en loi de puissance des
avalanches de faillites héritée de M4/M4B/M4.2 ?

## Réponse

**À la baseline demandée (γ=0,5, δ=0,01, σ=0,01, K0=25, η(N)=N), l'objectif
A échoue et le mécanisme est identifié ; l'objectif B n'est pas établi comme
indépendant de la taille du système.** Le budget de cette phase a été
consacré aux pilotes qui apportaient l'information causale la plus grande
(contrôle géométrique, balayages σ et λ, décomposition Var(log I)) plutôt
qu'à une grille exhaustive de η — conformément à la liberté de recherche
accordée par le prompt (§17).

## Terminologie

« Fait observé » = mesuré directement dans le code, les tests ou les runs.
« Inférence » = interprétation appuyée sur plusieurs faits. « Hypothèse » =
mécanisme proposé, pas encore établi. « Incertitude » = non tranché par les
données disponibles.

## Ce qui a été établi

| Résultat | Niveau |
|---|---|
| Parité stricte M4.2B(target_rule=geometric,ρ=1,β=1) ≡ M4.2 : écart flottant 0,000e+00 sur 2 régimes M4.2 + 1 régime baseline M4.2B | Fait observé (test automatisé) |
| q_A/q_geo=(1+√(K_ℓ/K_b))/2, sans borne ; K_ℓ'=K_b' exactement après transfert arithmétique | Fait observé (démontré + testé sur grille) |
| 0 défaut de liquidité sur l'ensemble des runs pilotes (100 % des racines de faillite sont des insolvabilités) | Fait observé |
| Gini(K)=0,052-0,064 à la baseline, quasi invariant sur λ∈{10,30,100} et sous les deux target_rule ; ne bouge qu'à σ=0,10 (→0,08-0,10) | Fait observé |
| Interêts reçus : α̂_density(seuil KS)=3,80±0,18 (46 snapshots), MAIS α̂ retombe à 2,52±0,12 à seuil moitié — instabilité systématique | Fait observé → **pas de régime Pareto robuste** (inférence, §11 critère 6 échoue) |
| Décomposition Var(log I) : 77 % deg_out, 23 % rq moyen, covariance négligeable | Fait observé (identité exacte) |
| Corrélation revenu~âge≈0,89 stable ; R²(revenu~âge)≈0,72 ; âge rejette l'exponentielle stricte (KS p≈0) mais reste sur-dispersé | Fait observé → mécanisme causal (inférence) |
| GB2 gagne systématiquement par AIC sur 3 snapshots testés ; Pareto pure très largement rejetée ; lognormale+Pareto explicite n'apporte rien vs GB2/mélange lognormal | Fait observé |
| Contrôle géométrique (même baseline lente) : branching=0,756 (vs 0,787 arithmétique), Gini(K)=0,053 (identique) — **le branching élevé et le Gini bas ne viennent PAS de l'institution arithmétique** mais de la baseline δ/σ | Fait observé — infirme une inférence provisoire antérieure (voir JOURNAL.md §3) |
| Institution arithmétique vs géométrique à baseline identique : α̂ 3,86 (arithmétique) vs 2,94 (géométrique) — **l'arithmétique donne une queue PLUS légère** | Fait observé → réponse à §21-Q1 |
| σ∈{0,01;0,03;0,05;0,10} : Gini(K) et part deg_out bougent dans le sens prédit, MAIS α̂(seuil KS) s'alourdit (3,86→5,03) tandis que α̂(seuil/2) reste quasi constant (≈2,6-2,8) | Fait observé → σ déplace une coupure (population/durée de vie), pas la forme du corps (§11 critère 7 : pas un contrôle de queue) |
| Avalanches : branching_ratio=0,78-0,79 sur λ∈{10,30,100} et les deux target_rule — pinning institutionnel robuste, à un niveau différent du 0,30 de M4.2 | Fait observé |
| τ̂ dérive avec λ (1,19-1,27 → 1,42-1,45 → 1,75) ; à λ=100 la coupure ajustée sature à e²⁰ (borne numérique de l'optimiseur) : aucune coupure finie détectée — τ̂=1,75 est l'exposant de la loi PURE, pas comparable aux deux autres cellules | Fait observé → **aucun exposant indépendant de la taille établi sur cette plage** (λ confond aussi taille et intensité de marché) |

## Réponses aux questions du prompt (§21) disposant d'un support empirique

1. **Que change la cible arithmétique ?** Principal non borné plus élevé
   (facteur (1+√(K_ℓ/K_b))/2, jusqu'à ~10× à la baseline pour un newborn vs
   une entité proche de K*_aut) ; égalisation exacte des deux capitaux
   (auto-terminaison de la paire après une rencontre, `merge_share`≈2,8 %
   sous les deux règles) ; **rend l'objectif A plus difficile** que la cible
   géométrique (α̂ plus élevé, dominance du degré plus forte).
2. **Forme du corps des intérêts ?** GB2 (4 paramètres), systématiquement
   meilleur par AIC ; exponentielle/Weibull très compétitifs à 1-2
   paramètres (cohérent avec le mécanisme âge→degré) ; lognormale+Pareto
   explicite n'apporte rien.
3. **Queue Pareto robuste ?** Non, dans aucune des configurations testées
   (baseline, σ∈[0,01;0,10], ρ∈{0,125;1;2}, λ∈{10;30;100}, target_rule
   géométrique). L'instabilité de seuil est systématique partout.
4. **Famille globale ?** GB2 pour le corps ; pas de composite Pareto qui
   batte GB2.
9. **Rôle de r, q, rq ?** r quasi constant (bande de 6 % autour de 0,018) ;
   la dispersion du log-revenu vient à 77 % du nombre de contrats (deg_out),
   23 % du rq moyen par contrat.
10. **Pathologie de la règle de taux ?** Non au sens service — 0 défaut de
    liquidité observé ; oui au sens levier — un newborn appairé à une
    entité proche de K*_aut porte un service c=rq tel que c/F_γ(K_b')≈1,57
    dès la création du contrat (production insuffisante ce pas-là), mais la
    faillite qui en résulte (si elle survient) est toujours une insolvabilité
    différée par les chocs, jamais un défaut de service immédiat.
11. **Avalanches en loi de puissance ?** Un exposant indépendant de la
    taille n'est pas établi (§ci-dessus) ; le rapport de branchement est en
    revanche robuste et pinné.
12. **Compromis queue/criticalité ?** σ dégrade LES DEUX à la fois
    (branching ↓, τ̂ ↑ = avalanches moins critiques ; α̂ ↑ = intérêts pas plus
    lourds) — pas de compromis favorable trouvé dans la plage testée.
15. **Exposant, coupure, échelle, masse en zéro ou transitoire ?** Coupure,
    de façon répétée et démontrée (σ, λ, ρ déplacent tous une coupure haute,
    pas la forme du corps ; λ=100 fait saturer l'estimateur de coupure des
    avalanches).

## Non testé (§18 — à ne pas confondre avec un résultat négatif)

γ≠0,5 ; K0≠25 ; η non linéaire (β≠1) ; ablations de mécanisme (règle de
taux alternative, fusion/mémoire des contrats) ; campagne multi-graines
complète par cellule ; collapse de taille finie en bonne et due forme
(nécessiterait de découpler taille du système et intensité de marché, et
un λ>100 avec une coupure d'avalanche correctement dans la plage observée).

## Où trouver quoi

- Moteur et tests : `m4_2b/`, `tests/` (31 tests, tous verts).
- Outils statistiques et leurs auto-tests : `scripts/pareto_convention.py`,
  `scripts/interest_income.py`, `tests/test_interest_income_tools.py`.
- Journal chronologique complet (avec les deux erreurs corrigées en cours
  de route) : `JOURNAL.md`.
- Résultats bruts des pilotes : `results/pilot_baseline_seed0/` (T=3000),
  `results/pilot_sigma_control/`, `results/pilot_lambda_scan/`,
  `results/rho_contrast_pilot.json`, `results/composite_family_aic_pilot.json`.
- Adaptateur Simulation Lab (validé par un run de fumée, 0 erreur de
  figure) : `../modeles-systeme-physicoeconomique/m4_2b_credit_soc/`.
