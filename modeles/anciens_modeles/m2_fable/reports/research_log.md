# Journal de recherche — réplication M2 (workspace m2_fable)

## 2026-07-03 — Session unique (inventaire → validation)

### Contexte
- Consigne : réplication critique du document de conception M2
  (`recherche/conception_boltzmann_pareto_soc/conception_modele_M2.md`).
- Un agent concurrent travaille dans `jupyter/reports/` ; tout mon travail est
  isolé sous `anciens_modeles/m2_fable/` (consigne utilisateur explicite). Aucun fichier hors
  de ce dossier n'est modifié ; le venv partagé est utilisé sans installation.

### Fichiers produits
- `reports/00_inventory.md` — inventaire ; repère notamment que le prototype
  E7c **dévie de la spec M2** (volume de prêt hérité du WIP : `theta`,
  `offer_frac` ; créances de la faillie annulées au lieu de transférées).
- `reports/01_critical_reading/main.tex` (compilé) — résumé fidèle,
  reconstruction mathématique, hypothèses H1/H2, critique (10 questions).
  Points saillants : condensation par prorata = candidat n°1 d'explication
  alternative de la queue ; le rappel déterministe vers w* rend le corps
  exponentiel improbable ; l'écart exposant revenu (4,5-4,9) vs NW (2,7-2,8)
  dans E7c contredit la prédiction §3.5 du rapport sans commentaire.
- `reports/02_technical_spec/main.tex` (compilé) — conventions C1-C10,
  invariants I1-I10, formats de sortie, protocole opérationnel.
- `src/m2/` — implémentation complète (config, entities, contracts, market,
  bankruptcy, simulation, metrics, analysis, plots).
- `tests/` — 31 tests, 0 échec (`python3 tests/run_all.py`).
- `experiments/m2/` — run_baseline, run_ablation, run_grid, run_long,
  run_validation, analyze_long, summarize_grid.

### Erreurs rencontrées et corrections
1. **Biais du critère AIC du corps** (découvert par test) : ajuster des
   familles non tronquées sur les 95 % inférieurs pénalise la vraie famille
   (gamma bat une exponentielle pure avec dAIC=31). Correction : MLE tronqué.
2. **Biais pro-Pareto du LR historique** (`tail_test.py`) : la log-normale de
   comparaison était ajustée par moments non tronqués sur la queue → sur des
   données log-normales pures, R=+575, p≈0 « en faveur de la loi de
   puissance ». Même ordre de grandeur que les « LR +566 à +694 » de [E7c] :
   la preuve de queue Pareto du rapport est très probablement un artefact de
   ce test. Correction : MLE de la log-normale tronquée en x_min.
3. Assertions de tests trop strictes sur le LR corrigé (une log-normale
   tronquée imite une Pareto : signe de R non informatif sur Pareto pure) —
   documenté comme limite de puissance du test.

### Expériences lancées (T=2000, sauf mention)
- baseline seeds 0/1/2 ; ablations proto_e7c (cancel), destroy, nocredit,
  arith, lam30 (seeds 0/1) ; grille sigma×eps0/w0×k (18 cases) ;
  ksweep k=2,4 ; runs longs T=6000 (nocredit, cancel; seeds 0/1).

### Résultats principaux (baseline, 3 seeds)
- **Population bornée endogène** : N* ≈ 1600-1720, pente relative
  < 0,1/1000 pas ; extensivité N*/λ = 166,6 identique à λ=10 et λ=30.
- **Prolifération des contrats** : la règle M2 « transfert au prorata » rend
  le carnet non stationnaire (1244 → 43 977 contrats entre t=1000 et 2000,
  seed 0) — croissance combinatoire par scission ; le prototype E7c (annulation)
  a un carnet stationnaire (~600). Vice de spécification à rapporter.
- **Queue** : α_CSN(NW) ≈ 2,56-2,79 par fenêtres, quasi stable (dérive +0,12
  sur seed 0, IC bootstrap disjoints ; stables seeds 1-2) — réplique E7c
  (2,70/2,79/2,84) malgré la règle de faillite différente.
- **MAIS le LR corrigé s'inverse** : la log-normale tronquée bat la loi de
  puissance sur NW dans 7 fenêtres sur 9 (p<0,05) ; jamais l'inverse.
