# Note de communication aux encadrants

Proto-rapport de stage autonome, incorporant les campagnes historiques et les
vérifications du 14 septembre 2026 après réponses d'Anatole à l'audit et au questionnaire.
Structuré en parties **retravaillables indépendamment**.

Il retrace le raisonnement, les hypothèses et les résultats négatifs.
Le document frère `../note_resultats/` est un proto-article scientifique
consacré aux conclusions : leurs fonctions sont distinctes.

## La question dorsale

> Si l'on modélise la société comme un système d'agents collaboratifs, quels
> phénomènes réels retrouve-t-on dans les comportements du système — et qui
> viennent donc soutenir l'interprétabilité du modèle ? Et parvient-on à
> reproduire un phénomène qui puisse s'identifier à l'effet rebond ?

## Contenu

| fichier | rôle |
|---|---|
| `latex/note_encadrants.tex` | le rapport, avec 51 figures incluses |
| `latex/note_encadrants.pdf` | le document compilé |
| `latex/numbers_m4_4.tex` | **copie** des 268 macros de M4.4, avec en-tête de provenance |
| `latex/provenance.tex` | table de provenance des figures — **engendrée** |
| `latex/tracabilite.tex` | annexe de traçabilité par `run_id` — **engendrée** |
| `latex/definitions.tex` | notations et termes internes, tous définis |
| `latex/bibliographie.tex` | références, avec ce que chacune établit *et n'établit pas* |
| `latex/figures/` | copies historiques et nouveaux graphiques calculés depuis les sources |
| `latex/typo_francaise.tex` | règles typographiques françaises (repris de `note_de_travail/`) |
| `scripts/collect_figures.py` | rassemble figures et macros, écrit `provenance.tex` et `tracabilite.tex`, vérifie qu'aucune inclusion n'est orpheline |
| `QUESTIONS.md` | ancien document de travail ; l'état de reprise fait foi |

## Reconstruire

```bash
cd /home/anatole/jupyter/recherche/note_communication_encadrants
cd latex && pdflatex note_encadrants && pdflatex note_encadrants
```

Deux passes suffisent normalement ; en ajouter une si LaTeX le demande. Pour
recalculer et synchroniser figures, nombres et annexes, suivre
`../revision_documents/README.md`. Cette opération exige les campagnes et les
données Simulation Lab ; une simple compilation utilise les copies locales.

## Trois règles tenues

**Graphiques traçables.** Les images historiques viennent des campagnes et de
Simulation Lab. Onze compléments de rédaction sont calculés par
`../revision_documents/build_visuals.py`, avec points sources et incertitudes.
`collect_figures.py` recopie les images historiques encore incluses ;
`build_sources.py` indexe l'ensemble des figures et leurs protocoles. Elles sont copiées et non liées parce
que `simulation_lab_data/` n'est pas versionné : une note qui cesserait de
compiler après le nettoyage d'un run ne serait pas autonome.

**Traçabilité par identifiant.** `tracabilite.tex` rattache chaque figure à
son run ou à sa campagne, avec paramètres et chemin. L'annexe complémentaire
`annexe_sources_revision.tex` et `data_revision/` donnent les 372 identifiants
M4.4, les configurations et les empreintes des sources. Une figure agrégeant une
campagne entière ne peut pas porter un identifiant unique : elle renvoie à
l'annexe engendrée de sa campagne, qui liste un `run_id` par ligne.

**Macros M4.4 synchronisées avec leur source.** `numbers_m4_4.tex` est la copie
conforme de `m4_4_rebond_credit_soc/report/numbers.tex`, elle-même engendrée
depuis `results/analysis/` et confrontée aux figures par
`tests/test_figures.py`. Les valeurs héritées des lignées antérieures, elles,
sont écrites dans le texte avec leur source citée. Des valeurs M4.4 restent
également littérales : la synchronisation des macros ne les contrôle pas.

## Ce que la note ajoute au dossier de recherche

`recherche/memo_stage/memo_recherche_complet.md` (v1.7, 24 août) s'arrête à
M4.3Live-v1. **Cette note est le premier document qui intègre M4.3Live-v2 et
M4.4Rebond au récit du stage.** Elle applique aussi les corrections de
`note_consolidation_questionnaire_2026-08-24.md`, non encore reportées dans le
mémo maître.

## Vérification faite pour la note

Les **sept tests de parité** reliant M4 → M4B → M4.2 → M4.2B → M4.3 →
M4.3Live → M4.4 ont été rejoués le 25 août 2026. Tous verts. C'est ce qui
établit une non-régression dans les restrictions et scénarios testés.
Cela ne valide pas toutes les configurations des moteurs généralisés,
ni leur interprétation empirique. Ces tests de parité n'ont pas été rejoués
le 14 septembre ; les quatre contrôles de figures M4.4 et les nouveaux contrôles
d'exports l'ont été. Le journal détaille ce qui a effectivement été vérifié.
