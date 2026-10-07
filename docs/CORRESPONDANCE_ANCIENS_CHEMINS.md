# Correspondance des anciens chemins (rangement d'octobre 2026)

Les documents historiques (journaux, mémos, notes de stage, présentations,
snapshots `revision_*/reference/`) citent les chemins d'avant le rangement. Ils
n'ont volontairement pas été réécrits : plusieurs sont scellés par empreinte
SHA-256. Cette table donne l'équivalent actuel de chaque ancien chemin.

| Ancien chemin (racine du dépôt) | Chemin actuel |
| --- | --- |
| `m4_credit_soc/`, `m4_credit_soc_fable/`, `m4_credit_soc_sol/` | `modeles/<même nom>/` |
| `m4b_credit_soc_mini/` | `modeles/m4b_credit_soc_mini/` |
| `m4_2_credit_soc/`, `m4_2b_credit_soc/` | `modeles/<même nom>/` |
| `m4_3_credit_soc/`, `m4_3live_credit_soc/`, `m4_3live_v2_credit_soc/` | `modeles/<même nom>/` |
| `m4_4_rebond_credit_soc/` | `modeles/m4_4_rebond_credit_soc/` |
| `anciens_modeles/` | `modeles/anciens_modeles/` |
| `modeles-systeme-physicoeconomique/` | `modeles/adaptateurs/` |
| `articles de référence/` | `recherche/bibliographie/articles_de_reference/` |
| `presentation/`, `presentation_2_le_retour/` | `presentations/` |
| `banque_versions_zip/` | `archives/banque_versions_zip/` |
| `codex_analysis_workspace/` | `archives/codex_analysis_workspace/` |
| `arborescence_modeles/` | `archives/arborescence_modeles/` |

## Liens de compatibilité

`m4_4_rebond_credit_soc` et `m4_3live_credit_soc` existent toujours à la racine
sous forme de liens symboliques vers `modeles/…`. Les manifestes d'empreintes des
articles (`recherche/note_resultats*/`, `recherche/note_communication_encadrants/`)
désignent les résultats de ces deux moteurs par leur ancien chemin ; les liens
évitent de réécrire ces manifestes (et donc de recalculer leurs empreintes).

## Ce qui n'a pas changé

- Les identifiants logiques des modèles (`m4_4_rebond_credit_soc`, etc.) utilisés
  par Simulation Lab et stockés dans `simulation_lab_data/` : ce sont des noms, pas des chemins.
- `simulation_lab/`, `simulation_lab_data/`, `recherche/*` (hors `bibliographie/`), `docs/`, `hooks/`, `outils/`.

## Retrouver l'état d'avant

La branche `backup/avant-rangement` contient le dépôt tel qu'il était avant le rangement.
