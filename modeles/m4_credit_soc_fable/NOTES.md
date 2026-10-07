# Journal de recherche M4 (m4_credit_soc_fable)

Fork de M3 — recherche d'un régime d'avalanches auto-organisé (SOC).
Une leçon par entrée : résumé d'une ligne en tête, confirmé/infirmé, pourquoi.
Consulter AVANT de relancer un run. Brief : PROMPT_M4_SOC.md.

**État au 2026-07-14 : OBJECTIF ATTEINT.** Le moteur fusionné (src/m4 : K
seul, d0 retiré du code, faillite annulation+destruction, marché 1
round/tête, chocs iid) produit des avalanches en loi de puissance
(α_queue≈2,2-2,3, LR pure-PL vs lognormale corrigée POSITIF partout,
z=+2,3 à +57), cutoff croissant avec N sans saturation (max 23→224 pour pop
148→4414), vraie propagation (racines/taille 0,50, profondeur ≤12), b
auto-stabilisé à 0,300, contraintes préservées (NW Fisk, revenu dPlN,
renouvellement total), robuste en T/seeds/k. Synthèse rédigée et compilée :
reports/01_soc_final/main.pdf (8 p., annexe de traçabilité). 61 tests
verts. Limites honnêtes : fenêtre critique institutionnelle (volume ∈ [n,
~2n) — l'apurement complet sur-vise), épaulement pré-coupure à λ≥100,
théorie de α ouverte.

## Entrées

### 2026-07-13 — Cadrage : suite de tests restaurée (51 verts), lecture du point de départ

**Résumé : le fork M4 n'avait pas de tests ; suite M3 copiée et adaptée aux
nouveaux défauts (objective="income", shock_rho_sector=0.8) — 51 tests verts,
y compris R1 (réduction bit à bit vers m2_fable) et I8 (observation neutre).**

Adaptations nécessaires (les tests M3 supposaient la baseline M3) :
- tests de choc iid / macro : `shock_rho_sector=0.0` explicite ;
- `test_market_productive` et `test_market_random_valid` : `objective="wealth"`
  explicite (ils testent la cible K*(r+δ) et l'ablation F, pas l'objectif) ;
- R1 : `shock_rho_sector=0.0` explicite (la séquence RNG sectorielle divergerait
  de M2 sinon).

Lecture du run existant `m4_first_s0` (income + rho_s=0.8, λ=10, T=2000) :
- pop stationnaire ≈ 135 (l'objectif revenu ÷8 l'espérance de vie, cohérent X1) ;
- avalanches max 7, var/moy 0,03 — MAIS régression hors taille 1 :
  pente −3,35 ± 0,18, r² = 0,99 (marqueur principal du brief déjà présent) ;
- dans un système de 135 entités, max=7 est d'abord une contrainte de taille
  finie, pas une preuve d'absence de criticité. D'où la phase A1 : scaling
  en λ (extensivité pop ≈ 115·λ/10 établie par Ja de M3, à revérifier ici
  sous la règle de revenu).

Plan initial (voir tâches) : A1 scaling λ, A2 ré-examen rho_s avec le
marqueur hors-taille-1 (pas var/mean), B régime d0=0 × revenu.

### 2026-07-13 — Outillage SOC : estimateurs DISCRETS, validés sur synthétique

**Résumé : les tailles d'avalanches sont des entiers presque tous égaux à 1 —
le CSN continu de M3 y dégénérait (rapport 05) ; l'outillage M4
(`experiments/m4/soc_stats.py`) utilise un MLE zêta discret (scan s_min par
KS) et un LR de Vuong contre lognormale DISCRÈTE renormalisée sur le même
support ; 5 tests synthétiques verts (récupération α ±0.15, signes LR
corrects des deux côtés — le piège n°1 ne se reproduit pas).**

Aussi : `dist_checks.py` (familles NW/K/revenu + renouvellement entre
fenêtres, réutilise m4.analysis) ; `run_sweep.py` (grilles nommées).
Burn-in par défaut : t ≥ T/4 (robustesse vérifiée sur 2 runs :
t_min ∈ {500, 1000, 1500} → pente ±0,3, r² > 0,90 partout).

### 2026-07-13 — Sweep B : d0=0 × règle de revenu — CONFIRMÉ comme meilleur régime candidat

**Résumé : le plancher endogène (d0=0 en config) sous la règle de revenu est
stationnaire, bon marché (42-160 s/run vs 3,2 h du H de M3 — la règle de
revenu écourte les vies, le carnet reste à ~10-70k contrats), et produit des
avalanches plus grosses que la baseline d0=28 à λ égal : max 38-44 à λ=30
(pop≈960) vs 13-21 (pop≈470-600 pour a1). Marqueur principal : r²
hors-taille-1 = 0,96-0,99, pente −2,6 à −2,9, LR discret corrigé z=15-37
pro-loi de puissance (3 seeds).**

- Cutoff ≈ linéaire en taille de système : λ=10 (pop~320) max 10-20 ;
  λ=30 (pop~960) max 38-44 ; <s²>/<s> 1,16 → 1,55.
- Pas de bimodalité (histogrammes bruts continus, gap_below_max petit) —
  le piège « effondrement ≠ SOC » (critère 7) est écarté sur ces runs.
- Signature accumulation-relaxation OBSERVÉE (analyse d'époque superposée,
  avalanches ≥ 6, fenêtre ±30 pas) : croissance du carnet pré-événement
  2× la tendance (b_lam10_s0 : +16,4 contrats/pas vs +7,5 tendance),
  chute de 5-10 % après. Signe opposé au corr(HHI→morts)<0 de M3.
- α discret (s_min par KS) : 5,0-5,5 — plus lourd que la baseline a1
  (6,4-7,0). NB : l'α discret à s_min=1 est dominé par les singletons ;
  la pente hors-taille-1 (−2,6/−2,9) est l'estimateur pertinent de la queue.

### 2026-07-13 — Contraintes distributionnelles : PRÉSERVÉES dans le régime B (d0=0 × revenu)

**Résumé : à λ=30 (n≈1000, familles identifiables contrairement aux pops
~150 de X1), le régime d0=0 × revenu garde des familles reconnaissables :
corps NW lognormale (3/3), K Fisk/lognormale, revenu dPlN (2/3) ou
lognormale, Gini NW 0,47-0,67, persistence du top décile 0,11-0,23 entre
mi-parcours et fin (renouvellement réel, pas de top immortel).**

Mesuré par dist_checks.py sur b_lam30p0_s{0,1,2} (dernier snapshot t=2000,
fenêtre de renouvellement [1000, 2000]).

### 2026-07-13 — Prototype fusionné « M4-simple » (K seul, sans d0) : le régime EXISTE

**Résumé : le modèle à UNE variable d'état (fusion L/K : intérêts payés
depuis K, prêts en transfert de K, aucun d0, règle de revenu K*(r)=√(K_l·K_b),
plancher purement endogène NW=K+créances−dettes<0) est stationnaire et
produit le marqueur : pop~107 à λ=10, max=11, pente hors-taille-1
−3,83±0,44, r²=0,93 (seed 0, T=2000, 13 s).**

