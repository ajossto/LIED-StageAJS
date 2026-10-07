# Inventaire du projet — réplication M2 (workspace `modeles/anciens_modeles/m2_fable/`)

Date : 3 juillet 2026.
Agent : Claude Fable 5, workspace isolé `/home/anatole/jupyter/modeles/anciens_modeles/m2_fable/`.

**Contexte de concurrence** : un autre agent travaille en parallèle sur la même
tâche dans `jupyter/reports/` (fichiers `00_inventory.md` et `research_log.md`
datés du même jour, non produits par moi). Par consigne de l'utilisateur, tous
mes livrables vivent sous `modeles/anciens_modeles/m2_fable/` et je ne modifie **aucun** fichier hors de
ce dossier. Le venv partagé `/home/anatole/jupyter/.venv` est utilisé en lecture
seule (aucune installation).

## 1. Source principale

- `recherche/conception_boltzmann_pareto_soc/conception_modele_M2.md` (~707
  lignes) : le document de conception M2, *Conception d'un modèle à distribution
  Boltzmann-Pareto émergente par auto-organisation critique*. Lu intégralement.
  Contient : résumé exécutif, squelette analytique (Fokker-Planck [YR],
  Kesten [BM]), définition complète de l'état et de la séquence à 7 phases,
  classification des ~18 paramètres du WIP → 6 paramètres M2, protocole de
  validation §6, annexe A (ablations E0–E7).
- `recherche/conception_boltzmann_pareto_soc/latex/rapport.{tex,pdf}` : version
  LaTeX du même document (pas de contenu supplémentaire attendu ; non pris comme
  source normative — le `.md` fait foi, il est plus récent dans l'arbre).

**Statut épistémique retenu** : proposition de recherche. L'annexe A est une
chaîne d'explorations *sur un prototype*, pas une validation. Le rapport
lui-même admet : corps exponentiel non acquis (log-normale/gamma gagnent
l'AIC), stabilité de μ = hypothèse H2 non prouvée, conventions non testées
(moyenne géométrique, max/min, prorata).

## 2. Prototype et sondes

- `exploration/proto_m1.py` (~360 lignes) : prototype M1. **Attention** : il
  n'implémente PAS la règle de marché M2 (il garde `theta` et
  `offer_frac = w/2`, hérités du WIP, avec `q = min(offer_frac·w_l, θ·qmax)`),
  et sa règle de faillite diffère de M2 : les contrats où la faillie est
  *prêteuse* sont **annulés** (`_fail`, commentaire « gain pour lui »), pas
  transférés au prorata comme l'exige §2.2 phase 7 du rapport. Les résultats
  [E7c] cités comme « pile complète M2 » proviennent donc d'un modèle qui
  s'écarte de la spécification M2 sur au moins deux règles. À documenter comme
  risque de non-réplication.
- `exploration/probe_body_age.py`, `probe_renewal.py` : sondes anti-cohorte et
  renouvellement — réutilisables comme idées, réimplémentées proprement.
- `exploration/run_*.log`, `renewal_*.log` : traces E0–E7. Preuves d'existence
  de régime, pas des données de validation (1 seed la plupart du temps).

## 3. Outils statistiques réutilisables

- `recherche/analyse_distributions_taille_revenu/scripts/tail_test.py` : CSN
  (x_min par KS sur grille de quantiles, MLE de l'exposant, LR Vuong contre
  log-normale). Autonome (numpy/scipy), conventions vérifiées (α = exposant de
  la pdf ; scipy `pareto.b = α−1`). **Réutilisable** ; je le réimplémente dans
  `src/m2/analysis.py` avec bootstrap en plus, pour ne pas dépendre d'un chemin
  hors workspace et pour le tester.
- `scripts/families.py` : échelle AIC/BIC — mais importe
  `modeles/anciens_modeles/modele-27-04-WIP/src/analysis.py` (dépendance dangereuse, hors périmètre).
  Je réimplémente localement le sous-ensemble requis (expon/gamma/lognorm/Fisk
  à `floc=0`).

## 4. Lignées historiques (non réutilisées comme base métier)

- `Modèle_sans_banque/src/` + adaptateur
  `modeles/adaptateurs/modele_sans_banque_wip/model.py` : WIP
  actuellement branché au laboratoire. Bilan à 8 postes, règles que M2 élimine.
- `modeles/anciens_modeles/modele-27-04-WIP/src/` : la référence [WIP] du rapport (config/models/
  simulation cités ligne à ligne). Utile pour vérifier les affirmations du
  rapport sur l'origine des règles ; pas une base de code pour M2.
- `modeles/anciens_modeles/claude/`, `modeles/anciens_modeles/claude3-v2/`, `archives/`, `banque_versions_zip/` : archives
  déclarées non modifiables.
- `simulation_lab/` : orchestration locale. Intégration possible *a
  posteriori* ; le noyau M2 reste autonome pour être testable seul.

## 5. Environnement

- Python : `/home/anatole/jupyter/.venv/bin/python3` (numpy 2.4.3, scipy
  1.17.1, matplotlib 3.10.8). **pytest absent** et installation interdite sans
  accord → tests écrits en style pytest (fonctions `test_*` + asserts) avec un
  runner stdlib `tests/run_all.py` ; `pytest` fonctionnera tel quel si installé
  un jour.
- LaTeX : `latexmk` et `pdflatex` disponibles (`/usr/bin/`).

## 6. Manques identifiés (à produire ici)

- Aucun module M2 conforme à la spécification §2.2 n'existe (le prototype
  dévie, cf. §2 ci-dessus).
- Aucune suite de tests, aucun protocole multi-seed automatisé, aucun format de
  snapshot/log défini.
- Ambiguïtés du rapport à trancher explicitement dans la spécification
  (02_technical_spec) : ordre de service des intérêts en cas de w insuffisant
  pour plusieurs contrats ; participation des défaillants au marché du même
  pas ; sort du capital résiduel quand la faillie n'a aucun créancier
  contractuel (d₀ seule) ; revenus mesurés avant ou après dépréciation ;
  définition opérationnelle du « revenu » ; tolérances numériques.

## 7. Décisions d'architecture

- Paquet autonome `modeles/anciens_modeles/m2_fable/src/m2/` (config, entities, contracts, market,
  bankruptcy, simulation, metrics, analysis, plots), expériences sous
  `modeles/anciens_modeles/m2_fable/experiments/m2/`, tests sous `modeles/anciens_modeles/m2_fable/tests/`, rapports sous
  `modeles/anciens_modeles/m2_fable/reports/`.
- Arborescence identique à celle demandée dans le brief, simplement enracinée
  dans `modeles/anciens_modeles/m2_fable/` (justification : consigne d'isolement vis-à-vis de l'agent
  concurrent ; le dépôt `jupyter/` n'impose pas d'autre organisation).
- RNG : `numpy.random.default_rng(seed)` unique par simulation (le brief
  CLAUDE.md impose un RNG isolé ; numpy est autorisé par la mémoire projet).
