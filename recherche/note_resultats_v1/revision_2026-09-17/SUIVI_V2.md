# État de la deuxième passe — 17 septembre 2026

## Livrables et périmètre

- [Article de travail](../latex/note.pdf) : corrections rédactionnelles, méthodologiques et graphiques V2 intégrées. Après vérification demandée par l'auteur, les figures 2, 7 et 13 ont été corrigées ; les anciennes versions restent archivées.
- [Registre des 24 décisions](REGISTRE_CORRECTIONS_V2.md) : chaque note renseignée est rattachée à une décision et à son transfert différé. Ce registre complète, sans le remplacer, celui des 15–17 septembre.
- [Carnet rempli figé](reference/COMMENTAIRES_PROTO_ARTICLE_V2.md), [PDF commenté](reference/note.pdf), sources et figures de référence dans `reference/latex_avant_v2/`.
- Aucun changement du rapport de stage, des moteurs, de Simulation Lab, de ses générateurs ou des campagnes. Aucune simulation lancée.

Le carnet original et sa copie ont la même empreinte SHA-256 :
`efeac5f2d2865e09ec2115f301b69f171ba0454f0408a892c7a37d7e39fc35cf`.

## Vérifications

### Ordre de lecture demandé après la passe V2

Les références bibliographiques précèdent désormais les annexes. Le glossaire
devient l'annexe A ; les autres annexes sont décalées de B à F, avec renvois
LaTeX automatiques. Cette consigne est conservée pour le futur traitement du
rapport de stage, sans modification de celui-ci.

Depuis `/home/anatole/jupyter/recherche/` :

```bash
OPENBLAS_NUM_THREADS=1 ../.venv/bin/python note_resultats/scripts/ages_v2.py
OPENBLAS_NUM_THREADS=1 ../.venv/bin/python note_resultats/scripts/figures_v2.py
OPENBLAS_NUM_THREADS=1 ../.venv/bin/python note_resultats/scripts/verify_v2.py
OPENBLAS_NUM_THREADS=1 ../.venv/bin/python note_resultats/scripts/verify_article.py --compile
```

- Recalcul des moyennes et médianes instantanées sur les panneaux existants : 24 combinaisons bras/graine, 100 instantanés chacune. Sorties dans `ages_v2_graines.csv` et `ages_v2.json`, avec les empreintes de toutes les sources.
- Cinq tests V2 passent : préservation des annotations et des figures non modifiées ; agrégation et empreintes des âges ; composition temporelle et compensation ; lecture de l'archive de parité sur 8000 pas ; corrections graphiques (parts, IC95, croisement, optimum, retrait de k, exports SVG). Ils ne relancent pas les moteurs.
- Les neuf contrôles antérieurs passent, notamment empreintes du rapport, cohérence des références LaTeX, sources des calculs et résultats numériques.
- Compilation autonome en trois passes réussie. Un débordement initial dû à un long chemin a été corrigé ; aucun débordement ni référence non résolue au contrôle final. L'avertissement de substitution de petites capitales grasses était déjà présent.
- Les treize PDF de figures inclus ne contiennent aucune image matricielle incorporée (`pdfimages -list`). Les trois autres figures sont dessinées en TikZ.
- Relecture visuelle ciblée des nouveaux développements, de la composition temporelle et du glossaire. Ce contrôle ne prétend pas revalider scientifiquement tout le projet ni remplacer la future revue des figures.

## Ce qui reste expressément ouvert

1. Attendre la fin des générateurs et de la génération des figures de l'auteur ; ne pas lancer une campagne entre-temps.
2. Intégrer l'étude de renouvellement, vérifier le décile concerné et ne pas assimiler disparition des membres à indépendance de l'état initial.
3. **Résolu après vérification** : technologies hétérogènes et stocks distincts avec croisement en figure 2 ; retrait du panneau k en figure 7 ; panneau de parts NW remplaçant les parts K en figure 13. Le classement des trois panneaux reste par capital, explicitement indiqué : grandeur mesurée et critère de classement ne sont pas synonymes.
4. Renommage officiel différé par l'auteur, sans blocage de la révision. Sa précision du 17 septembre porte sur le changement substantiel de la **règle du taux d'emprunt**, pas simplement sur le sens du prêt ou l'instrumentation. Conserver les noms techniques actuels et distinguer les règles de taux dans les comparaisons ; voir V2-004.
5. Réévaluer la cible de 15–20 pages **hors annexes** après intégration graphique : le corps actuel occupe environ 14 pages. Traductions et mise en page de diffusion restent à préparer, pas à exécuter maintenant.
6. La suppression demandée en annexe C vise une phrase non retrouvée telle quelle ; le mot éditorial « corrigé » a été retiré, sans supprimer les définitions scientifiques.

Le rapport de stage reste **non modifié**. Toutes les réserves ci-dessus doivent accompagner les corrections lors de son futur traitement.
