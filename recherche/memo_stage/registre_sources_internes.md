# Registre des sources internes du stage

**Auteur du corpus :** Anatole Joseph-Stouls  
**Période :** printemps–été 2026  
**Statut :** registre de travail, version 1.0 — 21 août 2026

Ce registre archive les notes, rapports, journaux et autres documents produits
pendant le stage. Il est volontairement distinct du
`registre_sources_scientifiques.md` : ces documents internes établissent la
chronologie du raisonnement, des modèles et des résultats, mais ne remplacent
pas les références scientifiques externes du futur rapport.

## Convention

- **Date documentaire** : date inscrite dans le document ou portée par ses
  métadonnées ; elle fournit un terminus chronologique, sans garantir que toutes
  les idées ont été formulées ce jour précis.
- **Rôle probatoire** : ce que le document permet d'établir sur l'état de la
  recherche à cette date.
- **Requalification** : correction imposée par des travaux ultérieurs, afin de
  ne pas transformer un constat provisoire en résultat final.

## D01 — *Note de travail*

- **Auteur :** Anatole Joseph-Stouls.
- **Date documentaire :** 24 avril 2026.
- **Nature :** note interne de 13 pages, marquée « Ne pas diffuser ».
- **Sources canoniques :**
  - `/home/anatole/jupyter/recherche/note_de_travail/latex/note.tex`
  - `/home/anatole/jupyter/recherche/note_de_travail/latex/note.pdf`
- **Métadonnées de fichier :** PDF créé le 24 avril 2026 à 18:11 ; source
  LaTeX modifiée le même jour à 18:10.
- **Empreintes SHA-256 :**
  - `note.tex` : `498bdaac33217e38643bca3ea83b9c344947521fc49b604c0fadb34d933ccafe`
  - `note.pdf` : `046b6e1d5179e25071f61846c947f34ee352b0fb538ce6caa37ebb817e10b428`

### Rôle dans la chronologie

Cette note constitue le premier instantané synthétique actuellement identifié
du programme de stage, dont Anatole date le premier moteur vers les 12–13 mars.
Elle atteste qu'au 24 avril
les objectifs suivants sont déjà explicites :

1. partir de règles interindividuelles simples et de principes physiques pour
   expliquer des distributions macroscopiques, notamment leurs classes
   exponentielle, normale ou en loi de puissance ;
2. étudier l'énergie comme variable centrale et la monnaie comme mécanisme
   d'organisation des échanges ;
3. construire une population d'entités qui extraient, dissipent et prêtent de
   l'énergie ;
4. relier formellement les paramètres de simulation aux statistiques finales,
   dont la population, la puissance totale et les propriétés spectrales ;
5. rechercher une explication endogène de l'effet rebond par une organisation
   sociale possiblement auto-critique.

### Résultats et énigmes consignés à cette date

- Sans mortalité suffisante, aucune limite théorique n'empêche l'accumulation
  et la divergence du système.
- Certaines configurations semblent au contraire atteindre après environ 500
  pas un macro-régime stationnaire : population et extraction totales restent
  bornées malgré les naissances, faillites et changements locaux de prêts.
- Deux classes paraissent émerger spontanément : des « banques », recevant
  principalement des intérêts, et des « travailleurs », tirant principalement
  leurs entrées de leur extraction propre.
- Aucune loi de puissance n'est encore observée. L'auteur écrit explicitement
  que la piste peut être un cul-de-sac.

### Requalification ultérieure

Le régime de flux apparemment stationnaire ne garantit pas la stationnarité de
tous les stocks, notamment lorsque les prêts ne sont pas amortis. Surtout,
l'analyse de juin–juillet 2026 montre que la bimodalité « banques / travailleurs »
est principalement produite par le mélange entre cohorte fondatrice et
entrantes récentes. D01 doit donc être cité comme preuve de la chronologie, des
premiers constats et des questions de recherche, non comme validation finale de
deux classes économiques ou d'une SOC.

### Intérêt pour le futur rapport

D01 permet d'éviter un récit rétrospectif trop linéaire. Il documente à la fois
la continuité de la question directrice — piloter un modèle local pour expliquer
et reproduire des statistiques globales — et l'incertitude réelle du travail à
ce stade : divergence ou convergence selon les réglages, interprétation encore
fragile des classes et absence de loi de puissance démontrée.

## D02 — Corpus des relectures adversariales d'avril

- **Date documentaire :** 3–9 avril 2026 environ.
- **Nature :** critiques d'agents, réponses, rapports formels, manifestes et CSV
  de vérification.
