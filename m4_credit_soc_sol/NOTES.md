# Journal de recherche M4 — workspace `m4_credit_soc_sol`

Une hypothèse par entrée. Chaque entrée sépare les faits vérifiés des inférences.

## 2026-07-13 — Baseline M4 existante : excellente droite hors taille 1, mais support trop court pour établir une SOC

**Résumé : confirmé pour le marqueur descriptif, infirmé comme preuve de SOC : sur
`m4_first_s0` après burn-in (t >= 500), la régression brute fréquence–taille hors
taille 1 a R²=0,977, mais elle ne porte que sur les tailles 2 à 7 et 99,2 % des
avalanches sont des singletons.**

Faits vérifiés sur les artefacts disque existants : population moyenne par fenêtre
de 500 pas = 167,4 / 158,9 / 151,7 / 156,4 ; la fenêtre [1000,1500) est sans
tendance notable (pente -0,004 entité/pas). Après t=500 : 14 919 avalanches,
max=7, 0,80 % multi-entités ; comptages {1:14799, 2:71, 3:30, 4:11, 5:5,
6:2, 7:1}. Régression log fréquence–log taille : toutes tailles R²=0,957,
hors taille 1 R²=0,977. Sur [1000,2000], R² hors taille 1=0,913.

Inférence : le marqueur demandé est réel mais, seul, trop facile à satisfaire sur
six abscisses. Il doit rester affiché ; le verdict SOC exigera aussi un support
étendu, le test LR corrigé et le scaling en taille finie.

## 2026-07-13 — Protocole H×X1×G2 avant exécution

**Résumé : test nouveau du plancher purement contractuel (`d0=0`) combiné à
l'objectif revenu et aux chocs sectoriels ; M3 a testé séparément H, X1 et G2,
pas leur interaction.**

