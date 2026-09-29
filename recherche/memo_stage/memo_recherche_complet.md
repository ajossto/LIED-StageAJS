# Mémo maître de recherche — pré-rapport de stage

**Auteur :** Anatole Joseph-Stouls  
**Intitulé du stage :** *Étude et modélisation de l'effet de rebond par approche énergétique. Métabolisme des sociétés industrielles*  
**Période couverte :** vers les 12–13 mars au 24 août 2026  
**Organisme d'accueil :** LIED — Laboratoire interdisciplinaire des énergies de demain  
**Formation :** ENS Rennes, département mécatronique, parcours *Recherche aux interfaces*  
**Nature :** stage de recherche  
**Encadrement :** Éric Herbert, Petros Chatzimpiros, Christophe Goupil et Jean-Philippe Brunetton  
**Statut :** dossier source de recherche, version 1.7 — mise à jour du 24 août 2026  
**Objet :** rechercher une explication générale de l'effet rebond en construisant un modèle minimal d'organisation économique potentiellement auto-critique, puis tester si un rebond peut y émerger endogènement

> Ce fichier est volontairement plus complet qu'un rapport ordinaire. Il doit
> permettre de produire, par condensation, une fiche d'avancement de quelques
> pages ou, par sélection et mise en forme, un rapport de stage complet. Il
> conserve donc les résultats négatifs, les bifurcations du raisonnement et les
> points encore ouverts.

## Statut des affirmations

Le texte utilise six catégories épistémiques.

- **Résultat établi** : observation vérifiée dans les données ou le code, avec protocole documenté.
- **Résultat provisoire** : observation reproductible dans un prototype ou une exploration, mais pas encore confirmée par une campagne complète.
- **Interprétation** : explication compatible avec les observations, sans démonstration causale complète.
- **Hypothèse** : proposition falsifiable qui motive une expérience future.
- **Résultat négatif ou réfutation** : effet recherché mais non observé, ou lecture antérieure invalidée par une analyse plus exigeante.
- **Témoignage de l'auteur** : information de première main sur l'intention,
  l'ordre des idées ou la manière dont une décision a été vécue. Elle établit
  la généalogie du raisonnement, mais ne constitue pas à elle seule une preuve
  du mécanisme scientifique invoqué.

Cette distinction est essentielle : le stage n'a pas consisté à dérouler un
plan linéaire jusqu'à une confirmation attendue, mais à construire
progressivement un objet scientifique en éliminant des mécanismes et des
interprétations insuffisamment robustes.

Les rapports produits par des agents ne sont pas traités comme des comptes rendus
infaillibles. Ils constituent des **interventions dans la recherche** : critique,
proposition de test, interprétation ou verdict provisoire. La chaîne de preuve
recherchée est : intuition ou question d'Anatole → réponse d'agent → réaction et
choix observables d'Anatole → modification ou expérience suivante → contrôle par
le code, les données et les figures. Un énoncé d'agent peut devenir un fait s'il
est recoupé par les sources adaptées ; son seul statut de rapport ne suffit pas.

Ce mémo vise une prise de notes exhaustive. Les localisations précises, résultats
intermédiaires, discordances de provenance et figures inspectées sont conservés
dans `registre_sources_internes.md`, `registre_sources_scientifiques.md` et
`annexe_preuves_historiographiques_2026-08-21.md`.

## Résumé exécutif

Le stage reçoit pour objectif de chercher une explication générale de l'effet
rebond. Les encadrants invitent Anatole à adopter un point de vue physique et à
travailler sur le « métabolisme industriel » : flux d'énergie et de matière,
accumulation, dissipation, réseaux de distribution et organisation collective.
Les lois allométriques associées à Kleiber et leurs explications par des réseaux
de transport ramifiés fournissent un premier langage. Leur caractère invariant
par changement d'échelle rapproche ensuite, dans le raisonnement d'Anatole, les
réseaux fractals des systèmes auto-critiques, sans établir d'identité entre ces
objets.

**Hypothèse justifiant la modélisation énergétique.** Les transferts monétaires
sont lus comme des transferts de droits socialement reconnus à mobiliser
l'exergie. Cette correspondance justifie la possibilité de représenter
énergétiquement une société économique et, dans un même toy-model, les flux
physiques et les positions financières. Elle s'inscrit dans la continuité de l'approche
macro-thermodynamique de Herbert, Giraud, Louis-Napoléon et Goupil, sans être
démontrée par celle-ci. La forte coévolution du PIB mondial et de la consommation
d'énergie entre 1965 et 2015 l'illustre, mais la source montre aussi un découplage
relatif et ne mesure pas directement l'exergie.

Une seconde voie, économique et distributionnelle, vient des travaux de
Drăgulescu et Yakovenko puis de la synthèse de Yakovenko et Rosser. Ils décrivent
un corps exponentiel dit « thermique » pour la grande majorité des revenus et
une queue de Pareto dite « superthermique », plus dynamique et hors équilibre.
Cette coexistence suggère à Anatole qu'une même organisation économique pourrait
faire émerger plusieurs régimes macroscopiques à partir d'interactions locales.
Bak, Chen, Scheinkman et Woodford avaient déjà proposé dès 1992 un toy-model
d'économie de production auto-critique où de petites perturbations sectorielles
peuvent produire de grandes fluctuations agrégées de type Pareto--Lévy. Le stage
ne revendique donc pas l'idée générale d'appliquer la SOC à l'économie ; il
cherche à la prolonger vers le métabolisme industriel et l'effet rebond.

**Témoignage de l'auteur.** La lecture de Hendrick, Rinaldo et Manoli, *A
stochastic theory of urban metabolism* (2025), constitue le déclencheur précis
de l'hypothèse directrice : **l'effet rebond pourrait être un phénomène endogène
à l'organisation de la société**. L'article montre des distributions urbaines à
scaling de taille finie qui s'effondrent, après remise à l'échelle, sur des
courbes communes. Ses auteurs indiquent que cette universalité ressemble à des
processus auto-critiques, tout en précisant qu'ils n'en étudient pas la
dynamique. Le passage à une société économique potentiellement auto-critique est
donc une hypothèse formulée par Anatole à partir de cette lecture, non un résultat
de l'article.

Le programme qui en découle est de construire un modèle-jouet fondé sur des
hypothèses minimales, inspiré de la physique statistique, qui engendre
endogènement des distributions plausibles et des cascades. Le premier objectif
opérationnel est d'obtenir et comprendre ce système ; le second est de modifier
dynamiquement son efficacité afin d'y rechercher un rebond.

Ce cahier des charges restera stable pendant tout le stage : coder uniquement
les interactions locales, observer les macro-statistiques émergentes, vérifier
les classes de distribution du capital et du revenu, mesurer la propagation par
le rapport de branchement et rendre les sorties pilotables par les paramètres.
La comparaison empirique exige toutefois une traduction des variables. Dans le
moteur, \(K\) est la taille intrinsèque productive d'une entité ; le meilleur
analogue de son patrimoine net comptable est \(NW=K+C-D\), non \(K\) seul.

L'approche choisie est physico-économique. Une population ouverte d'entités
abstraites transforme une ressource unique, comptée en joules, accumule du
capital productif, échange du crédit et peut disparaître par faillite. On cherche
à savoir si des règles microscopiques simples engendrent spontanément un système
borné, des distributions à queue lourde et des cascades de toutes tailles,
plutôt que d'imposer directement ces propriétés dans le code.

La première génération de modèles était riche en postes comptables et en
règles de marché. Elle produisait une population apparemment divisée entre
« travailleurs » et « banques », ainsi qu'une queue lourde de tailles et de
revenus. L'analyse distributionnelle a toutefois montré que cette séparation
était principalement portée par deux cohortes d'âge : une cohorte fondatrice
avantagée et des entrantes à vie courte. La corrélation entre âge et logarithme
de la taille atteignait 0,88 à 0,95, et l'exposant de queue dérivait de 5,4 à
3,1 lorsque l'horizon augmentait. Ce résultat a invalidé l'interprétation en
classes économiques stables et a imposé une discipline méthodologique : pas de
pooling entre régimes ou graines, contrôle explicite des cohortes, test de
stationnarité et comparaison des lois avec troncature correcte.

Les versions réduites suivantes ont isolé le rôle du crédit. Dans M2, la
démographie et les distributions étaient essentiellement celles d'un processus
de croissance-renouvellement de type Reed ; l'ablation du crédit ne changeait
pas les formes observées. M3 a séparé liquidité et capital productif et rendu le
crédit causal sur le niveau démographique : il divisait approximativement par
deux la population et l'espérance de vie, sans modifier de manière convaincante
les familles distributionnelles. Les chocs sectoriels corrélés produisaient de
grands groupes de morts, mais leur structure révélait des morts synchronisées,
non une propagation : rapport racines/taille égal à 1 et profondeur au plus 2.

La percée de M4 a consisté à simplifier davantage la règle de faillite. Lorsque
les contrats de la faillie sont annulés, que son capital résiduel est détruit et
qu'aucun amortisseur ne protège ses créancières, un défaut détruit directement
des actifs nominaux et peut rendre d'autres entités insolvables. Avec un marché
réalisant un round par entité et par pas, le système produit de véritables
cascades. M4B est la réduction minimale et validée de cette mécanique : un seul
stock réel productif par entité, un réseau de prêts nominaux perpétuels, des
chocs multiplicatifs, une production concave, de la dépréciation et une règle
d'annulation-destruction.

La campagne de sensibilité M4B constitue le résultat empirique le plus solide
du stage. Elle comprend 594 simulations distinctes, environ 22 heures CPU et
8,6 Go de données, sans erreur comptable, sans censure et avec une phase de
confirmation indépendante. Elle montre un régime stationnaire unique sur tout
l'espace exploré. La volatilité individuelle \(\sigma\) contrôle principalement
la durée de vie et l'exposition ; la taille d'échantillon du marché \(k\)
contrôle les inégalités de capital et la statistique fine des cascades ; le
capital de naissance \(K_0\) protège les jeunes ; la dépréciation \(\delta\)
agit surtout comme une échelle de capital ; l'intensité de naissance
\(\lambda\) fixe la taille du système sans modifier les grandeurs intensives.

Les tailles d'avalanches suivent une loi de puissance tronquée dont la coupure
croît avec la taille du système. L'exposant de grand système est estimé à
environ 2,31 et le rapport de branchement se stabilise près de 0,30 hors de la
zone de faible volatilité. La valeur nette, et non le capital brut, porte
l'inégalité et la mortalité : au point de référence, son Gini vaut environ
0,435 contre 0,074 pour le capital. La position nette de crédit suit un cycle
de vie débiteur puis créancier. Le canal de défaut de liquidité reste silencieux
sur la plage principale : la contagion observée est une contagion de bilan.
Enfin, l'activité agrégée alterne des phases courtes, sans longues récessions ;
sa volatilité décroît comme \(\lambda^{-1/2}\), et son temps de mémoire suit la
durée de vie moyenne des entités. Le contrôle désormais effectué sur l'énergie
totale \(E_t=\sum_iK_i\) donne la même image qualitative. Au centre, on observe
environ 252 récessions par millier de pas, d'une durée moyenne de 1,93 pas et
d'une perte moyenne d'environ 3,5 %. Les épisodes restent courts ; leur
amplitude, beaucoup plus que leur fréquence, est pilotée par la volatilité
individuelle.

Pris seuls, ces résultats M4B ne démontrent pas encore l'effet rebond. Ils
établissent l'étape préalable : un toy-model convergent, reproductible et
pré-SOC existe. La **première** expérience explicitement consacrée au rebond est
en réalité beaucoup plus ancienne : fin avril–début mai, la variante dynamique
`4-05-dynamique` compare le modèle courant à une hausse de 10 % de `alpha`. Le
rapport annonce une hausse de 5,1 % de l'extraction post-transitoire et de 25,2 %
des prêts actifs finaux. Cette expérience a nourri la réflexion, mais son
interprétation dépendait des « banques » ensuite reconnues comme artefacts de
cohorte et de modélisation. Le programme a donc dû repartir de loin, sans repartir
de zéro. Entre le 27 juillet et le 21 août, M4.2, M4.2B, M4.3 et M4.3Live ont
reconstruit une expérience dynamique plus contrôlée sur un mécanisme réduit.

M4.2 montre d'abord que l'effet attribué naïvement à la concavité productive
\(\gamma\) est dominé par un déplacement d'échelle. La dynamique possède une
covariance exacte sous remise à l'échelle du capital ; le rapport
\(K_0/K^*_{\mathrm{aut}}\) devient la combinaison structurelle à contrôler.
M4.2B étudie la distribution des intérêts reçus. Anatole voit une queue de Pareto
dans les graphiques, mais le premier critère d'agent compare à tort le seuil à
`seuil/2`, donc redescend dans le corps de la distribution. Le contrôle
conceptuellement pertinent à `seuil×2` devient trop peu alimenté : la taille de
queue médiane tombe de 113 à 17. L'existence de Pareto reste donc une hypothèse de
travail visible mais non confirmée par ce test, tandis que son exposant
conditionnel est reproductible. M4.3 trouve ensuite, sur une branche à
\(\gamma\) compensé, le premier levier qui épaissit simultanément la queue des
intérêts et renforce les avalanches, de façon robuste à la taille et au temps.

M4.3Live applique enfin une variation dynamique de productivité \(A\) à des
trajectoires appariées. Le verdict dépend de la portée, de l'horizon et de la
convention d'échelle. À portée partielle et court horizon, un rebond est observé.
À portée globale et \(K_0\) fixe, la réponse devient sous-proportionnelle en
régime établi parce que la population se contracte. Lorsque \(K_0\) suit
l'échelle technologique, la contraction disparaît et la réponse agrégée devient
fortement super-proportionnelle, avec une élasticité

\[
\varepsilon=\frac{1}{1-\gamma},
\]

démontrée par une covariance d'échelle exacte du moteur et vérifiée
numériquement. **Résultat actuel : un phénomène qualifiable de rebond est donc
observé dans le modèle, mais son signe à long terme dépend d'une convention de
naissance et sa portée empirique n'est pas établie.** Le stage n'a pas
fourni une explication générale validée de l'effet rebond réel ; il a
construit un mécanisme candidat et montré les conditions sous lesquelles une
réponse endogène apparaît ou s'inverse.

La plausibilité économique du modèle devra être jugée en priorité sur la classe
des distributions de revenu et de patrimoine, puis sur sa capacité future à
produire une mobilité sociale comparable aux observations. Une autre condition
est falsificatrice : l'exposant des cascades doit pouvoir être manipulé et
rapproché de celui mesuré sur les entreprises réelles. Si l'architecture impose
un exposant durablement incompatible avec les données, une restructuration des
hypothèses sera nécessaire.

La littérature présente dans Zotero ne fournit toutefois pas une cible
universelle pour les revenus. Elle fait plutôt apparaître une structure robuste
en deux régimes : un corps exponentiel ou lognormal selon les données et les
définitions, puis une queue de Pareto portant principalement les hauts revenus.
Dans les données fiscales américaines synthétisées par Yakovenko et Rosser, la
queue concerne environ 3 % des déclarations en 1997 et son exposant varie dans
le temps ; chez Wright, le corps lognormal est associé aux salaires et petits
employeurs, et la queue de Pareto aux revenus de propriété. La première cible de
validation doit donc être la présence et la séparation de régimes, complétées
par des statistiques d'inégalité, et non l'obtention d'un exposant universel.
Cette validation sera menée en parallèle pour les revenus des personnes et
ceux des entreprises. Leur appartenance à une même famille de distribution
devra être testée et ne sera pas posée par hypothèse.

De Vries et Toda apportent un repère plus large : sur 475 observations
pays–année couvrant 52 pays entre 1967 et 2018, les exposants de Pareto du revenu
du capital se situent principalement entre 1 et 3, contre 2 à 5 pour le revenu du
travail. Plusieurs exposants simulés sont du même ordre de grandeur. Cette
proximité ne valide pas le modèle et exige une conversion explicite : l'article
emploie l'exposant de CCDF, tandis que certains rapports du stage donnent un
exposant de densité.

Plus généralement, l'absence de données académiques solides, unifiées et
directement comparables aux observables du modèle constitue une information
centrale du stage. Elle concerne notamment les cascades causales de faillites,
la répartition de la consommation d'exergie, le niveau des chiffres d'affaires,
la mobilité et, dans une moindre mesure, les récessions et les revenus. Cette
absence ne confirme aucune hypothèse. Elle signifie en revanche que certains
tests externes de rejet ne peuvent pas encore être conduits proprement : tant
qu'une cible compatible n'est pas identifiée, le modèle ne peut être rejeté sur
la base d'un écart à une « loi réelle » mal définie. Son statut reste donc
**non actuellement réfuté**, et non validé.

Une clarification de l'auteur distingue désormais ontologie et proxys
historiques. Dans le sens voulu du modèle, le **revenu monétaire usuel** d'une
entité est représenté par la somme des intérêts qu'elle perçoit sur une fenêtre,
observable `int_in`. La production ou puissance extractrice représente plutôt
la **capacité d'une entité à grossir en fonction de sa taille et de sa
technologie**. Elle est le terme productif positif — par exemple
`alpha*sqrt(P)` puis `A*K^gamma` — avant érosion et transferts ; elle n'est pas
en elle-même un salaire ou un chiffre d'affaires.

Des analyses antérieures ont néanmoins utilisé la production cumulée comme
proxy du chiffre d'affaires d'une entreprise et « production + intérêts reçus »
comme proxy du revenu brut d'une personne. Ces grandeurs restent des **proxys
statistiques historiques** à documenter, non les définitions ontologiques
finales. Les applications personne et entreprise utilisent le même moteur avec
des jeux de paramètres potentiellement différents ; elles ne représentent pas
deux populations coexistantes. \(K\) désigne la taille intrinsèque productive et
\(NW\) la valeur nette de bilan. La mobilité sociale reste hors du périmètre du
moteur actuel ; une extension ultérieure pourrait introduire filiation et
transmission.

Le stage s'achève sur M4.3Live-v1. M4.3Live-v2 reste une feuille de route : les
ablations et la poursuite numérique n'ont pas été tranchées faute de temps. Le
prototype Boltzmann–Pareto reste une branche secondaire ; il obtient
provisoirement une queue stable et un renouvellement non démographique, mais pas
encore le corps exponentiel recherché.

## 1. Question de recherche et ambition du stage

### 1.1 Point de départ : l'effet rebond comme phénomène collectif

L'effet rebond désigne l'écart entre l'économie de ressource attendue après une
amélioration d'efficacité et l'économie effectivement observée. Dans certains
cas, l'augmentation des usages compense une partie du gain technique ; dans les
cas extrêmes, la consommation totale peut même augmenter. La littérature
économique distingue plusieurs définitions et plusieurs échelles de rebond.

L'objectif confié au début du stage est volontairement plus général que la
calibration d'un mécanisme microéconomique déjà choisi : **chercher une
explication générale de l'effet rebond**. Les encadrants proposent pour cela un
point de vue physique et invitent à étudier le « métabolisme industriel »,
c'est-à-dire l'organisation des flux de matière et d'énergie qui rendent
possible l'activité d'une société industrielle.

La réflexion initiale suit alors une chaîne d'analogies et d'hypothèses qu'il
faut conserver sans la raccourcir rétrospectivement :

1. la loi de Kleiber fournit l'exemple d'une relation de puissance entre taille
   et métabolisme dans le vivant ;
2. des modèles de type West--Brown--Enquist relient de telles lois
   allométriques à des réseaux de distribution ramifiés et fractals ;
3. l'invariance d'échelle de ces structures évoque les systèmes critiques et
   auto-critiques, eux aussi décrits au moyen de lois d'échelle ;
4. la possibilité que des villes présentent des distributions universelles
   après remise à l'échelle suggère qu'une organisation collective puisse
   produire des régularités communes malgré la diversité de ses composants.

Cette piste n'apparaît pas dans un vide bibliographique. Bak, Chen, Scheinkman
et Woodford proposent dès 1992 une économie de production interactive qui
s'auto-organise vers un état critique : de petites perturbations indépendantes
des secteurs ne s'annulent pas nécessairement dans l'agrégat et les fluctuations
de production suivent, dans leur modèle, une loi stable de Pareto--Lévy. L'idée
d'expliquer certaines fluctuations économiques par une SOC est donc antérieure
au stage et explicitement reconnue comme telle.

**Témoignage de l'auteur, 21 août 2026 ; lectures situées au début de la
réflexion, dates précises à retrouver.** La piste économique vient surtout de
Drăgulescu et Yakovenko (2001), puis de Yakovenko et Rosser (2009). Leur lecture
fait apparaître deux régimes empiriques : un corps exponentiel de type
Boltzmann--Gibbs, interprété comme « thermique » et statistiquement stable, puis
une queue de Pareto « superthermique », plus dynamique et hors équilibre. Cette
coexistence conduit Anatole à formuler la question suivante : les comportements
locaux et les échanges entre agents pourraient-ils engendrer ces macro-états par
une dynamique auto-critique ? C'est à ce moment que le problème est pleinement
reformulé en termes de physique statistique, avec micro-états, macro-états et
émergence collective.

Cette formulation est une hypothèse de recherche, pas une déduction des textes
de Yakovenko. Le corps exponentiel est relié, dans certains modèles d'échange, à
une variable additive conservée ; les mécanismes multiplicatifs peuvent produire
des queues de Pareto sans SOC. Réciproquement, une loi de puissance est
compatible avec une dynamique critique, mais ne suffit pas à l'identifier.

Le quatrième point devient décisif à la lecture de Hendrick, Rinaldo et Manoli
(2025). L'article ne démontre pas qu'une ville est auto-critique. Il établit que
les distributions marginales et jointes de population, de réseaux routiers et
d'émissions de CO2 présentent un scaling de taille finie et peuvent s'effondrer
sur des courbes communes. Les auteurs écrivent que cette universalité
**ressemble** à celle de processus auto-critiques, tout en indiquant qu'ils
n'étudient pas la dynamique sous-jacente.

**Témoignage de l'auteur, 21 août 2026.** Cette lecture est le déclencheur
principal de l'hypothèse spécifiquement consacrée au rebond : **l'effet rebond
est peut-être un phénomène endogène de l'organisation de la société**. Une
amélioration locale ne se
contente pas de modifier une technique isolée ; elle peut déplacer les flux,
les investissements, le crédit, la démographie et les fragilités, de sorte que
l'économie de ressource ne se déduit plus du seul gain technique local.

Pour rendre cette proposition falsifiable, Anatole choisit un modèle
multi-agents. Les premières règles physiques sont volontairement simples : une
puissance d'extraction croissante mais concave avec la taille, une érosion
constante et proportionnelle des stocks, une alimentation du système et des
disparitions. À ce noyau s'ajoute un mécanisme financier artificiel, conçu dans
l'intention de reproduire abstraitement certains traits du système financier
contemporain : bilans d'actif et de passif, prêts, intérêts, créances, dettes et
faillites. Le mot « reproduire » décrit ici l'intention de modélisation initiale,
non une validation empirique de la fidélité du mécanisme.

La société est ainsi étudiée comme un système **potentiellement**
auto-critique. Une loi de puissance peut être le symptôme d'une dynamique
critique sous-jacente, mais elle n'en constitue jamais une preuve isolée. Le
programme du stage consiste à construire puis tester la chaîne causale reliant
structure locale, accumulation, réseau financier, cascades, distributions
macroscopiques et réponse à une variation d'efficacité.

### 1.2 Hypothèse justifiant la modélisation énergétique : la monnaie comme droit d'accès à l'exergie

**Témoignage de l'auteur, 21 août 2026.** L'hypothèse qui justifie la
représentation énergétique d'une société économique est la suivante : **un
transfert monétaire peut être
interprété comme le transfert d'un droit socialement reconnu à mobiliser, et
donc à profiter, de l'exergie**. La monnaie n'est pas elle-même une énergie et
un virement bancaire ne transporte pas physiquement des joules. Il réalloue en
revanche des capacités d'achat, d'investissement et de commande qui donnent
accès à des biens, des services et des transformations matérielles dont la
réalisation exige de l'énergie de qualité. Dans cette perspective, les flux
monétaires peuvent être représentés, dans un modèle minimal, comme des
transferts énergétiques abstraits ou des droits sur de tels flux.

#### Puissance extractrice et analogie génératrice de la hache

