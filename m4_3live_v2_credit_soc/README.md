# M4.3Live-v2 — moteur M4.3 pilotable en direct

Successeur structurel de M4.3 (`m4_3_credit_soc/`), mais **fork indépendant** :
aucun module de ce dossier n'importe un autre moteur du dépôt. L'institution de
principal change de nature — le transfert d'une paire n'est plus la moitié de
l'écart de capital, c'est le transfert qui **maximise la production jointe** des
deux entités juste après l'échange.

## Ce que M4.3Live-v2 ajoute à M4.3

| | M4.3 | M4.3Live-v2 |
|---|---|---|
| `A`, `γ` | globaux | **par entité**, fixés à la naissance, routés par identifiant entier de technologie |
| principal | `(K_ℓ − K_b)/2` | `δ* = h(C) − K_b`, optimum de production jointe (`m4_3live/kernel.py`) |
| paramètres | figés au lancement | **modifiables en direct**, trois portées `all` / `new` / `fraction` |
| exécution | batch | boucle pilotable (lecture / pause / pas-à-pas / vitesse) + IHM `/live` |
| reproductibilité | graine | graine **+ journal d'interventions** rejouable à l'identique |

Quand les deux entités d'une paire partagent la même technologie, `δ*` vaut
exactement `(K_ℓ − K_b)/2` : la baseline homogène de M4.3Live-v2 est **bit à bit**
celle de M4.3. Vérifié sur les 8000 pas et les 26 colonnes du run stocké
`m4_3__d1__baseline__seed0` (9 366 225 appels au noyau, écart maximal nul) —
rejouable par `tests/test_parity_m4_3.py --full`.

## Arborescence

```
m4_3live_v2_credit_soc/
├── m4_3live/            moteur autonome
│   ├── kernel.py        institution de principal : 3 régimes, Newton (t,u,z), LUT 1D frexp
│   ├── model.py         Config / Population / LoanBook / Simulation, interventions
│   └── live.py          session en direct, journal, snapshots, reprise + divergence
├── driver/headless.py   pilote sans tête : burn / arm / replay / resume
├── web/                 IHM `/live` (routeur + gabarit + statique), branchée dans simulation_lab
├── tests/               test_institution, test_scopes, test_replay, test_resume_divergence,
│                        test_surplus_rate, test_parity_m4_3
├── scripts/             campaign.py, analyse.py (campagne §7) ; ablation_k0.py ;
│                        bench_kernel.py, conception_evidence.py, protocol_figures.py,
│                        verification_figures.py (preuves + figures) ;
│                        scaling_gamma.py (loi d'échelle) ;
│                        import_to_simulation_lab.py, make_traceability.py
├── results/             amorçages, bras, analyses
├── report/              conception_m4_3live.pdf, rapport_final.pdf
└── prompts/             spécification et rapport d'architecture offline/online
```

## Utilisation

```bash
cd /home/anatole/jupyter

# IHM : le serveur de simulation_lab sert aussi /live
/home/anatole/jupyter/.venv/bin/python3 -m simulation_lab.cli gui --open-browser
# puis http://127.0.0.1:8777/live

# Tests (assertions Python simples, pas de pytest)
for t in institution scopes replay resume_divergence surplus_rate parity_m4_3; do
  /home/anatole/jupyter/.venv/bin/python3 m4_3live_v2_credit_soc/tests/test_$t.py
done
# La parité complète (8000 pas, ~17 min) :
/home/anatole/jupyter/.venv/bin/python3 m4_3live_v2_credit_soc/tests/test_parity_m4_3.py --full

# Pilote sans tête
cd m4_3live_v2_credit_soc
python3 driver/headless.py burn   --seed 0 --t0 2000 --out results/x/seed0
python3 driver/headless.py arm    --snapshot results/x/seed0/snapshot_t2000.pkl \
                                  --plan plan.json --steps 2000 --out results/x/arm
python3 driver/headless.py replay --config results/x/arm/summary.json \
                                  --journal results/x/arm/interventions.jsonl
python3 driver/headless.py resume --run-id m4_3__d1__baseline__seed0 --t0 1000 --out results/x/resume

# Campagne §7
python3 scripts/campaign.py burn     # amorçages partagés (5 graines, 5 procs)
python3 scripts/campaign.py arms     # 9 bras × 5 graines (6 procs)
python3 scripts/analyse.py           # métriques + figures du rapport

# Ablation sur le capital de naissance (5 bras × 5 graines)
python3 scripts/ablation_k0.py run
python3 scripts/ablation_k0.py analyse

# Loi d'échelle ε = 1/(1-γ) : γ ∈ {0,4 ; 0,6}, 3 graines
python3 scripts/scaling_gamma.py burn && python3 scripts/scaling_gamma.py arms
python3 scripts/scaling_gamma.py analyse

# Preuves chiffrées et figures des rapports
python3 scripts/conception_evidence.py    # institution, table, plafond, taux, déterminisme
python3 scripts/protocol_figures.py       # choix de t0/W, dénominateur du service
python3 scripts/verification_figures.py   # parité, calibration
python3 scripts/make_report_tables.py     # tableaux LaTeX (aucun chiffre recopié à la main)

# Rendre les runs consultables dans simulation_lab, puis l'annexe de traçabilité
python3 scripts/import_to_simulation_lab.py
python3 scripts/make_traceability.py
bash scripts/nonregression.sh             # non-régression de simulation_lab, exécutée
```

