# Charte de visualisation — Règles de bonne-séance

Toutes les règles ci-dessous s'appliquent **toujours**, sans exception, à tout graphique produit dans ce projet.

---

## 1. Normalisation des histogrammes de densité

Un histogramme de densité doit satisfaire : ∑ (density_i × Δx_i) ≈ 1.

La formule correcte est :

```
density_i = count_i / (N × Δx_i)
```

où `Δx_i` est la **largeur linéaire** du bin `i` et `N` le nombre total d'observations.

**Attention :** quand les données sont dans (0, 1), les bin widths peuvent être << 1, ce qui rend `density >> 1`. Ce n'est pas un artefact — c'est correct. La valeur s'interprète comme :

```
P(x ∈ bin_i) = density_i × Δx_i
```

Un point avec `density = 10²` et `Δx = 0.01` représente une probabilité de 1 %. Sans barre d'erreur, on ne sait pas si ce point est basé sur 1 occurrence (très incertain) ou 1000 (fiable). D'où la règle suivante.

---

## 2. Barres d'incertitude — obligatoires sur tout histogramme de données

L'incertitude de Poisson sur le bin `i` est :

```
σ_density_i = sqrt(count_i) / (N × Δx_i)
```

Pour `count_i = 1` : `σ = density` → barre aussi haute que la valeur → point visuellement identifié comme peu fiable.

**Ne jamais produire un histogramme de données sans barres d'incertitude.** Utiliser `plot_utils.log_histogram()` ou `plot_utils.linear_histogram()` qui les calculent automatiquement.

Pour des histogrammes de comptage (effectif brut, pas de densité), utiliser `yerr=sqrt(counts)`.

---

## 3. Nombre de bins — adaptatif, jamais arbitraire

Utiliser `n_bins='auto'` qui applique :

- **Freedman-Diaconis** si l'IQR est non nul : `Δx = 2 × IQR × n^{-1/3}`
- **Sturges** sinon : `n_bins = ceil(log2(n) + 1)`, borné dans [5, 50]

Ne jamais choisir un nombre fixe sans justification explicite dans le commentaire du code.

---

## 4. Afficher N

Chaque graphique doit mentionner la taille de l'échantillon : dans le titre, le sous-titre ou la légende.

Mauvais : `ax.set_title("Distribution des actifs")`  
Bon : `ax.set_title(f"Distribution des actifs (n={len(values)})")`

---

## 5. Zoom inset — obligatoire quand une région est scientifiquement importante

Si une queue de distribution (e.g., grands actifs = potentielle loi de puissance) ou un pic n'est pas visible à l'échelle globale, ajouter un inset zoomé avec `plot_utils.add_zoom_inset()`.

L'inset doit tracer les mêmes données (barres + erreurs) restreintes à la zone d'intérêt.

---

## 6. Paramètres de sauvegarde

Toujours utiliser la fonction `_save(fig, path)` qui applique `dpi=150, bbox_inches='tight'`.

---

## 7. Axes log-log

Sur un graphique log-log :
- Vérifier que la densité est cohérente avec l'échelle affichée.
- Ne pas mélanger une densité normalisée par log-width et un axe à échelle linéaire (ou vice-versa).
- Afficher les grilles mineures : `ax.grid(True, which='both', alpha=0.25)`.

---

## 8. Régressions linéaires

Toujours afficher l'exposant **avec son incertitude** et le r² :

```
pente = -2.31 ± 0.14  (r²=0.97)
```

Utiliser `plot_utils.plot_regression()` qui calcule la bande de confiance à 95 % via `scipy.stats.linregress`.

---

## 9. Dépendances autorisées

`numpy`, `scipy`, `matplotlib` sont tous autorisés et encouragés. Ne pas réimplémenter ce qu'ils font mieux.

---

## Fonctions utilitaires disponibles

```python
from simulation_lab.plot_utils import (
    apply_style,        # rcParams globaux
    log_histogram,      # histogramme densité log-X + erreurs Poisson
    linear_histogram,   # histogramme densité linéaire + erreurs Poisson
    add_zoom_inset,     # zoom inset avec lignes de connexion
    plot_regression,    # régression linéaire + bande de confiance 95 %
)
```
