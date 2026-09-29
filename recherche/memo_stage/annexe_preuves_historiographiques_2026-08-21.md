# Annexe de preuves historiographiques — batch du 21 août 2026

**État :** annexe de preuves conservée séparément et référencée par le mémo maître — mise à jour du 24 août 2026  
**Fonction :** rendre auditables les affirmations historiographiques du mémo maître,
en séparant témoignage de l'auteur, code effectivement exécuté, résultats bruts,
figures, rapports d'agents et interprétation rétrospective.

## A. Règles de preuve appliquées

Cette annexe emploie les catégories suivantes :

- **T — témoignage d'Anatole :** information donnée directement par l'auteur du
  stage. Elle établit son intention, son souvenir d'une décision ou le sens qu'il
  donnait à une variable ; elle ne prouve pas à elle seule un résultat numérique.
- **C — code :** règle effectivement inscrite dans une version du moteur. Le code
  prouve une institution ou une équation, mais pas qu'elle a été exécutée dans
  toutes les campagnes décrites par un rapport.
- **R — résultat brut :** manifeste `run.json`, CSV ou autre sortie rattachable à
  une configuration et une graine.
- **F — figure :** représentation d'un résultat brut ou agrégé. Elle sert de trace
  visuelle et de source d'hypothèse ; un ajustement dessiné n'est pas, seul, une
  preuve de la famille statistique.
- **A — texte d'agent :** rapport, journal ou commentaire produit par un agent.
  Il est cité comme proposition, calcul ou compte rendu, puis contrôlé contre C,
  R, F et les réactions d'Anatole.
- **D — décision observable :** prompt suivant, mécanisme conservé, branche
  promue, réduction, nouvelle expérience ou arrêt de campagne.

Une affirmation devient un fait du dossier quand sa nature est correctement
qualifiée et qu'elle est soutenue par la source appropriée. Par exemple, « Anatole
avait l'intention de faire émerger les rôles » est établi par T ; « le code ne
déclare aucun type banque » est établi par C ; « une séparation apparaît sur une
figure » est établi par F/R ; « cette séparation correspond à deux classes
économiques réelles » demanderait une validation que les sources présentes ne
fournissent pas.

## B. Corrections apportées par les témoignages des 21 et 24 août

