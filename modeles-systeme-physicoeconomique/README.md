# Modèles compatibles

Chaque sous-dossier de `modeles-systeme-physicoeconomique/` doit contenir un `model.py`
exposant soit :

- `MODEL`, instance de `BaseSimulationModel`
- ou `get_model()`, retournant cette instance

Les modèles prioritaires actuellement branchés sont :

- `modele_sans_banque_wip`
- `claude3_v2`

Les exemples fournis servent de référence minimale, mais l’interface et le CLI sont
désormais préparés d’abord pour ces deux modèles.
