
---

## 22 août 2026 — lot F : ce qui détermine la rotation du crédit

### La décomposition (aucun calcul neuf)

Sur **322 runs** des deux lignées, la rotation se décompose en trois facteurs
dont le produit est une identité (vérifiée à 4,4·10⁻¹⁶, ce qui est ce qu'on
attend d'une identité et ne prouve rien) :

- `f₁ = rondes/entité` vaut ρ à **0,095** près — c'est l'effet de la partie
  entière ⌊ρN⌋/N, purement combinatoire ;
- `f₂ = prêts conclus/rondes` est compris entre **0,9944 et 0,9999** ;
- **toute la variation est donc dans f₃**, le transfert moyen rapporté au
  capital moyen.

### Le résultat : f₃ EST le coefficient de Gini

En régime homogène δ = (K_b − K_a)/2, donc E|δ| = ½·E|X−Y| = K̄·G où G est le
Gini — **par sa définition même**. Donc `rotation = ρ·G`. La rotation du crédit
n'est pas une grandeur de crédit : c'est l'inégalité des capitaux multipliée
par le taux d'appariement.

Une correction est nécessaire et elle est mesurée : chaque ronde **égalise** la
paire, donc le Gini décroît pendant la phase de marché. La quantité pertinente
est la moyenne logarithmique Ḡ entre le Gini d'avant et celui d'après.

Balayage instrumenté : 33 runs de 2500 pas (1452 s), un paramètre à la fois
(λ, ρ, σ, K₀, δ), Gini enregistré avant et après la phase de marché.

| relation | exposant | R² | n | étendue |
|---|---|---|---|---|
| **f₃ ~ Ḡ** | **0,9858** | **0,9998** | 33 | ×2,6 |
| f₃ ~ G avant marché | — | — | 33 | biais médian **−17,7 %** |
| rotation ~ ρ·CV prédit | 0,872 | 0,837 | 33 | ×2,1 |

Écart médian entre f₃ et Ḡ : **+0,5 %** (étendue +0,09 % à +2,1 %). La
relation n'est pas ajustée, elle est dérivée, et la mesure la confirme.

### La fermeture : un échec documenté

Le bilan de variance prédit CV² ≈ [(λ/N)(1−K₀/K̄)² + σ²]/ρ et donc
rotation ≈ ρ·CV/√π. L'ordre de grandeur est bon (écart médian −19,1 %), mais
**le contrôle §14.2 invalide l'ajustement groupé** :

| levier | exposant | R² | étendue de x | lecture |
|---|---|---|---|---|
| ρ | 0,595 | 1,0000 | ×2,13 | exploitable |
| K₀ | 1,378 | 1,0000 | ×1,73 | exploitable |
| σ | 1,410 | 0,9984 | ×1,08 | étendue trop faible |
| λ | 0,506 | 0,391 | ×1,01 | étendue trop faible |
| δ | 8,272 | 0,956 | ×1,01 | étendue trop faible — c'est du bruit |
| **groupé** | **0,872** | **0,837** | ×2,1 | — |

Trois familles sur cinq couvrent une étendue de x inférieure à 10 % : leur
exposant ne mesure rien. Des deux familles exploitables, les exposants (0,595
et 1,378) ne coïncident ni entre eux ni avec le groupé. **Le R² groupé reflète
la géométrie du balayage, pas une réponse.** Ce qu'il aurait fallu : un plan
factoriel avec des étendues d'au moins ×3 par levier.

### Un contrôle qui nuance le §4 de ce journal

Le biais résiduel par rapport à la loi `morts/pop ∝ rotation^1,26` est de
**+0,16 %** pour les 117 runs à sens libre et **+0,70 %** pour les 205 runs à
règle ancienne : **en niveau, le levier nouveau ne biaise pas la loi**. Cela ne
contredit pas le facteur 3 à 10 constaté sur la *réponse appariée* — une
régression sur des niveaux couvrant un facteur 5,4 n'a aucune puissance pour
détecter un écart apparié de 16 % sur la rotation. Les deux énoncés sont
rapportés côte à côte dans le rapport, avec cette articulation.

---

## 22 août 2026 — les survivantes, entité par entité

Rejeu du bras `new_A150` sur 3 graines et les deux règles (160 s), avec
contrôle que la trajectoire reproduit la campagne colonne par colonne avant de
lire l'état final.

| groupe | effectif | créancières nettes | revenu d'intérêt | capital moyen | âge médian |
|---|---|---|---|---|---|
| ancienne technologie, sens libre | 7,7 | **95,8 %** | **93,0 %** | 578 | **3998 pas** |
| nouvelle technologie, sens libre | 867 | 30,2 % | 50,8 % | 1125 | 30 pas |
| nouvelle technologie, règle v1 | 827 | 29,9 % | 52,5 % | 1151 | 34 pas |
| ancienne technologie, règle v1 | **0** | — | — | — | — |

Les survivantes détiennent une position nette de l'ordre de **vingt-quatre fois
leur propre capital** et sont **les mêmes depuis le début du run**. C'est
exactement le régime que le programme cherchait à produire, et il n'existe pas
sous l'ancienne règle.

---

## 22 août 2026 — traçabilité et IHM

- **153 runs v2 importés** dans `simulation_lab` (symlink + `run.json` +
  figure `macro_overview.png`), identifiants `m4_3live_v2__*` — aucune
  collision avec les 203 runs v1.
- **Annexe de traçabilité : 156 lignes, 0 sans rôle** (le script refuse de
  produire une annexe incomplète).
- **IHM vérifiée de bout en bout par HTTP** (`tests/test_web_live.py`) :
  serveur démarré, page servie, 8 éléments d'IHM présents, session créée,
  43 pas simulés à 24,9 pas/s, intervention soumise et appliquée avec son
  amplitude exacte enregistrée, fichiers de sortie écrits, IHM v1 intacte.
  **Ce test n'ouvre pas de navigateur** : il vérifie le contrat de données et
  les fichiers servis, pas le rendu graphique. C'est dit tel quel.
- **Un défaut trouvé par ce test et par rien d'autre** : le préfixe des routes
  POST du routeur v2 était resté `["api","live","sessions"]` après le
  renommage vers `/live2`, ce qui rendait toutes les actions de session
  inaccessibles. Les GET fonctionnaient, donc une relecture de page n'aurait
  rien vu.
