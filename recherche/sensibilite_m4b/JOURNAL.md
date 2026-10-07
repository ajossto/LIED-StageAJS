# Journal technique — étude de sensibilité M4B

Campagne : `recherche/sensibilite_m4b/`. Moteur : `m4b_credit_soc_mini/m4b/`
(lecture seule), version `m4b-mini-3`, condensat `f3a7ce02cd9185c7`
(SHA-256 tronqué de model.py + io.py + __init__.py — le moteur n'est pas
suivi par git, le condensat fait foi).

## 2026-07-17 — audit, benchmark, protocole

- **Tests moteur** : `tests/test_mini.py` → 6/6 OK (10 s), dont parité
  exacte M4↔M4B sur deux régimes. C'est l'unique recours exécutable à M4
  de l'étude (contrôle de provenance). `tests/test_reporting.py` → 4/4 OK.
- **Inventaire** : Simulation Lab contient 10 runs M4B (validations
  d'intégration, T≤260 sauf un T=2000 graine 1000). Aucun réutilisable
  comme cellule de campagne → tout est reproduit sous manifeste.
  0 run de campagne préexistant dans `recherche/sensibilite_m4b/`.
- **Benchmark** (plan `manifests/benchmark.json`, graine 0, T=2000,
  écriture minimale) : λ=10 → 24 s / 4,0 Mo ; λ=30 → 80 s / 11 Mo ;
  λ=100 → 291 s / 36 Mo ; δ=0,02+σ=0,10 → 42 s. Écriture complète λ=10 :
  39 s / 30 Mo. Instantanés/100 pas : surcoût nul (83 vs 80 s).
- **Neutralité des mesures** : `series.csv` bit à bit identiques entre
  écriture minimale et complète (2 contrôles : λ=10 et λ=30, graine 0).
- **Intégrité** : résidu comptable relatif max ≤ 6e-16, 0 erreur de carnet
  sur les 6 runs de benchmark.
- **Extracteur validé** (`scripts/lib_metrics.py`) sur les runs benchmark :
  N/λ = 14,8/14,8/14,7 pour λ=10/30/100 (grandeur intensive — cohérent
  loi de Little) ; α(s_min=2) = 2,31/2,24/2,32 ; b = 0,287/0,300/0,300 —
  compatibles avec le rapport M4 (α 2,25–2,32 ; b 0,292–0,301).
  Vuong PL/LN : négatif à λ=10/30 (log-normale favorisée, coupure de
  taille finie), positif à λ=100 (+15,0). LRT coupure toujours
  significatif → loi tronquée nécessaire aux petites tailles. À creuser
  dans la campagne (scaling de s_c avec λ).
- **Décisions protocole** : centre de campagne λ=30 (queues ×2,6 pour
  coût ×3,3) ; panels de graines : pilotes {1,2}, exploration {1,2,3},
  confirmation {11..15} (disjoint, indépendance de la confirmation) ;
  seuil d'identifiabilité 100 avalanches s≥2 ; burn-in T/4 + contrôles
  T/8, T/2, demi-fenêtres. LHS 64 points × 3 graines (δ, σ, K0 continus,
  k équilibré), graine du plan 20260717. Pas d'indices de Sobol (pas un
  plan de Saltelli).
- **Protocole compilé** : `report/protocole.pdf` (10 pages, XeLaTeX).
- Pilotes lancés (30 cellules, `manifests/pilotes.json`).

## 2026-07-17 (soir) — dépouillement des pilotes

30/30 `ok` (aucune extinction, aucune censure). Table :
`results/summary/pilotes.csv` ; figure `figures/pilotes_population.png`.

- **Plages initiales validées sans révision** : tous les coins
  (δ,σ,K0,k) produisent des régimes stationnaires non triviaux
  (|dérive relative| ≤ 0,04 sur la fenêtre, moitiés cohérentes).
