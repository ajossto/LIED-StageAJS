# Note d'interprétation abstraite du modèle

## Intention

Le vocabulaire du code (`actif`, `passif`, `prêt`, `intérêt`, `faillite`) sert d'interface de lecture, mais le mécanisme implémenté est plus général : une dynamique d'entités couplées où des capacités locales, des dépendances orientées et des fragilités se co-produisent dans le temps.

## Lecture fonctionnelle (et non sectorielle)

- `actif_*` : réserve mobilisable (liquide immédiat, capacité engagée, créance sur autrui).
- `passif_*` : taille engagée qui soutient la capacité d'extraction mais augmente l'exposition aux chocs.
- `Loan` : lien orienté durable qui transfère une capacité locale et crée une dépendance structurante.
- `interest_due()` : flux récurrent associé au lien orienté.
- `BankruptcyEstate` : mécanisme de redistribution post-rupture et transmission de dépendances résiduelles.

## Structure dynamique effectivement implémentée

À chaque pas, la simulation applique une boucle d'évolution qui ressemble à un système complexe dissipatif :

1. **Entrées de nouvelles entités** (processus de Poisson).
2. **Injection locale de ressource** via `Π = α * sqrt(P)` (croissance sous-linéaire avec la taille engagée).
3. **Contraintes de service des liens** (paiement des flux), avec ajustements forcés en cas d'illiquidité :
   - consommation du liquide,
   - cession de créances,
   - conversion partielle endo-investi → liquide.
4. **Dissipation** des stocks (dépréciations).
5. **Réallocation adaptative** via marché du crédit.
6. **Renforcement local** via auto-investissement du surplus.
7. **Perte de viabilité locale** et **propagation** de cascades de rupture.
8. **Mesure multi-échelle** (indicateurs systémiques + distributions + événements de cascade).

## Hypothèse explorée par le code

Le coeur du modèle est l'interaction entre :

- croissance locale sous-linéaire de la capacité d'extraction,
- accumulation de taille engagée,
- couplages orientés entre entités,
- mécanismes de fragilisation et de propagation.

Cette combinaison est compatible avec l'émergence de régimes critiques, de cascades et d'effets de rebond macroscopiques, sans imposer une lecture strictement économique.

## Guide de lecture recommandé

Pour analyser le modèle, séparer systématiquement :

1. **Sémantique de surface** (noms des variables).
2. **Rôle dynamique réel** (ce que la variable fait dans les équations de mise à jour).
3. **Portée abstraite** (classe de systèmes complexes que le mécanisme représente).

En pratique, la bonne granularité d'analyse n'est pas "l'agent économique", mais le triplet :
**réserves locales + liens orientés + règles de rupture/propagation**.
