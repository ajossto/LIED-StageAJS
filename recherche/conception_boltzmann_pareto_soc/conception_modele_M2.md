# Conception d'un modèle à distribution Boltzmann-Pareto émergente par auto-organisation critique

**Document de conception — pas d'implémentation ici.**
Destinataire : agent d'implémentation (Opus 4.8 + Sonnet).
Auteur : Claude (Fable 5), à la demande d'Anatole Joseph-Stouls, 2 juillet 2026.

Sources lues à l'appui (citées dans le texte) :
- Bouchaud & Mézard 2000 (*Wealth condensation…*, arXiv:cond-mat/0002374) — noté **[BM]**, équations numérotées comme dans l'article.
- Yakovenko & Rosser 2009 (*Colloquium: Statistical mechanics of money, wealth, and income*, Rev. Mod. Phys. 81, 1703) — noté **[YR]**.
- `modeles/anciens_modeles/modele-27-04-WIP/src/{config,models,simulation}.py` — noté **[WIP]**.
- `modeles/anciens_modeles/modele-27-04-WIP/RAPPORT_ELAGAGE_MODELE.md` — noté **[ÉLAGAGE]**.
- `modeles/anciens_modeles/modele-27-04-WIP/analyse_des_equations_de_la_vie_d_une_entite.pdf` — noté **[ODE]**.
- `recherche/analyse_distributions_taille_revenu/latex/rapport.pdf` — noté **[DISTRIB]**.
- Explorations numériques faites pour ce document :
  `recherche/conception_boltzmann_pareto_soc/exploration/` (prototype `proto_m1.py`,
  sondes `probe_body_age.py`, `probe_renewal.py`, logs `run_*.log`) — notées
  **[E0]–[E7]**, résumées en annexe A. **L'annexe A est une pièce maîtresse : elle
  documente une chaîne de sept résultats d'ablation qui contraint fortement la
  conception ; la lire avant d'implémenter.**

---

## 0. Résumé exécutif

On propose un modèle réduit — **M2** — à bilan **une colonne** (un scalaire de
capital `w ≥ 0` par entité, plus un carnet de contrats de prêt), à **règles et
paramètres strictement identiques** pour toutes les entités. La variable cible de la
forme Boltzmann-Pareto est la **valeur nette** `NW = w + créances − dettes − d₀`
(et le revenu qui en découle), pas le capital brut.

Les cinq éléments constitutifs, chacun adossé à un résultat d'exploration :

1. **Extraction concave** `Π = α√w` (imposée ; α ≡ 1 homogène) : chauffage lent,
   borne la croissance propre. Elle crée un point fixe autarcique commun
   x₊ = (α/δ)² qui est l'ennemi de la dispersion [E0] — tout le reste du modèle
   sert à tenir la population loin de ce point.
2. **Crédit conservatif à intérêts perpétuels, contrats nominaux** : transfert du
   principal = échange additif conservatif (candidat corps de Boltzmann) ; intérêts
   `r·q` et pertes de défaut ∝ encours = canal multiplicatif (queue de Pareto).
   L'asymétrie « le capital réel se déprécie, la dette nominale non » est l'horloge
   de fragilité du réseau [E1] — reprise concentrée du montage dispersé du [WIP]
   (passif inné + réévaluation paresseuse).
3. **Condition marginale au coût effectif r + δ** : sans elle, tout entrant se
   sur-endette fatalement et la classe supérieure est une aristocratie figée de
   l'ère d'amorçage [E2, E3] ; avec elle seule, plus personne ne meurt [E4]. Ce
   dilemme (sur-levier mortel / sous-levier immortel) est le résultat central des
   explorations : **la stochasticité d'appariement seule (piste n°2 du cahier des
   charges) ne suffit pas** à produire le régime.
4. **Choc multiplicatif commun en loi** `w → w·e^η`, η ~ N(−σ²/2, σ²) identique
   pour toutes (piste n°1 du cahier des charges ; le η_i(t)W_i de [BM] éq. 2).
   Nécessaire, mais pas suffisant : le drift √w domine tout bruit multiplicatif aux
   petits w, donc le bord w = 0 est inatteignable et les chocs seuls ne tuent
   personne [E5].
5. **Bilan de naissance tendu** : dotation w₀ et **dette d'amorçage nominale d₀**
   (marge ε₀ = w₀ − d₀ ≪ w₀ ; le couple (200, 190) du [WIP] en une colonne),
   dans la **fenêtre de naissance** 1/(σ+δ)² ≲ w₀ < w*(r̄+δ), ε₀ ≲ σw₀
   (établie [E6]-[E7] : en dessous, personne ne meurt ; au-dessus, le crédit
   meurt). d₀ fournit le **plancher d'absorption** qui rend le processus de
   valeur nette mortel pour toutes les entités, à tout âge [E6] — c'est lui qui
   transforme NW en variable de Boltzmann : bruit additif + multiplicatif,
   absorption en 0, réinjection à ε₀.

Le bornage de la population est endogène (N* = λ·E[vie], vérifié [E1, E6]) ; la
stabilité de l'exposant de queue est attendue d'une rétroaction auto-critique
levier ↔ cascades (§3.4) — c'est l'hypothèse de la thèse, testable, pas un acquis.

Paramètres : ~18 → **6**, dont deux conventions d'échelle (δ = temps, λ = taille),
et quatre paramètres de forme (k connectivité, σ variance du choc commun, w₀ et
d₀ bilan de naissance). Aucun n'est un « paramètre à régler pour obtenir la bonne
distribution » **si et seulement si** la forme Boltzmann-Pareto est robuste sur
leur domaine — c'est le critère d'acceptation étendu (§6.5) ; [BM] a le même
statut : μ = 1 + J/σ² dépend de (J, σ) mais la *forme* Pareto n'exige aucun réglage.