| Identifiant | Fait ou correction à conserver | Source | Conséquence pour le récit |
|---|---|---|---|
| T01 | L'idée « monnaie = transfert de droit à profiter de l'exergie » justifie la possibilité de modéliser énergétiquement une société économique. | Témoignage écrit d'Anatole, 21 août 2026 | Ne pas la réduire à une simple hypothèse interne au moteur ni prétendre qu'elle est démontrée par le modèle. |
| T02 | L'analogie de la hache doit être conservée entière comme donnée de conception. | Témoignages écrits d'Anatole, 21 août ; formulation antérieure dans `recherche/note_de_travail/latex/note.tex:97-103` | Conserver dépense initiale, surplus futur, usure, entretien, bilan de puissance et transposition capitaliste–ouvrier. |
| T03 | La puissance extractrice est la capacité d'une entité à grossir en fonction de sa taille et de sa technologie. | Correction écrite d'Anatole, 24 août 2026 | La traiter comme un flux de croissance dépendant de l'état de taille et de la règle technologique. Écarter l'ancienne paraphrase en termes d'apport énergétique journalier presque constant. Les formes `alpha*sqrt(P)` puis `A*K^gamma` en sont des instanciations successives. |
| T04 | Aucun modèle n'a déclaré des types d'agents « banque » ou « travailleur ». Toutes les entités obéissaient à des règles similaires ; la question était de comprendre l'émergence d'une classe et son éventuelle analogie avec un mécanisme réel. | Témoignage écrit d'Anatole, 21 août ; `note.tex:138-158` pour les observations contemporaines | Parler d'étiquettes interprétatives appliquées à des comportements ou trajectoires, jamais de types inscrits dans le code. |
| T05 | Le retrait de la banque explicite visait dès mars à tester l'émergence spontanée des rôles. | Témoignage écrit d'Anatole, 21 août 2026 | Le retrait est une expérience de conception, pas seulement une simplification logicielle. |
| T06 | Le modèle du 27 avril est la continuation intellectuelle du WIP sans banque. | Témoignage écrit d'Anatole, 21 août 2026 | Raconter une reprise/élagage, non une reconstruction indépendante. |
| T07 | Les deux implémentations M2 étaient concurrentes, lancées à partir du même prompt. | Témoignage écrit d'Anatole, 21 août 2026 | Les traiter comme réplications adversariales apparentées ; leur accord gagne du poids mais elles ne sont pas causalement indépendantes du cahier des charges commun. |
| T08 | La branche M4 Fable a été retenue parce que le mécanisme d'avalanche y apparaissait, que le système était établi comme « pré-SOC » et que ses statistiques étaient cohérentes. | Témoignage écrit d'Anatole, 21 août ; sources M4 en section F | Relier la promotion vers M4B à une décision scientifique, pas à une commodité de code. |
| T09 | Le branching ratio était une cible avant la lecture tardive de Bouchaud. Sa proximité avec 1 est caractéristique d'un SOC, mais ce n'est pas l'unique ni nécessairement la statistique principale du travail. | Témoignage écrit d'Anatole, 21 août 2026 | Bouchaud consolide le vocabulaire et l'interprétation ; il ne crée pas rétrospectivement la cible. Ne pas appeler `b` « la statistique centrale » sans nuance. |
| T10 | L'erreur structurelle du premier `k` est d'avoir gardé fixe le nombre de tentatives de création de contrats quand `N` variait. L'activité de marché doit dépendre de `N`; `k=3` est une complexité inutile pour un toy model et des paires aléatoires suffisent. | Témoignage écrit d'Anatole, 21 août ; code comparé en sections D et E | Requalifier les seuils anciens en propriétés du protocole ancien, non en lois structurelles du mécanisme réduit. |
| T11 | Pour la queue d'intérêts, Anatole voyait graphiquement une queue de Pareto. Les erreurs méthodologiques des agents — en particulier `seuil/2` au lieu de `seuil*2` — ont compliqué sa caractérisation. | Témoignage écrit d'Anatole, 21 août ; `m4_2b_credit_soc/JOURNAL.md:636-793`; figures en section G | Le passage à « Pareto comme hypothèse de travail » n'est pas un refus de la preuve visuelle, mais une séparation entre observation graphique et test confirmatoire devenu trop peu puissant. |
| T12 | La première expérience consacrée à l'effet rebond est le modèle dynamique ancien. Les « banques » y ayant été requalifiées comme artefacts de modélisation, le modèle a perdu sa crédibilité et le programme est reparti de loin, pas de zéro. | Témoignage écrit d'Anatole, 21 août ; campagne `alpha_plus_10pct` en section C | M4.3Live est une reprise tardive de l'expérience de rebond sur une lignée reconstruite, non la toute première expérience de rebond. |
| T13 | L'équivalence pratique « revenu usuel = somme des intérêts reçus » s'est imposée progressivement. | Témoignage écrit d'Anatole, 21 août 2026 | Ne pas lui attribuer une date de naissance unique ; distinguer présence du flux d'intérêts et promotion tardive en observable distributionnel principal. |
| T14 | Les encadrants ont nourri la réflexion par de longs échanges, puis supervisé et validé le travail. La conception et les décisions sont néanmoins revendiquées par Anatole comme les siennes. | Témoignage écrit d'Anatole, 21 août 2026 | Ne pas attribuer une décision précise à un encadrant sans trace ; distinguer influence intellectuelle, supervision et paternité des choix. |
| T15 | Les ablations M4.3 n'ont pas été tranchées faute de temps ; le stage touche à sa fin et la poursuite de la campagne a été arrêtée. | Témoignage écrit d'Anatole, 21 août ; question encore ouverte dans `m4_3_credit_soc/report/rapport_final.tex:557-581` | La clôture est temporelle, non un verdict selon lequel aucune ablation n'était utile. |
| T16 | Le tout premier moteur date approximativement des 12–13 mars 2026. Le dossier `anciens_modeles/4-05-dynamique/` est bien le modèle dynamique désigné comme première expérience de rebond. | Réponses écrites d'Anatole, 24 août 2026 | Ferme deux incertitudes de datation et d'identification laissées ouvertes dans le batch du 21 août. |

## C. Première expérience explicite sur l'effet rebond

### C.1 Dispositif retrouvé

Le dossier `anciens_modeles/4-05-dynamique/` contient une campagne
`alpha_plus_10pct`, décrite comme « test simple d'effet rebond » dans
`RAPPORT_ELAGAGE_MODELE.md:54-97`. Le test augmente `alpha_min` et `alpha_max`
de 10 %, puis compare le régime post-transitoire à un baseline sur 1 000 pas,
avec burn-in à 500 (`RAPPORT_ELAGAGE_MODELE.md:147-162,204-223`).

Le même dossier contient :

- `experiments/results/rebound_1000_runs.csv` : quatre runs actuellement
  présents, deux graines pour le baseline et deux pour `alpha_plus_10pct` ;
- `experiments/results/rebound_1000_aggregate.csv` : deux observations agrégées
  par variante ;
- `RAPPORT_ELAGAGE_MODELE.md` : tableau et interprétation d'agent ;
- `DYNAMIC_RUNTIME_NOTES.md` : ajout ultérieur d'un pilotage en direct et d'une
  modification de `alpha` pour les entités vivantes.

### C.2 Résultats consignés et discordance de provenance

Le rapport annonce une comparaison « 3 seeds combinés » et donne : extraction
post-500 `16115 → 16942` (+5,1 %), prêts actifs post-500 `22355 → 24992`
(+11,8 %), prêts actifs finaux `22068 → 27623` (+25,2 %), faillites `1474 →
1529` (+3,7 %), cascades `599 → 616` (+2,8 %), Gini du passif +4,1 % et
`P90/P10` du passif +6,3 % (`RAPPORT_ELAGAGE_MODELE.md:204-220`).

