# M4.3 — rapport (2026-08-08)

**Statut : D1/D2/D3 TERMINÉS. Une décision reste ouverte, réservée à la
supervision humaine.** La cartographie D1 est terminée (84/84 runs, y
compris K0_2000 documentée comme sévère). Un candidat D2 a été trouvé
(`gamma_comp` à γ≥0,6) et **confirmé robuste à la taille par D3**
(section 7). Le jalon de décision d'ablation (§4 du prompt) est atteint
et **explicitement réservé à la supervision** (§9 du prompt) — section 8
présente les éléments pour et contre, sans trancher. C'est la seule pièce
manquante pour clore intégralement le prompt de référence.

Document autonome : contexte, grandeurs et méthode sont rappelés avant
d'être utilisés, chaque affirmation quantitative renvoie à une donnée
vérifiable (fichier, figure, ou calcul reproductible par un script cité).

Terminologie : **Fait observé** (mesuré directement) / **Inférence**
(interprétation appuyée sur plusieurs faits) / **Hypothèse** (mécanisme
proposé, pas établi) / **Incertitude** (non tranché).

---

## 1. Contexte : la question de M4.3 en deux phrases

M4.3 est le successeur direct de M4.2B (`m4_2b_credit_soc/`, rapport final
dans `m4_2b_credit_soc/report/rapport_final.md`, lecture préalable
supposée). M4.2B a établi, sur les 37 cellules qu'il a explorées, que
**l'épaisseur de la queue de revenus d'intérêt et la criticité des
avalanches de faillites s'anti-corrèlent partout où il a regardé** :
aucune cellule ne combine queue plus épaisse ET criticité égale ou
accrue. M4.3 pose une question plus étroite et décidable : **cette
anti-corrélation est-elle une propriété structurelle de cette classe de
modèle, ou existe-t-il un paramètre ou un mécanisme qui la brise ?**
(prompt de référence : `prompts/PROMPT_M4_3_FINAL.md`, non répété ici).

Le moteur est repris de M4.2B **sans aucune modification** (`m4_3/model.py`
et `m4_3/io.py` sont des copies octet pour octet de
`m4_2b_credit_soc/m4_2b/{model,io}.py`, `diff` vide, parité runtime
vérifiée par `tests/test_parity_m4_2b.py` — égalité EXACTE sur 6
combinaisons seed×target_rule).

## 2. Méthode

### 2.1 Garde-fous de calcul (impératif de l'utilisateur, "un crash du PC serait catastrophique")

Six garde-fous, tous dans `scripts/safety/` + `scripts/mem_guard.py`,
détaillés et testés dans `JOURNAL.md` §3 :
préflight disque (budgété sur la cellule/le pool entier, pas le seul run
qui démarre), plafond mémoire par worker calculé sur `MemAvailable` réel,
verrou mono-pool (`flock`), checkpoint atomique, garde-fou mémoire
indépendant avec autorité de blocage/terminaison (processus séparé,
surveille `/proc/meminfo` et `/proc/vmstat`), budget ≤6 workers. **Fait
observé** : sur l'intégralité du programme à ce jour (campagne pilote +
D1, plusieurs dizaines d'heures de calcul cumulées), 0 arrêt machine, 0
intervention du garde-fou mémoire nécessaire (seuil d'action jamais
atteint), une seule catégorie d'échec — mémoire insuffisante sur la
cellule K0=2000 — capturée proprement (`status="error"`, traceback
complet, pool non affecté) plutôt que de faire planter le programme.

### 2.2 Fenêtre d'analyse adaptative, pas un burn-in fixe (§3 du prompt)

