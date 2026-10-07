# Modèles compatibles

Chaque sous-dossier de `modeles/adaptateurs/` doit contenir un `model.py`
exposant soit :

- `MODEL`, instance de `BaseSimulationModel`
- ou `get_model()`, retournant cette instance

Le seul modèle actif et lançable est désormais :

- `m4b_credit_soc_mini`

Les autres adaptateurs sont conservés pour nommer et consulter les simulations
historiques. Simulation Lab les expose comme modèles archivés et refuse tout nouveau
lancement avec ceux-ci.