Dans le vocabulaire d'Anatole, **la puissance extractrice est la capacité d'une
entité à grossir en fonction de sa taille et de sa technologie**. Elle ne
désigne donc ni un apport énergétique biologique journalier constant, ni
l'exergie totale dont une personne bénéficie. Dans le moteur, elle correspond
au terme productif positif : d'abord une forme du type
\(\alpha_i\sqrt{P_i}\), puis \(A_iK_i^{\gamma_i}\). La croissance nette de
l'entité n'est pas identique à cette puissance, puisque l'érosion, les intérêts,
les transferts et les défauts interviennent ensuite dans le bilan.

L'exemple de la hache résume cette intuition. Sa fabrication exige qu'un humain
dépense ou « investisse » de l'énergie. Cet investissement n'est rationnel que
si l'outil permet, au cours de son usage, d'extraire de l'environnement un
surplus d'énergie ou de travail utile supérieur à ce qui aurait été obtenu sans
lui. La hache incorpore ainsi une dépense passée qui démultiplie temporairement
la puissance propre. Mais elle s'use, perd progressivement son efficacité et
demande de nouvelles dépenses pour être entretenue ou remplacée : c'est le rôle
conceptuel de l'érosion.

La viabilité de l'outil se ramène alors à un bilan de puissance : le surplus
utile rendu accessible doit rester supérieur au flux requis pour entretenir le
capital. Lorsque l'entretien et la compensation de l'usure coûtent davantage
que le surplus produit, l'emploi de la machine n'est plus viable. Cette lecture
fait écho, sans s'y identifier exactement, au point fixe autarcique du moteur où
production nette et dépréciation se compensent.

L'analogie peut être étendue aux relations économiques. Une entité investit de
l'argent — interprété ici comme un droit sur de l'énergie — dans une autre en
espérant que cet investissement ramène un surplus avant d'être dissipé. Dans la
figure stylisée « capitaliste--ouvrier », le capitaliste met à disposition une
machine qui incorpore une grande quantité d'énergie passée ; l'ouvrier lui
apporte sa puissance propre et démultiplie sa production ; les deux se partagent
la plus-value, tandis que la machine se dégrade et exige un apport continu.

**Statut.** Cette histoire est une intuition de construction, non la description
littérale du code. Le moteur actuel ne contient ni classes fixes de capitalistes
et d'ouvriers, ni objet « machine » séparé, ni règle explicite de partage de la
plus-value. Il en conserve des équivalents abstraits : stock productif \(K\),
production concave, dépréciation, transferts de principal, intérêts et bilan de
solvabilité.

Cette hypothèse inscrit le stage dans la continuité du programme d'Éric Herbert,
Gaël Giraud, Aurélie Louis-Napoléon et Christophe Goupil. Leur approche par
potentiels thermodynamiques décrit l'économie comme une structure dissipative
hors équilibre, maintenue par des flux de matière et d'énergie dans un monde
fini. Elle construit une macrodynamique cohérente en stocks et flux physiques et
économiques, avec ressources, déchets, recyclage, intensité et friction. Elle
sépare néanmoins explicitement le monde physique du monde économique et étudie
leur couplage : elle soutient donc la dépendance matérielle de l'économie, mais
pas une identité générale démontrée entre monnaie et exergie.

Une illustration empirique motive fortement ce postulat. Dupont, Jeanmart et
Possoz représentent le PIB mondial en dollars constants en fonction de la
consommation mondiale d'énergie entre 1965 et 2015. Les deux grandeurs augmentent
en étroite corrélation et aucun découplage absolu n'apparaît sur la période.
Leur analyse montre toutefois un découplage **relatif** : l'intensité énergétique
du PIB passe approximativement de 11 à 7 MJ/$, avec ralentissement de ce
découplage depuis 2000. Le graphique illustre donc un couplage historique fort ;
il ne démontre ni l'équivalence monnaie--exergie, ni le sens de la causalité, ni
un mécanisme de rebond. Il mesure par ailleurs de l'énergie agrégée et non de
l'exergie.

Cette hypothèse justifie plusieurs choix du toy-model : une unité unique exprimée en
joules, des transferts internes représentables à la fois comme flux de bilan et
comme redistribution de capacité physique, une production nécessitant un stock
productif, ainsi qu'une érosion irréversible. Il fournit la correspondance qui
permet de lire le réseau financier comme une organisation de l'accès au
métabolisme industriel. Son statut reste celui d'une **hypothèse de
justification de la lecture énergétique**,
non d'un résultat : si cette correspondance était invalidée, la valeur formelle
du système stochastique en réseau subsisterait, mais sa portée énergétique et
socio-économique serait fortement réduite.

### 1.3 Pourquoi une approche de physique statistique ?

L'économie étudiée est un système à nombreux degrés de liberté, hors équilibre,
alimenté par un flux externe et dissipatif. Des unités hétérogènes interagissent
localement ; les variables macroscopiques sont des agrégats de trajectoires
individuelles et de relations en réseau. Cette description rend naturelles les
questions de physique statistique : existence d'un régime stationnaire,
distribution des fluctuations, lois d'échelle, effets de taille finie,
transitions, temps de corrélation et propagation sur un graphe.

Le choix ne consiste pas à affirmer que l'économie « est » un système physique
simple. Il consiste à utiliser des outils formels adaptés aux phénomènes
collectifs et à tester jusqu'où des mécanismes minimaux peuvent reproduire des
faits stylisés sans imposer directement leur forme.

Le niveau d'abstraction est volontairement bas. Une entité n'est pas, par
définition, une entreprise : elle peut représenter une entreprise, une personne,
un objet technique tel qu'une voiture, ou plus généralement une unité capable
d'accumuler, de transformer et d'échanger une ressource. Toutes les entités ont
pour le moment les mêmes règles et les mêmes caractéristiques initiales, à
l'exception des différences produites par leur histoire et les tirages
aléatoires. L'ambition est de construire un cadre assez large pour englober une
famille de phénomènes, tout en faisant de la société économique et de l'effet
rebond un cas d'application naturel de ce cadre.

Dans cette ontologie minimale, \(K\) mesure uniquement la **taille** d'une
entité. Il n'est pas nécessaire de décider s'il représente des machines, du
capital humain, un patrimoine productif ou une autre substance économique. De
même, \(NW\) est la taille nette corrigée des positions de crédit, sans
identification imposée à une catégorie comptable réelle. Cette indétermination
est une limite assumée du toy-model et non une question que le stage cherche à
résoudre.

### 1.4 Question opérationnelle progressivement construite

La question générale s'est décomposée en quatre questions plus précises :

1. Une population ouverte alimentée par des naissances peut-elle rester bornée
   sans capacité de charge exogène ?
2. Le crédit modifie-t-il seulement le niveau de mortalité, ou aussi la forme
   des distributions de capital, de revenu et de valeur nette ?
3. Les faillites sont-elles indépendantes, synchronisées par des chocs communs,
   ou réellement propagées par le réseau de créances ?
4. Les statistiques de cascade sont-elles robustes aux paramètres et à la
   taille du système ?
5. Après une hausse d'efficacité, la réorganisation du système rend-elle la
   production agrégée sous-, pro- ou super-proportionnelle, et par quels canaux ?

Le principal acquis du stage est d'avoir transformé une intuition générale en
une chaîne de questions falsifiables et en un protocole reproductible.

### 1.5 Cahier des charges permanent du toy-model

**Témoignage de l'auteur, 21 août 2026.** Dès les premières versions à actifs et
passifs, l'objectif qui sera finalement poursuivi pendant tout le stage est
l'élaboration d'un toy-model se rapprochant d'un système auto-critique. Le
modèle n'a pas vocation à reproduire institution par institution une économie
complète. Il doit isoler un petit nombre d'interactions locales et observer les
statistiques globales qu'elles font émerger.

La **moelle épinière du stage**, selon la formulation de l'auteur, est de rendre
ce modèle pilotable : faire varier ses paramètres microscopiques, quantifier la
variation des statistiques finales et déterminer s'il peut reproduire les
classes de distributions observées dans les données réelles. Cette ambition
associe deux recherches indissociables : trouver un diagnostic statistique de
proximité à la criticité — initialement des lois de puissance, puis notamment le
rapport de branchement — et expliquer par quels mécanismes les phénomènes
observés apparaissent. Une loi de puissance est ici un indice possible de
criticité, jamais une preuve suffisante de SOC.

Cette formulation n'est pas seulement rétrospective. La *Note de travail* datée
du 24 avril 2026 énonce déjà l'objectif de relier des règles individuelles
simples aux classes de distributions globales, puis de formaliser la dépendance
des statistiques aux paramètres de simulation. Elle précise avec prudence
qu'aucune loi de puissance n'a alors été observée et que cette voie pourrait
être un cul-de-sac.

Ce programme impose six critères de travail.

1. **Localité.** Le moteur ne code que des états individuels, des rencontres,
   des prêts, des transferts et des faillites locales. Les macro-états sont des
   observables agrégées, non des trajectoires imposées.
2. **Émergence statistique.** Le système doit engendrer des classes de
   distributions plausibles pour la taille, le revenu et la richesse nette. Le
   premier repère est Yakovenko : corps de type Boltzmann et queue de Pareto.
   Il s'agit d'une hypothèse de vérification, non d'une cible dogmatique, car la
   classe du corps et les exposants restent discutés dans la littérature.
3. **Propagation.** Les grandes faillites groupées doivent provenir de chaînes
   causales internes et non du simple partage d'un choc commun. Le rapport de
   branchement devient un diagnostic caractéristique de la proximité au régime
   critique, sans constituer à lui seul la statistique principale ni une preuve
   de SOC.
4. **Sensibilité pilotable.** Une variation des paramètres microscopiques doit
   modifier les statistiques de sortie de manière reproductible et
   interprétable. Une grande partie du stage consiste précisément à spécifier,
   observer puis caractériser ces liens de conséquence.
5. **Robustesse.** Les distributions, cascades et effets de taille doivent être
   contrôlés entre graines, horizons, cohortes et tailles de système afin de
   distinguer phénomène émergent et artefact numérique.
6. **Réponse à l'efficacité.** Une fois le régime collectif compris et
   pilotable, une perturbation technologique doit permettre de mesurer si la
   réorganisation endogène produit un effet rebond.

Le critère distributionnel demande une doctrine de correspondance. Les entités
du modèle échangent une grandeur énergétique abstraite, tandis que les données
réelles sont comptables et monétaires. Le rapprochement ne peut donc pas reposer
sur les seuls noms des variables : chaque observable doit être interprétée avant
comparaison, et deux grandeurs homonymes peuvent désigner des objets différents.
Dans le vocabulaire propre au moteur, **\(K\), appelé « capital », désigne la
taille intrinsèque productive d'une entité**. Le meilleur analogue du capital
comptable courant ou du patrimoine net total est plutôt **\(NW\), la valeur
nette**, puisqu'elle ajoute les créances et retranche les dettes. Cette
distinction devra être maintenue dans toutes les figures et comparaisons
empiriques.

## 2. Cadre bibliographique et positionnement

### 2.1 Thermodynamique, métabolisme et lois d'échelle

Les analogies entre organisme, ville et économie ont fourni l'intuition de
départ. La loi empirique de Kleiber relie une masse caractéristique à un taux
métabolique moyen par une relation allométrique. Les modèles de
West--Brown--Enquist et les travaux apparentés cherchent l'origine de ce type de
loi dans des réseaux ramifiés de distribution de ressources. La structure
fractale de ces réseaux a fourni à Anatole un premier rapprochement avec les
systèmes invariants d'échelle et la criticité auto-organisée. Ce rapprochement
est une source d'hypothèse, pas une équivalence théorique établie : une structure
fractale, une loi de puissance et une SOC sont trois objets distincts.

La littérature sur le métabolisme urbain décrit les villes comme des systèmes
de flux de matière et d'énergie. Hendrick, Rinaldo et Manoli déplacent l'analyse
des moyennes agrégées vers les fluctuations intra-urbaines. Sur 137 villes et
plusieurs niveaux d'agrégation spatiale, ils étudient les distributions de la
population, des propriétés du réseau routier et des émissions résidentielles de
CO2. Après remise à l'échelle par les grandeurs moyennes, les distributions
marginales et jointes s'effondrent sur des fonctions communes de taille finie.
Les auteurs rapprochent cette universalité des états statistiquement similaires
de processus auto-critiques ouverts et dissipatifs, mais précisent ne pas
étudier les dynamiques qui pourraient l'engendrer. Leur résultat autorise donc
une question sur l'organisation ; il ne permet pas de transférer directement
une SOC urbaine vers l'économie.

Dans la généalogie du stage, cette lecture joue néanmoins un rôle précis : elle
fait passer l'intuition « organismes et villes partagent des lois d'échelle » à
l'hypothèse de programme « l'organisation de la société peut produire
endogènement une réponse collective de type rebond ». Les premiers modèles ne
sont pas des implémentations de Hendrick et al. ; ils constituent une tentative
indépendante de construire la dynamique locale susceptible de produire de
telles régularités.

Ribeiro et Rybski replacent ces régularités dans une littérature urbaine plus
large. Ils recensent des activités socio-économiques généralement
superlinéaires avec la population, des services individuels proches de la
linéarité et des infrastructures sublinéaires. Les modèles proposés pour
expliquer ces lois mobilisent aussi bien interactions locales, gravité spatiale,
densification et géométrie fractale que réseaux hiérarchiques ou diffusion entre
villes. Cette revue étaye donc l'existence de lois d'échelle robustes dans les
systèmes urbains et la pertinence du programme micro--macro. Elle apporte
simultanément un contrepoint décisif : des prémisses différentes peuvent mener
à la même forme \(Y=Y_0N^\beta\). Le scaling est un symptôme à expliquer, non
une signature spécifique de SOC. Sa mesure dépend en outre de la définition des
villes, du modèle de fluctuations et de la distinction entre comparaison
transversale des villes et évolution longitudinale d'une ville.

Herbert, Louis-Napoléon, Goupil et Giraud proposent une dynamique
macroéconomique dans un monde fini fondée sur un potentiel thermodynamique. Le
présent travail est complémentaire : il part de règles microéconomiques et d'un
réseau de crédit, avec l'objectif futur de relier la dynamique multi-agents à un
cadre agrégé de flux et de contraintes physiques.

Le postulat monnaie--exergie présenté en section 1.2 fournit le pont entre ce
cadre macro-thermodynamique et le modèle multi-agents. Le graphique historique
utilisé par Anatole porte exactement sur la consommation d'énergie mondiale et
le PIB, non sur l'exergie : il faut préserver cette différence dans le rapport.
Dans M4B, le joule doit lui aussi être présenté avec prudence. Il est d'abord une
**unité comptable abstraite et conservée lors des échanges**, qui permet d'écrire
une comptabilité cohérente sans introduire immédiatement prix et monnaie.
L'interprétation en droits d'accès à l'exergie justifie la portée énergétique du
programme, mais n'est ni démontrée par la corrélation historique ni indispensable
à l'exécution mathématique du moteur.

### 2.2 Distributions économiques et mécanismes stochastiques

Drăgulescu et Yakovenko observent dans les données britanniques et américaines
que la grande majorité de la population est décrite par une distribution
exponentielle, tandis que l'extrémité supérieure suit une loi de puissance.
Yakovenko et Rosser synthétisent ensuite l'usage de la mécanique statistique pour
les distributions de monnaie, revenu et richesse. Ils qualifient le régime
inférieur de « thermique » et le régime supérieur de « superthermique » : le
premier est relativement stable, le second plus dynamique et hors équilibre.
Un régime additif conservatif peut produire un corps de type Boltzmann--Gibbs,
tandis que des mécanismes multiplicatifs peuvent produire des queues de Pareto.
Bouchaud et Mézard montrent, dans un modèle de richesse avec bruit
multiplicatif et échanges, une densité
stationnaire à queue de Pareto et une transition de condensation.

Dans la généalogie du stage, ce double régime joue un rôle plus fort qu'un
simple fait stylisé à reproduire : il suggère à Anatole de rechercher le
mécanisme collectif qui ferait émerger simultanément un macro-état proche de
l'équilibre et un autre hors équilibre. Le candidat envisagé est une SOC. Cette
lecture relève toutefois de l'hypothèse personnelle : ni Yakovenko ni la seule
présence d'une queue de Pareto ne démontrent que la distribution des revenus est
produite par une criticité auto-organisée.

La lecture détaillée des références Zotero interdit cependant de parler de
**la** distribution des revenus d'une société capitaliste comme d'une loi
unique et consensuelle. Les objets, les périodes comptables, les populations et
les conventions de mesure diffèrent. Quatre résultats sont particulièrement
utiles pour construire une cible de validation.

1. Yakovenko et Rosser ajustent les déclarations fiscales américaines par un
   corps exponentiel et une queue de Pareto. Pour 1997, la frontière ajustée se
   situe vers 120 k$ annuels et la queue représente environ 3 % des
   déclarations. Sur 1983–2000, l'exposant de la CCDF de la queue passe environ
   de 1,8 à 1,4 : la forme supérieure est donc dynamique, notamment avec les
   cycles financiers, et non une constante universelle.
2. Wright décrit plutôt le revenu annuel comme un mélange de salaires et de
   revenus de propriété : le régime inférieur est lognormal et le régime
   supérieur parétien. Sa synthèse de données antérieures situe généralement
   la queue dans les 1 à 5 % supérieurs, avec des exposants de CCDF allant
   approximativement de 0,5 à 1,7 selon le pays et la période. Son propre modèle
   engendre α ≈ 1,3.
3. Fisk montre dès 1961 qu'une loi unique ajustée à l'ensemble des revenus peut
   masquer la superposition de groupes professionnels hétérogènes. Il compare
   des formes à trois et quatre paramètres et souligne explicitement qu'un
   meilleur ajustement accompagne mécaniquement l'ajout d'un paramètre. Cette
   référence donne une profondeur historique au problème de probité des fits
   rencontré pendant le stage.
4. Revenu, monnaie détenue et patrimoine ne sont pas interchangeables. Dans le
   modèle de Wright, le bas des revenus est lognormal tandis que le bas des
   encaisses instantanées est exponentiel. Yakovenko et Rosser trouvent pour le
   patrimoine net britannique un corps exponentiel puis une queue de Pareto
   d'exposant de CCDF α ≈ 1,9. Ces différences peuvent provenir autant des
   mécanismes que de l'objet mesuré.
5. De Vries et Toda étudient séparément les queues supérieures des revenus du
   capital et du travail sur 475 observations pays-années couvrant 52 pays entre
   1967 et 2018. Les exposants de Pareto de **CCDF** du revenu du capital se
   situent principalement entre 1 et 3, avec une médiane de 1,46 ; ceux du
   revenu du travail principalement entre 2 et 5, avec une médiane de 3,35.
   Cette dispersion donne un ordre de grandeur utile pour le modèle, mais non
   une cible universelle. Toute comparaison doit d'abord expliciter si
   l'exposant estimé porte sur une densité ou une CCDF, les deux conventions
   différant d'une unité.

Ces valeurs sont des **repères bibliographiques**, pas encore des cibles de
calibration. Elles portent surtout sur des personnes ou des déclarations
fiscales annuelles, alors qu'une entité M4B peut représenter une personne, une
entreprise ou une unité technique. Avant toute comparaison quantitative, il
faudra donc fixer : l'unité statistique, la fenêtre d'agrégation, le revenu brut
ou net, le traitement des intérêts, la population incluse et la convention
d'exposant entre PDF et CCDF.

Deux applications seront retenues en parallèle : revenu d'une personne et
chiffre d'affaires d'une entreprise. Elles reposent sur le même moteur, mais
peuvent correspondre à des régions différentes de son espace de paramètres. La
généralité revendiquée du modèle autorise cette double application seulement si
elle résiste aux données. Il faudra d'abord établir si les deux distributions
empiriques relèvent de la même famille. Si elles diffèrent, on cherchera si le
moteur peut produire les deux familles par variation justifiée de ses
paramètres ; on ne forcera pas un histogramme unique à valider les deux objets.
La recherche Zotero menée à ce stade documente surtout le versant personnel ;
le versant entreprise devient donc un chantier bibliographique identifié.

Une première recherche ciblée dans Zotero apporte trois repères pour le versant
entreprise, sans encore le clore.

- Wright mesure explicitement la taille d'une firme soit par l'emploi, soit par
  le chiffre d'affaires annuel. Il rapporte que les **taux de croissance
  logarithmiques** des ventes des firmes américaines et italiennes sont proches
  d'une loi de Laplace, avec des travaux ultérieurs préférant parfois une
  Subbotin ou des ailes plus épaisses. Cette loi porte sur la croissance, pas
  sur le niveau du chiffre d'affaires.
- Dessertaine mobilise comme fait stylisé une distribution en loi de puissance
  de la taille des firmes, avec un exposant proche de Zipf, pour expliquer la
  granularité des ventes agrégées. La source primaire devra être relue pour
  vérifier quelle mesure de taille — ventes, emploi ou actifs — porte chaque
  estimation.
- Une étude urbaine de 2023 présente des chiffres d'affaires d'entreprises par
  salarié à queue lourde, mais conditionnés par la taille des villes et la
  complexité des secteurs. Elle ne fournit donc pas directement la distribution
  nationale brute recherchée.

Ces références empêchent de substituer automatiquement « taille de firme » à
« chiffre d'affaires ». La cible entreprise devra porter sur le **niveau du
chiffre d'affaires**, tandis que la distribution de son taux de croissance
constituera un test dynamique supplémentaire et non un équivalent.

Pour la comparaison des seules familles distributionnelles, le pas du modèle
reste une unité abstraite : changer son étiquette calendaire ne transforme pas
une famille après simple changement d'échelle. En revanche, sommer un flux sur
des fenêtres différentes peut lisser ou déformer sa distribution. L'absence
d'effet de la convention temporelle est donc retenue comme hypothèse de travail
à contrôler par agrégation sur plusieurs fenêtres, et non comme identité
mathématique générale.

Le recodage réalisé pendant le stage confirme les résultats centraux du modèle
de Bouchaud–Mézard : dans le régime condensé, l'inverse participation ratio
reste d'ordre un ; dans le régime diffus, il décroît avec la taille du système.
Il confirme également l'ordre de grandeur de la transition sur graphe aléatoire,
tout en montrant la sensibilité quantitative aux détails numériques non fournis
dans l'article.

Cette littérature a conduit à distinguer deux objectifs souvent confondus :

- expliquer une queue lourde locale sur une fenêtre finie ;
- établir une distribution stationnaire dont l'exposant reste stable avec le
  temps et dont le mécanisme est identifié.

La seconde exigence a été retenue. Elle est précisément ce que la première
génération du modèle ne satisfaisait pas.

### 2.3 Modèles multi-agents et émergence de structures sociales

Deux modèles de Ian Wright ont été recodés. Les reproductions retrouvent
qualitativement des classes sociales, des tailles de firmes à queue lourde, des
profits asymétriques et des récessions courtes. Elles révèlent aussi des écarts
quantitatifs stables par rapport aux valeurs publiées. Ce travail a renforcé
deux principes méthodologiques : reproduire un résultat sur plusieurs graines,
et traiter comme information scientifique les conventions d'implémentation qui
ne sont pas explicitées par un article.

### 2.4 Auto-organisation critique et cascades

Les modèles de tas de sable, de chip-firing et les processus absorbants
fournissent le vocabulaire de la criticité auto-organisée : accumulation lente,
relaxations rapides, événements de toutes tailles et invariance d'échelle.
Watts fournit un cadre de cascades sur réseaux aléatoires ; les travaux sur les
réseaux abéliens rappellent que la définition de l'événement et l'ordre de mise
à jour sont constitutifs du modèle.

L'application de ce vocabulaire à l'économie précède largement le stage. Dans
le working paper de Bak, Chen, Scheinkman et Woodford (1992), une économie de
production composée de secteurs localement interdépendants est soumise à de
petits chocs indépendants. Le modèle est relié à un modèle de SOC exactement
soluble et produit des fluctuations agrégées stationnaires de type
Pareto--Lévy, sans choc macroscopique exogène. Cette référence constitue un
précédent direct pour le principe « interactions locales \(\rightarrow\)
fluctuations globales », mais ni pour l'architecture financière du présent
modèle ni pour son application à l'effet rebond.

