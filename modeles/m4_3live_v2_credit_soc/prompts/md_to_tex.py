"""Convertit le prompt markdown en LaTeX, puis en PDF.

Pourquoi un convertisseur et pas une transcription à la main : le document
fait plus de 800 lignes et il sera révisé (c'est le PDF que l'utilisateur
annote, et ses annotations produisent la révision suivante). Une
transcription manuelle diverge dès la première révision ; un convertisseur
garde le markdown comme source unique.

Périmètre volontairement étroit — il ne gère que ce que ce document emploie :
titres de niveau 2 et 3, listes à puces et numérotées, tableaux, citations,
gras, italique, code inline, blocs de code, séparateurs.

    python3 prompts/md_to_tex.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "PROMPT_M4_3LIVE_V2.md"
TARGET = HERE / "PROMPT_M4_3LIVE_V2.tex"

#: Caractères non-ASCII employés par le document, déclarés au moteur LaTeX.
#: Les lettres accentuées latines passent seules avec inputenc ; seuls les
#: symboles grecs et mathématiques ont besoin d'une déclaration.
UNICODE = {
    "γ": r"\ensuremath{\gamma}", "δ": r"\ensuremath{\delta}",
    "σ": r"\ensuremath{\sigma}", "λ": r"\ensuremath{\lambda}",
    "ρ": r"\ensuremath{\rho}", "ε": r"\ensuremath{\varepsilon}",
    "η": r"\ensuremath{\eta}", "Δ": r"\ensuremath{\Delta}",
    "Σ": r"\ensuremath{\sum}", "≥": r"\ensuremath{\geq}",
    "μ": r"\ensuremath{\mu}", "α": r"\ensuremath{\alpha}",
    "β": r"\ensuremath{\beta}", "θ": r"\ensuremath{\theta}",
    "ℓ": r"\ensuremath{\ell}", "∈": r"\ensuremath{\in}",
    "∝": r"\ensuremath{\propto}", "√": r"\ensuremath{\sqrt{\;}}",
    "≈": r"\ensuremath{\approx}", "≤": r"\ensuremath{\leq}",
    "×": r"\ensuremath{\times}", "−": r"\ensuremath{-}",
    "→": r"\ensuremath{\rightarrow}", "·": r"\ensuremath{\cdot}",
    "′": r"\ensuremath{'}", "²": r"\ensuremath{^2}",
    "³": r"\ensuremath{^3}", "¹": r"\ensuremath{^1}",
    "⁵": r"\ensuremath{^5}", "⁻": r"\ensuremath{^-}",
    "₀": r"\ensuremath{_0}", "̄": "", "…": r"\dots{}",
    "—": "---", "–": "--", "°": r"\degree{}",
}

PREAMBLE = r"""\documentclass[11pt,a4paper]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[french]{babel}
\usepackage{lmodern}
\usepackage{amsmath,amssymb}
\usepackage[margin=2.35cm]{geometry}
\usepackage{booktabs,longtable,tabularx}
\usepackage{enumitem}
\usepackage{xcolor}
\usepackage{microtype}
\usepackage{hyperref}

