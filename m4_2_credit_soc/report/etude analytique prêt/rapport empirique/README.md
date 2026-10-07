# Rapport empirique — prêt arithmétique

La campagne étudie uniquement le principal
`q = (k1 - k2) / 2`, avec `k1 = 100` et six valeurs de `k2`.

Reproduction sur les huit cœurs disponibles :

```bash
/home/anatole/jupyter/.venv/bin/python campagne_empirique.py \
  --workers 8 --chunks-per-condition 16
latexmk -pdf -interaction=nonstopmode -halt-on-error rapport_empirique.tex
```

Les paramètres, graines, tailles d'échantillon et contrôles de couplage
sont enregistrés dans `resultats/manifest.json`. Les fichiers NPZ
contiennent les échantillons bruts à `r=0.1`; les CSV contiennent tous les
résumés de la grille.
