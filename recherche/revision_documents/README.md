# Compléments vérifiables de rédaction — 14 septembre 2026

Les scripts relisent les campagnes existantes sans lancer de simulation ni modifier les moteurs. Ils produisent onze graphiques et leurs données, puis des copies indépendantes dans chacun des deux dossiers LaTeX.

## Recalculer depuis la racine jupyter

```bash
.venv/bin/python3 recherche/revision_documents/build_visuals.py
.venv/bin/python3 recherche/note_communication_encadrants/scripts/collect_figures.py
.venv/bin/python3 recherche/note_resultats/scripts/collect.py
.venv/bin/python3 recherche/revision_documents/build_sources.py
.venv/bin/python3 recherche/revision_documents/verify_outputs.py
.venv/bin/python3 recherche/revision_documents/verify_autonomy.py
```

Les collecteurs recopient les figures historiques encore incluses ; les nouvelles figures viennent du premier script. L'annexe doit être construite après ces copies. Compiler ensuite chaque document depuis son dossier `latex/`, avec deux passes `pdflatex -interaction=nonstopmode -halt-on-error` et une troisième si LaTeX demande encore une passe.

Les bibliothèques utilisées sont NumPy, SciPy et Matplotlib ; leurs versions sont consignées dans chaque `data_revision/environnement.json`. Poppler et Pillow servent au contrôle visuel. Il s'agit de l'environnement existant, pas d'une installation propre certifiée.

## Mesures et limites

- Quantiles : moyenne des rapports traité/contrôle par graine ; quantiles temporellement moyennés dans le fichier source. Ce n'est ni le rapport des moyennes ni le suivi d'une cohorte.
- Réponse : même estimateur fini `log(moyenne traitée / moyenne contrôle) / log(1.5)` dans les lignées v1 et M4.4, fenêtre `3000 < t <= 4000` ; cinq et douze graines respectivement. Le rapport des moyennes entre graines est exporté séparément.
- IC95 : Student entre graines indépendantes. Ni les pas ni les victimes d'une même simulation ne sont traités comme des réplications indépendantes.
- Cascades : survies par graine ; régression descriptive log-log pour `2 <= S <= 30`, bootstrap de runs entiers pour le ruban. Ce n'est pas un test de Pareto, ni une estimation justifiée de son exposant de densité.
- Stock M4B : cinq graines centrales ; durée des contractions distincte de fréquence des épisodes des deux signes. Le texte historique publie des écarts-types et la fréquence des contractions seules : ne pas les comparer directement aux nouveaux IC95.
- Lorenz : instantanés à `t=4000`, non moyennes temporelles de Gini. Les valeurs nettes non négatives et médianes positives sont vérifiées pour ces seuls instantanés.
- Rho : courbes ajustées par graine ; ruban de confiance de leur moyenne, non intervalle de prédiction ni preuve d'une loi universelle.
- Suffisance : histogramme de fractions par classe, pas une densité ; les deux proportions comparées ont des dénominateurs distincts, indiqués dans le graphique.

`generated/manifest.json` inventorie les sources et empreintes. Les PDF se compilent sans campagnes ; recalculer demande les données non versionnées de M4.4, Live-v1 et Simulation Lab. Les exports de points ne remplacent pas intégralement les microdonnées.

## Contrôles

`verify_outputs.py` vérifie les empreintes, les rapports de quantiles et élasticités avec leurs IC95, les copies locales, les inclusions et sources LaTeX, l'unicité des 372 identifiants, ainsi que neuf points fixes et leur adimensionnement. Cela ne constitue pas une validation de chaque phrase, de tout le moteur ou de l'interprétation empirique.

`verify_autonomy.py` compile chaque document séparément dans un dossier temporaire avec ses seuls fichiers LaTeX et figures. `render_review.py` crée les planches de contrôle visuel sous `generated/relecture/`. Bilan et limites détaillés dans le journal du rapport.

Les questionnaires répondus sont conservés dans le dossier du rapport ; aucun n'est une dépendance des documents finaux.