- **σ=0 : régime propre, pas dégénéré.** Stationnaire, dense
  (N/λ=36,9–37,0 ; 46,2–46,7 avec δ=0,02), cascades très propagatives
  (b=0,65–0,77, α=1,72–1,80, Gini K 0,03). Ma prédiction initiale
  (croissance jusqu'au garde-fou) était fausse : la mortalité existe
  sans choc — à expliquer dans le rapport (défauts de service des
  jeunes emprunteuses, hétérogénéité par âge).
- **Coin lent (δ=0,02, σ=0,10) stationnaire dès T=2000** : T=8000
  donne N/λ=24,3 identique, dérive ~0. Pas besoin de T≫10000 dans les
  plages retenues.
- **Contrôle temporel du centre** : T=4000 vs 2000 → N/λ=14,8 identique,
  α 2,25–2,26 vs 2,26–2,27, b=0,30 stable. n_tail double (≈11 300).
- **Intensivité** : λ=100 au coin lent → N/λ=24,4 = valeur λ=30 (24,1–24,4).
- **Signes d'effets (exploratoire)** : σ↑ → N/λ↓ fortement (24→14,8→6,9
  pour σ=0,1→0,25→0,5) et Gini K↑ (0,05→0,08→0,15) ; δ↑ → N/λ légèrement
  ↑ à σ fixé (24,4→28,0 à σ=0,1) — contre-intuitif, à confirmer ;
  k=2→10 : Gini K 0,13→0,01, α 2,20→2,44, b 0,30→0,24, démographie ~plate ;
  K0=5→100 : N/λ 10,7→19,9.
- **Coûts** : centre 80 s ; σ=0 195–286 s ; T=8000 707 s ; λ=100 lent 513 s.
- **Frontières hors plages** : aucune extinction/censure observée →
  pilotes2 (16 runs) : σ ∈ {0,6, 0,7, 0,85, 1,0}, δ=0,01 (σ=0,05 et 0,25),
  K0 ∈ {2, 200}. OAT (66 runs) lancé en parallèle.

## 2026-07-18 (nuit) — OAT et sondes de frontière dépouillés

OAT 66 runs + pilotes2 16 runs, tous `ok`, 0 échec. Tables :
`results/summary/oat.csv`, `oat_contrasts.csv`, `pilotes2.csv` ;
figures `figures/oat_<axe>.png`. Contrastes appariés vs centre
(z = |Δ|/écart-type inter-graines du contraste) — exploratoire :

- **σ domine la démographie et la propagation.** N/λ : 37 (σ=0) → 7,2
  (σ=0,5), mortalité convexe croissante. Toute la non-linéarité est dans
  σ ∈ [0, 0,2] : b passe de 0,65 à 0,30 et la susceptibilité de 26 à 8,
  puis plateau au-delà de σ≈0,2 ; α monte de 1,80 à ~2,25 (plateau).
  **dette/capital non monotone** : bosse à σ≈0,15–0,2 (1,53) puis
  décroissance (0,90 à σ=0,5).
- **Frontière sans transition brutale** (pilotes2) : à λ=30, N/λ décroît
  continûment jusqu'à 3,5 (σ=1,0) sans extinction — l'extinction absorbante
  est quasi impossible à λ=30 (P(Poisson(30)=0)≈1e-13). La frontière
  d'extinction est une propriété du PETIT λ → plan `lambda_ext`
  (λ ∈ {1,2,3,5,10} × σ ∈ {0,25,0,5,1,0} × 3 graines, 45 runs) créé.
- **Loi de Little vérifiée partout** : N/λ = âge moyen au décès (à <1 %).
- **δ : quasi-échelle du capital.** Effets lisses ~linéaires : δ↑ →
  K/tête chute (159→51 J), N/λ monte (13,5→16,9 — contre-intuitif mais
  très net, z élevé), dette/K décroît ; avalanches à peine touchées
  (b 0,299→0,289, α 2,29→2,22). Candidat « convention d'échelle ».
- **k : levier des inégalités et de la statistique d'avalanches, pas de
  la démographie.** Gini K 0,136→0,010 (k=2→10) ; b 0,305→0,237 ;
  α 2,21→2,43 ; susceptibilité 8,3→5,2 ; dette/K bosse à k=4 ;
  N/λ presque plat (15,4→14,5).
- **K0 : log-linéaire sur la durée de vie** (N/λ 10,7→19,9 pour 5→100),
  b quasi plat, α 2,30→2,14.
- **λ (taille) : intensivité confirmée** (N/λ, Gini, K/tête plats) ;
  susceptibilité ~∝ λ ; max/pop décroît ; à λ=100 la coupure s_c devient
  NON IDENTIFIABLE (fit → 5e8 : dégénère en loi pure, cohérent avec
  Vuong z>0). Décision : traiter s_c comme « au-delà de la portée
  observable » quand s_c >> s_max observé ; le scaling de coupure se lit
  sur λ ∈ {10,30} + max absolu.
