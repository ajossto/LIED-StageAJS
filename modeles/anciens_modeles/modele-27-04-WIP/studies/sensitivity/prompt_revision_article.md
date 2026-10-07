# Prompt — Révision du rapport de sensibilité pour publication

## Contexte du projet

Tu travailles sur le rapport LaTeX d'une étude de sensibilité d'un modèle
multi-agents physico-économique. Le modèle simule des entités productives qui
s'échangent une ressource (le joule), se prêtent entre elles et peuvent faire
faillite en cascade.

**Fichiers de travail :**
- Rapport à modifier :
  `/home/anatole/jupyter/modeles/anciens_modeles/modele-27-04-WIP/studies/sensitivity/report/rapport_final_sensibilite.tex`
- Annexe traçabilité (incluse via `\input`) :
  `/home/anatole/jupyter/modeles/anciens_modeles/modele-27-04-WIP/studies/sensitivity/report/annexe_tracabilite.tex`
- Figures disponibles sur disque :
  - `report/figures/` — figures déjà référencées + heatmaps adaptatives
  - `studies/sensitivity/figures/` — surfaces 3D : `map_*_3d.png`
- Données sources (JSON) :
  `/home/anatole/jupyter/modeles/anciens_modeles/modele-27-04-WIP/studies/sensitivity/results/`
  - `adaptive_lambda_k_extended.json` (417 runs)
  - `adaptive_k_mu_extended.json` (327 runs)
  - `adaptive_sigma_k_extended.json` (267 runs)
  - `adaptive_theta_delta_unified.json` (468 runs)
  - `codex_long_probe_steps3000_seeds42.json`
  - `k_sweep_steps1500_eps0.001.json`
  - `alpha_sigma_sweep_steps1500_eps0.001.json`
- Python : `/home/anatole/jupyter/.venv/bin/python3`

**Compilateur LaTeX disponible :** `pdflatex`

---

## Mission

Le rapport existe déjà et contient les résultats. Il doit être **révisé pour
atteindre le niveau de lisibilité d'un article scientifique**. Il ne s'agit
pas de rajouter des résultats, mais de rendre les résultats existants lisibles
par un lecteur qui n'a pas participé à l'étude.

Lis l'intégralité du `.tex` avant d'agir. Les modifications sont nombreuses
et interdépendantes : planifie d'abord, puis édite.

---

## Liste des problèmes à corriger

### 1. Toute grille 2D de paramètres doit être une surface 3D, pas une table

**Principe général :** Chaque fois que le rapport montre un tableau dont les
lignes et colonnes sont deux paramètres variés et les cellules une fraction
ou une métrique, ce tableau doit être *remplacé ou complété* par une
visualisation graphique. Un tableau de chiffres de type 0.47 / 0.00 / 1.00
n'est pas lisible comme un article.

**Ce principe s'applique à :**
- Carte λ×k coarse (Table actuelle ~Table 7)
- Carte k×μ coarse (~Table 8)
- Carte σ_α×k coarse (~Table 9)
- Carte θ×δ coarse (~Table 10)
- Carte λ×k adaptative (~Table 11)
- Carte k×μ adaptative (~Table 12)
- Carte σ_α×k adaptative (~Table 13)
- Carte θ×δ adaptative (~Table 14)

**Figures déjà disponibles pour les campagnes adaptatives :**
Les surfaces 3D `map_*_3d.png` existent dans
`studies/sensitivity/figures/`. Copie-les dans `report/figures/` et
remplace les heatmaps `map_*_heatmap.png` actuellement dans le rapport.

**Figures à générer pour les campagnes coarse :**
Les `claude_coupling_*.pdf` actuellement dans le rapport sont des figures
2D peu lisibles. Il faut générer des surfaces 3D pour chacune des 4
campagnes coarse en lisant les données depuis les JSON correspondants :
- `alpha_sigma_sweep_steps1500_eps0.001_aggregate.json` pour σ×k
- `k_sweep_steps1500_eps0.001_aggregate.json` pour k
- Pour les couplages coarse (λ×k, k×μ, θ×δ) : les données sont dans les
  JSON `results/codex_phase_maps*.json` ou reconstituables depuis les runs
  Simulation Lab si disponibles ; sinon, les heatmaps coarse existantes
  suffisent et on garde les `claude_coupling_*.pdf`.

**Format des surfaces 3D :**
- Axe X : paramètre 1 (valeurs numériques)
- Axe Y : paramètre 2 (valeurs numériques)
- Axe Z : fraction de seeds converges ∈ [0, 1]
- Couleur : même fraction (colormap viridis ou RdYlGn)
- Taille des marqueurs ou transparence proportionnelle à n_seeds par cellule
  (3 = petit/transparent, 15 = grand/opaque)
- Générer en Python avec matplotlib via
  `/home/anatole/jupyter/.venv/bin/python3`
- Sauvegarder en `report/figures/claude_surface_3d_*.pdf` ou `.png`

**Les tables textuelles 2D peuvent rester en annexe** ou être conservées
sous forme compacte, mais ne doivent plus être la représentation principale.

