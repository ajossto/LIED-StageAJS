# Prompt M4.3Live-v2 — libérer le sens du prêt, et chercher ce qui détermine la rotation du crédit

Destinataire : une instance Claude Opus 5 (Claude Code), à qui ce document est
confié comme spécification de tâche complète et autonome. Ce n'est pas un
brouillon à discuter avant de commencer : les décisions de fond sont prises
ci-dessous ; les points explicitement laissés ouverts (§12) sont à trancher et
documenter toi-même, pas à retourner à l'utilisateur avant d'avoir essayé.

Version : 21 août 2026, révision 1. Lignée : succède à **M4.3Live**
(`m4_3live_credit_soc/`), qui est un programme **terminé et publié** — deux
rapports PDF, 203 runs enregistrés, parité bit à bit avec M4.3 vérifiée sur
8000 pas. Convention de dossier : `m4_3live_v2_credit_soc/`.

**Provenance.** Ce document dérive de
`m4_3live_v2_credit_soc/ROADMAP.md`, écrite à partir de 28 notes manuscrites
portées par l'utilisateur sur `m4_3live_credit_soc/report/rapport_final.pdf`
le 18 août 2026, puis complétée par quatre retours oraux du 21 août. La
feuille de route explique le *pourquoi* de chaque chantier et cite sa note
d'origine ; **ce prompt donne le *quoi* et l'*ordre***. Les deux se lisent
ensemble : en cas de contradiction, ce prompt fait foi, et la contradiction
est à signaler.

---

## 0. Lectures préalables obligatoires, et pièges du dépôt

Avant d'écrire une ligne de code, lire dans cet ordre :

- **`m4_3live_v2_credit_soc/ROADMAP.md`** — la feuille de route dont ce
  prompt est l'exécution. Elle donne, chantier par chantier, la note
  d'utilisateur qui le motive et les conséquences à instrumenter.
- **`m4_3live_credit_soc/m4_3live/model.py`** (~1000 lignes) — le moteur de
  référence. C'est le fichier dont ce prompt cite les numéros de ligne ; si
  le fichier a changé depuis, revérifier les citations, ne pas les croire
  sur parole.
- `m4_3live_credit_soc/m4_3live/kernel.py` — le noyau d'institution (table
  de Hermite d'ordre 4, δ\* = h(C) − K_b). Validé, coût 1,3 % du pas : à
  reprendre tel quel.
- `m4_3live_credit_soc/m4_3live/live.py` — session pilotable, journal
  d'interventions, rejeu, snapshots. Testé, non remis en cause.
- **`m4_3live_credit_soc/report/rapport_final.pdf`** (34 pages) — les
  résultats de v1. Lire au moins §5 (ablation K0), §6 (la tension et ses
  limites) et §7 (les deux groupes de covariance) : v2 en hérite comme
  acquis, et une bonne partie de son programme consiste à les prolonger.
- **`m4_3live_credit_soc/report/conception_m4_3live.pdf`** (27 pages) — les
  décisions d'architecture de v1 et leurs justifications.
- `m4_3live_credit_soc/JOURNAL.md` — le journal de travail de v1, y compris
  les pièges rencontrés et les inférences réfutées en cours de route.
- `simulation_lab/contracts.py`, `simulation_lab/jobs.py`,
  `simulation_lab/web/app.py` — l'orchestration existante, dont v2 étend
  l'usage sans le casser.
- `CLAUDE.md` (racine du dépôt) — règles de travail du dépôt.

### Deux passages de `CLAUDE.md` sont obsolètes et vont t'induire en erreur

1. `CLAUDE.md` désigne `m4b_credit_soc_mini/` comme « moteur actif ».
   **Faux pour ce travail** : le moteur de référence est
   `m4_3live_credit_soc/m4_3live/model.py`.
2. `CLAUDE.md` donne `random.Random(seed)` comme convention RNG. **Faux
   ici** : la lignée M4.3/M4.3Live utilise `numpy.random.default_rng(seed)`
   (`m4_3live/model.py:718`, `Simulation.__init__`). Reproduire cette convention
   dans le fork.

### Règle de confiance à 95 %

Si tu n'es pas certain à 95 % d'un fait sur ce projet, le signaler
explicitement, en distinguant **fait observé** (lu dans le code ou les
données), **inférence** (déduit), **hypothèse** et **incertitude**. Citer
systématiquement `fichier.py:ligne`. Ne jamais inventer un comportement du
moteur non vérifié dans le code. Cette règle a une traduction typographique
obligatoire dans les rapports (§10).

### La règle du fork : `m4_3live/` est en lecture seule, définitivement

Le paquet `m4_3live_credit_soc/m4_3live/` **ne doit pas être modifié**, ni
maintenant ni plus tard. Ce n'est pas une précaution de style : c'est le
moteur qui a produit 203 runs enregistrés et deux rapports publiés, et toute
modification invaliderait rétroactivement des résultats cités. L'utilisateur
a énoncé cette contrainte explicitement, en majuscules, pendant le travail de
v1.

v2 **forke** ce paquet dans son propre dossier
(`m4_3live_v2_credit_soc/m4_3live_v2/`, nom à confirmer §12), par copie, pas
par import. Le fork peut ensuite être modifié librement. Toute mesure
nouvelle qu'on voudrait faire sur v1 doit rester un dérivé des séries déjà
écrites (voir `m4_3live_credit_soc/scripts/tension.py`, qui reconstruit la
tension a posteriori sans toucher au moteur).

### Un trou connu dans la feuille de route

**`ROADMAP.md` §9 est un emplacement vide**, réservé aux annotations que
l'utilisateur a portées sur `conception_m4_3live.pdf` et que la visionneuse
n'a pas enregistrées (0 objet `/Subtype/Text` sur le fichier, vérifié par
`pdftk dump_data_annots` et par `mutool show … grep`). **N'invente rien pour
cette section.** Si l'utilisateur fournit une copie annotée en cours de
travail, l'intégrer ; sinon, laisser le trou et le signaler dans le rapport
de conception.

### Citer les sections, jamais les numéros de figure

