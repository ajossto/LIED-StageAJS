"""Rassemble les figures historiques incluses et les macros de nombres.

Aucune figure n'est dessinée ici : les images historiques sont engendrées par
`m4_4_rebond_credit_soc/scripts/make_figures.py` depuis les fichiers
d'analyse de la campagne, ou par l'interface locale. Ce script les copie et
vérifie qu'aucune n'est incluse sans exister ni copiée sans servir.
Les compléments rev_* sont produits par revision_documents/build_visuals.py.

Ce garde-fou existe parce que la note longue a inclus cinq figures absentes
sans que la compilation le dise assez fort pour qu'on le voie.

    /home/anatole/jupyter/.venv/bin/python3 scripts/collect.py
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

ICI = Path(__file__).resolve().parent.parent
DEPOT = ICI.parent.parent
FIGURES = ICI / "latex" / "figures"
M4_4 = DEPOT / "m4_4_rebond_credit_soc" / "report"
LIGNEE = DEPOT / "m4_3live_credit_soc" / "report" / "figures"

#: Quatorze figures, choisies pour rester lisibles à 0,78 de la largeur de
#: ligne — vérifié au rendu, pas supposé.
FIGURES_M4_4 = (
    "f08_avalanches_ccdf",  # les cascades et leur coupure de taille finie
    "f09_b1_b2",            # deux estimateurs de propagation, et leur écart
    "f07_chaine",           # la chaîne causale de la contraction
    "f10_k0",               # la fragilité est un effet d'échelle
    "f03_quantiles",        # où se dépose le surcroît
    "f04_deciles",          # producteurs ou rentiers
    "f14_bargain_population",  # l'anomalie du partage
    "f21_hasard",           # la convexité posée, et sa réfutation
    "f22_ponderation",      # l'identité de covariance
    "g03_partage_analytique",  # la covariance dérivée des fonctions du moteur
    "f23_suffisance",       # sur-détermination contre suffisance
    "f15_bargain_gini",     # l'invariance du Gini de valeur nette
    "f17_rho_controle",     # ce que l'intensité de marché contrôle
    "f13_vuong",            # pourquoi Pareto est indécidable
)
#: Une figure vient de la lignée qui a mesuré le rebond ; elle est reprise
#: telle quelle, la parité bit à bit rendant ce moteur identique au nôtre
#: sur la restriction correspondante.
FIGURES_LIGNEE = ("r01_reponse_prod",)


def main() -> int:
    if (ICI / "latex/corps_article.tex").exists():
        print("Collecteur historique désactivé pour l'article restructuré. "
              "Utiliser scripts/revision_article.py puis scripts/verify_article.py ; "
              "aucun fichier n'a été modifié.")
        return 1
    FIGURES.mkdir(parents=True, exist_ok=True)
    copiees: set[str] = set()
    incluses = set(re.findall(r"\\figurine\{([^}]+)\}",
                             (ICI / "latex/note.tex").read_text()))

    for nom in FIGURES_M4_4:
        if nom not in incluses:
            continue
        source = M4_4 / "figures" / f"{nom}.pdf"
        if not source.exists():
            print(f"INTROUVABLE : {source}")
            return 1
        shutil.copy2(source, FIGURES / f"{nom}.pdf")
        copiees.add(nom)

    for nom in FIGURES_LIGNEE:
        source = LIGNEE / "response_prod.png"
        if not source.exists():
            print(f"INTROUVABLE : {source}")
            return 1
        shutil.copy2(source, FIGURES / f"{nom}.png")
        copiees.add(nom)

    macros = M4_4 / "numbers.tex"
    entete = (
        "% Copié par scripts/collect.py depuis\n"
        "%   m4_4_rebond_credit_soc/report/numbers.tex\n"
        "% engendré par scripts/make_numbers.py depuis results/analysis/.\n"
        "% NE PAS ÉDITER À LA MAIN.\n\n"
    )
    texte = macros.read_text(encoding="utf-8")
    (ICI / "latex" / "numbers.tex").write_text(entete + texte, encoding="utf-8")
    print(f"{len(copiees)} figures copiées, "
          f"{texte.count(chr(92) + 'newcommand')} macros")

    note = ICI / "latex" / "note.tex"
    if not note.exists():
        return 0
    incluses = set(re.findall(r"\\figurine\{([^}]+)\}",
                              note.read_text(encoding="utf-8")))
    copiees.update(n for n in incluses if n.startswith("rev_") and (FIGURES / f"{n}.pdf").exists())
    absentes = sorted(incluses - copiees)
    orphelines = sorted(copiees - incluses)
    if absentes:
        print("INCLUSES MAIS NON COPIÉES :", *absentes, sep="\n  ")
    if orphelines:
        print("COPIÉES MAIS JAMAIS INCLUSES :", *orphelines, sep="\n  ")
    if not absentes and not orphelines:
        print(f"{len(incluses)} inclusions, toutes résolues, aucune orpheline")
    return 1 if absentes else 0


if __name__ == "__main__":
    raise SystemExit(main())
