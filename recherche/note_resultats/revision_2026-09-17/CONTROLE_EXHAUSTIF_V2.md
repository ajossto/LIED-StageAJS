# Contre-vérification du carnet V2

Lecture de toutes les remarques renseignées, y compris celles des paragraphes, et confrontation aux sources réellement incluses dans le PDF. Le premier traitement avait indûment différé les corrections graphiques : elles sont désormais effectuées. Les identifiants ci-dessous renvoient au registre détaillé et au carnet original archivé, jamais réécrit.

| Repère du carnet / demande | État vérifié |
|---|---|
| Général : diffusion académique, anglais/allemand, mise en page | Préparation consignée ; traduction et refonte non exécutées conformément à la demande. |
| Général : k fixé à 2 | Distinction explicite entre historique M4B et protocole ultérieur ; aucune configuration ancienne falsifiée. |
| Général : rétrocompatibilité | Annexe E.3, périmètres et tolérances des contrôles documentés ; pas de validation générale inventée. |
| Général : M5 | Renommage officiellement différé ; précision ultérieure sur le taux d'emprunt conservée. |
| Général : figures vectorielles | PDF vectoriels ; SVG éditables ajoutés pour les trois figures corrigées. |
| Général : 15–20 pages hors annexes | Cible conservée ; pas encore atteinte. Corps d'environ 14 pages ; réévaluation après ajouts scientifiques issus des nouvelles figures, sans remplissage artificiel. |
| Général : glossaire | Annexe F ; termes et notations avec définitions. |
| Général : temps caractéristique / renouvellement | Cadre méthodologique en annexe A ; étude quantitative et figure encore attendues de Simulation Lab. Aucune valeur de temps d'oubli inventée. |
| Général : attendre avant relance des simulations | Respecté ; seulement lecture des données existantes et calculs descriptifs/analytique. |
| §1 : supprimer l'expression sur la séparation stock/flux | Supprimée de l'introduction. |
| §2.1 : K° et γ°, retirer explication du cercle | Appliqué au régime de référence. |
| §2.2 : note renvoyant aux paramètres | Renvois vers les sections du pas, du crédit et le glossaire. |
| §2.5 : montrer l'étude de non-symétrie temporelle | Renvoi vers §5.4 et démonstration/essais en annexe E.4. |
| §2.6 / figure 2 : K et γ distincts, croisement, légende | **Corrigé** : stocks 20 et 4 ; exposants 1/4 et 1/2 ; croisement à K=16 ; gain de coopération recalculé pour cette paire ; légende concordante. |
| §3 : titre au pluriel | « Des démarches expérimentales en plusieurs étapes ». |
| §4.4 / figure 6 : supprimer commentaire sur les dates manquantes | Retiré de la légende ; dates effectivement utilisées conservées. |
| §4.4 : valeur nette / NW et centralité | Définition explicite ; section maintenue dans le corps ; réserves de comparabilité maintenues. |
| §5 / figure 7 : étude de k non prioritaire pour l'article, à conserver pour le rapport | **Corrigé** : panneau k retiré du PDF courant ; ancien graphique et données conservés dans l'archive. |
| §5.4 / figure 8 : supprimer la phrase « Le dernier panneau… » | Phrase supprimée de la figure rho, et non de la figure de recalage temporel. |
| §6.2 : compensation de K° et κ° | Explication des échelles et des apports supplémentaires aux nouvelles entités ; distinction avec rééchelonnement de tout l'état. |
| §6.4 : A×1,5 et exploration plus large | Portée, date, dotation fixe et exploration future explicitées. |
| §6.4 : paramètres des 111 pas et médiane | Configuration complète ; 110,97 pas de moyenne, 40,05 pour la moyenne des médianes instantanées, méthode et IC95 explicités. |
| §6.4 / figure 13 : panneau NW, pas capital | **Corrigé** : troisième panneau NW recalculé depuis K+C−D ; classement commun par capital conservé et annoncé, sans l'assimiler à un classement par NW. |
| §7 / figure 14 : règle archaïque, référence illustrative | Mention explicite dans la légende, exclusion de la régression maintenue. |
| Annexe C : « l'ancienne section… corrigée » | Phrase exacte absente des sources incluses et de la référence V2 ; mot éditorial « corrigé » retiré, définitions scientifiques conservées. Localisation exacte encore nécessaire si un autre passage est visé. |

## Contrôles d'application

Les figures 2 et 7 remplacent effectivement leurs PDF inclus. La figure 13 utilise désormais `art_deciles`, avec ses nouveaux CSV par graine ; l'ancien `rev_deciles` n'est plus inclus. Le générateur complet appelle les corrections V2 pour éviter qu'une régénération ne rétablisse les anciens panneaux.

Les quatorze tests (neuf antérieurs et cinq V2) passent, ainsi que la compilation autonome en trois passes. Les trois nouveaux graphiques ont été inspectés visuellement. Le rapport de stage, les moteurs et les générateurs Simulation Lab restent intacts. Les décisions et leurs réserves sont conservées pour le futur rapport, sans application actuelle à celui-ci.