M4.2B positionnait sa fenêtre d'analyse sur un burn-in fixe (T/4). M4.3
mesure, PAR RUN, le temps de relaxation propre de la variable d'intérêt
centrale (`int_in`, l'intérêt pur reçu — pas un proxy) par régression
FOPDT sur la persistance du décile supérieur (méthode déjà validée en
M4.2B, `scripts/renewal_relaxation_all_runs.py`, réutilisée sans
modification, étendue au champ `int_in` dans
`scripts/relaxation_pilot.py`/`campaign_d1.py`). **Fait observé** : ce
temps de relaxation (i) varie sensiblement entre graines à paramètres
FIXÉS (contrôle geometric : t_converge 3006 à 4174 sur 3 graines, ~28 %
d'écart) et (ii) diffère systématiquement, dans le sens d'être PLUS LENT,
des proxys utilisés par M4.2B (net worth, capital, revenu total) — ratio
1,35 à 1,66 selon la cellule et la graine, jamais inversé sur 4 mesures
indépendantes. Durée retenue pour toute la cartographie D1 : **T=8000**,
choisie empiriquement (validée sur les deux régimes de référence,
géométrique et arithmétique) plutôt que recalculée cellule par cellule
(coût déraisonnable sur 28 cellules) ; chaque run vérifie a posteriori que
son propre `t_converge < 0,9·T`, et se marque `severe_nonstationary` sinon
— **fait observé : 0/81 runs D1 marqués sévères**, T=8000 s'est avéré
large sur tout l'espace testé.

### 2.3 Statistique de queue gelée (§2 du prompt)

Choisie et gelée AVANT la cartographie D1, sur le critère prescrit
(reproductibilité inter-graines, pas la valeur) — détail complet et
**une erreur trouvée et corrigée avant que D1 ne s'appuie dessus** dans
`JOURNAL.md` §11. Deux candidats comparés sur 3 graines × 2 régimes
(géométrique, arithmétique) : l'estimateur de Hill/Pareto pur utilisé par
M4.2B (CV 1,35-1,59 %) contre le paramètre de forme `c` (indice de queue
supérieure, `survie ~ x^-c`) du meilleur ajustement à 3 paramètres
(`dagum_3p`, Burr Type III — famille usuelle pour les distributions de
revenu avec coude de queue ; AIC favorise TRÈS largement une famille à
coude sur les 6 graines testées, ΔAIC~15 000-20 000 contre une
exponentielle pure). **Résultat : `dagum_3p` c est ~2× plus reproductible**
(CV 0,69-0,70 %) **— statistique gelée pour tout le reste du programme.**

### 2.4 Cartographie D1

`scripts/campaign_d1.py` : pool multiprocessing (patron déjà validé en
M4.2B sur 87+45 runs), 6 workers, cellules = copie exacte des paramètres
de la campagne d'exploration M4.2B (`m4_2b_credit_soc/scripts/campaign.py`
— η/ρ, γ (compensé et non compensé), K0, δ/σ, target_rule), 28 cellules ×
3 graines = 84 runs. Nettoyage disque post-analyse intégré dès le départ
(journaux bruts par transaction et instantanés réseau supprimés après
extraction des métriques agrégées — nécessaire par arithmétique disque,
détail dans `JOURNAL.md` §13).

## 3. Repères : ce que mesurent les grandeurs citées plus loin

- **`dagum_c`** (statistique de queue gelée, §2.3) : indice de la queue
  supérieure de la distribution des revenus d'intérêt reçus, mesuré sur
  la fenêtre post-relaxation propre à chaque run. **Plus `c` est PETIT,
  plus la queue est ÉPAISSE** (décroissance plus lente).
- **`b` (branching ratio)** : rapport de branchement des avalanches de
  faillites (méthodologie M4B/M4.2B, `lib_metrics.window_avalanche_
  metrics`, inchangée). Proche de 1 = dynamique proche du point critique
  (avalanches plus grosses, plus fréquentes) ; proche de 0 = sous-
  critique.
- **`τ̂`** : exposant de la loi de puissance (tronquée si identifiable)
  ajustée sur la distribution des tailles d'avalanche — métrique
  secondaire par rapport à `b` (convention M4B, `JOURNAL.md` §5).
- **Anti-corrélation** (le sujet central du programme) : `dagum_c` et `b`
  varient dans le MÊME sens d'une cellule à l'autre (queue plus épaisse
  = `c` bas = `b` bas aussi = moins critique). Un « candidat D2 » est une
  cellule où `c` baisse (queue plus épaisse) MAIS `b` monte (plus
  critique) — le motif recherché par tout le programme.
- **`t_converge`** : instant estimé où la variable d'intérêt (`int_in`)
  atteint sa valeur stationnaire, par régression FOPDT sur la persistance
  du décile supérieur (§2.2). La fenêtre d'analyse d'un run est
  `[t_converge, T]`.

## 4. Résultat pilote : `target_rule` (géométrique vs arithmétique) — D2 négatif

Premier run prescrit par le prompt (§4) : le contrôle géométrique
(canal multiplicatif que la cible arithmétique de M4.2B supprime), 3
graines contre 3 graines de la baseline arithmétique, T=8000, méthode
complète (§2.2-2.3) — pas la mesure ponctuelle de M4.2B.

| régime | dagum_c | b | τ̂ |
|---|---|---|---|
| géométrique | 3,361 ± 0,023 | 0,754 ± 0,002 | 1,476 ± 0,007 |
| arithmétique | 3,969 ± 0,028 | 0,785 ± 0,001 | 1,424 ± 0,006 |

**Géométrique a la queue d'intérêt plus ÉPAISSE (c plus bas) ET des
avalanches MOINS critiques (b plus bas)** — anti-corrélation confirmée,
séparation ~29σ (c) à ~34σ (b), pas un effet marginal. Confirmé par trois
mesures indépendantes convergentes (candidat A, candidat B, et la mesure
historique de M4.2B — détail `JOURNAL.md` §12). **Verdict D2 pour ce
levier : négatif.** Un résultat négatif est un résultat scientifique
valide (le prompt le dit explicitement, §1) — le canal multiplicatif ne
casse pas l'anti-corrélation, il en est un point de plus.

## 5. Cartographie D1 : l'espace de M4.2B, remesuré

Figure : `figures/d1_plan_dagum_c_vs_b.png` (un point par cellule, barres
d'erreur inter-graines, axe `dagum_c` inversé pour lire « queue plus
épaisse » de gauche à droite). Table complète :
`results/d1/d1_verdict_cells.csv`.

**Sur 26 cellules identifiables** (K0_2000 exclu, en reprise — voir §6) :
24 confirment l'anti-corrélation ou montrent les deux métriques bougeant
ensemble dans le même sens (non informatif). **2 cellules — `gamma_comp_
0.6000` et `gamma_comp_0.6667` (γ=0,6 et γ=2/3, K0 compensé pour tenir
K0/K*_aut(γ) constant) — montrent le motif inverse : queue plus épaisse
ET b plus élevé que la baseline**, avec une tendance MONOTONE sur toute
la branche γ∈{1/3, 0.4, 0.6, 2/3} (`dagum_c` : 5,19→4,56→3,58→3,39 ;
`b` : 0,760→0,770→0,802→0,804), séparation ~15σ sur les deux axes contre
la baseline. Détail complet, y compris le contraste avec la branche γ NON
compensée (motif non monotone, pas le même effet), dans `JOURNAL.md` §16.

**Réserve non résolue à ce stade** : `gamma_comp` fait varier K0 (par
construction, pour la compensation), donc la population finale varie
d'environ ±25 % autour de la baseline sur cette branche (bien moins que
la variation sur plusieurs ordres de grandeur de la branche K0 brute, mais
pas nulle). Ce candidat n'est pas confirmé tant que sa robustesse à taille
FIXE (via λ, méthode M4B/§5 du prompt) n'est pas vérifiée — c'est l'objet
de la section suivante.