- **Corps non exponentiel** (H1 réfutée en l'état) : Fisk gagne partout sur NW
  (dAIC_exp ≈ 500-780) ; log-normale sur revenu et w. med/mean(corps NW)
  ≈ 0,69-0,70 pourtant — le ratio « exponentiel » ne discrimine pas.
- **Test mécanistique** : drift du corps POSITIF (A0_[YR] = -4,15 < 0 requis
  > 0) — le corps exponentiel [YR] est mécaniquement impossible : les entités
  du corps montent en moyenne (transport vers le croisement), le corps est un
  régime de flux, pas un équilibre drift-diffusion.
- **Anti-cohorte : passe largement** : corr(âge, log NW) = 0,09-0,15 ;
  top décile : survie 11-17 % sur 1000 pas, persistance < 4 %, 90-95 % du top
  né dans les 1000 derniers pas. Nuance : mortalité instantanée du top = 0
  (on ne meurt pas riche : on descend d'abord, puis on meurt pauvre).
- **SOC invisible en baseline** : faillites/pas ≈ Poisson(λ) étroit (max 21,
  p99=17), pas de queue lourde de cascades à k=6 ; corr(concentration du
  crédit, faillites suivantes) ≈ 0 (concentration ~82 % pourtant).
- **Ablation décisive — nocredit ≡ baseline distributionnellement** : sans
  aucun crédit, mêmes exposants (2,62-2,89), même corps Fisk, même med/mean,
  même renouvellement. **Le crédit ne contribue à rien de mesurable dans la
  distribution à T=2000.** La « queue stable » de E7c passe dans un modèle
  sans crédit ni cascades : l'exposant α≈2,7 ≠ 3,6 = 1+1+2δ/σ² (Kesten GBM
  pur) suggère un transitoire log-normal commun plutôt qu'un régime de Kesten.
- **Ablation arith : le marché meurt** (176 prêts en 2000 pas, tous vers des
  emprunteurs déjà condamnés). La moyenne géométrique des taux n'est pas une
  convention anodine : elle porte l'existence du marché.
- **Ablation destroy ≈ baseline** : la condensation par prorata du résiduel
  n'est PAS le moteur de la queue (mon hypothèse alternative n°1 réfutée).

### Hypothèses infirmées / confirmées à ce stade
- H1 (corps exponentiel) : **infirmée** (AIC tronqué + mécanisme drift).
- H2 (queue Pareto stabilisée par la boucle crédit-cascades) : **non soutenue
  à T=2000** (queue identique sans crédit ; LR pro-log-normale ; pas de
  cascades à queue lourde ; pas de corrélation concentration→cascades).
  Verdict définitif suspendu aux runs longs T=6000 (dérive comparée).
- Bornage endogène : **confirmé** (et il tient sans crédit).
- Classes dynamiques : **confirmé** (au-delà des seuils du rapport).
- « Sans réglage fin » : partiellement infirmé — la borne basse de la fenêtre
  de naissance mord exactement comme prévu (σ=0,15 → pop ~15 000, mortalité
  quasi nulle) ; grille en cours.

### Résultats complémentaires (même session, suite)
- **Runs longs T=6000** : aucune dérive de l'exposant, ni nocredit ni cancel
  (α∈[2,65;2,81] sur 11 fenêtres × 2 seeds × 2 variantes ; IC bootstrap se
  recouvrent). La queue est authentiquement stationnaire — mécanisme
  démographique type Reed (GBM tué au plancher + âges mélangés), le crédit
  n'y change rien. LR corrigé : log-normale préférée dans TOUTES les fenêtres.
- **Le « corps Fisk » n'est pas un artefact de pooling** : les snapshots
  individuels (n≈1500) préfèrent aussi Fisk (dAIC 43-61). Mais QQ-plot
  exponentiel quasi linéaire et med/mean=ln 2 : corps « exponentiel à l'œil,
  Fisk au microscope ».
- **Grille (partiel)** : ligne σ=0,15 hors régime (mortalité ~0, pop 15-20k
  croissante — borne basse de la fenêtre de naissance confirmée) ; cases
  σ=0,25 à ε₀ élevé : prolifération catastrophique de contrats
  (2,58 M actifs sur sig0.25_eps0.25_k6 !).
- Rapports 03, 04, 05 rédigés et compilés (04 : tableau de grille à insérer).

### Grille §6.5 (16/18 cases ; tableau dans le rapport 04)
- σ=0,15 : hors régime (mortalité ~0, pop 15-20k croissante) — borne basse
  binaire, confirmée.
- σ=0,25 : régime cible, forme invariante en ε₀/w₀ et k ; α = 2,66-2,81.
- σ=0,35 : régime à petite population (190-450), α = 2,1-2,4, med/mean
  0,54-0,57 → la coïncidence med/mean=ln 2 est propre à σ=0,25.
- Réponse de α à σ : 3,8 → 2,7 → 2,2-2,4, monotone. dmax≈20 partout : pas de
  transition SOC k=3 vs 6.
- Pathologie du carnet généralisée hors baseline : 1,1 M (0,25/0,5/k3),
  2,6 M (0,25/0,25/k6), 12,4 M de contrats (0,25/0,5/k6, 29 min de calcul) ;
  les 2 cases (0,35/0,5) encore en cours à la rédaction (5,5 M à t=1000).
- Test X1.4 : corps [BM] éq. 7 (inverse-gamma) rejeté, ΔAIC +4236 vs Fisk.
  Le corps n'est ni [YR] ni [BM] : Fisk (forme ≈ 1,45).

### Livrables finaux
- `reports/04_validation_report/main.pdf` : validation complète + tableau de
  grille + figure de dérive longue.
- `reports/05_negative_results/main.pdf` : hypothèses réfutées, artefacts
  d'outillage, vices de spécification, non-réplications.
- `reports/final_summary.md` : réponses aux 9 questions du brief.
- Reste à insérer à la fin des runs : 2 cases de grille (0,35/0,5) et le
  balayage ksweep k=2/k=4 (attendu : résultat nul, le crédit étant
  distributionnellement neutre).

## 2026-07-03 (suite) — correctif merge_pairs + synthèse PDF
- Sur question de l'utilisateur (« pourquoi ne pas agréger les contrats d'une
  même paire ? ») : variante `merge_pairs` implémentée (fusion au taux moyen
  pondéré par le principal — flux d'intérêts, NW et prorata exactement
  préservés ; seule la répartition C2 d'un paiement partiel entre prêteurs
  peut différer, événement rare suivi de faillite au même pas).
