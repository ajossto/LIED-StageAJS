# rapport_final.pdf — 28 notes

## [1] page 2  (y=376, obj 302)
rend les rendements *marginaux* décroissants

## [2] page 2  (y=226, obj 482)
"chaque capital est multiplié par eξ avec ξ ∼ N (−σ 2 /2, σ 2 ), un choc multiplicatif
d’espérance 1 (il ne crée ni ne détruit de richesse en moyenne)." : rajouter E(|xi|) pour sigma autour de l'ordre de grandeur utilisée.

## [3] page 2  (y=141, obj 484)
5. Service des intérêts — chaque emprunteuse doit due = k qk rk , somme sur ses contrats
du principal qk fois le taux rk . Si son capital ne suffit pas, elle paie ce qu’elle peut, tombe à
zéro et est marquée en défaut de liquidité.
6. Dépréciation — chaque capital est multiplié par 1 − δ.

Test à faire, échanger 5 et 6, ça devrait faire augmenter le taux de défaut

## [4] page 2  (y=77, obj 486)
"Dans
chaque paire, la plus riche est la prêteuse, la plus pauvre l’emprunteuse ; le prêt ne va jamais
dans l’autre sens"

C'est dommage. Si l'optimisation convexe donne un sens, alors c'est celui ci qui devrait être utilisé. Cette rêgle n'a pas de sens



## [5] page 3  (y=628, obj 488)
"pour K < 1, l’augmenter diminue K γ" ce cas n'arrive jamais

## [6] page 3  (y=281, obj 490)
"Paires où δ ∗ ≤ 0 : l’optimum voudrait faire circuler le capital
du pauvre vers le riche, ce que le sens du prêt interdit. Comp-
teur propre à M4.3Live."

On va derechef faire une autre version ou cette loi est annulée. Abandon de la nomenclature Kl Kb pour lender/borrower, passage à K_a, K_b. 


## [7] page 3  (y=75, obj 492)
"le partage devient pondéré en faveur de la
meilleure technologie."
Il n'y a pas de "meilleure" technologie. 

## [8] page 4  (y=539, obj 494)
fraction (une fraction φ) — une fraction φ des entités vivantes est tirée au sort une fois, et
elle seule est modifiée. La valeur par défaut à la naissance n’est pas touchée : aucune
naissance ne vient reconstituer la cohorte traitée.

Quid de fraction_new ? 

## [9] page 4  (y=288, obj 497)
"Pour une intervention d’amplitude m (rapport entre la pro-
duction d’une entité traitée et celle qu’elle aurait au même capital sans traitement) touchant une
part p de la production agrégée, la réponse strictement proportionnelle est (m − 1) p. On appelle
élasticité normalisée le rapport

E(h) =

prodtraité (h) − prodréf (h) / prodréf (h)
,
(m − 1) p(h)
(3)
avec p(h) mesuré à chaque pas. E > 1 signale une réponse super-proportionnelle (rebond), E < 1
une réponse sous-proportionnelle, E = 1 la proportionnalité exacte."

Retravailler ce paragraphe il n'est pas très compréhensible, donner un exemple, que signifie "h" ?

## [10] page 4  (y=136, obj 499)
"D’abord, tech_series mesure la
part de production après application du levier ; si p est la part ex ante, la part observée vaut
s = mp/(1 + (m − 1)p). On inverse cette relation (p = s/(m − (m − 1)s)) avant tout calcul : utiliser
s directement sous-estimerait l’élasticité de 10 % ici. Ensuite, sur un levier en γ l’amplitude n’est
pas le rapport des exposants mais K ∆γ , qui dépend du capital ; elle est donc mesurée à l’horizon 1
et non imposée."

L'élasticité se mesure en comparant la periode stable  - pré modification - et des periodes, plus ou moins proches du t0 de la modification, plus ou moins étalées.

## [11] page 5  (y=723, obj 501)
"sans remesurer la relaxation (le prompt §7 l’interdit)" On doit la mesurer à postériori pour s'assurer de la qualité de la fenêtre. Erreur lors de la conception du prompt. Problème secondaire, à ne pas corriger absolument.

