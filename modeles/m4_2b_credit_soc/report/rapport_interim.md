# M4.2B — rapport intermédiaire (2026-08-05)

**Statut** : ce document lit exclusivement les données de la campagne
d'**exploration** (87 runs). Une campagne de **confirmation**, plus
petite mais statistiquement plus exigeante, est en cours d'exécution au
moment de la rédaction et n'est pas encore intégrée ici. **Rien dans ce
document n'a été validé par cette confirmation** — c'est une lecture
provisoire, à seule fin de savoir où en est la science en attendant.

---

## 1. Contexte : le programme M4.2B en deux phrases

M4.2B est une simulation multi-agents d'une économie de crédit : des
entités abstraites empruntent, prêtent, se versent des intérêts, et
peuvent faire faillite — une faillite pouvant en déclencher d'autres en
cascade (« avalanche »). Le programme poursuit deux objectifs
**simultanés** :

- **Objectif A** — Le revenu d'intérêt réellement perçu par chaque
  entité à un instant donné a-t-il, dans une région significative de
  l'espace des paramètres, une distribution à queue épaisse de type
  **Pareto** (quelques entités touchant un revenu disproportionné selon
  une loi de puissance), et cette queue peut-elle être pilotée de façon
  reproductible en agissant sur la structure du marché du crédit — en
  particulier sur l'intensité des appariements emprunteur/prêteur
  (paramètre η, voir §3) ?
- **Objectif B** — Quel que soit le réglage trouvé pour l'objectif A, il
  ne doit pas détruire une propriété déjà établie dans les versions
  antérieures du modèle : la taille des cascades de faillites suit une
  loi de puissance, signature d'une dynamique proche d'un point
  critique. Un réglage qui produit une belle queue Pareto des revenus
  mais éteint cette criticalité n'est pas un succès — c'est un compromis
  à documenter comme tel.

## 2. Méthode : exploration puis confirmation

Une **campagne d'exploration** balaie 29 combinaisons de paramètres
(« cellules »), chacune répétée sur 3 graines aléatoires (0, 1, 2) pour
vérifier une cohérence minimale, sur 3000 pas de temps simulés (une
cellule est poussée à 10 000 pas pour vérifier la stabilité à long
terme) — 87 runs au total, tous terminés avec succès. Son rôle est de
repérer où, dans l'espace des paramètres, il se passe quelque chose
d'intéressant, avant d'investir plus de calcul sur un petit nombre de
cellules.