Quand tu renvoies au rapport v1, cite **§4**, **§6.3**, **§7.1** — jamais
« figure 12 ». Les numéros de figure ont déjà bougé une fois (l'insertion
d'une section en §6 a décalé toutes les figures à partir de la quinzième) et
rebougeront. Les numéros de section utilisés dans ce prompt ont été vérifiés
sur le PDF construit le 21 août 2026 :

| § | Contenu |
|---|---|
| 1 | Le modèle et les notations |
| 2 | Ce qui est mesuré |
| 3 | Protocole (3.1 fenêtre/graines, 3.2 bras, 3.3 appariement, 3.4 validation) |
| 4 | Résultats de la campagne |
| 5 | Ablation sur le capital de naissance K0 |
| 6 | La tension (6.1 définition, 6.2 niveaux, 6.3 mortalité, 6.4 le test qui échoue, 6.5 exposant dlnT/dlnA) |
| 7 | La loi d'échelle (7.1 covariance d'échelle, 7.2 trois γ, 7.3 covariance de pas de temps) |
| 8 | Verdict — 9 Limites — 10 Reproduire |

---

## 1. Le mandat, en une phrase

v2 porte **un changement de modèle** et **une question théorique**. Ils ne
sont pas de même rang :

> **Le changement de modèle est le livrable primaire ; la question théorique
> est le programme scientifique qu'il rend possible.**

Concrètement : si le budget se resserre, livrer le §3.1 (sens du prêt libéré)
mesuré proprement, avec son rapport, plutôt qu'un demi-chantier de modèle et
une demi-réponse théorique. Ne pas confondre les deux dans un même verdict.

**Le changement de modèle** (§3.1) supprime la règle « dans chaque paire, la
plus riche prête ». Son intérêt n'est pas cosmétique : il ouvre un régime que
v1 **ne pouvait pas produire** — une entité riche à mauvaise technologie qui
cède son capital à une entité pauvre à meilleur rendement marginal et vit de
l'intérêt. C'est ce régime qu'il faut caractériser.

**La question théorique** (§5) : *quelle combinaison de (A, γ, δ, K0, λ, ρ)
détermine la rotation du crédit `loan_volume/K_tot` à l'état stationnaire ?*
v1 a montré que cette rotation prédit la mortalité à 0,4 % près quel que soit
le levier employé (R² = 0,998 sur quatre leviers indépendants), là où la
« tension » échoue. Savoir la prédire donnerait la chaîne
rotation → mortalité → population → production.

---

## 2. Ce que v1 a établi : acquis à reprendre, pas à refaire

Ces résultats sont **publiés et vérifiés**. Les citer, ne pas les
reproduire.

| Acquis | Où | Valeur |
|---|---|---|
| Parité bit à bit avec M4.3, 8000 pas × 26 colonnes | `tests/test_parity_m4_3.py --full` | écart maximal **nul**, 9 366 225 appels au noyau, 1077 s |
| Noyau d'institution (δ\* = h(C) − K_b, Hermite ordre 4) | `m4_3live/kernel.py` | validé, 1,3 % du coût d'un pas |
| Verdict rebond | rapport §4, §8 | portée partielle court horizon : rebond, ε ≈ 2,3–2,9 ; portée globale à K0 fixe : effet **inverse**, ε = 0,76 ; K0 compensé : ε = 2,02 |
| Le signe du verdict global dépend entièrement de K0 | rapport §5 | à K0 fixe, A×1,5 **contracte** la population de 25 % ; compenser K0 par A^{1/(1−γ)} annule tout |
| Covariance d'échelle démontrée | rapport §7.1 | A→A′, K0→cK0 avec c = (A′/A)^{1/(1−γ)} donne la **même simulation** à l'échelle c ; écart 5·10⁻¹⁵, population rigoureusement identique |
| Covariance de pas de temps | rapport §7.3 | λ→sλ, δ→1−(1−δ)^s, σ→σ√s, **A→sA, ρ→sρ** ; résidu 6–17 % dû à la phase de marché, pas à la discrétisation |
| La tension T = K_aut/K_eq n'est **pas** un paramètre d'état | rapport §6.4 | excellente à δ fixé (R² = 0,989 sur ×15) ; mise en échec par δ (facteur 8 sur δ → facteur 13 sur T, 14 % sur la mortalité) |
| La rotation du crédit aligne les quatre leviers | rapport §6.4 | `morts/pop ∝ (loan_volume/K_tot)^1,337`, R² = 0,9982, biais par levier entre −1,7 % et +0,7 % |
| L'exposant dlnT/dlnA | rapport §6.5 | 0,776 / 1,145 / 1,673 pour γ = 0,4/0,5/0,6 ; = 0 sous compensation de K0 |
| 203 runs consultables | `simulation_lab`, lignée `m4_3live_credit_soc` | annexe de traçabilité à 207 lignes, 0 sans rôle |

**Définitions employées ci-dessus, à reprendre telles quelles** (rapport
§6.1) :

- **Échelle autarcique** `K_aut = [A(1−δ)/δ]^{1/(1−γ)}` : le point fixe de
  `(K + AK^γ)(1−δ) = K`, c'est-à-dire le capital qu'atteindrait une entité
  seule, sans crédit ni faillite.
- **Capital équivalent** `K_eq = (prod/(n·A))^{1/γ}` : le capital qui
  reproduirait la production observée si toutes les entités vivantes étaient
  identiques.
- **Tension** `T = K_aut / K_eq` : de combien le système tourne en dessous de
  son échelle autarcique. Vaut ≈ 13,3 au régime de référence.
- **Rotation du crédit** `loan_volume / K_tot` : le principal transféré au
  pas, rapporté au stock de capital. Variable **endogène** — c'est une
  régularité descriptive, pas une loi de contrôle, et v2 doit le rappeler
  chaque fois qu'il l'emploie.

---

## 3. Les quatre changements de modèle

### 3.1 Le sens du prêt cesse d'être imposé — **le chantier principal**

**État v1.** Dans chaque paire tirée, la plus riche est prêteuse et la plus
pauvre emprunteuse (`m4_3live/model.py:515-520`). Quand l'optimum de
production jointe voudrait faire circuler le capital du pauvre vers le riche
(δ\* ≤ 0), la paire est **refusée** et comptée dans `mkt_blocked_dir`
(`model.py:525-530`). Ce compteur se stabilise autour de 25 % des rondes.

**Ce que l'utilisateur en dit** (notes [4] et [6]) : « *C'est dommage. Si
l'optimisation convexe donne un sens, alors c'est celui-ci qui devrait être
utilisé. Cette règle n'a pas de sens.* » et « *Abandon de la nomenclature
K_ℓ K_b pour lender/borrower, passage à K_a, K_b.* »

**Changement.** La paire devient non ordonnée `(a, b)`, de capitaux
`K_a, K_b`, de capital joint `C = K_a + K_b`. Le noyau retourne l'allocation
optimale `K_a* = h(C)` ; le transfert est `δ = K_a* − K_a`, **de signe
libre**. Le prêt va de qui cède vers qui reçoit ; le receveur est le débiteur.

