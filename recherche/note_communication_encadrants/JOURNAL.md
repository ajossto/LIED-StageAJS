# Journal — note de communication aux encadrants

## 2026-09-14 — intégration du questionnaire répondu et vérification finale

Les deux questionnaires répondus ont été incorporés et sont conservés intacts.
Le rapport conserve raisonnement, impasses et résultats négatifs ; le
proto-article frère est centré sur les résultats et questions ouvertes. Le
résultat directeur est la réponse collective à la technologie, le partage
venant ensuite. Les PDF ne dépendent plus de la lecture des questionnaires.

**Fond.** Développement autonome stock/flux, joule/puissance, bilan réel/nominal,
réservoir extérieur et adimensionnement par Kaut. Distinction du point fixe
déterministe et de l'équilibre bruité, de la tension Kaut/Keq et de la chaîne
complète. Comparaisons de quantiles sans cohorte fixe ; stabilité de Gini sans
invariance universelle. Pondération par surplus distinguée de sa causalité
démographique. Pareto reste ouvert, et la cible exponentielle imposée est
abandonnée. Perspectives précisées : causalité entre pas, hétérogénéité jointe
(K0, A, gamma), naissance dépendante de l'état, sur-altruisme non implémenté.
Contribution humaine et usage des outils explicités sans inventer de souvenirs.

**Corrections numériques.** Même estimateur d'élasticité finie, même fenêtre
3000 < t <= 4000 et choc A × 1,5 : v1, toutes entités, 0,7560 ± 0,0203 ;
entrantes, 0,7639 ± 0,0269 (IC95, cinq graines). M4.4 : respectivement
0,7473 ± 0,0106 et 0,7495 ± 0,0147 (douze graines). L'ancienne comparaison
0,765 ± 0,008 ne correspondait pas au protocole annoncé. Rapports de quantiles
et de partage recalculés graine par graine ; tableaux générés. Les dispersions
historiques des contractions M4B sont des écarts-types, non les nouveaux IC95.

**Figures.** Onze compléments reproductibles, dont les régressions descriptives
de cascades demandées avec incertitudes. La pente d'une survie ajustée n'est
pas assimilée à l'exposant de densité de Pareto. Régressions de rho par graine,
sans segments entre niveaux. Deux erreurs de la figure de suffisance corrigées :
la perte vient d'une créance sur une débitrice défaillante ; le choc est
concentré. Son histogramme donne des fractions par classe, pas une densité.
Le diagnostic de Vuong a été redessiné pour éviter les titres superposés ;
σ=10 reste un seuil de diagnostic, non une frontière mathématique de validité.

**Traçabilité et bibliographie.** Annexes autonomes pour les 51 figures du
rapport et les 19 de l'article ; 372 identifiants M4.4, 31 groupes de
configurations, 110 empreintes sources. Les paramètres manquants des douze
métadonnées coverage/burn restent signalés. Références bibliographiques
ciblées normalisées, versions séparées des dates de publication ; portée du
contrôle détaillée dans `../revision_documents/REFERENCES_VERIFIEES.md`.

**Contrôles exécutés.** Rapports de quantiles et élasticités avec IC95
recalculés depuis les exports ; empreintes, copies, identifiants et inclusions
contrôlés ; neuf vérifications de point fixe et d'adimensionnement. Les quatre
tests de figures du projet M4.4 passent (29 annotations confrontées aux macros).
Deux PDF compilés : rapport 80 pages, article 20 pages. Compilation également
réussie pour chacun dans un dossier temporaire contenant seulement ses sources
LaTeX et figures, sans référence indéfinie ni débordement. Inspection des
planches couvrant toutes les pages, complétée par des vues agrandies des nouveaux
graphiques et pages modifiées. Avertissements de justification et substitution
de fonte subsistent ; pas de certification de chaque détail typographique.

**Limites.** Aucune campagne ni aucun moteur modifié, aucune simulation relancée.
Les tests de parité historiques n'ont pas été rejoués dans cette passe.
L'installation depuis un environnement vierge et la validation empirique ne
sont pas établies. Les contrôles ci-dessus ne sont pas une preuve de chaque
énoncé historique du dépôt. Reprise et commandes dans `REPRISE.md` et
`../revision_documents/README.md`.