- **Sources canoniques :**
  - `/home/anatole/jupyter/archives/codex_analysis_workspace/reviews/`
  - `/home/anatole/jupyter/archives/codex_analysis_workspace/papers/`
  - `/home/anatole/jupyter/archives/codex_analysis_workspace/data/round3/`
  - `/home/anatole/jupyter/archives/codex_analysis_workspace/data/round4/`
- **Empreintes témoins :**
  - `review_critique_paper_v2_baseline.txt` :
    `64033e7060174c58aaa2caf0779636aa6074b70b36627751ca28b5cd2d530e49`
  - `reponse_aux_critiques.md` :
    `59a889fb82cc67686f257b49e496a4b479a560e2396964bd7f781e8bbf46e90e`

### Rôle probatoire

Le corpus établit que les prétentions SOC initiales ont été volontairement mises
en critique. Il documente les objections sur Jensen, le drift brownien, la valeur
nette, le matching, les répétitions et les proxies de criticité, puis les réponses
et expériences ajoutées. Les textes d'agents n'établissent pas seuls la validité
des objections ; les versions suivantes et les données des rounds 3–4 établissent
les réactions d'Anatole et les tests effectivement lancés.

### Requalification

Le résultat historique n'est pas « un agent a réfuté le modèle », mais « Anatole a
utilisé des relectures adversariales pour abaisser les claims et accroître la
testabilité ».

## D03 — Campagne de sensibilité du modèle du 27 avril

- **Date documentaire :** fin avril–11 mai 2026, enrichissements ultérieurs dans
  le même dossier.
- **Nature :** rapport quantitatif, scripts, cartes, trajectoires et runs importés
  dans Simulation Lab.
- **Source canonique :**
  `/home/anatole/jupyter/anciens_modeles/modele-27-04-WIP/studies/sensitivity/report/rapport_final_sensibilite.tex`
- **SHA-256 :**
  `05bf0248f0bded4090d06ec14bbd20f23df9e1d28e00608850b62e35e4eb61c0`

### Rôle probatoire

Le rapport et ses sorties établissent le passage d'une exploration OAT à des
surfaces de régime : seuil initial `k=3→4`, dépendance à `mu`, fenêtre de bruit
sur `alpha`, effet destructeur des grands `epsilon`, transitoires longs, densité
financière en volume et mécanismes candidats à l'élagage. Il constitue la source
principale pour répondre à la question « quels résultats les campagnes de
sensibilité ont-elles effectivement produits ? »

### Requalification

Le seuil ancien en `k` est conditionnel à l'institution et à `mu`; il ne constitue
pas un seuil universel. Le nombre de tentatives de marché était en outre fixe par
rapport à `N`, erreur structurelle corrigée dans les moteurs suivants.

## D04 — Première expérience explicite de rebond

- **Date documentaire :** fin avril–début mai 2026 ; runtime dynamique repris ou
  documenté plus tard.
- **Nature :** ablation `alpha_plus_10pct`, rapport et CSV de runs.
- **Sources canoniques :**
  - `/home/anatole/jupyter/anciens_modeles/4-05-dynamique/RAPPORT_ELAGAGE_MODELE.md`
  - `/home/anatole/jupyter/anciens_modeles/4-05-dynamique/experiments/results/rebound_1000_runs.csv`
  - `/home/anatole/jupyter/anciens_modeles/4-05-dynamique/experiments/results/rebound_1000_aggregate.csv`
  - `/home/anatole/jupyter/anciens_modeles/4-05-dynamique/DYNAMIC_RUNTIME_NOTES.md`
- **SHA-256 :**
  - rapport : `16c759a550553fe651201092ade27ffac2420d03dc7c9b80d2a49a077190a6d7`
  - runs : `cc0f467d81a16b442f5ca5159de542d9cb9bc88434e5cfe9d7cc89a092f37d99`

### Rôle probatoire

Cette pièce établit que la hausse de productivité de 10 % a été testée comme
expérience de rebond avant M4.3Live. Le rapport décrit une hausse de l'extraction
et une extension du réseau de prêts, résultat qui a nourri la réflexion.
Anatole confirme le 24 août que `anciens_modeles/4-05-dynamique/` est bien le
« modèle dynamique » qu'il désigne comme première expérience de rebond.

### Réserve de provenance

Le rapport annonce trois graines agrégées, mais les CSV actuellement présents
n'en contiennent que deux par variante et ne reproduisent pas exactement tous les
nombres du tableau. Il faut citer à la fois l'effet interprétatif historique et
cette discordance, sans présenter les chiffres du rapport comme entièrement
recalculables depuis les quatre lignes conservées.