Les auteurs de ce travail ancien présentent les lois de puissance comme des
empreintes d'une dynamique coopérative critique. Le présent stage adopte une
exigence plus restrictive pour son propre diagnostic : plusieurs mécanismes non
critiques produisent eux aussi des queues lourdes, de sorte qu'une loi de
puissance ne devient un indice de SOC qu'avec propagation causale, effets de
taille finie, robustesse et dynamique d'auto-organisation documentée.

Dickman, Vespignani et Zapperi (1998) proposent un parallèle plus structurel :
la SOC peut être comprise comme une transition vers un état absorbant dans un
système à entraînement lent, dissipation faible, séparation des échelles de
temps et nombreuses configurations absorbantes. Le paramètre d'ordre est la
densité d'activité. Sous le seuil, toute activité finit par s'éteindre ;
au-dessus, elle peut se maintenir ; au point critique, les perturbations se
propagent sur toutes les échelles. Un substrat conservé et gelé en l'absence
d'activité garde la mémoire des avalanches précédentes.

Une correspondance de travail peut être proposée pour le toy-model. Pendant la
dynamique rapide d'une cascade, les faillites restant à traiter constituent
l'activité ; l'absence de nouveau défaut est l'état absorbant de cette
sous-dynamique ; le réseau de créances, les bilans et la densité d'entités
fragiles forment le substrat mémoriel. L'accumulation et les chocs jouent le rôle
d'entraînement, tandis que dépréciation, annulation et destruction assurent la
dissipation. Cette lecture est prometteuse parce qu'elle relie mortalité,
mémoire de bilan, avalanches et rapport de branchement dans un même cadre.

Elle reste toutefois une **hypothèse de correspondance**. Le système complet,
continuellement alimenté par les naissances et les chocs, n'est pas absorbant au
sens strict. Il faut distinguer l'arrêt d'une cascade rapide de l'extinction de
l'économie entière. Surtout, Dickman et al. montrent que la criticité requiert
des valeurs critiques de l'entraînement et de la dissipation ; l'étiquette SOC
demande encore de prouver que la dynamique sélectionne elle-même cette frontière
plutôt que de l'obtenir par réglage des paramètres.

La recherche d'un rapport de branchement proche de l'unité précède cette lecture
dans la trajectoire d'Anatole. La lecture, tardive dans le stage, de Bouchaud
(2024) lui fournit ensuite une formulation rétrospective particulièrement claire
de ce critère. Dans un processus de
branchement, si \(R_0\) est le nombre moyen d'événements directement déclenchés
par un événement, \(R_0<1\) est sous-critique : la taille moyenne reste finie et
la queue possède une coupure exponentielle. À \(R_0=1\), le processus devient
critique et, dans le cas classique, les tailles suivent \(S^{-3/2}\). Au-dessus
de l'unité apparaît une probabilité non nulle d'événement macroscopique limité
seulement par la taille du système.

Cette transition ne suffit toutefois pas à définir la **self-organization**. La
SOC demande en plus que les paramètres ou les rétroactions du système le
conduisent spontanément au point critique, ou lui fassent visiter régulièrement
son voisinage, plutôt qu'un expérimentateur règle \(R_0\) à un. Dans les
simulations du stage, le rapport

\[
b=1-\frac{\sum_a R_a}{\sum_a S_a}
\]

mesure la fraction moyenne de morts non racines dans les forêts de faillites ;
il estime la force de propagation et joue le rôle d'un rapport de branchement
empirique. Sa proximité de un est donc un indice caractéristique de criticité,
mais ni l'unique ni toujours la principale statistique du stage. Pour
conclure à une SOC du modèle entier, il faut encore établir l'attraction
endogène vers ce régime et les autres signatures de criticité.

Au point critique inférieur de son modèle, Watts obtient théoriquement une loi
de taille de cascade d'exposant \(3/2\) pour la densité — soit une pente \(1/2\)
pour la distribution cumulative complémentaire. Cette valeur ne constitue pas
une mesure de cascades de faillites réelles. L'article conclut au contraire que
l'absence de données empiriques détaillant les tailles de cascades ne permet
pas de départager les formes en loi de puissance et bimodales. La bibliothèque
Zotero contient aussi des références sur la taille ou la fréquence des firmes
en faillite ; ces observables ne doivent pas être confondues avec le nombre de
défauts causalement descendants d'un défaut racine. À ce stade, aucune cible
empirique directement comparable à l'avalanche M4B n'a donc été identifiée dans
la bibliothèque.

Ormerod et Mounfield fournissent un symptôme macroéconomique complémentaire.
Dans les taux annuels de croissance du PIB réel par habitant de 17 économies
capitalistes entre 1870 et 1994, une loi de puissance approxime les distributions
de durée et d'amplitude des récessions, mais prédit trop de grands événements.
Pour les récessions durant plus d'un an, les durées de deux à sept ans sont très
bien ajustées par la méthode des auteurs ; l'excès d'épisodes d'un an et la
rupture de scaling dans les extrêmes sont interprétés comme des manifestations
de l'adaptation des agents.

Ce résultat est compatible avec l'idée de comportements coopératifs et
corrélés, mais ne démontre pas une SOC. Le pooling des pays et des époques,
l'ajustement de fréquences groupées et l'absence de comparaison moderne entre
familles limitent la portée des exposants. Pour le stage, la contribution
principale est double : la distribution des durées et amplitudes devient un fait
stylisé candidat, et les écarts systématiques à la loi de puissance deviennent
eux-mêmes un phénomène à expliquer plutôt qu'un simple défaut d'ajustement.

La contre-analyse directe de Wright (2005) interdit toutefois de retenir cette
loi de puissance comme cible acquise. Sur les mêmes fréquences, une loi
exponentielle ajuste mieux l'ensemble des durées ainsi que les amplitudes selon
son critère d'erreur ; la puissance ne devient meilleure qu'après exclusion des
récessions d'un an, qui représentent 61 % des observations. Wright signale lui-même
qu'un jeu de données étendu conduit ensuite d'autres auteurs à la conclusion
opposée. La classe de distribution des récessions doit donc rester une question
ouverte et un cas exemplaire de la nécessité de comparer les familles.

Le stage retient une définition opérationnelle prudente. Une loi de puissance
visuelle ne suffit pas. Il faut au minimum : une définition causale de
l'avalanche, une propagation interne vérifiée, des estimateurs adaptés aux
données discrètes, un contrôle de la coupure, un scaling en taille finie et une
robustesse aux graines et aux fenêtres.

### 2.5 Effet rebond

Sorrell et Dimitropoulos montrent que le terme « effet rebond » recouvre des
objets différents selon la définition du service énergétique, du coût effectif
et de la réponse comportementale. Cette précaution s'applique directement au
modèle : une hausse de production ou de population après un changement de
paramètre n'est pas, à elle seule, une mesure de rebond. Il faut définir la
ressource, le service, l'amélioration d'efficacité et le contrefactuel sans
réorganisation.

## 3. Trajectoire de recherche

### 3.1 Une démarche « en accordéon »

La construction du modèle ne suit pas une réduction monotone. La méthode
adoptée est une succession d'élargissements et d'élagages. Une version est
d'abord enrichie pour ouvrir de nouveaux comportements possibles : davantage de
postes comptables, de règles de marché, de canaux de faillite ou de sources de
bruit. Les résultats obtenus sont ensuite soumis à des ablations, des analyses
de sensibilité et des tests de causalité. Les mécanismes qui ne portent pas les
phénomènes recherchés sont retirés, jusqu'à obtenir un noyau minimal lisible.

M4 puis M4B illustrent ce mouvement. M4 explore plusieurs mécanismes de
propagation et identifie la combinaison annulation-destruction. M4B retire les
branches expérimentales, conserve la mécanique nécessaire et permet une étude
de sensibilité systématique. Cette démarche en accordéon évite deux écueils :
rester prisonnier d'un modèle trop pauvre qui ne peut rien produire, ou conserver
une complexité dont on ne sait plus quel élément explique le résultat.

### 3.2 Un premier cycle de critique formelle — 3 au 9 avril

Les mémos et rapports conservés dans codex_analysis_workspace montrent qu'un
premier cycle explicite de revue critique a précédé la nomenclature M2–M4. Des
versions mathématiques des modèles v2 et v3/WIP ont été soumises à plusieurs
rounds de critique. Les objections portaient notamment sur une erreur de
Jensen, la dérive du bruit multiplicatif, une conservation incorrecte de
\(NW\), un matching déterministe présenté comme stochastique, la censure à
droite, l'usage d'une seule graine et une revendication de SOC non étayée.

La réaction n'a pas consisté à défendre le vocabulaire initial. Les documents de
réponse indiquent explicitement :

- l'abandon du terme SOC comme conclusion acquise ;
- la séparation entre flux quasi-stationnaires et stocks encore dérivants ;
- la dé-priorisation d'une cohorte suivie non représentative ;
- le remplacement d'un pseudo-rayon spectral par des métriques de propagation
  plus directement observables ;
- le passage à des sweeps multi-graines sur les axes les plus importants.

Le WIP d'avril atteignait un quasi-régime de flux après environ 500 pas, mais le
stock de prêts continuait à croître lorsque l'amortissement était nul. Un seuil
topologique net apparaissait entre \(k=2\) et \(k=3\) : un sweep à dix graines
estimait un saut d'un facteur 15,3 de l'intensité de création de crédit. Le
round suivant a également construit un point fixe local
\(N^*\simeq\lambda/h^*\), une fermeture de la fragilité cachée des créances et
un diagnostic spectral effectif. Ces résultats appartiennent à un moteur
historique ; ils ne doivent pas être transportés quantitativement vers M4B.
Leur contribution principale à la lignée actuelle est méthodologique :
stationnarité par observable, cohorte complète, métrique causale, séparation
exploration–confirmation et fermeture théorique testable.

Une limite structurelle de cette campagne doit toutefois rester attachée à ses
résultats en \(k\). Dans le moteur ancien, \(k\) règle la taille du pool de
candidates, tandis que le nombre maximal de tentatives de création de contrats
reste fixe quelle que soit la population. Le seuil observé est donc réel pour ce
protocole, mais il confond information locale, nombre de contreparties et
intensité agrégée du marché. La suite dissociera ces objets : l'activité sera
rendue proportionnelle à \(N\), puis la rencontre sera réduite à des paires
aléatoires \(k=2\), suffisantes pour un toy-model.

Les présentations préparées en mai constituent un autre instantané historique.
Elles remettent la SOC au rang d'hypothèse motivante et formulent déjà
l'enchaînement « effet rebond endogène — organisation micro — distributions
macro ». Elles annoncent toutefois comme résultat l'émergence de deux
populations aux comportements économiques distincts. Cette interprétation sera
ensuite invalidée par l'analyse des cohortes. Ce contraste doit être conservé :
il montre une hypothèse abandonnée puis reconstruite sous une forme plus
prudente, et empêche de raconter la trajectoire comme une confirmation linéaire.

### 3.3 Première génération : un modèle comptable riche — vers les 12–13 mars à fin avril

Ces premiers moteurs matérialisent immédiatement le programme : faire émerger
un comportement global potentiellement auto-critique à partir d'une comptabilité
locale d'actifs et de passifs, sans équation macroéconomique imposant la forme du
résultat. Leur richesse initiale vient du désir de donner au réseau assez de
canaux pour produire endogènement accumulation, redistribution, fragilité et
cascades. Les versions ultérieures chercheront à retirer tout ce qui n'est pas
causalement nécessaire.

La première version distinguait plusieurs postes d'actif et de passif :
liquidité, capital auto-investi, capital financé par emprunt, créances et
dettes. Les entités extrayaient une ressource selon une fonction concave de
leur taille, subissaient une dépréciation et arbitraient entre
auto-investissement et prêt. Le principal nominal d'un crédit ne se dépréciait
pas au même rythme que le capital réel. Cette asymétrie créait une fragilité :
les intérêts restaient dus alors que l'actif productif s'érodait.

Deux familles de comportements sont alors rencontrées selon les paramètres et
les versions. Dans certains régimes, le mécanisme de marché « ne prend pas » :
aucune mortalité suffisante ne vient borner l'accumulation, le nombre d'entités
et l'extraction totale divergent. Dans d'autres, le système converge vers un
macro-régime apparemment stationnaire, avec une population et une extraction
bornées malgré les naissances, faillites et renouvellements locaux. La note du
24 avril situe l'établissement apparent de ce régime après environ 500 pas.

Les simulations convergentes présentaient en outre une distribution bimodale.
Les grandes entités recevant une part importante de leurs entrées sous forme
d'intérêts furent interprétées comme des « banques », les autres comme des
« travailleurs ». **Aucun type d'agent « banque » ou « travailleur » n'a jamais
été déclaré** : toutes les entités suivaient des règles comparables, et ces mots
étaient des étiquettes exploratoires appliquées à une différenciation émergente.
Le retrait d'un mécanisme bancaire spécial dans les variantes « sans banque »
visait consciemment, dès mars, à tester cette émergence et à demander si elle
pouvait illustrer un mécanisme réel. Cette lecture était cohérente avec certaines trajectoires
individuelles et constituait alors une énigme causale à expliquer, mais elle
n'avait pas encore été soumise à un contrôle démographique rigoureux. L'analyse
ultérieure montrera que cette séparation reflétait principalement le mélange
entre cohorte fondatrice et nouvelles entrantes ; il faut donc conserver
l'observation historique sans maintenir son interprétation fonctionnelle.

À ce stade, les deux objectifs expérimentaux sont déjà formulés : chercher une
signature statistique compatible avec la criticité et expliquer les phénomènes
émergents, en particulier la convergence et les deux classes apparentes. Le
résultat contemporain est néanmoins explicitement négatif sur le premier point :
au 24 avril, aucune loi de puissance n'est établie et l'hypothèse SOC reste une
piste de travail susceptible d'être abandonnée.

Le modèle sauvegardé le 27 avril est la continuation intellectuelle directe du
WIP sans banque, non une reconstruction indépendante. Ses campagnes de
sensibilité rendent la recherche de « pilotage » quantitative. Le premier seuil
\(k=3\rightarrow4\), présent sur trois graines, est ensuite requalifié par la
carte \(k\times\mu\) : lorsque \(\mu=0\), des régimes actifs apparaissent déjà à
\(k=2\) ou 3. \(\epsilon=10^{-2}\) détruit le réseau dense ; le bruit sur
\(\alpha\) n'est actif que dans une fenêtre intermédiaire et aucun run n'est
borné pour \(\sigma_\alpha\geq0{,}035\) dans la carte étendue. Une configuration
\(k=3,\sigma_\alpha=0{,}005\), encore oscillante à 5 000 pas, devient stationnaire
pour cinq graines sur six à 10 000 pas : une instabilité apparente est ainsi
requalifiée en transitoire long. Dans les régimes actifs de deux cartes, la
densité financière en volume se situe autour de \(0{,}24\pm0{,}02\). Les sources
quantitatives et les figures correspondantes sont indexées dans l'annexe de
preuves historiographiques, section F.

Les prompts de cette période documentent aussi l'organisation du travail :
Codex prend en charge l'exécution numérique, l'infrastructure et Simulation
Lab ; Claude est sollicité pour l'interprétation, la critique statistique et la
rédaction des rapports. Anatole impose les axes de balayage, les couplages, les
critères de stationnarité, la distinction entre volume financier et densité de
contrats, puis exige que les runs soient consultables avec figures et
métadonnées. Ces textes décrivent une division instrumentale ; les verdicts des
agents ne sont retenus qu'après contrôle des sorties et des décisions qui les
suivent.

La branche `anciens_modeles/4-05-dynamique/`, apparentée à ce WIP, porte la
**première expérience explicitement consacrée à l'effet rebond**. La variante
`alpha_plus_10pct` augmente la productivité de 10 %. Son rapport annonce, après
le pas 500, une extraction supérieure de 5,1 % au baseline et 25,2 % de prêts
actifs supplémentaires à l'état final. Cette trace a nourri la suite, mais elle
n'est pas une campagne close : le rapport parle de trois graines alors que les
CSV archivés n'en contiennent que deux par variante et ne reproduisent pas
exactement tout son tableau. La découverte ultérieure de l'artefact de cohortes
a décrédibilisé ce premier moteur et conduit à repartir de loin, non de zéro.

### 3.4 Première correction majeure : les classes étaient surtout des cohortes — fin juin à début juillet

L'étude de 805 simulations de la lignée du 27 avril n'en retient que 163 comme
stationnaires selon les diagnostics disponibles. Sur les états finaux, l'âge
explique fortement la taille : la corrélation âge–log(taille) vaut 0,88 à 0,95.
La distribution des âges présente un trou entre une cohorte fondatrice très
ancienne et des entrantes récentes. Le mélange de deux log-normales ajuste bien
la distribution globale parce qu'il approxime ces deux cohortes, non parce
qu'il découvre deux fonctions économiques stables.

Autre alerte, l'exposant de queue estimé dérive avec l'horizon : environ 5,4 à
\(T\simeq1000\), 5,0 à \(T\simeq1500\), puis 3,1 à \(T\simeq3000\). Une vraie
loi d'échelle stationnaire ne devrait pas s'alourdir ainsi. La conclusion
correcte est donc négative : la queue est plus lourde qu'une log-normale simple,
mais le modèle ne démontre pas une queue de Pareto stationnaire.

**Effet sur le programme de recherche.** La cohorte initiale est supprimée des
versions suivantes ; les mesures doivent être conditionnées sur l'âge ou
vérifier explicitement le renouvellement ; l'exposant est comparé entre
fenêtres à seuil commun ; les familles sont ajustées run par run, sans pooling
inter-graines ou inter-régimes.

### 3.5 M2 : un noyau démographique robuste, mais un crédit neutre sur les formes — 3 juillet

Deux implémentations concurrentes de M2, lancées à partir du même prompt,
convergent. Elles constituent des réplications adversariales apparentées, non
deux hypothèses ni deux preuves entièrement indépendantes. La population est bornée,
les classes se renouvellent et la corrélation entre âge et valeur nette est
faible. En revanche, l'ablation sans crédit donne des distributions et des
exposants pratiquement indiscernables de la baseline. Le modèle est mieux
interprété comme un générateur démographique de type Reed : naissances,
croissance multiplicative et absorption suffisent à produire la structure
principale.

Cette interprétation repose sur plusieurs contrôles convergents. La queue
effective de valeur nette paraît assez stable entre fenêtres, avec un exposant
de l'ordre de 2,6--2,8, mais une log-normale tronquée gagne les comparaisons de
vraisemblance corrigées contre Pareto. Le corps n'est pas exponentiel : la
famille de Fisk domine presque toutes les cellules testées. Les exposants de la
variable de revenu et de la valeur nette diffèrent fortement ; ils ne peuvent
donc pas être présentés comme deux mesures interchangeables d'une même loi.
Enfin, les cascades sont étroites et le retrait du crédit conserve les
signatures principales. M2 produit donc une queue lourde plausible, non une
identification robuste de Pareto, et encore moins une preuve de SOC.

M2 a aussi corrigé deux sources possibles de faux positifs statistiques : une
comparaison de vraisemblance historiquement biaisée en faveur de Pareto, et un
calcul d'AIC défavorable à l'exponentielle lorsque sa troncature n'était pas
normalisée. Le fait que le verdict négatif subsiste après correction renforce
sa valeur méthodologique. Une règle de transfert proportionnel testée lors des
explorations a, par ailleurs, fait exploser le nombre de contrats ; elle a été
écartée comme convention génératrice d'un artefact numérique et comptable.

Cette étape constitue un résultat négatif important : la présence d'un carnet
de prêts ne prouve pas que le crédit cause les faits stylisés mesurés.

M2 introduit aussi, pour la première fois dans la lignée réduite, le déplacement
du choc multiplicatif vers le stock réel. Le WIP du 27 avril perturbait
\(\alpha\) par un brownien géométrique dont la dérive positive était déjà
annotée comme problématique. M2 perturbe directement \(w\), puis calcule
\(\alpha\sqrt{w}\). M3 renomme ce stock \(K\), et M4 hérite de cette règle. La
modification parfois attribuée à M4 est donc attestée dès M2.

### 3.6 M3 : rendre le crédit causal — 3 au 6 juillet

M3 sépare la liquidité \(L\) du capital productif \(K\). Le crédit devient le
canal de conversion inter-entités de liquidité en capital productif, tandis que
les intérêts sont exigibles en liquidité. Le protocole compare la baseline à
plusieurs ablations et variantes.

**Résultats établis dans M3 :**

- le crédit divise approximativement par deux la population stationnaire et
  l'espérance de vie ; il est donc causal démographiquement. Il accélère
  l'horloge de renouvellement sans changer sa loi ;
- les formes de valeur nette, revenu et capital restent très proches de
  l'ablation sans crédit dans la baseline ; le crédit reste neutre sur les
  distributions principales. Le revenu est double Pareto-lognormal dans toute
  la grille documentée, le corps de (NW) est généralement de type Fisk et
  (K) est log-normal ;
- le canal nominal porte l'effet démographique : la variante où le crédit reste
  nominal mais non productif reproduit l'essentiel du résultat, tandis que les
  pertes de créances et l'effet productif agrégé par tête contribuent peu ;
- la liquidité (L), pourtant introduite comme la candidate la plus proche de
  la variable monétaire de Yakovenko, n'est pas Boltzmann--Gibbs. Son corps est
  de type Fisk, car l'injection productive hétérogène et la fuite multiplicative
  dominent les transferts conservatifs ;
- les défauts de liquidité sont presque absents dans la baseline ;
- les chocs sectoriels corrélés augmentent continûment la taille des groupes de
  morts sans créer de transition auto-organisée. Les cascades causales existent
  mais restent petites et sous-dispersées ;
- sans renouvellement, le système s'éteint : les naissances sont une condition
  d'existence du régime, pas une simple perturbation périphérique ;
- retirer le plancher exogène de dette n'empêche pas nécessairement le bornage :
  sur trois graines, la population se stabilise autour de 5 600 entités avec un
  rapport morts/naissances proche de 0,98. La dette contractuelle devient alors
  l'unique mécanisme de mortalité et constitue un plancher d'absorption
  endogène.

Ce dernier résultat est le pont conceptuel direct proposé par le programme M3
vers M4 : remplacer la dette initiale envers un puits exogène par une dette de
subsistance contractée à la naissance auprès d'entités réelles. La disparition
d'une entité peut alors infliger une perte à des créancières identifiées. Il ne
prouve pas que M4 réalise nécessairement cette recommandation sans modification
supplémentaire, mais il documente l'origine de la recherche d'une propagation
endogène par pertes de créances.

Une variante de comportement, dite règle de revenu, change la cible du marché.
Au lieu d'internaliser le coût complet du capital, dépréciation comprise,
l'entité emprunte tant que la production marginale couvre l'intérêt courant.
Cette maximisation myope augmente fortement le levier : le service de la dette
passe d'environ 1,5 % à 6--14 % de la production, la population et l'espérance
de vie sont divisées par environ huit, le Gini de (NW) passe d'environ 0,56 à
0,62--0,69 et les intérêts représentent 9--22 % du revenu du centile supérieur.
Le crédit devient donc distributionnellement actif et les défauts de liquidité
s'allument. La faible population de ce régime ne permet toutefois pas
d'identifier proprement les familles de distribution. Les avalanches restent
sous-Poisson : la leçon est double, la neutralité du crédit dépend de la règle
de comportement et la financiarisation ne suffit pas à engendrer une criticité.

Deux échecs de protocole sont eux-mêmes informatifs. L'ablation destinée à
tester la topologie éteignait en réalité presque le marché et ne comparait donc
pas des volumes de crédit équivalents. Le premier protocole de chocs corrélés
confondait corrélation macroéconomique et réduction de la dispersion
idiosyncratique, donc raréfaction du crédit. Ces questions n'ont pas reçu de
réponse confirmatoire dans M3 et ont conduit à exiger des ablations à volume
contraint et des conventions de choc mieux séparées.

Enfin, M3 a révélé deux artefacts d'instrumentation : une fonction
d'observation modifiait un `defaultdict` en lecture et perturbait la trajectoire
au dernier bit ; l'estimateur CSN dégénérait lorsque toutes les avalanches
valaient un. Les deux problèmes ont été corrigés et testés. Ils fondent une
règle générale du stage : l'observation doit être démontrée neutre, et un
estimateur de queue ne doit pas être interprété hors de son domaine numérique.

