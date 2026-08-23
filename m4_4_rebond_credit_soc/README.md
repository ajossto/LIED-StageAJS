# M4.4Rebond — où vit l'effet rebond dans la distribution

Quatrième lignée de la série M4.3Live. **Fork indépendant** de
`m4_3live_v2_credit_soc/` : aucun module de ce dossier n'importe le moteur
d'une autre lignée (sauf en LECTURE, dans les tests d'équivalence). Le moteur
v2 est gelé — 153 runs enregistrés et deux rapports publiés en dépendent.

La spécification complète est `PLAN_M4_4_REBOND.md` (également en PDF dans
`prompts/`). Le journal de bord est `JOURNAL.md`.

## La question

L'effet rebond est un énoncé sur des agrégats : quand `A` monte de 50 %, la
production totale monte de 0,7473 % par pour-cent d'`A` (v2, 12 graines
appariées), parce que la production par entité monte de ×1,80 pendant que la
population se contracte de 25 %. **Ce programme demande où ce surcroît va
dans la distribution** — corps ou queue, producteurs ou rentiers — et si
l'exposant de queue α et le rapport de branchement b se pilotent par
intervention en direct.

## Ce que M4.4 ajoute au moteur

Rien qui change une trajectoire. Quatre additions d'INSTRUMENTATION, toutes
éteintes par défaut, toutes hors circuit :

| addition | drapeau | pourquoi |
|---|---|---|
| arbre causal des cascades | `record_loss_edges` | `avalanche_members.generation` est le numéro de passe du point fixe, pas un compte de descendance : sans les arêtes (source, victime, principal), le second estimateur du rapport de branchement n'existe pas |
| panneaux par entité | `panel_every` | `entity_snapshot()` existait mais n'était appelé que par `Simulation.run()`, que ni le pilote ni la campagne n'empruntent |
| flux des entités mortes | (toujours) | `prod`, `int_in`, `int_out` dans `dead_info` : sans eux aucun panneau ne peut se refermer sur `prod_tot` ni `interest_paid` |
| persistance | (toujours) | v2 mesurait décès, avalanches et contrats en mémoire et ne les écrivait jamais : d'où l'absence totale de données d'avalanche dans ses 153 runs |

Plus, côté exécution : un **checkpoint de fin de run**
(`save_snapshot(..., records=False)`), dette d'ingénierie inscrite par M4.2B
« pour tous les modèles postérieurs » et jamais payée depuis.

## Arborescence

```
m4_4_rebond_credit_soc/
├── m4_4/                moteur (fork de m4_3live_v2)
│   ├── model.py         Config / Population / LoanBook / Simulation, interventions
│   ├── kernel.py        institution de principal : production jointe maximale
│   ├── live.py          session en direct, journal, snapshots, panneaux, persistance
│   ├── tension.py       K_eq, K_aut, tension — colonnes natives
│   └── cascades.py      les DEUX estimateurs du rapport de branchement
├── driver/headless.py   pilote sans tête : burn / arm / replay / resume
├── web/                 IHM `/live3`, branchée dans simulation_lab (additive)
├── tests/               16 fichiers d'assertions Python simples — pas de pytest
├── scripts/             run_tests.py (la suite entière, codes de sortie compris),
│                        campaign.py, branching.py, cost_panels.py, cost_profile.py,
│                        tension_figures.py, import_to_simulation_lab.py
├── results/             non versionné (voir .gitignore)
└── report/              rapports LaTeX (lot G)
```

## Utilisation

```bash
cd /home/anatole/jupyter

# IHM : les TROIS lignées coexistent sur le même serveur
/home/anatole/jupyter/.venv/bin/python3 -m simulation_lab.cli gui --open-browser
#   http://127.0.0.1:8777/live    M4.3Live v1
#   http://127.0.0.1:8777/live2   M4.3Live-v2
#   http://127.0.0.1:8777/live3   M4.4Rebond

# Tests (assertions Python simples, pas de pytest)
/home/anatole/jupyter/.venv/bin/python3 m4_4_rebond_credit_soc/scripts/run_tests.py
# … et la parité complète, 8000 pas, ~25 min :
/home/anatole/jupyter/.venv/bin/python3 m4_4_rebond_credit_soc/scripts/run_tests.py --full

# Mesurer le prix de l'instrumentation avant de fixer k (porte du lot A)
/home/anatole/jupyter/.venv/bin/python3 m4_4_rebond_credit_soc/scripts/cost_panels.py
```

## Statut

| lot | contenu | état |
|---|---|---|
| **A** | fork, persistance, panneaux, checkpoint, arbre causal, deux estimateurs de b | **terminé** — 16/16 tests verts, les deux portes franchies |
| B | décomposition distributionnelle du rebond | à faire |
| C0 / C | pilote de couverture, puis classes de lois | à faire |
| D | avalanches et branchement | à faire |
| E | tentative de contrôle de α et de b | à faire |
| F | pourquoi b dépasse la valeur σ = 0 de M4B | à faire |
| G | rapports, journal, traçabilité | à faire |

**Portes du lot A, mesurées** (détail et chiffres dans `JOURNAL.md`) :

- parité bit à bit sur **8000 pas × 26 colonnes**, écart maximal **nul**, et
  le même nombre d'appels au noyau que la parité finale de v2 ;
- fermeture des panneaux : effectif, `K_tot` et `nw_tot` **bit à bit** ; les
  flux à 1,8·10⁻¹⁴ une fois les entités mortes du pas ajoutées ;
- les deux estimateurs de b réconciliés sur une cellule de campagne :
  b₁ = 0,7861 (le 0,7863 ± 0,0006 de v2), b₂ = 0,8485, écart 0,0624.

Coût mesuré de l'instrumentation : +3,7 % de temps pour les événements,
+1,8 % pour la sonde de Gini, 3,98 ms et 43,9 Kio par panneau ; campagne de
108 runs à **3,35 Gio** avec k = 10.
