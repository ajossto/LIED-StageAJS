# Rapport de stage — version adaptée le 25 septembre 2026

[Lire le rapport PDF](latex/note_encadrants.pdf).

Le rapport reprend le raisonnement du stage, les hypothèses, les impasses et les résultats négatifs. Il intègre les corrections des questionnaires et de la **version 0 de l'article**, `../note_resultats/`, ainsi qu'un complément de septembre sur le renouvellement du décile supérieur. L'article reste un document frère distinct et n'a pas été modifié.

- [Registre de transfert](revision_2026-09-25/REGISTRE_TRANSFERT.md) : traitement des 25 décisions COR et des 24 décisions V2, adaptations propres au rapport et limites ouvertes.
- [Contrôles](revision_2026-09-25/CONTROLES.md) : chiffres, sources, compilation et relecture visuelle.
- [Rapport avant adaptation](revision_2026-09-25/reference/latex/note_encadrants.pdf) : sauvegarde complète avec ses sources et figures.
- [État de reprise](REPRISE.md).

## Contenu

Le PDF comprend 57 figures, dont trois schémas TikZ. Les figures historiques restent dans leurs configurations ; les figures révisées de l'article sont copiées localement. La bibliographie précède les annexes, dont la première est le glossaire.

| Fichier | Rôle |
|---|---|
| `latex/note_encadrants.tex` | Récit, modèle et résultats du stage |
| `latex/physique_echelles.tex` | Dimensions et adimensionnement |
| `latex/definitions.tex` | Glossaire dans l'ordre d'introduction des notions |
| `latex/methodes_actualisees.tex` | Stationnarité, ajustements, parité et composition temporelle |
| `latex/annexe_sources_revision.tex` | Tableau de toutes les figures incluses et configurations |
| `latex/data_article/` | Exports transférés de l'article, nouveaux points de renouvellement et manifestes |
| `latex/data_revision/` | Exports historiques conservés |
| `latex/numbers_m4_4.tex` | Macros historiques ; les nombres littéraux du texte demandent aussi une vérification |
| `scripts/renewal_stage.py` | Relecture de deux runs M4.3, sans simulation |
| `scripts/verify_stage.py` | Contrôles ciblés et compilation autonome facultative |

## Compiler et vérifier

Depuis le dossier `latex/`, exécuter trois fois :

```bash
pdflatex -interaction=nonstopmode -halt-on-error note_encadrants.tex
```

Depuis `/home/anatole/jupyter` :

```bash
OPENBLAS_NUM_THREADS=1 .venv/bin/python recherche/note_communication_encadrants/scripts/verify_stage.py --compile
```

Pour recalculer uniquement le complément de renouvellement :

```bash
OPENBLAS_NUM_THREADS=1 .venv/bin/python recherche/note_communication_encadrants/scripts/renewal_stage.py
```

La compilation autonome ne demande que les sources LaTeX et figures locales. Le recalcul demande les instantanés des deux runs identifiés dans le registre. Après régénération volontaire d'un artefact, son empreinte dans `data_article/manifest_rapport.json` doit être réexaminée avant remplacement ; le contrôle signale toute dérive.

**Ne pas relancer les collecteurs historiques ou les générateurs partagés pour mettre à jour cette rédaction** : ils décrivent les anciennes inclusions et peuvent écraser les corrections. Les anciens fichiers `provenance.tex` et les figures retirées restent conservés, mais seul l'assemblage `note_encadrants.tex` définit le texte courant.

## Portée scientifique

La charge versée ne réfute pas la convexité du risque ; une réponse compensée proche de 2 n'est pas l'identité exacte d'une intervention sur les seules naissances. Les familles de queues et la criticité restent à établir. Les courbes de renouvellement distinguent survie et rétention, sans prouver l'oubli de l'état initial. Aucun nouveau run n'a été lancé pour cette adaptation.
