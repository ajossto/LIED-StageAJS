# Note de résultats — proto-article autonome

Révision des 15–17 septembre 2026 à partir du carnet rempli par Anatole. Le texte suit désormais la question physique du stage : modèle, émergence, pilotage, réponse collective à la technologie, puis partage du surplus. La criticité reste une hypothèse, non un résultat démontré.

Le [registre des corrections](revision_2026-09-15/REGISTRE_CORRECTIONS.md) conserve les décisions et le report différé. Le proto-rapport de stage et les commentaires originaux restent inchangés. La [version commentée](revision_2026-09-15/reference/latex/note.pdf) est archivée.

La deuxième passe traite le [carnet V2 rempli](COMMENTAIRES_PROTO_ARTICLE_V2.md). Son [PDF de référence figé](revision_2026-09-17/reference/note.pdf), ses sources et les annotations originales sont conservés. Le [registre V2](revision_2026-09-17/REGISTRE_CORRECTIONS_V2.md) distingue les corrections appliquées des intégrations graphiques différées et prépare leur transfert au rapport, toujours non modifié. Les générateurs Simulation Lab et les campagnes restent intacts pendant le travail de l'auteur ; aucune simulation complémentaire n'est lancée.

La passe V2 ajoute un glossaire, précise la compatibilité numérique et la composition temporelle, explicite la compensation de dotation et mesure les médianes instantanées des âges. Ce dernier calcul se reproduit avec `../.venv/bin/python note_resultats/scripts/ages_v2.py` depuis le dossier `recherche/` ; ses sorties et empreintes sont dans `revision_2026-09-17/`.

## Lire et compiler

- `latex/note.pdf` : document compilé.
- `latex/note.tex` : assemblage de `corps_article.tex`, `modele_article.tex`, `physique_echelles.tex`, des schémas, de `annexes_article.tex` et `sources_article.tex`.
- `latex/data_article/` : nouveaux exports, estimateurs, environnement et manifeste des sources avec SHA-256.
- `latex/data_revision/` : exports antérieurs conservés et utilisés. Les anciens fichiers LaTeX non inclus ne sont pas le texte courant.
- `latex/figures/` et `numbers.tex` : copies locales.

Depuis ce dossier :

```bash
cd latex
pdflatex -interaction=nonstopmode -halt-on-error note.tex
pdflatex -interaction=nonstopmode -halt-on-error note.tex
pdflatex -interaction=nonstopmode -halt-on-error note.tex
```

Compiler ne nécessite ni le rapport long, ni les questionnaires, ni les campagnes. Recalculer exige les données du projet et les dépendances scientifiques de son environnement Python. Depuis `/home/anatole/jupyter/recherche/` :

```bash
OPENBLAS_NUM_THREADS=1 ../.venv/bin/python note_resultats/scripts/revision_article.py
OPENBLAS_NUM_THREADS=1 ../.venv/bin/python note_resultats/scripts/verify_article.py --compile
```

Le premier script recalcule douze figures et le tableau de stationnarité, sans nouvelle simulation, y compris les corrections graphiques V2. Une figure antérieure est conservée et trois schémas sont dessinés directement en LaTeX. Le second effectue neuf tests ciblés et une compilation autonome dans un dossier temporaire. Cinq contrôles supplémentaires sont disponibles dans `scripts/verify_v2.py`. Ce n'est pas une réplication indépendante de tout le moteur.

Ne pas utiliser les générateurs partagés de `revision_documents/` pour cette révision limitée à l'article : ils peuvent aussi écrire dans le rapport. Le collecteur historique `scripts/collect.py`, inadapté au nouvel assemblage, s'arrête désormais sans écrire.

## Portée

Les élasticités sont des contrastes finis pour A × 1,5, non une calibration empirique de l'effet rebond. Les quantiles ne suivent pas des groupes fixes d'entités. Une stabilité de Gini n'établit pas l'invariance de toute une distribution. La pondération par surplus donne une identité comptable, pas à elle seule l'explication causale des populations.

Les figures nouvelles séparent observations et ajustements, avec incertitudes entre graines. Les tableaux de quantiles et d'élasticités sont générés depuis les données ; les macros historiques restent synchronisées avec M4.4. Des valeurs littérales demeurent dans le texte : il n'existe pas de garantie d'automatisation de chaque nombre.

Les ajustements de puissance tronquée présentent des écarts systématiques malgré leurs R² élevés. Les contractions sont ajustées par une exponentielle discrète. Aucun de ces résultats ne prouve la criticité.

Le diagnostic de charge utilise les intérêts versés divisés par production + intérêts reçus. Le service dû n'est pas disponible dans les panneaux : aucune réfutation causale de la convexité n'en découle. Les instantanés comparables commencent à 2010 ; les dates 1000, 2000 et 8000 ne sont pas représentées artificiellement. Aucune campagne supplémentaire de recherche d'une réponse négative n'a été lancée.
