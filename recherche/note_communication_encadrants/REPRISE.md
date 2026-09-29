# Reprise — 25 septembre 2026

Le [rapport courant](latex/note_encadrants.pdf) intègre la version 0 française de l'article (`../note_resultats/`, confirmation explicite de l'auteur), ses deux carnets de corrections, les réponses aux questionnaires et un complément sur deux runs M4.3 de septembre. Le récit historique demeure propre au rapport ; aucune limite de pages de l'article ne lui est appliquée.

Le [registre de transfert](revision_2026-09-25/REGISTRE_TRANSFERT.md) fait foi pour le statut courant des COR-001–025 et V2-001–024. Les anciens registres de l'article sont conservés tels quels comme historiques. Les questionnaires, les sources de l'article et les moteurs ne sont pas modifiés.

## Pour reprendre

1. Lire le registre et les [contrôles](revision_2026-09-25/CONTROLES.md).
2. Modifier les sources locales incluses par `latex/note_encadrants.tex`.
3. Compiler en trois passes dans `latex/`, ou exécuter `scripts/verify_stage.py --compile` avec le Python du venv racine.
4. Ne pas utiliser les générateurs partagés `revision_documents/` ou le collecteur historique pour synchroniser indistinctement les documents.

Le PDF, ses sources et ses figures d'avant adaptation sont sauvegardés dans `revision_2026-09-25/reference/latex/`. Les identifiants, paramètres et empreintes des instantanés du nouveau complément sont dans `latex/data_article/renouvellement_sources.json`. `sources_protegees.json` enregistre 150 empreintes de documents protégés lors de cette passe.

## Limites à maintenir visibles

- Les parités décrites sont historiques et limitées à leurs scénarios ; aucun test moteur n'a été relancé ici.
- L'élasticité est un contraste fini pour A×1,5 ; la compensation change aussi l'apport par naissance.
- Les données de charge enregistrent le payé, pas le service dû avant paiement ; l'ancienne réfutation de convexité est retirée.
- La suffisance des pertes nécessite un réaudit ; les pourcentages historiques ne sont plus des preuves courantes.
- Les deux courbes M4.3 de renouvellement n'attestent ni l'oubli de l'état initial ni le bon amorçage de toutes les expériences M4.4.
- Le répertoire Simulation Lab évolue indépendamment. Les copies et empreintes du rapport figent ce qui a effectivement été utilisé.
- La compilation autonome n'est pas une reproduction complète des expériences depuis un clonage neuf.

Les suites scientifiques (calibration, taille finie, causalité, robustesse, initialisations et limite continue) sont exposées dans le rapport. Il n'y a pas de question d'approbation en attente pour cette adaptation.