Cependant, les CSV actuellement archivés ne contiennent que deux graines par
variante et leurs moyennes ne reproduisent pas exactement tous les nombres du
rapport. Cette discordance doit rester visible. Elle indique soit qu'une troisième
graine a été utilisée puis retirée ou écrasée, soit que le rapport a été construit
à partir d'un état différent des CSV présents. Les résultats du rapport sont donc
une trace historique de l'interprétation qui a guidé la suite, mais pas encore un
tableau brut entièrement reproductible à partir des quatre lignes conservées.

### C.3 Décision et requalification ultérieure

Le rapport interprète la hausse de productivité comme une hausse de l'extraction et
une extension plus forte du réseau de prêts, puis avertit qu'il ne s'agit pas encore
d'une théorie complète avec ressource bornée (`RAPPORT_ELAGAGE_MODELE.md:221-223`).
Selon T12, cette expérience est bien la première consacrée au rebond. Sa force
explicative a toutefois été fortement diminuée quand la séparation « banques /
travailleurs », importante dans le mécanisme interprété, a été requalifiée comme
artefact de cohorte et de modélisation. La lignée M2–M4 ne repart donc pas de zéro :
elle conserve concavité, érosion, crédit, cascades, comparaisons distributionnelles
et démarche de réduction, mais abandonne une grande partie de l'architecture et de
l'interprétation sociale du premier moteur.

## D. Le problème ancien de `k` et de l'intensité de marché

### D.1 Institution ancienne

Dans `anciens_modeles/Modèle_sans_banque/src/simulation.py:745-775`, `k` est la
taille d'un pool local permettant de choisir parmi plusieurs candidats. Le nombre
de tentatives est ensuite borné par une boucle
`range(self.config.max_credit_iterations)`, donc par une quantité configurée
indépendamment de la population. Des annotations contemporaines dans le code
questionnent déjà le choix des meilleurs candidats, proposent des candidats
aléatoires et plusieurs rounds, et demandent « Pourquoi `k*k` ? »
(`simulation.py:758-761`).

Cette institution mélange donc au moins deux effets :

1. la taille de l'information locale ou du pool de rencontre ;
2. une activité agrégée de marché qui ne croît pas nécessairement avec `N`.

Les campagnes anciennes peuvent mesurer avec précision les conséquences de cette
institution, mais elles ne permettent pas d'interpréter `k` comme un seuil absolu
du mécanisme social général.

### D.2 Résultats de sensibilité qui ont fragilisé le « seuil absolu »

Le premier balayage homogène statique trouvait `0/3` runs bornés à `k=2` et
`k=3`, puis `3/3` à `k=4`, avec une densité financière en volume passant de
`0,049` à `0,399` (`rapport_final_sensibilite.tex:218-254`). La lecture visuelle
de `k_sweep_steps1500_eps0.001` a donc fourni une vraie raison expérimentale de
poursuivre l'hypothèse d'une transition.

Le couplage `k × mu` a ensuite montré que `mu=0` permet un régime borné même à
`k=2` et `k=3`, alors que `mu≥0,10` ferme le régime pour tous les `k` testés.
L'extension à 327 runs donne notamment `10/15` à `(k=2, mu=0)` et `8/15` à
`(k=3, mu=0)` ; le rapport conclut que le seuil apparent `k=4` dépendait du choix
`mu=0,05` (`rapport_final_sensibilite.tex:666-700,861-910`).

La conclusion historiographique n'est donc ni « il n'y avait aucun seuil », ni
« k=4 est critique ». Le seuil a été observé dans un protocole précis, puis
requalifié en frontière multidimensionnelle et, plus tard, en partie comme un
artefact d'une intensité de marché mal normalisée.

### D.3 Résolution progressive dans les moteurs suivants

- M4 Fable calcule `n_rounds = n // effective_rounds_div` : l'activité de marché
  dépend explicitement du nombre d'entités (`m4_credit_soc_fable/src/m4/market.py:39-64`).
- Le commentaire de configuration donne une dose-réponse du branching ratio :
  `n/6 → 0,14`, `n/3 → 0,20`, `n/2 → 0,24`, `n → 0,30`, `2n → 0,34`, et fixe par
  défaut un round par tête (`m4_credit_soc_fable/src/m4/config.py:42-49`).
- M4B réduit littéralement cette règle à `for _ in range(n)`
  (`m4b_credit_soc_mini/m4b/model.py:204-233`).
- M4.2 fixe le pool à `POOL_SIZE=2`, définit `eta(N)=N` et effectue une paire
  aléatoire par round (`m4_2_credit_soc/m4_2/model.py:36,210,246-299` ;
  `prompts/PROMPT_M4_2.md:175-179`).
- M4.2B généralise l'activité par
  `eta_{rho,beta}(N)=rho*N_ref*(N/N_ref)^beta`, tout en conservant `k=2`
  (`m4_2b_credit_soc/README.md:10-28`).

Cette séquence matérialise la correction décrite par T10 : dissocier le nombre de
partenaires d'une rencontre (`k=2` suffit) du nombre de rencontres par pas, qui
doit avoir une loi d'échelle explicite en `N`.

