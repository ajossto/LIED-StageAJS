# Prompts M4.2

Le prompt canonique est `PROMPT_M4_2.md`. La source
`PROMPT_M4_2.tex` inclut directement ce fichier Markdown afin que le PDF et la
version copiable partagent strictement le même contenu.

Compilation depuis ce dossier :

```bash
xelatex -shell-escape -interaction=nonstopmode -halt-on-error PROMPT_M4_2.tex
xelatex -shell-escape -interaction=nonstopmode -halt-on-error PROMPT_M4_2.tex
```

Les variantes de travail éventuelles doivent être nommées explicitement et ne
pas remplacer silencieusement la version canonique.
