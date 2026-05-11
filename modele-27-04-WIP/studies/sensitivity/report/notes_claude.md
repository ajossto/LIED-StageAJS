# Notes de reprise — campagne de sensibilité

**Version** : Mai 2026 — révision vers rapport de publication

## Corrections substantielles (non évidentes depuis le diff)

### 1. Tableau θ×δ : valeurs recalculées depuis le JSON

Les valeurs de fraction bornée dans la table θ×δ de la campagne adaptative
étaient périmées dans la version antérieure du rapport. Elles ont été régénérées
depuis `results/adaptive_theta_delta_unified.json` (468 runs).

Exemples de divergences corrigées :
- θ=0.50, δ=0.02 : ancien rapport 0.47 → JSON 13/15 = 0.87
- θ=0.50, δ=0.05 : ancien rapport 0.67 → JSON 0/3 = 0.00
- θ=0.40, δ=0.02 : recalculé depuis JSON

Toutes les cellules sont désormais au format k/n (ex. "13/15") pour afficher
la taille d'échantillon.

### 2. FLOW_THRESHOLD = 0.15, pas 0.5

Le critère de bilan de flux est |r_f − 1| < 0.15, défini dans
`claude_analysis/adaptive_coupling_campaign.py` (FLOW_THRESHOLD = 0.15) et
`claude_analysis/reclassify_flow_balance.py`.

La spécification initiale de la tâche indiquait 0.5 — valeur incorrecte.
Le rapport utilise désormais 0.15 partout (§Régime permanent, §Campagnes
adaptatives).

### 3. Les tableaux adaptatifs montrent bounded_tail, pas le critère dual

Les fractions dans les tableaux des campagnes adaptatives correspondent
uniquement au critère `bounded_tail` (stabilité de n_alive et de l'actif),
*pas* au critère dual bounded_tail ∧ |r_f−1|<0.15. La prose du rapport
a été corrigée en conséquence.

Le champ JSON `converged` vient de l'ancienne fonction `detect_regime()`
(critère chute 25%) — différent de `regime_diagnostics.bounded_tail`.

### 4. Ligne σ=0.100 ajoutée (absente du rapport initial)

Le JSON `adaptive_sigma_k_extended.json` contient des runs pour σ=0.100
(fraction bornée = 0 pour tous les k). Cette ligne manquait dans le tableau ;
elle a été ajoutée avec toutes les cellules à 0/3.

### 5. Ligne λ=6.0 ajoutée au tableau λ×k

De même, le JSON contient des runs pour λ=6.0, absents du tableau initial.
Ligne ajoutée.

### 6. Artefact d'extinction θ×δ : définition de "136 actifs"

La carte θ×δ présente deux régions distinctes :
- **Régime actif** : δ∈{0.02, 0.03} → seules valeurs donnant des runs bornés
  (71 + 65 = 136 runs bornés)
- **Extinctions** : δ≥0.07 → n_alive≈0, bounded_tail=True par artefact
  (variance nulle, pas de régime économique actif)
- **Aucun régime** : δ=0.01 → 0 run borné

Le tableau de synthèse retient 136 runs (δ∈{0.02, 0.03}).
La note de bas de tableau indiquait incorrectement "δ≤0.05" — corrigé en
"δ∈{0.02, 0.03}".

Note : δ≤0.05 donne 153 runs bornés (δ=0.05 en ajoute 17), mais δ=0.05
n'est pas un régime actif robuste (fraction faible, comportement marginal).

### 7. Figures adaptatives : 3D au lieu des heatmaps 2D

Les heatmaps adaptatives ont été remplacées par les surfaces 3D déjà générées :
`figures/map_*_3d.png` (copiées depuis `studies/sensitivity/figures/`).

Les cartes coarse ont été remplacées par de nouvelles surfaces 3D générées
via `claude_analysis/generate_coarse_3d.py` (fichiers `claude_surface_3d_*.png`).

## Fichiers modifiés

- `report/rapport_final_sensibilite.tex` — révision principale
- `claude_analysis/generate_coarse_3d.py` — nouveau script figures coarse 3D
- `report/notes_claude.md` — ce fichier

## Fichiers NON modifiés

- `run_simulation.py` — aucune modification
- `results/*.json` — aucune modification
- `claude_analysis/adaptive_coupling_campaign.py` — aucune modification