- Petite non-monotonie α(λ) : 2,32/2,27/2,31 — à trancher en confirmation.

## 2026-07-18 — LHS, carte d'extinction, rapport préliminaire

- **LHS 192/192 ok, 0 échec** (46 min). Screening
  (`results/summary/lhs_screening.csv`, figures `lhs_prcc/src.png`) :
  surfaces quadratiques R²CV 0,84–1,00 sauf profondeur max (0,09) et
  coupure (0,77). Rôles : σ → démographie (PRCC ∓0,98) ; k → Gini K
  (−0,99) et statistique d'avalanches (α +0,85, susceptibilité −0,86,
  coupure −0,71, b −0,79 avec σ −0,83) ; K0 → démographie secondaire
  (0,91) + Gini revenu (−0,85) ; δ → échelle du capital (K/tête −0,89)
  et faible sur la propagation. Variance graines ≤ 9 % sauf coupure
  (17 %) et profondeur max (72 %). nw_negative_frac : variance nulle
  (structurel — la cascade élimine toute NW négative).
- **lambda_ext 42 runs (3 dédupliqués OAT)** : extinctions SEULEMENT à
  t=1, à λ∈{1,2}, fréquences compatibles avec e^-λ (2/3 à λ=1 vs 0,37 ;
  1/3 à λ=2 vs 0,14). Aucune extinction tardive ; N/λ intensif jusqu'à
  λ=1. → PAS de frontière d'effondrement démographique dans l'espace
  exploré ; carte des régimes = un seul régime stationnaire continu.
- **Aucun run n'a atteint pop_max** (0/382 à ce stade) : diagnostic
  garde-fou sans objet sur l'exploration ; sera revérifié en
  confirmation.
- **Rapport préliminaire compilé** : `report/rapport_preliminaire.pdf`
  (15 pages) avec annexe de traçabilité auto-générée (355 entrées).
  Décisions : coupes σ×k et σ×δ (lancées, 175 nouveaux runs) ;
  13 cellules confirmatoires T=4000 graines 11–15 via lots Simulation
  Lab (`scripts/run_confirm.py`), + lam2_ext 10 graines ; critères de
  confirmation rappelés.
- Extracteur adapté aux dossiers du lab (fallback config.json/run.json ;
  volume_j optionnel pour vieux moteurs). Vieux run lab N/λ=92 :
  fausse alerte — config extrême (δ=0,01, σ=0,03, K0=300, k=2),
  pas un changement de moteur.

## 2026-07-18 — coupes 2D dépouillées, confirmation lancée

Coupes complètes (240 cellules, 169 nouveaux runs, 0 échec ; figures
`cut_sigma_{k,delta}_{heat,lines}.png` ; indices
`results/summary/cut_interactions.csv`) :

- **σ×k : pas de croisement qualitatif** — la transition en σ n'est pas
  déplacée par k (courbes b parallèles). Interaction quantitative
  majeure : ÉVASEMENT DU GINI — σ amplifie l'inégalité seulement à
  petit k (σ=0,5 : Gini 0,24 à k=2 vs 0,02 à k=10). N/λ et dette/K
  quasi indépendants de k (courbes maîtresses).
- **σ×δ : l'hypothèse « δ = échelle pure » tient à σ ≥ 0,2** (b,
  susceptibilité, Gini s'effondrent sur une courbe commune) mais δ
  module b dans le régime corrélé σ < 0,15 (b à σ=0,05 : 0,50 pour
  δ≤0,05 vs 0,43 pour δ=0,1). L'effet δ sur N/λ s'annule à σ=0,05 et
  culmine vers σ~0,15-0,3. dette/K : courbes ordonnées par δ, bosse
  basse-σ partout.
- Diagnostic pop_max : AUCUN run (0/551 exploration+coupes) n'a atteint
  le garde-fou — diagnostic sans objet à ce stade, revérifié en
  confirmation.
- 3 cellules d'interaction ajoutées à la confirmation :
  sigma005_k2, sigma005_delta010, sigma050_k2.