## Consulter les simulations

Les **203 runs** du programme (5 amorçages, 45 bras de campagne,
25 d'ablation, 18 de loi d'échelle, 39 de balayage de tension, 20 de
covariance d'échelle, 30 de balayage en A, 21 de recalage temporel)
sont enregistrés dans `simulation_lab` sous la lignée `m4_3live_v2_credit_soc`,
par lien symbolique — aucune copie, et les supprimer depuis l'IHM ne touche
que le lien. Chacun expose son `series.csv`, son `tech_series.csv`, son
journal d'interventions, les compteurs du noyau et une figure de synthèse.

```bash
/home/anatole/jupyter/.venv/bin/python3 -m simulation_lab.cli gui --open-browser
# page « Résultats », filtrer sur m4_3live_v2_credit_soc
```

L'annexe de traçabilité des deux rapports donne, pour chaque run cité, son
`run_id`, l'endroit où il apparaît, son rôle et ses interventions ; le
tableau complet est dans `results/analysis/traceability.csv`.

## Sémantique des portées (résumé ; détail dans le rapport de conception)

- **`all`** — rétroactif *et* prospectif : toutes les vivantes maintenant, et
  toutes les futures.
- **`new`** — vintage technologique : seules les entités nées après
  l'intervention ; les vivantes gardent leur valeur pour toujours.
- **`fraction`** — tirage unique d'une fraction φ des vivantes ; la valeur par
  défaut à la naissance **n'est pas modifiée**, donc aucune naissance ne
  reconstitue la cohorte traitée. (Le §2 du prompt en déduit que l'intensité de
  traitement reste fixe ; la campagne montre qu'elle décroît en fait vers zéro
  en ~300 pas — voir plus bas.)

Dégénérescences, affichées telles quelles par l'IHM plutôt que masquées :
`K0` n'existe qu'à la naissance (`all` ≡ `new`, `fraction` sans objet) ;
`lam`/`delta`/`sigma`/`rho`/`eta_beta`/`eta_n_ref` sont des paramètres de
population (`new` est un alias explicite de `all`, `fraction` sans objet).

## Garanties de reproductibilité

- Une intervention est appliquée **au tout début du pas**, avant les naissances,
  et journalisée avec son `t` effectif.
- Rejouer `(graine, paramètres, journal)` reproduit une trajectoire strictement
  identique — le journal du test provient d'une **vraie session en direct**, avec
  interventions soumises de façon asynchrone.
- Mettre en pause ne consomme aucun tirage.
- Un aller-retour par snapshot laisse la **dynamique** bit-identique. Réserve
  mesurée et bornée : `interest_paid` peut varier au dernier bit, car CPython ne
  sérialise pas la disposition interne d'un `set` et la phase d'intérêts somme
  dans cet ordre (détail dans `tests/test_replay.py`).
- Une reprise depuis un run M4.3 stocké **mesure et rapporte toujours** l'écart à
  la série d'origine ; elle n'est jamais présentée comme identique sans mesure.

## Non-régression

`simulation_lab` ne gagne qu'un aiguillage additif (`simulation_lab/live/`,
branché en tête de `do_GET`/`do_POST`). Aucune branche existante n'est modifiée,
et si M4.3Live-v2 est absent le serveur renvoie 503 sur `/live` sans rien casser
d'autre.