### 3.7 M4 : distinguer synchronisation et contagion — 13 au 17 juillet

M4 cherche explicitement une loi de tailles d'avalanches issue d'une propagation
endogène. Le fork du 13 juillet reprend trois enseignements de M3 : le plancher
exogène (d_0) est retiré, la règle de revenu à levier élevé est conservée, et
le capital productif et la liquidité sont progressivement fusionnés en un seul
stock (K). Le financement de la dotation de naissance par une prêteuse réelle,
directement inspiré de la « dette de subsistance » proposée après l'ablation H,
fait apparaître un peu de propagation, mais reste optionnel et ne sera pas
nécessaire au régime finalement retenu.

Une première piste utilise des chocs sectoriels corrélés. Les grands événements
obtenus ont un rapport racines/taille égal à 1 et une profondeur faible : ils
sont déclenchés simultanément. La bonne apparence de la régression en log-log et
la croissance de la taille maximale avec le système ne résistent pas à
l'inspection des arbres causaux. Cette piste est réfutée comme mécanisme de
contagion. Un autre candidat, observé à (k=3), se déforme en bosse lorsque la
taille du système passe d'environ 230 à 2 300 entités ; il s'agissait d'un
croisement de percolation de taille finie, non d'une SOC.

La découverte décisive, consignée le 14 juillet, est obtenue en simplifiant la
faillite :

1. les contrats portés par la faillie sont annulés au lieu d'être transférés ;
2. son capital résiduel est détruit au lieu d'être redistribué ;
3. les créancières perdent sans récupération le principal de leurs créances.

La combinaison annulation–destruction concentre les expositions, supprime les
amortisseurs et permet à un défaut de rendre une créancière insolvable. La
propagation devient visible dès le prototype : environ 56 % des membres des
événements sont alors des victimes induites et la profondeur maximale atteint
8. Les campagnes confirmatoires suivantes donnent un rapport racines/taille
d'environ 0,48--0,51 sur les avalanches d'au moins cinq morts, des profondeurs
maximales de 9 à 14 et une coupure croissante avec la taille du système. Les
ablations montrent que la destruction seule ne suffit pas : c'est la
combinaison des deux décisions qui engendre le régime.

Ce mécanisme explique le choix de poursuivre la branche Fable plutôt que la
branche Sol : annulation–destruction fournit une propagation causale, des
statistiques jugées cohérentes et un régime qualifié de **pré-SOC**. Dans une
campagne à un round de marché par tête, le rapport de branchement converge vers
0,300 ± 0,003 sur les graines et tailles testées, tandis que la taille maximale
d'avalanche croît approximativement comme \(N^{0,59}\) sur trois lots. Ces
résultats ont justifié la réduction vers M4B ; \(b\simeq0,30\neq1\) interdit
toutefois d'y voir une SOC stricte.

Le volume d'appariement est le paramètre institutionnel de contrôle. Autour
d'un round par entité et par pas, le système se place dans une fenêtre où la
coupure des avalanches est grande, sans effondrement systématique. La
revendication prudente n'est pas celle d'un attracteur critique universel, mais
d'une criticité auto-entretenue dans une fenêtre institutionnelle large.

Cette chronologie impose une distinction entre trois niveaux : une loi de
puissance apparente, une propagation causale, et une criticité au sens fort.
M4 franchit nettement le deuxième niveau. Le troisième reste une hypothèse de
programme, car l'apurement plus intense du marché sur-vise la fenêtre et le
rapport de branchement simple reste inférieur à un. Les résultats quantitatifs
de référence ne sont donc pas les annonces à chaud du journal M4, mais la
campagne ultérieure de sensibilité de M4B.

### 3.8 M4B : réduction minimale et audit de sensibilité — 16 au 27 juillet

M4B conserve exactement la mécanique finale de M4 tout en retirant les
variantes d'ablation et l'infrastructure expérimentale. Des tests de parité
comparent M4 et M4B pas à pas et obtiennent les mêmes trajectoires pour les
configurations contrôlées. M4 et M4B ne sont donc pas deux preuves
indépendantes : M4B est un condensat fidèle de M4.

M4B matérialise aussi la correction institutionnelle du vieux paramètre \(k\) :
il exécute un round de marché par entité vivante et par pas, de sorte que
l'activité agrégée croît avec \(N\). M4.2 séparera définitivement intensité de
marché et taille de rencontre en utilisant des paires aléatoires
(`POOL_SIZE=2`) et \(\eta(N)=N\).

La campagne M4B déplace la question. Il ne s'agit plus seulement de montrer un
exemple de cascade, mais de cartographier le régime, de hiérarchiser les
paramètres et d'établir les invariants utiles à la version suivante.

### 3.9 De M4.2 à M4.3Live : rendre le modèle pilotable puis perturber son efficacité — 27 juillet au 21 août

La période postérieure au premier mémo maître forme une seconde séquence de
recherche, désormais achevée jusqu'à M4.3Live-v1.

**M4.2 — 27 au 29 juillet.** La fonction de production devient
\(F_\gamma(K)=A K^\gamma\). La question initiale est de savoir si la
concavité permet de piloter l'exposant des avalanches. Un contraste entre
\(\gamma=1/3\) et \(1/2\) est mesuré sur graines confirmatoires, mais le
contrôle décisif montre que l'effet est principalement un effet d'échelle.
Cette version fixe en outre les rencontres à des paires aléatoires \(k=2\) et
l'activité de création de contrats à \(\eta(N)=N\), distinguant ainsi la
complexité locale de la rencontre du volume agrégé du marché :

\[
K^*_{\mathrm{aut}}(\gamma,A)
=\left(\frac{(1-\delta)A}{\delta}\right)^{1/(1-\gamma)}.
\]

La dynamique possède une covariance exacte sous
\((K,K_0,A)\mapsto(cK,cK_0,c^{1-\gamma}A)\). À \(\gamma\) fixé, les effets de
\(A\) et \(K_0\) ne peuvent donc dépendre que de leur combinaison
adimensionnelle \(K_0/K^*_{\mathrm{aut}}\). L'hypothèse naïve « la courbure
pilote directement la pente » est infirmée ; elle est remplacée par un résultat
structurel plus précis sur l'échelle.

Une étude analytique de la dyade de crédit complète cette étape le 29 juillet.
Elle montre qu'une prêteuse sans dette ne peut pas mourir de la perte de sa
créance : les cascades de plusieurs morts sont nécessairement un effet de
réseau. Sous bruit non dégénéré, l'emprunteuse de cette dyade meurt presque
sûrement en temps fini ; la cible arithmétique maximise la production commune
initiale mais raccourcit sa survie par rapport à la cible géométrique.

**M4.2B — 30 juillet au 6 août.** La cible de principal devient arithmétique et
le programme cherche conjointement une queue épaisse des intérêts reçus et le
maintien des avalanches. Trois tentatives successives de test de l'existence
d'une queue de Pareto échouent à trancher, principalement faute de données dans
la queue extrême. La bonne conclusion est une incertitude : l'existence de la
Pareto devient une hypothèse de travail. Sous cette hypothèse, l'exposant ajusté
est reproductible et répond à \(\eta\), \(K_0\), \(\gamma\) compensé et au couple
\((\delta,\sigma)\). La campagne met aussi au jour une anti-corrélation : dans
presque tout l'espace testé, épaissir la queue des intérêts réduit la criticité
des avalanches.

Cette incertitude résulte d'un épisode méthodologique précis. Anatole voyait sur
les figures une queue supérieure compatible avec Pareto, mais le test d'agent
comparait l'ajustement au seuil avec celui au `seuil/2`, donc redescendait dans
le corps. Sur un instantané réel, ce déplacement fait passer l'exposant de 3,78
à 2,46 et dégrade le KS de 0,041 à 0,173. Le contrôle conceptuellement pertinent
vers `seuil×2` est ensuite adopté ; il laisse toutefois une médiane de seulement
17 observations dans la queue, contre 113 au seuil initial, et 2 % seulement des
réajustements conservent au moins 80 observations. La conclusion est donc :
queue visible et Pareto comme hypothèse de travail, mais confirmation
sous-alimentée — non réfutation graphique de la queue.

Le rapport de branchement prend ici une importance nouvelle. Il vaut environ
0,786 dans la baseline lente, contre environ 0,30 dans la baseline M4B/M4.2, et
atteint 0,891 lorsque l'intensité de marché \(\rho\) vaut 4. Les neuf cellules
confirmatoires couvrent 0,386 à 0,891. Le contrôle géométrique montre que la
hausse de la baseline n'est pas causée par la seule cible arithmétique, mais par
la combinaison relaxation lente, chocs faibles et marché dense. Ces valeurs
établissent un régime fortement propagatif et pilotable, encore sous l'unité ;
elles ne démontrent donc pas à elles seules une SOC.

**M4.3 — 6 au 11 août.** Le programme teste si cette anti-corrélation est
structurelle. Après mesure d'une fenêtre de relaxation propre aux intérêts et
gel d'une statistique de queue de type Dagum, 28 cellules sont remesurées à
horizon \(T=8000\). La branche \(\texttt{gamma\_comp}\), où \(K_0\) suit
l'échelle autarcique, fournit le premier contre-exemple robuste : à
\(\gamma=2/3\), la queue des intérêts s'épaissit et le rapport de branchement
augmente simultanément. Le contraste reste pratiquement identique pour
\(\lambda=10,30,100\) et dans les deux moitiés de la fenêtre stationnaire. Il
brise donc l'anti-corrélation de manière robuste à la taille et au temps.

Quantitativement, pour \(\lambda=10,30,100\), l'écart de branching contre la
baseline reste +0,0184/+0,0184/+0,0185, et l'écart du paramètre `Dagum c` est
voisin de -0,59, malgré une variation de population supérieure à un facteur
dix. L'ablation institutionnelle envisagée n'a pas été tranchée : la campagne et
la poursuite de la recherche ont été arrêtées faute de temps à la fin du stage,
non parce que cette ablation aurait perdu son intérêt.

La statistique de queue a été gelée après correction : il s'agit du paramètre
`Dagum c`, et non du produit erroné utilisé auparavant. Le journal consigne
aussi une sélection de graines après coup, détectée puis corrigée, qui inverse
le sens d'une divergence sans modifier selon le rapport les verdicts D2/D3. Les
tables régénérées constituent donc la source à citer, non les paragraphes
intermédiaires du journal. Le prompt laissait en outre les décisions d'ablation
modifiant le mécanisme à Anatole ; leur absence n'est pas un verdict d'agent.

L'ampleur de l'infrastructure ne doit pas être confondue avec un nombre de
preuves indépendantes. L'inventaire du 21 août retrouve 1 508 manifestes
`run.json` dans Simulation Lab, répartis entre neuf identifiants de modèles ; ce
total inclut imports et archives liées. Un échantillon raisonné de figures —
cartes anciennes, convergence de \(b\), scaling en taille finie, arbres causaux,
queues d'intérêts et plan `Dagum c`–branching — a été inspecté et indexé dans
l'annexe de preuves, section G. Il établit que ces graphiques ont effectivement
servi de traces de décision, notamment pour poursuivre la piste des cascades.

**M4.3Live — 17 au 21 août.** Cette version reprend la question du rebond sur la
lignée reconstruite après M2–M4.3 ; elle n'est pas la première expérience de
rebond du stage, rôle qui revient à la variante dynamique `alpha_plus_10pct`
de fin avril–début mai. Le moteur devient pilotable en direct. \(A\) et
\(\gamma\) sont portés par les entités, les interventions peuvent viser toutes
les entités, les seules nouvelles ou une fraction des vivantes, et un journal
d'interventions permet un rejeu déterministe. La baseline homogène reste bit à
bit identique à M4.3.

Les annotations d'Anatole fixent la logique de l'expérience : observer d'abord
le rebond avant de prétendre l'expliquer, prendre \(A\) comme levier
technologique principal, faire du prêt un maximiseur de puissance extractrice
jointe, conserver M4.3Live comme fork indépendant contrôlé par parité et rendre
possible la reprise puis la bifurcation d'un état simulé. Le premier rapport
attribue la contraction de population à un service d'intérêts alourdi. Quatre
contrôles demandés par Anatole réfutent cette explication et conduisent à
l'ablation de \(K_0\), qui révèle la dépendance du verdict à la convention
d'échelle. Les corrections ultérieures imposent aussi l'amplitude mesurée,
réservent la « tension » au rôle de diagnostic à \(\delta\) fixé, identifient
la rotation du crédit comme corrélat plus robuste et corrigent les seuils de
Student ainsi que la formulation du surplus coopératif.

La campagne dynamique produit trois verdicts :

- à portée partielle et court horizon, la réponse dépasse de 2,3 à 2,9 fois la
  réponse proportionnelle : un rebond transitoire est observé ;
- à portée globale, en régime établi et à \(K_0\) fixe, une hausse de 50 % de
  \(A\) ne donne que 36,1 % de production supplémentaire, car la production par
  entité augmente mais la population se contracte d'environ 25 % ;
- lorsque \(K_0\) est compensé selon l'échelle technologique, la population ne
  se contracte plus et la réponse devient fortement super-proportionnelle,
  avec \(\varepsilon=1/(1-\gamma)\).

Cette dernière loi n'est pas seulement ajustée : elle découle de la covariance
d'échelle du moteur et est vérifiée à la précision machine. L'effet qualifiable
de rebond existe donc dans le modèle, mais son signe agrégé de long terme dépend
du traitement du capital de naissance. Une intervention partielle, quant à
elle, disparaît avec la cohorte traitée en l'absence de transmission aux
naissances. M4.3Live observe ainsi un phénomène et ses conditions ; il ne fournit
pas une explication générale validée de l'effet rebond réel.

**M4.3Live-v2 — 21 août.** Une feuille de route est rédigée, mais le
moteur v2 n'est pas implémenté. Elle prévoit notamment de libérer le sens
du prêt, de déplacer le service des intérêts après dépréciation, de simplifier
la borne de transfert et de mesurer plus directement la tension et l'amplitude.
Anatole en retire aussi les traitements partiels et la variante de plafonnement
`equalization`, qui n'avait jamais été activée dans les runs v1.
Ce chantier reste une conception non exécutée : le stage se termine et les
nouvelles ablations comme la poursuite numérique sont arrêtées faute de temps.

La branche **Boltzmann–Pareto** reste secondaire. Elle cherche une distribution
de valeur nette avec corps exponentiel et queue de Pareto. Sa queue est
provisoirement stable et non démographique ; le corps exponentiel reste à
obtenir. Le nom « M2 » utilisé localement dans son document de conception entre
en collision avec la lignée historique M2 et ne doit pas être repris seul dans
un rapport extérieur.

### 3.10 Registre explicite des modèles et branches

Les dates ci-dessous désignent les périodes grossières de conception, de test
ou de clôture visibles dans les journaux. Elles ne prétendent pas dater chaque
ligne de code. Le registre distingue les moteurs, les campagnes et les archives
afin de ne pas additionner des preuves dépendantes.

| Identifiant de récit | Dates grossières | Dossier ou archive | Parent / fonction | Question ou modification principale | Verdict et statut |
|---|---|---|---|---|---|
| V1 monolithique | vers les 12–13 mars–23 mars | `anciens_modeles/claude/` | premier moteur exécutable | comptabilité, extraction, crédit et cascades dans une architecture monolithique | régimes divergents sans mortalité suffisante ou régimes bornés selon les paramètres ; base historique non canonique scientifiquement |
| V2 modulaire | 23–25 mars | `anciens_modeles/claude3-v2/` | modularisation de V1 | séparer modèles, simulation, statistiques et sorties | socle exécutable des premières analyses ; crédit déterministe et propagation limitée |
| V3 sans banque / 25 mars | vers le 25 mars | ZIP `claude3-v3-25-mars-sans-banque.zip` | variante intermédiaire archivée | retirer un mécanisme bancaire spécial afin de tester l'émergence de rôles sous des règles communes | archive à consulter ; aucun type banque/travailleur n'a été déclaré ; non comptée comme preuve indépendante |
| V3 du 27 mars | 27 mars–3 avril | `archives/modeles/claude3-v3-27-mars/` | source intellectuelle riche issue de V2 | réseau de crédit, fragilité cachée, critique de la SOC | archive historique ; code et tests partiellement désalignés |
| Modèle sans banque WIP | 27 mars–9 avril environ | `anciens_modeles/Modèle_sans_banque/` | prolongement réel de V3, non simple copie | réévaluation des créances, matching local, intermédiaires, premier seuil en \(k\) | résultats exploratoires requalifiés ; nombre de tentatives de marché fixe indépendamment de \(N\) |
| Revue formelle rounds 1–4 | 3–9 avril | `codex_analysis_workspace/` | analyses de V2 et V3/WIP | stationnarité, point fixe local, fragilité, topologie et diagnostic spectral | apporte des fermetures utiles ; retire la SOC du statut de conclusion |
| Modèle du 27 avril WIP | 24 avril–11 mai | `anciens_modeles/modele-27-04-WIP/` | continuation intellectuelle directe du WIP sans banque | élagage, sensibilité, premières lectures en classes et test de productivité | formalise le pilotage paramètres–statistiques ; flux quasi stationnaires, stocks parfois dérivants ; classes ensuite identifiées comme cohortes |
| Variante dynamique 4-05 | fin avril–début mai | `anciens_modeles/4-05-dynamique/` | fork réel du WIP du 27 avril | première expérience explicite de rebond par `alpha+10%` | rapport : +5,1 % d'extraction post-500 et +25,2 % de prêts finaux ; discordance entre 3 graines annoncées et 2 archivées |
| Diagnostic distributions | fin juin–début juillet | `recherche/analyse_distributions_taille_revenu/` | critique transversale du WIP | contrôler âge, pooling, familles et dérive temporelle | réfute l'interprétation stable « banques / travailleurs » |
| M2 Codex | 3 juillet | `anciens_modeles/m2_codex/` | implémentation concurrente issue du même prompt que M2 Fable | le crédit cause-t-il les formes Boltzmann–Pareto ? ; choc déplacé vers le stock réel | non : modèle nul démographique de type Reed |
| M2 Fable | 3 juillet | `anciens_modeles/m2_fable/` | implémentation concurrente issue du même prompt que M2 Codex | parité, corrections statistiques et ablations ; choc sur `w` | même verdict ; réplication adversariale apparentée, indépendance limitée |
| M3 | 3–6 juillet | `anciens_modeles/m3_credit_soc/` | successeur causal de M2 | séparer liquidité et capital ; activer le crédit | crédit causal sur démographie ; H et X1 préparent M4 ; pas de SOC |
| M4 parallèle Sol | 13 juillet | `m4_credit_soc_sol/` | branche expérimentale parallèle | H×X1×G2 et plusieurs mécanismes de propagation | pré-critique prometteur ; SOC robuste non établie |
| M4 Fable | 13–17 juillet | `m4_credit_soc_fable/` | branche principale issue de M3, promue vers M4B | annulation–destruction et passage de synchronisation à contagion causale | pré-SOC aux statistiques cohérentes ; \(b\approx0,30\), donc pas SOC strict |
| M4B | 16–27 juillet | `m4b_credit_soc_mini/` + `recherche/sensibilite_m4b/` | réduction fidèle de M4 Fable | isoler et cartographier le mécanisme minimal ; un round de marché par tête | régime stationnaire robuste et avalanches tronquées ; activité proportionnelle à \(N\) ; pas une preuve indépendante de M4 |
| Boltzmann–Pareto | juillet, branche secondaire | `recherche/conception_boltzmann_pareto_soc/` | exploration hors lignée principale | obtenir corps exponentiel et queue Pareto | queue provisoirement stable ; corps exponentiel non obtenu |
| M4.2 | 27–29 juillet | `m4_2_credit_soc/` | extension de M4B | introduire \(\gamma\), paires \(k=2\), \(\eta(N)=N\), piloter les avalanches et contrôler l'échelle | effet surtout gouverné par \(K_0/K^*_{\mathrm{aut}}\) ; covariance exacte |
| M4.2B | 30 juillet–6 août | `m4_2b_credit_soc/` | cible de principal arithmétique | queue des intérêts et avalanches simultanées | queue visuellement compatible ; test `/2` erroné puis test `×2` sous-alimenté ; Pareto retenue comme hypothèse |
| M4.3 | 6–11 août | `m4_3_credit_soc/` | reprise de M4.2B à horizon adapté | casser l'anti-corrélation intérêts–avalanches | succès robuste de `gamma_comp_0.6667` ; ablation institutionnelle non tranchée faute de temps |
| M4.3Live | 17–21 août | `m4_3live_credit_soc/` | fork indépendant, parité M4.3 | reprise contrôlée du rebond sur la lignée reconstruite | rebond transitoire ; verdict de long terme dépendant de l'échelle de \(K_0\) |
| M4.3Live-v2 | 21 août | `m4_3live_v2_credit_soc/` | feuille de route | réviser institution de prêt, service et instrumentation | conception seulement, non implémentée ; poursuite arrêtée avec la fin du stage |

**Règles de lecture du registre.** `arborescence_modeles/` contient des liens
symboliques, non des réplications. `modeles-systeme-physicoeconomique/` contient
surtout des adaptateurs pour Simulation Lab. Les PDF sont des rendus des sources
Markdown ou LaTeX correspondantes. Les ZIP conservent des états historiques à
extraire seulement dans un dossier temporaire si une comparaison détaillée est
nécessaire. M4B est une réduction de M4 ; M4.3 hérite du moteur M4.2B ; la parité
homogène de M4.3Live avec M4.3 est testée. Ces liens de filiation interdisent de
présenter chaque ligne comme une confirmation indépendante.

### 3.11 Deux moments de bascule et un résultat partiel central

Le premier moment décisif précède les campagnes statistiques élaborées. Dès les
premiers runs, certaines simulations convergent vers une taille totale bornée,
mesurée en joules, alors qu'aucune limite exogène n'interdit a priori la
divergence. Les mécanismes avaient été conçus pour rendre ce bornage possible,
mais leur coexistence ne garantissait pas qu'un régime stationnaire apparaisse.
Voir « la mayonnaise prendre » a fourni la première preuve de faisabilité du
programme.

Le deuxième moment est l'apparition, dans M4, des premières lois de puissance
associées à de véritables cascades. L'hypothèse était que des régularités
statistiques devaient exister quelque part dans la projection des nombreux
micro-états du système. Leur observation est devenue scientifiquement
convaincante lorsque les distributions ont été accompagnées d'une structure
causale de propagation, d'effets de taille finie et de tests statistiques
adaptés.

Cette découverte intervient après une période où l'hypothèse directrice a été
proche d'être abandonnée. Avant M4, les statistiques obtenues n'apportaient pas
de soutien convaincant et plusieurs phénomènes prometteurs se sont révélés être
des artefacts de simulation : cohortes fondatrices, dérive temporelle des queues
ou synchronisation confondue avec propagation. M4 n'a donc pas seulement ajouté
un résultat positif ; il a empêché qu'une succession de réfutations locales ne
conduise à abandonner prématurément le programme entier.

La synthèse issue de M4 et M4B, encore partielle, peut être formulée ainsi : **la
combinaison d'un flux de naissances, de prêts portant intérêt et d'une érosion
des stocks réels suffit à engendrer un système borné présentant des cascades et
des signatures potentiellement auto-critiques**. Le terme « potentiellement »
reste indispensable : ces résultats soutiennent le programme, mais ne
démontrent pas une SOC universelle. Les expériences postérieures M4.3Live
établissent un rebond interne au modèle sous certaines conventions d'échelle ;
elles ne suffisent pas encore à en faire une explication générale du rebond réel.

## 4. Modèle M4B de référence

### 4.1 État et bilan

Chaque entité \(i\) possède un capital réel productif \(K_i\ge 0\). Un contrat
de prêt est défini par une prêteuse \(\ell\), une emprunteuse \(b\), un principal
nominal \(q\) et un taux par pas \(r\). Les agrégats individuels sont :

\[
C_i=\sum_{(i,b,q,r)}q,\qquad
D_i=\sum_{(\ell,i,q,r)}q,
\]

et la valeur nette est

\[
NW_i=K_i+C_i-D_i.
\]