## D05 — Diagnostic des distributions, de l'âge et des cohortes

- **Date documentaire :** fin juin–2 juillet 2026.
- **Nature :** analyse distributionnelle et figures.
- **Source canonique :**
  `/home/anatole/jupyter/recherche/analyse_distributions_taille_revenu/latex/rapport.tex`
- **SHA-256 :**
  `536839d671baefc960e780196b003e87441bad457aaf942d244f13c8588c1349`

### Rôle probatoire

Ce document contrôle l'âge, les cohortes, les fenêtres temporelles et plusieurs
familles candidates. Il fournit la base du changement d'interprétation des
« banques/travailleurs » vers un artefact de cohorte et de moteur.

### Décision associée

Anatole abandonne l'architecture comme validation sociale, demande des entités
initialement identiques et une colonne de capital plus lisible, puis lance deux M2
concurrentes. Selon son témoignage, cette requalification discrédite suffisamment
le premier modèle pour imposer un redémarrage lointain, mais non un oubli des
hypothèses physiques et de la démarche acquise.

## D06 — Réplications concurrentes M2

- **Date documentaire :** 2–3 juillet 2026.
- **Nature :** deux implémentations et suites de rapports issues du même prompt.
- **Sources canoniques témoins :**
  - `/home/anatole/jupyter/anciens_modeles/m2_codex/reports/06_final_summary/main.tex`
  - `/home/anatole/jupyter/anciens_modeles/m2_fable/reports/final_summary_pdf/main.tex`
  - moteurs et rapports précédents sous `anciens_modeles/m2_codex/` et
    `anciens_modeles/m2_fable/`.
- **SHA-256 :**
  - Codex : `3f7761ce5f20ef5649a6374237a6f4608af0511f3bf27206f655e5073eaee1c0`
  - Fable : `daeef082916c5eef42b214e0c451abe61e082e1b56de7148b8d920ac795e8147`

### Rôle probatoire

Les branches établissent une mise à l'épreuve concurrente d'un même cahier des
charges. Elles documentent les corrections des estimateurs, l'explosion des
contrats et le constat que le crédit modifie peu les formes dans ce moteur.

### Requalification

L'accord des branches a davantage de poids qu'un rapport isolé, mais elles restent
apparentées par le prompt commun. Leur résultat négatif conduit à M3, qui rend le
crédit causal. M2 est aussi la première attestation retrouvée du remplacement du
Brownien sur `alpha` par un choc multiplicatif centré sur le stock réel `w`.

## D07 — M3, crédit causal et anomalies retenues

- **Date documentaire :** 3–6 juillet 2026.
- **Nature :** moteur, journal, sept rapports et ablations.
- **Sources canoniques :**
  - `/home/anatole/jupyter/anciens_modeles/m3_credit_soc/NOTES.md`
  - `/home/anatole/jupyter/anciens_modeles/m3_credit_soc/reports/06_final_synthesis/main.tex`
  - `/home/anatole/jupyter/anciens_modeles/m3_credit_soc/reports/07_income_rule/main.tex`
- **SHA-256 du rapport de synthèse :**
  `c9bec168f12011d5208abd173a73437b7487bfdfa7834ddc7667c3093c494c63`

### Rôle probatoire

M3 sépare liquidité `L` et capital `K`, paie les intérêts depuis `L` et instrumente
les avalanches causales. Les ablations H (`d0=0`) et X1 (objectif de revenu myope)
fournissent les deux mécanismes que le prompt M4 reprend malgré un bilan M3
globalement négatif sur la SOC et Boltzmann–Pareto.

### Réserve

Le journal consigne des erreurs d'observation et des ablations confondues avec le
volume de marché. Les verdicts doivent être rattachés aux runs corrigés, et le
choix d'Anatole se lit surtout dans le prompt M4 qui sélectionne H et X1.

## D08 — M4 Fable, propagation causale et choix du candidat

- **Date documentaire :** 13–17 juillet 2026.
- **Nature :** journal d'exploration, code, rapports et lots Simulation Lab.
- **Sources canoniques :**
  - `/home/anatole/jupyter/m4_credit_soc_fable/NOTES.md`
  - `/home/anatole/jupyter/m4_credit_soc_fable/reports/01_soc_final/main.tex`
  - lots M4 sous `/home/anatole/jupyter/simulation_lab_data/runs/`.
- **SHA-256 du rapport :**
  `9f16721ee678facc65542ab3d88aaa23dd7c4e15ab1a7ba963493eff1131d4b0`

### Rôle probatoire

