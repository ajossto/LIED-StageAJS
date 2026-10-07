# Explorations pour la conception M2 (Boltzmann-Pareto auto-critique)

Support numérique du document `../conception_modele_M2.md` (voir son annexe A pour
l'interprétation). Prototype jetable, indépendant de `anciens_modeles/modele-27-04-WIP/src/`.

## Fichiers

- `proto_m1.py` — prototype du modèle réduit à capital scalaire + carnet de prêts.
  Flags principaux : `--no-deprec-loans` (asymétrie dette nominale / capital
  déprécié), `--cost-delta` (condition marginale au coût r+δ), `--gbm-sigma`
  (choc multiplicatif commun en loi), `--d0` (dette d'amorçage = plancher de
  valeur nette), `--n0` (population initiale ; 0 = pas de cohorte fondatrice),
  `--pool_every` (analyse de queue par fenêtres poolées).
- `probe_body_age.py` — composition en âge des déciles de capital (corps =
  cohorte en transit ?).
- `probe_renewal.py` — renouvellement du top décile (classe figée ?). Flags :
  `--service-cap`, `--cost-delta`, `--w0-endo`.

## Runs (logs)

| Log | Variante | Verdict (annexe A du doc) |
|---|---|---|
| — (E0, non conservé) | dettes dépréciées | 0 faillite, pop non bornée, corps piqué |
| `run_s1.log`, `run_s2.log` | E1 naïf, λ=10, seeds 1-2 | régime SOC borné, queue power-law |
| `run_lam30.log`, `run_lam30_pool.log` | E1 naïf, λ=30 (+pools) | idem, α(revenu)≈2,8-2,9 ; x_min instable |
| `run_rounds05.log` | E1 + échange intensifié | idem, pop plus petite |
| `run_n0zero.log` | E1 + n0=0 | s'amorce depuis vide ; classe âgée persiste |
| `renewal_cap.log` | E2 + plafond de service | identique (le plafond ne mord pas) |
| `run_m2_s015.log`, `run_m2_s025.log` | E7a-b (tués en cours : fenêtre de naissance mal calée) | σ=0,15 : 0 mort ; ε₀=10 : mortalité 14× trop faible |
| `run_m2_final.log` | **E7c pile complète** : σ=0,25, w₀=30, d₀=28, cost-delta, T=1500, pools | pop bornée ~1760 ; α_CSN(w)=2,80/2,86/2,88 par fenêtres ; corr(âge,log w)≈0,12 ; queue à âge contrôlé OK ; corps pas encore exponentiel |

Reproduction type :
```bash
/home/anatole/jupyter/.venv/bin/python3 proto_m1.py --seed 0 --T 2000 --lam 10 \
  --n0 0 --no-deprec-loans --cost-delta --gbm-sigma 0.15 --w0 20 --d0 10 --pool_every 50
```