## [12] page 6  (y=662, obj 504)
"Le bras null lève exactement cette confusion : il tire la même cohorte, dans le même état du
générateur, et ne lui applique rien (la valeur assignée est la valeur courante). C’est la référence
appariée des bras fraction. Les bras all et new, qui ne consomment aucun tirage, sont appariés
au contrôle. Le contraste contrôle ↔ null ne contient aucun traitement : c’est le plancher de
bruit."

Très bien. On explique qu'on vient définir le plancher de bruit. 

## [13] page 6  (y=295, obj 510)
"À l’horizon 1" De manière générale, la réponse à horizon 1 ne nous interesse assez peu. On ne continuera pas les recherches pour cet horizon, mais on garde les résultats déjà obtenus. 

## [14] page 6  (y=287, obj 506)
"À l’horizon 1, les capitaux du bras traité sont encore exactement ceux de sa référence appariée
(l’intervention ne touche que la technologie). L’écart relatif observé doit donc être exactement
l’effet mécanique (m − 1)p. C’est un test, pas un résultat."


Le choc se passe APRES l'action et AVANT la production. l'effet mecanique doit donc être relativement proche (loi des grands nombres), mais potentiellement inégal à seuil calculé

## [15] page 6  (y=188, obj 508)
"Bras
null
frac_A150_phi20
frac_A125_phi20
frac_A150_phi05
frac_A150_phi50
frac_g060_phi20
all_A150
new_A150
écart relatifpart ex anteamplitude mesuréeamplitude imposée
-0,015 %
9,921 %
4,961 %
2,481 %
24,859 %
18,775 %
50,000 %
0,243 %0,0000
0,1984
0,1984
0,0496
0,4972
0,1984
1,0000
0,0049—
1,5000
1,2500
1,5000
1,5000
1,9462
1,5000
1,50001,00
1,50
1,25
1,50
1,50
aucune
1,50
1,50"

Ce tableau est illisible. Il mérite une figure individuelle avec une légende expliquant les colonnes.

## [16] page 7  (y=644, obj 512)
"amplitude reconstruite depuis les agrégats" --> on peut parfaitement calculer l'exacte amplitude en conservant les bonnes données lors de la simulation... Il faut le faire !

## [17] page 7  (y=540, obj 515)
"Le bras γ n’a pas d’amplitude imposée" On peut tout de même obtenir un ordre de grandeur : pour gamma_avant, gamma après, on a Pi_tot=Pop_tot*A*K_eq^gamma_avant
Pi_prédit=Pop_tot*A*K_eq^gamma_après à comparer avec le Pi réel final. 

L'effet du marché permet de determiner un K_equivalent (K_eq) qui représente une entitée du système. Sans prévaloir de l'effet d'un changement de gamma, on peut donner une prédiction naïve du levier de gamma par ce calcul. 

TRES IMPORTANT : Une nouvelle métrique que j'aimerai observer est ce que j'appelle la "tension", c'est à dire le rapport K_aut/K_eq, comme précédemment décrit. J'aimerais que le calcul de ce rapport, ainsi que les graphs associés de son évolution soit ajouté aux code python pour qu'ils soient générés à chaque nouvelle simulation. Si les données présentes sont suffisantes sans relancer de nouveaux batchs de simulations, j'aimerais que ces graphiques "tension" soient générés. 

## [18] page 8  (y=766, obj 517)
"4 Résultats" Le travail sur les fractions n'est pas scientifiquement intéréssant, à cause des part bloqués. Mais le protocole de modification n'est pas encore clair, donc c'est un problème de deuxième classe qu'on ne traitera pas tout de suite. 

## [19] page 8  (y=110, obj 519)
"la
cellule φ = 0,05, la plus basse en intensité, n’est mesurée qu’à 3,2σ"
Il faut, quand cette histoire de mesure à x sigma arrive dans le rapport, un footnote expliquant mathématiquement ce que cela veut dire

