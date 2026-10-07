# Modèles

- **Moteurs M4** (`m4_*`) : une lignée par dossier, chacun autonome (README, code, tests, rapports).
  Le plus récent est `m4_4_rebond_credit_soc/`. Voir le [README racine](../README.md) pour le rôle de chacun.
- **`anciens_modeles/`** : moteurs et espaces de travail jusqu'à M3 inclus.
- **`adaptateurs/`** : un `model.py` par modèle branché dans Simulation Lab
  (`python -m simulation_lab.cli list-models`). Les adaptateurs retrouvent les moteurs
  frères dans ce dossier (`PROJECT_ROOT = modeles/`).

Les identifiants de modèle (par ex. `m4_4_rebond_credit_soc`) sont des noms logiques
indépendants de l'emplacement des dossiers.