Prototype jetable : experiments/m4/proto_simple.py (réutilise LoanBook ;
cascade = même définition causale que bankruptcy.py). Piège corrigé au
passage : ne pas tester l'extinction avant le premier pas (N(0)=0).
Espérance de vie ~10 pas (mortalité plus dure que B : pas de tampon L,
service depuis le capital productif lui-même). λ=30 × 3 seeds en cours
pour stationnarité et familles avant toute promotion dans src/m4/.

### 2026-07-13 — INFIRMÉ : les « grosses avalanches » des régimes B/a1 ne sont PAS de la propagation

**Résumé : dans TOUS les runs à chocs sectoriels (B, a1, a3), les avalanches
de taille ≥ 5 ont racines/taille = 1,00 et profondeur ≤ 2 — ce sont des morts
simultanées (synchronisées par le choc corrélé) que le graphe de pertes relie
via des prêteuses communes, pas des cascades. La loi de puissance mesurée est
celle des grappes de racines. Le critère 6 du brief (mécanisme endogène)
n'est PAS satisfait par l'axe sectoriel.**

Cause mesurée (snapshot b_lam30p0_s0, t=2000) : la sélection assortative
fait prêter les plus riches — exposition max/NW des prêteuses : méd 0,07,
p99 0,21, max 0,49 → AUCUNE prêteuse ne peut mourir d'un défaut isolé
(rapport de branchement ≈ 0 structurel). A2 (moteur L/K, ρ_s=0 → max 6-7 ;
0,4 → 12-14) confirme la dose-réponse continue de M3 : l'axe sectoriel est
de l'amplification, pas de l'auto-organisation.

### 2026-07-13 — Sweep A2 complet : l'axe ρ_s est bien une amplification continue — la lecture M3 tenait, même avec le bon critère

