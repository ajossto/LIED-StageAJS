"""Les figures ne mentent pas, et ne manquent pas.

Trois garde-fous, du même genre que ceux que ce programme s'impose ailleurs :
ce qui est publié doit être engendré, et ce qui est engendré doit coïncider
avec ce qui est écrit.

1. **Aucune figure manquante.** Chaque `\\figurine{...}` des deux rapports doit
   avoir un PDF dans `report/figures/`. Vingt-six inclusions entrent d'un
   coup ; une seule absente ferait échouer la compilation, et l'erreur de
   LaTeX est illisible.

2. **Aucune figure orpheline.** Une figure engendrée que personne n'inclut est
   du travail perdu — ou pire, une figure qu'on croit publiée.

3. **Aucune dérive entre figure et texte.** Les valeurs ANNOTÉES sur les
   figures sont déposées par `save()` dans `report/figures/manifest.json`.
   Chacune est confrontée à la macro correspondante de `report/numbers.tex`.
   C'est le pendant, pour les figures, de la règle « aucun nombre recopié à la
   main » : une figure qui affiche 93 quand le texte dit 98 est un défaut
   silencieux.

Aucun run n'est lancé : le test lit des fichiers déjà écrits.

    /home/anatole/jupyter/.venv/bin/python3 m4_3live_v2_credit_soc/tests/test_figures.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REPORTS = (ROOT / "report" / "rapport_final.tex",
           ROOT / "report" / "conception_m4_3live_v2.tex")
FIGURES = ROOT / "report" / "figures"
NUMBERS = ROOT / "report" / "numbers.tex"

#: Figure annotée -> (macro de `numbers.tex`, décimales, [facteur]).
#:
#: La tolérance est celle de l'ARRONDI de la macro : `make_numbers` écrit un
#: nombre déjà mis en forme, donc comparer au-delà de ses décimales n'aurait
#: pas de sens. Le facteur optionnel vaut 100 quand la macro est en pour cent
#: et la figure en fraction.
#:
#: Une entrée par valeur que le lecteur peut lire DEUX fois — une fois sur la
#: figure, une fois dans le texte. C'est là, et seulement là, qu'une dérive
#: peut passer inaperçue.
COHERENCE = {
    ("f01_institution", "lambda_star"): ("lambdaStarOld", 3),
    ("f01_institution", "seuil_bande"): ("seuilBandeOld", 3),
    ("f02_stationnarite", "controle_hors_bande"): ("nControleHorsBandeResiduel", 0),
    ("f02_stationnarite", "controle_graines"): ("nControleGrainesResiduel", 0),
    ("f04_contrefactuel", "reversed_new_A150"):
        ("pctReversalAhcentCinquanteTransition", 2, 100),
    ("f04_contrefactuel", "blocked_new_A150"):
        ("pctBlockedAhcentCinquanteTransition", 2, 100),
    ("f04_contrefactuel", "volume_new_A150"):
        ("pctVolumeRevAhcentCinquanteTransition", 2, 100),
    ("f04_contrefactuel", "ecart_contrefactuel_max"):
        ("ecartContrefactuelMax", 3),
    ("f05_survivants", "interet_ancienne_libre"): ("survFreeOldInterest", 1, 100),
    ("f05_survivants", "interet_nouvelle_libre"): ("survFreeNewInterest", 1, 100),
    ("f06_apparie", "prod_tot"): ("diffProdAhcentCinquanteTransition", 2, 100),
    ("f06_apparie", "K_tot"): ("diffKtotAhcentCinquanteTransition", 2, 100),
    ("f06_apparie", "deaths_per_pop"): ("diffMortAhcentCinquanteTransition", 2, 100),
    ("f06_apparie", "n_loans"): ("diffNLoansAhcentCinquanteTransition", 2, 100),
    ("f06_apparie", "nulsTransition"): ("nEcartsNulsTransition", 0),
    ("f06_apparie", "totalTransition"): ("nEcartsTransition", 0),
    ("f06_apparie", "nulsResiduel"): ("nEcartsNulsResiduel", 0),
    ("f06_apparie", "totalResiduel"): ("nEcartsResiduel", 0),
    ("f07_creanciers", "corr_K_net_free"): ("niveauCorrKFreeResiduel", 3),
    ("f07_creanciers", "corr_K_net_v1"): ("niveauCorrKVoneResiduel", 3),
    ("f07_creanciers", "corr_marg_net_free"): ("niveauCorrMargFreeResiduel", 3),
    ("f07_creanciers", "corr_marg_net_v1"): ("niveauCorrMargVoneResiduel", 3),
    ("f08_chaine", "n_loans"): ("diffNLoansAhcentCinquanteTransition", 2, 100),
    ("f08_chaine", "interest_paid"): ("diffIntAhcentCinquanteTransition", 2, 100),
    ("f08_chaine", "deaths_per_pop"): ("diffMortAhcentCinquanteTransition", 2, 100),
    ("f08_chaine", "destroyed_per_K"):
        ("diffDestroyedPerKAhcentCinquanteTransition", 2, 100),
    ("f08_chaine", "pop"): ("diffPopAhcentCinquanteTransition", 2, 100),
    ("f08_chaine", "K_tot"): ("diffKtotAhcentCinquanteTransition", 2, 100),
    ("f08_chaine", "prod_tot"): ("diffProdAhcentCinquanteTransition", 2, 100),
    ("f09_loi_en_defaut", "rotation_new_A150"):
        ("diffRotAhcentCinquanteTransition", 2, 100),
    ("f09_loi_en_defaut", "predite_new_A150"):
        ("lawPredAhcentCinquanteTransition", 2, 100),
    ("f09_loi_en_defaut", "mesuree_new_A150"):
        ("diffMortAhcentCinquanteTransition", 2, 100),
    ("f09_loi_en_defaut", "rotation_new_g060"):
        ("diffRotGammaSixZeroTransition", 2, 100),
    ("f09_loi_en_defaut", "predite_new_g060"):
        ("lawPredGammaSixZeroTransition", 2, 100),
    ("f09_loi_en_defaut", "mesuree_new_g060"):
        ("diffMortGammaSixZeroTransition", 2, 100),
    ("f09_loi_en_defaut", "rotation_new_A075"):
        ("diffRotAzeroSeptCinqTransition", 2, 100),
    ("f09_loi_en_defaut", "predite_new_A075"):
        ("lawPredAzeroSeptCinqTransition", 2, 100),
    ("f09_loi_en_defaut", "mesuree_new_A075"):
        ("diffMortAzeroSeptCinqTransition", 2, 100),
    ("f10_service_ratio", "n_debitrices"): ("ratioNResiduel", 0),
    ("f10_service_ratio", "minimum"): ("ratioMinResiduel", 4),
    ("f10_service_ratio", "seuil"): ("ratioSeuilResiduel", 4),
    ("f11_redistribution", "defauts_mesures"): ("lotEMeasuredDefaultsResiduel", 3),
    ("f11_redistribution", "prod_tot"): ("lotEProdResiduel", 2, 100),
    ("f11_redistribution", "part_redistribuee"): ("lotERedistShareResiduel", 4, 100),
    ("f12_tension", "tension_controle"): ("tensionControleResiduel", 1),
    ("f12_tension", "jensen_controle"): ("jensenControleResiduel", 4),
    ("f13_amplitude", "m_AllA"): ("amplAllAM", 6),
    ("f13_amplitude", "naive_AllA"): ("amplAllANaive", 6),
    ("f13_amplitude", "keq_AllA"): ("amplAllAKeq", 6),
    ("f13_amplitude", "p_AllA"): ("amplAllAP", 6),
    ("f13_amplitude", "m_FractionA"): ("amplFractionAM", 6),
    ("f13_amplitude", "naive_FractionA"): ("amplFractionANaive", 6),
    ("f13_amplitude", "keq_FractionA"): ("amplFractionAKeq", 6),
    ("f13_amplitude", "m_NewA"): ("amplNewAM", 6),
    ("f13_amplitude", "naive_NewA"): ("amplNewANaive", 6),
    ("f13_amplitude", "keq_NewA"): ("amplNewAKeq", 6),
    ("f13_amplitude", "p_Gamma"): ("amplGammaP", 6),
    ("f13_amplitude", "m_Gamma"): ("amplGammaM", 6),
    ("f13_amplitude", "naive_Gamma"): ("amplGammaNaive", 6),
    ("f13_amplitude", "keq_Gamma"): ("amplGammaKeq", 6),
    ("f13_amplitude", "p_NewA"): ("amplNewAP", 6),
    ("f13_amplitude", "p_FractionA"): ("amplFractionAP", 6),
    ("f14_decomposition", "f1_gap"): ("rotFOneGap", 3),
    ("f14_decomposition", "f2_min"): ("rotFTwoMin", 4),
    ("f14_decomposition", "f2_max"): ("rotFTwoMax", 4),
    ("f15_gini", "gini_free"): ("giniKFree", 4),
    ("f15_gini", "gini_richest_lends"): ("giniKVone", 4),
    ("f15_gini", "biais_avant"): ("rotGapGiniBeforeMed", 1, 100),
    ("f15_gini", "biais_logmean"): ("rotGapGiniLogMed", 1, 100),
    ("f16_fermeture", "ecart_median"): ("rotGapClosedFormMed", 1, 100),
    ("f16_fermeture", "pente_groupee"): ("rotSlopeClosureRot", 3),
    ("f16_fermeture", "r2_groupe"): ("rotRtwoClosureRot", 4),
    ("f17_leviers", "pente_rho"): ("leverSlopeRho", 3),
    ("f17_leviers", "pente_K0"): ("leverSlopeKzero", 3),
    ("f17_leviers", "pente_sigma"): ("leverSlopeSigma", 3),
    ("f17_leviers", "pente_lam"): ("leverSlopeLam", 3),
    ("f17_leviers", "pente_delta"): ("leverSlopeDelta", 3),
    ("f17_leviers", "pente_groupee"): ("rotSlopeClosureRot", 3),
    ("f18_hetero", "median_free"): ("heteroFreeMed", 2, 100),
    ("f18_hetero", "median_richest_lends"): ("heteroVoneMed", 2, 100),
    ("f19_mortalite_rotation", "pente"): ("rotSlopeMortAll", 3),
    ("f19_mortalite_rotation", "r2"): ("rotRtwoMortAll", 4),
    ("f19_mortalite_rotation", "n"): ("rotNMortAll", 0),
    ("f19_mortalite_rotation", "span"): ("rotSpanMortAll", 1),
    ("g01_cout", "clefs_v1"): ("costVoneKeys", 0),
    ("g01_cout", "clefs_v2"): ("costVtwoKeys", 0),
    ("g01_cout", "croissance_v1"): ("costVoneGrowth", 3),
    ("g01_cout", "croissance_v2"): ("costVtwoGrowth", 3),
    ("g01_cout", "part_vide"): ("costEmptyShare", 1, 100),
    ("g02_parite", "pas"): ("parityNPas", 0),
    ("g02_parite", "ecart_max"): ("parityEcartMax", 0),
}


#: Figures PUREMENT ANALYTIQUES : elles ne tracent aucune donnée mesurée, donc
#: elles n'ont rien à déposer. Toutes les autres lisent `results/`, qui est
#: ignoré par git — sans dépôt, la figure ne serait pas reproductible depuis
#: le dépôt seul, et la règle énoncée dans les deux rapports serait fausse.
ANALYTIQUES = {"g04_ordre_phases"}


def read_macros() -> dict[str, str]:
    text = NUMBERS.read_text(encoding="utf-8")
    return dict(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}\{(.*?)\}\n", text))


def to_float(raw: str) -> float:
    """Les macros sont mises en forme à la française : virgule décimale et
    espace fine insécable aux milliers. Il faut défaire les deux."""
    cleaned = (raw.replace("\u202f", "").replace("\u00a0", "")
               .replace("\\,", "").replace(" ", ""))
    return float(cleaned.replace(",", "."))


def included() -> dict[str, list[str]]:
    """Nom de figure -> rapports qui l'incluent."""
    out: dict[str, list[str]] = {}
    for report in REPORTS:
        if not report.exists():
            continue
        for name in re.findall(r"\\figurine\{([^}]+)\}",
                               report.read_text(encoding="utf-8")):
            out.setdefault(name, []).append(report.name)
    return out


