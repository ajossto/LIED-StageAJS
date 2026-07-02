# Prompt Fable 5 — Conception d'un modèle produisant une distribution empirique à deux classes

## Rôle et cadre

Tu es un chercheur en économophysique / systèmes complexes. Tu reprends un
modèle multi-agents d'entités économiques échangeant une ressource unique.
Tu ne dois **PAS coder** dans ce passage : le livrable est un **document de
conception** (jeu d'équations + mécanismes + classification des paramètres +
critères de validation). L'implémentation sera faite ensuite par un autre
agent (Opus 4.8 + agents Sonnet), à partir de ton document.

Travaille dans `/home/anatole/jupyter`. Python du venv :
`/home/anatole/jupyter/.venv/bin/python3` (numpy/scipy autorisés). Tu peux
**lancer des simulations d'exploration** pour étayer ta conception, mais
**sans modifier `modele-27-04-WIP/src/`**.

## Thèse de recherche et objectif unique

**Thèse à démontrer :** la distribution **Boltzmann-Pareto** (corps exponentiel
+ queue de Pareto, la structure à deux classes de Yakovenko-Rosser 2009 et
Bouchaud-Mézard 2000) peut **émerger d'un système auto-critique** (auto-
organisation critique) — sans réglage fin, à partir de règles identiques.

C'est un travail de recherche : **une seule distribution nous intéresse**, la
forme Boltzmann-Pareto, et le point scientifique est qu'elle *émerge*, pas
qu'on la fabrique. Cible à obtenir sur les revenus et les capitaux :

- **Corps exponentiel** (Boltzmann-Gibbs) `P(x) ∝ e^{−x/T}` pour la majorité
  (~95 % inférieurs, la classe « thermique »). **Cible dure** — la moitié
  « Boltzmann » de la thèse, à ne pas relâcher en lognormale.
- **Queue de Pareto** `P(x) ∝ x^{−1−μ}` pour la minorité supérieure (classe
  « superthermique »), exposant μ **stable** (invariant à la durée — ce que le
  modèle actuel rate).

**C'est le seul critère d'acceptation.** Contrainte de méthode : la distribution
doit sortir de la dynamique auto-critique elle-même. **Interdiction de la
fabriquer** en juxtaposant des lois toutes faites ou un canal ad hoc calibré
pour imiter la forme cible — ce serait vider la thèse de son sens.

**Cadre auto-critique (SOC).** Le système candidat est le couple extraction
concave + réseau de crédit + faillites : le rapport d'élagage situe déjà une
bifurcation « stable → SOC » à k ≥ 3, avec cascades de faillites. L'auto-
organisation critique est le mécanisme par lequel on espère voir émerger, sans
paramètre de contrôle réglé, à la fois le bornage de la population et la forme
Boltzmann-Pareto.

## Contraintes de conception imposées par l'utilisateur

1. **Entités strictement identiques.** Aucune entité n'a de rôle pré-assigné
   NI d'hétérogénéité innée : on **supprime l'hétérogénéité d'α** (α tiré à la
   naissance) du modèle actuel. Toutes les entités partagent règles ET
   paramètres ; les deux classes (thermique / superthermique, ≈ travailleur /
   capitaliste) doivent émerger **de la seule dynamique stochastique + échange**,
   comme chez Bouchaud-Mézard et Yakovenko. Une entité appartient à une classe
   par son état et son histoire, jamais par une caractéristique gelée.