**Statut honnête** (mis à jour après le run long [E7c]) : la pile complète M2
réalise déjà, dans le prototype, **trois des quatre cibles** — population bornée
endogènement ; **queue de Pareto d'exposant stable par fenêtres**
(α_CSN = 2,80/2,86/2,88 à x_min quasi constant, loi de puissance ≫ log-normale,
exactement le critère que le [WIP] rate) ; **classes dynamiques et non
démographiques** (corr(âge, log w) ≈ 0,12 contre 0,88-0,95 au [WIP] ; queue de
même exposant à âge contrôlé). Le **corps exponentiel n'est pas encore acquis**
(log-normale/gamma gagnent l'AIC sur le corps) — c'est le chantier restant,
désormais posé dans de bonnes conditions (le corps est peuplé par la dynamique,
plus par la pyramide des âges) : expérience X1 du §8.

---

## 1. Principe directeur : une invariance d'échelle, deux régimes, un seul réseau

La forme Boltzmann-Pareto exige deux régimes statistiques ([YR] Sec. IV.B) :

- un régime **additif** : fluctuations de x indépendantes de x (drift −A₀,
  variance 2B₀), avec plancher (x ≥ 0). Solution stationnaire de Fokker-Planck :
  `P(x) ∝ e^{−x/T}`, **T = B₀/A₀** — le corps de Boltzmann ([YR] éq. 7 et 24) ;
- un régime **multiplicatif invariant d'échelle** : Δx ∝ x (Gibrat), A = a·x,
  B = b·x². Solution : `P(x) ∝ x^{−1−μ}` — la queue de Pareto. C'est l'équation de
  richesse [BM] éq. (2), solution moyen-champ [BM] éq. (7) :
  `P(w) ∝ exp(−(μ−1)/w)/w^{1+μ}`, `μ = 1 + J/σ²`.

[YR] éq. (25) donne la forme complète quand les deux coexistent
(A = A₀ + a·x, B = B₀ + b·x²) : exponentielle sous le croisement x₀ = √(B₀/b),
Pareto au-dessus, sans recollement ad hoc — le croisement est l'échelle où la
variance multiplicative dépasse la variance additive. **C'est le squelette
analytique de M2.**

Le principe directeur : les deux régimes sortent du **même système** vu de deux
positions différentes :

- pour une entité **près du plancher** (valeur nette faible, emprunteuse ou
  entrante), les flux qui bougent NW — principal reçu/prêté, intérêts payés,
  marge de naissance ε₀ — sont dimensionnés par le marché et les contreparties,
  pas par sa propre valeur nette → **bruit additif conservatif + absorption à 0**
  → corps de Boltzmann sur NW ;
- pour une entité **établie** (créancière, w grand), le choc commun σ agit sur
  tout son capital, le carnet de créances croît ∝ capacité de prêt, les revenus
  d'intérêts et les pertes de cascade sont ∝ encours → **fluctuations
  multiplicatives** → queue de Pareto par Kesten ([BM] éq. 8-9).

L'extraction concave `α√w` n'est pas le générateur de la forme : c'est le
chauffage lent qui maintient le système hors équilibre (analogue du flux d'énergie
externe, [YR] Sec. II.B) et la borne qui interdit toute queue par le canal
travail. La dépréciation δ est le puits. L'invariance d'échelle de la queue vient
de ce que tous les flux du canal capital sont proportionnels aux encours ; ce qui
doit être auto-organisé, c'est la *valeur* de μ (§3.4).

---

## 2. Le modèle M2 : état, équations, séquence

### 2.1 État

- Entité i : capital `w_i ≥ 0` (une colonne) ; **dette d'amorçage** d₀ (constante
  universelle de naissance, nominale, jamais remboursée ni dépréciée — reprise du
  passif inné B du [WIP], `models.py:79`).
- Contrat de prêt : (prêteur l, emprunteur b, principal **nominal** q, taux r),
  perpétuel, q constant de la création à l'annulation.
- Dérivés : créances `C_i = Σ q` (i prêteur), dettes `D_i = Σ q` (i emprunteur),
  **valeur nette** `NW_i = w_i + C_i − D_i − d₀` (variable cible),
  revenu `y_i = α√w_i + (intérêts reçus)_i`, revenu net = y_i − (intérêts payés)_i.

### 2.2 Séquence d'un pas (7 phases, ordre fixé)

1. **Naissances** : n ~ Poisson(λ) ; dotation w₀, dette d'amorçage d₀
   (NW initial = ε₀ = w₀ − d₀ > 0, petit). **N(0) = 0** — pas de cohorte
   fondatrice (motif : §7.2, [E2-E3]). **Fenêtre de naissance** (contrainte de
   cohérence quantitative, établie par [E6]-[E7]) :

   ```
   1/(σ+δ)²  ≲  w₀  <  w*(r̄+δ)        et        ε₀ ≲ σ·w₀
   ```

   Borne basse : la diffusion doit dominer le drift √w à la naissance
   (σ·w₀ ≳ α√w₀ − δw₀), sinon aucun entrant ne meurt jamais [E7a] ; borne
   haute : l'entrante doit naître demandeuse de crédit, sinon le marché meurt
   [E6] ; marge ε₀ de l'ordre d'un choc, sinon la mortalité infantile est
   négligeable [E7b]. Cette fenêtre n'est pas un réglage de la forme : c'est la
   condition d'existence simultanée du crédit et de la mortalité — la vérifier
   est le premier test d'implémentation.
