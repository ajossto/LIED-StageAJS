"""Rassemble les figures de la note, et engendre leur table de provenance.

Aucune figure n'est dessinée ici. Toutes existent déjà, produites par les
campagnes ou par Simulation Lab. Ce script les COPIE dans `latex/figures/` et
écrit `latex/provenance.tex`, la table qui dit pour chacune d'où elle vient et
ce qu'elle établit.

Pourquoi copier plutôt que pointer vers l'original : la note doit rester
compilable si un dossier de lignée est archivé, déplacé ou purgé, et
`simulation_lab_data/` n'est pas versionné. Une note qui cesse de compiler
parce qu'un run a été nettoyé n'est pas un document autonome.

Pourquoi une table engendrée plutôt qu'écrite à la main : c'est la même règle
que celle des campagnes — un tableau recopié dérive du jour où une figure est
remplacée. Ici la table et les fichiers sortent du même dictionnaire.

    /home/anatole/jupyter/.venv/bin/python3 scripts/collect_figures.py
"""

from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent.parent
DEPOT = ICI.parent.parent
FIGURES = ICI / "latex" / "figures"

#: Un run Simulation Lab de confirmation M4B, au point central de la campagne
#: (lam=30, delta=0,05, sigma=0,5, K0=25, k=2, T=4000, graine 14). C'est le run
#: dont l'IHM a produit la batterie d'analyses individuelles ; il sert de
#: spécimen dans toute la note.
SPECIMEN = "20260718_033746_8b0c5acb"
LAB = DEPOT / "simulation_lab_data" / "runs" / SPECIMEN / "figures"