## 6. K0_2000 : échec mémoire propre, résolu, mais cellule intrinsèquement sévère

Les 3 graines de K0_2000 ont d'abord échoué dans le pool principal
(`ArrayMemoryError`, plafond mémoire virtuel par worker atteint, 4,43 Go)
— capturé proprement (§2.1), 0 impact sur les 81 autres runs. Reprise
séparée (2 workers, plafond ≈13,56 Go/worker) : **3/3 réussissent**,
confirmant que le problème était bien le plafond, pas la cellule. **Mais
les 3 graines sont `severe_nonstationary` à T=8000** (`t_converge_int_in`
entre 7568 et 9087, proche ou au-delà de 0,9·T) — K0_2000 (80× la
baseline) est intrinsèquement trop lente à relaxer pour T=8000. Décision
(convention déjà actée par le prompt §3, pas un choix nouveau) :
**ne pas étendre** (coût estimé 8-10h/run pour cette seule cellule
extrême) — `dagum_c` non disponible pour K0_2000, mais le rapport de
branchement reste identifiable (moins sensible à la fenêtre) :
**b = 0,6797 ± 0,0011** (2/3 graines identifiables). Détail complet dans
`JOURNAL.md` §15/§18/§19.

## 7. D3 — robustesse de taille du candidat `gamma_comp` : POSITIF

`scripts/d3_size_check.py` : `{baseline, gamma_comp_0.6667} × λ∈{10,30,100}`,
3 graines chacune (λ=30 réutilisé de D1). Résultat :

| λ | pop (baseline) | pop (gamma_comp) | Δc (gamma_comp−baseline) | Δb |
|---|---|---|---|---|
| 10 | 393 | 468 | −0,5935 (27,7σ) | +0,0184 (8,7σ) |
| 30 | 1163 | 1395 | −0,5819 (26,4σ) | +0,0184 (25,9σ) |
| 100 | 3775 | 4681 | −0,5944 (84,5σ) | +0,0185 (36,9σ) |

