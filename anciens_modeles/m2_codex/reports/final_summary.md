# Synthèse finale — réplication critique de M2

## Verdict exécutif

M2 a été implémenté et testé, mais la thèse « distribution
Boltzmann–Pareto émergente par auto-organisation critique » n'est pas confirmée.
Le modèle produit des classes fortement renouvelées et un régime démographique
de taille finie sur la baseline. Il ne produit pas de corps exponentiel. Sa queue
est compatible avec une pente de type Pareto sur une plage limitée, mais une
log-normale tronquée a une meilleure vraisemblance dans toutes les comparaisons.
La même queue apparente subsiste sans crédit, ce qui réfute le crédit comme cause
nécessaire et affaiblit fortement l'interprétation SOC.

## Réponses aux questions finales

### Le modèle M2 a-t-il été implémenté fidèlement ?

Oui, pour les règles explicites : capital scalaire, contrats nominaux
perpétuels, `d0`, choc log-normal sans drift moyen, extraction, intérêts,
dépréciation réelle, marché local, faillites en cascade et naissances Poisson.
L'implémentation passe 27 tests.

Les ambiguïtés ont été tranchées et documentées : service simultané prorata des
intérêts, exclusion du marché des entités en défaut, liquidation séquentielle par
identifiant et destruction du résiduel sans créancier. Les fractions de contrats
sont fusionnées par paire avec un taux moyen pondéré. Cette compression est
comptablement exacte pour des prêts nominaux perpétuels, mais perd la généalogie
détaillée des fragments.

### Quelles hypothèses sont confirmées ?

- Les classes ne sont pas des cohortes fondatrices : corrélation
  âge–`log(NW)` de 0,064 à 0,155, mortalité du top décile de 86 à 91 % entre
  `t=1000` et `t=2000`, renouvellement presque total.
- Le couple choc multiplicatif–`d0` crée une mortalité endogène et peut ralentir
  fortement la croissance démographique sans capacité de charge.
- La baseline est reproductible : populations finales 1672, 1680 et 1677 pour
  trois seeds.
- L'utilisation d'un `xmin` commun réduit l'instabilité apparente des exposants.

### Quelles hypothèses sont infirmées ?

- Le corps exponentiel : Fisk gagne pour les trois baselines et dans 35 des 36
  cas de grille; l'autre cas est log-normal. L'exponentielle perd de 61 à 80
  points d'AIC sur la baseline.
- Un même exposant pour revenu et valeur nette : revenu 4,20–4,86 contre `NW`
  2,54–3,05.
- La nécessité du crédit pour la queue et le renouvellement : l'ablation sans
  crédit à 2000 pas conserve ces deux signatures.
- La robustesse sans réglage fin : mortalité et population dépendent fortement
  de `sigma` et de `epsilon0/w0`.
- Le soutien empirique à une boucle SOC du crédit : aucune transition claire en
  `k`, pas de relation positive concentration–faillites, signatures maintenues
  sans crédit.

### Le corps exponentiel apparaît-il ?

Non. Le ratio médiane/moyenne de `NW` est proche de `ln(2)`, mais ce résumé est
trompeur : AIC/BIC et QQ-plots rejettent l'exponentielle. De plus, le drift moyen
mesuré sur les survivants du corps est positif, donc la relation `T=B0/A0` ne
produit pas de température positive avec la convention proposée.

### La queue de Pareto est-elle stable ?

Pas au sens requis. Les seeds 0 et 1 ont des exposants de `NW` assez stables,
autour de 2,8–2,9. Le seed 2 passe de 2,54 à 3,05 avec `xmin` de 324 à 857. Surtout,
une log-normale correctement normalisée sur `x >= xmin` a une vraisemblance
supérieure dans toutes les fenêtres et variables. La Pareto n'est donc pas
identifiée face à la log-normale.

### Les classes sont-elles dynamiques ou démographiques ?

Dynamiques au sens de mobilité de rang et de mortalité. Ce résultat est le plus
solide de l'étude. Il ne prouve toutefois pas l'existence de classes sociales au
sens économique : le modèle représente surtout des états de bilan sous sélection
démographique.

### La population est-elle bornée endogènement ?

La baseline produit un quasi-plateau sans capacité artificielle, mais le bornage
asymptotique n'est pas démontré : les pentes sur `[1000,2000]` restent positives.
Le résultat n'est pas robuste sur la grille. À `sigma=0.15`, certaines marges de
naissance donnent zéro à cinq faillites et une croissance presque linéaire.

### Le modèle est-il robuste sans réglage fin ?

Non. La forme du corps échoue partout, et l'existence du régime démographique
dépend fortement de `sigma` et `epsilon0/w0`. `k` a moins d'effet, mais aucune
phase SOC robuste n'est identifiée.

### Quelles expériences faut-il lancer ensuite ?

1. Prolonger baseline et ablation sans crédit à 4000–10000 pas.
2. Répéter sur trois seeds les frontières de grille, surtout `sigma=0.15` et
   `sigma=0.35`.
3. Tester l'invariance temporelle avec `delta/2` et un horizon doublé, puis
   l'extensivité en `lambda`.
4. Construire des avalanches causales séparant forçage et relaxation; les lots
   actuels par pas mélangent plusieurs déclencheurs.
5. Inclure les morts dans l'estimation des incréments `A0`, `B0`.
6. Comparer Pareto, log-normale et processus de Kesten en prédiction hors
   échantillon.
7. Tester liquidation simultanée, moyenne de taux et règle de transfert comme
   variantes nommées d'un modèle ultérieur, sans recalibrer M2 après coup.

## Livrables

- Code : `src/m2/`
- Tests : `tests/`
- Expériences : `experiments/m2/`
- Runs et artefacts : `outputs/`
- Inventaire : `reports/00_inventory.md`
- Lecture critique : `reports/01_critical_reading/main.pdf`
- Spécification : `reports/02_technical_spec/main.pdf`
- Implémentation : `reports/03_implementation_report/main.pdf`
- Validation : `reports/04_validation_report/main.pdf`
- Résultats négatifs : `reports/05_negative_results/main.pdf`
- Journal : `reports/research_log.md`

Commande de test :

```bash
cd /home/anatole/jupyter/anciens_modeles/m2_codex
PYTHONPATH=src /home/anatole/jupyter/.venv/bin/python3 -m unittest discover -s tests -v
```