Les pièces distinguent grappes de racines synchronisées et contagion. Elles
établissent que `cancel+destroy` produit des victimes induites et de la profondeur,
que le branching répond au volume de marché et qu'un round par tête stabilise
`b≈0,30` sur les tailles testées. Le scaling des avalanches et les figures de
causalité expliquent la décision de poursuivre cette branche.

### Requalification

Le rapport lui-même indique que `b≠1`; il ne prouve donc pas un processus de
branchement critique strict. Le statut validé par Anatole est celui d'un candidat
pré-SOC aux statistiques cohérentes, promu vers M4B.

## D09 — M4B et sa campagne de sensibilité

- **Date documentaire :** 16–27 juillet 2026.
- **Nature :** moteur réduit, prompt révisé, journal, runs et rapport.
- **Sources canoniques :**
  - `/home/anatole/jupyter/m4b_credit_soc_mini/`
  - `/home/anatole/jupyter/recherche/sensibilite_m4b/JOURNAL.md`
  - `/home/anatole/jupyter/recherche/sensibilite_m4b/report/rapport_final.tex`
- **SHA-256 du rapport :**
  `7b8caeab93e3571d0bd20a155be96936bdea2d5786813da6a821ac55a55befe3`

### Rôle probatoire

M4B réduit M4 Fable et fixe l'activité à un round par entité vivante et par pas.
La campagne mesure paramètres, valeur nette, démographie, croissance/récession et
énergie totale. Les interventions d'Anatole dans le journal documentent la
redéfinition des observables économiques et physiques.

### Réserve

M4B est une réduction du candidat M4, non une confirmation indépendante. Le
journal doit être utilisé pour identifier les comptages et prédictions d'agents
corrigés après contrôle des données.

## D10 — M4.2, concavité et contrôle d'échelle

- **Date documentaire :** 27–29 juillet 2026.
- **Nature :** prompt, moteur, journal, campagne et rapport.
- **Sources canoniques :**
  - `/home/anatole/jupyter/m4_2_credit_soc/prompts/PROMPT_M4_2.md`
  - `/home/anatole/jupyter/m4_2_credit_soc/JOURNAL.md`
  - `/home/anatole/jupyter/m4_2_credit_soc/report/rapport_final.tex`
- **SHA-256 :**
  - journal : `dcab8aa7c7161997ec60f8f9b656d643267208e0effb9bf3b3a476d29fde35fc`
  - rapport : `6c300b0da60772de0481f988beb48e4b1fe47a6bc64ac29ca8bd9138a73e9fab`

### Rôle probatoire

M4.2 introduit `A*K^gamma`, fixe les rencontres à des paires aléatoires et
`eta(N)=N`, puis teste le pilotage de la pente des avalanches. Les contrôles
requalifient l'effet de `gamma` en problème de rapport à l'échelle autarcique et
établissent une covariance d'échelle du moteur.

## D11 — M4.2B, intérêts reçus et controverse du seuil de queue

- **Date documentaire :** 30 juillet–6 août 2026.
- **Nature :** moteur, double cahier des charges, journal révisé, rapport, figures
  et runs.
- **Sources canoniques :**
  - `/home/anatole/jupyter/m4_2b_credit_soc/JOURNAL.md`
  - `/home/anatole/jupyter/m4_2b_credit_soc/report/rapport_final.md`
  - `/home/anatole/jupyter/m4_2b_credit_soc/report/figures/`
- **SHA-256 :**
  - journal : `1c4f0a66c7e150603e11e2a505a3affd33dc666c43e62d4ecacc7dcbd2df6b48`
  - rapport : `9ea1f4ab86c23377cfbcf04834fe82ee0e45c54a1392370bf88b6bdd7fc6cf8c`

### Rôle probatoire

La campagne rend les intérêts reçus centraux, cherche simultanément une queue
pilotable et des cascades fortes, et fait apparaître leur anti-corrélation. Les
figures établissent l'observation visuelle d'une queue supérieure ; le journal
reconstitue la contestation de `seuil/2`, le passage conceptuel à `seuil×2`, puis
le manque de données extrêmes pour appliquer ce dernier de façon fiable.

### Requalification

La queue de Pareto est retenue comme hypothèse de travail et son exposant est
caractérisé ; son existence n'est pas confirmée par le test devenu sous-alimenté.
Il serait faux de raconter cet épisode comme un simple refus d'une queue visible.

## D12 — M4.3, statistique gelée et premier levier contre l'anti-corrélation

- **Date documentaire :** 6–11 août 2026.
- **Nature :** campagne, journal, tables régénérées et rapport.
- **Sources canoniques :**
  - `/home/anatole/jupyter/m4_3_credit_soc/JOURNAL.md`
  - `/home/anatole/jupyter/m4_3_credit_soc/report/rapport_final.md`
  - `/home/anatole/jupyter/m4_3_credit_soc/report/figures/`
