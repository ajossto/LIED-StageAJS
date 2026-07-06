# Journal de recherche M3 (m3_credit_soc)

**État au 2026-07-06 : programme CLOS, tout est répliqué. Les 6 rapports sont
rédigés, compilés et poussés sur origin/main. La réplication H (seeds 1-2) a
CONFIRMÉ le plancher endogène : pop 5574/5566/5649, d/b=0,98 partout, 67-79
défauts de liquidité par run. Rapports 04 §H et 06 mis à jour en conséquence.
Budget final : 73 058 s = 20,3 h / 48 h (H = 10,1 h à elle seule). Correction
comptable : la mesure « 20,29 h » du 07-05 incluait déjà H s1/s2 (terminées
plus tôt que je ne le croyais) — aucun dépassement.**

Une leçon par entrée. Résumé d'une ligne en tête, puis confirmé/infirmé et pourquoi.
Consulter AVANT de relancer un run.

## Budget de calcul

Budget total de simulation : **48 h 00** (172 800 s, temps process cumulé).
Comptabilité : somme des temps wall-clock des processus de simulation
(les runs parallèles comptent chacun leur durée). Le raisonnement, la rédaction
et l'analyse statistique légère ne comptent pas.

| Étape | Consommé | Restant | Note |
|---|---|---|---|
| (init) | 0 s | 172 800 s | |
| Calibration (s,c) 12 cellules T=1500 | ~260 s | ~172 540 s | runs B sans crédit, 10-30 s/cellule |
| Baseline A 10×T=4000 | ~4 090 s | | ~400 s/run |
| Ablation B 10×T=4000 | ~730 s | | |
| Ablations C–J 3 seeds T=2000 | ~7 000 s | | H très lourde (en cours), Jb ~1 400 s/seed |
| Runs longs A/B T=20000 | ~9 060 s | | A ~3 370 s, B ~1 155 s |
| Grille 37/45 cellules | ~9 500 s | | c=0.02 et d0=20 dominent (carnet 2,6 M) |
| Grille complète (45) + H s0 + exploratoires | +42 400 s | | H s0 = 11 350 s à elle seule |
| **Cumul au 2026-07-05 (clôture synthèse)** | **73 058 s = 20,3 h** | **27,7 h** | suivi : `python3 exp_common.py` ; H s1/s2 en cours non compris |

Suivi automatique : `python3 experiments/m3/exp_common.py` somme les
wall_seconds de tous les summary.json.

## Entrées

### 2026-07-03 — Cadrage : les deux réplications M2 convergent, M2 = modèle nul Reed

**Résumé : M2 est un générateur démographique Reed-like validé deux fois indépendamment ;
le crédit n'y a aucun effet distributionnel mesurable ; M3 doit donner au crédit un canal
causal réel (recyclage L→K) sans casser le noyau démographique.**

Confirmé (les deux réplications, m2_fable et m2_codex, concordent) :
- classes dynamiques, renouvellement du top ~90 %/1000 pas, corr(âge, log NW) ≈ 0,06–0,16 ;
- population bornée dans la fenêtre de naissance (σ=0,25) — mais PAS grâce au crédit ;
- corps de NW = Fisk (pas exponentiel) ; queue non identifiée Pareto (lognormale tronquée
  gagne le LR corrigé dans 31/31 fenêtres) ;
- ablation sans crédit ≈ indiscernable de la baseline (exposant, stabilité, renouvellement).

Pièges d'outillage identifiés en M2, à ne PAS reproduire :
1. LR Pareto/lognormale sans renormalisation de la lognormale tronquée → biais pro-Pareto
   (le tail_test.py historique concluait Pareto sur des lognormales pures) ;