## E. Matrice sourcée des transformations de modèles

Les dates sont celles du développement attesté dans les dossiers et journaux ;
elles restent grossières pour mars et pour les copies plus tardives.

| Passage | Date grossière | Transformation du moteur ou du protocole | Question scientifique rendue possible | Sources principales |
|---|---:|---|---|---|
| V1 → versions modulaires/sans banque | avant le 23 → 27 mars | Séparation du moteur en entités, contrats, simulation et statistiques ; retrait de toute banque spéciale, sans déclarer de nouveaux types d'agents. | Une différenciation « banque/travailleur » peut-elle émerger de règles communes ? | T04–T05 ; `anciens_modeles/claude*/README.md`; `anciens_modeles/Modèle_sans_banque/description_modele_actuel.txt`; `note.tex:138-158`. |
| Sans banque → WIP du 27 avril | fin mars → 24–27 avril | Continuation/élagage de la comptabilité actif-passif ; extraction concave, érosion, prêts perpétuels, faillites ; marché encore à nombre maximal d'itérations fixe ; Brownien appliqué à `alpha`. | Quelles interactions minimales bornent le système et comment les sorties répondent-elles aux paramètres ? | T06 ; `note.tex:89-166`; `Modèle_sans_banque/src/simulation.py:745-775`; `modele-27-04-WIP/src/simulation.py:1303-1320`. |
| WIP → expérience dynamique de rebond | fin avril–début mai | Ablations et hausse de 10 % de `alpha`; ajout d'un runtime permettant ensuite des changements de paramètres et d'`alpha` en cours de simulation. | Une hausse de productivité augmente-t-elle l'extraction et/ou l'expansion financière ? | Section C ; `4-05-dynamique/RAPPORT_ELAGAGE_MODELE.md:54-97,204-223`; `DYNAMIC_RUNTIME_NOTES.md:13-54`. |
| WIP/conception → M2 Codex et M2 Fable | 2–3 juillet | Réduction à un stock réel `w`; naissance Poisson, choc multiplicatif centré directement sur `w`, extraction `alpha*sqrt(w)`, service, dépréciation, marché, faillites ; implémentations concurrentes depuis le même prompt. | Un moteur minimal produit-il un corps Boltzmann, une queue Pareto et un rôle causal du crédit ? | T07 ; `m2_fable/src/m2/simulation.py:1-11,38-60`; journaux M2. |
| M2 → M3 | 3–6 juillet | Séparation du stock réel en liquidité `L` et capital productif `K`; choc sur `K`; production répartie entre `K` et `L`; intérêts payés depuis `L`; avalanches causales instrumentées. | Rendre le crédit causal et distinguer pertes de stock, pertes de flux, nominal et réel. | `m3_credit_soc/src/m3/simulation.py:1-16,66-75`; `m3_credit_soc/src/m3/production.py:11-62`. |
| M3 → M4 Fable | 13–14 juillet | Retour à une variable réelle `K`; retrait de `d0`; paiement des intérêts depuis `K`; prêts transférant `K`; taux géométrique et fusion des paires fixés ; faillite `cancel+destroy`; activité de marché proportionnelle à `N`. | Produire une contagion réelle plutôt que des défauts synchronisés et mesurer accumulation–relaxation, profondeur, cutoff et branching. | `m4_credit_soc_fable/src/m4/config.py:1-22,42-64`; `market.py:1-64`; `NOTES.md`; rapport M4. |
| M4 Fable → M4B | 16–18 juillet | Réduction du candidat promu dans un moteur compact ; un round de marché par entité et par pas ; conservation du mécanisme `cancel+destroy`. | Vérifier que les cascades ne dépendent pas de la complexité résiduelle du prototype. | T08 ; `m4b_credit_soc_mini/m4b/model.py:204-233`; tests de parité/réduction. |
| M4B → M4.2 | 27–29 juillet | Fonction de production généralisée `A*K^gamma`; rendement marginal cohérent ; pool d'appariement fixé à deux ; `eta(N)=N`; compteurs de marché séparés ; contrôles de covariance d'échelle. | Tester si `gamma` pilote la pente des avalanches, puis isoler l'effet d'échelle `K0/K*_aut`. | `m4_2_credit_soc/prompts/PROMPT_M4_2.md:175-179,376,535`; `m4_2_credit_soc/m4_2/model.py:9,36,210,246-299`; journal M4.2. |
| M4.2 → M4.2B | 30 juillet–6 août | Cible de principal arithmétique au lieu de géométrique ; taux inchangé ; baseline lente `delta=sigma=0,01`; activité `eta_{rho,beta}`; journal complet des prêts et outils pour intérêts reçus. | Rendre la queue de revenus d'intérêt pilotable sans perdre les cascades. | `m4_2b_credit_soc/README.md:1-28`; prompt et journal M4.2B. |
| M4.2B → M4.3 | 6–11 août | Moteur reproduit par parité ; campagne et statistique de queue restructurées ; `Dagum c` gelé ; exploration de `gamma` avec compensation de `K0`; contrôles de taille/temps. | Trouver un levier augmentant à la fois épaisseur de queue et branching, malgré leur anti-corrélation antérieure. | `m4_3_credit_soc/tests/test_parity_m4_2b.py`; `report/rapport_final.md:258-334`; journal M4.3. |
| M4.3 → M4.3Live-v1 | 17–21 août | `A` et `gamma` deviennent propres à chaque entité et modifiables en direct ; portées `all/new/fraction`; transfert de principal maximisant la production jointe ; fork indépendant, parité sur le chemin homogène ; reprise/bifurcation d'état. | Observer directement la réponse à une amélioration technologique et distinguer effet d'amplitude, effet d'échelle et réponse démographique. | `m4_3live_credit_soc/README.md:1-23`; `prompts/PROMPT_M4_3LIVE.md:87-115,143-202,245-283,422-445`; journal M4.3Live. |
| M4.3Live-v1 → feuille de route v2 | 21 août | Direction du prêt à revoir ; service des intérêts après dépréciation à tester ; retrait des traitements partiels et du plafond `equalization`; instrumentation de la tension renforcée. | Corriger l'institution avant de prolonger l'explication du rebond. Aucun résultat v2 n'est encore produit. | `m4_3live_v2_credit_soc/ROADMAP.md:59-144,439-481`; T15. |

