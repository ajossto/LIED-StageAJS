# M4.3Live-v2 — journal de travail

Tenu au fil de l'eau.

## 21 août 2026 — décisions de périmètre (retours oraux de l'utilisateur)

- **Aucun traitement du cas partiel.** v2 mesure en portée globale.
- **Une seule borne de transfert : `optimum`.** `mkt_capped` cumulé vaut
  exactement 0 sur les runs du dépôt : c'est du code mort.

## 22 août 2026 — fork

Fork par COPIE de `m4_3live_credit_soc/`. Le paquet v1 est GELÉ et n'est
jamais importé. Renommages : paquet `m4_3live` → `m4_3live_v2`, routes de
l'IHM `/live` → `/live2` pour que les deux lignées coexistent dans le même
serveur `simulation_lab`, identifiants de run `m4_3live__` → `m4_3live_v2__`
pour qu'aucun run v2 ne se confonde avec les 203 runs v1 déjà importés.

Scripts non repris : les campagnes v1 (`ablation_k0`, `scaling_gamma`,
`scaling_theory`, `tension_sweep`, `tension_vs_A`, `time_rescaling`,
`bench_kernel`, `exact_amplitude`, `tension_analysis`, `conception_evidence`,
`protocol_figures`, `verification_figures`, `analyse`, `make_report_tables`)
ont produit des résultats **publiés et acquis** que v2 cite sans les refaire.