- 6 tests ajoutés (37 verts au total). Run de contrôle `abl_merge_s0` :
  trajectoire macro identique à baseline_s0 (pop 1631, W=4,415e5), carnet
  borné à 9 514 contrats (vs 43 977). Le correctif est validé ; rapports 05
  et final_summary mis à jour.
- Synthèse finale mise en page LaTeX (reports/final_summary_pdf/main.pdf,
  4 pages, tableau de bord à verdicts colorés) — le .md reste la source.
- Toujours en cours : 2 dernières cases de grille (0,35/0,5) + ksweep k2/k4.

## 2026-07-03 (fin) — clôture de la grille
- La case (0,35/0,5/k3) en règle prorata a été TUÉE après ~50 min : 5,5 M de
  contrats à t=1000, 7,8 Go de RAM, croissance géométrique du carnet →
  extrapolation en jours/OOM. Décision : ne pas attendre un temps de calcul
  exponentiel ; snapshots partiels conservés
  (results/grid_sig0.35_eps0.5_k3_partial_prorata, jusqu'à t=1900).
- Les 2 cases (0,35/0,5) réexécutées en merge_pairs : 72 s et 54 s.
  Contrôle de cohérence : pools [1400,1900) du prorata partiel vs merged
  IDENTIQUES (n=8934, m/m=0,590, α=2,32, xmin=378) — substitution rigoureuse.
- ksweep complet k∈{2,3,4,6} : α = 2,75/2,75/2,69/2,81, dmax = 22/22/20/24 —
  AUCUNE transition SOC à k≥3 ([ÉLAGAGE] non répliqué). À k=2 le marché est
  anecdotique (251 contrats) et N* remonte vers la valeur du modèle nul.
- Tableau de grille du rapport 04 complété (18/18 cases) et recompilé.
- Grille close. Toutes les expériences du protocole sont terminées.
