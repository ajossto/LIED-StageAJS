# Arborescence de liaison des modèles (sans modification des sources)

Objectif : trier/organiser le repo en créant des **liens symboliques** vers les versions existantes, sans déplacer ni modifier les dossiers d'origine.

## Structure

- `stable/` : versions techniquement stables à date.
- `candidates/` : versions riches/futures candidates `main` après durcissement.
- `archives/` : archives historiques/faiblement exploitables (dossiers supprimés, ZIPs dans `banque_versions_zip/`).

## Liaisons actives

- `stable/v1_monolithique` → `claude/`
- `stable/v2_modulaire_stable` → `claude3-v2/`

## Archives

- `archives/v3_27mars_archive` → `archives/modeles/claude3-v3-27-mars/`

## Versions supprimées (archivées en ZIP)

- `claude3 - Premier modèle fonctionnel/` → `banque_versions_zip/claude3-premier-modele-fonctionnel.zip`
- `claude_nouveau/` → `banque_versions_zip/claude_nouveau.zip`
- `claude3-v3-25-mars-sans-banque/` → `banque_versions_zip/claude3-v3-25-mars-sans-banque.zip`
- `claude3 (Copie)/` — duplicate supprimé
- `claude_nouveau (Copie)/` — duplicate supprimé