### E.1 Localisation correcte du changement de choc brownien

L'exemple donné oralement associait le changement « choc sur `alpha` → choc sur
`K` » à M4. La comparaison de code conduit à une datation plus précise :

- le WIP du 27 avril modifie `alpha` par
  `alpha *= exp(N(0,sigma))` et porte une annotation signalant un drift positif
  (`modele-27-04-WIP/src/simulation.py:1303-1320`) ;
- M2 applique déjà le choc multiplicatif centré directement au stock réel `w`,
  puis calcule l'extraction à partir de ce stock
  (`m2_fable/src/m2/simulation.py:1-11,50-60`) ;
- M3 appelle explicitement un choc sur `K`, avec composantes macro, sectorielle
  et idiosyncratique possibles (`m3_credit_soc/src/m3/production.py:11-41`) ;
- M4 conserve le choc sur `K` en fusionnant `L/K`.

La différence conceptuelle est bien structurante, mais sa première attestation
dans la lignée réduite se situe donc à M2, pas à M4. M4 l'hérite et la rend plus
visible par le nom unique `K`.

## F. Résultats de la campagne de sensibilité du modèle du 27 avril

La source principale est
`anciens_modeles/modele-27-04-WIP/studies/sensitivity/report/rapport_final_sensibilite.tex`.
Elle décrit 1 479 runs adaptatifs, auxquels s'ajoutent pilotes, OAT, sondes longues
et validations multi-graines. Les résultats ci-dessous sont des résultats de ce
rapport d'agent, recoupés quand possible par les figures et sorties présentes.

### F.1 Transition, activité financière et paramètres numériques

- Dans le cas homogène statique, le balayage initial trouve une transition
  `k=3 → k=4` et un plateau de densité pour `k≥4` : `d_f=0,015`, `0,049`,
  `0,399`, `0,411` pour `k=2,3,4,5`, respectivement
  (`rapport_final_sensibilite.tex:218-254`).
- `epsilon=10^-3` conserve les volumes de référence en accélérant le calcul ;
  `epsilon=10^-2` fait disparaître le réseau dense. Le nombre de prêts mélange
  donc topologie économique et résolution des microcrédits, tandis que le volume
  relatif `V/A` est plus robuste (`:257-275`).
- À `k=3`, une fenêtre de bruit sur `alpha` autour de `0,005–0,02` déclenche un
  réseau actif ; `0,05–0,1` le détruit. À `k=4`, le régime existe déjà sans bruit,
  se densifie jusqu'à environ `0,02`, puis se fragmente (`:278-292`).

### F.2 Frontières couplées et correction des premières lectures

- Pour `k=4`, le balayage fin en taux de création situe une frontière entre
  `lambda=2,0` (3/3 bornés) et `2,5` (1/3) ; la densité reste élevée à `lambda=3`
  malgré la croissance démographique, puis s'effondre vers `lambda≥3,5`.
  Pour `k=3` et bruit nul, aucune valeur `lambda∈[1,5]` n'est bornée
  (`:477-546`).
- La carte `k×mu` invalide le statut absolu de `k=4` : `mu=0` ouvre des régimes
  à `k=2/3`, tandis que `mu>0,10` ferme tous les `k` testés (`:666-700,861-910`).
- La carte `sigma_alpha×k` étendue trouve zéro run borné pour
  `sigma_alpha≥0,035`; `k=3` n'a qu'une fenêtre étroite et dépendante de la
  graine, tandis que `k=6` est le plus résilient (`:912-961`).
- Deux lectures OAT sont corrigées par le multi-graines : `delta_endo=0,02`
  n'est pas un centre densifiant robuste mais une frontière (`p≈0,15`) ;
  `theta=0,5`, d'abord jugé fragile sur une graine, devient robuste (`p≈0,92`)
  (`:1121-1128`).

