# Note d'interprétation abstraite du modèle (version 27-mars)

Le vocabulaire (`actif`, `passif`, `prêt`, `intérêt`, `faillite`) est un **habillage de lecture** pour une dynamique plus générale entre entités couplées.

## Lecture dynamique des grandeurs

- `actif` : réserve/ressource mobilisable.
- `passif` : taille engagée qui augmente la capacité locale mais aussi la vulnérabilité.
- `prêt` : couplage orienté transférant de la capacité et créant une dépendance persistante.
- `intérêt` : flux récurrent associé au couplage.
- `faillite` : perte locale de viabilité pouvant se propager.

## Mécanisme générique implémenté

Le système combine :

1. Entrées d'entités,
2. extraction sous-linéaire en fonction de la taille,
3. contraintes de flux sur les couplages,
4. dissipation des stocks,
5. réallocation via interactions,
6. fragilisation locale et cascades.

Cette structure se lit comme un modèle de **système complexe** (et pas uniquement comme une simulation économique).

## Grille d'analyse recommandée

Toujours distinguer :

1. la sémantique des noms,
2. la fonction dynamique effective dans les mises à jour,
3. la portée abstraite du mécanisme (régimes critiques, propagation, auto-organisation).