- **SHA-256 :**
  - journal : `584d94005ea58bcaeab9707047b2a48d5c78fdf6b8d83c3d984c1ce3790167df`
  - rapport : `25301dc151b8245f0efa3be98896c37a35320e1db090cf6848ceeeebcc58d1d3`

### Rôle probatoire

Sous la statistique `Dagum c` gelée, `gamma_comp_0.6667` augmente simultanément
l'épaisseur de la queue d'intérêts et le branching relativement à la baseline.
Les contrôles en `lambda=10,30,100` et sur deux moitiés temporelles soutiennent la
robustesse interne du contraste.

### Clôture

La décision d'ablation institutionnelle reste ouverte dans le rapport. Anatole
confirme le 21 août qu'elle n'a pas été tranchée faute de temps et que la campagne
s'arrête avec la fin du stage.

## D13 — M4.3Live-v1, retour expérimental au rebond

- **Date documentaire :** 17–21 août 2026.
- **Nature :** fork indépendant, interventions en direct, journal, campagnes,
  ablations, démonstrations de covariance et rapport.
- **Sources canoniques :**
  - `/home/anatole/jupyter/m4_3live_credit_soc/JOURNAL.md`
  - `/home/anatole/jupyter/m4_3live_credit_soc/report/rapport_final.tex`
  - `/home/anatole/jupyter/m4_3live_credit_soc/prompts/PROMPT_M4_3LIVE.md`
- **SHA-256 :**
  - journal : `0a25539ab20551474686d483835b1d9c8d23bd7558b88b137fcfcebb9650ea62`
  - rapport : `f3a0c18b9a44b60048c30cad15f58ab99f29040af137e39cdbbe32f034dd4341`

### Rôle probatoire

M4.3Live rend `A` et `gamma` propres aux entités et modifiables pendant un run,
introduit des portées d'intervention et une règle de principal maximisant la
production jointe. Les vérifications demandées par Anatole réfutent une première
explication par l'alourdissement des intérêts et montrent que le verdict dépend de
la covariance ou non de `K0` avec l'échelle technologique.

### Position chronologique

Il s'agit de la reprise tardive de la question du rebond après reconstruction de
la lignée, non de la première expérience de rebond du stage.

## D14 — M4.3Live-v2, feuille de route arrêtée

- **Date documentaire :** 21 août 2026.
- **Nature :** conception annotée, non moteur testé.
- **Source canonique :**
  `/home/anatole/jupyter/m4_3live_v2_credit_soc/ROADMAP.md`
- **SHA-256 :**
  `bef3f1b1aa47fd28e758167d3be7f3b43b21aa2ef81da4efc3669964dd924720`

### Rôle probatoire

La feuille de route établit les dernières décisions de conception : revoir la
direction des prêts et l'ordre du service des intérêts, supprimer les traitements
partiels et le plafond `equalization`, puis améliorer l'instrumentation.

### Statut

Ces éléments ne sont pas des résultats. La poursuite et les ablations sont arrêtées
par la fin du stage.

## D15 — Témoignage de l'auteur et annexe de recoupement des 21–24 août

- **Dates :** 21 et 24 août 2026.
- **Nature :** corrections et réponses en direct d'Anatole, recoupées avec code,
  rapports, sorties et figures.
- **Source dérivée consultable :**
  `/home/anatole/jupyter/recherche/memo_stage/annexe_preuves_historiographiques_2026-08-21.md`

### Rôle probatoire

Le témoignage établit les intentions et décisions qui ne peuvent pas être déduites
avec certitude du code : sens de l'hypothèse monnaie–exergie, analogie complète de
la hache, absence de types d'agents déclarés, but du retrait de la banque, filiation
du 27 avril, concurrence des M2, raison du choix Fable, statut du branching ratio,
erreur de normalisation de `k`, observation graphique de la queue, première
expérience de rebond, progression du revenu par intérêts, rôle des encadrants et
arrêt des ablations. Les compléments du 24 août fixent le premier moteur vers les
12–13 mars, confirment l'identité du modèle dynamique et corrigent l'ontologie de
la puissance extractrice : capacité d'une entité à grossir en fonction de sa
taille et de sa technologie.

### Limite

Le témoignage établit l'histoire intellectuelle de l'auteur, non les valeurs
numériques. L'annexe D15 associe chaque fait d'intention aux pièces techniques
disponibles et conserve les incertitudes encore ouvertes.