La nomenclature est interne au toy-model. Le symbole \(K\), historiquement
appelé « capital », représente d'abord la **taille intrinsèque productive** de
l'entité. Il ne correspond pas automatiquement au capital comptable, au
patrimoine total ou aux capitaux propres observés dans les données. Pour une
comparaison avec le patrimoine net comptable, \(NW\) est l'analogue le plus
proche : il combine le stock intrinsèque, les créances détenues et les dettes
dues. Même cette correspondance reste un proxy, car le moteur ne valorise ni
prix de marché, ni actifs hétérogènes, ni passifs autres que les prêts internes.

Le mot « entité » est intentionnellement générique. Le moteur n'encode ni firme,
ni personne, ni machine comme catégorie particulière. Il décrit des unités
homogènes soumises aux mêmes règles ; les différences observées sont émergentes.
L'interprétation économique provient de la production, du crédit, des intérêts
et des faillites, mais la structure formelle peut en principe être transposée à
d'autres systèmes d'unités dissipatives et interconnectées.

Le capital est réel, productif et dépréciable ; le principal est nominal,
perpétuel et non amorti. Cette asymétrie est constitutive : le réseau nominal
peut rester lourd alors que les actifs réels fluctuent ou se déprécient.

### 4.2 Chronologie d'un pas

1. **Naissances.** \(B_t\sim\mathrm{Poisson}(\lambda)\), chaque nouvelle entité reçoit \(K_0\).
2. **Choc multiplicatif.** \(K_i\leftarrow K_i e^{\eta_i}\), avec \(\eta_i\sim\mathcal N(-\sigma^2/2,\sigma^2)\), de moyenne multiplicative unitaire.
3. **Production.** \(K_i\leftarrow K_i+\sqrt{K_i}\).
4. **Intérêts.** L'emprunteuse paie \(\sum rq\) depuis son capital ; en cas d'insuffisance, elle paie au prorata et entre en défaut de service.
5. **Dépréciation.** \(K_i\leftarrow(1-\delta)K_i\), sans dépréciation des principaux.
6. **Marché.** Un round par entité vivante. Parmi \(k\) entités tirées, la plus riche prête à la plus pauvre vers la cible \(K^*=\sqrt{K_\ell K_b}\). Le taux est la moyenne géométrique de leurs rendements marginaux.
7. **Faillites.** Entrée si défaut de service ou \(NW_i<0\). Les créances sur la faillie sont détruites ; ses propres créances sont annulées ; son capital résiduel est détruit. Les nouvelles insolvabilités forment la génération suivante.
8. **Mesures.** Séries, états individuels, réseau et avalanches sont enregistrés sans modifier la trajectoire.

L'ordre est une partie du modèle : le modifier changerait la date de paiement
des nouveaux prêts, l'ensemble des entités admissibles au marché et la
construction des cascades.

### 4.3 Définition causale d'une avalanche

Lorsqu'une emprunteuse meurt, chaque prêteuse perd le principal correspondant ;
cette perte crée une arête dirigée de la morte vers la prêteuse. Une avalanche
est une composante faiblement connexe du graphe de pertes, restreinte aux mortes
d'une même résolution. Deux racines indépendantes restent deux avalanches si
aucune chaîne de perte ne les relie.

Les mesures principales sont la taille, le nombre de racines, la profondeur,
le volume de créances détruites, et le rapport de branchement empirique

\[
b=1-\frac{\sum_a R_a}{\sum_a S_a}.
\]

La mesure inter-pas a été explorée puis écartée des conclusions principales :
elle peut relier fortuitement des événements denses et construire une
composante géante artificielle.

### 4.4 Invariants

- \(K_i\ge0\) par construction.
- La somme des créances égale la somme des dettes.
- La somme des valeurs nettes des survivantes égale leur capital total.
- Les prêts et les intérêts sont des transferts internes. Le bilan réel du pas
  s'écrit : variation du capital total = injections + choc réalisé + production
  − dépréciation − destruction par faillite.
- Les options de mesure ne consomment aucun tirage aléatoire ; les trajectoires
  avec et sans enregistrement sont identiques.

## 5. Méthode expérimentale

### 5.1 Principe général

Le travail a progressivement adopté une logique proche d'un
pré-enregistrement : spécification des métriques, plans et critères de
confirmation avant les runs de production ; séparation entre exploration et
confirmation ; journal des décisions ; conservation des manifestes et des
graines ; audit des invariants et de la provenance du moteur.

Le **pilotage du modèle** en constitue le principe transversal. Pour chaque
mécanisme ou paramètre d'entrée, la démarche cherche à établir une chaîne
lisible :

\[
\text{paramètre ou règle locale}
\longrightarrow \text{dynamique microscopique}
\longrightarrow \text{statistique finale}
\longrightarrow \text{comparaison à une classe empirique}.
\]

Les sweeps, cartes de sensibilité, ablations et contrôles de robustesse ne sont
donc pas des exercices annexes. Ils servent simultanément à déterminer si le
modèle peut reproduire les distributions réelles et à expliquer pourquoi il
les produit. Une correspondance distributionnelle sans mécanisme causal
identifié resterait insuffisante, tout comme un mécanisme élégant incapable de
reproduire les faits stylisés visés.

### 5.2 Campagne M4B

La campagne finale comprend : benchmark, pilotes, sondes de frontière,
variations un facteur à la fois, carte de petite population, plan en hypercube
latin, coupes bidimensionnelles et confirmation indépendante. Au total : 594
runs distincts, zéro échec, zéro censure, environ 22 heures CPU et 8,6 Go.

Le centre de campagne est

\[
(\lambda,\delta,\sigma,K_0,k)=(30,0{,}05,0{,}25,25,3).
\]

L'exploration utilise principalement les graines 1 à 3 ; la confirmation les
graines 11 à 15, avec \(T=4000\) et burn-in \(T/4\). Les contrôles de fenêtre
\(T/8\), \(T/4\) et \(T/2\), ainsi que des horizons jusqu'à 8000 pas, ne
modifient pas les conclusions.

### 5.3 Estimation des distributions

Plusieurs erreurs méthodologiques possibles ont été explicitement contrôlées :

- données discrètes traitées avec des estimateurs discrets ;
- comparaison Pareto/log-normale sur le même support et avec renormalisation ;
- distinction entre loi pure et loi tronquée ;
- seuil \(x_{min}\) comparé entre fenêtres et, lorsque nécessaire, fixé en
  commun ;
- aucun pooling inter-graines ;
- contrôle des cohortes, de l'âge et du renouvellement ;
- séparation entre corps de distribution et queue ;
- rejet des métriques extrêmes trop dominées par la variance des graines.

### 5.4 Traçabilité et reproductibilité

Chaque run conserve configuration, séries temporelles, états individuels,
avalanches, membres d'avalanches, décès, réseau final et résumé de cohérence.
Le moteur M4B est identifié par la version `m4b-mini-3` et le condensat
`f3a7ce02cd9185c7`. Le résidu comptable relatif maximal observé est
\(6,8\times10^{-16}\), et aucune erreur de carnet n'a été détectée.

## 6. Résultats établis de M4B

### 6.1 Un régime stationnaire unique

Sur l'espace exploré

\[
\delta\in[0{,}01,0{,}10],\quad
\sigma\in[0,1],\quad
K_0\in[2,200],\quad
k\in\{2,\ldots,10\},\quad
\lambda\in[1,100],
\]

aucune trajectoire établie ne s'éteint et aucune n'atteint le garde-fou de
population. Les réponses varient continûment. L'extinction observée à petite
\(\lambda\) survient uniquement lorsque le premier tirage de Poisson est nul,
avec probabilité \(e^{-\lambda}\). C'est un artefact d'amorçage, non une
frontière dynamique.

La loi de Little est vérifiée partout à mieux de 1 % :

\[
\frac{\bar N}{\lambda}\simeq \mathbb E[\text{âge au décès}].
\]

La population stationnaire se comprend donc comme le flux de naissance
multiplié par une durée de vie endogène.

### 6.2 Point de référence

Au centre de campagne, mesuré sur cinq graines confirmatoires :

| Grandeur | Valeur |
|---|---:|
| Population / \(\lambda\) | \(14,75\pm0,02\) pas |
| Capital par tête | \(98,8\pm0,3\) J |
| Prêts par tête | \(8,88\pm0,03\) |
| Dette / capital | \(1,39\pm0,05\) |
| Part d'entités endettées | \(0,996\pm0,002\) |
| Gini du capital | \(0,074\pm0,004\) |
| Gini du revenu brut (proxy personnel historique) | \(0,226\pm0,006\) |
| Rapport de branchement | \(0,2968\pm0,0017\) |
| Exposant pur, \(s\ge2\) | \(2,248\pm0,003\) |
| Exposant tronqué | \(2,041\pm0,009\) |
| Coupure ajustée | \(51,6\pm1,8\) |
| Taille maximale | \(54\pm2\) |

Ces valeurs constituent la baseline quantitative à laquelle toute version
suivante doit être comparée.

### 6.3 Hiérarchie des paramètres

**Volatilité \(\sigma\).** C'est le levier dominant de la démographie et de
l'exposition. La durée de vie décroît fortement avec \(\sigma\). La dette
rapportée au capital est non monotone et atteint un maximum vers
\(\sigma\simeq0,15\)–0,20 : les vies sont alors assez longues pour accumuler
des contrats, tandis que les écarts de capital sont suffisants pour générer de
gros prêts. Entre \(\sigma=0\) et environ 0,2, le système traverse une transition
douce d'un régime corrélé et très propagatif vers le plateau ordinaire.

**Échantillon de marché \(k\).** Il modifie peu la démographie, mais fortement
les inégalités et les cascades. Quand \(k\) augmente, le marché sélectionne des
paires plus contrastées et les rapproche de la cible commune ; il égalise le
capital. Le Gini du capital passe d'environ 0,14 à \(k=2\) à 0,01 à \(k=10\),
le rapport de branchement diminue et la queue des avalanches se raidit.

**Capital de naissance \(K_0\).** La durée de vie croît presque linéairement
avec \(\log K_0\). \(K_0\) protège surtout les jeunes sans restructurer
fortement la propagation.

**Dépréciation \(\delta\).** Elle fixe principalement l'échelle du capital. Le
point fixe individuel sans crédit vaut \(K^*=(1/\delta)^2\). Une dépréciation
plus forte réduit le capital par tête et, contre-intuitivement, augmente
modérément la durée de vie. Cette lecture comme paramètre d'échelle est bonne
pour \(\sigma\ge0,2\), mais \(\delta\) module encore la propagation à très faible
volatilité.

**Intensité \(\lambda\).** Elle est un axe de taille finie. Les grandeurs
intensives restent stables ; la coupure, le maximum et la susceptibilité des
avalanches croissent avec la taille du système.

### 6.4 Avalanches et effets de taille finie

La loi de puissance tronquée bat la loi pure dans chaque cellule et chaque
graine confirmatoire. À petite taille, la log-normale discrète peut battre une
loi pure parce que la coupure est visible ; à \(\lambda=100\), la coupure sort
de la fenêtre observable et la loi de puissance pure devient meilleure.

Les scalings mesurés sont :

\[
s_{max}\propto\lambda^{0,58},\qquad
\chi=\frac{\langle s^2\rangle}{\langle s\rangle}\propto\lambda^{0,51},
\]

et la coupure ajustée croît approximativement comme \(\lambda^{1,5}\) entre
\(\lambda=10\) et 30, seule zone où elle est identifiable. L'exposant de la loi
tronquée converge vers environ 2,31 à grande taille.

Hors de la zone \(\sigma\lesssim0,2\), le rapport de branchement reste entre
0,28 et 0,31 pour les variations de \(\sigma\), \(\delta\), \(K_0\) et
\(\lambda\). Il est surtout déplacé par \(k\) et par le régime sans choc. Le
plateau proche de 0,30 est donc une signature institutionnelle de la règle de
marché retenue, non la valeur critique 1 d'un processus de branchement simple.

### 6.5 Valeur nette et inégalités de bilan

Le résultat distributionnel le plus important est que l'inégalité réside dans
les positions de bilan plus que dans le capital productif. Au centre :

\[
Gini(NW)=0,435\pm0,006,\qquad Gini(K)=0,074\pm0,004.
\]

Les deux Gini répondent parfois en sens opposé. Quand \(\sigma\) augmente,
l'inégalité de capital augmente mais l'inégalité de valeur nette diminue, car
les chocs raccourcissent la vie des vieilles créancières. Augmenter \(k\)
écrase l'inégalité de capital sans presque changer l'inégalité de bilan : le
marché égalise les stocks productifs, pas les positions accumulées.

La position nette de crédit \(C-D\) suit un cycle de vie : plongée initiale en
position débitrice, puis remontée vers une position créancière lorsque les
intérêts et les prêts s'accumulent. Au centre, environ 62 % des vivantes sont
nettes débitrices et la corrélation entre position nette et âge vaut 0,52.

La profondeur médiane du trou d'insolvabilité au décès, rapportée au capital
par tête, vaut environ −8,6 % le long de \(\delta\), \(K_0\), \(k\) et
\(\lambda\). Elle dépend surtout de \(\sigma\). Cette invariance est une cible
analytique forte pour la suite.

Le renouvellement rapide du haut de la distribution déjà mesuré ne doit pas
être appelé « mobilité sociale » sans précaution. Il indique que les identités du
top changent, en partie parce que les vies sont courtes et qu'il n'existe ni
héritage ni filiation. Une mesure de mobilité sociale demanderait au minimum une
définition des positions initiales et finales, des matrices de transition entre
quantiles, des horizons comparables et, selon l'objet empirique retenu, un
mécanisme intergénérationnel aujourd'hui absent.

Pour les comparaisons distributionnelles actuelles, quatre variables doivent
donc rester séparées :

- \(K\), stock interne qui détermine la taille et la production dans le modèle,
  sans identification empirique plus précise ;
- \(NW=K+C-D\), taille nette corrigée des positions de crédit, sans
  identification automatique à une catégorie de patrimoine ;
- la puissance ou production physique cumulée
  \(\sum_{t\in W}p_i(t)\), qui mesure le flux extractif rendu accessible ;
- le revenu monétaire usuel sur la même fenêtre, représenté dans l'ontologie
  désormais précisée par la somme des intérêts reçus `int_in`.

Les rapports M4B ont historiquement appelé « revenu » la production plus les
intérêts reçus et ont utilisé la production cumulée comme proxy de chiffre
d'affaires à prix unitaire. Or M4B ne représente ni ventes, ni prix, ni demande
finale : ces correspondances sont des constructions de validation exploratoires.
La clarification de l'auteur privilégie `int_in` pour le revenu usuel et réserve
la production au versant physique. Les anciens résultats ne sont pas renommés
rétroactivement ; leur définition exacte doit rester dans leurs légendes.

### 6.6 Le canal de liquidité est silencieux

Dans la plage principale \(\sigma\le0,5\), aucun défaut de service n'est observé
après burn-in sur les 594 runs. Le canal ne s'active qu'à volatilité extrême,
vers \(\sigma\ge0,85\), et reste marginal. La mortalité de M4B est donc, sur la
plage étudiée, une contagion de bilan : insolvabilité directe ou perte de
créances en cascade.

Ce résultat négatif a une implication de conception. La machinerie de défaut de
service peut être conservée comme garde-fou, mais elle ne doit pas être invoquée
pour expliquer les résultats actuels.

### 6.7 Activité agrégée, croissance et récession

La production totale \(X_t=\sum_i\sqrt{K_i}\) sert d'analogue d'activité. Les
épisodes de croissance ou de récession sont les suites maximales de variations
de même signe de \(\log X_t\).

Le critère de validation retenu pour le stage définit en priorité une récession
comme une contraction de la **quantité totale d'énergie présente dans le
système**, mesurée en fin de pas :

\[
E_t=\sum_i K_i(t).
\]

La lecture d'Ormerod et Mounfield précise la cible externe potentielle : il faut
comparer les **distributions complètes** de durée et d'amplitude, ainsi que leurs
ruptures éventuelles, et non seulement leurs moyennes. Cette comparaison n'est
pas encore réalisée. Elle exigera une définition temporelle compatible, des
ajustements non groupés menés run par run et une séparation entre calibration et
validation ; les exposants historiques de données annuelles ne peuvent pas être
transférés directement aux pas abstraits de M4B.

La fréquence, la durée et l'amplitude pic–creux des épisodes négatifs ont été
recalculées sur les séries déjà enregistrées, sans nouveau run, en appliquant
exactement le protocole utilisé pour \(X_t\). La production et le stock restent
deux observables liées mais non équivalentes, puisque la concavité de la
production et les variations de population changent leur relation.

Au centre, le système alterne environ 487 épisodes par millier de pas. Les
durées moyennes sont proches de deux pas, avec des maxima de 10 à 13 pas. Les
phases sont au niveau ou sous la référence géométrique d'incréments indépendants
: il n'existe pas de longues récessions endogènes dans M4B à l'échelle brute.

La volatilité de la croissance suit \(\lambda^{-0,50}\), signature d'une somme
d'aléas quasi indépendants. Elle possède un minimum vers \(\sigma\simeq0,1\),
interprété comme la frontière entre bruit endogène des cascades à faible
\(\sigma\) et bruit exogène des chocs à fort \(\sigma\).

La skewness des variations est toujours négative. À faible \(\sigma\), les
récessions sont plus courtes et plus raides que les expansions : montée lente,
chute brutale. Cette asymétrie disparaît lorsque la série est lissée à 25 pas ;
elle vit à l'échelle des cascades intra-pas, pas à celle de grands cycles.

Enfin, le temps de corrélation intégré de l'activité suit la durée de vie
moyenne, avec une corrélation de rang de 0,93 entre cellules. La démographie est
l'horloge de la persistance macroéconomique du modèle.

**Résultat provisoire sur l'énergie totale.** Au point central, sur cinq graines
confirmatoires et une fenêtre de 3 000 pas par graine :

- la fréquence vaut \(252,4\pm4,4\) récessions par millier de pas ;
- la durée moyenne vaut \(1,930\pm0,042\) pas, contre
  \(2,035\pm0,033\) pour les expansions ; les plus longues récessions
  durent 10 à 11 pas ;
- l'amplitude logarithmique moyenne vaut \(0,0361\pm0,0007\), soit une
  perte pic–creux représentative d'environ 3,5 % ; le quantile 90 correspond à
  environ 7,5 %, et la plus forte baisse observée sur ces cinq graines à
  environ 23 % ;
- les récessions sont environ 5,5 % plus raides que les expansions et la
  skewness des variations vaut \(-0,233\pm0,021\).

Le screening LHS montre une séparation nette des contrôles. La fréquence varie
peu et n'est expliquée de façon robuste par aucun paramètre
\(R^2_{\mathrm{CV}}<0\). L'amplitude moyenne est au contraire presque
entièrement pilotée par \(\sigma\) (PRCC \(+0,983\)) et par \(K_0\)
(PRCC \(-0,801\), \(R^2_{\mathrm{CV}}=0,989\)). Le temps de mémoire de
\(\log E_t\), égal à \(23,2\pm1,4\) pas au centre, diminue fortement avec
\(\sigma\) (PRCC \(-0,900\)). Enfin, la baisse de l'amplitude entre
\(\lambda=10\) et \(\lambda=100\) confirme une composante de taille finie.

Ainsi, M4B engendre de nombreuses contractions courtes dont la fréquence est
relativement institutionnelle, tandis que leur profondeur dépend de
l'intensité des chocs et de la protection initiale. Ce résultat établit une
baseline interne ; il ne constitue pas encore une validation externe, faute
d'une correspondance entre un pas du modèle, une période réelle et un jeu de
données empirique choisi.

La littérature Zotero confirme que la définition empirique est elle-même un
choix scientifique. Wright définit une récession comme une suite d'années de
croissance négative du PIB. Il rapporte, pour 17 économies occidentales entre
1871 et 1994, une majorité d'épisodes d'un an et peu d'épisodes au-delà de six
ans, mais signale qu'une étude ultérieure sur un jeu de données plus large
préfère une loi de puissance à une loi exponentielle pour les durées. Une autre
référence citée par Wright étudie conjointement durée et magnitude. La cible ne
peut donc pas être « reproduire une loi universelle des récessions » : il faut
fixer le jeu empirique, la résolution temporelle et la définition du seuil,
puis comparer durée, fréquence et amplitude sur les mêmes conventions.

## 7. Résultats négatifs et corrections de trajectoire

Les résultats suivants doivent être conservés dans tout rapport long, car ils
expliquent la construction du modèle final.

1. La première bimodalité n'établissait pas deux classes économiques : elle
   reflétait principalement la cohorte fondatrice et les entrantes.
2. La première queue lourde n'était pas stationnaire : son exposant dérivait
   avec l'horizon.
3. Dans M2, le crédit n'était pas causal sur les distributions principales.
4. Dans M3, le crédit était causal sur la démographie mais non sur les formes
   distributionnelles de la baseline.
5. La neutralité distributionnelle du crédit dans M3 était conditionnelle à la
   règle de comportement : elle disparaissait avec la règle de revenu X1, sans
   faire apparaître de SOC.
6. La liquidité de M3 n'était pas Boltzmann--Gibbs, bien qu'elle fût la variable
   la plus proche de celle visée par l'argument d'échange conservatif.
7. Les chocs sectoriels corrélés fabriquaient des morts synchronisées, pas une
   cascade de propagation.
8. Une régression log-log avec bon \(r^2\) ne suffit pas à identifier une loi de
   puissance ou une SOC.
9. Le GB2 pouvait gagner l'AIC en se plaçant sur une forme numérique dégénérée ;
   un bon score n'assure pas une famille interprétable.
10. La profondeur maximale de cascade est dominée par la variance des graines et
   n'est pas une bonne observable de pilotage.
11. La coupure ajustée est trop bruitée cellule par cellule ; son intérêt est
   principalement dans le scaling en taille.
12. M4B ne présente ni transition extinction/croissance, ni longue récession,
    ni défaut de liquidité significatif sur sa plage principale.
13. M4 et M4B ne sont pas deux confirmations indépendantes.
14. Plusieurs critères externes initialement envisagés ne disposent pas encore
    d'une cible académique assez solide et compatible pour réfuter ou valider le
    modèle ; ce défaut de comparabilité est lui-même un résultat du stage.
15. M4B n'avait pas mesuré l'effet rebond. La première expérience dynamique
    remonte à la variante `alpha_plus_10pct` du modèle 4-05, mais ses archives
    présentent une discordance de graines et son architecture est ensuite
    discréditée par l'artefact de cohortes. M4.3Live reprend la mesure sur la
    lignée reconstruite ; son verdict dépend de la portée, de l'horizon et du
    traitement de \(K_0\), et sa généralisation empirique reste ouverte.

## 8. Interprétation scientifique

### 8.1 Boucle accumulation–relaxation

Le marché reconstruit en permanence un réseau nominal d'expositions. La
production et les transferts entretiennent le capital réel ; les chocs et la
dépréciation déplacent les bilans. Lorsqu'une entité devient insolvable, ses
créancières perdent leur actif nominal sans récupération. Certaines deviennent
insolvables à leur tour. La cascade détruit capital et créances, puis les
naissances et le marché reconstruisent le réseau.

Cette boucle explique la propagation. Elle ne démontre pas à elle seule une SOC
universelle. Le rapport de branchement reste sous-critique au sens simple et la
fenêtre dépend de l'institution « un round de marché par tête ». La meilleure
formulation actuelle est : un régime de cascades à queue tronquée,
auto-entretenu par l'accumulation et l'élagage du réseau dans une fenêtre
institutionnelle robuste.

### 8.2 Séparation des rôles

Les paramètres n'agissent pas tous comme des « boutons » concurrents sur un
même résultat. Ils définissent des axes presque orthogonaux :

- \(\sigma\) : forme du risque individuel, durée de vie, exposition ;
- \(k\) : qualité de l'appariement, égalisation du capital, propagation fine ;
- \(K_0\) : vulnérabilité des jeunes ;
- \(\delta\) : unité de capital et temps de relaxation ;
- \(\lambda\) : taille du système et effets de coupure.

Cette séparation autorise une réduction future et suggère un
adimensionnement, mais elle ne permet pas encore de supprimer \(\delta\) sans
analyse, notamment à faible volatilité.

### 8.3 Le bilan comme mémoire

Le capital est fortement égalisé par le marché et oublie relativement l'âge.
La valeur nette conserve la trace des dettes, créances et intérêts cumulés.
Elle porte donc l'inégalité, le cycle de vie et la condition de mortalité. Le
modèle suggère une distinction conceptuelle utile : des stocks productifs
homogènes peuvent coexister avec des positions financières très inégales.