### F.3 Transitoires longs et régime borné

La configuration `k=3, sigma_alpha=0,005`, jugée encore oscillante à 5 000 pas,
est prolongée à 10 000 pas. Cinq graines sur six satisfont alors le critère de
stationnarité ; les six ont un ratio faillites/créations compris entre `0,966` et
`1,011`. Le rapport requalifie donc la probabilité observée à 1 500 pas comme une
probabilité de convergence rapide, non comme probabilité asymptotique de régime
(`:1130-1224`). La figure
`report/figures/long_run_k3sigma0005_10k_trajectoires.png` rend ce changement de
lecture directement visible.

### F.4 Propriété émergente et limites

- Dans les régimes actifs des cartes `lambda×k` et `k×mu`, la densité financière
  en volume est rapportée autour de `0,24±0,02`, relativement stable malgré les
  paramètres de connectivité (`:1377-1406`).
- La dépréciation unifiée stabilise dans une fenêtre `0,02–0,03`, empêche le régime
  au-delà de `0,05`, puis produit au-delà de `0,12` une extinction qui satisfait
  artificiellement le critère de queue bornée (`:1393-1399`).
- Deux paramètres de reliquéfaction ont un effet mesuré nul sur les horizons
  testés et deviennent candidats à la suppression, mais ce constat ne prouve pas
  leur inutilité dans tous les stress (`:1408-1417`).
- Le rapport reconnaît que les distributions de taille n'ont pas encore été
  comparées en détail aux familles lognormale, Pareto ou mélangées (`:1371-1375`).

Ces résultats répondent à la question « qu'a produit l'organisation Codex/Claude
des campagnes ? » : elle a transformé un seuil unidimensionnel séduisant en
surface de régime, séparé densité de contrats et volume financier, révélé des
transitoires de plusieurs milliers de pas et produit des candidats d'élagage.

## G. Échantillon raisonné de figures et de runs Simulation Lab

Le 21 août, un inventaire local a trouvé **1 508 manifestes `run.json`** sous
`simulation_lab_data/runs`, répartis entre neuf identifiants de modèles : 792
pour l'étude de sensibilité du 27 avril, 203 M4.3Live, 141 M4.2, 130 M4B, 104
M4.3, 88 M4.2B, 33 M4 Fable, 13 WIP du 27 avril et 4 WIP sans banque. Ce compte
inclut les imports et liens d'archives ; il ne signifie pas 1 508 expériences
scientifiquement indépendantes.

L'échantillon suivant a été choisi pour couvrir : transition ancienne, causalité
des cascades, taille finie, branching, distribution des intérêts et campagne
M4.3. Il ne prétend pas résumer toutes les figures.