2. **Choc multiplicatif commun** : `w_i ← w_i · e^{η_i}`, η_i i.i.d.
   ~ N(−σ²/2, σ²) — même loi pour toutes, E[e^η] = 1 (pas de drift moyen ; ne pas
   répéter le bug du brownien d'α du [WIP], `simulation.py:1320`). C'est le
   η_i(t)W_i de [BM] ; il frappe le capital réel, PAS les contrats (les créances
   ne sont pas un refuge sans risque pour autant : elles portent le risque de
   défaut — c'est la boucle SOC §3.4).
3. **Extraction** : `w_i += α√w_i`, α ≡ 1.
4. **Service des intérêts** : chaque contrat, l'emprunteur paie `r·q` au prêteur
   depuis w (transfert conservatif). Paiement partiel possible (tout le w
   disponible) puis **défaut** → faillite en phase 7.
5. **Dépréciation** : `w_i ← (1−δ)·w_i`. Contrats et d₀ **non dépréciés**
   (asymétrie constitutive, §2.4).
6. **Marché du crédit** : ⌊N/k⌋ rounds ; par round, tirage uniforme de k entités
   vivantes ; prêteur = w maximal, emprunteur = w minimal (équivalent au tri par
   r* = α/(2√w) à α homogène) ; taux `r = √(r*_l · r*_b)` (moyenne géométrique,
   convention symétrique sans paramètre) ; volume :

   ```
   coût/rendement effectif d'une unité de capital échangée : ρ = r + δ
   cible commune de capital : w*(ρ) = (α/(2ρ))²
   demande de l'emprunteur  : q_dem = max(0, w*(ρ) − w_b)
   offre du prêteur         : q_off = max(0, w_l − w*(ρ))
   volume : q = min(q_dem, q_off) ; transfert conservatif w_l −= q, w_b += q ;
   création du contrat (l, b, q, r).
   ```

   Une seule règle symétrique — « viser w*(ρ) ; prêter l'excédent, emprunter le
   manque » — définit les deux rôles ; personne n'est prêteur ou emprunteur par
   nature. Répond aux notes inline du [WIP] (`simulation.py:867` rounds aléatoires,
   `:900` pool unique, `:870` suppression de `MAX_IDLE`).
7. **Faillites en cascade** : critère `NW_i < 0` (ou défaut en phase 4). À la
   faillite de i : contrats empruntés annulés (perte sèche des prêteurs → choc
   multiplicatif négatif → contagion) ; contrats prêtés transférés aux créanciers
   au prorata ([WIP] `process_single_failure` phase 2, sans réévaluation puisque
   nominal) ; capital résiduel w_i réparti aux créanciers au prorata ; d₀ éteinte
   (personne ne la détient). Itérer jusqu'à stabilité. La mort est la seule sortie.

Pas d'auto-investissement paramétrique (une colonne ⟹ φ ≡ 1 structurel), pas
d'amortissement, pas de reliquéfaction, pas de contrainte d'endettement
paramétrique, pas de prime μ, pas de seuil de participation.

### 2.3 Ce que chaque mécanisme porte (engagement explicite)

| Mécanisme | Rôle dans la forme cible | Preuve/statut |
|---|---|---|
| Extraction `α√w` | chauffage ; anti-queue du canal travail ; fixe x₊ = (α/δ)² | imposé ; [E0] montre son piège (point fixe commun) |
| Transferts conservatifs (principal, intérêts) | bruit additif du corps de Boltzmann sur NW | hypothèse H1, test §6.1 + X1 |
| Intérêts perpétuels + pertes de défaut ∝ encours | canal multiplicatif → queue de Pareto (Kesten) | loi de puissance déjà favorisée [E1] ; stabilité de μ = hypothèse H2, test §6.2 |
| Choc commun σ (piste 1) | variance multiplicative de base 2σ² ([BM]) ; anti-esquive comportementale | nécessité démontrée [E4-E5] |
| Asymétrie nominal/réel | horloge de fragilité (défauts, cascades) | nécessité démontrée [E0] vs [E1] |
| Dette d'amorçage d₀ | plancher d'absorption de NW ; mortalité universelle à tout âge | nécessité démontrée [E5] vs [E6] |
| Coût effectif r+δ | classes = états traversables (renouvellement), pas cohortes | nécessité démontrée [E2-E3] vs [E4] |
| Faillite NW < 0 + cascade + naissances Poisson, N(0)=0 | absorption/réinjection du corps ; chocs négatifs de la queue ; bornage N* = λ·E[vie] | bornage vérifié [E1, E6] |

### 2.4 Justification de l'asymétrie nominal/réel

1. **Nécessité** [E0] : dette dépréciée au même taux que le capital ⟹ le prêt est
   neutre, personne ne meurt, population non bornée, distribution piquée
   (P90/P10 = 1,1). Le [WIP] obtient sa mortalité par le même principe, dispersé
   sur trois dispositifs : passif inné jamais déprécié, dépréciation du liquide
   face à lui, réévaluation paresseuse des créances (`simulation.py:470`,
   `compute_hidden_fragility` `:1034`). M2 le concentre en UNE asymétrie lisible :
   la dette ne s'use pas.
2. **Minimalité** : l'alternative — un coût fixe de subsistance c₀ — serait un
   paramètre d'échelle exogène pur ([ODE] cas C). L'asymétrie nominal/réel crée le
   flux net négatif *en unités des encours existants*, sans échelle nouvelle.
3. **Conséquence assumée** : le coût effectif d'un emprunt est r + δ et la règle
   de décision doit l'utiliser (§2.5), sinon artefact [E2-E3].

### 2.5 Le dilemme du levier et sa résolution (cœur de la conception)

Chaîne de résultats (détails annexe A) :

- **Règle naïve** (coût r, comme `_borrower_qmax` du [WIP] `simulation.py:716`
  transposé au bilan une colonne) : tout entrant s'endette jusqu'à la zone non
  viable ([ODE] cas E), meurt jeune (âge médian 16-20 pas) ; la classe supérieure
  = entités nées avant l'existence de créanciers, survie 100 % sur 1000 pas, zéro
  renouvellement [E2] ; le corps = cohorte en transit (déciles bas : âge médian
  2-16 pas, dette ≈ 100 % du capital) [E3]. C'est l'artefact [DISTRIB] recréé.
- **Règle corrigée** (coût r + δ) : l'emprunt devient petit et survivable… et la
  mortalité disparaît totalement (0 faillite, population non bornée) [E4]. Le
  choc commun σ ne la restaure pas : le drift √w domine tout bruit multiplicatif
  borné aux petits w, le bord w = 0 est inatteignable [E5].
- **Résolution** : le plancher ne peut être ni comportemental ni sur w — il doit
  être sur la **valeur nette**, via une dette incompressible : d₀. Avec (w₀, d₀)
  tendus (ε₀ ≪ w₀), chaque entité — entrante ou établie — meurt si son NW
  franchit 0 sous les chocs, les charges d'intérêts ou les pertes de créances.
  Mortalité universelle rétablie, population bornée [E6]. Le crédit reste actif
  si w₀ < w*(r̄+δ) (l'entrante naît demandeuse) — contrainte de cohérence entre
  w₀ et la zone d'échange, vérifiée en [E7].

Aucun de ces trois éléments n'est un paramètre de calibration de la forme : la
règle r+δ est l'optimalité correctement écrite (zéro paramètre), d₀ reprend le
passif inné existant du [WIP], σ est la piste n°1 du cahier des charges.

---

## 3. Argument analytique

### 3.1 Dynamique individuelle effective

Entre événements discrets ([ODE]) :

```
dw/dt = −δw + α√w + c_eff,   c_eff = intérêts reçus − payés ± principal ± pertes
```

- Autarcie (c_eff = 0) : convergence vers x₊ = (α/δ)², commun — le régime à
  détruire [E0].
- Endettée : cas C de [ODE] (seuil de viabilité x₋) puis cas E si les charges
  s'accumulent — l'horloge de fragilité.
- Créancière : cas A tant que le portefeuille paie, chocs négatifs brutaux aux
  défauts (c_eff ↓ discontinu) — le terme multiplicatif bruité demandé par le
  cahier des charges (« ODE + terme multiplicatif bruité issu des intérêts nets »).

En sus, phase 2 : d(ln w) reçoit η − σ²/2 par pas (choc commun), et le plancher
NW = 0 remplace le bord w = 0 (inatteignable, [E5]).

### 3.2 Fokker-Planck sur la valeur nette ([YR] éq. 23-25)

Variable X = NW. Moments des incréments conditionnés à X :

- **X petit (corps)** : les flux dominants — marge de naissance ε₀, intérêts
  payés/reçus par contrat (r·q dimensionné par le marché), transferts de
  principal, extraction nette α√w − δw évaluée près de w*(ρ) — sont **bornés et
  indépendants de X**. D'où A(X) ≈ A₀ (drift net, tiré vers le bas par les
  charges nominales), B(X) ≈ B₀ (variance additive des flux de crédit +
  σ²·w*(ρ)² du choc commun à capital borné). Plancher absorbant X = 0
  (faillite) + réinjection à ε₀ (naissances) ⟹ corps exponentiel
  `P(X) ∝ e^{−X/T}`, **T = B₀/A₀ endogène** (rapport de flux mesurables).
  Condition de validité (leçon [E3]) : le bas de la distribution doit être peuplé
  par la *dynamique* (établies redescendues, endettées en sursis), pas par une
  pyramide des âges — garde-fou §6.3.
- **X grand (queue)** : l'entité est créancière, son capital réel et son carnet
  scalent avec X : chocs communs σ·w, revenus r̄·C, pertes de cascade ∝ C, tous
  ∝ X ⟹ A(X) ≈ a·X, B(X) ≈ b·X² ⟹ `P(X) ∝ X^{−1−μ}` avec μ = 1 + a/b au sens
  [YR] (25).
- **Croisement** : X₀ = √(B₀/b) — la frontière de classes, endogène.

### 3.3 La queue comme processus de Kesten

Pour une établie : `X(t+1) = Λ(t)·X(t) + β(t)` avec

```
Λ(t) = 1 + η(t) − δ·h(t) + r̄·c(t) − ℓ(t)
```

(h = w/X part réelle, c = C/X part financiarisée, ℓ = pertes de défaut relatives,
intermittentes ; β = flux additifs). Queue en loi de puissance dès que Λ fluctue
avec E[ln Λ] < 0 < P(Λ > 1) ; μ est la racine de **E[Λ^μ] = 1** ([BM] éq. 8-9).
Repères analytiques :

- sans crédit (h = 1, c = ℓ = 0), η log-normal : μ ≈ 1 + 2δ/σ² — première
  échelle de contrôle : σ² trop petit devant δ ⟹ queue très raide (μ ≈ 11 pour
  δ = 0,05, σ = 0,1) ; la fenêtre intéressante commence vers σ² ≳ δ ;
- le crédit *abaisse* μ pour les financiarisées (r̄·c compense δ·h : E[Λ] ↑) et
  le *relève* par ℓ (cascades). μ_effectif sort de cette compétition — d'où §3.4.

À l'opposé de la diffusion log-normale sans rappel qui produit la fausse queue du
[WIP] ([DISTRIB] : exposant dérivant 5,4 → 3,1), un Kesten stationnaire a un μ
constant — critère §6.2.

### 3.4 L'hypothèse auto-critique sur μ (H2 — la thèse elle-même)

μ résout E[Λ^μ] = 1, avec Λ couplé à l'état macroscopique par une rétroaction de
signe stabilisant :

- queue plus lourde (μ ↓) ⟹ crédit plus concentré, chaînes d'intermédiation plus
  profondes (bifurcation k ≥ 3, [ÉLAGAGE] §3) ⟹ cascades plus grandes ⟹ ℓ ↑
  ⟹ μ ↑ ;
- queue plus légère (μ ↑) ⟹ crédit dispersé, cascades amorties ⟹ ℓ ↓ ⟹ μ ↓.

Le niveau de levier joue le rôle du paramètre de contrôle rappelé vers sa valeur
critique — c'est l'analogue exact du bornage démographique (E[vie] répond au
levier). Prédictions testables : (i) μ stationnaire par fenêtres ; (ii) μ
insensible à λ, w₀, et à k dans la phase SOC ; (iii) distribution des tailles de
cascade à queue lourde au voisinage du régime où μ est stable ; (iv) si σ → 0, le
moteur multiplicatif de base s'éteint et μ doit se raidir continûment (pas de
discontinuité — le crédit maintient un canal multiplicatif résiduel).
**Statut : hypothèse à démontrer, pas un acquis. Le protocole §6.2 est le juge.**

### 3.5 Le revenu

`y = α√w + intérêts reçus`. Pour le corps (w ≈ w*(ρ) borné), y hérite du bruit
additif → corps de y exponentiel si celui de NW l'est (à vérifier séparément,
[DISTRIB] rappelle qu'à α homogène taille et revenu ne sont PAS des tests
indépendants pour la composante extraction ; l'indépendance vient des intérêts).
Pour la queue, y ≈ r̄·C ∝ NW → même exposant μ. Mesurer les deux (§6).

---

## 4. Classification des ~18 paramètres de `config.py`

Catégories : **N** = normalisation d'unités ; **F** = fusion ; **E** = endogénéisé ;
**X** = éliminé ; **T** = transformé ; **R** = résiduel justifié.

| Paramètre [WIP] (valeur) | Cat. | Devenir dans M2 | Justification |
|---|---|---|---|
| `alpha` (1.0) | **N** | α ≡ 1 | Unité de flux/capital (w → F·w ⟺ α → √F·α, [ÉLAGAGE] §10). Fixe x₊ = (α/δ)². |
| `alpha_min`, `alpha_max` (0.8, 1.2) | **X** | supprimés | Hétérogénéité innée interdite (contrainte n°1) ; brise-symétrie remplacé par la position dans le réseau + l'histoire des chocs communs. |
| `alpha_sigma_brownien` (0.005) | **T** | → **σ**, choc commun par pas sur w | Le brownien d'α était (a) bugué (drift positif, `simulation.py:1320`, cause de 80 % de runs non stationnaires [DISTRIB]) et (b) une hétérogénéité *persistante* déguisée (α_i dérive et se fige). Remplacé par un choc i.i.d. par pas, loi commune, sans mémoire : c'est la piste n°1 du cahier des charges, et le σ² de [BM]. Nécessité démontrée [E4-E5]. |
| `seuil_ratio_liquide_passif` (0.05) | **X** | supprimé | Plus de compartiments ; le rôle de réserve est repris par la cible w*(ρ). |
| `theta` (0.35) | **X** | supprimé (θ ≡ 1) | θ compensait le coût mal écrit (r au lieu de r+δ) → sur-levier structurel à brider. Avec ρ = r+δ, q_dem est déjà borné [E4]. Si un θ < 1 se révélait de nouveau nécessaire, le déclarer comme limite (retour du paramètre à régler). |
| `mu` prime (0.05) | **X** | supprimé | Raffinement comportemental sans rôle dans la forme. |
| `seuil_ratio_endettement` (1) | **X** | supprimé | [ÉLAGAGE] : peu d'effet ; [E2] : ne mord pas quand le coût est correct. La contrainte réelle est NW ≥ 0. |
| `fraction_taux_emprunteur` (0.2) | **N** | moyenne géométrique | Règles identiques ⟹ aucune asymétrie justifiable ; √(r*_l·r*_b) est le choix symétrique invariant d'échelle. Convention à figer, pas à régler. |
| `taux_amortissement` (0) | **X** | supprimé | Déjà nul ; refus explicite de l'auteur (`simulation.py:1228`). Prêts perpétuels. |
| `n_entites_initiales` (100) | **X** | **N(0) = 0** | La cohorte fondatrice est la source des fausses classes ([DISTRIB] §1 ; [E2-E3]). Amorçage par le flux seul, transitoire exclu des mesures. |
| `lambda_creation` (2) | **R** échelle | λ | Ne fixe que N* = λ·E[vie] (vérifié [E1] : λ = 2/10/30 ⟹ N* ≈ 29λ, formes semblables). Analogue du N de [YR]. |
| `actif_liquide_initial` (200) | **T**+**R** | dotation w₀ | Une colonne ⟹ un seul montant brut. Fenêtre de naissance : 1/(σ+δ)² ≲ w₀ < w*(r̄+δ) [E6-E7] (et w₀ ≪ x₊). Piste d'endogénéisation (X3 : w₀ = quantile bas des w vivants — « héritage social ») pour éliminer l'échelle. |
| `passif_inne_initial` (190) | **T** (gardé!) | **dette d'amorçage d₀** | D'abord classé « à éliminer » ; les explorations [E4-E5-E6] ont montré qu'il est le **plancher d'absorption irremplaçable** : sans lui, coût correct + chocs communs ⟹ zéro mortalité. C'est le seul dispositif qui rende NW mortel pour toutes, à tout âge, sans règle comportementale. Paramétrer par la marge ε₀ = w₀ − d₀. |
| `taux_depreciation_liquide`, `_endo`, `_exo` (3 × 0.05) | **F**+**N** | un seul δ | Déjà égaux. δ = unité de temps (temps continu : δ ≡ 1 ; en discret δ ≪ 1 = résolution, invariance δ → δ/2 à vérifier, X5). La dépréciation *des créances* disparaît en tant que règle : contrats nominaux (§2.4), fragilité explicite au lieu de cachée. |
| `coefficient_reliquefaction` (0.5) | **X** | supprimé | Plus de compartiments à convertir ; peu sollicité ([ÉLAGAGE] §4). |
| `fraction_auto_investissement` (0.5) | **X** | supprimé (φ ≡ 1) | Une colonne : le produit d'extraction est du capital productif. |
| `n_candidats_pool` k (3) | **R** contrôle SOC | k | Connectivité du marché, analogue du c de [BM] éq. 16-17 (μ dépend faiblement de c). Transition stable → SOC à k ≥ 3 ([ÉLAGAGE]). La thèse exige la robustesse du régime pour k ≥ 3 (X5) — k est un paramètre de contrôle à balayer, pas à calibrer. |
| `max_credit_iterations` (10⁵) | **X** | supprimé | Boucle = ⌊N/k⌋ rounds (chaque entité échantillonnée ~1 fois/pas : définition du pas de marché, pas un paramètre). Supprime aussi `MAX_IDLE = max(20, k²)` caché (`simulation.py:870`). |
| `epsilon` (1e-6) | **N** | garde numérique | Sans rôle dynamique ([ÉLAGAGE] : 1e-3 conserve le régime). |
| `duree_simulation`, `seed`, `log_events`, `freq_snapshot` | — | techniques | Hors modèle. |

**Liste finale des paramètres de M2 et irréductibilité :**

| Paramètre | Statut | Irréductibilité |
|---|---|---|
| α = 1 | convention d'unité | — |
| δ | convention d'unité de temps | réductible en principe (X5) |
| λ | convention de taille N* | réductible (extensivité vérifiée [E1]) |
| k | contrôle SOC (connectivité) | structurel ; robustesse exigée pour k ≥ 3 (X5) |
| σ | variance du choc commun (piste 1) | irréductible — c'est le σ² de [BM] ; la forme ne doit PAS en dépendre, seulement μ (X4) ; repère : σ² ≳ δ |
| w₀, d₀ (ou w₀, ε₀) | bilan de naissance | w₀ contraint (< w*(r̄+δ)) avec piste d'endogénéisation (X3) ; ε₀ = échelle de réinjection du corps — candidat naturel : la forme exige seulement ε₀ ≪ T mesurée (X3) |

Verdict sur l'objectif « zéro paramètre réglé » : il reste (k, σ, ε₀/w₀) comme
paramètres de forme. L'objectif est atteint **au sens de [BM]** — aucun ne doit
être ajusté pour obtenir la *forme* Boltzmann-Pareto, seulement les valeurs de
(T, μ, X₀) — et ce point devient un critère d'acceptation explicite (§6.5). Tout
écart (une forme qui n'apparaît que dans un îlot fin de (σ, ε₀)) devra être
rapporté comme réfutation partielle de la thèse.

---

## 5. Garder / transformer / abandonner (par rapport au 27-04-WIP)

**Gardé**
- Extraction concave `α√P` → `α√w` (imposée).
- Prêts perpétuels à intérêts payés chaque pas.
- Passif inné → dette d'amorçage d₀ (rôle enfin explicité : plancher d'absorption).
- Faillite par insolvabilité + cascades + redistribution des créances au prorata
  (`process_single_failure` `simulation.py:1060`, simplifiée : plus de
  réévaluation).
- Naissances Poisson(λ).
- Esprit du matching local k (reformulé).

**Transformé**
- Bilan 8 postes (`models.py:72-88`) → w + contrats + d₀ ; NW calculé.
- Marché : double pool trié + MAX_IDLE + θ + μ + seuil L/P
  (`credit_market_iteration` `simulation.py:854`) → ⌊N/k⌋ rounds, tirage uniforme,
  règle symétrique unique « viser w*(r+δ) ».
- Fragilité : {passif inné + réévaluation paresseuse + dépréciations asymétriques}
  → {contrats nominaux vs capital déprécié} + {d₀}.
- Condition marginale : coût r → coût r + δ (la transformation la plus lourde de
  conséquences, [E2]-[E4]).
- Brownien d'α (hétérogénéité persistante, buguée) → choc commun i.i.d. par pas σ
  (sans mémoire, sans drift).
- Amorçage : 100 entités à t=0 → N(0) = 0.
- Dotation (L=200, B=190) → (w₀, d₀) avec w₀ < w*(r̄+δ).

**Abandonné** (motivé par [ÉLAGAGE] §4, la contrainte une-colonne, ou la traque
des paramètres cachés)
- Hétérogénéité d'α innée (contrainte utilisateur) et brownienne persistante.
- Auto-investissement paramétrique, reliquéfaction, cession de créances en
  paiement (`_ensure_payment_capacity` étapes 2-4), amortissement, contrainte
  d'endettement, prime μ, seuil L/P, comptabilité endo/exo, réévaluation
  paresseuse, `MAX_IDLE`, θ.

---

## 6. Protocole de validation (critère d'acceptation)

Mesures sur **NW, revenu ET capital w** (NW = variable théorique du §3, revenu =
variable de la thèse énoncée, w = diagnostic), **≥ 3 seeds**, t ≥ 500 (hors
transitoire). Réutiliser `recherche/analyse_distributions_taille_revenu/scripts/`
(`families.py` : échelle AIC/BIC exponentielle/gamma/log-normale/Fisk ;
`tail_test.py` : CSN + LR contre log-normale). Le prototype `proto_m1.py` contient
déjà l'outillage (fonctions `body_fits`, `analyze`, pooling par fenêtres).

### 6.1 Corps exponentiel (cible dure)
- MLE `e^{−x/T}` sur les ~95 % inférieurs, comparé par AIC/BIC à gamma,
  log-normale, Fisk : l'exponentielle gagne ou ΔAIC ≤ 2 — pas « une Fisk étroite
  fait l'affaire ».
- QQ-plot exponentiel (linéarité, pas de coude).
- Diagnostics rapides : mode en 0 (histogramme décroissant dès le premier bin),
  med/mean du corps ≈ ln 2 ≈ 0,69.
- **Test mécanistique** : T mesurée ≈ B₀/A₀ mesurés indépendamment (variance et
  drift des incréments de NW des entités du corps) — vérifie que le corps vient du
  canal identifié et pas d'un accident de forme.

### 6.2 Queue de Pareto stable (cible dure — là où le [WIP] échoue : 5,4 → 3,1)
- CSN (x_min par KS, MLE de l'exposant, LR contre log-normale) sur **pools par
  fenêtres** : instantanés tous les 50 pas agrégés sur [500,1000), [1000,1500),
  [1500,2000) — jamais de pooling entre seeds ni entre régimes ([DISTRIB]
  §Méthode) ; les instantanés espacés de 50 pas ≫ vie médiane (~20-30 pas) sont
  quasi indépendants.
- ⚠ Piège mesuré [E1] : l'estimateur x_min saute entre régimes de lecture selon la
  fenêtre (α = 2,8 à x_min = 11 vs 6,5 à x_min = 41 sur les mêmes données) →
  imposer EN PLUS la comparaison des exposants **à x_min commun fixé** (médiane
  des x_min de fenêtres).
- Critère : |μ_i − μ_j| entre fenêtres compatible avec le bootstrap des pools,
  sur 3 fenêtres × 3 seeds, ET LR(loi de puissance vs log-normale) > 0
  systématique. Ajouter une 4ᵉ fenêtre (T = 3000-4000) si le coût le permet.

### 6.3 Garde-fou anti-cohorte d'âge
- corr(âge, log NW) nettement < 0,85 ([WIP] : 0,88-0,95 ; prototype naïf : 0,75 —
  encore trop) et décroissante avec T.
- **Forme à âge contrôlé** : refaire 6.1-6.2 sur tranches d'âge fixes (p. ex.
  [50,150) et [150,400)) — corps exponentiel et queue non triviale doivent
  subsister DANS une tranche (le prototype naïf échoue : α_CSN ≈ 11-14 à âge
  contrôlé [E1-pool]).
- **Renouvellement** (sonde `probe_renewal.py`) : entre t et t+1000, top décile de
  NW : fraction née dans les 1000 derniers pas ≥ ~20 %, survie du top < 100 %,
  dates de naissance du top étalées (pas concentrées sur l'ère d'amorçage).
- Distribution des âges : décroissance régulière, pas de trou démographique
  ([DISTRIB] fig. cohorte).

### 6.4 Diagnostics SOC (soutien de la thèse)
- Distribution des tailles de cascade : queue lourde pour k ≥ 3, coupure
  exponentielle pour k ≤ 2 (la transition d'[ÉLAGAGE]).
- Stationnarité : N(t), W_tot(t), volume de prêts plats hors transitoire ;
  N(t) PLAT et non affine (une pente affine = classe immortelle qui s'accumule,
  §7.1).
- Mortalité du top décile par fenêtre de 500 pas > 0.

### 6.5 Robustesse de la forme (le « sans réglage fin »)
Grille (σ ∈ {0,15 ; 0,25 ; 0,35}) × (ε₀/w₀ ∈ {0,05 ; 0,25 ; 0,5}) × (k ∈ {3, 6}),
1 seed par case + 3 seeds sur la diagonale : la **forme** (6.1 + 6.2 + 6.3) doit
passer sur toute la grille ; seuls T, μ, X₀ bougent, de façon monotone et lisse.
Un îlot fin de validité = réfutation partielle à rapporter.

---

## 7. Population ouverte : bornage endogène et structure d'âge

### 7.1 Mécanisme de bornage
E[vie] est finie pour toutes les positions : entrantes (marge ε₀ sous les chocs),
endettées (horloge nominal/réel), créancières (cascades + chocs communs sur w).
D'où N* = λ·E[vie] stationnaire sans capacité de charge exogène — vérifié [E1]
(N* ≈ 29λ, λ ∈ {2,10,30}) et [E6] (mortalité restaurée par d₀). λ ne fixe que
l'échelle ; E[vie] est la réponse endogène du système (rétroaction §3.4).
Symptôme à surveiller : N(t) affine = sous-population immortelle ([E4] : +λt
exactement quand la mortalité s'éteint). L'hypothèse utilisateur (« immortalité
des originaires = artefact d'espérance de vie ≫ durée simulée ») est confirmée en
pire dans le prototype naïf : mortalité du top strictement nulle sur 1000 pas
[E2] ; M2 doit la rendre positive (critère 6.4).

### 7.2 Amorçage sans cohorte fondatrice
N(0) = 0 ; le monde démarre vide et s'amorce par le flux ([E1] : les premières
arrivées croissent en autarcie, le crédit démarre dès qu'un gradient existe).
L'ère d'amorçage (t ≲ 100) reste un environnement anormalement favorable →
exclusion du transitoire des mesures ET garde-fou de renouvellement 6.3 (l'avantage
d'époque doit s'éteindre).

### 7.3 Pourquoi les classes de M2 ne seraient pas des cohortes
L'appartenance de classe est un **état** (position par rapport à w*(ρ) et niveau
de NW), pas une date : montée possible (croissance autofinancée + chance des
chocs communs + carnet de créances), descente possible (cascades, suites de chocs
négatifs — [BM] éq. 14-15 : temps de relaxation fini, « rich become poor on a
finite time scale »). La différence structurelle avec le prototype naïf : le coût
r+δ rend la traversée montante survivable [E4], d₀ + σ rendent la position haute
mortelle [E6]. Si 6.3 échoue malgré cela, appliquer §8-X2 et rapporter la limite.

---

## 8. Incertitudes et expériences à lancer avant de coder la version définitive

Par priorité. X1-X2 conditionnent la conception ; X3-X6 la valident.

**X1 — Le corps exponentiel sur NW (LA question ouverte, cible dure).**
Constat : le prototype naïf donne un corps Fisk/gamma qui est une pyramide des
âges [E3] ; la conception révisée déplace le corps sur NW avec plancher
d'absorption réel (d₀) et bruit additif de crédit. Plan :
1. sur M2 complet ([E7] et au-delà) : composition en âge des déciles bas de NW
   (`probe_body_age.py` adapté à NW) — exiger des établies redescendues ;
2. test 6.1 complet sur NW et revenu ; mesurer A₀, B₀ sur les incréments et
   vérifier T ≈ B₀/A₀ ;
3. si le corps reste piqué : renforcer le canal additif à σ constant — churn de
   principal plus fréquent (k ↑ à rounds·k = N constant), taux plus élevés (via
   la borne basse : moyenne arithmétique au lieu de géométrique) ;
4. si le corps sort en `exp(−(μ−1)/X)·X^{−1−μ}` de [BM] éq. (7) (coupure basse,
   pas exponentielle) : le dire explicitement et confronter les deux ajustements —
   ce serait un résultat de recherche en soi (le corps [BM] contre le corps
   [YR]), pas un échec à maquiller.

**X2 — Renouvellement des classes dans M2 complet.**
`probe_renewal.py` sur M2 (top décile de NW) : fraction du top née dans les 1000
derniers pas ≥ ~20 %, survie < 100 %, mortalité du top > 0 par fenêtre. Si échec,
variantes ordonnées : (i) annulation symétrique des créances de la faillie au lieu
du transfert au prorata (vide les carnets aux cascades → redistribution brutale
vers le bas) ; (ii) σ ↑ (chocs plus lourds sur les établies) ; (iii) en dernier
recours, revisiter le partage prorata du capital résiduel (le donner aux
créancières renforce les grosses — variante : destruction pure).

**X3 — Bilan de naissance : sensibilité et endogénéisation.**
(i) Sensibilité : (w₀, ε₀/w₀) sur la grille 6.5 — la forme ne doit pas en
dépendre. (ii) Variante endogène : w₀(t) = quantile 10 % des w vivants, d₀ = même
règle − ε₀… attention à la boucle démographique ; flag `--w0-endo` déjà présent
dans le prototype. (iii) Vérifier la contrainte de cohérence w₀ < w*(r̄+δ) en
régime (sinon le crédit meurt, [E6]).

**X4 — Validation complète** : protocole §6 intégral sur M2, 3 seeds × T = 2000
(idéalement 4000), λ = 30 (pools ≈ 8000 points/fenêtre suffisants pour CSN, [E1]).

**X5 — Conventions d'échelle** : δ → δ/2 à 2T (invariance de temps) ; λ = 10/30/100
(extensivité) ; k ∈ {2,3,4,6} (transition SOC + robustesse — la démonstration
« sans réglage »).

**X6 — Diagnostics SOC** : tailles de cascade par k ; corrélation concentration du
crédit ↔ taille de cascade (mécanisme §3.4) ; réponse de μ à σ (prédiction iv du
§3.4).

**Incertitudes assumées** (à reporter telles quelles dans le rapport du modèle) :
1. Le corps exponentiel n'est garanti par aucun théorème ici : l'extraction
   concave crée un rappel que le bruit additif doit dominer près du plancher. Si
   X1 aboutit à la coupure [BM] plutôt qu'à l'exponentielle [YR], la thèse est à
   amender honnêtement.
2. La stabilité de μ (H2, §3.4) est plausible, non prouvée ; 6.2 est le juge.
3. Le choc commun σ est une *source* exogène de multiplicativité : la thèse
   defendue devient « le couple SOC (crédit+faillites) *stabilise et structure*
   en Boltzmann-Pareto une variance multiplicative donnée », pas « crée la
   multiplicativité ex nihilo ». Si on veut σ = 0 strict, il faut que le crédit
   seul fournisse la variance multiplicative — les explorations montrent que ce
   n'est pas suffisant dans la version naïve [E4-E5] ; à retester après X1-X2.
4. Conventions non testées : moyenne géométrique des taux, max/min de
   l'échantillon (vs paire aléatoire), transfert prorata. À passer en variantes
   si un comportement inattendu apparaît.
5. Les valeurs numériques du prototype (N* ≈ 29λ, α_CSN ≈ 2,8) ne sont pas des
   prédictions pour M2 complet — preuves d'existence de régime seulement.

---

## Annexe A — Chaîne d'explorations numériques (preuves d'ablation)

Scripts et logs : `recherche/conception_boltzmann_pareto_soc/exploration/`.
Prototype `proto_m1.py` (~400 lignes, indépendant de `src/`), flags :
`--no-deprec-loans` (asymétrie nominal/réel), `--n0`, `--cost-delta` (coût r+δ),
`--gbm-sigma` (choc commun), `--d0` (dette d'amorçage), `--w0-endo`,
`--service-cap`, `--pool_every` (pools par fenêtres). Communs : α = 1, δ = 0,05
(x₊ = 400), k = 6, rounds = N/6, taux géométrique. Les runs [E0]-[E3] utilisent
en outre θ = 0,35 et offre = w/2 (héritages du [WIP], supprimés dans M2).

**[E0] Contrôle symétrique** (dettes dépréciées comme le capital ; T = 600) :
0 faillite, population = n₀ + λt (non bornée), corps ultra-piqué vers x₊
(P90/P10 = 1,1, med/mean = 1,03), pas de queue. → La fragilité asymétrique est
constitutive.

**[E1] Asymétrie nominal/réel, règle naïve** (`--no-deprec-loans`, seeds 0/1/2,
λ ∈ {2,10,30}, T = 2000 ; `run_s*.log`, `run_lam30*.log`) :
- population bornée stationnaire N* ≈ 29λ, W_tot plat, faillites/pas ≈ λ ;
- deux régimes : med/mean ≈ 0,63-0,68, P90/P10 ≈ 7-13 (w) ;
- queue : loi de puissance favorisée contre log-normale sur le revenu (LR jusqu'à
  +1525, p < 10⁻³) ; α_CSN(revenu) = 2,76-2,91 (x_min ≈ 11) ; à x_min ≈ 41 :
  6,58 puis 6,49 sur deux fenêtres poolées (~8000 points) — l'estimateur x_min
  saute entre régimes de lecture → protocole 6.2 ;
- corps : Fisk/gamma battent l'exponentielle partout (ΔAIC 40-200) ;
- corr(âge, log w) ≈ 0,75-0,78 ; à âge contrôlé [20,100) : α_CSN ≈ 11-14 → pas de
  queue intra-cohorte.

**[E2] Renouvellement, règle naïve** (`probe_renewal.py`, n₀ = 0, λ = 10) : top
décile de w à t = 2000 entièrement né avant t ≈ 8 ; survie du top de t = 1000 à
t = 2000 : 100 % ; entrées nées après t = 1000 : 0. Le plafond de service
(`--service-cap`, seuil = 1) ne change rien (il ne mord pas). → Aristocratie
figée ; la cause est le coût mal évalué, pas le sur-emprunt ponctuel.

**[E3] Composition du corps** (`probe_body_age.py`, t = 1000, λ = 10) : déciles
D1-D7 de w : âge médian 2-16 pas (montée autarcique : 254 pas), dette ≈ 90-100 %
du capital, créances nulles — corps = entrants en transit sur-endettés. D8-D10 :
âge = 1000 (ère d'amorçage), créancières pures. → Les « deux classes » du
prototype naïf sont deux cohortes ; fonde §2.5 et le garde-fou 6.3.

**[E4] Coût corrigé r+δ seul** (`--cost-delta`, T = 400, λ = 10) : 0 faillite,
population non bornée (4069 à t = 400), crédit actif mais petit, retour au
voisinage du point fixe. → La règle rationnelle correcte TUE la mortalité : le
dilemme du levier est structurel, pas paramétrique.

**[E5] + choc commun σ = 0,1** (`--gbm-sigma 0.1`) : toujours 0 faillite,
population non bornée (4054 à t = 400), w_max ≈ 1900 (dispersion par les chocs,
sans mortalité). → Le drift √w domine tout bruit multiplicatif aux petits w : le
bord w = 0 est inatteignable ; la mort ne peut passer que par un plancher de
valeur nette.

**[E6] + dette d'amorçage (w₀ = 200, d₀ = 190)** : mortalité restaurée
(1595 faillites à t = 200), population bornée (~290-390, faillites ≈ naissances)…
mais **crédit mort** (0 prêt) : w₀ = 200 > w*(r̄+δ) ≈ 44 — personne ne demande.
→ Contrainte de cohérence w₀ < w*(r̄+δ) intégrée à la conception (§2.2 phase 1).

**[E7] Pile complète M2** (`--cost-delta --gbm-sigma σ --no-deprec-loans --d0`,
n₀ = 0, λ = 10) — trois étapes de calage de la fenêtre de naissance :
- **[E7a]** σ = 0,15, w₀ = 20, d₀ = 10 : 0 faillite à t = 200 (pop 2019, non
  bornée). Le drift √w (+3,5/pas à w₀ = 20) écrase les chocs (σw₀ = 3) : personne
  ne meurt. → borne basse de la fenêtre : σw₀ ≳ √w₀ − δw₀, soit w₀ ≳ 1/(σ+δ)².
- **[E7b]** σ = 0,25, w₀ = 20, d₀ = 10 : mortalité restaurée mais insuffisante
  (144 faillites à t = 200 contre ~2000 naissances ; pop 1921, croissante) :
  ε₀ = 10 = 2σw₀ de coussin. → ε₀ ≲ σw₀.
- **[E7c]** σ = 0,25, w₀ = 30, d₀ = 28 (ε₀ = 2 < σw₀ = 7,5) : ~6 morts/pas pour
  10 naissances/pas dès t = 200 (pop 720) — proche de l'équilibre démographique,
  crédit actif. Repère analytique : μ_base = 1 + 2δ/σ² = 2,6 pour cette
  configuration (§3.3), dans la gamme empirique.
- **[E7c-long]** même configuration, T = 1500, pools par fenêtres
  (`run_m2_final.log`, pools de 15 871 / 17 656 points + instantané final) —
  **le régime cible est atteint sur 3 des 4 critères** :
  * population bornée : N* ≈ 1760 plat de t = 800 à 1500, W_tot plat,
    faillites ≈ λ ;
  * **queue stable** (critère 6.2, là où le [WIP] fait 5,4 → 3,1) :
    α_CSN(capital) = 2,80 / 2,86 / 2,88 sur les fenêtres [500,1000) /
    [1000,1500) / t=1500, à x_min quasi constant (534-566) ;
    NW : 2,70 / 2,79 / 2,84 ; revenu : 4,54 / 4,70 / 4,85 (x_min ≈ 22-24) ;
    LR loi de puissance vs log-normale : +566 à +694, p < 10⁻³ partout.
    Cohérence théorique : exposant de pdf observé 2,8-2,9 contre 3,6 pour le
    GBM pur (1 + μ_base = 3,6) — le canal crédit alourdit la queue comme prévu
    (§3.3 : r̄·c compense δ·h) ;
  * **garde-fou anti-cohorte passé** (critère 6.3) : corr(âge, log w) =
    0,11-0,15 (naïf : 0,75-0,78 ; [WIP] : 0,88-0,95) ; distribution d'âges
    continue (q10/q50/q90 = 37/264/794), sans trou démographique ni
    concentration d'époque ; **queue présente à âge contrôlé avec le même
    exposant** (α = 3,19/2,94 dans [20,100)/[100,400) fenêtre 1 ; 2,86/2,88
    fenêtre 2) — les deux classes sont des états dynamiques, pas des cohortes ;
  * **corps : toujours PAS exponentiel** (critère 6.1 non atteint) : log-normale
    (w, revenu) ou gamma (NW) gagnent l'AIC ; med/mean(NW) = 0,52-0,55 pour une
    cible ~0,69. Mais le corps est désormais peuplé par la dynamique (âges
    mélangés), plus par la pyramide des âges : la question X1 est ouverte dans
    de bonnes conditions — c'est LE chantier restant.

  Conclusion d'ensemble de [E7] : la pile complète M2 (asymétrie nominal/réel +
  coût r+δ + choc commun σ + bilan de naissance tendu dans la fenêtre) réalise
  simultanément bornage endogène, queue de Pareto stable et classes
  renouvelées ; seul le corps exponentiel reste à conquérir (X1).

---

## Annexe B — Correspondances avec les équations des articles

| Objet M2 | Référence |
|---|---|
| Corps `P ∝ e^{−x/T}`, T = M/N | [YR] éq. (7), Sec. II.C ; générateur : échange additif conservatif + plancher (Sec. II.F, symétrie de renversement du temps) |
| Diffusion additive+multiplicative complète | [YR] éq. (23)-(25) : A = A₀+a·x, B = B₀+b·x², croisement x₀ = √(B₀/b), corps exp + queue x^{−1−μ} |
| Équation de richesse multiplicative, queue Pareto | [BM] éq. (2) ; solution moyen-champ éq. (7) : μ = 1 + J/σ² |
| Kesten discret (queue stable) | [BM] éq. (8)-(9) : `(1−Jτ)^μ⟨e^{−μV}⟩ = ⟨e^{−V}⟩^μ` |
| Connectivité finie (analogue de k) | [BM] éq. (16)-(17) : μ ≃ ln(c/σ²τ)/ln(c/Jτ) — dépendance faible en σ, J |
| Condensation μ < 1 (garde : si le crédit s'effondre) | [BM] Fig. 2-3, Y₂ = Σw̃² ; recodage local `recherche/analyse_articles/bouchaud_mezard_wealth_condensation/` (transition J/σ² ≈ 0,1-0,3 reproduite) |
| Deux classes d'agents identiques (précédent) | Wright 2005/2009, cité [YR] Sec. V ; recodages locaux `wright_*/` (partition ≈ 70/12 % reproduite) |
| ODE individuelle | [ODE] : `dx/dt = −δx + b√x + c`, c_crit = −b²/(4δ), cas A-E |
| Choc commun sans drift | η ~ N(−σ²/2, σ²), E[e^η] = 1 — correction du bug du brownien d'α ([WIP] `simulation.py:1320`) |