2. AIC du corps avec familles non tronquées sur un corps tronqué → biais anti-exponentiel ;
3. transfert prorata des créances en faillite → explosion combinatoire du carnet
   (1244 → 43 977 contrats ; jusqu'à 12,4 M sur la grille) → merge_pairs par défaut en M3 ;
4. moyenne arithmétique des taux → le marché meurt (176 prêts mort-nés / 2000 pas) →
   moyenne géométrique constitutive, à conserver ;
5. critère « mortalité instantanée du top » mal posé (structurellement nul) → mesurer le
   renouvellement entre fenêtres ;
6. σ=0,15 → mortalité éteinte, population divergente : la fenêtre d'existence du régime
   est étroite (facteur <2 sur σ). Vérifier qu'elle survit à la séparation L/K.

Décisions de conception prises pour M3 (à justifier dans le rapport 02) :
- production α√K répartie : s·P retenu en K, (1−s)·P versé en L (pas de décision
  d'investissement explicite ; s=1 et L ignoré redonne exactement M2) ;
- consommation proportionnelle c·L (sinon les créanciers accumulent L sans borne →
  top immortel → destruction du résultat anti-cohorte de M2) ;
- le crédit est le SEUL canal de recyclage L→K entre entités : c'est ce qui lui donne
  une possibilité causale réelle (absente de M2) ;
- service des intérêts depuis L seulement, simultané au prorata par emprunteur
  (convention codex, évite la priorité par ordre de création) ; défaut de liquidité
  possible avec NW>0 — c'est la fragilité nominal/réel voulue ;
- merge_pairs actif par défaut.

### 2026-07-04 — Calibration (s, c) : le coussin de liquidité tue la mortalité à c faible ; baseline figée à (0,75 ; 0,10)

**Résumé : à c ≤ 0,05 le stock stationnaire de liquidité L* ≈ (1−s)√K*/c est un
coussin qui éteint la mortalité au plancher d0 (d/b ≈ 0,34–0,44, population
divergente) ; seule la colonne c = 0,10 est dans le régime démographique de M2.**

Verdicts (experiments/m3/results/calibration_verdicts.json, critère pré-enregistré
rapport 02 §4) : viables = {(0,5 ; 0,1), (0,65 ; 0,1), (0,75 ; 0,1), (0,9 ; 0,1)}.
La cellule provisoire (0,75 ; 0,05) échoue → règle pré-enregistrée → **baseline
(s = 0,75 ; c = 0,10)**, figée dans config.py, ne plus retoucher.

Leçon mécanistique : la mortalité M2 venait de w qui fluctue près de d0 ; en M3
tout stock stable ajouté à NW (ici L) protège du plancher. Toute extension future
qui ajoute un actif stable devra re-vérifier la fenêtre démographique.
À noter pour la grille : l'axe c est le levier dominant du régime, plus que s.

### 2026-07-04 — Bug I8 trouvé par les tests : ne JAMAIS lire un defaultdict par [] dans une fonction d'observation

**Résumé : snapshot() lisait book.claims[i]/by_borrower[i] par [], insérant des
clés vides et changeant l'ordre d'itération du service des intérêts → un run
avec snapshots divergeait au dernier ulp d'un run sans (violation I8).**
Corrigé par .get() ; test I8 strict (identité bit à bit) rétabli et vert.
Règle générale : toute fonction d'observation (snapshot, diagnostic, check)
doit être en lecture pure — sur des defaultdict, [] est une écriture.
Suite : 50 tests verts (mécaniques, contrats/marché, faillites/avalanches,
invariants I1-I9 + R1 bit à bit contre m2_fable, estimateurs synthétiques).

### 2026-07-04 — Baseline A validée (10 seeds, T=4000) : régime Reed, canal de fragilité nominal INERTE en baseline

**Résumé : la baseline M3 est stationnaire et reproductible, mais dans ce régime
le crédit ne déclenche NI défauts de liquidité (0 en 4000 pas × 10 seeds) NI
avalanches non triviales (sous-Poisson, max 7) — la fragilité nominale voulue
existe dans le code (testée) mais pas dans le régime.**

Verdicts distributionnels (10 seeds concordants, validation.json par run) :
- NW : corps Fisk (9/10), ΔAIC_exp 21–84 ; queue α ≈ 2,2–3,2, LR corrigé
  pro-lognormale partout (comme M2) ; stable à x_min commun par fenêtres.
- L (variable Boltzmann candidate) : corps Fisk/lognormale, med/mean ≈ 0,92-0,94,
  ΔAIC_exp ≈ 707 (s0) → hypothèse Boltzmann-Gibbs REJETÉE en baseline. Queue
  légère (α≈4,9). Interprétation provisoire : L est piloté par l'injection
  (1−s)P et la fuite c·L, pas par des échanges conservatifs — les intérêts ne
  pèsent que 1,5 % de la production.
- Revenu : dPlN gagne 10/10 contre lognormale/Fisk/gamma → le mécanisme Reed
  (mélange d'âges × croissance multiplicative) domine le revenu.
- K : corps lognormal (mécanistique, GBM autour de la cible).
- Anti-cohorte : corr(âge, log NW) 0,13–0,20 ; renouvellement du top total sur
  2000 pas (survie 0 %, 97 % du top né dans les 1000 derniers pas).
- Financiarisation : part des intérêts dans le revenu du top1 = 2,7-4,7 % → faible.
- SOC : avalanches causales var/mean ≈ 0,06 (sous-Poisson) ; corr(HHI → morts
  futures) ≈ −0,5 (signe OPPOSÉ à l'accumulation-relaxation) ; AUC dettes→mort
  ≈ 0,63 (le réseau prédit un peu les morts individuelles).
- Niveau démographique : pop A ≈ 1150 << pop B ≈ 2270 : le crédit divise la
  population par ~2 (effet de NIVEAU net ; à confirmer distributionnellement
  contre B mêmes seeds/horizon).

Conséquence pour la suite : si B (10 seeds T=4000) montre les mêmes formes
distributionnelles, le verdict M2 se répète en M3-baseline et tout l'espoir
causal repose sur G (chocs corrélés) et sur la grille (zone où les intérêts
pèsent davantage : k, σ, d0). Piste identifiée : les taux d'intérêt effectifs
sont bas parce que les emprunteurs ont K ≈ K*(ρ) ≈ 23 très vite ; un régime à
service d'intérêts lourd demanderait des emprunteurs durablement pauvres en K.

### 2026-07-04 — Verdict causal A vs B (10 seeds × T=4000) : le crédit est causal DÉMOGRAPHIQUEMENT, pas distributionnellement

**Résumé : l'ablation B laisse toutes les formes distributionnelles inchangées
(NW Fisk, α=2,69 des deux côtés, revenu dPlN 10/10, K lognormal, Gini/top
identiques) mais le crédit divise par 2 la population stationnaire et
l'espérance de vie (118 vs 233 pas) et accélère le renouvellement du top
(frac_recent 0,985 vs 0,864, >5σ).**

Critère pré-enregistré (≥2 signatures modifiées) : FORMELLEMENT ATTEINT via
{population stationnaire, mortalité par tête, renouvellement du top, existence
d'avalanches multi-entités, AUC réseau→défaut}. MAIS lecture honnête : ces
signatures sont des manifestations partiellement redondantes d'un même effet
(vies plus courtes) ; les distributions elles-mêmes — la question de fond —
sont indiscernables de B. Le verdict M2 (« neutralité distributionnelle du
crédit ») se répète donc en M3-baseline malgré le crédit productif.

Mécanisme mesuré (seed 0) : par tête, K (161 vs 155), L (24,9 vs 24,4) et
production (11,2 vs 10,9) quasi identiques → le crédit ne change PAS la marge
intensive ; il convertit de la liquidité sûre en capital risqué + obligations
nominales, ce qui double le taux d'absorption au plancher (mortalité) —
« le crédit accélère l'horloge de Reed ». Production agrégée DIVISÉE par 2
(effet extensif). À départager par C (canal nominal seul), D (pertes de
créances coupées), E (stock vs flux).

Ne PAS conclure trop vite sur la SOC : en baseline les défauts de liquidité
sont inexistants et les avalanches sous-Poisson ; les vrais tests sont G
(chocs corrélés) et la grille (zones à service de dette lourd).

### 2026-07-04 — Ablations C–J (premières lectures, T=2000, 3 seeds)

**Résumé : le tueur démographique est le canal NOMINAL du crédit (C ≈ A), pas
sa productivité ; les pertes de créances n'y sont pour rien (D ≈ A) ; la perte
du flux d'intérêts pèse plus que la perte du stock (E intermédiaire) ; F est
confondue (l'appariement aléatoire tue le marché) ; G2 sectoriel allume les
premières avalanches non triviales ; I s'éteint (extinction totale).**

Populations finales (A≈1150, B≈2300 en référence) :
- C (q→L, non productif) ≈ 1055 : le canal nominal seul reproduit tout l'effet
  démographique — le côté « productif » du prêt n'est PAS la cause.
- D (pertes de créances indemnisées) ≈ 1150 = A : pertes de stock hors de cause.
- E (rente fantôme maintenue) ≈ 1560 : récupère ~40 % de l'écart A→B ; la perte
  de FLUX futur est le sous-canal dominant côté créancier.
- F (topologie aléatoire) ≈ 2110 ≈ B, MAIS CONFONDU : volume/pas 11,6 vs 75,9,
  contrats actifs 452 vs 68 608 — le protocole F pré-enregistré ne teste pas la
  topologie, il éteint le marché. À rapporter comme échec de conception (05) ;
  toute variante corrigée sera étiquetée exploratoire post-hoc.
- G1 macro : variance inter-seed énorme (826–3180) — dynamique agrégée dominée
  par les tirages macro ; NB : à σ total constant, ρ_m élevé réduit la
  dispersion idiosyncratique → le crédit s'amenuise aussi (656–3676 contrats),
  confusion partielle inhérente au design (documenter).
- G2 sectoriel (ρ_s=0,5, S=5) : avalanches max 36 (vs 6), var/mean 0,38 (vs
  0,07) — PREMIER signal type SOC ; crédit reste actif (64k contrats). À creuser
  en grille exploratoire (ρ_s, S).
- H (d0=0) : en cours — population sans mortalité, run lourd.
- I (λ=0, cohorte 1000) : extinction à t≈1760 (s0, s1) ; s2 pop=1 à T=2000.
  Sans réinjection, l'absorption au plancher vide le système : le
  renouvellement est une condition d'EXISTENCE du régime.
- Ja (λ=3) : pop ≈ 344 ≈ 115·λ — extensivité confirmée en première lecture.

Canal défaut de liquidité : TOUJOURS ZÉRO racine « liquidity », partout, y
compris sous chocs corrélés. Charge d'intérêts trop faible (1,5 % de la
production). Piste grille : s=0,9 (moins d'afflux de L), σ↑, d0↑, k↑.

### 2026-07-04 — Runs longs T=20000 : queue stable, A et B indiscernables ; G2 en détail : signal réel mais sous-critique

**Résumé : sur 20 000 pas, l'exposant de queue de NW (x_min commun, IC
bootstrap) fluctue sans dérive autour de 2,5-2,8, identique avec et sans
crédit — la stabilité long-horizon de M2 se reproduit en M3 et ne doit rien
au crédit. Les avalanches G2 sont réelles mais sous-critiques.**

Détail G2 (3 seeds) : max 16-36, var/mean 0,22-0,38, frac_multi ~1,7 % —
rafales par synchronisation sectorielle des défauts, PAS de queue critique
(distribution dominée par les singletons ; var/mean < 1 partout). AUC
levier→mort 0,59-0,64 (modeste). corr(HHI→morts futures) reste négative.
G1 macro : avalanches quasi nulles (le crédit s'y étiole, cf. confusion
dispersion). Figure : alpha_drift_long.png (04/figures).

### 2026-07-04 — Grille (37/45 cellules) : le canal de liquidité s'allume à peine à s=0,9 ; fenêtre σ étroite ; c=0,02 fait exploser le carnet

**Résumé : les 4 premiers défauts de liquidité du programme apparaissent à
s=0,9 (1+3 sur 2 seeds, contre ~18 000 insolvabilités) — le canal existe mais
reste marginal même dans la cellule la plus favorable ; aucune cellule ne
montre de zone SOC.**

- σ : 0,15 → divergence (pop ~15 900, crédit résiduel) ; 0,20 → ~6 000 encore
  croissant ; 0,25 → régime (1 150) ; 0,30 → 437 ; 0,35 → 215. Fenêtre
  d'existence étroite, comme M2, décalée vers [0,25 ; 0,35].
- s (avec crédit) : 0,5 → 643 ; 0,65 → 915 ; 0,75 → 1 150 ; 0,9 → 1 509.
  Mécanisme : K* = (s(1−δ)/δ)² contre d0 fixe — s pilote la distance au
  plancher. Interaction forte avec le crédit (en B, s comptait peu à c=0,1).
- k : 2 → 1 635 ; 3 → 1 400 ; 6 → 1 150 ; 12 → 1 015. Plus l'échantillon est
  grand (matching plus assortatif, plus de gros prêts), plus le crédit tue.
  Monotone, pas de transition.
- c=0,02 (avec crédit) : pop ~4 950 divergente ET carnet à 2,6 M de contrats
  (merge_pairs borne par PAIRE : la liquidité abondante inonde le marché de
  petits prêts) — 1 400 s/run. Leçon : c contrôle à la fois le régime
  démographique ET la densité du carnet.
- d0=20 : pop 2 582, carnet 690 k — plancher plus bas = moins de mortalité,
  crédit dense. (d0=25/29 en cours.)
- Défauts de liquidité : 0 partout SAUF s=0,9 (1 et 3 événements). Le régime
  « service d'intérêts contraignant » n'existe nulle part sur la grille : les
  taux d'équilibre au rendement marginal sont trop bas.
- H (d0=0, en cours) : la mortalité ne s'éteint PAS — seules les endettées
  peuvent mourir (D > actifs) : sans plancher, le crédit devient l'UNIQUE
  mécanisme de mort. Pop croissante freinée (5 530 à t=1600, 90 % endettées).

### 2026-07-04 — Robustesse des formes (grille) et dose-réponses exploratoires : pas de SOC, pas d'effet topologique au-delà du volume

**Résumé : Fisk 36/37 et dPlN 37/37 sur toute la grille ; α(NW) insensible à
k, s, c, d0 et monotone lisse en σ (3,71→2,19) — le motif M2 se réplique
quantitativement. Deux dose-réponses ferment les questions réseau et SOC :
la population suit le VOLUME de crédit quelle que soit la règle d'appariement,
et la sur-dispersion des avalanches suit ρ_s continûment sans transition.**

- Formes : corps NW Fisk 36/37 (1 gamma), revenu dPlN 37/37. α(NW) par axe :
  c0.02→3,21 ; σ : 0,15→3,71, 0,20→3,06, 0,25→2,69, 0,30→2,55, 0,35→2,19
  (M2 : 3,8/2,7/2,2-2,4) ; k, s, d0 : 2,6-2,8 sans tendance.
- Topologie (exploratoire F'') : prêteuse aléatoire à volume 41/pas → pop
  1637-1687 ; avec F (vol 12) → 2120 ; baseline (vol 76) → 1150. La relation
  pop↔volume est monotone à travers les trois règles d'appariement →
  AUCUNE évidence d'effet topologique au-delà du volume d'exposition.
  (F'' reste partiellement confondue : volume 53 % de la baseline.)
- SOC (exploratoire G2b/G2c) : var/mean des avalanches = 0,07 (iid) → 0,38
  (ρ_s=0,5) → 0,84 (ρ_s=0,8) ; max 72 à ρ_s=0,8. Réponse CONTINUE à la
  corrélation imposée, jamais var/mean > 1, pas de transition : le système
  amplifie proportionnellement, il ne s'auto-organise pas.
- Défauts de liquidité : toujours 0 dans F2/G2b/G2c (intérêts ≤ 1,1 % de la
  production partout).

### 2026-07-05 — H (d0=0) seed 0 complète : le plancher d'absorption peut être ENDOGÈNE — découverte positive majeure

**Résumé : sans d0, le système se borne quand même (pop ≈ 5 570
quasi-stationnaire, d/b=0,98) : la dette contractuelle remplace le plancher
exogène comme unique mécanisme de mort (14 338 morts par insolvabilité de
dette), et c'est le SEUL régime du programme où les défauts de liquidité
existent en nombre (71).**

Corrige ma lecture provisoire (« croissance persistante ») faite à t=1600.
Attention : carnet à 5,75 M de contrats (90 % des vivantes endettées),
wall 11 350 s (3,2 h) pour un seul seed — H est de loin le run le plus cher.
Piste M4 consignée : d0 remplacé par une dette de subsistance contractée
auprès d'entités réelles → plancher = réseau de créances exposé aux cascades.
Réplication s1/s2 en cours (~6 h) ; ne bloque pas la synthèse.

### 2026-07-04 — Budget : plan d'allocation après calibration

Coûts mesurés : run B T=1500 ≈ 10-30 s ; run A (crédit) T=600 ≈ 8 s.
Plan (large marge sous 48 h ; la puissance statistique n'est pas la contrainte) :
baseline A 10 seeds T=4000 (~0,3 h) ; B 10 seeds T=4000 (~0,2 h) ;
C-J 3 seeds T=2000 (~0,7 h) ; runs longs A et B T=20000 2 seeds (~1,5 h) ;
grille 1D (sigma, s, c, k, d0) 3 seeds (~0,7 h) ; réserve pour 2D et relances.

### 2026-07-03 — Coût de calcul M2 : référence pour la calibration M3

**Résumé : un run M2 T=2000, pop ~1700, coûte ~45 s (implémentation fable, 1 cœur).**
Machine : 8 cœurs, 31 Go. M3 sera plus lourd (2 variables d'état, avalanches causales,
buffer L) : hypothèse 1,5–3× à vérifier par le run de calibration avant toute allocation.