| Figure / run | Ce qui est directement visible ou inscrit dans le manifeste | Usage historiographique | Limite |
|---|---|---|---|
| `.../sensitivity/report/figures/codex_oat_key_trajectories.png` | Contraste entre trajectoires en croissance et trajectoires bornées ; évolution conjointe population, réseau et densité. | Source visuelle de la décision de cartographier la transition plutôt que de retenir un seul état final. | Figure agrégée par un script d'analyse ; le critère de bornage doit être lu dans le rapport. |
| `.../sensitivity/report/figures/map_k_mu_heatmap.png` | La zone active dépend conjointement de `k` et `mu`; elle n'est pas une barre verticale à `k=4`. | Trace graphique de la requalification du seuil en surface de phase. | Les fractions aux frontières restent sensibles au nombre de graines. |
| `.../sensitivity/report/figures/map_sigma_k_heatmap.png` | Fenêtre active intermédiaire et disparition des régimes pour bruit élevé. | Justifie la poursuite d'un mécanisme non monotone et l'usage de couplages. | Dépend du critère de queue bornée propre à cette campagne. |
| `.../sensitivity/report/figures/long_run_k3sigma0005_10k_trajectoires.png` | Cinq trajectoires marquées stationnaires après un transitoire long, une trajectoire limite. | Trace du changement de verdict 5 000 → 10 000 pas. | Six graines seulement et une graine divergente antérieure exclue du lot. |
| `m4_credit_soc_fable/reports/01_soc_final/figures/lot100_branching_ratio.png` | Pour cinq graines, `b(t)` converge rapidement autour de `0,299–0,300`. | Montre une auto-stabilisation reproductible de `b`, ce qui a nourri le statut « pré-SOC ». | `b≈0,30`, pas `1`; le rapport lui-même refuse d'en faire un processus de branchement critique strict (`main.tex:653-675`). |
| `m4_credit_soc_fable/reports/01_soc_final/figures/lots_scaling_finite_size.png` | Taille maximale d'avalanche croissant environ comme `N^0,59`; population/`lambda≈14,7`. | Montre que la coupure suit la taille accessible et que la démographie est extensive. | Un scaling sur trois lots ne démontre pas une limite critique asymptotique. |
| Run M4 `20260715_154731_2ca4d1cf`, `cascades_rank_size.png` | Configuration `lambda=30`, `k=3`, `sigma=0,25`, `cancel+destroy`, un round/tête, graine 4, `T=4000`; 461 vivantes, 59 966 avalanches, maximum 49. La figure montre une queue courbe/tronquée avec ajustements lourds. | Relie une figure consultable à un manifeste précis et confirme que les cascades ne sont pas un simple tableau de rapport. | L'ajustement graphique ne suffit pas à choisir définitivement entre familles. |
| Run M4B `20260718_033746_8b0c5acb`, `soc_avalanche_structure.png` | `lambda=30`, `k=2`, `sigma=0,5`, graine 14, `T=4000`, `b=0,278`; profondeur atteignant environ 10 et part de racines autour de 0,45 dans les grands événements. | Preuve visuelle que des morts induites et une profondeur causale persistent dans le moteur réduit à des paires. | Une seule graine illustrée ; la robustesse vient des campagnes agrégées. |
| Run M4.2 `20260727_175504_a6f95655` | `gamma=1/3`, `A=1`, `lambda=30`, `T=4000`, population finale 663, `b=0,318`. | Exemple traçable de l'exploration de `gamma` après réduction à `k=2`. | Un run ne tranche pas l'effet causal de `gamma`. |
| `m4_2b_credit_soc/report/figures/sim_interets_baseline.png` | Corps d'intérêts reçus et prolongement supérieur visuellement allongé, avec coupure/courbure observable. | Source directe de l'assertion T11 : la queue était vue avant sa caractérisation confirmatoire. | La rectitude visuelle ne suffit pas à établir Pareto. |
| `m4_2b_credit_soc/report/figures/sim_avalanches_rho_4.png` | CCDF large et tronquée pour environ 2 266 événements multi-entités dans la configuration illustrée. | Montre que la recherche du second objectif — propagation — s'appuyait également sur des distributions inspectables. | La légende et le run exact doivent accompagner toute réutilisation dans le rapport final. |
| `m4_2b_credit_soc/report/figures/fig7_seuil_exemple_travaille.png` | Exemple réel : au seuil, `alpha≈3,78`, `n_tail=277`, `KS=0,041`; au seuil/2, `alpha≈2,46`, `n_tail=610`, `KS=0,173`. | Matérialise pourquoi le critère `/2` faisait échouer une queue visuellement présente. | Le critère `/2` teste surtout la remontée dans le corps ; le correctif `×2` devient trop peu alimenté en données. |
| Run M4.2B `20260804_224656_92f07582` | `gamma=0,5`, cible arithmétique, `rho=0,5`, `delta=sigma=0,01`, graine 1, `T=3000`; population finale 1 284, 1 917 309 événements de prêt, `b=0,691`. | Exemple de la hausse du branching obtenue en augmentant/transformant l'activité contractuelle. | Le grand nombre de prêts pose aussi un problème de coût et de granularité ; `b<1`. |
| `m4_3_credit_soc/report/figures/d1_plan_dagum_c_vs_b.png` | La plupart des cellules suivent l'anti-corrélation ; la branche `gamma_comp` se déplace vers une queue plus épaisse et un `b` plus élevé. | Source visuelle du choix de confirmer `gamma_comp_0.6667`. | `Dagum c` est une statistique gelée sous hypothèse de queue, pas une preuve universelle de Pareto. |
| `.../verification/dagum_tail_gamma_comp_0.6667.png` | CCDF empirique post-convergence et ajustement Dagum, `c=3,417`. | Ordre de grandeur comparable, après conversion de convention, aux plages de de Vries–Toda. | Un ajustement sur un run de vérification ne suffit pas pour la comparaison empirique générale. |
| `.../verification/avalanches_gamma_comp_0.6667_D1.png` | Queue d'avalanches large avec ajustement tronqué ; branching et cutoff restent mesurables. | Vérifie visuellement que le candidat revenu n'a pas supprimé la propagation. | L'ajustement n'est pas parfait et reste de taille finie. |

## H. Reconstitution de l'épisode `seuil/2` / `seuil*2`

Le journal M4.2B permet de distinguer quatre moments :

1. Anatole demande pourquoi le critère compare le seuil à `seuil/2` et soupçonne
   une erreur (`JOURNAL.md:636-640`).
2. L'agent défend d'abord `/2`, en expliquant qu'il teste l'inclusion du corps et
   qu'il avait été pré-enregistré (`:642-656`).
3. À la demande de montrer le calcul, un exemple réel est tracé : le seuil KS
   sélectionné donne `alpha=3,78`, contre `2,46` à seuil/2, ce qui suffit à faire
   échouer le critère (`:727-742`).
4. Anatole tranche ensuite que `×2` correspond au test d'autosimilarité pertinent.
   L'audit trouve néanmoins que la médiane de taille de queue tombe de 113 à 17 et
   que seuls 2 % des réajustements gardent au moins 80 points. Le test `×2` est
   donc conceptuellement meilleur mais empiriquement sous-alimenté (`:744-786`).

Le facteur d'admissibilité continu construit ensuite donne `A<0,5` pour les 37
cellules, mais la limitation provient principalement de la couverture disponible,
pas d'une courbure clairement séparée du bruit. La décision d'Anatole est alors de
poser la queue de Pareto comme hypothèse de travail et de caractériser l'exposant
avec trois sources d'incertitude (`:658-717,773-793`).