def test_aucune_figure_manquante() -> None:
    missing = [name for name in included() if not (FIGURES / f"{name}.pdf").exists()]
    assert not missing, f"figures incluses mais absentes de report/figures/ : {missing}"
    total = sum(len(v) for v in included().values())
    print(f"  {total} inclusions ({len(included())} figures), toutes résolues")


def test_aucune_figure_orpheline() -> None:
    produced = {path.stem for path in FIGURES.glob("*.pdf")}
    orphans = sorted(produced - set(included()))
    assert not orphans, f"figures engendrées que personne n'inclut : {orphans}"
    print(f"  {len(produced)} figures engendrées, aucune orpheline")


def test_toute_figure_mesuree_depose_sa_serie() -> None:
    """La règle énoncée dans les deux rapports : une figure qui lit une source
    non versionnée dépose la série RÉELLEMENT TRACÉE dans
    `report/figures/data/`. Sans ce test, la règle se périme à la prochaine
    figure ajoutée — et le rapport affirmerait quelque chose de faux."""
    data = FIGURES / "data"
    deposited = {path.stem for path in data.glob("*.csv")} if data.exists() else set()
    missing = sorted(name for name in included()
                     if name not in ANALYTIQUES
                     and not any(stem == name or stem.startswith(name + "_")
                                 for stem in deposited))
    assert not missing, ("figures sans série déposée dans report/figures/data/ : "
                         f"{missing}")
    orphan = sorted(stem for stem in deposited
                    if not any(stem == name or stem.startswith(name + "_")
                               for name in included()))
    assert not orphan, f"séries déposées sans figure : {orphan}"
    print(f"  {len(deposited)} séries déposées, "
          f"{len(ANALYTIQUES)} figure(s) analytique(s) dispensée(s)")


