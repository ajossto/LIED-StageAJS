# Notes Claude — étude de sensibilité

## Session 2026-05-11 — Intégration campagnes adaptatives

### Ce qui a été fait

1. **Obj 4 résolu** : "densite" dans Figure 6 (`codex_long_probe_steps3000_seeds42.pdf`)
   identifié précisément dans le code (`codex_long_probe.py:206`) :
   - Colonne 3 "densite" (orange) = `ts_densite_fin` = `densite_fin` = `volume_prets / actif_total`
   - Colonne 4 "prets/entite" (rouge) = `ts_n_loans / ts_n_alive` = densité contractuelle
   - Caption de la Figure 6 mis à jour dans le rapport avec cette définition.

2. **Obj 5 — campagnes adaptatives intégrées au rapport** :
   - Heatmaps copiées : `figures/map_*_heatmap.png` → `report/figures/`
   - Figures coupling ajoutées aux subsections existantes (4 figures `claude_coupling_*.pdf`)
   - Nouvelle section `\section{Campagnes adaptatives : cartes de phase denses}` (lignes 629-895)
   - 4 sous-sections avec tables denses et analyses :
     - λ×k étendu (417 runs)
     - k×μ étendu (327 runs)
     - σ_α×k étendu (267 runs)
     - θ×δ unifié (468 runs) — avec mise en garde critique sur l'extinction
   - Tableau de synthèse transversal ajouté
   - Boucles #18-21 ajoutées dans la table de boucles
   - Annexe tracabilite mise à jour

3. **Diagnostic critique θ×δ** : le motif "fraction=1.00 pour δ≥0.12" est un
   artefact d'extinction (n_alive≈0, densite≈0), non un régime actif.
   Ce point est clairement signalé dans le rapport. Le régime actif est dans
   δ∈[0.02,0.03].

4. **Propriété émergente identifiée** : densite_fin stable à 0.24±0.02 dans les
   campagnes λ×k et k×μ, suggérant une propriété émergente robuste du régime.

### Résultats robustes (confiance haute)
- k≤3 jamais de régime en homogène (σ=0)
- μ>0.10 : destructeur universel de régime
- σ_α≥0.035 : destructeur universel de régime
- δ≥0.12 (unifié) : extinction rapide (artefact critère)
- Régime actif θ×δ : δ∈[0.02,0.03] seulement
- d_f≈0.24 robuste dans les campagnes λ×k et k×μ

### Résultats plausibles (confiance moyenne, fragiles statistiquement)
- Gini plus élevé (0.31) en campagne σ_α×k (91 runs seulement)
- Non-monotonie dans k×μ (effets de front de phase vs. artefacts petits N)

### Ce qui reste à faire
- Obj 8 (P4) : vérifier si Fig 13 (trajectoires 10k) est du même type que Fig 7
  (planches OAT comparatives). Si non, créer la planche comparative pour la sonde 10k.
- Analyse plus fine des fronts de phase dans k×μ (non-monotonie à k=3, k=6)
- Mécanisme de δ=0.01 (absence de régime même à θ faible)
- Distribution des tailles en régime (Gini/lognormal)
