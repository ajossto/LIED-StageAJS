# M4.2B — société de crédit à cible de principal arithmétique

Successeur expérimental direct de M4.2. Question de recherche : une queue
Pareto des revenus d'intérêt reçus peut-elle émerger et être contrôlée sans
détruire la structure en loi de puissance des avalanches de faillites ?

Document d'autorité : `prompts/PROMPT_M4_2B.md`. En cas de conflit entre un
document et le code : **le code exécuté fait foi**.

## Ce que M4.2B change par rapport à M4.2

- cible de principal **arithmétique** `K_target=(K_ℓ+K_b)/2` (au lieu de la
  cible géométrique `√(K_ℓK_b)`) : `q_A=(K_ℓ-K_b)/2` exactement, les deux
  capitaux s'égalisent après transfert. Bascule `Config.target_rule ∈
  {"arithmetic","geometric"}` — `"geometric"` reproduit M4.2 bit-à-bit ;
- taux **inchangé** (moyenne géométrique des rendements marginaux) — séparé
  structurellement du calcul du principal (`_pair_rate` / `_pair_principal`) ;
- baseline scientifique **lente** : δ=0,01, σ=0,01 (au lieu de 0,05/0,25) ;
- famille d'intensité de marché explicite η_{ρ,β}(N)=ρ·N_ref·(N/N_ref)^β
  (β=1 ⇒ ρ·N, reproduit η(N)=N de M4.2 à ρ=1) ;
- nouvelle table `loan_events.csv.gz` : r, q, rq et rq/K_b', rq/F_γ(K_b')
  par transaction réussie du marché (diagnostic de pathologie de service).

Tout le reste (chocs ξ, service des intérêts, dépréciation, faillites
cancel+destroy, avalanches causales, pool d'appariement k≡2, schéma de
sorties) est hérité de M4.2 sans changement — **parité vérifiée à
0,000e+00 d'écart flottant** (pas seulement en tolérance) quand
`target_rule="geometric", rho=1, eta_beta=1`.

## Arborescence

```
m4_2b/                 moteur (model.py + io.py, version m4_2b-1)
run.py                 lanceur CLI
tests/                 test_engine.py, test_parity_m4_2.py,
                       test_arithmetic_institution.py (grille §2),
                       test_interest_income_tools.py
scripts/               lib_metrics.py, lib_screening.py (copies M4.2,
                       inchangées), families.py, tail_test.py (copies
                       corrigées, cf. docstrings de provenance),
                       pareto_convention.py (NOUVEAU : réconciliation
                       κ_CCDF/α_densité), interest_income.py (NOUVEAU :
                       masse en zéro, décomposition Var(log I), test
                       exponentielle-vs-Pareto, ajustement par snapshot),
                       pilot_sigma_and_control.py, pilot_lambda_scan.py
                       (pilotes exécutés, pas une campagne figée)
results/               pilot_baseline_seed0/ (T=3000), pilot_sigma_control/,
                       pilot_lambda_scan/, rho_contrast_pilot.json,
                       composite_family_aic_pilot.json
report/                resume.md, rapport_pilote.tex/.pdf
prompts/               cahier des charges (figé, intouché)
JOURNAL.md             journal de recherche chronologique (avec les
                       hypothèses de départ infirmées en cours de route)
```

## Démarrage rapide

```bash
cd /home/anatole/jupyter/m4_2b_credit_soc

# Tests (moteur + parité + institution + outils statistiques)
/home/anatole/jupyter/.venv/bin/python3 tests/test_engine.py
/home/anatole/jupyter/.venv/bin/python3 tests/test_parity_m4_2.py
/home/anatole/jupyter/.venv/bin/python3 tests/test_arithmetic_institution.py
/home/anatole/jupyter/.venv/bin/python3 tests/test_interest_income_tools.py

# Auto-test de la convention alpha/kappa
/home/anatole/jupyter/.venv/bin/python3 scripts/pareto_convention.py

# Un run direct (hors lab), baseline
/home/anatole/jupyter/.venv/bin/python3 run.py --gamma 0.5 --delta 0.01 \
    --sigma 0.01 --steps 3000 --output results/mon_run

# Reproduire les pilotes exécutés (contrôle géométrique + balayage sigma)
/home/anatole/jupyter/.venv/bin/python3 scripts/pilot_sigma_and_control.py
# Balayage lambda
/home/anatole/jupyter/.venv/bin/python3 scripts/pilot_lambda_scan.py
```

## Simulation Lab

Modèle actif (`model_id = m4_2b_credit_soc`, adaptateur
`modeles-systeme-physicoeconomique/m4_2b_credit_soc/`), avec les 28 figures
M4.2/M4B réutilisées SANS MODIFICATION (`reporting.py` copié tel quel —
générique, ne suppose jamais la cible géométrique). Validé par un run de
fumée bout-en-bout (28 recettes → aucune erreur de figure).

```bash
cd /home/anatole/jupyter
/home/anatole/jupyter/.venv/bin/python3 -m simulation_lab.cli gui --open-browser
# ou : ... cli run --model m4_2b_credit_soc --seed 0 --params '{"gamma":0.5}'
```

## Résultat principal (voir `report/resume.md` pour le détail)

À la baseline (γ=0,5, δ=0,01, σ=0,01, K0=25, η(N)=N) : **pas de régime
Pareto robuste pour les intérêts reçus** — mécanisme identifié (le
principal arithmétique homogénéise le capital, Gini(K)≈0,05 ; le revenu
d'intérêt est dominé à 77 % par le nombre de contrats accumulés avec l'âge,
23 % seulement par la taille/taux individuels des contrats). σ, λ et ρ
déplacent des coupures, pas la forme du corps (invariante). Le contrôle
géométrique montre que la règle arithmétique rend l'objectif A **plus
difficile** que la règle géométrique (M4.2), pas plus facile. Côté
avalanches, un exposant indépendant de la taille n'a PAS été établi (dérive
de τ̂ avec λ, en partie un artefact de coupure hors-portée à λ=100) ; le
rapport de branchement (~0,78-0,79) est en revanche robuste et pinné
institutionnellement, comme dans M4.2 mais à un niveau différent.

## Sources amont (lecture seule)

1. `../m4_2_credit_soc/` — moteur, spécification et rapport M4.2.
2. `../m4b_credit_soc_mini/` — moteur et spécification M4B.
3. `../recherche/analyse_distributions_taille_revenu/` — outils de
   comparaison de familles continues et de test de queue (réutilisés).
4. `../recherche/sensibilite_m4b/` — méthodologie de campagne.

M4, M4B, M4.2 sont des références en lecture seule, non modifiées.

## Statut

Phase pilote complète (voir `JOURNAL.md`). Non testé : γ≠0,5, K0≠25, η
non linéaire (β≠1), ablations de mécanisme, collapse de taille finie en
bonne et due forme — voir `JOURNAL.md` §8 et `report/resume.md` pour le
détail de ce qui reste ouvert.