## Résultat de la campagne §7 (verdict d'observation)

Détail, figures et limites : `report/rapport_final.pdf`.

|                       | court horizon (h ≲ 300) | régime établi (h ≥ 1001) |
|---|---|---|
| **portée partielle** (`fraction`) | **rebond observé** — réponse 2,3 à 2,9 × la réponse proportionnelle, 3 à 48 σ | **non tranchable** — la cohorte traitée s'éteint, le dénominateur disparaît |
| **portée globale** (`all`, `new`), `K0` fixe | rebond transitoire (élasticité 2,18 à h≤50) | **effet inverse** — élasticité 0,72 (88 σ) : +36,1 % de production pour +50 % de A |
| **portée globale**, `K0` compensé à l'échelle | rebond transitoire également | **rebond établi, fort** — élasticité 2,53, ε = 2,02, à population inchangée |

Et cette élasticité suit une **loi** : ε = 1/(1−γ), l'exposant de l'échelle
autarcique, vérifié à mieux que 1,3 % en γ = 0,4 / 0,5 / 0,6 (ε mesuré
1,646 / 2,018 / 2,497 contre 1,667 / 2,000 / 2,500) — sur une plage où ε
varie lui-même de 52 %.

Décomposition du régime établi à `K0` fixe : production **par entité** ×1,80
(pour un choc de ×1,50) mais population ×0,754. La somme est
sous-proportionnelle parce qu'il y a un quart d'entités en moins, pas parce que
chacune produit moins.

**Et cette contraction est un artefact d'échelle, pas un effet de la
technologie.** `K0 = 25` est fixe alors que le capital moyen par entité monte
de 773 à 1118 : les nouveau-nés deviennent relativement trop petits et meurent
plus vite. Compenser `K0` par `A^{1/(1−γ)}` annule la contraction (population
×1,005) et ramène tous les diagnostics à leur valeur de contrôle. Le signe du
résultat global dépend donc d'une convention, explicitée dans le rapport.
L'explication concurrente — un service d'intérêts alourdi — a été **réfutée** :
rapporté à la production, le service baisse de 1,128 à 1,093.

Deux faits méthodologiques qui conditionnent la lecture :

- la mesure est calibrée exactement — à l'horizon 1, l'amplitude reconstruite à
  partir des seules mesures agrégées redonne 1,5000 / 1,2500 / 1,5000 aux
  valeurs imposées, à quatre décimales ;
- **la portée `fraction` ne fixe pas l'intensité de traitement** dans ce modèle,
  contrairement à ce que suppose le §2 du prompt : la part de production de la
  cohorte traitée tombe de 0,198 à 0,022 en 2000 pas. Ce sont `all` et `new`
  (intensité → 1) qui portent la version à intensité fixe de la question.

---

## Ce que la relecture annotée a ajouté (18 août 2026)

28 notes portées sur `report/rapport_final.pdf` ont été traitées. Les trois
apports scientifiques, au-delà des corrections de rédaction :

**L'amplitude et la part traitée sont mesurées entité par entité**, plus
reconstruites depuis les agrégats (`scripts/exact_amplitude.py`). La
production individuelle étant en mémoire après le pas, le capital au moment
de produire se retrouve exactement, et la production contrefactuelle avec.
`E(h=1) = 1` à **1,0·10⁻¹⁵** près sur les six bras à levier : l'égalité
« écart observé = (m−1)p » est exacte, pas approchée.

**ε = 1/(1−γ) est démontré, plus seulement mesuré**
(`scripts/scaling_theory.py`). Le modèle est **covariant d'échelle** :
`A → A'` avec `K0 → cK0`, `c = (A'/A)^{1/(1−γ)}`, redonne la même simulation
à l'échelle `c` près — chaque phase du pas est homogène de degré 1 en
capital et le taux d'intérêt marginal est un nombre sans dimension. Vérifié
depuis t=0 : écart maximal **5·10⁻¹⁵** sur la production, **population
rigoureusement identique**, ε = 1,6667 / 2,0000 / 2,5000 exactement. Sans
compensation : 58 % d'écart.

