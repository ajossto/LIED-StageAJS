# Révision du proto-article — 15–17 septembre 2026

Périmètre : article seul ; le rapport et les commentaires originaux restent inchangés. La version commentée est conservée dans `reference/latex/` et le carnet original dans `reference/`.

## Travail prévu

1. Vérifier chaque annotation et les possibilités réelles de recalcul.
2. Recentrer le texte sur le mandat physique du stage, l'émergence et les leviers de pilotage.
3. Construire des schémas vectoriels explicatifs, recalculer les graphiques et documenter les estimateurs.
4. Retirer les conclusions devenues injustifiées ; déplacer les développements secondaires en annexe.
5. Compiler et contrôler le PDF, les sources numériques, la couverture des annotations et la préservation du rapport.

## Constats initiaux

- Le fardeau antérieur était `debts/prod`, pas un taux de charge. Le nouveau diagnostic distinguera dette/revenu brut et intérêts effectivement versés/revenu brut. Les intérêts dus ne sont pas enregistrés dans les panneaux ; les assimiler aux intérêts versés serait injustifié en présence de prorata.
- Les panneaux de référence disponibles couvrent 2010 à 4000, tous les dix pas. Aucun instantané à 1000 ou 8000 n'y figure. Le checkpoint à 2000 contient un état dynamique, pas un panneau comparable des flux de fin de pas ; ne pas inventer ces observations.
- Les ajustements d'avalanches antérieurs étaient des puissances simples, et la régression visuelle portait sur des survies. Il faut distinguer explicitement la masse de probabilité, la survie, l'exposant et la coupure.
- Le Gini du « bassin » est celui de l'échantillon de rencontre, pas celui du capital de la population. Le pilotage du Gini de valeur nette nécessite un calcul propre.
- Wright étudie des durées de récession annuelles et conclut en faveur de l'exponentielle sur les données complètes. Les contractions par pas non calibré du modèle ne valident pas directement cette observation empirique.
- Une compensation de la seule dotation à partir d'un état non rééchelonné n'est pas la symétrie exacte qui rééchelonne tout l'état. Ne pas lui attribuer exactement l'élasticité théorique 2.

## Bilan

Le texte est restructuré, les onze nouvelles figures recalculées et les schémas intégrés. Les méthodes, contrôles de stationnarité et développements secondaires sont en annexe. Le [registre des corrections](REGISTRE_CORRECTIONS.md) détaille les décisions et adaptations futures au rapport.

Les contrôles sont reproductibles avec `../scripts/verify_article.py --compile` : neuf tests ciblés et compilation autonome en trois passes. Aucun moteur, aucune campagne et aucun document du rapport n'ont été modifiés par cette révision. Les empreintes du carnet original, du PDF archivé et des fichiers principaux du rapport sont contrôlées.

Les dates d'instantanés absentes et l'éventuelle recherche exploratoire d'une réponse négative restent ouvertes ; elles ne sont pas présentées comme réalisées.
