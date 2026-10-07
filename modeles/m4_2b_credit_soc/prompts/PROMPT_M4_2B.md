# Prompt de recherche M4.2B — émergence et contrôle des queues de revenus d'intérêt sous contrainte de cascades critiques

## Mission

Conçois, implémente, vérifie et étudie **M4.2B**, successeur expérimental direct de M4.2.

M4.2B poursuit deux objectifs scientifiques **simultanés**.

### Objectif A — distribution des revenus d'intérêt

Étudier la distribution cross-sectionnelle instantanée des **intérêts effectivement perçus** par les entités et construire un régime dans lequel sa **queue supérieure puisse être de type Pareto**, de manière endogène, robuste et statistiquement défendable.

Le **corps** de la distribution n'est pas imposé. Il peut être, selon les mécanismes et les données :

- lognormal ;
- exponentiel ;
- mélange de lognormales ;
- double-Pareto lognormal (DPLN) ;
- lognormal avec raccord Pareto ;
- exponentiel avec raccord Pareto ;
- double-lognormal avec raccord Pareto ;
- ou toute autre famille motivée par les résultats.

En revanche, l'objectif structurel est plus précis pour la partie haute :

> **il doit exister, si le modèle le permet, une région non dégénérée de l'espace des paramètres ou des mécanismes dans laquelle la queue des intérêts perçus soit compatible avec une loi de Pareto sur une plage statistiquement crédible.**

Ne fabrique pas cette queue par construction directe, par tirage exogène d'une loi de Pareto ou par calibration ad hoc sur l'exposant observé. Elle doit émerger de la dynamique économique du modèle.

Si une configuration particulière ne présente pas de queue Pareto, établis-le honnêtement. Le travail consiste alors à déterminer **où**, **quand** et **pourquoi** une queue Pareto apparaît ou disparaît, d'abord en explorant les paramètres du modèle, puis, seulement si nécessaire, en interrogeant explicitement ses mécanismes.

L'objectif n'est pas d'atteindre un exposant numérique fixé à l'avance. L'objectif est de déterminer si l'on peut obtenir un **contrôle de la queue** : une ou plusieurs variables du modèle doivent permettre de déplacer de manière reproductible l'exposant, la plage de scaling ou la transition vers la queue Pareto.

Une relation du type

θ ↦ α̂_I

est intéressante si θ est un paramètre ou mécanisme économiquement interprétable et si α̂_I représente réellement une queue Pareto, et non un artefact de coupure, de seuil, de mélange temporel ou de taille finie.

La fonction η est **un objet d'intérêt particulier**, parce qu'elle contrôle l'intensité des tentatives d'appariement et donc potentiellement la densification du réseau de crédit. Mais le travail de M4.2B **n'est pas limité à η**.

### Objectif B — préserver les cascades de faillites en loi de puissance

M4.2B ne doit pas obtenir la distribution recherchée des revenus d'intérêt au prix de la disparition du mécanisme critique hérité de M4/M4B/M4.2.

La **structure en loi de puissance des avalanches de faillites doit rester active** dans le régime final revendiqué.

Il faut donc suivre en parallèle :

- la distribution des tailles d'avalanches ;
- son éventuelle queue en loi de puissance ;
- l'exposant estimé et son incertitude ;
- la coupure de taille finie ;
- le nombre de racines ;
- la profondeur ;
- le rapport de branchement ou diagnostics équivalents déjà employés dans M4.2 ;
- la mortalité et la stationnarité de la population.

Une configuration qui produit une belle queue Pareto des intérêts mais détruit la structure de loi de puissance des cascades n'est **pas** un succès final de M4.2B. Elle peut être un résultat intermédiaire utile, à condition d'être identifiée comme telle et d'expliquer le compromis observé.

Réciproquement, conserver les avalanches critiques sans obtenir de régime à queue Pareto pour les revenus d'intérêt ne répond pas entièrement à la nouvelle question.

### Question générale

> **Quels paramètres et, si nécessaire, quels mécanismes institutionnels de cette société de crédit permettent de faire émerger et de contrôler une queue Pareto des revenus d'intérêt, tout en conservant une dynamique endogène d'accumulation-relaxation et des avalanches de faillites à structure de loi de puissance ? Quel rôle spécifique joue la fonction η dans cette organisation ?**

Les résultats doivent rester reproductibles entre graines, persistants entre snapshots et fenêtres temporelles, robustes à la taille du système, distincts d'un simple changement d'échelle, distincts d'un déplacement de coupure de taille finie, distincts d'une variation de la masse en zéro, distincts d'un transitoire de croissance, compatibles avec une population et une comptabilité non pathologiques, causalement intelligibles.

Un résultat négatif local est valide. Cartographie d'abord l'espace pertinent ; si les paramètres ne suffisent pas, formule ensuite des hypothèses sur les mécanismes et teste-les avec des ablations propres.

---

## 2. Modification constitutive de M4.2B : le principal devient arithmétique

M4.2 utilisait une cible de capital géométrique. M4.2B change explicitement cette institution.

