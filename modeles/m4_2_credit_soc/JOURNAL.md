# Journal de recherche M4.2

Chronologique. Chaque entrée : date, faits (avec chiffres), décisions et raisons.
Cahier des charges : `prompts/PROMPT_M4_2.md`. Moteur : `m4_2/`.

## 2026-07-27 — Implémentation du moteur et parité M4B

**Contexte.** Démarrage de la mission M4.2 (successeur de M4B, production
généralisée F_γ(K) = A·K^γ, question : la pente τ des avalanches est-elle
pilotable par γ ?). Plan approuvé par Anatole. Décisions utilisateur en
session : (1) les runs de campagne seront tous visibles dans Simulation Lab,
les 28 figures M4B n'étant générées que pour les runs confirmatoires et les
cellules centrales ; (2) `prompts/PROMPT_M4_2.md` est le document d'autorité.

**Moteur écrit** (`m4_2/model.py`, `m4_2/io.py`, `run.py`) — copie adaptée
ligne à ligne de `modeles/m4b_credit_soc_mini/m4b/` (diffable). Changements
constitutifs : gamma et A dans la Config (validés 0<γ<1, A>0, défauts
γ=0,5, A=1, λ=30) ; k retiré de la Config (POOL_SIZE=2 constitutif) ;
fonction η(N)=N nommée et instrumentée (colonnes series : mkt_pool,
mkt_rounds, mkt_new_edges, mkt_merges ; invariant new_loans = new_edges +
merges) ; `_pair_terms` généralisé m=A·γ·max(K,K_FLOOR)^(γ-1),
r=√(m_ℓ·m_b), K*=(A·γ/r)^(1/(1-γ)) ; production A·K^γ ; choc renommé ξ.
Écart voulu vs M4B, documenté : aucun round de marché si le pool < 2 —
suit la prose de PROMPT_M4_2.md:259-260 (qui contredit la formule
R_t=⌊η(N)⌋ à N=1 ; le code suit la prose). L'audit du 27/07 a montré que
`numpy.permutation(1)` ne consomme aucun état RNG : les rounds stériles
de M4B à n=1 étaient donc déjà neutres — les deux conventions sont
équivalentes en dynamique, seul le compteur mkt_rounds diffère.
MODEL_VERSION = "m4_2-1". Schéma de sorties = M4B + 4 colonnes (condition
de réutilisation des 28 figures Simulation Lab).

**Fait observé — runs de fumée** (T=200, seed 1, λ=30 par défaut) :
statut ok aux trois γ testés, book_errors=[]. Population à t=200 :
γ=1/3 → 657 ; γ=1/2 → 509 ; γ=2/3 → 269. Cohérent avec la prédiction
dimensionnelle m(K*_aut) = γ·δ/(1-δ) : service d'intérêts relativement
plus lourd à grand γ → vies plus courtes. (Exploratoire, une graine.)

**Fait observé — tests** (`tests/test_engine.py`, 18 tests, tous OK) :
dérivée, K*=√(K_ℓK_b) (tol 1e-12, y compris A≠1), encadrement strict des
taux, conservations au prêt, fusion et flux d'intérêts, k absent de la
config, η(0)=0/η(1)=1 sans consommation RNG, compteurs distincts sur
scénarios forgés, invariants du carnet, cascade forgée à 2 générations
(taille 2, profondeur 2, volume 18 J exacts), reproductibilité par graine
(octets identiques), neutralité des options d'enregistrement, bilan
ΔK=I+G+P−Δ−X à γ=0,4 et 0,65 (tol 1e-6), point fixe autarcique
K*_aut=((1-δ)A/δ)^(1/(1-γ)) atteint à 1e-9 relatif pour γ∈{1/3,1/2,2/3}.