Condition de conclusion avant run non trivial : un probe multi-seeds T=1000 suffit
à conclure que la combinaison nue mérite ou non une validation longue si, après
t=300, (a) la population est bornée sans atteindre le garde-fou, (b) le cutoff et
la fraction multi-entités dépassent clairement la baseline actuelle (max>7 sur
plus d'une seed, ou max agrégé >=20), et (c) l'effet ne vient pas d'une extinction
quasi totale (population médiane post-burn-in > 50 et pas d'avalanche proche de la
population entière). Si ces conditions échouent, aucun T supplémentaire sur cette
combinaison nue n'est requis : on passe à une boucle explicite de lente
accumulation du crédit puis relaxation par pertes.

Fait préalable : ce run n'est pas une répétition M3. H avait l'objectif richesse
et pas le choc sectoriel ; X1 gardait `d0=28` ; G2 gardait l'objectif richesse.

## 2026-07-13 — H×X1×G2 probe : plancher contractuel prometteur, validation longue justifiée

**Résumé : confirmé au stade probe, pas encore SOC : avec `d0=0`, T=1000 et
trois seeds, le régime est borné autour de 312–322 entités post-burn-in et les
cutoffs 10/11/20 dépassent 7 sans effondrement ; la robustesse de la droite hors
taille 1 échoue toutefois sur une seed (R²=0,829).**

Faits vérifiés (t>=300) : seeds 0/1/2, population moyenne 311,8/315,8/321,7 ;
max 10/11/20 ; fraction multi 2,39 %/1,85 %/1,77 % ; max/pop médiane
3,2 %/3,4 %/6,3 %. R² hors taille 1 = 0,984/0,931/0,830. Aucun run n'est une
extinction ou une avalanche quasi totale.

Inférence : le retrait du plancher abstrait laisse la dette contractuelle porter
seule mortalité et propagation. L'interaction mérite T plus long ; le mauvais R²
de la seed 2 interdit tout verdict de robustesse à ce stade.

Décision d'implémentation vérifiée ensuite : `d0` a été retiré de `config.py`,
`bankruptcy.py`, `simulation.py` et de tout `src/m4`; le moteur emploie désormais
une instance locale de `random.Random(seed)` via `ModelRNG`. Huit tests couvrent
le retrait, l'isolation/reproductibilité du RNG, le bilan global, la pureté des
snapshots, le carnet, le point fixe de cascade et le LR discret corrigé.

## 2026-07-13 — Protocole confirmatoire temporel et causal avant exécution

**Résumé : cinq seeds sectorielles T=4000 testent la robustesse temporelle ;
trois ablations iid T=4000 testent si la queue dépend de la corrélation imposée.**

Condition de conclusion avant runs non triviaux : cette campagne suffit à
conclure sans prolonger davantage T sur le mécanisme si les quatre fenêtres de
1000 pas après burn-in donnent une population sans dérive persistante, si au
moins 4/5 seeds sectorielles ont R² hors taille 1 >0,90, un cutoff >7 et un LR
discret puissance/lognormale tronquée qui ne rejette pas la puissance, sans
cascade >50 % de la population. L'ablation iid permet de conclure que le signal
est endogène plutôt qu'imposé si elle conserve un support multi-entités et des
diagnostics de queue comparables ; sinon la sectorialité reste un déclencheur
causal nécessaire et cette dépendance doit être rapportée. Quelle que soit
l'issue, le scaling en taille finie restera une campagne distincte requise par
le brief, pas une raison de prolonger arbitrairement ces trajectoires.

## 2026-07-13 — H×X1×G2 confirmatoire : marqueur R² robuste, loi de puissance robuste infirmée

**Résumé : confirmé pour le marqueur principal descriptif, infirmé pour la SOC
robuste : 5/5 seeds sectorielles T=4000 ont R² hors taille 1 >0,90 et max
16–21, mais le LR discret corrigé puissance/lognormale tronquée rejette la
puissance sur 2/5 seeds ; l'iid retombe à max 6–9.**

Faits vérifiés après burn-in t=1000 : population moyenne sectorielle
313,8–321,4 ; fraction multi 1,76–2,15 % ; max 16/17/18/18/21, soit seulement
5,1–6,7 % de la population médiane (pas d'effondrement) ; R² hors taille 1
0,908/0,913/0,962/0,963/0,974. Ajustement discret conditionné à s>=2 : deux
seeds rejettent la puissance au profit de la lognormale tronquée (p=0,035 et
0,007), trois sont non conclusives (p=0,141–0,562). En iid, max=6/7/9 malgré
R²=0,945–0,992 : la corrélation sectorielle est nécessaire au cutoff observé.

Inférence : la dette contractuelle produit une accumulation/propagation réelle,
mais trop amortie pour une queue robuste. Le critère R² seul serait ici un faux
positif si on annonçait une SOC.

## 2026-07-13 — Protocole zéro-recouvrement avant exécution

**Résumé : tester si supprimer le recouvrement des actifs résiduels transforme
les pertes de créance en relaxation assez forte, sans ajouter de variable d'état.**

Condition de conclusion avant run : trois probes sectoriels T=1500 suffisent à
retenir le zéro-recouvrement pour validation longue si, après t=500, au moins
deux seeds ont max>=30, R² hors taille 1 >0,90 et aucune cascade >50 % de la
population médiane. Si le cutoff reste <30 partout ou si une extinction/bimodalité
systémique apparaît, cette règle est rejetée sans prolongation et une boucle
d'appétit de crédit lentement pilotée sera l'étape suivante. Ce test n'a pas été
fait dans M3 : son « Jb » était lam=30, pas `fail_residual="destroy"`.

## 2026-07-13 — Zéro-recouvrement : infirmé, pertes plus sèches mais cutoff inchangé

**Résumé : infirmé : détruire tous les actifs résiduels donne max 15/20/15 et
n'améliore ni le cutoff ni le LR ; la règle n'est pas prolongée.**

Faits vérifiés sur trois seeds T=1500, t>=500 : population moyenne
351,6–366,9 ; R² hors taille 1=0,931–0,960 ; max/pop=4,3–5,4 %. Deux LR sur
trois favorisent significativement la lognormale tronquée (p=0,018 et 0,006).
Aucune extinction, mais zéro seed ne satisfait max>=30.

Inférence : le recouvrement des résidus n'est pas l'amortisseur décisif. Le
levier doit être lentement poussé vers une zone de propagation puis relaxé par
la contagion elle-même.

## 2026-07-13 — Protocole d'appétit de crédit adaptatif avant exécution

**Résumé : introduire un seul état global A : cible de capital A*K*(r), A monte
de 0,002/pas (plafond 3) et est multiplié par exp(-5*décès_propagés/N) après
chaque résolution.**

Histoire causale pré-spécifiée : les périodes sans propagation accroissent
lentement le levier ; une cascade détruit des créances et réduit immédiatement
l'appétit, donc le réseau se reconstruit avant la relaxation suivante. Les
racines indépendantes ne réduisent pas A : seul le canal endogène mesuré par
`_build_avalanches` ferme la boucle.

Condition de conclusion avant run : trois probes sectoriels T=2000 suffisent à
retenir ce mécanisme si au moins deux seeds ont max>=30, R² hors taille 1>0,90,
un A qui visite l'intérieur de [1,3] (pas collé à une borne), et aucune cascade
>50 % de la population médiane. Si A reste à une borne, produit max<30 partout,
ou provoque des effondrements bimodaux, cette paramétrisation est infirmée ; le
résultat sera journalisé avant toute variante.

## 2026-07-13 — Appétit adaptatif A*K*(r) : infirmé, mauvaise variable de contrôle

**Résumé : infirmé : A se colle presque au plafond (moyenne 2,77–2,79) et les
cutoffs diminuent à 11–12 ; aucun probe n'atteint max>=30.**

Faits vérifiés sur trois seeds T=2000, t>=500 : population moyenne 316,8–326,1 ;
R² hors taille 1=0,952–0,981 ; max/pop=3,4–3,8 % ; A visite [1,95,3] mais passe
l'essentiel du régime près de 3. Un LR rejette la puissance (p=0,022), deux sont
non conclusifs. La condition pré-spécifiée échoue sur le cutoff.

Inférence : multiplier la cible productive augmente simultanément K et la dette ;
dans ce régime l'effet stabilisateur du capital domine la fragilité de bilan.
Le feedback doit agir sur la concentration des expositions, pas sur le capital
productif brut.

## 2026-07-13 — Protocole de concentration locale avant exécution

**Résumé : limiter chaque prêteuse à trois contreparties emprunteuses, en gardant
la fusion par paire et toutes les autres règles, afin que chaque exposition reste
matérielle dans son portefeuille.**

Condition de conclusion avant run : trois probes sectoriels T=1500 suffisent à
retenir la concentration locale si au moins deux seeds ont max>=30 et R² hors
taille 1>0,90, sans extinction ni cascade >50 % de la population médiane, et si
le volume de crédit reste au moins égal à 50 % du mécanisme contractuel nu
(éviter de répéter l'ablation F confondue de M3). Si le marché s'éteint, si le
cutoff reste <30 partout ou si le régime devient bimodal/systémique, la piste est
infirmée sans prolongation.

## 2026-07-13 — Concentration locale : infirmée par divergence et carnet dense

**Résumé : infirmé et runs arrêtés à t>1000 : population 5604–5896 et carnet
153 k–440 k, très loin du régime stationnaire de référence (~320).**

Faits vérifiés dans les logs à t=1000 : seeds 0/1/2, population
5819/5896/5604, contrats 358090/152997/439752, morts du pas 6/5/7. Les trois
processus ont été terminés avant T=1500 : la divergence rendait déjà impossible
le calcul post-burn-in demandé. Le transfert des créances d'une prêteuse faillie
peut aussi créer des contreparties hors limite, donc la topologie ne reste pas
réellement bornée malgré `merge_pairs`.

Inférence : comme l'ablation F de M3, cette règle change trop le volume et la
démographie pour isoler la concentration. Elle n'est pas un candidat SOC.

## 2026-07-13 — Protocole crédit de liquidité avant exécution

**Résumé : verser le principal en L plutôt qu'en K dans le régime sans d0,
revenu myope et chocs sectoriels ; le besoin productif ne se referme plus par le
prêt, ce qui permet une lente accumulation contractuelle.**

Condition de conclusion avant run : trois probes T=1200 suffisent à retenir la
piste si au moins deux seeds ont, après t=400, max>=30, R² hors taille 1>0,90,
population médiane >50, aucun événement >50 % de cette population, et un volume
de crédit non éteint. Une extinction, une population <50, une avalanche
quasi-totale ou max<30 partout infirme la règle sans prolongation. M3-C n'est
pas un doublon : il gardait d0, l'objectif richesse et les chocs iid.

## 2026-07-13 — Crédit de liquidité : infirmé, marché actif mais cascades plus courtes

**Résumé : infirmé : le marché reste actif (volume 926–1103/pas) mais les
cutoffs sont 6/6/8, donc aucun probe n'atteint max>=30.**

Faits vérifiés sur trois seeds T=1200, t>=400 : population moyenne 271,5–277,3 ;
R² hors taille 1=0,947–0,975 sur seulement 5–7 tailles distinctes ; max/pop
2,2–2,9 %. Les trois LR sont non conclusifs, mais le support est plus court que
celui du mécanisme contractuel nu.

Inférence : accumuler de la dette liquide n'expose pas assez le capital réel aux
chocs sectoriels et raccourcit les cascades.

## 2026-07-13 — Protocole seuil de capital avant exécution

**Résumé : défaut de solvabilité si NW < 10 % des dettes contractuelles ; le
crédit charge le ratio sans changer NW à l'émission, les pertes font franchir le
même seuil aux créancières.**

Justification quantitative préalable : dans les cinq runs sectoriels longs du
mécanisme nu, le minimum transversal NW/dette vaut 0,004–0,115 selon la seed et
le quantile 1 % vaut 0,043–0,227. Un seuil 10 % mord donc la frange fragile sans
mettre mécaniquement toute la population en défaut.

Condition de conclusion avant run : trois probes sectoriels T=2000 suffisent à
retenir le seuil pour validation longue si au moins deux seeds ont max>=30,
R² hors taille 1>0,90, population médiane >50, aucune avalanche >50 % de celle-ci
et pas de régime collé au seuil avec mortalité immédiate de toutes les nouvelles.
Si les max restent <30, si la population s'effondre, ou si les événements sont
bimodaux/quasi totaux, le seuil 10 % est infirmé sans réglage post-hoc.

## 2026-07-13 — Seuil de capital 10 % : infirmé, racines ajoutées mais branchement sous-critique

**Résumé : infirmé : ≈3,2–3,4 racines prudentielles/pas apparaissent, mais les
cutoffs restent 11/9/18 ; aucune seed n'atteint max>=30.**

Faits vérifiés sur trois seeds T=2000, t>=500 : population moyenne 300,7–312,2 ;
R² hors taille 1=0,909–0,991 ; max/pop=3,0–5,8 %. Un LR rejette la puissance
(p=0,011), deux sont non conclusifs. Il n'y a ni extinction ni effondrement :
le régime est simplement sous-critique.

Inférence : le mécanisme de seuil est actif mais la masse de bilans proches du
seuil est insuffisante pour un ratio de branchement critique.

## 2026-07-13 — Test de principe seuil de capital 30 % avant exécution

**Résumé : tester une marge prudentielle de 30 % comme hypothèse distincte pour
augmenter la densité de bilans proches du seuil, sans grille fine post-hoc.**

Condition de conclusion avant run : trois probes T=1500 ferment cet axe. Le
mécanisme n'est retenu que si au moins deux seeds atteignent max>=30 avec R²
hors taille 1>0,90, population médiane >50 et aucun événement >50 % de celle-ci.
Max<30 sur deux seeds, extinction ou avalanches quasi totales suffisent à
infirmier l'axe des seuils sans tester 20 %, 25 %, etc.

## 2026-07-13 — Seuil de capital 30 % : infirmé, axe des seuils fermé

**Résumé : infirmé : max 9/13/12 sur trois seeds ; renforcer le coussin ne
rapproche pas le régime d'un cutoff 30+.**

Faits vérifiés sur trois seeds T=1500, t>=500 : population moyenne 275,8–281,4 ;
R² hors taille 1=0,934–0,978 ; max/pop=3,3–4,7 %. Les LR sont non conclusifs,
mais portent sur seulement 8–10 tailles distinctes. Aucune condition de succès
pré-spécifiée n'est atteinte.

Inférence : les défauts prudentiels ajoutent des racines plus qu'ils
n'augmentent le branchement des pertes. L'axe est fermé sans grille fine.

## 2026-07-13 — Protocole de scaling en taille finie avant exécution

**Résumé : tester le meilleur mécanisme (contractuel nu, sectoriel) à lam=5,
10,20 ; trois seeds par taille, T=2500 aux deux bords et T=4000 déjà disponible
à lam=10.**

Condition de conclusion avant run : la campagne suffit à conclure au scaling si
la médiane inter-seeds du cutoff (max et p99 des avalanches multi-entités) croît
avec la population post-burn-in entre lam=5,10,20, sans croissance du ratio
max/pop vers une extinction systémique. Une médiane plate/décroissante, ou des
max pilotés par une seule seed, infirme le scaling. Le décalage T est contrôlé
par les probes T=1000 et les longs T=4000 à lam=10 ; aucune extrapolation ne sera
faite si les fenêtres temporelles ne sont pas stables.

## 2026-07-13 — Scaling positif, verdict final : pré-critique prometteur, SOC robuste non établie

**Résumé : confirmé pour le scaling et le dépassement de 7, infirmé pour la loi
de puissance robuste : N≈160/318/639 donne max médian 7/18/24 et p99 multi
6/9,8/13 sans effondrement, mais le LR rejette la puissance sur 2/5 seeds à
λ=10.**

Faits vérifiés : à λ=20, max 37/23/24 et max/pop 3,6–5,8 % ; les trois LR sont
non conclusifs (p=0,319–0,883), R² hors taille 1=0,898/0,942/0,976. À λ=10,
R²=0,908–0,974 sur 5/5 mais deux rejets LR (p=0,035 et 0,007). L'iid donne
max 6–9. Les pentes de population sont faibles et le renouvellement du top est
réel (persistance 0–13,8 % sur ~1500 pas).

Distributions (échelle existante de 13 familles, 5 seeds λ=10) : NW mélange de
deux lognormales 4/5, gamma généralisée 1/5 ; K réparti entre exponentielle,
Dagum et lognormales ; revenu mélange lognormal 4/5, lognormale 3p 1/5. Formes
identifiables mais moins stables que Fisk/lognormal/dPlN en M3.

Inférence finale : le mécanisme contractuel sans d0 est extensif et proche d'un
régime critique, mais la sectorialité reste nécessaire au grand cutoff et la
famille de queue n'est pas robuste. Annoncer « SOC obtenue » violerait la règle
preuve avant conclusion. Rapport : `reports/m4_research/REPORT.md`.