### 8.4 La démographie comme horloge macroéconomique

La loi de Little et la corrélation entre mémoire de l'activité et durée de vie
indiquent qu'une grande partie de la dynamique agrégée est une dynamique de
renouvellement. Cette observation protège contre une surinterprétation
macroéconomique : des oscillations peuvent provenir de la durée de vie des
unités plutôt que d'un cycle autonome de long terme.

## 9. De la première expérience historique à la mesure reconstruite du rebond

La première expérience explicitement consacrée à l'effet rebond est la campagne
`alpha_plus_10pct` de `anciens_modeles/4-05-dynamique/`, fin avril–début mai.
Elle annonce un effet positif sur l'extraction et le crédit, avec la discordance
documentaire signalée en section 3.3. La requalification des premières classes
comme artefact de cohortes interdit d'en faire le résultat final du stage.
M4.3Live constitue donc une reprise contrôlée de la question après la
reconstruction M2–M4.3, et non sa première apparition.

### 9.1 Ce que M4B avait rendu possible

M4B fournit la base expérimentale nécessaire : régime stationnaire, taille de
système contrôlable par \(\lambda\), comptabilité exacte, séries de production,
capital, crédit, intérêts et démographie, ainsi qu'une baseline de fluctuations
et de cascades. Mais il ne sépare pas clairement une ressource consommée d'un
service rendu. À ce stade du travail, une hausse de \(\sum_i\sqrt{K_i}\) ne
pouvait donc pas être appelée « rebond » sans protocole supplémentaire.

### 9.2 Protocole M4.3Live et définition de travail

M4.3Live rend \(A\) et \(\gamma\) propres à chaque entité et modifiables pendant
le run. Une intervention peut toucher toutes les entités, seulement les
nouvelles, ou une fraction des vivantes. Chaque trajectoire traitée est comparée
à une trajectoire contrefactuelle utilisant le même état initial et les mêmes
tirages aléatoires ; le journal d'interventions permet de rejouer exactement le
protocole.

La définition de travail retient deux mesures complémentaires. \(E\) est le
rapport entre la réponse observée et la réponse strictement proportionnelle
\((m-1)p\), où \(m\) est le multiplicateur de \(A\) et \(p\) la part de
production traitée avant intervention. \(E>1\) est qualifié de rebond dans le
modèle. Pour les interventions globales, on rapporte aussi l'élasticité
logarithmique \(\varepsilon=\mathrm d\ln(\mathrm{prod})/\mathrm d\ln A\).
Cette définition permet une mesure interne, mais ne résout pas encore la
correspondance empirique entre production, service utile et ressource physique
consommée.

### 9.3 Résultats selon la portée, l'horizon et l'échelle

Les résultats ne se résument pas à un verdict binaire.

- **Portée partielle, court horizon :** le rebond est observé. Le rapport \(E\)
  est compris entre 2,3 et 2,9, sur deux amplitudes, trois intensités et avec des
  écarts de 3 à 48 écarts-types par rapport au bruit apparié.
- **Portée partielle, long horizon :** le verdict devient non tranchable. La
  cohorte traitée finit par disparaître et sa part dans la population tend vers
  zéro ; le dénominateur même de la mesure s'éteint en l'absence de transmission
  du traitement aux nouvelles entités.
- **Portée globale, \(K_0\) fixe, régime établi :** la réponse est
  sous-proportionnelle. Une hausse de \(A\) de 50 % augmente la production
  agrégée de 36,1 %, soit \(E\simeq0{,}72\) et une élasticité logarithmique
  \(\varepsilon\simeq0{,}76\). La production par entité est multipliée par
  environ 1,80, mais la population par 0,754.
- **Portée globale, \(K_0\) compensé :** lorsque le capital de naissance suit
  l'échelle technologique, la population reste pratiquement inchangée et le
  rebond établi devient fort. Pour le contraste principal, la campagne mesure
  \(E\simeq2{,}53\) et \(\varepsilon\simeq2{,}02\).

Le dernier résultat s'explique par la covariance d'échelle. Sous compensation
de \(K_0\), le niveau agrégé varie théoriquement comme

\[
A^{1/(1-\gamma)},
\qquad
\varepsilon=\frac{1}{1-\gamma}.
\]

Cette loi est démontrée pour le moteur homogène et vérifiée numériquement à la
précision machine pour plusieurs valeurs de \(\gamma\). Elle explique pourquoi
la réponse peut être super-proportionnelle sans invoquer rétrospectivement un
mécanisme comportemental absent du code.

### 9.4 Portée du résultat

M4.3Live établit donc l'existence d'un rebond **dans ce modèle**, sous une
définition opérationnelle explicite. Il montre surtout que le verdict de long
terme est conditionnel à une décision de modélisation : le capital fourni aux
nouvelles entités reste-t-il fixe en unités absolues, ou suit-il l'échelle
technologique ? L'effet observé affine l'hypothèse initiale d'un rebond endogène,
mais ne la valide pas encore comme explication générale des sociétés réelles.

La campagne vise d'abord l'observation, non l'attribution causale complète. Elle
reste limitée par une institution de crédit particulière, un nombre restreint
de paramètres et de graines, l'absence de calibration empirique et l'absence de
séparation explicite entre ressource, service et consommation finale. La
distinction entre résultat interne, interprétation du mécanisme et validation
externe doit donc rester visible dans le rapport.

## 10. Prototype Boltzmann–Pareto et difficulté de validation

### 10.1 Pourquoi ce chantier est secondaire

Le chantier Boltzmann–Pareto ne constitue pas la prochaine version principale
du moteur. Il explore une difficulté rencontrée au moment de choisir les faits
stylisés qui permettraient de juger le modèle plausible. Yakovenko décrit une
distribution en deux régimes au moyen d'un ajustement à trois paramètres ;
d'autres familles, dont la double Pareto-lognormale, utilisent quatre paramètres
ou davantage et peuvent mieux décrire les données.

L'arbitrage est délicat. Plus une famille possède de paramètres, plus elle peut
épouser une distribution empirique, et moins la qualité du fit suffit à appuyer
le mécanisme. Mais une loi analytique à quatre paramètres n'est pas forcément un
artifice statistique : un mécanisme réel comportant plusieurs échelles ou
régimes peut produire légitimement une telle forme. La parcimonie du fit et la
complexité du phénomène ne doivent donc pas être confondues.

La difficulté est renforcée par l'absence, dans la littérature consultée à ce
stade, d'une caractérisation simple et unifiée de la distribution de la
consommation d'exergie entre agents. Identifier une cible empirique énergétique
demanderait une recherche spécifique, distincte de la construction du moteur.

### 10.2 Résultats provisoires

Le chantier théorique le plus récent part de la valeur nette comme variable
cible. Il cherche à réunir dans un même système :

- un régime additif près du plancher, susceptible de produire un corps
  exponentiel ;
- un régime multiplicatif pour les entités établies, susceptible de produire
  une queue de Pareto ;
- une absorption à \(NW=0\) et une réinjection par les naissances ;
- une rétroaction entre concentration du crédit, cascades et exposant de queue.

Le prototype complet documenté obtient provisoirement : population bornée,
queue stable entre fenêtres avec exposants autour de 2,80–2,88, faible
corrélation âge–log(capital) autour de 0,12 et queue subsistant à âge contrôlé.
Le corps est mieux décrit par des familles gamma, log-normale ou Fisk que par
l'exponentielle stricte. Trois des quatre cibles sont donc atteintes ; la cible
Boltzmann reste ouverte.

L'interprétation auto-critique de la stabilité de l'exposant est encore une
hypothèse. Le bruit multiplicatif individuel \(\sigma\) est exogène dans le
prototype ; la formulation honnête est que le réseau de crédit pourrait
stabiliser et structurer une multiplicativité donnée, non nécessairement la
créer ex nihilo.

### 10.3 Proposition de doctrine de validation

La plausibilité du toy-model ne devrait pas reposer sur un unique ajustement de
distribution. Une doctrine de validation adaptée à ce programme peut être
organisée en cinq niveaux :

1. **Validité interne** : invariants comptables, reproductibilité, absence
   d'artefacts de mesure et stationnarité.
2. **Validité mécanistique** : chaque phénomène doit disparaître ou changer de
   manière prévisible lorsque son mécanisme supposé est retiré par ablation.
3. **Faits stylisés multiples** : le même jeu de règles doit reproduire plusieurs
   propriétés non redondantes — bornage, renouvellement, distribution des
   bilans, cascades, effets de taille finie, temporalité de l'activité — plutôt
   qu'un seul histogramme.
4. **Robustesse sans réglage fin** : les formes qualitatives doivent persister
   sur une région de paramètres ; les paramètres peuvent déplacer les échelles
   ou les exposants sans faire disparaître immédiatement le régime.
5. **Prédiction hors calibration** : une partie des observables sert à choisir le
   modèle, puis d'autres observables ou d'autres tailles de système servent à le
   tester. Un meilleur fit in-sample ne suffit pas si les prédictions nouvelles
   sont moins bonnes.

Dans cette perspective, le nombre de paramètres d'une loi ajustée devient un
élément du diagnostic, mais non le juge unique. Le véritable arbitrage porte sur
la complexité du **mécanisme** nécessaire pour reproduire conjointement des
phénomènes indépendants.

Pour l'application aux sociétés capitalistes, trois familles de tests sont
prioritaires sur les distributions :

- les classes de distribution des revenus des personnes et des entreprises,
  étudiées d'abord séparément ;
- les classes de distribution distinctes de la taille \(K\) et de la taille
  nette \(NW\), sans leur imposer une identification patrimoniale précise ;
- la mobilité entre positions de la distribution, qui n'est pas encore une
  observable correctement définie dans le moteur.

La première de ces cibles doit être formulée comme une batterie de diagnostics,
et non comme le choix anticipé d'une loi :

- tester si personnes et entreprises relèvent effectivement d'une même famille
  de distribution ; en cas de réponse négative, vérifier si deux régions de
  paramètres du même moteur reproduisent séparément les deux cibles plutôt que
  les agréger ;
- utiliser pour les entreprises le niveau du chiffre d'affaires, sans le
  confondre avec sa croissance, l'emploi, les actifs ou la capitalisation ;
- si `int_in` est comparé aux personnes, utiliser comme cible le revenu brut
  annuel avant impôts tout en signalant que l'étiquette « intérêt » du moteur
  représente abstraitement l'ensemble du revenu usuel, et non sa seule
  composante financière ;
- comparer au minimum corps exponentiel, lognormal, gamma et Fisk, puis queue de
  Pareto et alternatives à queue lourde ;
- estimer séparément la position du coude, la fraction de population dans la
  queue, la fraction de revenu qu'elle reçoit, le Gini et l'exposant de CCDF ;
- pénaliser explicitement la complexité des familles, puis réserver des fenêtres
  ou des graines au test hors calibration ;
- vérifier la stabilité temporelle et la sensibilité au choix du seuil ;
- contrôler que l'agrégation sur plusieurs longueurs de fenêtre ne change pas
  la famille retenue, puisque le pas n'a pas d'équivalent calendaire fixé ;
- ne comparer aux données personnelles de Yakovenko ou Wright, ou à des comptes
  d'entreprises, que si l'entité, le revenu et la période comptable du modèle
  ont reçu une interprétation compatible.

Une quatrième famille de tests concerne la dynamique agrégée : durée, fréquence
et amplitude des récessions, définies comme des contractions de l'énergie totale
\(E_t=\sum_iK_i(t)\). Ces statistiques doivent être calculées conjointement :
reproduire une durée sans reproduire la fréquence ou la profondeur des épisodes
ne suffirait pas à établir la plausibilité dynamique.

À ces critères de plausibilité s'ajoute un critère de réfutation structurelle.
M4.2 a commencé à comprendre et manipuler l'exposant des cascades, en montrant
notamment le rôle de l'échelle autarcique. Si cet
exposant reste verrouillé loin de la valeur observée sur les cascades
d'entreprises réelles, malgré des variations institutionnelles justifiables,
l'échec devra conduire à restructurer les hypothèses plutôt qu'à multiplier les
paramètres de calibration.

Cette règle de réfutation reste suspendue à l'identification d'une donnée
comparable. L'exposant \(3/2\) de Watts est un résultat théorique de percolation
sur graphe aléatoire, pas un étalon empirique de faillites. De même, une loi de
puissance sur la taille des firmes qui font faillite ou sur la fréquence annuelle
des disparitions ne mesure pas la taille d'une cascade causale. Il faudra soit
trouver un jeu de données reliant explicitement défauts racines et défauts
descendants, soit redéfinir honnêtement le test externe.

### 10.4 L'absence de données directement comparables comme résultat

La recherche bibliographique n'a pas seulement fourni des valeurs de référence.
Elle a révélé que plusieurs questions apparemment simples ne disposent pas
d'une réponse académique unique directement utilisable :

- la « distribution des revenus » dépend de l'unité, du périmètre fiscal, de la
  fenêtre, du traitement des revenus du capital et de la famille ajustée ;
- la « taille d'une firme » peut désigner emploi, ventes, actifs ou
  capitalisation, et la loi de son niveau ne doit pas être confondue avec celle
  de son taux de croissance ;
- les travaux sur les faillites mesurent taille des firmes faillies, fréquence
  des disparitions ou événements agrégés, rarement une chaîne causale
  racine–descendants comparable aux avalanches M4B ;
- la consommation d'énergie ou d'exergie varie avec la définition du
  consommateur, l'énergie primaire ou utile, l'échelle sectorielle et le
  domaine étudié ;
- les durées de récession sont décrites par des lois différentes selon les jeux
  de données et les conventions de datation ;
- la mobilité sociale exige des trajectoires, des horizons et souvent une
  structure intergénérationnelle absente du moteur.

Cette difficulté n'est pas un simple retard de bibliographie. Elle est un
résultat sur la construction des faits empiriques : les données ne répondent
pas spontanément à une question théorique ; elles deviennent comparables après
un travail de définition, de mesure et de choix d'échelle.

Un texte de candidature rédigé pendant le stage montre que ce constat est
contemporain de la recherche et non une rationalisation rétrospective. Anatole
y décrit le vertige provoqué par des centaines d'articles pertinents, dont les
méthodes et conclusions nourrissent le travail sans répondre directement à ses
questions. Cette expérience constitue un fil narratif important : l'obstacle
n'est pas l'absence de littérature, mais l'écart entre une littérature abondante
et la donnée précisément nécessaire pour réfuter une hypothèse particulière.

La conséquence épistémique doit être formulée avec précision. En l'absence de
cible solide, on ne peut ni valider le modèle par ressemblance, ni le rejeter
sur la base d'un exposant ou d'une famille choisis arbitrairement. Le verdict
externe est **suspendu**. Le modèle peut être conservé tel quel comme candidat
minimal tant qu'il satisfait ses tests internes et qu'aucune observation
compatible ne le réfute. Cette non-réfutation est informative pour la poursuite
du programme, mais elle ne doit jamais être convertie en preuve de réalisme.

Ce constat déplace une partie du travail futur : avant d'ajouter de la
complexité au moteur pour améliorer un fit, il faut construire ou identifier
l'objet empirique qui rendrait ce fit probant. Une extension n'est justifiée
que si elle répond à une cible définie, à un échec mécanistique interne ou à une
prédiction hors calibration ; l'absence de données n'est pas une raison pour
multiplier les paramètres.

### 10.5 Dictionnaire de correspondance entre modèle et données

Ce dictionnaire doit accompagner toute comparaison externe afin d'éviter les
homonymies trompeuses.

| Variable du modèle | Sens interne exact | Analogue empirique possible | Limite principale |
|---|---|---|---|
| \(K_i\), « capital » | taille intrinsèque productive, réelle et dépréciable | capacité ou actif productif abstrait | pas le patrimoine ni les capitaux propres comptables |
| \(NW_i=K_i+C_i-D_i\) | valeur nette interne après créances et dettes | patrimoine net ou capitaux propres | valorisation nominale simplifiée, sans prix de marché |
| production \(F_\gamma(K_i)\) | puissance extractrice : capacité de l'entité à grossir en fonction de sa taille \(K\) et de sa technologie ; terme productif positif, distinct de la croissance nette | énergie ou travail utile ; historiquement proxy du chiffre d'affaires | érosion, intérêts, transferts et défauts modifient ensuite le bilan ; pas de mesure séparée du service final |
| intérêts reçus `int_in` | transfert entrant versé par les emprunteuses | revenu monétaire usuel dans l'ontologie de l'auteur | ne doit pas être lu littéralement comme le seul revenu financier réel |
| principal \(q\), créances \(C\), dettes \(D\) | mise à disposition de stock productif et droits nominaux associés | investissement dans une machine ou financement d'un équipement | ni machine séparée, ni contrat réel, ni prix de l'actif |
| \(E_t=\sum_iK_i\) | stock réel total présent dans le système | taille ou capacité énergétique agrégée | ne mesure pas directement la consommation finale d'énergie ou d'exergie |
| avalanche | morts reliées causalement par destruction de créances | cascade de faillites | les données réelles identifient rarement les liens racine--descendants |
| rapport \(b\) | fraction moyenne de morts non racines, intensité de propagation | rapport de branchement d'une contagion | proximité de un = criticité de branchement, pas preuve suffisante de SOC |

La priorité n'est donc pas de faire coïncider deux histogrammes portant le même
nom, mais de vérifier que l'unité statistique, le bilan, le flux et la fenêtre
temporelle décrivent des objets réellement comparables.

## 11. Limites générales

- Le modèle est abstrait et non calibré sur une économie réelle.
- Le joule est actuellement une unité comptable abstraite. L'interprétation de
  la monnaie comme droit d'accès à l'exergie justifie la lecture énergétique de
  l'ensemble du programme, mais elle n'est ni imposée par les équations de
  M4B, ni validée par ses simulations.
- La généralité de la notion d'entité augmente la portée formelle du modèle,
  mais rend le choix d'une cible empirique moins immédiat : toute validation
  externe doit préciser le système concret auquel elle se rapporte.
- Les applications « personne » et « entreprise » sont deux paramétrisations
  possibles du même moteur, non deux types d'agents coexistants. Le stage ne
  cherche pas à construire une économie articulant ménages et firmes.
- \(K\) et \(NW\) restent des mesures abstraites de taille et de taille nette.
  Leur identification à du capital humain, des actifs productifs, des capitaux
  propres ou un patrimoine précis dépasserait l'ambition du travail.
- La mobilité du sommet actuellement mesurée est un renouvellement
  démographique, pas encore une mobilité sociale comparable aux statistiques
  empiriques.
- L'ontologie précisée associe les revenus usuels aux intérêts reçus et la
  production au versant physique. Les rapports antérieurs ont utilisé d'autres
  proxys — production cumulée pour le chiffre d'affaires, production plus
  intérêts pour le revenu brut — qui restent valides comme définitions de leurs
  statistiques, mais pas comme identifications économiques démontrées.
- L'analogie de la machine n'est pas encodée littéralement : le moteur ne sépare
  ni outil ou machine, énergie incorporée, maintenance, service utile et
  surplus, ni classes ouvrière et capitaliste.
- La littérature Zotero examinée porte surtout sur des revenus individuels ou
  fiscaux annuels. Elle documente les taux de croissance des ventes des firmes
  et des lois de taille, mais pas encore de façon assez précise la distribution
  du niveau des chiffres d'affaires. Les mesures de « taille » doivent être
  désambiguïsées dans leurs sources primaires.
- L'étiquette temporelle d'un pas n'est pas requise pour comparer des familles
  à échelle près, mais la longueur de la fenêtre d'agrégation peut modifier la
  forme d'une distribution de flux. Cette robustesse reste à tester.
- Un futur test de mobilité intergénérationnelle demanderait d'ajouter un
  mécanisme de filiation et de transmission qui n'existe pas dans M4B.
- La cible empirique de l'exposant des cascades d'entreprises doit encore être
  fixée à partir d'une définition et d'un jeu de données compatibles avec la
  définition causale des avalanches du modèle.
- Les contractions de l'énergie totale ont désormais une baseline interne,
  mais pas de cible empirique alignée. Contrairement à la seule comparaison des
  familles distributionnelles, une comparaison quantitative de leur durée et
  de leur fréquence exigera une correspondance temporelle.
- Les prêts sont perpétuels, nominaux et sans récupération : ce sont des choix
  institutionnels forts, utiles pour isoler un mécanisme, non des descriptions
  universelles du crédit.
- Le marché sélectionne la plus riche et la plus pauvre d'un échantillon ; la
  portée empirique de cette règle reste à discuter.
- Le modèle n'a ni ménages, ni firmes explicitement distinctes, ni prix, ni
  travail, ni consommation finale.
- Les horizons numériques ne permettent pas d'exclure des métastabilités très
  longues.
- Les estimations de queue et de coupure sont sensibles à la taille finie ; les
  comparaisons de familles restent des diagnostics, non des preuves de mécanisme.
- La campagne de sensibilité, bien que large, n'est pas une analyse de Sobol.
- Les extensions valeur nette et cycles ont été menées après l'audit principal
  sur les mêmes runs ; elles sont confirmées sur graines séparées mais restent
  des analyses post-hoc explicitement étiquetées.
- Un rebond est établi à l'intérieur de M4.3Live sous certaines conventions ;
  ni sa généralité empirique ni son attribution à un mécanisme socio-économique
  réel ne sont établies. Le corps Boltzmann reste lui aussi non confirmé.

## 12. Contributions du stage

### 12.1 Contributions scientifiques

- Obtention d'un système total borné sans plafond dynamique actif, malgré une
  possibilité a priori de divergence.
- Construction progressive d'un modèle multi-agents de crédit physico-économique.
- Formulation explicite du postulat reliant transferts monétaires et droits
  d'accès à l'exergie, avec séparation entre son rôle structurant et son statut
  non démontré.
- Identification et correction d'un artefact de cohorte dans les premières distributions.
- Recodage et test statistique de modèles de référence en econophysique.
- Mise en évidence de la neutralité distributionnelle du crédit dans certaines versions, puis des conditions qui la rompent.
- Distinction empirique entre synchronisation des morts et propagation causale.
- Identification de la règle annulation–destruction comme mécanisme minimal de contagion.
- Réduction de M4 en moteur M4B auditable.
- Campagne de sensibilité complète avec confirmation indépendante.
- Mise en évidence du rôle de la valeur nette, du cycle de vie débiteur–créancier et de l'horloge démographique.
- Première expérience de rebond dans la branche dynamique 4-05, puis reprise
  contrôlée par une expérience appariée M4.3Live sur la lignée reconstruite,
  avec identification d'une dépendance décisive à l'échelle de \(K_0\).
- Cartographie des lacunes de comparabilité empirique pour les revenus, chiffres
  d'affaires, cascades, consommations d'exergie, mobilité et récessions.

### 12.2 Contributions méthodologiques et techniques

- Démarche en accordéon : enrichissement exploratoire, ablations, élagage et
  validation du noyau minimal.
- Architecture séparant moteur, données primaires, analyse et visualisation.
- Simulation Lab pour cataloguer, lancer et comparer les expériences.
- Invariants comptables automatisés et tests de neutralité des mesures.
- Manifestes de campagne, graines séparées et journal de décisions.
- Estimateurs discrets et tests de lois corrigés pour la troncature.
- Analyse multi-graines, OAT, hypercube latin, surfaces de réponse et coupes 2D.
- Conservation de résultats négatifs et traçabilité des changements de modèle.
- Registre scientifique associant chaque article transmis à son fichier
  canonique, son empreinte, son apport réel et ses précautions de citation.

### 12.3 Apprentissages du métier de chercheur

Le coût principal du travail n'a pas été un mécanisme particulier abandonné,
mais la présence d'artefacts de simulation dans des résultats d'abord jugés
prometteurs, ainsi que la complexité excessive du premier modèle. Ces échecs
n'ont pas constitué une perte sèche. Ils ont fait émerger plusieurs compétences
et règles de conduite scientifique :

- distinguer un phénomène robuste d'un effet de cohorte, de pooling, d'horizon
  ou d'implémentation ;
- construire une question par ablations successives plutôt que défendre le
  premier modèle qui semble fonctionner ;