## [20] page 9  (y=129, obj 521)
"Le retour ne se fait pas par le haut : il y a un creux. [Fait observé] Les deux bras les
plus intenses ne reviennent pas à zéro, ils passent d’abord en dessous : −7,76 ± 2,01 % à h = 195
(3,9σ) pour φ = 0,5, et −12,98 ± 2,40 % à h = 303 (5,4σ) pour le bras γ. [Fait observé] Au fond
de ce creux, la population est à −20,7 % et −39,1 % de sa référence, pour un capital agrégé à
seulement −9,1 % et −5,9 %."

On ne comprend pas de quoi tu parles dans ce paragraphe. A retravailler.

## [21] page 11  (y=767, obj 523)
": le capital par entité
10monte de ×1,45 (Ktot × 1,090 pour une population ×0,754), et 1,50 × 1,450,5 = 1,806," Explique mieux le calcul. On comprend quand on connait les chiffres, mais la transmission du savoir n'est pas idéal pour un novice du projet. 

## [22] page 12  (y=752, obj 526)
"Le nombre absolu de morts par pas est fixé par le flux de naissances : à l’état
stationnaire il vaut λ = 30 quoi qu’il arrive. Ce qui change réellement est le taux : un tiers de
morts en plus par entité et par pas, et une insolvabilité en hausse de 53 % par entité — donc des
durées de vie plus courtes, ce qui est exactement l’autre face de la contraction de population"

La durée de vie et le nombre de morts par pas est à analyser contre la notion de "tension" que j'ai introduite plus tôt. 

## [23] page 12  (y=308, obj 528)
"le surplus coopératif créé par le
marché fait ×1,92." Le surplus coopératif est intéréssant comme notion, mais il faut le définir mathématiquement en amont. 

## [24] page 13  (y=452, obj 530)
"Figure 8 – Canaux : volume de prêt, part des paires refusées par le sens du prêt, capital agrégé,
morts par pas"

Dans la figure : volume de prêt : intéréssant. 
paires refusées : figure qui sera à terme archaïque. On la garde pour le moment. 

Capital agrégé K_tot : Couper le faut de la figure, l'essentiel de la figure se situe en dessous de l'ordonnée 0.7. Mettre une figure incrustée dans cette dernière avec la vision d'ensemble. Elle peut être très petite, ce n'est pas un soucis. 

morts par pas : pas intéréssant. On sait que les morts vont tourner autour de alpha. 

## [25] page 13  (y=351, obj 533)
"On rapporte donc aussi la réponse
P
P
cumulée sur tout l’horizon, h ∆prod(h)
h (m − 1) p(h) prodréf (h) : 0,744 ± 0,002 (all_A150),
0,765 ± 0,008 (new_A150)"
On ne comprend pas ce passage. A retravailler.

## [26] page 14  (y=545, obj 535)
"Compenser K0 à l’échelle autarcique annule complètement la contraction :
la population revient à ×1,005 ± 0,005 de son contrôle. Et ce n’est pas seulement la population :
tous les diagnostics reviennent à leur valeur de contrôle — capital de naissance relatif 0,0322 contre
0,0323, durée de vie moyenne 37,9 contre 37,7 pas, part des morts avant 10 pas 0,416 contre 0,413,
racines d’insolvabilité ×1,018 contre ×1,155 sans compensation. Le bras à compensation partielle
(×1,45) se place exactement entre les deux sur chacun de ces indicateurs." 

On sait depuis un rapport précédent qu'on peut multiplier K0, A et gamma sans modifier le fonctionnement du système. Ce paragraphe n'est pas intéressant en tant que tel, il ne fait que de la redite. Néanmoins, ce fait reste intéressant. 

## [27] page 17  (y=737, obj 538)
Une étude théorique sur l'action de K0 sera menée. 

## [28] page 17  (y=693, obj 540)

"ε = 1/(1 − γ)" Est ce qu'on a une idée d'une justification analytique de cette loi ? Si oui, je ne l'ai pas bien vu/lu/comprise