## 2026-09-14 — première intégration de l'audit répondu

Anatole a validé les corrections de l'audit et autorisé les nouveaux calculs
utiles. Il confirme deux documents frères distincts : proto-rapport du
raisonnement ici, proto-article des conclusions dans `../note_resultats/`.
Le questionnaire temporaire est encore en cours de lecture ; aucune de ses
inférences n'est considérée comme approuvée par défaut. Les deux fichiers de
relecture restent intacts.

**Modifications.** Point fixe corrigé et vérifié sur trois configurations ;
marché historique distingué du sens libre et de l'intensité M4.4 ; branchement
endogène sans plafond universel ; comparaison erronée des élasticités retirée ;
Lorenz capital/intérêts distingué de capital/valeur nette ; portée réelle des
macros explicitée ; excès d'arêtes distingué de multiplicité/suffisance ;
appariement limité à la garantie effective à la bifurcation. Première
harmonisation des formulations sur le rebond, les quantiles, la stationnarité,
les queues, la covariance d'échelle et l'identité de pondération.

**Transmission.** README racine, CODEX et index recherche actualisés ; fonction
des documents explicitée. Le collecteur déduit la racine depuis son propre
emplacement. `REPRISE.md` décrit compilation, données et travaux encore ouverts.

**Contrôles.** Syntaxe et résolution des chemins du collecteur vérifiées sans
exécuter sa synchronisation ; 47 copies comparées aux sources par SHA-256,
toutes identiques. `git diff --check` sur les fichiers édités : sans erreur.
Compilation LaTeX réussie (71 pages), sans référence indéfinie ni demande de
nouvelle passe dans le dernier journal ; les contrôles de rendu détaillés et les
avertissements typographiques restent à traiter. Aucun moteur modifié, aucune
campagne relancée, aucun résultat numérique remplacé. La réconciliation
statistique v1/v2, les figures de stock total, les configurations de référence
et la bibliographie ne sont pas encore terminées.

## 2026-08-25 — rédaction de la note

**Objet.** Note autonome sur l'état d'avancement, articulée sur la question
dorsale : quels phénomènes réels le système d'agents collaboratifs retrouve-t-il,
et reproduit-on quelque chose qui s'identifie à l'effet rebond ?

**Livré.** 71 pages, 47 figures, 0 erreur LaTeX, 0 référence indéfinie.
Sept parties retravaillables indépendamment, quatre annexes.

### Vérification faite avant d'écrire

**Chaîne de parité rejouée en entier.** Les sept tests reliant
M4 → M4B → M4.2 → M4.2B → M4.3 → M4.3Live → M4.4 ont été relancés (cinq en
parallèle, six cœurs sur huit). Tous verts :

| passage | tolérance | durée |
|---|---|---|
| M4 → M4B | exacte | 11 s |
| M4B → M4.2 (γ=1/2, A=1) | 10⁻⁹, mesuré à 5,7·10⁻¹³ | 84 s |
| M4.2 → M4.2B (géométrique) | 10⁻⁹, mesuré à 0 | 181 s |
| M4.2B → M4.3 (deux institutions) | exacte | 445 s |
| M4.3 → M4.3Live (homogène) | bit à bit | 59 s |
| M4.3 → M4.4 (homogène, 8000 pas) | bit à bit | 763 s |
| M4.3Live-v1 → M4.4 (sens hérité) | bit à bit | 92 s |