2. **Bilan simplifié à une seule colonne de capital.** On abandonne le miroir
   actif/passif du modèle actuel (c'était un artefact). Une entité = un stock
   scalaire (capital / richesse) et éventuellement un flux (revenu).
3. **Objectif zéro paramètre exogène réglé à la main** (aspiration forte, pas
   couperet). Tout paramètre résiduel doit être soit une convention d'unité
   fixable à 1, soit une quantité endogène. Un paramètre « à régler pour
   obtenir la bonne distribution » est une limite à signaler explicitement.
4. **Population ouverte, bornée endogènement.** On garde des naissances et des
   faillites (pas de N fermé à la Yakovenko). Le bornage de la population doit
   **émerger** (faillite par capital négatif / sur-endettement), sans paramètre
   d'échelle réglé : le flux d'entrée, s'il subsiste, ne doit fixer qu'une
   échelle, pas le régime. ATTENTION : une population ouverte réintroduit un
   **gradient d'âge** (établis vs entrants). Le rapport de distributions montre
   que c'est la FAUSSE source des « deux classes » actuelles. Le document doit
   donc garantir que les deux classes obtenues sont thermique/superthermique
   (issues de la dynamique de capital), et non un simple artefact de cohortes
   d'âge — voir le garde-fou dans le protocole de validation.

## Mécanismes cibles (à lire dans les articles, sur la machine)

Lire ces sources AVANT de proposer un mécanisme :

- Bouchaud & Mézard 2000, *Wealth condensation in a simple model of economy* :
  `/home/anatole/Zotero/storage/V4LJMQGK/arXivcond-mat0002374v1  24 Feb 2000.pdf`
  — équation de richesse invariante d'échelle `dW_i/dt = η_i W_i + Σ J_ij W_j
  − Σ J_ji W_i` ; solution moyen-champ `P(w) ∝ exp(−(μ−1)/w)/w^{1+μ}` avec
  `μ = 1 + J/σ²` ; transition de condensation à μ < 1 ; lien polymère dirigé.
- Yakovenko & Rosser 2009, *Colloquium: Statistical mechanics of money,
  wealth, and income* :
  `/home/anatole/Téléchargements/Yakovenko et Rosser - 2009 - Colloquium Statistical mechanics of money, wealth.pdf`
  — conservation locale de la monnaie (échange additif) + borne `m ≥ 0` ⟹
  corps exponentiel `P(m) = c·e^{−m/T}`, `T = M/N` ; distinction **additif vs
  multiplicatif** (Sec. II.F) ; structure à deux classes (Sec. III–IV).
- Analyses déjà faites dans le dépôt (recodage + rapports) :
  `recherche/analyse_articles/bouchaud_mezard_wealth_condensation/`,
  `recherche/analyse_articles/wright_social_architecture/`,
  `recherche/analyse_articles/wright_implicit_microfoundations/`.
- Constat d'échec du modèle actuel :
  `recherche/analyse_distributions_taille_revenu/latex/rapport.pdf` — les
  « deux classes » actuelles sont un artefact de cohortes d'âge (l.211) et la
  queue n'est pas une loi de puissance stable (exposant 5,4→3,1, l.326).

**Enseignement central à exploiter** : la forme Boltzmann-Pareto met en jeu
deux ingrédients — un **échange additif conservatif** (corps exponentiel de
Boltzmann-Gibbs) et une **croissance multiplicative invariante d'échelle**
(queue de Pareto, `W → λW`). L'enjeu n'est pas de les bricoler séparément mais
de voir lequel des mécanismes DÉJÀ présents dans le modèle 27-04-WIP les porte.
Analyse canal par canal :

- **Intérêts du crédit = canal capital → queue de Pareto.** L'intérêt perçu
  est proportionnel au capital prêté (`r·W`), donc multiplicatif et invariant
  d'échelle : c'est le canal qui peut produire une VRAIE queue de Pareto, à
  condition que le coefficient multiplicatif net (intérêts reçus − intérêts
  payés − dépréciation) soit **fluctuant** et assorti d'un terme additif /
  rappel (structure de Kesten → loi de puissance). Ce demi-mécanisme est solide.
- **Extraction concave `Π = α√P` = canal travail.** **La concavité est conservée
  (hypothèse imposée).** Elle garantit l'ABSENCE de queue épaisse dans le canal
  travail et un corps borné — mais elle ne produit PAS à elle seule un corps
  exponentiel. À α homogène, l'ODE `dx/dt=−δx+b√x+c` a un point fixe stable
  `x₊≈(b/δ)²` COMMUN à toutes les entités : la dynamique déterministe pousse
  tout le monde vers la même taille → corps *piqué en x₊* (lognormale/Fisk,
  mode ≠ 0), pas un Boltzmann-Gibbs (mode en 0). C'est confirmé empiriquement :
  `rapport.pdf` ajuste le corps par Fisk/lognormale/Singh-Maddala, jamais par
  l'exponentielle. **Le mécanisme du corps exponentiel est donc une QUESTION
  OUVERTE, pas un acquis** (voir ci-dessous).

**Question ouverte n°1 — d'où vient le corps de Boltzmann ?** Le générateur
canonique d'un corps exponentiel est un **échange additif conservatif** par
paires avec plancher (`capital ≥ 0`) : c'est la redistribution monétaire de
Dragulescu-Yakovenko. Hypothèse à évaluer (sans la décréter) : **le crédit
contient déjà ce canal**. Le transfert du principal prêteur → emprunteur est un
échange conservatif de capital ; c'est un candidat naturel pour engendrer le
corps de Boltzmann de façon *endogène*, tandis que les intérêts fournissent le
canal multiplicatif de la queue. Les deux régimes sortiraient alors du **même**
mécanisme de crédit, l'extraction concave jouant le rôle de « chauffage lent »
qui maintient le système hors équilibre. RAPPEL DE MÉTHODE : il ne s'agit pas
d'ajouter un canal Dragulescu-Yakovenko *à côté* pour forcer la forme, mais de
montrer si la dynamique auto-critique la produit d'elle-même.

**Attention (α homogène) :** supprimer l'hétérogénéité d'α retire le
brise-symétrie propre des deux classes. Le point fixe commun pousse tout le
monde vers `x₊`, donc toute la dispersion de taille doit venir (a) du canal
crédit — le moteur Pareto — et (b) du calendrier de naissance / âge — soit
précisément l'artefact de cohorte à désamorcer. α homogène **augmente** donc la
charge sur le crédit ET le risque de confusion avec l'âge.

**Question ouverte n°2 — faut-il une source de dispersion stochastique ?**
Sans hétérogénéité gelée, il se peut que la thèse exige une **source de bruit
identique pour toutes les entités** pour engendrer la dispersion et alimenter
le canal multiplicatif (chez Bouchaud-Mézard, c'est précisément le bruit `η_i(t)`
de moyenne `m` et variance `2σ²` qui, multiplié par `W_i`, produit la queue de
Pareto — les agents restent statistiquement identiques). Pistes à évaluer, par
ordre de préférence vis-à-vis de « règles identiques » :
  1. un **choc multiplicatif commun en loi** sur le capital ou le rendement
     (`W → W·e^{η}`, `η` tiré dans une loi unique) — ne réintroduit PAS
     d'hétérogénéité gelée, chaque entité subit la même règle de bruit ;
  2. la **stochasticité de l'appariement de crédit** elle-même (qui prête à qui,
     à quel volume) comme seule source de dispersion, sans bruit ajouté ;
  3. en dernier recours seulement, un bruit sur α **tiré à chaque pas dans une
     loi commune** (dérive brownienne partagée), à distinguer nettement d'un α
     gelé à la naissance.
Le document doit dire laquelle suffit à produire la forme Boltzmann-Pareto avec
le moins d'ingrédients, et vérifier qu'aucune ne revient à une hétérogénéité
gelée déguisée.

## Tâche centrale à trancher

À α **homogène** (hétérogénéité innée supprimée) et concavité conservée, les
deux classes doivent émerger du **croisement de régimes** : petites entités
`√P`-dominées (thermiques) vs grandes entités intérêt-dominées (Pareto), la
position dans le réseau de crédit remplaçant l'hétérogénéité d'α. Relier ce
montage à l'ODE effective `dx/dt = −δx + b√x + c` en lui ajoutant le **terme
multiplicatif bruité** issu des intérêts nets (le canal capital).

Ta tâche principale : proposer le **jeu de mécanismes minimal** qui produit
*simultanément* un corps exponentiel et une queue de Pareto **stable** (μ
invariant à la durée), à partir de **règles identiques**, et dire explicitement
ce qu'il faut **garder, transformer ou abandonner** du modèle 27-04-WIP
(crédit à intérêts, auto-investissement, dépréciation, naissances — l'extraction
`√P` est, elle, conservée). Justifier chaque choix par son effet attendu sur la
forme de la distribution.

## Repenser l'échange / la création de prêts

Si un mécanisme d'échange type crédit est conservé, il doit être reformulé de
façon minimale et à règles identiques. Les notes inline de l'auteur dans
`modele-27-04-WIP/src/simulation.py::credit_market_iteration` (l.854) indiquent
la direction : tirage aléatoire d'un nombre de contreparties par round avec
plusieurs rounds par pas (l.867), pool unique au lieu de deux (l.900),
suppression des paramètres cachés `MAX_IDLE = max(20, k²)` (l.870). À relier
au terme d'échange `J_ij` de Bouchaud-Mézard (matrice de couplage, mean-field
`J_ij = J/N`, ou réseau à connectivité `c`).

## Fichiers du modèle actuel à lire

- `modele-27-04-WIP/src/config.py` — les ~18 paramètres exogènes actuels
- `modele-27-04-WIP/src/models.py` — bilan `Entity`, `Loan`
- `modele-27-04-WIP/src/simulation.py` — dynamique complète
- `modele-27-04-WIP/RAPPORT_ELAGAGE_MODELE.md` — ablations déjà faites
- `modele-27-04-WIP/analyse_des_equations_de_la_vie_d_une_entite.pdf` — ODE
  effective `dx/dt = −δx + b√x + c`, seuil de viabilité

## Inventaire des paramètres à classer

Classer CHAQUE paramètre de `config.py` dans exactement une catégorie :

- **Fixer par normalisation d'unités** — convention d'échelle fixable à 1 sans
  perte de généralité (exploite l'invariance `W → λW` ; rappel de
  transformation `α' = √F · α` pour l'extraction √P si elle est conservée).