\hypersetup{colorlinks=true,linkcolor=blue!45!black,urlcolor=blue!45!black}
\setlist{nosep}
\newcommand{\code}[1]{\texttt{#1}}
\providecommand{\degree}{\ensuremath{^\circ}}
\sloppy

\title{Prompt M4.3Live-v2\\
\large Libérer le sens du prêt, et chercher ce qui détermine la rotation
du crédit}
\author{Lignée M4.3Live-v2 --- succède à M4.3Live
(\code{m4\_3live\_credit\_soc}, programme terminé et publié),\\
destiné à une instance Claude Opus 5}
\date{21 août 2026 --- révision 1}

\begin{document}
\maketitle
\tableofcontents
\bigskip
"""


#: Échappements propres au markdown (`\*`, `\_`, `\|`) : ils n'ont pas de
#: sens en LaTeX et doivent disparaître AVANT que `\` ne soit échappé.
MARKDOWN_ESCAPES = re.compile(r"\\([*_|`\[\]])")


def escape(text: str) -> str:
    """Échappe le texte courant (hors code inline, traité séparément)."""
    text = MARKDOWN_ESCAPES.sub(r"\1", text)
    for char, replacement in (("\\", r"\textbackslash{}"), ("&", r"\&"),
                              ("%", r"\%"), ("$", r"\$"), ("#", r"\#"),
                              ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
                              ("~", r"\textasciitilde{}"),
                              ("^", r"\textasciicircum{}")):
        text = text.replace(char, replacement)
    for char, replacement in UNICODE.items():
        text = text.replace(char, replacement)
    return text


def code_escape(text: str) -> str:
    """Échappe l'intérieur d'un \\code{} : verbatim-like mais robuste."""
    for char, replacement in (("\\", r"\textbackslash{}"), ("&", r"\&"),
                              ("%", r"\%"), ("$", r"\$"), ("#", r"\#"),
                              ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
                              ("~", r"\textasciitilde{}"),
                              ("^", r"\textasciicircum{}")):
        text = text.replace(char, replacement)
    for char, replacement in UNICODE.items():
        text = text.replace(char, replacement)
    # `--full` ne doit pas devenir un tiret demi-cadratin dans du \texttt.
    return text.replace("--", "-{}-")


def inline(text: str) -> str:
    """Gras, italique et code inline, dans cet ordre.

    Le code inline est extrait AVANT tout échappement, sinon les
    caractères spéciaux qu'il contient (`_`, `^`, `{`) seraient échappés
    deux fois.
    """
    chunks: list[str] = []

    def stash(match: re.Match) -> str:
        chunks.append(r"\code{" + code_escape(match.group(1)) + "}")
        return f"\x00{len(chunks) - 1}\x00"

    text = re.sub(r"`([^`]+)`", stash, text)
    text = escape(text)
    # Gras d'abord, en NON-GLOUTON : le gras peut contenir de l'italique
    # (`**du *gras* italique**`), que la passe suivante traitera.
    text = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\\emph{\1}", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: chunks[int(m.group(1))], text)


def table(rows: list[str]) -> list[str]:
    """Un tableau markdown → longtable. La première ligne est l'en-tête,
    la deuxième (les tirets) donne le nombre de colonnes."""
    cells = [[c.strip() for c in row.strip().strip("|").split("|")] for row in rows]
    header, body = cells[0], cells[2:]
    n = len(header)
    # Une colonne dont aucune cellule ne dépasse WIDE caractères reste en `l`
    # (elle n'a pas besoin d'être justifiée) ; les autres passent en `X` et se
    # partagent la largeur restante. Sans cette heuristique, un tableau à
    # quatre colonnes écrase les colonnes courtes (« Lot », « Coût »).
    wide = 22
    widths = [max(len(row[column]) if column < len(row) else 0
                  for row in cells) for column in range(n)]
    spec = "@{}" + "".join("l" if width <= wide else "X"
                           for width in widths) + "@{}"
    if "X" not in spec:  # tout est court : laisser LaTeX répartir
        spec = "@{}" + "l" * n + "@{}"
    out = [r"\begin{center}", rf"\begin{{tabularx}}{{\linewidth}}{{{spec}}}",
           r"\toprule",
           " & ".join(rf"\textbf{{{inline(c)}}}" for c in header) + r" \\",
           r"\midrule"]
    for row in body:
        row = (row + [""] * n)[:n]
        out.append(" & ".join(inline(c) for c in row) + r" \\")
    out += [r"\bottomrule", r"\end{tabularx}", r"\end{center}"]
    return out


def convert(markdown: str) -> str:
    lines = markdown.split("\n")
    out: list[str] = []
    index = 0
    list_stack: list[str] = []

    def close_lists(depth: int = 0) -> None:
        while len(list_stack) > depth:
            out.append(rf"\end{{{list_stack.pop()}}}")

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if stripped.startswith("```"):
            close_lists()
            index += 1
            block = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                block.append(lines[index])
                index += 1
            index += 1
            out += [r"\begin{quote}\footnotesize", r"\begin{verbatim}"]
            out += block
            out += [r"\end{verbatim}", r"\end{quote}"]
            continue

        if stripped.startswith("|") and index + 1 < len(lines) \
                and set(lines[index + 1].strip()) <= set("|-: "):
            close_lists()
            block = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                block.append(lines[index])
                index += 1
            out += table(block)
            continue

        if stripped == "---":
            close_lists()
            out.append(r"\bigskip")
            index += 1
            continue

        if stripped.startswith("# "):
            index += 1  # le titre est déjà dans \maketitle
            continue
        if stripped.startswith("### "):
            close_lists()
            out.append(rf"\subsection*{{{inline(stripped[4:])}}}")
            index += 1
            continue
        if stripped.startswith("## "):
            close_lists()
            title = stripped[3:]
            # « 3. Les quatre changements » → section numérotée par LaTeX
            match = re.match(r"^(\d+)\.\s+(.*)$", title)
            if match:
                out.append(rf"\setcounter{{section}}{{{int(match.group(1)) - 1}}}")
                out.append(rf"\section{{{inline(match.group(2))}}}")
            else:
                out.append(rf"\section*{{{inline(title)}}}")
            index += 1
            continue

        if stripped.startswith("> "):
            close_lists()
            block = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                block.append(lines[index].strip().lstrip(">").strip())
                index += 1
            out += [r"\begin{quote}", inline(" ".join(b for b in block if b)),
                    r"\end{quote}"]
            continue

        bullet = re.match(r"^(\s*)-\s+(.*)$", line)
        number = re.match(r"^(\s*)(\d+)\.\s+(.*)$", line)
        if bullet or number:
            match = bullet or number
            depth = len(match.group(1)) // 2 + 1
            kind = "itemize" if bullet else "enumerate"
            close_lists(depth)
            while len(list_stack) < depth:
                list_stack.append(kind)
                out.append(rf"\begin{{{kind}}}")
            body = match.group(2) if bullet else match.group(3)
            index += 1
            # continuation : lignes suivantes plus indentées et non-vides
            while index < len(lines) and lines[index].strip() \
                    and not re.match(r"^\s*(-|\d+\.)\s", lines[index]) \
                    and not lines[index].strip().startswith(("#", "|", ">", "```")) \
                    and lines[index].startswith(" "):
                body += " " + lines[index].strip()
                index += 1
            out.append(rf"\item {inline(body)}")
            continue

        if not stripped:
            close_lists()
            out.append("")
            index += 1
            continue

        close_lists()
        paragraph = [stripped]
        index += 1
        while index < len(lines) and lines[index].strip() \
                and not lines[index].strip().startswith(("#", "|", ">", "-", "```")) \
                and not re.match(r"^\s*\d+\.\s", lines[index]) \
                and lines[index].strip() != "---":
            paragraph.append(lines[index].strip())
            index += 1
        out.append(inline(" ".join(paragraph)))

    close_lists()
    return "\n".join(out)


def main() -> int:
    body = convert(SOURCE.read_text(encoding="utf-8"))
    TARGET.write_text(PREAMBLE + body + "\n\n\\end{document}\n", encoding="utf-8")
    print(f"{TARGET.name} écrit ({len(body.splitlines())} lignes)")
    for _ in range(3):
        # pdflatex écrit du latin-1 dans son flux : on ne le décode pas.
        subprocess.run(["pdflatex", "-interaction=nonstopmode", TARGET.name],
                       cwd=HERE, capture_output=True)
    log = (HERE / (TARGET.stem + ".log")).read_text(encoding="utf-8", errors="replace")
    errors = [line for line in log.split("\n") if line.startswith("! ")]
    if errors:
        print("ERREURS LaTeX :")
        for line in errors[:12]:
            print("  ", line)
        return 1
    pdf = HERE / (TARGET.stem + ".pdf")
    print(f"{pdf.name} : {pdf.stat().st_size} octets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