**Fait observé — parité γ=1/2 vs M4B k=2** (`tests/test_parity_m4b.py`) :
discret identique (naissances, morts, contrats, causes, avalanches,
compteurs) sur les deux régimes de gating (seed 0, λ=10, 120 pas ;
seed 7, λ=18, 90 pas) ; écart flottant max 5,7e-13 et 3,0e-13 (tolérance
1e-9). Sonde longue seed 1, λ=30, T=1000 : aucune divergence discrète,
écart flottant max des séries 3,1e-12. Inférence : les formes génériques
(pow) et M4B (sqrt) coïncident presque partout à l'ULP près et l'écart ne
s'amplifie pas en bifurcation discrète sur 1000 pas dans ce régime. La
parité est donc établie et bornée ; pas de branche de compatibilité.
(Source de l'écart identifiée par l'audit : `K**0.5` diffère de
`math.sqrt(K)` d'1 ULP sur ~0,1 % des valeurs.)

**Audits en contexte frais (27/07)** — deux agents indépendants :
- *Fidélité au cahier des charges* : moteur FIDÈLE, aucun bug ; diff vs
  m4b/model.py entièrement classé en changements voulus ; Population,
  LoanBook, _fail_one, _build_avalanches, _resolve_bankruptcies octet
  pour octet identiques à M4B ; chasse aux bugs (indices de pool, merges
  avant add, due=0, ordre RNG, floor η, bords γ) : tous négatifs.
- *Invariants comptables* (run γ=0,6, λ=20, seed 5, T=300 + cas forgés) :
  bilan exact à l'arrondi (résidu max 1,3e-11/pas), Σclaims=Σdebts
  (1,5e-11), nw_tot=K_tot (1,5e-11), Σvolume_j=claim_losses (9e-12),
  carnet incrémental vs reconstruit ≤1,5e-12 après 300 pas. Deux legs
  M4B documentés (pas corrigés, pour la parité) : puits de dépréciation
  ZERO_TOL (≤1e-12/entité planchée, 0 déclenchement en régime normal) et
  clés d'agrégats jamais purgées (mémoire O(naissances), sans effet).
Corrections appliquées : spec_m4_2.tex (formule R_t par cas, conventions
de résolution C1-C5, fuites d'arrondi mesurées), commentaire _run_market.

**Écrits également** : scripts/lib_metrics.py (copie adaptée : s_min
paramétrable, scan CSN fit_tail_discrete intégré, bootstrap (τ,s_c,s_min)
n=200, métriques η), scripts/lib_screening.py (copie), tests/test_stats.py
(6 tests estimateurs sur synthétique, tous OK en 20 s : biais τ<0,05,
récupération (τ,s_c), sélection s_min implanté, LRT/Vuong cohérents,
bootstrap couvrant), report/spec_m4_2.tex+pdf (8 p.),
report/protocole.tex+pdf (6 p., version 1 figée avant tout run de
campagne ; audit statistique en cours).

**Audit mathématique de la spec (27/07)** : toutes les dérivations
CORRECTES (K*=√(K_ℓK_b) vérifié à 1,4e-15 ; raison de convergence
1−δ(1−γ) ; identités dimensionnelles ; A_norm=19^(1-2γ)). Deux coquilles
corrigées dans la table du point fixe : 82,8 (γ=1/3, pas 83,0) et 135,3
(γ=0,4, pas 135,1). Ajout de "phase_order" à FIXED_RULES (io.py) pour que
config.json enregistre l'ordre des phases comme la spec l'affirmait.
Tests relancés après retouches : 18+2 OK.

**Intégration Simulation Lab (27/07)** : adaptateur
modeles/adaptateurs/m4_2_credit_soc/ (model.py, figures.py,
reporting.py — copie M4B, taux marginal généralisé A·γ·K^(γ-1) lu depuis
config.json, reporting.py:462) ; "m4_2_credit_soc" ajouté à
ACTIVE_MODEL_IDS (simulation_lab/settings.py:16, seule modif hors dossiers
neufs). Paramètre bool `figures` (défaut True ; False = pas de
post-traitement, trajectoires inchangées). Smoke tests : run γ=0,65
T=400 → 31 figures dont internal_rate_evolution.png correcte (r* médian
0,088-0,094 ≈ 0,65·K^-0,35 à K≈300 J) ; run figures=false OK.

**Fait observé (smoke, exploratoire)** : à γ=0,65, T=400, λ=30 :
N/λ=9,7 (vs ~14,8 à γ=0,5 k=3 dans M4B), α_pur=2,23, α_tronc=1,97,
s_c=39, b=0,317, singletons 72 %, taux de succès des rounds 1,00 (presque
chaque tentative produit un prêt à k=2), part de fusions 2 %.

**Orchestration de campagne (27/07)** : scripts/lib_lab.py (condensat
moteur, cell_id SHA-256, lancement cli batch, index global de reprise
cells_index.json), run_campaign.py (cellules en parallèle, budget
cell_workers×parallel_cells ≤ 6), make_plans.py (6 plans :
benchmark 2, pilotes 6, taille_finie 15 — cellules λ=30 partagées avec
les pilotes par cell_id —, horizon_double 3, ablation_A 2, mecanisme 5 ;
plan confirm généré après pilotes), extract_metrics.py (→
results/metrics/<run_id>.json, option --bootstrap), analyze_pilotes.py
(diagnostics go/no-go pré-enregistrés). Pipeline de métriques validé de
bout en bout sur le run smoke. Volet 0 (benchmark de coût) lancé.

**Audit du protocole statistique (27/07, agent indépendant)** : verdict
« solide et pré-enregistrable, mais à ne pas lancer en l'état ». Puissance
validée par calcul (SE(τ̂)/run ≈ 0,01, variance décisionnelle
inter-graines ; Δτ≈0,2-0,3 détectable à 5 graines, 0,1 rattrapé par
l'extension à 10). Corrections appliquées AVANT le volet 1 →
**protocole v1.1** (recompilé, 7 p.) :
1. convention « s_c hors portée » (ŝ_c>10·s_max → drapeau
   s_c_out_of_range + tau_hat lu sur la pure) implémentée dans
   compare_laws — elle n'existait que dans le texte ;
2. conditions de confirmation 2/4/5/7 chiffrées (persistance ≥ ½ à
   λ=100 ou IC excluant 0 ; cohérence de signe du scan + profil de
   vraisemblance à coupure commune ré-attribuant ≥ 50 % de l'effet —
   nouvelle fonction fit_powerlaw_cutoff_fixed_sc ; LRT p<0,05 ou hors
   portée avec Vuong z>2, jamais log-normale préférée ; combinaison en
   quadrature inter-graines ⊕ bootstrap) ;
3. bootstrap obligatoire pour l'extraction confirmatoire ;
4. limites documentées : estimation (τ,s_c,s_min) décomposée et non
   jointe (justifiée), min_tail=50 du scan, bootstrap iid intra-run,
   LRT anticonservateur (~15 % de faux positifs « coupure » mesurés sur
   pures, direction bénigne), fenêtres emboîtées, Student df=4 ;
5. clause de complétude (arbre partitionnant confirmé/infirmé/partiel).
test_stats étendu à 8 tests (hors-portée + profil s_c fixé), tous OK.

**Volet 0 — benchmark (27/07, manifests/benchmark.manifest.json)** :
γ=1/3 → 291 s/run ; γ=2/3 → 166 s/run (T=4000, λ=30, graine 1).
Plus lent à petit γ (population plus nombreuse attendue). Aucun run
au-dessus du seuil de re-budget (30 min). Budget des volets inchangé.

## 2026-07-27 — Volet 1 : pilotes (EXPLORATOIRE, graines 1-3)

16 runs (5 γ × 3 graines + sonde γ=0,75), 812 s wall. **Tous GO** aux
critères pré-enregistrés : statuts ok 16/16, stationnarité 16/16,
identifiabilité massive (10 200 à 11 500 avalanches s≥2 par run — 100×
le seuil). Même la sonde γ=0,75 est stationnaire à T=4000 (la crainte du
transitoire ne se matérialise pas : K/tête=902 ≪ K*_aut=130 321 — le
crédit et la mortalité maintiennent le capital loin de l'échelle
autarcique). **Décision de grille (clause adaptative)** : grille
inchangée, les 5 γ retenus pour le volet 2 ; aucun amendement nécessaire.

Faits observés (fenêtre T/4, moyenne±sd inter-graines,
results/tables/avalanches_cells.csv) :
- **τ̂ (tronqué, primaire) dépend de γ, non monotone** :
  1,894±0,022 (γ=1/3) → 1,969±0,016 (0,4) → 1,990±0,032 (1/2) →
  2,028±0,007 (0,6) → 1,992±0,016 (2/3) ; sonde 0,75 : 1,947 (1 graine).
  Contraste g033−g050 ≈ −0,10 (3-4× le sd inter-graines) ; g060−g050 ≈
  +0,04 ; maximum g033 vs g060 ≈ 0,13. Stabilité aux fenêtres T/8-T/2 :
  ±0,005 (fenêtres emboîtées — contrôle faible, cf. protocole).
- **b quasi invariant** : 0,307-0,319 sur toute la grille (H2 tenue en
  exploration — le rapport de branchement reste institutionnel).
- s_c : 57,6 / 62,7 / 51,9 / 52,3 / 47,6 / 43,3 — variation modérée,
  non monotone ; jamais hors portée.
- Démographie (H3 confirmée en exploration) : N/λ = 22,0 / 19,5 / 15,4 /
  11,5 / 9,2 / 6,9 — décroissance forte et monotone en γ.
- K/tête : 52,6 → 901,7 (toujours ≪ K*_aut dès γ≥0,5).

Interprétation prudente (exploratoire) : signal de pente réel à petit γ
(vers τ̂ plus faible = queues plus lourdes), plateau/repli au-delà de
γ=0,6. Confusions possibles à trancher : taille de population (N varie
avec γ à λ fixé — le volet 2 λ∈{10,100} sépare), coupure (s_c bouge peu),
échelle (volet 5 A_norm). Volets 2-3 lancés dans la foulée.

## 2026-07-27 — Volets 2-3 : taille finie et horizon (EXPLORATOIRE)

taille_finie : 30 nouveaux runs (λ=10 T=8000, λ=100 T=4000 ; λ=30 réutilisé
par cell_id), 56 min wall. horizon_double : 9 runs T=8000, 22 min. 0 échec,
0 censure, stationnarité partout. Tables : results/tables/avalanches_*.csv.

Faits observés (fenêtre T/4, fits par graine) :
- **Contraste principal γ=1/3 vs 1/2 : même signe aux trois tailles** :
  Δτ̂ = −0,198 (λ=10) ; −0,096 (λ=30) ; −0,078 (λ=100). À λ=100 la coupure
  est hors portée 3/3 (ŝ_c sature la borne e²⁰ de l'optimiseur — drapeau
  s_c_out_of_range levé, τ̂ lu sur la loi pure, conformément au protocole)
  et les sd inter-graines sont minuscules (0,002-0,008).
- **Non-monotonie reproduite aux trois tailles** : λ=10 : 1,389/1,439/
  1,587/1,564/1,525 ; λ=30 : 1,894/1,969/1,990/2,028/1,992 ; λ=100 :
  2,212/2,251/2,290/2,302/2,292 (pur). Pic vers γ=0,5-0,6, repli à 2/3.
  Contraste g067−g050 ≈ 0 à λ≥30 (−0,062 à λ=10).
- **b ∈ [0,299 ; 0,320] sur les 19 cellules** — plateau institutionnel du
  branchement robuste à γ ET λ (H2 tenue).
- Horizon doublé (λ=30, T=8000) : g033−g050 = −0,105 (vs −0,096 à
  T=4000) ; g067−g050 = −0,017 (vs +0,002) — contraste principal stable,
  contraste nul stable dans le bruit.
- s_c à λ=10 ≈ 10 (troncature sévère) ; à λ=30 ≈ 48-63.

**Décisions pré-confirmation (datées, avant tout run du volet 4)** :
1. Contrastes confirmatoires : g033 et g067 (extrêmes pré-enregistrés)
   + **g060** (pic de la relation — extension identifiée comme
   confirmatoire, décidée sur les diagnostics exploratoires, évaluée avec
   les critères pré-enregistrés inchangés).
2. Pas de bras λ=100 en confirmation : la clause ne se déclenche pas
   (même signe, même ordre de grandeur entre λ=30 et λ=100).
3. Ablation A_norm étendue à g060_Anorm (contrôle d'échelle du pic),
   A_norm(0,6)=19^(-0,2)≈0,555 — décision datée avant les runs du volet 5.

**Maillons mécanistiques (λ=30, exploration, observables_cells.csv)** :
taux médian du carnet 0,024→0,130 entre γ=1/3 et 0,75 (systématiquement
2-3× au-dessus de γδ/(1-δ) : les contrats se signent entre entités bien
sous K*_aut) ; intérêts/production 0,45→0,77 ; âge au décès 22,0→6,8 ;
contrats/tête 10,7→4,2 ; D/K 1,38→0,98 ; fusions ~2 % ; **0 mort par
liquidité partout** (canal silencieux, comme M4B σ=0,25 : contagion de
bilan pure — le levier γ agit par redistribution des flux d'intérêts,
pas par défaut de service).

**Argument anti-artefact démographique (inférence)** : à γ fixé, τ̂ croît
avec N (g050 : 1,587/1,990/2,290 pour λ=10/30/100). À λ=30, g033 a
N≈660 > N≈462 (g050) : un pur effet de taille pousserait τ̂(g033) VERS LE
HAUT ; on observe l'inverse (−0,096). Le confound démographique joue
contre l'effet observé, qui est donc au pire sous-estimé. Pas de contrôle
apparié en N nécessaire.

## 2026-07-27 — Volets 4-6 exécutés ; ablation : l'effet est un effet d'ÉCHELLE

confirm : 4 cellules × 5 graines {11-15}, keep+figures, 37 min.
ablation_A : 3 cellules × 3 graines, 12 min. mecanisme : 5 runs denses,
11 min. Campagne totale : 106 runs, 0 échec, 0 censure.

**Fait observé — ablation A_norm (results/tables/ablation_A.csv,
graines appariées 1-3)** :
- γ=1/3 : effet total Δτ̂=−0,096 ; effet résiduel à échelle autarcique
  égalisée **+0,049 (signe inversé)** ; part d'échelle −0,145. La
  démographie suit le même schéma (ΔN/λ : total +6,6 → résiduel +1,3).
  Le taux médian, lui, reste plus bas à γ=1/3 même à échelle égalisée
  (−0,017, cohérent avec m(K_ref)=γ·δ/(1-δ) linéaire en γ : la courbure
  garde son effet propre sur les taux, mais cet effet ne pilote PAS τ̂).
- γ=2/3 : total +0,002, résiduel −0,008 (nuls tous deux, cohérents).

**Inférence (conforme au critère 8 pré-enregistré)** : la conclusion
« γ pilote τ̂ » doit être requalifiée — γ est un levier EFFICACE de τ̂ à
A=1, mais le canal causal est le changement d'échelle du point fixe
K*_aut(γ), pas la concavité elle-même. À courbure variable et échelle
fixe, τ̂ ne bouge presque pas (voire légèrement en sens inverse).

**Hypothèse structurelle issue des mesures (datée, AVANT ses runs)** :
les cellules d'ablation épinglent à la fois K*_aut (=361 J) et le rapport
sans dimension K0/K*_aut (=0,069, celui du centre) — et l'effet disparaît.
Candidat le plus simple : **τ̂ est piloté par K0/K*_aut** (taille relative
des nouveau-nées). Valeurs à A=1 : 0,301 (γ=1/3) ; 0,185 (0,4) ; 0,069
(1/2) ; 0,016 (0,6) ; 0,0036 (2/3) ; 0,0002 (0,75). Test décisif SANS
toucher γ : à γ=1/2, A=1 (K*=361), varier K0 pour reproduire les
rapports extrêmes — K0=108,7 (ratio 0,301, prédiction τ̂≈1,89 si
l'hypothèse est vraie) et K0=1,31 (ratio 0,0036, prédiction τ̂≈1,99,
c'est-à-dire quasi inchangé vu la saturation). Plan « hypothese_K0 »,
3 graines {1,2,3}, T=4000, λ=30 — expérience ciblée exploratoire,
critères de lecture : signe et amplitude du contraste apparié vs centre,
mêmes fits pré-enregistrés.

**Fait observé — test K0/K* (27/07, plan hypothese_K0, 6 runs)** :
- k0_match_g033 (γ=1/2, K0=108,7, rapport 0,301) : τ̂ = 1,893 ± 0,022 —
  reproduit la cellule γ=1/3 (1,894 ± 0,022) à 0,001 près, SANS toucher
  γ. N/λ = 20,5 (γ=1/3 : 22,0) : la démographie suit aussi.
- k0_match_g067 (γ=1/2, K0=1,31, rapport 0,0036) : τ̂ = 2,042 ± 0,013 ;
  N/λ = 9,65 (γ=2/3 : 9,2). τ̂ est au-dessus de la cellule γ=2/3
  (1,992 ± 0,016) de ~0,05 (≈3 sd).

**Inférence centrale** : la pente des avalanches est pilotée par la
combinaison adimensionnelle K0/K*_aut (taille relative des nouveau-nées),
pas par la concavité : le flanc bas de la relation τ̂(γ) est reproduit
exactement par K0 seul à γ fixé, et sur l'axe K0 pur la relation
τ̂(rapport) est monotone (1,893 @0,301 → 1,990 @0,069 → 2,042 @0,0036).
La non-monotonie observée sur l'axe γ (repli au-delà de 0,6) est la part
résiduelle de la courbure (~−0,05, cohérente avec le résiduel d'ablation
γ=2/3 et la sonde 0,75). γ reste un LEVIER efficace de τ̂ à A=1, mais son
canal causal dominant est K0/K*_aut(γ).

## 2026-07-27 — Volet 4 : verdicts confirmatoires (graines 11-15)

`scripts/analyze_confirm.py` exécuté sur les 4 contrastes confirmatoires
× 8 conditions pré-enregistrées (protocole v1.1). Extraction --bootstrap
obligatoire (20 runs) : effectuée avant tout calcul de verdict.

**Contraste g033 (γ=1/3) vs g050 (centre)** : Δτ̂=−0,125, IC95
[−0,135;−0,115], n=5 — le plus net. PASS : 1 (IC apparié), 2 (persiste à
λ=100, exploration), 3 (fenêtres+horizon doublé stables), 4a (scan même
signe), 6 (stationnaire), 7 (excède l'incertitude combinée). FAIL : 8
(ablation — voir ci-dessous). Condition 5 (famille défendable) échoue
LITTÉRALEMENT partout — voir avertissement méthodologique ci-dessous.

**Contrastes g060 et g067** : effets petits (+0,021 et −0,018),
IC-significatifs mais fragiles : g060 échoue 4,5(lit.),7,8 (persistance
λ=100 marginale, non-N/A) ; g067 échoue la persistance à λ=100
(exploration : +0,002, IC∋0), 4,5(lit.),7. **Aucun des deux ne survit à
la robustesse complète** — le "pic" à γ=0,6 vu en exploration est
statistiquement fragile, probablement en grande partie bruit/interaction
coupure-graine.

**Erratum méthodologique découvert en confirmation (condition 5)** : le
Vuong disponible (`vuong_pl_vs_ln`) compare la loi PURE au log-normal —
or la loi pure est rejetée par LRT partout avec p<10⁻³³ (tronquée
strictement nécessaire, comme dans M4B). Ce Vuong échoue donc
IDENTIQUEMENT en cellule ET en centre (z=−5,5 à −7,2 partout, 20/20
runs) : non différentiel, donc non informatif contre un contraste
spécifique. Diagnostic correctif ajouté (comparaison directe des
vraisemblances tronquée vs log-normale, 2 paramètres chacune, donc
comparable sans test dédié) : la tronquée domine le log-normal de 54 à
77 unités de log-vraisemblance dans TOUS les runs confirmatoires — la
famille est massivement défendable ; l'échec de la condition 5 littérale
est un artefact d'outillage (mauvaise paire de modèles comparée par
Vuong), pas une preuve contre les contrastes. Le code (comportement) n'a
PAS été modifié rétroactivement pour faire passer la condition — le
diagnostic correctif est additif et documenté, la lecture littérale
reste rapportée.

**Extension confirmatoire de l'ablation (clause pré-écrite protocole
§volet 5)** : g033 étant le contraste principal confirmé (au sens des
conditions 1,2,3,6,7), son ablation est répétée sur les graines 11-15
(`ablation_A_confirm`, 5 runs, cell hors plans standards mais tracée dans
l'annexe). **Résultat décisif** : effet résiduel à échelle égalisée
Δτ̂=+0,031, IC95 [+0,001;+0,061], n=5 — SIGNIFICATIF et de SIGNE INVERSÉ
par rapport à l'effet total (−0,125). Confirme exactement le résultat
d'exploration (+0,049, 3 graines). **Verdict scientifique final sur le
contraste g033** : l'effet de γ=1/3 sur τ̂ à A=1 est réel, robuste,
massivement significatif — mais sa cause dominante est le déplacement du
point fixe autarcique K*_aut(γ) (effet d'échelle), pas la concavité en
tant que telle. À échelle égalisée, la courbure a un effet résiduel
petit et de sens OPPOSÉ (légèrement moins de traînes lourdes à γ plus
faible, à échelle fixée). Condition 8 (protocole) échoue donc à bon
droit — c'est elle qui révèle cette décomposition, pas un défaut de la
grille de test.

**Réponse à la question ouverte de la mission (état final, avant audit —
voir corrections ci-dessous)** : γ seul (à A=1) pilote τ̂ de façon
mesurable, mais PAS par la concavité — par le rapport adimensionnel
K0/K*_aut(γ,A) qu'il fait varier sur deux décades. b reste épinglé
institutionnellement. [Note : l'affirmation "canal silencieux partout /
0 mort par liquidité" a été trouvée FAUSSE par l'audit de traçabilité —
voir entrée du 29/07 ci-dessous.]

## 2026-07-29 — Reprise après coupure de courant ; deux audits finaux
## indépendants ; corrections substantielles au rapport

Session interrompue par une coupure de courant le 27/07 après le calcul
de l'ablation confirmatoire g033_Anorm_confirm (résultat déjà obtenu :
résiduel +0,031, IC95 [+0,001;+0,061], graines 11-15). Reprise le 29/07 :
état vérifié intact (95 fichiers de métriques, 20 avec bootstrap, tous
manifestes présents). Rapport préliminaire, rapport final et resume.md
rédigés une première fois, puis soumis à deux audits indépendants en
contexte frais (traçabilité des chiffres ; confrontation des
conclusions). **Les deux audits ont trouvé des problèmes réels**,
au-delà de la simple validation — conformément à la consigne du prompt
de ne pas se contenter d'un vérificateur qui reformule.

**Corrections appliquées (par gravité) :**

1. **Terminologie « confirmé » erronée (trouvé indépendamment par les
   DEUX audits)** — mon propre `analyze_confirm.py` rend le verdict
   `PARTIEL/INDÉTERMINÉ` pour les 3 contrastes (échec des conditions 5
   et/ou 8), mais le texte des rapports employait « confirmé » comme si
   le verdict machine était CONFIRMÉ. Corrigé partout (rapport_final,
   resume.md, rapport_preliminaire) : le mot « confirmé » n'est plus
   utilisé que pour un contraste dont les 8 conditions passent
   (aucun cas dans cette campagne) ; le contraste γ=1/3 est décrit comme
   satisfaisant 6/8 conditions, avec l'échec de la condition 8 mis en
   avant comme LE résultat scientifique (pas un défaut de robustesse).

2. **Affirmation « 0 défaut de service / canal silencieux partout » —
   FAUSSE** (audit traçabilité). Recompte exact sur la série complète de
   chaque run : **17 événements de défaut distincts sur 102 runs
   distincts**, exclusivement à γ∈{2/3, 0,75} (2 au benchmark, 3 à
   l'horizon doublé γ=2/3, 2 au mécanisme γ=2/3, 3 aux pilotes γ=2/3,
   4 à la sonde γ=0,75, 3 à taille_finie λ=100 γ=2/3) — **jamais** à
   γ≤0,6, jamais dans les 20 runs confirmatoires. Corrigé partout : le
   canal est requalifié "quasi silencieux, pas rigoureusement nul",
   avec l'interprétation (cohérente avec le mécanisme mesuré) que le
   canal s'éveille précisément où le service devient relativement plus
   lourd — un signal physique, pas un artefact à cacher.

3. **Erreur de facteur 10** : K0/K*_aut à γ=2/3 est 25/6859 =
   **0,0036448**, pas 3,6e-4 comme écrit partout initialement. Corrigé.
   "Deux décades" reste vrai une fois corrigé (log10(0,301/0,00364)=1,92).

4. **Cellule g060_Anorm exécutée mais omise du pipeline d'ablation**
   (audit traçabilité) : `analyze_ablation_A.py` avait `for name in
   ("g033","g067")` en dur, alors que le JOURNAL du 27/07 documentait
   la décision d'étendre à g060. Corrigé (ajout de "g060"), rerun :
   résultat cohérent avec la thèse (total +0,038, résiduel −0,006,
   part d'échelle +0,044) — la cellule omise renforçait la conclusion,
   ce n'était pas un tri sélectif, mais une négligence de pipeline à
   corriger quand même.

5. **Bug de précédence Python dans `analyze_confirm.py` (condition 4)** :
   `f"A" if cond else "B" + (X if Y else Z)` se parse `A if cond else
   (B+(...))`, donc le détail du profil à coupure commune disparaissait
   silencieusement chaque fois que le scan existait (cas normal). Le
   STATUT (PASS/FAIL) était néanmoins calculé correctement
   (`scan_ok and prof_ok`, tous deux corrects) — seul l'affichage était
   tronqué. Corrigé : recalcul et affichage explicites des deux
   sous-tests. Résultat pour g033 : profil à coupure commune Δτ̂=−0,131
   (104 % de l'effet total réattribué à la pente, même signe) — plus
   fort que ce que le rapport initial laissait paraître (il ne citait
   que le scan CSN, −0,043, 34 % de l'effet).

6. **Test de Vuong "condition 5" invalide** : `vuong_pl_vs_ln` compare
   la loi PURE (rejetée par LRT partout, p<4e-33) au log-normal —
   comparaison non informative sur le modèle primaire (tronqué), de
   plus doublement invalide (support infini pour la pure vs fini pour
   le log-normal). Corrigé en profondeur (pas juste documenté) :
   nouvelle fonction `lib_metrics.vuong_trunc_vs_ln` (tronquée vs
   log-normale, même support fini, statistique de Vuong proprement
   normalisée) remplaçant le diagnostic brut "Δloglik" initial (qui
   confondait pénalité de complexité neutralisée et variabilité
   d'échantillonnage non traitée). Résultat : z=+16 à +19 dans tous les
   runs confirmatoires — la conclusion "famille massivement défendable"
   tient, mais est maintenant étayée par un vrai test statistique.
   Testé sur données synthétiques (`test_vuong_trunc_vs_ln_prefers_
   generating_family`, n=20000 pour matcher l'échelle réelle des runs —
   à n modeste, tronquée et log-normale peuvent être statistiquement
   proches, fait noté mais non alarmant vu la taille réelle des runs).

7. **Résultat 3 (test K0) présenté avec une précision fictive** — LA
   correction la plus substantielle (trouvée par l'audit conclusions).
   J'avais écrit "écart 0,001, reproduit exactement" en utilisant
   l'écart-type de CHAQUE CELLULE (~0,022) comme s'il mesurait la
   précision de la COMPARAISON, alors que le contraste apparié correct
   (par graine, comme partout ailleurs dans cette campagne) a un
   écart-type de 0,039-0,057, donnant des IC95 de largeur ≈±0,1 —
   du même ordre que l'effet total (−0,125) que le test est censé
   expliquer. Recalculé rigoureusement (paired par graine, n=3) :
   contraste γ=1/3 = +0,0010 IC95 [−0,096;+0,098] (∋0) ; contraste
   γ=2/3 = −0,0499 IC95 [−0,114;+0,014] (∋0). **Les deux sont
   statistiquement indiscernables de zéro.** Le rapport final est
   réécrit : l'hypothèse K0/K*_aut est corroborée dans sa partie
   NÉCESSAIRE (conséquence prouvée de l'invariance d'échelle exacte,
   voir point 9) mais sa partie empirique (résidu propre de courbure à
   rapport fixé) reste NON TRANCHÉE à cette précision — un panel plus
   large est nécessaire, laissé pour une extension future. Le
   raisonnement "cohérent avec le résidu d'ablation" est signalé comme
   asymétrique (utilisé pour excuser l'écart γ=2/3 mais ignoré pour le
   non-écart γ=1/3, où le même raisonnement prédirait +0,03 à +0,05 non
   observés) — noté explicitement dans le rapport plutôt que masqué.

8. **117 vs 102 runs** : 117 = nombre de lignes non dédupliquées dans
   les manifestes (chaque cellule liste ses run_ids ; les 15 cellules
   λ=30 partagées entre pilotes et taille_finie par cell_id apparaissent
   dans les deux manifestes). 102 = runs Simulation Lab réellement
   distincts (vérifié : `len(set(tous les run_ids)) == 102`). Corrigé
   partout : "117 exécutions de cellule (102 runs distincts, 15
   partagés)".

9. **Renforcement scientifique ajouté (recommandé par l'audit
   conclusions, pas une correction d'erreur)** : démonstration de
   l'**invariance d'échelle exacte** de la dynamique discrète sous
   (K,K0,A)→(cK,cK0,c^(1-γ)A) — vérifiée empiriquement par l'auditeur à
   1,2e-11 relatif sur γ∈{1/3,1/2,0,6,2/3}, c∈{0,1;4;7;19}. Ajoutée à
   `spec_m4_2.tex` §7 (dérivation : le taux r=Aγ(K_ℓK_b)^((γ-1)/2) est
   lui-même invariant sous cette transformation car de dimension
   1/temps ; K*_aut scale par c ; donc K0/K*_aut est invariant).
   Conséquence : K0/K*_aut n'est plus seulement un motif empirique
   observé, mais le SEUL canal possible pour A et K0 à γ fixé —
   un théorème, pas une hypothèse. Référencé dans rapport_final
   §Résultat 2 et §Résultat 3.

10. Corrections mineures : p<1e-33 → p<4e-33 (borne réellement valide
    sur les 20 runs) ; "8300 à 34000" → "8292 à 34249" (bornes exactes) ;
    "systématiquement 2-3×" (taux/prédiction) → "de 1,4 à 2,7×,
    croissant avec γ" (3/5 cellules étaient sous 2×) ; "un ordre de
    grandeur" (expositions unitaires) → "un facteur ~5" (valeur réelle) ;
    "24 cellules de la grille γ×λ" → "15 cellules de grille" (24 =
    total toutes cellules confondues, ablation/horizon/sonde inclus) ;
    table Résultat 1 : ligne λ=100 flaggée comme exposant de la loi PURE
    (coupure hors portée 3/3 partout à cette taille) ; légende λ=10
    corrigée (T=8000, pas T=4000).

**Ce qui n'a PAS été changé** : aucune donnée brute, aucun run n'a été
relancé pour "corriger" un résultat gênant. Les corrections 4, 5, 6 ont
changé des NOMBRES AFFICHÉS (bugs de pipeline/statistique corrigés) mais
pas les données sources ; toutes vont dans le sens d'un renforcement
(g060 confirme, Vuong correct confirme "massivement défendable" en
mieux). La correction 7 est la seule qui affaiblit une affirmation du
rapport (la précision du test K0) — c'est la marque d'un audit qui a
fait son travail plutôt que de valider poliment.

**Réponse finale à la question ouverte de la mission** (voir
rapport_final.pdf pour le texte complet) : γ seul (à A=1) déplace
mesurablement τ̂ (contraste γ=1/3 : 6/8 conditions pré-enregistrées),
mais son canal causal dominant, établi par une invariance d'échelle
EXACTE et démontrée (pas seulement observée), est le rapport
adimensionnel K0/K*_aut(γ,A) — "la pente dépend d'une combinaison
adimensionnelle", exactement le type de conclusion que le prompt
anticipait comme possible. La part résiduelle propre à la concavité
elle-même n'est pas tranchée par cette campagne. b reste épinglé
institutionnellement. Le canal de liquidité, quasi silencieux, s'éveille
faiblement à γ≥2/3 — cohérent avec le mécanisme mesuré, pas un artefact.