Pour deux entités de capitaux avant transaction K_ℓ > K_b > 0, la plus riche est prêteuse ℓ et la plus pauvre emprunteuse b. Le transfert doit désormais **égaliser leurs capitaux** :

K_target = (K_ℓ + K_b) / 2

Le principal est donc exactement

**q_A = (K_ℓ − K_b) / 2**

et après transfert : K_ℓ' = K_b' = (K_ℓ + K_b) / 2.

Cette règle n'est pas une approximation et ne doit pas être reformulée comme une utilisation de K*(r). Elle constitue précisément la nouvelle institution M4.2B. Justification économique : pour une production strictement concave F_γ(K)=A K^γ (0<γ<1), elle maximise F_γ(K_ℓ−q)+F_γ(K_b+q) sous conservation du capital des deux parties.

Tests indispensables : K_ℓ'+K_b'=K_ℓ+K_b ; K_ℓ'=K_b' ; q_A=(K_ℓ−K_b)/2 ; conservation des valeurs nettes ; comparaison automatique sur grille (K_ℓ,K_b) du principal arithmétique au principal géométrique de M4.2.

## 3. Le taux d'intérêt est conservé en baseline, mais placé sous surveillance explicite

Pour m_ℓ=Aγ K_ℓ^(γ−1), m_b=Aγ K_b^(γ−1), le taux reste r_ℓb=√(m_ℓ m_b) = Aγ(K_ℓK_b)^((γ−1)/2). Cette formule détermine le taux ; elle ne détermine plus le principal. Le contrat reste nominal et perpétuel, service c=r·q_A.

Le taux n'est pas supposé neutre : le principal arithmétique augmente structurellement q, donc c, même à r inchangé. Mesurer systématiquement r, q, rq et, à la création/fusion d'un contrat, rq/K_b' et rq/F_γ(K_b'). Par entité : service total dû, service/capital, service/production, taux moyen pondéré, taux max porté, nombre de contrats, fraction des défauts liés à une incapacité de service.

Rechercher les anomalies : taux extrêmes pour petits capitaux, service comparable/supérieur au capital ou à la production de l'emprunteuse, défaut quasi immédiat, concentration de la queue dans quelques contrats extrêmes. Pas de plafond arbitraire sur r en baseline. Si pathologie réelle, traiter la règle de taux comme institution candidate à l'ablation, avec alternatives dérivées et testées proprement.

## 4. Régime principal : dépréciation et chocs faibles

δ=0.01 (1%/pas). Choc ξ~N(−σ²/2,σ²), K←K·e^ξ, σ=0.01 en baseline. Ne jamais recalibrer σ sur les distributions de queue. Vérifier avant campagne la distribution de e^ξ−1 (moyenne, écart-type, moyenne/médiane absolues, quantiles 5/50/95%), à titre descriptif seulement.

## 5. Échelles, stationnarité et liberté sur K0

K*_aut = ((1−δ)A/δ)^(1/(1−γ)). Avec δ=0.01,A=1,γ=1/2 : K*_aut=9801, largement au-dessus de K0=25 historique. K0 n'est pas sanctuarisé — paramètre scientifique à part entière (distance à l'échelle endogène, transitoires, démographie). Distinguer changement d'échelle/temps de relaxation, véritable changement de forme, effet stationnaire durable. Ne jamais confondre distribution large, transitoire de croissance, régime stationnaire, queue Pareto authentique, mélange de cohortes d'âges différents.

## 6. Variable scientifique centrale : intérêts instantanément perçus

I_i,t^recv = montant effectivement perçu par i pendant le service des intérêts du pas t (paiement réel, après paiement partiel éventuel). Objet principal : distribution cross-sectionnelle par snapshot {I_i,t^recv}. Ne pas pooler aveuglément le temps. Masse en zéro p0(t)=P(I=0) mesurée séparément de la queue conditionnelle I|I>0.

## 7-8. η : levier privilégié mais non exclusif ; exploration paramétrique

R_t=⌊η(N_t^mkt)⌋. Baseline η(N)=N. Famille linéaire η_ρ(N)=ρN, ρ=1 baseline, grille pilote suggérée {0.125,0.25,0.5,1,2,4,8}. Famille non linéaire η_{ρ,β}(N)=ρ·N_ref·(N/N_ref)^β si justifiée. Paramètres à explorer : η, γ, λ, δ, σ, K0, éventuellement A. Interactions ciblées (η×K0, η×γ, η×σ, η×δ, η×λ) à partir d'hypothèses, pas de grille cartésienne exhaustive.

## 9. Mesurer la chaîne causale

paramètres → activité de marché → réseau → (r,q,rq) → revenus d'intérêt → fragilité et cascades. Pour η : fréquence d'interaction → topologie/forces du réseau → concentration des créances → queue des intérêts et propagation des pertes.

## 10. Analyse statistique des revenus d'intérêt