def test_figures_coherentes_avec_les_macros() -> None:
    manifest_path = FIGURES / "manifest.json"
    assert manifest_path.exists(), "manifeste absent : lancer scripts/make_figures.py"
    manifest = {entry["nom"]: entry["valeurs"]
                for entry in json.loads(manifest_path.read_text(encoding="utf-8"))}
    macros = read_macros()
    problems: list[str] = []
    for (figure, key), spec in sorted(COHERENCE.items()):
        macro, digits = spec[0], spec[1]
        factor = spec[2] if len(spec) > 2 else 1
        if figure not in manifest:
            problems.append(f"{figure} : absente du manifeste")
            continue
        if key not in manifest[figure]:
            problems.append(f"{figure}.{key} : valeur non annotée")
            continue
        if macro not in macros:
            problems.append(f"{figure}.{key} : macro \\{macro} inconnue")
            continue
        drawn = manifest[figure][key]
        if drawn is None or drawn != drawn:
            problems.append(f"{figure}.{key} : la figure annote NaN")
            continue
        written = to_float(macros[macro])
        rounded = round(factor * drawn, digits)
        if abs(rounded - written) > 0.5 * 10 ** (-digits) + 1e-12:
            problems.append(f"{figure}.{key} = {rounded} mais \\{macro} = {written}")
    assert not problems, "figure et texte divergent :\n  " + "\n  ".join(problems)
    print(f"  {len(COHERENCE)} valeurs annotées, toutes conformes à numbers.tex")


def test_toute_figure_annotee_est_couverte() -> None:
    """Une figure peut annoter une valeur sans entrée dans COHERENCE ; ce
    serait un trou dans le garde-fou, pas une erreur de rendu. Le test le
    signale plutôt que de le laisser passer."""
    manifest = json.loads((FIGURES / "manifest.json").read_text(encoding="utf-8"))
    uncovered = [(entry["nom"], key) for entry in manifest
                 for key in entry["valeurs"]
                 if (entry["nom"], key) not in COHERENCE]
    assert not uncovered, ("valeurs annotées sans macro de contrôle : "
                           f"{uncovered}")
    print(f"  aucune valeur annotée hors du garde-fou")


def main() -> int:
    print("test_figures.py — les figures engendrées, incluses, et fidèles au texte")
    test_aucune_figure_manquante()
    test_aucune_figure_orpheline()
    test_toute_figure_mesuree_depose_sa_serie()
    test_figures_coherentes_avec_les_macros()
    test_toute_figure_annotee_est_couverte()
    print("test_figures.py : tout est passé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
