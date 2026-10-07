# M4.2 — résumé (27–29 juillet 2026)

**Question posée** : dans le modèle de société de crédit M4B, la pente τ
de la distribution des tailles d'avalanches de faillites peut-elle
devenir une propriété modulable en introduisant un exposant de concavité
γ dans la fonction de production F_γ(K) = A·K^γ ?

## Réponse

**γ déplace mesurablement τ̂, avec un contraste principal (γ=1/3 vs 1/2)
qui satisfait 6 des 8 conditions pré-enregistrées de confirmation — mais
pas par la concavité.** Un contrôle d'échelle apparié, exécuté en
exploration et sur les graines confirmatoires disjointes, montre que
l'effet est dominé par le déplacement du point fixe autarcique
K*_aut(γ) = ((1−δ)A/δ)^(1/(1−γ)) : c'est précisément la condition n°8
(contrôle d'échelle) qui échoue, et c'est elle qui porte l'information
scientifique la plus importante. Ce n'est pas qu'une observation
empirique : on démontre une **invariance d'échelle exacte** de la
dynamique discrète sous (K, K₀, A) → (cK, cK₀, c^(1−γ)A), qui implique
qu'à γ fixé, τ̂ ne peut dépendre de A et K₀ qu'à travers le rapport
adimensionnel **K₀/K*_aut(γ,A)**.

## Terminologie utilisée dans ce résumé

Le protocole rend un verdict machine à trois issues sur les graines
confirmatoires 11-15 : **CONFIRMÉ** seulement si les 8 conditions
pré-enregistrées passent toutes ; **PARTIEL** si certaines échouent
(nommées explicitement) ; **infirmé** si l'IC contient zéro avec une
demi-largeur ≤0,15. Le mot « confirmé » n'est jamais utilisé ici pour un
résultat que le protocole classe PARTIEL.

## Ce qui a été établi, avec le niveau de preuve associé

| Résultat | Verdict machine | Niveau |
|---|---|---|
| τ̂(γ=1/3) − τ̂(γ=1/2) = −0,125, IC95 [−0,135;−0,115] | **PARTIEL** (6/8 conditions PASS, échec 5 et 8) | Établi sur 5 graines disjointes 11-15 |
| Robuste à λ∈{10,30,100} (exploration), aux fenêtres T/8-T/2, à l'horizon doublé (T=8000) | conditions 2, 3 PASS | Exploration pour λ=100 et horizon ; confirmatoire pour l'IC lui-même |
| Invariance d'échelle exacte sous (K,K₀,A)→(cK,cK₀,c^(1−γ)A) | -- | **Démontrée** (théorème + vérification numérique à 1,2·10⁻¹¹) |
| Effet dominé par l'échelle, pas la concavité (résiduel γ=1/3 : +0,031, signe opposé au total) | condition 8 = FAIL (c'est l'info) | Confirmatoire (IC95 [+0,001;+0,061], marginal) + exploratoire cohérent (γ=0,6 et 2/3) |
| Résidu propre de courbure à K₀/K*_aut fixé (test de substitution K₀) | -- | **Non tranché** : IC95 ≈ ±0,1 sur 3 graines, englobe zéro dans les deux sens |
| Contrastes γ=0,6 et γ=2/3 (le "pic" vu en exploration) | **PARTIEL**, minorité de conditions PASS | Non établis comme robustes |
| Rapport de branchement b ≈ 0,30-0,32, invariant en γ et λ | -- | Confirmé sur les 4 cellules confirmatoires + 15-24 cellules d'exploration |
| Canal de liquidité quasi silencieux | -- | 17 événements sur 102 runs, **exclusivement à γ≥2/3**, jamais en confirmation |

## La chaîne causale mesurée

γ ↑ → taux médian du carnet ↑ (1,4 à 2,7 fois la prédiction γδ/(1−δ),
croissant avec γ) → intérêts/production ↑ (0,45→0,77) → âge moyen au
décès ↓ (22,0→6,8 pas), contrats par tête ↓ (10,7→4,2) → expositions
unitaires au décès ↑ d'un facteur ~5. Ce mécanisme est réel — il
explique *comment* γ agit, et pourquoi le canal de liquidité s'éveille
précisément à γ élevé — mais son effet net sur τ̂ transite majoritairement
par le canal d'échelle K₀/K*_aut, pas par la courbure elle-même.

## Ce qui reste invariant

- La cible instantanée de crédit √(K_ℓ·K_b) ne dépend jamais de γ à
  capitaux donnés (identité démontrée).
- b reste épinglé institutionnellement par la règle « un round de
  marché par tête », indépendamment de γ.
- La propagation reste très majoritairement une contagion de bilan pure ;
  le canal de liquidité ne s'éveille (faiblement) qu'à γ≥2/3.

## Prédictions analytiques vérifiées

- K*_aut(γ) = 19^(1/(1−γ)) à δ=0,05, A=1 (exact, testé à 10⁻⁹).
- Rendement marginal au point fixe : m(K*_aut) = γ·δ/(1−δ), linéaire en γ.
- Production/capital au point fixe : δ/(1−δ), invariante en γ.
- A_norm(γ) = 19^(1−2γ) égalise K*_aut à toute échelle de référence.
- Invariance exacte (K,K₀,A)→(cK,cK₀,c^(1−γ)A) de toute l'histoire
  discrète (naissances, morts, avalanches) — démontrée et vérifiée
  numériquement à 1,2·10⁻¹¹ relatif.

## Limites et résultats négatifs

- Seul le contraste γ=1/3 vs 1/2 atteint 6/8 conditions ; γ≥0,6 reste
  au niveau PARTIEL avec une minorité de conditions satisfaites.
- Le test de l'hypothèse structurelle K₀/K*_aut établit sa partie
  nécessaire (théorème) mais pas sa partie empirique (résidu de courbure
  à rapport fixé) : la précision disponible (3 graines) ne permet ni de
  l'établir ni de l'exclure.
- Erratum méthodologique découvert en confirmation : le test de Vuong
  initialement disponible comparait la loi pure (déjà rejetée par LRT
  partout, p<4·10⁻³³) au log-normal au lieu du modèle primaire (tronqué)
  — échec non différentiel, corrigé par un test de Vuong correctement
  normalisé tronquée/log-normale (z=+16 à +19 dans tous les runs
  confirmatoires). Le critère de décision n'a pas été modifié
  rétroactivement.
- À λ=100, τ̂ est en réalité l'exposant de la loi pure (coupure hors
  portée dans les 9 runs) ; les scalings de coupure reposent sur
  seulement deux tailles exploitables.
- 0 run éteint, censuré ou instable sur 102 runs distincts (117
  exécutions de cellule, 15 partagées entre pilotes et taille finie par
  identifiant déterministe).

## Où trouver quoi

- Moteur et tests : `m4_2/`, `tests/` (18+2+8 tests, tous verts).
- Spécification mathématique (dont la démonstration d'invariance
  d'échelle) : `report/spec_m4_2.pdf`.
- Protocole pré-enregistré (v1.1, figé avant production) : `report/protocole.pdf`.
- Rapport préliminaire (exploration/confirmation séparées) : `report/rapport_preliminaire.pdf`.
- Rapport final complet : `report/rapport_final.pdf` (avec annexe de traçabilité).
- Journal chronologique, y compris les corrections post-audit : `JOURNAL.md`.
- Figures régénérables : `scripts/make_figures.py` → `figures/*.png`.
- Verdicts confirmatoires détaillés : `results/tables/confirm_contrasts.csv`.
- Tous les runs sont dans Simulation Lab (`model_id=m4_2_credit_soc`),
  traçables via `manifests/*.manifest.json`.