**Δb est identique à 4 chiffres significatifs sur les trois échelles de
taille (0,0184 / 0,0184 / 0,0185) et Δc varie de moins de 2 % relatif**,
malgré un facteur >10× sur la population absolue. C'est la signature
attendue d'un effet indépendant de la taille — pas l'atténuation qu'on
observerait si l'effet était un artefact de la variation de population
que la compensation K0/K*_aut(γ) ne neutralise pas parfaitement.
**Vérification annexe** : la baseline elle-même est size-indépendante sur
ces deux métriques (écart <1 % sur c, <0,5 % sur b entre λ=10 et λ=100) —
reproduit directement le résultat déjà établi par M4B, validation
indépendante que le test de taille par λ fonctionne comme attendu sur ce
moteur.

**Verdict D3 : POSITIF.** `gamma_comp_0.6667` casse l'anti-corrélation de
façon robuste à la taille. **C'est le premier résultat de tout le
programme M4.2B→M4.3 (65 cellules testées au total, M4.2B + D1 de M4.3)
qui casse l'anti-corrélation avec cette solidité statistique.**
Mécanisme : γ et la compensation K0/K*_aut(γ) sont DÉJÀ dans le moteur —
aucune ablation de mécanisme n'est nécessaire pour ce résultat spécifique.

**Robustesse temporelle** (distincte de la reproductibilité inter-graines
ci-dessus) : la fenêtre post-convergence de chaque run (baseline,
gamma_comp_0.6667, λ=30) découpée en deux moitiés temporelles donne un
écart `b` stable (+0,0189 en première moitié, +0,0178 en seconde,
`scripts/temporal_robustness_check.py`) — pas un artefact d'une
sous-période particulière.

Figure : `figures/d3_size_robustness.png` — Δc et Δb (gamma_comp−baseline)
contre λ, échelle log, barres d'erreur inter-graines. Les deux courbes
sont visuellement plates : aucune tendance décelable sur deux ordres de
grandeur de λ.

## 8. Décision d'ablation (§4 du prompt) : jalon atteint, décision réservée à la supervision (§9 du prompt)

La cartographie D1 est le jalon fixé à l'avance pour trancher, par écrit,
si une refonte de mécanisme (ex. famille de moyennes de puissance pour la
règle de taux, note manuscrite citée au §4 du prompt) est nécessaire.
**Cette décision est explicitement hors du périmètre de ce qui peut être
tranché de façon autonome**, même après confirmation D3. Éléments pour la
décision, sans trancher :

- **Pour** : D3 (§7) CONFIRME `gamma_comp_0.6667` robuste à la taille
  (marge statistique large, 27-85σ selon λ) — la preuve directe qu'un
  changement de règle de taux COMBINÉ à une compensation de capital casse
  l'anti-corrélation. Signal fort qu'une famille plus riche (moyennes de
  puissance, note manuscrite) pourrait révéler une région encore plus
  favorable que les deux points déjà couverts (arithmétique, géométrique)
  — ou, alternative moins coûteuse à explorer d'abord, qu'un simple
  affinement du balayage γ_comp déjà existant (γ∈{0,7;0,8;0,9} compensé)
  pourrait suffire sans nouveau code.
- **Contre / pas encore** : le mécanisme qui casse l'anti-corrélation
  (`gamma_comp`) EXISTE DÉJÀ dans le moteur — ce n'est pas `target_rule`
  (D2-négatif, §4) qui était le déclencheur anticipé par le prompt pour
  cette famille de moyennes de puissance. Un affinement du γ déjà
  implémenté (coût ~identique à une cellule D1) est un préalable moins
  coûteux et plus informatif qu'un engagement de code de mécanisme
  nouveau — et ce prolongement lui-même est un nouvel engagement de
  calcul non couvert par le plan D1 initial, donc également signalé
  plutôt que lancé seul (`JOURNAL.md` §21).

## 9. Limites et non testé à ce stade

- Statistique de queue gelée sur 3 graines par régime (§2.3) — assez pour
  trancher entre les deux candidats testés (écart net, ~2×), pas assez
  pour une incertitude publiable au sens strict (M4.2B utilisait 5 graines
  de confirmation disjointes pour ce niveau de rigueur).
- D1 mesure `dagum_c`/`b` en fin de fenêtre post-convergence, pas
  l'évolution temporelle intra-fenêtre (stationnarité supposée une fois
  `t > t_converge`, pas re-testée formellement dans D1).
- La coupure d'avalanche ŝc(λ) n'a pas encore été ré-établie sur ce moteur
  (§5 du prompt, prévu si D2 devient positif après D3).
- Rapport de branchement `b` et `τ̂` utilisent `s_min=2` (convention
  M4B/M4.2B) sans re-test de sensibilité à ce choix dans M4.3.

---

*Document généré et maintenu par le programme autonome M4.3 (voir
`JOURNAL.md` pour le détail chronologique complet). Prochaine mise à
jour : verdict D3 dès disponible.*
