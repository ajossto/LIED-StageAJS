# Note De Reponse Aux Critiques — Round 3

Date: 2026-04-09

Cette note accompagne la review:
- `review_round3_formal_regimes.txt`

et propose des pistes de resolution pour le round suivant.

## Synthese des critiques recues

Le relecteur valide les corrections des rounds 1-2 (SOC abandonnee, separation flux/stocks, metriques de propagation, cohorte clarifiee) mais identifie un probleme central : **le rapport round 3 ne derive aucune prediction analytique**. La carte de parametres est empirique, les coefficients du champ moyen ne sont pas calibres, et la connexion formelle (k, theta, lambda) --> observables n'existe pas.

Trois derivations concretes sont demandees :
1. beta_k (taux de matching) au premier ordre ;
2. calibration du hazard h* et du point fixe ;
3. estimation numerique de rho(B_t).

## Reponse point par point

### A1. Aucune prediction analytique derivee

Statut : accepte comme critique principale.

La distinction entre « cartographie empirique des regimes » et « modelisation predictive » est juste. Le rapport round 3 releve de la premiere categorie.

Action proposee :
- reformuler l'objectif comme cartographie empirique guidee par la theorie ;
- ajouter au minimum une derivation de beta_k et une calibration du point fixe (N*, m*) ;
- reserv le mot « predictif » aux resultats qui derivent effectivement d'une formule fermee testee contre les donnees.

### A2. beta_k derivable mais jamais derive

Statut : accepte. C'est la piece manquante la plus accessible.

Le relecteur a raison de noter que le mecanisme de matching (echantillonner 2k, trier, scinder, tirer) est suffisamment simple pour une analyse au premier ordre. La probabilite de transaction par tentative depend de :
- P(r*_b > r*_l | tirage dans un pool de 2k) -- derivable de la distribution des r* ;
- P(offre > 0) -- depend de la distribution de L - reserve ;
- P(gain ok) et P(dette ok) -- conditions additionnelles filtrantes.

Piste de derivation :
- Si les r* suivent une distribution F a support [r_min, r_max], alors pour un pool de taille 2k tire uniformement, la probabilite que le preteur (tire dans la moitie basse) ait un r* inferieur a l'emprunteur (tire dans la moitie haute) depend des statistiques d'ordre de F.
- Pour k=1 : matching entre les deux extremes --> une seule paire, probabilite de reussite elevee mais aucun intermediaire.
- Pour k >= 3 : le pool est assez large pour que des entites medianes apparaissent dans les deux roles sur des pas differents, creant le graphe d'intermediation.
- Le seuil critique correspond au point ou le degre moyen de sortie (out-degree) depasse 1, permettant la percolation de cascades.

### A3. Fragilite cachee non fermee

Statut : la fermeture amelioree proposee par le relecteur est correcte et devrait etre integree.

La distribution geometrique des ages P(a) ~ (1-delta_exo)^a donne :

  H_t ~ delta_exo * M_t * q_bar * sum (1-delta_exo)^{2a}
       = delta_exo * M_t * q_bar / (1 - (1-delta_exo)^2)

Avec delta_exo = 0.1, le facteur correctif est 1/0.19 = 5.26.

A confronter au ratio observe de 0.894 en fenetre tardive. Si le ratio de fragilite est defini comme H_t / (volume nominal total), la fermeture predit une valeur qui depend aussi du rapport q_bar * M_t / volume_nominal.

Action proposee : deriver cette expression, la calibrer sur les donnees de reference, et la comparer au ratio mesure.

### A4. Critere spectral vide

Statut : accepte comme point toujours ouvert.

Le relecteur a raison de noter que l'estimation de rho(B_t) est faisable numeriquement. La matrice B_t a pour entrees :

  b_{ij} = 1_{i prete a j} * min(1, q_{ij} / NW_j)

et son rayon spectral peut etre estime par la methode des puissances.

Difficulte pratique : a ~4000 prets actifs et ~600 entites, la matrice est 600x600 et sparse. C'est parfaitement tractable.

Action proposee : implementer l'estimation de rho(B_t) dans le code d'analyse et la tracer sur la run de reference.

### B1. Seulement 2 seeds par configuration

Statut : accepte. La critique sur les intervalles de confiance est justifiee.

Avec df = 1, le facteur t de Student a 95% est 12.71 et non ~2. Les ecarts-types presentes sont donc trompeurs comme estimateurs d'incertitude.

Action proposee : augmenter a 10-20 seeds par configuration pour les points cles de la carte (k=3, theta = {0.35, 0.5, 0.7}, lambda = {1, 2, 3}).

### B2. La population decline dans le « quasi-regime »