- **Fusionner** — ex. les trois taux de dépréciation (tous 0.05) en un δ, puis
  absorber δ dans l'échelle de temps si possible.
- **Endogénéiser** — remplacer le paramètre par une règle qui le fait émerger
  de l'état du système (ex. « température » `T = M/N`, exposant `μ` issu d'un
  rapport de grandeurs de la règle universelle).
- **Éliminer** — mécanisme dispensable (ex. `alpha_sigma_brownien`).

Objectif : que la catégorie « paramètre libre à régler » soit **vide**. Sortie :
tableau `paramètre → catégorie → valeur/formule → justification`.

## Livrable attendu (structure du document)

1. **Principe directeur** : l'invariance d'échelle comme source commune de la
   queue de Pareto et de l'absence de paramètre d'échelle.
2. **Équations du modèle réduit** : stock de capital scalaire par entité, flux
   de revenu, extraction concave `α√P` (canal travail, borne la croissance
   propre), transfert conservatif du principal (canal candidat pour le corps de
   Boltzmann), intérêts multiplicatifs du crédit (canal capital → queue de
   Pareto), dépréciation, condition de sortie/faillite, règle de naissance —
   en identifiant explicitement quel mécanisme porte le corps exponentiel.
3. **Argument analytique** reliant chaque mécanisme à la forme de distribution
   visée (s'appuyer sur les solutions moyen-champ de Bouchaud-Mézard et
   Yakovenko ; relier à l'ODE `dx/dt = −δx + b√x + c` si `√P` est conservé).
4. **Tableau de classification des ~18 paramètres** (voir ci-dessus) et **liste
   finale des paramètres résiduels** avec justification de leur irréductibilité.
5. **Ce qu'on garde / transforme / abandonne** du modèle 27-04-WIP, motivé.
6. **Protocole de validation** :
   - Ajustement du corps : test d'exponentialité (QQ-plot exponentiel, ou
     ajustement MLE `e^{−x/T}` sur les ~95 % inférieurs).
   - Ajustement de la queue : loi de puissance par Clauset-Shalizi-Newman, et
     **stabilité de μ sur fenêtres temporelles** (500-1000, 1000-1500,
     1500-2000) — le critère qui distingue une vraie loi d'échelle d'un
     artefact. Réutiliser `recherche/analyse_distributions_taille_revenu/
     scripts/` (`families.py`, `tail_test.py`).
   - Sur revenu ET capital, ≥ 3 seeds.
7. **Bornage de la population (ouverte)** : expliciter le mécanisme endogène
   qui borne N (faillites vs naissances) sans paramètre d'échelle réglé, et le
   **garde-fou anti-cohorte d'âge** : montrer que le corps exponentiel et la
   queue de Pareto ne sont pas de simples effets « entrants récents vs
   établis » — p.ex. vérifier la forme de distribution à âge contrôlé, ou que
   l'exposant de queue est stable indépendamment de la structure d'âge.
8. **Incertitudes** et **expériences d'exploration** à lancer avant de coder.

## Contraintes

- Document seulement : ne rien modifier de `src/`.
- Pas de dépendance externe, pas de ressource bornée exogène introduite.
- Toute hypothèse sur le comportement du modèle signalée comme telle et
  vérifiable dans le code ou les données.
- Citer fichiers/lignes et équations des articles à l'appui des choix forts.