Séparer masse en zéro / corps / queue. Confronter au moins : lognormale, exponentielle, Pareto (pure/tronquée), lognormale+Pareto, exponentielle+Pareto, mélange de lognormales+Pareto, DPLN, autres si motivés. Ne jamais mélanger exposant CCDF (κ) et exposant densité (α=κ+1). Seuil I_min choisi par procédure reproductible (MLE/scan KS/bootstrap), jamais visuellement. Rapporter n, fraction, exposant+IC, seuil, étendue, qualité d'ajustement, comparaison aux concurrents, coupure éventuelle. Unité de réplication = snapshot, pas l'individu poolé.

## 11. Régime réussi et contrôle de queue

Contrôle = un paramètre déplace reproductiblement exposant/seuil/largeur/coupure de la queue Pareto des intérêts, sans changer simplement l'échelle. Conditions : queue défendable, variation substantielle et reproductible entre graines, effet persistant entre fenêtres, effectif suffisant, effet non réductible à un changement de moyenne/coupure/masse en zéro, stationnarité, cohérence causale avec réseau/r/q/rq — ET simultanément avalanches en loi de puissance robuste, non artefact d'effondrement, accumulation-relaxation active, population/bilans non pathologiques.

## 12. Comparaison M4.2/M4.2B

À paramètres identiques : principal géométrique (M4.2) vs arithmétique (M4.2B). Quantifier volume par transaction, distribution des taux, service rq, durée de vie des contrats, fréquence des défauts, densité du réseau, intérêts reçus, concentration, queues.

## 13-14. Cartographie des paramètres, taille de système, démographie

γ (concavité), η (marché), λ (démographie/taille), δ (relaxation), σ (fluctuations), K0 (distance à l'échelle), A (échelle). Baseline δ=0.01, σ=0.01 reste la référence principale. Contrôles appariés quand plusieurs paramètres changent l'échelle du capital. Distinguer exposant asymptotique / coupure de taille finie / réseau trop petit / queue apparente due à quelques entités dominantes.

## 15. Les avalanches restent une contrainte centrale

Conserver définition causale d'une avalanche et mécanique de faillite M4.2 en baseline. Analyser distribution des tailles, CCDF, exposant, seuil, coupure, comparaisons, stabilité graines/fenêtres, dépendance à la taille, profondeur, générations, racines, rapport de branchement. Un régime qui épaissit la queue des intérêts mais détruit la structure des avalanches est un échec au regard du double objectif (mais peut être instructif).

## 16. Parcours suggéré (non contraignant)

A. audit/reproduction M4.2 — B. implémentation minimale (cible arithmétique) — C. baseline (γ=1/2, δ=0.01, σ=0.01, η(N)=N) — D. exploration paramètres — E. approfondissement η — F. domaine conjoint — G. mécanismes si nécessaire — H. robustesse et synthèse.

## 17. Liberté de recherche et refonte justifiée

Exploiter d'abord les degrés de liberté existants. Refonte lourde acceptable si : hypothèse explicite, motivée par diagnostic antérieur, comparée à la baseline, ablation isolant l'effet, invariants comptables préservés, pas de Pareto/exposant codé en dur, évaluée sur les deux objectifs.

## 18. Discipline scientifique

Distinguer fait observé / inférence / hypothèse / incertitude. Ne jamais sélectionner après coup graines/snapshots/seuils donnant le résultat attendu. Protocole figé après pilotes, résultats négatifs conservés.

## 19. Efficacité de calcul

Profiler avant runs longs, budget parallélisme ≤6 processus, reproductibilité via config.json+graine.

## 20. Parité graphique avec M4.2 et simulation_lab

Réutiliser le code de génération de figures existant (simulation_lab, adaptateur M4.2). Mêmes définitions, conventions de snapshot, transformations, normalisations, échelles, binning, CCDF, unités, diagnostics d'avalanches. Ajouter les figures propres à M4.2B (distributions d'intérêts, queue Pareto, r/q/rq, cartes du domaine conjoint).

## 21. Livrables

Moteur autonome, config sérialisable, tests, adaptateur simulation_lab, scripts de snapshots/analyse, protocole figé + journal, résultats bruts, figures M4.2+M4.2B, tableaux de synthèse (distributions, queue Pareto intérêts, queue avalanches), diagnostics r/q/rq/réseau/stationnarité, rapport LaTeX+PDF, README de reproduction.

## 22. Comportement agentique attendu

Inspecter le dépôt avant de coder. Agir dès que l'information est suffisante. Le parcours de la section 16 est une suggestion. En cas de résultat surprenant, vérifier code/invariants/échelle/stationnarité/cohortes/taux/principaux/rq/seuil/queue/effets de taille finie avant d'expliquer économiquement.

---

*(Version condensée du prompt intégral fourni le 2026-07-30. Le texte complet fait foi en cas de doute sur une formulation exacte : voir `PROMPT_M4_2B_COMPLET.md` dans ce même dossier (22 sections, double objectif A/B, 17 questions finales §21). Toutes les formules, contraintes numériques et exigences méthodologiques ci-dessus sont reproduites fidèlement.)*
