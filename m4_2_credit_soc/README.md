# M4.2 — société de crédit à production concave généralisée

Successeur direct de M4B. Question de recherche : la pente τ de la
distribution des tailles d'avalanches de faillites est-elle **pilotable par
l'exposant de concavité γ** de la production F_γ(K) = A·K^γ, sans détruire
le régime endogène d'accumulation-relaxation ?

Document d'autorité : `prompts/PROMPT_M4_2.md` (cahier des charges figé,
version de lecture `prompts/PROMPT_M4_2.pdf`). En cas de conflit entre un
document et le code : **le code exécuté fait foi**.

## Ce que M4.2 change par rapport à M4B

- production `A·K^γ` (0<γ<1, A=1 hors ablation d'échelle) ; γ=1/2 ≡ M4B ;
- taux d'intérêt dérivés des rendements marginaux `m=A·γ·K^(γ-1)`
  (moyenne géométrique, institution explicite) ; cible K* = √(K_ℓ·K_b)
  pour tout γ (démontré et testé) ;
- pool d'appariement **fixé à deux** (k≡2, retiré de la configuration) ;
- fonction d'intensité du marché **η(N)=N** nommée et instrumentée
  (colonnes `mkt_pool`, `mkt_rounds`, `mkt_new_edges`, `mkt_merges`) ;
- notation : le choc s'écrit ξ (η est réservé au marché).

Tout le reste (chocs, service des intérêts, dépréciation, faillites
cancel+destroy, avalanches causales, schéma de sorties) est identique à
M4B — vérifié par tests de parité pas à pas (γ=1/2 vs M4B k=2 : discret
identique, flottant ≤3·10⁻¹² sur 1000 pas).

## Arborescence

```
m4_2/                  moteur (model.py + io.py, version m4_2-1)
run.py                 lanceur CLI
tests/                 test_engine.py (points 1-13), test_parity_m4b.py,
                       test_stats.py (estimateurs sur synthétique)
scripts/               campagne (lib_lab, run_campaign, make_plans,
                       extract_metrics, analyze_*) et statistiques
                       (lib_metrics, lib_screening — copies adaptées de la
                       campagne sensibilite_m4b, provenance en docstring)
manifests/             plans de campagne + manifestes cellule → run_ids lab
results/metrics/       métriques par run ; results/tables/ tables agrégées
report/                spec_m4_2 (mécanique), protocole (pré-enregistré),
                       rapports préliminaire/final, resume.md
prompts/               cahier des charges (figé, intouché)
JOURNAL.md             journal de recherche chronologique
```

## Démarrage rapide

```bash
cd /home/anatole/jupyter/m4_2_credit_soc

# Tests (moteur + parité + estimateurs)
/home/anatole/jupyter/.venv/bin/python3 tests/test_engine.py
/home/anatole/jupyter/.venv/bin/python3 tests/test_parity_m4b.py
/home/anatole/jupyter/.venv/bin/python3 tests/test_stats.py

# Un run direct (hors lab)
/home/anatole/jupyter/.venv/bin/python3 run.py --gamma 0.6 --steps 2000 \
    --output /tmp/run_test

# Campagne (runs stockés dans Simulation Lab)
/home/anatole/jupyter/.venv/bin/python3 scripts/make_plans.py
/home/anatole/jupyter/.venv/bin/python3 scripts/run_campaign.py --plan pilotes
/home/anatole/jupyter/.venv/bin/python3 scripts/extract_metrics.py --plan pilotes
/home/anatole/jupyter/.venv/bin/python3 scripts/analyze_pilotes.py
```

## Simulation Lab

Le modèle est actif dans l'interface (`model_id = m4_2_credit_soc`,
adaptateur `modeles-systeme-physicoeconomique/m4_2_credit_soc/`) avec les
28 figures M4B adaptées (taux marginal r* = A·γ·K^(γ−1) lu depuis la
config du run). Lancement :

```bash
cd /home/anatole/jupyter
/home/anatole/jupyter/.venv/bin/python3 -m simulation_lab.cli gui --open-browser
# ou : ... cli run --model m4_2_credit_soc --seed 1 --params '{"gamma":0.6}'
```

Convention de campagne (décision utilisateur 2026-07-27) : **tous** les
runs de campagne sont des runs Simulation Lab (visibles dans l'interface,
étiquetés « M4.2 — <plan> — <cellule> ») ; les 28 figures ne sont générées
que pour les runs confirmatoires et les cellules centrales (paramètre
booléen `figures` de l'adaptateur, pur post-traitement). La correspondance
cellule → run_ids est dans `manifests/*.manifest.json` et
`manifests/cells_index.json` (avec condensat du moteur).

## Sources amont (lecture seule)

1. `../m4_credit_soc_fable/reports/01_soc_final/` — conclusion M4 (SOC).
2. `../m4b_credit_soc_mini/` — moteur et spécification M4B.
3. `../recherche/sensibilite_m4b/report/rapport_final.pdf` — sensibilité M4B.
4. `../m4_credit_soc_sol/reports/m4_research/` — branche parallèle (contrepoint).
5. `../anciens_modeles/m3_credit_soc/reports/` — résultats M3.

M4 et M4B sont deux implémentations liées d'une même mécanique, pas deux
validations indépendantes. Les moteurs M3, M4, M4B ne sont pas modifiés.

## Statut

Voir `JOURNAL.md` (chronologie) et `report/` (spec, protocole figé,
rapports).
