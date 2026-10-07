# Prompt de recherche — M4 : avalanches auto-organisées

Destiné aux agents de développement (Claude Fable 5, Codex Sol / GPT-5.6). Lire
aussi `Prompting Claude Fable.md` et `Prompting Codex Sol.md` dans ce dossier
pour le style d'exécution attendu de chaque modèle ; les deltas spécifiques par
agent sont en fin de document.

## Lecture préalable obligatoire

- `/home/anatole/jupyter/modeles/anciens_modeles/m3_credit_soc/NOTES.md` — journal complet du
  programme M3. C'est la source de vérité sur ce qui a déjà été testé et
  fermé. Ne pas relancer un test que ce journal a déjà tranché sans le citer
  et expliquer pourquoi le refaire apporte quelque chose de nouveau.
- `/home/anatole/jupyter/modeles/anciens_modeles/m3_credit_soc/reports/05_negative_results/main.tex`
  et `reports/07_income_rule/main.tex` — synthèses rédigées des résultats
  négatifs et du mini-protocole X1.
- `src/m4/*.py` (ce dépôt) — moteur actuel, fork de M3. `config.py` documente
  chaque champ et pourquoi ses valeurs par défaut sont ce qu'elles sont.

## Contexte

M3 est un modèle multi-agents de société de crédit : entités avec liquidité
`L` et capital productif `K`, prêts bilatéraux, faillites en cascade,
recherche d'un régime SOC (self-organized criticality) sur la taille des
avalanches de faillites. Programme M3 clos le 2026-07-06, tout répliqué,
6 rapports rédigés. M4 est un nouveau dépôt (fork de M3) où deux réglages
d'ablation M3 sont devenus la baseline : chocs sectoriels corrélés
(`shock_rho_sector=0.8`, variante G2b) et objectif de revenu myope
(`objective="income"`, protocole X1). Un premier run simple (`m4_first_s0`,
seed 0, T=2000) a été exécuté et confirme la population effondrée (~135) et
les avalanches non triviales mais petites (max=7) — cohérent avec M3.

## Objectif

Obtenir un régime où les avalanches de faillites (composantes connexes du
graphe de pertes, cf. `bankruptcy.py::_build_avalanches`) sont produites par
un mécanisme d'**accumulation-relaxation endogène** — pas par amplification
d'une corrélation imposée de l'extérieur — et suivent une distribution de
taille en loi de puissance robuste, avec des tailles significativement
au-delà de 7 (potentiellement 100+ selon la taille du système). Le système
doit continuer à produire des distributions de **taille des entités** (NW,
K — pas la taille des avalanches) et de **revenu** dont la **famille** de loi
colle aux régularités empiriques déjà établies dans ce programme (voir
"Contraintes à préserver").

**Refonte radicale autorisée.** Vous n'êtes pas limités à ajuster des
paramètres de M4 tel quel. Toute partie du mécanisme peut être repensée si
l'analyse le justifie et si le changement est documenté et comparé à la
baseline actuelle : la règle de faillite (`bankruptcy.py`), la topologie de
marché (`market.py`), la structure du choc, le nombre et la nature des
variables d'état par entité (L et K sont-elles toutes les deux nécessaires,
ou une variable d'état unique / une structure différente suffit-elle à porter
le canal de fragilité ?), la règle de taux, etc. Rien n'est sanctuarisé sauf
ce qui est listé ci-dessous comme contrainte.