C'est ce qui autorise la note à hériter des résultats anciens : chaque moteur
**contient** le précédent comme cas particulier, par identité de trajectoire.
Le seul maillon non bit-à-bit est documenté (formes génériques contre formes
spécialisées, écart d'un dernier bit ; le discret est identique).

**Nombres hérités confrontés à leurs sources primaires**, pas au mémo narratif :

- tableau de référence M4B (12 valeurs) → `sensibilite_m4b/report/rapport_final.tex`,
  table « Le centre de campagne » ✓
- Gini de valeur nette 0,435 ± 0,006 → même fichier, ligne 627 ✓
- bloc rebond M4.3Live (+36,1 ± 0,4 %, E=0,72, ε=0,76, ×1,80, ×0,754, E=2,53,
  ε=2,02, E∈[2,3;2,9]) → `m4_3live_credit_soc/report/rapport_final.tex` ✓
- bloc cycles sur l'énergie (252,4 ± 4,4 ; 1,930 ± 0,042 ; −0,233 ± 0,021 ;
  PRCC +0,983 et −0,801) → `sensibilite_m4b/JOURNAL.md`, entrée du 27 juillet,
  et `results/summary/cycles_*.csv` ✓

### Trois défauts trouvés en route

1. **Cinq figures incluses sans exister.** Le texte citait `f11_couverture`,
   `f16_bargain_systeme`, `f17_rho_controle`, `f18_rotation_rho` et
   `f20_rampes`, absentes du catalogue de `collect_figures.py`. Corrigé, et
   `collect_figures.py` porte désormais le garde-fou : « toute inclusion doit
   exister, toute figure copiée doit servir ». Même rôle que
   `tests/test_figures.py` dans les programmes de campagne.

2. **Cinq erreurs LaTeX invisibles.** Caractères Unicode non déclarés (`∝`,
   `−`, `½`) et un `^` lu comme exposant mathématique hors mode math, dans les
   légendes engendrées. La fonction d'échappement du générateur n'échappe
   désormais **que hors des segments `$…$`**, ce qui permet d'écrire de vraies
   mathématiques en légende sans casser les soulignés.

3. **Discordance d'observable sur les récessions.** Les chiffres publiés
   portent sur l'énergie totale `E_t = Σ K_i` ; les figures `p09` et `p10` de
   la campagne M4B sont tracées sur la **production totale**. Le journal de la
   campagne le disait : « une figure énergétique dédiée reste à produire ».
   Signalé dans les deux légendes, avec le chiffre de production (487 épisodes
   par millier de pas) pour que les figures aient leurs propres nombres.
   Consigné en Q10 de `QUESTIONS.md`.

### Deux valeurs coexistantes, réconciliées plutôt que masquées

- **ε = 0,7473 (v2, 12 graines) contre ε = 0,76 (v1, 5 graines)** pour la même
  configuration : note de bas de page sous le tableau du volet rebond.
- **b₁ = 0,2968 (M4B) contre 0,7863 (M4.4)** : l'ablation ferme 87,8 % de
  l'écart, le reliquat est imputé sans vérification au bassin d'appariement.
  Note de bas de page au point où le second nombre apparaît.

### Conformité aux consignes du projet

- **Autonomie** : section « Définitions » — 9 paramètres, 9 observables,
  19 termes internes, tous définis avant emploi.
- **Sources** : chaque valeur héritée porte son fichier et sa section ;
  les 268 macros de M4.4 sont **copiées**, pas retapées.
- **Traçabilité par `run_id`** : annexe engendrée rattachant les 47 figures à
  8 origines. Une figure agrégeant une campagne renvoie à l'annexe engendrée de
  celle-ci (693 lignes pour M4B, 372 pour M4.4) plutôt que de porter un faux
  identifiant unique.
- **Reproductibilité** : `scripts/collect_figures.py` reconstruit figures,
  provenance, traçabilité et macros ; deux passes `pdflatex` suffisent.
- **Bibliographie** : 15 entrées, chacune avec ce qu'elle établit **et ce
  qu'elle n'établit pas**. Deux ne sont pas encore normalisées au registre
  (Sorrell–Dimitropoulos, Wildauer–Heck) — signalé.

### Questions ouvertes

Onze, dans `QUESTIONS.md`, chacune avec l'hypothèse provisoire retenue pour que
la note soit complète sans la réponse. Les trois de fond : le sens à donner au
mot « tension » (Q1), la figure énergétique manquante (Q10), et laquelle des
deux mesures de ε publier (Q11).