**La « tension » T = K_aut/K_eq, et le test qu'elle ne passe pas.** Le
système observé tourne à **un treizième de son échelle autarcique**. À
dépréciation fixe, la tension prédit la mortalité à 1,4 % près sur une plage
×15 atteinte par trois leviers sans rapport — `K0/4` et `A×2` amènent à
T = 29,46 et 29,61 et donnent 0,04282 et 0,04304 morts par entité et par
pas. **Mais un balayage à quatre leviers (39 runs) la met en échec sur δ** :
un facteur 8 sur δ déplace T d'un facteur 13 et la mortalité de 14 % ;
`δ=0,04` et `K0=400` ont la même tension et des mortalités dans un rapport
3,3. Ce qui aligne les quatre leviers est la **rotation du crédit**
`loan_volume/K_tot` (R² = 0,998) — variable endogène, donc une régularité
descriptive qui désigne le canal sans le démontrer.

## Ce que la relecture du 21 août 2026 a ajouté

**Figure 12 refaite.** Elle superposait trois γ dans un plan avec quatre
droites d'ajustement. Deux de ces droites portaient sur des plages de tension
de 0,6 % et 1,0 % — du bruit de graine, laissé passer par un garde-fou qui
comptait les valeurs distinctes au lieu de mesurer l'étendue. La troisième,
« tous γ confondus » (R² = 0,72), a été identifiée pour ce qu'elle était : la
droite passant par les **trois lignes de base** a pour exposant 0,410 contre
0,396 pour l'ajustement sur 127 runs — elle mesurait le déplacement de la
base avec γ, pas une réponse à la tension. Un panneau par γ désormais, sans
aucun ajustement.

**Covariance de pas de temps** (§7.3, `scripts/time_rescaling.py`). λ→2λ,
δ→2δ−δ², σ→√2σ **composent exactement** — identité algébrique pour δ, somme
de deux log-normales (dérive comprise) pour σ, somme de deux Poisson pour λ.
Mais elles ne suffisent pas : il faut y ajouter les deux flux par pas, `A→2A`
(qui porte aussi le taux d'intérêt) et `ρ→2ρ` (rondes de marché). Avec les
cinq : population ×1,067, morts par pas ancien ×1,003, tension ×0,943,
production par pas neuf ×2,24. Avec trois seulement : population ×1,85,
production par pas ancien ×0,70. Le résidu de 6 à 17 % est irréductible — la
phase de marché ne se compose pas, deux rondes de ρN appariements ne valant
pas une ronde de 2ρN.

**D'où vient le résidu — deux tests, un seul qui tranche.** Rejouer le
recalage à `s = 4` triple le résidu, mais triple aussi le déplacement de
K_aut : les deux termes croissent en (s−1), donc ce test **ne sépare rien**.
Le discriminant est δ : à `δ = 0,002` le terme de K_aut tombe de 1,00 % à
0,20 %, et le résidu **ne décroît pas** (production +11,8 % → +15,0 %). La
discrétisation est écartée ; c'est bien la phase de marché.

**Piège de lecture à connaître** : sous l'énoncé brut, `K_tot` ne bouge que
de 1 %, non parce que le système est conservé mais parce que chaque entité
est deux fois plus petite et qu'il y en a presque deux fois plus.

**« A×x implique-t-il T×x ? » Non** (§6.5, `scripts/tension_vs_A.py`). À
K0 fixé la tension suit une loi de puissance très propre (R² ≥ 0,9999), mais
d'exposant **0,776 / 1,145 / 1,673** pour γ = 0,4 / 0,5 / 0,6 : il ne passe
par 1 qu'au voisinage de γ ≈ 0,46. L'exposant n'est pas libre, il vaut
`1/(1−γ) − (1/γ)(ε_prod − η_pop − 1)` — une réécriture des définitions de
K_aut et K_eq. Et sous compensation de K0 il vaut exactement **0** : tout le
phénomène est un effet du décalage entre l'échelle du système et un capital
de naissance laissé derrière.

**203 runs** sont consultables dans `simulation_lab` ; l'annexe de
traçabilité en recense 207 avec les runs M4.3 cités.

La feuille de route de la suite est dans
`../m4_3live_v2_credit_soc/ROADMAP.md`.