- **Phase confirmatoire lancée** (`scripts/run_confirm.py`) : 16 cellules
  en lots Simulation Lab, graines 11-15 (11-20 pour lam2_ext), T=4000
  (2000 pour lam2_ext), snapshots/100 pas, individual_every=0, marqués
  keep. Manifeste : `manifests/confirm_lab.json`.

## 2026-07-18 (matin) — confirmation dépouillée

85 runs confirmatoires (16 lots lab, ~2,4 h), tous `completed`,
0 anomalie comptable (résidu max 6,8e-16), 0 erreur de carnet,
**0 pop_max atteint sur TOUTE la campagne** (509 runs campagne + 85
runs lab = 594) → diagnostic garde-fou : sans objet, aucune trajectoire
censurée.

- **Contrastes appariés (graines 11-15 vs centre, T=4000)** :
  141 CONFIRMÉS / 19 nuls-cohérents / 3 signe-ok / 5 NON-CONFIRMÉS
  (`results/summary/confirm_contrasts.csv`). Les 5 non-confirmés :
  micro-dépendances de N/λ, deaths_rate, âge en λ (±1-2 %, signes
  instables) → l'intensivité en λ est RENFORCÉE ; coupure à k=2
  (métrique bruitée, variance graines connue).
- **lam2_ext** : 1/10 extinctions, toutes à t=1 (IC95 [0,01;0,38] ∋
  e^-2=0,135) — confirme l'extinction = artefact initial.
- **Lois d'avalanches par cellule (5 graines, fits par graine puis
  agrégés)** (`confirm_laws.csv`) : LRT coupure p≈0 partout (loi
  tronquée >> pure) ; Vuong tous négatifs par graine (log-normale >
  pure) SAUF λ=100 tous positifs (+21) — cohérent avec coupure de
  taille finie sortant de la fenêtre. b=0,29-0,31 hors transition ;
  σ=0 : α=1,80, b=0,647 ; k10 : α=2,43, b=0,237.
- **Scaling de taille** (`confirm_scaling.png`) : susceptibilité ∝
  λ^0,51 ; s_max ∝ λ^0,58 ; ŝ_c ∝ λ^1,5 (10→30), non identifiable à
  λ=100. **Résolution α(λ)** : l'exposant de la loi TRONQUÉE est
  monotone (1,58/2,04/2,31 pour λ=10/30/100) et converge vers la loi
  pure à λ=100 → α∞ ≈ 2,31-2,32 ; la non-monotonie du α pur était un
  artefact d'ajustement.