**Attention à la tension simplification ↔ objectif SOC.** `L` est
aujourd'hui la seule variable qui porte l'asymétrie nominal/réel (le défaut
d'une entité solvable mais illiquide) — c'est le canal dont le régime H
(ci-dessous) montre qu'il est le seul du programme à produire des défauts de
liquidité en nombre. Fusionner `L` et `K` en une seule variable est une
simplification légitime à évaluer, mais si elle supprime cette asymétrie,
elle supprime aussi le canal sur lequel repose le mécanisme SOC visé —
répondre à « peut-on retirer L ? » seulement après avoir mesuré ce que ça
coûte au mécanisme candidat, pas comme une simplification gratuite.

## Ce que M3 a établi (points de départ, pas des vérités intangibles)

Ce qui suit vient des runs et rapports M3. Ce sont des faits observés sous
les conditions testées, pas des conclusions à accepter sans regard critique —
l'un d'entre eux (le point 4 ci-dessous, sur le réseau) a déjà dû être
recadré après relecture par l'utilisateur : la portée exacte d'un résultat
négatif compte autant que le résultat lui-même. Si vous avez de bonnes
raisons expérimentales de contredire un point ci-dessous, documentez-le et
avancez — ne le traitez pas comme un mur.

1. **Corrélation imposée ≠ auto-organisation.** G1 (choc macro) et G2/G2b/G2c
   (choc sectoriel, ρ_s de 0 à 0,8) montrent une réponse *continue* :
   var/mean des avalanches passe de 0,07 (iid) à 0,84 (ρ_s=0,8), max jusqu'à
   72, mais **jamais de transition, jamais var/mean > 1** — le système
   amplifie proportionnellement la corrélation qu'on lui injecte, il ne
   s'auto-organise pas (NOTES.md, entrées 2026-07-04 tardive et 2026-07-06).
   Le run M4 baseline actuel (G2b + X1, max=7) est une instance de ce même
   constat, pas un point de départ vers la SOC.
2. **Le canal de liquidité (défaut nominal, NW ≥ 0 mais illiquide) est
   quasiment toujours nul.** Sur toute la grille M3 (45 cellules + G2b/c),
   des défauts de liquidité en nombre n'apparaissent que dans deux régimes :
   `s=0,9` (résiduel, 1 à 3 événements) et surtout **H (plancher endogène,
   d0=0)** où la dette contractuelle remplace le plancher exogène comme seul
   mécanisme de mort et où 71 défauts de liquidité apparaissent sur un seul
   seed. C'est le seul régime du programme où la fragilité nominale/réelle
   voulue par la conception existe *en nombre*, pas seulement dans le code.
3. **Décision de conception retenue pour M4 : `d0` est supprimé (fixé à 0)
   comme baseline permanente, pas comme option d'ablation.** Le run H de M3
   (d0=0, NOTES.md 2026-07-05) a montré que le système se borne seul par
   l'insolvabilité contractuelle (pop stationnaire ≈5570, d/b=0,98, seul
   régime avec des défauts de liquidité en nombre — 71 sur un seed) : on sait
   donc que le plancher exogène n'est pas nécessaire à l'existence du régime.
   Documenter ce choix dans `config.py` comme les défauts déjà figés
   (`shock_rho_sector`, `objective`) plutôt que comme un champ d'ablation
   réglable. Extension possible mais non imposée : router la dette de
   subsistance née de ce plancher endogène vers de vraies créancières du
   marché plutôt que vers un puits abstrait, ce qui exposerait le plancher
   lui-même aux cascades — piste intéressante si utile au mécanisme SOC, pas
   un prérequis pour la décision ci-dessus.
4. **Le réseau de crédit a un effet réel et attendu sur les cascades — ne
   pas généraliser un résultat étroit en « le réseau n'a pas d'effet ».**
   Activer le crédit (vs l'ablation B, sans marché) multiplie les cascades :
   c'est le canal même qui les rend possibles en connectant les entités entre
   elles, et c'est attendu. Ce que la dose-réponse F/F''/baseline de M3
   (2026-07-04 tardive) a réellement fermé est plus étroit : *à volume de
   crédit égal*, changer la règle d'appariement (assortative / random /
   random_lender) ne change rien de mesuré au-delà de ce volume. Une refonte
   de la topologie doit donc viser un changement de *structure* du réseau
   (pas seulement de règle d'appariement à volume constant) si elle veut
   tester autre chose que ce que M3 a déjà tranché ; et toute comparaison
   doit contrôler le volume de crédit actif pour ne pas re-mesurer l'effet
   trivial credit-actif-vs-inactif.
5. **Le crédit est causal démographiquement, pas distributionnellement**, en
   baseline richesse (A vs B) ; ce n'est qu'avec la règle de revenu (X1) que
   le crédit devient distributionnellement actif (Gini 0,62–0,69 vs 0,56).
   Toute mécanique candidate doit expliquer si/pourquoi elle préserve ou
   change cet effet.

## Contraintes à préserver

- **Familles de distribution déjà établies**, à ne pas casser sans le
  signaler explicitement comme un changement assumé : corps de NW ~ Fisk
  (log-logistique), revenu ~ dPlN (double Pareto-lognormale, effet Reed de
  mélange d'âges × croissance multiplicative), K ~ lognormal. "Coller aux
  distributions réelles" veut dire coller à la *famille* (ces lois sont les
  régularités empiriques reconnues pour richesse/revenu en économie), pas
  fitter des paramètres numériques d'un jeu de données externe précis —
  aucune cible numérique externe n'est actuellement enregistrée dans ce
  programme.
- **Invariants comptables I1–I9** du moteur (seuil de faillite
  `L+K+claims-debts-d0 ≥ -tol_nw`, cf. `bankruptcy.py::net_worth` — avec
  `d0=0` décidé ci-dessus, ce seuil devient simplement NW ≥ -tol_nw ; cascade
  avec point fixe garanti ; snapshot en lecture pure ; etc. — voir docstrings
  `bankruptcy.py`, `contracts.py`, tests `tests/`). Toute refonte du moteur
  doit préserver un jeu d'invariants équivalent et le tester.
- **Reproductibilité** : `random.Random(seed)` isolé, jamais le RNG global ;
  artefacts sur disque (`config.json`, `summary.json`, `series.csv`,
  `avalanches.csv`, `snap_t*.npz`) comme seule source pour les figures —
  jamais l'état mémoire de la simulation (invariant déjà en place dans
  `metrics.py`, à conserver dans toute extension).

## Pièges d'outillage à ne pas reproduire (NOTES.md 2026-07-03)

1. Test LR Pareto/lognormale **sans renormalisation** de la lognormale
   tronquée → biais pro-Pareto systématique.