### 2. Incertitude sur les fractions de régime

Les tables des campagnes adaptatives montrent des fractions comme `0.47` ou
`1.00` sans indiquer combien de seeds ont été tirés par cellule.

**Problème** : 2/3 = 0.67 n'a pas la même valeur informative que 10/15 = 0.67.
La campagne adaptative alloue justement 3 seeds dans les zones stables et
jusqu'à 15 aux frontières — cette information est invisible dans les tables.

**Ce qu'il faut faire :**

a) Lire chaque JSON pour extraire le nombre de seeds par cellule (clé `seed`
par run). La distribution réelle est 3 ou 15 seeds par cellule.

b) Dans chaque table de campagne adaptative, ajouter une colonne ou une
annotation montrant `k/n` (ex : `7/15`) au lieu de la fraction seule.
Format suggéré : remplacer `0.47` par `7/15` dans les cellules où n=15,
et `1/3` dans les cellules où n=3. Cela rend l'échantillon visible.

c) Ajouter en dessous de chaque table une ligne d'annotation :
```
n = 3 dans les zones stables (fraction = 0.0 ou 1.0 confirmées) ;
n = 15 sur les frontières détectées (0 < fraction < 1).
```

d) Dans la section méthode (voir point 4), expliquer l'intervalle de Wilson
pour une proportion : pour n=3, l'intervalle à 95 % d'une fraction 2/3
est [0.19, 0.93] — très large. Pour n=15 avec 10/15, il est [0.46, 0.87].
Mentionner cela explicitement pour prévenir la sur-lecture des fractions
basses à n=3.

### 3. Standardisation de la notation

Le rapport utilise actuellement plusieurs notations pour les mêmes grandeurs.
Les corriger **partout** de façon cohérente :

| Ancienne notation(s)                      | Notation canonique à utiliser |
|------------------------------------------|-------------------------------|
| `df_mean`, `d_f`, `D`, `densite_fin_mean`, "densite financiere en volume" | $d_f = V/A$ (défini une fois en section Périmètre) |
| `loan_density`, `L/n_{\mathrm{alive}}`, "prets/entite" | $\ell = L/N$ (défini une fois) |
| `n_alive`, `n_{\mathrm{alive}}`, $N$, "nombre d'entites vivantes" | $N$ ou $n_{\mathrm{alive}}$ — choisir l'un et s'y tenir |
| "failure_lambda_ratio", "flr", "ratio faillites/lambda", "equilibre de flux" | $r_f = \bar{f}/\lambda$ (défini formellement) |
| "bounded_tail" | $\mathcal{B}$ ou garder le nom de code, mais **définir formellement une fois** |

Dans la section Périmètre et conventions, ajouter une mini-table de notation.

### 4. Section Méthode formelle (à créer)

Insérer une nouvelle section `\section{Protocole expérimental}` **avant**
la section "Lecture initiale : corrélations pilotes". Elle doit contenir :

**4a. Table des paramètres du modèle**

Une table avec au minimum :

| Symbole | Nom code (`snake_case`) | Signification | Valeur nominale | Plage testée |
|---------|------------------------|---------------|-----------------|--------------|
| $k$ | `n_candidats_pool` | Nombre de candidats évalués par emprunteur à chaque pas | 4 | 2–8 |
| $\lambda$ | `lambda_creation` | Taux de création d'entités par pas | 2.0 | 0.5–6.0 |
| ... | ... | ... | ... | ... |

Les valeurs nominales sont les valeurs des deux centres OAT (voir ci-dessous).
Extraire ces valeurs du JSON `codex_long_probe_steps3000_seeds42.json`
(premier run params) pour le centre k=3, et adapter pour k=4.

**4b. Définition des deux centres OAT**

Les deux centres sont les configurations de référence à partir desquelles
toutes les variations OAT sont mesurées. Définir explicitement **l'intégralité**
du vecteur de paramètres pour chaque centre (pas seulement k et σ) :

- Centre $C_3$ (`subcritical_k3`) : $k=3$, $\theta=0.35$, $\mu=0.05$,
  $\lambda=2.0$, $f=0.2$, $\phi=0.5$, $\delta=0.05$, actif initial = 200,
  passif inné = 190, $n_0=100$ entités, $\epsilon=10^{-3}$, $\sigma_\alpha=0$.
- Centre $C_4$ (`regime_k4`) : identique à $C_3$ mais $k=4$.

**4c. Définition formelle de bounded\_tail**

Le critère opérationnel de régime stationnaire est $\mathcal{B}$, satisfait
si et seulement si, sur la fenêtre de queue $[t_{\mathrm{measure}}, T]$ :
(i) la pente relative de $N$ est inférieure à un seuil, (ii) la pente relative
de $A$ est inférieure à un seuil, (iii) les corrélations de queue sont
suffisantes. Préciser les seuils numériques effectivement utilisés en lisant
le code `claude_analysis/adaptive_coupling_campaign.py` ou le script
`codex_long_probe.py`. Ne pas inventer : lire le code.