- considérer les résultats négatifs comme des contraintes qui améliorent
  l'architecture suivante ;
- questionner la probité d'un ajustement lorsque le nombre de paramètres
  augmente ;
- accepter qu'une question formulée simplement — par exemple « quelle est la
  distribution des consommations d'énergie ? » — puisse recevoir plusieurs
  réponses légitimes selon la définition, l'échelle et le domaine.

La trajectoire M1–M4B est ainsi aussi un apprentissage de la structuration d'un
travail de recherche : définition des objets, séparation entre exploration et
confirmation, traçabilité, formulation de critères de réfutation et révision
d'une interprétation séduisante lorsqu'elle repose sur un artefact.

### 12.4 Place de l'encadrement et origine du programme

Les idées et choix scientifiques exposés dans ce mémo ont été formulés par
Anatole. Les encadrants ont joué un rôle de garde-fou, d'aide systémique et
méthodologique : apprendre où chercher une information, comment organiser une
recherche, éprouver une hypothèse et situer un résultat. Ils ont également été
une source d'inspiration importante au cours des discussions.

Selon le témoignage explicite d'Anatole, les échanges avec les encadrants ont
été longs, nombreux et scientifiquement nourrissants ; ils ont supervisé et
validé le travail. La conception des modèles et les décisions de recherche
restent néanmoins attribuées à Anatole. En l'absence de compte rendu précis, le
rapport ne devra pas assigner arbitrairement à un encadrant l'origine d'une
équation ou d'une bifurcation particulière.

Cette répartition ne doit pas être racontée comme une comptabilité simpliste de
la « parentalité » de chaque idée. La recherche s'est construite en réflexion
avec les encadrants, aux deux sens du terme : réflexion intellectuelle et
réflexion par confrontation, déplacement ou opposition. Une discussion sur un
sujet tiers peut modifier profondément une intuition sans que l'idée résultante
soit directement attribuable à une phrase ou à une personne. Le rapport devra
donc reconnaître précisément la fonction de l'encadrement sans lui attribuer ni
lui retirer artificiellement chaque micro-décision.

## 13. Pistes de rédaction et travaux non réalisés à la clôture du stage

Le stage s'est terminé avant que les ablations de M4.3 ou la feuille de route
M4.3Live-v2 soient poursuivies. Les points ci-dessous distinguent donc les tâches
de rédaction encore utiles des expériences restées à l'état de pistes ; ils ne
décrivent pas une campagne active.

### Court terme

1. Organiser le rapport autour de la trajectoire complète : intuition
   métabolique et statistique, construction du toy-model, réfutations
   successives, mécanisme de cascades, puis expérience dynamique de rebond.
2. Consolider le registre des modèles avec les dates que les prochains
   témoignages de l'auteur permettront de préciser ; conserver séparément dates
   de conception, premiers runs, campagnes et clôture.
3. Formaliser la définition physique du rebond : ressource mobilisée, service
   utile, gain technique attendu et consommation contrefactuelle.
4. Archiver le protocole M4.3Live-v1, ses graines, ses contrastes et sa preuve
   d'échelle de façon à rendre le verdict indépendant de l'interface live.
5. Tester la robustesse du verdict aux tailles de population, aux graines, aux
   amplitudes, aux fenêtres et à plusieurs régimes du marché de crédit.
6. Sélectionner six à huit figures principales et reconstruire leurs légendes
   pour un lectorat non familier du dépôt.
7. Transformer les références Zotero en bibliographie homogène et expliciter la
   filiation Bak--Yakovenko--Hendrick sans confondre résultats publiés et
   hypothèses personnelles.
8. Vérifier avec l'encadrement la force admissible des termes « criticité
   auto-organisée » et « effet rebond » dans le rapport.
9. Définir un panier restreint de faits stylisés non redondants et une règle de
   validation hors calibration pour les revenus, bilans, cascades et cycles.
10. Identifier des données empiriques compatibles avec les observables du
    modèle, en distinguant personnes, entreprises, consommation de ressource et
    production de service.
11. Formaliser le parallèle avec une transition absorbante : définir l'activité,
    l'état absorbant de la cascade, le substrat mémoriel, l'entraînement et la
    dissipation, puis vérifier si ces objets sont effectivement mesurables.
12. Réanalyser les durées et amplitudes des récessions run par run, avec des
    méthodes non groupées et des comparaisons de familles, avant toute
    confrontation qualitative à Ormerod--Mounfield.

### Moyen terme

1. Implémenter la feuille de route M4.3Live-v2 si ses changements institutionnels
   sont retenus : sens du prêt, ordre du service des intérêts, borne de transfert
   et instrumentation de la tension.
2. Ajouter un mécanisme de transmission aux naissances pour rendre une
   intervention partielle observable à long terme sans changer de cohorte cible.
3. Poursuivre l'analyse des groupes adimensionnels, de la durée de vie, du trou
   d'insolvabilité, du plateau de branchement et de la rotation du crédit.
4. Tester si l'élasticité de rebond demeure distincte de la simple covariance
   d'échelle lorsque la ressource et le service sont séparés explicitement.
5. Établir une cible empirique causale pour les cascades de faillites et vérifier
   si leur exposant peut être déplacé sans réglage fin.
6. Pour la branche Boltzmann--Pareto, tester le corps sur valeur nette, mesurer
   directement dérive et variance conditionnelles, et comparer la température
   ajustée au rapport \(B_0/A_0\).

## 14. Figures candidates pour un rapport

1. **Artefact de cohorte initial** : `../analyse_distributions_taille_revenu/figures/age_cohorte.png`.
2. **Hiérarchie globale des paramètres** : `../sensibilite_m4b/figures/lhs_prcc.png`.
3. **Scaling des avalanches** : `../sensibilite_m4b/figures/confirm_scaling.png`.
4. **Gini et renouvellement** : `../sensibilite_m4b/figures/confirm_gini_renewal.png`.
5. **Structure de la valeur nette** : `../sensibilite_m4b/figures/nw_structure.png`.
6. **Sensibilité des cycles** : `../sensibilite_m4b/figures/cycles_sensibilite.png`.
7. **Structure des cycles** : `../sensibilite_m4b/figures/cycles_structure.png`.
8. **Mécanique du modèle** : figures du rapport `../../m4b_credit_soc_mini/report/mecanique_m4b.pdf` à reconstruire sous forme de schéma unique si nécessaire.
9. **Effet d'échelle de M4.2** : `../../m4_2_credit_soc/figures/ablation_scale.png`.
10. **Rupture de l'anti-corrélation dans M4.3** : `../../m4_3_credit_soc/report/figures/d1_plan_dagum_c_vs_b.png`.
11. **Réponse dynamique de la production** : `../../m4_3live_credit_soc/report/figures/response_prod.png`.
12. **Ablation du capital de naissance** : `../../m4_3live_credit_soc/report/figures/ablation_k0_levels.png`.
13. **Covariance d'échelle et loi d'élasticité** : `../../m4_3live_credit_soc/report/figures/scaling_covariance.png` ou `scaling_gamma.png`.
14. **Couplage historique PIB--énergie** : figure 1, page 8 de `/home/anatole/Documents/Articles stage c/Numero_135_-_novembre_2017-1.pdf`, à redessiner avec sa figure complémentaire sur l'intensité énergétique et à citer comme Dupont, Jeanmart et Possoz (2017).
15. **Transition croissance–bornage du modèle d'avril** : `../../anciens_modeles/modele-27-04-WIP/studies/sensitivity/report/figures/codex_oat_key_trajectories.png`.
16. **Carte \(k\times\mu\)** : `../../anciens_modeles/modele-27-04-WIP/studies/sensitivity/report/figures/map_k_mu_heatmap.png`.
17. **Transitoire long à 10 000 pas** : `../../anciens_modeles/modele-27-04-WIP/studies/sensitivity/report/figures/long_run_k3sigma0005_10k_trajectoires.png`.
18. **Convergence du branching dans M4 Fable** : `../../m4_credit_soc_fable/reports/01_soc_final/figures/lot100_branching_ratio.png`.
19. **Taille finie dans M4 Fable** : `../../m4_credit_soc_fable/reports/01_soc_final/figures/lots_scaling_finite_size.png`.
20. **Structure causale M4B** : figure `soc_avalanche_structure.png` du run Simulation Lab `20260718_033746_8b0c5acb`.
21. **Queue d'intérêts M4.2B** : `../../m4_2b_credit_soc/report/figures/sim_interets_baseline.png`.
22. **Erreur du contrôle de seuil M4.2B** : `../../m4_2b_credit_soc/report/figures/fig7_seuil_exemple_travaille.png`.

## 15. Registre synthétique des affirmations

| ID | Affirmation | Statut | Source principale |
|---|---|---|---|
| A1 | La bimodalité initiale est principalement démographique | Établi pour la lignée 27-04 | `analyse_distributions_taille_revenu/latex/rapport.tex` |
| A2 | La queue initiale dérive avec l'horizon | Établi | même source |
| A3 | M3 rend le crédit causal démographiquement | Établi dans M3 | `anciens_modeles/m3_credit_soc/reports/06_final_synthesis/` |
| A4 | Les chocs corrélés synchronisent plus qu'ils ne propagent | Établi dans M4 | `m4_credit_soc_fable/reports/01_soc_final/` |
| A5 | Annulation + destruction permet la propagation | Établi dans M4/M4B | rapport M4 et rapport mécanique M4B |
| A6 | M4B est fidèle à M4 | Établi par tests de parité | `m4b_credit_soc_mini/report/mecanique_m4b.tex` |
| A7 | M4B présente un régime stationnaire unique sur les plages testées | Établi | `sensibilite_m4b/report/rapport_final.tex` |
| A8 | \(\sigma,k,K_0,\delta,\lambda\) ont des rôles distincts | Établi | même source |
| A9 | Les avalanches suivent une loi tronquée avec exposant asymptotique ~2,31 | Établi sur la campagne | même source |
| A10 | L'inégalité principale est dans la valeur nette | Établi, extension post-audit | même source, section valeur nette |
| A11 | Le défaut de liquidité est silencieux sur la plage principale | Établi | même source |
| A12 | La mémoire de l'activité suit la durée de vie | Établi, extension post-audit | même source, section cycles |
| A13 | M4B démontre un effet rebond | Faux ; la première expérience est dans 4-05-dynamique et la reprise contrôlée vient de M4.3Live | archives 4-05, résultats M4B et rapport M4.3Live |
| A14 | Le prototype récent produit une queue Pareto stable | Provisoire | `conception_boltzmann_pareto_soc/` |
| A15 | Le prototype produit un corps Boltzmann | Non confirmé | même source |
| A16 | La société capitaliste possède une architecture de type SOC | Hypothèse non actuellement réfutée, non démontrée | programme général du stage |
| A17 | Le renouvellement du top mesuré équivaut à la mobilité sociale empirique | Faux à ce stade | absence de définition et de mécanisme intergénérationnel |
| A18 | Un exposant de cascade non manipulable et incompatible avec les données imposerait une refonte | Critère de réfutation retenu | objectif scientifique de M4.2 |
| A19 | Il existe une loi universelle unique des revenus capitalistes | Non étayé ; corps exponentiel ou lognormal et queue de Pareto selon objets et données | Yakovenko–Rosser, Wright, Fisk |
| A20 | L'exposant \(3/2\) de Watts est une mesure empirique des cascades de faillites | Faux ; résultat théorique sur graphe aléatoire | Watts (2002) |
| A21 | Les contractions de M4B sont caractérisées sur l'énergie totale | Résultat provisoire post-audit ; baseline interne établie, validation externe absente | tableaux de cycles, colonnes energy |
| A22 | Les revenus des personnes et des entreprises suivent la même famille | Question empirique à tester ; sinon deux paramétrisations du moteur peuvent être comparées séparément | doctrine de validation |
| A23 | La production M4B est littéralement un chiffre d'affaires | Faux à ce stade ; proxy supposant la production vendue à prix unitaire | absence de prix et de marché de biens |
| A24 | L'étiquette calendaire d'un pas change la famille distributionnelle | Non pour un simple changement d'échelle ; l'effet de la fenêtre d'agrégation reste à tester | convention de validation |
| A25 | \(K\) ou \(NW\) doit être identifié à une catégorie économique précise | Hors ambition ; ce sont taille et taille nette abstraites | choix de périmètre |
| A26 | L'absence de cible académique compatible valide le modèle | Faux ; elle suspend le verdict externe et empêche aussi bien validation que rejet | section 10.4 |
| A27 | Le crédit est toujours distributionnellement neutre dans M3 | Faux ; vrai dans la baseline « richesse soutenable », faux dans X1 « revenu myope » | rapports M3 06 et 07 |
| A28 | La dette peut remplacer le plancher d'absorption exogène | Établi dans l'ablation H de M3 sur trois graines ; origine proposée de M4 | rapport M3 06 |
| A29 | La liquidité de M3 suit Boltzmann--Gibbs | Faux sur la campagne M3 ; corps généralement Fisk | rapports M3 05 et 06 |
| A30 | Les tests de topologie et de corrélation pré-enregistrés de M3 sont tous concluants | Faux ; F et G1 confondent les effets qu'ils devaient isoler | rapport M3 05 |
| A31 | La courbure \(\gamma\) pilote directement l'exposant des avalanches dans M4.2 | Réfuté dans la comparaison naïve ; l'effet dominant est un déplacement d'échelle | `m4_2_credit_soc/report/rapport_final.tex` |
| A32 | M4.2 possède une covariance exacte sous remise à l'échelle de \(K,K_0,A\) | Établi analytiquement et numériquement dans le moteur | même source et `m4_2_credit_soc/JOURNAL.md` |
| A33 | Une queue de Pareto des intérêts reçus est établie dans M4.2B | Non tranché : queue visible, contrôle `/2` erroné puis contrôle `×2` trop peu alimenté ; hypothèse de travail seulement | `m4_2b_credit_soc/JOURNAL.md` et figure du seuil |
| A34 | La branche `gamma_comp_0.6667` épaissit la queue des intérêts tout en renforçant les avalanches | Établi dans M4.3, robuste à la taille et aux deux moitiés temporelles testées | `m4_3_credit_soc/report/rapport_final.md` |
| A35 | Une intervention partielle produit un rebond à court horizon | Établi à l'intérieur de M4.3Live | `m4_3live_credit_soc/report/rapport_final.tex` |
| A36 | Une hausse globale de \(A\) avec \(K_0\) fixe produit nécessairement un rebond établi | Faux au contraste principal ; \(E\simeq0{,}72\), \(\varepsilon\simeq0{,}76\), à cause de la contraction démographique | même source |
| A37 | Compenser \(K_0\) à l'échelle technologique produit un rebond établi fort | Établi dans la campagne M4.3Live | même source |
| A38 | Sous compensation d'échelle, \(\varepsilon=1/(1-\gamma)\) | Théorème exact du moteur homogène, vérifié à la précision machine | même source, section covariance d'échelle |
| A39 | M4.3Live fournit une explication générale validée du rebond réel | Faux ; observation interne, dépendante de conventions et non calibrée | limites du rapport M4.3Live |
| A40 | Hendrick et al. démontrent une SOC urbaine | Faux ; ils observent un collapse universel et signalent une ressemblance avec la SOC sans étudier la dynamique | Hendrick, Rinaldo et Manoli (2025) |
| A41 | Appliquer la SOC à l'économie est une idée propre à ce stage | Faux ; Bak et al. proposent un modèle économique auto-critique dès 1992 | Bak, Chen, Scheinkman et Woodford (1992) |
| A42 | Les deux régimes observés par Yakovenko prouvent une SOC économique | Faux ; ils motivent l'hypothèse d'Anatole, mais les queues de Pareto ont plusieurs mécanismes possibles | Drăgulescu--Yakovenko (2001), Yakovenko--Rosser (2009), témoignage de l'auteur |
| A43 | Hendrick est le déclencheur de l'hypothèse que le rebond est endogène à l'organisation sociale | Témoignage de l'auteur confirmé le 21 août 2026 | section 1.1 |
| A44 | Les transferts monétaires peuvent être interprétés comme des transferts de droits à mobiliser l'exergie | Hypothèse qui justifie la modélisation énergétique d'une société économique ; non démontrée | témoignage du 21 août 2026 et section 1.2 |
| A45 | Herbert et al. démontrent que monnaie et exergie sont équivalentes | Faux ; ils modélisent le couplage de deux sphères explicitement distinctes | Herbert et al. (2022) |
| A46 | Le PIB mondial et la consommation mondiale d'énergie sont découplés en valeur absolue entre 1965 et 2015 | Faux dans la source utilisée ; coévolution forte et découplage relatif seulement | Dupont, Jeanmart et Possoz (2017), figures 1 et 2 |
| A47 | Le graphique PIB--énergie mesure directement l'exergie | Faux ; son abscisse est la consommation d'énergie en EJ | même source |
| A48 | Un rapport de branchement égal à un suffit à démontrer une SOC | Faux ; il établit la criticité du processus de branchement, mais la SOC exige une dynamique endogène vers ce point | Bouchaud (2024) |
| A49 | Le rapport de branchement est l'unique ou la principale statistique du programme | Faux ; sa proximité de un est caractéristique, mais il s'insère parmi les distributions, la propagation causale, la taille finie et la robustesse | témoignage de l'auteur, M4.2B, M4.3 et section 1.5 |
| A50 | La baseline M4.2B possède un rapport de branchement proche de 0,786 | Établi ; certaines cellules atteignent 0,891, toutes restent sous l'unité | `m4_2b_credit_soc/report/rapport_final.md` |
| A51 | \(K\) représente le capital comptable total d'une personne | Faux ; \(K\) est la taille intrinsèque productive de l'entité | témoignage du 21 août 2026 et définition du moteur |
| A52 | \(NW\) est le meilleur analogue interne du patrimoine net ou des capitaux propres | Convention d'interprétation retenue, encore imparfaite | sections 1.5, 4.1 et 10.5 |
| A53 | Le toy-model impose les macro-statistiques recherchées | Faux ; il code des interactions locales et mesure les sorties agrégées | architecture du moteur et témoignage de l'auteur |
| A54 | Le modèle doit pouvoir relier des variations de paramètres à des variations reproductibles des sorties | Objectif permanent et axe majeur du stage | campagnes d'ablation et de sensibilité M2--M4.3Live |
| A55 | Le revenu monétaire usuel est représenté, dans l'ontologie voulue, par les intérêts reçus | Convention construite progressivement depuis les premiers bilans, puis devenue cible explicite en M4.2B | témoignage de l'auteur, M4.2B et M4.3 |
| A56 | La production du moteur est littéralement un salaire, un revenu monétaire ou un apport biologique constant | Faux ; la puissance extractrice est la capacité d'une entité à grossir en fonction de sa taille et de sa technologie, avant érosion et transferts | témoignage du 24 août, section 1.2 et dictionnaire 10.5 |
| A57 | Le moteur contient explicitement ouvriers, capitalistes et machines | Faux ; il en conserve seulement des équivalents abstraits | architecture homogène du moteur |
| A58 | L'analogie de la hache décrit le critère de viabilité comme surplus utile supérieur à l'entretien et à l'érosion | Hypothèse conceptuelle de construction, non test direct du moteur | témoignage du 21 août 2026 |
| A59 | Les anciens proxys « production » ou « production + intérêts » doivent être effacés | Faux ; ils restent les définitions historiques des statistiques déjà calculées | rapports M4B et clarification de l'auteur |
| A60 | L'objectif paramètres microscopiques → statistiques globales → classes empiriques n'est qu'une reconstruction tardive | Faux ; il est déjà formulé dans la note du 24 avril 2026 | `note_de_travail/latex/note.tex`, témoignage du 21 août |
| A61 | Toutes les premières simulations convergent vers un régime borné | Faux ; certaines divergent lorsque le mécanisme de marché et la mortalité ne bornent pas l'accumulation | note du 24 avril et témoignage du 21 août |
| A62 | Les « banques » et les « travailleurs » sont deux classes fonctionnelles établies | Faux ; c'est une interprétation initiale, ensuite largement expliquée par les cohortes | note du 24 avril et analyse des distributions de juin–juillet |
| A63 | Une loi de puissance est déjà observée dans le modèle au 24 avril | Faux ; la note dit explicitement qu'aucune n'a encore été observée | `note_de_travail/latex/note.tex` |
| A64 | Le stage cherche à la fois un diagnostic de proximité critique et une explication causale des phénomènes | Objectif directeur confirmé | note du 24 avril et témoignage du 21 août |
| A65 | Une SOC peut être formulée comme une transition vers un état absorbant sous entraînement lent | Établi pour la classe de modèles étudiée par Dickman et al., non universellement pour toute SOC | Dickman, Vespignani et Zapperi (1998) |
| A66 | Le système M4B complet possède déjà un état absorbant démontré | Faux ; seule la fin d'une cascade rapide admet une correspondance candidate avec un état sans activité | interprétation du stage à partir de Dickman et al. |
| A67 | Les distributions de récessions étudiées par Ormerod et Mounfield suivent une loi de puissance exacte sur tout leur support | Faux ; l'ajustement est approximatif et surestime les grands événements, sauf très bon fit rapporté pour les durées supérieures à un an | Ormerod et Mounfield (2001) |
| A68 | Les récessions d'Ormerod et Mounfield démontrent une SOC capitaliste | Faux ; elles constituent un symptôme compatible avec des interactions corrélées, non une identification causale | même source |
| A69 | Les lois d'échelle urbaines désignent spécifiquement un mécanisme SOC | Faux ; plusieurs modèles fondés sur la géométrie, la gravité, les réseaux ou les interactions peuvent produire la même forme | Ribeiro et Rybski (2023) |
| A70 | Les durées et amplitudes empiriques des récessions sont une cible de validation déjà testée pour M4B | Faux ; seules des statistiques internes ont été calculées, sans comparaison distributionnelle externe compatible | section 6.7 et Ormerod--Mounfield |
| A71 | Une loi de puissance des durées de récession constitue un fait empirique consensuel | Faux ; Wright obtient une exponentielle sur les mêmes données complètes, tandis que des données étendues ont ensuite ravivé la controverse | Ormerod--Mounfield (2001), Wright (2005) |
| A72 | Le premier moteur date des 12–13 mars 2026 | Date grossière confirmée par Anatole ; les archives ne permettent pas de dater chaque variante au jour près | témoignage du 24 août et archives de mars |
| A73 | Des types d'agents « banque » et « travailleur » ont été déclarés | Faux ; les étiquettes ont été appliquées à des comportements émergents sous des règles communes | témoignage des 21 et 24 août, archives sans banque |
| A74 | Le vieux seuil en \(k\) mesure uniquement une complexité locale | Faux ; le protocole gardait un nombre total de tentatives fixe indépendamment de \(N\). M4B puis M4.2 séparent activité en \(N\) et paires \(k=2\) | code WIP, M4B et M4.2 ; annexe de preuves |
| A75 | Le choc brownien est déplacé de \(\alpha\) vers \(K\) pour la première fois dans M4 | Faux ; le déplacement vers le stock réel \(w\) est attesté dès M2, puis conservé sous le nom \(K\) | codes WIP, M2 Fable, M3 et M4 |
| A76 | M4.3Live est la première expérience de rebond du stage | Faux ; la variante dynamique 4-05 teste déjà `alpha_plus_10pct`. M4.3Live est la reprise sur la lignée reconstruite | rapport et CSV 4-05 ; rapport M4.3Live |
| A77 | Les exposants de revenus du capital et du travail possèdent une valeur empirique universelle étroite | Faux ; de Vries et Toda trouvent des plages larges, principalement 1–3 et 2–5 en convention CCDF | de Vries et Toda, S12 |
| A78 | L'ablation institutionnelle de M4.3 a été scientifiquement tranchée | Faux ; elle reste non décidée parce que le stage s'est terminé | témoignage du 21 août et journal M4.3 |
| A79 | M4.3Live-v2 constitue un modèle testé | Faux ; il s'agit d'une feuille de route non implémentée à la clôture | `m4_3live_v2_credit_soc/ROADMAP.md` |
| A80 | Les encadrants sont les auteurs des choix de conception du modèle | Faux selon le témoignage d'Anatole ; ils ont nourri, supervisé et validé la recherche, tandis qu'Anatole revendique conception et décisions | témoignage du 21 août et section 12.4 |

## 16. Sources principales du dépôt

