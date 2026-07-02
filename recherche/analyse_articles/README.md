# Analyse d'articles scientifiques (recodage)

Recodage et analyse statistique de modèles issus d'articles d'économie
statistique / econophysique, en lien avec les questions de distribution de
taille et de richesse traitées dans ce dépôt.

- `bouchaud_mezard_wealth_condensation/` — Bouchaud & Mézard, *Wealth
  condensation in a simple model of economy* (arXiv:cond-mat/0002374, 2000).
- `wright_implicit_microfoundations/` — recodage d'un modèle de Ian Wright
  sur les microfondations implicites d'une économie de classes.
- `wright_social_architecture/` — recodage d'un second modèle de Ian Wright
  sur l'architecture sociale d'une économie de classes.

Chaque sous-dossier contient :

- `recoding.py`, `statistical_analysis.py` — le recodage du modèle de
  l'article et son analyse statistique ;
- `figures/` — figures reproduites ou produites par l'analyse ;
- `results/` — résumés numériques (JSON) ;
- `report/report.tex` + `report.pdf` — note de synthèse.

**Le texte intégral des articles (`article.txt` dans la copie de travail
locale) n'est volontairement pas inclus ici** : ce dépôt GitHub est public,
et republier le texte verbatim d'articles sous copyright pose problème même
quand l'article source est cité et discuté. Seuls le recodage et l'analyse
sont versionnés.
