# Synthèse finale — réplication critique du modèle M2

Workspace : `anciens_modeles/m2_fable/` (agent Fable, isolé de l'agent concurrent).
Date : 3 juillet 2026.
Code : `src/m2/` (31 tests verts, `python3 tests/run_all.py`).
Rapports LaTeX compilés : `reports/01…05/main.pdf`.
Données : `experiments/m2/results/` (~40 runs, JSON de validation sous
`results/validation/`).

## Réponses aux questions posées

### Le modèle M2 a-t-il été implémenté fidèlement ?
**Oui** — séquence à 7 phases, règle de marché `w*(ρ)` symétrique, transfert
au prorata, telles qu'écrites au §2.2 du rapport de conception ; les
ambiguïtés ont été tranchées par des conventions documentées (C1–C10, rapport
02) et les variantes par des champs de configuration nommés. À noter : le
prototype qui a produit les résultats [E7c] du rapport n'implémentait PAS
cette spécification (volume de prêt hérité du WIP, créances de la faillie
annulées au lieu de transférées) ; la réplication a donc testé les deux
règles de faillite.

### Quelles hypothèses du rapport sont confirmées ?
1. **Population bornée endogènement** : N(t) plat, faillites ≈ naissances,
   N*/λ = 166,4 identique à λ=10 et λ=30 (extensivité exacte). Aucune
   capacité de charge exogène.
2. **Queue d'exposant stable** : α(NW) ≈ 2,6–2,8, sans dérive sur 6000 pas
   (11 fenêtres, IC bootstrap) — le critère que le WIP ratait (5,4 → 3,1)
   est atteint. Valeurs de [E7c] répliquées.
3. **Classes dynamiques, non démographiques** : corr(âge, log NW) = 0,09–0,15 ;
   90–95 % du top décile né dans les 1000 derniers pas ; survie du top
   11–17 % par 1000 pas ; queue présente à âge contrôlé. Bien au-delà des
   seuils du rapport.
4. **Fenêtre de naissance** : ses bornes mordent exactement comme prédit
   (σ=0,15 → mortalité ≈ 0, population 15–20k croissante).

### Quelles hypothèses sont infirmées ?
1. **H1 (corps exponentiel)** : infirmée en forme ET en mécanisme. Fisk gagne
   l'AIC tronqué partout (NW) ; l'alternative [BM] éq. 7 (inverse-gamma) est
   massivement rejetée (ΔAIC +4236). Surtout, le drift mesuré du corps est
   ascendant (+4,15/pas ; [YR] exige un drift descendant A₀>0) : le corps est
   un régime de transport réinjecté/absorbé, pas un équilibre de Boltzmann.
   Nuance : le corps de NW est *quasi* exponentiel (QQ linéaire,
   med/mean = 0,69 ≈ ln 2) — mais cette coïncidence se dégrade déjà à
   σ=0,35 (med/mean 0,55).
2. **H2 (μ stabilisé par la boucle SOC crédit↔cascades)** : non soutenue.
   Le modèle nul SANS crédit produit une queue identique (exposant, stabilité,
   corps, renouvellement) ; les cascades sont un Poisson étroit (max 21,
   p99 = 17, pas de queue lourde) ; corr(concentration du crédit, faillites
   suivantes) ≈ 0 ; aucune transition k=3 visible. La stabilité de l'exposant
   est un effet démographique (GBM tué au plancher × mélange d'âges,
   mécanisme type Reed), pas un effet de crédit.
3. **§3.5 (même exposant pour revenu et NW)** : infirmée — α(revenu) ≈ 4,1–4,7
   ≈ 2α(w)−1 (le revenu reste dominé par l'extraction √w jusque dans le top
   décile), contre α(NW) ≈ 2,7. L'écart était déjà dans les chiffres [E7c],
   non relevé.
4. **« Loi de puissance ≫ log-normale » ([E7c])** : artefact d'outillage. Le
   test LR historique conclut « Pareto » même sur des données log-normales
   pures (R = +575, p ≈ 0, même ordre que les +566/+694 cités). Avec le LR
   corrigé (log-normale tronquée en x_min), la log-normale gagne dans TOUTES
   les fenêtres de tous les runs. La queue de M2 est mieux décrite comme
   log-normale tronquée à exposant effectif stationnaire.

### Le corps exponentiel apparaît-il ?
**Non au sens statistique** (critère §6.1 : échec partout, trois variables,
tous seeds). **Presque au sens pratique** pour NW à σ=0,25 : histogramme
décroissant dès le premier bin, QQ-plot exponentiel linéaire, med/mean = ln 2.
Pour le revenu — la variable de la thèse énoncée — le corps est en bosse
(log-normale, med/mean = 0,92) : échec net.

### La queue de Pareto est-elle stable ?
**L'exposant effectif est remarquablement stable** (2,6–2,8 sur 6000 pas,
3 seeds, toutes ablations en régime). Mais (i) la loi de puissance n'est
jamais préférée à la log-normale tronquée par le test corrigé, et (ii) la
stabilité n'a rien à voir avec le crédit ou la SOC : elle est portée par le
renouvellement démographique. Réponse de l'exposant à σ : 3,8 / 2,7 / 2,2–2,4
pour σ = 0,15 / 0,25 / 0,35 (monotone, comme le prédit aussi bien Kesten que
le mécanisme démographique).