Le critère dual utilisé dans les campagnes adaptatives est :
$\mathcal{B} \wedge (|r_f - 1| < 0.5)$ où
$r_f = \bar{f}/\lambda$ est le ratio faillites/création.

**4d. Définition du terme "sonde"**

Expliquer une fois : une *sonde* est une simulation unique ou un petit
ensemble de simulations à durée allongée (3 000 ou 10 000 pas), destinée à
vérifier si un cas ambigu à 1 500 pas est en transitoire ou en régime
permanent. Différent d'une *campagne* (grille systématique de paramètres).

**4e. Définition du terme "OAT" (One-At-a-Time)**

Une analyse OAT consiste à partir d'un vecteur de paramètres de référence
(le *centre*) et à faire varier un seul paramètre à la fois, tous les autres
restant fixés à leur valeur nominale. Chaque variation est appelée une
*perturbation OAT*. L'effet mesuré est le delta de métrique par rapport
au résultat du centre.

**4f. Définition du terme "seed"**

Un *seed* est une valeur d'initialisation du générateur pseudo-aléatoire.
Des seeds différents produisent des réalisations indépendantes du processus
stochastique avec les mêmes paramètres. La variation inter-seeds mesure
la sensibilité aux fluctuations d'initialisation, non à la stochasticité
paramétrique.

### 5. Suppression ou reformulation de la section "Boucles"

La section "Boucles autonomes effectuées" (table avec 21 entrées) est un
journal de travail, pas un élément d'article. Elle doit être soit :
- Supprimée du corps et déplacée en annexe technique (hors `annexe_tracabilite`),
- Soit reformulée en quelques lignes narratives décrivant les itérations
  majeures du protocole.

Option recommandée : transformer en une courte section
`\section{Itérations du protocole}` (6-8 lignes) décrivant les grandes
phases de l'étude (pilote → OAT → couplages coarse → campagnes adaptatives →
sondes longues), sans le détail de chaque boucle.

### 6. Corrections des légendes de figures

Chaque figure doit avoir une légende auto-suffisante : un lecteur ne lisant
que la légende doit comprendre ce qui est représenté.

Corrections prioritaires :

- **Figure "Effets OAT"** : préciser que les barres sont des $\Delta d_f$
  (delta de densité financière) par rapport au centre $C_3$ ou $C_4$ selon
  le groupe ; mentionner seed 42 uniquement.
- **Figure "Balayage $k$"** : préciser les axes, les unités, le nombre de
  seeds, la durée.
- **Figure "Sonde longue"** (Fig. codex_long_probe) : la légende a été
  améliorée dans la version courante mais vérifier qu'elle mentionne
  explicitement la définition de $d_f$.
- **Figures de surfaces 3D** : ajouter dans la légende la couleur = fraction
  de seeds converges ; expliquer que l'axe Z = fraction bornée ∈ [0, 1].
  Mentionner le nombre de seeds par cellule (3 ou 15).

### 7. Définir $\bar{d}_f$ dans le tableau de synthèse

Dans le tableau de synthèse des campagnes adaptatives, la colonne
$\bar{d}_f$ n'est pas définie. Ajouter dans la caption :
"$\bar{d}_f$ = densité financière moyenne en volume ($V/A$) sur les runs
converges ; $\bar{G}$ = coefficient de Gini moyen de l'actif entre entités."

### 8. Correction de la date et du titre

La date `30 avril 2026 -- mise a jour couplages et probabilites` est obsolète.
Remplacer par `Mai 2026 -- version intégrant les campagnes adaptatives (1\,479 runs)`.

### 9. Vérification de cohérence de la section θ×δ

S'assurer que la mise en garde sur l'extinction (δ≥0.12, n_alive≈0) est
clairement signalée dans :
- Le texte de la subsection θ×δ (déjà présent dans la version actuelle)
- La légende de la surface 3D correspondante (à ajouter)
- Le tableau de synthèse (colonne θ×δ doit noter "actif seulement, δ≤0.05")

---

## Contraintes

- Ne pas modifier les scripts de simulation (`oat_*.py`, `*sweep*.py`, etc.)
- Ne pas modifier les JSON de résultats
- Écrire en LaTeX correct, compilable avec `pdflatex`
- Conserver le français
- Ne pas ajouter de nouveaux résultats numériques inventés : tout chiffre
  doit être extrait d'un JSON existant ou calculé depuis les JSON

## Validation finale

Compiler avec `pdflatex -interaction=nonstopmode rapport_final_sensibilite.tex`
depuis le répertoire `report/`. Vérifier absence d'erreurs fatales.
Les overfull \hbox dans l'annexe traçabilité (lignes longues de noms de runs)
sont tolérables.

## Périmètre de fichiers modifiables

- `report/rapport_final_sensibilite.tex`
- `report/annexe_tracabilite.tex`
- `report/figures/` (pour y copier les `map_*_3d.png`)
- `notes_claude.md` (note de reprise à la fin)
