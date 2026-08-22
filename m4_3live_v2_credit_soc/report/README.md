# M4.3Live-v2 — le sens du prêt libéré

Fork de `m4_3live_credit_soc/` (**gelé**, jamais importé). Le changement
central : dans une paire, ce n'est plus la plus riche qui prête, c'est
l'optimum de production jointe qui décide, et son signe est libre.

## Où sont les choses

```
m4_3live_v2/          moteur forké (model.py, kernel.py, live.py, tension.py)
driver/headless.py    pilote sans tête : burn / arm / replay / resume
web/                  IHM « direct », servie sur /live2 par simulation_lab
tests/                12 fichiers de tests, assertions Python simples
scripts/              campagnes, analyses, figures, traçabilité
results/              runs, snapshots, analyses (non versionné)
report/               les deux rapports LaTeX et leurs figures
ROADMAP.md            feuille de route issue des 28 notes de l'utilisateur
JOURNAL.md            journal de travail, tenu au fil de l'eau
```

## Statut

| chantier | état |
|---|---|
| Fork, purge des clefs mortes, suppression de `equalization` | **terminé** — parité bit à bit, coût redevenu linéaire en horizon |
| Sens du prêt libre | **terminé** — parité reconduite, v1 rejouable dans v2 |
| Instrumentation native (tension, amplitude, prédiction γ) | **terminé** |
| Ordre des phases configurable | **terminé** — prédiction a priori réfutée, canal réel identifié |
| Campagne A/B du sens du prêt, 12 graines | **terminée** — 96 runs |
| Rotation du crédit | **terminé** — identité établie, fermeture en échec documenté |
| Rapports | **terminés** — `report/*.pdf` |

## Les trois résultats

1. **La règle « la plus riche prête » interdisait une part substantielle des
   échanges optimaux** : 23,7 % des rondes de marché dans la fenêtre de
   transition, portant 18,4 % du volume.
2. **Le régime nouveau existe et il est durable** : des entités de faible
   rendement marginal cèdent leur capital et vivent de l'intérêt (93 % de leur
   revenu). Elles survivent indéfiniment sous le sens libre et **s'éteignent**
   sous l'ancienne règle. Mais l'effet agrégé est **négatif** : plus de
   contrats, donc plus de service perpétuel, donc plus de faillites, et une
   faillite détruit le capital.
3. **La rotation du crédit est l'inégalité des capitaux** :
   `rotation = ρ · Ḡ`, où `Ḡ` est le coefficient de Gini moyenné sur la phase
   de marché. Exposant mesuré 0,986, R² = 0,9998, écart médian 0,5 %. La
   *fermeture* — prédire `Ḡ` depuis les paramètres — n'est pas établie, et
   l'échec est documenté.

## Démarrer

```bash
PY=/home/anatole/jupyter/.venv/bin/python3

# IHM en direct (v2 sur /live2 ; v1 reste sur /live)
cd /home/anatole/jupyter && $PY -m simulation_lab.cli gui --open-browser

# un run sans tête
cd m4_3live_v2_credit_soc
$PY driver/headless.py burn --seed 0 --t0 2000 --out results/essai

# la suite de tests
for t in tests/test_*.py; do $PY $t; done
```

## Ce qui est hors périmètre, et à la demande de qui

- **Aucun traitement du cas partiel.** La portée `fraction` reste dans le
  moteur et fonctionne, mais aucune campagne de v2 ne l'emploie.
- **Une seule borne de transfert** : `equalization` est supprimé — la branche
  n'a jamais mordu sur aucun run de v1.

## Règles permanentes de ce dossier

- `m4_3live_credit_soc/m4_3live/` est **en lecture seule, définitivement**.
- La parité bit à bit avec M4.3 en régime homogène est repassée après chaque
  changement du moteur.
- `loan_direction="richest_lends"` doit reproduire le moteur v1 **bit à bit**,
  y compris en régime hétérogène : c'est ce qui rend les campagnes appariées.
- Tout nombre cité dans un rapport est une macro engendrée par
  `scripts/make_numbers.py` depuis un fichier de `results/analysis/`.
