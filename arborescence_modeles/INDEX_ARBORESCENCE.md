# Arborescence de liaison des modèles (sans modification des sources)

Objectif : trier/organiser le repo en créant des **liens symboliques** vers les versions existantes, sans déplacer ni modifier les dossiers d'origine.

## Structure

- `stable/` : versions techniquement stables à date.
- `candidates/` : versions riches/futures candidates `main` après durcissement.
- `regressions/` : versions avec régressions de tests observées.
- `duplicates/` : copies à dédupliquer ultérieurement.
- `archives/` : archives historiques/faiblement exploitables.

## Liaisons créées

- `stable/v1_monolithique` → `claude/`
- `stable/v2_modulaire_stable` → `claude3-v2/`
- `candidates/v3_27mars_reference` → `claude3-v3-27-mars/`
- `regressions/v3_premier_modele` → `claude3 - Premier modèle fonctionnel/`
- `regressions/v3_nouveau` → `claude_nouveau/`
- `duplicates/copie_claude3` → `claude3 (Copie)/`
- `duplicates/copie_nouveau` → `claude_nouveau (Copie)/`
- `archives/v3_25mars_sans_banque` → `claude3-v3-25-mars-sans-banque/`

## Bénéfice immédiat

- Pas de modification des modèles.
- Navigation unifiée pour travailler sur la consolidation.
- Préparation d'un nettoyage git progressif (suppression des copies et archivage final) sans risque de casse immédiate.