#: nom dans la note -> (chemin source, origine lisible, ce que la figure établit)
#: L'ordre est celui de la table de provenance ; le préfixe est celui de la
#: partie où la figure apparaît.
CATALOGUE: dict[str, tuple[Path, str, str]] = {
    # ---- Partie 2 : le modèle ----
    "m01_reseau_credit": (
        LAB / "loan_network_final.png",
        f"Simulation Lab, run {SPECIMEN} (M4B, point central, graine 14)",
        "Le réseau de crédit final : aucun type déclaré, et 182 entités sur 228 "
        "sont simultanément prêteuses et emprunteuses.",
    ),
    "m02_vue_macro": (
        LAB / "macro_overview.png",
        f"Simulation Lab, run {SPECIMEN}",
        "Capital, crédit nouveau, population et levier sur 4000 pas : le "
        "système est borné et stationnaire, sans dérive ni extinction.",
    ),
    # ---- Partie 3 : la trajectoire ----
    "t01_artefact_cohorte": (
        DEPOT / "recherche/analyse_distributions_taille_revenu/figures/age_cohorte.png",
        "recherche/analyse_distributions_taille_revenu, campagne du WIP "
        "du 27 avril (163 runs stationnaires sur 805)",
        "Le résultat négatif fondateur : la bimodalité lue comme « banques et "
        "travailleurs » est une structure d'âge, pas deux classes économiques.",
    ),
    "t02_derive_queue": (
        DEPOT / "recherche/analyse_distributions_taille_revenu/figures/derive_T.png",
        "même campagne",
        "La première queue lourde n'était pas stationnaire : son exposant "
        "dérive avec l'horizon d'observation.",
    ),
    "t03_branchement_m4": (
        DEPOT / "m4_credit_soc_fable/reports/01_soc_final/figures/lot100_branching_ratio.png",
        "m4_credit_soc_fable, rapport 01_soc_final",
        "M4 : le rapport de branchement se stabilise vers 0,30 une fois la "
        "règle annulation–destruction en place.",
    ),
    "t04_taille_finie_m4": (
        DEPOT / "m4_credit_soc_fable/reports/01_soc_final/figures/lots_scaling_finite_size.png",
        "m4_credit_soc_fable, rapport 01_soc_final",
        "M4 : la coupure des avalanches croît avec la taille du système — "
        "signature de taille finie, condition nécessaire d'un candidat SOC.",
    ),
    "t05_effet_echelle_m42": (
        DEPOT / "m4_2_credit_soc/figures/ablation_scale.png",
        "m4_2_credit_soc, campagne M4.2",
        "M4.2 : l'effet attribué naïvement à la concavité γ est dominé par un "
        "déplacement d'échelle du capital.",
    ),
    # ---- Partie 4 : les phénomènes ----
    "p01_lorenz": (
        LAB / "gini_lorenz_snapshots.png",
        f"Simulation Lab, run {SPECIMEN}",
        "L'inégalité ne vit pas dans la taille productive (G = 0,215) mais "
        "dans le revenu d'intérêt (G = 0,595).",
    ),
    "p02_structure_nw": (
        DEPOT / "recherche/sensibilite_m4b/figures/nw_structure.png",
        "recherche/sensibilite_m4b, campagne de 594 simulations",
        "Structure de la valeur nette : cycle de vie débitrice puis "
        "créancière, et trou d'insolvabilité au décès.",
    ),
    "p03_vie_par_taille": (
        LAB / "instantaneous_life_expectancy_by_size.png",
        f"Simulation Lab, run {SPECIMEN}",
        "L'espérance de vie restante croît avec la taille : les grandes "
        "entités survivent plus longtemps, sans être immortelles.",
    ),
    "p04_avalanches_structure": (
        LAB / "soc_avalanche_structure.png",
        f"Simulation Lab, run {SPECIMEN}",
        "Structure causale des avalanches : la part des racines décroît avec "
        "la taille et la profondeur atteint 10 — c'est de la propagation, pas "
        "de la synchronisation.",
    ),
    "p05_cascades_rank_size": (
        LAB / "cascades_rank_size.png",
        f"Simulation Lab, run {SPECIMEN}",
        "Densité, CCDF et volume des cascades : loi de puissance tronquée, "
        "coupure visible dans la fenêtre observable.",
    ),
    "p06_scaling_avalanches": (
        DEPOT / "recherche/sensibilite_m4b/figures/confirm_scaling.png",
        "recherche/sensibilite_m4b, phase de confirmation",
        "Les lois d'échelle des avalanches en fonction de la taille du "
        "système : $s_{\\max} \\propto \\lambda^{0,58}$ et "
        "$\\chi \\propto \\lambda^{0,51}$.",
    ),
    "p07_hierarchie_prcc": (
        DEPOT / "recherche/sensibilite_m4b/figures/lhs_prcc.png",
        "recherche/sensibilite_m4b, criblage LHS",
        "Hiérarchie des paramètres : $\\sigma$, $k$, $K_0$, $\\delta$ et "
        "$\\lambda$ ont des rôles distincts et séparables.",
    ),
    "p08_gini_renouvellement": (
        DEPOT / "recherche/sensibilite_m4b/figures/confirm_gini_renewal.png",
        "recherche/sensibilite_m4b, phase de confirmation",
        "Gini et renouvellement sur graines de confirmation : les deux "
        "inégalités, capital et valeur nette, répondent parfois en sens "
        "opposé.",
    ),
    "p09_cycles_structure": (
        DEPOT / "recherche/sensibilite_m4b/figures/cycles_structure.png",
        "recherche/sensibilite_m4b, extension cycles (post-audit)",
        "Structure des épisodes d'activité : courts, asymétriques, sans "
        "longue récession endogène.",
    ),
    "p10_cycles_sensibilite": (
        DEPOT / "recherche/sensibilite_m4b/figures/cycles_sensibilite.png",
        "recherche/sensibilite_m4b, extension cycles (post-audit)",
        "Ce qui pilote les épisodes : l'amplitude suit σ et K₀, la fréquence "
        "n'est expliquée de façon robuste par aucun paramètre.",
    ),
    "p11_renouvellement_top": (
        LAB / "soc_top_decile_renewal.png",
        f"Simulation Lab, run {SPECIMEN}",
        "Le décile supérieur se renouvelle intégralement en moins de cent "
        "pas : c'est un renouvellement démographique, et non une mobilité "
        "sociale comparable aux données.",
    ),
    "p12_revenu_empirique": (
        LAB / "soc_revenue_fits.png",
        f"Simulation Lab, run {SPECIMEN}",
        "Le revenu brut du modèle, sans ajustement imposé : ni corps "
        "exponentiel net, ni queue de Pareto convaincante sur cette "
        "observable.",
    ),
    "p13_queue_interets": (
        DEPOT / "m4_2b_credit_soc/report/figures/sim_interets_baseline.png",
        "m4_2b_credit_soc, campagne M4.2B",
        "La queue d'intérêts telle qu'elle se voit sur les graphiques — "
        "l'observation qui a motivé le test de Pareto.",
    ),
    "p14_erreur_seuil": (
        DEPOT / "m4_2b_credit_soc/report/figures/fig7_seuil_exemple_travaille.png",
        "m4_2b_credit_soc, campagne M4.2B",
        "Le contrôle d'autosimilarité mal orienté, puis corrigé : à seuil×2 "
        "la queue médiane tombe de 113 à 17 points. L'existence de Pareto "
        "reste une hypothèse.",
    ),
    # ---- Partie 5 : le rebond ----
    "r01_reponse_prod": (
        DEPOT / "m4_3live_credit_soc/report/figures/response_prod.png",
        "m4_3live_credit_soc, campagne M4.3Live",
        "La mesure centrale du rebond : à portée partielle la réponse est "
        "forte puis s'éteint avec la cohorte traitée ; à portée globale elle "
        "s'établit à +36 % pour A×1,5, donc sous-proportionnelle.",
    ),
    "r02_ablation_k0": (
        DEPOT / "m4_3live_credit_soc/report/figures/ablation_k0_levels.png",
        "m4_3live_credit_soc, campagne M4.3Live",
        "Le pivot du verdict : selon que la dotation de naissance K₀ suit ou "
        "non l'échelle technologique, la population se contracte ou non.",
    ),
    "r03_covariance_echelle": (
        DEPOT / "m4_3live_credit_soc/report/figures/scaling_covariance.png",
        "m4_3live_credit_soc, campagne M4.3Live",
        "La covariance d'échelle du moteur, vérifiée numériquement : sous "
        "compensation de K₀, l'élasticité vaut exactement 1/(1−γ).",
    ),
}