Avant de lancer cette exploration, des **critères numériques précis**
ont été fixés à l'avance (avant de voir le moindre résultat) pour
décider si un effet observé peut être qualifié de « robuste » — un
garde-fou classique contre le biais qui consiste à ajuster une
conclusion après coup pour qu'elle colle aux données. Une **campagne de
confirmation**, en cours au moment de la rédaction, applique ces
critères sur un petit nombre de cellules choisies dans l'exploration,
avec 5 graines **nouvelles** (10 à 14, jamais vues pendant
l'exploration) — précisément pour empêcher de choisir a posteriori les
graines qui arrangent le résultat.

## 3. Repères : ce que mesurent les grandeurs citées plus loin

- **K0** : le capital de départ d'une entité nouvellement créée.
- **K\*aut** : le capital vers lequel une entité isolée (sans jamais
  emprunter ni prêter) convergerait naturellement à long terme, calculé
  à partir des équations de production/dépréciation du modèle. C'est
  une échelle de référence : ce qui compte pour la dynamique n'est pas
  la valeur brute de K0, mais son rapport à K\*aut (est-on loin ou
  proche de l'échelle naturelle de l'entité ?).
- **γ** : la concavité de la fonction de production — à quelle vitesse
  les rendements du capital diminuent. γ petit = rendements fortement
  décroissants ; γ proche de 1 = rendements presque linéaires.
- **η** (« eta ») : le nombre de tentatives d'appariement emprunteur/
  prêteur à chaque pas de temps — l'intensité d'activité du marché du
  crédit. Deux familles sont testées : une famille **linéaire** (le
  nombre de tentatives est proportionnel à la population active, avec
  un facteur ρ ; ρ=1 est la référence historique) et une famille **non
  linéaire** (exposant β autour d'une population de référence).
- **δ, σ** : δ est le taux de dépréciation du capital à chaque pas ; σ
  est l'amplitude des chocs aléatoires individuels sur la production.
  Ensemble, ils fixent la « vitesse » et le « bruit » de l'économie.
- **Mécanisme deg\_out / rq** (établi lors d'une phase antérieure) : la
  dispersion du revenu d'intérêt entre entités se décompose en une part
  due au **nombre de contrats de prêt actifs accumulés** (« deg\_out »,
  un effet de quantité) et une part due au **taux × montant remboursé
  par contrat** (« rq », un effet de prix). En baseline, environ 77 %
  de la dispersion vient du nombre de contrats, 23 % du prix par
  contrat.
- **α̂ (alpha estimé) et stabilité de seuil** : α̂ est l'exposant ajusté
  d'une loi de puissance sur la queue de la distribution des revenus.
  Un ajustement de queue nécessite de choisir un seuil au-delà duquel
  les données sont considérées comme « la queue » ; la **stabilité de
  seuil** consiste à refaire l'ajustement avec un seuil deux fois plus
  bas et à vérifier que α̂ ne bouge pas de plus de 20 % — sinon, la
  « queue Pareto » n'est qu'un artefact du choix de seuil, pas un vrai
  trait des données.
- **n\_tail** : le nombre de points de données effectivement utilisés
  pour l'ajustement de la queue — trop peu de points rend l'exposant
  peu fiable.
- **Test de Vuong** : un test statistique qui compare deux modèles de
  distribution concurrents (ici, loi de puissance contre exponentielle,
  ou loi de puissance contre lognormale) et indique lequel est mieux
  supporté par les données.
- **τ̂ (tau estimé) et rapport de branchement** : τ̂ est l'exposant de
  loi de puissance ajusté sur la taille des avalanches de faillites. Le
  rapport de branchement est le nombre moyen de faillites supplémentaires
  déclenchées par une faillite donnée — plus il est proche de 1, plus
  la dynamique de cascade est proche d'un régime critique auto-entretenu.
- **Plancher de renouvellement** : on repère les entités dans le
  décile le plus riche (top 10 % en capital ou en revenu) au début
  d'une fenêtre d'observation, puis on mesure quelle fraction de ce
  groupe initial est *encore* dans le top 10 % en fin de fenêtre. Un
  plancher proche de 0 signale un renouvellement total de l'élite
  (grande mobilité) ; proche de 1, une élite figée.

## 4. Les critères de confirmation, fixés avant tout résultat

Une queue Pareto des revenus d'intérêt sera qualifiée de robuste pour
une cellule si, sur au moins 3 des 5 graines de confirmation :

1. **Stabilité de seuil** (définie au §3) : écart de moins de 20 %
   relatif entre α̂ au seuil optimal et α̂ à seuil moitié.
2. **Au moins 100 points** dans la queue en moyenne par instantané.
3. **Signe et ampleur de l'effet cohérents** entre les graines, pas
   seulement en moyenne.
4. **Le test de Vuong favorise la loi de puissance** dans la majorité
   des instantanés (contre l'exponentielle et contre la lognormale).
5. **L'effet ne se réduit pas** à un simple changement d'inégalité
   globale (indice de Gini) ou au seul mécanisme de quantité de
   contrats (deg\_out) — il doit s'agir d'un vrai changement de forme
   de la queue.

Un exposant d'avalanche sera qualifié d'indépendant de la taille du
système si : l'ajustement détecte une vraie coupure finie (pas de
saturation contre une borne numérique de l'algorithme) sur toutes les
tailles testées ; τ̂ varie de moins de 15 % relatif entre les tailles de
population les plus petites et les plus grandes ; le rapport de
branchement reste stable à ±0,05 près sur la même plage.

**Aucun chiffre de ce document n'a encore été confronté à ces
critères** — c'est l'objet de la campagne de confirmation en cours.

---

## 5. Le résultat le plus robuste de l'exploration : l'objectif A échoue presque partout

La fraction d'instantanés satisfaisant le critère de stabilité de seuil
(§4, critère 1) est **quasi nulle sur 28 des 29 cellules** du grid —
autrement dit, la queue Pareto n'est stable au changement de seuil dans
(quasi) aucun instantané, quelle que soit la cellule testée.

**Fait observé** : c'est le résultat le plus solidement établi de toute
la campagne — une régularité sur 87 runs couvrant K0 (facteur 2000), γ
(brut et compensé, voir §7), η linéaire (facteur 32), η non linéaire, δ
et σ conjoints, et un réglage institutionnel de comparaison.

Seule exception : la cellule à δ=σ=0,10 atteint 9,2 % — toujours loin
d'une majorité d'instantanés stables, mais un ordre de grandeur
au-dessus de tout le reste du grid (détail au §9).

## 6. K0 : le mécanisme deg_out se confirme, mais pas de façon monotone simple

| K0 | α̂ | n\_tail/instantané | rapport de branchement | population finale | plancher de renouvellement |
|---|---:|---:|---:|---:|---:|
| 1 | 3,59 | 105 | 0,588 | 387 | **0,000** |
| 5 | 4,08 | 119 | 0,709 | 620 | 0,022 |
| 25 (baseline) | 3,78 | 252 | 0,786 | 1147 | 0,088 |
| 100 | 3,51 | 500 | 0,795 | 1978 | 0,201 |
| 500 | 3,10 | 1330 | 0,746 | 3852 | 0,509 |
| 2000 | **2,79** | 3314 | 0,655 | 7247 | **0,796** |

α̂ décroît globalement avec K0 (queue plus lourde à K0 élevé, cohérent
avec le mécanisme deg\_out : plus de population, plus de contrats
accumulés possibles), mais pas monotoniquement (bosse à K0=5). Le
rapport de branchement est **en cloche** (pic à K0=100), pas monotone
non plus — une nuance par rapport à l'idée d'un effet K0 simple sur la
criticalité des avalanches.

Le changement le plus spectaculaire est ailleurs : le **plancher de
renouvellement** passe de 0,000 (K0=1 : l'élite du décile supérieur se
renouvelle entièrement) à 0,796 (K0=2000 : l'élite est quasi figée).
**Inférence** : K0 contrôle autant la mobilité sociale de long terme
que la forme de la queue instantanée des revenus — deux effets à ne pas
confondre.

K0=1 et K0=2000 sont les deux extrêmes retenus pour la confirmation.

## 7. γ : l'effet réel n'apparaît qu'une fois l'échelle contrôlée

| γ | α̂ (K0=25 fixe) | α̂ (K0 compensé pour tenir K0/K\*aut constant) |
|---|---:|---:|
| 1/3 | 3,80 | **4,86** |
| 0,4 | 3,81 | **4,34** |
| 0,5 (baseline) | 3,78 | 3,78 |
| 0,6 | 3,74 | **3,48** |
| 2/3 | 3,35 | **3,31** |

À K0 fixe, la branche est quasi plate : K0=25 représente une fraction
très différente de K\*aut(γ) selon γ (985 à γ=1/3 contre 970 299 à
γ=2/3), ce qui confond l'effet d'échelle (distance à K\*aut) avec
l'effet de courbure proprement dit. Une fois K0 ajusté pour tenir ce
rapport constant, la décroissance de α̂ avec γ devient nette et quasi
monotone (4,86 → 3,31).

**Inférence, exploration seule** : plus la production est concave (γ
petit), plus la queue des revenus est légère ; plus elle est proche de
la linéarité (γ grand), plus elle s'alourdit. C'est le signal le plus
net et le plus propre de toute la campagne pour un paramètre autre que
η — mais la branche « K0 compensé » n'était pas dans la sélection
initiale de confirmation (voir §10), ajoutée depuis en complément.

## 8. η : le levier le plus systématique du grid — linéaire fort, non linéaire nul

Famille linéaire (η proportionnel à la population, facteur ρ) : effet
le plus net sur tous les diagnostics mesurés, dans le sens attendu.

| ρ | α̂ | τ̂ | rapport de branchement | Vuong vs exponentielle (fraction d'instantanés favorisant Pareto) |
|---|---:|---:|---:|---:|
| 0,125 | 4,20 | 1,84 | 0,480 | 0,10 |
| 0,25 | 4,09 | 1,89 | 0,584 | 0,57 |
| 1 (baseline) | 3,78 | 1,41 | 0,786 | 1,00 |
| 2 | 3,93 | 1,17 | 0,854 | 1,00 |
| 4 | 4,05 | 0,99 | 0,891 | 1,00 |

**Fait observé** : à ρ=0,125 et 0,25, le test de Vuong favorise
l'**exponentielle** sur la loi de puissance dans la majorité des
instantanés (seulement 10 %/57 % en faveur de Pareto) — un marché de
crédit clairsemé ne produit quasiment jamais une queue Pareto-compatible,
même ponctuellement. Les deux extrêmes (ρ=0,125 et ρ=4) sont dans les
cellules de confirmation.

Famille non linéaire (exposant β entre 0,5 et 1,5 autour d'une
population de référence) : **aucun effet mesurable** sur α̂
(3,78-3,84), τ̂ (1,42-1,44), rapport de branchement (0,785-0,789) ou
population finale (1070-1170). Résultat négatif propre, mais valable
uniquement sur la plage testée : rien n'indique ce qui se passerait
en dehors de β∈[0,5 ; 1,5].

## 9. δ et σ conjoints : le seul endroit où l'objectif A progresse un peu — au prix de l'objectif B

| (δ,σ) | α̂ | stabilité de seuil (fraction d'instantanés) | rapport de branchement | τ̂ |
|---|---:|---:|---:|---:|
| (0,01 ; 0,01) baseline | 3,78 | 0,004 | 0,786 | 1,41 |
| (0,02 ; 0,02) | 3,55 | 0,011 | 0,709 | 1,52 |
| (0,05 ; 0,05) | 3,19 | 0,011 | 0,547 | 1,71 |
| (0,10 ; 0,10) | 3,04 | **0,092** | **0,385** | 1,82 |
| (0,05 ; 0,25) — régime historique bruité | 4,40 | 0,000 | **0,357** | 1,97 |

À mesure que δ et σ augmentent ensemble, le rapport de branchement
**s'effondre** (0,786 → 0,385, plus de moitié perdu) et τ̂ s'alourdit
(avalanches moins critiques). Dans le même mouvement, la stabilité de
seuil progresse légèrement — c'est la seule branche du grid où elle
bouge de façon notable.

**Hypothèse, exploration seule** : compromis direct entre les deux
objectifs sur cette branche — davantage de bruit individuel semble
aider marginalement à stabiliser la queue des revenus, mais au prix
d'une nette dégradation de la criticalité des avalanches. Non confirmé
au moment de la rédaction ; cette cellule a été ajoutée en complément à
la confirmation (voir §10).

## 10. Une limite identifiée dans le choix des cellules de confirmation

Trois façons de choisir les cellules à confirmer étaient possibles au
sortir de l'exploration : la taille de l'effet sur le mécanisme de prix
(rq, voir §3), la stabilité de seuil elle-même, ou un comportement
d'avalanche particulièrement intéressant. La sélection initiale n'a
utilisé que le premier critère. Deux cellules ressortaient nettement
sur les deux autres et n'étaient pas dans les 6 retenues :

- la cellule δ=σ=0,10 — seule cellule à sortir du bruit sur la
  stabilité de seuil elle-même (§9) ;
- la branche γ compensée — effet le plus propre sur γ une fois
  l'échelle contrôlée (§7).

Décision prise : ne pas modifier les 6 cellules déjà lancées en
confirmation (les changer après coup reviendrait à sélectionner a
posteriori les résultats qui arrangent), mais lancer ces cellules
supplémentaires **en complément**, sur un lot de calcul séparé,
décidé avant tout résultat de confirmation — à rapporter séparément
dans le rapport final pour ne pas mélanger les deux sélections.

## 11. Ce qui reste strictement en attente de la confirmation

- Le critère 3 (§4) — cohérence du signe et de l'ampleur sur au moins 3
  graines **différentes de celles de l'exploration** — ne peut par
  construction pas être évalué avec les seules données d'exploration :
  c'est l'objet même de la confirmation.
- Le critère 2 (§4, au moins 100 points de queue en moyenne) est
  globalement satisfait, mais tout juste sur K0=1 (105) et sur la
  cellule γ=2/3 (104), deux des cellules en confirmation — à surveiller
  sur les nouvelles graines.
- Le critère 5 (§4, l'effet ne se réduit pas à l'inégalité globale ou
  au seul mécanisme de quantité de contrats) n'a pas encore été vérifié
  systématiquement sur les cellules retenues ; à faire une fois la
  confirmation terminée.

## À ne pas citer comme conclusion

Aucun chiffre de ce document n'a passé les cinq critères de robustesse
du §4. Le statut correct de toute affirmation ci-dessus est « observé
sur les graines d'exploration, non confirmé ».