**Nomenclature.** Renommer partout `lender`/`borrower` en `a`/`b`. Ce n'est
pas cosmétique : tant que le code dit « prêteuse », un lecteur suppose la
règle de richesse, et une régression s'y cachera.

**Conséquences à instrumenter, pas à supposer.**

- `mkt_blocked_dir` tombe à zéro par construction. **Garder le compteur** et
  l'alimenter avec ce qu'il aurait valu sous l'ancienne règle — un
  **compteur contrefactuel**. Il mesure directement combien d'échanges v1
  s'interdisait, et c'est une des mesures les plus parlantes du chantier.
- Le volume de prêt augmente mécaniquement. Toute comparaison v1/v2 sur
  `loan_volume` doit se faire à protocole apparié, jamais en absolu.
- Le régime nouveau (riche à mauvaise technologie qui devient créancière)
  demande ses propres diagnostics : **part du capital détenue par les
  créancières nettes**, et **corrélation entre technologie et position
  nette**. Les ajouter aux séries.
- Le taux d'intérêt (`pair_rate`, moyenne géométrique des rendements
  marginaux γAK^{γ−1} de chaque côté) a-t-il encore le même sens quand la
  créancière est la plus fragile des deux ? Question ouverte (§12), à
  trancher et documenter.

**Parité : hypothèse à retester, pas acquise.** En régime homogène,
l'optimum est le partage égal, donc `δ = (K_b − K_a)/2` : magnitude et sens
coïncident avec l'ancienne règle. La parité bit à bit *devrait* survivre.
C'est une **hypothèse** : l'ordre de sommation et l'ordre d'insertion dans le
carnet dépendent de l'ordre du couple, et c'est exactement le genre de détail
qui décale un flottant. `test_parity_m4_3.py --full` est le premier test à
repasser, et **un écart doit être expliqué ligne à ligne, pas absorbé dans
une tolérance**.

### 3.2 Ordre des phases : dépréciation avant service des intérêts, en option

**État v1.** Ordre du pas : naissances → choc → production → **service des
intérêts** → **dépréciation** → marché → faillites
(`m4_3live/model.py:864-934`).

**Note [3]** : « *Test à faire, échanger 5 et 6, ça devrait faire augmenter
le taux de défaut.* »

**Changement.** Un champ de configuration
`phase_order ∈ {"v1", "deprec_first"}`, valeur par défaut `"v1"` — la parité
doit rester atteignable sans détour. Sous `"deprec_first"` : dépréciation
puis service.

**Prédiction à falsifier, à écrire avant de lancer.** Le capital disponible
au moment de payer est réduit d'un facteur (1−δ) ; toute emprunteuse dont le
capital était compris entre `dû` et `dû/(1−δ)` bascule en défaut de
liquidité. À δ = 0,01 c'est une fenêtre étroite : l'effet attendu est **petit
et calculable a priori** à partir de la distribution du ratio capital/dû,
qu'il faut donc enregistrer avant de mesurer. Test A/B apparié par graine.

### 3.3 Aucun traitement du cas partiel — **périmètre retiré**

Consigne explicite de l'utilisateur, 21 août 2026 : « *Pour la v2, on se
souvient, je ne veux aucun traitement du cas partiel.* »

**Ce qui sort du périmètre** : la portée `fraction` et toute campagne qui
l'emploie ; les bras `null` appariés qui lui servaient de référence ;
l'inversion part ex post → part ex ante ; la question « le long horizon
est-il tranchable ? » posée en portée partielle. **v2 mesure en portée
globale**, où l'intensité de traitement vaut 1 par construction et ne dérive
pas.

**Ce qui ne sort pas** : les résultats v1 obtenus en portée partielle restent
acquis et publiés ; ils ne sont simplement pas prolongés. La portée `new`
(les naissances postérieures à t₀ reçoivent la nouvelle technologie) reste
disponible et n'est pas concernée : ce n'est pas un traitement partiel de la
population vivante.

### 3.4 Purger les clefs mortes du carnet — **exigence, pas option**

Consigne explicite de l'utilisateur, 21 août 2026 : « *Il est essentiel de
purger les clefs mortes. Le run est en λT² en ce moment.* »

**Le diagnostic.** `LoanBook.by_borrower` est un
`defaultdict[int, set[int]]` (`m4_3live/model.py:307`), et `remove()`
retire un prêt par `.discard()` (`model.py:349`) : **la clef reste**, avec un
ensemble vide. Une entité qui meurt voit tous ses prêts retirés
(`_fail_one`, `model.py:608-616`) et laisse donc derrière elle une entrée
vide, définitive. La phase de service des intérêts itère sur **toutes** les
clefs — `for borrower in list(book.by_borrower.keys())`
(`model.py:901`) — et fait `continue` sur les vides (`model.py:903-904`).

**Le coût, correctement énoncé.** Le nombre de clefs croît comme le nombre
d'entités jamais créées, soit ≈ λ·t. Le coût *par pas* de la phase d'intérêts
est donc en λ·t, et le coût **total d'un run** est la somme de λ·t sur les T
pas, soit **λT²/2 : quadratique en T**. Mesuré en v1 : +20 % de coût par
pas entre t = 210 et t = 1810, à prêts actifs et population constants, avec
98 % des clefs vides. À T = 4000 et λ = 30, le carnet porte ≈ 120 000 clefs
pour ≈ 1130 entités vivantes. C'est le plafond qui empêche aujourd'hui les
horizons longs.

**Ce qu'il faut faire.** Supprimer l'entrée de `by_borrower`, `by_lender`,
`due`, `claims` et `debts` d'une entité **au moment de sa mort**, dans
`_fail_one`, après le retrait de ses prêts. Reconstruire les listes de clefs
une fois par pas devient alors proportionnel à la population vivante, et le
run redevient linéaire en T.

**Et la parité tient — c'est vérifiable, pas à parier.** Une note de v1
affirmait que purger « changerait l'ordre de sommation et ferait perdre la
parité ». **Cette inférence est fausse** pour le cas qui nous occupe, pour
trois raisons qui doivent toutes être vraies :

1. le corps de boucle est un **no-op** pour un ensemble vide — le `continue`
   précède la lecture de `book.due[borrower]` (`model.py:903-905`), donc
   aucune opération flottante n'a lieu ;
2. supprimer une clef d'un `dict` CPython **ne réordonne pas** les clefs
   restantes ; la séquence des emprunteuses non vides est identique ;
