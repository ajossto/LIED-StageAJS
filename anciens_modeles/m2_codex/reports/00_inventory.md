# Inventaire initial du projet M2

Date de l'inventaire : 3 juillet 2026. Cet inventaire précède toute
implémentation de M2. Le dépôt était déjà fortement modifié et contenait de
nombreux fichiers non suivis ; ces travaux préexistants ne seront ni écrasés ni
attribués à la présente réplication.

## Source de conception M2

- `recherche/conception_boltzmann_pareto_soc/conception_modele_M2.md` : source
  textuelle principale (environ 700 lignes), intitulée *Conception d'un modèle à
  distribution Boltzmann--Pareto émergente par auto-organisation critique*.
- `recherche/conception_boltzmann_pareto_soc/latex/rapport.tex` et `rapport.pdf` :
  version mise en forme du même document. L'annexe A rassemble les ablations
  exploratoires E0--E7 et doit être traitée comme une source de résultats
  préliminaires, non comme une validation indépendante.
- `recherche/conception_boltzmann_pareto_soc/latex/typo_francaise.tex` : macros
  typographiques réutilisables, mais non nécessaires à la nouvelle
  implémentation.

## Prototype et sondes directement liés à M2

- `recherche/conception_boltzmann_pareto_soc/exploration/proto_m1.py` : prototype
  jetable qui encode une partie de la dynamique réduite. Il est utile comme
  oracle documentaire et pour comparer les ordres de grandeur, mais ne doit pas
  être promu tel quel : il mélange des variantes par drapeaux et n'est pas la
  spécification finale.
- `exploration/probe_body_age.py` et `probe_renewal.py` : sondes utiles pour les
  diagnostics anti-cohorte et de renouvellement du sommet.
- `exploration/run_*.log` et `renewal_cap.log` : traces des essais E1--E7. Le log
  `run_m2_final.log` rapporte une population apparemment bornée, une queue
  estimée et un corps non exponentiel. Ces logs ne suffisent pas à établir la
  robustesse : certains sont vides, les seeds sont peu nombreux et les sorties
  individuelles ne remplacent pas un protocole reproductible.
- `exploration/README.md` : index utile des variantes et verdicts revendiqués.

## Ancien modèle WIP et lignées historiques

- `modeles-systeme-physicoeconomique/modele_sans_banque_wip/model.py` : adaptateur
  actuellement branché au laboratoire ; il pointe vers `Modèle_sans_banque/src`.
- `Modèle_sans_banque/src/` : lignée WIP active selon `CODEX.md`, avec état riche,
  prêts, faillites et analyses. Réutilisable pour des idées de journalisation ou
  de graphiques, mais dangereux comme base métier : M2 réduit volontairement
  l'état et modifie le coût du crédit, les chocs, la dette d'amorçage et les
  transferts de faillite.
- `anciens_modeles/modele-27-04-WIP/src/` et `anciens_modeles/4-05-dynamique/src{,_v2}/` : autres versions riches,
  partiellement modifiées dans l'arbre de travail. Elles sont historiques ou
  expérimentales et ne seront pas modifiées.
- `anciens_modeles/claude/`, `anciens_modeles/claude3-v2/`, `archives/modeles/` et `banque_versions_zip/` :
  archives. Elles sont impropres à une réutilisation non critique et certaines
  sont explicitement déclarées non modifiables.
- `arborescence_modeles/INDEX_ARBORESCENCE.md` et
  `docs/ORGANISATION_ACTIVE_27_MARS.md` : index historiques utiles pour la
  provenance, pas pour définir M2.

## Orchestration et analyse potentiellement réutilisables

- `simulation_lab/` : registre de modèles, exécution, stockage et interface
  locale. Les contrats `BaseSimulationModel`, `SimulationResult` et le collecteur
  d'artefacts pourront servir à une intégration ultérieure ; ils ne sont pas
  requis pour établir d'abord un noyau M2 indépendant et testable.
- `recherche/analyse_distributions_taille_revenu/scripts/` : ajustements de
  familles (AIC/BIC) et test de queue CSN utilisant NumPy/SciPy. La méthodologie
  et certaines fonctions sont réutilisables après vérification des conventions
  de support, des domaines ajustés et du pooling.
- `recherche/analyse_distributions_taille_revenu/latex/rapport.tex` : exemple de
  rapport statistique et discussion des familles candidates.
- `anciens_modeles/modele-27-04-WIP/studies/sensitivity/` et ses nombreux JSON/figures : exemples
  de campagnes de sensibilité et de stockage. Ils portent sur un autre modèle et
  ne constituent pas des données de validation de M2.
- `PLOTTING_GUIDE.md` et `regen_all_graphs.py` : conventions graphiques et
  régénération de figures du dépôt, réutilisables après examen ciblé.

## Données et résultats disponibles

- Les seules données directement attribuables à la conception M2 sont les logs
  d'exploration précités ; aucun snapshot individuel complet ni carnet de
  contrats sérialisé n'a été trouvé dans ce dossier.
- `simulation_lab_data/` contient de nombreux artefacts de simulations WIP et de
  sensibilité, pas des exécutions du futur noyau M2.
- Des figures et PDF de présentation existent sous `presentation/`; ils sont des
  supports de communication, non des données primaires.

## Manques à combler

- Aucun module propre `src/m2/`, aucune suite `tests/m2/` et aucun script
  `experiments/m2/` n'existent encore.
- Il n'existe pas de schéma M2 documenté pour les logs, snapshots, contrats
  transférés, identifiants ou motifs de décès.
- Les conventions ambiguës du rapport doivent être tranchées explicitement :
  ordre exact choc/extraction, définition opérationnelle du revenu, priorité et
  base de calcul du service partiel, créanciers admissibles lors d'une faillite,
  traitement de `d0` dans la distribution du résiduel, et tolérances numériques.
- Aucun protocole M2 automatisé ne compare encore corps exponentiel, gamma,
  log-normale et Fisk, ni Pareto contre log-normale par seed et fenêtre.
- Aucun environnement de dépendances spécifique à M2 n'est déclaré. Le venv du
  dépôt est la cible documentée ; ses versions devront être consignées.

## Décision d'architecture issue de l'inventaire

M2 sera créé comme nouveau paquet autonome `src/m2/`, avec tests et expériences
séparés. Les sources historiques resteront inchangées. Les outils statistiques
existants seront réutilisés seulement lorsque leur support et leurs conventions
correspondent explicitement aux variables M2 ; sinon une implémentation locale,
plus étroite et testée sera préférée.