Statut : accepte. La pente de -0.304 entites/pas est significative.

Sur 500 pas, cela represente ~152 entites perdues, soit ~26% de la population moyenne. Ce n'est pas un quasi-regime pour N. Les consequences :
- les ratios « par entite » (prets/entite) augmentent mecaniquement ;
- le vieillissement du portefeuille amplifie la fragilite cachee ;
- le regime observe est transitoire, pas asymptotique.

Action proposee :
- mentionner explicitement la derive negative de N ;
- tester si lambda > 2 stabilise la population ;
- alternativement, tester si tau > 0 stabilise M et indirectement N (en reduisant la fragilite).

### B3. Incoherence batch long / sweep

Statut : a verifier. La divergence (4266 prets actifs vs ~2591) peut venir de seeds differentes et de la faible statistique (4 vs 2 seeds).

Action proposee : harmoniser les seeds et presenter les resultats de facon coherente.

### B4. Figures non lisibles dans le tex

Statut : mineur, corrigeable.

### C1. Gamma_t abandonne sans remplacement

Statut : accepte. Un diagnostic directionnel est necessaire.

Action proposee : definir un Gamma_t corrige :

  Gamma_t = Pi_eff(p_t) - delta_L * ell_t - X_t + epsilon_t^ell

et le mesurer sur les donnees pour verifier qu'il oscille autour de zero en regime tardif.

### C2. Analogie feu de foret non formalisee

Statut : accepte. L'analogie est evocatrice mais dangereuse sans formalisation.

Differences fondamentales avec Drossel-Schwabl :
- DS a une topologie fixe (grille), le WIP a un graphe dynamique ;
- DS a un seul parametre critique (f/p), le WIP en a trois (k, theta, lambda) ;
- DS produit une vraie SOC dans la limite f/p --> 0, le WIP n'a pas de separation d'echelles prouvee.

Action proposee : soit formaliser l'analogie en identifiant explicitement les correspondances et les ecarts, soit la retirer du discours.

### C3. Definition de G_t ambigue

Statut : corrigeable. G_t = nombre d'entites insolvables (A_i + epsilon < P_i^bilan) au debut de la resolution, avant propagation.

### C4. Errata v2 incomplets

Statut : le fichier paper_v2_baseline.tex contient toujours la phrase contradictoire en Section 4. A corriger.

### C5. Notation F_t surchargee

Statut : corrigeable. Distinguer F_t (nombre de faillites du pas) et phi_i (perte individuelle de contrepartie).

## Ce qui est maintenant resolu (cumulatif rounds 1-3)

- contradiction sur Delta NW : corrigee ;
- vocabulaire SOC : abandonne ;
- confusion proxy/rayon spectral : levee ;
- non-stationnarite : documentee et separee flux/stocks ;
- cohorte : definie et de-priorisee ;
- terme +iota m : remplace par epsilon_t^ell ;
- carte de parametres : fournie (empirique) ;
- incoherence Gamma_t : supprimee (mais Gamma_t abandonne — a remplacer).

## Ce qui reste ouvert (cumulatif)

1. **beta_k** : deriver le taux de formation de credit en fonction de k et de la distribution des r* ;
2. **Calibration du champ moyen** : estimer h*, eta, kappa_* sur les donnees pour produire une prediction de point fixe ;
3. **rho(B_t)** : estimer numeriquement le rayon spectral de la matrice de reproduction ;
4. **Fermeture de H_t** : integrer la correction facteur d'age derive par le relecteur ;
5. **Stationnarite de N** : la population decline dans le « quasi-regime » — tester lambda > 2 ou tau > 0 ;
6. **Statistique** : augmenter le nombre de seeds a >= 10 pour les configurations cles ;
7. **Analogie feu de foret** : formaliser ou abandonner ;
8. **Gamma_t** : restaurer un diagnostic directionnel calibre.

## Priorites pour le round suivant

Par ordre d'impact decroissant :

1. **Deriver beta_k** — c'est la brique formelle la plus urgente et la plus accessible ;
2. **Estimer rho(B_t)** — ancre le critere de propagation dans les donnees ;
3. **Calibrer le point fixe** — transforme le champ moyen en outil predictif ;
4. **Augmenter les seeds** — credibilise les resultats empiriques.

## Conclusion

La critique du round 3 est constructive et cible le bon probleme : le modele formel n'est pas encore predictif. Les donnees empiriques sont de bonne qualite (sous reserve d'augmenter les seeds), la comprehension qualitative est solide, mais la boucle theorie --> prediction --> verification n'est pas fermee. Le round suivant devrait se concentrer sur les trois derivations demandees (beta_k, calibration point fixe, rho(B_t)) plutot que sur des corrections de detail.