#: Figures de M4.4, déjà engendrées en PDF par `scripts/make_figures.py` du
#: programme. Elles sont reprises telles quelles : les régénérer ici les
#: détacherait de `numbers.tex`, que `tests/test_figures.py` confronte.
M4_4 = DEPOT / "m4_4_rebond_credit_soc" / "report" / "figures"
CATALOGUE_M4_4: dict[str, str] = {
    "f01_ancrages": "Les trois élasticités de la lignée sont reproduites sur une campagne neuve.",
    "f03_quantiles": "Où va le surcroît de production : dans le corps, presque proportionnellement, et pas dans la queue.",
    "f04_deciles": "Le premier décile du revenu d'intérêt tombe d'un facteur dix pendant que la médiane double.",
    "f05_position_nette": "La position nette de crédit par âge, et son déplacement sous intervention.",
    "f06_mortalite_rotation": "L'exposant qui relie mortalité et rotation du crédit n'est pas universel : il dépend du levier.",
    "f07_chaine": "La chaîne causale de la contraction, maillon par maillon, avec la valeur de chaque élasticité.",
    "f08_avalanches_ccdf": "Les CCDF d'avalanches par bras : la forme survit au changement de productivité.",
    "f09_b1_b2": "Les deux estimateurs de branchement, et pourquoi il en faut deux.",
    "f10_k0": "La fragilité attribuée au rebond n'est pas la sienne : 97,9 % de l'effet est annulé par la compensation de dotation.",
    "f12_alpha_bras": "Les exposants de queue ne bougent pas d'un bras à l'autre.",
    "f11_couverture": "La couverture de queue n'est plus l'obstacle, et l'exposant ne bouge pas quand l'échantillon grandit de moitié.",
    "f13_vuong": "Le test de Vuong sur les données réelles de campagne, et la dégénérescence prédite.",
    "f14_bargain_population": "La population en fonction du partage du surplus : une non-linéarité forte entre p = 0 et p = 1.",
    "f15_bargain_gini": "L'invariance du Gini de valeur nette au partage, alors que le Gini de capital bouge.",
    "f16_bargain_systeme": "Ce que le partage déplace : branchement, tension, rotation et taux du carnet.",
    "f17_rho_controle": "L'intensité de marché contrôle les deux exposants de queue et les deux estimateurs de branchement.",
    "f18_rotation_rho": "Une relation héritée qui ne survit pas au changement de levier.",
    "f19_ablation": "Ce qui explique l'écart de branchement avec la lignée M4B : 87,8 % attribués, un huitième résiduel.",
    "f20_rampes": "Montée et descente du partage se superposent : retard de relaxation, pas dépendance au chemin.",
    "f21_hasard": "La convexité posée ne tient pas : le risque n'est pas convexe dans le fardeau, et la courbure meurt au conditionnement.",
    "f22_ponderation": "Le mécanisme, et c'est une identité : 0,53 par contrat, 0,94 par joule, l'écart est Cov(p,Δ)/E[Δ].",
    "f23_suffisance": "Sur-détermination et suffisance sont deux choses distinctes : 28,2 % contre un plancher de 51,0 %.",
    "g03_partage_analytique": "Le partage dérivé des seules fonctions du moteur : ½ à la limite infinitésimale, au-delà de 1 sur les paires très inégales.",
}