3. une entité morte est tuée (`population.kill`) et **ne peut plus jamais
   emprunter**, donc sa clef ne sera pas réinsérée.

**Le piège à ne pas commettre** : purger les clefs vides des entités
**vivantes** (celles dont tous les prêts se sont simplement clos) **casserait**
la parité — un `defaultdict` réinsère la clef en **fin** d'ordre au prochain
emprunt, ce qui change la séquence d'itération et donc l'ordre de sommation.
Ne purger qu'à la mort.

**Porte de sortie** : parité bit à bit reconduite (lot A), et courbe de coût
par pas mesurée avant/après sur un run de 4000 pas, pour montrer que la pente
s'aplatit.

### 3.5 Une seule borne de transfert : `optimum`

Consigne explicite de l'utilisateur, 21 août 2026 : « *Je ne veux plus que
`transfer_cap="optimum"`.* »

La valeur `equalization` (plafond du transfert à (K_ℓ − K_b)/2) est retirée.
À supprimer, avec les références v1 :

| À supprimer | Où (v1) |
|---|---|
| tuple `TRANSFER_CAPS` et sa validation | `m4_3live/model.py:69, 167-168` |
| champ `transfer_cap` de `Config` | `m4_3live/model.py:144` |
| `cap_at_equalization` et la branche de plafonnement | `m4_3live/model.py:506, 531-536` |
| compteur `mkt_capped` (devient mort) | `_run_market`, colonne de `series.csv` |
| option `--transfer-cap` du CLI | `driver/headless.py:214` |
| champ exposé par l'API locale | `web/router.py:55` |
| pilote de plafond et sa figure `cap_pilot.png` | `scripts/campaign.py:166`, `scripts/conception_evidence.py:309, 348, 723` |
| contrôle d'intégrité « transfer_cap inattendu » | `scripts/analyse.py:249-256` |

**C'est du code mort, et c'est prouvé** : `mkt_capped` cumulé vaut
**exactement 0 sur les 203 runs** du dépôt. La suppression ne peut donc
changer aucun nombre, et **la parité doit être reconduite telle quelle**.
C'est ce qui la distingue du §3.1. À faire dans le lot A, avant tout
changement de comportement, pour que la parité qui suit porte sur un moteur
déjà simplifié.

Le pilote de plafond du 16 août reste publié dans le rapport de conception de
v1 : il documente *pourquoi* le plafond est sans objet (les entités dopées
deviennent en quelques dizaines de pas le côté riche de presque toutes leurs
paires, l'optimum voudrait alors leur envoyer du capital, et l'ancienne règle
de sens l'interdisait). Ce résultat justifie la suppression ; il ne disparaît
pas avec elle. **Noter la boucle** : c'est précisément le §3.1 qui rend ce
raisonnement caduc, puisque le sens n'est plus interdit. Si le plafond
redevenait pertinent sous sens libre, le dire dans le rapport de conception
plutôt que de le réintroduire en silence.

---

## 4. Instrumentation à ajouter au moteur forké

### 4.1 Tension native, et l'effectif producteur exact

**Note [17], la demande la plus explicite de l'utilisateur** — « TRÈS
IMPORTANT ». v1 l'a satisfaite *a posteriori*, par un dérivé des séries
(`m4_3live_credit_soc/scripts/tension.py`), parce que le moteur était gelé.
v2 n'a pas cette contrainte : **la tension doit être une colonne native**.

Ce qui manque dans v1 et qu'il faut enregistrer : par technologie et par pas,
`n_prod` (l'effectif qui a **produit** au pas) et `K_prod` (le capital au
moment de produire). Aujourd'hui `tech_series` donne l'effectif de *fin* de
pas, alors que la production a été calculée **avant** les morts du pas ;
`scripts/tension.py` reconstruit l'effectif producteur par `n + deaths`, ce
qui est exact tant qu'une seule technologie vit et approché sinon (imputation
au prorata). La colonne `basis` de `tension_agg.csv` documente laquelle des
reconstructions a servi — cette colonne doit disparaître en v2, parce que la
mesure devient exacte.

Sorties attendues, pour **chaque** run et sans intervention manuelle :
`tension.csv` (par pas), `tension_agg.csv` (agrégé) et une figure de
tension dans `figures/`. Reprendre la structure de
`m4_3live_credit_soc/scripts/tension_figures.py`, qui est branchée dans
`driver/headless.py:write_outputs()`.

### 4.2 Amplitude exacte, enregistrée et non reconstruite

**Note [16].** Après le pas d'intervention, `population.prod[i] = A′·K_i^{γ′}`
est en mémoire, donc `K_i = (prod_i/A′)^{1/γ′}` exactement (aller-retour
flottant propre), d'où la production contrefactuelle `A·K_i^γ` et donc
l'amplitude `m` et la part traitée `p` **sans aucune inversion**. v1 l'a fait
en post-traitement (`scripts/exact_amplitude.py`) ; v2 doit l'enregistrer au
moment de l'intervention.

Ce que ça a rapporté en v1, à reproduire comme contrôle : m = 1,500000 /
1,250000 / 1,946184 (le troisième est un levier sur γ, dont l'amplitude vaut
`K^Δγ` et **doit être mesurée**, pas imposée) ; et `E(h=1) = 1` à 1,0·10⁻¹⁵.

### 4.3 Prédiction naïve du levier γ