- `recherche/memo_stage/registre_sources_scientifiques.md` : registre durable
  des articles transmis, avec métadonnées, empreintes SHA-256, rôle dans le
  raisonnement et précautions de citation.
- `recherche/memo_stage/registre_sources_internes.md` : registre chronologique
  des notes, rapports et archives produits pendant le stage, distinct de la
  bibliographie scientifique externe.
- `recherche/memo_stage/annexe_preuves_historiographiques_2026-08-21.md` :
  matrice sourcée des modifications de modèles, résultats anciens, figures
  inspectées dans Simulation Lab et localisations de preuve.
- `recherche/note_de_travail/latex/note.tex` et `note.pdf` : instantané daté du
  24 avril 2026 de la formulation initiale du stage, des deux régimes des
  premiers modèles et de l'absence de loi de puissance alors établie.
- `recherche/analyse_distributions_taille_revenu/latex/rapport.tex` : diagnostic des cohortes et des distributions.
- `recherche/analyse_articles/` : recodages de Bouchaud–Mézard et de deux modèles de Wright.
- `anciens_modeles/modele-27-04-WIP/studies/sensitivity/report/rapport_final_sensibilite.tex` : source quantitative principale des cartes de sensibilité d'avril–mai.
- `anciens_modeles/4-05-dynamique/RAPPORT_ELAGAGE_MODELE.md` et
  `experiments/results/rebound_1000_*` : première campagne de rebond et
  discordance entre graines annoncées et archivées.
- `anciens_modeles/m3_credit_soc/NOTES.md` et `reports/` : programme causal M3.
- `m4_credit_soc_fable/NOTES.md` et `reports/01_soc_final/main.tex` : découverte du mécanisme M4.
- `m4b_credit_soc_mini/report/mecanique_m4b.tex` : définition du moteur minimal.
- `recherche/sensibilite_m4b/JOURNAL.md` : journal expérimental.
- `recherche/sensibilite_m4b/report/rapport_final.tex` : résultats quantitatifs de référence.
- `m4_2_credit_soc/report/rapport_final.tex` et `JOURNAL.md` : concavité,
  covariance d'échelle et analyse de la dyade de crédit.
- `m4_2b_credit_soc/report/rapport_final.md` et `JOURNAL.md` : campagne sur les
  intérêts reçus et statut non tranché de la queue de Pareto.
- `m4_3_credit_soc/report/rapport_final.md` et `JOURNAL.md` : rupture de
  l'anti-corrélation entre queue des intérêts et avalanches.
- `m4_3live_credit_soc/report/rapport_final.tex` et `JOURNAL.md` : moteur
  pilotable, campagne dynamique de rebond et covariance d'échelle.
- `m4_3live_v2_credit_soc/ROADMAP.md` : feuille de route v2, non implémentée à
  la clôture du stage.
- `recherche/conception_boltzmann_pareto_soc/conception_modele_M2.md` : branche théorique récente.
- `/home/anatole/Zotero/storage/S9BMXQ39/Bak et Chen - SELF ORGANIZED CRITICALITY AND FLUCTUATIONS IN ECO.pdf` : précédent SOC appliqué à une économie de production.
- `/home/anatole/Zotero/storage/FN774CRH/Drăgulescu et Yakovenko - 2001 - Exponential and power-law probability distribution.pdf` : double régime exponentiel--Pareto dans les données britanniques et américaines.
- `/home/anatole/Zotero/storage/XQPEMVVN/Yakovenko et Rosser - 2009 - Colloquium Statistical mechanics of money, wealth.pdf` : synthèse thermique/superthermique et modèles d'échange.
- `/home/anatole/Zotero/storage/76W9LTRW/Hendrick et al. - 2025 - A stochastic theory of urban metabolism.pdf` : scaling de taille finie du métabolisme urbain et déclencheur de l'hypothèse de rebond endogène.
- `/home/anatole/Zotero/storage/AFHT2X4G/Herbert et al. - Macroeconomic Dynamics in a finite world the Ther.pdf` : économie dissipative hors équilibre, ressources finies et couplage des comptabilités physique et économique.
- `/home/anatole/Documents/Articles stage c/Numero_135_-_novembre_2017-1.pdf` : source canonique du graphique PIB--énergie, figure 1 page 8, et de sa nuance sur le découplage relatif.
- `/home/anatole/Zotero/storage/62DJW8X2/Bouchaud - The Self-Organized Criticality Paradigm in Economi.pdf` : revue tardive clarifiant criticité de branchement, auto-organisation et applications économiques de la SOC.
- `/home/anatole/Zotero/storage/KP7VGKBQ/Dickman et al. - Self-organized criticality as an absorbing-state p.pdf` : formulation de la SOC comme transition absorbante sous entraînement lent et base du parallèle avec les cascades de faillites.
- `/home/anatole/Zotero/storage/TFIDTI26/Ormerod - Power Law Distribution of the Duration and Magnitu.pdf` : distributions de durée et d'amplitude des récessions capitalistes, avec rupture du scaling aux grands événements.
- `/home/anatole/Zotero/storage/2EFXZ53Z/Ribeiro et Rybski - Mathematical models to explain the origin of urban.pdf` : revue des mécanismes concurrents expliquant les lois d'échelle urbaines.
- `/home/anatole/Zotero/storage/FZ7F6G3N/Wright - 2005 - The duration of recessions follows an exponential .pdf` : contre-analyse directe d'Ormerod--Mounfield en faveur d'une loi exponentielle sur les durées complètes.
- `/home/anatole/Zotero/storage/Q8Y8288A/de Vries et Toda - Capital and Labor Income Pareto Exponents across T.pdf` : plages empiriques internationales des exposants de Pareto des revenus du capital et du travail, en convention CCDF.
- Bibliothèque Zotero locale : 43 références principales, dont
  Yakovenko–Rosser, *Colloquium: Statistical Mechanics of Money, Wealth, and
  Income* ; Wright, *The Social Architecture of Capitalism* et *Implicit
  Microfoundations for Macroeconomics* ; Fisk, *The Graduation of Income
  Distributions* ; Watts, *A Simple Model of Global Cascades on Random
  Networks* ; Arvidsson, Lovsjö et Keuschnigg, *Urban Scaling Laws Arise from
  Within-City Inequalities* ; ainsi que Bouchaud–Mézard, Bak, Dhar,
  Dickman–Vespignani–Zapperi, Sorrell–Dimitropoulos, Herbert et al.,
  West–Brown–Enquist et Hendrick et al.

## 17. Informations confirmées et questions à résoudre avec l'auteur

### Informations confirmées

- Période : du premier moteur vers les 12–13 mars à la clôture du stage en août
  2026 ; les dates des variantes de mars restent grossières.
- Cadre de formation : ENS Rennes, département mécatronique, parcours
  *Recherche aux interfaces* ; stage de recherche.
- Intitulé : *Étude et modélisation de l'effet de rebond par approche
  énergétique. Métabolisme des sociétés industrielles*.
- Encadrement : Éric Herbert, Petros Chatzimpiros, Christophe Goupil et
  Jean-Philippe Brunetton.
- Objectif confié : chercher une explication générale de l'effet rebond en
  adoptant un point de vue physique sur le métabolisme industriel.
- Première filiation conceptuelle : Kleiber et les modèles de réseaux
  métaboliques fractals conduisent à interroger l'invariance d'échelle, sans
  équivalence posée entre fractalité, loi de puissance et SOC.
- Piste économique : la lecture de Drăgulescu--Yakovenko puis
  Yakovenko--Rosser, au début de la réflexion, fait du double régime
  thermique/superthermique un indice à expliquer par des interactions locales et
  un candidat SOC. Cette interprétation appartient à Anatole, non aux résultats
  démontrés par ces articles.
- Antériorité : Bak, Chen, Scheinkman et Woodford appliquent déjà en 1992 la SOC
  à une économie de production ; le stage ne revendique pas cette idée générale
  comme originale.
- Déclencheur spécifique du rebond : Hendrick, Rinaldo et Manoli conduisent
  Anatole à proposer que l'effet rebond soit endogène à l'organisation de la
  société. L'article établit un collapse de distributions urbaines, pas une SOC
  ni un mécanisme de rebond.
- Fil directeur : construire d'abord un toy-model potentiellement
  auto-critique produisant endogènement des distributions plausibles ; chercher
  ensuite un effet rebond dynamique.
- Objectif permanent du toy-model : ne simuler que les interactions locales,
  observer les macro-statistiques émergentes et rendre leurs variations
  explicables par celles des paramètres microscopiques.
- Moelle épinière du stage : piloter le modèle en quantifiant la relation entre
  paramètres de départ et statistiques finales, afin de tester s'il peut
  reproduire les classes de distributions réelles et d'expliquer les mécanismes
  qui les engendrent. Cet objectif est attesté au plus tard le 24 avril 2026.
- Première bifurcation expérimentale : certains réglages divergent lorsque le
  marché et la mortalité ne bornent pas l'accumulation ; d'autres convergent
  vers un macro-régime apparemment stationnaire avec renouvellement local.
- Premières classes apparentes : les catégories « banques » et « travailleurs »
  sont une observation et une interprétation historiques importantes, mais non
  un résultat final ; l'analyse de juin–juillet les réattribue principalement à
  un effet de cohortes.
- Types d'agents : aucun type « banque » ou « travailleur » n'a jamais été
  déclaré. Le retrait du mécanisme bancaire spécial visait dès mars à comprendre
  l'émergence d'une différenciation sous des règles communes et sa possible
  portée économique réelle.
- Filiation d'avril : le modèle du 27 avril poursuit intellectuellement le WIP
  sans banque ; il ne constitue pas une reconstruction indépendante.
- Limite de l'ancien \(k\) : les tentatives totales de nouveaux contrats étaient
  fixes indépendamment de \(N\). La suite rend l'activité proportionnelle à la
  population et réduit la rencontre à des paires \(k=2\).
- Première expérience de rebond : la branche `4-05-dynamique` teste
  `alpha_plus_10pct`. Son rapport annonce +5,1 % d'extraction après le pas 500 et
  +25,2 % de prêts finaux, avec une discordance entre trois graines annoncées et
  deux archivées par variante.
- M2 : les versions Codex et Fable sont deux implémentations concurrentes du même
  prompt, utiles comme réplications adversariales mais non indépendantes. C'est
  dès M2 que le choc brownien quitte \(\alpha\) pour agir directement sur le
  stock réel, nommé \(w\) puis \(K\).
- Sélection de M4 Fable : la branche est poursuivie parce que
  l'annulation–destruction produit des avalanches causales, un régime pré-SOC et
  des statistiques cohérentes. Les figures montrent un branching stabilisé vers
  0,30 et une coupure croissant avec la taille ; elles justifient la poursuite,
  sans démontrer une SOC stricte.
- Queue d'intérêts M4.2B : Anatole la voyait sur les graphiques. Le contrôle
  `seuil/2` proposé par l'agent était mal orienté ; le contrôle `seuil×2`
  rétablit le sens de l'autosimilarité mais laisse trop peu de points. Pareto est
  donc conservée comme hypothèse de travail visible, non comme résultat
  statistiquement confirmé.
- État au 24 avril : aucune loi de puissance n'est encore observée ; la SOC est
  une hypothèse de travail et la possibilité d'un cul-de-sac est explicitement
  reconnue.
- Hypothèses de vérification : classes de distribution de la taille, du revenu
  et de la valeur nette ; queues de Pareto et corps de type Boltzmann comme
  premiers repères, sans les ériger en lois universelles puisque leur
  caractérisation académique reste discutée.
- Démarche : alternance d'élargissement et d'élagage du modèle.
- Moments décisifs : première convergence du système total ; premières lois de
  puissance causales dans M4.
- Entité : unité volontairement générique pouvant représenter une entreprise,
  une personne ou un objet technique ; toutes les entités suivent actuellement
  les mêmes règles.
- Applications personne/entreprise : même moteur, mais jeux de paramètres
  potentiellement différents ; il ne s'agit pas de deux populations
  coexistantes.
- Interprétation des stocks : \(K\), malgré son nom historique de « capital »,
  est la taille intrinsèque productive de l'entité. \(NW\) est le meilleur
  analogue interne du patrimoine net ou du capital comptable total, tout en
  restant un proxy simplifié.
- Postulat monnaie--exergie : hypothèse qui justifie la modélisation énergétique
  d'une société économique. Un transfert monétaire est lu comme un transfert de droit social à
  mobiliser ou profiter de l'exergie ; le transfert n'est pas lui-même un flux
  physique de joules.
- Joule : unité comptable abstraite dans le moteur. La dynamique peut être
  exécutée sans valider le postulat monnaie--exergie, mais sa lecture comme
  métabolisme industriel en dépend fortement.
- Continuité théorique : Herbert, Giraud, Louis-Napoléon et Goupil fondent une
  macrodynamique de monde fini sur le couplage de sphères physique et économique
  distinctes ; leur article soutient la dépendance matérielle, non une identité
  monnaie--exergie.
- Illustration PIB--énergie : Dupont, Jeanmart et Possoz montrent une forte
  coévolution mondiale entre 1965 et 2015, sans découplage absolu mais avec un
  découplage relatif. Leur figure mesure l'énergie, pas l'exergie.
- Lecture tardive de Bouchaud : elle fournit le vocabulaire rétrospectif du
  programme SOC. Un rapport de branchement égal à un marque la criticité du
  processus de branchement ; parler de SOC exige en plus une organisation
  endogène vers ce point.
- Antériorité du branching : sa recherche guidait déjà les simulations avant la
  lecture de Bouchaud. Sa proximité de un est caractéristique d'un SOC, mais il
  n'est ni l'unique ni nécessairement la principale statistique du stage.
- Branchement M4.2B : 0,786 à la baseline lente et jusqu'à 0,891 dans la cellule
  \(\rho=4\), contre environ 0,30 dans M4B/M4.2. La propagation est forte et
  pilotable, mais reste sous-critique au sens strict.
- Cadre absorbant : Dickman, Vespignani et Zapperi relient la SOC à une
  transition entre extinction et activité persistante sous entraînement lent.
  Dans le toy-model, la fin d'une cascade peut être lue comme un état absorbant
  de la dynamique rapide ; cette correspondance reste à formaliser et ne vaut
  pas pour l'économie entière continuellement alimentée.
- Substrat mémoriel candidat : réseau de crédit, bilans et densité d'entités
  fragiles ; activité candidate : défauts en cours de propagation ; dissipation
  candidate : dépréciation, annulation et destruction. Ces identifications sont
  des hypothèses du stage, non des résultats publiés par Dickman et al.
- Symptômes empiriques supplémentaires : Ormerod et Mounfield observent des
  comportements proches de lois de puissance dans les durées et amplitudes des
  récessions, avec rupture aux grands événements ; Ribeiro et Rybski synthétisent
  la robustesse et la diversité des lois d'échelle urbaines.
- Controverse sur les récessions : Wright réanalyse les mêmes données et préfère
  une exponentielle sur le support complet ; la puissance n'est meilleure
  qu'après exclusion des épisodes d'un an. Une étude étendue mentionnée par
  Wright retrouve ensuite l'avantage de la puissance. La classe reste ouverte.
- Non-unicité des symptômes : ni les récessions à queue lourde ni le scaling
  urbain n'identifient une SOC. L'adaptation, la géométrie, la gravité, les
  réseaux et d'autres mécanismes peuvent produire ou déformer ces formes.
- Clôture du stage : M4.3Live-v1 est la version expérimentale la plus avancée et
  M4.3Live-v2 une feuille de route non implémentée. L'ablation institutionnelle
  de M4.3 et la poursuite numérique sont restées non tranchées faute de temps ;
  la branche Boltzmann–Pareto reste secondaire.
- Rebond M4.3Live : observé à court horizon pour une portée partielle ; non
  tranchable à long horizon partiel faute de transmission ; sous-proportionnel à
  portée globale et \(K_0\) fixe ; fortement super-proportionnel lorsque \(K_0\)
  suit l'échelle technologique.
- Loi d'échelle du rebond compensé :
  \(\varepsilon=1/(1-\gamma)\), démontrée pour le moteur homogène et vérifiée à
  la précision machine. Ce résultat interne ne vaut pas validation empirique.
- Validation économique prioritaire : classes de distribution des revenus des
  personnes et des entreprises, d'abord séparées puis comparées ; patrimoines ;
  mobilité sociale à définir et à intégrer.
- Critère de réfutation : incapacité structurelle à déplacer l'exposant des
  cascades vers la cible empirique des faillites d'entreprises.
- Statut de la SOC : hypothèse non actuellement réfutée, mais non démontrée.
- Valeur résiduelle du travail : même si l'interprétation de la société
  capitaliste comme architecture auto-critique était réfutée, le modèle
  conserverait une valeur théorique comme système stochastique en réseau ; sa
  portée physique et économique serait toutefois fortement réduite.
- Revenu dans l'ontologie précisée : somme des intérêts perçus sur la fenêtre
  (`int_in`), utilisée comme représentation abstraite du revenu monétaire usuel
  et non du seul revenu financier réel. Cette convention s'est construite
  progressivement et devient une cible explicite dans M4.2B.
- Production dans l'ontologie précisée : **la puissance extractrice est la
  capacité d'une entité à grossir en fonction de sa taille et de sa
  technologie**. Elle est le terme productif positif, non un revenu monétaire,
  un apport journalier constant ou la croissance nette après érosion et
  transferts.
- Proxys historiques M4B : production cumulée pour le chiffre d'affaires et
  production plus intérêts pour le revenu brut personnel. Ils doivent rester
  associés aux analyses qui les ont effectivement utilisés, sans devenir les
  définitions finales des variables.
- Temps : le pas reste abstrait pour les comparaisons de familles
  distributionnelles. Une simple convention d'échelle est supposée sans effet
  sur la famille ; la robustesse à la longueur d'agrégation reste à contrôler.
- Taille \(K\) et taille nette \(NW\) : deux variables internes distinctes à
  analyser séparément, sans identification empirique précise imposée.
- Mobilité : question non encore traitée ; piste future de filiation et de
  transmission intergénérationnelle.
- Récessions : nouveau critère de validation portant sur leur durée, leur
  fréquence et leur amplitude, observées comme variations de l'énergie totale
  présente dans le système \(E_t=\sum_iK_i(t)\), mesurée en fin de pas.
- Cible Ormerod--Mounfield : comparer ultérieurement les distributions complètes
  de durée et d'amplitude et leurs ruptures, sans transférer directement leurs
  exposants annuels aux pas abstraits de M4B.
- Baseline énergétique provisoire au centre : environ 252 récessions par
  millier de pas, durée moyenne 1,93 pas et perte moyenne 3,5 % ; amplitude
  surtout pilotée par \(\sigma\) et \(K_0\).
- Origine du programme : la conception et les décisions scientifiques sont
  attribuées à Anatole ; les encadrants ont nourri la réflexion par de longs
  échanges, puis supervisé et validé le travail.
- Échecs les plus structurants : artefacts de simulation et complexité
  excessive du premier modèle ; ils ont conduit à mieux structurer la recherche,
  contrôler les fits et expliciter l'absence fréquente de données immédiatement
  compatibles avec une question.
- Cible revenus issue de Zotero : structure en régimes plus robuste qu'une loi
  globale unique ; corps exponentiel ou lognormal selon l'objet, puis queue de
  Pareto. Les exposants publiés ne sont pas transférables sans aligner unités,
  périodes et conventions.
- Repère de Vries--Toda : sur 475 observations pays-années de 52 pays
  (1967–2018), les exposants de CCDF se situent principalement entre 1 et 3 pour
  le revenu du capital (médiane 1,46) et entre 2 et 5 pour celui du travail
  (médiane 3,35). Toute comparaison au modèle doit convertir explicitement les
  conventions CCDF/densité.
- Portée de la cible revenus : personnes et entreprises sont deux objets de
  validation. L'hypothèse qu'ils suivent la même famille doit être testée ; si
  elle est fausse, deux paramétrisations du même moteur pourront être évaluées
  séparément.
- Cible entreprise issue de Zotero : les taux de croissance du chiffre
  d'affaires sont souvent décrits par une loi de Laplace ou Subbotin ; les lois
  de puissance de taille des firmes doivent encore être reliées sans ambiguïté
  au niveau du chiffre d'affaires plutôt qu'à l'emploi ou aux actifs.
- Cible cascades issue de Zotero : l'exposant \(3/2\) de Watts est théorique et
  non une mesure de faillites réelles ; aucune cible empirique causalement
  comparable à M4B n'a encore été identifiée dans la bibliothèque.
- Statut de l'absence de données : information centrale de la recherche. Elle
  empêche de rejeter le modèle contre une cible mal définie, mais ne constitue
  pas une validation ; le verdict externe est suspendu.
- Finalité actuelle du dossier : assembler exhaustivement les données,
  raisonnements, résultats, hypothèses, échecs et sources. Les choix de lectorat,
  longueur, langue et mise en forme sont volontairement différés.

### Questions de fond encore ouvertes

Les questions conservées ici doivent porter sur le contenu scientifique et le
récit de recherche. Les choix éditoriaux du futur rapport ou des notes de
communication seront traités ultérieurement, une fois le dossier source
stabilisé.

1. Le passage M3-H + X1 vers M4 est-il une décision que tu avais consciemment
   formulée à l'époque — combiner plancher contractuel endogène et règle de
   revenu — ou une reconstruction que les journaux permettent seulement de
   faire après coup ?
2. Dans le noyau actuel « naissances + prêts avec intérêts + érosion », quel
   statut donnes-tu à la production concave et à la règle
   annulation--destruction : mécanismes indispensables à l'hypothèse, choix
   provisoires à élaguer, ou simples conventions techniques ?
3. Dans le premier mécanisme financier, quels traits précis du système actuel
   l'actif/passif devait-il reproduire : création de crédit, intermédiation,
   levier, paiements d'intérêts, pertes en cascade, ou seulement une comptabilité
   cohérente des créances et dettes ?
4. À quel moment approximatif du stage le postulat monnaie--exergie a-t-il été
   formulé explicitement : avant le premier modèle, pendant sa construction, ou
   après l'observation de sa convergence ?
5. Quel test empirique ou conceptuel pourrait réellement réfuter ce postulat :
   un découplage absolu durable, une mesure directe des flux d'exergie par groupe
   social, ou l'existence de transferts monétaires sans contrepartie matérielle
   pertinente à l'échelle étudiée ?
6. À quelle date approximative la lecture tardive de Bouchaud a-t-elle eu lieu ?
   Il est établi que la cible branching la précède, mais pas encore quand son
   vocabulaire a été intégré au récit.
7. Dans l'analogie capitaliste--ouvrier, faut-il interpréter l'intérêt comme la
   part du surplus revenant au capitaliste et la production conservée comme la
   part de l'ouvrier, ou garder cette correspondance volontairement qualitative ?
8. Pour le parallèle avec Dickman et al., quel état veux-tu considérer comme
   absorbant dans ton récit : disparition de toute la population, absence
   temporaire de faillite active au terme d'une cascade, ou autre chose ?
9. À quelles dates approximatives as-tu lu Dickman et al., Ormerod--Mounfield
   et Ribeiro--Rybski, afin de distinguer les inspirations précoces des lectures
   rétrospectives venues interpréter les résultats ?
10. Ormerod--Mounfield a-t-il motivé pendant le stage l'analyse des récessions de
   M4B, ou constitue-t-il pour l'instant une cible de validation reconnue après
   cette analyse ?

## 18. Mode d'emploi pour produire les formats dérivés

### Fiche d'avancement courte

Conserver : résumé exécutif réduit, question, trajectoire jusqu'à M4.3Live,
trois résultats M4B, verdict conditionnel sur le rebond, limites et prochaines
étapes. Supprimer la mécanique
détaillée, les valeurs secondaires, le registre complet et la majorité de la
bibliographie.

### Pré-rapport de 10 à 20 pages

Conserver : sections 1 à 3, mécanique synthétique, méthode, résultats centraux,
résultats négatifs, expérience M4.3Live, effet rebond et limites. Utiliser quatre
à six figures.
Reporter les détails de reproductibilité en annexe.

### Rapport complet

Développer : cadre bibliographique, équations, chronologie des versions,
protocole statistique, discussion des résultats négatifs et articulation avec
l'effet rebond. Ajouter une annexe technique décrivant les fichiers, graines,
tests et manifestes, ainsi qu'une bibliographie exportée de Zotero.
