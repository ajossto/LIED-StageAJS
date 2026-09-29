# Contrôles de l'adaptation — 25 septembre 2026

## Périmètre

Contrôles ciblés du rapport et de ses exports ; aucune simulation, aucun test moteur ni recalcul complet des campagnes. Les valeurs transférées de l'article sont vérifiées contre ses exports par graine, pas présentées comme une réplication indépendante de tous les résultats.

Commande reproductible depuis la racine du dépôt :

```bash
OPENBLAS_NUM_THREADS=1 .venv/bin/python recherche/note_communication_encadrants/scripts/verify_stage.py --compile
```

## Résultats

- **Références et provenance** : aucune référence LaTeX manquante, aucun label dupliqué ; les 54 fichiers de figures et les trois schémas TikZ ont une entrée de provenance. Les figures retirées ne produisent pas de renvois orphelins.
- **Conservation** : 105 empreintes d'artefacts locaux contrôlées ; 150 documents protégés (article, mémos, questionnaires) inchangés. La sauvegarde complète du rapport avant adaptation est conservée.
- **Réponse technologique** : recalcul des moyennes et IC95 de Student à partir des douze log-rapports appariés : 0,7473 ± 0,0106 à dotation fixe ; 2,0029 ± 0,0148 avec compensation. Cohérence logarithme/rapport vérifiée.
- **Déciles** : dix parts par observable, bras et graine ; somme égale à un à la précision numérique. La figure porte sur production, intérêts et NW, classés par capital.
- **Âges** : douze graines, cent instantanés par graine ; moyennes et IC95 des âges moyens et des médianes instantanées conformes aux exports de la passe V2.
- **Renouvellement** : empreintes de tous les instantanés utilisés ; rétention ≤ survie ; survie non croissante ; ancrages à un ; premiers franchissements conformes aux exports. Les comptages finaux sont également relus directement depuis les instantanés, indépendamment du CSV.
- **Compilation autonome** : trois passes dans un dossier temporaire ne contenant que les sources LaTeX et les figures ; succès sans débordement, référence indéfinie ou label multiple. Le PDF courant est aussi reconstruit dans son dossier local.
- **Rendu** : relecture visuelle ciblée de la couverture/résumé, technologies et surplus, histogrammes d'avalanches, renouvellement, diagnostic de charge, glossaire et table de provenance. Aucun défaut de mise en page bloquant observé sur ces pages. Ce contrôle n'est pas une inspection visuelle exhaustive de chaque page.
- **Diff** : `git diff --check` ne signale pas d'erreur d'espacement dans les changements suivis du rapport.

## Limites maintenues

La stabilité d'un indicateur, un R² élevé ou le remplacement des membres d'un décile ne démontrent ni invariance distributionnelle, ni adéquation absolue, ni indépendance de l'initialisation. Les snapshots des deux runs M4.3 ne valent pas validation générale des fenêtres M4.4. Les figures historiques conservent leur convention d'incertitude et leur qualité graphique d'origine ; seules les nouvelles figures et les copies vectorielles disponibles sont vectorielles.

Les sources extérieures peuvent évoluer dans le laboratoire : les manifestes du rapport figent ce qui a été utilisé. Les éléments retirés du texte courant restent accessibles dans l'archive du rapport et les rapports de campagne ; leur conservation ne les requalifie pas comme preuves validées.

## Artefact livré

PDF : 85 pages, 57 figures. SHA-256 :

```text
848cb567a288f1b5726ae2d1b9b8ae17a567e0b9f1339d282f4408bfe10291c4
```