**Note [17].** Pour tout levier sur γ, enregistrer côte à côte l'amplitude
mesurée et la prédiction naïve qu'on aurait faite en supposant K = 1
(c'est-à-dire amplitude = 1). L'écart est le contenu informatif : en v1 il
valait 1,946 contre 1,000. C'est ce qui montre qu'un levier sur γ n'est pas
un cadran de puissance.

### 4.4 Diagnostics du régime nouveau (§3.1)

- `mkt_blocked_dir` **contrefactuel** (ce qu'il aurait valu sous l'ancienne
  règle) ;
- part du capital total détenue par les entités en **position nette
  créancière** ;
- corrélation entre le rendement marginal d'une entité et sa position nette.

### 4.5 Statistique : ce que « x σ » veut dire

**Note [19].** Avec n graines, les écarts rapportés sont des **Student à
n−1 degrés de liberté**, pas des normales. À 5 graines : seuil 5 % à **2,776**
et non 1,96 ; seuil 1 % à **4,604** et non 2,58. v1 a vérifié qu'aucun verdict
ne basculait, mais une marge était mince (p = 3,3 %).

**Recommandation** : passer à **12 graines** pour la campagne de verdict, ce
qui ramène le seuil à 2,201 et divise l'erreur-type par 1,55. Coût : ×2,4 sur
la campagne. À confirmer contre le budget (§12).

---

## 5. La question théorique : qu'est-ce qui détermine la rotation du crédit ?

C'est le programme scientifique de v2, et il est ouvert.

**Ce que v1 a établi.** Sur 109 runs couvrant quatre leviers indépendants
(K0 seul, δ seul, A seul, A et K0 ensemble),
`morts/population/pas ∝ (loan_volume/K_tot)^1,337` avec R² = 0,9982, écart
médian 0,41 %, et un biais par levier compris entre −1,7 % et +0,7 %. Aucune
autre variable testée n'aligne les quatre leviers — la tension échoue sur δ.

**Ce qui manque.** La rotation est **endogène** : on la mesure, on ne la
choisit pas. Tant qu'on ne sait pas la prédire à partir des paramètres, on a
une régularité descriptive et non une loi.

**Piste, non imposée.** La rotation est le produit de trois facteurs : le
nombre de paires tirées par pas `η(N) = ρN` (`model.py:497`), la probabilité
qu'une paire traite, et le transfert moyen rapporté au capital. Les deux
premiers sont combinatoires et se calculent ; le troisième est
`E|δ*|/K̄`, dont l'institution donne la forme exacte. Une prédiction
analytique est donc plausible. **Le §3.1 change les deux derniers facteurs** :
plus aucune paire n'est refusée pour cause de sens, donc la probabilité de
traiter monte et le transfert moyen change de distribution. C'est une raison
de plus de faire le §3.1 d'abord.

Les 203 runs de v1 suffisent pour commencer l'analyse sans lancer un seul
calcul neuf.

---

## 6. Les deux groupes de covariance : à énoncer ensemble

v1 les a démontrés séparément. **v2 doit les présenter comme un seul
résultat** dans son rapport de conception : ce sont deux groupes de symétrie
qui réduisent le nombre de paramètres réellement libres du modèle.

**Covariance d'échelle (capital)** — rapport v1 §7.1. Avec `A → A′` et
`K0 → cK0`, `c = (A′/A)^{1/(1−γ)}`, on obtient la **même simulation à
l'échelle c près** : chaque phase du pas est homogène de degré 1 en capital,
et le taux marginal `γAK^{γ−1}` est **sans dimension**, donc invariant.
Vérifié à 5·10⁻¹⁵, population rigoureusement identique. Ce qui casse
l'exactitude : trois constantes dimensionnées non rééchelonnées (`MIN_LOAN`,
`ZERO_TOL`, le plafond de transfert — ce dernier disparaissant avec le §3.5).

**Covariance de pas de temps** — rapport v1 §7.3. Avec un pas de recalage `s`
(le nombre de pas anciens comprimés en un) :
`λ→sλ`, `δ→1−(1−δ)^s`, `σ→σ√s`, **`A→sA`**, **`ρ→sρ`**. Les trois premières
substitutions composent **exactement** (identité algébrique ; somme de deux
log-normales dérive comprise ; somme de deux Poisson). Les deux dernières
sont les **flux par pas**, que l'énoncé initial oubliait.

**Classification à porter dans le `model_summary` de v2** :

| Grandeurs **par pas** (se recalent avec l'unité de temps) | Grandeurs **de forme** (n'en dépendent pas) |
|---|---|
| δ, σ, λ, A, ρ | γ, K0, règle de transfert, règle de taux |

Cette colonne évite de discuter un « effet de δ » qui n'est qu'un changement
d'unité de temps.

**Une limite mesurée, à ne pas réouvrir naïvement.** Le résidu du recalage
(6 à 17 %) ne vient **pas** de la discrétisation en δ — c'était l'hypothèse
de départ, elle a été **réfutée**. Le test à `s = 4` ne tranche pas (les deux
termes croissent en s−1) ; celui à `δ = 0,002` tranche : le terme de K_aut
est divisé par 5 et le résidu ne bouge pas. La source est la **phase de
marché, qui ne se compose pas** — deux rondes de ρN appariements ne valent
pas une ronde de 2ρN, la seconde voyant l'état laissé par la première. C'est
ce qui distingue ce modèle d'une équation différentielle, et c'est la vraie
question ouverte : *que font s rondes successives qu'une ronde s fois plus
grosse ne fait pas ?*

---

## 7. Protocole expérimental

**Reprendre le protocole v1 tel quel** (rapport §3), sauf sur les points
ci-dessous. Il est éprouvé : amorçage partagé de 2000 pas, snapshots à
t₀ = 2000, bras branchés sur les mêmes snapshots, appariement par graine,
fenêtre d'observation sur les 1000 ou 2000 derniers pas.

**Modifications pour v2** :

1. **Portée globale uniquement** (§3.3). Plus de bras `frac_*`, plus de bras
   `null`. Le contrôle apparié redevient un simple bras inerte.