La formulation sûre est donc : **une queue compatible visuellement avec Pareto
était observée ; un premier critère mal orienté la rejetait en redescendant dans
le corps ; le critère conceptuellement corrigé ne disposait pas d'assez de données
dans l'extrême queue ; le stage a choisi de séparer hypothèse de forme et
caractérisation de l'exposant.**

## I. Résultats M4 Fable et statut pré-SOC

Le mécanisme `cancel+destroy` fait passer la fraction racines/taille de `1` à
`0,44–0,51` et la profondeur de 2 à `8–12`. Les deux composantes testées seules
ne reproduisent pas le même régime (`m4_credit_soc_fable/reports/01_soc_final/main.tex:179-191`).

Le volume de marché agit sur le branching : `1/6`, `1/3`, `1/2`, `1`, `2`, `4`
rounds par tête donnent respectivement environ `0,14`, `0,20`, `0,24`, `0,30`,
`0,34`, `0,36`. La coupure ajustée augmente fortement jusqu'à un round par tête,
puis la distribution se dégrade quand le marché est suractivé (`main.tex:193-222`).

À un round par tête, le rapport donne :

- `b=0,300±0,003` sur une gamme de taille multipliée par 30 ;
- taille maximale d'avalanche croissant comme `N^0,59` sur trois lots ;
- exposant de queue des tailles autour de `2,2–2,3` lorsque les singletons sont
  exclus du seuil ;
- moitié environ des membres d'événements `≥5` comme victimes induites et
  profondeur maximale `8–12` (`main.tex:226-264,340-410`).

Le même rapport précise explicitement que `b=0,30≠1` et que le système n'est pas
un processus de branchement critique strict. Il parle de criticité auto-entretenue
dans une fenêtre institutionnelle, avec une théorie de l'exposant encore ouverte
(`main.tex:653-677`). Cette réserve est cohérente avec T08–T09 : les résultats
étaient suffisamment cohérents pour promouvoir le mécanisme et parler de
pré-SOC, mais la proximité de `b` avec 1 n'était ni atteinte ni l'unique critère.

## J. Résultats M4.3 à conserver avant l'arrêt des ablations

M4.3 compare 26 cellules exploitables à la baseline. Vingt-quatre confirment
l'anti-corrélation antérieure ou bougent dans un sens non informatif. Deux cellules
compensées, `gamma_comp_0.6000` et `gamma_comp_0.6667`, donnent simultanément une
queue d'intérêts plus épaisse et un branching plus élevé ; sur la branche compensée,
`Dagum c` évolue `5,19→4,56→3,58→3,39` et `b` `0,760→0,770→0,802→0,804`
(`m4_3_credit_soc/report/rapport_final.md:258-275`).

Le candidat `gamma_comp_0.6667` est ensuite comparé à la baseline pour
`lambda=10,30,100`, trois graines par taille. L'écart de `b` reste
`+0,0184/+0,0184/+0,0185` et l'écart de `c` environ `-0,59` sur une population
variant d'un facteur supérieur à dix ; la différence de branching reste également
présente dans deux moitiés temporelles (`rapport_final.md:297-334`).

Ces résultats sont des faits du programme sous la statistique gelée `Dagum c` et
les protocoles décrits. Ils ne prouvent pas à eux seuls une distribution de Pareto
universelle ni une SOC stricte. L'ablation institutionnelle proposée ensuite dans
le rapport n'a pas été choisie : selon T15, la campagne s'est arrêtée faute de temps
à la fin du stage.

## K. Source empirique ajoutée : de Vries et Toda

L'article est archivé sous S12 dans `registre_sources_scientifiques.md`, avec
chemin canonique et SHA-256. Il porte sur 475 observations pays–année, 52 pays,
1967–2018. Les auteurs trouvent principalement des exposants de Pareto de revenu
du capital entre 1 et 3 (médiane 1,46) et de revenu du travail entre 2 et 5
(médiane 3,35), avec peu de corrélation entre les deux.

Pour le stage, cette source :

- soutient l'idée que les exposants empiriques occupent une plage large ;
- permet de comparer des **ordres de grandeur**, pas de valider le modèle ;
- renforce la nécessité de distinguer intérêts reçus, revenu du travail, capital
  productif et valeur nette ;
- impose une conversion de convention : de Vries–Toda définissent la queue par
  `P(X>x)~x^-alpha`, alors que certains rapports du modèle donnent un exposant de
  densité, décalé de 1 dans le cas continu usuel.

## L. Incertitudes fermées par les réponses du 24 août

- **Datation :** le premier moteur est situé vers les 12–13 mars 2026.
- **Identification :** `anciens_modeles/4-05-dynamique/` est bien le modèle
  dynamique de la première expérience de rebond.
- **Ontologie :** la puissance extractrice est la capacité d'une entité à grossir
  en fonction de sa taille et de sa technologie. La formulation du batch précédent
  en termes d'énergie journalière presque constante était erronée.