### Les classes sont-elles dynamiques ou démographiques ?
**Dynamiques**, sans ambiguïté (voir plus haut). Détail instructif : personne
ne meurt riche — on quitte le top par chocs et charges, puis on meurt pauvre ;
le critère « mortalité du top > 0 » du rapport était mal posé, le
renouvellement est la bonne mesure.

### La population est-elle bornée endogènement ?
**Oui**, dans la fenêtre de naissance (σ ≥ 0,25 pour w₀=30). Hors fenêtre :
croissance sans borne (σ=0,15) ou population très réduite (σ=0,35,
N* ≈ 200–450, risque d'extinction non observé mais plausible). Et le bornage
tient sans crédit (modèle nul : N* ≈ 1900).

### Le modèle est-il robuste sans réglage fin ?
**Dans la fenêtre, oui ; la fenêtre elle-même est un calage.** Sur la grille
σ×ε₀/w₀×k : la forme qualitative (corps Fisk quasi exponentiel, queue stable,
classes dynamiques) est insensible à ε₀/w₀ (0,05–0,5) et à k (2–6) ; elle
répond à σ de façon monotone et lisse. Mais l'existence même du régime exige
σ dans une fenêtre étroite (facteur < 2), et DEUX conventions se révèlent
porteuses : la moyenne géométrique des taux (en arithmétique, le marché du
crédit meurt : 176 prêts en 2000 pas, tous mort-nés) et — pour la santé
numérique — la règle de faillite (le transfert au prorata fait exploser le
carnet : 12,4 millions de contrats sur une case de grille, contre ~600 en
annulation, sans aucune différence distributionnelle).

## Découvertes non prévues par le protocole
1. **Deux outils statistiques hérités biaisaient les conclusions** (LR
   pro-Pareto ; AIC anti-exponentiel par troncature non renormalisée). Les
   deux ont été corrigés et testés sur données de contrôle ; le premier
   invalide la preuve de queue de [E7c].
2. **La règle de faillite M2 est non stationnaire** (prolifération
   combinatoire des contrats par scission au prorata) — invisible dans le
   prototype qui annulait.
3. **Le crédit est distributionnellement neutre** dans tout le régime étudié
   — le résultat central de cette réplication. Le générateur effectif de la
   forme « Boltzmann-Pareto » de M2 est le triplet {choc σ, extraction −
   dépréciation, plancher d₀ + naissances Poisson}.

## Quelles expériences lancer ensuite ?
1. **Chercher un régime où le crédit compte** : marché plus dense
   (rounds ≫ N/k), taux plus élevés sans tuer le marché (borne géométrique
   relevée), chocs corrélés entre entités (le choc i.i.d. moyenne le risque
   de portefeuille — des chocs agrégés pourraient réactiver les cascades),
   λ plus faible (moins de renouvellement démographique → place au canal
   financier).
2. **Théorie du corps Fisk** : dériver la distribution stationnaire du
   processus w (GBM + √w − δw, tué à NW=0, réinjecté à ε₀) et vérifier si
   Fisk(1,45) en est la vraie forme ; expliquer la coïncidence med/mean ≈ ln 2
   à σ=0,25.
3. **Invariance d'échelle de temps** (δ → δ/2 à 2T) — non testée ici.
4. ~~Consolidation des contrats par paire~~ — **fait** : variante
   `merge_pairs` implémentée et validée (fusion au taux moyen pondéré ; flux
   exactement préservés ; trajectoire macro identique à la baseline ; carnet
   borné à 9 514 contrats contre 43 977). À utiliser par défaut si la règle
   prorata est conservée.
5. **Grille à 3 seeds** sur la ligne σ=0,25 pour des IC sur les réponses de
   forme.

## Verdict d'ensemble
M2 atteint trois de ses quatre cibles phénoménologiques — mieux que le WIP
sur chacune — mais par un mécanisme plus simple que celui qu'il revendique :
c'est un modèle démographique de renouvellement (type Reed) habillé d'un
marché du crédit qui, dans le régime exploré, ne laisse aucune empreinte
distributionnelle. La thèse SOC (H2) n'est pas réfutée dans l'absolu mais
elle est actuellement sans objet : le phénomène qu'elle devait expliquer
existe sans elle. Le corps exponentiel (H1) est réfuté en mécanisme ; sa
quasi-réalisation en forme à σ=0,25 est le meilleur point de départ pour la
suite théorique.