**Résumé : moteur L/K (d0=28, revenu, λ=30, 3 seeds/cellule), max d'avalanche
par ρ_s : 0 → 6-7 ; 0,2 → 7-9 ; 0,4 → 12-14 ; 0,6 → 13-14 ; 0,8 → 13-24.
Pas de transition, r² hors-taille-1 élevé PARTOUT (0,92-0,99) — le marqueur
r² ne discrimine PAS cet axe ; c'est la structure interne (racines/taille = 1,
profondeur ≤ 2) qui tranche : synchronisation imposée, pas d'auto-organisation.
Le point de départ suggéré par le brief (ré-examiner l'axe sectoriel) est
soldé : axe réel mais non-SOC.**

Leçon d'outillage : le marqueur « r² > 0,90 hors taille 1 » est NÉCESSAIRE
mais PAS suffisant — des grappes de racines synchronisées le passent très
bien. Ajouter systématiquement racines/taille et profondeur max aux critères
(fait dans soc_stats à venir).

### 2026-07-13 — Prototype fusionné : k (connectivité du marché) est le paramètre de contrôle structurel

**Résumé : à chocs PUREMENT IID (ρ_s=0, λ=30, pop 230-400), balayer k donne
une transition nette : k=12 → avalanches éteintes (max 3) ; k=6 → max 7-9,
pente −4,7 ; k=3 → max 27, pente −2,3/−2,4, r² 0,92-0,94 ; k=2 → régime à
BOSSE (plateau tailles 9-26, r² 0,76, quasi-cycle boom-bust, max 44 à pop
233). La note de conception pré-M2 (transition stable → SOC pilotée par la
connectivité, [ÉLAGAGE] k≥3) est qualitativement retrouvée — k=3 est le
candidat critique.**

Mécanisme lu : k grand = tri assortatif fort = seules les très riches
(NW épais) prêtent = pas de contagion ; k petit = tri faible = des entités
moyennes à NW mince prêtent = intermédiation vulnérable. ATTENTION
confusion possible : k change aussi le nombre de rounds (n//k) donc le
volume — à contrôler avant conclusion (leçon F de M3). Structure k=2 :
racines/taille 0,96, profondeur ≤ 3 — la bosse reste dominée par la
synchronisation dynamique (cohortes), pas par la propagation profonde.

### 2026-07-13 — Sweep A1 complet : le cutoff de la baseline M4 scale avec λ… mais ce sont toujours des grappes de racines

**Résumé : baseline M4 (L/K, d0=28, revenu, ρ_s=0,8), max d'avalanche par λ :
10 (pop~156) → 6-7 ; 30 (pop~490) → 13-24 ; 100 (pop~1550) → 62-89. Le
critère 2 du brief (cutoff croissant avec la taille du système) est
satisfait numériquement, MAIS racines/taille = 1,00 et profondeur ≤ 2 à
toutes les tailles : l'objet qui scale est la grappe de morts synchronisées
par le choc sectoriel, pas une cascade. λ=100 coûte ~45-75 min/run (carnet
150-250k contrats).**

k=3 sans naissance-par-emprunt, λ=30 : ACF des morts ≈ 0 à tous lags
(pas de cycle, contrairement à k=2) — le régime k=3 reste le candidat
« critique » structurel.

### 2026-07-13 — Naissance par emprunt (piste M3 « dette de subsistance ») : implémentée au prototype, propagation partielle

**Résumé : financer la dotation K0 des nouveau-nées par une vraie prêteuse
(prototype, birth_loan : transfert réel de K + contrat nominal, apport en
fonds propres ε0 = 0,2·K0 ≈ σ·K0 conforme à la fenêtre de naissance §2.5 de
la note de conception, fallback fonds propres si aucune prêteuse faisable)
fait apparaître les premières morts propagées : racines/taille passe de 1,00
à 0,86-0,90, profondeur max 3, max=30 à pop 164 (k=3, chocs iid, λ=30).**

- k=3 + prêteuse de naissance aléatoire parmi les faisables + ε0=0,2·K0 :
  pente −2,25, r²=0,94. Sans apport (ε0=0) : mortalité infantile ~50 %/pas,
  pop 109. Prêteuse riche vs aléatoire : peu de différence à k=3.
- La masse des grosses avalanches reste des racines synchronisées de façon
  ENDOGÈNE (cohortes nées ensemble, leviers identiques, chocs iid !) reliées
  par les morts réelles de leurs créancières communes — c'est une histoire
  causale endogène acceptable, mais la profondeur ≤ 3 reste le point faible.
- NB : le critère racines/taille≈1 n'est pas rédhibitoire en soi — deux
  racines ne sont dans la MÊME composante que si une créancière commune est
  morte aussi (l'arête exige les deux extrémités mortes) ; mais on veut
  voir la profondeur croître avec la taille du système pour parler de
  cascade. Scaling λ ∈ {100, 300} en cours (proto_scaling.log).

### 2026-07-14 — INFIRMÉ : le régime k=3 (transfer/prorata) n'est pas SOC — croisement critique de taille finie

**Résumé : en scaling λ (30 → 100 → 300, pop 233 → 763 → 2300), la « loi de
puissance » du régime k=3 iid se courbe en bosse : r² hors-taille-1 passe de
0,94 à 0,78 puis 0,31-0,68 ; racines/taille reste 0,95-0,96, profondeur ≤ 3.
Interprétation : le graphe de couplage des morts traverse son seuil de
percolation quand la taille croît (composantes géantes à grand N) — le
pseudo-critique de λ=30 était une coïncidence de taille finie, pas de
l'auto-organisation. L'âge des membres (IQR ~13) infirme aussi l'histoire
« cohortes ». Coût : λ=300 avec carnet fragmenté par le prorata = 12,5 h —
NE PAS relancer de λ=300 en transfer/prorata.**

### 2026-07-14 — DÉCOUVERTE : cancel+destroy = vraies cascades propagées ET loi de puissance propre — avec une règle de faillite PLUS SIMPLE

**Résumé : en remplaçant à la faillite (i) le transfert prorata des prêts de
la morte par leur ANNULATION (fail_lender_loans="cancel") et (ii) la
récupération prorata des actifs résiduels par leur DESTRUCTION
(fail_residual="destroy"), le prototype fusionné (k=3, chocs iid, λ=30,
seed 0) donne : racines/taille 0,44 (56 % des membres sont des victimes de
cascade !), profondeur moyenne 3,4 / max 8, pente −3,78 ± ?, r² = 0,994,
pop 517 stationnaire. Premier régime du programme M3+M4 avec de la VRAIE
propagation. Et la règle est plus simple que la baseline (pure suppression +
arêtes de perte, zéro machinerie de redistribution).**

Mécanisme lu : « destroy » supprime le coussin (chaque mort = perte sèche
pour les créancières) ; « cancel » empêche la fragmentation du carnet par
héritage prorata (les expositions restent concentrées → un défaut isolé
peut tuer) + soulage les emprunteuses de la morte (rappel vers l'équilibre).
Grille de validation en cours (proto_cd_grid.log) : seeds, λ=100/300,
robustesse en k (2/3/6). Avec naissance-par-emprunt : quasi identique
(r²=0,978) — la naissance par emprunt n'est PAS nécessaire à la propagation.

### 2026-07-14 — Validation du candidat cancel+destroy : exposant STABLE en seeds et en taille, cutoff et profondeur croissants

**Résumé : grille prototype (k=3, iid, cancel+destroy) — α discret (s_min
par KS) = 2,90/2,92/2,90 (λ=30, 3 seeds) et 2,90/2,91/2,91 (λ=100, 3
seeds) : l'exposant est une CONSTANTE du mécanisme. Cutoff : max 23-30
(pop~520) → 36-48 (pop~1720) ; profondeur max 7-8 → 8-11 ; racines/taille
0,44-0,45 PARTOUT ; chute de pop max 3-6 %/pas (pas d'effondrement). En k :
k=2 → α 2,65 (LR z=+1,2), k=3 → 2,9, k=6 → 3,6 — la propagation
(profondeur 7-9) existe à tous les k, l'exposant glisse doucement : PAS de
réglage fin de k requis pour l'existence du régime.**

Réserve : le LR discret PL pure vs lognormale reste négatif (z −5 à −10)
— attendu en taille finie (cutoff exponentiel) ; ajouter le modèle PL ×
cutoff au LR pour un verdict honnête (à faire). destroy SEUL échoue
(bosse, r²=0,36 — cohérent avec le journal de m4_credit_soc_sol qui
l'infirme aussi indépendamment) : c'est la COMBINAISON cancel+destroy qui
fait le régime ; ablations à un levier en cours sur le moteur refondu.

### 2026-07-14 — Cutoff du candidat cancel+destroy : croît jusqu'à pop~1700 puis SATURE — branchement sous-critique intrinsèque

**Résumé : max d'avalanche par taille de système (k=3, cd, iid) : pop 170
(λ=10) → 15-18 ; pop 520 (λ=30) → 23-30 ; pop 1720 (λ=100) → 36-48 ; pop
5180 (λ=300) → 47. La croissance s'arrête entre λ=100 et λ=300 : le cutoff
est une échelle INTRINSÈQUE du mécanisme (longueur de corrélation finie du
processus de branchement, b < 1), pas une limite de taille finie. Le
critère 2 du brief échoue en l'état au-delà de pop~1700. L'exposant reste
α=2,90-2,92 et racines/taille 0,44 partout.**

Conséquence : chercher le levier qui pousse le branchement b = 1 −
Σracines/Σtailles vers 1 (σ, volume via rounds_div, k), mesurer x_c (fit
PL×cutoff, nouvel estimateur testé sur synthétique — 8 tests verts) le
long de ces axes, PUIS poser la question du feedback qui épinglerait le
système au point critique (sinon c'est de la criticité réglée, pas de la
SOC). Scan en cours (proto_lever_scan.log).

### 2026-07-14 — Le rapport de branchement s'auto-stabilise (b≈0,20 ∀N) ; son levier est le VOLUME de marché ; PL×cutoff bat la lognormale partout

**Résumé : (i) sur les runs candidats sauvegardés, b = 1 − Σracines/Σtailles
= 0,197-0,204 à toutes les tailles de système (λ=10/30/100) — le mécanisme
épingle le branchement à une valeur reproductible, mais sous-critique
(xc ≈ 6-11 sature). (ii) Le scan de leviers (prototype) montre que σ ne
déplace PAS b (0,18-0,21 pour σ 0,20-0,35) mais le volume de marché OUI :
rounds n//6 → b=0,141, xc=3,2 ; n//3 → b=0,199, xc=10,2 ; n//2 → b=0,240,
xc=33 — xc répond de façon fortement non-linéaire, suggérant une divergence
vers b_c. (iii) Le LR PL×cutoff vs lognormale (nouvel estimateur, testé)
est POSITIF partout (z=2,5-5,2) : la taille d'avalanche est une loi de
puissance α≈2,6 à cutoff exponentiel, PAS une lognormale — le critère 3
honnête est satisfait, c'est le critère 2 (xc croissant avec N) qui reste
à conquérir via le volume.**

Piste sans paramètre identifiée : faire APURER le marché à chaque pas
(prêter tout l'excédent faisable, pas de dial rounds_div) et demander si
b s'auto-limite sous le point critique avec xc croissant en N — la vraie
question SOC. Test rounds_div=1 en cours (proto_rounds1.log). Question
jumelle : la mesure même-pas tronque-t-elle les cascades (une prêteuse
blessée qui meurt au pas suivant compte racine) ? Analyse inter-pas en
cours (causal_window.py, arêtes de perte datées journalisées par le
moteur, option log_loss_edges).

### 2026-07-14 — Fenêtre causale inter-pas : τ=1 débloque les cascades du régime cd MAIS n'est pas fiable en général (sur-liaison par coïncidence)

**Résumé : relier mort(i,t) → mort(créancière, t+τ) via les arêtes de perte
datées (moteur : option log_loss_edges ; analyse : causal_window.py) change
tout pour le candidat cd : à τ=1, α=2,60-2,64 SANS cutoff (fit xc → ∞),
r²=0,99, LR PL×cutoff z=12-21, et le max scale LINÉAIREMENT avec N (122 à
pop 517 → 419 à pop 1722). Justification de τ=1 : une perte subie en phase
7 du pas t n'est réévaluée qu'à la résolution du pas t+1 — la mesure
même-pas tronque la première génération. MAIS le contrôle règle-M3 montre
que τ=1 sur-lie quand la densité de morts est haute : max 27 → 896 à pop
233 (384 % de la population !), ~3,5 liens fortuits/mort (30 morts/pas ×
27 prêteuses/morte) contre ~0,08 dans le régime cd. Verdict : mesure
même-pas = mesure PRINCIPALE (stricte) ; τ=1 = preuve d'appoint pour le
régime cd, à toujours accompagner du taux de coïncidence. À τ≥2-3 : tout
percole, mesure inutilisable.**

### 2026-07-14 — Le volume ne s'auto-limite PAS sous le critique ; le régime finalisable est « un round par tête » (rounds_div=1)

**Résumé : en poussant le volume (rounds 2n puis 4n par pas), b continue de
monter (0,340 puis 0,356) et la distribution se dégrade (r² 0,88 puis 0,64,
bosse) — l'apurement complet du marché sur-vise légèrement le point
critique, il n'y a pas d'auto-limitation au sens OFC conservatif. MAIS à
UN round par tête et par pas (rounds_div=1, normalisation naturelle sans
réglage fin), b s'épingle à 0,300 (3 runs, indépendant de N et du seed),
α≈2,42-2,54, xc ≈ 500-800 À λ=30 (>> max observé 46-49) et xc → ∞ à λ=100
(max 111) : le cutoff est au-delà de la taille du système accessible —
criticité de taille finie à toutes les tailles atteintes. Séquence b par
volume : n/6→0,141 ; n/3→0,199 ; n/2→0,240 ; n→0,300 ; 2n→0,340 ;
4n→0,356 (saturation vers ~0,36 > b_c). λ=300 en cours
(proto_r1_scaling.log).**

### 2026-07-14 — Campagnes moteur V et F (partielles) : dose-réponse du cutoff sur 2,5 décades, LR loi-de-puissance-PURE positif partout dans la config finale

**Résumé : (V, 3 seeds/point, λ=30) le cutoff ajusté xc répond au volume de
marché : 1/6 round/tête → xc=3 (LR PL pure z≈−10) ; 1/3 → xc=8-10 (z≈−5) ;
1/2 → xc=28-33 (z≈+2) ; 1 → xc=514-1019 (z≈+16/+18). (F, config finale
rounds_div=1) λ=10 : max 23-29 à pop~147, α=2,39-2,42, LR PURE z=+2,3/+4,6 ;
λ=30 : max 46-60 à pop~445, α=2,43-2,45, z=+15,6/+18,1, profondeur max 9-12.
Le xc croît SUPERlinéairement avec la taille (×3 en pop → ×20 en xc).
Artefacts complets sur disque (results/f_*, v_*, y compris loss_edges.csv
pour l'analyse causale inter-pas — consignes de traçabilité).**

λ=100/300 et T=4000 en cours (sweep_F.log). Défaut du moteur fixé à
rounds_div=1 (config.py documente la dose-réponse) ; tests mis à jour
(rounds_div=2 explicite dans les tests de formule par round), 61 verts.

### 2026-07-14 — Audit indépendant (subagent à contexte frais) : les chiffres du rapport reproduits depuis le disque, zéro écart

**Résumé : un agent d'audit indépendant a recalculé depuis
avalanches.csv/series.csv/config.json (sans lire les JSON dérivés ni le
rapport) les 7 blocs d'affirmations du tableau central : pop, max, b, LR z,
r², configs (d0 absent, cancel/destroy/rounds_div=1/iid/income/k=3), et la
contre-vérification structurelle baseline (racines/taille 0,998, prof ≤2)
vs candidat (0,500, prof 12). Tout reproduit, aucun écart > 5 %. Précision
intégrée au rapport : b(λ=10) = 0,287-0,293 (0,300 ± 0,001 dès λ≥30).**

### 2026-07-14 — Campagne F : tous les critères du brief passés sur la config finale

**Résumé : config finale (fusionné, cancel+destroy, 1 round/tête, chocs
iid) — λ=10 : max 23-29 (pop~147) ; λ=30 : 46-60 (pop~445) ; λ=100 :
108-117 (pop~1475) ; λ=300 (prototype) : 224 (pop 4414). LR loi de
puissance PURE vs lognormale corrigée : z=+2,3 à +34,5 (moteur), +57
(prototype λ=300). b=0,295-0,301 partout. T=4000 : α et xc inchangés.
Accumulation-relaxation vérifiée sur la config finale (~390 événements ≥15
par seed : carnet +1 à +4 contrats/pas avant, −1,0 à −1,4 % après).
Contraintes : NW Fisk (3/4), K Fisk (4/4), revenu dPlN (3/4), Gini
0,42-0,44, renouvellement total. Pas d'effondrement (chute max 2-9 %/pas).**

Dérive apparente de α (2,40→2,63 en s_min=1) : artefact du poids des
singletons — à s_min=2, α=2,26-2,32 stable sur toute la gamme (s_min=3 :
2,18-2,41, dérive inversée) ; l'exposant de queue est ~2,2-2,3.
Rapport de synthèse : reports/01_soc_final/main.tex (avec annexe de
traçabilité par run_id, consignes rapport respectées).

### 2026-07-14 — REFONTE : moteur fusionné promu dans src/m4 (K seul, d0 retiré du code), 58 tests verts

**Résumé : src/m4 est refondu — une variable d'état réelle K (fusion L/K :
intérêts payés depuis K, prêts en transfert K→K, production entièrement
retenue), d0 SUPPRIMÉ du code (NW = K + créances − dettes, plancher
purement contractuel), marché symétrique « viser K*(ρ) » de la note de
conception §2.2, règle de faillite par défaut cancel+destroy, naissance
par emprunt en option (birth_loan). Champs supprimés : d0, L0, s, c,
beta_L, loan_target, claim_loss, flow_loss, market_selection, rate_rule,
merge_pairs, shock defaults iid. Moteur L/K pré-refonte archivé dans
archive/m4_lk_pre_refonte/ (le dossier n'est pas suivi par git — sans
copie, la baseline ne serait plus reproductible).**

- Suite de tests réécrite : 58 verts. R1 (réduction bit à bit vers m2_fable,
  qui reposait sur d0) remplacée par R1' : credit=False → personne ne meurt
  (NW=K>0), pop = cumul des naissances, trajectoire K de la première entité
  identique au rejeu manuel (< 1e-9 relatif). I4 refondu (bilan K_tot avec
  injected/destroyed) et testé aussi sous birth_loan et sous la règle M3.
- Validation croisée moteur/prototype (λ=30, s0) : pop 517 vs ~520, max 27,
  pente −3,78, α 2,92 vs 2,90, racines/taille 0,44, profondeur 8 — identique
  aux fluctuations près.
- Nouveau test de couverture : la faisabilité du prêt de naissance
  échantillonne min(k, |pool|) (le pool < k au démarrage ne bloque plus).

### 2026-07-13 — À volume contrôlé, le tri du marché a un effet propre : la clôture « topologie = volume » de M3 ne tient pas sous le critère avalanches

**Résumé : prototype fusionné, chocs iid, λ=30, en croisant k (force du tri
assortatif) et le nombre de rounds (n//rounds_div, proxy du volume) : à
rounds n//3 égaux (vol ≈ 12k/pas), k=3 → max 27, pente −2,26 ; k=6 → max 15,
pente −3,50. À rounds n//6 égaux : k=3 → max 21/−3,04 ; k=6 → max 9/−4,77.
Le tri faible (k petit) aplatit la distribution À VOLUME ÉGAL — l'effet
topologique existe, M3 ne le voyait pas parce qu'il regardait la population,
pas les avalanches.** Le volume a AUSSI un effet propre (plus de rounds →
plus plat à k fixé). Deux leviers indépendants vers la criticité.

### 2026-07-13 — Sweep A3 (n_sectors) : le cutoff n'est PAS fixé par la taille de secteur

**Résumé : à λ=30 fixé (pop≈470, baseline d0=28), diviser la taille de
secteur par 10 (S=2 → S=20, secteur ~235 → ~23 entités) ne divise le max
d'avalanche que par ~2 (28-36 → 10-12) — la synchronisation sectorielle
module le taux de déclenchement mais ne fixe pas l'échelle des avalanches,
qui vient de la propagation par le réseau de crédit.**

max par S (3 seeds) : S=2 : 21/36/28 ; S=5 (=a1_lam30) : 21/13/24 ;
S=10 : 15/16/15 ; S=20 : 12/10/11. r² hors-taille-1 : 0,90-0,99 partout.
Si le cutoff était la taille du secteur, S=20 (23 entités/secteur)
plafonnerait ~23 fois plus bas que S=2 — il ne perd qu'un facteur 2.
Verdict A2 (ρ_s=0) attendu pour trancher si le choc sectoriel est
nécessaire au déclenchement ou seulement amplificateur.

### 2026-07-16 — Intégration Simulation Lab : lots confirmatoires λ=10/30/100 (5 seeds, T=4000) + figures agrégées et « figures du rapport »

**Résumé : le modèle est branché dans Simulation Lab (adaptateur
`lab/{config,output,analysis}.py`, journalisation enrichie `src/m4/richlog.py`
sans effet sur la dynamique — testé bit-à-bit). Trois lots de la config
finale (λ∈{10,30,100} × 5 seeds × T=4000) ont été exécutés via le lab ;
`lab/batch_report.py` construit par lot un run synthétique consultable
(figures « façon m0 » superposant les seeds) et un export inter-lots
`m4_soc_synthese_lots` qui rejoue les conclusions du rapport 01_soc_final
sur ces 15 runs : tout est confirmé, en plus net (T=4000).**

Critères sur les nouveaux lots (burn-in T/4, mesure stricte même-pas) :
- max 26-30 (λ=10) → 44-52 (λ=30) → 103-117 (λ=100), max ∝ N^0,59 ;
- α MLE discret s_min=1 : 2,38-2,40 → 2,44 → 2,54 (dérive artefact des
  singletons : à s_min=2, 2,25-2,32 stable sur toute la gamme) ;
- z (PL vs lognormale discrète renormalisée) : +3,0 à +5,7 (λ=10),
  +23 à +26 (λ=30), +47 à +49 (λ=100) ; r² hors t.1 : 0,92-0,97 ;
- b : 0,292-0,301 sur les 15 runs ; racines/taille (≥5) 0,48-0,51 ;
  profondeur max 9-14 ; pop/λ = 14,6-14,8.
La figure accumulation_relaxation quantifie le cycle : +2 à +2,7
contrats/pas dans les 20 pas avant un événement ≥15, élagage instantané
−3,6 % (λ=30) à −14,5 % (λ=10) du carnet au pas de l'événement (mesure
un-pas, plus large que le −1 à −1,4 % « après événement » du rapport,
mesuré sur une fenêtre).

Artefacts : `simulation_lab_data/runs/<batch>_lot/` (3 lots),
`simulation_lab_data/runs/m4_soc_synthese_lots/` (synthèse + stats par
run dans soc_summary.json). Reconstruction : `lab/batch_report.py --all-m4
--force`. Interface : `python3 -m simulation_lab.cli gui --open-browser`.

### 2026-07-16 — Lois ajustées sur les figures de lot ; profil double-Pareto du volume ; le revenu > 10 J est lognormal (ni Boltzmann×Pareto, ni dPlN)

**Résumé : toutes les figures de lot portent désormais les lois ajustées
en surimpression (paramètres, r² pondéré par les comptes de bins, z de
Vuong en légende). Trois résultats nouveaux par rapport au rapport
01_soc_final : (1) la densité du VOLUME (J) des avalanches a un profil
double-Pareto flagrant — branche montante ~+3,2 à +3,9, branche
descendante −2,12 (λ=10) à −2,30 (λ=100) très stable (r² 0,99), mode
~110-120 J INDÉPENDANT de la taille du système (∝ N^0,02) — le mode est
une échelle intensive (échelle des créances individuelles ~K*), seule la
coupure de la branche descendante suit N ; (2) sur l'histogramme de
répartition des tailles (bins entiers de largeur ≥ 2, vue principale de
cascades_rank_size sur consigne — la coupure y est bien plus nette que
sur la CCDF), l'épaulement pré-coupure à λ=100 est directement visible ;
(3) le revenu brut au-dessus de 10 J est LOGNORMAL (AIC : lognorm 5/5
seeds sur chacun des 3 lots) — le corps n'est pas exponentiel
(Boltzmann rejeté, r² négatifs), la « queue Pareto » du scan CSN a
α_pdf ≈ 8,7-9,2 (c'est la coupure lognormale, pas une loi d'échelle),
et la dPlN dégénère vers sa limite lognormale (a ≈ 15-17, ΔAIC ≈ +2-4 =
pénalité de ses 2 paramètres superflus).**

Nuance d'échantillonnage : sur l'échantillon complet (> 0 J, où la
branche montante x^{b-1} de la dPlN a un support), la dPlN gagne
l'AIC 5/5 à λ=10 ; c'est la bosse < 10 J (jeunes entités proches de la
dotation K0) qui porte cette victoire — au-dessus de 10 J la lognormale
suffit. Fits par seed (pas de pooling inter-seed) ; échantillons par
seed élargis aux 5 derniers instantanés espacés de ≥ 150 pas (≫
espérance de vie ~15 pas, populations quasi indépendantes ; licite en
régime stationnaire). Corps de NW : Fisk 5/5 (λ=100, r² 0,94-0,96) ;
corps de K : Fisk par AIC mais visuellement piqué avec plateau de
petites entités (r² pondéré 0,39-0,55) — la revendication « corps de K
en Fisk » est la plus faible du lot. Renouvellement : persistance du top
décile < 0,2 dès Δt=50, 0,00 à Δt≥200 ; espérance de vie 14,8 ± 0,1 pas.

Figures : lots `<batch>_lot/figures/` (cascades_rank_size refondu,
volume_double_pareto, revenue_fits, distribution_fits,
top_decile_renewal) ; synthèse `m4_soc_synthese_lots/figures/`
(volume_exponents = régression des paramètres double-Pareto sur N,
soc_criteria_table avec colonnes x_c et max/pop). Régénération :
`lab/batch_report.py --all-m4 --force` (lots indépendants → lancer en
parallèle, ≤ 6 processus).

### 2026-07-17 — Âge au décès lognormal ; K en deux régimes (mélange de 2 lognormales) ; NW plein échantillon en gamma ; la coupure du revenu est plus raide qu'exponentielle

**Résumé : quatre verdicts statistiques nouveaux, tous par seed (5/5)
sur les lots de campagne T=4000. (1) ÂGE AU DÉCÈS : lognormal 5/5 sur
les deux échantillons demandés — toutes morts (σ_log ≈ 1,06, échelle
≈ 8,3 pas) et morts d'âge > 5 décalées de −5 (σ_log ≈ 1,14, échelle
≈ 10,4 pas), r² 0,97-0,99. L'exponentielle est nettement battue : la
mortalité n'est PAS sans mémoire, le risque de décès dépend de l'âge
(cohérent avec l'accumulation de levier). (2) CAPITAL K plein
échantillon (sans troncature au corps) : mélange de 2 lognormales
gagne l'AIC 5/5 — régime étroit ~99-100 J, σ_log 0,10-0,11, ~89-90 %
de la masse (l'attracteur K*) + régime large ~87 J, σ_log 0,37-0,43,
~10-11 % (entités déstabilisées/jeunes). Confirme l'hypothèse « deux
régimes entre hauts et bas capitaux ». (3) NW plein échantillon :
gamma 5/5 (forme 1,41-1,45, échelle ≈ 68-70 J) — le Fisk ne gagnait
que sur le corps tronqué. (4) COUPURE DU REVENU au-delà du mode
(~12,7 J à λ=100) : le test exponentiel direct exp(−(x−mode)/T) donne
T ≈ 7,1 ± 0,3 J/pas mais r² 0,73-0,81 seulement, et l'AIC sur la
queue décalée est gagné par weibull_min 5/5 : en semi-log la densité
est convexe vers le bas — la coupure est PLUS RAIDE qu'une
exponentielle (type Weibull k>1 / compatible coupure lognormale).
L'énoncé « coupure exponentielle » est une bonne approximation de
premier ordre mais le fit global lognorm 5/5 (revenus > 10 J) reste
la meilleure description.**

Figures : `<batch>_lot/figures/age_at_death_fits.png`,
`distribution_fits.png` (panneaux K et NW plein échantillon + mélange
2 lognormales), `revenue_fits.png` (panneau « coupure exponentielle » ;
version avec ce panneau visible uniquement dans le lot λ=100
`20260715_155159_76b0c26e_lot`, voir note de concurrence ci-dessous).

**Note de concurrence entre sessions (2026-07-16/17) :** une seconde
session de travail a fait évoluer en parallèle les figures des lots
(bins adaptatifs à effectifs égaux + IC de Wilson 68 %, loi tronquée
α=2,43±0,01 s_c=827±132 sur les cascades, dPlN sur le volume a=1,28
b=6,56 r²=0,94 — convergent avec les résultats ci-dessus, version
« empirique » de revenue_fits, figures d'espérance de vie instantanée
par taille/levier) et a régénéré la synthèse (16/07 16:36). Ses
versions sont conservées dans les lots λ=10, λ=30 et les lots du
16/07 (`20260716_*_lot`) — NE PAS les régénérer avec batch_report.py
sans sauvegarde. Incident : un rebuild `--force` lancé le 17/07 13:54
a écrasé une partie des figures standard des lots
`20260716_151943_3d153308_lot` et `20260716_161030_229387bf_lot`
(macro→revenue_distributions ; les figures custom de l'autre session
y sont intactes) avant d'être stoppé. Le lot λ=100
(`20260715_155159_76b0c26e_lot`), dont l'export avait été supprimé
(par l'autre session ou manuellement — à confirmer), a été reconstruit
intégralement le 17/07 (13:58-14:12) avec la version courante de
batch_report.py.

Complément (2026-07-17, après-midi) : sur consigne, le fit EXPONENTIEL de
l'âge au décès est désormais tracé explicitement sur
`age_at_death_fits.png` (3 lots régénérés) — un seul paramètre
(T = 15,2 pas toutes morts, 19,3 pas morts > 5, à λ=100) contre deux pour
la lognormale, mais rejet sans ambiguïté : ΔAIC +2,3·10⁴ à +7,5·10⁴ et
densité convexe en semi-log (queue plus lourde que toute exponentielle).
Le verdict lognormal ne tient pas à la souplesse paramétrique.
Intégration au rapport : les figures des lots T=4000 sont intégrées dans
`reports/01_soc_final/main.tex` (version « complétée le 17 juillet
2026 », 15 p.) — 13 figures ajoutées, §7 refondu (lois distributionnelles
précisées), nouvelle §5.1 (volume double-Pareto), annexe de traçabilité
des lots. Les figures de synthèse du rapport sont recalculées sur les
3 lots de campagne exclusivement (la synthèse du lab, régénérée le 16/07
par l'autre session, inclut des lots exploratoires supplémentaires —
pente max∝N^0,55 au lieu de 0,59 et un point pop/λ≈19,8 issus de ces
lots). Successeur du modèle : `m4b_credit_soc_mini/` (réduction minimale,
voir son README) — m4_credit_soc_fable passe en référence lecture seule.

### 2026-07-17 (soir) — Retouches sur annotations PDF d'Anatole : le revenu est corps exponentiel × queue Pareto ; K en Burr XII ; NW en gamma généralisée ; figures cascades/volume sans analyse de coupure

Anatole a annoté `reports/01_soc_final/main.pdf` (copie conservée :
`main_annote_20260717.pdf`). Retouches appliquées dans
`lab/batch_report.py` puis 3 lots régénérés (5 figures chacun) et
rapport recompilé :

1. **Cascades** : plus aucune analyse de coupure sur la figure — loi de
   puissance discrète seule (α, z de Vuong, r² hors taille 1).
2. **Volume** : abandon de la branche montante et du dPlN — fit de la
   seule branche descendante (pente −2,12±0,02 à λ=10 → −2,30 à λ=100,
   r² 0,99), mode ≈110-120 J marqué comme borne ; pas d'interprétation
   de l'épaulement. Synthèse volume_exponents refaite (pente + mode).
3. **Revenu** : « le corps est en exponentielle et la queue en pareto »
   — VÉRIFIÉ. Nouveau modèle composite MLE à 3 paramètres (densité
   ∝ exp(−(x−10)/T) jusqu'à un raccord x_b, puis ∝ x^{−α}, continue) :
   il bat la lognormale par AIC 5/5 SUR LES 3 LOTS (ΔAIC +70 à +800
   par seed). Le verdict « lognormal 5/5 » de la veille est donc
   RENVERSÉ par ce modèle composite (jamais testé jusque-là : seules
   les familles pures l'avaient été). Paramètres λ=100 : T=22,3±1,6
   J/pas, x_b=25,1±0,5 J, α=8,96±0,28 (r² 0,96-0,97) ; x_b≈25 J stable
   sur la gamme ; α≈8,5-10 (queue raide, pas « sans échelle »).
4. **K/NW** : abandon total du mélange de 2 lognormales (5 params >
   tolérance 4, objectif 3). Familles ≤3 params (ajout gengamma, burr) :
   K = Burr XII 5/5 sur les 3 lots (c≈15-17, d≈0,6, échelle≈104 J ;
   r² 0,63-0,93 — le plateau bas-K reste au-dessus du fit) ;
   NW = gamma généralisée (gengamma 5/5 à λ=100, gengamma/gamma
   partagés aux petites tailles).
5. **Âge au décès** : figure réduite au seul fit lognormal (params, r²).

Rapport mis à jour en conséquence (§5.1 volume, §7 verdicts, légendes,
note de révision, limites). Figures : `<batch>_lot/figures/` +
`reports/01_soc_final/figures/lot100_*.png`, `lots_volume_exponents.png`.