2. AIC du corps de distribution avec des familles **non tronquées** sur un
   corps qui est en réalité tronqué → biais anti-exponentiel.
3. Transfert prorata des créances de faillite sans fusion par paire
   (`merge_pairs`) → explosion combinatoire du carnet de prêts (observé
   jusqu'à 12,4M de contrats sur la grille M3).
4. Moyenne arithmétique des taux d'intérêt au lieu de géométrique → le
   marché de crédit s'éteint de lui-même.
5. Critère de "mortalité instantanée du top" — structurellement nul, mesurer
   plutôt le renouvellement entre fenêtres temporelles.

## Critères de succès

Une taille maximale d'avalanche élevée seule **ne suffit pas** (c'est
manipulable en augmentant la taille du système). Le signal SOC recherché est :

1. **Scaling en taille finie** : le cutoff de la distribution de taille
   d'avalanches croît avec la taille du système (population stationnaire ou
   nombre d'entités actives), signature classique d'un régime critique.
2. **Ajustement en loi de puissance qui survit au test LR corrigé** (avec la
   renormalisation correcte des alternatives tronquées — piège n°1
   ci-dessus), pas seulement une droite à l'œil sur un graphe log-log.
3. `var/mean > 1` (sur-Poisson) est une condition **nécessaire mais faible** —
   ne pas s'arrêter là, M3 atteint déjà 0,84 sans que ce soit suffisant.
4. Les distributions de richesse/revenu gardent une famille reconnaissable
   (voir contraintes ci-dessus), avec le changement documenté si une famille
   change.
5. Le mécanisme proposé a une **histoire causale endogène** articulable en
   une phrase (pas juste "on a poussé un paramètre de corrélation plus
   haut") — feedback d'accumulation puis de relaxation porté par la
   dynamique du modèle lui-même.
6. **Piège à nommer explicitement : un effondrement quasi total n'est pas de
   la SOC.** La façon la moins chère d'obtenir de "grosses avalanches" dans
   un modèle de cascade de levier est un régime bimodal (une masse de
   défauts de taille 1 + un effondrement occasionnel de tout le système) —
   ce n'est ni une loi de puissance ni un régime critique, c'est une
   extinction. Les critères 1–2 gardent déjà contre ça, mais un run qui
   rapporte "avalanche de 100+ obtenue !" doit être vérifié contre ce
   scénario avant d'être compté comme un succès.

## Livrables attendus

- Modifications du moteur dans `src/m4/` (ou nouveau module si la refonte le
  justifie), avec tests couvrant les invariants touchés.
- Au moins un run comparatif baseline-vs-mécanisme-candidat avec figures
  (réutiliser les recettes déjà établies : `simulation_lab/plot_utils.py`
  et `webapp/mpl_figures.py` — log-binning adaptatif, erreur bootstrap,
  double régression avec/sans taille 1, écrites pour `cascades_rank_size.png`
  dans m3_credit_soc — à copier/adapter, pas à réinventer).
- Une entrée de journal dans `modeles/m4_credit_soc/NOTES.md` (à créer sur le modèle
  de celui de M3 : un résumé d'une ligne en tête de chaque entrée, confirmé
  ou infirmé, et pourquoi) pour chaque hypothèse testée, y compris les
  échecs — les négatifs sont aussi précieux que les positifs dans ce
  programme (cf. `reports/05_negative_results` de M3, qui existe pour cette
  raison).

## Quand s'arrêter et demander

- Avant toute modification qui changerait une convention déjà figée et
  documentée comme telle ailleurs dans le repo (ex. `s`, `c` en M3 sont
  explicitement "figés, ne plus retoucher" — une décision équivalente en M4
  doit être signalée avant d'être écrasée).
  Avant un run dont le coût estimé dépasse largement les runs déjà observés
  dans ce programme (le run H de M3 seul a coûté 11 350 s / seed) : signaler
  l'estimation avant de lancer.
- Si l'analyse mène à conclure qu'aucune mécanique testée ne produit de SOC
  robuste : c'est un résultat négatif valide, à documenter comme tel plutôt
  qu'à masquer en gonflant `var/mean` par des réglages ad hoc.

## Deltas spécifiques par agent

**Claude Fable 5** : tenir `modeles/m4_credit_soc/NOTES.md` comme mémoire de travail
au fil de l'eau (une entrée par hypothèse testée, cf. Livrables). Avant de
rapporter un résultat comme acquis, auditer chaque affirmation contre une
sortie d'outil réelle de cette session (pas de statut de progression
fabriqué). Pour les runs longs, utiliser des subagents à contexte frais pour
vérifier les invariants et les ajustements statistiques plutôt que
l'auto-critique seule.

**Codex Sol (GPT-5.6)** : garder le prompt de travail court — ne pas répéter
une règle déjà énoncée une fois ici. Poser explicitement, avant chaque run
non trivial, la condition d'arrêt ("qu'est-ce qui, dans le résultat, permet
de conclure sans lancer un run supplémentaire ?"). Séparer clairement dans
les livrables ce qui est un fait vérifié par un test/run de ce qui est une
inférence.
