# Feuille de route -- analyse des équations de la vie d'une entité

## Objectif

Construire une note LaTeX autonome, compilable avec `pdflatex`, qui relie l'équation
`dx/dt = -delta x + b sqrt(x) + c` au modèle multi-agents de `note.pdf`, puis l'étend en appendice au cas
`dx/dt = -delta x + b f(x) + c` pour des extractions concaves plus générales.

## Principes de rédaction

- Rester honnête sur le statut de l'EDO : brique analytique, pas preuve du modèle complet.
- Garder le lien avec le modèle : extraction concave, dépréciation exponentielle, crédit, faillites, classes d'entités.
- Privilégier des critères qualitatifs robustes : existence d'équilibres, stabilité, seuils de viabilité.
- Conserver une note compilable sans figures externes, avec TikZ/PGFPlots uniquement.

## Plan de travail annoté

1. Lire `note.pdf` et identifier les points à raccrocher.
   - Statut : fait.
   - Notes : les points centraux sont `Pi_i = alpha_i sqrt(P_i)`, la dépréciation endo/exo, les prêts perpétuels, les intérêts, les faillites bilancielles et la séparation banques/travailleurs.

2. Produire le document principal sur le cas racine carrée.
   - Statut : fait en première version.
   - Notes : le document contient introduction, changement de variable, classification en cinq cas, figures PGFPlots, discussion modèle.

3. Corriger la compilation de la première version.
   - Statut : correction appliquée.
   - Notes : première erreur trouvée dans une option PGFPlots de légende (`legend pos=east` non valide). Remplacée par une position standard.

4. Ajouter un appendice généralisé `b f(x)`.
   - Statut : rédigé dans le fichier LaTeX, compilation à vérifier.
   - Sous-plan :
     - Racine cubique : `f(x)=x^{1/3}` ; poser `z=x^{1/3}` ou analyser directement `g(x)=-delta x + b x^{1/3}+c`.
     - Puissance générale : `f(x)=x^{1/a}`, `a>1` ; déterminer le maximum de `h(x)=delta x - b x^{1/a}` et le seuil critique.
     - Concave générale : hypothèses minimales sur `f`, existence et nombre des équilibres via la concavité de `G(x)=delta x-bf(x)`, stabilité par le signe de `F(x)=-delta x+bf(x)+c`.
   - Résultat mathématique central :
     - Pour `f(x)=x^{1/a}`, `x_m=(b/(a delta))^{a/(a-1)}`.
     - `M=b(1-1/a)(b/(a delta))^{1/(a-1)}`.
     - `c_crit(a)=-M`.
     - Pour une fonction concave générale, `c_crit=-max_x {b f(x)-delta x}` sous hypothèses de sous-linéarité.

5. Recompiler et noter les limites.
   - Statut : fait.
   - Points vérifiés :
     - `pdflatex` produit le PDF.
     - Les références croisées sont stabilisées après double compilation.
     - L'appendice ne prétend pas prouver le modèle complet ; il reste présenté comme brique analytique.
     - Le seuil généralisé est formulé par `c_crit=-max_x {b f(x)-delta x}`.
   - Point restant non bloquant :
     - La compilation signale des messages `Missing character ... nullfont` autour d'une figure TikZ. Le PDF est produit correctement ; à traiter plus tard si l'on veut un log parfaitement propre.

## État final de ce cycle

- Fichier LaTeX : `analyse_des_equations_de_la_vie_d_une_entite.tex`.
- PDF généré : `analyse_des_equations_de_la_vie_d_une_entite.pdf`.
- Extension ajoutée : appendice sur `dx/dt=-delta x+b f(x)+c`.
- Cas couverts : racine cubique, puissance `x^{1/a}` avec `a>1`, fonction concave générale.
