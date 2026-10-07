# Étude analytique du prêt unique

Le rapport principal est `etude_analytique_pret.tex`. Il étudie exactement
les chocs lognormaux de M4.2 et ne repose sur aucune simulation.

`verification_empirique.py` est un contrôle Monte-Carlo séparé. Il dépend
uniquement de NumPy. Dans l'environnement actuel, on peut l'appeler ainsi :

```bash
/home/anatole/jupyter/.venv/bin/python verification_empirique.py \
  --k1 100 --k2 25 --gamma 0.5 --delta 0.05 --sigma 0.25 \
  --rate 0.1 --scheme arithmetic --paths 100000 --max-steps 2000
```

Le fichier NPZ contient les temps de mort de l'emprunteuse, les capitaux
des deux entités au premier décès, la cause du défaut et les capitaux à
l'horizon. Les trajectoires non absorbées à l'horizon portent le temps
`inf`; le temps de mort de la prêteuse vaut toujours `inf`, conformément
au théorème du rapport.