- **Distributions** (`confirm_gini_renewal.png`, `confirm_ccdf.png`) :
  Gini(t) stationnaire et hiérarchisé (k10≈0,010 < σ0≈0,035 <
  σ010≈0,045 < centre≈0,073 < σ050/k2≈0,13-0,14) ; renouvellement du
  top 1 % complet à 100 pas (recouvrement 0,00) sauf faible persistance
  σ=0 (0,078) et σ=0,10 (0,047) — cohérent avec la durée de vie ;
  aucune dynastie (pas d'héritage dans le modèle).
- **Robustesse fenêtre (confirm)** : pop ≤4 % ; α ≤0,08 ; b ≤0,011
  entre burn-ins T/8-T/2.
- keep vérifié sur les runs lab ; 27 lots dans le lab.

## 2026-07-18 — rapport final compilé, audit indépendant

- Corrections faites après vérification contre les données :
  Spearman âge-K modéré partout (0,15–0,29) et gouverné par k, PAS par
  σ (le marché découple capital et âge — surprise à retenir) ;
  n_tail confirmatoires 4 300–33 000/graine ; N/λ(σ=0,05, δ=0,05)=32,1 ;
  intensivité N/λ jusqu'à λ=2 (λ=1 : 1 seule graine survivante).
- `report/rapport_final.pdf` compilé (23 pages, XeLaTeX), annexe de
  traçabilité 680 entrées (594 runs distincts), 0 référence cassée
  dans les trois PDF.
- **Audit indépendant (sous-agent à contexte frais) : conforme sur les
  8 points** — plans et graines conformes au protocole (LHS régénéré
  depuis la graine 20260717 : identique), séparation
  exploration/confirmation vérifiée sur données, métriques recalculées
  indépendamment (écart 0 sur pop_mean et b, campagne et lab), 0
  « explosion » sur 594 runs, figures tracées jusqu'aux plans sources,
  chiffres clés du rapport final recoupés, condensat moteur recalculé
  identique, 0 book_errors sur 509 runs, 3 PDF recompilés sans
  référence cassée.
## 2026-07-18 — extension NW (demande d'Anatole : « très peu d'infos sur NW »)

Extension post-audit sans nouveau run (`scripts/analyze_nw.py` ;
tables `results/summary/nw_{oat,lhs,confirm,screening,confirm_contrasts}.csv` ;
figures `nw_sensibilite.png`, `nw_structure.png` ; section dédiée dans
rapport_final.tex, recompilé 25 p.) :

- **L'inégalité est dans les bilans** : Gini NW = 0,435±0,006 au centre
  vs Gini K = 0,074. Réponses OPPOSÉES à σ (Gini NW ↓ 0,68→0,42, PRCC
  −0,77 ; Gini K ↑) ; k écrase Gini K (0,14→0,01) mais laisse Gini NW
  PLAT (~0,44) — le marché égalise le stock, pas les positions.
  Mécanisme : queue de créancières (CCDF NW à σ=0 jusqu'à ~4600 J vs
  ~560 au centre) ; le choc tronque l'accumulation.
- **Cycle de vie de la position nette** x=C−D : plongeon initial
  x/K≈−0,85 (emprunt vers K*), remontée, passage créancier ; 62 %
  nettes débitrices au centre (0,59–0,64 partout sauf σ) ;
  Spearman(x, âge)=0,52. NW corrèle à l'âge (0,59) ≫ K (0,28).
- **Invariance du trou d'insolvabilité** : NW médiane au décès / K par
  tête = −0,086±0,002 le long de δ, K0, k, λ ; dépend de σ seul
  (−0,018 / −0,046 / −0,086 / −0,138 pour σ=0/0,1/0,25/0,5). 93,5 %
  meurent en NW<0 au centre ; les 6,5 % à NW≥0 = convention de file
  (annulation de dette par une faillite antérieure de la même file).
- **Canal de liquidité SILENCIEUX** : 0 défaut de service et 0 mort
  « liquidity » post burn-in sur les 594 runs (σ≤0,5) ; s'active à
  σ≥0,85 (0,05–0,19 défaut/pas) et reste <0,4 % des morts. M4B =
  contagion de bilan pure dans les plages d'étude ; seuil d'activation
  σ≈0,85 fourni à M5.
- Contrastes confirmatoires NW (extension post-hoc étiquetée, mêmes
  runs graines 11-15) : 24 CONFIRMÉ / 29 nul-cohérent / 1 signe-ok /
  1 NON-CONF / 15 sans-explo (cellules d'interaction hors axes OAT).
- PRCC (LHS) : gini_nw ← σ −0,77, K0 −0,70 ; nw_median ← δ −0,85,
  K0 +0,90 ; frac_net_debtor ← σ −0,80. R²CV 0,68–0,94.

## 2026-07-18 — extension cycles (demande d'Anatole : périodes croissance/récession)

Extension post-audit sans nouveau run (`scripts/analyze_cycles.py` ;
tables `results/summary/cycles_{oat,lhs,confirm,screening,confirm_contrasts}.csv` ;
figures `cycles_sensibilite.png`, `cycles_structure.png` ; section
« Cycles de l'activité » dans rapport_final.tex, recompilé 29 p.).
Définitions figées : épisodes = suites maximales de même signe de
Δlog(prod_tot) ; taille temporelle (durée) et indicielle (amplitude
log) ; fenêtre [T/4, T] ; lissages w ∈ {1,5,25} ; nulle i.i.d. : durée
moyenne 2, CCDF géométrique.

- **Phases courtes, jamais longues** : centre 487±7 épisodes/1000 pas
  (cycle complet 4,1 pas), durées moyennes 2,11/2,00, max 10-13 sur
  3000 pas ; CCDF sous la référence géométrique (antipersistance).
- **Volatilité** : sd(Δlog) ← σ (+0,97) et K0 (−0,81), R²CV 0,985 ;
  ∝ λ^−0,50 (mesuré exactement −0,50) ; **minimum intérieur à σ≈0,1**
  (0,0119 vs 0,0131 à σ=0 et 0,0366 à σ=0,5) = frontière bruit
  endogène (avalanches) / exogène (chocs).
- **Asymétrie de krach** (skew Δlog toujours <0) : −0,83 à σ=0 →
  −0,17 à σ=0,5 ; récessions plus courtes (1,62 vs 2,01 pas à σ=0) et
  plus raides (pente r/e 1,24 à σ=0, 1,06 centre) ; ACF1 −0,16 (σ=0)
  → +0,05, croisement à σ≈0,15 (= la transition de propagation) ;
  effet de taille finie (skew −0,46 à λ=10, −0,20 à λ=100).
  PROPRIÉTÉ D'ÉCHELLE BRUTE : disparaît à w=25 (pente r/e → 1,00) —
  origine avalanches intra-pas.
- **Horloge démographique** : τ_int(log prod) suit N/λ (Spearman 0,93
  sur 13 cellules, rapport 1,2–1,8) — pendant temporel de la loi de
  Little. Centre 23,5±0,6 pas ; σ=0 : 43,5 ; σ=0,5 : 11,6.
- Multi-échelle : cycle moyen 9-10 pas (w=5), 12-19 (w=25, max près du
  centre) ; exposant amplitude-durée 1,7-1,8 (descriptif, PAS un Hurst).
- Contrastes (graines 11-15, post-hoc étiqueté) : 33 CONFIRMÉ /
  49 nul-cohérent / 6 discordants mineurs / 24 sans-explo.
- PRCC notables : acf1 ← σ +0,71, k +0,48 ; τ_int ← σ −0,88 ;
  skew ← σ +0,59 (R²CV 0,45 — métrique bruitée).

- **UN ÉCART corrigé** : les rapports annonçaient « 5 extinctions »
  sur la carte λ ; les données en montrent 9/45 (graines 2-3 à λ=1 et
  graine 3 à λ=2, identiques pour chaque σ — l'événement ne dépend que
  du premier tirage de Poisson, donc 3 événements de graine
  indépendants). Corrigé dans rapport_preliminaire.tex et
  rapport_final.tex ; conclusion inchangée (artefact d'amorçage,
  fréquences compatibles e^-λ). Abstract précisé aussi (3 signe-ok +
  5 non confirmés au lieu de « 8 non confirmés »). Les deux PDF
  recompilés (15 et 23 pages, 0 réf. cassée).

## 2026-07-27 — contrôle des récessions sur l'énergie totale

À la demande d'Anatole, la définition principale d'une récession pour
la validation du toy-model devient une baisse de l'énergie totale présente
\(E_t=\sum_iK_i(t)\), mesurée en fin de pas. Extension de
scripts/analyze_cycles.py sans nouveau run : le protocole historique sur
prod_tot est conservé, et toutes les métriques sur K_tot sont ajoutées avec
le préfixe energy dans les cinq tables de cycles.

- **Centre, cinq graines, fenêtre de 3 000 pas** : 252,4±4,4 récessions
  par millier de pas ; durée 1,930±0,042 pas contre 2,035±0,033 pour
  les expansions ; maxima de durée 10–11 pas.
- **Amplitude pic–creux** : moyenne logarithmique 0,0361±0,0007
  (baisse représentative 3,5 %), quantile 90 moyen 0,0778 (7,5 %) ;
  plus grande baisse des cinq graines 0,259 en log, soit environ 23 %.
- **Asymétrie** : raideur récession/expansion 1,055 au centre ;
  skewness des accroissements −0,233±0,021.
- **Screening LHS** : amplitude moyenne pilotée par σ (PRCC +0,983) et
  K0 (−0,801), R²CV 0,989 ; fréquence sans contrôle paramétrique robuste
  (R²CV −0,032) ; mémoire de log(K_tot) pilotée négativement par σ
  (PRCC −0,900), 23,2±1,4 pas au centre.
- **Taille finie** : amplitude moyenne 0,0633 à λ=10, 0,0361 à λ=30 et
  0,0196 à λ=100 dans les cellules confirmatoires.
- Les tableaux régénérés comptent 66 lignes OAT, 192 LHS et 75
  confirmatoires. Le screening contient désormais 16 métriques et les
  contrastes 224 lignes. Les figures historiques restent centrées sur
  prod_tot ; une figure énergétique dédiée reste à produire.