2. **12 graines** pour la campagne de verdict (§4.5), à confirmer.
3. **Comparaison v1/v2 appariée.** Le chantier du §3.1 exige une campagne
   A/B où le *seul* changement est la règle de sens : mêmes graines, mêmes
   snapshots d'amorçage, même protocole. Attention : le fork v2 doit pouvoir
   **rejouer l'ancienne règle** (drapeau de configuration, `loan_direction ∈
   {"richest_lends", "free"}`), sinon la comparaison n'est pas appariée mais
   inter-lignée.
4. **Contrôle de stationnarité obligatoire** avant de lire un niveau :
   rapport de la moyenne du dernier quart à celle du quart précédent, sur
   `K_tot`, `pop` et `prod_tot`. v1 accepte 0,993 à 1,003. Un bras qui
   n'est pas stationnaire donne un transitoire, pas un niveau — le dire.

---

## 8. Séquencement en lots

Chaque lot a une **porte de sortie** : tant qu'elle n'est pas franchie, le
lot suivant ne commence pas. Les lots qui changent le modèle doivent être
**séparés dans l'historique git** et chacun accompagné de sa campagne
appariée. Ne jamais les empiler avant mesure — c'est la seule manière de
garder un verdict attribuable.

| Lot | Contenu | Porte de sortie | Coût estimé |
|---|---|---|---|
| **A** | Fork du dossier ; **§3.4** purge des clefs mortes ; **§3.5** suppression de `equalization` ; parité sur le fork nu | `test_parity_m4_3.py --full` : **écart nul exigé** — les deux changements sont neutres sur le calcul (§3.4, §3.5). **Et** courbe de coût par pas mesurée avant/après sur 4000 pas : la pente doit s'aplatir | 3 h + 2200 s de calcul |
| **B** | **§3.1** sens du prêt libre, nomenclature `K_a`/`K_b`, compteur contrefactuel, diagnostics §4.4 | parité reconduite **ou** écart expliqué ligne à ligne — pas de tolérance de confort | 1 j |
| **C** | **§4.1–4.3** tension native, amplitude exacte, prédiction naïve γ | tests unitaires sur données synthétiques dont on connaît la réponse | 0,5 j |
| **D** | Campagne A/B appariée du §3.1 : ancienne règle vs sens libre, 12 graines | verdict sur le régime nouveau, avec sa statistique de Student | 2 h de calcul |
| **E** | **§3.2** `phase_order`, campagne A/B appariée | taux de défaut mesuré **contre la prédiction écrite a priori** | 0,5 j + 2 h de calcul |
| **F** | **§5** analyse de la rotation du crédit sur les runs existants + ceux du lot D | soit une prédiction analytique testée, soit un constat d'échec documenté avec ce qui a été essayé | 1 j |
| **G** | **§6** énoncé unifié des deux covariances dans le rapport de conception | les deux groupes présentés ensemble, avec la classification par pas / de forme | 0,5 j |
| **H** | Rapports (§10), journal, traçabilité, import `simulation_lab` | relecture annotée par l'utilisateur | 1,5 j |

*(Il n'y a pas de lot « portée persistante » : le cas partiel est hors
périmètre, §3.3.)*

---

## 9. Tests exigés

Assertions Python simples, convention du dépôt (**pas de pytest**).
Reprendre la suite de v1 (`m4_3live_credit_soc/tests/`) et l'étendre.

### Trois sémantiques de parité, à ne pas confondre

C'est le point le plus facile à saboter par inattention.

- **Lot A — parité obligatoire et bit-exacte.** Supprimer `equalization`
  retire du code qui n'a jamais été exécuté (`mkt_capped` = 0 partout).
  Toute déviation est un bug de la suppression, pas un effet du changement.
  Commande : `python3 tests/test_parity_m4_3.py --full` — 8000 pas,
  26 colonnes, ~1100 s, référence `m4_3__d1__baseline__seed0`.
- **Lot B — parité à retester, pas à supposer.** Le sens libre coïncide avec
  l'ancienne règle en régime homogène, mais l'ordre du couple change l'ordre
  de sommation et d'insertion dans le carnet. Si la parité tombe, **expliquer
  l'écart ligne à ligne** ; ne pas l'absorber dans une tolérance.
- **Lot E — parité conditionnelle.** Le défaut `phase_order = "v1"` doit la
  préserver ; la branche `"deprec_first"` ne la préserve pas, par
  construction, et c'est le but.

### Autres tests

- **Institution** : le régime homogène applique littéralement
  (K_b − K_a)/2 ; les régimes hétérogènes vérifiés contre la formule fermée
  et contre une résolution de Newton.
- **Sens du prêt** (nouveau) : sur une paire construite à la main où
  l'optimum exige que la pauvre cède, vérifier que le prêt part bien dans ce
  sens, que le carnet enregistre la bonne débitrice, et que le compteur
  contrefactuel s'incrémente.
- **Rejeu/déterminisme** : un journal issu d'une **session en direct
  réelle** (interventions soumises de façon asynchrone), rejoué en mode
  headless, reproduit une trajectoire strictement identique, même `t`
  effectif compris.
- **Invariant de pause** : N pas avec pauses = N pas sans pause.
- **Portées** : `all` change bien toutes les entités vivantes au pas
  suivant ; `new` ne change rien aux entités déjà nées.
- **Tension** (nouveau) : sur un état synthétique à une seule technologie
  dont on connaît `n`, `K` et `A`, vérifier que `K_eq` et `T` valent
  exactement la formule.
- **Covariance de pas de temps** (§12, question ouverte) : candidat naturel
  pour un test de non-régression — mais son résidu est de 6 à 17 %, donc le
  seuil devrait être calibré sur le résidu mesuré, pas sur zéro.

---

## 10. Livrables et conventions de rédaction

L'utilisateur a explicitement demandé que v2 reproduise la manière de v1 :
**un rapport scientifique, illustré, détaillé et autonome ; un rapport de
conception ; un journal de travail.** Ce qui suit n'est donc pas indicatif.

### Livrables

- **Code complet et fonctionnel** dans `m4_3live_v2_credit_soc/` — un système
  qui tourne réellement, pas un squelette. Démarrer le serveur, piloter une
  session en direct dans un vrai navigateur, vérifier visuellement les
  graphiques et le panneau de contrôle avant de déclarer la tâche terminée.
- **Rapport de conception**, LaTeX compilé en PDF
  (`report/conception_m4_3live_v2.pdf`) : toutes les décisions
  d'architecture justifiées avec citations `fichier.py:ligne` — en
  particulier le sens libre et sa nomenclature (§3.1), le statut de la parité
  après chaque lot, la purge des clefs mortes (§3.4) et la suppression de
  `equalization` (§3.5), l'instrumentation
  native (§4), l'énoncé unifié des deux covariances (§6), et les décisions
  laissées ouvertes (§12) avec la façon dont tu les as tranchées.
- **Rapport de résultats**, LaTeX compilé en PDF
  (`report/rapport_final.pdf`) : protocole, résultats, figures, verdict,
  limites. Même discipline que
  `m4_3live_credit_soc/report/rapport_final.tex`, qui est le modèle à imiter.
- **Compilation PDF vérifiée** — le `.tex` seul ne suffit pas. Trois passes
  `pdflatex` après suppression des `.aux`/`.toc`, aucun `!` dans le log,
  aucune référence non définie.
- **`README.md`** et **`JOURNAL.md`** dans `m4_3live_v2_credit_soc/`. Le
  journal est tenu **au fil de l'eau**, pas reconstitué à la fin : chaque
  session y consigne ses chiffres clés, ses décisions, et les inférences
  qu'elle a dû retirer.

### Conventions de rédaction — règles permanentes du dépôt

**Autonomie.** Un rapport doit être compréhensible par un lecteur tiers
compétent dans le domaine général, **sans accès aux données, au code, ni aux
conversations qui l'ont précédé**.

- Toute variable, tout paramètre, toute notation est **défini explicitement
  à sa première apparition** — même si la définition semble évidente dans le
  contexte de travail. Jamais de notation avant sa définition.
- Tout terme technique non standard est expliqué dans le corps du texte.
- Toute méthode d'analyse est décrite avec assez de détail pour qu'un lecteur
  puisse la réimplémenter ou en évaluer la validité ; les hypothèses
  implicites sont rendues explicites.
- Toute valeur numérique et toute figure a une **source identifiable** dans
  le texte (section, tableau, fichier de données). Les chiffres ne tombent
  pas du ciel.
- Une conclusion est **proportionnée aux données** : distinguer ce qui est
  robuste (confirmé sur plusieurs graines, paramètres, horizons) de ce qui
  est fragile ou exploratoire.

**Marquage typographique obligatoire.** v1 emploie trois macros LaTeX qui
rendent la règle des 95 % visible à la lecture : `\fait{}` (fait observé),
`\inference{}` (inférence), `\incertitude{}` (incertitude ou réserve). Elles
s'affichent en clair dans le PDF. **Les reprendre.** C'est une grande part de
ce que l'utilisateur entend par « rapport scientifique » : on doit pouvoir
lire un paragraphe et savoir immédiatement s'il rapporte une mesure ou une
interprétation.

**Cinq règles tirées des annotations de l'utilisateur sur le rapport v1** :

1. **Tout tableau de plus de quatre colonnes est d'abord une figure.** Si
   l'information est comparative, elle se voit ; le tableau vient après, pour
   les chiffres exacts.
2. **Aucune notation avant sa définition**, sans exception.
3. **Un calcul cité est un calcul déroulé.** Ne pas écrire « soit ×1,80 » :
   écrire l'opération.
4. **Un paragraphe qu'on ne peut pas paraphraser est à réécrire, pas à
   défendre.**
5. **Jamais de « meilleure technologie ».** L'ordre des rendements marginaux
   dépend du capital : il n'existe pas de technologie meilleure dans
   l'absolu. Écrire « plus grand rendement marginal à ce capital ».

**Traçabilité par hash — règle permanente.** Toute simulation mentionnée dans
un rapport (figure, tableau ou texte) doit être identifiable par son `run_id`.
Chaque rapport se termine par une **annexe de traçabilité** donnant, pour
chaque run : `run_id`, l'endroit où il apparaît, son rôle, ses paramètres
principaux, sa graine, son statut, son chemin `simulation_lab`. v1 génère
cette annexe par script (`scripts/make_traceability.py`) et vérifie qu'aucune
ligne n'est sans rôle — reprendre le mécanisme. **Dans cette annexe, renvoyer
aux sections, pas aux numéros de figure** : v1 s'est fait piéger, ses renvois
dataient d'une version où le rapport avait deux figures de moins.

**Travail scientifique — règles permanentes.**

- **Données** : toute donnée qui a informé une décision est sauvegardée dans
  un fichier accessible (JSON ou CSV, sous `results/`), pas seulement dans un
  `print` ou un log.
- **Raisonnement** : toute inférence non triviale est explicitée avec les
  chiffres qui la justifient. Une conclusion sans source chiffrée est
  invalide.
- **Reproductibilité** : tout calcul, toute analyse, toute figure est
  accompagné du script qui permet de le reproduire. Un résultat non
  reproductible est un résultat non publié. Le rapport se termine par une
  section « Reproduire » listant les commandes dans l'ordre, avec leur coût
  mesuré.
- **Journal** : consigné immédiatement, avec les chiffres clés.

---

## 11. Arborescence attendue

```
m4_3live_v2_credit_soc/
+-- ROADMAP.md                       (feuille de route, deja presente)
+-- notes/                           (28 notes extraites du PDF v1, deja presentes)
+-- prompts/PROMPT_M4_3LIVE_V2.md    (ce document)
+-- m4_3live_v2/                     (paquet moteur FORKE, S0 -- nom a confirmer S12)
|   +-- model.py                     (sens libre S3.1, phase_order S3.2, instrumentation S4)
|   +-- kernel.py                    (repris tel quel de v1)
|   +-- live.py                      (session, boucle, journal)
+-- driver/                          (pilote headless)
+-- web/                             (IHM, ou extension de simulation_lab/live/)
+-- tests/
|   +-- test_parity_m4_3.py          (S9, trois semantiques)
|   +-- test_institution.py
|   +-- test_loan_direction.py       (S9, NOUVEAU)
|   +-- test_replay.py
|   +-- test_scopes.py
|   +-- test_tension.py              (S9, NOUVEAU)
+-- scripts/                         (campagnes et analyses)
+-- results/                         (runs, snapshots, analysis/)
+-- report/
|   +-- conception_m4_3live_v2.tex/.pdf
|   +-- rapport_final.tex/.pdf
|   +-- figures/
|   +-- tables/
+-- README.md
+-- JOURNAL.md
```

---

## 12. Décisions laissées ouvertes, à trancher et documenter toi-même

1. **Nom du paquet forké** — `m4_3live_v2` par défaut ; changer si gênant.
2. **Le taux d'intérêt quand la créancière est la plus fragile** (§3.1) — la
   règle de taux actuelle (moyenne géométrique des rendements marginaux)
   a-t-elle encore un sens si celle qui prête est la plus pauvre ? À trancher
   avant le lot D, et à documenter quelle que soit la réponse.
3. **Nombre de graines de verdict** (§4.5) — 12 recommandé, à confirmer
   contre le budget de calcul.
4. **Constantes dimensionnées** (§6) — rééchelonner `MIN_LOAN` et `ZERO_TOL`
   en unités de capital rendrait la covariance d'échelle exacte, mais casse
   la comparabilité directe avec toutes les campagnes antérieures.
5. **La covariance de pas de temps devient-elle un test de non-régression ?**
   (§6, §9) — au même titre que la parité, ou reste-t-elle une vérification
   ponctuelle du rapport ? Attention : son résidu est de 6 à 17 %, donc un
   seuil naïf à zéro échouerait toujours.

---

## 13. Pièges de mesure hérités de v1

Ceux qui sont **toujours actifs** :

- **L'amplitude d'un levier sur γ vaut `K^Δγ`** (≈ 1,95 en v1, pas 1,2) :
  elle dépend du capital et doit être **mesurée à l'horizon 1**, jamais
  imposée.
- **Le coût d'un run est QUADRATIQUE en T**, et pas seulement croissant avec
  la taille du système : le carnet accumule une clef morte par entité jamais
  créée, la phase d'intérêts les parcourt toutes, donc le coût par pas est en
  λ·t et le coût total en **λT²/2**. Mesuré en v1 : +20 % de coût par pas
  entre t = 210 et t = 1810 à prêts actifs et population constants, 98 % des
  clefs étant vides. **C'est corrigé en v2 (§3.4), ce n'est pas une fatalité
  à contourner.**
- **Le choc multiplicatif ne biaise pas une comparaison appariée.** Il frappe
  entre l'action et la production, mais il est **commun aux deux bras** :
  mêmes vivantes, même ordre, même état du générateur. Il ne s'annule pas
  terme à terme — il est identique des deux côtés. Corollaire à préserver en
  v2 : *tant qu'une intervention ne touche pas au capital, tout ce qui est en
  amont de la production se simplifie dans un rapport apparié.* C'est ce qui
  rend l'appariement par graine puissant.
- **Pour mesurer l'ordre de convergence d'une table, l'échantillon doit
  balayer la variable indexée**, sinon on ne sonde qu'un point.

Ceux qui deviennent **dormants** avec le retrait du cas partiel (§3.3), à
connaître mais pas à outiller — sauf si une portée partielle réapparaît un
jour :

- un tirage `fraction` consomme le générateur, donc sa référence appariée est
  un bras `null` qui tire la même cohorte sans rien appliquer, jamais un
  contrôle inerte ;
- la part de production d'une cohorte traitée se mesure **après** application
  du levier, et doit être inversée en part ex ante par
  `p = s/(m − (m−1)s)` avant toute élasticité, sinon on la sous-estime de
  10 % ;
- la portée `fraction` ne fixe **pas** l'intensité de traitement dans ce
  modèle : elle décroît vers zéro en ~300 pas.

---

## 14. Quatre leçons d'analyse, générales

Elles ont coûté du temps réel en v1 et elles dépassent ce modèle.

1. **Un garde-fou d'ajustement doit tester l'ÉTENDUE, pas le nombre de
   valeurs distinctes.** v1 traçait des régressions sur neuf runs couvrant
   une plage de 0,6 % — du bruit de graine — parce que le garde-fou comptait
   les valeurs distinctes.
2. **Un ajustement groupé sur plusieurs familles peut n'être que la droite
   qui joint les lignes de base.** v1 avait un R² de 0,72 sur 127 runs ; la
   droite passant par les **trois bases seules** donne l'exposant 0,410
   contre 0,396 pour l'ajustement complet. Il ne mesurait aucune réponse.
   **Contrôle systématique** : ajuster sur les seules bases et comparer.
3. **Un observable peut être ininformatif précisément parce que deux effets
   se compensent.** Sous le recalage temporel brut, `K_tot` ne bouge que de
   1 % — non parce que le système est conservé, mais parce que chaque entité
   est deux fois plus petite et qu'il y en a presque deux fois plus.
4. **Une identité qui est une réécriture des définitions ne doit jamais être
   présentée comme une confirmation empirique.** L'identité
   `dlnT/dlnA = 1/(1−γ) − (1/γ)(ε_prod − η_pop − 1)` ne pouvait pas être
   fausse ; son résidu de 10⁻³ mesure la propreté de l'aller-retour
   numérique, rien d'autre. Le dire dans le texte.

À quoi s'ajoute une **habitude à prendre** : quand un test est possible,
**écrire la prédiction avant de lancer les runs**, et rapporter ensuite ce
que la prédiction a et n'a pas attrapé. v1 l'a fait deux fois ; les deux fois
la prédiction était partiellement juste, et le dire valait mieux que de ne
rapporter que la mesure.

---

## 15. Consignes de méthode de travail

- **Livrer un système complet, pas des ébauches.** Chaque pièce du §11 doit
  fonctionner de bout en bout avant que la tâche soit déclarée terminée — pas
  de squelette avec des TODO, pas de fonctionnalité à moitié câblée.
- **Calibrer la longueur des livrables écrits sur leur substance.** Les deux
  rapports doivent couvrir ce que ce prompt demande, sans sections de
  remplissage, sans résumé redondant en fin de document, sans paragraphe qui
  répète ce qui vient d'être dit autrement.
- **Paralléliser les calculs par lot.** La machine a 8 cœurs, dont
  **7 utilisables** (autorisation explicite de l'utilisateur, 21 août 2026) :
  **7 processus au maximum**, un par lot de runs indépendants. Les coûts
  ci-dessous ont été mesurés à 6 processus ; les rapporter à 7 en le disant.
  Ordres de grandeur mesurés en v1 : amorçage 5 graines × 2000 pas = 220 s ;
  9 bras × 5 graines × 2000 pas = 1865 s ; ablation 25 runs = 1287 s ; parité
  8000 pas = 1077 s. Attention : un run à γ = 0,4 coûte **4 fois** un run à
  γ = 0,5, parce que la population double et que le marché et le service
  doublent avec elle.
- **Périmètre : livrer ce qui est demandé, à l'échelle demandée.** Prendre
  seul les décisions d'implémentation de routine (y compris celles du §12) ;
  ne pas élargir le mandat au-delà du §1 ; si une lecture différente de ce
  prompt changerait matériellement le travail à produire, le signaler en une
  phrase et continuer avec la lecture la plus proche du texte.
- **Signaler ce qui est retiré.** Si une inférence écrite plus tôt se révèle
  fausse, la retirer explicitement dans le journal avec ce qui l'a réfutée.
  v1 l'a fait trois fois ; c'est une partie du travail, pas un aveu.

### Sous-agents : subdiviser intelligemment, pas systématiquement

- **Réserver ton propre raisonnement aux décisions qui déterminent la
  validité scientifique du travail** : la sémantique du sens libre et son
  effet sur le carnet (§3.1), les trois sémantiques de parité (§9), le
  protocole et l'écriture des verdicts (§7), l'analyse de la rotation (§5),
  et la relecture finale de cohérence entre code et rapports.
- **Déléguer les missions simples, bien délimitées et vérifiables
  isolément** à des sous-agents sur un modèle plus léger : écrire un test
  unitaire donné une spécification précise, lancer et collecter une graine
  d'une campagne dont le protocole est gelé, rédiger une section descriptive
  à partir de décisions déjà prises et citées, exécuter une non-régression
  sur `simulation_lab` et rapporter le résultat brut.
- Donner à chaque sous-agent un mandat **autonome et complet** — quel
  fichier, quel contrat d'entrée/sortie, quel test de validation. Un
  sous-agent frais ne voit pas ce prompt : lui fournir directement les
  extraits pertinents (numéros de ligne, formules, sémantique) plutôt que d'y
  renvoyer par référence.
- Ne pas déléguer la vérification de ton propre travail à un sous-agent en
  plus des tests déjà exigés (§9).
- Ne pas ouvrir plus de sous-agents que la structure du travail n'en
  justifie.