def empreinte(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()[:12]


#: Caractères qui, laissés bruts, cassent la compilation ou changent le sens.
_SPECIAUX = (("&", r"\&"), ("%", r"\%"), ("_", r"\_"), ("#", r"\#"),
             ("^", r"\textasciicircum{}"))


def coupable(chemin: str) -> str:
    """Autorise LaTeX à couper un chemin long après chaque séparateur.

    `\\texttt` ne coupe pas de lui-même : un chemin de soixante caractères
    déborde alors de la marge. `\\allowbreak` après chaque `/` et chaque
    souligné échappé donne des points de coupure sans ajouter de tiret.
    """
    return (chemin.replace("/", "/\\allowbreak{}")
                  .replace("\\_", "\\_\\allowbreak{}"))


def echappe(texte: str) -> str:
    """Échappe le texte d'une légende, SAUF ce qui est entre `$`.

    Une légende peut avoir besoin de mathématiques --- $s_{\\max} \\propto
    \\lambda^{0,58}$ ne s'écrit pas autrement. Échapper aveuglément casserait
    l'indice et l'exposant ; ne rien échapper casserait le pour-cent et le
    souligné des noms de fichiers. On découpe donc sur les délimiteurs et on
    n'échappe que les segments hors mathématiques.
    """
    morceaux = texte.split("$")
    for i, morceau in enumerate(morceaux):
        if i % 2:  # segment mathématique : laissé intact, délimiteurs compris
            continue
        for brut, remplace in _SPECIAUX:
            morceau = morceau.replace(brut, remplace)
        morceaux[i] = morceau
    return "$".join(morceaux)


#: Annexe de traçabilité par identifiant de run — règle permanente du projet.
#: Une figure d'un run unique porte son `run_id` et ses paramètres. Une figure
#: agrégeant une campagne entière ne PEUT pas porter un identifiant : elle
#: porte celui de la campagne, et renvoie à l'annexe engendrée de celle-ci, qui
#: liste chaque run. Écrire un faux identifiant unique serait pire que de
#: renvoyer.
TRACABILITE: dict[str, tuple[str, str, str]] = {
    #  préfixe de figure -> (identifiant, paramètres, où retrouver le détail)
    "specimen": (
        f"\\code{{{SPECIMEN.replace(chr(95), chr(92) + chr(95))}}}",
        "$\\lambda = 30$, $\\delta = 0{,}05$, $\\sigma = 0{,}5$, $K_0 = 25$, "
        "$k = 2$, $T = 4000$, graine 14, statut \\code{ok}, "
        "population finale 235",
        "\\code{simulation\\_lab\\_data/runs/}"
        f"\\code{{{SPECIMEN.replace(chr(95), chr(92) + chr(95))}}} --- "
        "\\code{run.json}, \\code{config.json}, \\code{series.csv}",
    ),
    "m4b": (
        "campagne \\code{sensibilite\\_m4b} (594 runs)",
        "centre : $\\lambda = 30$, $\\delta = 0{,}05$, $\\sigma = 0{,}25$, "
        "$K_0 = 25$, $k = 3$ ; graines confirmatoires 11--15, $T = 4000$",
        "annexe engendrée \\code{recherche/sensibilite\\_m4b/report/"
        "annexe\\_tracabilite\\_finale.tex} --- un \\code{run\\_id} par ligne",
    ),
    "wip": (
        "campagne du WIP du 27 avril (805 runs, 163 stationnaires)",
        "filtre \\code{bounded\\_tail} et \\code{flow\\_balanced}, calculés par "
        "\\code{detect\\_regime\\_}\\allowbreak{}\\code{diagnostics} "
        "du harnais",
        "\\code{recherche/analyse\\_distributions\\_taille\\_revenu/}",
    ),
    "m4_4": (
        "campagne \\code{m4\\_4\\_rebond\\_credit\\_soc} (372 runs)",
        "12 graines appariées, amorçage partagé jusqu'au pas 2000, "
        "fenêtre sur les 1000 derniers pas",
        "\\code{m4\\_4\\_rebond\\_credit\\_soc/results/analysis/"
        "traceability.csv} et \\code{simulation\\_lab\\_index.csv}",
    ),
    "m4": (
        "campagne \\code{m4\\_credit\\_soc\\_fable} (lots 100)",
        "balayage en $\\lambda$ pour la taille finie ; règle "
        "annulation--destruction",
        "\\code{m4\\_credit\\_soc\\_fable/reports/01\\_soc\\_final/}",
    ),
    "m4_2": (
        "campagne \\code{m4\\_2\\_credit\\_soc}",
        "ablation d'échelle à $\\gamma$ balayé, $K_0/K^*_{\\mathrm{aut}}$ "
        "tenu fixe ou libre",
        "\\code{m4\\_2\\_credit\\_soc/results/} et rapport de lignée",
    ),
    "m4_2b": (
        "campagne \\code{m4\\_2b\\_credit\\_soc}",
        "queue des intérêts reçus ; seuils de Hill, contrôle "
        "d'autosimilarité à seuil$\\times 2$",
        "\\code{m4\\_2b\\_credit\\_soc/results/} et rapport de lignée",
    ),
    "m4_3live": (
        "campagne \\code{m4\\_3live\\_credit\\_soc}",
        "5 graines appariées, intervention à $t_0 = 2000$, horizon 2000 pas ; "
        "$A \\times 1{,}5$ et $A \\times 1{,}25$",
        "\\code{m4\\_3live\\_credit\\_soc/results/analysis/} et "
        "rapport de lignée",
    ),
}

#: préfixe de nom de figure -> clef de TRACABILITE
_ORIGINE = {"m0": "specimen", "p0": None, "p1": None, "t01": "wip",
            "t02": "wip", "f": "m4_4", "g": "m4_4", "r": "lignee",
            "t03": "lignee", "t04": "lignee", "t05": "lignee"}


def origine_de(nom: str, source: str) -> str:
    """Quelle ligne de traçabilité s'applique à cette figure."""
    if str(SPECIMEN) in source:
        return "specimen"
    if "sensibilite_m4b" in source:
        return "m4b"
    if "distributions" in source or "même campagne" in source:
        return "wip"
    if nom[0] in "fg":
        return "m4_4"
    if "m4_credit_soc_fable" in source or "soc\\_final" in source:
        return "m4"
    if "m4_2b" in source or "m4\\_2b" in source:
        return "m4_2b"
    if "m4_2_credit" in source or "m4\\_2\\_credit" in source:
        return "m4_2"
    return "m4_3live"


def ecrit_tracabilite(lignes: list[tuple[str, str, str, str]]) -> None:
    """Annexe de traçabilité : chaque figure renvoyée à son ou ses runs."""
    par_origine: dict[str, list[str]] = {}
    for nom, origine, _etablit, _sha in lignes:
        par_origine.setdefault(origine_de(nom, origine), []).append(nom)

    sortie = [
        "% Engendré par scripts/collect_figures.py — NE PAS ÉDITER À LA MAIN.",
        "",
        # `>{\\raggedright\\arraybackslash}` : sans lui, LaTeX justifie et
        # déborde de la marge dès qu'une cellule contient un chemin long
        # insécable. `\\footnotesize` : la table porte des chemins complets.
        "{\\footnotesize\\setlength{\\tabcolsep}{4pt}",
        "\\begin{longtable}{@{}"
        ">{\\raggedright\\arraybackslash}p{0.19\\textwidth}"
        ">{\\raggedright\\arraybackslash}p{0.27\\textwidth}"
        ">{\\raggedright\\arraybackslash}p{0.22\\textwidth}"
        ">{\\raggedright\\arraybackslash}p{0.26\\textwidth}@{}}",
        "\\toprule",
        "\\textbf{identifiant} & \\textbf{figures de la note} & "
        "\\textbf{paramètres} & \\textbf{où retrouver le détail} \\\\",
        "\\midrule",
        "\\endhead",
    ]
    for clef, (identifiant, parametres, ou) in TRACABILITE.items():
        noms = sorted(par_origine.get(clef, []))
        if not noms:
            continue
        liste = ", ".join(f"\\code{{{coupable(echappe(n))}}}" for n in noms)
        sortie.append(f"{coupable(identifiant)} & {liste} & {parametres} & "
                      f"{coupable(ou)} \\\\")
        sortie.append("\\addlinespace")
    sortie += ["\\bottomrule", "\\end{longtable}}", ""]
    (ICI / "latex" / "tracabilite.tex").write_text("\n".join(sortie),
                                                   encoding="utf-8")
    total = sum(len(v) for v in par_origine.values())
    print(f"annexe de traçabilité écrite : {total} figures rattachées à "
          f"{len(par_origine)} origines")


def macros_m4_4() -> int:
    """Recopie `numbers.tex` de M4.4 avec un en-tête de provenance.

    Les 268 macros sont engendrées par `scripts/make_numbers.py` du programme
    depuis `results/analysis/`. Les recopier plutôt que de les réécrire est la
    seule façon d'être sûr que la note dit exactement ce que le rapport dit ;
    les réécrire à la main rouvrirait la porte à la dérive que le programme
    avait fermée.
    """
    source = DEPOT / "m4_4_rebond_credit_soc" / "report" / "numbers.tex"
    if not source.exists():
        print(f"SOURCE INTROUVABLE : {source}")
        return 0
    entete = (
        "% Recopié par scripts/collect_figures.py depuis\n"
        "%   m4_4_rebond_credit_soc/report/numbers.tex\n"
        f"% empreinte de la source : {empreinte(source)}\n"
        "% Elle-même engendrée par scripts/make_numbers.py depuis results/analysis/.\n"
        "% NE PAS ÉDITER À LA MAIN : rejouer collect_figures.py.\n\n"
    )
    cible = ICI / "latex" / "numbers_m4_4.tex"
    cible.write_text(entete + source.read_text(encoding="utf-8"), encoding="utf-8")
    nombre = source.read_text(encoding="utf-8").count("\\newcommand")
    print(f"{nombre} macros M4.4 recopiées dans {cible}")
    return nombre


def main() -> int:
    FIGURES.mkdir(parents=True, exist_ok=True)
    lignes: list[tuple[str, str, str, str]] = []
    manquantes: list[str] = []
    import re
    incluses = set(re.findall(r"\\figurine\{([^}]+)\}",
                             (ICI / "latex/note_encadrants.tex").read_text()))

    for nom, (source, origine, etablit) in CATALOGUE.items():
        if nom not in incluses:
            continue
        if not source.exists():
            manquantes.append(f"{nom} -> {source}")
            continue
        cible = FIGURES / f"{nom}{source.suffix}"
        shutil.copy2(source, cible)
        lignes.append((nom, origine, etablit, empreinte(source)))

    for nom, etablit in CATALOGUE_M4_4.items():
        if nom not in incluses:
            continue
        source = M4_4 / f"{nom}.pdf"
        if not source.exists():
            manquantes.append(f"{nom} -> {source}")
            continue
        shutil.copy2(source, FIGURES / f"{nom}.pdf")
        lignes.append((
            nom,
            "m4_4_rebond_credit_soc, engendrée par scripts/make_figures.py",
            etablit,
            empreinte(source),
        ))

    if manquantes:
        print("SOURCES INTROUVABLES :", *manquantes, sep="\n  ")
        return 1

    tableau = [
        "% Engendré par scripts/collect_figures.py — NE PAS ÉDITER À LA MAIN.",
        f"% {len(lignes)} figures.",
        "",
        "{\\setlength{\\tabcolsep}{4pt}",
        "\\begin{longtable}{@{}"
        ">{\\raggedright\\arraybackslash}p{0.18\\textwidth}"
        ">{\\raggedright\\arraybackslash}p{0.27\\textwidth}"
        ">{\\raggedright\\arraybackslash}p{0.45\\textwidth}@{}}",
        "\\toprule",
        "\\textbf{figure} & \\textbf{provenance} & \\textbf{ce qu'elle établit} \\\\",
        "\\midrule",
        "\\endhead",
    ]
    for nom, origine, etablit, sha in lignes:
        # `origine` arrive brute du catalogue : c'est `echappe` qui l'échappe,
        # jamais l'appelant. Une chaîne pré-échappée passerait deux fois.
        figure = coupable(echappe(nom))
        source = coupable(echappe(origine))
        tableau.append(
            f"{{\\small\\texttt{{{figure}}}}}\\newline{{\\scriptsize\\texttt{{{sha}}}}} & "
            f"{source} & {echappe(etablit)} \\\\"
        )
    tableau += ["\\bottomrule", "\\end{longtable}}", ""]
    (ICI / "latex" / "provenance.tex").write_text("\n".join(tableau), encoding="utf-8")

    print(f"{len(lignes)} figures copiées dans {FIGURES}")
    print(f"table de provenance écrite dans {ICI / 'latex' / 'provenance.tex'}")
    ecrit_tracabilite(lignes)
    macros_m4_4()
    return verifie_la_note({nom for nom, *_ in lignes})


def verifie_la_note(rassemblees: set[str]) -> int:
    """Toute figure incluse doit exister, toute figure copiée doit servir.

    Ce garde-fou a été ajouté APRÈS avoir manqué cinq inclusions : le texte
    citait `f11_couverture` et quatre autres figures qui n'étaient pas au
    catalogue. LaTeX ne se plaint pas toujours assez fort pour qu'on le voie
    dans un journal de mille lignes, et une figure absente laisse un trou dans
    le document sans arrêter la compilation. C'est le pendant, ici, du test
    `tests/test_figures.py` du programme M4.4.
    """
    note = ICI / "latex" / "note_encadrants.tex"
    if not note.exists():
        return 0
    import re

    incluses = set(re.findall(r"\\figurine\{([^}]+)\}",
                              note.read_text(encoding="utf-8")))
    rassemblees.update(n for n in incluses if n.startswith("rev_") and (FIGURES / f"{n}.pdf").exists())
    absentes = sorted(incluses - rassemblees)
    orphelines = sorted(rassemblees - incluses)
    if absentes:
        print("INCLUSES MAIS NON RASSEMBLÉES :", *absentes, sep="\n  ")
    if orphelines:
        print("RASSEMBLÉES MAIS JAMAIS INCLUSES :", *orphelines, sep="\n  ")
    if not absentes and not orphelines:
        print(f"{len(incluses)} inclusions dans la note, toutes résolues, "
              f"aucune figure orpheline")
    return 1 if absentes else 0


if __name__ == "__main__":
    raise SystemExit(main())
