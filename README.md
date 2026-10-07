# Modèles physico-économiques — point d'entrée

Ce dépôt rassemble plusieurs générations d'un programme de recherche sur les
systèmes économiques multi-agents, le crédit et les faillites en cascade.

## Où commencer

- **Dernière lignée auditée (index révisé le 14 septembre 2026)** :
  [`m4_4_rebond_credit_soc/`](m4_4_rebond_credit_soc/) — moteur M4.4,
  campagnes, analyses, tests et rapport. État scientifique documenté en août 2026.
- **Proto-rapport de stage** :
  [`recherche/note_communication_encadrants/`](recherche/note_communication_encadrants/)
  — raisonnement, hypothèses, impasses et résultats négatifs.
- **Proto-article scientifique, document frère** :
  [`recherche/note_resultats/`](recherche/note_resultats/) — conclusions du travail.
- **Référence historique de sensibilité M4B** :
  [`recherche/sensibilite_m4b/`](recherche/sensibilite_m4b/).
- **Interface de simulation** : [`simulation_lab/`](simulation_lab/) et
  [`docs/README_simulation_lab.md`](docs/README_simulation_lab.md).
- **Consignes de travail** : [`CODEX.md`](CODEX.md) et [`CLAUDE.md`](CLAUDE.md).

## Lignée scientifique récente

| Dossier | Rôle | Statut de navigation |
| --- | --- | --- |
| `anciens_modeles/m2_codex/`, `anciens_modeles/m2_fable/` | Deux réplications critiques de M2 | Travaux antérieurs |
| `anciens_modeles/m3_credit_soc/` | Crédit productif, liquidité et fragilité nominale | Programme clos ; référence |
| `m4_credit_soc/` | Brief et matériaux de lancement de M4 | Documentation source |
| `m4_credit_soc_fable/` | Branche M4 avec rapport scientifique final | Référence en lecture |
| `m4_credit_soc_sol/` | Branche expérimentale M4 parallèle | Référence en lecture |
| `m4b_credit_soc_mini/` | Réduction minimale reproduisant la mécanique retenue de M4 | Référence historique |
| `recherche/sensibilite_m4b/` | Campagne, données, figures et rapport de sensibilité | Étude achevée à consulter |
| `m4_2_credit_soc/` | Généralisation de la production et étude d'échelle | Implémentée |
| `m4_2b_credit_soc/` | Prolongement M4.2B | Implémenté |
| `m4_3_credit_soc/` | Institutions de crédit | Implémentée |
| `m4_3live_credit_soc/` | Technologies individuelles et interventions Live | Implémentée |
| `m4_3live_v2_credit_soc/` | Sens libre du prêt et campagnes Live-v2 | Implémentée |
| `m4_4_rebond_credit_soc/` | Rebond, distributions, partage et cascades | Dernière lignée auditée |

M4 et M4B ne constituent pas deux preuves indépendantes : M4B est une
réduction fidèle de la mécanique M4 retenue. Cette distinction devra rester
explicite lors de l'interprétation des parités entre lignées.

## Autres zones du dépôt

| Zone | Contenu |
| --- | --- |
| `modeles-systeme-physicoeconomique/` | Adaptateurs découverts par Simulation Lab ; consulter `list-models` pour les capacités présentes |
| `anciens_modeles/` | Tous les moteurs et espaces de travail jusqu'à M3 inclus |
| `recherche/` | Analyses, campagnes et matériaux scientifiques hors moteurs |
| `docs/` | Documentation transversale et notes historiques |
| `presentation/`, `presentation_2_le_retour/` | Sources et artefacts des présentations |
| `archives/`, `banque_versions_zip/` | Versions historiques et sauvegardes |
| `arborescence_modeles/` | Liens symboliques historiques ; ne pas traiter comme des copies |
| `simulation_lab_data/` | Données volumineuses produites par Simulation Lab |
| `hooks/` | Hooks Git du dépôt |

Les lignées antérieures à la nomenclature M2–M4 sont elles aussi regroupées
dans [`anciens_modeles/`](anciens_modeles/). Leurs noms internes restent
inchangés afin de préserver les imports et la reproductibilité.

## Règle de rangement

- Un nouveau travail scientifique possède un dossier autonome avec un `README.md`.
- Les prompts, scripts, figures, rapports et données d'une campagne restent dans
  ce dossier autonome.
- Les sorties volumineuses ne sont pas déplacées sans audit de leurs chemins.
- Les archives ne sont pas modifiées pour construire une nouvelle version.
